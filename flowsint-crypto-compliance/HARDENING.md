# FinSkalp — Production Hardening Runbook



Self-hosted stack for observability, search, feature flags, DB audit, and attribution evaluation.



## Security



- **Hardening compose is standalone** — never merge with `docker-compose.prod.yml` or `docker-compose.dev.yml`. Merging re-declares prod services and can restart production containers.

- All hardening ports bind to **127.0.0.1 only** (not exposed to LAN).

- Use `UNLEASH_DISABLED=1` + `FINSKALP_FEATURE_FLAGS` when Unleash is not running.

- For LAN exposure of the demo stand, set `FINSKALP_DEMO_API_TOKEN` and restrict CORS.



## Prerequisites



```bash

# Install optional deps

uv sync --package flowsint-crypto-compliance --extra hardening --extra osint-quality



# Ensure base stack is already running (prod OR dev — do not start via hardening compose)

docker ps   # flowsint-postgres-prod or flowsint-postgres-dev must be healthy



# Start hardening ONLY (joins existing Docker network)

export FLOWSINT_DOCKER_NETWORK=flowsint_network_prod   # or flowsint_network_dev

export FLOWSINT_POSTGRES_HOST=flowsint-postgres-prod   # container hostname on that network

docker compose -f docker-compose.hardening.yml up -d

```



| Service     | URL (default)               | Purpose                          |

|-------------|-----------------------------|----------------------------------|

| pgHero      | http://127.0.0.1:8088       | Postgres slow queries / indexes  |

| Grafana     | http://127.0.0.1:3001       | Trace dashboards (admin/finskalp)|

| Tempo OTLP  | 127.0.0.1:4317 (gRPC)       | OpenTelemetry trace backend      |

| Meilisearch | http://127.0.0.1:7700       | Full-text search                 |

| Unleash     | http://127.0.0.1:4242       | Risk-logic feature flags         |



Port overrides: `GRAFANA_HOST_PORT`, `PGHERO_HOST_PORT`, `MEILI_HOST_PORT`, `UNLEASH_HOST_PORT`, `TEMPO_OTLP_GRPC_PORT`.



## Health endpoints



| Endpoint | Use | Blocks on collector pings? |

|----------|-----|----------------------------|

| `GET /api/health/live` | Liveness (K8s/Docker) | No |

| `GET /api/health/ready` | Readiness | No (cached snapshot) |

| `GET /api/health` | Ops dashboard | No (cached snapshot) |

| `GET /api/osint/collector-health?force=1` | Full collector audit | Yes (up to 45s) |



Collector pings run in a **background daemon** on stand startup.



## Task 2 — Distributed tracing



1. Set in `.env`:

   ```env

   OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317

   OTEL_SERVICE_NAME=finskalp-api

   ```

2. Start demo server: `flowsint-regulator-stand`

3. Run an investigation (`POST /api/finskalp/investigate`)

4. Open Grafana → Explore → Tempo → search `service.name=finskalp-api`



## Task 3 — DB performance



```bash

cd flowsint-api && alembic upgrade m5n6o7p8q9r0

# pgHero: http://127.0.0.1:8088

```



## Task 1+5 — Evaluation + feature flags



```bash

python flowsint-crypto-compliance/scripts/run_attribution_eval.py

curl http://127.0.0.1:8877/api/compliance/attribution/eval

UNLEASH_DISABLED=1

FINSKALP_FEATURE_FLAGS=cospend_v2

```



## Task 6 — Search



```bash

curl "http://127.0.0.1:8877/api/search?q=TRU"

```



## Troubleshooting



| Symptom | Fix |

|---------|-----|

| `/api/health` hangs | Upgrade stand — health must use snapshot only; use `/api/health/live` for probes |

| Prod containers restarted | Never `docker compose -f prod.yml -f hardening.yml`; use hardening file alone |

| Grafana port conflict | Set `GRAFANA_HOST_PORT=3002` |

| No traces | Check Tempo on 127.0.0.1:4317 |

| Unleash spam in logs | `UNLEASH_DISABLED=1` |

| pgHero can't connect | Match `FLOWSINT_DOCKER_NETWORK` + `FLOWSINT_POSTGRES_HOST` to running stack |



## Architecture reference



See [RFC-0000 Enterprise Constitution](flowsint-crypto-compliance/docs/rfc/RFC-0000-enterprise-constitution.md).

