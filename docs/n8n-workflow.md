# Phase 6 n8n Workflow Package

Phase 6 packages the safe n8n path around the webhook contract: n8n fetches provider mail, maps it into bounded JSON, writes `n8n-messages.json`, and calls BotFucker's local import CLI. BotFucker still stays out of provider auth and provider side effects. Boring boundary, excellent boundary.

## Provider boundary

- n8n owns Gmail, Microsoft, IMAP, or other provider connections.
- BotFucker does not receive OAuth tokens, refresh tokens, API keys, cookies, raw provider headers, app passwords, or mailbox connection settings.
- BotFucker receives only normalized message metadata and bounded preview text.
- BotFucker imports into local SQLite review state only.
- This workflow must not send mail, move mail, delete mail, archive mail, update a provider whitelist, update a provider blacklist, or change provider labels/folders.

## Files

- [`docs/n8n-workflow.json`](n8n-workflow.json): importable n8n workflow starter.
- [`docs/webhook-contract.md`](webhook-contract.md): normalized JSON contract accepted by `import-webhook-json`.

The workflow is intentionally inactive by default and includes a provider-fetch placeholder. Replace the placeholder with your actual Gmail/Microsoft/IMAP fetch node inside n8n, then leave the Normalize node as the hard boundary before BotFucker sees anything.

## Environment variables for n8n Execute Command

Set these in the environment where n8n runs, or edit the Execute Command node locally:

```bash
export BOTFUCKER_REPO="/path/to/BotFucker"
export BOTFUCKER_REVIEW_DB="/path/to/botfucker_review.sqlite3"
export BOTFUCKER_N8N_MESSAGES="/path/to/n8n-messages.json"
```

The import node runs:

```bash
cd "${BOTFUCKER_REPO:-/path/to/BotFucker}" && \
python3 -m botfucker.review_cli \
  --db "${BOTFUCKER_REVIEW_DB:-botfucker_review.sqlite3}" \
  import-webhook-json "${BOTFUCKER_N8N_MESSAGES:-n8n-messages.json}"
```

No `--live`. No `--auto-approve`. No provider action. If those appear in this workflow, someone has converted a seatbelt into decorative yarn.

## n8n import steps

1. In n8n, import `docs/n8n-workflow.json`.
2. Replace **Fetch Provider Mail Placeholder** with a Gmail, Microsoft, IMAP, or other provider node.
3. Configure that provider node to return only candidate recent messages you want reviewed.
4. Confirm **Normalize BotFucker Payload** emits this shape:

```json
{
  "messages": [
    {
      "id": "gmail-msg-123",
      "threadId": "gmail-thread-7",
      "from": { "email": "sales@example.com", "name": "Sales Bot" },
      "subject": "Can we book a quick call?",
      "snippet": "I help teams scale your business with lead generation.",
      "receivedAt": "2026-05-13T09:30:00Z",
      "provider": "gmail",
      "source": { "workflow": "botfucker-local-review-import", "node": "Normalize BotFucker Payload" }
    }
  ]
}
```

5. Confirm **Convert Normalized JSON To File** converts the normalized JSON item into binary field `data`.
6. Confirm **Write n8n-messages.json** writes that binary JSON file to the path referenced by `BOTFUCKER_N8N_MESSAGES`.
7. Run **Import Into Local Review Queue**.
8. Start the local UI:

```bash
cd "$BOTFUCKER_REPO"
python3 -m botfucker.local_ui --host 127.0.0.1 --port 8765 --db "$BOTFUCKER_REVIEW_DB"
```

8. Open `http://127.0.0.1:8765/` and review the imported queue.

## Mapping guide

Map provider output into the normalized contract using these stable fields:

- `id`: provider message id, or a stable workflow-generated id.
- `threadId`: provider thread/conversation id when available.
- `from.email`: sender address.
- `from.name`: display name when available.
- `subject`: subject line.
- `snippet`: bounded preview/body preview, max 1200 chars before import.
- `receivedAt`: parseable timestamp.
- `provider`: short label such as `gmail`, `outlook`, `imap`, or `n8n`.
- `source.workflow`: local workflow label for attribution.

Do not map raw headers, cookies, auth material, provider account metadata, private contact lists, or full unbounded email bodies. The importer redacts and truncates defensively, but making it eat garbage just to prove it can is not architecture. It's hazing.

## Local smoke test without provider mail

Save this as `n8n-messages.json`:

```json
{
  "messages": [
    {
      "id": "demo-msg-001",
      "threadId": "demo-thread-001",
      "from": { "email": "sales@example.com", "name": "Demo Sales" },
      "subject": "Quick call about scaling your business",
      "snippet": "I help teams scale your business with lead generation. Are you free next week?",
      "receivedAt": "2026-05-13T09:30:00Z",
      "provider": "n8n",
      "source": { "workflow": "botfucker-local-review-import", "node": "manual-test" }
    }
  ]
}
```

Then run:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json n8n-messages.json
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 list --status pending
python3 -m botfucker.local_ui --db botfucker_review.sqlite3
```

## Safety checklist before enabling a real n8n schedule

- The n8n workflow is inactive until explicitly enabled.
- The provider node is read/fetch only.
- The Execute Command node contains `import-webhook-json` and does not contain `--live` or `--auto-approve`.
- The normalized JSON does not include raw headers or mailbox access data.
- The BotFucker UI is run on `127.0.0.1` unless intentionally tunneled.
- Human review happens before any real mailbox action.

## Next phase after this

Once this workflow is tested locally, the next product phase should be an optional provider-side callback/action contract. That should still be approval-first: BotFucker records human intent, and n8n may later perform provider actions only from a separate, explicit action export. Keep the loaded gun in a different drawer. Preferably locked.
