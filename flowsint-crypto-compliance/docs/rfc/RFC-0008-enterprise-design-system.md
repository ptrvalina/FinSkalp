# RFC-0008 Enterprise Design System v2.0

**Статус:** Complete (100%)  
**Связанные RFC:** RFC-0002 (presentation layer), RFC-0005 (Investigation Workspace)

## Цель

Единая дизайн-система FinSkalp: токены, темы, иконография сущностей, принципы UX для аналитических расследований.

## Принципы (Глава 1)

| Принцип | Реализация |
|---------|------------|
| Investigation First | `InvestigationContextProvider` — sessionStorage |
| Information Density | `.fs-density-compact`, табличный mono |
| Progressive Disclosure | shadcn Collapsible / Sheet |
| Explainability | RFC-0005 `/explain/{entity_id}` |
| Context Preservation | `useInvestigationUiContext` |

## Токены (Главы 3–5, 12)

- `flowsint-app/src/design-system/tokens.css`
- 8px grid: `--fs-space-1` … `--fs-space-6`
- Типографика: `--fs-text-h1` … `--fs-text-label`
- Семантика, риск, граф-сущности

## Темы (Глава 10)

- Light / Dark / High Contrast — `theme-provider.tsx`, `mode-toggle.tsx`

## API

| Endpoint | Описание |
|----------|----------|
| `GET /design-system/manifest` | Каталог токенов, компонентов, принципов |

## UI

- Compliance page: блок RFC-0008
- `EntityIcon` — Lucide-иконки сущностей

## Governance (Глава 13)

Манифест перечисляет обязательные поля для новых компонентов.

## Completion

[`rfc0008-completion.md`](../architecture/v2/rfc0008-completion.md)
