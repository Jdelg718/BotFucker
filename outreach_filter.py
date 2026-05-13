#!/usr/bin/env python3
"""
IMAP outreach filter for unsolicited sales and generic AI-generated pitches.

Default behavior is dry-run. Use --live to send replies, move messages, delete
blacklisted senders, and update the local blacklist file.
"""

from __future__ import annotations

import argparse
import email
import imaplib
import os
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import EmailMessage, Message
from email.policy import default
from email.utils import getaddresses, make_msgid, parsedate_to_datetime
from pathlib import Path


NOTICE_REPLY = (
    "Your message has been identified as unsolicited outreach. "
    "This address is not monitored for sales pitches. "
    "Please remove all associated data from your CRM immediately and cease "
    "further contact."
)

COLD_OUTREACH_PATTERNS = [
    r"\bquick call\b",
    r"\bscale your business\b",
    r"\bwondering if you saw my last\b",
    r"\bfollow(?:ing)? up\b",
    r"\bjust checking in\b",
    r"\bbook (?:a )?(?:call|demo|meeting)\b",
    r"\b15[- ]?minute\b",
    r"\bvalue proposition\b",
    r"\bgrowth strategy\b",
    r"\blead generation\b",
    r"\bcrm\b",
    r"\bsales pipeline\b",
    r"\bdecision maker\b",
    r"\bsolutions?\b",
]

AI_SIGNATURE_PATTERNS = [
    r"\bi hope this (?:email|message) finds you well\b",
    r"\bin today's (?:competitive|fast[- ]paced) landscape\b",
    r"\btailored solutions\b",
    r"\bunlock (?:growth|potential|efficiency)\b",
    r"\bdrive measurable results\b",
    r"\bstreamline your operations\b",
    r"\btransform your business\b",
    r"\bpersonalized strategy\b",
    r"\bgeneric value proposition\b",
]


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
        whitelist_domains=split_csv_env("BF_WHITELIST_DOMAINS"),
        whitelist_contacts=split_csv_env("BF_WHITELIST_CONTACTS"),
    )


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""

    decoded_parts: list[str] = []
    for content, charset in decode_header(value):
        if isinstance(content, bytes):
            decoded_parts.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(content)
    return "".join(decoded_parts)


def get_sender(message: Message) -> tuple[str, str]:
    from_header = decode_mime_header(message.get("From", ""))
    addresses = getaddresses([from_header])
    if not addresses:
        return "", ""

    _, address = addresses[0]
    address = address.lower().strip()
    domain = address.split("@", 1)[1] if "@" in address else ""
    return address, domain


def is_whitelisted(sender: str, domain: str, config: Config) -> bool:
    return sender in config.whitelist_contacts or domain in config.whitelist_domains


def load_blacklist(path: Path) -> set[str]:
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8") as handle:
        return {
            line.strip().lower()
            for line in handle
            if line.strip() and not line.lstrip().startswith("#")
        }


def append_to_blacklist(domain: str, path: Path) -> None:
    if not domain:
        return

    existing = load_blacklist(path)
    if domain in existing:
        return

    with path.open("a", encoding="utf-8") as handle:
        handle.write(domain + "\n")


def extract_text(message: Message) -> str:
    parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/plain":
                parts.append(get_part_text(part))
    elif message.get_content_type() == "text/plain":
        parts.append(get_part_text(message))

    return "\n".join(parts)


def get_part_text(part: Message) -> str:
    try:
        return part.get_content()
    except Exception:
        payload = part.get_payload(decode=True) or b""
        return payload.decode(errors="replace")


def message_is_recent(message: Message, cutoff: datetime) -> bool:
    date_header = message.get("Date")
    if not date_header:
        return True

    try:
        sent_at = parsedate_to_datetime(date_header)
    except Exception:
        return True

    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    return sent_at >= cutoff


def classify_cold_outreach(subject: str, body: str) -> tuple[bool, list[str]]:
    text = f"{subject}\n{body}".lower()
    reasons: list[str] = []

    for pattern in COLD_OUTREACH_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            reasons.append(f"cold outreach phrase: {pattern}")

    words = re.findall(r"\b[a-z']+\b", text)
    if words:
        first_person_count = sum(
            1 for word in words if word in {"i", "i'm", "my", "mine", "me"}
        )
        solutions_count = sum(
            1 for word in words if word in {"solution", "solutions"}
        )
        first_person_ratio = first_person_count / len(words)

        if first_person_ratio > 0.035 and first_person_count >= 6:
            reasons.append("high first-person language frequency")

        if solutions_count >= 2:
            reasons.append("repeated solution/solutions wording")

    return bool(reasons), reasons


def analyze_ai_generated(
    subject: str, body: str, sender_domain: str
) -> tuple[bool, list[str]]:
    text = f"{subject}\n{body}".lower()
    reasons: list[str] = []

    for pattern in AI_SIGNATURE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            reasons.append(f"generic AI-like phrase: {pattern}")

    has_formal_structure = bool(
        re.search(r"\b(dear|hello|hi)\b.{0,80}\n", text)
        and re.search(r"\b(best regards|warm regards|sincerely|kind regards)\b", text)
    )
    has_generic_value_prop = bool(
        re.search(
            r"\b(help|enable|empower)\b.{0,80}"
            r"\b(grow|scale|optimize|streamline|automate)\b",
            text,
        )
    )
    lacks_specific_reference = sender_domain not in text and not re.search(
        r"\b(your recent|your article|your post|your team at|your work on)\b",
        text,
    )

    if has_formal_structure:
        reasons.append("overly formal email structure")
    if has_generic_value_prop:
        reasons.append("generic value proposition wording")
    if lacks_specific_reference:
        reasons.append("no specific personal or business reference detected")

    return len(reasons) >= 2, reasons


def ensure_folder(imap: imaplib.IMAP4_SSL, folder: str) -> None:
    # Some servers return an error if the folder already exists; that is fine.
    imap.create(folder)


def delete_message(imap: imaplib.IMAP4_SSL, uid: bytes) -> None:
    imap.uid("STORE", uid, "+FLAGS", r"(\Deleted)")


def move_message(imap: imaplib.IMAP4_SSL, uid: bytes, folder: str) -> None:
    ensure_folder(imap, folder)
    imap.uid("COPY", uid, folder)
    delete_message(imap, uid)


def send_notice_reply(config: Config, original_message: Message, sender: str) -> None:
    subject = decode_mime_header(original_message.get("Subject", ""))
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    reply = EmailMessage()
    reply["From"] = config.email_address
    reply["To"] = sender
    reply["Subject"] = reply_subject
    reply["Message-ID"] = make_msgid()

    original_message_id = original_message.get("Message-ID", "")
    if original_message_id:
        reply["In-Reply-To"] = original_message_id
        reply["References"] = original_message_id

    reply.set_content(NOTICE_REPLY)

    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
        smtp.login(config.email_address, config.email_password)
        smtp.send_message(reply)


def process_inbox(config: Config, live: bool) -> None:
    blacklist = load_blacklist(config.blacklist_file)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    mode = "LIVE" if live else "DRY-RUN"

    with imaplib.IMAP4_SSL(config.imap_host, config.imap_port) as imap:
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

            message = email.message_from_bytes(msg_data[0][1], policy=default)
            sender, sender_domain = get_sender(message)

            if is_whitelisted(sender, sender_domain, config):
                print(f"[{mode}] whitelisted: {sender}")
                continue

            if sender_domain in blacklist:
                print(f"[{mode}] blacklist match, delete: {sender}")
                if live:
                    delete_message(imap, uid)
                continue

            if not message_is_recent(message, cutoff):
                continue

            subject = decode_mime_header(message.get("Subject", ""))
            body = extract_text(message)
            is_cold, cold_reasons = classify_cold_outreach(subject, body)
            is_ai_like, ai_reasons = analyze_ai_generated(subject, body, sender_domain)

            if is_cold or is_ai_like:
                reasons = "; ".join(cold_reasons + ai_reasons)
                print(f"[{mode}] flagged: {sender} | {reasons}")

                if live:
                    send_notice_reply(config, message, sender)
                    append_to_blacklist(sender_domain, config.blacklist_file)
                    move_message(imap, uid, config.sales_folder)

        if live:
            imap.expunge()
        imap.logout()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan unread IMAP mail for unsolicited sales outreach."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Perform replies, moves, deletes, and blacklist writes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    process_inbox(load_config(), live=args.live)


if __name__ == "__main__":
    main()
