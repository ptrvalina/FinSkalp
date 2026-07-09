# RFC-0010 Analyst Workspace — 100% Completion Checklist



Дата: 2026-07-09



## Единое рабочее пространство (Главы 1–2)



- ✅ Принцип «всё в контексте расследования»

- ✅ 10 модулей навигации в манифесте

- ✅ 3 уровня навигации: global / contextual / local



## Вкладки (Главы 3–4)



- ✅ 8 вкладок: Сводка, Сущности, Кошельки, Хронология, Доказательства, Граф, Отчёты, Активность

- ✅ `AnalystWorkspaceShell` — tabbed UI

- ✅ Русские подписи вкладок



## Панели и модули (Главы 5–12)



- ✅ Dashboard / Investigation Center — сводка

- ✅ Graph — ссылка на compliance graph

- ✅ Timeline / Activity — `ActivityTimeline`

- ✅ Entity / Wallet Explorer — заглушки с контекстом KG

- ✅ Evidence — `EvidenceSection`

- ✅ OSINT / Registry / AI Assistant — в манифесте и command palette



## Универсальный поиск (Глава 5)



- ✅ `platform/v2/analyst_workspace/search.py` — `universal_search()`

- ✅ `GET /analyst-workspace/search?q=&case_ref=`

- ✅ Command palette — debounced поиск через API



## Палитра команд (Глава 14)



- ✅ `workspace-command-palette.tsx` (cmdk)

- ✅ 16+ команд на русском

- ✅ Ctrl+K открывает палитру



## Уведомления (Глава 17)



- ✅ Типы уведомлений в манифесте

- ✅ `notifications` в state API (timeline + комментарии)

- ✅ UI: badge + popover в заголовке workspace shell



## Персонализация (Глава 18)



- ✅ density, theme, default_tab, locale в манифесте

- ✅ RFC-0008 themes + InvestigationContext

- ✅ localStorage (`workspace-personalization.ts`) + `GET|PUT /personalization`



## Производительность (Глава 19)



- ✅ SLA в манифесте (`performance_slas`)

- ✅ `latency_ms` в ответах manifest/state/search/collaboration

- ✅ Заголовок `X-Finskalp-Latency-Ms`



## Синхронизация окон (Глава 15)



- ✅ `sync_fields` в манифесте и state API

- ✅ `workspace-sync.ts` — BroadcastChannel `finskalp.workspace.v1`

- ✅ Синхронизация: activeTab, caseRef, selectedEntityId, filters



## Совместная работа (Глава 16)



- ✅ In-memory store комментариев/активности per `case_ref`

- ✅ `POST /collaboration/comment`, `GET /collaboration/activity`

- ✅ UI: панель комментариев во вкладке «Активность»

- ✅ `collaboration.realtime: "channel"` (polling; WebSocket — prod)



## API



- ✅ `GET /analyst-workspace/manifest`

- ✅ `GET /analyst-workspace/state?case_ref=&investigation_id=`

- ✅ `GET /analyst-workspace/search?q=&case_ref=`

- ✅ `POST /analyst-workspace/collaboration/comment`

- ✅ `GET /analyst-workspace/collaboration/activity?case_ref=`

- ✅ `GET|PUT /analyst-workspace/personalization`

- ✅ `platform/v2/analyst_workspace/service.py` — агрегация RFC-0005 + intelligence



## Frontend



- ✅ `compliance-service.ts` — manifest/state/search/collaboration/personalization

- ✅ Compliance page — блок RFC-0010

- ✅ Investigation page — AnalystWorkspaceShell



## Тесты



- ✅ `tests/test_rfc0010_analyst_workspace.py` — manifest, state, search, collaboration, personalization



## Вне скоупа (prod infrastructure)



- ⚠️ WebSocket push для realtime collaboration (сейчас polling 30s + BroadcastChannel между окнами)

- ⚠️ RFC-0004 package cycle (architectural)


