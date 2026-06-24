"""Policy rules data structures."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


@dataclass
class PolicyRule:
    """Represents a single moderation policy rule."""

    id: str
    description: str
    action: str
    category: str
    severity: str
    examples: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "category": self.category,
            "severity": self.severity,
            "examples": self.examples,
        }

    @property
    def embedding_text(self) -> str:
        """Text to embed for semantic search.
        
        We combine the description and examples into a single document
        for the embedding model to represent the semantic space of the rule.
        """
        parts = [self.description]
        if self.examples:
            parts.append("Examples:")
            parts.extend(f"- {ex}" for ex in self.examples)
        return "\n".join(parts)


class PolicyRuleLoader:
    """Loads policy rules from YAML configuration."""

    @staticmethod
    def from_yaml(path: Path | str) -> list[PolicyRule]:
        path_obj = Path(path)
        if not path_obj.exists():
            log.warning("Policy rules file not found: %s", path_obj)
            return []

        try:
            with path_obj.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "rules" not in data:
                log.warning("No 'rules' key found in %s", path_obj)
                return []

            rules = []
            for item in data["rules"]:
                rules.append(
                    PolicyRule(
                        id=item.get("id", "unknown_rule"),
                        description=item.get("description", ""),
                        action=item.get("action", "allow"),
                        category=item.get("category", "unknown"),
                        severity=item.get("severity", "none"),
                        examples=item.get("examples", []),
                    )
                )
            return rules

        except Exception as e:
            log.error("Failed to load policy rules from %s: %s", path_obj, e)
            return []
