import pytest

from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
    infer_chain,
)
from flowsint_crypto_compliance.storage.label_cache import LabelCache
from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel


def test_infer_chain_rejects_invalid_wallet():
    with pytest.raises(ValueError):
        infer_chain("not-a-wallet")


@pytest.mark.asyncio
async def test_wallet_screening_detects_high_risk_registry_label():
    wallet = "0x" + "a" * 40
    cache = LabelCache()
    cache.put(
        SovereignRiskLabel(
            label_id="reg-1",
            source=RegistrySource.ROSFINMONITORING,
            chain=Chain.ETH,
            address=wallet,
            entity_name="Криптомиксер (перечень 115-ФЗ)",
            category="mixer",
            risk_score=92,
            sanctioned=True,
            list_reference="Росфинмониторинг, перечень 115-ФЗ",
            confidence=0.9,
        )
    )
    service = WalletScreeningService(
        chain_adapters={Chain.ETH: InMemoryChainAdapter(Chain.ETH, [])},
        label_cache=cache,
    )

    result = await service.screen(WalletScreeningRequest(address=wallet, limit=10))

    assert result.chain == Chain.ETH
    assert result.risk_score >= 80
    assert result.risk_level.value == "critical"
    assert any(f["code"] == "SANCTIONS_LIST_HIT" for f in result.findings)
    assert result.source_status["registry_primary"] == "hit"


@pytest.mark.asyncio
async def test_wallet_screening_uses_onchain_fanout_and_counterparty_labels():
    wallet = "0x" + "a" * 40
    risky_counterparty = "0x" + "b" * 40
    transfers = [
        OnChainTransfer(Chain.ETH, "tx-in", risky_counterparty, wallet, "ETH", 1.0),
        *[
            OnChainTransfer(Chain.ETH, f"tx-out-{idx}", wallet, "0x" + f"{idx + 1:040x}", "ETH", 0.01)
            for idx in range(12)
        ],
    ]
    cache = LabelCache()
    cache.put(
        SovereignRiskLabel(
            label_id="reg-2",
            source=RegistrySource.INTERNAL_OSINT,
            chain=Chain.ETH,
            address=risky_counterparty,
            entity_name="Обналичивание (ransomware)",
            category="ransomware",
            risk_score=88,
            confidence=0.85,
        )
    )
    service = WalletScreeningService(
        chain_adapters={Chain.ETH: InMemoryChainAdapter(Chain.ETH, transfers)},
        label_cache=cache,
    )

    result = await service.screen(WalletScreeningRequest(address=wallet, limit=20))

    codes = {f["code"] for f in result.findings}
    assert "HIGH_FAN_IN_OUT" in codes
    assert any(c.startswith("REGISTRY_") for c in codes)
    assert result.onchain_summary["outbound_count"] == 12
    assert result.source_status["onchain"] == "ok"
    assert result.confidence >= 0.6
