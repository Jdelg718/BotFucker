import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs" / "provider-auth-plan.md"


class ProviderAuthPlanDocsTests(unittest.TestCase):
    def test_plan_exists_and_keeps_provider_boundary_explicit(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("Phase 7 Provider Auth Plan", plan)
        self.assertIn("n8n-first", plan)
        self.assertIn("Direct OAuth", plan)
        self.assertIn("BotFucker core stays provider-action-free", plan)
        self.assertIn("provider credentials stay server-side", plan)
        self.assertIn("Next engineering step", plan)
        self.assertIn("Approved Action Export", plan)

    def test_plan_defines_secret_storage_and_browser_boundary(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        for phrase in (
            "No secrets in the browser",
            "No secrets in the repo",
            "No OAuth tokens in local UI JSON",
            "encrypted secret store",
            "environment variables are acceptable for local development only",
        ):
            self.assertIn(phrase, plan)

    def test_plan_defines_approved_action_export_before_provider_side_effects(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn("approved action export", plan)
        self.assertIn("human-reviewed SQLite audit event", plan)
        self.assertIn("n8n action bridge", plan)
        for action in ("send reply", "archive", "move", "label", "blacklist"):
            self.assertIn(action, plan)
        self.assertIn("MUST NOT perform provider actions from the local review UI", plan)

    def test_plan_forbids_implementation_creep_in_phase_7(self):
        plan = PLAN_PATH.read_text(encoding="utf-8")

        for phrase in (
            "Do not implement Gmail OAuth in this phase",
            "Do not implement Microsoft OAuth in this phase",
            "Do not add IMAP passwords to BotFucker core",
            "Do not enable YOLO mode",
            "Do not add send/move/delete provider calls",
        ):
            self.assertIn(phrase, plan)


if __name__ == "__main__":
    unittest.main()
