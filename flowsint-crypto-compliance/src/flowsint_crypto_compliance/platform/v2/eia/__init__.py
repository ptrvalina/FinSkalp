"""RFC-0018 Explainable AI & Investigation Assistant v2.0."""

from flowsint_crypto_compliance.platform.v2.eia.manifest import eia_manifest
from flowsint_crypto_compliance.platform.v2.eia.orchestrator import run_eia_task
from flowsint_crypto_compliance.platform.v2.eia.service import get_eia_service

__all__ = [
    "eia_manifest",
    "get_eia_service",
    "run_eia_task",
]
