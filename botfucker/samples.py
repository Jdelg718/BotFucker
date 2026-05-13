"""Deterministic fake/sample data for the local Phase 2 UI.

All addresses use reserved documentation domains. These records are never
intended to represent real people, real companies, or a connected mailbox.
"""

from __future__ import annotations

from botfucker.review_queue import ReviewItem

RESERVED_SAMPLE_DOMAINS = frozenset({"example.com", "example.net", "example.org"})


def build_sample_review_items() -> list[ReviewItem]:
    """Return deterministic sample review items using only reserved domains."""

    return [
        ReviewItem(
            item_id="sample-001",
            message_id="<sample-001@example.com>",
            thread_id="thread-sample-001",
            from_email="casey.sales@example.com",
            from_name="Casey Sample",
            sender_domain="example.com",
            subject="Quick call to scale your pipeline?",
            snippet="Hi, checking whether you want a 15-minute demo for automated lead generation.",
            received_at="2026-05-13T09:15:00+00:00",
            classification="cold_outreach",
            confidence=0.91,
            recommended_action="warn_1",
            reasons=["Uses quick-call sales framing", "Mentions lead generation demo"],
            sender_strike_level=0,
            draft_reply="Mock warning draft: Please stop sending unsolicited sales outreach.",
        ),
        ReviewItem(
            item_id="sample-002",
            message_id="<sample-002@example.net>",
            thread_id="thread-sample-002",
            from_email="robin.sequence@example.net",
            from_name="Robin Followup",
            sender_domain="example.net",
            subject="Re: wondering if you saw my last note",
            snippet="Just bumping this to the top of your inbox in case now is a better time.",
            received_at="2026-05-13T08:40:00+00:00",
            classification="crm_followup",
            confidence=0.86,
            recommended_action="warn_2",
            reasons=["CRM-style bump language", "Repeated follow-up pattern"],
            sender_strike_level=1,
            draft_reply="Mock warning draft: Continued unsolicited follow-ups are not welcome.",
        ),
        ReviewItem(
            item_id="sample-003",
            message_id="<sample-003@example.org>",
            thread_id="thread-sample-003",
            from_email="newsletter@example.org",
            from_name="Example Org Updates",
            sender_domain="example.org",
            subject="Weekly product digest",
            snippet="This week in the sample digest: product notes, release highlights, and unsubscribe links.",
            received_at="2026-05-12T18:05:00+00:00",
            classification="newsletter",
            confidence=0.78,
            recommended_action="review",
            reasons=["Contains newsletter-style digest language", "Includes unsubscribe framing"],
            sender_strike_level=0,
            draft_reply="",
        ),
        ReviewItem(
            item_id="sample-004",
            message_id="<sample-004@example.com>",
            thread_id="thread-sample-004",
            from_email="growthbot@example.com",
            from_name="Growth Bot Sample",
            sender_domain="example.com",
            subject="Unlock measurable results",
            snippet="Our tailored solutions help teams streamline operations and drive measurable results.",
            received_at="2026-05-12T16:30:00+00:00",
            classification="ai_generated_pitch",
            confidence=0.88,
            recommended_action="warn_3",
            reasons=["Generic AI-pitch phrasing", "Vague value proposition"],
            sender_strike_level=2,
            draft_reply="Mock warning draft: This generic automated pitch is not welcome.",
        ),
    ]
