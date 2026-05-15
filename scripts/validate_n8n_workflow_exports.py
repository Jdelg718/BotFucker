#!/usr/bin/env python3
"""Validate BotFucker n8n workflow exports before importing them.

This is intentionally local/static. It checks the repo artifacts for the
properties that matter before an operator copies them into n8n: inactive,
manual-triggered, dry-run where required, and free of credential/provider
mutation nodes. It does not call n8n, Gmail, Microsoft, IMAP, SMTP, or any
provider API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATHS = [
    REPO_ROOT / "docs" / "n8n-workflow.json",
    REPO_ROOT / "docs" / "n8n-approved-action-bridge.json",
]

FORBIDDEN_STRINGS = [
    "authorization",
    "access_token",
    "refresh_token",
    "api_key",
    "password",
    "credential",
]

FORBIDDEN_NODE_TERMS = [
    "gmail",
    "microsoft",
    "imap",
    "smtp",
    "emailSend",
    "sendMail",
    "deleteMessage",
    "moveMessage",
    "archive",
    "label",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{path}: workflow export must be a JSON object")
    return payload


def node_names(workflow: dict[str, Any]) -> set[str]:
    return {str(node.get("name", "")) for node in workflow.get("nodes", [])}


def validate_workflow(path: Path) -> list[str]:
    workflow = load_json(path)
    serialized = json.dumps(workflow, sort_keys=True)
    serialized_lower = serialized.lower()
    errors: list[str] = []

    if workflow.get("active") is not False:
        errors.append(f"{path.name}: active must be false for import validation")
    if "nodes" not in workflow or not isinstance(workflow["nodes"], list):
        errors.append(f"{path.name}: nodes list missing")
    if "connections" not in workflow or not isinstance(workflow["connections"], dict):
        errors.append(f"{path.name}: connections object missing")
    if "Manual Trigger" not in node_names(workflow):
        errors.append(f"{path.name}: Manual Trigger node missing")
    if "manualTrigger" not in serialized:
        errors.append(f"{path.name}: manualTrigger node type missing")

    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in serialized_lower:
            errors.append(f"{path.name}: forbidden credential-like string found: {forbidden}")

    node_types = "\n".join(str(node.get("type", "")) for node in workflow.get("nodes", []))
    node_type_lower = node_types.lower()
    for term in FORBIDDEN_NODE_TERMS:
        if term.lower() in node_type_lower:
            errors.append(f"{path.name}: forbidden provider mutation node type found: {term}")

    if path.name == "n8n-approved-action-bridge.json":
        if "botfucker.approved_actions.v1" not in serialized:
            errors.append(f"{path.name}: approved-actions schema marker missing")
        if "dry_run" not in serialized:
            errors.append(f"{path.name}: dry_run marker missing")
        if "audit_id" not in serialized:
            errors.append(f"{path.name}: audit_id dedupe marker missing")

    return errors


def main() -> int:
    all_errors: list[str] = []
    for path in WORKFLOW_PATHS:
        all_errors.extend(validate_workflow(path))

    if all_errors:
        print("n8n workflow export validation failed:")
        for error in all_errors:
            print(f"- {error}")
        return 1

    print("n8n workflow export validation passed:")
    for path in WORKFLOW_PATHS:
        print(f"- {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
