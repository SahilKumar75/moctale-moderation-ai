"""CPU-light, thread-safe moderation policy engine for Moctale.

This module provides the core ModerationEngine which orchestrates the AgentBus.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import namedtuple
from collections.abc import Iterable

from moctale_moderation.agents import AgentBus
from moctale_moderation.agents.context_agent import ContextAgent
from moctale_moderation.agents.heuristic_agent import HeuristicAgent
from moctale_moderation.agents.intake_agent import IntakeAgent
from moctale_moderation.agents.language_agent import LanguageAgent
from moctale_moderation.agents.learning_agent import LearningAgent
from moctale_moderation.agents.ml_toxicity_agent import MLToxicityAgent
from moctale_moderation.agents.policy_agent import PolicyAgent
from moctale_moderation.agents.review_queue_agent import ReviewQueueAgent
from moctale_moderation.patterns import (
    MENTION_RE,
    MENTION_TOKEN,
    NON_TOKEN_RE,
    OBFUSCATED_FUCK_RE,
    OBFUSCATED_SHIT_RE,
    REPEATED_CHAR_RE,
    SPACE_RE,
    SPLIT_WORD_RE,
    SYMBOL_TRANSLATION,
    TOKEN_RE,
    transliterate_devanagari,
    unicode_normalize,
)
from moctale_moderation.schemas import ModerationRequest, ModerationResult

log = logging.getLogger(__name__)

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])


class ModerationEngine:
    """CPU-light, thread-safe moderation policy engine."""

    def __init__(self, cache_size: int = 8192) -> None:
        self._cache_ref: object | None = None  # set by service after ModerationCache init
        self._bus = AgentBus()
        self._bus.register(IntakeAgent())
        self._bus.register(LanguageAgent())
        self._bus.register(HeuristicAgent())
        self._bus.register(MLToxicityAgent())
        self._bus.register(ContextAgent())
        self._bus.register(PolicyAgent())
        self._bus.register(ReviewQueueAgent())
        self._bus.register(LearningAgent())
        log.info("ModerationEngine initialized with AgentBus")

    def analyze(self, request: ModerationRequest | str, **kwargs: object) -> ModerationResult:
        if isinstance(request, str):
            request = ModerationRequest(text=request, **kwargs)
            
        t0 = time.perf_counter()
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            raise RuntimeError(
                "analyze() called from a running event loop. "
                "Use analyze_many_async() instead."
            )
            
        result = asyncio.run(self._bus.run_pipeline(request))

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        _log_decision(
            action=result.predicted_action,
            category=result.predicted_category,
            severity=result.predicted_severity,
            risk_score=result.risk_score,
            latency_ms=latency_ms,
            reason_codes=result.reason_codes,
            context_type=request.context_type,
        )
        return result

    def analyze_many(self, requests: Iterable[ModerationRequest | str]) -> list[ModerationResult]:
        return [self.analyze(request) for request in requests]

    async def analyze_many_async(
        self,
        requests: Iterable[ModerationRequest | str],
        *,
        concurrency: int = 256,
    ) -> list[ModerationResult]:
        semaphore = asyncio.Semaphore(concurrency)

        async def run_one(request: ModerationRequest | str) -> ModerationResult:
            if isinstance(request, str):
                request = ModerationRequest(text=request)
            async with semaphore:
                t0 = time.perf_counter()
                result = await self._bus.run_pipeline(request)
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                _log_decision(
                    action=result.predicted_action,
                    category=result.predicted_category,
                    severity=result.predicted_severity,
                    risk_score=result.risk_score,
                    latency_ms=latency_ms,
                    reason_codes=result.reason_codes,
                    context_type=request.context_type,
                )
                return result

        return list(await asyncio.gather(*(run_one(r) for r in requests)))

    def set_cache(self, cache: object) -> None:
        """Wire an external ModerationCache so cache_info() returns real counters."""
        self._cache_ref = cache

    def cache_info(self) -> _CacheInfo:
        if self._cache_ref is not None:
            return _CacheInfo(
                hits=getattr(self._cache_ref, "hits", 0),
                misses=getattr(self._cache_ref, "misses", 0),
                maxsize=8192,
                currsize=0,
            )
        return _CacheInfo(hits=0, misses=0, maxsize=8192, currsize=0)


def normalize_text(text: str) -> str:
    value = unicode_normalize(str(text))
    value = transliterate_devanagari(value)
    value = value.lower()
    value = MENTION_RE.sub(f" {MENTION_TOKEN} ", value)
    value = REPEATED_CHAR_RE.sub(r"\1\1", value)
    value = value.translate(SYMBOL_TRANSLATION)
    value = SPLIT_WORD_RE.sub(
        lambda match: SPACE_RE.sub("", NON_TOKEN_RE.sub(" ", match.group(0))), value
    )
    value = OBFUSCATED_SHIT_RE.sub("shit", value)
    value = OBFUSCATED_FUCK_RE.sub("fuck", value)
    value = NON_TOKEN_RE.sub(" ", value)
    return SPACE_RE.sub(" ", value).strip()


def token_set(text: str) -> frozenset[str]:
    return frozenset(TOKEN_RE.findall(text))


def _log_decision(
    *,
    action: str,
    category: str,
    severity: str,
    risk_score: float,
    latency_ms: float,
    reason_codes: tuple[str, ...] | list[str],
    context_type: str,
) -> None:
    extra = {
        "action": action,
        "category": category,
        "severity": severity,
        "risk_score": risk_score,
        "latency_ms": latency_ms,
        "reason_codes": list(reason_codes),
        "context_type": context_type,
    }
    if action == "flag_for_removal":
        log.warning("Content flagged for removal", extra=extra)
    elif action == "flag_for_review":
        log.info("Content flagged for review", extra=extra)
    else:
        log.debug("Content allowed", extra=extra)


_DEFAULT_ENGINE: ModerationEngine | None = None
_DEFAULT_ENGINE_LOCK = threading.Lock()


def get_default_engine() -> ModerationEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        with _DEFAULT_ENGINE_LOCK:
            if _DEFAULT_ENGINE is None:
                _DEFAULT_ENGINE = ModerationEngine()
    return _DEFAULT_ENGINE
