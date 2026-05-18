# Phase 17 — Inactive Outlook Warning-Draft Workflow Scaffold

This artifact adds an importable n8n scaffold for the first selected provider/action pair:

- Provider: Microsoft Outlook / Microsoft Graph
- Reviewed action: `approve_warning`
- Graph primitive: `POST /me/messages/{id}/createReply`
- Permission note: Microsoft documents `Mail.ReadWrite` for draft creation. This is documentation only; no OAuth setup or secrets are stored here.
- Workflow export: `docs/n8n-outlook-warning-draft-scaffold.json`

The scaffold is deliberately inactive, manual, and not connected to live provider execution. It is a rehearsal artifact for operator review, not a production workflow.

## Safety boundary

The workflow export must stay:

- `active: false`
- manual-triggered only
- free of tokens, secrets, client secrets, passwords, private mailbox data, and exported n8n auth material
- limited to fake/sample input until an operator imports a controlled sandbox bundle
- draft-only; the only documented Microsoft Graph operation is `createReply`

The included Graph node is a disabled, unconnected placeholder. The connected path validates a fake approved-action bundle, applies emergency-stop and `audit_id` duplicate checks, and emits a safety summary only.

## Emergency stop

`BOTFUCKER_EMERGENCY_STOP` defaults to on. Unless an operator explicitly sets it to an off value for a reviewed sandbox rehearsal, the validation node returns `blocked_by_emergency_stop` before any provider-side step can be considered.

Required operator behavior:

1. Confirm the workflow is inactive after import.
2. Confirm only the manual trigger exists as a trigger node.
3. Leave the disabled Graph placeholder disconnected unless Rex and Gus approve the exact sandbox rehearsal.
4. Turn the emergency stop back on immediately after rehearsal.

## Dedupe

The scaffold preserves the Phase 14/15 duplicate boundary:

- `audit_id` is the dedupe key.
- `BOTFUCKER_PROCESSED_AUDIT_IDS` can be used in n8n sandbox rehearsal to skip known processed audit IDs.
- Real durable ledger state remains outside this scaffold until the operator wires the reviewed bridge path.
- Duplicate exports must not acquire a second draft attempt.

## Rollback and manual deletion

Rollback for a sandbox draft is intentionally manual:

1. Stop the workflow and verify it is inactive.
2. Turn `BOTFUCKER_EMERGENCY_STOP` on.
3. In the sandbox Outlook mailbox, manually delete the created draft if one exists.
4. Mark the bridge ledger/audit record as rolled back in operator-maintained state.
5. Record the draft ID, `audit_id`, operator, timestamp, and reason in the rehearsal notes.

No rollback step should mutate inbox messages, rules, contacts, settings, folders, read state, or non-draft data.

## Import/rehearsal checklist

Use this only in an n8n sandbox owned by the operator:

1. Import `docs/n8n-outlook-warning-draft-scaffold.json`.
2. Verify the imported workflow is inactive.
3. Verify there are no stored credentials in the imported export.
4. Verify the Microsoft Graph placeholder is disabled and unconnected.
5. Execute the connected manual path with the emergency stop still on; expect `blocked_by_emergency_stop`.
6. Execute with a fake reviewed action and emergency stop off only after Rex/Gus review; expect draft-only readiness output before any provider node is connected.
7. If a future reviewed rehearsal connects the Graph placeholder, use only a sandbox mailbox and only the `createReply` draft primitive.
8. Return the workflow to inactive and emergency-stop-on state.

## Non-goals

This phase does not implement OAuth, does not activate n8n, does not add production credentials, does not connect a live Microsoft node, and does not perform live mailbox delivery. The next phase should be sandbox import/rehearsal or operator validation of this scaffold, not live delivery or broad OAuth work.
