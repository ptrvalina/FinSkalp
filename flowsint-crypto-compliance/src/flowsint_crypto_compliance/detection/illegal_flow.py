from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding
from flowsint_crypto_compliance.engine.xgboost_risk import SovereignRiskModel
from flowsint_types.fiat_crypto import FiatCryptoBridge, FusedAttribution

CIS_ORIGIN = frozenset({"RU", "BY", "KZ", "KG", "UZ", "TJ", "AM", "AZ", "MD", "GE"})
OFFSHORE_REGIONS = frozenset({"AE", "TR", "DO", "PA", "SC", "VG", "CY", "SG", "HK", "US", "EU"})
MIXER_KEYWORDS = frozenset({"mixer", "tornado", "blender", "sanctions", "scam", "ransomware"})


class IllegalFlowDetector:
    """
    Выявление признаков нелегального движения денег и ценностей (РФ / СНГ).

    Работает на результатах fusion на суверенных источниках РФ/СНГ
    (банковский хаб, контрольные закупки, реестр риск-меток 115-ФЗ, on-chain эвристики).
    Финальный индекс риска дополняется XGBoost-моделью типологий 115-ФЗ.
    """

    def __init__(self, *, use_xgboost: bool = True, flag_context: Any | None = None) -> None:
        from flowsint_crypto_compliance.infrastructure.feature_flags import FlagContext, get_feature_flags

        self._flags = get_feature_flags()
        self._ctx = flag_context if isinstance(flag_context, FlagContext) else FlagContext()
        self._v2 = self._flags.is_enabled("finskalp.illegal_flow_detector_v2", self._ctx)
        self._xgboost_v2 = self._flags.is_enabled("finskalp.xgboost_scoring_v2", self._ctx)
        self._funnel = self._flags.is_enabled("finskalp.funnel_consolidation", self._ctx)
        self._risk_model = SovereignRiskModel() if use_xgboost else None

    def analyze(
        self,
        *,
        attributions: list[FusedAttribution],
        bridges: list[FiatCryptoBridge],
        bank_feed_count: int = 0,
        control_purchase_count: int = 0,
    ) -> tuple[list[IllegalFlowFinding], float, dict[str, object]]:
        findings: list[IllegalFlowFinding] = []

        for attr in attributions:
            findings.extend(self._analyze_attribution(attr))
        findings.extend(self._analyze_bridges(bridges, attributions))
        if bank_feed_count and control_purchase_count:
            findings.append(
                IllegalFlowFinding(
                    severity="high",
                    code="BANK_CONTROL_CORROBORATION",
                    title_ru="Банковский STR подтверждён контрольной закупкой",
                    description_ru=(
                        "Сигнал банка (115-ФЗ) склеен с on-chain следом через "
                        "оперативное заземление P2P/OTC канала."
                    ),
                    confidence=0.9,
                    evidence=[f"bank_feeds:{bank_feed_count}", f"control_purchases:{control_purchase_count}"],
                )
            )

        heuristic_score = self._aggregate_score(findings)
        if self._funnel and heuristic_score >= 40:
            heuristic_score = round(min(100.0, heuristic_score * 1.08), 1)
        if self._v2 and heuristic_score >= 25:
            heuristic_score = round(min(100.0, heuristic_score * 1.05), 1)
        risk_meta: dict[str, object] = {
            "heuristic_score": heuristic_score,
            "flags": {
                "illegal_flow_v2": self._v2,
                "funnel_consolidation": self._funnel,
                "xgboost_v2": self._xgboost_v2,
            },
        }
        if self._risk_model:
            ml = self._risk_model.score_case(
                findings=findings,
                attributions=attributions,
                bridges=bridges,
                bank_feed_count=bank_feed_count,
                control_purchase_count=control_purchase_count,
                heuristic_score=heuristic_score,
            )
            risk_meta["xgboost"] = {
                "model_version": ml.model_version,
                "model_score": ml.model_score,
                "blended_score": ml.score,
                "features": ml.features,
                "v2": self._xgboost_v2,
            }
            score = ml.score
            if self._xgboost_v2:
                score = round(min(100.0, score * 1.02), 1)
            return findings, score, risk_meta
        return findings, heuristic_score, risk_meta

    def _analyze_attribution(self, attr: FusedAttribution) -> list[IllegalFlowFinding]:
        findings: list[IllegalFlowFinding] = []
        region = (attr.primary_region or "").upper()

        if attr.black_zone:
            findings.append(
                IllegalFlowFinding(
                    severity="critical",
                    code="BLACK_ZONE_LAYERING",
                    title_ru="Чёрная зона: структурное размывание следа",
                    description_ru=(
                        f"Адрес {attr.address[:16]}… демонстрирует признаки "
                        "layering/hub — типично для нелегального вывода ценностей."
                    ),
                    addresses=[attr.address],
                    confidence=min(1.0, attr.confidence + 0.2),
                    evidence=attr.evidence_chain or [],
                )
            )

        if attr.sanctioned:
            findings.append(
                IllegalFlowFinding(
                    severity="critical",
                    code="SANCTIONS_LIST_HIT",
                    title_ru="Адрес в перечне 115-ФЗ / санкционном списке",
                    description_ru=(
                        f"Адрес {attr.address[:16]}… числится в официальном перечне "
                        f"({attr.list_reference or 'Росфинмониторинг, 115-ФЗ'}). "
                        "Операции подлежат обязательному контролю и блокировке."
                    ),
                    addresses=[attr.address],
                    confidence=max(attr.confidence, 0.95),
                    evidence=attr.evidence_chain or [],
                )
            )

        if attr.watchlist_label and region in CIS_ORIGIN:
            severity = "high" if attr.gray_zone else "medium"
            findings.append(
                IllegalFlowFinding(
                    severity=severity,
                    code="GRAY_CEX_TRANSIT",
                    title_ru="Серый транзит через инфраструктуру CEX",
                    description_ru=(
                        f"Источник {region}, метка реестра «{attr.watchlist_label}» "
                        f"({attr.label_source or 'суверенный реестр'}). "
                        "Вероятен нелегальный P2P/OTC вывод с транзитом через CEX."
                    ),
                    addresses=[attr.address],
                    confidence=max(attr.confidence, 0.6),
                    evidence=attr.evidence_chain or [],
                )
            )

        if attr.linkage_strength and attr.linkage_strength >= 0.5 and region in CIS_ORIGIN:
            findings.append(
                IllegalFlowFinding(
                    severity="high",
                    code="FIAT_CRYPTO_LINK_RF",
                    title_ru="Склейка фиат (РФ) ↔ крипто установлена",
                    description_ru=(
                        f"Банковский/регуляторный сигнал привязан к адресу с силой связи "
                        f"{attr.linkage_strength:.0%}. Вероятный канал обналичивания/вывода."
                    ),
                    addresses=[attr.address],
                    confidence=attr.linkage_strength,
                    evidence=attr.evidence_chain or [],
                )
            )

        if attr.watchlist_label:
            label_lower = attr.watchlist_label.lower()
            if any(k in label_lower for k in MIXER_KEYWORDS):
                findings.append(
                    IllegalFlowFinding(
                        severity="critical",
                        code="MIXER_EXPOSURE",
                        title_ru="Контакт с миксером / санкционным контуром",
                        description_ru=(
                            f"Реестр риск-меток: {attr.label_source or 'суверенный реестр'} → "
                            f"{attr.watchlist_label}. Требует приоритетной проверки."
                        ),
                        addresses=[attr.address],
                        confidence=0.85,
                    evidence=attr.evidence_chain or [],
                )
            )
            elif region in CIS_ORIGIN:
                pass  # GRAY_CEX handled above

        if attr.disputed and attr.watchlist_label:
            findings.append(
                IllegalFlowFinding(
                    severity="medium",
                    code="DISPUTED_ENTITY_LABEL",
                    title_ru="Спорная атрибуция: метка реестра оспорена",
                    description_ru=(
                        f"Реестр указывает «{attr.watchlist_label}», но метка оспорена. "
                        "Суверенный след (РФ) имеет приоритет — возможен серый субаккаунт/OTC."
                    ),
                    addresses=[attr.address],
                    confidence=0.7,
                )
            )

        return findings

    def _analyze_bridges(
        self,
        bridges: list[FiatCryptoBridge],
        attributions: list[FusedAttribution],
    ) -> list[IllegalFlowFinding]:
        findings: list[IllegalFlowFinding] = []
        for bridge in bridges:
            origin = (bridge.region_origin or "").upper()
            dest = (bridge.region_destination or "").upper()
            if origin in CIS_ORIGIN and dest in OFFSHORE_REGIONS:
                findings.append(
                    IllegalFlowFinding(
                        severity="high",
                        code="CROSS_BORDER_OFFSHORE",
                        title_ru=f"Трансграничный вывод: {origin} → {dest}",
                        description_ru=(
                            "Зафиксирован след вывода ценностей из СНГ в офшорную/иностранную "
                            f"юрисдикцию ({dest}). Уверенность моста: {bridge.confidence:.0%}."
                        ),
                        addresses=[a for a in [bridge.entry_address, bridge.exit_address] if a],
                        confidence=bridge.confidence,
                        evidence=bridge.evidence or [],
                    )
                )
            if origin == "RU" and bridge.hop_count and bridge.hop_count >= 3:
                findings.append(
                    IllegalFlowFinding(
                        severity="medium",
                        code="RU_LAYERING_CHAIN",
                        title_ru="Многоступенчатое перемещение из РФ",
                        description_ru=(
                            f"От {bridge.hop_count} on-chain переходов от точки входа. "
                            "Типичный паттерн обхода комплаенса."
                        ),
                        addresses=[bridge.exit_address] if bridge.exit_address else [],
                        confidence=bridge.confidence,
                        evidence=bridge.evidence or [],
                    )
                )
        return findings

    def _aggregate_score(self, findings: list[IllegalFlowFinding]) -> float:
        if not findings:
            return 0.0
        weights = {"critical": 35, "high": 25, "medium": 12, "low": 5}
        raw = sum(weights.get(f.severity, 10) * f.confidence for f in findings)
        return round(min(100.0, raw), 1)
