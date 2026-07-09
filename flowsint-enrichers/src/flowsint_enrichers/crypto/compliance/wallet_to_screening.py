from typing import Any, Dict, List

from flowsint_core.core.enricher_base import Enricher
from flowsint_core.core.logger import Logger
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
)
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_types.fiat_crypto import Chain, WalletScreeningResult
from flowsint_types.wallet import CryptoWallet


@flowsint_enricher
class WalletToScreeningResult(Enricher):
    """[REG/OSINT] Real first-look wallet screening with on-chain and sovereign-registry evidence."""

    InputType = CryptoWallet
    OutputType = WalletScreeningResult

    @classmethod
    def name(cls) -> str:
        return "wallet_to_screening_result"

    @classmethod
    def category(cls) -> str:
        return "Compliance"

    @classmethod
    def key(cls) -> str:
        return "address"

    @classmethod
    def icon(cls) -> str | None:
        return "cryptowallet"

    @classmethod
    def documentation(cls) -> str:
        return (
            "Checks a crypto wallet for a first regulator-grade view: address validation, "
            "on-chain neighborhood, sovereign RF/CIS risk-registry labels (115-FZ list), "
            "risk score, evidence chain and Russian recommendations. API keys must be stored "
            "in Vault/environment; the enricher does not accept raw secrets as input."
        )

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "chain",
                "type": "select",
                "description": "Optional chain override. Auto-detect when empty.",
                "required": False,
                "options": [
                    {"label": "Auto", "value": ""},
                    {"label": "Bitcoin", "value": "btc"},
                    {"label": "Ethereum", "value": "eth"},
                    {"label": "TRON", "value": "tron"},
                ],
            },
            {
                "name": "limit",
                "type": "number",
                "description": "Maximum direct transfers to fetch per wallet (1..100).",
                "required": False,
                "default": "50",
            },
        ]

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        params = self.get_params()
        chain_param = params.get("chain") or None
        limit = _safe_limit(params.get("limit"))
        service = WalletScreeningService()
        results: List[OutputType] = []

        for wallet in data:
            try:
                chain = Chain(chain_param) if chain_param else None
                result = await service.screen(
                    WalletScreeningRequest(
                        address=wallet.address,
                        chain=chain,
                        depth=1,
                        limit=limit,
                    )
                )
                results.append(result)
            except Exception as exc:
                Logger.error(
                    self.sketch_id,
                    {
                        "message": (
                            "wallet_to_screening_result failed for "
                            f"{wallet.address[:12]}...: {exc}"
                        )
                    },
                )
        return results

    def postprocess(
        self, results: List[OutputType], original_input: List[InputType]
    ) -> List[OutputType]:
        for result in results:
            self.create_node(result)
            wallet = next((w for w in original_input if w.address == result.address), None)
            if wallet:
                self.create_node(wallet)
                self.create_relationship(wallet, result, "SCREENED_AS")
        return results


def _safe_limit(value: Any) -> int:
    try:
        return max(1, min(int(value or 50), 100))
    except (TypeError, ValueError):
        return 50


InputType = WalletToScreeningResult.InputType
OutputType = WalletToScreeningResult.OutputType
