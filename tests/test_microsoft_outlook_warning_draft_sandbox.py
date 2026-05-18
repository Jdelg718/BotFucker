import json
import unittest
from pathlib import Path

DOC_PATH = Path("docs/microsoft-outlook-warning-draft-sandbox.md")
WORKFLOW_PATHS = [
    Path("docs/n8n-workflow.json"),
    Path("docs/n8n-approved-action-bridge.json"),
]


class MicrosoftOutlookWarningDraftSandboxContractTests(unittest.TestCase):
    def test_contract_exists_and_targets_outlook_warning_draft_only(self):
        text = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("Microsoft Outlook", text)
        self.assertIn("warning draft", text.lower())
        self.assertIn("approve_warning", text)
        self.assertIn("POST /me/messages/{id}/createReply", text)
        self.assertIn("Mail.ReadWrite", text)
        self.assertIn("Explicit non-goal: sending replies", text)

    def test_contract_forbids_send_and_other_provider_mutations(self):
        text = DOC_PATH.read_text(encoding="utf-8")

        required_phrases = [
            "The bridge must never call `/send` in this phase.",
            "Do not:",
            "send the draft",
            "call Microsoft Graph `/send`",
            "delete email",
            "move email",
            "archive email",
            "mark read/unread",
            "No “just testing” send.",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_keeps_credentials_out_of_repo(self):
        text = DOC_PATH.read_text(encoding="utf-8")

        for forbidden_secret in [
            "OAuth client secret",
            "refresh token",
            "access token",
            "password",
            "cookie",
            "exported n8n credentials",
        ]:
            with self.subTest(forbidden_secret=forbidden_secret):
                self.assertIn(forbidden_secret, text)
        self.assertIn("Credentials are not BotFucker state.", text)
        self.assertIn("Credentials remain in n8n/operator infrastructure only.", text)

    def test_existing_n8n_workflows_still_do_not_contain_outlook_send_or_credentials(self):
        forbidden_terms = [
            "/send",
            "sendMail",
            "microsoftGraph",
            "client_secret",
            "refresh_token",
            "access_token",
            "password",
        ]
        for path in WORKFLOW_PATHS:
            raw = path.read_text(encoding="utf-8")
            json.loads(raw)
            lowered = raw.lower()
            for term in forbidden_terms:
                with self.subTest(path=str(path), term=term):
                    self.assertNotIn(term.lower(), lowered)

    def test_roadmap_records_kents_selected_phase_16_target(self):
        text = Path("ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("Phase 16 — Microsoft Outlook Warning-Draft Sandbox Contract", text)
        self.assertIn("Provider: Microsoft Outlook", text)
        self.assertIn("First action: create/save a warning draft only", text)
        self.assertIn("no send-reply mutation yet", text)


if __name__ == "__main__":
    unittest.main()
