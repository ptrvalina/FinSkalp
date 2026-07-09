# Blockscout self-hosted stack (optional)

FinSkalp uses Blockscout's Etherscan-compatible REST API for ETH, BSC, and Polygon live collectors. Public endpoints are defaults; this compose is for **on-prem / sovereign** due diligence.

## Requirements

- Docker Compose v2
- External chain RPC (Geth/Erigon for ETH, or Polygon/BSC RPC) — Blockscout indexes from JSON-RPC
- Disk: chain-dependent (100GB+ for ETH archive)

## Quick start

```bash
cd flowsint-crypto-compliance
# Copy and edit env — set BLOCKSCOUT_ETHEREUM_RPC_URL to your node
docker compose -f docker/docker-compose.blockscout.yml --profile blockscout up -d
```

After indexer catches up (~hours to days depending on chain):

```env
FINSKALP_BLOCKSCOUT_ETH_URL=http://localhost:4000/api
FINSKALP_BLOCKSCOUT_BSC_URL=http://localhost:4001/api
FINSKALP_BLOCKSCOUT_POLYGON_URL=http://localhost:4002/api
```

## Services

| Service | Port | Role |
|---------|------|------|
| `blockscout-db` | 5432 (internal) | Postgres metadata |
| `blockscout-redis` | 6379 (internal) | Cache / queues |
| `blockscout` | 4000 | API + UI |

## Notes

- Not required for CI or demo laptop — use `*.blockscout.com` public APIs.
- Full production deploy: [Blockscout docker-compose deployment](https://docs.blockscout.com/setup/deployment/docker-compose-deployment)
- This stack is a **minimal template**; point `ETHEREUM_JSONRPC_HTTP_URL` at your sovereign node before regulator-grade use.
