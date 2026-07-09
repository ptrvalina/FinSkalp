# RFC-0009 RBAC Harmonization — 100% Completion Checklist

Дата: 2026-07-09

## Единая матрица

- ✅ Compliance roles: viewer → admin
- ✅ Investigation roles: owner/admin/editor/viewer
- ✅ Mapping investigation → compliance equivalent
- ✅ `effective_compliance_role()` — max rank

## Permissions

- ✅ Compliance PERMISSIONS (case:read, batch:screen, …)
- ✅ Platform permissions (workspace:comment, investigation:edit, …)
- ✅ `harmonized_user_has_permission()`

## API

- ✅ `GET /rbac/manifest`
- ✅ `GET /rbac/effective?investigation_id=`

## Enforcement

- ✅ `require_harmonized_permission()` в `platform/v2/rbac/deps.py`
- ✅ `flowsint-api` platform_v2 router wired

## UI

- ✅ Compliance page — блок RFC-0009

## Тесты

- ✅ `tests/test_rfc0009_rbac.py`

## TD-S5

- ✅ Закрыт — harmonized RBAC layer
