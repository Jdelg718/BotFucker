"""BotFucker core library."""

from .classifier import classify_message
from .models import ClassificationResult, EmailMessage

__all__ = ["ClassificationResult", "EmailMessage", "classify_message"]
