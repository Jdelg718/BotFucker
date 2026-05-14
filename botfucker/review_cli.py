"""Safe local CLI for BotFucker durable review queues.

All commands operate on local SQLite review state only. They do not import the
legacy IMAP/SMTP CLI module, do not require provider credentials, and do not
send, move, delete, archive, whitelist, or blacklist anything with a provider.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .review_queue import MOCK_SAFETY_NOTE
from .review_store import DurableReviewStore, ReviewStoreError
from .samples import build_sample_review_items
from .webhook_contract import WebhookPayloadError, iter_webhook_review_items

ACTION_BY_COMMAND = {
    "approve": "approve_warning",
    "dismiss": "dismiss",
    "whitelist-sender": "whitelist_sender",
    "blacklist-sender": "blacklist_sender",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage a local durable BotFucker review queue. Provider-safe and dry/mock by default."
    )
    parser.add_argument("--db", default="botfucker_review.sqlite3", help="Local SQLite review database path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-samples", help="Seed deterministic fake review items into the local queue.")

    list_parser = subparsers.add_parser("list", help="List local review items.")
    list_parser.add_argument("--status", choices=("pending", "actioned", "all"), default="pending")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON lines.")

    for command in ACTION_BY_COMMAND:
        action_parser = subparsers.add_parser(command, help=f"Record local {command} review action.")
        action_parser.add_argument("item_id", help="Review item id to action.")
        action_parser.add_argument("--actor", default="review-cli", help="Local actor label for the audit log.")
        action_parser.add_argument("--note", default="", help="Optional local audit note.")
        action_parser.add_argument("--json", action="store_true", help="Emit the audit event as JSON.")

    audit_parser = subparsers.add_parser("audit", help="Show local review audit events.")
    audit_parser.add_argument("--item-id", default=None, help="Filter audit events by review item id.")
    audit_parser.add_argument("--json", action="store_true", help="Emit JSON lines.")

    export_parser = subparsers.add_parser(
        "export-approved-actions",
        help="Export human-approved local audit intents as provider-action JSON without executing them.",
    )
    export_parser.add_argument(
        "--since-audit-id",
        default=None,
        help="Export approved actions after this audit id, e.g. audit-0001.",
    )

    import_parser = subparsers.add_parser("import-json", help="Import review items from a JSON file or '-' for stdin.")
    import_parser.add_argument("path", help="JSON list of review items, {'items': [...]}, or '-' for stdin.")

    webhook_import_parser = subparsers.add_parser(
        "import-webhook-json",
        help="Normalize n8n/webhook email JSON from a file or '-' for stdin into local review items.",
    )
    webhook_import_parser.add_argument("path", help="Webhook JSON object/list/wrapper, or '-' for stdin.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with DurableReviewStore(Path(args.db)) as store:
            if args.command == "seed-samples":
                inserted = store.upsert_items(build_sample_review_items())
                total = len(store.list_items(status="all"))
                print(f"Seeded 4 sample review items into {args.db} ({inserted} new, {total} total).")
                print("Safety: local deterministic samples only; no provider credentials required; no email was sent.")
                return 0

            if args.command == "list":
                items = store.list_items(status=args.status)
                if args.json:
                    for item in items:
                        print(json.dumps(item.to_dict(), sort_keys=True))
                else:
                    if not items:
                        print(f"No {args.status} review items found in {args.db}.")
                    for item in items:
                        print(
                            f"{item.item_id} | {item.status} | {item.from_email} | "
                            f"{item.classification}/{item.confidence:.2f} | {item.recommended_action} | {item.subject}"
                        )
                    print("Safety: local review queue only. Listing does not touch mailbox providers.")
                return 0

            if args.command in ACTION_BY_COMMAND:
                action = ACTION_BY_COMMAND[args.command]
                event = store.apply_action(args.item_id, action, actor=args.actor, note=args.note)
                if args.json:
                    print(json.dumps(event.to_dict(), sort_keys=True))
                else:
                    label = "local review approval only" if action == "approve_warning" else "local review action only"
                    print(f"{action} recorded locally for {args.item_id} by {event.actor} ({label}).")
                    print(event.safety_note)
                return 0

            if args.command == "audit":
                events = store.list_audit_events(item_id=args.item_id)
                if args.json:
                    for event in events:
                        print(json.dumps(event.to_dict(), sort_keys=True))
                else:
                    if not events:
                        print("No local review audit events found.")
                    for event in events:
                        print(f"{event.created_at} | {event.event_id} | {event.item_id} | {event.action} | {event.actor} | {event.note}")
                    print("Safety: audit events describe local review decisions only, not provider-side effects.")
                return 0

            if args.command == "export-approved-actions":
                bundle = _build_approved_action_export(store, since_audit_id=args.since_audit_id)
                print(json.dumps(bundle, sort_keys=True))
                return 0

            if args.command == "import-json":
                payload = _load_json(args.path)
                items = payload.get("items", []) if isinstance(payload, dict) else payload
                if not isinstance(items, list):
                    raise ReviewStoreError("JSON import must be a list or an object with an 'items' list")
                inserted = store.upsert_items(items)
                total = len(store.list_items(status="all"))
                print(f"Imported {len(items)} local review items into {args.db} ({inserted} new, {total} total).")
                print("Safety: import records local review metadata only; no provider action was performed.")
                return 0

            if args.command == "import-webhook-json":
                payload = _load_json(args.path)
                # Normalize the entire batch before writing, so invalid later
                # messages cannot partially import earlier messages.
                items = iter_webhook_review_items(payload)
                inserted = store.upsert_items(items)
                total = len(store.list_items(status="all"))
                print(f"Imported {len(items)} webhook message(s) into {args.db} ({inserted} new, {total} total).")
                print("Safety: webhook import stores bounded local review metadata only; no provider action was performed.")
                return 0

    except (OSError, json.JSONDecodeError, ReviewStoreError, WebhookPayloadError) as exc:
        print(f"review_cli error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unhandled command: {args.command}")
    return 2


def _load_json(path: str) -> Any:
    if path == "-":
        return json.loads(sys.stdin.read())
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_approved_action_export(store: DurableReviewStore, since_audit_id: str | None = None) -> dict[str, Any]:
    since_number = _audit_number(since_audit_id) if since_audit_id else None
    actions: list[dict[str, Any]] = []
    last_audit_id = since_audit_id

    for event in store.list_audit_events():
        if event.action != "approve_warning":
            continue
        event_number = _audit_number(event.event_id)
        if since_number is not None and event_number <= since_number:
            continue

        item = store.get_item(event.item_id)
        actions.append(
            {
                "audit_id": event.event_id,
                "item_id": item.item_id,
                "message_id": item.message_id,
                "thread_id": item.thread_id,
                "provider": _provider_from_item(item.item_id, item.source),
                "approved_action": event.action,
                "approved_by": event.actor,
                "approved_at": event.created_at,
                "draft_reply": item.draft_reply,
                "safety_scope": "provider_action_export_only",
                "provider_execution": "not_performed",
            }
        )
        last_audit_id = event.event_id

    return {
        "schema": "botfucker.approved_actions.v1",
        "safety_scope": "provider_action_export_only",
        "provider_execution": "not_performed",
        "cursor": {
            "since_audit_id": since_audit_id,
            "last_audit_id": last_audit_id,
        },
        "actions": actions,
    }


def _audit_number(audit_id: str | None) -> int:
    if not audit_id:
        return 0
    prefix = "audit-"
    if not audit_id.startswith(prefix):
        raise ReviewStoreError(f"Invalid audit id cursor: {audit_id}")
    try:
        return int(audit_id[len(prefix):])
    except ValueError as exc:
        raise ReviewStoreError(f"Invalid audit id cursor: {audit_id}") from exc


def _provider_from_item(item_id: str, source: str) -> str:
    for value in (source, item_id):
        if value.startswith("webhook:"):
            parts = value.split(":", 2)
            if len(parts) >= 2 and parts[1]:
                return parts[1]
    return "local"


if __name__ == "__main__":
    raise SystemExit(main())
