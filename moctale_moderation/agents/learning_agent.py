"""Learning agent for Moctale Moderation AI.

Persists human moderator feedback to logs/feedback.jsonl.
Not in the real-time inference pipeline — called directly by the /feedback endpoint.
Use scripts/train_weights.py to analyze feedback and update risk_weights.yaml.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)

_FEEDBACK_LOG = Path("logs/feedback.jsonl")
_WRITE_LOCK = threading.Lock()


class LearningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "learning"

    async def process(self, payload: AgentPayload) -> AgentResult:
        # Not used in the real-time pipeline. Call record_feedback() directly.
        return AgentResult(payload=payload, next_agent=None)

    @staticmethod
    def record_feedback(
        text_hash: str,
        human_action: str,
        moderator_id: str = "anonymous",
    ) -> None:
        """Persist a moderator correction to logs/feedback.jsonl.

        Args:
            text_hash: SHA-256 hash of the original comment text.
            human_action: Corrected action (allow/flag_for_review/flag_for_removal).
            moderator_id: Identifier for the moderator (default: anonymous).
        """
        entry = {
            "timestamp": time.time(),
            "text_hash": text_hash,
            "human_action": human_action,
            "moderator_id": moderator_id,
        }
        try:
            _FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _WRITE_LOCK:
                with _FEEDBACK_LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            log.info(
                "Feedback recorded",
                extra={"text_hash": text_hash[:8], "human_action": human_action},
            )
        except Exception as exc:
            log.error("Failed to persist feedback: %s", exc)
