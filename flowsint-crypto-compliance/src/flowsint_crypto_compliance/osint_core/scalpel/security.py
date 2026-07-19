"""Безопасность OSINT-шлюза: SSRF, загрузки, subprocess."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

MAX_UPLOAD_BYTES = int(os.getenv("FINSKALP_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

# Magic-byte signatures for OCR upload validation (extension alone is insufficient).
_UPLOAD_MAGIC: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".tif": (b"II*\x00", b"MM\x00*"),
    ".tiff": (b"II*\x00", b"MM\x00*"),
    ".webp": (b"RIFF",),
}

_SAFE_TOKEN = re.compile(r"^[a-zA-Z0-9._@_-]{2,64}$")
_SAFE_TARGET = re.compile(r"^[a-zA-Z0-9._@:/-]{1,256}$")

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    }
)


def sanitize_filename(name: str) -> str:
    # Normalize Windows separators before Path.name (POSIX keeps `\`)
    normalized = str(name).replace("\\", "/").strip()
    base = Path(normalized).name
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:120]
    # Collapse path-traversal leftovers (.. / leading dots)
    safe = re.sub(r"^\.+", "", safe)
    safe = safe.replace("..", "_")
    return safe or "document.bin"


def sanitize_username(value: str) -> str:
    """
    Normalize to a Maigret-safe ASCII token.
    Cyrillic ФИО and spaces are transliterated / underscored — not rejected.
    Shell metacharacters are still rejected.
    """
    from flowsint_crypto_compliance.osint_core.scalpel.seed_query import transliterate_cyrillic

    token = value.strip().lstrip("@")
    if re.search(r"[;|&$`\\<>]", token):
        raise ValueError("Недопустимые символы в username")
    token = transliterate_cyrillic(token)
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^a-zA-Z0-9._@_-]", "", token)[:64]
    token = token.strip("._-")
    if not _SAFE_TOKEN.match(token):
        raise ValueError("Недопустимые символы в username")
    return token


def sanitize_spiderfoot_target(value: str) -> str:
    target = value.strip()[:256]
    if not _SAFE_TARGET.match(target):
        raise ValueError("Недопустимый target для SpiderFoot")
    if ".." in target:
        raise ValueError("Недопустимый target")
    return target


def assert_upload_size(size: int) -> None:
    if size <= 0:
        raise ValueError("Пустой файл")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Файл превышает лимит {MAX_UPLOAD_BYTES // (1024 * 1024)} МБ")


def validate_upload_magic(data: bytes, filename: str) -> None:
    """Reject uploads whose content does not match allowed magic bytes for the extension."""
    ext = Path(filename).suffix.lower()
    if ext not in _UPLOAD_MAGIC:
        raise ValueError(f"Недопустимый тип файла: {ext or 'unknown'}")
    sigs = _UPLOAD_MAGIC[ext]
    if ext == ".webp":
        if not (data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP"):
            raise ValueError("Содержимое файла не соответствует формату WEBP")
        return
    if not any(data.startswith(sig) for sig in sigs):
        raise ValueError(f"Содержимое файла не соответствует расширению {ext}")


def is_safe_external_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS:
        return False
    if host.endswith(".local") or host.endswith(".internal") or host.endswith(".localhost"):
        return False
    if host in ("metadata", "metadata.google"):
        return False
    try:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                for res in socket.getaddrinfo(host, None, family, socket.SOCK_STREAM):
                    ip = ipaddress.ip_address(res[4][0])
                    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                        return False
            except socket.gaierror:
                continue
    except ValueError:
        return False
    return True
