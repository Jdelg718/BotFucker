"""Durable local SQLite review queue storage.

This module is intentionally local-only. It records review items and review audit
state, but it never calls email providers, sends mail, moves mail, deletes mail,
or writes provider/auth secrets.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_queue import AuditEvent, ReviewItem, SUPPORTED_ACTIONS, MOCK_SAFETY_NOTE

SQLITE_EFFECT_SCOPE = "local_sqlite_review_state_only"


class ReviewStoreError(ValueError):
    """Raised when durable local review state cannot be read or mutated."""


class DurableReviewStore:
    """SQLite-backed durable review queue and audit log.

    The store is safe by construction: actions only change local SQLite rows and
    append audit events. They are review approvals/decisions, not provider-side
    effects.
    """

    def __init__(self, path: str | Path = "botfucker_review.sqlite3") -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path.parent) != ".":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def __enter__(self) -> "DurableReviewStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_items (
                item_id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL DEFAULT '',
                thread_id TEXT NOT NULL DEFAULT '',
                from_email TEXT NOT NULL DEFAULT '',
                from_name TEXT NOT NULL DEFAULT '',
                sender_domain TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL DEFAULT '',
                snippet TEXT NOT NULL DEFAULT '',
                received_at TEXT NOT NULL DEFAULT '',
                classification TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                recommended_action TEXT NOT NULL DEFAULT '',
                reasons TEXT NOT NULL DEFAULT '[]',
                sender_strike_level INTEGER NOT NULL DEFAULT 0,
                draft_reply TEXT NOT NULL DEFAULT '',
                allowed_actions TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                source TEXT NOT NULL DEFAULT 'local_import',
                mock_only INTEGER NOT NULL DEFAULT 1,
                safety_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_review_items_status ON review_items(status)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_review_items_sender ON review_items(from_email)")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_audit_events (
                event_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                mock_only INTEGER NOT NULL DEFAULT 1,
                effect_scope TEXT NOT NULL DEFAULT 'local_sqlite_review_state_only',
                safety_note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(item_id) REFERENCES review_items(item_id)
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_review_audit_item ON review_audit_events(item_id)")
        self.connection.commit()

    def upsert_item(self, item: ReviewItem | dict[str, Any]) -> bool:
        """Insert or refresh one review item.

        Returns True only when a new row is inserted. Existing item status is
        preserved so repeated imports do not undo human review decisions.
        """
        review_item = coerce_review_item(item)
        if not review_item.item_id:
            raise ReviewStoreError("Review item requires item_id")

        now = _now()
        existing = self.connection.execute(
            "SELECT status, created_at FROM review_items WHERE item_id = ?",
            (review_item.item_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        status = existing["status"] if existing else review_item.status
        inserted = existing is None

        self.connection.execute(
            """
            INSERT INTO review_items (
                item_id, message_id, thread_id, from_email, from_name,
                sender_domain, subject, snippet, received_at, classification,
                confidence, recommended_action, reasons, sender_strike_level,
                draft_reply, allowed_actions, status, source, mock_only,
                safety_note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                message_id = excluded.message_id,
                thread_id = excluded.thread_id,
                from_email = excluded.from_email,
                from_name = excluded.from_name,
                sender_domain = excluded.sender_domain,
                subject = excluded.subject,
                snippet = excluded.snippet,
                received_at = excluded.received_at,
                classification = excluded.classification,
                confidence = excluded.confidence,
                recommended_action = excluded.recommended_action,
                reasons = excluded.reasons,
                sender_strike_level = excluded.sender_strike_level,
                draft_reply = excluded.draft_reply,
                allowed_actions = excluded.allowed_actions,
                source = excluded.source,
                mock_only = excluded.mock_only,
                safety_note = excluded.safety_note,
                updated_at = excluded.updated_at
            """,
            (
                review_item.item_id,
                review_item.message_id,
                review_item.thread_id,
                review_item.from_email.lower(),
                review_item.from_name,
                review_item.sender_domain.lower(),
                review_item.subject,
                review_item.snippet,
                review_item.received_at,
                review_item.classification,
                float(review_item.confidence),
                review_item.recommended_action,
                json.dumps(list(review_item.reasons), sort_keys=True),
                int(review_item.sender_strike_level),
                review_item.draft_reply,
                json.dumps(list(review_item.allowed_actions), sort_keys=True),
                status,
                review_item.source,
                1 if review_item.mock_only else 0,
                review_item.safety_note or MOCK_SAFETY_NOTE,
                created_at,
                now,
            ),
        )
        self.connection.commit()
        return inserted

    def upsert_items(self, items: list[ReviewItem] | tuple[ReviewItem, ...] | list[dict[str, Any]]) -> int:
        inserted = 0
        for item in items:
            inserted += 1 if self.upsert_item(item) else 0
        return inserted

    def get_item(self, item_id: str) -> ReviewItem:
        row = self.connection.execute("SELECT * FROM review_items WHERE item_id = ?", (item_id,)).fetchone()
        if not row:
            raise ReviewStoreError(f"Unknown review item: {item_id}")
        return _item_from_row(row)

    def list_items(self, status: str | None = None) -> list[ReviewItem]:
        if status and status != "all":
            rows = self.connection.execute(
                "SELECT * FROM review_items WHERE status = ? ORDER BY received_at DESC, item_id ASC",
                (status,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM review_items ORDER BY received_at DESC, item_id ASC"
            ).fetchall()
        return [_item_from_row(row) for row in rows]

    def apply_action(self, item_id: str, action: str, actor: str = "review-cli", note: str = "") -> AuditEvent:
        if action not in SUPPORTED_ACTIONS:
            raise ReviewStoreError(f"Unsupported local review action: {action}")
        # Ensure item exists before recording an audit event.
        self.get_item(item_id)

        created_at = _now()
        next_id = self.connection.execute("SELECT COUNT(*) AS count FROM review_audit_events").fetchone()["count"] + 1
        event = AuditEvent(
            event_id=f"audit-{next_id:04d}",
            item_id=item_id,
            action=action,
            actor=actor or "review-cli",
            created_at=created_at,
            note=note,
            mock_only=True,
            effect_scope=SQLITE_EFFECT_SCOPE,
            safety_note=MOCK_SAFETY_NOTE,
        )
        self.connection.execute(
            """
            INSERT INTO review_audit_events (
                event_id, item_id, action, actor, created_at, note,
                mock_only, effect_scope, safety_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.item_id,
                event.action,
                event.actor,
                event.created_at,
                event.note,
                1,
                event.effect_scope,
                event.safety_note,
            ),
        )
        self.connection.execute(
            "UPDATE review_items SET status = 'actioned', updated_at = ? WHERE item_id = ?",
            (created_at, item_id),
        )
        self.connection.commit()
        return event

    def list_audit_events(self, item_id: str | None = None) -> list[AuditEvent]:
        if item_id:
            rows = self.connection.execute(
                "SELECT * FROM review_audit_events WHERE item_id = ? ORDER BY created_at ASC, event_id ASC",
                (item_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM review_audit_events ORDER BY created_at ASC, event_id ASC"
            ).fetchall()
        return [_event_from_row(row) for row in rows]


def coerce_review_item(data: ReviewItem | dict[str, Any]) -> ReviewItem:
    if isinstance(data, ReviewItem):
        return data
    if not isinstance(data, dict):
        raise ReviewStoreError(f"Unsupported review item payload: {type(data)!r}")

    return ReviewItem(
        item_id=str(data.get("item_id", "")),
        message_id=str(data.get("message_id", "")),
        thread_id=str(data.get("thread_id", "")),
        from_email=str(data.get("from_email", "")).lower(),
        from_name=str(data.get("from_name", "")),
        sender_domain=str(data.get("sender_domain", "")).lower(),
        subject=str(data.get("subject", "")),
        snippet=str(data.get("snippet", "")),
        received_at=str(data.get("received_at", "")),
        classification=str(data.get("classification", "unknown_review_needed")),
        confidence=float(data.get("confidence", 0.0)),
        recommended_action=str(data.get("recommended_action", "review")),
        reasons=list(data.get("reasons", [])),
        sender_strike_level=int(data.get("sender_strike_level", 0)),
        draft_reply=str(data.get("draft_reply", "")),
        allowed_actions=list(data.get("allowed_actions", SUPPORTED_ACTIONS)),
        status=data.get("status", "pending") if data.get("status", "pending") in {"pending", "actioned"} else "pending",
        source=str(data.get("source", "local_import")),
        mock_only=bool(data.get("mock_only", True)),
        safety_note=str(data.get("safety_note", MOCK_SAFETY_NOTE)),
    )


def _item_from_row(row: sqlite3.Row) -> ReviewItem:
    return ReviewItem(
        item_id=row["item_id"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        from_email=row["from_email"],
        from_name=row["from_name"],
        sender_domain=row["sender_domain"],
        subject=row["subject"],
        snippet=row["snippet"],
        received_at=row["received_at"],
        classification=row["classification"],
        confidence=float(row["confidence"]),
        recommended_action=row["recommended_action"],
        reasons=json.loads(row["reasons"] or "[]"),
        sender_strike_level=int(row["sender_strike_level"]),
        draft_reply=row["draft_reply"],
        allowed_actions=json.loads(row["allowed_actions"] or "[]"),
        status=row["status"],
        source=row["source"],
        mock_only=bool(row["mock_only"]),
        safety_note=row["safety_note"],
    )


def _event_from_row(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        item_id=row["item_id"],
        action=row["action"],
        actor=row["actor"],
        created_at=row["created_at"],
        note=row["note"],
        mock_only=bool(row["mock_only"]),
        effect_scope=row["effect_scope"],
        safety_note=row["safety_note"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
