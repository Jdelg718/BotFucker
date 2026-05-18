# Phase 15 — Emergency-Stop Bridge Rehearsal

Phase 15 proves the brakes before anyone touches a live mailbox.

This is a dry-run-only bridge rehearsal that uses the durable Phase 14 ledger and verifies the emergency stop exits before any provider mutation slot is claimed.

## What exists

- `botfucker.bridge_rehearsal.rehearse_approved_actions()`
- `botfucker.bridge_ledger.DurableBridgeLedger.mark_dry_run_logged()`
- `tests/test_bridge_rehearsal.py`

## Safety boundary

This phase performs:

- no OAuth
- no provider credentials
- no Gmail/Microsoft/IMAP/SMTP calls
- no n8n calls
- no HTTP calls
- no live provider mutation nodes
- no message send/move/delete/archive/label behavior

Provider execution remains exactly:

```text
not_performed
```

## Rehearsal lifecycle

### Emergency stop on

Default behavior is stopped.

```python
outcomes = rehearse_approved_actions(bundle, ledger, emergency_stop=True)
```

Expected result:

- status: `blocked_by_emergency_stop`
- `ledger_acquired: false`
- `would_execute: false`
- no ledger row is created
- provider execution is `not_performed`

This proves the stop switch exits before claiming a provider mutation slot.

### Emergency stop off, dry-run on

```python
outcomes = rehearse_approved_actions(bundle, ledger, emergency_stop=False)
```

Expected result for the first valid action:

- validates the approved-action bundle
- claims the durable `audit_id`
- marks the row `dry_run_logged`
- returns `would_execute: true`
- provider execution remains `not_performed`

### Duplicate replay

Running the same bundle again returns:

- status: `duplicate_skipped`
- `ledger_acquired: false`
- `would_execute: false`

The durable ledger prevents replay by `audit_id`.

## Dry-run only

`dry_run=False` raises `BridgeLedgerError`. There is no hidden live mode in Phase 15.

## Accepted input

The rehearsal inherits Phase 14 ledger validation:

- bundle schema must be `botfucker.approved_actions.v1`
- bundle/action safety scope must be `provider_action_export_only`
- bundle/action provider execution must be `not_performed`
- action must be present in the bundle's `actions` list
- `audit_id`, provider, message ID, and thread ID must be present
- approved action is limited to `approve_warning`

Anything else fails closed.

## Future live bridge requirement

Before live provider mutation exists, Rex/Gus must review a separate provider-specific bridge artifact with:

- n8n-owned credentials only
- emergency stop tested against that exact workflow
- durable ledger claim before provider mutation
- provider sandbox/manual evidence
- rollback/remediation procedure
- structured logs with no credentials or raw message bodies

Until then, this is the brake test. No fireworks, no live inbox surgery.
