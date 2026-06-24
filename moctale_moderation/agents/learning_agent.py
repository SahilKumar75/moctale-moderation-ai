"""Learning agent for Moctale Moderation AI.

Receives feedback and updates risk weights.
"""
from __future__ import annotations

import logging

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)


class LearningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "learning"

    async def process(self, payload: AgentPayload) -> AgentResult:
        # Currently, feedback processing logic is not in the real-time inference loop.
        # This agent can act as a trigger or run asynchronously to update the YAML,
        # but for the main pipeline, we do nothing or log.
        log.info("Learning agent received feedback payload.")
        return AgentResult(payload=payload, next_agent=None)
