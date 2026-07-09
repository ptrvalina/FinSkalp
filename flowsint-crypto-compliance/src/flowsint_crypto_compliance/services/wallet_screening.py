from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from flowsint_crypto_compliance.chains import get_chain_adapter
from flowsint_crypto_compliance.chains.base import AddressNeighborhood, ChainAdapter
from flowsint_crypto_compliance.engine.xgboost_risk import SovereignRiskModel
from flowsint_crypto_compliance.storage.label_cache import LabelCache
from flowsint_types.fiat_crypto import (
    Chain,
    SovereignRiskLabel,
    WalletRiskLevel,
    WalletScreeningResult,
)

MAX_ADDRESS_LEN = 128
MAX_NEIGHBORHOOD_LIMIT = 300
HIGH_RISK_KEYWORDS = frozenset(
    {
        "mixer",
        "tornado",
        "blender",
        "sanctions",
        "ofac",
        "scam",
        "ransomware",
        "darknet",
        "terror",
        "fraud",
        "stolen",
    }
)


@dataclass(frozen=True)
class WalletScreeningRequest:
    address: str
    chain: Chain | None = None
    depth: int = 1
    limit: int = 50


class WalletScreeningService:
    """
    First-look wallet screening (fully sovereign).

    The service is intentionally deterministic and conservative: it combines on-chain
    behaviour with the sovereign RF/CIS risk-label registry (115-FZ list, FIU, internal
    OSINT). Source failures are explicit, and raw personal data is never emitted.
    """

    def __init__(
        self,
        *,
        chain_adapters: dict[Chain, ChainAdapter] | None = None,
        label_cache: LabelCache | None = None,
    ) -> None:
        self._adapters = chain_adapters or {}
        self._label_cache = label_cache or LabelCache()

    async def screen(self, request: WalletScreeningRequest) -> WalletScreeningResult:
        address = _sanitize_address(request.address)
        chain = request.chain or infer_chain(address)
        depth = max(1, min(request.depth, 3))
        limit = max(1, min(request.limit, MAX_NEIGHBORHOOD_LIMIT))
        source_status: dict[str, str] = {"address_validation": "ok"}
        findings: list[dict[str, Any]] = []
        evidence: list[str] = [f"wallet:{chain.value}:{_safe_address(address)}"]

        adapter = self._adapters.get(chain)
        if adapter is None and self._adapters:
            from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter

            adapter = InMemoryChainAdapter(chain, [])
        if adapter is None:
            adapter = get_chain_adapter(chain)
        neighborhood = await self._safe_neighborhood(
            adapter,
            address,
            depth=depth,
            limit=limit,
            source_status=source_status,
            evidence=evidence,
        )

        primary_label = self._lookup_label(chain, address)
        if primary_label:
            source_status["registry_primary"] = "hit"
            findings.extend(_findings_from_label(primary_label, "primary_wallet"))
            evidence.append(_label_evidence(primary_label))
        else:
            source_status["registry_primary"] = "miss"

        counterparty_labels = []
        if neighborhood:
            counterparty_labels = self._lookup_counterparty_labels(neighborhood)
            source_status["registry_counterparties"] = (
                f"hits:{len(counterparty_labels)}" if counterparty_labels else "miss"
            )
            for label in counterparty_labels[:10]:
                findings.extend(_findings_from_label(label, "counterparty"))
                evidence.append(_label_evidence(label))

            onchain_findings = _findings_from_neighborhood(neighborhood)
            findings.extend(onchain_findings)
            evidence.extend(f["evidence"] for f in onchain_findings if f.get("evidence"))

        heuristic_score = _aggregate_risk(findings, primary_label, counterparty_labels, neighborhood)
        ml = SovereignRiskModel().score_wallet(
            findings=findings,
            risk_score_hint=primary_label.risk_score if primary_label else None,
            sanctioned=bool(primary_label and primary_label.sanctioned),
            counterparty_hits=len(counterparty_labels),
            onchain_hops=(
                len(neighborhood.inbound) + len(neighborhood.outbound) if neighborhood else 0
            ),
            heuristic_score=heuristic_score,
        )
        risk_score = ml.score
        risk_level = _risk_level(risk_score)

        if neighborhood:
            onchain_summary = _summarize_neighborhood(neighborhood)
            from flowsint_crypto_compliance.attribution import AttributionEngine
            from flowsint_crypto_compliance.storage.kyt_exposure_store import get_exposure

            engine = AttributionEngine(label_cache=self._label_cache)
            attr = await engine.attribute_wallet(
                address=address,
                chain=chain.value,
                inbound=neighborhood.inbound,
                outbound=neighborhood.outbound,
            )
            engine.sync_to_label_cache(attr)
            onchain_summary["kyt_exposure"] = (
                attr.exposure.to_dict() if attr.exposure else {}
            )
            onchain_summary["attribution"] = attr.to_dict()
            if attr.labels:
                source_status["kyt_primary"] = "auto"
            if attr.sanctions_hits:
                source_status["sanctions"] = f"hits:{len(attr.sanctions_hits)}"
            for src, st in attr.source_status.items():
                source_status[f"attr_{src}"] = st

            # Manual MetaSleuth import supplements (Tier-1) when present
            imported = get_exposure(chain.value, address)
            if imported and attr.exposure:
                from flowsint_crypto_compliance.engine.exposure_engine import compute_exposure

                merged = compute_exposure(
                    focus_address=address,
                    chain=chain,
                    inbound=neighborhood.inbound,
                    outbound=neighborhood.outbound,
                    label_lookup=lambda a: engine._label_for_exposure(chain, a, attr.labels),
                    imported_exposure=imported,
                )
                onchain_summary["kyt_exposure"] = merged.to_dict()
                source_status["kyt_import"] = "hit"

            if chain == Chain.TRON and hasattr(adapter, "get_account_state"):
                try:
                    account = await adapter.get_account_state(address)  # type: ignore[attr-defined]
                    onchain_summary["balance_trx"] = account.get("balance_trx")
                    onchain_summary["balance_usd"] = account.get("balance_usd")
                    onchain_summary["tokens"] = account.get("tokens") or []
                    onchain_summary["token_count"] = account.get("token_count", 0)
                    source_status["account_state"] = "ok"
                except Exception:
                    source_status["account_state"] = "degraded"
        else:
            onchain_summary = {
                "chain": chain.value,
                "address": _safe_address(address),
                "inbound_count": 0,
                "outbound_count": 0,
                "counterparties": 0,
            }
            from flowsint_crypto_compliance.engine.exposure_engine import compute_exposure
            from flowsint_crypto_compliance.storage.kyt_exposure_store import get_exposure

            imported = get_exposure(chain.value, address)
            if imported:
                exposure = compute_exposure(
                    focus_address=address,
                    chain=chain,
                    inbound=[],
                    outbound=[],
                    label_lookup=lambda addr: self._lookup_label(chain, addr),
                    imported_exposure=imported,
                )
                onchain_summary["kyt_exposure"] = exposure.to_dict()
                source_status["kyt_primary"] = "hit"
        onchain_summary["risk_model"] = {
            "model_version": ml.model_version,
            "heuristic_score": ml.heuristic_score,
            "model_score": ml.model_score,
        }
        if chain == Chain.TRON:
            from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta

            onchain_summary.update(get_on_chain_source_meta())
            if neighborhood:
                source_status["onchain"] = "ok"
            source_status["onchain_provider"] = onchain_summary.get("on_chain_source", "trongrid")

        confidence = _confidence(source_status, findings, neighborhood)
        result = WalletScreeningResult(
            screening_id=_screening_id(chain, address),
            address=address,
            chain=chain,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            summary_ru=_summary_ru(chain, address, risk_score, risk_level, findings),
            findings=findings,
            evidence_chain=sorted(set(evidence)),
            source_status=source_status,
            onchain_summary=onchain_summary,
            recommendations_ru=_recommendations(risk_level, findings),
            limitations_ru=_limitations(source_status),
        )
        return result

    async def _safe_neighborhood(
        self,
        adapter: ChainAdapter,
        address: str,
        *,
        depth: int,
        limit: int,
        source_status: dict[str, str],
        evidence: list[str],
    ) -> AddressNeighborhood | None:
        try:
            neighborhood = await adapter.get_neighborhood(address, depth=depth, limit=limit)
            source_status["onchain"] = "ok"
            evidence.append(
                "onchain:"
                f"{neighborhood.chain.value}:in={len(neighborhood.inbound)}:"
                f"out={len(neighborhood.outbound)}"
            )
            return neighborhood
        except Exception as exc:
            source_status["onchain"] = f"degraded:{exc.__class__.__name__}"
            evidence.append("onchain:degraded")
            return None

    def _lookup_label(self, chain: Chain, address: str) -> SovereignRiskLabel | None:
        try:
            return self._label_cache.lookup(chain, address)
        except Exception:
            return None

    def _lookup_counterparty_labels(
        self, neighborhood: AddressNeighborhood
    ) -> list[SovereignRiskLabel]:
        labels: list[SovereignRiskLabel] = []
        seen: set[str] = set()
        for tx in [*neighborhood.inbound, *neighborhood.outbound]:
            for addr in (tx.source, tx.target):
                if addr == neighborhood.address or addr in seen:
                    continue
                seen.add(addr)
                label = self._lookup_label(neighborhood.chain, addr)
                if label:
                    labels.append(label)
        return labels


_SOLANA_BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def infer_chain_slug(address: str) -> str:
    """Detect chain slug including multichain extensions (polygon, solana, …)."""
    address = _sanitize_address(address)
    if ":" in address:
        prefix, rest = address.split(":", 1)
        if prefix.lower() in ("polygon", "bsc", "eth", "tron", "btc", "solana"):
            return prefix.lower()
        address = rest
    if re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        return "eth"
    if re.fullmatch(r"T[1-9A-HJ-NP-Za-km-z]{33}", address):
        return "tron"
    if re.fullmatch(r"([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})", address):
        return "btc"
    if _SOLANA_BASE58.fullmatch(address) and not address.startswith("T"):
        return "solana"
    raise ValueError("Unsupported or invalid wallet address format")


def infer_chain(address: str) -> Chain:
    slug = infer_chain_slug(address)
    if slug == "tron":
        return Chain.TRON
    if slug == "btc":
        return Chain.BTC
    if slug in ("eth", "bsc", "polygon"):
        return Chain.ETH
    if slug == "solana":
        raise ValueError(
            "Solana address detected; pass chain=solana explicitly for screening"
        )
    raise ValueError("Unsupported or invalid wallet address format")


def _sanitize_address(address: str) -> str:
    if not isinstance(address, str):
        raise ValueError("Wallet address must be a string")
    value = address.strip()
    if not value:
        raise ValueError("Wallet address is required")
    if len(value) > MAX_ADDRESS_LEN:
        raise ValueError("Wallet address is too long")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("Wallet address contains control characters")
    if any(ch.isspace() for ch in value):
        raise ValueError("Wallet address must not contain whitespace")
    return value.lower() if value.startswith("0x") else value


def _safe_address(address: str) -> str:
    return f"{address[:10]}…{address[-6:]}" if len(address) > 18 else address


def _screening_id(chain: Chain, address: str) -> str:
    digest = hashlib.sha256(f"{chain.value}:{address}".encode("utf-8")).hexdigest()[:16]
    return f"wallet-screen-{digest}"


def _label_evidence(label: SovereignRiskLabel) -> str:
    entity = label.entity_name or label.category or "без метки"
    return f"registry:{label.source.value}:{label.chain.value}:{_safe_address(label.address)}:{entity}"


def _findings_from_label(label: SovereignRiskLabel, scope: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    risk_score = label.risk_score or 0.0

    if label.sanctioned:
        findings.append(
            {
                "code": "SANCTIONS_LIST_HIT",
                "severity": "critical",
                "scope": scope,
                "title_ru": "Адрес в перечне 115-ФЗ / санкционном списке",
                "description_ru": (
                    f"Источник: {label.source.value}; "
                    f"ссылка: {label.list_reference or 'Росфинмониторинг, 115-ФЗ'}. "
                    "Операции подлежат обязательному контролю."
                ),
                "evidence": _label_evidence(label),
                "confidence": max(label.confidence, 0.95),
            }
        )

    text = " ".join(
        str(v).lower()
        for v in [label.entity_name, label.category, label.source.value]
        if v
    )
    keyword_hit = next((k for k in HIGH_RISK_KEYWORDS if k in text), None)
    if keyword_hit or risk_score >= 70:
        severity = "critical" if keyword_hit in {"mixer", "tornado", "sanctions", "ofac"} or risk_score >= 85 else "high"
        findings.append(
            {
                "code": "REGISTRY_HIGH_RISK_LABEL",
                "severity": severity,
                "scope": scope,
                "title_ru": "Высокорисковая метка суверенного реестра",
                "description_ru": (
                    f"{label.source.value}: {label.entity_name or label.category or 'метка'}; "
                    f"риск={risk_score:.0f}; уверенность={label.confidence:.0%}."
                ),
                "evidence": _label_evidence(label),
                "confidence": max(label.confidence, 0.65),
            }
        )
    elif label.entity_name or label.category:
        findings.append(
            {
                "code": "REGISTRY_CONTEXT_LABEL",
                "severity": "medium" if risk_score >= 40 else "low",
                "scope": scope,
                "title_ru": "Контекстная метка суверенного реестра",
                "description_ru": f"{label.source.value}: {label.entity_name or label.category}.",
                "evidence": _label_evidence(label),
                "confidence": label.confidence,
            }
        )
    if label.disputed:
        findings.append(
            {
                "code": "REGISTRY_DISPUTED_LABEL",
                "severity": "medium",
                "scope": scope,
                "title_ru": "Спорная метка реестра",
                "description_ru": "Метка оспорена; не перезаписывает суверенную атрибуцию.",
                "evidence": _label_evidence(label),
                "confidence": 0.6,
            }
        )
    return findings


def _findings_from_neighborhood(neighborhood: AddressNeighborhood) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    inbound = len(neighborhood.inbound)
    outbound = len(neighborhood.outbound)
    counterparties = {
        tx.source for tx in neighborhood.inbound if tx.source != neighborhood.address
    } | {tx.target for tx in neighborhood.outbound if tx.target != neighborhood.address}
    if inbound + outbound == 0:
        findings.append(
            {
                "code": "NO_RECENT_ONCHAIN_ACTIVITY",
                "severity": "low",
                "title_ru": "Нет последних on-chain операций у источника",
                "description_ru": "Адаптер не вернул прямые входящие/исходящие операции в заданном лимите.",
                "evidence": f"onchain:{neighborhood.chain.value}:empty",
                "confidence": 0.4,
            }
        )
        return findings
    if inbound >= 10 or outbound >= 10 or len(counterparties) >= 12:
        findings.append(
            {
                "code": "HIGH_FAN_IN_OUT",
                "severity": "high" if max(inbound, outbound) >= 20 else "medium",
                "title_ru": "Адрес похож на хаб / OTC-узел",
                "description_ru": (
                    f"Входящих: {inbound}, исходящих: {outbound}, "
                    f"контрагентов: {len(counterparties)}."
                ),
                "evidence": f"onchain:{neighborhood.chain.value}:fan:{len(counterparties)}",
                "confidence": 0.72,
            }
        )
    if outbound >= 3 and inbound >= 1:
        findings.append(
            {
                "code": "LAYERING_PATTERN",
                "severity": "medium",
                "title_ru": "Признак многоступенчатого рассеивания",
                "description_ru": "У адреса есть входящий поток и несколько исходящих направлений.",
                "evidence": f"onchain:{neighborhood.chain.value}:layering",
                "confidence": 0.62,
            }
        )
    return findings


def _summarize_neighborhood(neighborhood: AddressNeighborhood) -> dict[str, Any]:
    inbound_amount = sum(tx.amount or 0.0 for tx in neighborhood.inbound)
    outbound_amount = sum(tx.amount or 0.0 for tx in neighborhood.outbound)
    counterparties = {
        tx.source for tx in neighborhood.inbound if tx.source != neighborhood.address
    } | {tx.target for tx in neighborhood.outbound if tx.target != neighborhood.address}
    assets = sorted({tx.asset for tx in [*neighborhood.inbound, *neighborhood.outbound] if tx.asset})
    timestamps = [tx.timestamp for tx in [*neighborhood.inbound, *neighborhood.outbound] if tx.timestamp]
    first_activity = min(timestamps) if timestamps else None
    last_activity = max(timestamps) if timestamps else None
    return {
        "chain": neighborhood.chain.value,
        "address": neighborhood.address,
        "address_display": _safe_address(neighborhood.address),
        "inbound_count": len(neighborhood.inbound),
        "outbound_count": len(neighborhood.outbound),
        "counterparties": len(counterparties),
        "counterparty_addresses": sorted(counterparties)[:50],
        "inbound_amount": round(inbound_amount, 8),
        "outbound_amount": round(outbound_amount, 8),
        "assets": assets[:10],
        "first_activity": first_activity,
        "last_activity": last_activity,
        "sample_tx": [
            {
                "hash": tx.tx_hash,
                "direction": "in" if tx.target == neighborhood.address else "out",
                "counterparty": _safe_address(tx.source if tx.target == neighborhood.address else tx.target),
                "asset": tx.asset,
                "amount": tx.amount,
                "timestamp": tx.timestamp,
            }
            for tx in [*neighborhood.inbound[:3], *neighborhood.outbound[:3]]
        ],
    }


def _aggregate_risk(
    findings: list[dict[str, Any]],
    primary_label: SovereignRiskLabel | None,
    counterparty_labels: list[SovereignRiskLabel],
    neighborhood: AddressNeighborhood | None,
) -> float:
    weights = {"critical": 35.0, "high": 24.0, "medium": 12.0, "low": 4.0}
    score = sum(weights.get(str(f.get("severity")), 5.0) * float(f.get("confidence", 0.5)) for f in findings)
    if primary_label and primary_label.sanctioned:
        score = max(score, 96.0)
    if primary_label and primary_label.risk_score is not None:
        score = max(score, primary_label.risk_score * 0.9)
    if counterparty_labels:
        score += min(20.0, 5.0 * len(counterparty_labels))
    if neighborhood and len(neighborhood.inbound) + len(neighborhood.outbound) == 0:
        score = max(score, 8.0)
    return round(min(100.0, score), 1)


def _risk_level(score: float) -> WalletRiskLevel:
    if score >= 80:
        return WalletRiskLevel.CRITICAL
    if score >= 55:
        return WalletRiskLevel.HIGH
    if score >= 25:
        return WalletRiskLevel.MEDIUM
    if score >= 0:
        return WalletRiskLevel.LOW
    return WalletRiskLevel.UNKNOWN


def _confidence(
    source_status: dict[str, str],
    findings: list[dict[str, Any]],
    neighborhood: AddressNeighborhood | None,
) -> float:
    confidence = 0.25
    if source_status.get("onchain") == "ok":
        confidence += 0.3
    if source_status.get("kyt_primary") == "hit":
        confidence += 0.25
    if findings:
        confidence += min(0.2, len(findings) * 0.04)
    if neighborhood and (neighborhood.inbound or neighborhood.outbound):
        confidence += 0.1
    return round(min(1.0, confidence), 2)


def _summary_ru(
    chain: Chain,
    address: str,
    risk_score: float,
    risk_level: WalletRiskLevel,
    findings: list[dict[str, Any]],
) -> str:
    if not findings:
        return (
            f"Адрес {_safe_address(address)} ({chain.value}) проверен. "
            f"Критичных признаков не найдено; риск {risk_score:.0f}/100."
        )
    top = findings[0]
    return (
        f"Адрес {_safe_address(address)} ({chain.value}) проверен. "
        f"Уровень риска: {risk_level.value}, индекс {risk_score:.0f}/100. "
        f"Главный признак: {top.get('title_ru', top.get('code'))}."
    )


def _recommendations(
    risk_level: WalletRiskLevel, findings: list[dict[str, Any]]
) -> list[str]:
    if risk_level in {WalletRiskLevel.CRITICAL, WalletRiskLevel.HIGH}:
        return [
            "Открыть кейс 115-ФЗ и закрепить evidence_chain в материалах проверки.",
            "Проверить входящие/исходящие контрагенты и наличие связи с банковским STR.",
            "Запустить полный OSINT Fusion на суверенных источниках РФ/СНГ и сверить с реестром 115-ФЗ.",
        ]
    if risk_level == WalletRiskLevel.MEDIUM:
        return [
            "Провести ручной triage: контрагенты, суммы, региональные признаки.",
            "Сопоставить адрес с банковским hub и локальным реестром VASP/OTC.",
        ]
    return ["Сохранить результат как baseline и включить адрес в мониторинг при появлении новых сигналов."]


def _limitations(source_status: dict[str, str]) -> list[str]:
    notes = [
        "Результат не содержит ФИО и не является единственным основанием для санкции без проверки аналитиком.",
        "Используются только суверенные источники РФ/СНГ (реестр 115-ФЗ, ФИУ, внутренняя OSINT-разведка).",
    ]
    if source_status.get("onchain", "").startswith("degraded"):
        notes.append("On-chain источник недоступен или вернул ошибку; риск может быть занижен.")
    if source_status.get("registry_primary") == "miss":
        notes.append("Нет прямой метки реестра на адрес; это не доказывает отсутствие риска.")
    return notes
