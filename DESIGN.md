# BotFucker v2 Design: AI-Era Inbox Self-Defense

BotFucker v1 is a small IMAP/SMTP proof-of-concept. It proves the basic point: cold outreach, CRM follow-ups, and generic AI sales pitches can be detected and pushed out of the inbox.

BotFucker v2 should become something stronger:

> A consent enforcement system for the AI spam era.

The goal is not to build another spam filter. The goal is to help productive people protect their attention from automated interruption, while keeping humans in control of anything destructive, public, or legally sensitive.

## Problem

AI makes builders more productive. It also lets non-builders manufacture fake personalization, fake urgency, and fake relationships at scale.

The result is inbox sludge:

- cold sales outreach
- AI-generated pitches
- repeated CRM follow-ups
- fake "just checking in" sequences
- low-effort lead-gen campaigns
- messages where the sender benefits and the recipient pays the attention tax

Most of these emails are not opportunities. They are extraction attempts.

## Current v1 Behavior

The current Python script:

- connects to an IMAP inbox
- scans unread messages from the last 24 hours
- detects outreach patterns with regexes
- detects generic AI-like language heuristically
- sends one opt-out notice in live mode
- moves flagged messages to `Junk/Sales`
- blacklists sender domains locally
- deletes future unread messages from blacklisted domains

This is useful as a proof-of-concept, but it is intentionally primitive.

## v1 Limitations

- Requires mailbox credentials through environment variables
- Uses simple regex and heuristics only
- Does not maintain rich sender/company history
- Does not support review/approval before sending notices
- Does not track strike counts or escalation state
- Does not integrate with n8n, Gmail/Microsoft OAuth, or webhook-based workflows
- Treats sender domains too bluntly for some real-world cases

## v2 Principles

1. **Human approval by default**
   - BotFucker may classify and draft.
   - The human approves before replies, blacklists, or escalations are sent.

2. **Delete bloat, keep signal**
   - The inbox should surface real work, real customers, and real relationships.
   - Repetitive sales automation should be compressed into a review queue or discarded.

3. **Consent matters**
   - If a sender is told to stop, future messages should be treated differently.
   - Ignoring opt-out requests should move a sender up the strike ladder.

4. **Evidence over vibes**
   - Each classification should include reasons.
   - Example: "CRM follow-up phrase", "asks for demo", "no prior relationship", "ignored previous warning".

5. **Safety before aggression**
   - Never auto-send angry or legal-ish messages without approval.
   - Never delete mail permanently by default.
   - Prefer archive/quarantine over destruction.

## Proposed Architecture

```text
Email Provider / n8n Trigger
        |
        v
Message Normalizer
        |
        v
Classifier
(regex + rules + optional LLM)
        |
        v
Sender History Store
(SQLite/Postgres/Google Sheet/Airtable/etc.)
        |
        v
Review Queue
        |
        +--> Approve: archive
        +--> Approve: send warning
        +--> Approve: blacklist
        +--> Approve: escalate
        +--> Mark safe / whitelist
```

## Components

### 1. Email ingestion

Preferred production path:

- n8n Gmail/Microsoft trigger
- OAuth-managed credentials for inbox providers
- API-key authentication for BotFucker service/API clients
- no raw app password in BotFucker config

Fallback developer path:

- local IMAP adapter
- dry-run mode by default

### 2. Message normalizer

Convert provider-specific email payloads into a stable object:

```json
{
  "message_id": "provider-id",
  "thread_id": "thread-id",
  "from_email": "sales@example.com",
  "from_name": "Sales Person",
  "sender_domain": "example.com",
  "to": ["me@example.com"],
  "subject": "Quick question",
  "body_text": "...",
  "received_at": "2026-05-13T12:00:00Z",
  "headers": {}
}
```

### 3. Classifier

The classifier should produce structured output:

```json
{
  "classification": "cold_outreach",
  "confidence": 0.91,
  "recommended_action": "warn_1",
  "reasons": [
    "contains demo/call request",
    "generic personalization",
    "no known relationship",
    "first contact from sender domain"
  ]
}
```

Initial categories:

- `safe`
- `customer_or_partner`
- `newsletter`
- `cold_outreach`
- `ai_generated_pitch`
- `crm_followup`
- `known_offender`
- `unknown_review_needed`

### 4. Sender history / strike system

Track:

- sender email
- sender domain
- company name if known
- first seen
- last seen
- message count
- classification counts
- warnings sent
- last warning date
- current strike level
- whitelist/blacklist status

Suggested strike ladder:

- **Strike 0:** classify only / no action
- **Strike 1:** polite opt-out and data removal request
- **Strike 2:** firm continued-contact warning
- **Strike 3:** aggressive complaint-ready notice
- **Strike 4:** block/blackhole/report candidate

### 5. Review queue

BotFucker should make the human decision cheap:

- show sender, subject, summary, reasons, confidence
- show proposed action
- draft the response
- provide one-click approve/skip/block/whitelist

Possible frontends:

- n8n approval workflow
- Telegram approval buttons
- branded hosted review queue for non-technical users
- simple local web UI
- GitHub issue-style queue for development/testing

The core should stay frontend-agnostic: normalized messages, classifications,
review-queue records, and approval actions should be API-friendly so a branded UI
can be added later without rewriting the classifier or sender-history logic.

### 6. Draft responses

Drafts should be generated from templates first, LLM second.

Tone levels:

- `polite`
- `firm`
- `sharp`
- `legalish`

No response should be sent automatically unless the user explicitly configures automation for a class of messages.
A YOLO/auto-approve mode may exist for power users and cron jobs, but it must be
a clearly named guarded action mode, disabled by default, and separate from ordinary live/provider access.

## Near-Term Roadmap

### Phase 1 — safer core library

- Refactor `outreach_filter.py` into reusable modules
- Add a normalized message model
- Add structured classification output
- Add a local SQLite sender history store
- Add dry-run JSON output
- Add tests for classification and strike logic

### Phase 2 — review workflow

- Add a review queue format
- Add generated draft warnings
- Add CLI commands:
  - `scan`
  - `review`
  - `approve`
  - `whitelist`
  - `blacklist`

### Phase 3 — n8n integration

- Add webhook input/output contract
- Document n8n Gmail/Microsoft trigger flow
- Support approval callbacks
- Keep credentials in n8n, not in BotFucker

### Phase 4 — optional LLM classifier

- Add optional LLM classification behind a provider interface
- Require structured JSON output
- Keep deterministic rules as fallback
- Include prompt-injection hardening: emails are untrusted content

## Safety Defaults

- Dry-run by default
- Human approval before sending replies
- Archive/quarantine before delete
- Whitelist support always available
- Never commit credentials, mailbox exports, private contact lists, or real email samples
- Treat email content as untrusted input

## Project Thesis

AI is good when builders use it to build. AI is garbage when parasites use it to manufacture interruption.

BotFucker exists to turn the tools around:

> Use automation to protect productive work from automated interruption.
