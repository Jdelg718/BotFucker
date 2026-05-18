import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_GUIDE = REPO_ROOT / "docs" / "n8n-import-validation.md"
VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "validate_n8n_workflow_exports.py"
SAMPLE_ACTIONS = REPO_ROOT / "samples" / "approved-actions.sample.json"


class N8nImportValidationDocsTests(unittest.TestCase):
    def test_validation_guide_documents_real_n8n_dry_run_and_cleanup(self):
        guide = VALIDATION_GUIDE.read_text(encoding="utf-8")

        self.assertIn("n8n 2.18.5", guide)
        self.assertIn("n8n-vps", guide)
        self.assertIn("inactive", guide.lower())
        self.assertIn("dry-run", guide.lower())
        self.assertIn("sample-only", guide.lower())
        self.assertIn("/home/node/.n8n-files", guide)
        self.assertIn("approved-actions.sample.json", guide)
        self.assertIn("delete validation workflows", guide.lower())
        self.assertIn("no Gmail", guide)
        self.assertIn("no Microsoft", guide)
        self.assertIn("no IMAP", guide)
        self.assertIn("no SMTP", guide)
        self.assertIn("Cleanup completed", guide)
        self.assertIn("getBinaryDataBuffer", guide)
        self.assertIn("non-null `id`", guide)
        self.assertIn("would_execute: approve_warning", guide)
        self.assertIn("provider_execution: not_performed", guide)
        self.assertIn("no provider mutation credentials", guide.lower())

    def test_validator_script_checks_both_workflow_exports_and_forbidden_mutations(self):
        script = VALIDATOR_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("n8n-workflow.json", script)
        self.assertIn("n8n-approved-action-bridge.json", script)
        self.assertIn("active", script)
        self.assertIn("manualTrigger", script)
        self.assertIn("forbidden", script.lower())
        for phrase in ("gmail", "microsoft", "imap", "smtp", "emailSend", "access_token", "password"):
            self.assertIn(phrase, script)

    def test_sample_approved_actions_bundle_is_safe_and_matches_schema(self):
        bundle = json.loads(SAMPLE_ACTIONS.read_text(encoding="utf-8"))
        serialized = json.dumps(bundle, sort_keys=True).lower()

        self.assertEqual(bundle["schema"], "botfucker.approved_actions.v1")
        self.assertEqual(bundle["safety_scope"], "provider_action_export_only")
        self.assertEqual(len(bundle["actions"]), 1)
        action = bundle["actions"][0]
        self.assertEqual(action["audit_id"], "audit-sample-0001")
        self.assertEqual(action["approved_action"], "approve_warning")
        self.assertEqual(action["provider_execution"], "not_performed")
        self.assertIn("example.invalid", serialized)
        for forbidden in ("authorization", "access_token", "refresh_token", "api_key", "password", "credential"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
