# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: Phase 10 optional LLM classifier (`feat: add optional llm classifier hook`, PR #11)
- Current working branch: `phase-11-guarded-yolo-guardrails`
- Current PR target: Phase 11 guarded YOLO guardrails
- Current local demo target: demonstrate deterministic local review, optional mocked LLM classifier fallback/validation, approved-action export, dry-run n8n bridge contract, and fail-closed YOLO policy checks
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
ROADMAP.md                    # phased product roadmap, current through Phase 11 guarded YOLO guardrails
docs/webhook-contract.md      # normalized n8n/webhook JSON contract
docs/n8n-workflow.json        # importable n8n import starter workflow
docs/n8n-workflow.md          # n8n import operator guide and safety checklist
docs/n8n-approved-action-bridge.json # importable n8n approved-action dry-run bridge
docs/n8n-approved-action-bridge.md   # approved-action bridge operator guide
docs/provider-auth-plan.md    # provider auth/action boundary plan
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
python3 -m py_compile outreach_filter.py botfucker/*.py
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
e0443b7 feat: add optional llm classifier hook (#11)
```

If this handoff update has been merged after that, the top commit will be newer. The important part is that PR #11 content is present.

### Verify locally

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
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

Implemented on branch `phase-11-guarded-yolo-guardrails`.

Delivered:

1. Added `botfucker.yolo_policy.YoloPolicy` and `evaluate_yolo_decision`.
2. YOLO is disabled by default.
3. Requires exact confirmation phrase: `I ACCEPT BOTFUCKER YOLO RISK`.
4. Supports emergency stop override.
5. Gates provider actions by action allowlist, classification allowlist, confidence threshold, daily action limit, and reply tone allowlist.
6. Legacy `--live --auto-approve` path now requires a YOLO policy before live provider actions.
7. Live warning path checks `send_warning`, `write_blacklist`, and `move_to_sales`; blacklist match delete checks `delete_message`.
8. Added tests proving default denial, confirmation failure, valid pass, gate failures, emergency stop, and live-auto-approve guardrail requirement.

Verification:

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
python3 -m unittest discover -s tests -v
```

## Next PR Recommendation

Build **Phase 12: Real n8n Import/Dry-Run Validation**, not OAuth.

Suggested scope:

1. Import `docs/n8n-workflow.json` into Kent's n8n test target or local matching n8n.
2. Import `docs/n8n-approved-action-bridge.json` inactive/dry-run.
3. Confirm node compatibility, file paths, and environment variable assumptions.
4. Run sample-only dry-run payloads end-to-end.
5. Document import/export fixes.
6. Attach no Gmail/Microsoft/IMAP/SMTP mutation credentials.

## Suggested Prompt for Kodex/Codex

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, docs/webhook-contract.md, docs/n8n-workflow.md, docs/n8n-approved-action-bridge.md, and docs/provider-auth-plan.md.

First, verify the current Phase 11 branch without changing behavior:
- run python3 -m py_compile outreach_filter.py botfucker/*.py
- run python3 -m unittest discover -s tests -v
- inspect botfucker/yolo_policy.py and tests/test_yolo_guardrails.py
- confirm live provider actions require explicit YOLO guardrails

Then review Phase 11 only: Guarded YOLO Mode.

Check that YOLO is disabled by default, requires the exact confirmation phrase, supports emergency stop, gates provider actions by allowlist/classification/confidence/daily limit/tone, and that legacy --live --auto-approve cannot silently mutate mail without a YOLO policy.

Do not add real OAuth. Do not add provider credentials. Do not attach Gmail/Microsoft/IMAP/SMTP mutation credentials. Do not enable live n8n provider actions. Preserve the provider boundary: live provider execution remains separately reviewed and guarded.
```

## Team Plan

- **Amy**: orchestration and scope control. She keeps the product from wandering into OAuth swamp country before n8n dry-run validation is real.
- **Chip**: owns n8n import/export compatibility fixes if Phase 11 review passes.
- **Rex**: security veto on YOLO guardrails, live-action safety gates, credential absence, provider-boundary isolation, and XSS regressions.
- **Gus**: local demo verification, n8n import/dry-run validation, CLI ergonomics, CI, and operator docs.
- **Fred**: n8n version/node compatibility research only; no direct OAuth implementation yet.

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- Optional LLM classifier exists only as a provider hook; no real provider wiring or credentials are implemented.
- No production OAuth yet.
- n8n workflow package needs real local import testing against Kent's actual n8n instance before activation.
- n8n approved action bridge is dry-run only; live provider actions still need a separate explicit reviewed workflow.
- YOLO guardrails exist but live provider actions still require explicit operator configuration and must not be casually enabled.

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
