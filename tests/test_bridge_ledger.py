import sqlite3
import tempfile
import unittest
from pathlib import Path

from botfucker.bridge_ledger import (
    BRIDGE_LEDGER_EFFECT_SCOPE,
    BridgeLedgerError,
    DurableBridgeLedger,
    FAILED,
    PENDING,
    PROCESSED,
    ROLLED_BACK,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "bridge-ledger-scaffold.md"
README_PATH = REPO_ROOT / "README.md"
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
HANDOFF_PATH = REPO_ROOT / "HANDOFF.md"


def sample_bundle(action=None):
    action = action or sample_action()
    return {
        "schema": "botfucker.approved_actions.v1",
        "safety_scope": "provider_action_export_only",
        "provider_execution": "not_performed",
        "cursor": {"since_audit_id": None, "last_audit_id": action["audit_id"]},
        "actions": [action],
    }


def sample_action(**overrides):
    action = {
        "audit_id": "audit-0001",
        "action_id": "bf-action-audit-0001",
        "item_id": "webhook:gmail:gmail-msg-123",
        "message_id": "gmail-msg-123",
        "thread_id": "gmail-thread-7",
        "provider": "gmail",
        "approved_action": "approve_warning",
        "approved_by": "human",
        "approved_at": "2026-05-14T21:45:00Z",
        "draft_reply": "Human-reviewed warning text",
        "safety_scope": "provider_action_export_only",
        "provider_execution": "not_performed",
    }
    action.update(overrides)
    return action


class DurableBridgeLedgerTests(unittest.TestCase):
    def test_claim_action_inserts_pending_record_before_provider_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                claim = ledger.claim_action(
                    sample_bundle(action),
                    action,
                    processed_by_workflow="botfucker-reviewed-live-bridge-v1",
                    dry_run=False,
                )

                self.assertTrue(claim.acquired)
                self.assertEqual(PENDING, claim.record.status)
                self.assertFalse(claim.record.dry_run)
                self.assertEqual("audit-0001", claim.record.audit_id)
                self.assertEqual("bf-action-audit-0001", claim.record.action_id)
                self.assertEqual("gmail", claim.record.provider)
                self.assertEqual("approve_warning", claim.record.approved_action)
                self.assertEqual("gmail-msg-123", claim.record.message_id)
                self.assertEqual("gmail-thread-7", claim.record.thread_id)
                self.assertEqual(BRIDGE_LEDGER_EFFECT_SCOPE, claim.record.effect_scope)

    def test_claim_action_dedupes_by_audit_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                first = ledger.claim_action(
                    sample_bundle(action),
                    action,
                    processed_by_workflow="bridge-v1",
                )
                second = ledger.claim_action(
                    sample_bundle(action),
                    action,
                    processed_by_workflow="bridge-v1",
                )

                self.assertTrue(first.acquired)
                self.assertFalse(second.acquired)
                self.assertEqual(first.record.audit_id, second.record.audit_id)
                self.assertEqual(1, len(ledger.list_records()))

    def test_mark_processed_and_failed_update_existing_claim_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                ledger.claim_action(sample_bundle(action), action, processed_by_workflow="bridge-v1")

                processed = ledger.mark_processed("audit-0001", provider_result_id="provider-reply-123")
                self.assertEqual(PROCESSED, processed.status)
                self.assertEqual("provider-reply-123", processed.provider_result_id)
                self.assertTrue(ledger.has_processed("audit-0001"))

                failed_action = sample_action(audit_id="audit-0002", action_id="bf-action-audit-0002")
                ledger.claim_action(sample_bundle(failed_action), failed_action, processed_by_workflow="bridge-v1")
                failed = ledger.mark_failed("audit-0002", provider_result_id="provider-error-429")
                self.assertEqual(FAILED, failed.status)
                self.assertFalse(ledger.has_processed("audit-0002"))

                with self.assertRaises(BridgeLedgerError):
                    ledger.mark_processed("audit-missing")

    def test_rejects_unsafe_or_already_executed_exports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                unsafe_bundle = sample_bundle(action)
                unsafe_bundle["provider_execution"] = "performed"

                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(unsafe_bundle, action, processed_by_workflow="bridge-v1")

                unsafe_action = sample_action(provider_execution="performed")
                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(sample_bundle(unsafe_action), unsafe_action, processed_by_workflow="bridge-v1")

                missing_id_action = sample_action(audit_id="")
                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(sample_bundle(missing_id_action), missing_id_action, processed_by_workflow="bridge-v1")

                missing_thread_action = sample_action(thread_id="")
                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(sample_bundle(missing_thread_action), missing_thread_action, processed_by_workflow="bridge-v1")

                unsupported_action = sample_action(approved_action="delete_message")
                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(sample_bundle(unsupported_action), unsupported_action, processed_by_workflow="bridge-v1")

                action_outside_bundle = sample_action(audit_id="audit-outside", action_id="bf-action-audit-outside")
                with self.assertRaises(BridgeLedgerError):
                    ledger.claim_action(sample_bundle(action), action_outside_bundle, processed_by_workflow="bridge-v1")

    def test_status_transitions_fail_closed_after_terminal_states(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                processed_action = sample_action()
                ledger.claim_action(sample_bundle(processed_action), processed_action, processed_by_workflow="bridge-v1")
                ledger.mark_processed("audit-0001", provider_result_id="provider-reply-123")

                with self.assertRaises(BridgeLedgerError):
                    ledger.mark_failed("audit-0001", provider_result_id="late-error")

                rolled_back = ledger.mark_rolled_back("audit-0001", provider_result_id="manual-remediation-1")
                self.assertEqual(ROLLED_BACK, rolled_back.status)

                with self.assertRaises(BridgeLedgerError):
                    ledger.mark_processed("audit-0001", provider_result_id="retry-after-rollback")

                failed_action = sample_action(audit_id="audit-0002", action_id="bf-action-audit-0002")
                ledger.claim_action(sample_bundle(failed_action), failed_action, processed_by_workflow="bridge-v1")
                ledger.mark_failed("audit-0002", provider_result_id="provider-error-429")

                with self.assertRaises(BridgeLedgerError):
                    ledger.mark_processed("audit-0002", provider_result_id="retry-after-failure")

    def test_schema_excludes_message_content_and_secret_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "ledger.sqlite3"
            with DurableBridgeLedger(db_path):
                pass
            connection = sqlite3.connect(db_path)
            try:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(bridge_processed_audits)").fetchall()
                }
            finally:
                connection.close()

        forbidden_columns = {
            "subject",
            "snippet",
            "body",
            "raw_headers",
            "headers",
            "oauth_token",
            "refresh_token",
            "api_key",
            "password",
            "cookie",
        }
        self.assertFalse(columns & forbidden_columns)
        self.assertIn("audit_id", columns)
        self.assertIn("status", columns)
        self.assertIn("provider_result_id", columns)

    def test_docs_describe_phase_14_as_scaffold_without_provider_side_effects(self):
        doc = DOC_PATH.read_text(encoding="utf-8")
        readme = README_PATH.read_text(encoding="utf-8")
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
        handoff = HANDOFF_PATH.read_text(encoding="utf-8")

        for text in (doc, readme, roadmap, handoff):
            self.assertIn("Phase 14", text)
            self.assertIn("durable bridge ledger", text.lower())

        for phrase in (
            "no OAuth",
            "no provider credentials",
            "no live provider mutation nodes",
            "before provider mutation",
            "bridge_ledger_state_only",
        ):
            self.assertIn(phrase, doc)

        self.assertIn("botfucker.bridge_ledger.DurableBridgeLedger", doc)


if __name__ == "__main__":
    unittest.main()
