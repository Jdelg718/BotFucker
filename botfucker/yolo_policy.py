"""Guardrails for any future BotFucker YOLO/live provider actions.

This module is deliberately boring. Boring is good here. Exciting live-mail
mutation code is how products become apology threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ClassificationResult

YOLO_CONFIRMATION_PHRASE = "I ACCEPT BOTFUCKER YOLO RISK"
DEFAULT_ALLOWED_ACTIONS = frozenset({"send_warning", "move_to_sales"})
DEFAULT_ALLOWED_CLASSIFICATIONS = frozenset({"cold_outreach", "ai_generated_pitch", "crm_followup"})


@dataclass(frozen=True)
class YoloPolicy:
    enabled: bool = False
    emergency_stop: bool = False
    confirmation_phrase: str = ""
    allowed_actions: set[str] = field(default_factory=lambda: set(DEFAULT_ALLOWED_ACTIONS))
    allowed_classifications: set[str] = field(default_factory=lambda: set(DEFAULT_ALLOWED_CLASSIFICATIONS))
    min_confidence: float = 0.9
    daily_action_limit: int = 0
    reply_tone: str = "firm_professional"


@dataclass(frozen=True)
class YoloDecision:
    allowed: bool
    reasons: list[str]


def evaluate_yolo_decision(
    policy: YoloPolicy,
    *,
    classification: ClassificationResult,
    provider_action: str,
    daily_action_count: int,
) -> YoloDecision:
    """Return whether a live provider action passes YOLO safety gates."""

    reasons: list[str] = []

    if policy.emergency_stop:
        reasons.append("YOLO emergency stop is active")

    if not policy.enabled:
        reasons.append("YOLO mode is disabled")

    if policy.confirmation_phrase != YOLO_CONFIRMATION_PHRASE:
        reasons.append("missing exact YOLO confirmation phrase")

    if provider_action not in policy.allowed_actions:
        reasons.append(f"provider action {provider_action} is not allowlisted")

    if classification.classification not in policy.allowed_classifications:
        reasons.append(f"classification {classification.classification} is not allowlisted")

    if classification.confidence < policy.min_confidence:
        reasons.append(f"confidence {classification.confidence:.3f} is below minimum {policy.min_confidence:.3f}")

    if policy.daily_action_limit <= 0 or daily_action_count >= policy.daily_action_limit:
        reasons.append("daily YOLO action limit reached")

    if policy.reply_tone not in {"firm_professional", "neutral", "minimal"}:
        reasons.append("reply tone is not allowlisted")

    if reasons:
        return YoloDecision(False, reasons)

    return YoloDecision(True, ["all YOLO guardrails passed"])
