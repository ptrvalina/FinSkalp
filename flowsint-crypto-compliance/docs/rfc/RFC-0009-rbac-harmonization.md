# RFC-0009 RBAC Harmonization v2.0

**Статус:** Complete (100%)

## Цель

Единая матрица прав для compliance roles и investigation roles (owner/admin/editor/viewer).

## Правило

`effective_role = max(compliance_role, investigation_role → compliance_equivalent)`

| Investigation | Compliance equivalent |
|---------------|----------------------|
| owner | admin |
| admin | admin |
| editor | senior_analyst |
| viewer | viewer |

## API

| Endpoint | Описание |
|----------|----------|
| `GET /rbac/manifest` | Матрица ролей и permissions |
| `GET /rbac/effective?investigation_id=` | Эффективные права текущего пользователя |

## Интеграция

- `flowsint-api` platform v2 использует `require_harmonized_permission`
- Модуль: `platform/v2/rbac/`

## Completion

[`rfc0009-completion.md`](../architecture/v2/rfc0009-completion.md)
