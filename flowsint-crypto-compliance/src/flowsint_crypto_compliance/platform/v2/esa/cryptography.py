"""RFC-0020 Ch.7 — cryptography manifest."""

from __future__ import annotations

from typing import Any


def cryptography_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 7,
        "encryption_at_rest": {
            "enabled": True,
            "default_algorithm": "AES-256-GCM",
            "key_management": "flowsint vault",
            "database": "PostgreSQL TDE (planned)",
            "object_storage": "S3 SSE-KMS",
            "technical_debt": "TD-ESA-2",
        },
        "encryption_in_transit": {
            "enabled": True,
            "min_tls_version": "1.2",
            "preferred_tls_version": "1.3",
            "cipher_suites": [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            ],
            "internal_mtls": True,
        },
        "algorithms": {
            "symmetric": ["AES-256-GCM", "ChaCha20-Poly1305"],
            "asymmetric": ["RSA-4096", "ECDSA P-256", "Ed25519"],
            "hashing": ["SHA-256", "SHA-384", "SHA3-256"],
            "key_derivation": ["PBKDF2", "Argon2id", "HKDF-SHA256"],
            "signing": ["RSA-PSS", "ECDSA", "Ed25519"],
        },
        "forbidden_algorithms": ["MD5", "SHA-1", "DES", "3DES", "RC4"],
        "key_rotation": {
            "data_keys_days": 90,
            "tls_certs_days": 365,
            "api_keys_days": 90,
        },
        "principle_ru": "Шифрование везде — at-rest и in-transit с современными алгоритмами",
    }
