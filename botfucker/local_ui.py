"""Stdlib local UI server for BotFucker local review queues.

The local UI has two explicit storage modes:

* ``--sample-data`` uses deterministic in-memory fake data for demos/tests.
* ``--db PATH`` reads/writes the durable local SQLite review queue.

Both modes are local-only. UI actions never call providers, send mail, move mail,
delete mail, or mutate provider-side whitelist/blacklist state.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from botfucker.review_queue import MOCK_SAFETY_NOTE, MockReviewQueue, ReviewQueueError, SUPPORTED_ACTIONS
from botfucker.review_store import DurableReviewStore, ReviewStoreError
from botfucker.samples import build_sample_review_items

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
YOLO_COPY = (
    "YOLO mode lets BotFucker reply/block without asking you first. This can save time and also make you look "
    "like an unhinged mailbox goblin if configured badly. Start conservative."
)
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
}


@dataclass
class LocalUIState:
    """Local UI state facade for sample-memory and durable SQLite modes."""

    storage_mode: str
    queue: MockReviewQueue | None = None
    db_path: Path | None = None

    @classmethod
    def sample(cls) -> "LocalUIState":
        return cls(storage_mode="sample", queue=MockReviewQueue(build_sample_review_items()))

    @classmethod
    def sqlite(cls, db_path: str | Path) -> "LocalUIState":
        return cls(storage_mode="sqlite", db_path=Path(db_path))

    @property
    def sample_data(self) -> bool:
        return self.storage_mode == "sample"

    @property
    def mock_only(self) -> bool:
        # Both local modes are provider-safe: no provider action is performed.
        return True

    def db_path_label(self) -> str | None:
        return self.db_path.name if self.db_path else None

    def _mode_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "sample_data": self.sample_data,
            "mock_only": self.mock_only,
            "storage_mode": self.storage_mode,
        }
        if self.db_path is not None:
            fields["db_path"] = self.db_path_label()
        return fields

    def dashboard(self) -> dict[str, Any]:
        items = self.list_items()
        events = self.list_audit_events()
        pending = len([item for item in items if item.status == "pending"])
        actioned = len(items) - pending
        safety_note = (
            "Local SQLite review UI only; actions update local SQLite state and never call mail providers."
            if self.storage_mode == "sqlite"
            else "Local sample UI only; no provider auth and no real mail actions are available."
        )
        return {
            "app": "BotFucker Local Review UI",
            "phase": "Phase 5 durable local UI",
            **self._mode_fields(),
            "human_approval_enabled": True,
            "yolo_enabled": False,
            "yolo_copy": YOLO_COPY,
            "provider_auth_status": "coming_later",
            "counts": {
                "total_review_items": len(items),
                "pending_review_items": pending,
                "actioned_review_items": actioned,
                "audit_events": len(events),
            },
            "safety_note": safety_note,
        }

    def settings(self) -> dict[str, Any]:
        return {
            **self._mode_fields(),
            "human_approval_enabled": True,
            "yolo_visible": True,
            "yolo_enabled": False,
            "yolo_copy": YOLO_COPY,
            "provider_auth": "not_configured_local_only",
            "actions_are_mock_simulations_only": self.storage_mode == "sample",
            "actions_are_local_sqlite_review_state_only": self.storage_mode == "sqlite",
            "available_mock_actions": list(SUPPORTED_ACTIONS),
        }

    def list_items(self, status: str | None = None) -> list[Any]:
        if self.storage_mode == "sample":
            assert self.queue is not None
            if status and status != "all":
                return [item for item in self.queue.items if item.status == status]
            return list(self.queue.items)
        assert self.db_path is not None
        with DurableReviewStore(self.db_path) as store:
            return store.list_items(status=status)

    def list_audit_events(self) -> list[Any]:
        if self.storage_mode == "sample":
            assert self.queue is not None
            return list(self.queue.audit_events)
        assert self.db_path is not None
        with DurableReviewStore(self.db_path) as store:
            return store.list_audit_events()

    def sender_history(self) -> list[dict[str, Any]]:
        if self.storage_mode == "sample":
            assert self.queue is not None
            return list(self.queue.sender_history().values())

        items = self.list_items()
        events = self.list_audit_events()
        last_actions = {event.item_id: event.action for event in events}
        history: dict[str, dict[str, Any]] = {}
        for item in items:
            row = history.setdefault(
                item.from_email,
                {
                    "sender": item.from_email,
                    "sender_domain": item.sender_domain,
                    "message_count": 0,
                    "max_strike_level": 0,
                    "classifications": [],
                    "last_mock_action": None,
                    "mock_only": True,
                    "storage_mode": "sqlite",
                    "safety_note": MOCK_SAFETY_NOTE,
                },
            )
            row["message_count"] += 1
            row["max_strike_level"] = max(row["max_strike_level"], item.sender_strike_level)
            if item.classification not in row["classifications"]:
                row["classifications"].append(item.classification)
            if item.item_id in last_actions:
                row["last_mock_action"] = last_actions[item.item_id]
        return list(history.values())

    def apply_action(self, item_id: str, action: str, actor: str = "local-ui", note: str = "") -> Any:
        if self.storage_mode == "sample":
            assert self.queue is not None
            return self.queue.apply_action(item_id=item_id, action=action, actor=actor, note=note)
        assert self.db_path is not None
        with DurableReviewStore(self.db_path) as store:
            return store.apply_action(item_id=item_id, action=action, actor=actor or "local-ui", note=note)


def make_handler(state: LocalUIState):
    class BotFuckerLocalUIHandler(BaseHTTPRequestHandler):
        server_version = "BotFuckerLocalUI/0.5"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed.path, parse_qs(parsed.query))
                return
            self._serve_asset(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/actions":
                self._handle_action_post()
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
            if path == "/api/dashboard":
                self._send_json(state.dashboard())
            elif path == "/api/review-queue":
                status = query.get("status", [None])[0]
                self._send_json(
                    {
                        "items": [item.to_dict() for item in state.list_items(status=status)],
                        "mock_only": True,
                        "storage_mode": state.storage_mode,
                    }
                )
            elif path == "/api/senders":
                self._send_json({"senders": state.sender_history(), "mock_only": True, "storage_mode": state.storage_mode})
            elif path == "/api/audit-events":
                self._send_json(
                    {
                        "events": [event.to_dict() for event in state.list_audit_events()],
                        "mock_only": True,
                        "storage_mode": state.storage_mode,
                    }
                )
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
                event = state.apply_action(
                    item_id=str(payload.get("item_id", "")),
                    action=str(payload.get("action", "")),
                    actor=str(payload.get("actor", "local-ui")),
                    note=str(payload.get("note", "")),
                )
            except (json.JSONDecodeError, ReviewQueueError, ReviewStoreError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(event.to_dict())

        def _send_security_headers(self) -> None:
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)

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
            self._send_security_headers()
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_security_headers()
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

    return BotFuckerLocalUIHandler


def validate_mode_args(sample_data: bool, db_path: str | Path | None) -> None:
    if sample_data == bool(db_path):
        raise SystemExit("Choose exactly one local UI storage mode: --sample-data or --db PATH.")


def run_server(host: str, port: int, sample_data: bool = False, db_path: str | Path | None = None) -> None:
    validate_mode_args(sample_data=sample_data, db_path=db_path)
    state = LocalUIState.sample() if sample_data else LocalUIState.sqlite(Path(db_path or ""))
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"BotFucker local review UI running at http://{host}:{port}/")
    if state.storage_mode == "sqlite":
        print(f"SQLite review queue mode: {state.db_path_label()} (local review actions only; no provider actions).")
    else:
        print("Sample/mock data only. No provider auth or real mail actions are enabled.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down BotFucker local review UI.")
    finally:
        httpd.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the BotFucker local review UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    parser.add_argument("--sample-data", action="store_true", help="Use deterministic fake sample review data.")
    parser.add_argument("--db", help="Use a durable local SQLite review queue database path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_server(args.host, args.port, sample_data=args.sample_data, db_path=args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
