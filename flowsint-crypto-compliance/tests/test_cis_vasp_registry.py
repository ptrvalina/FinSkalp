from flowsint_crypto_compliance.cis.coverage import CISJurisdiction
from flowsint_crypto_compliance.registry.cis_vasp_registry import (
    load_cis_vasp_registry,
    registry_metadata,
)


def test_cis_vasp_registry_only_verified_sources():
    entries = load_cis_vasp_registry()
    meta = registry_metadata()
    assert len(entries) >= 30
    assert meta["licensed_count"] == len(entries)
    for e in entries:
        assert e.get("registry_source"), f"missing source for {e['id']}"
        assert "Unlicensed exchanger" not in e.get("label_ru", "")
        assert "exchanger #" not in e.get("label_ru", "").lower()


def test_cis_vasp_no_fabricated_jurisdictions():
    codes = {e["jurisdiction"] for e in load_cis_vasp_registry()}
    # Убраны вымышленные записи KG/TJ/MD/AZ/AM без публичного подтверждения
    assert "KG" not in codes
    assert "TJ" not in codes
    assert "MD" not in codes
    assert "AZ" not in codes
    for required in ("RU", "KZ", "BY", "UZ"):
        assert required in codes


def test_cis_vasp_russia_cbr_operators():
    ru = [e for e in load_cis_vasp_registry() if e["jurisdiction"] == "RU"]
    assert len(ru) >= 20
    names = " ".join(e["legal_name_ru"] for e in ru)
    assert "Атомайз" in names
    assert "Сбербанк" in names


def test_cis_vasp_kazakhstan_afsa_license_refs():
    kz = [e for e in load_cis_vasp_registry() if e["jurisdiction"] == "KZ"]
    assert len(kz) >= 2
    assert any("AFSA" in (e.get("license_ref") or "") for e in kz)


def test_match_vasp_requires_known_wallet():
    from flowsint_crypto_compliance.registry.cis_vasp_registry import match_vasp_for_address

    assert match_vasp_for_address("TRU_HUB_MSK", "tron") is None
