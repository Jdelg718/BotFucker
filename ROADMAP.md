# BotFucker Roadmap

BotFucker is evolving from a local inbox-filtering script into an AI-era inbox defense system.

The thesis is simple:

> Use automation to protect productive work from automated interruption.

AI is excellent when builders use it to build. It is garbage when lead-gen parasites use it to manufacture fake personalization and CRM follow-up sludge at scale. BotFucker exists to turn the tools around.

## Current State

Merged through PR #8:

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
- provider auth boundary plan
- FF2K-branded local browser UI and hero art
- HyperFrames animated/narrated product explainer under `promo/botfucker-animated-explainer/`
- tests for classifier/history/safety/review/webhook/docs/branding behavior

The repo is ready to pull locally into Kodex/Codex and demonstrate the local cockpit without connecting to any live mail provider.

## Product Direction

BotFucker should become a small but serious inbox-defense app:

- branded dashboard using the BotFucker/FF2K identity
- review queue for flagged messages
- sender/domain strike history
- drafted warning responses
- approval-first workflow by default
- approved-action export for provider bridges
- explicit guarded YOLO mode for users who want automation without review
- OAuth/provider integrations for Gmail and Microsoft, later and behind the provider boundary
- optional LLM classifier with strict structured output
- n8n/webhook integration path

## Guiding Principles

1. **Human approval by default**
   - BotFucker may classify, summarize, and draft.
   - Sending replies, blacklisting, deleting, or escalating requires approval unless YOLO mode is explicitly enabled.

2. **Provider boundary first**
   - BotFucker core imports normalized JSON and exports approved intent.
   - n8n or a future provider bridge owns credentials and provider-side execution.
   - The local UI must never directly send, move, delete, archive, or mutate mailbox state.

3. **YOLO mode must be explicit**
   - Disabled by default.
   - Requires scary confirmation copy.
   - Must include daily send limits, allowed classifications, confidence thresholds, audit logging, and an emergency off switch.

4. **Credentials stay out of the repo**
   - No secrets, no real mailbox exports, no private contact lists.
   - Use OAuth/provider credential stores where possible.
   - API keys must be server-side only.

5. **Evidence over vibes**
   - Classifications must include reasons.
   - Review screens should show why BotFucker thinks something is spam/outreach.

6. **Archive/quarantine before delete**
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

### Phase 7 — Provider Auth Boundary Plan ✅

Status: merged.

Delivered:

- n8n-first versus Direct OAuth tradeoff analysis
- IMAP/SMTP fallback constraints
- secret storage requirements
- browser/server boundary requirements
- approved action export shape
- future n8n action bridge rules

Non-goals preserved:

- no Gmail OAuth implementation
- no Microsoft OAuth implementation
- no IMAP passwords in BotFucker core
- no YOLO mode
- no send/move/delete provider calls

### Phase 8 — Approved Action Export ✅

Status: implemented on `phase-8-approved-action-export`.

Goal: export human-approved local review/audit events as an idempotent JSON bundle that n8n or another provider bridge can consume later.

Delivered:

- local-only `export-approved-actions` CLI command
- export only approved warning audit events from SQLite
- `--since-audit-id` cursor for idempotent exports
- explicit action IDs / audit IDs for provider bridge deduplication
- no provider credentials, message subject, or message snippet in exports
- no provider-side execution in BotFucker core
- README documentation and tests for the export workflow

Acceptance criteria:

- Unapproved, dismissed, whitelist, and blacklist actions are not exported.
- Export output contains enough IDs for downstream idempotency.
- Export output contains no secrets, OAuth tokens, passwords, raw private headers, or provider credentials.
- The command does not call Gmail, Microsoft, IMAP, SMTP, n8n, or any live provider.
- Tests prove approved-only export, cursor behavior, and provider-boundary behavior.

### Phase 9 — Optional LLM Classifier

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

### Phase 10 — Guarded YOLO Mode

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

## Local Kodex/Codex Demo Plan

Kent is pulling this locally onto Kodex/Codex next. The demo should show what exists now, not pretend Phase 8 is already done. Revolutionary concept, apparently.

### Pull and verify

```bash
git clone https://github.com/Jdelg718/BotFucker.git
cd BotFucker
python3 -m py_compile outreach_filter.py botfucker/*.py
python3 -m unittest discover -s tests -v
```

### Demo the local cockpit with fake/local data

```bash
rm -f botfucker_review.sqlite3
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3
```

Open:

```text
http://127.0.0.1:8765/
```

Demo talking points:

- the browser UI is local-only
- sample seed data proves the review loop without live email access
- approve/dismiss/whitelist/blacklist only mutates SQLite review state
- sender history and audit views are durable
- no provider credentials are present
- no live mailbox actions are possible from the UI

### Demonstrate the n8n boundary without activating live mail

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json path/to/n8n-messages.json
```

Use fake or sanitized JSON only. Real mailbox payloads stay out of the repo.

## Near-Term Recommendation

Next PR should be the **n8n Approved Action Bridge**, not OAuth implementation.

Recommended scope:

- create a separate n8n action workflow that consumes `approved-actions.json`
- process only `botfucker.approved_actions.v1` bundles
- dedupe using `audit_id`
- start in dry-run/log-only mode
- keep provider credentials in n8n
- do not let the local UI execute provider actions directly

OAuth can wait until the export-to-bridge contract proves useful. Building OAuth first is how products become login screens with delusions of grandeur.

## Team Utilization

- **Amy**: orchestrates scope, keeps phases honest, and blocks shiny-object OAuth detours.
- **Chip**: owns bridge implementation once the export contract is reviewed.
- **Rex**: reviews security boundaries, export contents, credential leakage, unapproved actions, browser-triggered side effects, and XSS regressions.
- **Gus**: verifies CLI ergonomics, local demo steps, CI, and n8n bridge usability.
- **Fred**: researches Gmail/Microsoft/n8n provider action shapes for the bridge only; no direct OAuth implementation yet.
