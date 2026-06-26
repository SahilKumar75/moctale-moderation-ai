"""Heuristic agent for Moctale Moderation AI."""
from __future__ import annotations

import logging

from moctale_moderation.patterns import (
    COMMUNITY_TERMS,
    DIRECTED_ATTACK_PHRASES,
    GROUP_TARGET_PHRASES,
    MENTION_TOKEN,
    MOVIE_TERMS,
    PROFANITY,
    PROTECTED_ABUSE_PHRASES,
    SEVERE_ABUSE,
    SOFT_ABUSE,
    THREAT_TERMS,
    USER_TERMS,
    PhraseMatcher,
)

from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)


class HeuristicAgent(BaseAgent):
    def __init__(self) -> None:
        self._group_targets = PhraseMatcher.build(GROUP_TARGET_PHRASES)
        self._directed_attacks = PhraseMatcher.build(DIRECTED_ATTACK_PHRASES)
        self._protected_abuse = PhraseMatcher.build(PROTECTED_ABUSE_PHRASES)
        self._soft_abuse = PhraseMatcher.build(SOFT_ABUSE)
        self._severe_abuse = PhraseMatcher.build(SEVERE_ABUSE)
        self._threats = PhraseMatcher.build(THREAT_TERMS)
        self._profanity = PhraseMatcher.build(PROFANITY)

    @property
    def name(self) -> str:
        return "heuristic"

    def _contains_any(self, text: str, tokens: frozenset[str], terms: frozenset[str]) -> bool:
        return bool(tokens & terms) or any(term in text for term in terms if " " in term)

    def detect_target(self, text: str, tokens: frozenset[str], context_type: str = "reply_to_review") -> str:
        has_user = MENTION_TOKEN in tokens or bool(tokens & USER_TERMS)
        has_movie = bool(tokens & MOVIE_TERMS)

        if self._protected_abuse.contains(text, tokens):
            return "protected_class"

        if tokens & COMMUNITY_TERMS:
            if self._contains_any(text, tokens, frozenset({"disgusting", "leave", "hate", "dirty", "cheap", "identity"})):
                return "protected_class"
            return "review_content"

        if self._group_targets.contains(text, tokens):
            return "community_identity"

        if self._directed_attacks.contains(text, tokens):
            return "reviewer_or_user"

        REPLY_CONTEXTS = frozenset({"reply_to_review", "reply_to_comment"})
        if context_type in REPLY_CONTEXTS and self._severe_abuse.contains(text, tokens):
            return "reviewer_or_user"

        if has_user and (
            self._soft_abuse.contains(text, tokens)
            or self._severe_abuse.contains(text, tokens)
            or self._threats.contains(text, tokens)
        ):
            return "reviewer_or_user"

        if has_user and context_type in REPLY_CONTEXTS and not has_movie:
            return "reviewer_or_user"

        if context_type in REPLY_CONTEXTS and self._soft_abuse.contains(text, tokens):
            return "reviewer_or_user"

        if has_movie:
            return "movie_show"

        if self._contains_any(text, tokens, frozenset({"fans", "fanbase", "people in comments", "perfection dene wale", "skip gang"})):
            return "community_identity"

        return "unknown"

    def heuristic_toxicity(self, text: str, tokens: frozenset[str]) -> float:
        score = 0.0
        if self._profanity.contains(text, tokens):
            score += 0.18
        if self._soft_abuse.contains(text, tokens):
            score += 0.35
        if self._directed_attacks.contains(text, tokens):
            score += 0.30
        if self._protected_abuse.contains(text, tokens):
            score += 0.60
        if self._severe_abuse.contains(text, tokens):
            score += 0.65
        if self._threats.contains(text, tokens):
            score += 0.75
        return round(min(score, 1.0), 3)

    async def process(self, payload: AgentPayload) -> AgentResult:
        text = payload.normalized_text
        tokens = payload.tokens

        payload.heuristic_signals = {
            "has_mention": MENTION_TOKEN in tokens,
            "severe": self._severe_abuse.contains(text, tokens),
            "threat": self._threats.contains(text, tokens),
            "soft": self._soft_abuse.contains(text, tokens),
            "profanity": self._profanity.contains(text, tokens),
            "directed_attack": self._directed_attacks.contains(text, tokens),
            "protected_abuse": self._protected_abuse.contains(text, tokens),
            "target": self.detect_target(text, tokens, payload.request.context_type),
            "toxicity": self.heuristic_toxicity(text, tokens),
        }

        return AgentResult(payload=payload, next_agent="ml_toxicity")
