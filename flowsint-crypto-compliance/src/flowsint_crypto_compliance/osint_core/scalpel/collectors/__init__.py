"""Коллекторы FinSkalp Scalpel."""

from flowsint_crypto_compliance.osint_core.scalpel.collectors.blockchain_explorer import (
    BlockchainExplorerCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.clearnet_intel import (
    ClearnetIntelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.corpus_telegram import (
    CorpusTelegramCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.darknet_tor import (
    DarknetTorCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.maigret_ext import (
    MaigretExtCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.open_intel_feeds import (
    DnsWhoisCollector,
    MempoolBtcCollector,
    OpenSanctionsCollector,
    TronGridPublicCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.paste_leak import (
    PasteLeakCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.spiderfoot_ext import (
    SpiderFootExtCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.username_probe import (
    UsernameProbeCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.vasp_registry import (
    VaspRegistryCollector,
)

ALL_COLLECTORS = [
    CorpusTelegramCollector,
    VaspRegistryCollector,
    BlockchainExplorerCollector,
    TronGridPublicCollector,
    MempoolBtcCollector,
    OpenSanctionsCollector,
    ClearnetIntelCollector,
    PasteLeakCollector,
    UsernameProbeCollector,
    MaigretExtCollector,
    SpiderFootExtCollector,
    DnsWhoisCollector,
    DarknetTorCollector,
]

__all__ = [
    "ALL_COLLECTORS",
    "BlockchainExplorerCollector",
    "ClearnetIntelCollector",
    "CorpusTelegramCollector",
    "DarknetTorCollector",
    "DnsWhoisCollector",
    "MaigretExtCollector",
    "MempoolBtcCollector",
    "OpenSanctionsCollector",
    "PasteLeakCollector",
    "SpiderFootExtCollector",
    "TronGridPublicCollector",
    "UsernameProbeCollector",
    "VaspRegistryCollector",
]
