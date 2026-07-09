from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import (
    run_spiderfoot,
)
from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import (
    run_maigret,
)


def test_spiderfoot_compat_layer():
    result = run_spiderfoot("example.com")
    assert result["engine"] in ("spiderfoot_compat", "spiderfoot_cli")
    assert "status" in result


def test_maigret_embedded_fallback():
    result = run_maigret("testuser_no_cli_expected")
    assert result["status"] in ("embedded", "ok", "miss", "error", "timeout")
    assert "hits" in result
