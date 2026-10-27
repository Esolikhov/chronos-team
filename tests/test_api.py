"""Tests use an isolated SQLite file and entirely fictional data."""
import asyncio
from contextlib import closing
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.main import build_report, create_app


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / 'test.sqlite3'


@pytest.fixture
async def client(database_path):
    app = create_app(database_path, seed_demo=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost",headers={'X-Chronos-Request':'1'}) as http:
            yield http


async def create_employee(client, name="Алексей Миронов"):
    response = await client.post('/api/employees', json={'full_name':name,'position':'Тестовый аналитик','weekly_target_hours':40})
    assert response.status_code == 201, response.text
    return response.json()['id']


def week_range():
    now = datetime.now(timezone.utc)
    return {'start_ms':int((now-timedelta(days=2)).timestamp()*1000),'end_ms':int((now+timedelta(days=2)).timestamp()*1000),'tz':'Asia/Dushanbe'}


@pytest.mark.asyncio
async def test_add_employee_and_empty_report(client):
    employee_id = await create_employee(client)
    staff = (await client.get('/api/employees')).json()
    assert len(staff) == 1 and staff[0]['id'] == employee_id
    response = await client.get('/api/report', params=week_range())
    assert response.status_code == 200
    report = response.json()
    assert report['summary']['tracked_ms'] == 0
    assert report['summary']['entries_count'] == 0
    assert report['employees'][0]['tracked_ms'] == 0
    assert report['entries'] == []
    assert all(day['tracked_ms'] == 0 for day in report['daily'])


@pytest.mark.asyncio
async def test_start_stop_and_repeat_start_rejected(client):
    employee_id = await create_employee(client)
    payload={'employee_id':employee_id,'description':'Подготовка макета карточки','category':'Дизайн'}
    started = await client.post('/api/timers/start',json=payload)
    assert started.status_code == 201
    assert started.json()['ended_at_ms'] is None
    duplicate = await client.post('/api/timers/start',json=payload)
    assert duplicate.status_code == 409
    assert len((await client.get('/api/report',params=week_range())).json()['entries']) == 1
    stopped = await client.post(f'/api/timers/{employee_id}/stop')
    assert stopped.status_code == 200
    assert stopped.json()['ended_at_ms'] is not None
    repeated = await client.post(f'/api/timers/{employee_id}/stop')
    assert repeated.status_code == 409
    second = await client.post('/api/timers/start',json=payload)
    assert second.status_code == 201
    assert second.json()['id'] != started.json()['id']


@pytest.mark.asyncio
async def test_concurrent_start_is_atomic(client):
    employee_id=await create_employee(client)
    payload={'employee_id':employee_id,'description':'Параллельный запуск таймера','category':'Тестирование'}
    responses=await asyncio.gather(*(client.post('/api/timers/start',json=payload) for _ in range(6)))
    assert [r.status_code for r in responses].count(201) == 1
    assert [r.status_code for r in responses].count(409) == 5
    report = (await client.get('/api/report',params=week_range())).json()
    assert report['summary']['active_timers'] == 1
    assert len(report['entries']) == 1


@pytest.mark.asyncio
async def test_persists_across_restart(database_path):
    app=create_app(database_path,seed_demo=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as http:
            employee_id=await create_employee(http)
            start=await http.post('/api/timers/start',json={'employee_id':employee_id,'description':'Задача до перезапуска','category':'Разработка'})
            assert start.status_code==201
    # New app and fresh DB connections represent process restart.
    app2=create_app(database_path,seed_demo=False)
    async with app2.router.lifespan_context(app2):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app2),base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as http:
            report=(await http.get('/api/report',params=week_range())).json()
            assert report['summary']['active_timers']==1
            assert report['entries'][0]['description']=='Задача до перезапуска'
            assert (await http.post(f'/api/timers/{employee_id}/stop')).status_code==200


def ms(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def test_interval_correctness_and_midnight_split():
    # Two hours crossing midnight in Dushanbe, only 30 minutes inside report.
    start=ms('2026-10-26T23:30:00+05:00')
    end=ms('2026-10-27T01:30:00+05:00')
    boundary=ms('2026-10-27T00:00:00+05:00')
    period_end=ms('2026-10-27T00:30:00+05:00')
    employee={'id':1,'full_name':'София Тестовая','position':'QA','weekly_target_hours':40,'active_entry_id':None,
              'active_description':None,'active_category':None,'active_started_at_ms':None}
    entry={'id':1,'employee_id':1,'description':'Ночной тест','category':'Тестирование','started_at_ms':start,
           'ended_at_ms':end,'full_name':employee['full_name'],'position':employee['position']}
    r=build_report([entry],[employee],boundary,period_end,ZoneInfo('Asia/Dushanbe'),ms('2026-10-28T00:00:00+05:00'))
    assert r['summary']['tracked_ms']==30*60*1000
    assert r['daily']==[{'day':'2026-10-27','tracked_ms':30*60*1000}]
    # Full interval splits between local calendar days, not UTC days.
    r2=build_report([entry],[employee],start,end,ZoneInfo('Asia/Dushanbe'),end)
    assert [d['tracked_ms'] for d in r2['daily']]==[30*60*1000,90*60*1000]
    assert sum(d['tracked_ms'] for d in r2['daily'])==r2['summary']['tracked_ms']


@pytest.mark.asyncio
async def test_empty_future_report_and_filter(client):
    employee_id=await create_employee(client)
    await client.post('/api/timers/start',json={'employee_id':employee_id,'description':'Выполнение задачи','category':'Аналитика'})
    future=datetime.now(timezone.utc)+timedelta(days=20)
    params={'start_ms':int(future.timestamp()*1000),'end_ms':int((future+timedelta(days=1)).timestamp()*1000),
            'tz':'UTC','employee_id':employee_id}
    report=(await client.get('/api/report',params=params)).json()
    assert report['summary']['tracked_ms']==0
    assert not report['entries']
    assert report['summary']['active_timers']==1  # Independently of date-filtered entries.
    assert report['daily'][0]['tracked_ms']==0


@pytest.mark.asyncio
async def test_edit_delete_and_validation(client):
    employee_id=await create_employee(client)
    invalid=await client.post('/api/timers/start',json={'employee_id':employee_id,'description':' ','category':'Дизайн'})
    assert invalid.status_code==422
    invalid_category=await client.post('/api/timers/start',json={'employee_id':employee_id,'description':'Валидная задача','category':'Прочее'})
    assert invalid_category.status_code==422
    nonexistent=await client.post('/api/timers/start',json={'employee_id':987,'description':'Валидная задача','category':'Дизайн'})
    assert nonexistent.status_code==404
    started=await client.post('/api/timers/start',json={'employee_id':employee_id,'description':'Первая задача','category':'Дизайн'})
    entry_id=started.json()['id']
    no_delete=await client.delete(f'/api/entries/{entry_id}')
    assert no_delete.status_code==409
    edited=await client.put(f'/api/entries/{entry_id}',json={'description':'Доработка дизайна','category':'Аналитика'})
    assert edited.status_code==200 and edited.json()['description']=='Доработка дизайна'
    await client.post(f'/api/timers/{employee_id}/stop')
    assert (await client.delete(f'/api/entries/{entry_id}')).status_code==204
    assert (await client.get('/api/report',params=week_range())).json()['entries']==[]


@pytest.mark.asyncio
async def test_bad_interval_timezone_and_missing_employee(client):
    bad=await client.get('/api/report',params={'start_ms':200,'end_ms':100})
    assert bad.status_code==422
    tz=await client.get('/api/report',params={'start_ms':100,'end_ms':200,'tz':'Bad/Timezone'})
    assert tz.status_code==422
    emp=await client.get('/api/report',params={**week_range(),'employee_id':404})
    assert emp.status_code==404


@pytest.mark.asyncio
async def test_security_response_and_static_ui(client):
    response=await client.get('/')
    assert response.status_code==200
    assert '<title>Chronos' in response.text
    assert 'frame-ancestors' in response.headers['content-security-policy']
    assert response.headers['x-frame-options']=='DENY'
    assert (await client.get('/assets/app.js')).status_code==200
    assert (await client.get('/api/health')).json()=={'status':'ok'}


def test_daylight_saving_split_is_calendar_correct():
    # Europe/Berlin begins DST on 2026-03-29. That local day is 23 hours.
    from app.main import _local_days
    tz = ZoneInfo('Europe/Berlin')
    start = ms('2026-03-29T00:00:00+01:00')
    end = ms('2026-03-30T00:00:00+02:00')
    result = _local_days(start, end, tz)
    assert len(result) == 1
    assert result[0][0] == '2026-03-29'
    assert result[0][2] - result[0][1] == 23 * 3600 * 1000


def test_active_timer_clamped_to_report_cutoff():
    member = {'id': 1, 'full_name': 'Тест Тестов', 'position': 'QA',
              'weekly_target_hours': 40, 'active_entry_id': 1,
              'active_description': 'Задача', 'active_category': 'Аналитика',
              'active_started_at_ms': 500}
    task = {'id': 1, 'employee_id': 1, 'description': 'Задача',
            'category': 'Аналитика', 'started_at_ms': 500, 'ended_at_ms': None}
    report = build_report([task], [member], 1000, 5000, ZoneInfo('UTC'), 4000)
    assert report['summary']['tracked_ms'] == 3000
    assert report['summary']['focus_ms'] == 3000
    assert report['summary']['active_timers'] == 1
    assert report['employees'][0]['entries_count'] == 1


@pytest.mark.asyncio
async def test_employee_name_is_not_interpreted_as_markup(client):
    # An API is JSON; this checks text is stored as text rather than treated as HTML.
    name = '<script>alert(1)</script> Иванов'
    response = await client.post('/api/employees', json={
        'full_name': name, 'position': 'Сотрудник отдела', 'weekly_target_hours': 40})
    assert response.status_code == 201
    data = (await client.get('/api/employees')).json()
    assert data[0]['full_name'] == name
    assert (await client.get('/')).headers['content-security-policy'].startswith("default-src 'self'")

@pytest.mark.asyncio
async def test_update_employee_and_preserve_work_history(client):
    employee_id = await create_employee(client)
    started = await client.post('/api/timers/start', json={
        'employee_id': employee_id, 'description': 'Подготовка отчёта', 'category': 'Аналитика'})
    assert started.status_code == 201
    changed = await client.put(f'/api/employees/{employee_id}', json={
        'full_name': 'Елена Тестовая', 'position': 'Старший аналитик',
        'weekly_target_hours': 35})
    assert changed.status_code == 200
    assert changed.json()['weekly_target_hours'] == 35
    report = (await client.get('/api/report', params=week_range())).json()
    assert report['employees'][0]['full_name'] == 'Елена Тестовая'
    assert report['entries'][0]['full_name'] == 'Елена Тестовая'
    assert report['summary']['active_timers'] == 1
    bad = await client.put('/api/employees/99999', json={
        'full_name': 'Елена Тестовая', 'position': 'Старший аналитик',
        'weekly_target_hours': 35})
    assert bad.status_code == 404
    invalid = await client.put(f'/api/employees/{employee_id}', json={
        'full_name': 'Елена Тестовая', 'position': 'Аналитик',
        'weekly_target_hours': 99})
    assert invalid.status_code == 422
    assert (await client.get('/api/employees')).json()[0]['weekly_target_hours'] == 35


@pytest.mark.asyncio
async def test_concurrent_first_start_seeds_once(database_path):
    from app.storage import Store
    # Three app instances sharing the same initial empty database.
    stores = [Store(database_path) for _ in range(3)]
    await asyncio.gather(*(store.init(seed_demo=True) for store in stores))
    assert len(await stores[0].employees()) == 6
    await stores[0].init(seed_demo=True)
    assert len(await stores[1].employees()) == 6


@pytest.mark.asyncio
async def test_report_snapshot_consistent_during_stop(client):
    employee_id = await create_employee(client)
    await client.post('/api/timers/start', json={
        'employee_id': employee_id, 'description': 'Проверка конкурентности',
        'category': 'Тестирование'})
    reports, stopped = await asyncio.gather(
        asyncio.gather(*(client.get('/api/report', params=week_range()) for _ in range(8))),
        client.post(f'/api/timers/{employee_id}/stop'),
    )
    assert stopped.status_code == 200
    for response in reports:
        assert response.status_code == 200
        value = response.json()
        assert len(value['entries']) == 1
        entry = value['entries'][0]
        assert value['summary']['active_timers'] == int(entry['ended_at_ms'] is None)
        assert value['employees'][0]['active_entry_id'] == (entry['id'] if entry['ended_at_ms'] is None else None)


@pytest.mark.asyncio
async def test_reject_extreme_timestamps_and_untrusted_host(client):
    assert (await client.get('/api/report', params={
        'start_ms': 0, 'end_ms': 999999999999999999999999999})).status_code == 422
    response = await client.get('/api/health', headers={'host':'attacker.example'})
    assert response.status_code == 400
    assert (await client.get('/api/health')).status_code == 200


def test_completed_entry_is_not_counted_beyond_snapshot_time():
    member = {'id': 1, 'full_name': 'Тестовый Пользователь', 'position': 'QA',
              'weekly_target_hours': 40, 'active_entry_id': None,
              'active_description': None, 'active_category': None,
              'active_started_at_ms': None}
    task = {'id': 1, 'employee_id': 1, 'description': 'Раннее завершение',
            'category': 'Тестирование', 'started_at_ms': 500,
            'ended_at_ms': 5000}
    report = build_report([task], [member], 0, 7000, ZoneInfo('UTC'), 3000)
    assert report['summary']['tracked_ms'] == 2500

@pytest.mark.asyncio
async def test_offline_documentation_and_openapi(client):
    docs = await client.get('/api/docs')
    assert docs.status_code == 200
    assert 'Chronos Team API' in docs.text
    assert 'cdn.jsdelivr.net' not in docs.text
    assert (await client.get('/assets/docs.css')).status_code == 200
    schema = await client.get('/api/openapi.json')
    assert schema.status_code == 200
    assert '/api/employees/{employee_id}' in schema.json()['paths']

@pytest.mark.asyncio
async def test_health_probes_storage_failure(database_path):
    app = create_app(database_path, seed_demo=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url='http://localhost',headers={'X-Chronos-Request':'1'}) as http:
            assert (await http.get('/api/health')).status_code == 200
            # Simulate storage failure after application initialization.
            import sqlite3
            database_path.unlink()
            with closing(sqlite3.connect(database_path)) as db:
                db.execute('CREATE TABLE irrelevant (id INTEGER)')
            response = await http.get('/api/health')
            assert response.status_code == 503
