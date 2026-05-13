"""Stdlib local UI server for BotFucker Phase 2 sample review queue."""

from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from botfucker.review_queue import MockReviewQueue, ReviewQueueError
from botfucker.samples import build_sample_review_items

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
YOLO_COPY = (
    "YOLO mode lets BotFucker reply/block without asking you first. This can save time and also make you look "
    "like an unhinged mailbox goblin if configured badly. Start conservative."
)


@dataclass
class LocalUIState:
    queue: MockReviewQueue
    sample_data: bool = True

    @classmethod
    def sample(cls) -> "LocalUIState":
        return cls(queue=MockReviewQueue(build_sample_review_items()), sample_data=True)

    def dashboard(self) -> dict[str, Any]:
        pending = len(self.queue.pending_items())
        actioned = len(self.queue.items) - pending
        return {
            "app": "BotFucker Local Review UI",
            "phase": "Phase 2 local UI skeleton",
            "sample_data": self.sample_data,
            "mock_only": True,
            "human_approval_enabled": True,
            "yolo_enabled": False,
            "yolo_copy": YOLO_COPY,
            "provider_auth_status": "coming_later",
            "counts": {
                "total_review_items": len(self.queue.items),
                "pending_review_items": pending,
                "actioned_review_items": actioned,
                "audit_events": len(self.queue.audit_events),
            },
            "safety_note": "Local sample UI only; no provider auth and no real mail actions are available.",
        }

    def settings(self) -> dict[str, Any]:
        return {
            "human_approval_enabled": True,
            "yolo_visible": True,
            "yolo_enabled": False,
            "yolo_copy": YOLO_COPY,
            "provider_auth": "coming_later",
            "actions_are_mock_simulations_only": True,
            "available_mock_actions": list(self.queue.supported_actions),
        }


def make_handler(state: LocalUIState):
    class BotFuckerLocalUIHandler(BaseHTTPRequestHandler):
        server_version = "BotFuckerLocalUI/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed.path)
                return
            self._serve_asset(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/actions":
                self._handle_action_post()
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def _handle_api_get(self, path: str) -> None:
            if path == "/api/dashboard":
                self._send_json(state.dashboard())
            elif path == "/api/review-queue":
                self._send_json({"items": [item.to_dict() for item in state.queue.items], "mock_only": True})
            elif path == "/api/senders":
                self._send_json({"senders": list(state.queue.sender_history().values()), "mock_only": True})
            elif path == "/api/audit-events":
                self._send_json({"events": [event.to_dict() for event in state.queue.audit_events], "mock_only": True})
            elif path == "/api/settings":
                self._send_json(state.settings())
            else:
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def _handle_action_post(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw)
                event = state.queue.apply_action(
                    item_id=str(payload.get("item_id", "")),
                    action=str(payload.get("action", "")),
                    actor=str(payload.get("actor", "local-ui")),
                    note=str(payload.get("note", "")),
                )
            except (json.JSONDecodeError, ReviewQueueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(event.to_dict())

        def _serve_asset(self, path: str) -> None:
            if path in ("", "/"):
                asset = WEB_DIR / "index.html"
            else:
                relative = Path(unquote(path).lstrip("/"))
                asset = (WEB_DIR / relative).resolve()
                if WEB_DIR.resolve() not in asset.parents and asset != WEB_DIR.resolve():
                    self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                    return
            if not asset.is_file():
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(str(asset))[0] or "application/octet-stream"
            data = asset.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

    return BotFuckerLocalUIHandler


def run_server(host: str, port: int, sample_data: bool = False) -> None:
    if not sample_data:
        raise SystemExit("Phase 2 local UI only supports --sample-data. Provider auth is coming later.")
    state = LocalUIState.sample()
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"BotFucker local review UI running at http://{host}:{port}/")
    print("Sample/mock data only. No provider auth or real mail actions are enabled.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down BotFucker local review UI.")
    finally:
        httpd.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the BotFucker local review UI skeleton.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    parser.add_argument("--sample-data", action="store_true", help="Use deterministic fake sample review data.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_server(args.host, args.port, sample_data=args.sample_data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
