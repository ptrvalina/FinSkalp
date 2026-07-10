# FinSkalp — Enterprise Gap Report

**Тип:** Аудит as-is (только чтение, без изменений кода)
**Дата:** 2026-07-09
**Область:** `flowsint-crypto-compliance/platform/v2/*`, `reporting/*`, `flowsint-api`, `flowsint-app`, демо-стенд `:8877`
**Базовый принцип:** текущая архитектура — базовый актив. Ничего не удаляется и не переписывается. Ниже — только карта, разрывы и приоритеты.

Легенда статуса:
- **WORKS** — реальная логика, подключена к БД/внешним API/зависимостям.
- **STUB** — hardcoded / synthetic / in-memory / TODO / декларативный манифест.
- **ABSENT** — заявлено, но не реализовано / не подключено.

Легенда оценок: **Приоритет** P0 (немедленно) … P3 (можно отложить) · **Риск** Critical/High/Medium/Low · **Сложность** S (дни) / M (недели) / L (1–2 мес.) / XL (квартал+).

---

## 1. Карта реализованных компонентов

### 1.1 Платформа v2 (ядро расследований)

| Компонент | RFC | Путь | Ядро (works) | Заглушки / декларатив | Персистентность |
|---|---|---|---|---|---|
| Blockchain Intelligence | 0012/0013 | `platform/v2/blockchain_intelligence/` | `analyze_address`, аналитика, профилирование, BTC block sync, Postgres sync-store (опц.) | Non-BTC block sync симулируется (`sim-*`), smart-contract/token — только в манифесте | Опц. Postgres + in-memory кэп |
| ICF | 0014 | `platform/v2/icf/` | 8-стадийный pipeline, entity extraction, evidence, quality-scoring, KG-bridge, scheduler | OCR документов/картинок — stub и **не подключены** к pipeline; scheduler in-memory | In-memory |
| CRIF | 0015 | `platform/v2/crif/` | Pipeline 9 стадий, entity resolution, комплаенс-проверки, rules engine, change-history | Реестры — **синтетика** (`_RegistryDataConnector`), sanctions — 4 записи hardcoded, `cache.py` — dead code | In-memory |
| RDE | 0016 | `platform/v2/rde/` | Оценка риска, факторы, корреляция, confidence, explainability, рекомендации | Registry-сигналы = stub-записи; `rollback()` = stub; temporal store in-memory | In-memory |
| ECCF | 0017 | `platform/v2/eccf/` | Регистрация, хеширование, integrity, audit trail, timeline, версии, KG-linking | `access_control` (RBAC) — **не применяется**; report/archive стадии — placeholder | **In-memory** (потеря при рестарте) |
| EIA | 0018 | `platform/v2/eia/` | Сбор контекста (RDE/KG/ECCF/workflow), explanation engines, рекомендации, PII-redaction | LLM — детерминированный stub (нет HTTP); нет SSE; analyst history stub; кэш in-memory | In-memory |
| ASPP | 0019 | `platform/v2/aspp/` | Реестр плагинов (bootstrap из реальных registry), event/REST catalog, versioning | GraphQL/gRPC/SDK — descriptors; webhooks — stub-доставка; marketplace — только листинг | In-memory |
| ESA | 0020 | `platform/v2/esa/` | RBAC+ABAC `evaluate_access` (реально, с тестами), MFA-политика | `api_protection` pipeline — **документация** (`flowsint_api.middleware.auth` не существует); crypto/SIEM/mesh/IdP — манифесты; audit in-memory | In-memory |
| IDOO | 0021 | `platform/v2/idoo/` | Скан реальных `.github/workflows`, monitoring-манифест, метрики | K8s/DR/observability — манифесты; health-probe **всегда HEALTHY** (`"mode":"stub"`) | In-memory |
| EGPR | 0022 | `platform/v2/egpr/` | RFC-каталог, maturity по наличию файлов, tech-debt реестр, ADR | Переходы RFC — non-persistent stub; board-workflow — статичный | In-memory (bootstrap) |

**Общая шина:** `HTTP → platform/v2/routes.py → gateway.py → {component}/service.py`; Celery beat → `flowsint-core/tasks/*.py`; UI → `flowsint-app/src/api/compliance-service.ts`. Все компоненты покрыты юнит-тестами (6–10 на RFC).

### 1.2 Отчёты (основа продукта)

| Отчёт | `report_type` | Builder | Статус |
|---|---|---|---|
| Screening Report | `address` | `FinSkalpReportBuilder.build_address_report` | WORKS (заголовок «Отчёт скрининга…») |
| SAR Report | `sar` | `SarReportBuilder.build` | WORKS |
| Forensic Report | `forensic` | `build_forensic_report_v2` + `enrich_forensic_report` | WORKS (эталон — 17+ секций) |
| Seizure Report | `seizure` | `SeizureReportBuilder.build` | WORKS (часть dict не рендерится) |

Оркестратор: `FinSkalpInvestigator.investigate()`. Рендер: Jinja2 → HTML → **WeasyPrint** (fallback в HTML). Экспорт: Excel (`openpyxl`), XML (115-ФЗ). i18n: только для FZ115.

### 1.3 Рабочее место аналитика (UI)

- **flowsint-app:** React 19 + Vite + TanStack Router/Query + Zustand + Tailwind v4 + Radix. `AnalystWorkspaceShell` с manifest-driven вкладками (summary/entities/wallets/timeline/evidence/graph/reports/activity). Вкладки `graph`, `wallets`, `reports` — **stub**. `EIA` полностью обёрнут в клиенте, но **не потребляется в UI**. `TasksSection`, `MetricsGrid` — существуют, но **не смонтированы**.
- **Демо-стенд:** богатый ops-центр — inbox, kanban, live feed (SSE), workflow track, evidence-chain, force-graph. Служит эталоном UX для Alert Center / Task Board.

### 1.4 Инфраструктура

- 2 реальных API-плоскости: `flowsint-api :5001` (JWT+RBAC), демо-стенд `:8877` (без auth на platform v2). Alembic — 45 ревизий. Docker Compose: dev/prod/hardening. CI: GitHub Actions (тесты + сборка образов). ~115 тест-файлов. OSINT-evidence — файловая система + SHA-256.

---

## 2. Что работает / stub / отсутствует (сводка)

**Работает по-настоящему (можно демонстрировать регулятору):**
- Полный цикл расследования по адресу (скрининг → on-chain → fusion → 4 отчёта) на демо-стенде с реальным TRON.
- On-chain аналитика и профилирование; BTC инкрементальный sync.
- RBAC+ABAC логика (ESA `evaluate_access`), harmonized RBAC на `:5001`.
- Postgres-аудит комплаенса, KG на Postgres, файловое evidence с хешами.
- Explainability-цепочка (RDE → EIA) на детерминированной логике.
- Метрики Prometheus, correlation-id, структурные JSON-логи, опц. OTEL.

**Stub / синтетика / in-memory (работает на демо, не на проде):**
- CRIF реестры и sanctions-лист; RDE registry-сигналы; non-BTC block sync.
- ICF OCR; EIA LLM; ASPP webhooks/marketplace/GraphQL/gRPC/SDK.
- ESA crypto/SIEM/mesh/IdP/api-protection; IDOO K8s/DR/observability/health-probe.
- Персистентность ECCF, RDE temporal, ICF scheduler, CRIF history/cache — в оперативной памяти.

**Отсутствует (заявлено, но нет):**
- Единая сущность **Case** (TD-C1), **Evidence** как first-class в БД (TD-C2).
- Реальный middleware ESA на пути каждого запроса.
- Бэкапы/restore-скрипты, DR-репликация/failover.
- WORM/immutable audit, tamper-evident цепочки.
- Реальный LLM-путь, SSE-стриминг.

---

## 3. Сравнение с Enterprise Investigation Platform

Эталон = класс Chainalysis Reactor / Elliptic Investigator / TRM / Palantir Gotham (расследовательские платформы enterprise-уровня).

| Возможность эталона | FinSkalp сейчас | Разрыв |
|---|---|---|
| Мульти-чейн on-chain аналитика | BTC/ETH/TRON реально; часть чейнов симулируется | **Средний** — расширить реальные адаптеры/sync |
| Кластеризация / attribution | Есть эвристики + attribution records | Малый–средний — нет ML-моделей |
| Risk scoring + explainability | RDE + explainability (детерминированно) | Малый — нет ML/temporal persistence |
| Реестры/sanctions live | Синтетика + demo OFAC | **Критический** — нет лицензированных фидов |
| Единая модель Case/Entity/Evidence | Fragmented (Investigation/ComplianceCase, evidence in-mem) | **Критический** (TD-C1/C2) |
| Chain-of-custody (WORM) | ECCF in-memory | **Критический** — нет персистентности/WORM |
| Граф знаний + визуализация | KG Postgres + force-graph | Малый — 2 графовых стека |
| AI-ассистент расследователя | EIA детерминированный, не в UI | Средний — нет реального LLM + UI |
| RBAC/ABAC/аудит | Реально на `:5001`; демо открыт | **Высокий** — демо-плоскость без auth |
| Отчёты enterprise-класса | 4 отчёта, forensic богатый | Средний — унификация секций |
| Наблюдаемость/SRE | Метрики+OTEL opt-in; health stub | Высокий — нет prod-стека/бэкапов/DR |
| API-платформа/SDK/marketplace | Каталоги + реестр плагинов | Низкий (для пилота) — стабы |

**Вывод:** FinSkalp — сильный **production-candidate прототип** с когерентной архитектурой и реальным ядром расследования. До enterprise-класса не хватает прежде всего: (1) персистентности evidence/audit + WORM, (2) закрытия демо-плоскости auth/RBAC, (3) реальных данных реестров/sanctions, (4) единой сущности Case/Evidence, (5) prod-инфры (бэкап/DR/observability). Ни один разрыв не требует переписывания — все закрываются эволюционно.

---

## 4. Gap Analysis (реестр разрывов)

Каждый разрыв: описание · влияние · риск · сложность · приоритет.

### P0 — Критично (блокеры регулируемого прода)

| ID | Разрыв | Влияние | Риск | Слож. | Приор. |
|---|---|---|---|---|---|
| GAP-01 | Демо-плоскость `:8877` без JWT/RBAC (`_noop_user`), токен на 3 роутах | Полный доступ к platform v2 без аутентификации при выставлении в сеть | Critical | M | P0 |
| GAP-02 | ECCF chain-of-custody in-memory (теряется при рестарте/scale-out) | Нарушение доказательности; несовместимо с 115-ФЗ/судом | Critical | L | P0 |
| GAP-03 | Аудит (ESA/ECCF/EIA) in-memory + compliance-audit не tamper-evident | Нет неизменяемого следа действий | Critical | L | P0 |
| GAP-04 | Нет бэкапов/restore и DR | Потеря данных без пути восстановления | Critical | M | P0 |
| GAP-05 | Реестры/sanctions — синтетика/demo-subset | Ложные результаты комплаенса в проде | High | L | P0 |

### P1 — Высокий

| ID | Разрыв | Влияние | Риск | Слож. | Приор. |
|---|---|---|---|---|---|
| GAP-06 | Единая сущность Case отсутствует (TD-C1) | Расследование не entity-first, дубли моделей | High | L | P1 |
| GAP-07 | Evidence не first-class в БД (TD-C2) | Слабая связность доказательств/отчётов | High | L | P1 |
| GAP-08 | ESA `api_protection` — документация, middleware отсутствует | Zero Trust не применяется автоматически | High | M | P1 |
| GAP-09 | IDOO health-probe всегда HEALTHY | Ложная зелёная телеметрия, скрытые сбои | High | M | P1 |
| GAP-10 | Нет rate-limit/TLS на `:5001` | DoS/перехват на периметре | High | M | P1 |
| GAP-11 | In-memory singletons (ECCF/audit/scheduler/temporal) блокируют горизонт. масштаб | Нельзя запускать >1 инстанса корректно | High | L | P1 |
| GAP-12 | CI гоняет ~4% тестов crypto-compliance, нет deploy-pipeline и интеграц. тестов | Регрессии проходят в прод | Medium | M | P1 |
| GAP-13 | `audit:read` не enforced; default-роль ANALYST | Эскалация привилегий | High | S | P1 |

### P2 — Средний

| ID | Разрыв | Влияние | Риск | Слож. | Приор. |
|---|---|---|---|---|---|
| GAP-14 | Non-BTC block sync симулируется | Неполный охват соседства для не-BTC | Medium | L | P2 |
| GAP-15 | ICF OCR документов/картинок stub и не подключён | Нет извлечения из сканов постановлений | Medium | M | P2 |
| GAP-16 | EIA без реального LLM + SSE | Ограниченная объяснимость/UX | Medium | M | P2 |
| GAP-17 | EIA/RDE/ECCF не подключены к report builders | Отчёты не используют платформенные данные | Medium | M | P2 |
| GAP-18 | UI: вкладки graph/wallets/reports — stub; EIA не в UI | Аналитик не получает полную картину | Medium | M | P2 |
| GAP-19 | Dual-gateway drift (`8877` vs `5001`) | Расхождение поведения/безопасности | Medium | L | P2 |
| GAP-20 | Prometheus/Loki отсутствуют в hardening-стеке | Нет prod-мониторинга/логов | Medium | M | P2 |

### P3 — Отложить (после пилота)

| ID | Разрыв | Влияние | Риск | Слож. | Приор. |
|---|---|---|---|---|---|
| GAP-21 | ASPP GraphQL/gRPC/SDK/marketplace — стабы | Нет внешней экосистемы плагинов | Low | XL | P3 |
| GAP-22 | mTLS/service mesh/OAuth2/FIDO2 | Усиление Zero Trust | Low | L | P3 |
| GAP-23 | ML-риск-модели (ONNX) | Точность выше эвристик | Low | XL | P3 |
| GAP-24 | Cross-region DR, cold storage (S3 Glacier) | RPO/RTO enterprise | Low | L | P3 |
| GAP-25 | Package cycle core ↔ crypto-compliance (TD-C4), Plugin First | Мешает вынести комплаенс в плагин | Medium | L | P3 |

---

## 5. Итог

Архитектура FinSkalp **зрелая и когерентная**: RFC-0000…0022, единый паттерн service/orchestrator/manifest/routes/tests, реальное ядро расследования. Основной разрыв между «100% в completion-доках» и enterprise-продом — это **персистентность, безопасность демо-плоскости, реальные данные и prod-инфра**. Все 25 разрывов закрываются эволюционно, без нарушения API/RFC/UI/отчётов/пайплайнов.

Дорожная карта закрытия — в сопутствующих документах:
- `architecture-hardening-plan.md` — усиление 9 компонентов.
- `enterprise-report-upgrade-plan.md` — отчёты до enterprise.
- `workspace-enhancement-roadmap.md` — рабочее место аналитика.
- `enterprise-readiness-roadmap.md` — 30/60/90/180 дней.
