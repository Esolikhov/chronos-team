"""Regression tests for integrity, auditability and the local security perimeter."""
import asyncio
from contextlib import closing
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.main import create_app
from scripts.backup import make_backup
from tests.test_api import create_employee, week_range, client, database_path


@pytest.mark.asyncio
async def test_csrf_cross_site_origin_and_fetch_metadata(client):
    employee_id = await create_employee(client)
    payload = {'employee_id': employee_id, 'description': 'Тест защиты данных', 'category': 'Тестирование'}
    missing_header = await client.post('/api/timers/start', json=payload, headers={'X-Chronos-Request': ''})
    assert missing_header.status_code == 403
    other_origin = await client.post('/api/timers/start', json=payload,
                                     headers={'Origin': 'https://attacker.example'})
    assert other_origin.status_code == 403
    form = await client.post('/api/timers/start', json=payload,
                             headers={'Sec-Fetch-Site': 'cross-site'})
    assert form.status_code == 403
    same_site_different_origin = await client.post('/api/timers/start', json=payload,
                                                   headers={'Origin': 'http://localhost:7777'})
    assert same_site_different_origin.status_code == 403
    malicious_referer = await client.post('/api/timers/start', json=payload,
                                         headers={'Referer': 'https://attacker.example/attack'})
    assert malicious_referer.status_code == 403
    good = await client.post('/api/timers/start', json=payload,
                             headers={'Origin': 'http://localhost', 'Sec-Fetch-Site': 'same-origin'})
    assert good.status_code == 201
    # No mutation was made by any rejected cross-site request.
    report = (await client.get('/api/report', params=week_range())).json()
    assert len(report['entries']) == 1


@pytest.mark.asyncio
async def test_chunked_body_without_content_length_is_bounded(client):
    async def chunks():
        for _ in range(20):
            yield b'a' * 1024
    res = await client.post('/api/employees', content=chunks(),
                            headers={'Content-Type': 'application/json'})
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_json_content_type_and_body_size(client):
    bad = await client.post('/api/employees', content=b'full_name=x',
                            headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert bad.status_code == 415
    large = await client.post('/api/employees', json={
        'full_name': 'Алексей Миронов', 'position': 'X' * 17_000, 'weekly_target_hours': 40})
    assert large.status_code == 413
    good = await client.post('/api/employees', json={
        'full_name': 'Алексей Миронов', 'position': 'Аналитик', 'weekly_target_hours': 40})
    assert good.status_code == 201
    assert good.headers['x-content-type-options'] == 'nosniff'
    assert good.headers['cross-origin-resource-policy'] == 'same-origin'
    assert len(good.headers['x-request-id']) == 32


@pytest.mark.asyncio
async def test_audit_is_atomic_complete_and_append_only(client, database_path):
    employee_id = await create_employee(client)
    changed = await client.put(f'/api/employees/{employee_id}', json={
        'full_name': 'Алексей Петров', 'position': 'Аналитик', 'weekly_target_hours': 38})
    assert changed.status_code == 200
    payload = {'employee_id': employee_id, 'description': 'Написание отчёта', 'category': 'Аналитика'}
    started = (await client.post('/api/timers/start', json=payload)).json()
    repeated = await client.post('/api/timers/start', json=payload)
    assert repeated.status_code == 409
    changed = await client.put(f'/api/entries/{started["id"]}', json={
        'description': 'Подготовка отчёта', 'category': 'Разработка'})
    assert changed.status_code == 200
    assert (await client.post(f'/api/timers/{employee_id}/stop')).status_code == 200
    assert (await client.delete(f'/api/entries/{started["id"]}')).status_code == 204
    audit = (await client.get('/api/audit?limit=100')).json()
    assert [e['action'] for e in audit] == [
        'entry.deleted', 'timer.stopped', 'entry.updated',
        'timer.started', 'employee.updated', 'employee.created']
    assert audit[0]['before']['description'] == 'Подготовка отчёта'
    assert audit[0]['after'] is None
    assert audit[2]['before']['description'] == 'Написание отчёта'
    assert audit[2]['after']['description'] == 'Подготовка отчёта'
    assert 'before_json' not in audit[0]
    assert len((await client.get(f'/api/audit?employee_id={employee_id}&limit=3')).json()) == 3
    assert (await client.get('/api/audit?limit=1000')).status_code == 422
    with closing(sqlite3.connect(database_path)) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM audit_events')
    # Domain failures were not logged.
    assert len(audit) == 6


@pytest.mark.asyncio
async def test_audit_persists_after_restart(database_path):
    import httpx
    first = create_app(database_path, seed_demo=False)
    async with first.router.lifespan_context(first):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=first), base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as client:
            await create_employee(client)
    second = create_app(database_path, seed_demo=False)
    async with second.router.lifespan_context(second):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=second), base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as client:
            events = (await client.get('/api/audit')).json()
            assert len(events) == 1 and events[0]['action'] == 'employee.created'


@pytest.mark.asyncio
async def test_concurrent_start_has_exactly_one_audit_event(client):
    employee_id = await create_employee(client)
    payload = {'employee_id': employee_id, 'description': 'Параллельный тест аудита', 'category': 'Тестирование'}
    responses = await asyncio.gather(*(client.post('/api/timers/start', json=payload) for _ in range(10)))
    assert [r.status_code for r in responses].count(201) == 1
    assert [r.status_code for r in responses].count(409) == 9
    events = (await client.get('/api/audit')).json()
    assert [e['action'] for e in events].count('timer.started') == 1


@pytest.mark.asyncio
async def test_prohibit_unicode_controls_and_unknown_json_fields(client):
    for name in ('A\u202eevil Б', 'Иван\x00 Иванов', '\ufeff Иванов'):
        answer = await client.post('/api/employees', json={
            'full_name': name, 'position': 'Аналитик', 'weekly_target_hours': 40})
        assert answer.status_code == 422
    unknown = await client.post('/api/employees', json={
        'full_name': 'Анна Иванова', 'position': 'Аналитик',
        'weekly_target_hours': 40, 'is_admin': True})
    assert unknown.status_code == 422


@pytest.mark.asyncio
async def test_report_cutoff_prevents_excessive_result(client, database_path):
    employee_id = await create_employee(client)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    with closing(sqlite3.connect(database_path)) as db:
        db.executemany('''INSERT INTO entries
        (employee_id, description, category, started_at_ms, ended_at_ms)
        VALUES (?, ?, ?, ?, ?)''', (
            (employee_id, 'Массовое тестирование', 'Тестирование', now_ms - (i + 1) * 1000, now_ms - i * 1000)
            for i in range(20_001)
        ))
        db.commit()
    report = await client.get('/api/report', params=week_range())
    assert report.status_code == 413
    assert 'более короткий период' in report.json()['detail']


@pytest.mark.asyncio
async def test_backup_captures_committed_wal_without_overwriting(client, database_path, tmp_path):
    employee_id = await create_employee(client)
    await client.post('/api/timers/start', json={
        'employee_id': employee_id, 'description': 'Резервное копирование', 'category': 'Другое'})
    backup = tmp_path / 'backups' / 'safe.sqlite3'
    assert make_backup(database_path, backup) == backup
    with closing(sqlite3.connect(backup)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT count(*) FROM employees').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM entries WHERE ended_at_ms IS NULL').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM audit_events').fetchone()[0] == 2
    with pytest.raises(FileExistsError):
        make_backup(database_path, backup)
    with pytest.raises(ValueError):
        make_backup(database_path, database_path)
    with pytest.raises(FileNotFoundError):
        make_backup(tmp_path / 'missing.sqlite3', tmp_path / 'empty.sqlite3')


@pytest.mark.asyncio
async def test_existing_1_1_database_migrates_without_data_loss(tmp_path):
    """An old installation without audit_events must retain employees and entries."""
    from app.storage import SCHEMA
    database = tmp_path / 'old.sqlite3'
    legacy_schema = SCHEMA.split('CREATE TABLE IF NOT EXISTS audit_events')[0]
    with closing(sqlite3.connect(database)) as db:
        db.executescript(legacy_schema)
        db.execute('INSERT INTO employees(full_name,position,weekly_target_hours,created_at_ms) VALUES (?,?,?,?)',
                   ('Мария Тестовая', 'Аналитик', 40, 0))
        db.execute('INSERT INTO entries(employee_id,description,category,started_at_ms,ended_at_ms) VALUES (?,?,?,?,?)',
                   (1, 'Тестовая работа', 'Аналитика', 1000, 5000))
        db.commit()
    app = create_app(database, seed_demo=False)
    async with app.router.lifespan_context(app):
        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as http:
            employees = (await http.get('/api/employees')).json()
            assert len(employees) == 1 and employees[0]['full_name'] == 'Мария Тестовая'
            report = (await http.get('/api/report', params={
                'start_ms': 0, 'end_ms': 10000, 'tz': 'UTC'})).json()
            assert report['summary']['tracked_ms'] == 4000
            assert (await http.get('/api/audit')).json() == []
            await create_employee(http, name='Игорь Селиванов')
            assert len((await http.get('/api/audit')).json()) == 1
