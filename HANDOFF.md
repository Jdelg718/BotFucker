# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: PR #8 — provider auth boundary plan
- Current working branch: `main`
- Current PR target: none; next recommended branch is `phase-8-approved-action-export`
- Current local demo target: pull repo into Kodex/Codex and demonstrate the local review cockpit on `127.0.0.1:8765`

## What BotFucker Is

BotFucker is an AI-era inbox defense project.

It started as a Python proof-of-concept for detecting cold outreach, AI-generated sales pitches, and CRM follow-ups. It is now a local-first review cockpit: classify suspicious outreach, store review items locally, show a browser review queue, track audit events, and let the human approve actions before any provider-side automation exists.

The public thesis:

> Use automation to protect productive work from automated interruption.

## Current Architecture

Important files:

```text
DESIGN.md                     # v2 architecture and principles
ROADMAP.md                    # phased product roadmap, current through Phase 8 recommendation
docs/webhook-contract.md      # normalized n8n/webhook JSON contract
docs/n8n-workflow.json        # importable n8n starter workflow
docs/n8n-workflow.md          # n8n operator guide and safety checklist
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
15b8ee3 docs: add provider auth boundary plan (#8)
```

If this handoff update has been merged after that, the top commit will be newer. The important part is that PR #8 content is present.

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
- n8n is the planned credential buffer
- next build is approved-action export, not live provider mutation

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

## Next PR Recommendation

Build **Phase 8: Approved Action Export**, not OAuth.

Suggested branch:

```bash
git checkout main
git pull origin main
git checkout -b phase-8-approved-action-export
```

Suggested scope:

1. Add a local-only `export-approved-actions` command.
2. Export only human-approved SQLite audit events.
3. Include audit IDs / action IDs so n8n can dedupe downstream.
4. Provide `--since-audit-id` or equivalent cursor support.
5. Strip/omit secrets, private headers, OAuth tokens, passwords, and provider credentials.
6. Do not call Gmail, Microsoft, IMAP, SMTP, or n8n from BotFucker core.
7. Add tests before implementation.

## Suggested Prompt for Kodex/Codex

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, docs/webhook-contract.md, docs/n8n-workflow.md, and docs/provider-auth-plan.md.

First, verify the current local demo path without changing behavior:
- run python3 -m py_compile outreach_filter.py botfucker/*.py
- run python3 -m unittest discover -s tests -v
- seed sample data with python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
- launch python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3

Then implement Phase 8 only: Approved Action Export.

Use strict TDD:
1. Write failing tests first for approved-only export, cursor/idempotency behavior, and secret/provider-boundary safety.
2. Run the focused tests and confirm they fail for the expected reason.
3. Implement the minimal CLI/store behavior to pass.
4. Run py_compile and the full unittest suite.

Do not add real OAuth. Do not add provider credentials. Do not send, move, delete, archive, or mutate email. Do not enable YOLO mode. Preserve the provider boundary: BotFucker exports approved intent only; provider execution belongs to a later explicit bridge.
```

## Team Plan

- **Amy**: orchestration and scope control. She keeps the product from wandering into OAuth swamp country before the action contract exists.
- **Chip**: Phase 8 implementation using strict TDD.
- **Rex**: security veto on export content, credential leakage, unapproved actions, browser-triggered side effects, and XSS regressions.
- **Gus**: local demo verification, CLI ergonomics, CI, n8n bridge fit, and operator docs.
- **Fred**: provider/API research only after export shape stabilizes; no implementation until the boundary is proven.

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- No production OAuth yet.
- n8n workflow package needs real local import testing against Kent's actual n8n instance before activation.
- Approved action export is not implemented yet.
- LLM classifier not implemented yet.
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
