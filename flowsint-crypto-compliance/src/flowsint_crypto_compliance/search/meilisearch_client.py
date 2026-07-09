"""Meilisearch full-text search for cases, wallets, VASP, СОО."""

from __future__ import annotations

import os
from typing import Any


INDEX_NAME = "finskalp_global"


class SearchClient:
    def __init__(self) -> None:
        self._client = None
        self._url = os.getenv("MEILI_URL", "http://localhost:7700")
        self._key = os.getenv("MEILI_MASTER_KEY", "finskalp-dev-key")
        self._init()

    def _init(self) -> None:
        try:
            import meilisearch

            self._client = meilisearch.Client(self._url, self._key)
            self._ensure_index()
        except Exception:
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _ensure_index(self) -> None:
        if not self._client:
            return
        try:
            self._client.get_index(INDEX_NAME)
        except Exception:
            self._client.create_index(INDEX_NAME, {"primaryKey": "id"})
        idx = self._client.index(INDEX_NAME)
        idx.update_searchable_attributes(
            ["title", "subtitle", "address", "case_ref", "label", "entity_name", "kind"]
        )
        idx.update_filterable_attributes(["kind", "chain", "risk_score"])
        idx.update_typo_tolerance({"enabled": True, "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8}})

    def upsert(self, docs: list[dict[str, Any]]) -> None:
        if not self._client or not docs:
            return
        self._client.index(INDEX_NAME).add_documents(docs)

    def delete(self, doc_ids: list[str]) -> None:
        if not self._client or not doc_ids:
            return
        self._client.index(INDEX_NAME).delete_documents(doc_ids)

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not self._client or not query.strip():
            return []
        try:
            res = self._client.index(INDEX_NAME).search(
                query.strip(),
                {"limit": limit, "attributesToHighlight": ["title", "address", "case_ref"]},
            )
            return list(res.get("hits") or [])
        except Exception:
            return []


_client: SearchClient | None = None


def get_search_client() -> SearchClient:
    global _client
    if _client is None:
        _client = SearchClient()
    return _client


def doc_id(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def index_case(case_ref: str, workflow_status: str = "", owner_id: str = "") -> None:
    get_search_client().upsert(
        [
            {
                "id": doc_id("case", case_ref),
                "kind": "case",
                "title": case_ref,
                "subtitle": workflow_status,
                "case_ref": case_ref,
                "owner_id": owner_id,
            }
        ]
    )


def index_wallet(chain: str, address: str, label: str = "", risk_score: float | None = None) -> None:
    get_search_client().upsert(
        [
            {
                "id": doc_id("wallet", f"{chain}:{address}"),
                "kind": "wallet",
                "chain": chain,
                "address": address,
                "title": address,
                "label": label,
                "risk_score": risk_score,
            }
        ]
    )


def index_vasp(name: str, jurisdiction: str = "", license_id: str = "") -> None:
    get_search_client().upsert(
        [
            {
                "id": doc_id("vasp", name),
                "kind": "vasp",
                "title": name,
                "entity_name": name,
                "subtitle": jurisdiction,
                "label": license_id,
            }
        ]
    )


def search_postgres_fallback(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """ILIKE fallback when Meilisearch is unavailable."""
    import os

    url = os.getenv("DATABASE_URL")
    if not url or not query.strip():
        return []
    pattern = f"%{query.strip()}%"
    hits: list[dict[str, Any]] = []
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url)
        with engine.connect() as conn:
            for row in conn.execute(
                text(
                    """
                    SELECT case_ref, workflow_status, owner_id::text
                    FROM compliance_cases
                    WHERE case_ref ILIKE :q
                    ORDER BY updated_at DESC NULLS LAST
                    LIMIT :lim
                    """
                ),
                {"q": pattern, "lim": limit},
            ).mappings():
                hits.append(
                    {
                        "id": doc_id("case", row["case_ref"]),
                        "kind": "case",
                        "title": row["case_ref"],
                        "subtitle": row["workflow_status"] or "",
                        "case_ref": row["case_ref"],
                    }
                )
            remaining = max(0, limit - len(hits))
            if remaining:
                for row in conn.execute(
                    text(
                        """
                        SELECT chain, address, label, risk_score
                        FROM compliance_entity_labels
                        WHERE address ILIKE :q OR label ILIKE :q
                        ORDER BY added_at DESC NULLS LAST
                        LIMIT :lim
                        """
                    ),
                    {"q": pattern, "lim": remaining},
                ).mappings():
                    hits.append(
                        {
                            "id": doc_id("wallet", f"{row['chain']}:{row['address']}"),
                            "kind": "wallet",
                            "chain": row["chain"],
                            "address": row["address"],
                            "title": row["address"],
                            "label": row["label"] or "",
                            "risk_score": row["risk_score"],
                        }
                    )
    except Exception:
        pass
    return hits[:limit]
