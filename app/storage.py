"""SQLite repository.

Each operation is executed in asyncio.to_thread so synchronous SQLite calls never
block the ASGI event loop. Every operation owns its connection. Writes use
BEGIN IMMEDIATE and a partial UNIQUE index to prevent duplicate active timers.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

CATEGORIES = ("Разработка", "Тестирование", "Дизайн", "Аналитика", "Встречи", "Другое")
FOCUS_CATEGORIES = frozenset(CATEGORIES[:4])

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS employees (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL CHECK(length(full_name) BETWEEN 2 AND 80),
  position TEXT NOT NULL CHECK(length(position) BETWEEN 2 AND 80),
  weekly_target_hours INTEGER NOT NULL DEFAULT 40
    CHECK(weekly_target_hours BETWEEN 1 AND 80),
  created_at_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
  description TEXT NOT NULL CHECK(length(description) BETWEEN 3 AND 240),
  category TEXT NOT NULL CHECK(category IN ('Разработка', 'Тестирование', 'Дизайн', 'Аналитика', 'Встречи', 'Другое')),
  started_at_ms INTEGER NOT NULL,
  ended_at_ms INTEGER,
  CHECK(ended_at_ms IS NULL OR ended_at_ms >= started_at_ms)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_timer_per_employee
  ON entries(employee_id) WHERE ended_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS ix_entries_employee_dates
  ON entries(employee_id, started_at_ms, ended_at_ms);
CREATE INDEX IF NOT EXISTS ix_entries_start ON entries(started_at_ms);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at_ms INTEGER NOT NULL,
  action TEXT NOT NULL CHECK(action IN (
    'employee.created','employee.updated','timer.started','timer.stopped',
    'entry.updated','entry.deleted'
  )),
  entity_type TEXT NOT NULL CHECK(entity_type IN ('employee','entry')),
  entity_id INTEGER NOT NULL,
  employee_id INTEGER,
  before_json TEXT,
  after_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_events_occurred ON audit_events(occurred_at_ms, id);
CREATE TRIGGER IF NOT EXISTS prevent_audit_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS prevent_audit_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END;
"""


def utc_now_ms() -> int:
    return time.time_ns() // 1_000_000


class DomainError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _audit(db: sqlite3.Connection, action: str, entity_type: str, entity_id: int,
           employee_id: int | None, before: dict | None, after: dict | None) -> None:
    # Written in the SAME transaction as the change: never log a failed mutation.
    db.execute("""INSERT INTO audit_events
      (occurred_at_ms,action,entity_type,entity_id,employee_id,before_json,after_json)
      VALUES (?,?,?,?,?,?,?)""", (
        utc_now_ms(), action, entity_type, entity_id, employee_id,
        json.dumps(before, ensure_ascii=False, sort_keys=True) if before else None,
        json.dumps(after, ensure_ascii=False, sort_keys=True) if after else None,
    ))


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=8.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=8000")
        return conn

    async def _run(self, callback: Callable[[sqlite3.Connection], T]) -> T:
        def worker() -> T:
            conn = self._connect()
            try:
                return callback(conn)
            finally:
                conn.close()
        return await asyncio.to_thread(worker)

    async def init(self, *, seed_demo: bool = True) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def worker() -> None:
            # sqlite3.Connection's context manager commits but does NOT close.
            # Explicit finally is necessary to avoid leaking a connection.
            db = self._connect()
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.executescript(SCHEMA)
                if not seed_demo:
                    return
                # Check-and-seed is one write transaction. Concurrent app workers
                # may initialize the same empty database at the same time.
                db.execute("BEGIN IMMEDIATE")
                try:
                    if db.execute("SELECT 1 FROM employees LIMIT 1").fetchone():
                        db.execute("COMMIT")
                        return
                except Exception:
                    db.execute("ROLLBACK")
                    raise
                # Every sample person and time entry is entirely fictional.
                names = [
                    ("Ирина Волкова", "Продуктовый дизайнер", 40),
                    ("Тимур Сафин", "Frontend-разработчик", 40),
                    ("Мария Ким", "Бизнес-аналитик", 40),
                    ("Артём Лебедев", "QA-инженер", 40),
                    ("София Алиева", "Проектный менеджер", 40),
                    ("Даниил Морозов", "Backend-разработчик", 40),
                ]
                now = utc_now_ms()
                try:
                    for name, position, hours in names:
                        db.execute("INSERT INTO employees(full_name,position,weekly_target_hours,created_at_ms) VALUES (?,?,?,?)", (name, position, hours, now))
                    today = datetime.now(timezone.utc).date()
                    tasks = [
                        ("Прототипирование интерфейса", "Дизайн"),
                        ("Разработка интерфейса отчётов", "Разработка"),
                        ("Анализ требований проекта", "Аналитика"),
                        ("Проверка сценариев таймера", "Тестирование"),
                        ("Командный синк и планирование", "Встречи"),
                        ("Рефакторинг серверного API", "Разработка"),
                    ]
                    for offset in range(1, 13):
                        day = today - timedelta(days=offset)
                        if day.weekday() >= 5:
                            continue
                        for i, (description, category) in enumerate(tasks):
                            begin = datetime(day.year, day.month, day.day, 8 + (i % 3), 10, tzinfo=timezone.utc)
                            start = int(begin.timestamp() * 1000)
                            duration = (90 + ((i * 37 + offset * 23) % 160)) * 60_000
                            db.execute(
                                "INSERT INTO entries(employee_id,description,category,started_at_ms,ended_at_ms) VALUES (?,?,?,?,?)",
                                (i + 1, description, category, start, start + duration),
                            )
                    db.execute("COMMIT")
                except Exception:
                    db.execute("ROLLBACK")
                    raise
            finally:
                db.close()

        def initialize_with_retry() -> None:
            # First startup can run in multiple processes/threads. SQLite may
            # raise SQLITE_BUSY immediately while switching to WAL, even when
            # busy_timeout is enabled. Retry *only* transient lock errors.
            for attempt in range(7):
                try:
                    worker()
                    return
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or attempt == 6:
                        raise
                    time.sleep(min(0.03 * (2 ** attempt), 0.3))

        await asyncio.to_thread(initialize_with_retry)

    async def check_health(self) -> bool:
        """Probe the real database; HTTP responsiveness alone is insufficient."""
        def worker(db: sqlite3.Connection) -> bool:
            db.execute("SELECT 1 FROM employees LIMIT 1").fetchone()
            return True
        try:
            return await self._run(worker)
        except sqlite3.Error:
            return False

    async def employees(self) -> list[dict[str, Any]]:
        def worker(db: sqlite3.Connection) -> list[dict[str, Any]]:
            rows = db.execute("""SELECT e.*, t.id AS active_entry_id, t.description AS active_description,
                t.category AS active_category, t.started_at_ms AS active_started_at_ms
                FROM employees e LEFT JOIN entries t ON t.employee_id=e.id AND t.ended_at_ms IS NULL
                ORDER BY e.id""").fetchall()
            return [dict(row) for row in rows]
        return await self._run(worker)

    async def add_employee(self, name: str, position: str, hours: int) -> dict[str, Any]:
        def worker(db: sqlite3.Connection) -> dict[str, Any]:
            db.execute("BEGIN IMMEDIATE")
            try:
                cursor = db.execute("INSERT INTO employees(full_name,position,weekly_target_hours,created_at_ms) VALUES (?,?,?,?)", (name, position, hours, utc_now_ms()))
                result = dict(db.execute("SELECT * FROM employees WHERE id=?", (cursor.lastrowid,)).fetchone())
                _audit(db, "employee.created", "employee", result["id"], result["id"], None, result)
                db.execute("COMMIT")
                return result
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def update_employee(self, employee_id: int, name: str, position: str, hours: int) -> dict[str, Any]:
        def worker(db: sqlite3.Connection) -> dict[str, Any]:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
                if existing is None:
                    raise DomainError("Сотрудник не найден", 404)
                db.execute("UPDATE employees SET full_name=?, position=?, weekly_target_hours=? WHERE id=?",
                           (name, position, hours, employee_id))
                result = dict(db.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone())
                _audit(db, "employee.updated", "employee", employee_id, employee_id, dict(existing), result)
                db.execute("COMMIT")
                return result
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def start_timer(self, employee_id: int, description: str, category: str) -> dict[str, Any]:
        def worker(db: sqlite3.Connection) -> dict[str, Any]:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT 1 FROM employees WHERE id=?", (employee_id,)).fetchone() is None:
                    raise DomainError("Сотрудник не найден", 404)
                if db.execute("SELECT 1 FROM entries WHERE employee_id=? AND ended_at_ms IS NULL", (employee_id,)).fetchone():
                    raise DomainError("У сотрудника уже запущен таймер. Сначала остановите его.", 409)
                cursor = db.execute(
                    "INSERT INTO entries(employee_id,description,category,started_at_ms) VALUES (?,?,?,?)",
                    (employee_id, description, category, utc_now_ms()),
                )
                result = dict(db.execute("SELECT * FROM entries WHERE id=?", (cursor.lastrowid,)).fetchone())
                _audit(db, "timer.started", "entry", result["id"], employee_id, None, result)
                db.execute("COMMIT")
                return result
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def stop_timer(self, employee_id: int) -> dict[str, Any]:
        def worker(db: sqlite3.Connection) -> dict[str, Any]:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM entries WHERE employee_id=? AND ended_at_ms IS NULL", (employee_id,)).fetchone()
                if not row:
                    if not db.execute("SELECT 1 FROM employees WHERE id=?", (employee_id,)).fetchone():
                        raise DomainError("Сотрудник не найден", 404)
                    raise DomainError("У сотрудника нет активного таймера", 409)
                end_ms = max(utc_now_ms(), row["started_at_ms"])
                db.execute("UPDATE entries SET ended_at_ms=? WHERE id=? AND ended_at_ms IS NULL", (end_ms, row["id"]))
                result = dict(db.execute("SELECT * FROM entries WHERE id=?", (row["id"],)).fetchone())
                _audit(db, "timer.stopped", "entry", row["id"], employee_id, dict(row), result)
                db.execute("COMMIT")
                return result
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def update_entry(self, entry_id: int, description: str, category: str) -> dict[str, Any]:
        def worker(db: sqlite3.Connection) -> dict[str, Any]:
            db.execute("BEGIN IMMEDIATE")
            try:
                before = db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
                if before is None:
                    raise DomainError("Запись не найдена", 404)
                db.execute("UPDATE entries SET description=?, category=? WHERE id=?", (description, category, entry_id))
                result = dict(db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone())
                _audit(db, "entry.updated", "entry", entry_id, result["employee_id"], dict(before), result)
                db.execute("COMMIT")
                return result
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def delete_entry(self, entry_id: int) -> None:
        def worker(db: sqlite3.Connection) -> None:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
                if not row:
                    raise DomainError("Запись не найдена", 404)
                if row["ended_at_ms"] is None:
                    raise DomainError("Активную запись нельзя удалить. Остановите таймер.", 409)
                db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
                _audit(db, "entry.deleted", "entry", entry_id, row["employee_id"], dict(row), None)
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        await self._run(worker)

    async def report_snapshot(
        self, start_ms: int, end_ms: int, employee_id: int | None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Return staff, entries, and one clock sample from the same DB snapshot.

        All report reads share one SQLite read transaction instead of racing
        between separate employee and entry requests. The database connection
        is only used inside a worker thread and is always closed by _run.
        """
        def worker(db: sqlite3.Connection) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
            db.execute("BEGIN")
            try:
                # Establish the SQLite snapshot before sampling the clock.
                employees = [dict(row) for row in db.execute("""
                    SELECT e.*, t.id AS active_entry_id,
                           t.description AS active_description,
                           t.category AS active_category,
                           t.started_at_ms AS active_started_at_ms
                    FROM employees e
                    LEFT JOIN entries t ON t.employee_id=e.id AND t.ended_at_ms IS NULL
                    ORDER BY e.id
                """).fetchall()]
                if employee_id is not None and not any(e["id"] == employee_id for e in employees):
                    raise DomainError("Сотрудник не найден", 404)
                now_ms = utc_now_ms()
                # A future period should not read future-dated records.
                cutoff = min(end_ms, now_ms)
                sql = """SELECT t.*, e.full_name, e.position FROM entries t
                    JOIN employees e ON e.id=t.employee_id
                    WHERE t.started_at_ms < ?
                      AND (t.ended_at_ms IS NULL OR t.ended_at_ms > ?)"""
                args: list[Any] = [cutoff, start_ms]
                if employee_id is not None:
                    sql += " AND t.employee_id=?"
                    args.append(employee_id)
                sql += " ORDER BY t.started_at_ms DESC, t.id DESC"
                # Return a bounded result set; prevents accidental giant reports
                # from exhausting RAM or blocking the UI for a large database.
                rows = [dict(row) for row in db.execute(sql, args).fetchmany(20_001)]
                if len(rows) > 20_000:
                    raise DomainError("Слишком много записей для отчёта: выберите более короткий период", 413)
                db.execute("COMMIT")
                if employee_id is not None:
                    employees = [e for e in employees if e["id"] == employee_id]
                return employees, rows, now_ms
            except Exception:
                db.execute("ROLLBACK")
                raise
        return await self._run(worker)

    async def audit_events(self, *, limit: int = 100, employee_id: int | None = None) -> list[dict[str, Any]]:
        """Latest append-only events, never including HTTP secrets or passwords."""
        def worker(db: sqlite3.Connection) -> list[dict[str, Any]]:
            sql = """SELECT id, occurred_at_ms, action, entity_type, entity_id,
                  employee_id, before_json, after_json FROM audit_events"""
            args: list[Any] = []
            if employee_id is not None:
                sql += " WHERE employee_id=?"
                args.append(employee_id)
            sql += " ORDER BY id DESC LIMIT ?"
            args.append(limit)
            rows = db.execute(sql, args).fetchall()
            return [{**dict(row),
                     "before": json.loads(row["before_json"]) if row["before_json"] else None,
                     "after": json.loads(row["after_json"]) if row["after_json"] else None}
                    for row in rows]
        events = await self._run(worker)
        for event in events:
            del event["before_json"]
            del event["after_json"]
        return events
