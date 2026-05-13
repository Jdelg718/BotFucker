import json
import tempfile
import unittest
from pathlib import Path

from botfucker.review_store import DurableReviewStore
from botfucker.webhook_contract import WebhookPayloadError, iter_webhook_review_items, webhook_payload_to_review_item


class WebhookContractTests(unittest.TestCase):
    def sample_payload(self):
        return {
            "id": "gmail-msg-123",
            "threadId": "gmail-thread-7",
            "from": {"email": "Sales@Example.COM", "name": "Sales Bot"},
            "subject": "Can we book a quick call?",
            "snippet": "I help teams scale your business with lead generation.",
            "body": "I help teams scale your business with lead generation. Could we book a quick call next week?",
            "receivedAt": "2026-05-13T09:30:00Z",
            "provider": "gmail",
            "source": {"workflow": "n8n-inbox-review", "node": "gmail-trigger", "account": "support@example.com"},
        }

    def test_valid_n8n_payload_normalizes_to_review_item(self):
        item = webhook_payload_to_review_item(self.sample_payload())
        self.assertEqual(item.item_id, "webhook:gmail:gmail-msg-123")
        self.assertEqual(item.message_id, "gmail-msg-123")
        self.assertEqual(item.thread_id, "gmail-thread-7")
        self.assertEqual(item.from_email, "sales@example.com")
        self.assertEqual(item.from_name, "Sales Bot")
        self.assertEqual(item.sender_domain, "example.com")
        self.assertEqual(item.subject, "Can we book a quick call?")
        self.assertIn("lead generation", item.snippet)
        self.assertEqual(item.received_at, "2026-05-13T09:30:00+00:00")
        self.assertEqual(item.source, "webhook:gmail:n8n-inbox-review")
        self.assertEqual(item.classification, "cold_outreach")
        self.assertEqual(item.recommended_action, "warn_1")
        self.assertTrue(item.mock_only)
        self.assertIn("No email was sent", item.safety_note)

    def test_secret_like_fields_are_not_persisted(self):
        payload = self.sample_payload()
        payload.update(
            {
                "headers": {"Authorization": "Bearer SECRET", "Cookie": "sid=SECRET", "X-Trace": "ok"},
                "authorization": "Bearer SECRET",
                "access_token": "SECRET_TOKEN",
                "subject": "Token test Bearer SECRET",
                "snippet": "Cookie: sid=SECRET Authorization: Bearer SECRET visible copy",
                "source": {"workflow": "n8n", "credential": "SECRET_TOKEN", "api_key": "SECRET_KEY", "node": "gmail"},
            }
        )
        item = webhook_payload_to_review_item(payload)
        persisted = json.dumps(item.to_dict(), sort_keys=True)
        self.assertNotIn("SECRET", persisted)
        self.assertNotIn("Bearer", persisted)
        self.assertNotIn("Cookie", persisted)
        self.assertIn("[redacted]", item.subject)
        self.assertIn("[redacted]", item.snippet)
        self.assertEqual(item.source, "webhook:gmail:n8n")

    def test_body_is_truncated_for_review_storage(self):
        payload = self.sample_payload()
        payload.pop("snippet")
        payload["body"] = "A" * 10000
        item = webhook_payload_to_review_item(payload)
        self.assertLessEqual(len(item.snippet), 1200)
        self.assertTrue(item.snippet.endswith("…[truncated]"))

    def test_payload_collections_accept_lists_and_common_wrappers(self):
        payload = self.sample_payload()
        for wrapped in ([payload], {"items": [payload]}, {"events": [payload]}, {"messages": [payload]}):
            items = iter_webhook_review_items(wrapped)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].message_id, "gmail-msg-123")

    def test_missing_required_fields_fail_cleanly_without_partial_import(self):
        bad = self.sample_payload()
        bad.pop("id")
        with self.assertRaises(WebhookPayloadError):
            webhook_payload_to_review_item(bad)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            with DurableReviewStore(db_path) as store:
                with self.assertRaises(WebhookPayloadError):
                    iter_webhook_review_items({"items": [self.sample_payload(), bad]})
                self.assertEqual(store.list_items(status="all"), [])


if __name__ == "__main__":
    unittest.main()
