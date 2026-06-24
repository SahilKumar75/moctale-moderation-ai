"""Policy agent for Moctale Moderation AI.

Evaluates signals, computes risk score, and decides final action.
"""
from __future__ import annotations

import logging
import math
import threading
from pathlib import Path

import yaml

from moctale_moderation.schemas import ModerationResult
from .base import AgentPayload, AgentResult, BaseAgent

log = logging.getLogger(__name__)

REPLY_CONTEXTS = frozenset({"reply_to_review", "reply_to_comment"})
PERSON_OR_GROUP_TARGETS = frozenset({"reviewer_or_user", "community_identity", "protected_class"})
CONTENT_TARGETS = frozenset({"movie_show", "actor_public_work", "review_content"})

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class RiskWeights:
    def __init__(self, weights: dict[str, float], thresholds: dict[str, float]) -> None:
        self.reply_context_base = weights.get("reply_context_base", 0.20)
        self.main_review_base = weights.get("main_review_base", 0.05)
        self.has_mention = weights.get("has_mention", 0.15)
        self.negative_sentiment = weights.get("negative_sentiment", 0.15)
        self.toxicity_scale = weights.get("toxicity_scale", 0.45)
        
        self.flag_for_review_risk = thresholds.get("flag_for_review_risk", 0.62)
        self.flag_for_review_model = thresholds.get("flag_for_review_model", 0.82)

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "RiskWeights":
        path = path or _CONFIG_DIR / "risk_weights.yaml"
        if not path.exists():
            return cls({}, {})
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls(data.get("weights", {}), data.get("thresholds", {}))
        except Exception as exc:
            log.warning("Failed to load risk_weights.yaml", exc_info=exc)
            return cls({}, {})


_WEIGHTS_INSTANCE: RiskWeights | None = None
_WEIGHTS_LOCK = threading.Lock()


def get_risk_weights() -> RiskWeights:
    global _WEIGHTS_INSTANCE
    if _WEIGHTS_INSTANCE is None:
        with _WEIGHTS_LOCK:
            if _WEIGHTS_INSTANCE is None:
                _WEIGHTS_INSTANCE = RiskWeights.from_yaml()
    return _WEIGHTS_INSTANCE


class PolicyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "policy"

    def build_reason_codes(self, signals: dict[str, Any]) -> list[str]:
        codes = []
        if signals.get("has_mention"):
            codes.append("MENTION_OR_DIRECT_REPLY")
        if signals.get("disagreement"):
            codes.append("RATING_DISAGREEMENT_RISK")
        if signals.get("sentiment_label") == "negative":
            codes.append("NEGATIVE_SENTIMENT")
        target = str(signals.get("target"))
        if target in CONTENT_TARGETS:
            codes.append("TARGETS_MOVIE_OR_REVIEW_CONTENT")
        if target in PERSON_OR_GROUP_TARGETS:
            codes.append("TARGETS_PERSON_OR_GROUP")
        if signals.get("profanity"):
            codes.append("PROFANITY_SIGNAL")
        if signals.get("soft"):
            codes.append("SOFT_ABUSE_SIGNAL")
        if signals.get("directed_attack"):
            codes.append("DIRECTED_ATTACK_PATTERN")
        if signals.get("severe"):
            codes.append("SEVERE_ABUSE_SIGNAL")
        if signals.get("threat"):
            codes.append("THREAT_SIGNAL")
        if signals.get("protected_abuse"):
            codes.append("PROTECTED_CLASS_ABUSE_PATTERN")
        return codes

    def decide_action(
        self,
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
        thresholds: RiskWeights,
    ) -> tuple[str, str, str, str]:
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
        if model_score >= thresholds.flag_for_review_model and target not in CONTENT_TARGETS:
            return "flag_for_review", "harassment", "insult", "medium"
        if risk_score >= thresholds.flag_for_review_risk and target in PERSON_OR_GROUP_TARGETS | {"unknown"}:
            return "flag_for_review", "harassment", "trolling", "low"
        intent = "criticism" if sentiment_label == "negative" else "normal_discussion"
        return "allow", "non_abusive", intent, "none"

    def explain(self, action: str, target: str) -> str:
        if action == "allow":
            if target in CONTENT_TARGETS:
                return "Allowed because the negative language targets movie or review content rather than a user."
            return "Allowed because no severe abuse or user-directed attack was detected."
        if action == "flag_for_review":
            return "Sent to review because the comment is aggressive, borderline, or aimed at people rather than movie craft."
        return "Flagged for removal because the comment contains severe user-directed abuse or threat-like language."

    async def process(self, payload: AgentPayload) -> AgentResult:
        hs = payload.heuristic_signals
        mls = payload.ml_signals
        cs = payload.context_signals
        weights = get_risk_weights()
        
        # We also need the policy store
        from moctale_moderation.policy.store import get_policy_store
        store = get_policy_store()

        htox = hs.get("toxicity", 0.0)
        ml_score = mls.get("model_toxicity")
        if ml_score is None or math.isnan(ml_score):
            model_score = htox
        else:
            model_score = ml_score

        context_type = cs.get("context_type", "reply_to_review")
        sentiment_label = mls.get("sentiment_label", "neutral")
        has_mention = hs.get("has_mention", False)
        disagreement = cs.get("disagreement_risk", 0.0)

        risk_score = weights.reply_context_base if context_type in REPLY_CONTEXTS else weights.main_review_base
        risk_score += weights.has_mention if has_mention else 0.0
        risk_score += weights.negative_sentiment if sentiment_label == "negative" else 0.0
        risk_score += disagreement
        risk_score += max(htox, model_score) * weights.toxicity_scale
        risk_score = round(min(risk_score, 1.0), 3)

        target = hs.get("target", "unknown")
        
        action, category, intent, severity = self.decide_action(
            target=target,
            threat=hs.get("threat", False),
            protected_abuse=hs.get("protected_abuse", False),
            severe=hs.get("severe", False),
            directed_attack=hs.get("directed_attack", False),
            soft=hs.get("soft", False),
            model_score=model_score,
            risk_score=risk_score,
            sentiment_label=sentiment_label,
            thresholds=weights,
        )

        all_signals = {**hs, **mls, **cs, "disagreement": disagreement}
        reason_codes = self.build_reason_codes(all_signals)
        
        # --- Conditional RAG (Early Exit) ---
        # If the heuristic and model show completely benign intent, skip expensive semantic search.
        triggered_rules = []
        is_clean = (
            risk_score < 0.1 
            and model_score < 0.1 
            and action == "allow"
            and not any([hs.get("threat"), hs.get("severe"), hs.get("soft"), hs.get("protected_abuse"), hs.get("directed_attack")])
        )

        if not is_clean:
            rules = store.retrieve(payload.normalized_text, k=1, max_distance=1.1)
            if rules:
                top_rule = rules[0]
                triggered_rules.append(top_rule.id)
                
                if top_rule.action != "allow":
                    # If the hardcoded engine is not sure or says allow, but RAG sees explicit abuse:
                    if action == "allow" and model_score > 0.75:
                        action = top_rule.action
                        category = top_rule.category
                        severity = top_rule.severity
                    
                    # If hardcoded engine says flag, we adopt RAG's nuanced category
                    elif action != "allow":
                        category = top_rule.category
                    severity = top_rule.severity
                    # We keep the base action (no escalation or downgrade based solely on RAG)
                    
            else:
                # If RAG says allow (e.g. movie criticism) but base engine flagged it for review, override it to allow.
                # We never downgrade a severe 'flag_for_removal' based on fuzzy semantic search.
                if action == "flag_for_review" and model_score < 0.7:
                    action = "allow"
                    category = top_rule.category
                    severity = top_rule.severity

        payload.risk_score = risk_score
        payload.policy_action = action
        payload.policy_category = category
        payload.policy_intent = intent
        payload.policy_severity = severity
        payload.policy_reason_codes = reason_codes

        # If flagged for review, route to review queue agent.
        # Else finish up.
        if action == "flag_for_review":
            next_agent = "review_queue"
        else:
            next_agent = None  # Finish
            
        # Create final result to store in payload
        payload.final_result = ModerationResult(
            predicted_action=action,
            predicted_category=category,
            predicted_intent=intent,
            predicted_severity=severity,
            target_detected_pred=target,
            sentiment_label=sentiment_label,
            sentiment_score=mls.get("sentiment_score", 0.0),
            risk_score=risk_score,
            heuristic_toxicity_score=htox,
            model_toxicity_score=round(model_score, 3),
            reason_codes=tuple(reason_codes),
            triggered_rules=triggered_rules,
            reason=self.explain(action, target),
        )

        return AgentResult(payload=payload, next_agent=next_agent)
