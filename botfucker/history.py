"""SQLite sender history and strike tracking."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import ClassificationResult, EmailMessage


@dataclass(frozen=True)
class SenderRecord:
    sender_email: str
    sender_domain: str
    first_seen: str
    last_seen: str
    message_count: int
    classification_counts: dict[str, int]
    warnings_sent: int
    last_warning_date: str | None
    strike_level: int
    whitelist_status: bool
    blacklist_status: bool


class SenderHistory:
    def __init__(self, path: str | Path = "botfucker_history.sqlite3") -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SenderHistory":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS senders (
                sender_email TEXT PRIMARY KEY,
                sender_domain TEXT NOT NULL,
                company_name TEXT DEFAULT '',
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                classification_counts TEXT NOT NULL DEFAULT '{}',
                warnings_sent INTEGER NOT NULL DEFAULT 0,
                last_warning_date TEXT,
                strike_level INTEGER NOT NULL DEFAULT 0,
                whitelist_status INTEGER NOT NULL DEFAULT 0,
                blacklist_status INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_senders_domain ON senders(sender_domain)")
        self.connection.commit()

    def get_sender(self, sender_email: str) -> SenderRecord | None:
        row = self.connection.execute(
            "SELECT * FROM senders WHERE sender_email = ?",
            (sender_email.lower(),),
        ).fetchone()
        return self._record_from_row(row) if row else None

    def get_domain_strike_level(self, sender_domain: str) -> int:
        row = self.connection.execute(
            "SELECT MAX(strike_level) AS max_strike FROM senders WHERE sender_domain = ?",
            (sender_domain.lower(),),
        ).fetchone()
        return int(row["max_strike"] or 0) if row else 0

    def is_blacklisted(self, sender_email: str, sender_domain: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM senders
            WHERE (sender_email = ? OR sender_domain = ?) AND blacklist_status = 1
            LIMIT 1
            """,
            (sender_email.lower(), sender_domain.lower()),
        ).fetchone()
        return row is not None

    def is_whitelisted(self, sender_email: str, sender_domain: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM senders
            WHERE (sender_email = ? OR sender_domain = ?) AND whitelist_status = 1
            LIMIT 1
            """,
            (sender_email.lower(), sender_domain.lower()),
        ).fetchone()
        return row is not None

    def record_classification(self, message: EmailMessage, result: ClassificationResult) -> SenderRecord:
        now = _now()
        sender_email = message.from_email.lower()
        sender_domain = message.sender_domain.lower()
        existing = self.get_sender(sender_email)
        if existing:
            counts = dict(existing.classification_counts)
            counts[result.classification] = counts.get(result.classification, 0) + 1
            self.connection.execute(
                """
                UPDATE senders
                SET sender_domain = ?, last_seen = ?, message_count = message_count + 1,
                    classification_counts = ?
                WHERE sender_email = ?
                """,
                (sender_domain, now, json.dumps(counts, sort_keys=True), sender_email),
            )
        else:
            counts = {result.classification: 1}
            self.connection.execute(
                """
                INSERT INTO senders (
                    sender_email, sender_domain, first_seen, last_seen,
                    message_count, classification_counts
                ) VALUES (?, ?, ?, ?, 1, ?)
                """,
                (sender_email, sender_domain, now, now, json.dumps(counts, sort_keys=True)),
            )
        self.connection.commit()
        record = self.get_sender(sender_email)
        assert record is not None
        return record

    def issue_warning(self, sender_email: str, strike_level: int | None = None) -> SenderRecord:
        sender_email = sender_email.lower()
        existing = self.get_sender(sender_email)
        if not existing:
            raise KeyError(f"Unknown sender: {sender_email}")

        next_strike = strike_level if strike_level is not None else min(existing.strike_level + 1, 4)
        now = _now()
        self.connection.execute(
            """
            UPDATE senders
            SET warnings_sent = warnings_sent + 1,
                last_warning_date = ?,
                strike_level = MAX(strike_level, ?)
            WHERE sender_email = ?
            """,
            (now, next_strike, sender_email),
        )
        self.connection.commit()
        record = self.get_sender(sender_email)
        assert record is not None
        return record

    def set_whitelist(self, sender_email: str, enabled: bool = True) -> None:
        self.connection.execute(
            "UPDATE senders SET whitelist_status = ? WHERE sender_email = ?",
            (1 if enabled else 0, sender_email.lower()),
        )
        self.connection.commit()

    def set_blacklist(self, sender_email: str, enabled: bool = True) -> None:
        self.connection.execute(
            "UPDATE senders SET blacklist_status = ? WHERE sender_email = ?",
            (1 if enabled else 0, sender_email.lower()),
        )
        self.connection.commit()

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> SenderRecord:
        return SenderRecord(
            sender_email=row["sender_email"],
            sender_domain=row["sender_domain"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            message_count=int(row["message_count"]),
            classification_counts=json.loads(row["classification_counts"] or "{}"),
            warnings_sent=int(row["warnings_sent"]),
            last_warning_date=row["last_warning_date"],
            strike_level=int(row["strike_level"]),
            whitelist_status=bool(row["whitelist_status"]),
            blacklist_status=bool(row["blacklist_status"]),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
