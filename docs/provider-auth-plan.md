# Phase 7 Provider Auth Plan

Phase 7 is a planning and boundary-design phase. It intentionally does not add real OAuth, IMAP passwords, provider mutations, or YOLO mode. The point is to define how provider auth can arrive later without turning a local review cockpit into a credential piñata.

## Decision summary

Recommended sequence:

1. Keep the n8n-first path as the default near-term integration.
2. Define an approved action export from BotFucker's local review/audit state.
3. Let a separate n8n action bridge consume approved actions and perform provider-side work later.
4. Treat Direct OAuth as a later product track once the local review loop proves useful.

BotFucker core stays provider-action-free until the action bridge is explicit, reviewed, tested, and opt-in.

## Integration options

### Option A — n8n-first

n8n-first means n8n owns provider connections and BotFucker receives only normalized JSON through `import-webhook-json`.

Pros:

- Existing provider nodes handle Gmail, Microsoft, and IMAP complexity.
- Provider credentials stay server-side in n8n; in short, provider credentials stay server-side.
- BotFucker keeps a small standard-library Python core.
- Safer for early real-world testing because local review state remains separate from provider actions.

Cons:

- Requires n8n installation and local filesystem/command access.
- Provider action behavior depends on later n8n workflow design.
- Less polished for non-technical users than native OAuth.

Recommendation: use this first for Kent's actual workflow.

### Option B — Direct OAuth

Direct OAuth means BotFucker eventually owns Gmail/Microsoft OAuth flow, token refresh, provider APIs, and action execution.

Pros:

- Cleaner one-app experience for a packaged product.
- Easier onboarding once built correctly.
- Centralized provider behavior.

Cons:

- More attack surface.
- Token refresh and revocation rules are provider-specific.
- Requires a real server-side secret store and OAuth callback handling.
- Easy to accidentally leak tokens into browser JSON, logs, or SQLite if rushed.

Recommendation: document now, implement later. Do not implement Gmail OAuth in this phase. Do not implement Microsoft OAuth in this phase.

### Option C — IMAP/SMTP fallback

IMAP/SMTP can remain a developer/self-hosting fallback for legacy script users.

Rules:

- Do not add IMAP passwords to BotFucker core.
- Keep app passwords in environment variables or a platform secret store.
- Never expose password-derived state to the local UI.
- Prefer read-only scan/review before any SMTP send path.

## Secret storage requirements

Minimum requirements before direct provider auth exists:

- No secrets in the browser.
- No secrets in the repo.
- No OAuth tokens in local UI JSON.
- No provider tokens, refresh tokens, cookies, app passwords, API keys, or private headers in SQLite review records.
- Use an encrypted secret store for packaged/server deployments.
- environment variables are acceptable for local development only.
- Logs must redact token-like values and provider auth headers.
- Docs/examples must use reserved domains and fake values only.

Browser/server boundary:

- Browser UI receives review data, safety flags, and local audit status only.
- Browser UI never receives OAuth access tokens, refresh tokens, API keys, provider cookies, IMAP passwords, SMTP passwords, or provider raw headers.
- Browser UI posts local review intent only.
- Server/provider bridge validates whether intent is allowed before any real provider call.

## Approved Action Export

BotFucker now includes an approved action export from human-reviewed SQLite audit events.

Command shape:

```bash
python3 -m botfucker.review_cli \
  --db botfucker_review.sqlite3 \
  export-approved-actions --since-audit-id audit-0001 > approved-actions.json
```

Current export fields:

```json
{
  "schema": "botfucker.approved_actions.v1",
  "safety_scope": "provider_action_export_only",
  "provider_execution": "not_performed",
  "actions": [
    {
      "audit_id": "audit-0002",
      "item_id": "webhook:gmail:gmail-msg-123",
      "message_id": "gmail-msg-123",
      "thread_id": "gmail-thread-7",
      "provider": "gmail",
      "approved_action": "approve_warning",
      "approved_by": "human",
      "approved_at": "2026-05-13T09:45:00Z",
      "draft_reply": "Human-reviewed warning text",
      "safety_scope": "provider_action_export_only",
      "provider_execution": "not_performed"
    }
  ]
}
```

The export may later support approved actions such as:

- send reply
- archive
- move
- label
- blacklist sender or domain

But those are export intents only until a separate bridge consumes them.

## n8n action bridge

BotFucker now includes a dry-run n8n action bridge starter in `docs/n8n-approved-action-bridge.json`. It consumes `approved-actions.json`, validates `botfucker.approved_actions.v1`, dedupes by `audit_id`, and logs `would_execute` records only.

Rules for any future live bridge:

- It must be a separate workflow from the import workflow.
- It must require explicit enablement.
- It must process only human-approved audit events.
- It must keep provider credentials in n8n.
- It must log what provider action it attempted.
- It must support a dry-run mode before live action.
- It must define provider-specific idempotency behavior.

BotFucker MUST NOT perform provider actions from the local review UI. The UI can record approval intent; the action bridge handles the loaded weapon later, with the safety on and preferably not pointed at anyone's foot.

## Phase 7 non-goals

Do not implement Gmail OAuth in this phase.
Do not implement Microsoft OAuth in this phase.
Do not add IMAP passwords to BotFucker core.
Do not enable YOLO mode.
Do not add send/move/delete provider calls.
Do not add browser-visible provider tokens.
Do not add live provider whitelist/blacklist mutations.

## Next engineering step

The next engineering step should be **Optional LLM Classifier**, not OAuth.

Approved action export and the dry-run bridge contract now exist. Next, improve classification quality behind a strict provider abstraction, structured output validation, prompt-injection hardening, mocked provider tests, and a deterministic fallback.

## Acceptance criteria for Phase 7

- Provider-auth architecture options are documented.
- Secret storage and browser/server boundaries are documented.
- Approved action export is defined before provider side effects exist.
- n8n action bridge is described as a separate future workflow.
- Tests verify that the plan includes the safety boundaries and non-goals.
