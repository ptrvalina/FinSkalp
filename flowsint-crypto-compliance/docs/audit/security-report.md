# Отчёт по безопасности

**RFC-0001 · Глава 14** · Статус: Draft · Дата: 2026-07-08

---

## Зрелость модели безопасности

| Область | Prod (flowsint-api) | Demo stand | Оценка |
|---------|---------------------|------------|--------|
| Authentication | JWT | Optional Bearer | Split |
| Authorization | RBAC partial | Rate limit only | **Gap** |
| Secrets | Vault `Key` model + env | `compliance_secrets.py` | OK |
| Audit log | `ComplianceAuditLog` | Partial | OK |
| Evidence integrity | SHA-256 snapshots | `evidence_preservation.py` | Good |
| SSRF protection | `is_safe_external_url` | Same | Fixed |
| Upload validation | Magic bytes OCR | `security_hardening.py` | OK |
| Network exposure | Postgres/Redis on localhost in prod compose | Hardening 127.0.0.1 | Improved |

---

## Исправлено (подтверждено аудитом)

| Находка | Митигация |
|---------|-----------|
| SSRF в live collectors | URL allowlist |
| Blocking `/api/health` | Snapshot + background daemon |
| Hardening ports в LAN | `127.0.0.1:` bind |
| Compose merge с prod | Standalone hardening only |
| Unleash connection spam | `UNLEASH_DISABLED=1` |

---

## Открытые находки

### High

| ID | Находка | Файл |
|----|---------|------|
| SEC-H1 | `compliance.py` — JWT без `require_permission` на mutate | `routes/compliance.py` |
| SEC-H2 | Demo stand: большинство POST без token | `web_server.py` |

### Medium

| ID | Находка |
|----|---------|
| SEC-M1 | Infra ports 5433/6379/7474 на host (prod compose) |
| SEC-M2 | CORS `*` при `COMPLIANCE_DEMO_ALLOW_ALL_CORS=1` |
| SEC-M3 | Default postgres password `flowsint` в compose |

### Low

| ID | Находка |
|----|---------|
| SEC-L1 | IDOR in-memory inbox |
| SEC-L2 | HSTS off unless env set |
| SEC-L3 | Docker tron runs as root |

---

## RBAC

- **Compliance ops:** `services/compliance_rbac.py` — viewer/analyst/lead/admin
- **Investigation:** отдельная модель `InvestigationUserRole`
- **Gap:** не все compliance routes используют единую модель

---

## Рекомендации (RFC-0001 — только фиксация)

1. RBAC audit matrix: endpoint × role × permission
2. Обязательный `FINSKALP_DEMO_API_TOKEN` при `BIND_HOST != 127.0.0.1`
3. Secrets rotation runbook для `MASTER_VAULT_KEY_V1`

**Полный лог:** `flowsint-crypto-compliance/SECURITY_AUDIT.md`
