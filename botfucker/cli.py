"""CLI and IMAP adapter for BotFucker."""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage as OutboundEmailMessage
from email.message import Message
from email.policy import default
from email.utils import make_msgid
from pathlib import Path

from .classifier import classify_message
from .history import SenderHistory
from .models import EmailMessage, decode_mime_header
from .responses import warning_template
from .yolo_policy import YoloPolicy, evaluate_yolo_decision


@dataclass(frozen=True)
class Config:
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    email_address: str
    email_password: str
    inbox_folder: str
    sales_folder: str
    blacklist_file: Path
    history_db: Path
    whitelist_domains: set[str]
    whitelist_contacts: set[str]


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def split_csv_env(name: str) -> set[str]:
    value = os.getenv(name, "")
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    return float(value) if value else default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def build_yolo_policy_from_env() -> YoloPolicy:
    return YoloPolicy(
        enabled=env_flag("BF_YOLO_ENABLED"),
        emergency_stop=env_flag("BF_YOLO_EMERGENCY_STOP"),
        confirmation_phrase=os.getenv("BF_YOLO_CONFIRMATION", ""),
        allowed_actions=split_csv_env("BF_YOLO_ALLOWED_ACTIONS"),
        allowed_classifications=split_csv_env("BF_YOLO_ALLOWED_CLASSIFICATIONS"),
        min_confidence=env_float("BF_YOLO_MIN_CONFIDENCE", 0.9),
        daily_action_limit=env_int("BF_YOLO_DAILY_ACTION_LIMIT", 0),
        reply_tone=os.getenv("BF_YOLO_REPLY_TONE", "firm_professional").strip().lower() or "firm_professional",
    )


def load_config() -> Config:
    return Config(
        imap_host=env_required("BF_IMAP_HOST"),
        imap_port=int(os.getenv("BF_IMAP_PORT", "993")),
        smtp_host=env_required("BF_SMTP_HOST"),
        smtp_port=int(os.getenv("BF_SMTP_PORT", "465")),
        email_address=env_required("BF_EMAIL_ADDRESS"),
        email_password=env_required("BF_EMAIL_PASSWORD"),
        inbox_folder=os.getenv("BF_INBOX_FOLDER", "INBOX"),
        sales_folder=os.getenv("BF_SALES_FOLDER", "Junk/Sales"),
        blacklist_file=Path(os.getenv("BF_BLACKLIST_FILE", "blacklist.txt")),
        history_db=Path(os.getenv("BF_HISTORY_DB", "botfucker_history.sqlite3")),
        whitelist_domains=split_csv_env("BF_WHITELIST_DOMAINS"),
        whitelist_contacts=split_csv_env("BF_WHITELIST_CONTACTS"),
    )


def is_whitelisted(sender: str, domain: str, config: Config, history: SenderHistory | None = None) -> bool:
    if sender in config.whitelist_contacts or domain in config.whitelist_domains:
        return True
    return history.is_whitelisted(sender, domain, status_scope="sender_or_domain") if history else False


def load_blacklist(path: Path) -> set[str]:
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle if line.strip() and not line.lstrip().startswith("#")}


def append_to_blacklist(domain: str, path: Path) -> None:
    if not domain:
        return

    existing = load_blacklist(path)
    if domain in existing:
        return

    with path.open("a", encoding="utf-8") as handle:
        handle.write(domain + "\n")


def message_is_recent(message: Message, cutoff: datetime) -> bool:
    normalized = EmailMessage.from_email_message(message)
    return normalized.received_at is None or normalized.received_at >= cutoff


def ensure_folder(imap: imaplib.IMAP4_SSL, folder: str) -> None:
    imap.create(folder)


def delete_message(imap: imaplib.IMAP4_SSL, uid: bytes) -> None:
    imap.uid("STORE", uid, "+FLAGS", r"(\Deleted)")


def move_message(imap: imaplib.IMAP4_SSL, uid: bytes, folder: str) -> None:
    ensure_folder(imap, folder)
    imap.uid("COPY", uid, folder)
    delete_message(imap, uid)


def send_notice_reply(config: Config, original_message: Message, sender: str, strike_level: int) -> None:
    subject = decode_mime_header(original_message.get("Subject", ""))
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    reply = OutboundEmailMessage()
    reply["From"] = config.email_address
    reply["To"] = sender
    reply["Subject"] = reply_subject
    reply["Message-ID"] = make_msgid()

    original_message_id = original_message.get("Message-ID", "")
    if original_message_id:
        reply["In-Reply-To"] = original_message_id
        reply["References"] = original_message_id

    reply.set_content(warning_template(strike_level))

    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
        smtp.login(config.email_address, config.email_password)
        smtp.send_message(reply)


def process_inbox(
    config: Config,
    live: bool,
    json_output: bool = False,
    auto_approve: bool = False,
    yolo_policy: YoloPolicy | None = None,
) -> None:
    if live and not auto_approve:
        raise RuntimeError("--live requires --auto-approve before replies, moves, deletes, or blacklist writes are performed")
    if live and yolo_policy is None:
        raise RuntimeError("YOLO guardrails are required before live provider actions")

    blacklist = load_blacklist(config.blacklist_file)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    mode = "LIVE/AUTO-APPROVE/YOLO-GUARDED" if live else "DRY-RUN"
    yolo_actions_taken = 0

    with SenderHistory(config.history_db) as history, imaplib.IMAP4_SSL(config.imap_host, config.imap_port) as imap:
        imap.login(config.email_address, config.email_password)
        imap.select(config.inbox_folder)

        since_date = cutoff.strftime("%d-%b-%Y")
        status, data = imap.uid("SEARCH", None, "UNSEEN", "SINCE", since_date)
        if status != "OK":
            raise RuntimeError("Could not search inbox")

        for uid in data[0].split():
            status, msg_data = imap.uid("FETCH", uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw_message = email.message_from_bytes(msg_data[0][1], policy=default)
            normalized = EmailMessage.from_email_message(raw_message)
            sender = normalized.from_email
            sender_domain = normalized.sender_domain

            if is_whitelisted(sender, sender_domain, config, history):
                _emit(mode, "whitelisted", normalized, None, json_output)
                continue

            domain_strike_level = history.get_domain_strike_level(sender_domain)
            blacklisted = sender_domain in blacklist or history.is_blacklisted(sender, sender_domain, status_scope="sender_or_domain")
            if blacklisted:
                result = classify_message(normalized, known_offender=True, strike_level=domain_strike_level)
                history.record_classification(normalized, result)
                _emit(mode, "blacklist_match", normalized, result, json_output)
                if live:
                    _require_yolo_allowed(
                        yolo_policy,
                        classification=result,
                        provider_action="delete_message",
                        daily_action_count=yolo_actions_taken,
                    )
                    yolo_actions_taken += 1
                    delete_message(imap, uid)
                continue

            if not message_is_recent(raw_message, cutoff):
                continue

            result = classify_message(
                normalized,
                strike_level=domain_strike_level,
            )
            history.record_classification(normalized, result)

            if result.recommended_action == "block_candidate":
                _emit(mode, "block_candidate", normalized, result, json_output)
                continue

            if result.recommended_action in {"warn_1", "warn_2", "warn_3"}:
                _emit(mode, "flagged", normalized, result, json_output)

                if live:
                    strike_level = min(domain_strike_level + 1, 3)
                    for provider_action in ("send_warning", "write_blacklist", "move_to_sales"):
                        _require_yolo_allowed(
                            yolo_policy,
                            classification=result,
                            provider_action=provider_action,
                            daily_action_count=yolo_actions_taken,
                        )
                        yolo_actions_taken += 1
                    send_notice_reply(config, raw_message, sender, strike_level)
                    history.issue_warning(sender, strike_level)
                    append_to_blacklist(sender_domain, config.blacklist_file)
                    move_message(imap, uid, config.sales_folder)
            elif json_output:
                _emit(mode, "review", normalized, result, json_output)

        if live:
            imap.expunge()
        imap.logout()


def _require_yolo_allowed(
    yolo_policy: YoloPolicy | None,
    *,
    classification: object,
    provider_action: str,
    daily_action_count: int,
) -> None:
    if yolo_policy is None:
        raise RuntimeError("YOLO guardrails are required before live provider actions")
    decision = evaluate_yolo_decision(
        yolo_policy,
        classification=classification,
        provider_action=provider_action,
        daily_action_count=daily_action_count,
    )
    if not decision.allowed:
        raise RuntimeError("YOLO guardrail blocked live provider action: " + "; ".join(decision.reasons))


def _emit(mode: str, event: str, message: EmailMessage, result: object | None, json_output: bool) -> None:
    if json_output:
        payload = {
            "mode": mode,
            "event": event,
            "message": {
                "message_id": message.message_id,
                "from_email": message.from_email,
                "sender_domain": message.sender_domain,
                "subject": message.subject,
                "received_at": message.received_at.isoformat() if message.received_at else None,
            },
            "classification": result.to_dict() if result else None,
        }
        print(json.dumps(payload, sort_keys=True))
        return

    if result is None:
        print(f"[{mode}] {event}: {message.from_email}")
    else:
        reasons = "; ".join(result.reasons)
        print(f"[{mode}] {event}: {message.from_email} | {reasons}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan unread IMAP mail for unsolicited sales outreach.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Connect in live mode. Requires --auto-approve before replies, moves, deletes, or blacklist writes occur.",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Explicitly approve legacy automation for warnings, moves, deletes, and blacklist writes. In live mode this still requires BF_YOLO_* guardrails.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON lines for dry-run/review output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    yolo_policy = build_yolo_policy_from_env() if args.live else None
    process_inbox(load_config(), live=args.live, json_output=args.json, auto_approve=args.auto_approve, yolo_policy=yolo_policy)
