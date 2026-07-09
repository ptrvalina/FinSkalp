"""Celery worker entrypoints for FinSkalp Scalpel."""

from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import run_maigret
from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import run_spiderfoot

__all__ = ["run_maigret", "run_spiderfoot"]
