# Отчёт углублённого технического аудита — Chronos Team 2.0

**Дата:** 27.10.2026 · **Основание:** повторный анализ версии 1.1 · **Предмет:** веб-приложение учёта рабочего времени без авторизации · **Результат:** 29 из 29 backend/functional/security тестов пройдены, `node --check` — успешно · **Python test coverage: 94%** (pytest-cov).

**Важно:** это инженерная оценка отдельных контролей, **НЕ** ISO-сертификация, **НЕ** подтверждение OWASP ASVS Level 1 и **НЕ** отчёт аккредитованной испытательной лаборатории. Полная проверка сотен требований международных стандартов не проводилась.

## 1. Матрица качества ISO/IEC 25010:2023 (выборочные критерии)

| Характеристика | Проверенные меры | Оценка/пробел |
|---|---|---|
| Functional suitability | Сотрудники, таймеры, edit/delete, отчёты, фильтры, пустой период, резервные копии | Подтверждено тестами API; нет браузерного e2e с настоящим сервером |
| Performance efficiency | SQLite WAL; асинхронный вызов через threadpool; O(фактически затронутые дни), выборка <=20k | Нужны нагрузочный тест, измерение p95 и capacity planning |
| Compatibility | Стандартные HTTP/JSON, браузер ES modules, SQLite | Нет matrix-тестов Safari/Firefox и старых Windows |
| Interaction capability | Адаптивная панель, поиск, модальные формы, клавиатурная навигация, явные сообщения ошибок | Полный WCAG 2.2 AA audit не выполнен |
| Reliability | Atomic transactions, uniqueness, WAL, deterministic report snapshot, health-check, SQLite backup | Нет geo-redundancy, автоматического восстановления и SLA |
| Security | CSRF controls, allowed Host, CSP, parameterized SQL, validation, bounded requests, audit trail | Нет пользователей и авторизации — запрет на публичную эксплуатацию |
| Maintainability | Типизированные модели API, отделённая БД/HTTP/UI логика, тесты, CI, changelog | Нет полноценного typecheck, нет утверждённого code review процесса |
| Flexibility | `CHRONOS_DB`, timezones, отсутствие vendor lock-in | Процесс миграции на PostgreSQL не реализован |
| Safety | Не используются реальные лица, неоднозначные метрики не представлены как «эффективность» | Нужна нормативная оценка для реальных HR-сценариев |

Ссылка: [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html); стандарт задаёт модель качеств, а не автоматическое «соответствует / не соответствует» для конкретного ПО.

## 2. OWASP ASVS 5.0 — сопоставление технических контролей

| Контроль / угроза | Реализация / свидетельство | Остаточный риск |
|---|---|---|
| Серверная проверка вводимых значений (ASVS V2.2) | Pydantic, запрещённые поля, диапазоны, категории, запрет bidi/управляющих Unicode-символов | Не проверены все возможные семантические правила HR |
| Безопасные SQL-вызовы | Только параметризованные выражения и транзакции | Доступ обладателя прав на физический файл БД сохраняется |
| CSRF межсайтовой формы | Custom header, same-origin проверка Origin/Referer/Fetch Metadata, без CORS | Не заменяет отсутствующую авторизацию |
| XSS / вывод данных | Экранирование динамического контента + CSP, нет JS-CDN | Нужен дополнительный DOM-XSS / SAST scan |
| Excel/CSV formula injection | Префикс `'` для формул с потенциальными невидимыми префиксами | Excel/LibreOffice/импорт других систем могут интерпретировать экранирование по-разному |
| API resource exhaustion | ≤16KiB HTTP body даже chunked; ≤20k rows; отчёт ≤371 день; audit ≤500 | Нет per-client rate limit, поскольку нет identity/principal |
| Data integrity | DB UNIQUE, CHECK, FOREIGN KEY; транзакционный audit | Удаление/правки администратором SQLite возможны; journal не защищён от root |
| Security response headers | CSP `default-src 'self'`, frame-ancestors none, nosniff, CORP, referrer deny, frame deny | Не настраивается HTTPS/ HSTS, т.к. localhost HTTP |
| Authentication / authorization | Отсутствует по условию задания | **Блокер для реальной эксплуатации** |

OWASP ASVS 5.0.0: https://asvs.owasp.org/ . Рекомендации по CSRF: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html .

## 3. NIST SP 800-218 SSDF — инженерный жизненный цикл

- **Prepare the Organization (PO):** документированы ограничения области, security assumptions и политика `SECURITY.md`; формальная security-команда отсутствует.
- **Protect the Software (PS):** фиксация версий Python-зависимостей, отсутствие стороннего клиентского CDN, `.gitignore`, минимальные контейнерные привилегии; дальнейшая защита ветки GitHub настраивается владельцем.
- **Produce Well-Secured Software (PW):** parameterized SQL, input validation, concurrency control, bounds, regression tests, тесты известных атак и изменения интерфейса.
- **Respond to Vulnerabilities (RV):** предусмотрены документирование дефектов и сценарий частного сообщения; автоматическое уведомление о CVE и процедура реагирования в этой среде не подтверждены.

NIST SP 800-218: https://csrc.nist.gov/pubs/sp/800/218/final . Это выборочная практическая привязка процессов, не полный аудит соответствия SSDF.

## 4. Доступность: WCAG 2.2

**Добавлено:** заметный `:focus-visible`, Escape для закрытия модального окна, перемещение фокуса в диалог, фон `inert` на время модального окна, возврат фокуса к кнопке-инициатору, ссылка «Перейти к содержимому», reduced-motion media query, `aria-label` на графике и управляющих кнопках, текстовые empty states.

**Не проверено:** все коэффициенты контрастности и target size; обзор со screen reader NVDA/VoiceOver, навигация без мыши по всему приложению, WCAG 2.2 AA checklist. Результат **не** является сертификатом WCAG.

W3C: https://www.w3.org/TR/WCAG22/

## 5. Threat modeling (STRIDE, кратко)

| Категория | Модель атаки | Защита / нерешённые вопросы |
|---|---|---|
| Spoofing | Пользователь выдает себя за другого | **Нет учётных записей → не решено**. Только localhost и fictitious data |
| Tampering | Удаление/исправление табеля и записи | транзакции + audit before/after; оператор не устанавливается |
| Repudiation | «Я не менял эту запись» | события операции есть, но actor attribution отсутствует |
| Information disclosure | внешний сайт пытается получить данные localhost | Host allowlist, нет CORS, CSP; локальный процесс всё равно может читать |
| Denial of Service | бесконечные запросы / гигантские отчёты | запрет больших body, лимиты отчёта; rate limiting не реализован |
| Elevation of privilege | подключение из Интернета к управлению рабочим временем | только localhost; отсутствует многоуровневая модель ролей |

## 6. Реальные исправления: версия 1.1 → 2.0

1. **HIGH (для доступного извне localhost): CSRF.** Изменяющие запросы требовали лишь рабочий маршрут; внешняя страница могла послать POST HTML-формой, обходя CORS для самого запроса. Добавлены проверка Fetch Metadata/Origin/Referer и обязательный нестандартный заголовок `X-Chronos-Request`. Проверено отрицательными тестами.
2. **MEDIUM: Отсутствие следа при изменениях.** Добавлены `audit_events`, `before_json`/`after_json`, инвариант «аудит и операция в одной транзакции», SQL-триггеры против обычных UPDATE/DELETE событий. Проверены успешные и ошибочные операции, повторный запрос и рестарт.
3. **MEDIUM: Неограниченный объём отчёта.** Добавлена граница 20 000 строк, 413 при превышении; не требуется извлекать в память весь набор. Проверено на 20 001 записи.
4. **MEDIUM: Стоимость распределения времени по дням.** До обновления каждый результат проходил по всем дням периода; теперь через `bisect_right` начинается с даты фактического пересечения и посещаются только затронутые дни.
5. **MEDIUM: Нет целостной процедуры backup.** Добавлен SQLite Backup API и `integrity_check`, запрет перезаписи, автоматический тест WAL с активным таймером.
6. **LOW: CSV-формулы и невидимые символы.** Дополнительное экранирование потенциально исполняемых значений; ввод скрытых Unicode control characters на стороне API теперь отклоняется.
7. **LOW: Модальное окно и клавиатура.** Фон `inert`, фокус возвращается, Esc, focus ring, reduced-motion.
8. **LOW: Нет пользовательского журнала изменений.** Добавлена отдельная страница и bounded `GET /api/audit`.
9. **LOW: Избыточная графическая разметка.** При диапазоне 365 дней подписи на графике прореживаются, без изменения точных исходных данных отчёта.

## 7. Подтверждения тестирования

- **29 `pytest` tests: PASS** — выполнение в текущей среде после модификаций. **Coverage: 94%** (критические модули API и SQLite 97% и 92% соответственно; это не гарантия отсутствия уязвимостей).
- Проверка **`node --check app/static/app.js`: PASS**. **6 утверждений Node.js** для XSS/CSV-экранирования: PASS.
- Тест миграции существующей схемы, без потери ранее сохранённых записей: PASS.
- SQLite backup с WAL, целостность, запрет перезаписи: PASS.
- **Uvicorn реальный HTTP:** PASS, сценарий из 6 запросов `health → add employee → start → report → stop → audit`; журнал содержит 3 корректных события.
- **Chromium локальный HTTP:** FAIL / BLOCKED_BY_ADMINISTRATOR — проблема ограничений окружения, а не доказанный дефект приложения. Нельзя считать браузерный e2e успешным.
- **Chromium in-memory with mock Fetch API:** UI initial render, adding employee, starting timer, audit list, no JS exceptions, no horizontal overflow at 390px: PASS. **Не заменяет e2e с реальной БД**.
- **Docker image build/run, penetration test, SAST/SCA, accessibility scanner, load test, backup restore drill:** не проводились; не приписывать подтверждения.

## 8. Решение о выпуске и условия эксплуатации

**GO для демонстрации в пределах localhost с вымышленными данными; NO-GO для публичного / производственного HR-развёртывания.** Для перехода к production нужны: authn/authz + audit actor, TLS, PostgreSQL или иная проектно обоснованная хранилище при росте нагрузки, аттестация работы с персональными данными и кадровым учётом в применимой юрисдикции, restore drill, automated SCA/SAST, наблюдаемость, threat modeling под реальные активы, реальные e2e браузеры и внешнее тестирование на проникновение.
