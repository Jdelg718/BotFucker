# Phase 14 Durable Bridge Ledger Scaffold

Phase 14 adds a durable bridge ledger scaffold for future reviewed provider bridges. It is **not** a provider implementation: no OAuth, no provider credentials, no live provider mutation nodes, no Gmail/Microsoft/IMAP/SMTP calls, and no n8n activation changes.

The purpose is narrow and boring in the useful way: give a future n8n/operator-owned bridge a tested way to record approved `audit_id` state durably **before provider mutation** so duplicate sends/moves/actions are blocked by construction.

## Artifact

- `botfucker.bridge_ledger.DurableBridgeLedger`: a standard-library SQLite ledger keyed by `audit_id`.

Default local file name if used directly:

```text
botfucker_bridge_ledger.sqlite3
```

A future n8n deployment may instead map this shape to n8n Data Store, Postgres, or another operator-owned durable store. The required behavior is the same: claim `audit_id` before provider mutation, then mark the record processed/failed/rolled back after the bridge attempt is known.

## Safety boundary

This scaffold only records bridge ledger state:

```text
bridge_ledger_state_only
```

It does not:

- implement Gmail OAuth
- implement Microsoft OAuth
- store IMAP/SMTP passwords
- store OAuth access or refresh tokens
- store provider API keys, cookies, or private headers
- call Gmail, Microsoft, IMAP, SMTP, n8n, HTTP APIs, or live mailbox providers
- send replies
- move, delete, archive, label, whitelist, or blacklist provider-side messages
- add live provider mutation nodes to checked-in n8n workflows

The ledger stores only provider/action identifiers and execution state. It intentionally omits message subject, snippet, body, raw headers, and credential material.

## Required input

`claim_action()` requires the existing approved-action export contract:

```json
{
  "schema": "botfucker.approved_actions.v1",
  "safety_scope": "provider_action_export_only",
  "provider_execution": "not_performed",
  "actions": [
    {
      "audit_id": "audit-0001",
      "action_id": "bf-action-audit-0001",
      "message_id": "gmail-msg-123",
      "thread_id": "gmail-thread-7",
      "provider": "gmail",
      "approved_action": "approve_warning",
      "safety_scope": "provider_action_export_only",
      "provider_execution": "not_performed"
    }
  ]
}
```

The scaffold rejects bundles/actions that are missing the expected schema, safety scope, or `provider_execution: not_performed` marker.

## Ledger lifecycle

A future reviewed bridge should use this sequence:

1. Validate the approved-actions bundle.
2. Check emergency stop and provider/action enablement.
3. Call `claim_action()` for the action.
4. If `acquired` is false, stop before provider mutation because the `audit_id` was already claimed.
5. If `acquired` is true, the durable row is already `pending`.
6. Only after that pending row exists may the reviewed bridge approach a provider mutation node.
7. Mark the row `processed`, `failed`, or `rolled_back` after the attempt is known.
8. Never blindly retry a processed or ambiguous `audit_id`; require manual review.

Minimal Python example using fake/local IDs only:

```python
from botfucker.bridge_ledger import DurableBridgeLedger

bundle = {...}  # botfucker.approved_actions.v1 export
action = bundle["actions"][0]

with DurableBridgeLedger("botfucker_bridge_ledger.sqlite3") as ledger:
    claim = ledger.claim_action(
        bundle,
        action,
        processed_by_workflow="botfucker-reviewed-live-bridge-v1",
        dry_run=True,
    )
    if not claim.acquired:
        raise SystemExit("audit_id already claimed; stop before provider mutation")

    # Future reviewed provider bridge would run only after this point.
    # Phase 14 deliberately does not include that provider node/action.

    ledger.mark_processed(action["audit_id"], provider_result_id="dry-run-result-id")
```

## Stored fields

The SQLite table is `bridge_processed_audits`.

Stored fields:

- `audit_id` — primary idempotency key
- `action_id`
- `provider`
- `approved_action`
- `message_id`
- `thread_id`
- `status` — `pending`, `processed`, `failed`, or `rolled_back`
- `dry_run`
- `provider_result_id`
- `processed_at`
- `processed_by_workflow`
- `effect_scope` — always `bridge_ledger_state_only`

Not stored:

- message subject/snippet/body
- raw headers
- OAuth tokens
- API keys
- passwords
- cookies
- private provider headers

## Promotion gate remains closed

Phase 14 does not make the bridge live. Before any live provider mutation is connected, the Phase 13 gate still applies:

- one provider/action pair only
- dry-run evidence exists
- provider-specific sandbox/manual evidence exists
- emergency stop exits before provider mutation
- rollback/remediation is documented
- provider credentials remain in n8n/operator infrastructure only
- Rex/security approval is recorded
- Gus/ops approval is recorded
- checked-in starter workflows remain inactive and free of live mutation nodes

This phase is the seatbelt mount, not the rocket engine.
