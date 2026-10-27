"""Chronos Team API, static app, and interval-correct reports."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, time as dtime, timedelta, timezone
from bisect import bisect_right
from urllib.parse import urlsplit
import unicodedata
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.storage import CATEGORIES, FOCUS_CATEGORIES, DomainError, Store, utc_now_ms

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = Path(os.getenv("CHRONOS_DB", str(ROOT.parent / "data" / "chronos.sqlite3")))


def clean_field(value: str, minimum: int) -> str:
    # Prevent misleading bidirectional controls and invisible control characters.
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value):
        raise ValueError("Невидимые или управляющие символы не допускаются")
    normalized = " ".join(value.split())
    if len(normalized) < minimum:
        raise ValueError(f"Необходимо минимум {minimum} символа")
    return normalized


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=80)
    position: str = Field(min_length=2, max_length=80)
    weekly_target_hours: int = Field(default=40, ge=1, le=80)

    @field_validator("full_name", "position")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return clean_field(value, 2)


class TimerStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: int = Field(ge=1)
    description: str = Field(min_length=3, max_length=240)
    category: str = "Разработка"

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        return clean_field(value, 3)

    @field_validator("category")
    @classmethod
    def allowed_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Недопустимая категория")
        return value


class EntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=3, max_length=240)
    category: str

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return TimerStart.description_not_blank(value)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return TimerStart.allowed_category(value)


def _local_days(start_ms: int, end_ms: int, tz: ZoneInfo) -> list[tuple[str, int, int]]:
    start_utc = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
    end_utc = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
    local_day = start_utc.astimezone(tz).date()
    result = []
    while True:
        midnight = datetime.combine(local_day, dtime.min, tzinfo=tz)
        following = midnight + timedelta(days=1)
        begin_ms = int(midnight.timestamp() * 1000)
        finish_ms = int(following.timestamp() * 1000)
        if begin_ms >= end_ms:
            break
        result.append((local_day.isoformat(), begin_ms, finish_ms))
        local_day += timedelta(days=1)
        if len(result) > 373:
            break
    return result


def build_report(rows: list[dict], employees: list[dict], start_ms: int, end_ms: int, tz: ZoneInfo, now_ms: int) -> dict:
    # Half-open intervals [start, end): entries crossing report boundaries
    # contribute only their overlapping duration. Active timers are sampled once.
    days = _local_days(start_ms, end_ms, tz)
    by_employee = {
        emp["id"]: {
            "id": emp["id"], "full_name": emp["full_name"], "position": emp["position"],
            "weekly_target_hours": emp["weekly_target_hours"], "tracked_ms": 0,
            "focus_ms": 0, "entries_count": 0,
            "active_entry_id": emp["active_entry_id"],
            "active_description": emp["active_description"],
            "active_category": emp["active_category"],
            "active_started_at_ms": emp["active_started_at_ms"],
        }
        for emp in employees
    }
    daily = [{"day": day, "tracked_ms": 0} for day, _, _ in days]
    day_finishes = [finish for _, _, finish in days]
    detailed = []
    total_ms = 0
    focus_ms = 0
    for row in rows:
        # A report is a snapshot: even completed entries must never extend
        # beyond the sampled server time.
        actual_end = min(now_ms, row["ended_at_ms"] if row["ended_at_ms"] is not None else now_ms)
        overlap_start = max(start_ms, row["started_at_ms"])
        overlap_end = min(end_ms, actual_end)
        overlap_ms = max(0, overlap_end - overlap_start)
        if not overlap_ms:
            continue
        decorated = {**row, "overlap_ms": overlap_ms}
        detailed.append(decorated)
        total_ms += overlap_ms
        member = by_employee[row["employee_id"]]
        member["tracked_ms"] += overlap_ms
        member["entries_count"] += 1
        if row["category"] in FOCUS_CATEGORIES:
            member["focus_ms"] += overlap_ms
            focus_ms += overlap_ms
        # Only visit the local calendar days this entry actually overlaps.
        # This avoids O(entries × entire report period) work.
        index = bisect_right(day_finishes, overlap_start)
        while index < len(days) and days[index][1] < overlap_end:
            _, day_start, day_end = days[index]
            chunk = max(0, min(overlap_end, day_end) - max(overlap_start, day_start))
            if chunk:
                daily[index]["tracked_ms"] += chunk
            index += 1
    active_count = sum(emp["active_entry_id"] is not None for emp in employees)
    return {
        "start_ms": start_ms, "end_ms": end_ms, "now_ms": now_ms,
        "summary": {
            "employees": len(employees), "active_timers": active_count,
            "tracked_ms": total_ms, "focus_ms": focus_ms,
            "entries_count": len(detailed),
        },
        "employees": list(by_employee.values()), "entries": detailed,
        "daily": daily, "categories": list(CATEGORIES),
    }




class LimitedBodyMiddleware:
    """Bound API write bodies even for HTTP chunked/no Content-Length requests."""

    def __init__(self, app, limit: int = 16_384):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or not scope.get("path", "").startswith("/api/")
                or scope.get("method") in {"GET", "HEAD", "OPTIONS"}):
            return await self.app(scope, receive, send)
        buffered = []
        total = 0
        while True:
            item = await receive()
            if item["type"] != "http.request":
                # Stop processing if the client disconnects while uploading.
                return
            total += len(item.get("body", b""))
            if total > self.limit:
                response = JSONResponse({"detail": "Тело запроса слишком велико"}, status_code=413)
                return await response(scope, receive, send)
            buffered.append(item)
            if not item.get("more_body", False):
                break

        async def replay_receive():
            if buffered:
                return buffered.pop(0)
            return await receive()

        return await self.app(scope, replay_receive, send)


def create_app(database_path: str | Path | None = None, *, seed_demo: bool = True) -> FastAPI:
    store = Store(database_path or DEFAULT_DB)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.init(seed_demo=seed_demo)
        yield

    app = FastAPI(title="Chronos Team API", description="Local async time tracker", version="2.0.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")

    # Mitigates DNS rebinding on a local, unauthenticated development server.
    # To use another trusted host behind a reverse proxy, explicitly configure
    # CHRONOS_ALLOWED_HOSTS (comma-separated); never publish without auth.
    allowed_hosts = [h.strip() for h in os.getenv(
        "CHRONOS_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver"
    ).split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.add_middleware(LimitedBodyMiddleware, limit=16_384)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        # No sign-in is intentionally available in this local demo. A malicious
        # external website must still not be able to mutate localhost via forms.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            # Non-simple request header makes unauthenticated localhost POST
            # impossible from an ordinary cross-origin HTML form. A remote
            # fetch with this header would need a successful CORS preflight;
            # we do not enable CORS anywhere in the application.
            if request.url.path.startswith("/api/") and request.headers.get("x-chronos-request") != "1":
                return JSONResponse({"detail": "Требуется заголовок X-Chronos-Request: 1"}, status_code=403)
            fetch_site = request.headers.get("sec-fetch-site", "")
            # This unauthenticated application is intentionally LOCAL ONLY.
            # Fetch Metadata protects modern browsers; Origin/Referer provide
            # an independent fallback. CLI clients with neither are supported.
            if fetch_site in {"cross-site", "same-site"}:
                return JSONResponse({"detail": "Межсайтовые изменения запрещены"}, status_code=403)
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            expected_origin = (request.url.scheme, request.url.netloc)
            if origin or referer:
                source = urlsplit(origin or referer or "")
                if ((source.scheme, source.netloc) != expected_origin or
                        (origin is not None and (source.path or source.query or source.fragment))):
                    return JSONResponse({"detail": "Недопустимый источник запроса"}, status_code=403)
            if request.url.path.startswith("/api/"):
                size = request.headers.get("content-length")
                if size and size.isdecimal() and int(size) > 16_384:
                    return JSONResponse({"detail": "Тело запроса слишком велико"}, status_code=413)
                expects_json = (request.method in {"POST", "PUT", "PATCH"} and
                                not (request.method == "POST" and
                                     request.url.path.endswith("/stop")))
                if expects_json and "application/json" not in request.headers.get("content-type", "").lower():
                    return JSONResponse({"detail": "Ожидается application/json"}, status_code=415)
        response = await call_next(request)
        response.headers["X-Request-ID"] = uuid.uuid4().hex
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(DomainError)
    async def domain_exception(_req: Request, exc: DomainError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.get("/api/health")
    async def health():
        if not await store.check_health():
            raise HTTPException(503, "Хранилище временно недоступно")
        return {"status": "ok"}

    @app.get("/api/employees")
    async def employees():
        return await store.employees()

    @app.post("/api/employees", status_code=201)
    async def add_employee(payload: EmployeeCreate):
        return await store.add_employee(payload.full_name, payload.position, payload.weekly_target_hours)

    @app.put("/api/employees/{employee_id}")
    async def edit_employee(employee_id: int, payload: EmployeeCreate):
        if employee_id < 1:
            raise HTTPException(422, "Недопустимый идентификатор сотрудника")
        return await store.update_employee(
            employee_id, payload.full_name, payload.position, payload.weekly_target_hours
        )

    @app.post("/api/timers/start", status_code=201)
    async def start_timer(payload: TimerStart):
        return await store.start_timer(payload.employee_id, payload.description, payload.category)

    @app.post("/api/timers/{employee_id}/stop")
    async def stop_timer(employee_id: int):
        if employee_id < 1:
            raise HTTPException(422, "Недопустимый идентификатор сотрудника")
        return await store.stop_timer(employee_id)

    @app.put("/api/entries/{entry_id}")
    async def edit_entry(entry_id: int, payload: EntryUpdate):
        return await store.update_entry(entry_id, payload.description, payload.category)

    @app.delete("/api/entries/{entry_id}", status_code=204)
    async def delete_entry(entry_id: int):
        await store.delete_entry(entry_id)

    @app.get("/api/audit")
    async def audit_events(limit: int = Query(default=100, ge=1, le=500),
                           employee_id: int | None = Query(default=None, ge=1)):
        return await store.audit_events(limit=limit, employee_id=employee_id)

    @app.get("/api/report")
    async def get_report(
        start_ms: int = Query(ge=0), end_ms: int = Query(ge=0),
        employee_id: int | None = Query(default=None, ge=1),
        tz: str = Query(default="UTC", min_length=1, max_length=80),
    ):
        # Supported epoch range: Unix epoch through (exclusive) 2100-01-01.
        # Reject extreme integers before calling datetime.fromtimestamp.
        if (end_ms <= start_ms or end_ms > 4_102_444_800_000
                or end_ms - start_ms > 371 * 86_400_000):
            raise HTTPException(422, "Некорректный период (максимум 371 день)")
        try:
            zone = ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            raise HTTPException(422, "Неизвестный часовой пояс") from None
        staff, rows, now_ms = await store.report_snapshot(start_ms, end_ms, employee_id)
        return build_report(rows, staff, start_ms, end_ms, zone, now_ms)

    app.mount("/assets", StaticFiles(directory=ROOT / "static"), name="assets")

    @app.get("/api/docs", include_in_schema=False)
    async def docs():
        return FileResponse(ROOT / "static" / "api-docs.html")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app(seed_demo=os.getenv("CHRONOS_SEED_DEMO", "1").lower() not in {"0", "false", "no"})
