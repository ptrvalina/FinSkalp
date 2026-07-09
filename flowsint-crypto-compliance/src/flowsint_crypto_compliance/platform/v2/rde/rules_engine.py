"""RFC-0016 Ch.5+13 — declarative versioned rules engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RDEEvent:
    """Emitted when a rule fires."""

    id: str
    rule_id: str
    rule_version: str
    event_type: str
    severity: str
    message_ru: str
    context: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "event_type": self.event_type,
            "severity": self.severity,
            "message_ru": self.message_ru,
            "context": self.context,
            "occurred_at": self.occurred_at,
        }


@dataclass
class RDERule:
    rule_id: str
    version: str
    condition: dict[str, Any]
    action: dict[str, Any]
    description_ru: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "condition": self.condition,
            "action": self.action,
            "description_ru": self.description_ru,
        }


@dataclass
class RuleHistoryEntry:
    rule_id: str
    version: str
    action: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


_DEFAULT_RULES: list[RDERule] = [
    RDERule(
        rule_id="elevated_attention",
        version="1.0.0",
        condition={"activity_spike": True, "new_links": True, "multi_source_evidence": True},
        action={"event_type": "ElevatedAttentionEvent", "severity": "high"},
        description_ru="Всплеск активности + новые связи + мультиисточниковые доказательства",
    ),
    RDERule(
        rule_id="sanction_blockchain_correlation",
        version="1.0.0",
        condition={"sanctioned": True, "mixer_exposure": True},
        action={"event_type": "CriticalCorrelationEvent", "severity": "critical"},
        description_ru="Санкционное попадание коррелирует с миксер-экспозицией",
    ),
    RDERule(
        rule_id="registry_evidence_mismatch",
        version="1.0.0",
        condition={"org_status": "dissolved", "operations_active": True},
        action={"event_type": "ComplianceAnomalyEvent", "severity": "high"},
        description_ru="Ликвидированная организация с активными операциями",
    ),
]


class RulesEngine:
    """Versioned declarative IF/THEN rules with history and rollback stubs."""

    def __init__(self, rules: list[RDERule] | None = None) -> None:
        self._rules = rules or list(_DEFAULT_RULES)
        self._history: list[RuleHistoryEntry] = []

    def list_rules(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._rules]

    def evaluate(self, context: dict[str, Any]) -> list[RDEEvent]:
        events: list[RDEEvent] = []
        for rule in self._rules:
            if self._matches(rule.condition, context):
                action = rule.action
                events.append(
                    RDEEvent(
                        id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        rule_version=rule.version,
                        event_type=str(action.get("event_type", "RDEEvent")),
                        severity=str(action.get("severity", "medium")),
                        message_ru=rule.description_ru or f"Правило {rule.rule_id} сработало",
                        context=dict(context),
                    )
                )
        return events

    def preview(self, context: dict[str, Any]) -> dict[str, Any]:
        """Preview which rules would fire without side effects."""
        would_fire = []
        for rule in self._rules:
            would_fire.append({
                "rule_id": rule.rule_id,
                "version": rule.version,
                "matches": self._matches(rule.condition, context),
                "description_ru": rule.description_ru,
            })
        return {"preview": True, "rules": would_fire}

    def add_rule(self, rule: RDERule) -> None:
        self._rules.append(rule)
        self._history.append(
            RuleHistoryEntry(
                rule_id=rule.rule_id,
                version=rule.version,
                action="add",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def rollback(self, rule_id: str, target_version: str) -> dict[str, Any]:
        """Rollback stub — records intent, does not delete rules in production."""
        self._history.append(
            RuleHistoryEntry(
                rule_id=rule_id,
                version=target_version,
                action="rollback_requested",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"stub": True},
            )
        )
        return {"ok": True, "rule_id": rule_id, "target_version": target_version, "stub": True}

    def get_history(self) -> list[dict[str, Any]]:
        return [
            {"rule_id": h.rule_id, "version": h.version, "action": h.action, "timestamp": h.timestamp}
            for h in self._history
        ]

    def _matches(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        return all(context.get(k) == v for k, v in condition.items())


_engine: RulesEngine | None = None


def get_rules_engine() -> RulesEngine:
    global _engine
    if _engine is None:
        _engine = RulesEngine()
    return _engine
