"""Multilingual ML scorer for sentiment and toxicity signals.

Provides a fast, multilingual sentiment model (twitter-xlm-roberta)
with automatic fallback to heuristic bag-of-words when the model
is unavailable or times out.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

_MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_LOAD_TIMEOUT_S = 10.0


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Result from the ML sentiment scorer."""
    label: str          # 'positive', 'negative', 'neutral'
    score: float        # confidence in [0, 1]
    source: str         # 'model' or 'heuristic'


class MLScorer:
    """Multilingual sentiment scorer with heuristic fallback.

    Uses cardiffnlp/twitter-xlm-roberta-base-sentiment when available,
    falls back gracefully to heuristic bag-of-words otherwise.

    Usage::

        scorer = MLScorer.build()
        results = scorer.score_batch(["great movie!", "tu chutiya hai"])
    """

    def __init__(self, pipeline: Any | None = None) -> None:
        self._pipeline = pipeline
        self._available = pipeline is not None

    @classmethod
    def build(cls, timeout: float = _LOAD_TIMEOUT_S) -> "MLScorer":
        """Load the ML model (lazy, with timeout guard).

        Returns an MLScorer using the real model if available,
        or a heuristic-only scorer if the model cannot be loaded.
        """
        try:
            import signal

            def _timeout_handler(signum: int, frame: Any) -> None:
                raise TimeoutError("Model load timed out")

            # Only works on Unix — safe fallback on Windows
            try:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(int(timeout))
            except AttributeError:
                pass

            from transformers import pipeline as hf_pipeline
            pipe = hf_pipeline(
                "text-classification",
                model=_MODEL_NAME,
                return_all_scores=False,
                truncation=True,
                max_length=512,
            )
            try:
                signal.alarm(0)  # cancel alarm
            except AttributeError:
                pass
            log.info("MLScorer: model loaded", extra={"model": _MODEL_NAME})
            return cls(pipeline=pipe)
        except Exception as exc:
            log.warning("MLScorer: falling back to heuristic", extra={"reason": str(exc)})
            return cls(pipeline=None)

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        """Score a batch of texts for sentiment.

        Args:
            texts: List of normalized text strings.

        Returns:
            List of SentimentResult, one per input text.
        """
        if not texts:
            return []
        if self._available and self._pipeline is not None:
            try:
                raw = self._pipeline(texts, batch_size=32, truncation=True)
                return [
                    SentimentResult(
                        label=self._map_label(r["label"]),
                        score=round(r["score"], 4),
                        source="model",
                    )
                    for r in raw
                ]
            except Exception as exc:
                log.warning("MLScorer: batch inference failed, using heuristic", extra={"error": str(exc)})
        return [self._heuristic(t) for t in texts]

    def score_one(self, text: str) -> SentimentResult:
        """Score a single text. Convenience wrapper around score_batch."""
        return self.score_batch([text])[0]

    @staticmethod
    def _map_label(raw_label: str) -> str:
        """Map model-specific label strings to canonical labels."""
        label = raw_label.lower()
        if label in ("positive", "pos", "label_2", "2"):
            return "positive"
        if label in ("negative", "neg", "label_0", "0"):
            return "negative"
        return "neutral"

    @staticmethod
    def _heuristic(text: str) -> SentimentResult:
        """Fallback bag-of-words sentiment heuristic."""
        from .patterns import POSITIVE_TERMS, NEGATIVE_TERMS
        tokens = frozenset(text.split())
        pos = sum(1 for t in POSITIVE_TERMS if t in text or t in tokens)
        neg = sum(1 for t in NEGATIVE_TERMS if t in text or t in tokens)
        import math
        raw = neg - pos
        score = 1 / (1 + math.exp(-raw)) if raw else 0.5
        label = "negative" if raw > 0 else ("positive" if raw < 0 else "neutral")
        return SentimentResult(label=label, score=round(score, 3), source="heuristic")


_SCORER_INSTANCE: MLScorer | None = None
_SCORER_LOCK = threading.Lock()


def get_default_scorer() -> MLScorer:
    """Return process-wide MLScorer singleton (heuristic-only, fast startup)."""
    global _SCORER_INSTANCE
    if _SCORER_INSTANCE is None:
        with _SCORER_LOCK:
            if _SCORER_INSTANCE is None:
                _SCORER_INSTANCE = MLScorer(pipeline=None)  # heuristic by default
    return _SCORER_INSTANCE
