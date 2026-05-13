# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: PR #6 — durable local UI mode
- Current working branch: `phase-6-n8n-workflow-package`
- Current PR target: Phase 6 n8n workflow package

## What BotFucker Is

BotFucker is an AI-era inbox defense project.

It started as a Python proof-of-concept for detecting cold outreach, AI-generated sales pitches, and CRM follow-ups. It is now a local-first review cockpit: classify suspicious outreach, store review items locally, show a browser review queue, track audit events, and let the human approve actions before any provider-side automation exists.

The public thesis:

> Use automation to protect productive work from automated interruption.

## Current Architecture

Important files:

```text
DESIGN.md                    # v2 architecture and principles
ROADMAP.md                   # phased product roadmap, current through Phase 6
docs/webhook-contract.md     # normalized n8n/webhook JSON contract
docs/n8n-workflow.json       # importable n8n starter workflow
docs/n8n-workflow.md         # n8n operator guide and safety checklist
README.md                    # user-facing setup and project overview
outreach_filter.py           # compatibility CLI wrapper
botfucker/models.py          # normalized email/classification/review models
botfucker/classifier.py      # deterministic classifier
botfucker/history.py         # SQLite sender history + strike state
botfucker/review_queue.py    # review item/audit models and sample data helpers
botfucker/review_store.py    # durable SQLite review queue and audit store
botfucker/review_cli.py      # durable local review CLI
botfucker/webhook_contract.py # n8n/webhook payload sanitizer/import adapter
botfucker/local_ui.py        # local browser review UI server
web/                         # static UI assets
tests/                       # fake-email-only tests
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

## Phase 6 Scope

Phase 6 packages the n8n integration path without crossing the provider boundary.

Delivered/targeted files:

- `docs/n8n-workflow.json`: inactive n8n starter workflow with placeholder provider fetch, normalization, file write, and local CLI import.
- `docs/n8n-workflow.md`: mapping guide, env vars, smoke test, and safety checklist.
- `tests/test_n8n_workflow_docs.py`: validates workflow JSON, required nodes, local-only command, and forbidden side-effect docs.
- README/ROADMAP/HANDOFF updates.

## Next PR Recommendation After Phase 6

Build **Phase 7: Provider Auth Planning Stub**, not real OAuth yet.

Suggested branch:

```bash
git checkout main
git pull origin main
git checkout -b phase-7-provider-auth-plan
```

Suggested scope:

1. Document direct OAuth vs n8n-first provider integration paths.
2. Define secret storage requirements and browser/server boundaries.
3. Define provider action export/callback contract for later approved actions.
4. Add docs tests/checks proving no example commits secrets or browser-visible tokens.
5. Do not implement Gmail/Microsoft OAuth yet.

## Suggested Prompt for Codex/Claude

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, docs/webhook-contract.md, and docs/n8n-workflow.md.

Implement Phase 7 only: a provider-auth planning stub and action-boundary design. Do not add real OAuth, do not add provider credentials, do not send/move/delete/archive email, and do not enable YOLO mode. Preserve the provider boundary: BotFucker core remains local-review-first, while provider actions require a later explicit bridge.

Use TDD/docs checks where possible. Add or update tests before docs/behavior changes. Run py_compile and the full unittest suite before opening a PR.
```

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- No production OAuth yet.
- n8n workflow package needs real local import testing against Kent's actual n8n instance before activation.
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
