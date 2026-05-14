import os
import unittest
from unittest.mock import patch

from botfucker.models import ClassificationResult
from botfucker.yolo_policy import YoloPolicy, evaluate_yolo_decision
from botfucker.cli import build_yolo_policy_from_env, process_inbox


class YoloGuardrailTests(unittest.TestCase):
    def test_default_policy_denies_every_live_action(self):
        policy = YoloPolicy()
        result = evaluate_yolo_decision(
            policy,
            classification=ClassificationResult("cold_outreach", 0.99, "warn_1", ["sales ask"]),
            provider_action="send_warning",
            daily_action_count=0,
        )

        self.assertFalse(result.allowed)
        self.assertIn("YOLO mode is disabled", result.reasons)

    def test_policy_requires_explicit_confirmation_phrase(self):
        with patch.dict(
            os.environ,
            {
                "BF_YOLO_ENABLED": "true",
                "BF_YOLO_CONFIRMATION": "sure whatever",
                "BF_YOLO_ALLOWED_ACTIONS": "send_warning,move_to_sales",
                "BF_YOLO_ALLOWED_CLASSIFICATIONS": "cold_outreach,ai_generated_pitch",
            },
            clear=True,
        ):
            policy = build_yolo_policy_from_env()

        result = evaluate_yolo_decision(
            policy,
            classification=ClassificationResult("cold_outreach", 0.95, "warn_1", ["sales ask"]),
            provider_action="send_warning",
            daily_action_count=0,
        )

        self.assertFalse(result.allowed)
        self.assertIn("missing exact YOLO confirmation phrase", result.reasons)

    def test_policy_allows_only_when_all_safety_gates_pass(self):
        policy = YoloPolicy(
            enabled=True,
            confirmation_phrase="I ACCEPT BOTFUCKER YOLO RISK",
            allowed_actions={"send_warning", "move_to_sales"},
            allowed_classifications={"cold_outreach"},
            min_confidence=0.8,
            daily_action_limit=5,
        )

        result = evaluate_yolo_decision(
            policy,
            classification=ClassificationResult("cold_outreach", 0.91, "warn_1", ["sales ask"]),
            provider_action="send_warning",
            daily_action_count=3,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.reasons, ["all YOLO guardrails passed"])

    def test_policy_blocks_action_classification_confidence_and_daily_limit_failures(self):
        policy = YoloPolicy(
            enabled=True,
            confirmation_phrase="I ACCEPT BOTFUCKER YOLO RISK",
            allowed_actions={"send_warning"},
            allowed_classifications={"cold_outreach"},
            min_confidence=0.9,
            daily_action_limit=1,
        )

        result = evaluate_yolo_decision(
            policy,
            classification=ClassificationResult("unknown_review_needed", 0.4, "review", ["uncertain"]),
            provider_action="delete_message",
            daily_action_count=1,
        )

        self.assertFalse(result.allowed)
        self.assertIn("provider action delete_message is not allowlisted", result.reasons)
        self.assertIn("classification unknown_review_needed is not allowlisted", result.reasons)
        self.assertIn("confidence 0.400 is below minimum 0.900", result.reasons)
        self.assertIn("daily YOLO action limit reached", result.reasons)

    def test_emergency_stop_overrides_otherwise_valid_policy(self):
        policy = YoloPolicy(
            enabled=True,
            emergency_stop=True,
            confirmation_phrase="I ACCEPT BOTFUCKER YOLO RISK",
            allowed_actions={"send_warning"},
            allowed_classifications={"cold_outreach"},
            min_confidence=0.5,
            daily_action_limit=10,
        )

        result = evaluate_yolo_decision(
            policy,
            classification=ClassificationResult("cold_outreach", 0.99, "warn_1", ["sales ask"]),
            provider_action="send_warning",
            daily_action_count=0,
        )

        self.assertFalse(result.allowed)
        self.assertIn("YOLO emergency stop is active", result.reasons)

    def test_live_auto_approve_requires_yolo_policy_before_provider_actions(self):
        config = object()
        with self.assertRaisesRegex(RuntimeError, "YOLO guardrails are required"):
            process_inbox(config, live=True, auto_approve=True)


if __name__ == "__main__":
    unittest.main()
