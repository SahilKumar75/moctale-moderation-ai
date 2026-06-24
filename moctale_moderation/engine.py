"""CPU-light, thread-safe moderation policy engine for Moctale.

This module provides the core ModerationEngine which orchestrates:
- Text normalization (Unicode, Devanagari, homoglyphs)
- Pattern-based heuristic scoring
- Sentiment signal detection
- Risk score computation
- Action decision logic
- Structured logging of every decision
"""
from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from functools import lru_cache
from typing import Iterable

from .patterns import (
    COMMUNITY_TERMS,
    DIRECTED_ATTACK_PHRASES,
    GROUP_TARGET_PHRASES,
    MENTION_TOKEN,
    MENTION_RE,
    MOVIE_TERMS,
    NEGATIVE_TERMS,
    NON_TOKEN_RE,
    OBFUSCATED_FUCK_RE,
    OBFUSCATED_SHIT_RE,
    POSITIVE_TERMS,
    PROFANITY,
    PROTECTED_ABUSE_PHRASES,
    REPEATED_CHAR_RE,
    SEVERE_ABUSE,
    SOFT_ABUSE,
    SPACE_RE,
    SPLIT_WORD_RE,
    SYMBOL_TRANSLATION,
    THREAT_TERMS,
    TOKEN_RE,
    USER_TERMS,
    PhraseMatcher,
    transliterate_devanagari,
    unicode_normalize,
)
from .schemas import ModerationRequest, ModerationResult

log = logging.getLogger(__name__)

REPLY_CONTEXTS = frozenset({"reply_to_review", "reply_to_comment"})
PERSON_OR_GROUP_TARGETS = frozenset({"reviewer_or_user", "community_identity", "protected_class"})
CONTENT_TARGETS = frozenset({"movie_show", "actor_public_work", "review_content"})


class ModerationEngine:
    """CPU-light, thread-safe moderation policy engine.

    The engine keeps all heavyweight state immutable and shared: compiled regexes,
    phrase indexes, and cached pure policy decisions. One warm process can safely
    reuse a single instance across many concurrent requests.

    Usage::

        engine = ModerationEngine()
        result = engine.analyze("@reviewer tu chutiya hai")
        print(result.predicted_action)  # 'flag_for_removal'
    """

    def __init__(self, cache_size: int = 8192) -> None:
        """Initialise the engine and build all phrase indexes.

        Args:
            cache_size: Maximum number of entries in the LRU decision cache.
        """
        self._group_targets = PhraseMatcher.build(GROUP_TARGET_PHRASES)
        self._directed_attacks = PhraseMatcher.build(DIRECTED_ATTACK_PHRASES)
        self._protected_abuse = PhraseMatcher.build(PROTECTED_ABUSE_PHRASES)
        self._soft_abuse = PhraseMatcher.build(SOFT_ABUSE)
        self._severe_abuse = PhraseMatcher.build(SEVERE_ABUSE)
        self._threats = PhraseMatcher.build(THREAT_TERMS)
        self._profanity = PhraseMatcher.build(PROFANITY)
        self._analyze_cached = lru_cache(maxsize=cache_size)(self._analyze_uncached)
        log.info("ModerationEngine initialised", extra={"cache_size": cache_size})

    def analyze(self, request: ModerationRequest | str, **kwargs: object) -> ModerationResult:
        """Analyze a single moderation request.

        Args:
            request: A ModerationRequest or raw text string.
            **kwargs: If request is a string, these are passed to ModerationRequest.

        Returns:
            A ModerationResult with action, category, severity, scores, and reason.
        """
        if isinstance(request, str):
            request = ModerationRequest(text=request, **kwargs)
        model_score = (
            None
            if request.model_toxicity_score is None
            else round(float(request.model_toxicity_score), 4)
        )
        return self._analyze_cached(
            request.text,
            request.context_type,
            request.parent_review_rating,
            float(request.movie_rating_perfection_pct),
            float(request.movie_rating_skip_pct),
            model_score,
        )

    def analyze_many(
        self, requests: Iterable[ModerationRequest | str]
    ) -> list[ModerationResult]:
        """Analyze multiple requests synchronously, preserving order.

        Args:
            requests: Iterable of requests or strings.

        Returns:
            List of ModerationResult in the same order as input.
        """
        return [self.analyze(request) for request in requests]

    async def analyze_many_async(
        self,
        requests: Iterable[ModerationRequest | str],
        *,
        concurrency: int = 256,
    ) -> list[ModerationResult]:
        """Analyze multiple requests concurrently using asyncio.

        Args:
            requests: Iterable of requests or strings.
            concurrency: Maximum number of concurrent analyses.

        Returns:
            List of ModerationResult in the same order as input.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def run_one(request: ModerationRequest | str) -> ModerationResult:
            async with semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.analyze, request)

        return list(await asyncio.gather(*(run_one(r) for r in requests)))

    def cache_info(self) -> object:
        """Return LRU cache statistics."""
        return self._analyze_cached.cache_info()

    def _analyze_uncached(
        self,
        text: str,
        context_type: str,
        parent_review_rating: str,
        perfection_pct: float,
        skip_pct: float,
        model_toxicity_score: float | None,
    ) -> ModerationResult:
        """Core analysis logic (uncached — called by lru_cache wrapper).

        Args:
            text: Raw comment text.
            context_type: Where the comment appears (e.g. 'reply_to_review').
            parent_review_rating: Rating of the parent review ('Skip'/'Perfection'/etc.).
            perfection_pct: Percentage of 'Perfection' ratings for the movie.
            skip_pct: Percentage of 'Skip' ratings for the movie.
            model_toxicity_score: Optional ML model toxicity score (0–1).

        Returns:
            A fully-populated ModerationResult.
        """
        t0 = time.perf_counter()
        normalized = normalize_text(text)
        tokens = token_set(normalized)
        sentiment_label, sentiment_score = sentiment_signal(normalized, tokens)
        target = self.detect_target(normalized, tokens, context_type=context_type)
        htox = self.heuristic_toxicity(normalized, tokens)
        model_score = (
            htox
            if model_toxicity_score is None or math.isnan(model_toxicity_score)
            else float(model_toxicity_score)
        )
        disagreement = rating_disagreement_risk(parent_review_rating, perfection_pct, skip_pct)

        has_mention = MENTION_TOKEN in tokens
        severe = self._severe_abuse.contains(normalized, tokens)
        threat = self._threats.contains(normalized, tokens)
        soft = self._soft_abuse.contains(normalized, tokens)
        profanity = self._profanity.contains(normalized, tokens)
        directed_attack = self._directed_attacks.contains(normalized, tokens)
        protected_abuse = self._protected_abuse.contains(normalized, tokens)

        risk_score = 0.20 if context_type in REPLY_CONTEXTS else 0.05
        risk_score += 0.15 if has_mention else 0.0
        risk_score += 0.15 if sentiment_label == "negative" else 0.0
        risk_score += disagreement
        risk_score += max(htox, model_score) * 0.45
        risk_score = round(min(risk_score, 1.0), 3)

        reason_codes = build_reason_codes(
            has_mention=has_mention,
            disagreement=disagreement,
            sentiment_label=sentiment_label,
            target=target,
            profanity=profanity,
            soft=soft,
            directed_attack=directed_attack,
            severe=severe,
            threat=threat,
            protected_abuse=protected_abuse,
        )

        action, category, intent, severity = decide_action(
            target=target,
            threat=threat,
            protected_abuse=protected_abuse,
            severe=severe,
            directed_attack=directed_attack,
            soft=soft,
            model_score=model_score,
            risk_score=risk_score,
            sentiment_label=sentiment_label,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        _log_decision(
            action=action,
            category=category,
            severity=severity,
            risk_score=risk_score,
            latency_ms=latency_ms,
            reason_codes=reason_codes,
            context_type=context_type,
        )

        return ModerationResult(
            predicted_action=action,
            predicted_category=category,
            predicted_intent=intent,
            predicted_severity=severity,
            target_detected_pred=target,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            risk_score=risk_score,
            heuristic_toxicity_score=htox,
            model_toxicity_score=round(model_score, 3),
            reason_codes=reason_codes,
            reason=explain(action, target),
        )

    def detect_target(
        self,
        text: str,
        tokens: frozenset[str],
        context_type: str = "reply_to_review",
    ) -> str:
        """Detect what the comment is targeting.

        Args:
            text: Normalized comment text.
            tokens: Token set from the normalized text.
            context_type: Context in which the comment appears.

        Returns:
            One of: 'protected_class', 'community_identity', 'reviewer_or_user',
            'movie_show', 'actor_public_work', 'review_content', 'unknown'.
        """
        has_user = MENTION_TOKEN in tokens or bool(tokens & USER_TERMS)
        has_movie = bool(tokens & MOVIE_TERMS)

        if self._protected_abuse.contains(text, tokens):
            return "protected_class"

        if tokens & COMMUNITY_TERMS:
            if self._contains_any(
                text, tokens, frozenset({"disgusting", "leave", "hate", "dirty", "cheap", "identity"})
            ):
                return "protected_class"
            return "review_content"

        if self._group_targets.contains(text, tokens):
            return "community_identity"

        if self._directed_attacks.contains(text, tokens):
            return "reviewer_or_user"

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

        if self._contains_any(
            text,
            tokens,
            frozenset({"fans", "fanbase", "people in comments", "perfection dene wale", "skip gang"}),
        ):
            return "community_identity"

        return "unknown"

    def heuristic_toxicity(self, text: str, tokens: frozenset[str]) -> float:
        """Compute a heuristic toxicity score in [0, 1].

        Args:
            text: Normalized comment text.
            tokens: Token set from the normalized text.

        Returns:
            Float between 0.0 and 1.0 representing heuristic toxicity.
        """
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

    def _contains_any(
        self, text: str, tokens: frozenset[str], terms: frozenset[str]
    ) -> bool:
        """Return True if any term appears in tokens or (for multi-word terms) in text.

        Args:
            text: Normalized text for substring search of multi-word terms.
            tokens: Token set for single-word O(1) lookup.
            terms: Set of terms to check.

        Returns:
            True if at least one term matches.
        """
        return bool(tokens & terms) or any(term in text for term in terms if " " in term)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normalize text for pattern matching.

    Steps applied in order:
    1. Unicode NFKC normalization (collapses compatibility characters)
    2. Zero-width character stripping
    3. Cyrillic/Greek confusable mapping
    4. Devanagari → Roman transliteration
    5. Lowercasing
    6. Mention replacement (@user → usermention)
    7. Repeated character collapsing (aaaaaa → aa)
    8. Symbol-to-letter substitution (@ → a, $ → s, etc.)
    9. Split-word rejoining (c h u t → chut)
    10. Obfuscated word detection (sh*t → shit)
    11. Non-token character removal

    Args:
        text: Raw input text from a comment or review.

    Returns:
        Normalized lowercase ASCII-safe string.
    """
    # Phase 1: Unicode normalization and homoglyph defense
    value = unicode_normalize(str(text))
    # Phase 2: Devanagari transliteration (must happen before lowercasing)
    value = transliterate_devanagari(value)
    # Phase 3: Platform-specific normalization
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
    """Extract a frozenset of tokens from normalized text.

    Args:
        text: Normalized text string.

    Returns:
        Frozenset of individual word tokens.
    """
    return frozenset(TOKEN_RE.findall(text))


def sentiment_signal(text: str, tokens: frozenset[str]) -> tuple[str, float]:
    """Compute a simple bag-of-words sentiment signal.

    Returns (label, score) where label is 'positive'/'negative'/'neutral'
    and score is a sigmoid-transformed raw signal in (0, 1).

    Note:
        This is a heuristic fallback. When the MLScorer is available
        (Phase 2), it replaces this function entirely.

    Args:
        text: Normalized text for substring matching of multi-word terms.
        tokens: Token set for single-word term lookup.

    Returns:
        Tuple of (sentiment_label, sentiment_score).
    """
    pos = sum(1 for term in POSITIVE_TERMS if term in text or term in tokens)
    neg = sum(1 for term in NEGATIVE_TERMS if term in text or term in tokens)
    raw = neg - pos
    score = 1 / (1 + math.exp(-raw)) if raw else 0.5
    if raw > 0:
        label = "negative"
    elif raw < 0:
        label = "positive"
    else:
        label = "neutral"
    return label, round(score, 3)


def rating_disagreement_risk(
    parent_review_rating: str, perfection_pct: float, skip_pct: float
) -> float:
    """Compute extra risk from rating disagreement context.

    A comment replying to a 'Skip' review when most users rated 'Perfection'
    (or vice versa) is more likely to be aggressive disagreement.

    Args:
        parent_review_rating: Rating of the parent review ('Skip', 'Perfection', etc.).
        perfection_pct: Percentage of movie's 'Perfection' ratings.
        skip_pct: Percentage of movie's 'Skip' ratings.

    Returns:
        Extra risk addend (0.0, 0.15, or 0.25).
    """
    rating = str(parent_review_rating).lower()
    if rating == "skip" and perfection_pct >= 80:
        return 0.25
    if rating == "perfection" and skip_pct >= 35:
        return 0.15
    return 0.0


def build_reason_codes(**signals: object) -> tuple[str, ...]:
    """Build a tuple of human-readable reason codes from boolean signals.

    Args:
        **signals: Named boolean or string signal values. Expected keys:
            has_mention, disagreement, sentiment_label, target, profanity,
            soft, directed_attack, severe, threat, protected_abuse.

    Returns:
        Tuple of reason code strings.
    """
    reason_codes: list[str] = []
    if signals["has_mention"]:
        reason_codes.append("MENTION_OR_DIRECT_REPLY")
    if signals["disagreement"]:
        reason_codes.append("RATING_DISAGREEMENT_RISK")
    if signals["sentiment_label"] == "negative":
        reason_codes.append("NEGATIVE_SENTIMENT")
    target = str(signals["target"])
    if target in CONTENT_TARGETS:
        reason_codes.append("TARGETS_MOVIE_OR_REVIEW_CONTENT")
    if target in PERSON_OR_GROUP_TARGETS:
        reason_codes.append("TARGETS_PERSON_OR_GROUP")
    if signals["profanity"]:
        reason_codes.append("PROFANITY_SIGNAL")
    if signals["soft"]:
        reason_codes.append("SOFT_ABUSE_SIGNAL")
    if signals["directed_attack"]:
        reason_codes.append("DIRECTED_ATTACK_PATTERN")
    if signals["severe"]:
        reason_codes.append("SEVERE_ABUSE_SIGNAL")
    if signals["threat"]:
        reason_codes.append("THREAT_SIGNAL")
    if signals["protected_abuse"]:
        reason_codes.append("PROTECTED_CLASS_ABUSE_PATTERN")
    return tuple(reason_codes)


def decide_action(
    *,
    target: str,
    threat: bool,
    protected_abuse: bool,
    severe: bool,
    directed_attack: bool,
    soft: bool,
    model_score: float,
    risk_score: float,
    sentiment_label: str,
) -> tuple[str, str, str, str]:
    """Apply policy rules to produce (action, category, intent, severity).

    Rules are evaluated top-to-bottom; the first matching rule wins.

    Args:
        target: Detected target type.
        threat: True if threat language was detected.
        protected_abuse: True if protected-class abuse phrases were found.
        severe: True if severe abuse terms were found.
        directed_attack: True if a directed-attack phrase was found.
        soft: True if soft abuse terms were found.
        model_score: Effective toxicity score (heuristic or ML model).
        risk_score: Aggregated risk score.
        sentiment_label: 'positive', 'negative', or 'neutral'.

    Returns:
        Tuple of (action, category, intent, severity).
    """
    if threat:
        return "flag_for_removal", "threat_or_violence", "threat", "critical"
    if protected_abuse and target == "protected_class":
        return "flag_for_removal", "hate_or_identity_attack", "insult", "high"
    if severe and target in PERSON_OR_GROUP_TARGETS | {"unknown"}:
        category = "hate_or_identity_attack" if target == "protected_class" else "personal_attack"
        return "flag_for_removal", category, "insult", "high"
    if directed_attack and target in PERSON_OR_GROUP_TARGETS | {"unknown"}:
        return "flag_for_review", "harassment", "trolling", "medium"
    if soft and target in PERSON_OR_GROUP_TARGETS:
        return "flag_for_review", "harassment", "trolling", "medium"
    if model_score >= 0.82 and target not in CONTENT_TARGETS:
        return "flag_for_review", "harassment", "insult", "medium"
    if risk_score >= 0.62 and target in PERSON_OR_GROUP_TARGETS | {"unknown"}:
        return "flag_for_review", "harassment", "trolling", "low"
    intent = "criticism" if sentiment_label == "negative" else "normal_discussion"
    return "allow", "non_abusive", intent, "none"


def explain(action: str, target: str) -> str:
    """Generate a human-readable explanation for a moderation decision.

    Args:
        action: The moderation action ('allow', 'flag_for_review', 'flag_for_removal').
        target: The detected target type.

    Returns:
        A one-sentence explanation string.
    """
    if action == "allow":
        if target in CONTENT_TARGETS:
            return (
                "Allowed because the negative language targets movie or review "
                "content rather than a user."
            )
        return "Allowed because no severe abuse or user-directed attack was detected."
    if action == "flag_for_review":
        return (
            "Sent to review because the comment is aggressive, borderline, "
            "or aimed at people rather than movie craft."
        )
    return (
        "Flagged for removal because the comment contains severe user-directed "
        "abuse or threat-like language."
    )


def _log_decision(
    *,
    action: str,
    category: str,
    severity: str,
    risk_score: float,
    latency_ms: float,
    reason_codes: tuple[str, ...],
    context_type: str,
) -> None:
    """Emit a structured log entry for every moderation decision.

    Args:
        action: The moderation action taken.
        category: The harm category.
        severity: Severity level string.
        risk_score: Computed risk score.
        latency_ms: Processing latency in milliseconds.
        reason_codes: Tuple of reason code strings.
        context_type: Comment context type.
    """
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


# ---------------------------------------------------------------------------
# Thread-safe default engine singleton
# ---------------------------------------------------------------------------

_DEFAULT_ENGINE: ModerationEngine | None = None
_DEFAULT_ENGINE_LOCK = threading.Lock()


def get_default_engine() -> ModerationEngine:
    """Return the process-wide default ModerationEngine (thread-safe singleton).

    Uses double-checked locking to avoid redundant lock acquisition on the
    hot path once the engine has been initialized.

    Returns:
        The shared ModerationEngine instance.
    """
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        with _DEFAULT_ENGINE_LOCK:
            if _DEFAULT_ENGINE is None:  # double-checked locking
                _DEFAULT_ENGINE = ModerationEngine()
    return _DEFAULT_ENGINE
