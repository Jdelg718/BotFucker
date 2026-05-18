"""Durable provider-bridge ledger scaffold.

This module records bridge idempotency state only. It does not call Gmail,
Microsoft, IMAP, SMTP, n8n, HTTP APIs, or any provider mutation surface. A
future operator-owned bridge can use this before provider mutation to claim an
approved ``audit_id`` and avoid duplicate execution.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BRIDGE_LEDGER_EFFECT_SCOPE = "bridge_ledger_state_only"
APPROVED_ACTIONS_SCHEMA = "botfucker.approved_actions.v1"
REQUIRED_SAFETY_SCOPE = "provider_action_export_only"
REQUIRED_PROVIDER_EXECUTION = "not_performed"
ALLOWED_APPROVED_ACTIONS = {"approve_warning"}

PENDING = "pending"
PROCESSED = "processed"
FAILED = "failed"
ROLLED_BACK = "rolled_back"
VALID_STATUSES = {PENDING, PROCESSED, FAILED, ROLLED_BACK}


class BridgeLedgerError(ValueError):
    """Raised when bridge ledger state cannot be read or mutated safely."""


@dataclass(frozen=True)
class BridgeLedgerRecord:
    """One durable idempotency record keyed by approved-action ``audit_id``."""

    audit_id: str
    action_id: str
    provider: str
    approved_action: str
    message_id: str
    thread_id: str
    status: str
    dry_run: bool
    provider_result_id: str
    processed_at: str
    processed_by_workflow: str
    effect_scope: str = BRIDGE_LEDGER_EFFECT_SCOPE


@dataclass(frozen=True)
class BridgeLedgerClaim:
    """Result of trying to claim an ``audit_id`` before provider mutation."""

    acquired: bool
    record: BridgeLedgerRecord


class DurableBridgeLedger:
    """SQLite-backed durable bridge idempotency ledger.

    The ledger is intentionally narrow: it stores only IDs and bridge status. It
    stores no OAuth tokens, provider credentials, message subjects, snippets, raw
    headers, or message bodies, and it performs no provider-side work.
    """

    def __init__(self, path: str | Path = "botfucker_bridge_ledger.sqlite3") -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path.parent) != ".":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def __enter__(self) -> "DurableBridgeLedger":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bridge_processed_audits (
                audit_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                approved_action TEXT NOT NULL DEFAULT '',
                message_id TEXT NOT NULL DEFAULT '',
                thread_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                dry_run INTEGER NOT NULL DEFAULT 1,
                provider_result_id TEXT NOT NULL DEFAULT '',
                processed_at TEXT NOT NULL,
                processed_by_workflow TEXT NOT NULL DEFAULT '',
                effect_scope TEXT NOT NULL DEFAULT 'bridge_ledger_state_only'
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bridge_processed_status ON bridge_processed_audits(status)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bridge_processed_provider ON bridge_processed_audits(provider)"
        )
        self.connection.commit()

    def claim_action(
        self,
        bundle: dict[str, Any],
        action: dict[str, Any],
        *,
        processed_by_workflow: str,
        dry_run: bool = True,
    ) -> BridgeLedgerClaim:
        """Claim an approved action's ``audit_id`` before provider mutation.

        Returns ``acquired=True`` only for the first claim of an ``audit_id``.
        Repeated claims return the existing record with ``acquired=False``.
        This method validates the approved-action export safety markers before
        inserting ledger state.
        """

        normalized = _normalize_action(bundle, action)
        workflow = _require_nonempty(processed_by_workflow, "processed_by_workflow")
        now = _now()

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO bridge_processed_audits (
                    audit_id, action_id, provider, approved_action, message_id,
                    thread_id, status, dry_run, provider_result_id, processed_at,
                    processed_by_workflow, effect_scope
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized["audit_id"],
                    normalized["action_id"],
                    normalized["provider"],
                    normalized["approved_action"],
                    normalized["message_id"],
                    normalized["thread_id"],
                    PENDING,
                    1 if dry_run else 0,
                    "",
                    now,
                    workflow,
                    BRIDGE_LEDGER_EFFECT_SCOPE,
                ),
            )
            acquired = cursor.rowcount == 1
            row = self.connection.execute(
                "SELECT * FROM bridge_processed_audits WHERE audit_id = ?",
                (normalized["audit_id"],),
            ).fetchone()

        if row is None:  # pragma: no cover - defensive guard for corrupted DB handles.
            raise BridgeLedgerError(f"Could not read claimed audit_id: {normalized['audit_id']}")
        return BridgeLedgerClaim(acquired=acquired, record=_record_from_row(row))

    def mark_processed(
        self,
        audit_id: str,
        *,
        provider_result_id: str = "",
        processed_by_workflow: str | None = None,
    ) -> BridgeLedgerRecord:
        """Mark a claimed audit as processed after provider-side work completes."""

        return self._update_status(
            audit_id,
            PROCESSED,
            provider_result_id=provider_result_id,
            processed_by_workflow=processed_by_workflow,
        )

    def mark_failed(
        self,
        audit_id: str,
        *,
        provider_result_id: str = "",
        processed_by_workflow: str | None = None,
    ) -> BridgeLedgerRecord:
        """Record an attempted action that failed and requires manual review."""

        return self._update_status(
            audit_id,
            FAILED,
            provider_result_id=provider_result_id,
            processed_by_workflow=processed_by_workflow,
        )

    def mark_rolled_back(
        self,
        audit_id: str,
        *,
        provider_result_id: str = "",
        processed_by_workflow: str | None = None,
    ) -> BridgeLedgerRecord:
        """Record rollback/remediation status without retrying the action."""

        return self._update_status(
            audit_id,
            ROLLED_BACK,
            provider_result_id=provider_result_id,
            processed_by_workflow=processed_by_workflow,
        )

    def _update_status(
        self,
        audit_id: str,
        status: str,
        *,
        provider_result_id: str = "",
        processed_by_workflow: str | None = None,
    ) -> BridgeLedgerRecord:
        audit_id = _require_nonempty(audit_id, "audit_id")
        if status not in VALID_STATUSES:
            raise BridgeLedgerError(f"Unsupported ledger status: {status}")

        existing = self.get(audit_id)
        _validate_status_transition(existing.status, status)
        workflow = processed_by_workflow if processed_by_workflow is not None else existing.processed_by_workflow
        workflow = _require_nonempty(workflow, "processed_by_workflow")

        with self.connection:
            self.connection.execute(
                """
                UPDATE bridge_processed_audits
                SET status = ?, provider_result_id = ?, processed_at = ?, processed_by_workflow = ?
                WHERE audit_id = ?
                """,
                (status, provider_result_id or "", _now(), workflow, audit_id),
            )
        return self.get(audit_id)

    def get(self, audit_id: str) -> BridgeLedgerRecord:
        audit_id = _require_nonempty(audit_id, "audit_id")
        row = self.connection.execute(
            "SELECT * FROM bridge_processed_audits WHERE audit_id = ?",
            (audit_id,),
        ).fetchone()
        if row is None:
            raise BridgeLedgerError(f"Unknown bridge ledger audit_id: {audit_id}")
        return _record_from_row(row)

    def has_processed(self, audit_id: str) -> bool:
        """Return true only when an audit is durably marked processed."""

        try:
            return self.get(audit_id).status == PROCESSED
        except BridgeLedgerError:
            return False

    def list_records(self) -> list[BridgeLedgerRecord]:
        rows = self.connection.execute(
            "SELECT * FROM bridge_processed_audits ORDER BY processed_at ASC, audit_id ASC"
        ).fetchall()
        return [_record_from_row(row) for row in rows]


def _normalize_action(bundle: dict[str, Any], action: dict[str, Any]) -> dict[str, str]:
    actions = bundle.get("actions")
    if not isinstance(actions, list):
        raise BridgeLedgerError("Approved-actions bundle must include an actions list")
    if action not in actions:
        raise BridgeLedgerError("Approved action must be present in the approved-actions bundle")

    if bundle.get("schema") != APPROVED_ACTIONS_SCHEMA:
        raise BridgeLedgerError(f"Unsupported approved-actions schema: {bundle.get('schema')!r}")
    if bundle.get("safety_scope") != REQUIRED_SAFETY_SCOPE:
        raise BridgeLedgerError("Approved-actions bundle has unsafe safety_scope")
    if bundle.get("provider_execution") != REQUIRED_PROVIDER_EXECUTION:
        raise BridgeLedgerError("Approved-actions bundle must not have provider execution already performed")
    if action.get("safety_scope") != REQUIRED_SAFETY_SCOPE:
        raise BridgeLedgerError("Approved action has unsafe safety_scope")
    if action.get("provider_execution") != REQUIRED_PROVIDER_EXECUTION:
        raise BridgeLedgerError("Approved action must have provider_execution: not_performed")

    audit_id = _require_nonempty(action.get("audit_id", ""), "audit_id")
    approved_action = _require_nonempty(action.get("approved_action", ""), "approved_action")
    if approved_action not in ALLOWED_APPROVED_ACTIONS:
        raise BridgeLedgerError(f"Unsupported approved action for bridge ledger scaffold: {approved_action}")
    return {
        "audit_id": audit_id,
        "action_id": _require_nonempty(action.get("action_id") or f"bf-action-{audit_id}", "action_id"),
        "provider": _require_nonempty(action.get("provider", ""), "provider"),
        "approved_action": approved_action,
        "message_id": _require_nonempty(action.get("message_id", ""), "message_id"),
        "thread_id": _require_nonempty(action.get("thread_id", ""), "thread_id"),
    }


def _validate_status_transition(current: str, target: str) -> None:
    if current not in VALID_STATUSES:
        raise BridgeLedgerError(f"Unknown current bridge ledger status: {current}")
    if current == target:
        return
    allowed = {
        PENDING: {PROCESSED, FAILED, ROLLED_BACK},
        FAILED: {ROLLED_BACK},
        PROCESSED: {ROLLED_BACK},
        ROLLED_BACK: set(),
    }
    if target not in allowed[current]:
        raise BridgeLedgerError(f"Unsafe bridge ledger status transition: {current} -> {target}")


def _record_from_row(row: sqlite3.Row) -> BridgeLedgerRecord:
    return BridgeLedgerRecord(
        audit_id=row["audit_id"],
        action_id=row["action_id"],
        provider=row["provider"],
        approved_action=row["approved_action"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        status=row["status"],
        dry_run=bool(row["dry_run"]),
        provider_result_id=row["provider_result_id"],
        processed_at=row["processed_at"],
        processed_by_workflow=row["processed_by_workflow"],
        effect_scope=row["effect_scope"],
    )


def _require_nonempty(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise BridgeLedgerError(f"Bridge ledger requires {name}")
    return text


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
