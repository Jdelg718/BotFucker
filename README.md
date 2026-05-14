# BotFucker

<p align="center">
  <img src="assets/botfucker-ff2k-hero.png" alt="FF2K-style character squashing a spam bot with a robotic fist" width="900">
</p>


BotFucker is a local-first inbox defense cockpit for filtering unsolicited sales outreach, generic AI-generated pitches, and repeated CRM follow-ups without handing the keys to your mailbox to a half-baked robot.

The project is intentionally simple: standard-library Python, deterministic classification, local SQLite review state, an audit trail, a browser review queue, and a strict provider boundary. BotFucker imports normalized mail-shaped JSON, lets a human review decisions locally, and saves provider-side execution for an explicit future bridge.


## BotFucker Current Design

The current core is split into reusable modules under `botfucker/`:

- `models.py` normalizes provider-specific mail into stable input/output objects.
- `classifier.py` returns structured deterministic classifications with reasons.
- `history.py` tracks sender history, warning counts, and strike levels in SQLite.
- `review_store.py` persists local review queue items and audit events in SQLite.
- `webhook_contract.py` normalizes bounded n8n/webhook email JSON into local review items.
- `review_cli.py` provides a provider-safe local review workflow around seeded/imported items.
- `responses.py` contains human-reviewable warning templates.
- `cli.py` keeps the IMAP proof-of-concept behavior behind the existing wrapper.

See [DESIGN.md](DESIGN.md) for the proposed architecture and roadmap.

## What It Does

- Accepts normalized email-shaped input from local files, n8n/webhook exports, or the legacy IMAP proof-of-concept path.
- Detects common cold outreach phrases like "quick call", "scale your business", and "wondering if you saw my last".
- Looks for generic AI-pitch markers such as overly formal structure, vague value propositions, and missing personal references.
- Produces structured classification results with reasons and recommended actions.
- Tracks sender/domain history and strike levels locally in SQLite.
- Persists a durable local review queue and audit log.
- Runs a local browser cockpit for reviewing, approving, dismissing, whitelisting, or blacklisting items in local SQLite state.
- Imports bounded n8n/webhook JSON after the provider layer has already fetched mail.
- Exports approved local audit events as an idempotent JSON bundle for a future provider bridge.
- Keeps provider credentials and live mailbox side effects outside the local UI and review queue.
- Leaves send/move/delete/archive provider actions for a future explicit action bridge.

## Safety First

The current product path is local-review-first and fails closed.

BotFucker does **not** need OAuth, IMAP passwords, SMTP passwords, or provider credentials to run the local review cockpit.

Local UI and review CLI actions do not:

- send replies
- move email
- delete email
- archive email
- call Gmail/Microsoft/IMAP/SMTP
- update a real provider whitelist or blacklist
- expose secrets in the browser

The legacy IMAP scanner still exists behind `outreach_filter.py`, but live automation requires both `--live` and `--auto-approve`. The preferred current path is n8n/provider fetch → normalized JSON → local SQLite review → human decision → approved-action export → future n8n action bridge.

## Requirements

- Python 3.10 or newer
- No third-party Python packages required
- Optional: n8n or another provider-side workflow to fetch mail and write normalized JSON
- Optional legacy path: an email account with IMAP/SMTP access if you are intentionally using `outreach_filter.py` directly

## Setup

Clone the repo:

```bash
git clone https://github.com/Jdelg718/BotFucker.git
cd BotFucker
```

Create a local blacklist file if you plan to use the legacy scanner:

```bash
cp blacklist.example.txt blacklist.txt
```

## Quick Local Demo

The current recommended demo path uses fake/local data only. No mailbox credentials, OAuth tokens, or provider setup required.

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
python3 -m unittest discover -s tests -v
rm -f botfucker_review.sqlite3
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3
```

Open:

```text
http://127.0.0.1:8765/
```

This demonstrates the local cockpit, durable review queue, sender history, and audit trail without touching a live inbox. Which is the sane order. Weird how that keeps coming up.

## Animated Explainer

A branded FF2K/HyperFrames product explainer lives in:

```text
promo/botfucker-animated-explainer/
```

Current rendered cut:

```text
promo/botfucker-animated-explainer/renders/botfucker-animated-explainer_narrated-final.mp4
```

It uses the same FF2K hero art and local-first safety copy as the browser cockpit: no live sends, no deletes, no OAuth in the BotFucker core, human review first, provider bridge later.

Preview/check/render from that folder:

```bash
npm run dev
npm run check
npm run render
```

## Optional Legacy IMAP/SMTP Setup

Only configure these environment variables if you are intentionally using the older `outreach_filter.py` IMAP/SMTP path. They are not needed for the local review UI, n8n import workflow, or current provider-boundary design.

Linux/macOS:

```bash
export BF_IMAP_HOST="imap.example.com"
export BF_IMAP_PORT="993"
export BF_SMTP_HOST="smtp.example.com"
export BF_SMTP_PORT="465"
export BF_EMAIL_ADDRESS="you@example.com"
export BF_EMAIL_PASSWORD="your-app-password"
export BF_WHITELIST_DOMAINS="yourcompany.com,trustedpartner.com"
export BF_WHITELIST_CONTACTS="person@example.com,client@example.com"
```

PowerShell:

```powershell
$env:BF_IMAP_HOST="imap.example.com"
$env:BF_IMAP_PORT="993"
$env:BF_SMTP_HOST="smtp.example.com"
$env:BF_SMTP_PORT="465"
$env:BF_EMAIL_ADDRESS="you@example.com"
$env:BF_EMAIL_PASSWORD="your-app-password"
$env:BF_WHITELIST_DOMAINS="yourcompany.com,trustedpartner.com"
$env:BF_WHITELIST_CONTACTS="person@example.com,client@example.com"
```

Optional settings:

```bash
export BF_INBOX_FOLDER="INBOX"
export BF_SALES_FOLDER="Junk/Sales"
export BF_BLACKLIST_FILE="blacklist.txt"
export BF_HISTORY_DB="botfucker_history.sqlite3"
```

## Common Provider Settings

Gmail:

```text
BF_IMAP_HOST=imap.gmail.com
BF_SMTP_HOST=smtp.gmail.com
```

Outlook / Microsoft 365:

```text
BF_IMAP_HOST=outlook.office365.com
BF_SMTP_HOST=smtp.office365.com
```

Yahoo:

```text
BF_IMAP_HOST=imap.mail.yahoo.com
BF_SMTP_HOST=smtp.mail.yahoo.com
```

## Phase 5 Local Review UI

The local browser UI supports exactly one explicit storage mode per run:

- `--sample-data` — deterministic fake data in memory for demos/tests.
- `--db PATH` — durable local SQLite review queue items and audit events.

Running the UI with neither mode, or with both modes, fails closed. Neither mode connects to IMAP/SMTP/OAuth providers, sends replies, moves/deletes/archives mail, or changes a real provider whitelist/blacklist. UI actions are local review decisions only.

Run the local sample UI:

```bash
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --sample-data
```

Seed a durable local SQLite queue, then run the UI against it:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db botfucker_review.sqlite3
```

Import webhook/n8n-shaped JSON into SQLite, then review it in the UI:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json n8n-messages.json
python3 -m botfucker.local_ui --db botfucker_review.sqlite3
```

Then open:

```text
http://127.0.0.1:8765/
```

Available local JSON endpoints:

- `GET /api/dashboard` — dashboard counts, safety mode flags, `storage_mode`, and SQLite DB basename when using `--db`.
- `GET /api/review-queue` — sample or durable SQLite review items. Optional `?status=pending` or `?status=actioned` filters are supported.
- `GET /api/senders` — sender history derived from local queue items and local audit events.
- `GET /api/audit-events` — in-memory sample audit log or durable SQLite audit log.
- `GET /api/settings` — safety settings, including human approval enabled, YOLO disabled, and storage mode.
- `POST /api/actions` — records a local review action only. Supported actions: `approve_warning`, `dismiss`, `whitelist_sender`, `blacklist_sender`.

Safety posture:

- Human approval is enabled.
- YOLO mode is visible but disabled.
- Provider authentication is not performed by the local UI.
- Sample mode actions are in-memory mock simulations only.
- SQLite mode actions update only `botfucker_review.sqlite3` review status/audit rows; they do not perform provider-side effects.
- The review DB should not contain secrets, raw auth tokens, passwords, or private provider headers.

YOLO warning copy shown in the UI: “YOLO mode lets BotFucker reply/block without asking you first. This can save time and also make you look like an unhinged mailbox goblin if configured badly. Start conservative.”

## Phase 3 Durable Review Queue CLI

Phase 3 adds a durable, local-only SQLite review queue plus a CLI workflow. This is not provider auth and it is not live mailbox automation. The review CLI never connects to IMAP/SMTP/OAuth providers, never sends mail, never moves/deletes/archives mail, and never changes a real provider whitelist or blacklist. Approvals are local review approvals only; they record that a human approved a proposed warning in SQLite, but they do not send the warning.

Seed deterministic fake/sample items:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 seed-samples
```

List pending local review items:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 list --status pending
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 list --status pending --json
```

Record local review decisions:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 approve sample-001 --actor you --note "approved local warning draft"
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 dismiss sample-002 --actor you
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 whitelist-sender sample-003 --actor you
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 blacklist-sender sample-004 --actor you
```

Show durable local audit history:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 audit
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 audit --json
```

Import local review items from JSON (a list of item objects, or `{ "items": [...] }`):

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-json review_items.json
cat review_items.json | python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-json -
```

Durable queue notes:

- Re-importing the same `item_id` is idempotent and does not duplicate items.
- Re-importing preserves `pending`/`actioned` human review status and audit history.
- The local SQLite DB must not contain secrets, tokens, passwords, or real mailbox credentials.
- Sample data uses reserved documentation domains only.

## Phase 4 n8n/Webhook Contract Import

Phase 4 adds a normalized JSON contract for messages that n8n or another provider-side workflow has already fetched. In this flow, n8n owns Gmail/Microsoft/IMAP credentials and maps mail into bounded JSON; BotFucker only imports that JSON into the local SQLite review queue. There is no HTTP listener, OAuth setup, provider auth, sending, moving, deleting, archiving, whitelisting, or blacklisting in this adapter.

Import n8n/webhook JSON from a file or stdin:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json n8n-messages.json
cat n8n-messages.json | python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json -
```

Accepted payload shapes include a single message object, a list of message objects, or an object with `items`, `events`, or `messages` arrays. Required fields are a stable message id, sender email, received timestamp, and subject and/or bounded preview/body text. The importer redacts secret-looking values, drops raw headers, truncates long snippets, classifies deterministically, and rejects invalid batches without partial import.

See [docs/webhook-contract.md](docs/webhook-contract.md) for the JSON examples and n8n mapping guidance.

## Phase 6 n8n Workflow Package

Phase 6 adds an importable starter workflow and operator guide for the safe n8n path:

- [`docs/n8n-workflow.json`](docs/n8n-workflow.json) — inactive n8n workflow starter with a provider-fetch placeholder, normalization node, file write, and local CLI import command.
- [`docs/n8n-workflow.md`](docs/n8n-workflow.md) — setup, mapping, environment variables, smoke test, and safety checklist.

The workflow keeps the same provider boundary as the webhook contract: n8n fetches mail and BotFucker imports bounded JSON into local SQLite review state. It does not send, move, delete, archive, whitelist, blacklist, or run live mailbox actions.

Typical local loop:

```bash
export BOTFUCKER_REPO="/path/to/BotFucker"
export BOTFUCKER_REVIEW_DB="/path/to/botfucker_review.sqlite3"
export BOTFUCKER_N8N_MESSAGES="/path/to/n8n-messages.json"

cd "$BOTFUCKER_REPO"
python3 -m botfucker.review_cli --db "$BOTFUCKER_REVIEW_DB" import-webhook-json "$BOTFUCKER_N8N_MESSAGES"
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db "$BOTFUCKER_REVIEW_DB"
```

## Phase 7 Provider Auth Plan

Phase 7 documents how provider auth should arrive later without shoving OAuth tokens into the local review UI like a raccoon hiding snacks in an engine bay.

See [`docs/provider-auth-plan.md`](docs/provider-auth-plan.md).

Phase 7 does **not** implement Gmail OAuth, Microsoft OAuth, IMAP password handling, YOLO mode, or send/move/delete provider calls. It defines:

- n8n-first versus direct OAuth tradeoffs
- secret storage requirements
- browser/server boundaries
- approved action export shape
- future n8n action bridge rules

## Phase 8 Approved Action Export

Phase 8 adds a local-only approved action export. This is **not** OAuth, not provider auth, and not mailbox automation. It turns human-approved SQLite audit events into an idempotent JSON bundle that n8n or a future provider bridge can consume later.

Example:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 approve sample-001 --actor you
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 export-approved-actions > approved-actions.json
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 export-approved-actions --since-audit-id audit-0001
```

Export constraints:

- exports approved intent only (`approve_warning` audit events)
- includes audit IDs/action IDs for downstream deduplication
- supports `--since-audit-id` cursoring
- omits message subject/snippet and provider credential material
- does not call Gmail, Microsoft, IMAP, SMTP, n8n, or any live provider from BotFucker core
- keeps browser UI actions local-only

## Test Before Going Live

Compile-check the script and package:

```bash
python3 -m py_compile outreach_filter.py botfucker/*.py
```

Run the unit tests. Tests use fake emails only and do not send mail:

```bash
python3 -m unittest discover -s tests -v
```

Run a dry scan:

```bash
python3 outreach_filter.py
```

Emit dry-run/review output as JSON lines:

```bash
python3 outreach_filter.py --json
```

Run live automation only after reviewing the dry-run output. `--live` must be paired with explicit approval before the tool can send replies, move messages, delete blacklisted messages, or update blacklist/history state:

```bash
python3 outreach_filter.py --live --auto-approve
```

## Scheduling

Run every 15 minutes with cron:

```cron
*/15 * * * * cd /path/to/BotFucker && /usr/bin/python3 outreach_filter.py --live --auto-approve >> outreach_filter.log 2>&1
```

For Windows Task Scheduler, use:

```text
Program: python
Arguments: C:\path\to\BotFucker\outreach_filter.py --live --auto-approve
```

## Tuning The Filters

The filter lists live in `botfucker/classifier.py`:

- `COLD_OUTREACH_PATTERNS`
- `AI_SIGNATURE_PATTERNS`

Good filter ideas should be specific enough to catch bot-like outreach without catching real clients, coworkers, support threads, invoices, or personal messages.

## Contributing

Ideas are welcome. Useful contributions include:

- new cold outreach patterns
- better false-positive protections
- provider-specific IMAP folder handling
- safer dry-run reporting
- lightweight NLP experiments
- tests with anonymized sample emails
- documentation for more email providers

Please do not commit real emails, private contact lists, passwords, tokens, or production blacklist data.

## Disclaimer

Email rules vary by provider and jurisdiction. Test carefully, keep a whitelist, and make sure any automated reply behavior is appropriate for your use case.
