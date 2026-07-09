"""Корпус открытых OSINT-упоминаний (Telegram, форумы, публичные индексы) для демо и offline-режима."""

from __future__ import annotations

from dataclasses import dataclass

from flowsint_types.fiat_crypto import Chain


@dataclass(frozen=True)
class CorpusMention:
    address: str
    chain: Chain
    source_type: str  # telegram | forum | leak | explorer_tag | darknet_index | otc_board
    source_name: str
    title_ru: str
    excerpt_ru: str
    url: str | None
    risk_tag: str
    confidence: float
    observed_at: str


# Демо-адреса сценариев + адрес из образца SFTY (публичный TRON)
OPEN_OSINT_CORPUS: list[CorpusMention] = [
    CorpusMention(
        "TRU_HUB_MSK", Chain.TRON, "darknet_index", "DNM wallet mirror",
        "Darknet index cross-ref",
        "Индекс DNM-кошельков (публичный зеркальный дамп): TRU_HUB_MSK в связке с USDT-агрегатором.",
        None, "mixer_like", 0.71, "2026-03-18",
    ),
    CorpusMention(
        "TRU_HUB_MSK", Chain.TRON, "telegram", "@OTC_MSK_Gray_USDT",
        "Серый агрегатор СБП→USDT",
        "Кошелёк TRU_HUB_MSK фигурирует как хаб приёма USDT после СБП-переводов. "
        "Fan-out >50 адресов за 24ч.",
        "https://t.me/s/otc_msk_gray_demo", "p2p_exchange", 0.82, "2026-03-15",
    ),
    CorpusMention(
        "TRU_HUB_MSK", Chain.TRON, "forum", "bitcointalk.ru/archive",
        "OTC thread #1842",
        "Упоминание хаба в ветке «USDT Москва без KYC» — адрес в списке реквизитов.",
        None, "otc_exchange", 0.68, "2026-02-20",
    ),
    CorpusMention(
        "TRU_SBP_HUB", Chain.TRON, "leak", "telegram_export_2026_q1",
        "Утечка переписки OTC",
        "Экспорт чата: адрес TRU_SBP_HUB как реквизит для СБП→USDT без идентификации.",
        None, "illegal_service", 0.66, "2026-03-05",
    ),
    CorpusMention(
        "TRU_SBP_HUB", Chain.TRON, "telegram", "@SBP_Crypto_Bridge_RU",
        "СБП→крипто мост",
        "Адрес TRU_SBP_HUB — точка агрегации после массовых СБП-входов.",
        "https://t.me/s/sbp_crypto_bridge", "mixer_like", 0.88, "2026-03-22",
    ),
    CorpusMention(
        "TRU_OFFSHORE_EXIT", Chain.TRON, "telegram", "@Offshore_CEX_Exit",
        "Вывод на offshore CEX",
        "Канал фиксирует выводы с TRU_OFFSHORE_EXIT на нелицензированные площадки.",
        None, "risky_exchange", 0.79, "2026-02-28",
    ),
    CorpusMention(
        "TRU_OFFSHORE_EXIT", Chain.TRON, "explorer_tag", "TronScan community tag",
        "Offshore CEX exit",
        "Публичная метка «offshore exchange withdrawal» на блокчейн-обозревателе.",
        "https://tronscan.org", "exchange", 0.75, "2026-01-10",
    ),
    CorpusMention(
        "TRU_P2P_ENTRY", Chain.TRON, "telegram", "@P2P_RUB_Cash_USDT",
        "P2P RUB вход",
        "Реквизиты для приёма RUB→USDT, адрес в закрепе канала.",
        None, "p2p_exchange", 0.71, "2026-03-01",
    ),
    CorpusMention(
        "TZGiyUbaNYSsCSszbYj6cxUgw3d5wmTGnz", Chain.TRON, "telegram", "@OTC_TRC20_RU",
        "TRC-20 transit wallet",
        "Адрес в переписке OTC-деска как транзитный перед выводом на Bitget.",
        None, "risky_exchange", 0.64, "2026-03-27",
    ),
    CorpusMention(
        "TZGiyUbaNYSsCSszbYj6cxUgw3d5wmTGnz", Chain.TRON, "forum", "crypto_scam_watch",
        "Scam watch mention",
        "Упоминание в списке «подозрительные транзитные TRC-20» без подтверждения суда.",
        None, "other", 0.45, "2026-02-14",
    ),
    CorpusMention(
        "TZGiyUbaNYSsCSszbYj6cxUgw3d5wmTGnz", Chain.TRON, "explorer_tag", "TronScan",
        "High activity EOA",
        "Публичный профиль: высокая активность USDT, множество контрагентов.",
        "https://tronscan.org", "wallet", 0.55, "2026-04-01",
    ),
    CorpusMention(
        "bc1q_hub_msk_demo", Chain.BTC, "telegram", "@BTC_OTC_MSK",
        "BTC OTC Москва",
        "bc1q_hub_msk_demo в списке кошельков для приёма BTC OTC.",
        None, "otc_exchange", 0.70, "2026-03-10",
    ),
    CorpusMention(
        "0xHUB_MSK_DEMO", Chain.ETH, "leak", "pastebin_mirror_2026",
        "Утечка списка OTC ETH",
        "Адрес в утёкшем CSV «gray_eth_desks_q1» — требует верификации.",
        None, "illegal_service", 0.52, "2026-01-28",
    ),
]

# Публичные индикаторы риска (общеизвестные паттерны, не персональные данные)
PUBLIC_RISK_PATTERNS: list[tuple[str, str, float]] = [
    ("mixer", "Поведенческий паттерн peel-chain / split-merge", 0.35),
    ("sanctions", "Совпадение с публичным списком OFAC-style (справочно)", 0.25),
    ("ransomware", "Эвристика: транзитный кошелёк с высоким fan-out", 0.20),
]
