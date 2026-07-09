# BlockSci co-spend methodology — account-model adaptation

BlockSci clusters **UTXO** addresses that appear as inputs in the same transaction (common-input-ownership heuristic). FinSkalp operates primarily on **account-based** chains (TRON, ETH, BSC, Polygon). This document maps BlockSci concepts to FinSkalp heuristics in `attribution/cospend_cluster.py`.

## UTXO (BlockSci native)

| BlockSci signal | Confidence | FinSkalp |
|-----------------|------------|----------|
| Same tx, multiple input addresses | High (same wallet) | `chain == "btc"` — group `from` per `tx_hash` |
| Change output heuristic | Medium | Not implemented (BTC depth-1 only) |

## Account-model equivalents

| Heuristic | Chains | Tier | Rationale |
|-----------|--------|------|-----------|
| **Shared funder** — many addresses receive from same `from` in overlapping window | TRON, all EVM | Tier 2 (0.65–0.75) | Batch payouts from OTC/hub |
| **Contract + method + block window** — recipients of calls from same contract with same `method_id` within ±N blocks | ETH, BSC, Polygon | Tier 2 (0.70–0.80) | Distributor contracts, airdrops, mixer exits |
| **Same tx batch** — multiple `to` in one native tx (rare on EVM) | EVM | Tier 2 (0.75) | Multisend contracts |

## ETH contract+method clustering (implemented)

For `chain in ("eth", "bsc", "polygon")`:

1. Index outbound transfers with `contract` (caller) + `method_id` + `block_number`.
2. Group recipients sharing `(contract, method_id)` where `max(block) - min(block) ≤ block_window` (default **3**).
3. Clusters with ≥2 recipients → co-spend set; propagate labels via `propagate_cluster_labels`.

## Confidence tiers

| Tier | Source | Confidence cap | Use |
|------|--------|----------------|-----|
| 1 | Sanctions / registry | 0.95+ | Legal filing |
| 2 | Co-spend cluster | 0.75 | Investigation lead |
| 3 | Heuristic corridor | 0.55 | Triage only |

Label propagation: `confidence = min(0.75, seed.confidence × 0.85)` — never upgrades Tier-1 seeds.

## Limits (honest)

- Account chains do **not** prove common ownership as strongly as UTXO co-spend.
- Contract batching (DEX routers, bridges) creates **false positive** clusters — analyst review required.
- No stolen label databases; clusters use only live transfers + sovereign `entity_labels`.

## References

- BlockSci paper: common-input-ownership (Bitcoin)
- FinSkalp: `build_cospend_clusters`, `propagate_cluster_labels`, `tests/test_cospend_account_model.py`
