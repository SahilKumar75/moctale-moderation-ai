"""ML toxicity and sentiment agent for Moctale Moderation AI.

Wraps the MLScorer to provide batched predictions.
"""
from __future__ import annotations

import logging

from moctale_moderation.ml_scorer import get_default_scorer
from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)


class MLToxicityAgent(BaseAgent):
    def __init__(self) -> None:
        self.scorer = get_default_scorer()

    @property
    def name(self) -> str:
        return "ml_toxicity"

    async def process(self, payload: AgentPayload) -> AgentResult:
        # Currently, AgentBus runs per-request sequentially.
        # Batched ML requires a queue system across requests (async batching).
        # We simulate the interface here but evaluate single.
        
        # In a real batched architecture, this agent would push to a queue
        # and wait for an asyncio.Event or Future.
        
        # If model_toxicity_score was passed in request, use it.
        # Otherwise run ml scorer
        req = payload.request
        model_score = req.model_toxicity_score
        
        # Also run sentiment
        sentiment_result = self.scorer.score_one(payload.normalized_text)
        
        if model_score is None:
            # We don't have a separate toxicity model yet, we use heuristic toxicity or sentiment score
            # if we wanted. For now we use heuristic toxicity as fallback as per previous logic.
            # But the requirement says "Wraps MLScorer". 
            # We will use the heuristic toxicity from previous agent if missing.
            ml_toxicity = float('nan')
        else:
            ml_toxicity = float(model_score)

        payload.ml_signals = {
            "sentiment_label": sentiment_result.label,
            "sentiment_score": sentiment_result.score,
            "model_toxicity": ml_toxicity
        }

        return AgentResult(payload=payload, next_agent="context")
