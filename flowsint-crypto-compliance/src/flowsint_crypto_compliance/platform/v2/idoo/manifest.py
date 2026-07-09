"""RFC-0021 IDOO v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION
from flowsint_crypto_compliance.platform.v2.idoo.backup import backup_manifest
from flowsint_crypto_compliance.platform.v2.idoo.cicd import cicd_manifest
from flowsint_crypto_compliance.platform.v2.idoo.configuration import configuration_manifest
from flowsint_crypto_compliance.platform.v2.idoo.constraints import constraints_manifest
from flowsint_crypto_compliance.platform.v2.idoo.containers import containers_manifest
from flowsint_crypto_compliance.platform.v2.idoo.disaster_recovery import disaster_recovery_manifest
from flowsint_crypto_compliance.platform.v2.idoo.gitops import gitops_manifest
from flowsint_crypto_compliance.platform.v2.idoo.kubernetes import kubernetes_manifest
from flowsint_crypto_compliance.platform.v2.idoo.logging import logging_manifest
from flowsint_crypto_compliance.platform.v2.idoo.monitoring import monitoring_manifest
from flowsint_crypto_compliance.platform.v2.idoo.observability import observability_manifest
from flowsint_crypto_compliance.platform.v2.idoo.operations import operations_manifest
from flowsint_crypto_compliance.platform.v2.idoo.principles import principles_manifest
from flowsint_crypto_compliance.platform.v2.idoo.queues import queues_manifest
from flowsint_crypto_compliance.platform.v2.idoo.scaling import scaling_manifest
from flowsint_crypto_compliance.platform.v2.idoo.slo import slo_manifest
from flowsint_crypto_compliance.platform.v2.idoo.topology import topology_manifest
from flowsint_crypto_compliance.platform.v2.idoo.tracing import tracing_manifest
from flowsint_crypto_compliance.platform.v2.idoo.types import Environment, InfraPrinciple, ObservabilitySignal
from flowsint_crypto_compliance.platform.v2.idoo.versioning import versioning_manifest


def idoo_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "schema_version": SCHEMA_VERSION,
        "title": "Infrastructure, DevOps & Observability v2.0",
        "title_ru": "Инфраструктура, DevOps и наблюдаемость v2.0",
        "principle": "Infrastructure as Code",
        "principle_ru": "Инфраструктура как код, GitOps и наблюдаемость по умолчанию",
        "chapters": list(range(1, 20)),
        "infra_principles": [p.value for p in InfraPrinciple],
        "environments": [e.value for e in Environment],
        "observability_signals": [s.value for s in ObservabilitySignal],
        "principles": principles_manifest(),
        "topology": topology_manifest(),
        "containers": containers_manifest(),
        "kubernetes": kubernetes_manifest(),
        "cicd": cicd_manifest(),
        "gitops": gitops_manifest(),
        "configuration": configuration_manifest(),
        "observability": observability_manifest(),
        "monitoring": monitoring_manifest(),
        "logging": logging_manifest(),
        "tracing": tracing_manifest(),
        "scaling": scaling_manifest(),
        "queues": queues_manifest(),
        "backup": backup_manifest(),
        "disaster_recovery": disaster_recovery_manifest(),
        "operations": operations_manifest(),
        "versioning": versioning_manifest(),
        "slo": slo_manifest(),
        "constraints": constraints_manifest(),
        "api": {
            "manifest": "/api/platform/v2/idoo/manifest",
            "health": "/api/platform/v2/idoo/health",
            "observability": "/api/platform/v2/idoo/observability",
            "cicd": "/api/platform/v2/idoo/cicd",
            "runbooks": "/api/platform/v2/idoo/runbooks",
            "queues": "/api/platform/v2/idoo/queues",
            "backup": "/api/platform/v2/idoo/backup",
        },
    }
