"""Deterministic classifier for v2 core."""

from __future__ import annotations

import re

from .models import ClassificationResult, EmailMessage

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

NEWSLETTER_PATTERNS = [
    r"\bunsubscribe\b",
    r"\bmanage (?:your )?preferences\b",
    r"\bview (?:this )?(?:email|message) in (?:your )?browser\b",
]

SAFE_RELATIONSHIP_PATTERNS = [
    r"\binvoice\b",
    r"\breceipt\b",
    r"\bsupport ticket\b",
    r"\border confirmation\b",
]


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
        return ClassificationResult("known_offender", 0.97, action, ["sender/domain is blacklisted or above strike threshold"])

    newsletter_reasons = _matches(NEWSLETTER_PATTERNS, text, "newsletter marker")
    if newsletter_reasons and not _has_direct_sales_ask(text):
        return ClassificationResult("newsletter", 0.82, "review", newsletter_reasons)

    safe_reasons = _matches(SAFE_RELATIONSHIP_PATTERNS, text, "transactional/safe marker")
    if safe_reasons and not _has_direct_sales_ask(text):
        return ClassificationResult("safe", 0.78, "none", safe_reasons)

    cold_reasons = _cold_outreach_reasons(text)
    ai_reasons = _ai_generated_reasons(text, message.sender_domain)

    if ai_reasons and len(ai_reasons) >= 2 and len(ai_reasons) >= len(cold_reasons):
        confidence = min(0.9, 0.55 + (0.08 * len(ai_reasons)))
        return ClassificationResult("ai_generated_pitch", confidence, _action_for_strike(strike_level + 1), ai_reasons + cold_reasons)

    if cold_reasons:
        classification = "crm_followup" if any("follow" in reason or "checking in" in reason for reason in cold_reasons) else "cold_outreach"
        reasons = cold_reasons + ai_reasons
        confidence = min(0.96, 0.62 + (0.08 * len(reasons)))
        return ClassificationResult(classification, confidence, _action_for_strike(strike_level + 1), reasons)

    return ClassificationResult("unknown_review_needed", 0.35, "review", ["no deterministic outreach rule matched"])


def _matches(patterns: list[str], text: str, label: str) -> list[str]:
    return [f"{label}: {pattern}" for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def _cold_outreach_reasons(text: str) -> list[str]:
    reasons = _matches(COLD_OUTREACH_PATTERNS, text, "cold outreach phrase")

    words = re.findall(r"\b[a-z']+\b", text)
    if words:
        first_person_count = sum(1 for word in words if word in {"i", "i'm", "my", "mine", "me"})
        solutions_count = sum(1 for word in words if word in {"solution", "solutions"})
        first_person_ratio = first_person_count / len(words)

        if first_person_ratio > 0.035 and first_person_count >= 6:
            reasons.append("high first-person language frequency")

        if solutions_count >= 2:
            reasons.append("repeated solution/solutions wording")

    return reasons


def _ai_generated_reasons(text: str, sender_domain: str) -> list[str]:
    reasons = _matches(AI_SIGNATURE_PATTERNS, text, "generic AI-like phrase")

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
        reasons.append("overly formal email structure")
    if has_generic_value_prop:
        reasons.append("generic value proposition wording")
    if lacks_specific_reference:
        reasons.append("no specific personal or business reference detected")

    return reasons


def _has_direct_sales_ask(text: str) -> bool:
    return bool(re.search(r"\b(book|schedule|hop on|quick call|demo|meeting)\b", text))


def _action_for_strike(strike: int) -> str:
    if strike <= 1:
        return "warn_1"
    if strike == 2:
        return "warn_2"
    if strike == 3:
        return "warn_3"
    return "block_candidate"
