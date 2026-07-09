"""RFC-0015 Ch.9 — declarative IF/THEN rules engine (versioned)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ComplianceEvent:
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
class ComplianceRule:
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


_DEFAULT_RULES: list[ComplianceRule] = [
    ComplianceRule(
        rule_id="license_lost_active_ops",
        version="1.0.0",
        condition={"license_status": "revoked", "operations_active": True},
        action={"event_type": "ComplianceEvent", "severity": "critical"},
        description_ru="Лицензия отозвана при активных операциях",
    ),
    ComplianceRule(
        rule_id="sanction_hit",
        version="1.0.0",
        condition={"sanctioned": True},
        action={"event_type": "ComplianceEvent", "severity": "critical"},
        description_ru="Санкционное попадание",
    ),
    ComplianceRule(
        rule_id="registration_dissolved",
        version="1.0.0",
        condition={"org_status": "dissolved"},
        action={"event_type": "ComplianceEvent", "severity": "high"},
        description_ru="Организация ликвидирована",
    ),
]


class RulesEngine:
    """Versioned declarative IF/THEN rules."""

    def __init__(self, rules: list[ComplianceRule] | None = None) -> None:
        self._rules = rules or list(_DEFAULT_RULES)

    def list_rules(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._rules]

    def evaluate(self, context: dict[str, Any]) -> list[ComplianceEvent]:
        events: list[ComplianceEvent] = []
        for rule in self._rules:
            if self._matches(rule.condition, context):
                action = rule.action
                events.append(
                    ComplianceEvent(
                        id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        rule_version=rule.version,
                        event_type=str(action.get("event_type", "ComplianceEvent")),
                        severity=str(action.get("severity", "medium")),
                        message_ru=rule.description_ru or f"Правило {rule.rule_id} сработало",
                        context=dict(context),
                    )
                )
        return events

    def _matches(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        return all(context.get(k) == v for k, v in condition.items())


_engine: RulesEngine | None = None


def get_rules_engine() -> RulesEngine:
    global _engine
    if _engine is None:
        _engine = RulesEngine()
    return _engine
