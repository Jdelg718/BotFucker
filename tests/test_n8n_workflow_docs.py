import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "docs" / "n8n-workflow.json"
GUIDE_PATH = REPO_ROOT / "docs" / "n8n-workflow.md"
ACTION_BRIDGE_WORKFLOW_PATH = REPO_ROOT / "docs" / "n8n-approved-action-bridge.json"
ACTION_BRIDGE_GUIDE_PATH = REPO_ROOT / "docs" / "n8n-approved-action-bridge.md"


class N8nWorkflowDocsTests(unittest.TestCase):
    def test_workflow_export_is_valid_json_without_credentials(self):
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        serialized = json.dumps(workflow, sort_keys=True).lower()

        self.assertEqual(workflow["name"], "BotFucker Local Review Import")
        self.assertIn("nodes", workflow)
        self.assertIn("connections", workflow)
        self.assertNotIn("authorization", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("credential", serialized)
        self.assertNotIn("password", serialized)

    def test_workflow_contains_safe_provider_boundary_nodes(self):
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        node_names = {node["name"] for node in workflow["nodes"]}

        self.assertIn("Manual Trigger", node_names)
        self.assertIn("Fetch Provider Mail Placeholder", node_names)
        self.assertIn("Normalize BotFucker Payload", node_names)
        self.assertIn("Convert Normalized JSON To File", node_names)
        self.assertIn("Write n8n-messages.json", node_names)
        self.assertIn("Import Into Local Review Queue", node_names)
        self.assertIn("Safety Boundary Notes", node_names)

    def test_workflow_writes_json_via_binary_file_conversion(self):
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}
        connections = workflow["connections"]

        convert_node = nodes["Convert Normalized JSON To File"]
        write_node = nodes["Write n8n-messages.json"]

        self.assertEqual(convert_node["type"], "n8n-nodes-base.convertToFile")
        self.assertEqual(convert_node["parameters"]["operation"], "toJson")
        self.assertEqual(convert_node["parameters"]["binaryPropertyName"], "data")
        self.assertEqual(write_node["parameters"]["dataPropertyName"], "data")
        self.assertEqual(
            connections["Normalize BotFucker Payload"]["main"][0][0]["node"],
            "Convert Normalized JSON To File",
        )
        self.assertEqual(
            connections["Convert Normalized JSON To File"]["main"][0][0]["node"],
            "Write n8n-messages.json",
        )

    def test_workflow_import_command_targets_local_cli_only(self):
        workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        command_nodes = [node for node in workflow["nodes"] if node.get("type") == "n8n-nodes-base.executeCommand"]
        commands = "\n".join(node.get("parameters", {}).get("command", "") for node in command_nodes)

        self.assertIn("python3 -m botfucker.review_cli", commands)
        self.assertIn("import-webhook-json", commands)
        self.assertIn("--db", commands)
        self.assertNotIn("--live", commands)
        self.assertNotIn("--auto-approve", commands)

    def test_guide_documents_mapping_and_forbidden_side_effects(self):
        guide = GUIDE_PATH.read_text(encoding="utf-8")

        self.assertIn("Provider boundary", guide)
        self.assertIn("BotFucker does not receive OAuth tokens", guide)
        self.assertIn("import-webhook-json", guide)
        self.assertIn("python3 -m botfucker.local_ui", guide)
        for phrase in ("send mail", "move mail", "delete mail", "archive mail", "provider whitelist"):
            self.assertIn(phrase, guide)

    def test_action_bridge_workflow_is_valid_dry_run_json_without_credentials(self):
        workflow = json.loads(ACTION_BRIDGE_WORKFLOW_PATH.read_text(encoding="utf-8"))
        serialized = json.dumps(workflow, sort_keys=True).lower()

        self.assertEqual(workflow["name"], "BotFucker Approved Action Bridge Dry Run")
        self.assertFalse(workflow["active"])
        self.assertIn("nodes", workflow)
        self.assertIn("connections", workflow)
        self.assertIn("botfucker.approved_actions.v1", serialized)
        self.assertIn("dry_run", serialized)
        self.assertNotIn("authorization", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("refresh_token", serialized)
        self.assertNotIn("credential", serialized)
        self.assertNotIn("password", serialized)

    def test_action_bridge_workflow_contains_schema_dedupe_and_dry_run_nodes(self):
        workflow = json.loads(ACTION_BRIDGE_WORKFLOW_PATH.read_text(encoding="utf-8"))
        node_names = {node["name"] for node in workflow["nodes"]}
        node_types = {node["type"] for node in workflow["nodes"]}

        self.assertIn("Manual Trigger", node_names)
        self.assertIn("Read approved-actions.json", node_names)
        self.assertIn("Validate And Dedupe Approved Actions", node_names)
        self.assertIn("Dry Run Provider Action Log", node_names)
        self.assertIn("Safety Boundary Notes", node_names)
        self.assertNotIn("n8n-nodes-base.gmail", node_types)
        self.assertNotIn("n8n-nodes-base.microsoftOutlook", node_types)
        self.assertNotIn("n8n-nodes-base.emailSend", node_types)
        self.assertNotIn("n8n-nodes-base.imap", node_types)

    def test_action_bridge_workflow_connections_keep_provider_actions_disabled(self):
        workflow = json.loads(ACTION_BRIDGE_WORKFLOW_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}
        connections = workflow["connections"]
        validation_code = nodes["Validate And Dedupe Approved Actions"]["parameters"]["jsCode"]
        dry_run_code = nodes["Dry Run Provider Action Log"]["parameters"]["jsCode"]

        self.assertIn("botfucker.approved_actions.v1", validation_code)
        self.assertIn("audit_id", validation_code)
        self.assertIn("processedAuditIds", validation_code)
        self.assertIn("provider_execution", validation_code)
        self.assertIn("not_performed", validation_code)
        self.assertIn("dry_run", dry_run_code)
        self.assertIn("would_execute", dry_run_code)
        self.assertEqual(connections["Manual Trigger"]["main"][0][0]["node"], "Read approved-actions.json")
        self.assertEqual(
            connections["Read approved-actions.json"]["main"][0][0]["node"],
            "Validate And Dedupe Approved Actions",
        )
        self.assertEqual(
            connections["Validate And Dedupe Approved Actions"]["main"][0][0]["node"],
            "Dry Run Provider Action Log",
        )

    def test_action_bridge_guide_documents_dry_run_and_provider_boundary(self):
        guide = ACTION_BRIDGE_GUIDE_PATH.read_text(encoding="utf-8")

        self.assertIn("approved-actions.json", guide)
        self.assertIn("botfucker.approved_actions.v1", guide)
        self.assertIn("dry-run", guide.lower())
        self.assertIn("dedupe", guide.lower())
        self.assertIn("audit_id", guide)
        self.assertIn("provider credentials stay in n8n", guide.lower())
        self.assertIn("does not send mail", guide.lower())
        self.assertIn("does not move mail", guide.lower())
        self.assertIn("does not delete mail", guide.lower())


if __name__ == "__main__":
    unittest.main()
