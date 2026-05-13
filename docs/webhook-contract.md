# Phase 4 Webhook / n8n Payload Contract

Phase 4 is a safe adapter layer for email JSON that was already fetched by n8n or another provider-side workflow. BotFucker does not own provider credentials in this flow, does not expose an HTTP webhook listener, and does not send, move, delete, archive, whitelist, or blacklist provider mail.

Use `import-webhook-json` to normalize bounded message metadata into the local SQLite review queue.

## Ownership boundary

- n8n owns Gmail/Microsoft/IMAP/provider credentials and fetches messages.
- n8n maps each fetched message into the normalized JSON shape below.
- BotFucker reads that JSON from a file or stdin and writes local review records only.
- Do not include OAuth tokens, API keys, cookies, raw Authorization headers, provider credential IDs, or full unbounded email bodies.

## Accepted top-level shapes

BotFucker accepts any one of these shapes:

```json
{ "id": "gmail-msg-123", "from": { "email": "sender@example.com" }, "subject": "Hello", "snippet": "Preview", "receivedAt": "2026-05-13T09:30:00Z" }
```

```json
[
  { "id": "gmail-msg-123", "from": "Sender <sender@example.com>", "subject": "Hello", "snippet": "Preview", "receivedAt": "2026-05-13T09:30:00Z" }
]
```

```json
{ "messages": [ { "id": "gmail-msg-123", "from": { "email": "sender@example.com" }, "subject": "Hello", "bodyPreview": "Preview", "receivedAt": "2026-05-13T09:30:00Z" } ] }
```

The wrapper key may be `items`, `events`, or `messages`.

## Message fields

Required:

- `id`, `message_id`, `messageId`, `external_id`, or `externalId`: stable provider/workflow message id.
- `from.email`, `from.address`, `from` string, `from_email`, `fromEmail`, `sender_email`, or `senderEmail`: sender email.
- `receivedAt`, `received_at`, `date`, or `timestamp`: parseable timestamp.
- `subject` and/or a bounded preview field such as `snippet`, `preview`, `bodyPreview`, `text`, `body`, `body_text`, or `bodyText`.

Optional:

- `threadId`, `thread_id`, `conversationId`, or `conversation_id`.
- `from.name`, `from.displayName`, `from_name`, or `sender_name`.
- `to`: string or list of recipient strings/objects.
- `provider`: short provider label such as `gmail`, `outlook`, `imap`, or `n8n`.
- `source.workflow`: n8n workflow label used only for local source attribution.

## Recommended n8n mapping

Map provider nodes into a Function/Set node that emits only normalized fields:

```json
{
  "messages": [
    {
      "id": "={{ $json.id }}",
      "threadId": "={{ $json.threadId }}",
      "from": {
        "email": "={{ $json.from.email }}",
        "name": "={{ $json.from.name }}"
      },
      "subject": "={{ $json.subject }}",
      "snippet": "={{ $json.snippet || $json.bodyPreview }}",
      "receivedAt": "={{ $json.date }}",
      "provider": "gmail",
      "source": {
        "workflow": "inbox-to-botfucker-review",
        "node": "gmail-trigger"
      }
    }
  ]
}
```

Then export the JSON or pipe it locally:

```bash
python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json n8n-messages.json
cat n8n-messages.json | python3 -m botfucker.review_cli --db botfucker_review.sqlite3 import-webhook-json -
```

## Safety and normalization

BotFucker treats webhook JSON as untrusted input:

- Secret-looking keys and values are not persisted.
- Authorization headers, cookies, bearer tokens, API keys, passwords, and credential values are redacted from persisted text.
- Raw headers are not stored.
- Review snippets are bounded to 1200 characters and long values are marked `…[truncated]`.
- Text fields are control-character cleaned and bounded.
- Each imported item remains `mock_only=true` with the local-only safety note enforced by `DurableReviewStore`.
- Batches normalize fully before writing; if one message is invalid, no partial batch import occurs.

## Example normalized payload

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
      "source": { "workflow": "n8n-inbox-review", "node": "gmail-trigger" }
    }
  ]
}
```
