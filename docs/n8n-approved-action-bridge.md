# n8n Approved Action Bridge — Dry Run

This package is the first provider-bridge step after Phase 8 approved action export. It consumes BotFucker's `approved-actions.json` bundle and validates what would happen next, without touching a live mailbox.

This is deliberately dry-run. The bridge does not send mail, does not move mail, does not delete mail, does not archive mail, and does not update provider labels, whitelists, or blacklists. Provider credentials stay in n8n; BotFucker core still exports approved intent only.

## Files

- [`docs/n8n-approved-action-bridge.json`](n8n-approved-action-bridge.json): importable n8n dry-run workflow starter.
- [`docs/provider-auth-plan.md`](provider-auth-plan.md): boundary plan and future live-action rules.
- [`docs/n8n-workflow.json`](n8n-workflow.json): import-side workflow that feeds the local review queue.

## Input contract

The workflow expects the Phase 8 export schema:

```json
{
  "schema": "botfucker.approved_actions.v1",
  "safety_scope": "provider_action_export_only",
  "provider_execution": "not_performed",
  "cursor": {
    "since_audit_id": null,
    "last_audit_id": "audit-0001"
  },
  "actions": [
    {
      "audit_id": "audit-0001",
      "item_id": "webhook:gmail:gmail-msg-123",
      "message_id": "gmail-msg-123",
      "thread_id": "gmail-thread-7",
      "provider": "gmail",
      "approved_action": "approve_warning",
      "approved_by": "human",
      "approved_at": "2026-05-14T21:45:00Z",
      "draft_reply": "Human-reviewed warning text",
      "safety_scope": "provider_action_export_only",
      "provider_execution": "not_performed"
    }
  ]
}
```

Generate it locally with:

```bash
python3 -m botfucker.review_cli \
  --db botfucker_review.sqlite3 \
  export-approved-actions > approved-actions.json
```

Cursored export for dedupe/resume:

```bash
python3 -m botfucker.review_cli \
  --db botfucker_review.sqlite3 \
  export-approved-actions --since-audit-id audit-0001 > approved-actions.json
```

## Environment variables

Set these in the n8n runtime or edit the workflow locally:

```bash
export BOTFUCKER_APPROVED_ACTIONS="/path/to/approved-actions.json"
export BOTFUCKER_PROCESSED_AUDIT_IDS="audit-0001,audit-0002"
```

`BOTFUCKER_PROCESSED_AUDIT_IDS` is the starter dry-run dedupe source. A later live bridge should replace that with durable storage, but it must still dedupe by `audit_id` before touching a provider.

## Workflow behavior

1. **Read approved-actions.json** reads the Phase 8 export bundle.
2. **Validate And Dedupe Approved Actions** requires schema `botfucker.approved_actions.v1`, requires `safety_scope: provider_action_export_only`, filters already-processed `audit_id` values, and accepts only `approve_warning` actions with `provider_execution: not_performed`.
3. **Dry Run Provider Action Log** emits `dry_run: true`, `would_execute`, `audit_id`, provider identifiers, and `provider_execution: not_performed`.

There are intentionally no Gmail, Microsoft, IMAP, SMTP, send-mail, move-mail, delete-mail, archive, or label mutation nodes in this starter. If someone wires those in before the dry-run contract is reviewed, congratulations, they found the rake and stepped on it.

## Safety checklist before live bridge work

- Import workflow has already fetched and normalized mail.
- BotFucker local UI recorded a human approval.
- `export-approved-actions` generated the bundle.
- Bridge validates `botfucker.approved_actions.v1`.
- Bridge dedupes by `audit_id`.
- Bridge starts in dry-run/log-only mode.
- Provider credentials stay in n8n.
- BotFucker local UI still does not perform provider actions directly.

## Future live bridge rules

When this graduates from dry-run to live provider execution:

- keep the live workflow separate from the import workflow
- require explicit enablement
- retain dry-run mode
- persist processed `audit_id` values durably
- log each attempted provider action and result
- prefer archive/quarantine over delete
- never execute unapproved, dismissed, whitelist, or blacklist events unless those action types get their own reviewed export contract
- never expose provider tokens or private headers to BotFucker core or the browser UI
