"""Tests for account-model co-spend clustering (BlockSci adaptation)."""

from flowsint_crypto_compliance.attribution.cospend_cluster import build_cospend_clusters


def test_evm_contract_method_cluster_within_block_window():
    transfers = [
        {
            "from": "0xcontract",
            "to": "0xaaa",
            "contract": "0xcontract",
            "method_id": "0xa9059cbb",
            "block_number": 100,
            "tx_hash": "0x1",
        },
        {
            "from": "0xcontract",
            "to": "0xbbb",
            "contract": "0xcontract",
            "method_id": "0xa9059cbb",
            "block_number": 101,
            "tx_hash": "0x2",
        },
        {
            "from": "0xcontract",
            "to": "0xccc",
            "contract": "0xcontract",
            "method_id": "0xa9059cbb",
            "block_number": 120,
            "tx_hash": "0x3",
        },
    ]
    clusters = build_cospend_clusters(transfers, chain="eth", block_window=3)
    assert any({"0xaaa", "0xbbb"}.issubset(c) for c in clusters)


def test_tron_shared_funder_cluster():
    transfers = [
        {"from": "THub", "to": "Ta", "tx_hash": "1"},
        {"from": "THub", "to": "Tb", "tx_hash": "2"},
    ]
    clusters = build_cospend_clusters(transfers, chain="tron")
    assert any("THub" in c and "Ta" in c and "Tb" in c for c in clusters)


def test_btc_utxo_cospend():
    transfers = [
        {"from": "1Alice", "tx_hash": "tx1"},
        {"from": "1Bob", "tx_hash": "tx1"},
    ]
    clusters = build_cospend_clusters(transfers, chain="btc")
    assert {"1Alice", "1Bob"} in clusters
