# FinSkalp — Workspace Enhancement Roadmap

**Тип:** Дорожная карта усиления рабочего места аналитика (аудит + план; без изменений кода)
**Дата:** 2026-07-09
**Принцип:** интерфейс уже работает. **Запрещено** переписывать фронтенд, менять стек, удалять страницы, ломать навигацию. Все улучшения — **новые компоненты поверх существующей системы**, на **существующих API**.

---

## 1. Контекст стека (не меняется)

React 19 + Vite + **TanStack Router** (file-based) + **TanStack Query** + **Zustand** + **Tailwind v4** + **Radix/shadcn** (`src/components/ui/*`). Enterprise-примитивы: `src/components/enterprise/enterprise-ui.tsx` (`EnterprisePanel`, `EnterpriseContextBar`, `EntityCard`, `EvidenceRow`, `RiskBadge`, `ExplainabilityDrawer`).

**Точки монтирования (аддитивные, без слома навигации):**
1. **Manifest-driven вкладки** `AnalystWorkspaceShell` — новую вкладку можно объявить в `platform/v2/analyst_workspace/manifest.py` (`workspace_tabs`) + добавить `TabsContent`; сайдбар менять **не нужно**.
2. **Right-side drawer** — Radix `Sheet` / готовый `ExplainabilityDrawer`.
3. **`EnterprisePanel` + `useInvestigationUiContext()`** — новые панели читают `caseRef`/`selectedEntityId`.
4. **Command palette** — команды в `COMMAND_PALETTE_COMMANDS` манифеста.
5. Демо-стенд (`app.js`: `opsKanban`, `liveFeed`) — **референс UX** для Alert Center / Task Board.

**Контракт сохранения контекста:** новые панели используют `useInvestigationUiContext()`, `useWorkspaceSync()` (BroadcastChannel), `saveWorkspacePersonalization`.

---

## 2. 8 компонентов — статус, монтирование, API

| Компонент | Есть сейчас | Тип работы | Точка монтирования | Ключевые существующие API |
|---|---|---|---|---|
| **Case Dashboard** | Частично (3 места: `DashboardPage`, `summary`-вкладка, compliance-hero) | Enhancement (консолидация) | Новая/усиленная `summary`-вкладка shell | `GET /api/investigations`, `analyst-workspace/state`, `workflow/state`, `workflow/recommendations`, `cases/workflow/stats` |
| **Investigation Timeline** | Да (тонкий `ActivityTimeline`) | Enhancement | `timeline`-вкладка | `analyst-workspace/state` (`timeline.events`), `cases/{ref}/timeline`, `eccf/{id}/timeline`, `crif/history/{key}` |
| **Evidence Drawer** | Частично (`EvidenceRow`, `EvidenceSection` не смонтирован) | Enhancement | Radix `Sheet` из строк evidence | `investigations/{ref}/evidence`, `eccf/{id}` + `/verify` `/audit` `/timeline`, `evidence/export` |
| **Risk Panel** | Частично (`RiskBadge`+статичный `ExplainabilityDrawer`) | Enhancement (подключить live) | Drawer из `RiskBadge` в summary | `rde/assess`, `rde/priorities`, `rde/rules/evaluate`, `intelligence/analyze`, `intelligence-engine/run` |
| **AI Context Panel** | Chat есть; **EIA не в UI** | Net-new wiring | Новая панель/вкладка + palette `ask_ai` | `eia/assist`, `eia/context`, `eia/prompts`, `eia/manifest` |
| **Graph Insights** | Да (sketch-граф, compliance-preview); `graph`-вкладка stub | Enhancement | Заполнить `graph`-вкладку shell | `compliance/cases/{id}/graph`, `entities/{id}/neighbors`, `blockchain-intelligence/analyze`, `investigations/{ref}/explain/{entity}` |
| **Alert Center** | Частично (popover; Bell пустой); демо: inbox+feed | Enhancement | Расширить notifications или новый глоб. роут | workspace `notifications`, демо `GET /api/inbox`, `PATCH /inbox/{id}/workflow`, `GET /api/feed/live` (SSE), `rde/monitoring` |
| **Task Board** | Демо `opsKanban`; `TasksSection` не смонтирован | Net-new (поверх workflow) | Новая вкладка / общий компонент с compliance | `compliance/cases?workflow_status=`, `PATCH /compliance/cases/{id}`, `workflow/state`, демо `inbox` |

---

## 3. Детализация по компонентам

### 3.1 Case Dashboard
**Задача:** единый case-центричный обзор вместо трёх разрозненных.
**Как:** новый компонент `CaseDashboardPanel` в `enterprise/`, монтируется в `summary`-вкладку; агрегирует `analyst-workspace/state` + `workflow/*` + счётчики. Никаких новых роутов.

### 3.2 Investigation Timeline
**Задача:** обогатить тонкий `ActivityTimeline` (фильтры по типам событий, drill-down в ECCF/CRIF).
**Как:** расширить компонент (не заменять), источники — `cases/{ref}/timeline` + `eccf/{id}/timeline`. Обратная совместимость с текущей `timeline`-вкладкой.

### 3.3 Evidence Drawer
**Задача:** боковой drawer с chain-of-custody, verify, audit trail.
**Как:** `Sheet` открывается из `EvidenceRow`; данные — `eccf/{id}` + `/verify` `/audit` `/timeline`. Смонтировать неиспользуемый `EvidenceSection` внутри drawer.

### 3.4 Risk Panel
**Задача:** оживить статичный `ExplainabilityDrawer` реальными RDE-данными.
**Как:** `RiskPanel` дергает `rde/assess`/`rde/priorities`, показывает факторы+объяснение; открывается из `RiskBadge`.

### 3.5 AI Context Panel
**Задача:** дать аналитику EIA (объяснения, гипотезы, рекомендации) — сейчас API обёрнут, но не используется.
**Как:** новая панель/вкладка `AIContextPanel` → `eia/assist` + `eia/context`; команда `ask_ai` в palette. Нативный `FloatingChat` остаётся отдельно.

### 3.6 Graph Insights
**Задача:** заполнить stub-вкладку `graph` инсайтами (кластеры, exposure, соседи).
**Как:** `GraphInsightsPanel` поверх `compliance/cases/{id}/graph` + `entities/{id}/neighbors`; **не заменяет** sketch-граф, а дополняет.

### 3.7 Alert Center
**Задача:** единый центр алертов (сейчас — пустой Bell + popover; демо имеет полноценный inbox+SSE).
**Как:** `AlertCenter` использует workspace `notifications` + мост к демо `inbox`/`feed/live` через `VITE_COMPLIANCE_API`. Опц. новый глобальный пункт сайдбара (единственное допустимое доп. в навигации).

### 3.8 Task Board
**Задача:** канбан задач поверх workflow-модели (нет отдельного `/tasks` API — используем cases/inbox как карточки).
**Как:** `TaskBoard` на `compliance/cases?workflow_status=` + `PATCH /compliance/cases/{id}`; переиспользовать логику демо `opsKanban`. Оживить неиспользуемый `TasksSection`.

---

## 4. Известные нюансы для реализаторов

- `TasksSection`, `MetricsGrid` — существуют, но **не смонтированы** (готовы к переиспользованию).
- Вкладки `graph`, `wallets`, `reports` в shell — **stub** (целевые точки).
- `EvidenceSection` импортирован, но вытеснен `EvidenceRow`.
- `complianceService.listCases()` / `getWorkflowStats()` могут возвращать 404 на демо-роутере — на демо используются `/api/inbox` + `/api/cases/workflow/stats`. Учесть при мостах.
- Существуют **два графовых стека** (sketch force-graph vs compliance/демо evidence-graph) — Graph Insights должен **мостить, не заменять**.

---

## 5. Порядок внедрения

| Волна | Компоненты | Обоснование |
|---|---|---|
| 1 | Risk Panel, Evidence Drawer | Данные уже почти есть (RDE/ECCF), высокая ценность для аналитика |
| 2 | Investigation Timeline, Graph Insights | Расширение существующих stub/тонких вкладок |
| 3 | AI Context Panel, Case Dashboard | Подключение EIA + консолидация обзора |
| 4 | Alert Center, Task Board | Мост к демо-инбоксу/workflow, возможен глоб. роут |

Все волны — новые компоненты в `enterprise/`, существующие API, manifest-driven вкладки. Навигация, стек и страницы не меняются.
