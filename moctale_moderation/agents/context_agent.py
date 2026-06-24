"""Context agent for Moctale Moderation AI.

Extracts context signals from the request and prepares for policy.
"""
from __future__ import annotations

import logging

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)


class ContextAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "context"

    def rating_disagreement_risk(self, parent_review_rating: str, perfection_pct: float, skip_pct: float) -> float:
        rating = str(parent_review_rating).lower()
        if rating == "skip" and perfection_pct >= 80:
            return 0.25
        if rating == "perfection" and skip_pct >= 35:
            return 0.15
        return 0.0

    async def process(self, payload: AgentPayload) -> AgentResult:
        req = payload.request
        disagreement = self.rating_disagreement_risk(
            req.parent_review_rating,
            float(req.movie_rating_perfection_pct),
            float(req.movie_rating_skip_pct),
        )

        payload.context_signals = {
            "context_type": req.context_type,
            "disagreement_risk": disagreement,
        }

        return AgentResult(payload=payload, next_agent="policy")
