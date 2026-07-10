"""OpenTelemetry tracing — FastAPI, Celery, investigation pipeline phases."""

from __future__ import annotations

import functools
import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator

_CORRELATION_HEADER = "X-Correlation-ID"
_TRACER_NAME = "finskalp"


def otel_enabled() -> bool:
    try:
        from flowsint_crypto_compliance.feature_flags import otel_tracing_enabled

        if otel_tracing_enabled():
            return True
    except Exception:
        pass
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


def correlation_id_from_headers(headers: dict[str, str] | None) -> str | None:
    if not headers:
        return None
    for k, v in headers.items():
        if k.lower() == _CORRELATION_HEADER.lower():
            return v
    return None


def instrument_fastapi(app: Any) -> None:
    if not otel_enabled():
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        _setup_tracer_provider(os.getenv("OTEL_SERVICE_NAME", "finskalp-api"))
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass


def init_worker_tracing(service_name: str = "finskalp-worker") -> None:
    """Initialize OTLP tracing in Celery worker processes."""
    if not otel_enabled():
        return
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        _setup_tracer_provider(service_name)
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass


def _setup_tracer_provider(service_name: str) -> None:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": os.getenv("FINSKALP_ENV", "dev"),
        }
    )
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def get_tracer(name: str = _TRACER_NAME):
    if not otel_enabled():
        return None
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except Exception:
        return None


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    tracer = get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(name) as s:
        for k, v in attributes.items():
            if v is not None:
                s.set_attribute(k, str(v))
        yield


def trace_celery_task(task_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from flowsint_crypto_compliance.observability.logging import correlation_id_var

            if not kwargs.get("correlation_id"):
                cid = correlation_id_var.get()
                if cid:
                    kwargs["correlation_id"] = cid
            tracer = get_tracer("finskalp.celery")
            if tracer is None:
                return fn(*args, **kwargs)
            with tracer.start_as_current_span(task_name) as s:
                if kwargs.get("correlation_id"):
                    s.set_attribute("correlation_id", kwargs["correlation_id"])
                return fn(*args, **kwargs)

        return wrapper

    return decorator


def trace_async_celery_task(task_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            from flowsint_crypto_compliance.observability.logging import correlation_id_var

            if not kwargs.get("correlation_id"):
                cid = correlation_id_var.get()
                if cid:
                    kwargs["correlation_id"] = cid
            tracer = get_tracer("finskalp.celery")
            if tracer is None:
                return await fn(*args, **kwargs)
            with tracer.start_as_current_span(task_name) as s:
                if kwargs.get("correlation_id"):
                    s.set_attribute("correlation_id", kwargs["correlation_id"])
                return await fn(*args, **kwargs)

        return wrapper

    return decorator


def inject_trace_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Propagate W3C trace context into outbound HTTP / Celery headers."""
    out = dict(headers or {})
    if not otel_enabled():
        return out
    try:
        from opentelemetry.propagate import inject

        inject(out)
    except Exception:
        pass
    return out


def shutdown_tracing() -> None:
    """Flush pending spans on application shutdown."""
    if not otel_enabled():
        return
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:
        pass


def celery_dispatch_kwargs(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build Celery kwargs with correlation ID and trace propagation."""
    from flowsint_crypto_compliance.observability.logging import correlation_id_var

    out = dict(extra or {})
    cid = correlation_id_var.get()
    if cid and "correlation_id" not in out:
        out["correlation_id"] = cid
    return out
