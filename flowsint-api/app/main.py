import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# Routes to be included
from app.api.routes import auth
from app.api.routes import investigations
from app.api.routes import sketches
from app.api.routes import enrichers
from app.api.routes import flows
from app.api.routes import events
from app.api.routes import analysis
from app.api.routes import chat
from app.api.routes import scan
from app.api.routes import keys
from app.api.routes import types
from app.api.routes import custom_types
from app.api.routes import enricher_templates
from app.api.routes import compliance
from app.api.routes import compliance_ops
from app.api.routes import platform_v2

# Comma-separated list of allowed origins, e.g. "https://app.example.com,https://staging.example.com"
# Falls back to localhost dev origin when unset. Never use "*" with allow_credentials=True.
origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]


app = FastAPI(ignore_trailing_slash=True, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "ok"}


@app.get("/metrics")
async def prometheus_metrics():
  from flowsint_crypto_compliance.observability.metrics import metrics_payload

  return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4")


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(sketches.router, prefix="/api/sketches", tags=["sketches"])
app.include_router(
    investigations.router, prefix="/api/investigations", tags=["investigations"]
)
app.include_router(enrichers.router, prefix="/api/enrichers", tags=["enrichers"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(analysis.router, prefix="/api/analyses", tags=["analyses"])
app.include_router(chat.router, prefix="/api/chats", tags=["chats"])
app.include_router(scan.router, prefix="/api/scans", tags=["scans"])
app.include_router(keys.router, prefix="/api/keys", tags=["keys"])
app.include_router(types.router, prefix="/api/types", tags=["types"])
app.include_router(custom_types.router, prefix="/api/custom-types", tags=["custom-types"])
app.include_router(enricher_templates.router, prefix="/api/enrichers/templates", tags=["enricher-templates"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["compliance"])
app.include_router(compliance_ops.router, prefix="/api/compliance", tags=["compliance-ops"])
app.include_router(platform_v2.router, prefix="/api/platform/v2", tags=["platform-v2"])


@app.on_event("startup")
async def bootstrap_platform_v2_startup() -> None:
    if not any(getattr(route, "path", "").startswith("/api/platform/v2") for route in app.routes):
        return
    from flowsint_crypto_compliance.platform.v2.integration import bootstrap_platform_v2

    await bootstrap_platform_v2()

from flowsint_crypto_compliance.observability.middleware import CorrelationIdMiddleware
from flowsint_crypto_compliance.observability.tracing import instrument_fastapi

app.add_middleware(CorrelationIdMiddleware)

from flowsint_crypto_compliance.observability.api_rate_limit import ApiRateLimitMiddleware

app.add_middleware(ApiRateLimitMiddleware)
instrument_fastapi(app)

from flowsint_crypto_compliance.demo.combat_mode import apply_combat_env_defaults
from flowsint_crypto_compliance.platform.v2.entity_store_mode import warn_if_memory_store_in_production

apply_combat_env_defaults()
warn_if_memory_store_in_production()
