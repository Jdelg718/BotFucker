# BotFucker Handoff

## Repo

- GitHub: `https://github.com/Jdelg718/BotFucker`
- Default branch: `main`
- Latest merged milestone: PR #1 — v2 core library
- Related issue: #2 — branded UI, YOLO mode, provider auth

## What BotFucker Is

BotFucker is an AI-era inbox defense project.

It started as a Python proof-of-concept for detecting cold outreach, AI-generated sales pitches, and CRM follow-ups. It is now moving toward a review-first app that classifies junk outreach, drafts responses, tracks sender/domain strikes, and lets the user approve actions.

The public thesis:

> Use automation to protect productive work from automated interruption.

## Current Architecture

Important files:

```text
DESIGN.md                 # v2 architecture and principles
ROADMAP.md                # phased product roadmap
README.md                 # user-facing setup and project overview
outreach_filter.py        # compatibility CLI wrapper
botfucker/models.py       # normalized email/classification/review models
botfucker/classifier.py   # deterministic classifier
botfucker/history.py      # SQLite sender history + strike state
botfucker/responses.py    # warning templates
botfucker/cli.py          # CLI behavior / guarded live mode
tests/                    # fake-email-only tests
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

## Current Test Commands

Run from repo root:

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
python3 -m unittest discover -s tests -v
```

Expected current result: all tests pass.

## Current CLI Notes

View help:

```bash
python3 outreach_filter.py --help
```

Dry-run is the default.

Live mode is intentionally guarded:

```bash
python3 outreach_filter.py --live
```

should fail unless explicit automation is enabled with the appropriate guard flag, currently `--auto-approve`.

## Next PR Recommendation

Build **Phase 2: Review Queue + Local UI Skeleton**.

Do not start with OAuth yet. First create the product shell and review model using fake data.

### Suggested branch

```bash
git checkout main
git pull origin main
git checkout -b phase-2-review-ui
```

### Suggested scope

1. Add review queue persistence/model if not already complete enough.
2. Add fake sample messages for local development.
3. Add a local UI skeleton.
4. Use BotFucker branding:
   - dark background
   - orange/blue accents
   - repo hero image/logo
   - sharp anti-bot tone, not corporate SaaS slop
5. Add screens:
   - dashboard
   - review queue
   - sender history
   - settings
6. Make YOLO visible only as disabled/scary settings copy, not functional automation yet.
7. Add docs for running the UI locally.

### UI Acceptance Criteria

- Runs without email credentials.
- Uses fake/sample messages only.
- Shows pending review cards with:
  - sender
  - domain/company
  - subject
  - summary
  - classification
  - confidence
  - reasons
  - strike level
  - proposed action
  - drafted response
- Shows actions visually:
  - approve warning
  - archive
  - blacklist sender
  - blacklist domain
  - whitelist
  - mark safe
  - escalate
- Does not actually send email.

## Suggested Prompt for Codex/Claude

```text
You are working on BotFucker, an AI-era inbox defense app.

Read DESIGN.md, ROADMAP.md, HANDOFF.md, README.md, and issue #2.

Implement Phase 2 only: a local review queue + branded UI skeleton using fake/sample data. Do not add real email OAuth yet. Do not send email. Keep human approval as the default product path. YOLO mode may appear only as disabled/scary settings UI copy.

Before editing, propose the file structure and implementation plan. Then implement, add tests or smoke checks, and update README with local run instructions.
```

## Known Follow-Up Issues

- Deterministic classifier still needs real-world tuning.
- No production OAuth yet.
- No real review UI yet.
- n8n/webhook contracts not implemented yet.
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
