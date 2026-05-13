"""Normalized n8n/webhook payload contract for safe local review imports.

This module accepts already-fetched email JSON from automation tools such as n8n
and converts it into durable ``ReviewItem`` records. It deliberately does not
run an HTTP listener, authenticate to providers, or persist provider secrets.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from .classifier import classify_message
from .models import EmailMessage
from .review_queue import MOCK_SAFETY_NOTE, SUPPORTED_ACTIONS, ReviewItem

MAX_TEXT_FIELD_CHARS = 500
MAX_SNIPPET_CHARS = 1200
DEFAULT_PROVIDER = "webhook"

_SECRET_KEY_RE = re.compile(
    r"(authorization|cookie|set-cookie|token|access[_-]?token|refresh[_-]?token|api[_-]?key|secret|password|credential)",
    re.IGNORECASE,
)
_CREDENTIAL_HEADER_NAMES = (
    r"authorization",
    r"proxy-authorization",
    r"x-api-key",
    r"api-key",
    r"x-auth-token",
    r"x-access-token",
    r"access-token",
    r"set-cookie",
    r"cookie",
    r"[A-Za-z0-9-]*(?:secret|token|credential|password)[A-Za-z0-9-]*",
)
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"(?im)(?<![^\n\r])\s*(?:{'|'.join(_CREDENTIAL_HEADER_NAMES)})\s*:\s*[^\n\r]+"),
    re.compile(r"\bBearer\s+[^\s,;]+", re.IGNORECASE),
    re.compile(r"\b(Basic|Digest)\s+[^\s,;]+", re.IGNORECASE),
    re.compile(r"\bCookie\s*:\s*[^\n\r]+", re.IGNORECASE),
    re.compile(r"\bSet-Cookie\s*:\s*[^\n\r]+", re.IGNORECASE),
    re.compile(r"\b(?:access[_-]?token|refresh[_-]?token|api[_-]?key|secret|password|credential)\s*[:=]\s*[^\s,;&]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9._%+-]*(?:SECRET|TOKEN|APIKEY|PASSWORD|CREDENTIAL)[A-Za-z0-9._%+-]*\b", re.IGNORECASE),
)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class WebhookPayloadError(ValueError):
    """Raised when an inbound webhook JSON payload is unsupported or unsafe."""


def iter_webhook_review_items(payload: Any) -> list[ReviewItem]:
    """Normalize a single payload or a common collection wrapper atomically.

    Accepted shapes:
    - ``{...message fields...}``
    - ``[{...}, {...}]``
    - ``{"items": [...]}``, ``{"events": [...]}``, or ``{"messages": [...]}``
    """

    raw_items = _extract_payload_items(payload)
    normalized = [webhook_payload_to_review_item(item) for item in raw_items]
    return normalized


def webhook_payload_to_review_item(payload: dict[str, Any]) -> ReviewItem:
    """Convert one untrusted n8n-ish email payload to a local ReviewItem."""

    if not isinstance(payload, dict):
        raise WebhookPayloadError(f"Webhook item must be an object, got {type(payload)!r}")

    message_id = _first_text(payload, "id", "message_id", "messageId", "external_id", "externalId")
    if not message_id:
        raise WebhookPayloadError("Webhook payload requires stable message id field: id/message_id/messageId")

    from_name, from_email = _extract_sender(payload.get("from") or payload.get("sender") or payload.get("from_email"))
    if not from_email:
        from_email = _sanitize_text(_first_text(payload, "from_email", "fromEmail", "sender_email", "senderEmail"), MAX_TEXT_FIELD_CHARS).lower()
        from_name = _sanitize_text(_first_text(payload, "from_name", "fromName", "sender_name", "senderName"), MAX_TEXT_FIELD_CHARS)
    if not from_email:
        raise WebhookPayloadError("Webhook payload requires sender email in from.email/from/from_email")
    from_email = from_email.lower().strip()
    sender_domain = from_email.split("@", 1)[1] if "@" in from_email else ""

    subject = _sanitize_text(_first_text(payload, "subject"), MAX_TEXT_FIELD_CHARS)
    snippet_source = _first_text(payload, "snippet", "preview", "bodyPreview", "text", "body", "body_text", "bodyText")
    snippet = _sanitize_text(snippet_source, MAX_SNIPPET_CHARS)
    if not snippet and not subject:
        raise WebhookPayloadError("Webhook payload requires subject and/or bounded snippet/body preview")

    received_at = _normalize_timestamp(_first_text(payload, "received_at", "receivedAt", "date", "timestamp"))
    if not received_at:
        raise WebhookPayloadError("Webhook payload requires parseable received timestamp")

    provider = _sanitize_identifier(_first_text(payload, "provider", "source_provider", "sourceProvider") or DEFAULT_PROVIDER)
    workflow = _source_workflow(payload.get("source"))
    source = f"webhook:{provider}:{workflow}" if workflow else f"webhook:{provider}"

    message = EmailMessage(
        message_id=message_id,
        thread_id=_sanitize_text(_first_text(payload, "thread_id", "threadId", "conversation_id", "conversationId"), MAX_TEXT_FIELD_CHARS),
        from_email=from_email,
        from_name=from_name,
        sender_domain=sender_domain,
        to=_safe_recipient_list(payload.get("to")),
        subject=subject,
        body_text=snippet,
        received_at=_parse_iso_datetime(received_at),
        headers={},
    )
    classification = classify_message(message)

    return ReviewItem(
        item_id=f"webhook:{provider}:{message_id}",
        message_id=message_id,
        thread_id=message.thread_id,
        from_email=from_email,
        from_name=from_name,
        sender_domain=sender_domain,
        subject=subject,
        snippet=snippet,
        received_at=received_at,
        classification=classification.classification,
        confidence=classification.confidence,
        recommended_action=classification.recommended_action,
        reasons=[_sanitize_text(reason, MAX_TEXT_FIELD_CHARS) for reason in classification.reasons],
        sender_strike_level=0,
        draft_reply="",
        allowed_actions=list(SUPPORTED_ACTIONS),
        status="pending",
        source=source,
        mock_only=True,
        safety_note=MOCK_SAFETY_NOTE,
    )


def _extract_payload_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("items", "events", "messages"):
            if key in payload:
                items = payload[key]
                break
        else:
            items = [payload]
    else:
        raise WebhookPayloadError("Webhook import must be an object, list, or object with items/events/messages")

    if not isinstance(items, list):
        raise WebhookPayloadError("Webhook collection field must be a list")
    if not items:
        return []
    if not all(isinstance(item, dict) for item in items):
        raise WebhookPayloadError("Webhook collection must contain only objects")
    return items


def _first_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (str, int, float)):
            return _sanitize_text(str(value), MAX_SNIPPET_CHARS)
    return ""


def _extract_sender(value: Any) -> tuple[str, str]:
    if isinstance(value, dict):
        name = _sanitize_text(str(value.get("name") or value.get("displayName") or ""), MAX_TEXT_FIELD_CHARS)
        email = _sanitize_text(str(value.get("email") or value.get("address") or ""), MAX_TEXT_FIELD_CHARS).lower()
        return name, email
    if isinstance(value, str):
        parsed = getaddresses([value])
        if parsed and parsed[0][1]:
            return _sanitize_text(parsed[0][0], MAX_TEXT_FIELD_CHARS), _sanitize_text(parsed[0][1], MAX_TEXT_FIELD_CHARS).lower()
        return "", _sanitize_text(value, MAX_TEXT_FIELD_CHARS).lower()
    return "", ""


def _safe_recipient_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [_sanitize_text(addr, MAX_TEXT_FIELD_CHARS).lower() for _, addr in getaddresses([value]) if addr]
    if isinstance(value, list):
        recipients: list[str] = []
        for row in value[:25]:
            if isinstance(row, dict):
                email = row.get("email") or row.get("address")
            else:
                email = row
            if isinstance(email, str) and email:
                recipients.append(_sanitize_text(email, MAX_TEXT_FIELD_CHARS).lower())
        return recipients
    return []


def _source_workflow(source: Any) -> str:
    if isinstance(source, dict):
        for key in ("workflow", "workflowName", "name", "node"):
            if key in source and not _SECRET_KEY_RE.search(key):
                return _sanitize_identifier(str(source.get(key) or ""))
    if isinstance(source, str):
        return _sanitize_identifier(source)
    return ""


def _sanitize_identifier(value: str) -> str:
    value = _sanitize_text(value, 80).lower()
    value = re.sub(r"[^a-z0-9_.-]+", "-", value).strip("-._")
    return value or DEFAULT_PROVIDER


def _sanitize_text(value: str, max_chars: int) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = _CONTROL_RE.sub(" ", value).replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    for pattern in _SECRET_VALUE_PATTERNS:
        value = pattern.sub("[redacted]", value)
    value = value.strip()
    if len(value) > max_chars:
        suffix = "…[truncated]"
        value = value[: max(0, max_chars - len(suffix))].rstrip() + suffix
    return value


def _normalize_timestamp(value: str) -> str:
    value = _sanitize_text(value, MAX_TEXT_FIELD_CHARS)
    if not value:
        return ""
    parsed = _parse_iso_datetime(value)
    if parsed:
        return parsed.isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
