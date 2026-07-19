# FinSkalp — Golden Path Checklist

Demo operator: `analyst@example.com` / `FinSkalp2026!`

**Client UI:** http://localhost:5173 — do **not** send clients to `:8877`.

## API smoke (automated)

```powershell
# Stack must be up (docker compose -f docker-compose.dev.yml up -d)
powershell -File scripts/golden-collect-graph-kyt.ps1
```

Expected: Health → Login → Create case → Scalpel → Merge graph → KYT → Graph GET.

## Manual UI walkthrough

1. **Login** — Stitch secure gateway, void `#0b141c`
2. **Mission Control** — `/dashboard/fusion`, queue visible or empty state
3. **Collect** — seed wallet `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`, run collectors
4. **Investigation** — Case Command Bar, pipeline chips, graph renders
5. **Systems HUD** — Scalpel / Visualizer / Risk Logic on graph
6. **Entity panel** — select node, 2×2 stats grid
7. **Brief lens** — executive summary overlay
8. **Report Center** — `/dashboard/fusion/reports/$caseRef`, export PDF/XLSX/115-ФЗ
9. **Platform** — Vault / Flows / Enrichers share Graph OS chrome

## Demo seed (if login fails)

```bash
docker exec flowsint-api-dev python -m app.bootstrap_demo_user
```

## Client preview (optional)

```powershell
powershell -File scripts/client-preview.ps1
```

Uses named Cloudflare tunnel when `$env:CF_TUNNEL_NAME` is set.
