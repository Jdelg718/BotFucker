import tempfile
import unittest
from pathlib import Path

from botfucker.review_queue import MOCK_SAFETY_NOTE
from botfucker.review_store import DurableReviewStore, ReviewStoreError
from botfucker.samples import build_sample_review_items


class DurableReviewStoreTests(unittest.TestCase):
    def test_upsert_is_durable_and_idempotent_preserving_status_and_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.sqlite3"
            item = build_sample_review_items()[0]

            with DurableReviewStore(db_path) as store:
                inserted = store.upsert_items([item])
                repeated = store.upsert_items([item])
                event = store.apply_action(item.item_id, "approve_warning", actor="tester", note="approved locally")

            self.assertEqual(inserted, 1)
            self.assertEqual(repeated, 0)
            self.assertIn("No email was sent", event.safety_note)

            with DurableReviewStore(db_path) as reopened:
                self.assertEqual(len(reopened.list_items()), 1)
                self.assertEqual(reopened.get_item(item.item_id).status, "actioned")
                self.assertEqual(reopened.list_audit_events()[0].action, "approve_warning")

                # Re-importing the same item may refresh metadata, but must not
                # duplicate the row or reset human approval state/audit history.
                self.assertEqual(reopened.upsert_items([item]), 0)
                self.assertEqual(reopened.get_item(item.item_id).status, "actioned")
                self.assertEqual(len(reopened.list_audit_events()), 1)

    def test_list_pending_and_supported_actions_are_local_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableReviewStore(Path(tmpdir) / "review.sqlite3") as store:
                items = build_sample_review_items()[:2]
                store.upsert_items(items)
                store.apply_action(items[0].item_id, "dismiss", actor="tester")

                pending = store.list_items(status="pending")
                self.assertEqual([item.item_id for item in pending], [items[1].item_id])

                for action in ("whitelist_sender", "blacklist_sender"):
                    event = store.apply_action(items[1].item_id, action, actor="tester")
                    self.assertTrue(event.mock_only)
                    self.assertEqual(event.effect_scope, "local_sqlite_review_state_only")
                    self.assertIn("No email was sent", event.safety_note)

    def test_unknown_item_or_action_does_not_create_audit_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableReviewStore(Path(tmpdir) / "review.sqlite3") as store:
                store.upsert_items(build_sample_review_items()[:1])

                with self.assertRaises(ReviewStoreError):
                    store.apply_action("missing", "dismiss", actor="tester")
                with self.assertRaises(ReviewStoreError):
                    store.apply_action("sample-001", "send_real_email", actor="tester")

                self.assertEqual(store.list_audit_events(), [])

    def test_seeded_items_carry_mock_safety_note_not_secrets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableReviewStore(Path(tmpdir) / "review.sqlite3") as store:
                store.upsert_items(build_sample_review_items())
                item = store.list_items()[0]
                self.assertTrue(item.mock_only)
                self.assertEqual(item.safety_note, MOCK_SAFETY_NOTE)
                self.assertNotIn("password", str(item.to_dict()).lower())
                self.assertNotIn("token", str(item.to_dict()).lower())


if __name__ == "__main__":
    unittest.main()
