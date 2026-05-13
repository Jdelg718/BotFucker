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
    return history.is_whitelisted(sender, domain) if history else False


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


def process_inbox(config: Config, live: bool, json_output: bool = False) -> None:
    blacklist = load_blacklist(config.blacklist_file)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    mode = "LIVE" if live else "DRY-RUN"

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
            blacklisted = sender_domain in blacklist or history.is_blacklisted(sender, sender_domain)
            if blacklisted:
                result = classify_message(normalized, known_offender=True, strike_level=domain_strike_level)
                history.record_classification(normalized, result)
                _emit(mode, "blacklist_match", normalized, result, json_output)
                if live:
                    delete_message(imap, uid)
                continue

            if not message_is_recent(raw_message, cutoff):
                continue

            result = classify_message(
                normalized,
                strike_level=domain_strike_level,
            )
            history.record_classification(normalized, result)

            if result.recommended_action in {"warn_1", "warn_2", "warn_3", "block_candidate"}:
                _emit(mode, "flagged", normalized, result, json_output)

                if live:
                    strike_level = min(domain_strike_level + 1, 3)
                    send_notice_reply(config, raw_message, sender, strike_level)
                    history.issue_warning(sender, strike_level)
                    append_to_blacklist(sender_domain, config.blacklist_file)
                    move_message(imap, uid, config.sales_folder)
            elif json_output:
                _emit(mode, "review", normalized, result, json_output)

        if live:
            imap.expunge()
        imap.logout()


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
        help="Perform replies, moves, deletes, and blacklist writes. Dry-run is default.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON lines for dry-run/review output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    process_inbox(load_config(), live=args.live, json_output=args.json)
