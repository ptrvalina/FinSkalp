"""RFC-0021 Ch.2 — deployment pipeline topology."""

from __future__ import annotations

from typing import Any


def topology_manifest() -> dict[str, Any]:
    """git → ci → artifact → cd → k8s → services → db → monitoring → backup → dr."""
    stages = [
        {"stage": "git", "tool": "GitHub", "description": "Source control, PR reviews, branch protection"},
        {"stage": "ci", "tool": "GitHub Actions", "description": "Lint, test, build on push/PR"},
        {"stage": "artifact", "tool": "Docker Registry", "description": "Immutable container images tagged by version"},
        {"stage": "cd", "tool": "GitOps / Compose", "description": "Declarative deployment manifests"},
        {"stage": "k8s", "tool": "Kubernetes", "description": "Orchestration — Deployment, StatefulSet, HPA"},
        {"stage": "services", "tool": "flowsint-api / celery / app", "description": "Application tier services"},
        {"stage": "db", "tool": "Postgres / Redis / Neo4j", "description": "Stateful data stores"},
        {"stage": "monitoring", "tool": "Prometheus / Grafana / Loki / Tempo", "description": "Metrics, logs, traces"},
        {"stage": "backup", "tool": "pg_dump / neo4j-admin / S3", "description": "Scheduled backup jobs"},
        {"stage": "dr", "tool": "Cross-region replica", "description": "Disaster recovery failover"},
    ]
    return {
        "rfc": "RFC-0021",
        "chapter": 2,
        "pipeline": stages,
        "stage_count": len(stages),
        "compose_files": [
            "docker-compose.dev.yml",
            "docker-compose.prod.yml",
            "docker-compose.hardening.yml",
        ],
        "makefile_targets": ["dev", "prod", "infra-dev", "migrate-dev", "test"],
        "principle_ru": "Топология развёртывания: Git → CI → артефакт → CD → K8s → сервисы → БД → мониторинг → бэкап → DR",
    }
