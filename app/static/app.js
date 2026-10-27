/* Chronos Team — no build step, no third-party browser scripts.
   All user-controlled content is escaped before interpolation into HTML. */
const $ = (selector, root = document) => root.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const icons = {
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  chart:'<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-7"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  arrowUp:'<path d="m7 14 5-5 5 5M12 9v11"/>',
  chevron:'<path d="m9 18 6-6-6-6"/>',
  down:'<path d="m6 9 6 6 6-6"/>',
  search:'<circle cx="10.8" cy="10.8" r="7"/><path d="m16 16 5 5"/>',
  play:'<path d="m8 5 12 7-12 7z"/>',
  pause:'<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>',
  check:'<path d="m4 12 5 5L20 6"/>',
  bolt:'<path d="m13 2-9 12h7l-1 8 10-12h-7z"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  settings:'<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="m19 13 2-1-2-1-.5-2 1-2-2-2-2 1-2-.5-1-2-1 2-2 .5-2-1-2 2 1 2-.5 2-2 1 2 1 .5 2-1 2 2 2 2-1 2 .5 1 2 1-2 2-.5 2 1 2-2-1-2z"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
  edit:'<path d="M12 20h9M16 4a2 2 0 0 1 4 4L9 19l-5 1 1-5Z"/>',
  trash:'<path d="M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3"/>',
  close:'<path d="M18 6 6 18M6 6l12 12"/>',
  logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4m7 14 5-5-5-5M21 12H9"/>',
  spark:'<path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7zM19 17l.7 1.3L21 19l-1.3.7L19 21l-.7-1.3L17 19l1.3-.7z"/>',
  info:'<circle cx="12" cy="12" r="10"/><path d="M12 11v6m0-10h.01"/>',
  coffee:'<path d="M4 8h13v7a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8Zm13 1h2a3 3 0 0 1 0 6h-2M3 4h16"/>',
  menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',
  external:'<path d="M14 3h7v7m0-7-9 9M19 13v7H4V5h7"/>',
  list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
};
const icon = (name, size = 20) => `<svg aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${icons[name] ?? icons.clock}</svg>`;
const categories = ['Разработка','Тестирование','Дизайн','Аналитика','Встречи','Другое'];
const names = {dashboard:'Обзор',team:'Сотрудники',reports:'Отчёты',audit:'Журнал изменений',about:'О проекте'};
const state = {
  page:'dashboard', range:'last7', customFrom:'', customTo:'', search:'',
  reportEmployee:'', report:null, filteredReport:null, modal:null,
  refreshing:false, busy:false, audit:[], timezone:Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', clockDelta:0,
};

const dateISO = value => `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`;
const localDay = iso => new Date(`${iso}T00:00:00`);
const daysForward = (d, n) => {const x = new Date(d); x.setDate(x.getDate()+n); return x;};
function getPeriod() {
  const today = localDay(dateISO(new Date()));
  let start = today, end = daysForward(today, 1);
  if (state.range === 'last7') start = daysForward(today, -6);
  if (state.range === 'week') {start = daysForward(today, -(today.getDay()+6)%7); end = daysForward(start,7);}
  if (state.range === 'month') {start = new Date(today.getFullYear(), today.getMonth(), 1); end = new Date(today.getFullYear(),today.getMonth()+1,1);}
  if (state.range === 'custom') {
    start = localDay(state.customFrom || dateISO(daysForward(today,-6)));
    end = daysForward(localDay(state.customTo || dateISO(today)),1);
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end <= start || end - start > 370*86400000) {
      throw new Error('Выберите период не более 370 дней; конец должен быть не раньше начала.');
    }
  }
  return {startMs:start.getTime(), endMs:end.getTime(), startDate:dateISO(start),endDate:dateISO(daysForward(end,-1))};
}
const msHours = ms => (ms / 3600000).toLocaleString('ru-RU',{maximumFractionDigits:1});
function duration(ms, short=false) {
  const minutes = Math.floor(Math.max(0,ms)/60000);
  if (!minutes) return short ? '0 мин' : '< 1 мин';
  const hrs=Math.floor(minutes/60), rest=minutes%60;
  return hrs ? `${hrs} ч${rest ? ` ${rest} мин` : ''}` : `${rest} мин`;
}
const digital = ms => { const t = Math.floor(Math.max(0,ms)/1000); return [Math.floor(t/3600),Math.floor(t/60)%60,t%60].map(n=>String(n).padStart(2,'0')).join(':'); };
const dayTime = ms => new Date(ms).toLocaleString('ru-RU',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
const clockTime = ms => new Date(ms).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
const avatar = (person, size='normal') => {
  const n=String(person.full_name??'').trim().split(/\s+/);
  const letters=(n[0]?.[0]||'С')+(n[1]?.[0]||'');
  return `<span class="avatar avatar--${Number(person.id)%6} ${size==='small'?'avatar--small':''}" aria-hidden="true">${esc(letters.toUpperCase())}</span>`;
};
const percent = (a,b) => b>0?Math.round((a/b)*100):0;
const weekdays = (startDate,endDate) => {
  let count=0;
  for(let day=localDay(startDate),end=localDay(endDate);day<=end;day=daysForward(day,1)) if(day.getDay()%6!==0) count++;
  return count;
};
function targetMs(employee){const {startDate,endDate}=getPeriod();return weekdays(startDate,endDate)*employee.weekly_target_hours/5*3600000;}
function workload(employee){return percent(employee.tracked_ms,targetMs(employee));}
const choosePeriod = () => `<div class="date-controls">
  <div class="date-select">${icon('calendar',17)}<select id="period-select" aria-label="Выберите период">
  <option value="today" ${state.range==='today'?'selected':''}>Сегодня</option>
  <option value="last7" ${state.range==='last7'?'selected':''}>Последние 7 дней</option>
  <option value="week" ${state.range==='week'?'selected':''}>Эта неделя</option>
  <option value="month" ${state.range==='month'?'selected':''}>Этот месяц</option>
  <option value="custom" ${state.range==='custom'?'selected':''}>Свой период</option></select>${icon('down',15)}</div>
  ${state.range==='custom'?`<div class="custom-dates"><input aria-label="Начало периода" type="date" id="range-from" value="${esc(state.customFrom||getTodayOffset(-6))}"><span>—</span><input aria-label="Конец периода" type="date" id="range-to" value="${esc(state.customTo||getTodayOffset(0))}"><button class="btn btn--primary date-apply" data-action="apply-range" type="button">Применить</button></div>`:''}
  </div>`;
const getTodayOffset = n => dateISO(daysForward(new Date(),n));

async function api(path, opts={}) {
  const response = await fetch(path, { ...opts, headers:{'Accept':'application/json','X-Chronos-Request':'1',...(opts.body?{'Content-Type':'application/json'}:{}),...(opts.headers||{})}, cache:'no-store' });
  if(!response.ok) {
    let result={};try{result=await response.json();}catch{}
    const detail=Array.isArray(result.detail)?result.detail.map(e=>e.msg).join('; '):(result.detail||`HTTP ${response.status}`);
    throw new Error(detail);
  }
  if(response.status===204)return null;
  return response.json();
}
async function fetchReport(employee='') {
  const {startMs,endMs}=getPeriod();
  const qs=new URLSearchParams({start_ms:String(startMs),end_ms:String(endMs),tz:state.timezone});
  if(employee) qs.set('employee_id',String(employee));
  return api(`/api/report?${qs}`);
}
let requestId = 0;
async function reload() {
  const id=++requestId;
  state.refreshing=true;
  try {
    const [report,filtered,audit]=await Promise.all([
      fetchReport(),
      state.reportEmployee?fetchReport(state.reportEmployee):Promise.resolve(null),
      state.page==='audit'?api('/api/audit?limit=100'):Promise.resolve(null),
    ]);
    if(id!==requestId) return;
    state.report=report; state.filteredReport=filtered;
    if(audit)state.audit=audit;
    state.clockDelta=report.now_ms-Date.now();
    render();
  } catch(error) { if(id===requestId) {toast(error.message,'error');if(!state.report)renderError(error.message);} }
  finally {if(id===requestId)state.refreshing=false;}
}
function toast(message,kind='success') {
  const el=document.createElement('div');el.className=`toast toast--${kind}`;
  el.innerHTML=`${icon(kind==='success'?'check':'info',18)}<span>${esc(message)}</span>`;
  $('#toast-root').append(el);setTimeout(()=>el.remove(),4200);
}
function renderError(message){$('#app').innerHTML=`<div class="error-screen"><div class="error-illustration">${icon('info',32)}</div><h1>Не удалось получить данные</h1><p>${esc(message)}</p><button class="btn btn--primary" data-action="retry">Повторить попытку</button></div>`;}
function navLink(page,ico){return `<button type="button" class="nav-link ${state.page===page?'nav-link--active':''}" data-action="nav" data-page="${page}" aria-current="${state.page===page?'page':'false'}">${icon(ico,19)}<span>${names[page]}</span>${state.page===page?'<span class="nav-mark"></span>':''}</button>`;}
function shell(main) {
  const report=state.report;
  return `<div class="shell">
  <aside class="rail" aria-label="Быстрый доступ">
    <div class="rail-logo" title="Chronos Team">${icon('clock',29)}</div>
    <div class="rail-icons">
      <button class="rail-item ${state.page==='dashboard'?'is-active':''}" title="Обзор" data-action="nav" data-page="dashboard">${icon('grid',21)}</button>
      <button class="rail-item ${state.page==='team'?'is-active':''}" title="Команда" data-action="nav" data-page="team">${icon('users',21)}</button>
      <button class="rail-item ${state.page==='reports'?'is-active':''}" title="Отчёты" aria-label="Отчёты" data-action="nav" data-page="reports">${icon('chart',21)}</button>
      <div class="rail-divider"></div><button class="rail-item" title="Новый таймер" data-action="start">${icon('plus',21)}</button>
    </div>
    <div class="rail-bottom"><button class="rail-item ${state.page==='about'?'is-active':''}" title="Информация" data-action="nav" data-page="about">${icon('info',20)}</button><div class="avatar avatar--5 avatar--small" title="Демо-режим">DE</div></div>
  </aside>
  <aside class="side">
    <div class="brand"><div class="brand-symbol">C<span>·</span></div><div><strong>chronos<span class="brand-period">.</span></strong><small>TEAM WORKSPACE</small></div></div>
    <div class="workspace-switch"><div class="ws-icon">${icon('grid',19)}</div><div><strong>Рабочее пространство</strong><small>Демонстрационная компания</small></div>${icon('down',14)}</div>
    <div class="side-label">РАБОЧАЯ ПАНЕЛЬ</div>
    <nav class="side-nav" aria-label="Основная навигация">${navLink('dashboard','grid')}${navLink('team','users')}${navLink('reports','chart')}${navLink('audit','list')}</nav>
    <div class="side-label side-label--second">ДОПОЛНИТЕЛЬНО</div>
    <nav class="side-nav" aria-label="Дополнительное меню">${navLink('about','info')}</nav>
    <div class="side-spacer"></div>
    <div class="sidebar-note"><div class="sidebar-note-icon">${icon('spark',20)}</div><strong>Время работать умнее</strong><p>Прозрачный учёт задач и времени вашей команды.</p><button data-action="nav" data-page="about">О платформе ${icon('arrow',14)}</button></div>
    <div class="side-footer">${icon('shield',15)}<span>Данные хранятся локально</span></div>
  </aside>
  <div class="workspace"><header class="topbar"><div class="crumbs"><span>Пространство</span>${icon('chevron',14)}<strong>${names[state.page]}</strong></div><div class="top-actions"><span class="top-today">${new Date().toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'})}</span><span class="top-separator"></span><span class="security-tag">${icon('shield',14)} Безопасное локальное хранение</span><span class="profile-bubble">DE</span></div></header>
  <main class="content" id="main-content">${main}</main></div>
  </div>`;
}
function header(title,subtitle,actions='') {return `<div class="page-heading"><div><div class="eyebrow"><span></span> TEAM ANALYTICS / 2026</div><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-actions">${choosePeriod()}${actions}</div></div>`;}
function miniStat(ico,color,label,value,extra) {return `<div class="metric-card"><div class="metric-heading"><span>${esc(label)}</span><span class="metric-icon metric-icon--${color}">${icon(ico,20)}</span></div><div class="metric-value">${value}</div><div class="metric-extra">${extra}</div></div>`;}
function dayChart(data,label='Рабочее время, ч') {
  const values=data.map(d=>d.tracked_ms/3600000);
  const max=Math.max(1,...values)*1.23;
  const width=760,height=232,left=36,right=16,top=15,bottom=40;
  const plotHeight=height-bottom-top;
  const x=i=>left+(values.length===1?0:i*(width-left-right)/(values.length-1));
  const y=v=>top+plotHeight-(v/max*plotHeight);
  const ticks=[0,.25,.5,.75,1].map(n=>`<g><line x1="${left}" x2="${width-right}" y1="${y(max*n)}" y2="${y(max*n)}" stroke="#e8edf6" stroke-dasharray="4 5"/><text x="${left-10}" y="${y(max*n)+4}" text-anchor="end" font-size="11" fill="#98a4b7">${(max*n).toFixed(n===0?0:1)}</text></g>`).join('');
  if(!values.length || !values.some(v=>v>0)) return `<div class="chart-empty">${icon('chart',36)}<strong>Пока нет данных</strong><span>Запустите таймер — и здесь появится статистика.</span></div>`;
  const points=values.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area=`${x(0)},${y(0)} ${points} ${x(values.length-1)},${y(0)}`;
  const labelStep=Math.max(1,Math.ceil(values.length/10));
  const labels=data.map((d,i)=>(i%labelStep===0||i===values.length-1)?`<text x="${x(i)}" y="${height-12}" text-anchor="middle" fill="#98a4b7" font-size="11">${new Date(d.day+'T12:00:00').toLocaleDateString('ru-RU',{day:'numeric',month:'short'})}</text>`:'').join('');
  return `<div class="chart-scroll"><svg class="line-chart" role="img" aria-label="${esc(label)}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="area-color" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4b75ed" stop-opacity=".23"/><stop offset="100%" stop-color="#4b75ed" stop-opacity="0"/></linearGradient></defs>${ticks}<polygon points="${area}" fill="url(#area-color)"/><polyline points="${points}" fill="none" stroke="#4169eb" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>${values.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="4.3" fill="#fff" stroke="#4169eb" stroke-width="2.5"><title>${esc(data[i].day)}: ${msHours(data[i].tracked_ms)} ч</title></circle>`).join('')}${labels}</svg></div>`;
}
function employeeRow(e,compact=false) {
  const active=e.active_entry_id!==null;
  const load=workload(e);
  return `<div class="employee-row ${compact?'employee-row--compact':''}">
    <div class="person">${avatar(e)}<div class="person-identity"><strong>${esc(e.full_name)}</strong><span>${esc(e.position)}</span></div></div>
    <div class="employee-status"><span class="status ${active?'status--active':'status--idle'}"><span class="status-dot"></span>${active?'В работе':'Неактивен'}</span></div>
    <div class="employee-hours"><strong>${duration(e.tracked_ms)}</strong><small>за период</small></div>
    <div class="employee-load"><div class="load-top"><span>${load}%</span><small>от нормы</small></div><div class="progress"><span class="${load>=100?'progress--full':''}" style="width:${Math.min(100,load)}%"></span></div></div>
    <div class="employee-actions"><button class="icon-button icon-button--details" data-action="profile" data-id="${e.id}" title="Профиль и показатели" aria-label="Профиль: ${esc(e.full_name)}">${icon('info',18)}</button>${active?`<button class="icon-button icon-button--stop" data-action="stop" data-id="${e.id}" title="Остановить таймер" aria-label="Остановить таймер: ${esc(e.full_name)}">${icon('pause',18)}</button>`:`<button class="icon-button icon-button--play" data-action="start" data-id="${e.id}" title="Начать задачу" aria-label="Начать задачу: ${esc(e.full_name)}">${icon('play',18)}</button>`}</div>
  </div>`;
}
function teamTable(list, compact=false) {
  return `<div class="employee-table"><div class="employee-table-head"><span>СОТРУДНИК</span><span>СТАТУС</span><span>УЧТЕНО</span><span>ЗАГРУЗКА</span><span>ДЕЙСТВИЕ</span></div><div class="employee-table-body">${list.length?list.map(e=>employeeRow(e,compact)).join(''):emptyState('Сотрудников пока нет','Добавьте первого сотрудника, чтобы начать учёт.')}</div></div>`;
}
function emptyState(title,desc) {return `<div class="empty-state"><div class="empty-symbol">${icon('coffee',30)}</div><strong>${esc(title)}</strong><p>${esc(desc)}</p></div>`;}
function focusCard(report) {
  const active=report.employees.filter(e=>e.active_entry_id!=null);
  return `<section class="focus-card"><div class="focus-top"><div class="focus-top-left">${icon('bolt',19)}<span>LIVE TIME TRACKING</span></div><span class="focus-live"><span></span> В ПРЯМОМ ЭФИРЕ</span></div>
    <div class="focus-title">Время под контролем<span class="focus-dot">.</span></div><p>Каждая минута имеет значение. Фиксируйте работу без лишних действий.</p>
    ${active.length?`<div class="running-label"><span class="pulse-dot"></span> Активные таймеры · ${active.length}</div><div class="running-list">${active.slice(0,3).map(e=>`<div class="running-item">${avatar(e,'small')}<div class="running-info"><strong>${esc(e.full_name)}</strong><small>${esc(e.active_description)}</small></div><span class="running-timer" data-live-id="${e.id}" data-start="${e.active_started_at_ms}">${digital(report.now_ms-e.active_started_at_ms)}</span></div>`).join('')}</div>`:`<div class="focus-time"><span class="focus-time-icon">${icon('clock',31)}</span><strong>00:00:00</strong><small>Готовы к продуктивному дню?</small></div>`}
    <button class="focus-button" data-action="start">${icon('play',18)} Запустить таймер ${icon('arrow',18)}</button>
    <div class="focus-bottom">${icon('shield',14)} Состояние таймера сохраняется в базе данных</div></section>`;
}
function activityCard(report) {
  const entries=report.entries.slice(0,5);
  return `<section class="panel activity-panel"><div class="panel-top"><div><span class="panel-caption">ACTIVITY FEED</span><h2>Последние события</h2></div><span class="clock-pill">${icon('clock',15)} Live</span></div>
  <div class="activity-list">${entries.length?entries.map(e=>`<div class="activity-item"><span class="activity-avatar">${avatar({full_name:e.full_name,id:e.employee_id},'small')}</span><div><strong>${esc(e.full_name)}</strong><p>${esc(e.description)}</p><span>${dayTime(e.started_at_ms)}</span></div><span class="activity-duration">${duration(e.overlap_ms)}</span></div>`).join(''):emptyState('Нет событий','Задачи появятся после первого запуска таймера.')}</div>
  <button class="activity-link" data-action="nav" data-page="reports">Вся история ${icon('arrow',16)}</button></section>`;
}
function dashboard(report) {
  const s=report.summary,focus=percent(s.focus_ms,s.tracked_ms),avg=s.employees?s.tracked_ms/s.employees:0;
  return `${header('Рабочее время','Управляйте временем команды. Находите баланс между задачами и результатом.',`<button class="btn btn--primary" data-action="add">${icon('plus',18)} Сотрудник</button>`)}
  <div class="dashboard-layout"><div class="dashboard-main">
    <div class="welcome-banner"><div class="welcome-orb"></div><div class="welcome-content"><div class="welcome-kicker">${icon('spark',17)} ЕДИНАЯ СИСТЕМА УЧЁТА ВРЕМЕНИ</div><h2>Команда в ритме результата<span>.</span></h2><p>Все рабочие часы, задачи и активность — в одном красивом пространстве.</p><button data-action="nav" data-page="reports">Смотреть аналитику ${icon('arrow',16)}</button></div><div class="welcome-art">${icon('clock',118)}</div></div>
    <div class="metrics-grid">
      ${miniStat('clock','blue','Учтено времени',`${msHours(s.tracked_ms)} <small>ч</small>`,`${icon('check',14)} За выбранный период`)}
      ${miniStat('users','violet','Сотрудников',s.employees,`${icon('users',14)} В рабочей группе`)}
      ${miniStat('bolt','green','Сейчас работают',s.active_timers,`${icon('bolt',14)} Активных таймеров`)}
      ${miniStat('target','orange','Доля профильных задач',`${focus}<small>%</small>`,`${icon('info',14)} Без совещаний и прочего`)}
    </div>
    <section class="panel chart-panel"><div class="panel-top"><div><span class="panel-caption">PERFORMANCE OVERVIEW</span><h2>Динамика рабочего времени</h2></div><span class="chart-tag">${icon('chart',16)} ${msHours(avg)} ч / сотрудник</span></div>${dayChart(report.daily)}<div class="chart-foot"><span><i></i> Зафиксированное время</span><span>Часовой пояс: ${esc(state.timezone)}</span></div></section>
    <section class="panel team-panel"><div class="panel-top"><div><span class="panel-caption">TEAM DIRECTORY</span><h2>Ваша команда <em>${s.employees}</em></h2></div><button class="subtle-link" data-action="nav" data-page="team">Все сотрудники ${icon('arrow',16)}</button></div>${teamTable(report.employees.slice(0,5),true)}</section>
  </div><aside class="dashboard-right">${focusCard(report)}${activityCard(report)}<div class="hint-card">${icon('info',19)}<div><strong>Как считается загрузка?</strong><p>Учтённые часы / плановые часы по рабочим дням. Это не оценка качества работы.</p></div></div></aside></div>`;
}
function teamPage(report) {
  const members=report.employees.filter(e=>(`${e.full_name} ${e.position}`).toLowerCase().includes(state.search.toLowerCase()));
  const active=report.employees.filter(e=>e.active_entry_id!=null).length;
  return `${header('Сотрудники','Управление командой, рабочими задачами и персональной нагрузкой.',`<button class="btn btn--primary" data-action="add">${icon('plus',18)} Добавить сотрудника</button>`)}
  <div class="team-hero"><div class="team-hero-icon">${icon('users',28)}</div><div><strong>Пространство вашей команды</strong><p>Всего ${report.employees.length} сотрудников · ${active} сейчас ведут учёт времени</p></div><div class="team-avatar-stack">${report.employees.slice(0,5).map(e=>avatar(e,'small')).join('')}</div></div>
  <section class="panel full-panel"><div class="panel-top"><div><span class="panel-caption">PEOPLE & WORKLOAD</span><h2>Список сотрудников</h2></div><label class="search-field">${icon('search',18)}<input id="team-search" placeholder="Найти сотрудника…" autocomplete="off" value="${esc(state.search)}"></label></div>${teamTable(members)}</section>
  <p class="footnote">Нажмите ${icon('info',13)} в строке сотрудника, чтобы увидеть персональные показатели и изменить его профиль. Нагрузка — это доля учтённого времени от плана (${weekdays(getPeriod().startDate,getPeriod().endDate)} рабочих дней), а не оценка эффективности труда.</p>`;
}
function badgeCategory(category) {const index=Math.max(0,categories.indexOf(category));return `<span class="category category--${index}"><i></i>${esc(category)}</span>`;}
function reportPage(report) {
  const entries=report.entries, summary=report.summary;
  const selected=state.reportEmployee;
  const members=state.report.employees;
  const topEmployees=[...report.employees].sort((a,b)=>b.tracked_ms-a.tracked_ms);
  return `${header('Отчёты и аналитика','Прозрачная история трудозатрат с фильтрами, метриками и экспортом.',`<button class="btn btn--outline" data-action="export">${icon('download',17)} Экспорт CSV</button>`)}
  <div class="report-filterbar"><div><span class="panel-caption">ОТЧЁТ ПО ПЕРИОДУ</span><strong>${new Date(report.start_ms).toLocaleDateString('ru-RU',{day:'numeric',month:'long'})} — ${new Date(report.end_ms-1).toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'})}</strong></div><label class="filter-select">${icon('users',17)}<select id="report-employee" aria-label="Фильтр сотрудника"><option value="">Все сотрудники</option>${members.map(e=>`<option value="${e.id}" ${String(e.id)===String(selected)?'selected':''}>${esc(e.full_name)}</option>`).join('')}</select>${icon('down',15)}</label></div>
  <div class="report-stats">
    ${miniStat('clock','blue','Всего часов',`${msHours(summary.tracked_ms)} <small>ч</small>`,`${icon('list',14)} ${summary.entries_count} записей`)}
    ${miniStat('users','violet','Сотрудников',report.employees.length,`${icon('users',14)} В текущей выборке`)}
    ${miniStat('target','green','Доля профильных задач',`${percent(summary.focus_ms,summary.tracked_ms)}<small>%</small>`,`${icon('info',14)} Без совещаний и прочего`)}
    ${miniStat('bolt','orange','Активные таймеры',summary.active_timers,`${icon('clock',14)} На момент запроса`)}
  </div>
  <div class="report-chart-grid"><section class="panel chart-panel"><div class="panel-top"><div><span class="panel-caption">TIME DISTRIBUTION</span><h2>Время по дням</h2></div><span class="chart-tag">${icon('chart',16)} ${msHours(summary.tracked_ms)} часов</span></div>${dayChart(report.daily)}<div class="chart-foot"><span><i></i> Время, попавшее в период</span><span>${esc(state.timezone)}</span></div></section>
  <section class="panel ranking-panel"><div class="panel-top"><div><span class="panel-caption">TEAM WORKLOAD</span><h2>Учтённое время команды</h2></div></div><div class="rank-list">${topEmployees.length?topEmployees.map(e=>`<div class="rank-row"><div>${avatar(e,'small')}<span title="${esc(e.full_name)}">${esc(e.full_name)}</span><strong>${msHours(e.tracked_ms)} ч</strong></div><div class="rank-progress"><span style="width:${Math.min(100,workload(e))}%"></span></div><small>${workload(e)}% от плана</small></div>`).join(''):emptyState('Нет сотрудников','Для отчёта добавьте сотрудника.')}</div></section></div>
  <section class="panel records-panel"><div class="panel-top"><div><span class="panel-caption">WORK LOG</span><h2>Журнал записей <em>${entries.length}</em></h2></div><button class="subtle-link" data-action="export">${icon('download',16)} Скачать CSV</button></div>
  ${entries.length?`<div class="records-scroll"><table class="records-table"><thead><tr><th>Сотрудник / задача</th><th>Категория</th><th>Начало</th><th>Окончание</th><th>Время в периоде</th><th>Действия</th></tr></thead><tbody>${entries.map(e=>`<tr><td><div class="record-person">${avatar({id:e.employee_id,full_name:e.full_name},'small')}<div><strong>${esc(e.full_name)}</strong><span title="${esc(e.description)}">${esc(e.description)}</span></div></div></td><td>${badgeCategory(e.category)}</td><td>${dayTime(e.started_at_ms)}</td><td>${e.ended_at_ms===null?'<span class="status status--active"><span class="status-dot"></span>Идёт</span>':dayTime(e.ended_at_ms)}</td><td class="time-cell">${duration(e.overlap_ms)}</td><td><div class="record-actions"><button aria-label="Изменить запись" title="Изменить запись" class="table-icon" data-action="edit" data-id="${e.id}">${icon('edit',16)}</button><button aria-label="Удалить запись" title="Удалить остановленную запись" class="table-icon table-icon--danger" data-action="delete" data-id="${e.id}" ${e.ended_at_ms===null?'disabled':''}>${icon('trash',16)}</button></div></td></tr>`).join('')}</tbody></table></div>`:emptyState('Пустой отчёт','За выбранный период записей нет. Измените даты или запустите таймер.')}
  </section><p class="footnote">Отчёт учитывает пересечение интервалов с выбранным периодом и использует часовой пояс браузера. Активные таймеры считаются до времени формирования отчёта. Загрузка — ориентир занятости, а не оценка производительности.</p>`;
}
const auditNames = {
  'employee.created':'Сотрудник добавлен', 'employee.updated':'Профиль сотрудника изменён',
  'timer.started':'Таймер запущен', 'timer.stopped':'Таймер остановлен',
  'entry.updated':'Запись изменена', 'entry.deleted':'Запись удалена',
};
function auditPage(){
  const items=state.audit||[];
  const employeeNames=new Map((state.report?.employees||[]).map(p=>[p.id,p.full_name]));
  return `${header('История изменений','Отдельный журнал изменений, сохраняемый вместе с данными в SQLite.')}
  <section class="panel records-panel"><div class="panel-top"><div><span class="panel-caption">AUDIT TRAIL</span><h2>Последние 100 событий</h2></div><button class="btn btn--outline" data-action="refresh-audit">${icon('clock',16)} Обновить</button></div>
  ${items.length?`<div class="records-scroll"><table class="records-table"><thead><tr><th>Когда</th><th>Действие</th><th>Сотрудник</th><th>Объект</th></tr></thead><tbody>${items.map(a=>`<tr><td>${dayTime(a.occurred_at_ms)}</td><td><strong>${esc(auditNames[a.action]||a.action)}</strong></td><td>${esc(employeeNames.get(a.employee_id)||a.after?.full_name||a.before?.full_name||'—')}</td><td>${esc(a.entity_type)} #${Number(a.entity_id)}</td></tr>`).join('')}</tbody></table></div>`:emptyState('История пуста','События появятся после первого добавления сотрудника или запуска таймера.')}</section>
  <p class="footnote">Изменения записываются в одной транзакции с бизнес-операцией. Журнал доступен только локально, не является криптографически неизменяемым и не содержит сведений о личности оператора (авторизации нет). Подробные данные доступны через /api/audit.</p>`;
}
function aboutPage(report) {return `${header('О проекте','Небольшое приложение, которое спроектировано как настоящий продукт.')}<div class="about-grid"><div class="panel about-card"><div class="about-icon">${icon('clock',31)}</div><h2>Chronos Team</h2><p>Минималистичная система учёта рабочего времени с асинхронным Python API, локальным SQLite-хранилищем, надёжными транзакциями и удобной аналитикой.</p><div class="about-tags"><span>Python</span><span>FastAPI</span><span>SQLite</span><span>Vanilla JS</span><span>Async</span></div></div><div class="panel about-card"><div class="about-icon about-icon--green">${icon('shield',31)}</div><h2>Как защищены данные</h2><p>Таймеры сохраняются на сервере и переживают перезапуск. Для каждого сотрудника работает ограничение «не больше одного активного таймера». Пользовательские данные экранируются в интерфейсе.</p><p class="about-warn">Важно: авторизация не предусмотрена по условиям задания. По умолчанию приложение запускается только на localhost. Не публикуйте базу и не открывайте API в Интернет без аутентификации и HTTPS.</p></div><div class="panel about-card"><div class="about-icon about-icon--orange">${icon('target',31)}</div><h2>Про аналитику</h2><p>Учёт времени помогает видеть загрузку команды. «Доля задач» означает время по профильным категориям без встреч и «другого». Количество часов само по себе не измеряет качество, пользу или результат работы.</p></div><div class="panel about-card"><div class="about-icon about-icon--violet">${icon('list',31)}</div><h2>Что можно проверить</h2><p>Добавьте нового сотрудника, запустите ему таймер, обновите страницу, остановите задачу и откройте отчёт. Измените диапазон на будущие даты — получите корректный пустой отчёт.</p><button class="btn btn--primary" data-action="start">${icon('play',17)} Проверить таймер</button></div></div>`;}
function render() {
  if(!state.report) return;
  let output='';
  if(state.page==='dashboard')output=dashboard(state.report);
  if(state.page==='team')output=teamPage(state.report);
  if(state.page==='reports')output=reportPage(state.reportEmployee?state.filteredReport||state.report:state.report);
  if(state.page==='audit')output=auditPage();
  if(state.page==='about')output=aboutPage(state.report);
  $('#app').innerHTML=shell(output);
  renderModal();tick();
}
function employeeOptions(selected='') {return (state.report?.employees??[]).map(e=>`<option value="${e.id}" ${String(e.id)===String(selected)?'selected':''}>${esc(e.full_name)}${e.active_entry_id!=null?' · таймер активен':''}</option>`).join('');}
function categoryOptions(selected='Разработка') {return categories.map(c=>`<option ${selected===c?'selected':''}>${esc(c)}</option>`).join('');}
let modalOpener=null;
function showModal(details){
  if(!state.modal)modalOpener=document.activeElement;
  state.modal=details;
  renderModal();
}
function closeModal(){
  state.modal=null;
  renderModal();
  if(modalOpener?.isConnected)modalOpener.focus();
  modalOpener=null;
}
function renderModal() {
  const root=$('#modal-root');
  const page=$('#app');
  if(page)page.inert=Boolean(state.modal);
  if(!state.modal){root.innerHTML='';document.body.classList.remove('modal-is-open');return;}
  document.body.classList.add('modal-is-open');
  const modal=state.modal;let title='',caption='',fields='',form='';
  if(modal.type==='add') {
    title='Новый сотрудник';caption='Добавьте участника рабочего пространства';form='add';
    fields=`<label class="form-field">ФИО сотрудника <input name="full_name" autocomplete="off" maxlength="80" minlength="2" required placeholder="Например, Алексей Миронов" autofocus></label>
     <label class="form-field">Должность <input name="position" maxlength="80" minlength="2" required placeholder="Например, UI/UX дизайнер"></label>
     <label class="form-field">Норма часов в неделю <input type="number" name="weekly_target_hours" min="1" max="80" value="40" required></label>`;
  } else if(modal.type==='start') {
    title='Новый таймер';caption='Фиксируйте время на конкретной задаче';form='start';
    fields=`<label class="form-field">Сотрудник <select name="employee_id" required>${employeeOptions(modal.id)}</select></label>
      <label class="form-field">Описание задачи <textarea name="description" minlength="3" maxlength="240" rows="3" required placeholder="Например, Проверка сценариев оформления заказа"></textarea><small>Опишите конкретный результат или выполняемое действие</small></label>
      <label class="form-field">Категория работы <select name="category">${categoryOptions()}</select></label>`;
  } else if(modal.type==='profile' || modal.type==='editEmployee') {
    const person=state.report.employees.find(e=>e.id===modal.id);
    if(!person){state.modal=null;root.innerHTML='';return;}
    if(modal.type==='profile'){
      const currentWork=person.active_entry_id!==null;
      const share=percent(person.focus_ms,person.tracked_ms);
      const planned=targetMs(person);
      const perTask=person.entries_count?person.tracked_ms/person.entries_count:0;
      root.innerHTML=`<div class="modal-backdrop" data-action="close-overlay"><div class="modal profile-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div class="modal-head"><div class="profile-person">${avatar(person)}<div><strong id="modal-title">${esc(person.full_name)}</strong><span>${esc(person.position)}</span></div></div><button class="table-icon" data-action="close-modal" aria-label="Закрыть">${icon('close',20)}</button></div><div class="profile-status"><span class="status ${currentWork?'status--active':'status--idle'}"><span class="status-dot"></span>${currentWork?'Таймер запущен':'Сейчас без таймера'}</span><small>Показатели за выбранный период</small></div><div class="profile-stats"><div><span>Учтено</span><strong>${duration(person.tracked_ms)}</strong></div><div><span>План</span><strong>${msHours(planned)} ч</strong></div><div><span>Задач</span><strong>${person.entries_count}</strong></div><div><span>Средняя запись</span><strong>${duration(perTask,true)}</strong></div></div><div class="profile-detail"><div><strong>Заполнение нормы</strong><span>${workload(person)}%</span></div><div class="progress"><span style="width:${Math.min(100,workload(person))}%"></span></div><div><strong>Доля профильных задач</strong><span>${share}%</span></div><div class="progress"><span class="progress--focus" style="width:${Math.min(100,share)}%"></span></div></div><p class="profile-hint">Это учёт времени и состава задач, а не объективная оценка качества, скорости или результативности сотрудника.</p><div class="modal-actions"><button type="button" class="btn btn--outline" data-action="edit-employee" data-id="${person.id}">${icon('edit',17)} Редактировать</button><button type="button" class="btn btn--primary" data-action="view-employee" data-id="${person.id}">${icon('chart',17)} Отчёт</button></div></div></div>`;
      requestAnimationFrame(()=>root.querySelector('button[data-action="close-modal"]')?.focus());
      return;
    }
    title='Профиль сотрудника'; caption='Измените данные и недельную норму'; form='employee';
    fields=`<input type="hidden" name="id" value="${person.id}"><label class="form-field">ФИО сотрудника <input name="full_name" autocomplete="off" maxlength="80" minlength="2" required value="${esc(person.full_name)}"></label><label class="form-field">Должность <input name="position" maxlength="80" minlength="2" required value="${esc(person.position)}"></label><label class="form-field">Норма часов в неделю <input type="number" name="weekly_target_hours" min="1" max="80" value="${person.weekly_target_hours}" required></label>`;
  } else if(modal.type==='edit') {
    const record=state.report.entries.find(e=>e.id===modal.id);
    if(!record){root.innerHTML='';return;}
    title='Редактировать запись';caption=record.full_name;form='edit';
    fields=`<input type="hidden" name="id" value="${record.id}"><label class="form-field">Описание задачи <textarea name="description" minlength="3" maxlength="240" rows="3" required>${esc(record.description)}</textarea></label><label class="form-field">Категория работы<select name="category">${categoryOptions(record.category)}</select></label>`;
  }
  root.innerHTML=`<div class="modal-backdrop" data-action="close-overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div class="modal-head"><div class="modal-icon">${icon(form==='start'?'play':form==='edit'?'edit':'users',24)}</div><button class="table-icon" data-action="close-modal" aria-label="Закрыть">${icon('close',20)}</button></div><h2 id="modal-title">${title}</h2><p>${esc(caption)}</p><form data-form="${form}"><div class="modal-fields">${fields}</div><div class="modal-actions"><button type="button" class="btn btn--outline" data-action="close-modal">Отмена</button><button type="submit" class="btn btn--primary">${icon(form==='start'?'play':'check',17)} ${form==='start'?'Запустить':form==='edit'?'Сохранить':'Добавить'}</button></div></form></div></div>`;
  requestAnimationFrame(()=>root.querySelector('input:not([type="hidden"]),select,textarea')?.focus());
}
function tick() {
  const now=Date.now()+state.clockDelta;
  document.querySelectorAll('[data-live-id]').forEach(el=>{const started=Number(el.dataset.start);el.textContent=digital(now-started);});
}
function csvSafe(value){
  let text=String(value??'');
  // Spreadsheet formulas may start after invisible Unicode format characters.
  if(/^[\u0000-\u0020\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]*[=+@-]/u.test(text))text=`'${text}`;
  return `"${text.replaceAll('"','""')}"`;
}
function exportCsv() {
  const report=state.page==='reports'&&state.reportEmployee ? state.filteredReport : state.report;
  if(!report)return;
  const columns=['Сотрудник','Должность','Описание задачи','Категория','Начало','Окончание','Время в периоде (мин)','Статус'];
  const rows=report.entries.map(e=>[e.full_name,e.position,e.description,e.category,new Date(e.started_at_ms).toLocaleString('ru-RU'),e.ended_at_ms===null?'':new Date(e.ended_at_ms).toLocaleString('ru-RU'),(e.overlap_ms/60000).toFixed(2),e.ended_at_ms===null?'Активна':'Завершена']);
  const csv='\uFEFF'+[columns,...rows].map(row=>row.map(csvSafe).join(';')).join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`chronos-report-${getPeriod().startDate}_${getPeriod().endDate}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),500);
  toast(`Экспортировано записей: ${rows.length}`);
}

// One delegated event listener works even when components are re-rendered.
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action]');if(!button)return;
  const action=button.dataset.action;
  if(action==='close-overlay' && event.target!==button)return;
  if(action==='nav'){state.page=button.dataset.page;closeModal();render();window.scrollTo(0,0);if(state.page==='audit')await reload();return;}
  if(action==='retry'||action==='refresh-audit'){await reload();return;}
  if(action==='add'){showModal({type:'add'});return;}
  if(action==='start'){showModal({type:'start',id:button.dataset.id||state.report?.employees.find(e=>e.active_entry_id===null)?.id||''});return;}
  if(action==='edit'){showModal({type:'edit',id:Number(button.dataset.id)});return;}
  if(action==='profile'||action==='edit-employee') {showModal({type:action==='profile'?'profile':'editEmployee',id:Number(button.dataset.id)});return;}
  if(action==='view-employee') {state.reportEmployee=String(button.dataset.id);state.page='reports';closeModal();await reload();return;}
  if(action==='close-modal'||action==='close-overlay'){closeModal();return;}
  if(action==='export'){exportCsv();return;}
  if(action==='apply-range'){try{getPeriod();await reload();}catch(error){toast(error.message,'error');}return;}
  if(action==='stop' && !state.busy){state.busy=true;button.disabled=true;
    try{await api(`/api/timers/${Number(button.dataset.id)}/stop`,{method:'POST'});toast('Таймер остановлен. Запись сохранена.');await reload();}
    catch(error){toast(error.message,'error');button.disabled=false;}finally{state.busy=false;}return;}
  if(action==='delete' && !state.busy){
    const row=state.report.entries.find(e=>e.id===Number(button.dataset.id));
    if(!row||row.ended_at_ms===null)return;
    if(!window.confirm(`Удалить запись «${row.description}»? Это действие нельзя отменить.`))return;
    state.busy=true;try{await api(`/api/entries/${row.id}`,{method:'DELETE'});toast('Запись удалена');await reload();}catch(err){toast(err.message,'error');}finally{state.busy=false;}
  }
});
document.addEventListener('submit',async event=>{
  const form=event.target.closest('form[data-form]');if(!form)return;
  event.preventDefault();if(state.busy)return;
  const payload=Object.fromEntries(new FormData(form).entries());
  state.busy=true;const button=form.querySelector('[type=submit]');button.disabled=true;
  try{
    const kind=form.dataset.form;
    if(kind==='add')await api('/api/employees',{method:'POST',body:JSON.stringify({...payload,weekly_target_hours:Number(payload.weekly_target_hours)})});
    else if(kind==='start')await api('/api/timers/start',{method:'POST',body:JSON.stringify({...payload,employee_id:Number(payload.employee_id)})});
    else if(kind==='employee')await api(`/api/employees/${Number(payload.id)}`,{method:'PUT',body:JSON.stringify({full_name:payload.full_name,position:payload.position,weekly_target_hours:Number(payload.weekly_target_hours)})});
    else if(kind==='edit')await api(`/api/entries/${Number(payload.id)}`,{method:'PUT',body:JSON.stringify({description:payload.description,category:payload.category})});
    closeModal();toast(kind==='add'?'Сотрудник добавлен':kind==='start'?'Таймер успешно запущен':kind==='employee'?'Профиль сотрудника обновлён':'Запись обновлена');await reload();
  }catch(err){toast(err.message,'error');button.disabled=false;}
  finally{state.busy=false;}
});
document.addEventListener('change',async event=>{
  if(event.target.id==='period-select'){
    const value=event.target.value;
    state.range=value;
    if(value==='custom') {state.customFrom ||= getTodayOffset(-6);state.customTo ||= getTodayOffset(0);render();}
    else await reload();
  }
  if(event.target.id==='range-from'||event.target.id==='range-to'){
    if(event.target.id==='range-from')state.customFrom=event.target.value;
    if(event.target.id==='range-to')state.customTo=event.target.value;
    // The user may change start and end sequentially. Apply both together
    // to avoid a misleading error while only one field has been edited.
  }
  if(event.target.id==='report-employee') {state.reportEmployee=event.target.value;await reload();}
});
document.addEventListener('input',event=>{
  if(event.target.id==='team-search'){
    const pos=event.target.selectionStart;state.search=event.target.value;render();
    const input=$('#team-search');input?.focus();input?.setSelectionRange(pos,pos);
  }
});
document.addEventListener('keydown',event=>{
  if(event.key==='Tab' && state.modal){
    const modal=$('#modal-root .modal');
    const focusable=[...modal.querySelectorAll('button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled])')];
    if(focusable.length){
      const first=focusable[0],last=focusable.at(-1);
      if(event.shiftKey && document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first.focus();}
    }
  }
  if(event.key==='Escape'&&state.modal){closeModal();}
  if(event.key==='/'&&state.page==='team'&&!state.modal&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName) && !event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();$('#team-search')?.focus();}
});
setInterval(tick,1000);
setInterval(()=>{if(document.visibilityState==='visible'&&!state.modal&&!state.busy)reload();},35000);
window.addEventListener('focus',()=>{if(!state.modal&&!state.busy)reload();});
await reload();
