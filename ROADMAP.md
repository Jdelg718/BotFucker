# BotFucker Roadmap

BotFucker is evolving from a local inbox-filtering script into an AI-era inbox defense system.

The thesis is simple:

> Use automation to protect productive work from automated interruption.

AI is excellent when builders use it to build. It is garbage when lead-gen parasites use it to manufacture fake personalization and CRM follow-up sludge at scale. BotFucker exists to turn the tools around.

## Current State

Merged through PR #7:

- v2 design document
- reusable `botfucker/` Python package
- normalized email model
- structured classifier results
- deterministic outreach classifier
- SQLite sender history and strike tracking
- warning templates
- guarded live mode requiring explicit `--auto-approve`
- dry-run default
- local review queue UI with sample mode and durable SQLite mode
- durable review CLI and audit log
- normalized n8n/webhook import contract
- n8n workflow package and mapping guide
- tests for classifier/history/safety/review/webhook/docs behavior

## Product Direction

BotFucker should become a small but serious inbox-defense app:

- branded dashboard using the BotFucker/FF2K identity
- review queue for flagged messages
- sender/domain strike history
- drafted warning responses
- approval-first workflow by default
- explicit guarded YOLO mode for users who want automation without review
- OAuth/provider integrations for Gmail and Microsoft
- optional LLM classifier with strict structured output
- n8n/webhook integration path

## Guiding Principles

1. **Human approval by default**
   - BotFucker may classify, summarize, and draft.
   - Sending replies, blacklisting, deleting, or escalating requires approval unless YOLO mode is explicitly enabled.

2. **YOLO mode must be explicit**
   - Disabled by default.
   - Requires scary confirmation copy.
   - Must include daily send limits, allowed classifications, confidence thresholds, audit logging, and an emergency off switch.

3. **Credentials stay out of the repo**
   - No secrets, no real mailbox exports, no private contact lists.
   - Use OAuth/provider credential stores where possible.
   - API keys must be server-side only.

4. **Evidence over vibes**
   - Classifications must include reasons.
   - Review screens should show why BotFucker thinks something is spam/outreach.

5. **Archive/quarantine before delete**
   - Permanent deletion should never be the casual default.

## Phases

### Phase 1 — Safer Core Library ✅

Status: merged.

Delivered:

- core package modules
- structured classifier
- sender history
- strike logic
- safe CLI guardrails
- tests

### Phase 2 — Review Queue + Local UI Skeleton ✅

Status: merged.

Delivered:

- sample/fake local review data
- local browser UI skeleton
- branded dark/orange/blue BotFucker styling
- dashboard, review queue, sender history, settings mock
- visual approval actions only
- no email credentials and no real sends

### Phase 3 — CLI Review Workflow ✅

Status: merged.

Delivered:

- durable local SQLite review queue
- CLI list/approve/dismiss/whitelist/blacklist/audit workflow
- local JSON import for review items
- enforced local-only safety scope and mock-only review state
- durable audit trail

### Phase 4 — n8n/Webhook Integration Contract ✅

Status: merged.

Delivered:

- normalized webhook input contract
- n8n/provider JSON mapping guidance
- deterministic classification during import
- secret/header redaction and bounded snippets
- invalid batch rejection without partial import

### Phase 5 — Durable Local UI ✅

Status: merged.

Delivered:

- `--db` mode for the local browser UI
- durable SQLite-backed review queue, sender history, and audit views
- local action application through `DurableReviewStore`
- fail-closed startup requiring either `--sample-data` or `--db`
- no provider auth, no live mailbox action

### Phase 6 — n8n Workflow Package ✅

Status: merged.

Delivered:

- importable inactive `docs/n8n-workflow.json` starter
- `docs/n8n-workflow.md` operator guide
- safe provider boundary checklist
- local CLI import command example
- TDD coverage validating docs/workflow safety assumptions

### Phase 7 — Provider Auth Planning Stub

Status: in PR #8.

Goal: document how provider auth and provider actions should arrive later without adding real OAuth or live mailbox side effects in this phase.

Deliverables:

- n8n-first versus Direct OAuth tradeoff analysis
- IMAP/SMTP fallback constraints
- secret storage requirements
- browser/server boundary requirements
- approved action export shape
- future n8n action bridge rules

Non-goals:

- no Gmail OAuth implementation
- no Microsoft OAuth implementation
- no IMAP passwords in BotFucker core
- no YOLO mode
- no send/move/delete provider calls

Acceptance criteria:

- Secrets never reach the browser.
- Keys are not committed.
- Provider action execution is separated from local review approval.
- OAuth and key storage are documented clearly.

### Phase 8 — Optional LLM Classifier

Goal: improve classification quality without trusting email content blindly.

Deliverables:

- provider abstraction
- strict JSON schema
- prompt-injection hardening
- deterministic classifier fallback
- tests using mocked provider responses

Acceptance criteria:

- Email content is treated as untrusted input.
- LLM output is validated before use.
- Classifier reasons remain explainable.

### Phase 9 — Guarded YOLO Mode

Goal: allow power users to automate replies/blocks while making footguns obvious.

Deliverables:

- explicit YOLO settings
- daily send limits
- classification allowlist
- confidence thresholds
- tone restrictions
- audit log
- emergency off switch

Acceptance criteria:

- Disabled by default.
- Requires explicit confirmation.
- Never silently enables aggressive/legal-ish replies.

## Near-Term Recommendation

Next PR after Phase 7 should be **Approved Action Export**, not OAuth implementation.

Recommended scope:

- add a local-only `export-approved-actions` command
- export only human-reviewed SQLite audit events
- make the export idempotent/traceable using audit IDs
- preserve the provider boundary: export intent, do not execute provider actions
- add tests for no `--live`, no provider credentials, and no unapproved action export

OAuth can wait until we know the exact action contract. Building OAuth first is how products become login screens with delusions of grandeur.
