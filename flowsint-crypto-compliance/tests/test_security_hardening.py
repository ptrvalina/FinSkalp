from flowsint_crypto_compliance.osint_core.scalpel.security import (
    assert_upload_size,
    is_safe_external_url,
    sanitize_filename,
    sanitize_username,
    validate_upload_magic,
)


def test_ssrf_blocks_localhost():
    assert not is_safe_external_url("http://127.0.0.1/admin")
    assert not is_safe_external_url("http://localhost/api")
    assert not is_safe_external_url("file:///etc/passwd")
    assert not is_safe_external_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_allows_public_https():
    assert is_safe_external_url("https://api.trongrid.io/v1/accounts/test")
    assert is_safe_external_url("https://polygon.blockscout.com/api")


def test_sanitize_filename_strips_path():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert ".." not in sanitize_filename("..\\evil.pdf")


def test_sanitize_username_rejects_shell():
    try:
        sanitize_username("user;rm -rf")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_sanitize_username_transliterates_cyrillic_fio():
    assert sanitize_username("Иванов Алексей") == "ivanov_aleksey"
    assert sanitize_username("ivanov_aleksey") == "ivanov_aleksey"


def test_bare_seed_query_strips_prefixes():
    from flowsint_crypto_compliance.osint_core.scalpel.seed_query import (
        bare_seed_query,
        person_to_usernames,
        seed_kind,
    )

    assert bare_seed_query("org:ООО Пример") == "ООО Пример"
    assert bare_seed_query("person:Иванов Алексей") == "Иванов Алексей"
    assert seed_kind("org:Acme") == "org"
    assert "ivanov_aleksey" in person_to_usernames("Иванов Алексей")


def test_upload_size_limit():
    try:
        assert_upload_size(100 * 1024 * 1024)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_validate_upload_magic_pdf():
    validate_upload_magic(b"%PDF-1.4 content", "report.pdf")
    try:
        validate_upload_magic(b"MZ executable", "report.pdf")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_validate_upload_magic_rejects_unknown_ext():
    try:
        validate_upload_magic(b"data", "evil.exe")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_demo_rate_limit_middleware_exists():
    from flowsint_crypto_compliance.demo.security_hardening import DemoRateLimitMiddleware

    assert DemoRateLimitMiddleware is not None


def test_validate_evidence_hash_rejects_traversal():
    from flowsint_crypto_compliance.demo.security_hardening import validate_evidence_hash

    try:
        validate_evidence_hash("../etc/passwd")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert validate_evidence_hash("a1b2c3d4") == "a1b2c3d4"


def test_validate_case_ref_rejects_path():
    from flowsint_crypto_compliance.demo.security_hardening import validate_case_ref

    try:
        validate_case_ref("../../secret")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
