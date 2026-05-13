# BotFucker

<p align="center">
  <img src="assets/botfucker-ff2k-hero.png" alt="FF2K-style character squashing a spam bot with a robotic fist" width="900">
</p>


BotFucker is a small Python automation project for filtering unsolicited sales outreach, generic AI-generated pitches, and repeated CRM follow-ups from an IMAP mailbox.

The project is intentionally simple: standard-library Python, readable regex rules, a local domain blacklist, a local SQLite sender-history database, and a whitelist for people or domains that should never be filtered.


## BotFucker v2 Direction

The v2 core is now split into reusable modules under `botfucker/`:

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

- Connects to an IMAP inbox.
- Scans unread messages from the last 24 hours.
- Detects common cold outreach phrases like "quick call", "scale your business", and "wondering if you saw my last".
- Looks for generic AI-pitch markers such as overly formal structure, vague value propositions, and missing personal references.
- Produces structured classification results with reasons and recommended actions.
- Tracks sender/domain history and strike levels locally in SQLite.
- Drafts recommended warning actions for human review by default.
- Sends notices, moves flagged messages, and updates blacklist state only when both `--live` and `--auto-approve` are supplied.
- Marks strike-4 senders as `block_candidate` for review instead of sending the strike-3 warning endlessly.
- Deletes future unread messages from explicitly blacklisted domains only in approved live automation mode.
- Skips all whitelisted contacts and domains.

## Safety First

The script runs in dry-run mode by default.

Dry-run mode logs what it would do, but does not:

- send replies
- move email
- delete email
- update `blacklist.txt`
- send warning replies without explicit `--live --auto-approve`

`--live` by itself fails closed. Use `--auto-approve` only after testing the filters on your own mailbox and accepting legacy YOLO-style automation.

## Requirements

- Python 3.10 or newer
- An email account with IMAP enabled
- SMTP access for sending replies
- An app password if your provider requires one

No third-party Python packages are required.

## Setup

Clone the repo:

```bash
git clone https://github.com/Jdelg718/BotFucker.git
cd BotFucker
```

Create a local blacklist file:

```bash
cp blacklist.example.txt blacklist.txt
```

Configure environment variables.

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

## Phase 2 Local Review UI

Phase 2 includes a branded local UI skeleton backed by deterministic fake data only. It does not connect to IMAP/SMTP/OAuth providers, does not send replies, does not move or delete mail, and does not change any real whitelist or blacklist. UI actions are mock simulations recorded as in-memory audit events.

Run the local sample UI:

```bash
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --sample-data
```

Then open:

```text
http://127.0.0.1:8765/
```

Available local JSON endpoints:

- `GET /api/dashboard` — dashboard counts and safety mode flags.
- `GET /api/review-queue` — deterministic sample review items.
- `GET /api/senders` — sample sender history derived from the queue and local audit events.
- `GET /api/audit-events` — in-memory mock action audit log.
- `GET /api/settings` — safety settings, including human approval enabled and YOLO disabled.
- `POST /api/actions` — records a mock action only. Supported actions: `approve_warning`, `dismiss`, `whitelist_sender`, `blacklist_sender`.

Safety posture:

- Human approval is enabled.
- YOLO mode is visible but disabled.
- Provider authentication is coming later.
- All Phase 2 actions are mock/local simulations only.

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
