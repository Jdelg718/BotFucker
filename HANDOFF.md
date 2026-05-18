# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: Phase 12 real n8n import/dry-run validation (`docs: validate n8n import dry run`, PR #13)
- Current working branch: `phase-13-reviewed-action-bridge-promotion-plan`
- Current PR target: Phase 13 Reviewed Action Bridge Promotion Plan — docs/tests only, no OAuth/live provider mutation
- Current local demo target: demonstrate deterministic local review, optional mocked LLM classifier fallback/validation, approved-action export, dry-run n8n bridge contract, fail-closed YOLO policy checks, real n8n import validation results, and reviewed bridge-promotion gate
- Current promo artifact: `promo/botfucker-animated-explainer/renders/botfucker-animated-explainer_narrated-final.mp4`

## What BotFucker Is

BotFucker is an AI-era inbox defense project.

It started as a Python proof-of-concept for detecting cold outreach, AI-generated sales pitches, and CRM follow-ups. It is now a local-first review cockpit: classify suspicious outreach, store review items locally, show a browser review queue, track audit events, and let the human approve actions before any provider-side automation exists.

The public thesis:

> Use automation to protect productive work from automated interruption.

## Current Architecture

Important files:

```text
DESIGN.md                     # v2 architecture and principles
ROADMAP.md                    # phased product roadmap, current through Phase 12 n8n import validation
docs/n8n-import-validation.md # Phase 12 real n8n import/dry-run procedure and results
docs/webhook-contract.md      # normalized n8n/webhook JSON contract
docs/n8n-workflow.json        # importable n8n import starter workflow
docs/n8n-workflow.md          # n8n import operator guide and safety checklist
docs/n8n-approved-action-bridge.json # importable n8n approved-action dry-run bridge
docs/n8n-approved-action-bridge.md   # approved-action bridge operator guide
docs/provider-auth-plan.md    # provider auth/action boundary plan
docs/reviewed-action-bridge-promotion-plan.md # Phase 13 reviewed live-bridge gate; no OAuth/live mutation
README.md                     # user-facing setup and project overview
outreach_filter.py            # compatibility CLI wrapper
botfucker/models.py           # normalized email/classification/review models
botfucker/classifier.py       # deterministic classifier
botfucker/history.py          # SQLite sender history + strike state
botfucker/review_queue.py     # review item/audit models and sample data helpers
botfucker/review_store.py     # durable SQLite review queue and audit store
botfucker/review_cli.py       # durable local review CLI
botfucker/webhook_contract.py # n8n/webhook payload sanitizer/import adapter
botfucker/local_ui.py         # local browser review UI server
web/                          # static UI assets
promo/botfucker-animated-explainer/ # HyperFrames FF2K product explainer source + rendered cut
tests/                        # fake-email-only tests
```

## Safety Defaults

These are non-negotiable:

- Dry-run by default.
- Human approval by default.
- `--live` alone must not send replies.
- Any automation that sends/moves/blacklists needs explicit opt-in.
- YOLO mode must be disabled by default and heavily guarded.
- No credentials, real emails, mailbox exports, private contacts, or secrets in the repo.
- Treat all email body/content as untrusted input.
- n8n/provider credentials stay in n8n or the provider layer, not BotFucker core.
- Local UI and review CLI actions affect SQLite review state only.
- Provider-side actions are future bridge work, not local UI behavior.

## Current Test Commands

Run from repo root:

```bash
python3 scripts/validate_n8n_workflow_exports.py
python3 -m py_compile outreach_filter.py botfucker/*.py scripts/validate_n8n_workflow_exports.py
python3 -m unittest discover -s tests -v
```

Expected current result: all tests pass.

## Current Local Review Flow

Seed fake review data:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
```

Import normalized n8n/webhook JSON:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json n8n-messages.json
```

Run durable local UI:

```bash
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3
```

Open:

```text
http://127.0.0.1:8765/
```

## Pull-It-Locally Kodex/Codex Demo

Kent is on the way home and plans to pull this locally into Kodex/Codex. Demonstrate the safe local product as-is; do not wire live Gmail/Microsoft/n8n credentials during the first demo. Let's not turn the driveway demo into a credential incident.

### Fresh pull

```bash
git clone https://github.com/Jdelg718/BotFucker.git
cd BotFucker
git log --oneline -5
```

Expected current top commit:

```text
713bc7f feat: add guarded yolo policy (#12)
```

If this handoff update has been merged after that, the top commit will be newer. The important part is that PR #12 content is present.

### Verify locally

```bash
python3 scripts/validate_n8n_workflow_exports.py
python3 -m py_compile outreach_filter.py botfucker/*.py scripts/validate_n8n_workflow_exports.py
python3 -m unittest discover -s tests -v
```

### Start a clean local demo database

```bash
rm -f botfucker_review.sqlite3
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
```

### Launch the review cockpit

```bash
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3
```

Open:

```text
http://127.0.0.1:8765/
```

### Demo script

Show:

1. **Dashboard** — local state, no provider connection.
2. **Review queue** — flagged outreach candidates from fake/sample data.
3. **Decision buttons** — approve/dismiss/whitelist/blacklist mutate only local SQLite state.
4. **Sender history** — durable local tracking.
5. **Audit trail** — human actions are recorded before any provider bridge exists.
6. **Provider boundary docs** — `docs/provider-auth-plan.md` explains why OAuth is later.

Say explicitly:

- no OAuth is configured
- no provider credentials are in the repo
- the browser UI cannot send/move/delete email
- n8n is the credential buffer
- approved-action export exists
- current bridge work is dry-run/log-only, not live provider mutation
- optional LLM classifier is provider-hooked and validated, with deterministic fallback
- legacy live automation now requires explicit YOLO guardrails before provider actions
- real n8n import validation passed sample-only dry-run on n8n-vps; validation rows were cleaned up

## Animated Explainer Demo

A branded FF2K/HyperFrames explainer now lives in:

```text
promo/botfucker-animated-explainer/
```

Current narrated render:

```text
promo/botfucker-animated-explainer/renders/botfucker-animated-explainer_narrated-final.mp4
```

Validate from the promo folder:

```bash
npm run check
```

The video copy must keep the current safety truth: local-first review, no live sends, no deletes, no OAuth in core, provider bridge later.

## Completed Phases

### Phase 1 — Safer Core Library

Delivered core package modules, deterministic classifier, sender history, strike logic, safe CLI guardrails, and tests.

### Phase 2 — Review Queue + Local UI Skeleton

Delivered sample/fake local review data, local browser UI skeleton, branded styling, and visual-only approval actions.

### Phase 3 — CLI Review Workflow

Delivered durable SQLite review queue, CLI list/approve/dismiss/whitelist/blacklist/audit workflow, local JSON import, and local-only review state.

### Phase 4 — n8n/Webhook Integration Contract

Delivered normalized webhook input contract, n8n/provider mapping guidance, deterministic classification during import, header redaction, bounded snippets, and invalid batch rejection.

### Phase 5 — Durable Local UI

Delivered `--db` mode for the local browser UI, SQLite-backed review queue/history/audit views, and fail-closed startup requiring `--sample-data` or `--db`.

### Phase 6 — n8n Workflow Package

Delivered importable inactive `docs/n8n-workflow.json`, operator guide, local CLI import example, and tests validating workflow safety assumptions.

### Phase 7 — Provider Auth Boundary Plan

Delivered `docs/provider-auth-plan.md`, documenting n8n-first vs Direct OAuth tradeoffs, IMAP/SMTP constraints, secret storage, browser/server boundaries, approved action export shape, and future n8n action bridge rules.

### Phase 8 — Approved Action Export

Delivered local-only `export-approved-actions`, approved-only SQLite audit export, audit ID cursoring, secret/content minimization, and tests validating approved-only export, cursor behavior, and provider-boundary safety.

### Phase 9 — n8n Approved Action Bridge Dry Run

Delivered inactive `docs/n8n-approved-action-bridge.json`, operator guide, schema validation for `botfucker.approved_actions.v1`, `audit_id` dedupe, dry-run `would_execute` logs, and tests proving no live provider action nodes exist in the starter workflow.

### Phase 10 — Optional LLM Classifier

Delivered optional `llm_provider` hook to `classify_message`, untrusted/bounded provider payloads, raw-header omission, strict output validation, deterministic fallback, local safety-state LLM bypass, and mocked-provider tests.

### Phase 11 — Guarded YOLO Mode

Delivered `YoloPolicy`, fail-closed YOLO decision evaluator, default-off exact confirmation phrase, emergency stop, action/classification allowlists, confidence/daily-limit/tone gates, legacy live-auto-approve guardrail requirement, and tests proving live action attempts fail closed.

### Phase 12 — Real n8n Import/Dry-Run Validation

Implemented on branch `phase-12-n8n-import-dry-run-validation`.

Delivered:

1. Added `scripts/validate_n8n_workflow_exports.py` static workflow export preflight.
2. Added `samples/approved-actions.sample.json` safe fake approved-action bundle.
3. Added `docs/n8n-import-validation.md` with exact procedure and actual n8n-vps results.
4. Added explicit workflow IDs required by n8n 2.18.5 CLI import.
5. Updated n8n file paths to `/home/node/.n8n-files` because Read/Write Files rejects arbitrary paths on the target.
6. Updated approved-action bridge to parse `readWriteFile` binary JSON with `getBinaryDataBuffer` before schema validation.
7. Imported both workflows into n8n-vps as inactive/manual workflows.
8. Executed approved-action bridge sample-only dry-run; final node emitted `would_execute: approve_warning`, `provider_execution: not_performed`, and `bridge_status: dry_run_logged_only`.
9. Cleaned validation workflow rows, sample execution rows, related n8n workflow metadata rows, and temp files.

Verification:

```bash
python3 scripts/validate_n8n_workflow_exports.py
python3 -m py_compile outreach_filter.py botfucker/*.py scripts/validate_n8n_workflow_exports.py
python3 -m unittest discover -s tests -v
```

## Next PR Recommendation

After Phase 13, keep OAuth on hold. The next safe step is either documentation review cleanup for the promotion gate or a mocked/sandbox-only processed-audit state prototype that still performs no live provider mutation.

Do **not** add real OAuth, provider credentials, or live n8n provider mutation nodes until the Phase 13 gate has Rex/Gus review and provider-specific sandbox evidence.

Suggested follow-up scope:

1. Review Phase 13 plan with Rex/Gus.
2. Decide the first provider/action pair for sandbox review, likely `approve_warning` only.
3. Prototype processed-`audit_id` state with fake/sample data only.
4. Keep credentials in n8n only.
5. Require rollback and emergency-stop proof before any live provider action node is connected.

## Suggested Prompt for Kodex/Codex

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, docs/webhook-contract.md, docs/n8n-workflow.md, docs/n8n-approved-action-bridge.md, docs/n8n-import-validation.md, and docs/provider-auth-plan.md.

First, verify the current Phase 12 branch without changing behavior:
- run python3 scripts/validate_n8n_workflow_exports.py
- run python3 -m py_compile outreach_filter.py botfucker/*.py scripts/validate_n8n_workflow_exports.py
- run python3 -m unittest discover -s tests -v
- inspect docs/n8n-import-validation.md and samples/approved-actions.sample.json
- confirm n8n workflows include explicit ids, are inactive, and use /home/node/.n8n-files for Read/Write Files paths

Then review Phase 12 only: Real n8n Import/Dry-Run Validation.

Check that both workflows imported into n8n-vps as inactive/manual, approved-action bridge executed sample-only dry-run, final output was provider_execution:not_performed, and cleanup removed validation rows/temp files.

Do not add real OAuth. Do not add provider credentials. Do not attach Gmail/Microsoft/IMAP/SMTP mutation credentials. Do not enable live n8n provider actions. Preserve the provider boundary: live provider execution remains separately reviewed and guarded.
```

## Team Plan

- **Amy**: orchestration and scope control. She keeps the product from wandering into OAuth swamp country before bridge promotion is reviewed.
- **Chip**: owns reviewed action bridge promotion docs/tests if Phase 12 review passes.
- **Rex**: security veto on processed-audit dedupe, credential absence, live-action safety gates, provider-boundary isolation, and XSS regressions.
- **Gus**: n8n operator verification, dry-run bridge observability, cleanup steps, CI, and operator docs.
- **Fred**: provider sandbox/action-limit research only; no direct OAuth implementation yet.

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- Optional LLM classifier exists only as a provider hook; no real provider wiring or credentials are implemented.
- No production OAuth yet.
- Real n8n import validation passed on n8n-vps with sample-only dry-run and cleanup; do not activate those workflows without a separate reviewed bridge-promotion plan.
- n8n approved action bridge is dry-run only; live provider actions still need a separate explicit reviewed workflow.
- YOLO guardrails exist but live provider actions still require explicit operator configuration and must not be casually enabled.

## Tomorrow Restart

- PR #13 is open and CI green: `https://github.com/Jdelg718/BotFucker/pull/13`.
- First move tomorrow: re-check PR #13, merge if green, pull `main`, branch Phase 13.
- Phase 13 target: **Reviewed Action Bridge Promotion Plan**.
- Do **not** add OAuth, provider credentials, or live n8n provider mutation nodes.
- Keep live provider execution separate, reviewed, audited, deduped by processed `audit_id`, rollback-ready, and security/ops-reviewed.

## Product Voice

BotFucker should be funny and hostile to spam, but serious about safety.

Good tone:

- blunt
- builder-focused
- anti-sludge
- anti-fake-personalization
- clear about risks

Bad tone:

- corporate SaaS
- fake edgy
- careless with legal/security implications
- auto-sending angry emails by default
