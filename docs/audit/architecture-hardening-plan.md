# FinSkalp — Architecture Hardening Plan

**Тип:** План эволюционного усиления (только чтение/аудит, без изменений кода)
**Дата:** 2026-07-09
**Принцип:** архитектура уже правильная. Не переписывать, не менять домены, не ломать API/RFC, не менять названия сервисов. Только эволюционные, обратносовместимые изменения.

Для каждого из 9 компонентов: технический долг · узкие места · масштабирование · отказоустойчивость · безопасность · предлагаемые эволюционные шаги (совместимые с текущим кодом).

Легенда шагов: **[S]** дни · **[M]** недели · **[L]** 1–2 мес. Все шаги — аддитивные (новый модуль/опц. параметр/адаптер), без слома сигнатур.

---

## 1. Blockchain Intelligence (RFC-0012/0013)

**Технический долг:** silent degradation (адаптер падает → пустой in-memory neighborhood, но `ok:True`); стадии `risk_engine`/`timeline` в pipeline без логики; двойная запись Postgres + in-memory кэп; нет orchestrator/types-модуля.
**Узкие места:** соседство до 50 tx без пагинации; sync последовательно по 7 чейнам; индекс трансферов ≤200/адрес.
**Масштабирование:** in-memory locks в режиме `FINSKALP_ENTITY_STORE=memory`; BTC блок ≤50 tx.
**Отказоустойчивость:** нет ретраев на HTTP tip-fetch (`except: return None`); non-BTC sync симулируется; нет идемпотентности трансфера в Postgres.
**Безопасность:** нет валидации адреса/чейна сверх `normalize_chain_key`; PII из on-chain уходит в KG без редактирования.

**Эволюционные шаги:**
- [S] Явно возвращать `degraded: true` + причину в `analyze_address`, когда сработал fallback-адаптер (не менять форму ответа — добавить поле).
- [S] Добавить unique-constraint/upsert на `FinskalpIndexedTransfer` для идемпотентности (Alembic-миграция, аддитивно).
- [M] Реальный block-fetch для ETH/TRON через существующие провайдеры (расширить `_sync_*_block`, оставив BTC-путь).
- [M] Ретраи с backoff в `_fetch_tip_height`/block-fetch (обёртка, без смены API).
- [M] Курсорная пагинация соседства (`cursor`/`limit`) — новый опц. параметр.

---

## 2. ICF — Intelligence Collection Framework (RFC-0014)

**Технический долг:** scheduler in-memory (теряется при рестарте, не шарится между воркерами); `ok=True` при пустом сборе без ошибок валидации; OCR/изображения — stub и **не подключены** к `run_icf_pipeline`.
**Узкие места:** последовательная обработка записей в KG-bridge (N ingest-вызовов); нет пагинации; `asyncio.run()` на каждый Celery-job.
**Отказоустойчивость:** `collector.shutdown()` не вызывается на исключении; ретрай только для scheduled jobs.
**Безопасность:** security-манифест ссылается на vault/TLS, но ICF сам не enforce'ит; entity extractor пропускает сырой текст в KG (PII).

**Эволюционные шаги:**
- [M] Персистентность scheduler'а в Postgres (новая таблица + адаптер `PostgresCollectionScheduler`, in-memory как fallback).
- [S] `finally: collector.shutdown()` в orchestrator (bugfix, не меняет API).
- [S] Уточнить `result.ok` (пустой сбор → `ok=False` c причиной) — за флагом совместимости.
- [M] Подключить `DocumentProcessor`/`ImageProcessor` как опц. стадию pipeline (по флагу), заменить `_ocr_stub` на реальный Tesseract/PaddleOCR-адаптер.
- [M] Батч-ingest в KG-bridge (bulk вместо N вызовов).

---

## 3. CRIF — Compliance & Registry Intelligence (RFC-0015)

**Технический долг:** `_RegistryDataConnector` перезаписывает реальные фабрики коннекторов синтетикой; sanctions — 4 записи в коде; `ChangeHistoryStore` не трекает `old_value`; `RegistryCache` — dead code; cross-source проверки не получают данные из orchestrator.
**Узкие места:** in-memory history/monitor растут неограниченно; entity resolution N-вызовов; нет пагинации.
**Отказоустойчивость:** sanctions никогда не падает (может тихо вернуть пусто); нет ретраев (синтетика не ходит в сеть).
**Безопасность:** sanctions-данные в исходниках; нет редактирования полей в history.

**Эволюционные шаги:**
- [L] Реальные адаптеры реестров (ЕГРЮЛ/ЦБ/OpenSanctions) за интерфейсом коннектора; синтетика остаётся как `demo`-профиль по флагу.
- [M] Подключить `RegistryCache` (Redis) в orchestrator (закрыть dead code, TD-CRIF-3).
- [S] Трекинг `old_value` в `record_from_records` (diff).
- [M] Персистентность change-history/monitor (Postgres) + webhook-канал уведомлений аналитику (TD-CRIF-4).
- [S] Передавать `cross_source_records` из orchestrator в `run_organization_checks`.

---

## 4. RDE — Risk & Decision Engine (RFC-0016)

**Технический долг:** registry-сигналы = stub-записи (не реальный CRIF); `rollback()` = stub; `priorities()` лезет в приватный `_snapshots`; magic-numbers весов; temporal store не персистится.
**Узкие места:** `priorities()` — O(n) скан; KG-соседи ≤5; single-process snapshots.
**Отказоустойчивость:** signal_bridge глотает ошибки подсистем (`pass`); нет ретраев; snapshots растут неограниченно.
**Безопасность:** caller может подставить произвольный `signals` (доверенный путь); нет валидации `entity_key`.

**Эволюционные шаги:**
- [M] Заменить registry-stub на реальный вызов CRIF-pipeline (через существующий `signal_bridge`, сохранить сигнатуры).
- [L] Персистентность temporal store в Postgres (TD-RDE-1) + публичный API вместо `_snapshots`.
- [M] Реализовать `rollback()` поверх persistent rule store (TD-RDE-2).
- [S] Выносить веса/пороги в конфиг (не хардкод) — обратносовместимо через defaults.
- [S] Логировать (не глотать) сбои подсистем в signal_bridge с пометкой degraded.

---

## 5. ECCF — Evidence & Chain of Custody (RFC-0017)

**Технический долг:** весь стор (evidence/audit/timeline/archive) in-memory → рестарт = полная потеря; KG-bridge глотает исключения; report/archive стадии — placeholder; нет blob-хранилища.
**Узкие места:** `list_all()` O(n) для integrity-батча и поиска; нет пагинации; thread-lock = single-process.
**Отказоустойчивость:** integrity-сбой не блокирует запись; KG-сбой не фатален (тихо null); нет ретраев.
**Безопасность:** RBAC-манифест `access_control` **не применяется** на роутах; `actor` из тела запроса; payload без сканирования/лимитов; PII в памяти/KG.

**Эволюционные шаги (P0-приоритет — доказательность):**
- [L] **Postgres WORM-репозиторий** для evidence/audit/timeline (append-only, триггеры запрета UPDATE/DELETE); in-memory как dev-fallback. Сохранить `ECCFRepository` API.
- [M] Blob-хранилище (S3/MinIO) для крупных payload'ов вместо JSON в памяти.
- [S] Применить `access_control` (RBAC) как FastAPI-зависимость на ECCF-роутах.
- [S] Брать `actor` из аутентифицированного пользователя, не из тела.
- [M] Hash-chained audit (tamper-evident): каждая запись включает hash предыдущей.

---

## 6. EIA — Explainable AI & Investigation Assistant (RFC-0018)

**Технический долг:** LLM — детерминированный stub (нет HTTP-клиента); analyst history/hypotheses — stub; context-cache in-memory; contradictions/data-gaps — эвристики.
**Узкие места:** контекст — O(entities) round-trips к RDE/KG; метрики/аудит in-memory.
**Отказоустойчивость:** широкие `try/except` → пустые списки при сбоях (silent degradation); нет circuit-breaker.
**Безопасность:** хорошая база (constraints, `requires_analyst_confirmation`, PII-redaction), но prompt-injection guard только декларативен; EIA-аудит не в ESA.

**Эволюционные шаги:**
- [M] Реальный LLM-адаптер в `model_registry` (OpenAI/Anthropic HTTP), детерминированная модель — fallback (TD-EIA-1). Ключи через vault.
- [M] SSE-стриминг ответов (новый endpoint, старый JSON остаётся) (TD-EIA-2).
- [M] Redis-кэш контекста с TTL (TD-EIA-4); батч-запросы к RDE.
- [S] Подключить analyst history к analyst_workspace (TD-EIA-5).
- [S] Направить EIA-аудит в ESA audit system.

---

## 7. ASPP — API, SDK & Plugin Platform (RFC-0019)

**Технический долг:** webhooks — stub-доставка (без HTTP); marketplace — только листинг; GraphQL/gRPC/SDK — descriptors.
**Узкие места:** `PluginManager`/`WebhookRegistry` — process-local singletons (не durable); синхронная доставка webhook.
**Отказоустойчивость:** ретрай webhook симулируется; нет идемпотентности доставки.
**Безопасность:** нет HMAC-подписи исходящих webhook; нет валидации URL сверх invalid-host; OAuth/JWT/mTLS — манифест.

**Эволюционные шаги (низкий приоритет для пилота):**
- [M] Реальная HTTP-доставка webhook + HMAC-подпись + очередь ретраев (Celery), сохранить registry API.
- [M] Durable плагин-реестр/подписки (Postgres) вместо singleton.
- [L] Реальный GraphQL (Strawberry) / gRPC (grpcio) — как отдельные опц. сервисы, каталоги остаются.
- [S] Валидация целевых URL webhook (allowlist).

---

## 8. ESA — Enterprise Security Architecture (RFC-0020)

**Технический долг:** `api_protection` pipeline — документация (`flowsint_api.middleware.auth` отсутствует); crypto/SIEM/mesh/IdP — манифесты; audit in-memory; `run_security_scan` integrity-проверка тривиальна (`len(audit)>0`).
**Узкие места:** in-memory audit без ротации (при `retention_days:2555`); сессия БД на каждый gateway-вызов.
**Отказоустойчивость:** publish на event bus в `try/except: pass`.
**Безопасность:** сильная RBAC+ABAC логика (тесты есть), НО не применяется автоматически на каждом запросе (только явный `POST /esa/access/evaluate`); audit не tamper-evident.

**Эволюционные шаги (P1 — безопасность):**
- [M] Реализовать ESA как **FastAPI middleware** (реальный `evaluate_security_request` на пути запросов), начиная с `:5001`. Сохранить endpoint для ad-hoc проверок.
- [L] Persistent tamper-evident audit (Postgres + hash-chain), общий для ESA/ECCF/EIA.
- [S] Усилить integrity-проверку в `run_security_scan` (реальная верификация SHA-256 через ECCF `integrity.py`).
- [M] Реальный SIEM-экспорт (syslog/webhook) за флагом (TD-ESA-4).
- [L] Интеграция IdP (Keycloak/OIDC) — опц., JWT-путь остаётся (TD-ESA-1).

---

## 9. IDOO — Infrastructure, DevOps & Observability (RFC-0021)

**Технический долг:** K8s/DR/observability/backup — манифесты; health-probe `_probe_service` всегда HEALTHY (`"mode":"stub"`); нет Prometheus/Loki в compose.
**Узкие места:** health не даёт реального autoscaling-сигнала.
**Отказоустойчивость:** DR `"automated":False`, `last_tested:null`; нет circuit-breaker.
**Безопасность:** network policies — spec only; секреты — ссылка на vault без исполнения.

**Эволюционные шаги (P1 — наблюдаемость):**
- [M] Реальные health-probe: HTTP/DB/Redis/Neo4j ping вместо stub (сохранить форму `HealthProbeResult`).
- [M] Развернуть Prometheus + alertrules и Loki в hardening-compose (Grafana-дашборды уже есть).
- [M] Реальные backup-скрипты (`pg_dump`/neo4j-dump/evidence-sync) + CronJob (TD-IDOO-4/5).
- [L] Helm-чарты/K8s-манифесты из существующих deklarative-описаний (постепенно).
- [S] Включить OTEL по умолчанию в prod-compose (endpoint уже в `.env.example`).

---

## Сводная приоритизация усиления

| Приоритет | Компоненты | Ключевые шаги |
|---|---|---|
| **P0** | ECCF, ESA (audit) | Persistent WORM evidence+audit, hash-chain, применить RBAC на ECCF |
| **P1** | ESA (middleware), IDOO, RDE, ICF, CRIF | ESA middleware, реальные health-probe+Prometheus, persistent temporal/scheduler, реальные реестры |
| **P2** | Blockchain Intelligence, EIA | Реальный non-BTC sync, LLM+SSE, подключение OCR |
| **P3** | ASPP | Реальные webhooks/GraphQL/gRPC/marketplace |

Все изменения аддитивны: новые адаптеры/таблицы/middleware/опц. параметры. Публичные API, имена сервисов, RFC-контракты и текущие пайплайны сохраняются.
