# Phase 13 Reviewed Action Bridge Promotion Plan

Phase 13 is a promotion plan, not a provider implementation. It defines how one approved action type can move from n8n dry-run logs toward live provider execution after review, without adding OAuth, provider credentials, or live mailbox mutation nodes to BotFucker core.

The default remains boring and safe: BotFucker imports bounded provider-shaped JSON, records human review state locally, exports approved intent, and the n8n approved-action bridge stays dry-run until a separate reviewed live bridge is created and approved.

## Non-goals

Do not do these in Phase 13:

- Do not implement Gmail OAuth.
- Do not implement Microsoft OAuth.
- Do not add IMAP passwords, SMTP passwords, OAuth tokens, API keys, cookies, or provider credentials to BotFucker core.
- Do not add Gmail, Microsoft, IMAP, SMTP, send-mail, move-mail, delete-mail, archive, or label mutation nodes to the checked-in starter workflows.
- Do not activate the n8n workflows by default.
- Do not execute provider mutations from the local UI, review CLI, tests, samples, or docs examples.
- Do not promote more than one provider action type in a single reviewed change.

## Promotion target for the first live review

The first eligible live bridge review should be limited to one action type:

- Approved action: `approve_warning`
- Source schema: `botfucker.approved_actions.v1`
- Source requirement: human-approved SQLite audit event exported by `export-approved-actions`
- Initial live behavior candidate: send or draft a provider reply only after sandbox/manual validation
- Safer default: keep dry-run enabled and log `would_execute` until the security and ops checklists are signed off

Permanent deletion is out of scope. Whitelist, blacklist, archive, move, and label actions require their own export contracts and separate reviewed promotion plans.

## Credential ownership

Provider credentials belong in n8n only.

BotFucker core must never store or receive:

- OAuth access tokens
- OAuth refresh tokens
- provider API keys
- IMAP passwords
- SMTP passwords
- browser-visible provider cookies
- private provider headers

The local UI, local SQLite review DB, JSON samples, tests, and checked-in n8n workflow exports must remain credential-free. n8n can own provider connections later, but a live bridge must be created as a separate operator-owned workflow after review.

## Required live bridge shape

A future live bridge must be separate from both checked-in starters:

1. Import workflow: provider fetch to normalized local review input.
2. Dry-run approved-action bridge: validates approved exports and logs what would execute.
3. Reviewed live bridge: operator-created, provider-specific, explicit opt-in, and security/ops approved.

The live bridge must retain a dry-run switch. The reviewed version should fail closed unless all of these are true:

- source schema is exactly `botfucker.approved_actions.v1`
- action has `safety_scope: provider_action_export_only`
- action has `provider_execution: not_performed`
- `approved_action` is exactly the one action type under review
- `audit_id` has not already been processed
- provider, message, and thread identifiers are present for that provider
- emergency stop is off
- daily action limit has not been exceeded
- operator explicitly enabled this provider/action pair

## Persistent processed-audit design

Dry-run currently supports a starter `BOTFUCKER_PROCESSED_AUDIT_IDS` list. Live bridge work must replace that with durable state before any provider mutation.

Minimum durable fields:

```json
{
  "audit_id": "audit-0001",
  "action_id": "bf-action-audit-0001",
  "provider": "gmail",
  "approved_action": "approve_warning",
  "message_id": "gmail-msg-123",
  "thread_id": "gmail-thread-7",
  "status": "processed",
  "dry_run": false,
  "provider_result_id": "provider-response-id-or-null",
  "processed_at": "2026-05-18T00:00:00Z",
  "processed_by_workflow": "botfucker-reviewed-live-bridge-v1"
}
```

Rules:

- Use `audit_id` as the primary idempotency key.
- Check durable state before the provider node executes.
- Insert a pending/attempted record before live mutation if the state store supports transactions or equivalent lock behavior.
- Record provider result, failure, and rollback status after execution.
- Never retry a processed `audit_id` blindly; manual review is required for ambiguous failures.
- Keep the durable processed-audit store in n8n/operator infrastructure, not BotFucker core.

Acceptable early storage options are n8n Data Store, a provider-bridge SQLite/Postgres table owned by n8n, or a locked append-only file on the n8n host. Environment variables are not acceptable for live processed-audit state.

## Rollback and emergency stop

A reviewed live bridge must document rollback before it is enabled.

Emergency stop requirements:

- one operator-visible switch that stops provider mutations immediately
- default value is stopped/off for live mutation
- documented place where the switch is configured in n8n
- test showing the bridge exits before provider mutation when the stop is active

Rollback requirements for `approve_warning`:

- log the provider message/reply identifier returned by the provider
- document whether the provider supports deleting, retracting, or annotating the sent/drafted reply
- if reversal is unsafe or unsupported, document that rollback is notification/manual remediation only
- keep a manual incident note template for bad sends
- preserve processed-audit state even when rollback is manual so duplicate sends do not compound the mistake

## Provider-specific sandbox/manual test plan

Before any provider mutation node is connected to a production account, run provider-specific tests in a sandbox or controlled test mailbox.

Minimum manual test matrix:

- Import one fake/sandbox message into local review state.
- Approve exactly one `approve_warning` item locally.
- Export approved actions from the local CLI.
- Run the bridge in dry-run mode and verify `provider_execution: not_performed`.
- Enable the reviewed live bridge only for the sandbox provider/action pair.
- Execute one action against a sandbox/test message.
- Verify exactly one provider-side result was created.
- Re-run the same export and confirm dedupe prevents duplicate mutation.
- Turn on emergency stop and confirm no provider mutation occurs.
- Trigger a controlled provider failure and confirm the audit state is not marked successfully processed.
- Remove sandbox/test artifacts and record cleanup.

Provider-specific notes must document provider rate limits, reply/draft semantics, delete/retract availability, and how to identify a safe test mailbox/thread.

## Security review checklist

Rex/security review must pass before any live provider action node is connected:

- no provider credentials in the repo, samples, docs examples, local SQLite review DB, browser JSON, or test fixtures
- live bridge is separate from BotFucker core and checked-in dry-run starter
- provider node cannot execute unless schema, safety scope, action type, emergency stop, and dedupe checks pass
- durable processed-`audit_id` state exists and is checked before mutation
- logs redact tokens, cookies, private headers, and message bodies where possible
- untrusted message content cannot alter workflow control flow
- rollback/emergency-stop documentation exists
- action limits are configured for the first live review

## Ops review checklist

Gus/ops review must pass before any live provider action node is connected:

- workflow starts inactive or disabled for live mutation by default
- operator can run dry-run and inspect `would_execute` output
- processed-audit storage is backed up or otherwise durable enough for the target
- failures are visible in n8n execution history or external logs
- cleanup steps exist for sandbox data
- production activation requires explicit human action
- final reviewed workflow name/version is recorded

## Promotion gate

A live provider bridge is not ready until all gate items are true:

- one provider/action pair only
- dry-run evidence exists
- sandbox/manual evidence exists
- persistent processed-`audit_id` state exists
- emergency stop tested
- rollback/remediation documented
- Rex/security approval recorded
- Gus/ops approval recorded
- no changes added OAuth or provider mutation behavior to BotFucker core

Until then, the correct state is dry-run only. The robot can wait; the inbox cannot un-send regret.
