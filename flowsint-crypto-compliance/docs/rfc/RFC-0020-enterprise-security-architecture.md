# RFC-0020: Enterprise Security Architecture v2.0

**RFC-0020 · ESA · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0009](RFC-0009-rbac-harmonization.md), [RFC-0017](RFC-0017-evidence-chain-of-custody.md), [RFC-0019](RFC-0019-api-sdk-plugin-platform.md) |
| Реализация | `platform/v2/esa/` |
| Completion | [`rfc0020-completion.md`](../architecture/v2/rfc0020-completion.md) |

---

## Предисловие

ESA — единая корпоративная архитектура безопасности FinSkalp v2.0.

**Zero Trust — проверка каждого запроса, минимальные привилегии, аудит всего.**

---

## Глава 1. Zero Trust

Принципы `SecurityPrinciple` — `constraints.py`.

## Глава 2. IAM

Интеграция с RFC-0009 RBAC harmonization.

## Глава 3. Identity Providers

LDAP, OIDC, SAML, local — `identity.py`.

## Глава 4. Authentication

Password+MFA, FIDO2, JWT, service accounts — `authentication.py`. `require_mfa_for_admin`.

## Глава 5. Authorization

RBAC + ABAC — `authorization.py`, `evaluate_access()`. Интеграция `resolve_effective_permissions`.

## Глава 6. Data Classification

public/internal/confidential/restricted — `data_classification.py`.

## Глава 7. Cryptography

Encryption at-rest/transit — `cryptography.py`.

## Глава 8. Secrets

Vault integration, no-secrets-in-code — `secrets.py`.

## Глава 9. API Protection

Request pipeline: auth → authz → schema → rate limit → audit — `api_protection.py`.

## Глава 10. Service Mesh

mTLS policies stub — `service_mesh.py`.

## Глава 11. Knowledge Graph Security

Entity/relation access, export controls — `kg_security.py`.

## Глава 12. Evidence Security

ECCF integrity bridge — `evidence_security.py`.

## Глава 13. Audit System

Append-only security audit — `audit_system.py`.

## Глава 14. SIEM

Syslog/OpenTelemetry/webhook stubs — `siem.py`.

## Глава 15. Threat Model

STRIDE threat register — `threat_model.py`.

## Глава 16. Secure SDLC

Checklist manifest — `sdlc.py`.

## Глава 17. Vulnerability Management

Process stub — `vulnerability.py`.

## Глава 18. Security Monitoring

Metrics: failed auth, role changes, API anomalies — `security_monitoring.py`.

## Глава 19. BCP/DR

Business continuity manifest — `continuity.py`.

## Глава 20. Orchestration

`evaluate_security_request()`, `record_security_event()` — `orchestrator.py`.

---

## API

| Method | Path | Описание |
|--------|------|----------|
| GET | `/esa/manifest` | Манифест ESA |
| POST | `/esa/access/evaluate` | RBAC+ABAC evaluate |
| POST | `/esa/audit` | Запись security audit |
| GET | `/esa/threat-model` | Реестр угроз |
| GET | `/esa/monitoring` | Метрики безопасности |
| GET | `/esa/siem` | SIEM конфигурация |
| GET | `/esa/data-classification` | Правила классификации |

## Celery

`esa_security_scan_batch` — beat 3600s, integrity checks stub.
