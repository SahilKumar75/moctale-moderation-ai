from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ModerationAction(str, Enum):
    ALLOW = "allow"
    FLAG_FOR_REVIEW = "flag_for_review"
    FLAG_FOR_REMOVAL = "flag_for_removal"


class ContextType(str, Enum):
    MAIN_REVIEW = "main_review"
    REPLY_TO_REVIEW = "reply_to_review"
    REPLY_TO_COMMENT = "reply_to_comment"
    TOPIC_FEED = "topic_feed"


@dataclass(frozen=True, slots=True)
class ModerationRequest:
    text: str
    context_type: str = ContextType.REPLY_TO_REVIEW.value
    parent_review_rating: str = "Skip"
    movie_rating_perfection_pct: float = 90.0
    movie_rating_skip_pct: float = 5.0
    model_toxicity_score: float | None = None


@dataclass(frozen=True, slots=True)
class ModerationResult:
    predicted_action: str
    predicted_category: str
    predicted_intent: str
    predicted_severity: str
    target_detected_pred: str
    sentiment_label: str
    sentiment_score: float
    risk_score: float
    heuristic_toxicity_score: float
    model_toxicity_score: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reason_codes"] = list(self.reason_codes)
        return data
