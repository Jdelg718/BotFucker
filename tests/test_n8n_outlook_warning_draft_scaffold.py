import json
import unittest
from pathlib import Path


WORKFLOW_PATH = Path("docs/n8n-outlook-warning-draft-scaffold.json")
GUIDE_PATH = Path("docs/n8n-outlook-warning-draft-scaffold.md")
VALIDATOR_PATH = Path("scripts/validate_n8n_workflow_exports.py")


class OutlookWarningDraftWorkflowScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.serialized = json.dumps(self.workflow, sort_keys=True).lower()
        self.nodes = {node["name"]: node for node in self.workflow["nodes"]}

    def test_workflow_is_inactive_and_manual_trigger_only(self):
        self.assertEqual(self.workflow["id"], "botfucker-outlook-warning-draft-scaffold-v1")
        self.assertEqual(self.workflow["name"], "BotFucker Outlook Warning Draft Scaffold")
        self.assertFalse(self.workflow["active"])

        trigger_nodes = [
            node for node in self.workflow["nodes"] if "trigger" in node.get("type", "").lower()
        ]
        self.assertEqual(len(trigger_nodes), 1)
        self.assertEqual(trigger_nodes[0]["name"], "Manual Trigger")
        self.assertEqual(trigger_nodes[0]["type"], "n8n-nodes-base.manualTrigger")

    def test_workflow_contains_no_secret_or_credential_material(self):
        for forbidden in (
            "authorization",
            "client_secret",
            "access_token",
            "refresh_token",
            "api_key",
            "password",
            "credential",
            "cookie",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.serialized)

    def test_workflow_forbids_send_and_mailbox_mutation_strings(self):
        for forbidden in (
            "/send",
            "sendmail",
            "reply send",
            "delete",
            "move",
            "archive",
            "mark read",
            "mark unread",
            "mark read/unread",
            "rules",
            "contacts/settings mutation",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.serialized)

    def test_connected_path_is_validation_and_summary_only(self):
        connections = self.workflow["connections"]
        self.assertEqual(
            connections["Manual Trigger"]["main"][0][0]["node"],
            "Sample Approved Action Bundle",
        )
        self.assertEqual(
            connections["Sample Approved Action Bundle"]["main"][0][0]["node"],
            "Validate Emergency Stop And Dedupe",
        )
        self.assertEqual(
            connections["Validate Emergency Stop And Dedupe"]["main"][0][0]["node"],
            "Draft Only Safety Summary",
        )
        self.assertNotIn("Disabled Graph createReply Draft Placeholder", connections)
        for outputs in connections.values():
            for group in outputs.get("main", []):
                for edge in group:
                    self.assertNotEqual(edge["node"], "Disabled Graph createReply Draft Placeholder")

    def test_draft_placeholder_is_disabled_unconnected_create_reply_only(self):
        placeholder = self.nodes["Disabled Graph createReply Draft Placeholder"]
        self.assertTrue(placeholder["disabled"])
        self.assertEqual(placeholder["type"], "n8n-nodes-base.httpRequest")
        self.assertEqual(placeholder["parameters"]["method"], "POST")
        self.assertIn("createReply", placeholder["parameters"]["url"])
        self.assertNotIn("/send", placeholder["parameters"]["url"].lower())

    def test_safety_code_mentions_emergency_stop_dedupe_and_draft_only(self):
        validation_code = self.nodes["Validate Emergency Stop And Dedupe"]["parameters"]["jsCode"]
        summary_code = self.nodes["Draft Only Safety Summary"]["parameters"]["jsCode"]
        self.assertIn("BOTFUCKER_EMERGENCY_STOP", validation_code)
        self.assertIn("blocked_by_emergency_stop", validation_code)
        self.assertIn("BOTFUCKER_PROCESSED_AUDIT_IDS", validation_code)
        self.assertIn("audit_id", validation_code)
        self.assertIn("approve_warning", validation_code)
        self.assertIn("provider_execution", validation_code)
        self.assertIn("not_performed", validation_code)
        self.assertIn("blocked_by_emergency_stop", summary_code)
        self.assertIn("graph_operation: 'none'", summary_code)
        self.assertIn("draft_only: false", summary_code)
        self.assertIn("draft_only: true", summary_code)
        self.assertIn("createReply", summary_code)

    def test_emergency_stop_status_is_preserved_by_terminal_summary(self):
        summary_code = self.nodes["Draft Only Safety Summary"]["parameters"]["jsCode"]
        blocked_index = summary_code.index("blocked_by_emergency_stop")
        ready_index = summary_code.index("ready_for_manual_sandbox_rehearsal")

        self.assertLess(blocked_index, ready_index)
        self.assertIn("Emergency stop is on", summary_code)
        self.assertIn("before any draft readiness signal", summary_code)

    def test_guide_documents_operator_safety_and_rollback(self):
        guide = GUIDE_PATH.read_text(encoding="utf-8")
        for phrase in (
            "active: false",
            "manual-triggered only",
            "Microsoft Outlook",
            "POST /me/messages/{id}/createReply",
            "Mail.ReadWrite",
            "BOTFUCKER_EMERGENCY_STOP",
            "audit_id",
            "dedupe",
            "Rollback and manual deletion",
            "manually delete the created draft",
            "sandbox import/rehearsal or operator validation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_validator_includes_new_workflow_export(self):
        script = VALIDATOR_PATH.read_text(encoding="utf-8")
        self.assertIn("n8n-outlook-warning-draft-scaffold.json", script)
        self.assertIn("createReply", script)
        self.assertIn("BOTFUCKER_EMERGENCY_STOP", script)
        self.assertIn("Graph createReply placeholder must remain unconnected", script)


if __name__ == "__main__":
    unittest.main()
