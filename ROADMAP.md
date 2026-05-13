# BotFucker Roadmap

BotFucker is evolving from a local inbox-filtering script into an AI-era inbox defense system.

The thesis is simple:

> Use automation to protect productive work from automated interruption.

AI is excellent when builders use it to build. It is garbage when lead-gen parasites use it to manufacture fake personalization and CRM follow-up sludge at scale. BotFucker exists to turn the tools around.

## Current State

Merged in PR #1:

- v2 design document
- reusable `botfucker/` Python package
- normalized email model
- structured classifier results
- deterministic outreach classifier
- SQLite sender history and strike tracking
- warning templates
- guarded live mode requiring explicit `--auto-approve`
- dry-run default
- tests for classifier/history/safety behavior

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

### Phase 2 — Review Queue + Local UI Skeleton

Goal: create a usable local review experience without committing to production auth yet.

Deliverables:

- `review_items` model / JSON format
- audit event model
- local sample data generator using fake emails
- minimal web UI or static dashboard prototype
- branded dark/orange/blue BotFucker styling
- screens:
  - dashboard
  - review queue
  - sender history
  - settings mock
- actions represented in UI:
  - approve warning
  - archive
  - blacklist sender
  - blacklist domain
  - whitelist
  - mark safe
  - escalate strike

Acceptance criteria:

- UI runs locally without email credentials.
- Uses fake/sample emails only.
- No real sends.
- Shows classifier reasons and proposed draft responses.
- Makes approval-first workflow obvious.

### Phase 3 — CLI Review Workflow

Goal: make the core usable without a browser.

Deliverables:

- `scan` command outputs review queue
- `review` command displays pending items
- `approve` command applies a selected action
- `whitelist` / `blacklist` helpers
- JSON output suitable for n8n/webhooks

Acceptance criteria:

- No live send without explicit approval or YOLO mode.
- Review items are durable and auditable.

### Phase 4 — n8n/Webhook Integration

Goal: integrate with existing automation systems without putting mailbox credentials directly into BotFucker.

Deliverables:

- webhook input contract
- webhook output/action contract
- n8n workflow documentation
- Gmail/Microsoft trigger examples
- approval callback pattern

Acceptance criteria:

- n8n holds provider credentials.
- BotFucker receives normalized messages or provider payloads.
- Human approval can happen outside BotFucker if desired.

### Phase 5 — Provider Auth

Goal: support real users connecting email and LLM providers.

Email providers:

- Gmail OAuth
- Microsoft OAuth
- IMAP fallback for developers/self-hosters

LLM providers:

- OpenAI API key
- Anthropic API key
- OpenRouter API key
- local/custom endpoint later

Acceptance criteria:

- Secrets never reach the browser.
- Keys are not committed.
- OAuth and key storage are documented clearly.

### Phase 6 — Optional LLM Classifier

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

### Phase 7 — Guarded YOLO Mode

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

Next PR should be **Phase 2: Review Queue + Local UI Skeleton**.

Do not start with OAuth. Auth first will create a pile of provider-specific complexity before the product shape is clear. Build the review queue and fake-data UI first, then wire providers into a known interface.
