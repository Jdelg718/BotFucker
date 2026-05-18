"""Dry-run bridge rehearsal with emergency-stop proof.

This module is deliberately provider-free. It does not call Gmail, Microsoft,
IMAP, SMTP, n8n, HTTP APIs, or any provider mutation surface. It proves the
operator-side gates that must happen before a future reviewed live bridge:

1. emergency stop is checked first;
2. dry-run remains mandatory;
3. the durable bridge ledger is claimed before any would-execute result;
4. duplicate audit IDs are skipped rather than replayed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from botfucker.bridge_ledger import (
    BridgeLedgerError,
    DurableBridgeLedger,
    REQUIRED_PROVIDER_EXECUTION,
)

BRIDGE_REHEARSAL_WORKFLOW = "botfucker-bridge-rehearsal-v1"


@dataclass(frozen=True)
class BridgeRehearsalOutcome:
    """One action's dry-run bridge rehearsal result."""

    audit_id: str
    approved_action: str
    provider: str
    status: str
    dry_run: bool
    ledger_acquired: bool
    provider_execution: str = REQUIRED_PROVIDER_EXECUTION
    would_execute: bool = False
    reason: str = ""


def rehearse_approved_actions(
    bundle: dict[str, Any],
    ledger: DurableBridgeLedger,
    *,
    emergency_stop: bool = True,
    dry_run: bool = True,
    processed_by_workflow: str = BRIDGE_REHEARSAL_WORKFLOW,
) -> list[BridgeRehearsalOutcome]:
    """Rehearse approved actions through the safety gates without side effects.

    Phase 15 intentionally supports dry-run only. Passing ``dry_run=False`` is an
    error, not a secret live mode. When ``emergency_stop`` is enabled, actions
    are blocked before the ledger is claimed so operators can prove the stop
    switch exits before any provider mutation slot is acquired.
    """

    if not dry_run:
        raise BridgeLedgerError("Bridge rehearsal is dry-run only; live provider execution is out of scope")

    actions = bundle.get("actions")
    if not isinstance(actions, list):
        raise BridgeLedgerError("Approved-actions bundle must include an actions list")

    outcomes: list[BridgeRehearsalOutcome] = []
    for action in actions:
        if not isinstance(action, dict):
            raise BridgeLedgerError("Approved action entries must be objects")

        if emergency_stop:
            outcomes.append(
                BridgeRehearsalOutcome(
                    audit_id=str(action.get("audit_id") or ""),
                    approved_action=str(action.get("approved_action") or ""),
                    provider=str(action.get("provider") or ""),
                    status="blocked_by_emergency_stop",
                    dry_run=True,
                    ledger_acquired=False,
                    would_execute=False,
                    reason="Emergency stop enabled before ledger claim or provider mutation",
                )
            )
            continue

        claim = ledger.claim_action(
            bundle,
            action,
            processed_by_workflow=processed_by_workflow,
            dry_run=True,
        )
        if claim.acquired:
            record = ledger.mark_dry_run_logged(
                claim.record.audit_id,
                processed_by_workflow=processed_by_workflow,
            )
            outcomes.append(
                BridgeRehearsalOutcome(
                    audit_id=record.audit_id,
                    approved_action=record.approved_action,
                    provider=record.provider,
                    status=record.status,
                    dry_run=True,
                    ledger_acquired=True,
                    would_execute=True,
                    reason="Dry-run rehearsal logged; provider execution not performed",
                )
            )
        else:
            outcomes.append(
                BridgeRehearsalOutcome(
                    audit_id=claim.record.audit_id,
                    approved_action=claim.record.approved_action,
                    provider=claim.record.provider,
                    status="duplicate_skipped",
                    dry_run=True,
                    ledger_acquired=False,
                    would_execute=False,
                    reason="Durable ledger already contains this audit_id",
                )
            )

    return outcomes
