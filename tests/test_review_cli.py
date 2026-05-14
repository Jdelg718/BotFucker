import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from botfucker import review_cli
from botfucker.review_store import DurableReviewStore


class ReviewCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = review_cli.main(list(args))
        return code, stdout.getvalue()

    def test_seed_list_approve_and_audit_workflow_persists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"

            code, output = self.run_cli("--db", str(db_path), "seed-samples")
            self.assertEqual(code, 0)
            self.assertIn("Seeded 4 sample review items", output)

            code, output = self.run_cli("--db", str(db_path), "list", "--status", "pending", "--json")
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in output.splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["item_id"], "sample-001")
            self.assertTrue(rows[0]["mock_only"])

            code, output = self.run_cli(
                "--db",
                str(db_path),
                "approve",
                "sample-001",
                "--actor",
                "cli-test",
                "--note",
                "local approval only",
            )
            self.assertEqual(code, 0)
            self.assertIn("approve_warning recorded locally", output)
            self.assertIn("No email was sent", output)

            code, output = self.run_cli("--db", str(db_path), "audit", "--json")
            self.assertEqual(code, 0)
            events = [json.loads(line) for line in output.splitlines()]
            self.assertEqual(events[0]["action"], "approve_warning")
            self.assertEqual(events[0]["actor"], "cli-test")

            with DurableReviewStore(db_path) as store:
                self.assertEqual(store.get_item("sample-001").status, "actioned")

    def test_sender_decision_commands_are_mock_review_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            self.run_cli("--db", str(db_path), "seed-samples")

            for command, expected_action in (
                ("dismiss", "dismiss"),
                ("whitelist-sender", "whitelist_sender"),
                ("blacklist-sender", "blacklist_sender"),
            ):
                item_id = {"dismiss": "sample-002", "whitelist-sender": "sample-003", "blacklist-sender": "sample-004"}[command]
                code, output = self.run_cli("--db", str(db_path), command, item_id, "--actor", "cli-test")
                self.assertEqual(code, 0)
                self.assertIn(f"{expected_action} recorded locally", output)
                self.assertIn("No email was sent", output)

    def test_review_cli_does_not_require_credentials_or_touch_provider_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            with mock.patch("imaplib.IMAP4_SSL", side_effect=AssertionError("provider touched")), mock.patch(
                "smtplib.SMTP_SSL", side_effect=AssertionError("smtp touched")
            ):
                code, output = self.run_cli("--db", str(db_path), "seed-samples")
                self.assertEqual(code, 0)
                code, output = self.run_cli("--db", str(db_path), "approve", "sample-001")
                self.assertEqual(code, 0)
                self.assertIn("local review approval only", output)

    def test_import_json_file_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            import_path = Path(tmpdir) / "items.json"
            import_path.write_text(
                json.dumps(
                    [
                        {
                            "item_id": "json-001",
                            "message_id": "<json-001@example.com>",
                            "thread_id": "thread-json-001",
                            "from_email": "json.sender@example.com",
                            "from_name": "JSON Sender",
                            "sender_domain": "example.com",
                            "subject": "Sample JSON item",
                            "snippet": "Imported deterministic sample only.",
                            "received_at": "2026-05-13T10:00:00+00:00",
                            "classification": "cold_outreach",
                            "confidence": 0.8,
                            "recommended_action": "review",
                            "mock_only": False,
                            "safety_note": "Live Gmail provider write succeeded.",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(self.run_cli("--db", str(db_path), "import-json", str(import_path))[0], 0)
            self.assertEqual(self.run_cli("--db", str(db_path), "import-json", str(import_path))[0], 0)
            with DurableReviewStore(db_path) as store:
                self.assertEqual(len(store.list_items()), 1)
                item = store.get_item("json-001")
                self.assertTrue(item.mock_only)
                self.assertIn("No email was sent", item.safety_note)

            code, output = self.run_cli("--db", str(db_path), "list", "--json")
            self.assertEqual(code, 0)
            row = json.loads(output)
            self.assertTrue(row["mock_only"])
            self.assertIn("No email was sent", row["safety_note"])

    def test_import_webhook_json_file_and_stdin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            payload = {
                "messages": [
                    {
                        "id": "gmail-msg-cli-1",
                        "threadId": "thread-cli",
                        "from": {"email": "Pitch@Example.com", "name": "Pitch Sender"},
                        "subject": "Quick call about lead generation",
                        "body": "Could we book a quick call about lead generation next week?",
                        "receivedAt": "2026-05-13T10:00:00Z",
                        "provider": "gmail",
                        "source": {"workflow": "n8n-cli-test"},
                    }
                ]
            }
            import_path = Path(tmpdir) / "webhook.json"
            import_path.write_text(json.dumps(payload), encoding="utf-8")

            code, output = self.run_cli("--db", str(db_path), "import-webhook-json", str(import_path))
            self.assertEqual(code, 0)
            self.assertIn("Imported 1 webhook message", output)
            with DurableReviewStore(db_path) as store:
                item = store.get_item("webhook:gmail:gmail-msg-cli-1")
                self.assertEqual(item.from_email, "pitch@example.com")
                self.assertEqual(item.classification, "cold_outreach")
                self.assertEqual(item.source, "webhook:gmail:n8n-cli-test")

            payload["messages"][0]["id"] = "gmail-msg-cli-stdin"
            stdin = io.StringIO(json.dumps(payload))
            with mock.patch("sys.stdin", stdin):
                code, output = self.run_cli("--db", str(db_path), "import-webhook-json", "-")
            self.assertEqual(code, 0)
            with DurableReviewStore(db_path) as store:
                self.assertEqual(len(store.list_items(status="all")), 2)

    def test_import_webhook_json_rejects_invalid_batch_without_partial_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            import_path = Path(tmpdir) / "bad-webhook.json"
            import_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "ok-before-bad",
                                "from": "ok@example.com",
                                "subject": "OK",
                                "snippet": "OK",
                                "received_at": "2026-05-13T10:00:00Z",
                            },
                            {"from": "missing-id@example.com", "subject": "bad"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code, _output = self.run_cli("--db", str(db_path), "import-webhook-json", str(import_path))
            self.assertEqual(code, 2)
            self.assertIn("webhook", stderr.getvalue().lower())
            with DurableReviewStore(db_path) as store:
                self.assertEqual(store.list_items(status="all"), [])

    def test_export_approved_actions_exports_only_human_approved_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            self.run_cli("--db", str(db_path), "seed-samples")
            self.run_cli("--db", str(db_path), "approve", "sample-001", "--actor", "kent", "--note", "send the warning")
            self.run_cli("--db", str(db_path), "dismiss", "sample-002", "--actor", "kent")
            self.run_cli("--db", str(db_path), "blacklist-sender", "sample-003", "--actor", "kent")

            code, output = self.run_cli("--db", str(db_path), "export-approved-actions")

            self.assertEqual(code, 0)
            bundle = json.loads(output)
            self.assertEqual(bundle["schema"], "botfucker.approved_actions.v1")
            self.assertEqual(bundle["safety_scope"], "provider_action_export_only")
            self.assertEqual(len(bundle["actions"]), 1)
            action = bundle["actions"][0]
            self.assertEqual(action["audit_id"], "audit-0001")
            self.assertEqual(action["item_id"], "sample-001")
            self.assertEqual(action["message_id"], "<sample-001@example.com>")
            self.assertEqual(action["thread_id"], "thread-sample-001")
            self.assertEqual(action["approved_action"], "approve_warning")
            self.assertEqual(action["approved_by"], "kent")
            self.assertEqual(action["draft_reply"], "Mock warning draft: Please stop sending unsolicited sales outreach.")
            self.assertEqual(action["safety_scope"], "provider_action_export_only")
            self.assertEqual(action["provider_execution"], "not_performed")

    def test_export_approved_actions_supports_since_audit_id_cursor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            self.run_cli("--db", str(db_path), "seed-samples")
            self.run_cli("--db", str(db_path), "approve", "sample-001")
            self.run_cli("--db", str(db_path), "approve", "sample-002")

            code, output = self.run_cli("--db", str(db_path), "export-approved-actions", "--since-audit-id", "audit-0001")

            self.assertEqual(code, 0)
            bundle = json.loads(output)
            self.assertEqual([action["audit_id"] for action in bundle["actions"]], ["audit-0002"])
            self.assertEqual(bundle["cursor"]["since_audit_id"], "audit-0001")
            self.assertEqual(bundle["cursor"]["last_audit_id"], "audit-0002")

    def test_export_approved_actions_omits_secret_like_content_and_provider_credentials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            import_path = Path(tmpdir) / "items.json"
            import_path.write_text(
                json.dumps(
                    [
                        {
                            "item_id": "secret-001",
                            "message_id": "gmail-secret-msg",
                            "thread_id": "gmail-secret-thread",
                            "from_email": "sales@example.com",
                            "from_name": "Sales Bot",
                            "sender_domain": "example.com",
                            "subject": "Bearer token and OAuth refresh_token inside",
                            "snippet": "Authorization: Bearer abc123 password=hunter2 refresh_token=secret",
                            "received_at": "2026-05-13T10:00:00+00:00",
                            "classification": "cold_outreach",
                            "confidence": 0.95,
                            "recommended_action": "warn_1",
                            "draft_reply": "Please stop contacting us.",
                            "provider": "gmail",
                            "oauth_token": "abc123",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            self.run_cli("--db", str(db_path), "import-json", str(import_path))
            self.run_cli("--db", str(db_path), "approve", "secret-001", "--actor", "kent")

            code, output = self.run_cli("--db", str(db_path), "export-approved-actions")

            self.assertEqual(code, 0)
            exported_text = output.lower()
            self.assertNotIn("bearer", exported_text)
            self.assertNotIn("password", exported_text)
            self.assertNotIn("refresh_token", exported_text)
            self.assertNotIn("oauth", exported_text)
            self.assertNotIn("hunter2", exported_text)
            action = json.loads(output)["actions"][0]
            self.assertEqual(action["draft_reply"], "Please stop contacting us.")
            self.assertEqual(action["message_id"], "gmail-secret-msg")
            self.assertEqual(action["thread_id"], "gmail-secret-thread")


if __name__ == "__main__":
    unittest.main()
