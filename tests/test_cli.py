import tempfile
import unittest
from pathlib import Path

from botfucker.cli import Config, process_inbox


class CliSafetyTests(unittest.TestCase):
    def test_live_requires_auto_approve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                imap_host="imap.example.com",
                imap_port=993,
                smtp_host="smtp.example.com",
                smtp_port=465,
                email_address="user@example.com",
                email_password="password",
                inbox_folder="INBOX",
                sales_folder="Junk/Sales",
                blacklist_file=Path(tmpdir) / "blacklist.txt",
                history_db=Path(tmpdir) / "history.sqlite3",
                whitelist_domains=set(),
                whitelist_contacts=set(),
            )

            with self.assertRaisesRegex(RuntimeError, "--live requires --auto-approve"):
                process_inbox(config, live=True)


if __name__ == "__main__":
    unittest.main()
