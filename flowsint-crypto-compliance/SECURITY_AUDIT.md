# FinSkalp Security Audit — Phase 5.6 (2026-07-03)

Systematic pass per `finskalp_security_audit_prompt.md`. Findings below; **Critical/High fixed in code** during this phase.

## Summary

| Severity | Found | Fixed in Phase 5 | Open (product decision) |
|----------|-------|------------------|-------------------------|
| Critical | 0 | — | — |
| High | 3 | 3 | 0 |
| Medium | 5 | 1 | 4 |
| Low | 4 | 0 | 4 |

---

## Section 1 — Attack surface & inputs

### [HIGH] SSRF: live collectors bypassed SSRF filter

**Где:** `osint_core/live_collectors.py` — `_get_json`  
**Что не так:** HTTP client did not call `is_safe_external_url` (unlike Scalpel `network_gateway`).  
**Фикс:** Block non-public URLs before `httpx` request.  
**Проверка:** `tests/test_security_hardening.py`

### [HIGH] OCR upload: no magic-byte validation

**Где:** `demo/web_server.py` — `/api/ocr/extract`  
**Что не так:** Only extension + size checked; malicious payload could masquerade as PDF.  
**Фикс:** `validate_upload_magic()` in `scalpel/security.py`, enforced on upload.  
**Проверка:** `test_validate_upload_magic_pdf`

### [HIGH] No rate limit on public scoring/status endpoints

**Где:** `demo/web_server.py`  
**Что не так:** `/api/v1/score/*`, `/status`, OCR could be abused for DoS.  
**Фикс:** `DemoRateLimitMiddleware` in `security_hardening.py`.  
**Проверка:** manual — burst >20 req/s returns 429

### [MEDIUM] Tor gateway clearnet URL via tor route

**Где:** `scalpel/network_gateway.py`  
**Фикс:** SSRF check for non-.onion URLs on tor route.

### [MEDIUM] `live_collectors._get_json` user-controlled address in URL

**Статус:** Address validated by chain collectors; SSRF target is API host (env), not user URL — mitigated by SSRF on constructed URLs.

### [LOW] Batch upload CSV — no row-level SSRF (addresses only)

**Статус:** Acceptable; addresses passed to screening, not as fetch URLs.

---

## Section 2 — Auth & access control

### [MEDIUM] RBAC viewer role missing

**Фикс:** `ComplianceRole.VIEWER` with `case:read` only; flowsint-app `VITE_COMPLIANCE_VIEWER=1` for read-only kanban UI.

### [MEDIUM] Demo stand has no JWT (by design)

**Статус:** Combat prototype on `127.0.0.1`; production uses flowsint-api JWT + `compliance_rbac`.

### [LOW] IDOR on demo inbox

**Статус:** In-memory demo; production cases use `_ensure_case_access`.

---

## Section 3 — Dependencies & infrastructure

### [MEDIUM] CORS `*` only when `COMPLIANCE_DEMO_ALLOW_ALL_CORS=1`

**Статус:** Documented; default localhost-only.

### [LOW] HSTS not enabled by default

**Фикс:** `COMPLIANCE_DEMO_HSTS=1` enables `Strict-Transport-Security` header.

### [LOW] Docker root user

**Статус:** Existing tron compose; Blockscout stub documents non-root pattern — full deploy out of scope.

---

## Section 4 — Data integrity

### [MEDIUM] Workflow transitions

**Статус:** `can_transition()` enforced on demo + API.

### [LOW] Audit log immutability

**Статус:** Append-only in `compliance_service.log_audit` — no delete endpoint.

---

## Section 5 — Functional reliability

### [LOW] External API degradation

**Статус:** Circuit breaker + degraded responses in live collectors (existing).

---

## Verification commands

```bash
cd flowsint-crypto-compliance
PYTHONPATH=src;../flowsint-types/src python -m pytest tests/test_security_hardening.py tests/test_cospend_account_model.py tests/test_polygon_collector.py -q
```

---

## Explicit non-findings

- No stolen databases in codebase (policy enforced).
- No Marble/AGPL code imports (see `docs/MARBLE_STUDY.md`).
- SQL/Cypher: ORM/parameterized paths in compliance service (no user f-strings in queries found in audit pass).
