"""Smart OSINT query expansion — aliases, pseudonyms, related domains."""

from __future__ import annotations

from typing import Any


def expand_osint_queries(
    *,
    address: str,
    chain: str,
    case_pseudonym: str | None = None,
    co_spend_aliases: list[str] | None = None,
    prior_domains: list[str] | None = None,
    prior_usernames: list[str] | None = None,
    extracted_entities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build expanded query context for Scalpel collectors.
    """
    usernames: list[str] = list(prior_usernames or [])
    domains: list[str] = list(prior_domains or [])
    addresses: list[str] = [address]

    if case_pseudonym:
        usernames.append(case_pseudonym.strip().lstrip("@"))

    for alias in co_spend_aliases or []:
        a = alias.strip()
        if a and a != address and a not in addresses:
            addresses.append(a)

    agg = (extracted_entities or {}).get("aggregate") or extracted_entities or {}
    for u in agg.get("usernames") or []:
        if u not in usernames:
            usernames.append(str(u).lstrip("@"))
    for d in agg.get("domains") or []:
        if d not in domains:
            domains.append(str(d))

    return {
        "expanded_addresses": addresses[:12],
        "usernames": usernames[:10],
        "domains": domains[:12],
        "chain": chain,
        "expansion_sources": {
            "co_spend_aliases": len(co_spend_aliases or []),
            "case_pseudonym": bool(case_pseudonym),
            "prior_findings": len(domains) + len(usernames),
        },
    }
