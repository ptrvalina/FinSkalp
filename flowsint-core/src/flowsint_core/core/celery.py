from celery import Celery
from .config import settings

celery = Celery(
    "flowsint",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "flowsint_core.tasks.event",
        "flowsint_core.tasks.enricher",
        "flowsint_core.tasks.flow",
        "flowsint_core.tasks.compliance",
        "flowsint_core.tasks.scalpel",
        "flowsint_core.tasks.live_collectors",
        "flowsint_core.tasks.compliance_ops",
        "flowsint_core.tasks.blockchain_sync",
        "flowsint_core.tasks.icf",
        "flowsint_core.tasks.crif",
        "flowsint_core.tasks.rde",
        "flowsint_core.tasks.eccf",
        "flowsint_core.tasks.eia",
        "flowsint_core.tasks.aspp",
        "flowsint_core.tasks.esa",
        "flowsint_core.tasks.idoo",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,  # Allow each worker to prefetch up to 4 tasks
    task_routes={
        "scalpel_collect_onchain": {"queue": "scalpel-onchain"},
        "scalpel_collect_sanctions": {"queue": "scalpel-sanctions"},
        "scalpel_collect_username": {"queue": "scalpel-username"},
        "scalpel_collect_abuse": {"queue": "scalpel-abuse"},
        "scalpel_collect_darknet": {"queue": "scalpel-darknet"},
        "scalpel_collect_vasp": {"queue": "scalpel-vasp"},
        "scalpel_collect_court": {"queue": "scalpel-court"},
        "scalpel_collect_dns": {"queue": "scalpel-dns"},
        "run_scalpel_collect": {"queue": "scalpel-fusion"},
        "ingest_enforcement_notices": {"queue": "scalpel-enforcement"},
        "run_multihop_fusion": {"queue": "scalpel-fusion"},
        "live_collect_tron_chain": {"queue": "live-onchain"},
        "live_collect_tron_trc20": {"queue": "live-onchain"},
        "live_collect_btc_chain": {"queue": "live-onchain"},
        "live_collect_sanctions": {"queue": "live-sanctions"},
        "live_collect_bitcoinabuse": {"queue": "live-abuse"},
        "live_collect_maigret": {"queue": "live-username"},
        "live_collect_ahmia": {"queue": "live-darknet"},
        "sync_blockchain_chains_incremental": {"queue": "live-onchain"},
    },
    beat_schedule={
        "ingest-enforcement-notices-daily": {
            "task": "ingest_enforcement_notices",
            "schedule": 86_400.0,
        },
        "scan-watchlist-subscriptions-hourly": {
            "task": "scan_watchlist_subscriptions",
            "schedule": 3_600.0,
            "kwargs": {"limit": 500},
        },
        "blockchain-incremental-sync": {
            "task": "sync_blockchain_chains_incremental",
            "schedule": 120.0,
        },
        "icf-scheduled-collections": {
            "task": "icf_run_scheduled_collections",
            "schedule": 300.0,
        },
        "crif-registry-sync": {
            "task": "crif_sync_registries",
            "schedule": 600.0,
        },
        "rde-batch-reassess": {
            "task": "rde_batch_reassess",
            "schedule": 900.0,
        },
        "eccf-integrity-batch": {
            "task": "eccf_verify_integrity_batch",
            "schedule": 1800.0,
        },
        "eia-warm-context-cache": {
            "task": "eia_warm_context_cache",
            "schedule": 1200.0,
        },
        "aspp-deliver-webhooks": {
            "task": "aspp_deliver_webhooks",
            "schedule": 300.0,
        },
        "esa-security-scan": {
            "task": "esa_security_scan_batch",
            "schedule": 3600.0,
        },
        "idoo-health-probe": {
            "task": "idoo_health_probe_batch",
            "schedule": 120.0,
        },
    },
)

try:
    from celery.signals import worker_process_init

    @worker_process_init.connect
    def _init_celery_otel(**_kwargs: object) -> None:
        from flowsint_crypto_compliance.observability.tracing import init_worker_tracing

        init_worker_tracing()
except Exception:
    pass
