import tempfile
import unittest
from pathlib import Path

from botfucker.classifier import classify_message
from botfucker.history import SenderHistory
from botfucker.models import EmailMessage


class SenderHistoryTests(unittest.TestCase):
    def test_records_classification_counts_and_message_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = SenderHistory(Path(tmpdir) / "history.sqlite3")
            message = EmailMessage(
                from_email="sales@example.com",
                sender_domain="example.com",
                subject="Quick call",
                body_text="Can we book a demo?",
            )
            result = classify_message(message)

            first = history.record_classification(message, result)
            second = history.record_classification(message, result)

            self.assertEqual(first.message_count, 1)
            self.assertEqual(second.message_count, 2)
            self.assertEqual(second.classification_counts[result.classification], 2)
            history.close()

    def test_issue_warning_advances_strikes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = SenderHistory(Path(tmpdir) / "history.sqlite3")
            message = EmailMessage(
                from_email="sales@example.com",
                sender_domain="example.com",
                subject="Following up",
                body_text="Just checking in to book a call.",
            )
            history.record_classification(message, classify_message(message))

            first = history.issue_warning("sales@example.com")
            second = history.issue_warning("sales@example.com")

            self.assertEqual(first.strike_level, 1)
            self.assertEqual(second.strike_level, 2)
            self.assertEqual(second.warnings_sent, 2)
            self.assertEqual(history.get_domain_strike_level("example.com"), 2)
            history.close()

    def test_blacklist_and_whitelist_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = SenderHistory(Path(tmpdir) / "history.sqlite3")
            message = EmailMessage(from_email="person@example.com", sender_domain="example.com")
            history.record_classification(message, classify_message(message))

            history.set_whitelist("person@example.com", True)
            self.assertTrue(history.is_whitelisted("person@example.com", "example.com"))

            history.set_blacklist("person@example.com", True)
            self.assertTrue(history.is_blacklisted("person@example.com", "example.com"))
            history.close()


if __name__ == "__main__":
    unittest.main()
