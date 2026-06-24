"""Review queue agent for Moctale Moderation AI.

Enqueues items flagged for human review.
"""
from __future__ import annotations

import logging
from collections import deque

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)

# Simple in-memory queue for phase 3
# In phase 5, this moves to Redis/SQS
_IN_MEMORY_QUEUE = deque(maxlen=1000)

def get_review_queue() -> deque:
    return _IN_MEMORY_QUEUE

class ReviewQueueAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "review_queue"

    async def process(self, payload: AgentPayload) -> AgentResult:
        # We only arrive here if action == flag_for_review
        
        # enqueue the result for human review
        if payload.final_result:
            _IN_MEMORY_QUEUE.append({
                "text": payload.normalized_text,
                "result": getattr(payload.final_result, "model_dump", lambda: getattr(payload.final_result, "__dict__", {}))() if hasattr(payload.final_result, "model_dump") else getattr(payload.final_result, "__dict__", {}),
                "request": getattr(payload.request, "model_dump", lambda: getattr(payload.request, "__dict__", {}))() if hasattr(payload.request, "model_dump") else getattr(payload.request, "__dict__", {})
            })
            log.info("Enqueued item for review. Queue depth: %d", len(_IN_MEMORY_QUEUE))

        return AgentResult(payload=payload, next_agent=None)  # End of pipeline
