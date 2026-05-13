"""Human-reviewable warning response templates."""

from __future__ import annotations

WARNING_TEMPLATES: dict[int, str] = {
    1: (
        "Your message appears to be unsolicited outreach. This address is not "
        "monitored for sales pitches. Please remove this address and associated "
        "data from your CRM and cease further contact."
    ),
    2: (
        "This is a second notice. Continued unsolicited contact is not welcome. "
        "Remove this address and associated data from your systems immediately."
    ),
    3: (
        "This is a final notice. Further unsolicited contact after an opt-out "
        "request may be documented for complaint or enforcement review. Remove "
        "this address and stop contacting it."
    ),
}


def warning_template(strike_level: int) -> str:
    if strike_level <= 1:
        return WARNING_TEMPLATES[1]
    if strike_level == 2:
        return WARNING_TEMPLATES[2]
    return WARNING_TEMPLATES[3]
