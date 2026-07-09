"""Live SSE ticker for combat mode — session metrics and on-chain screening, no RNG."""

from __future__ import annotations

import itertools
from typing import Any

from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode
from flowsint_crypto_compliance.demo.live_ops_metrics import get_live_ops_metrics

_rotate = itertools.cycle(range(4))


def live_combat_feed_event() -> dict[str, Any] | None:
    """Fallback row when the event bus is quiet — still real session / watchlist data."""
    if not is_combat_mode():
        return None

    metrics = get_live_ops_metrics().snapshot()
    tick = next(_rotate)
    addr = metrics.get("last_screen_address")
    risk = metrics.get("last_screen_risk")
    screens = int(metrics.get("wallet_screens") or 0)
    inv = int(metrics.get("investigations") or 0)
    kyt = int(metrics.get("kyt_alerts") or 0)
    str_n = int(metrics.get("str_received") or 0)

    if tick == 0 and addr and risk is not None:
        return {
            "type": "screening",
            "text_ru": (
                f"Live KYT · {str(addr)[:16]}… · риск {float(risk):.0f}/100 · "
                f"TronGrid/Blockstream"
            ),
            "source": "KYT_LIVE",
            "severity": _severity_for_risk(float(risk)),
        }

    if tick == 1 and screens:
        return {
            "type": "screening",
            "text_ru": (
                f"Сессия · {screens} on-chain скринингов · "
                f"{inv} расследований · {kyt} KYT-алертов"
            ),
            "source": "FinSkalp",
            "severity": "info",
        }

    watch = []
    try:
        from flowsint_crypto_compliance.demo.live_kyt_scanner import kyt_watchlist

        watch = kyt_watchlist()
    except Exception:
        pass

    if tick == 2 and watch:
        address, chain = watch[0]
        chain_label = chain.upper() if isinstance(chain, str) else chain.value.upper()
        return {
            "type": "alert",
            "text_ru": (
                f"Мониторинг · {len(watch)} live-адресов · "
                f"{chain_label} · {address[:12]}…"
            ),
            "source": "TX_MON",
            "severity": "medium",
        }

    if str_n:
        return {
            "type": "sar",
            "text_ru": f"Live СОО · принято {str_n} сообщений · банковский хаб 115-ФЗ",
            "source": "INST_HUB",
            "severity": "medium",
        }

    if watch:
        return {
            "type": "intel",
            "text_ru": f"Live очередь · {len(watch)} адресов в KYT watchlist",
            "source": "TX_MON",
            "severity": "info",
        }

    return {
        "type": "intel",
        "text_ru": (
            "Live режим · укажите FINSKALP_KYT_WATCHLIST или "
            "FINSKALP_COMBAT_SEED_ADDRESS в .env"
        ),
        "source": "FinSkalp",
        "severity": "info",
    }


def _severity_for_risk(risk: float) -> str:
    if risk >= 80:
        return "critical"
    if risk >= 65:
        return "high"
    if risk >= 40:
        return "medium"
    return "info"


def publish_screening_feed(
    *,
    address: str,
    chain: str,
    risk_score: float,
    summary_ru: str | None = None,
    alert_id: str | None = None,
) -> None:
    """Push a real screening hit into the live feed bus."""
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        get_event_bus().publish(
            "wallet_screened",
            payload={
                "source": "KYT_LIVE",
                "address": address,
                "chain": chain,
                "risk_score": round(risk_score, 1),
                "alert_id": alert_id,
            },
            severity=_severity_for_risk(risk_score),
            text_ru=(
                summary_ru
                or f"Live скрининг · {address[:16]}… · {risk_score:.0f}/100 · {chain.upper()}"
            ),
            correlation_id=alert_id,
        )
    except Exception:
        pass
