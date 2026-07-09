"""Parse address lists from CSV / JSONL uploads."""

from __future__ import annotations

import csv
import io
import json


def parse_address_rows(content: bytes, *, filename: str = "") -> list[dict[str, str]]:
    text = content.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return []
    lower = filename.lower()
    if lower.endswith((".json", ".jsonl", ".ndjson")):
        rows: list[dict[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append({"address": str(obj["address"]), "chain": str(obj.get("chain") or "tron")})
        return rows
    delimiter = "\t" if "\t" in text.splitlines()[0] else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for row in reader:
        addr = (row.get("address") or row.get("Address") or row.get("wallet") or "").strip()
        if not addr:
            continue
        chain = (row.get("chain") or row.get("Chain") or "tron").strip().lower()
        rows.append({"address": addr, "chain": chain})
    return rows
