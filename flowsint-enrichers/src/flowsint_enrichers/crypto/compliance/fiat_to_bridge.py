from typing import Any, Dict, List, Optional

from flowsint_core.core.enricher_base import Enricher
from flowsint_core.core.logger import Logger
from flowsint_crypto_compliance.chains import get_chain_adapter
from flowsint_crypto_compliance.engine.bridge_linker import BridgeLinker, BridgeTraceConfig
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_types.fiat_crypto import Chain, FiatCryptoBridge, FiatLegEvent


@flowsint_enricher
class FiatAlertToCryptoBridge(Enricher):
    """[REG] Trace fiat/FIU alert to on-chain bridge hypotheses (BTC/ETH/TRON)."""

    InputType = FiatLegEvent
    OutputType = FiatCryptoBridge

    @classmethod
    def name(cls) -> str:
        return "fiat_alert_to_crypto_bridge"

    @classmethod
    def category(cls) -> str:
        return "Compliance"

    @classmethod
    def key(cls) -> str:
        return "event_id"

    @classmethod
    def icon(cls) -> str | None:
        return "cryptowallet"

    @classmethod
    def documentation(cls) -> str:
        return (
            "Links a fiat-side FIU/bank alert to probable on-chain exit paths. "
            "Requires licensed platform and control-purchase seeds in the investigation sketch "
            "or linked platform_id on the alert."
        )

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        results: List[OutputType] = []
        params = self.get_params()
        max_hops = int(params.get("max_hops", 4))

        adapters = {
            Chain.BTC: get_chain_adapter(Chain.BTC),
            Chain.ETH: get_chain_adapter(Chain.ETH),
            Chain.TRON: get_chain_adapter(Chain.TRON),
        }
        linker = BridgeLinker(
            adapters=adapters,
            config=BridgeTraceConfig(max_hops=max_hops),
        )

        # MVP: context built only from alert metadata; extend with sketch graph later
        context = await linker.build_context(
            fiat_events=data,
            licensed_events=[],
            control_purchases=[],
        )

        for event in data:
            try:
                bridges = await linker.trace_fiat_event(event, context)
                results.extend(bridges)
            except Exception as exc:
                Logger.error(
                    self.sketch_id,
                    {"message": f"Bridge trace failed for {event.event_id}: {exc}"},
                )
        return results

    def postprocess(
        self, results: List[OutputType], original_input: List[InputType]
    ) -> List[OutputType]:
        if not self._graph_service:
            return results

        from flowsint_types.wallet import CryptoWallet

        for bridge in results:
            self.create_node(bridge)
            matching_fiat = next(
                (e for e in original_input if e.event_id == bridge.fiat_event_id),
                None,
            )
            if matching_fiat:
                self.create_relationship(matching_fiat, bridge, "FIAT_TO_CRYPTO")
            if bridge.exit_address:
                exit_wallet = CryptoWallet(address=bridge.exit_address)
                self.create_node(exit_wallet)
                self.create_relationship(bridge, exit_wallet, "EXIT_TO")
        return results

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "max_hops",
                "type": "number",
                "description": "Maximum on-chain hops to explore from entry address.",
                "required": False,
                "default": 4,
            },
            {
                "name": "ETHERSCAN_API_KEY",
                "type": "vaultSecret",
                "description": "Etherscan API key for ETH tracing.",
                "required": False,
            },
            {
                "name": "TRONGRID_API_KEY",
                "type": "vaultSecret",
                "description": "TronGrid API key for TRON tracing.",
                "required": False,
            },
        ]


InputType = FiatAlertToCryptoBridge.InputType
OutputType = FiatAlertToCryptoBridge.OutputType
