"""Deterministic classifier for v2 core."""

from __future__ import annotations

import re

from .models import ClassificationResult, EmailMessage

PatternReason = tuple[str, str]

COLD_OUTREACH_PATTERNS: list[PatternReason] = [
    (r"\bquick call\b", "asks for a quick call"),
    (r"\bscale your business\b", "uses generic business-scaling pitch language"),
    (r"\bwondering if you saw my last\b", "uses common CRM follow-up wording"),
    (r"\bfollow(?:ing)? up\b", "uses follow-up wording"),
    (r"\bjust checking in\b", "uses common CRM check-in wording"),
    (r"\bbook (?:a )?(?:call|demo|meeting)\b", "asks to book a sales call or demo"),
    (r"\b15[- ]?minute\b", "mentions a short sales-call time slot"),
    (r"\bvalue proposition\b", "uses generic value-proposition language"),
    (r"\bgrowth strategy\b", "uses generic growth-strategy pitch language"),
    (r"\blead generation\b", "mentions lead generation"),
    (r"\bcrm\b", "mentions CRM tooling or follow-up workflow"),
    (r"\bsales pipeline\b", "mentions a sales pipeline"),
    (r"\bdecision maker\b", "mentions finding or reaching a decision maker"),
]

AI_SIGNATURE_PATTERNS: list[PatternReason] = [
    (r"\bi hope this (?:email|message) finds you well\b", "uses generic AI-like greeting"),
    (r"\bin today's (?:competitive|fast[- ]paced) landscape\b", "uses generic market-landscape framing"),
    (r"\btailored solutions\b", "uses generic tailored-solutions wording"),
    (r"\bunlock (?:growth|potential|efficiency)\b", "uses generic unlock-growth wording"),
    (r"\bdrive measurable results\b", "uses generic measurable-results wording"),
    (r"\bstreamline your operations\b", "uses generic streamline-operations wording"),
    (r"\btransform your business\b", "uses generic business-transformation wording"),
    (r"\bpersonalized strategy\b", "uses generic personalized-strategy wording"),
    (r"\bgeneric value proposition\b", "mentions a generic value proposition"),
]

NEWSLETTER_PATTERNS: list[PatternReason] = [
    (r"\bunsubscribe\b", "contains unsubscribe language"),
    (r"\bmanage (?:your )?preferences\b", "contains email-preferences language"),
    (r"\bview (?:this )?(?:email|message) in (?:your )?browser\b", "contains view-in-browser language"),
]

SAFE_RELATIONSHIP_PATTERNS: list[PatternReason] = [
    (r"\binvoice\b", "contains invoice language"),
    (r"\breceipt\b", "contains receipt language"),
    (r"\bsupport ticket\b", "contains support-ticket language"),
    (r"\border confirmation\b", "contains order-confirmation language"),
]

CUSTOMER_OR_PARTNER_PATTERNS: list[PatternReason] = [
    (r"\bexisting (?:customer|client|partner)\b", "references an existing customer or partner relationship"),
    (r"\bcurrent (?:customer|client|partner)\b", "references a current customer or partner relationship"),
    (r"\bour (?:contract|agreement|project|account)\b", "references an existing business relationship"),
]

SALES_CONTEXT_RE = re.compile(
    r"\b(sales|sell|demo|pitch|proposal|lead generation|crm|pipeline|growth|marketing|prospect|vendor|solution|solutions|offer)\b",
    flags=re.IGNORECASE,
)
SALES_ASK_RE = re.compile(
    r"\b(quick call|book (?:a )?(?:call|demo|meeting)|schedule (?:a )?(?:call|demo|meeting)|hop on (?:a )?call|see (?:a )?demo)\b",
    flags=re.IGNORECASE,
)


def classify_message(
    message: EmailMessage,
    *,
    known_offender: bool = False,
    whitelisted: bool = False,
    strike_level: int = 0,
) -> ClassificationResult:
    """Classify one normalized message.

    Email body text is untrusted content. This function only pattern-matches it;
    it does not execute instructions or call external services.
    """

    text = f"{message.subject}\n{message.body_text}".lower()

    if whitelisted:
        return ClassificationResult("safe", 0.99, "none", ["sender is whitelisted"])

    if known_offender:
        action = _action_for_strike(max(strike_level, 1))
        return ClassificationResult("known_offender", 0.97, action, ["sender or domain is already flagged in history"])

    newsletter_reasons = _matches(NEWSLETTER_PATTERNS, text)
    if newsletter_reasons and not _has_direct_sales_ask(text):
        return ClassificationResult("newsletter", 0.82, "review", newsletter_reasons)

    customer_reasons = _matches(CUSTOMER_OR_PARTNER_PATTERNS, text)
    if customer_reasons and not _has_direct_sales_ask(text):
        return ClassificationResult("customer_or_partner", 0.78, "review", customer_reasons)

    safe_reasons = _matches(SAFE_RELATIONSHIP_PATTERNS, text)
    if safe_reasons and not _has_direct_sales_ask(text):
        return ClassificationResult("safe", 0.78, "none", safe_reasons)

    cold_reasons = _cold_outreach_reasons(text)
    ai_reasons = _ai_generated_reasons(text, message.sender_domain)

    if ai_reasons and len(ai_reasons) >= 2 and len(ai_reasons) >= len(cold_reasons):
        confidence = min(0.9, 0.55 + (0.08 * len(ai_reasons)))
        return ClassificationResult("ai_generated_pitch", confidence, _action_for_strike(strike_level + 1), ai_reasons + cold_reasons)

    if cold_reasons:
        classification = "crm_followup" if any("follow" in reason or "check-in" in reason for reason in cold_reasons) else "cold_outreach"
        reasons = cold_reasons + ai_reasons
        confidence = min(0.96, 0.62 + (0.08 * len(reasons)))
        return ClassificationResult(classification, confidence, _action_for_strike(strike_level + 1), reasons)

    return ClassificationResult("unknown_review_needed", 0.35, "review", ["no deterministic outreach rule matched"])


def _matches(patterns: list[PatternReason], text: str) -> list[str]:
    return [reason for pattern, reason in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def _cold_outreach_reasons(text: str) -> list[str]:
    reasons = _matches(COLD_OUTREACH_PATTERNS, text)

    words = re.findall(r"\b[a-z']+\b", text)
    if words:
        first_person_count = sum(1 for word in words if word in {"i", "i'm", "my", "mine", "me"})
        solutions_count = sum(1 for word in words if word in {"solution", "solutions"})
        first_person_ratio = first_person_count / len(words)

        if first_person_ratio > 0.035 and first_person_count >= 6 and _has_direct_sales_ask(text):
            reasons.append("high first-person sales-ask language frequency")

        if solutions_count >= 2 and _has_direct_sales_ask(text):
            reasons.append("repeated solution wording near a sales ask")

    return reasons


def _ai_generated_reasons(text: str, sender_domain: str) -> list[str]:
    reasons = _matches(AI_SIGNATURE_PATTERNS, text)

    has_formal_structure = bool(
        re.search(r"\b(dear|hello|hi)\b.{0,80}\n", text)
        and re.search(r"\b(best regards|warm regards|sincerely|kind regards)\b", text)
    )
    has_generic_value_prop = bool(
        re.search(r"\b(help|enable|empower)\b.{0,80}\b(grow|scale|optimize|streamline|automate)\b", text)
    )
    lacks_specific_reference = sender_domain not in text and not re.search(
        r"\b(your recent|your article|your post|your team at|your work on)\b",
        text,
    )

    if has_formal_structure:
        reasons.append("uses overly formal email structure")
    if has_generic_value_prop:
        reasons.append("uses generic value-proposition wording")
    if lacks_specific_reference:
        reasons.append("does not include a specific personal or business reference")

    return reasons


def _has_direct_sales_ask(text: str) -> bool:
    if SALES_ASK_RE.search(text):
        return True

    has_meeting_word = re.search(r"\b(book|schedule|meeting|demo)\b", text, flags=re.IGNORECASE)
    return bool(has_meeting_word and SALES_CONTEXT_RE.search(text))


def _action_for_strike(strike: int) -> str:
    if strike <= 0:
        return "review"
    if strike == 1:
        return "warn_1"
    if strike == 2:
        return "warn_2"
    if strike == 3:
        return "warn_3"
    return "block_candidate"
