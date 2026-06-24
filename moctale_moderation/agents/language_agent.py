"""Language detection agent for Moctale Moderation AI."""
from __future__ import annotations

import logging
from typing import Any

from moctale_moderation.patterns import has_devanagari
from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)


class LanguageAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "language"

    async def process(self, payload: AgentPayload) -> AgentResult:
        # Simple language/script detection
        text = payload.request.text
        
        # Check script
        if has_devanagari(text):
            payload.language = "hi_devanagari"
        else:
            # We assume hi_roman / english based on heuristics or let it be 'unknown'
            # For this Phase, we'll label hi_roman if certain tokens exist, otherwise english/mixed.
            # Real implementation could use langdetect here.
            payload.language = "unknown"
            
        return AgentResult(payload=payload, next_agent="heuristic")
