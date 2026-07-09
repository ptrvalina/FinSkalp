#!/usr/bin/env bash
# FinSkalp — bootstrap sovereign java-tron FullNode (Linux/macOS)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> FinSkalp sovereign TRON setup"
echo "    See docker/tron-fullnode/README.md for snapshot download."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker required" >&2
  exit 1
fi

DATA_DIR="${FINSKALP_TRON_DATA:-./tron-data/output-directory}"
mkdir -p "$DATA_DIR"

echo "==> Starting java-tron compose (ports 8090/18888)"
docker compose -f docker/docker-compose.tron-fullnode.yml up -d

echo "==> Waiting for HTTP API (max 120s)..."
for i in $(seq 1 24); do
  if curl -sf -X POST "http://127.0.0.1:8090/wallet/getnowblock" -d '{}' >/dev/null 2>&1; then
    echo "    Node HTTP is up."
    break
  fi
  sleep 5
done

echo "==> Health + snapshot gate"
uv run python scripts/tron_node_health.py || python scripts/tron_node_health.py

echo ""
echo "Set in .env:"
echo "  FINSKALP_TRON_PROVIDER=failover"
echo "  FINSKALP_TRON_SOVEREIGN_URL=http://127.0.0.1:8090"
echo "Verify: curl http://localhost:8877/api/infra/tron-node"
