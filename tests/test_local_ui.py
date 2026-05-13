import json
import threading
import unittest
from http.client import HTTPConnection

from botfucker.local_ui import LocalUIState, make_handler
from botfucker.samples import build_sample_review_items

try:
    from http.server import ThreadingHTTPServer
except ImportError:  # pragma: no cover
    from http.server import HTTPServer as ThreadingHTTPServer


class LocalUISmokeTests(unittest.TestCase):
    def setUp(self):
        state = LocalUIState.sample()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        self.httpd.daemon_threads = True
        self.httpd.block_on_close = False
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.httpd.server_address

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    def request_json(self, method, path, body=None):
        conn = HTTPConnection(self.host, self.port, timeout=5)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()
        return response.status, json.loads(data)

    def test_dashboard_endpoint_declares_safe_local_modes(self):
        status, data = self.request_json("GET", "/api/dashboard")

        self.assertEqual(status, 200)
        self.assertTrue(data["human_approval_enabled"])
        self.assertFalse(data["yolo_enabled"])
        self.assertEqual(data["provider_auth_status"], "coming_later")
        self.assertTrue(data["mock_only"])

    def test_review_queue_and_action_endpoints_use_in_memory_state(self):
        status, queue = self.request_json("GET", "/api/review-queue")
        self.assertEqual(status, 200)
        item_id = queue["items"][0]["item_id"]

        action_status, event = self.request_json(
            "POST",
            "/api/actions",
            {"item_id": item_id, "action": "dismiss", "actor": "ui-test"},
        )
        self.assertEqual(action_status, 200)
        self.assertTrue(event["mock_only"])
        self.assertEqual(event["effect_scope"], "local_in_memory_sample_state_only")

        audit_status, audit = self.request_json("GET", "/api/audit-events")
        self.assertEqual(audit_status, 200)
        self.assertEqual(len(audit["events"]), 1)
        self.assertEqual(audit["events"][0]["action"], "dismiss")

    def test_unknown_endpoint_returns_json_404(self):
        status, data = self.request_json("GET", "/api/nope")

        self.assertEqual(status, 404)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
