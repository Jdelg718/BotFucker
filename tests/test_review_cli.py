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
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(self.run_cli("--db", str(db_path), "import-json", str(import_path))[0], 0)
            self.assertEqual(self.run_cli("--db", str(db_path), "import-json", str(import_path))[0], 0)
            with DurableReviewStore(db_path) as store:
                self.assertEqual(len(store.list_items()), 1)


if __name__ == "__main__":
    unittest.main()
