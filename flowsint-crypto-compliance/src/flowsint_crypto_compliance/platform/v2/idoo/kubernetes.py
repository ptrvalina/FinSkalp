"""RFC-0021 Ch.4 — Kubernetes resources manifest."""

from __future__ import annotations

from typing import Any


def kubernetes_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 4,
        "namespace": "finskalp",
        "resources": {
            "deployments": [
                {"name": "flowsint-api", "replicas": 2, "port": 5001},
                {"name": "flowsint-app", "replicas": 2, "port": 80},
                {"name": "flowsint-celery-worker", "replicas": 3, "port": None},
            ],
            "statefulsets": [
                {"name": "postgres", "replicas": 1, "storage": "50Gi"},
                {"name": "redis", "replicas": 1, "storage": "10Gi"},
                {"name": "neo4j", "replicas": 1, "storage": "100Gi"},
            ],
            "hpa": [
                {"target": "flowsint-api", "min_replicas": 2, "max_replicas": 10, "cpu_target": 70},
                {"target": "flowsint-celery-worker", "min_replicas": 2, "max_replicas": 20, "queue_depth_target": 100},
            ],
            "network_policies": [
                {
                    "name": "api-ingress-only",
                    "pod_selector": "app=flowsint-api",
                    "ingress_from": ["ingress-controller", "flowsint-app"],
                    "technical_debt": "TD-IDOO-1",
                },
                {
                    "name": "db-internal-only",
                    "pod_selector": "tier=data",
                    "ingress_from": ["flowsint-api", "flowsint-celery-worker"],
                    "technical_debt": "TD-IDOO-1",
                },
            ],
        },
        "technical_debt": "TD-IDOO-1",
        "principle_ru": "K8s Deployment, StatefulSet, HPA, NetworkPolicy — декларативные манифесты",
    }
