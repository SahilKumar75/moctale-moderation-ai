"""Evaluation harness for Moctale Moderation AI.

Computes precision, recall, F1, and confusion matrix for
the moderation engine on a labeled CSV dataset.

Usage::

    from moctale_moderation.evaluator import Evaluator
    report = Evaluator().run("data/moderation_examples.csv")
    print(report.summary())
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


ACTIONS = ["allow", "flag_for_review", "flag_for_removal"]


@dataclass
class ClassMetrics:
    """Per-class precision, recall, F1."""
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def support(self) -> int:
        return self.tp + self.fn


@dataclass
class EvaluationReport:
    """Full evaluation report."""
    dataset_path: str
    total: int = 0
    skipped: int = 0
    per_class: dict[str, ClassMetrics] = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def macro_f1(self) -> float:
        scores = [m.f1 for m in self.per_class.values() if m.support > 0]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def weighted_f1(self) -> float:
        total_support = sum(m.support for m in self.per_class.values())
        if total_support == 0:
            return 0.0
        return sum(m.f1 * m.support for m in self.per_class.values()) / total_support

    @property
    def accuracy(self) -> float:
        correct = sum(m.tp for m in self.per_class.values())
        return correct / self.total if self.total > 0 else 0.0

    def summary(self) -> str:
        """Return a Markdown-formatted summary table."""
        lines = [
            "# Moctale Moderation AI — Evaluation Report\n",
            f"**Dataset**: {self.dataset_path}  ",
            f"**Total rows**: {self.total} ({self.skipped} skipped)  ",
            f"**Accuracy**: {self.accuracy:.3f}  ",
            f"**Macro F1**: {self.macro_f1:.3f}  ",
            f"**Weighted F1**: {self.weighted_f1:.3f}  ",
            "",
            "## Per-Class Metrics",
            "",
            "| Class | Precision | Recall | F1 | Support |",
            "|---|---|---|---|---|",
        ]
        for label in ACTIONS:
            m = self.per_class.get(label)
            if m:
                lines.append(
                    f"| {label} | {m.precision:.3f} | {m.recall:.3f} | {m.f1:.3f} | {m.support} |"
                )
        lines += [
            "",
            "## Confusion Matrix",
            "",
            "| actual \\ predicted | " + " | ".join(ACTIONS) + " |",
            "|---|" + "---|" * len(ACTIONS),
        ]
        for actual in ACTIONS:
            row = self.confusion.get(actual, {})
            cells = [str(row.get(pred, 0)) for pred in ACTIONS]
            lines.append(f"| **{actual}** | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Return JSON-serializable dict."""
        return {
            "dataset_path": self.dataset_path,
            "total": self.total,
            "skipped": self.skipped,
            "accuracy": round(self.accuracy, 4),
            "macro_f1": round(self.macro_f1, 4),
            "weighted_f1": round(self.weighted_f1, 4),
            "per_class": {
                label: {
                    "precision": round(m.precision, 4),
                    "recall": round(m.recall, 4),
                    "f1": round(m.f1, 4),
                    "support": m.support,
                }
                for label, m in self.per_class.items()
            },
            "confusion": self.confusion,
        }


class Evaluator:
    """Run evaluation on a labeled CSV dataset."""

    def run(
        self,
        dataset_path: str | Path,
        label_col: str = "moderation_action",
        text_col: str = "text",
    ) -> EvaluationReport:
        """Evaluate the default engine against a labeled CSV.

        Args:
            dataset_path: Path to CSV file with 'text' and 'label' columns.
            label_col: Name of the ground-truth label column.
            text_col: Name of the text column.

        Returns:
            EvaluationReport with precision, recall, F1, and confusion matrix.
        """
        from .engine import get_default_engine, normalize_text
        from .schemas import ModerationRequest

        engine = get_default_engine()
        path = Path(dataset_path)
        report = EvaluationReport(
            dataset_path=str(path),
            per_class={a: ClassMetrics(label=a) for a in ACTIONS},
            confusion={a: {b: 0 for b in ACTIONS} for a in ACTIONS},
        )

        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            text = row.get(text_col, "").strip()
            true_label = row.get(label_col, "").strip().lower()

            if not text or true_label not in ACTIONS:
                report.skipped += 1
                continue

            request = ModerationRequest(
                text=text,
                context_type=row.get("context_type", "reply_to_review"),
                parent_review_rating=row.get("parent_review_rating", "Skip"),
                movie_rating_perfection_pct=float(row.get("movie_rating_perfection_pct") or 90),
                movie_rating_skip_pct=float(row.get("movie_rating_skip_pct") or 5),
            )
            result = engine.analyze(request)
            pred_label = result.predicted_action

            report.total += 1
            report.confusion[true_label][pred_label] = report.confusion[true_label].get(pred_label, 0) + 1

            for action in ACTIONS:
                m = report.per_class[action]
                if true_label == action and pred_label == action:
                    m.tp += 1
                elif true_label != action and pred_label == action:
                    m.fp += 1
                elif true_label == action and pred_label != action:
                    m.fn += 1

        return report
