import tempfile
import unittest
from pathlib import Path

from botfucker.bridge_ledger import BridgeLedgerError, DRY_RUN_LOGGED, DurableBridgeLedger
from botfucker.bridge_rehearsal import rehearse_approved_actions


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
        "approved_at": "2026-05-18T12:00:00Z",
        "draft_reply": "Human-reviewed warning text",
        "safety_scope": "provider_action_export_only",
        "provider_execution": "not_performed",
    }
    action.update(overrides)
    return action


def sample_bundle(action=None):
    action = action or sample_action()
    return {
        "schema": "botfucker.approved_actions.v1",
        "safety_scope": "provider_action_export_only",
        "provider_execution": "not_performed",
        "cursor": {"since_audit_id": None, "last_audit_id": action["audit_id"]},
        "actions": [action],
    }


class BridgeRehearsalTests(unittest.TestCase):
    def test_emergency_stop_blocks_before_ledger_claim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                outcomes = rehearse_approved_actions(sample_bundle(action), ledger, emergency_stop=True)

                self.assertEqual(1, len(outcomes))
                self.assertEqual("blocked_by_emergency_stop", outcomes[0].status)
                self.assertFalse(outcomes[0].ledger_acquired)
                self.assertFalse(outcomes[0].would_execute)
                self.assertEqual("not_performed", outcomes[0].provider_execution)
                self.assertEqual([], ledger.list_records())

    def test_dry_run_rehearsal_claims_ledger_and_logs_without_provider_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                outcomes = rehearse_approved_actions(sample_bundle(action), ledger, emergency_stop=False)

                self.assertEqual(1, len(outcomes))
                self.assertEqual(DRY_RUN_LOGGED, outcomes[0].status)
                self.assertTrue(outcomes[0].ledger_acquired)
                self.assertTrue(outcomes[0].would_execute)
                self.assertEqual("not_performed", outcomes[0].provider_execution)

                record = ledger.get("audit-0001")
                self.assertEqual(DRY_RUN_LOGGED, record.status)
                self.assertTrue(record.dry_run)
                self.assertEqual("", record.provider_result_id)

    def test_duplicate_rehearsal_is_skipped_by_durable_ledger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                action = sample_action()
                bundle = sample_bundle(action)

                first = rehearse_approved_actions(bundle, ledger, emergency_stop=False)
                second = rehearse_approved_actions(bundle, ledger, emergency_stop=False)

                self.assertEqual(DRY_RUN_LOGGED, first[0].status)
                self.assertEqual("duplicate_skipped", second[0].status)
                self.assertFalse(second[0].ledger_acquired)
                self.assertFalse(second[0].would_execute)
                self.assertEqual(1, len(ledger.list_records()))

    def test_live_mode_is_not_a_hidden_option(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                with self.assertRaises(BridgeLedgerError):
                    rehearse_approved_actions(sample_bundle(), ledger, dry_run=False, emergency_stop=False)

    def test_unsafe_actions_still_fail_closed_when_stop_is_off(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with DurableBridgeLedger(Path(tmpdir) / "ledger.sqlite3") as ledger:
                unsafe_action = sample_action(approved_action="delete_message")
                with self.assertRaises(BridgeLedgerError):
                    rehearse_approved_actions(sample_bundle(unsafe_action), ledger, emergency_stop=False)


if __name__ == "__main__":
    unittest.main()
