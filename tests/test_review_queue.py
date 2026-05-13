import unittest

from botfucker.review_queue import MockReviewQueue, ReviewQueueError
from botfucker.samples import build_sample_review_items


class ReviewQueueTests(unittest.TestCase):
    def test_mock_actions_record_local_audit_event_only(self):
        queue = MockReviewQueue(build_sample_review_items())
        item = queue.items[0]

        event = queue.apply_action(item.item_id, "approve_warning", actor="tester", note="looks botty")

        self.assertEqual(event.item_id, item.item_id)
        self.assertEqual(event.action, "approve_warning")
        self.assertTrue(event.mock_only)
        self.assertIn("No email was sent", event.safety_note)
        self.assertEqual(queue.get_item(item.item_id).status, "actioned")
        self.assertEqual(len(queue.audit_events), 1)
        self.assertEqual(queue.audit_events[0], event)

    def test_all_supported_fake_actions_are_side_effect_free(self):
        queue = MockReviewQueue(build_sample_review_items())
        supported = {"approve_warning", "dismiss", "whitelist_sender", "blacklist_sender"}

        self.assertEqual(set(queue.supported_actions), supported)
        for index, action in enumerate(sorted(supported)):
            event = queue.apply_action(queue.items[index].item_id, action, actor="tester")
            self.assertTrue(event.mock_only)
            self.assertEqual(event.effect_scope, "local_in_memory_sample_state_only")

    def test_unknown_action_is_rejected_without_audit_event(self):
        queue = MockReviewQueue(build_sample_review_items())

        with self.assertRaises(ReviewQueueError):
            queue.apply_action(queue.items[0].item_id, "delete_real_email")

        self.assertEqual(queue.audit_events, [])

    def test_sender_history_is_derived_from_sample_items_and_local_actions(self):
        queue = MockReviewQueue(build_sample_review_items())
        queue.apply_action(queue.items[0].item_id, "whitelist_sender", actor="tester")

        history = queue.sender_history()
        sender = queue.items[0].from_email
        self.assertIn(sender, history)
        self.assertEqual(history[sender]["last_mock_action"], "whitelist_sender")
        self.assertGreaterEqual(history[sender]["message_count"], 1)


if __name__ == "__main__":
    unittest.main()
