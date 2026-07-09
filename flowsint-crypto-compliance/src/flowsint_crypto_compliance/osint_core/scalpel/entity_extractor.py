"""
Извлечение сущностей из неструктурированного текста OSINT.

Криптоадреса, ИНН/ОГРН, телефоны, email, паспортные шаблоны, суммы в RUB/USD/USDT.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class ExtractedEntities:
    crypto_addresses: list[dict[str, str]] = field(default_factory=list)
    inn: list[str] = field(default_factory=list)
    ogrn: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    amounts: list[dict[str, str]] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.crypto_addresses)
            + len(self.inn)
            + len(self.phones)
            + len(self.emails)
            + len(self.domains)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "crypto_addresses": self.crypto_addresses,
            "inn": self.inn,
            "ogrn": self.ogrn,
            "phones": self.phones,
            "emails": self.emails,
            "amounts": self.amounts,
            "usernames": self.usernames,
            "domains": self.domains,
            "total": self.total,
        }


_RE_TRON = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")
_RE_ETH = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_RE_BTC = re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b")
_RE_INN = re.compile(r"\b(?:ИНН[:\s]*)?(\d{10}|\d{12})\b", re.I)
_RE_OGRN = re.compile(r"\b(?:ОГРН[:\s]*)?(\d{13}|\d{15})\b", re.I)
_RE_PHONE = re.compile(r"\b(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
_RE_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_RE_AMOUNT = re.compile(
    r"\b(\d[\d\s.,]*)\s*(₽|руб\.?|RUB|USD|\$|USDT|BTC|ETH)\b",
    re.I,
)
_RE_USERNAME = re.compile(r"(?:@|username[:\s]+)([a-zA-Z0-9_]{3,32})\b", re.I)
_RE_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_SKIP_HOSTS = frozenset({"localhost", "example.com", "example.org"})


def _host_from_text(url: str) -> str | None:
    if "://" not in url:
        return None
    host = (urlparse(url).hostname or "").lower()
    if host and host not in _SKIP_HOSTS:
        return host
    return None


def extract_entities(text: str, *, context_address: str = "") -> ExtractedEntities:
    if not text:
        return ExtractedEntities()

    entities = ExtractedEntities()
    seen_crypto: set[str] = set()

    for m in _RE_TRON.finditer(text):
        addr = m.group(0)
        if addr not in seen_crypto and addr != context_address:
            seen_crypto.add(addr)
            entities.crypto_addresses.append({"address": addr, "chain": "tron"})
    for m in _RE_ETH.finditer(text):
        addr = m.group(0).lower()
        if addr not in seen_crypto and addr != context_address.lower():
            seen_crypto.add(addr)
            entities.crypto_addresses.append({"address": addr, "chain": "eth"})
    for m in _RE_BTC.finditer(text):
        addr = m.group(0)
        if addr not in seen_crypto:
            seen_crypto.add(addr)
            entities.crypto_addresses.append({"address": addr, "chain": "btc"})

    entities.inn = _uniq(_RE_INN.findall(text))[:20]
    entities.ogrn = _uniq(_RE_OGRN.findall(text))[:10]
    entities.phones = _uniq(_RE_PHONE.findall(text))[:15]
    from flowsint_crypto_compliance.osint.multilingual import extract_cis_entities

    cis = extract_cis_entities(text)
    for key in ("phones_kz", "phones_ua", "phones_by", "phones_uz"):
        entities.phones.extend(cis.get(key) or [])
    entities.phones = _uniq(entities.phones)[:20]
    entities.emails = _uniq(_RE_EMAIL.findall(text))[:15]
    entities.usernames = _uniq(_RE_USERNAME.findall(text))[:10]
    seen_hosts: set[str] = set()
    for m in _RE_URL.finditer(text):
        host = _host_from_text(m.group(0))
        if host and host not in seen_hosts:
            seen_hosts.add(host)
            entities.domains.append(host)
    entities.domains = entities.domains[:15]

    for m in _RE_AMOUNT.finditer(text):
        entities.amounts.append({"value": m.group(1).strip(), "currency": m.group(2).upper()})
    entities.amounts = entities.amounts[:25]

    return entities


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in items:
        k = x.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(x.strip())
    return out
