# RFC-0010 Analyst Workspace & User Experience v2.0

**Статус:** Complete (100%)  
**Связанные RFC:** RFC-0005 (Investigation Platform), RFC-0008 (Design System)

## Цель

Единое рабочее пространство аналитика: вкладки, палитра команд, навигация по уровням, агрегированное состояние расследования.

## Принцип

Аналитик работает в едином контексте расследования — все панели, команды и данные синхронизированы через `InvestigationContextProvider` (RFC-0008).

## Вкладки (Главы 3–4)

| Вкладка | ID | Описание |
|---------|-----|----------|
| Сводка | `summary` | Обзор расследования и кейса |
| Сущности | `entities` | Обозреватель сущностей KG |
| Кошельки | `wallets` | Обозреватель кошельков |
| Хронология | `timeline` | События дела |
| Доказательства | `evidence` | Реестр доказательств |
| Граф | `graph` | Связи и граф |
| Отчёты | `reports` | Отчёты RFC-0005 |
| Активность | `activity` | Журнал активности |

## Модули навигации (Глава 2)

Dashboard, Investigation Center, Graph, Timeline, Entity/Wallet Explorer, Evidence, OSINT, Registry, AI Assistant.

## Уровни навигации (Глава 5)

- **global** — глобальная навигация платформы
- **contextual** — контекст расследования
- **local** — локальная панель

## Палитра команд (Глава 14)

Русскоязычные команды с горячими клавишами (Ctrl+K, Ctrl+1…8). Реализация: `workspace-command-palette.tsx` (cmdk).

## API

| Endpoint | Описание |
|----------|----------|
| `GET /analyst-workspace/manifest` | Панели, команды, SLA, sync fields |
| `GET /analyst-workspace/state` | Агрегат workspace + evidence + timeline + intelligence |

## UI

- `flowsint-app/src/components/analyst-workspace/analyst-workspace-shell.tsx`
- Интеграция: `/dashboard/investigations/$id` через `InvestigationWorkspaceSection`
- Compliance page: блок RFC-0010

## Вне скоупа

- Совместная работа в реальном времени
- Синхронизация нескольких окон браузера (BroadcastChannel stub)
- Полноценный универсальный поиск по backend

## Completion

[`rfc0010-completion.md`](../architecture/v2/rfc0010-completion.md)
