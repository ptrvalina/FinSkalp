from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowsint_types.fiat_crypto import (
    BankRegulatorFeed,
    Chain,
    ControlPurchaseEvent,
    EvidenceSource,
    FiatLegEvent,
    LicensedPlatformEvent,
    RegistrySource,
    SovereignRiskLabel,
)


@dataclass(frozen=True)
class DemoScenario:
    id: str
    title_ru: str
    description_ru: str
    case_ref: str
    bank_feeds: list[BankRegulatorFeed]
    licensed_events: list[LicensedPlatformEvent]
    control_purchases: list[ControlPurchaseEvent]
    registry_labels: list[SovereignRiskLabel]
    fiat_events: list[FiatLegEvent]


SCENARIOS: dict[str, DemoScenario] = {}


def _register(s: DemoScenario) -> DemoScenario:
    SCENARIOS[s.id] = s
    return s


_register(
    DemoScenario(
        id="p2p_rub_offshore",
        title_ru="P2P рубли → серый OTC → офшорный CEX",
        description_ru=(
            "STR Сбера на 2.5 млн ₽. Контрольная закупка P2P. След уходит через "
            "московский hub-кошелёк на адрес, размеченный суверенным реестром как офшорный CEX-вывод."
        ),
        case_ref="DEMO-RU-001",
        bank_feeds=[
            BankRegulatorFeed(
                feed_id="str-sber-2026-001",
                bank_name="Сбер",
                bank_bic="SABRRUMM",
                alert_type="crypto_suspicion",
                region="RU",
                currency="RUB",
                amount=2_500_000,
                subject_id="subj-demo-001",
                case_id="DEMO-RU-001",
                observed_at="2026-06-15T14:30:00Z",
            )
        ],
        licensed_events=[
            LicensedPlatformEvent(
                event_id="vasp-ru-1",
                platform_name="RU_Licensed_VASP",
                platform_license_id="RU-VASP-0042",
                region="RU",
                direction="deposit",
                chain=Chain.TRON,
                address="TRU_OFFSHORE_EXIT",
                amount_fiat=2_450_000,
                amount_crypto=25000,
                asset="USDT",
                currency="RUB",
            )
        ],
        control_purchases=[
            ControlPurchaseEvent(
                event_id="cp-demo-001",
                operator_ref="unit-alpha",
                region="RU",
                channel="p2p_rub",
                chain=Chain.TRON,
                source_address="TRU_P2P_ENTRY",
                target_address="TRU_GRAY_A",
                amount_fiat=50_000,
                currency="RUB",
                asset="USDT",
                notes="Контрольная P2P покупка USDT за рубли",
            )
        ],
        registry_labels=[
            SovereignRiskLabel(
                label_id="reg-cex-exit-1",
                source=RegistrySource.INTERNAL_OSINT,
                chain=Chain.TRON,
                address="TRU_OFFSHORE_EXIT",
                entity_name="Офшорный CEX-вывод",
                category="cex",
                confidence=0.82,
            ),
            SovereignRiskLabel(
                label_id="reg-otc-hub-1",
                source=RegistrySource.INTERNAL_OSINT,
                chain=Chain.TRON,
                address="TRU_HUB_MSK",
                category="otc",
                confidence=0.65,
            ),
        ],
        fiat_events=[],
    )
)

_register(
    DemoScenario(
        id="cis_transit_kz",
        title_ru="Транзит СНГ: РФ → Казахстан",
        description_ru=(
            "ВТБ фиксирует подозрительный перевод. OTC РФ → цепочка транзитных кошельков → "
            "локальная площадка KZ. Коридор RU→KZ→TR."
        ),
        case_ref="DEMO-RU-002",
        bank_feeds=[
            BankRegulatorFeed(
                feed_id="str-vtb-2026-002",
                bank_name="ВТБ",
                bank_bic="VTBRRUMM",
                alert_type="cross_border",
                region="RU",
                currency="RUB",
                amount=890_000,
                subject_id="subj-demo-002",
                case_id="DEMO-RU-002",
                observed_at="2026-06-18T09:00:00Z",
            )
        ],
        licensed_events=[
            LicensedPlatformEvent(
                event_id="kz-dep-1",
                platform_name="KZ_Local_Exchange",
                region="KZ",
                direction="deposit",
                chain=Chain.TRON,
                address="TKZ_LOCAL_EXIT",
                amount_fiat=4_200_000,
                asset="USDT",
                amount_crypto=15000,
                currency="KZT",
            )
        ],
        control_purchases=[
            ControlPurchaseEvent(
                event_id="cp-demo-002",
                operator_ref="unit-beta",
                region="RU",
                channel="otc_telegram",
                chain=Chain.TRON,
                target_address="TRU_OTC_RU",
                amount_fiat=30_000,
                currency="RUB",
            )
        ],
        registry_labels=[],
        fiat_events=[],
    )
)

_register(
    DemoScenario(
        id="cross_border_do",
        title_ru="Трансгран: рубли → Карибы (Доминикана)",
        description_ru=(
            "Классический след обхода: P2P в РФ, layering на TRON, выход на "
            "лицензированную площадку в DO."
        ),
        case_ref="DEMO-RU-003",
        bank_feeds=[
            BankRegulatorFeed(
                feed_id="str-tink-2026-003",
                bank_name="Тинькофф",
                alert_type="p2p_suspicion",
                region="RU",
                currency="RUB",
                amount=420_000,
                subject_id="subj-demo-003",
                case_id="DEMO-RU-003",
                observed_at="2026-06-20T16:45:00Z",
            )
        ],
        licensed_events=[
            LicensedPlatformEvent(
                event_id="do-dep-1",
                platform_name="DO_Local_CEX",
                region="DO",
                direction="deposit",
                chain=Chain.TRON,
                address="TDO_CEX_EXIT",
                asset="USDT",
                amount_crypto=8000,
            )
        ],
        control_purchases=[
            ControlPurchaseEvent(
                event_id="cp-demo-003",
                operator_ref="unit-gamma",
                region="RU",
                channel="p2p_rub",
                chain=Chain.TRON,
                source_address="TRU_P2P_RU2",
                target_address="TRU_LAYER_1",
                amount_fiat=35_000,
                currency="RUB",
            )
        ],
        registry_labels=[],
        fiat_events=[],
    )
)

_register(
    DemoScenario(
        id="sbp_gray_hub",
        title_ru="СБП → серый hub (массовый fan-out)",
        description_ru=(
            "Быстрый платёж СБП на P2P-мерчанта. Hub-кошелёк с аномальным "
            "fan-in/fan-out — признак нелегального OTC-агрегатора."
        ),
        case_ref="DEMO-RU-004",
        bank_feeds=[
            BankRegulatorFeed(
                feed_id="str-alfa-2026-004",
                bank_name="Альфа-Банк",
                alert_type="STR",
                region="RU",
                currency="RUB",
                amount=500_000,
                payment_reference="hash:sbp-ref-demo-004",
                linked_crypto_address="TRU_SBP_HUB",
                linked_chain=Chain.TRON,
                subject_id="subj-demo-004",
                case_id="DEMO-RU-004",
                observed_at="2026-06-22T11:20:00Z",
            )
        ],
        licensed_events=[],
        control_purchases=[],
        registry_labels=[
            SovereignRiskLabel(
                label_id="reg-mixer-flag",
                source=RegistrySource.ROSFINMONITORING,
                chain=Chain.TRON,
                address="TRU_SBP_DST_0",
                category="mixer",
                entity_name="Криптомиксер (перечень 115-ФЗ)",
                sanctioned=True,
                list_reference="Росфинмониторинг, перечень 115-ФЗ",
                confidence=0.9,
            ),
        ],
        fiat_events=[],
    )
)


def list_scenarios() -> list[dict[str, str]]:
    return [
        {
            "id": s.id,
            "title_ru": s.title_ru,
            "description_ru": s.description_ru,
            "case_ref": s.case_ref,
        }
        for s in SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> DemoScenario:
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {scenario_id}")
    return SCENARIOS[scenario_id]
