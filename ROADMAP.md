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
- reviewed live-bridge promotion gate
- durable bridge ledger scaffold for processed `audit_id` state before provider mutation
- tests for classifier/history/safety/review/webhook/docs/branding/bridge-ledger behavior

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

### Phase 9 — n8n Approved Action Bridge Dry Run ✅

Status: implemented on `phase-9-n8n-approved-action-bridge`.

Goal: consume `botfucker.approved_actions.v1` export bundles in a separate n8n workflow, validate/dedupe approved actions, and log what would execute without touching live mail.

Delivered:

- importable inactive `docs/n8n-approved-action-bridge.json` dry-run workflow
- operator guide `docs/n8n-approved-action-bridge.md`
- schema validation for `botfucker.approved_actions.v1`
- dedupe hook based on `audit_id`
- dry-run `would_execute` logging with `provider_execution: not_performed`
- docs/tests proving no Gmail/Microsoft/IMAP/email-send nodes in the starter

Acceptance criteria:

- Bridge starts inactive and dry-run/log-only.
- Bridge validates schema and safety scope before emitting actions.
- Bridge dedupes by `audit_id`.
- Provider credentials stay in n8n.
- No provider action nodes are connected in the starter workflow.

### Phase 10 — Optional LLM Classifier ✅

Status: implemented on `phase-10-optional-llm-classifier`.

Goal: improve classification quality without trusting email content blindly.

Delivered:

- optional `llm_provider` hook on `classify_message`
- bounded prompt/payload with subject/body marked as untrusted input
- no raw headers or credential-like provider material in LLM payloads
- strict structured output validation for classification/action/confidence/reasons
- deterministic classifier fallback when provider output is invalid or provider call fails
- local safety-state bypass: whitelist and known-offender decisions do not call the LLM provider
- tests using mocked provider responses

Acceptance criteria:

- Email content is treated as untrusted input.
- LLM output is validated before use.
- Classifier reasons remain explainable with `llm:` prefixes.
- Provider failures and invalid model output fall back to deterministic rules.

### Phase 11 — Guarded YOLO Mode ✅

Status: implemented on `phase-11-guarded-yolo-guardrails`.

Goal: allow power users to automate replies/blocks while making footguns obvious.

Delivered:

- `botfucker.yolo_policy.YoloPolicy` and `evaluate_yolo_decision`
- YOLO disabled by default
- exact confirmation phrase requirement: `I ACCEPT BOTFUCKER YOLO RISK`
- emergency stop override
- provider-action allowlist
- classification allowlist
- confidence threshold
- daily action limit
- reply tone allowlist
- legacy `--live --auto-approve` now requires YOLO guardrails before live provider actions
- tests proving YOLO cannot silently enable live provider actions

Acceptance criteria:

- Disabled by default.
- Requires explicit confirmation.
- Never silently enables aggressive/legal-ish replies.
- Blocks provider actions that fail allowlist/confidence/daily-limit/emergency-stop gates.

### Phase 12 — Real n8n Import/Dry-Run Validation ✅

Status: implemented on `phase-12-n8n-import-dry-run-validation`.

Goal: test the packaged n8n workflows against Kent's actual n8n instance without activating live provider mutations.

Delivered:

- added `scripts/validate_n8n_workflow_exports.py` static preflight validator
- added `samples/approved-actions.sample.json` safe fake approved-action bundle
- added `docs/n8n-import-validation.md` with exact procedure and actual results
- imported both workflows into `n8n-vps` running n8n 2.18.5
- confirmed both imported as inactive/manual workflows
- executed the approved-action bridge dry-run on sample data only
- confirmed dry-run output: `would_execute: approve_warning`, `provider_execution: not_performed`
- cleaned up validation workflows, related sample execution rows, and temp files
- fixed n8n compatibility issues: workflow `id` required, files must live under `/home/node/.n8n-files`, readWriteFile JSON arrives as binary and must be parsed with `getBinaryDataBuffer`

Acceptance criteria:

- Workflows import cleanly into real n8n.
- Dry-run path executes on sample data only.
- No Gmail/Microsoft/IMAP/SMTP mutation credentials are attached.
- Activation remains manual and reviewed.

### Phase 13 — Reviewed Action Bridge Promotion Plan ✅

Status: implemented on `phase-13-reviewed-action-bridge-promotion-plan`.

Goal: define the reviewed path from dry-run logs to a live provider bridge without adding OAuth/provider mutation directly to BotFucker core.

Delivered:

- operator checklist for promoting one provider action type at a time
- explicit credential ownership in n8n only
- audit/dedupe persistence design for processed `audit_id` values
- rollback/emergency-stop steps
- provider-specific sandbox/manual test plan
- security review checklist before any live provider action node is connected

Acceptance criteria:

- Live bridge remains separate from BotFucker core.
- Only reviewed approved-action records are eligible.
- Every provider mutation is idempotent, audited, and reversible where possible.
- No live provider credentials are committed or exported.
- No OAuth, live provider mutation nodes, or provider behavior changes are added by this phase.

### Phase 14 — Durable Bridge Ledger Scaffold ✅

Status: implemented on `phase-14-durable-bridge-ledger`.

Goal: provide a durable processed-`audit_id` ledger scaffold that a future reviewed bridge can use before any provider mutation, without adding OAuth, credentials, or live mutation nodes.

Delivered:

- `botfucker.bridge_ledger.DurableBridgeLedger` SQLite scaffold keyed by `audit_id`
- `pending`, `processed`, `failed`, and `rolled_back` statuses
- `claim_action()` flow that inserts durable `pending` state before provider mutation
- validation for `botfucker.approved_actions.v1`, `provider_action_export_only`, and `provider_execution: not_performed`
- docs in `docs/bridge-ledger-scaffold.md`
- tests proving dedupe, status transitions, unsafe export rejection, and no message-content/secret columns

Acceptance criteria:

- Durable state is keyed by `audit_id`.
- Repeated claims of an `audit_id` do not acquire a second mutation slot.
- Ledger stores IDs/status only, not message body/header/credential material.
- No OAuth, no provider credentials, no live provider mutation nodes, and no checked-in n8n activation changes are added.

### Phase 15 — Emergency-Stop Bridge Rehearsal ✅

Status: implemented on `phase-15-emergency-stop-bridge-rehearsal`.

Goal: prove the emergency-stop and dry-run bridge path against the durable ledger before any live provider mutation exists.

Delivered:

- `botfucker.bridge_rehearsal.rehearse_approved_actions()` dry-run-only bridge rehearsal
- emergency-stop default that exits before claiming the durable ledger
- dry-run path that claims the ledger and marks `dry_run_logged` without provider execution
- duplicate replay handling that returns `duplicate_skipped`
- docs in `docs/bridge-rehearsal.md`
- tests proving emergency stop, dry-run logging, duplicate skip, live-mode rejection, and unsafe-action rejection

Acceptance criteria:

- Emergency stop creates no ledger row and no provider execution.
- Dry-run remains mandatory; `dry_run=False` fails closed.
- Duplicate approved-action exports are skipped by durable `audit_id`.
- Provider execution remains `not_performed`.
- No OAuth, provider credentials, provider API calls, or live mutation nodes are added.

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

After Phase 15 is reviewed and merged, the next PR should be **Phase 16: Microsoft Outlook warning-draft sandbox contract**, not broad OAuth implementation.

Kent selected the first provider/action target:

- Provider: Microsoft Outlook
- First action: create/save a warning draft only
- Scope: sandbox/manual reviewed bridge contract first; no send-reply mutation yet

Recommended scope:

- keep one provider/action pair only (`approve_warning`)
- document the exact sandbox mailbox/provider target Kent wants to use
- keep credentials in n8n only
- keep dry-run as the default path
- map the Phase 15 rehearsal outcomes onto an inactive n8n/operator checklist
- require Rex/Gus security/ops review before any live mutation node is connected

OAuth can still wait. Phase 15 proves the brakes in code. Next is picking the sandbox road — not handing the robot live mailbox keys because apparently we enjoy learning by fire.

### Restart checklist after Phase 15

1. Re-check Phase 15 PR CI and mergeability.
2. Squash-merge Phase 15 into `main` if still green.
3. Use Microsoft Outlook as the selected sandbox provider target.
4. Limit the first provider/action pair to warning draft creation/save only; do not send replies.
5. Keep provider credentials inside n8n/operator infrastructure only; do not put secrets in BotFucker.

## Team Utilization

- **Amy**: orchestrates scope, keeps phases honest, and blocks shiny-object OAuth detours.
- **Chip**: owns bridge promotion docs/tests and any dry-run-to-live scaffolding after review.
- **Rex**: reviews credential absence, processed-audit dedupe, live-action safety gates, and rollback.
- **Gus**: verifies n8n operator steps, imports, cleanup, and bridge observability.
- **Fred**: researches provider-specific sandbox/action constraints only; no direct OAuth implementation yet.
