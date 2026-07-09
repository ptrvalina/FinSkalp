from flowsint_crypto_compliance.demo.live_kyt_scanner import (
    add_kyt_watch_address,
    list_kyt_watch_addresses,
)


def test_runtime_watchlist_add():
    from flowsint_crypto_compliance.demo import live_kyt_scanner as mod

    mod._runtime_watchlist.clear()
    addr = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
    add_kyt_watch_address(addr)
    listed = list_kyt_watch_addresses()
    assert addr in listed
    mod._runtime_watchlist.clear()
