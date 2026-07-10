#!/usr/bin/env python3
"""Download Google Stitch screen HTML + PNG for FinSkalp redesign reference.

Requires: STITCH_API_KEY (or GOOGLE_STITCH_API_KEY) from https://stitch.withgoogle.com

Usage:
  cd flowsint-crypto-compliance
  set STITCH_API_KEY=your-key
  uv run python scripts/fetch_stitch_screens.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ID = "4653582392684471060"

SCREENS: list[tuple[str, str, str]] = [
    ("platform-modules", "efffcb9d42674c0fafb3521c4f060ce8", "Platform Modules | IC-Catalog v2.4"),
    ("ic-console", "0ce8137af34e4c8796ab057d42ef827c", "IC Console | Tactical Instrumentation"),
    ("finskalp-product-map", "525b6c9cb96f40a3b89fd4bcb9e2817a", "FinSkalp Product Map"),
    ("registries", "f28def9806124dbd9601097f5921bbbe", "Registries | CIS Banking & VASP Hub"),
    ("regulatory-reporting", "b54d7aa8493649c292452887fb5b2184", "Regulatory Reporting | 115-FZ Filing Center"),
    ("compliance-case-lifecycle", "739963f35a024c2791dddf0c7d3573be", "Compliance 115-FZ | Case Lifecycle Manager"),
    ("flow-architect", "88b87a9f19ea46c0989c0a5a3a770728", "Flow Architect | Forensic Pipeline Editor"),
    ("secure-gateway", "477ede7f4d914f3e969ac901163c5955", "FinSkalp Enterprise | Secure Gateway"),
    ("vault", "90a7fe72ef554945bbdd200c84130d5b", "The Vault | Sovereign Secret Management"),
    ("system-telemetry", "f8eb2d4da37b4858b401d11f8e91e79c", "System Telemetry | Sovereign Node Status"),
    ("investigation-workspace", "87c385fd2e4842f08acff830a6bda7b9", "Investigation Workspace | CASE-2024-8842"),
    ("osint-fusion-hub", "1d8ca124a63b40b5b5e6dc14ac822120", "OSINT Fusion Hub | Scalpel Collector"),
    ("command-center", "c3dbb844aa6941f496c0c342861e378f", "Command Center | Global Operations Terminal"),
    ("microservices-mesh", "2702aa51df964483a7f81f63ba36b3ed", "Microservices Mesh | System Topology"),
    ("forensic-toolset", "f4fe7230fa1348c69ca978b6b039f305", "Forensic Toolset | OSINT & Intelligence Catalog"),
    ("wallet-explorer", "202daa3cf1944ebfb810fb1f4611f346", "Wallet Explorer | Deep Forensic Analysis & KYT"),
    ("command-center-v4", "a834a977dde74449a82b8d769df5b0c4", "Global Operations Terminal | Command Center v4.0.2"),
    ("api-integration-status", "d0cb5702c96a467898021f064c9c46d1", "API Integration Status | Platform v2 Hub"),
    ("user-profile", "4933a19ec28f43d4b1ad967be7e0b625", "User Profile | Sovereign Operator SEC-OP-8821"),
    ("knowledge-graph-explorer", "e20abf1655a04c9ea717acc2dc8abb2a", "Knowledge Graph Explorer | Force-Directed Analysis"),
    ("schema-architect", "d596451be089436da9ad02a7c94bde2f", "Schema Architect | Custom Entity Type Editor"),
    ("investigation-briefing", "1d8acac256fa4f33909cad4f89882ac5", "Investigation Briefing | CASE-2024-8842"),
]

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "stitch"
MCP_URL = "https://stitch.googleapis.com/mcp"


def _api_key() -> str:
    key = os.getenv("STITCH_API_KEY") or os.getenv("GOOGLE_STITCH_API_KEY") or ""
    if not key.strip():
        print("ERROR: set STITCH_API_KEY or GOOGLE_STITCH_API_KEY", file=sys.stderr)
        sys.exit(1)
    return key.strip()


def _mcp_call(api_key: str, tool: str, arguments: dict) -> dict:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    ).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Goog-Api-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if "error" in payload:
        raise RuntimeError(payload["error"])
    result = payload.get("result") or {}
    if isinstance(result.get("content"), list):
        for block in result["content"]:
            if block.get("type") == "text":
                return json.loads(block["text"])
    return result


def _download(url: str, dest: Path, api_key: str) -> None:
    req = urllib.request.Request(url, headers={"X-Goog-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    api_key = _api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_lines = ["# FinSkalp Stitch screens", f"Project: {PROJECT_ID}", ""]
    ok = 0
    for slug, screen_id, title in SCREENS:
        print(f"Fetching {slug} …")
        try:
            screen = _mcp_call(
                api_key,
                "get_screen",
                {
                    "name": f"projects/{PROJECT_ID}/screens/{screen_id}",
                    "projectId": PROJECT_ID,
                    "screenId": screen_id,
                },
            )
            result = screen.get("result") or screen
            html_url = (result.get("htmlCode") or {}).get("downloadUrl")
            shot_url = (result.get("screenshot") or {}).get("downloadUrl")
            if html_url:
                _download(html_url, OUT_DIR / f"{slug}.html", api_key)
            if shot_url:
                shot = shot_url if "=s" in shot_url else f"{shot_url}=s1280"
                _download(shot, OUT_DIR / f"{slug}.png", api_key)
            index_lines.append(f"- [{title}]({slug}.html) · `{screen_id}`")
            ok += 1
        except (urllib.error.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"  FAIL {slug}: {exc}", file=sys.stderr)
            index_lines.append(f"- ~~{title}~~ FAILED: {exc}")
    (OUT_DIR / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Done: {ok}/{len(SCREENS)} screens → {OUT_DIR}")


if __name__ == "__main__":
    main()
