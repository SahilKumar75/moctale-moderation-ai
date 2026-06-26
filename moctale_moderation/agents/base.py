"""Base classes for the agency-agents moderation architecture."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from moctale_moderation.schemas import ModerationRequest, ModerationResult

log = logging.getLogger(__name__)


@dataclass
class AgentPayload:
    """The state payload passed between agents."""
    request: ModerationRequest
    normalized_text: str = ""
    tokens: frozenset[str] = field(default_factory=frozenset)
    language: str = "unknown"
    heuristic_signals: dict[str, Any] = field(default_factory=dict)
    ml_signals: dict[str, Any] = field(default_factory=dict)
    context_signals: dict[str, Any] = field(default_factory=dict)
    policy_action: str | None = None
    policy_category: str | None = None
    policy_intent: str | None = None
    policy_severity: str | None = None
    policy_reason_codes: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    final_result: ModerationResult | None = None


@dataclass
class AgentResult:
    """Result returned by an agent's process method."""
    payload: AgentPayload
    next_agent: str | None = None
    error: Exception | None = None


class BaseAgent(ABC):
    """Abstract base class for all moderation agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the agent (used for routing)."""
        pass

    @abstractmethod
    async def process(self, payload: AgentPayload) -> AgentResult:
        """Process the payload and return the updated payload and next agent."""
        pass


class AgentBus:
    """Lightweight in-process message bus for routing between agents."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent with the bus."""
        self._agents[agent.name] = agent
        log.debug("Registered agent: %s", agent.name)

    async def run_pipeline(
        self,
        request: ModerationRequest,
        start_agent: str = "intake",
    ) -> ModerationResult:
        """Run a request through the agent pipeline until completion."""
        payload = AgentPayload(request=request)
        current_agent = start_agent

        while current_agent:
            if current_agent not in self._agents:
                log.error("Agent not found: %s", current_agent)
                raise ValueError(f"Agent not found: {current_agent}")

            agent = self._agents[current_agent]
            try:
                result = await agent.process(payload)
                payload = result.payload
                current_agent = result.next_agent
            except Exception as e:
                log.exception("Error in agent %s: %s", current_agent, e)
                # Fail conservative: uncertain content goes to review, never silently allowed.
                return ModerationResult(
                    predicted_action="flag_for_review",
                    predicted_category="pipeline_error",
                    predicted_intent="error",
                    predicted_severity="none",
                    target_detected_pred="unknown",
                    sentiment_label="neutral",
                    sentiment_score=0.0,
                    risk_score=0.0,
                    heuristic_toxicity_score=0.0,
                    model_toxicity_score=0.0,
                    reason_codes=("PIPELINE_ERROR",),
                    triggered_rules=[],
                    reason=f"Pipeline failed at {current_agent} — defaulting to review",
                )

        if not payload.final_result:
            log.error("Pipeline finished without generating a final result.")
            return ModerationResult(
                predicted_action="allow",
                predicted_category="error",
                predicted_intent="error",
                predicted_severity="none",
                target_detected_pred="unknown",
                sentiment_label="neutral",
                sentiment_score=0.0,
                risk_score=0.0,
                heuristic_toxicity_score=0.0,
                model_toxicity_score=0.0,
                reason_codes=(),
                triggered_rules=[],
                reason="Pipeline incomplete",
            )

        return payload.final_result
