# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: Phase 9 n8n approved-action bridge dry run (`docs: add n8n approved action bridge dry run`, PR #10)
- Current working branch: `phase-10-optional-llm-classifier`
- Current PR target: Phase 10 optional LLM classifier
- Current local demo target: demonstrate deterministic local review, optional mocked LLM classifier fallback/validation, approved-action export, and dry-run n8n bridge contract
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
ROADMAP.md                    # phased product roadmap, current through Phase 10 optional LLM classifier
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
757ed41 docs: add n8n approved action bridge dry run (#10)
```

If this handoff update has been merged after that, the top commit will be newer. The important part is that PR #10 content is present.

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

Implemented on branch `phase-10-optional-llm-classifier`.

Delivered:

1. Added optional `llm_provider` hook to `classify_message`.
2. Provider may be an object with `classify(payload)` or a callable.
3. LLM payload marks subject/body as untrusted and bounds body text before provider handoff.
4. Raw headers are not sent to the provider.
5. LLM output is validated for known classification/action values, numeric confidence, and reasons.
6. Invalid provider output and provider exceptions fall back to deterministic classification.
7. Whitelisted and known-offender local safety states bypass the LLM provider.
8. Added mocked-provider tests for valid output, prompt-injection payload boundary, invalid output fallback, provider exception fallback, and local safety-state bypass.

Verification:

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
python3 -m unittest discover -s tests -v
```

## Next PR Recommendation

Build **Phase 11: Guarded YOLO Mode design/guardrails**, not OAuth.

Suggested scope:

1. Explicit YOLO settings, disabled by default.
2. Daily send/action limits.
3. Classification allowlist and confidence thresholds.
4. Tone restrictions for any generated/sent reply.
5. Audit log and emergency off switch.
6. Tests proving YOLO cannot silently enable live provider actions.

## Suggested Prompt for Kodex/Codex

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, docs/webhook-contract.md, docs/n8n-workflow.md, docs/n8n-approved-action-bridge.md, and docs/provider-auth-plan.md.

First, verify the current Phase 10 branch without changing behavior:
- run python3 -m py_compile outreach_filter.py botfucker/*.py
- run python3 -m unittest discover -s tests -v
- inspect botfucker/classifier.py and tests/test_llm_classifier.py
- confirm classify_message supports optional llm_provider only, with deterministic fallback

Then review Phase 10 only: Optional LLM Classifier.

Check that provider output is schema-validated, subject/body are treated as untrusted, raw headers are not sent to the provider, invalid output/provider exceptions fall back to deterministic rules, and whitelist/known-offender local safety state bypasses the LLM.

Do not add real OAuth. Do not add provider credentials. Do not send, move, delete, archive, or mutate email. Do not enable YOLO mode. Preserve the provider boundary: LLM classification may inform review only; live provider execution belongs to a separate explicit bridge.
```

## Team Plan

- **Amy**: orchestration and scope control. She keeps the product from wandering into OAuth swamp country before guarded automation exists.
- **Chip**: owns guarded YOLO-mode settings/guardrail implementation if Phase 10 review passes.
- **Rex**: security veto on LLM prompt boundaries, output validation, live-action safety gates, provider-boundary isolation, and XSS regressions.
- **Gus**: local demo verification, CLI ergonomics, CI, n8n dry-run bridge fit, and operator docs.
- **Fred**: safe automation/provider-action-limit research only; no direct OAuth implementation yet.

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- Optional LLM classifier exists only as a provider hook; no real provider wiring or credentials are implemented.
- No production OAuth yet.
- n8n workflow package needs real local import testing against Kent's actual n8n instance before activation.
- n8n approved action bridge is dry-run only; live provider actions still need a separate explicit reviewed workflow.
- YOLO mode is product direction only; must not be casually enabled.

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
