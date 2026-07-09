"""Combat mode defaults entity_labels store to postgres."""

from flowsint_crypto_compliance.attribution.entity_label_store import (
    get_entity_label_store,
    reset_entity_label_store,
)
from flowsint_crypto_compliance.attribution.postgres_entity_store import entity_store_mode


def test_combat_mode_defaults_entity_store_postgres(monkeypatch):
    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")
    assert entity_store_mode() == "postgres"


def test_explicit_memory_override_in_combat(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    assert entity_store_mode() == "memory"


def test_offline_mode_defaults_memory(monkeypatch):
    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "0")
    assert entity_store_mode() == "memory"


def test_apply_combat_env_defaults_sets_env(monkeypatch):
    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")
    from flowsint_crypto_compliance.demo.combat_mode import apply_combat_env_defaults

    apply_combat_env_defaults()
    assert __import__("os").environ.get("FINSKALP_ENTITY_STORE") == "postgres"


def test_combat_without_database_falls_back_to_memory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")
    reset_entity_label_store()
    store = get_entity_label_store()
    from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore

    assert isinstance(store, EntityLabelStore)
    reset_entity_label_store()
