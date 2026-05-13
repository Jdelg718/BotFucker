import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from botfucker.local_ui import LocalUIState, make_handler, validate_mode_args
from botfucker.review_store import DurableReviewStore
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
        response_headers = dict(response.getheaders())
        conn.close()
        return response.status, json.loads(data), response_headers

    def request_text(self, method, path):
        conn = HTTPConnection(self.host, self.port, timeout=5)
        conn.request(method, path)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        response_headers = dict(response.getheaders())
        conn.close()
        return response.status, data, response_headers

    def test_dashboard_endpoint_declares_safe_local_modes(self):
        status, data, _headers = self.request_json("GET", "/api/dashboard")

        self.assertEqual(status, 200)
        self.assertTrue(data["human_approval_enabled"])
        self.assertFalse(data["yolo_enabled"])
        self.assertEqual(data["provider_auth_status"], "coming_later")
        self.assertTrue(data["mock_only"])

    def test_review_queue_and_action_endpoints_use_in_memory_state(self):
        status, queue, _headers = self.request_json("GET", "/api/review-queue")
        self.assertEqual(status, 200)
        item_id = queue["items"][0]["item_id"]

        action_status, event, _headers = self.request_json(
            "POST",
            "/api/actions",
            {"item_id": item_id, "action": "dismiss", "actor": "ui-test"},
        )
        self.assertEqual(action_status, 200)
        self.assertTrue(event["mock_only"])
        self.assertEqual(event["effect_scope"], "local_in_memory_sample_state_only")

        audit_status, audit, _headers = self.request_json("GET", "/api/audit-events")
        self.assertEqual(audit_status, 200)
        self.assertEqual(len(audit["events"]), 1)
        self.assertEqual(audit["events"][0]["action"], "dismiss")

    def test_unknown_endpoint_returns_json_404(self):
        status, data, _headers = self.request_json("GET", "/api/nope")

        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_security_headers_apply_to_json_and_static_assets(self):
        expected_csp = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'"

        json_status, _data, json_headers = self.request_json("GET", "/api/dashboard")
        static_status, _body, static_headers = self.request_text("GET", "/app.js")

        self.assertEqual(json_status, 200)
        self.assertEqual(static_status, 200)
        for headers in (json_headers, static_headers):
            self.assertEqual(headers.get("Content-Security-Policy"), expected_csp)
            self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")

    def test_action_endpoint_preserves_malicious_looking_strings_as_data(self):
        status, queue, _headers = self.request_json("GET", "/api/review-queue")
        self.assertEqual(status, 200)
        item_id = queue["items"][0]["item_id"]
        actor = '<img src=x onerror=alert(1)>'
        note = '<script>alert(1)</script> " onmouseover="alert(1)'

        action_status, event, _headers = self.request_json(
            "POST",
            "/api/actions",
            {"item_id": item_id, "action": "dismiss", "actor": actor, "note": note},
        )

        self.assertEqual(action_status, 200)
        self.assertEqual(event["actor"], actor)
        self.assertEqual(event["note"], note)


class LocalUIDurableSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "botfucker_review.sqlite3"
        with DurableReviewStore(self.db_path) as store:
            store.upsert_items(build_sample_review_items())
        state = LocalUIState.sqlite(self.db_path)
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
        self.tempdir.cleanup()

    def request_json(self, method, path, body=None):
        conn = HTTPConnection(self.host, self.port, timeout=5)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        response_headers = dict(response.getheaders())
        conn.close()
        return response.status, json.loads(data), response_headers

    def test_dashboard_review_queue_senders_and_audit_read_from_sqlite(self):
        status, dashboard, _headers = self.request_json("GET", "/api/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["storage_mode"], "sqlite")
        self.assertEqual(dashboard["db_path"], self.db_path.name)
        self.assertFalse(dashboard["sample_data"])
        self.assertTrue(dashboard["mock_only"])
        self.assertEqual(dashboard["counts"]["total_review_items"], len(build_sample_review_items()))
        self.assertEqual(dashboard["counts"]["pending_review_items"], len(build_sample_review_items()))
        self.assertEqual(dashboard["counts"]["actioned_review_items"], 0)
        self.assertEqual(dashboard["counts"]["audit_events"], 0)

        queue_status, queue, _headers = self.request_json("GET", "/api/review-queue")
        self.assertEqual(queue_status, 200)
        self.assertEqual(queue["storage_mode"], "sqlite")
        self.assertEqual(len(queue["items"]), len(build_sample_review_items()))

        sender_status, senders, _headers = self.request_json("GET", "/api/senders")
        self.assertEqual(sender_status, 200)
        self.assertEqual(senders["storage_mode"], "sqlite")
        self.assertGreaterEqual(len(senders["senders"]), 1)
        self.assertIn("sender", senders["senders"][0])

        audit_status, audit, _headers = self.request_json("GET", "/api/audit-events")
        self.assertEqual(audit_status, 200)
        self.assertEqual(audit["storage_mode"], "sqlite")
        self.assertEqual(audit["events"], [])

    def test_action_endpoint_persists_action_and_audit_to_sqlite(self):
        item_id = build_sample_review_items()[0].item_id
        action_status, event, _headers = self.request_json(
            "POST",
            "/api/actions",
            {"item_id": item_id, "action": "dismiss", "actor": "ui-test", "note": "durable"},
        )
        self.assertEqual(action_status, 200)
        self.assertEqual(event["action"], "dismiss")
        self.assertEqual(event["effect_scope"], "local_sqlite_review_state_only")

        with DurableReviewStore(self.db_path) as reopened:
            self.assertEqual(reopened.get_item(item_id).status, "actioned")
            events = reopened.list_audit_events(item_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "ui-test")
        self.assertEqual(events[0].note, "durable")


class LocalUICLIValidationTests(unittest.TestCase):
    def test_fail_closed_when_neither_sample_data_nor_db_is_selected(self):
        with self.assertRaisesRegex(SystemExit, "Choose exactly one"):
            validate_mode_args(sample_data=False, db_path=None)

    def test_fail_closed_when_both_sample_data_and_db_are_selected(self):
        with self.assertRaisesRegex(SystemExit, "Choose exactly one"):
            validate_mode_args(sample_data=True, db_path="botfucker_review.sqlite3")


class LocalUIRenderingSafetyTests(unittest.TestCase):
    def test_app_js_builds_dynamic_ui_with_dom_text_apis_not_inner_html(self):
        app_js = (Path(__file__).resolve().parent.parent / "web" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("innerHTML", app_js)
        self.assertNotIn("insertAdjacentHTML", app_js)
        self.assertIn("createElement", app_js)
        self.assertIn("textContent", app_js)

    def test_local_ui_uses_ff2k_hero_art_and_brand_tokens(self):
        web_dir = Path(__file__).resolve().parent.parent / "web"
        index_html = (web_dir / "index.html").read_text(encoding="utf-8")
        styles_css = (web_dir / "styles.css").read_text(encoding="utf-8")

        self.assertIn('/assets/botfucker-ff2k-hero.png', index_html)
        self.assertIn('alt="FF2K-style BotFucker mascot crushing spam bots"', index_html)
        self.assertIn('Inbox defense command center', index_html)
        self.assertIn('--bitcoin-orange: #f7931a', styles_css.lower())
        self.assertIn('--security-blue: #1da9ff', styles_css.lower())
        self.assertIn('box-shadow: 0 8px 0', styles_css)
        self.assertIn('hero-art', styles_css)

    def test_ff2k_hero_asset_is_served_locally(self):
        state = LocalUIState.sample()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        httpd.daemon_threads = True
        httpd.block_on_close = False
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = httpd.server_address
            conn = HTTPConnection(host, port, timeout=5)
            conn.request("GET", "/assets/botfucker-ff2k-hero.png")
            response = conn.getresponse()
            data = response.read()
            headers = dict(response.getheaders())
            conn.close()

            self.assertEqual(response.status, 200)
            self.assertEqual(headers.get("Content-Type"), "image/png")
            self.assertGreater(len(data), 1000)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
