"""Intake agent for Moctale Moderation AI.

Responsible for Unicode normalization, transliteration, and tokenization.
"""
from __future__ import annotations

import logging

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)

class IntakeAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "intake"

    async def process(self, payload: AgentPayload) -> AgentResult:
        from moctale_moderation.engine import normalize_text, token_set
        # Normalize and tokenize text
        text = payload.request.text
        normalized = normalize_text(text)
        tokens = token_set(normalized)

        payload.normalized_text = normalized
        payload.tokens = tokens

        # Route to language detection agent
        return AgentResult(payload=payload, next_agent="language")
