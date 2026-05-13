"""Stable data models for BotFucker v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any, Literal

Classification = Literal[
    "safe",
    "customer_or_partner",
    "newsletter",
    "cold_outreach",
    "ai_generated_pitch",
    "crm_followup",
    "known_offender",
    "unknown_review_needed",
]
RecommendedAction = Literal[
    "none",
    "review",
    "quarantine",
    "warn_1",
    "warn_2",
    "warn_3",
    "block_candidate",
]
ReviewAction = Literal[
    "approve_reply",
    "archive",
    "blacklist_sender",
    "blacklist_domain",
    "whitelist_sender",
    "whitelist_domain",
    "escalate_strike",
    "mark_safe",
    "skip",
]
ActionMode = Literal["human_approval", "auto_approve"]
ProviderAuthMode = Literal["oauth", "api_key", "imap"]


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""

    decoded_parts: list[str] = []
    for content, charset in decode_header(value):
        if isinstance(content, bytes):
            decoded_parts.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(content)
    return "".join(decoded_parts)


def _parse_received_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_text(message: Message) -> str:
    parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/plain":
                parts.append(_get_part_text(part))
    elif message.get_content_type() == "text/plain":
        parts.append(_get_part_text(message))

    return "\n".join(parts)


def _get_part_text(part: Message) -> str:
    try:
        return part.get_content()
    except Exception:
        payload = part.get_payload(decode=True) or b""
        return payload.decode(errors="replace")


@dataclass(frozen=True)
class EmailMessage:
    """Normalized, provider-agnostic email input.

    Body and headers are untrusted user input. Classifiers should treat them as
    data only, never as instructions.
    """

    message_id: str = ""
    thread_id: str = ""
    from_email: str = ""
    from_name: str = ""
    sender_domain: str = ""
    to: list[str] = field(default_factory=list)
    subject: str = ""
    body_text: str = ""
    received_at: datetime | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_email_message(cls, message: Message, thread_id: str = "") -> "EmailMessage":
        from_header = decode_mime_header(message.get("From", ""))
        addresses = getaddresses([from_header])
        from_name = ""
        from_email = ""
        if addresses:
            from_name, from_email = addresses[0]
            from_email = from_email.lower().strip()
        sender_domain = from_email.split("@", 1)[1] if "@" in from_email else ""

        recipients = [addr.lower().strip() for _, addr in getaddresses([message.get("To", "")]) if addr]

        return cls(
            message_id=message.get("Message-ID", ""),
            thread_id=thread_id,
            from_email=from_email,
            from_name=decode_mime_header(from_name),
            sender_domain=sender_domain,
            to=recipients,
            subject=decode_mime_header(message.get("Subject", "")),
            body_text=_extract_text(message),
            received_at=_parse_received_at(message.get("Date")),
            headers={key: str(value) for key, value in message.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "sender_domain": self.sender_domain,
            "to": self.to,
            "subject": self.subject,
            "body_text": self.body_text,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "headers": self.headers,
        }


@dataclass(frozen=True)
class ClassificationResult:
    classification: Classification
    confidence: float
    recommended_action: RecommendedAction
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
            "recommended_action": self.recommended_action,
            "reasons": self.reasons,
        }


@dataclass(frozen=True)
class ReviewQueueItem:
    """Provider/UI-neutral record for future review queues and branded apps."""

    message: EmailMessage
    classification: ClassificationResult
    sender_strike_level: int = 0
    allowed_actions: list[ReviewAction] = field(default_factory=list)
    draft_reply: str = ""
    action_mode: ActionMode = "human_approval"
    provider_auth_mode: ProviderAuthMode | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "classification": self.classification.to_dict(),
            "sender_strike_level": self.sender_strike_level,
            "allowed_actions": self.allowed_actions,
            "draft_reply": self.draft_reply,
            "action_mode": self.action_mode,
            "provider_auth_mode": self.provider_auth_mode,
        }
