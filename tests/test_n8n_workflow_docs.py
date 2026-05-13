import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "docs" / "n8n-workflow.json"
GUIDE_PATH = REPO_ROOT / "docs" / "n8n-workflow.md"


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


if __name__ == "__main__":
    unittest.main()
