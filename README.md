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
