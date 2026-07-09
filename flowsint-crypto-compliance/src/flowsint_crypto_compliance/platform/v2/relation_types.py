"""Knowledge Graph relation types — RFC-0003 Ch.4."""

from __future__ import annotations

from enum import Enum


class RelationType(str, Enum):
    """Canonical relation taxonomy for the Knowledge Graph."""

    OWNS = "owns"
    MANAGES = "manages"
    USES = "uses"
    SENT_TO = "sent_to"
    RECEIVED_FROM = "received_from"
    REGISTERED_AT = "registered_at"
    RELATED_TO = "related_to"
    CO_MENTIONED = "co_mentioned"
    SIGNED = "signed"
    WORKS_AT = "works_at"
    CONTROLS = "controls"
    BENEFICIARY_OF = "beneficiary_of"
    SAME_CLUSTER = "same_cluster"
    # RFC-0002 legacy
    INVESTIGATES = "investigates"


# Human-readable labels (Russian) for API manifest
RELATION_TYPE_LABELS_RU: dict[str, str] = {
    RelationType.OWNS.value: "владеет",
    RelationType.MANAGES.value: "управляет",
    RelationType.USES.value: "использует",
    RelationType.SENT_TO.value: "отправил",
    RelationType.RECEIVED_FROM.value: "получил от",
    RelationType.REGISTERED_AT.value: "зарегистрирован на",
    RelationType.RELATED_TO.value: "связан с",
    RelationType.CO_MENTIONED.value: "совместное упоминание",
    RelationType.SIGNED.value: "подписал",
    RelationType.WORKS_AT.value: "работает в",
    RelationType.CONTROLS.value: "контролирует",
    RelationType.BENEFICIARY_OF.value: "бенефициар",
    RelationType.SAME_CLUSTER.value: "один кластер",
    RelationType.INVESTIGATES.value: "расследует",
}
