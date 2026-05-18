import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs" / "reviewed-action-bridge-promotion-plan.md"
README_PATH = REPO_ROOT / "README.md"
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
HANDOFF_PATH = REPO_ROOT / "HANDOFF.md"
ACTION_BRIDGE_GUIDE_PATH = REPO_ROOT / "docs" / "n8n-approved-action-bridge.md"


class ReviewedActionBridgePromotionPlanTests(unittest.TestCase):
    def test_plan_exists_and_is_phase_13_only(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("Phase 13 Reviewed Action Bridge Promotion Plan", plan)
        self.assertIn("promotion plan, not a provider implementation", plan)
        self.assertIn("Reviewed Action Bridge Promotion Plan", ROADMAP_PATH.read_text(encoding="utf-8"))
        self.assertIn("Reviewed Action Bridge Promotion Plan", HANDOFF_PATH.read_text(encoding="utf-8"))

    def test_plan_forbids_oauth_credentials_and_live_mutation_creep(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        for phrase in (
            "Do not implement Gmail OAuth",
            "Do not implement Microsoft OAuth",
            "Do not add IMAP passwords",
            "Do not add Gmail, Microsoft, IMAP, SMTP, send-mail, move-mail, delete-mail, archive, or label mutation nodes",
            "Do not activate the n8n workflows by default",
            "Do not execute provider mutations from the local UI",
        ):
            self.assertIn(phrase, plan)

    def test_plan_limits_first_promotion_to_one_reviewed_action_type(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("Approved action: `approve_warning`", plan)
        self.assertIn("human-approved SQLite audit event", plan)
        self.assertIn("Do not promote more than one provider action type", plan)
        self.assertIn("Whitelist, blacklist, archive, move, and label actions require their own export contracts", plan)

    def test_plan_requires_n8n_credential_ownership_and_separate_live_bridge(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("Provider credentials belong in n8n only", plan)
        self.assertIn("BotFucker core must never store or receive", plan)
        self.assertIn("Reviewed live bridge", plan)
        self.assertIn("separate from both checked-in starters", plan)
        self.assertIn("dry-run switch", plan)

    def test_plan_defines_persistent_audit_id_dedupe_before_live_mutation(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("Persistent processed-audit design", plan)
        self.assertIn('"audit_id": "audit-0001"', plan)
        self.assertIn("Use `audit_id` as the primary idempotency key", plan)
        self.assertIn("Check durable state before the provider node executes", plan)
        self.assertIn("Environment variables are not acceptable for live processed-audit state", plan)

    def test_plan_requires_rollback_emergency_stop_sandbox_security_and_ops_reviews(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        for phrase in (
            "Rollback and emergency stop",
            "one operator-visible switch that stops provider mutations immediately",
            "Provider-specific sandbox/manual test plan",
            "Security review checklist",
            "Ops review checklist",
            "Rex/security approval recorded",
            "Gus/ops approval recorded",
        ):
            self.assertIn(phrase, plan)

    def test_existing_docs_link_phase_13_plan_without_claiming_live_actions_exist(self):
        readme = README_PATH.read_text(encoding="utf-8")
        bridge_guide = ACTION_BRIDGE_GUIDE_PATH.read_text(encoding="utf-8")

        self.assertIn("reviewed-action-bridge-promotion-plan.md", readme)
        self.assertIn("reviewed-action-bridge-promotion-plan.md", bridge_guide)
        for doc in (readme, bridge_guide):
            self.assertIn("dry-run", doc.lower())
            self.assertIn("no OAuth", doc)
            self.assertIn("no provider credentials", doc)


if __name__ == "__main__":
    unittest.main()
