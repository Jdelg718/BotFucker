"""Local mock review queue domain layer for the Phase 2 UI skeleton.

This module intentionally models UI-only review actions. It never calls an
email provider, sends mail, moves mail, deletes mail, or persists blacklist
changes. Actions mutate only the in-memory queue passed to ``MockReviewQueue``
and append local audit events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

MockAction = Literal["approve_warning", "dismiss", "whitelist_sender", "blacklist_sender"]
ReviewStatus = Literal["pending", "actioned"]

SUPPORTED_ACTIONS: tuple[MockAction, ...] = (
    "approve_warning",
    "dismiss",
    "whitelist_sender",
    "blacklist_sender",
)
MOCK_EFFECT_SCOPE = "local_in_memory_sample_state_only"
MOCK_SAFETY_NOTE = (
    "Mock/local UI action only. No email was sent, moved, deleted, whitelisted, "
    "or blacklisted with any provider."
)


class ReviewQueueError(ValueError):
    """Raised when a local mock review action cannot be applied."""


@dataclass
class ReviewItem:
    """A deterministic, provider-free item displayed in the local review UI."""

    item_id: str
    message_id: str
    thread_id: str
    from_email: str
    from_name: str
    sender_domain: str
    subject: str
    snippet: str
    received_at: str
    classification: str
    confidence: float
    recommended_action: str
    reasons: list[str] = field(default_factory=list)
    sender_strike_level: int = 0
    draft_reply: str = ""
    allowed_actions: list[str] = field(default_factory=lambda: list(SUPPORTED_ACTIONS))
    status: ReviewStatus = "pending"
    source: str = "deterministic_sample_data"
    mock_only: bool = True
    safety_note: str = MOCK_SAFETY_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "sender_domain": self.sender_domain,
            "subject": self.subject,
            "snippet": self.snippet,
            "received_at": self.received_at,
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
            "recommended_action": self.recommended_action,
            "reasons": list(self.reasons),
            "sender_strike_level": self.sender_strike_level,
            "draft_reply": self.draft_reply,
            "allowed_actions": list(self.allowed_actions),
            "status": self.status,
            "source": self.source,
            "mock_only": self.mock_only,
            "safety_note": self.safety_note,
        }


@dataclass(frozen=True)
class AuditEvent:
    """A local audit event for a simulated review action."""

    event_id: str
    item_id: str
    action: str
    actor: str
    created_at: str
    note: str = ""
    mock_only: bool = True
    effect_scope: str = MOCK_EFFECT_SCOPE
    safety_note: str = MOCK_SAFETY_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "item_id": self.item_id,
            "action": self.action,
            "actor": self.actor,
            "created_at": self.created_at,
            "note": self.note,
            "mock_only": self.mock_only,
            "effect_scope": self.effect_scope,
            "safety_note": self.safety_note,
        }


class MockReviewQueue:
    """In-memory review queue for the local branded UI skeleton."""

    supported_actions = SUPPORTED_ACTIONS

    def __init__(self, items: list[ReviewItem] | tuple[ReviewItem, ...]):
        self.items = list(items)
        self.audit_events: list[AuditEvent] = []

    def get_item(self, item_id: str) -> ReviewItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise ReviewQueueError(f"Unknown review item: {item_id}")

    def pending_items(self) -> list[ReviewItem]:
        return [item for item in self.items if item.status == "pending"]

    def apply_action(self, item_id: str, action: str, actor: str = "local-ui", note: str = "") -> AuditEvent:
        if action not in SUPPORTED_ACTIONS:
            raise ReviewQueueError(f"Unsupported mock review action: {action}")

        item = self.get_item(item_id)
        item.status = "actioned"
        event = AuditEvent(
            event_id=f"audit-{len(self.audit_events) + 1:04d}",
            item_id=item_id,
            action=action,
            actor=actor or "local-ui",
            note=note,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.audit_events.append(event)
        return event

    def sender_history(self) -> dict[str, dict[str, Any]]:
        history: dict[str, dict[str, Any]] = {}
        last_actions = {event.item_id: event.action for event in self.audit_events}
        for item in self.items:
            row = history.setdefault(
                item.from_email,
                {
                    "sender": item.from_email,
                    "sender_domain": item.sender_domain,
                    "message_count": 0,
                    "max_strike_level": 0,
                    "classifications": [],
                    "last_mock_action": None,
                    "mock_only": True,
                    "safety_note": MOCK_SAFETY_NOTE,
                },
            )
            row["message_count"] += 1
            row["max_strike_level"] = max(row["max_strike_level"], item.sender_strike_level)
            if item.classification not in row["classifications"]:
                row["classifications"].append(item.classification)
            if item.item_id in last_actions:
                row["last_mock_action"] = last_actions[item.item_id]
        return history
