import unittest

from botfucker.classifier import classify_message
from botfucker.models import EmailMessage


class ClassifierTests(unittest.TestCase):
    def test_detects_cold_outreach_with_structured_output(self):
        message = EmailMessage(
            from_email="sales@example.com",
            sender_domain="example.com",
            subject="Quick call?",
            body_text="Hi, following up to book a 15-minute demo for our lead generation solution.",
        )

        result = classify_message(message)

        self.assertIn(result.classification, {"cold_outreach", "crm_followup"})
        self.assertEqual(result.recommended_action, "warn_1")
        self.assertGreaterEqual(result.confidence, 0.7)
        self.assertTrue(result.reasons)

    def test_detects_ai_generated_pitch(self):
        message = EmailMessage(
            from_email="bot@vendor.test",
            sender_domain="vendor.test",
            subject="Unlock growth",
            body_text=(
                "Hello,\nI hope this email finds you well. Our tailored solutions help "
                "teams streamline your operations and drive measurable results.\nBest regards"
            ),
        )

        result = classify_message(message)

        self.assertEqual(result.classification, "ai_generated_pitch")
        self.assertEqual(result.recommended_action, "warn_1")
        self.assertGreaterEqual(len(result.reasons), 2)

    def test_whitelist_forces_safe(self):
        message = EmailMessage(from_email="friend@example.com", sender_domain="example.com", subject="Quick call", body_text="book a demo")

        result = classify_message(message, whitelisted=True)

        self.assertEqual(result.classification, "safe")
        self.assertEqual(result.recommended_action, "none")

    def test_strike_level_changes_recommended_action(self):
        message = EmailMessage(
            from_email="sales@example.com",
            sender_domain="example.com",
            subject="Following up",
            body_text="Just checking in to book a call.",
        )

        result = classify_message(message, strike_level=2)

        self.assertEqual(result.recommended_action, "warn_3")

    def test_strike_four_becomes_block_candidate(self):
        message = EmailMessage(
            from_email="sales@example.com",
            sender_domain="example.com",
            subject="Following up",
            body_text="Just checking in to book a call.",
        )

        result = classify_message(message, strike_level=3)

        self.assertEqual(result.recommended_action, "block_candidate")

    def test_newsletter_goes_to_review_not_warning(self):
        message = EmailMessage(
            from_email="updates@example.com",
            sender_domain="example.com",
            subject="Weekly update",
            body_text="This week's product notes. Unsubscribe or manage preferences.",
        )

        result = classify_message(message)

        self.assertEqual(result.classification, "newsletter")
        self.assertEqual(result.recommended_action, "review")

    def test_unknown_message_needs_review(self):
        message = EmailMessage(
            from_email="person@example.com",
            sender_domain="example.com",
            subject="Lunch",
            body_text="Are you free for lunch next week?",
        )

        result = classify_message(message)

        self.assertEqual(result.classification, "unknown_review_needed")
        self.assertEqual(result.recommended_action, "review")

    def test_single_generic_solution_word_does_not_classify_as_outreach(self):
        message = EmailMessage(
            from_email="person@example.com",
            sender_domain="example.com",
            subject="Solution notes",
            body_text="I found a solution to the bug we discussed.",
        )

        result = classify_message(message)

        self.assertEqual(result.classification, "unknown_review_needed")

    def test_customer_or_partner_placeholder_path(self):
        message = EmailMessage(
            from_email="partner@example.com",
            sender_domain="example.com",
            subject="Current partner project",
            body_text="Following up on our contract status for the current partner project.",
        )

        result = classify_message(message)

        self.assertEqual(result.classification, "customer_or_partner")
        self.assertEqual(result.recommended_action, "review")

    def test_reasons_do_not_expose_regex_syntax(self):
        message = EmailMessage(
            from_email="sales@example.com",
            sender_domain="example.com",
            subject="Quick call?",
            body_text="Can we book a demo for lead generation?",
        )

        result = classify_message(message)

        self.assertFalse(any("\\b" in reason or "(?:" in reason for reason in result.reasons))


if __name__ == "__main__":
    unittest.main()
