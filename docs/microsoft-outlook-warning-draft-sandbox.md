# Phase 16 — Microsoft Outlook Warning-Draft Sandbox Contract

Kent selected the first provider/action target:

- Provider: Microsoft Outlook / Microsoft Graph
- Action: create/save a warning draft only
- Environment: sandbox/manual reviewed bridge first
- Explicit non-goal: sending replies

This phase is a contract and safety checklist for the future n8n/provider bridge. It does not add OAuth code, credentials, tokens, live n8n activation, or provider mutation logic to BotFucker core.

## Microsoft Graph primitive

Microsoft Graph supports creating a reply draft with:

```http
POST /me/messages/{id}/createReply
```

or the user-scoped form:

```http
POST /users/{id | userPrincipalName}/messages/{id}/createReply
```

Microsoft documents the least-privileged permission for this operation as `Mail.ReadWrite`.

Important behavior:

- `createReply` creates a draft reply.
- It does not send the draft.
- Sending is a separate operation and remains out of scope.
- The bridge must never call `/send` in this phase.

Reference:

- https://learn.microsoft.com/en-us/graph/api/message-createreply?view=graph-rest-1.0

## Required safety gates

Before any sandbox call is allowed, the bridge must prove all of these gates:

1. Human-approved local audit event exists.
2. Approved-action export schema is `botfucker.approved_actions.v1`.
3. `provider_execution` is `not_performed`.
4. Approved action is exactly `approve_warning`.
5. Provider is exactly `outlook` or `microsoft_outlook`, normalized to a single bridge value.
6. Durable bridge ledger claim succeeds for the `audit_id`.
7. Emergency stop is false.
8. Dry-run rehearsal has passed for the same action shape.
9. Sandbox mailbox/provider target is explicitly configured in n8n/operator infrastructure.
10. Credentials remain in n8n/operator infrastructure only.

If any gate fails, the bridge exits before provider mutation.

## Credential boundary

Credentials are not BotFucker state.

Allowed:

- n8n-owned Microsoft credential
- operator-owned Microsoft sandbox account
- environment/credential store controlled outside this repo

Forbidden in this repo:

- OAuth client secret
- refresh token
- access token
- password
- cookie
- exported n8n credentials
- real mailbox payloads
- private message bodies

## Allowed provider effect for first sandbox test

The only permitted provider effect is:

```text
create Outlook reply draft warning for the reviewed message
```

The provider result must be recorded back to the bridge ledger as metadata only, such as:

- provider: `microsoft_outlook`
- approved_action: `approve_warning`
- provider_result_id: draft message ID or opaque test ID
- status: `processed` only after Graph returns a successful draft creation

The ledger must still avoid storing raw message bodies, headers, secrets, or tokens.

## Explicitly forbidden provider effects

Do not:

- send the draft
- call Microsoft Graph `/send`
- reply in a single operation
- delete email
- move email
- archive email
- mark read/unread
- create rules
- update contacts
- write mailbox settings
- attach credentials to exported workflow JSON

No “just testing” send. That is how a sandbox turns into a customer-service fire drill wearing a fake mustache.

## n8n sandbox shape

A future n8n workflow may contain these conceptual steps:

1. Manual trigger only.
2. Read approved-action export from controlled test input.
3. Validate schema/safety fields.
4. Check emergency-stop flag.
5. Claim `audit_id` in durable bridge ledger.
6. Use Microsoft Outlook/Graph credential from n8n only.
7. Create reply draft with Microsoft Graph `createReply`.
8. Update draft body with the human-approved warning text if the create step produces an empty draft.
9. Record provider draft ID in bridge ledger.
10. Stop. Do not send.

The workflow must remain inactive/manual until Rex and Gus review the exact artifact.

## Acceptance criteria for implementation PR

A future implementation PR must include:

- an inactive/manual n8n workflow or operator guide only
- sample fake Outlook action bundle using reserved/fake IDs
- tests/static validator proving no `/send` call exists
- tests/static validator proving no credentials are exported
- emergency-stop test evidence
- duplicate `audit_id` test evidence
- rollback/remediation note for deleting the sandbox draft manually
- Rex security review
- Gus ops/n8n review

## Current status

Phase 16 selected target is documented, but no live provider mutation has been implemented yet.
