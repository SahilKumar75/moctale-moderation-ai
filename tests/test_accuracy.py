"""Accuracy and coverage tests for Phase 2 improvements."""
from __future__ import annotations

import unittest

from moctale_moderation import ModerationEngine, ModerationRequest


class ProtectedClassTests(unittest.TestCase):
    def setUp(self):
        self.engine = ModerationEngine()

    def test_anti_dalit_slur_flagged(self):
        result = self.engine.analyze("tu chamar hai, review mat de")
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_lgbtq_slur_flagged(self):
        result = self.engine.analyze("arey chakka hai tu")
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_anti_muslim_phrase_flagged(self):
        result = self.engine.analyze("katua log yahan kya kar rahe hain")
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_go_to_pakistan_flagged(self):
        result = self.engine.analyze("pakistan chale jao tum log")
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_dehumanizing_term_flagged(self):
        result = self.engine.analyze("these people are subhuman vermin")
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_legitimate_religion_discussion_allowed(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="This movie beautifully depicts Hindu-Muslim unity during partition.",
                context_type="main_review",
            )
        )
        self.assertEqual(result.predicted_action, "allow")

    def test_faggot_flagged(self):
        result = self.engine.analyze("tu faggot hai")
        self.assertEqual(result.predicted_action, "flag_for_removal")


class MLScorerTests(unittest.TestCase):
    def setUp(self):
        from moctale_moderation.ml_scorer import MLScorer
        # Use heuristic-only scorer (no model download in tests)
        self.scorer = MLScorer(pipeline=None)

    def test_heuristic_negative_sentiment(self):
        result = self.scorer.score_one("worst movie ever trash bakwas")
        self.assertEqual(result.label, "negative")
        self.assertEqual(result.source, "heuristic")

    def test_heuristic_positive_sentiment(self):
        result = self.scorer.score_one("great amazing loved it best movie")
        self.assertEqual(result.label, "positive")

    def test_heuristic_neutral_sentiment(self):
        result = self.scorer.score_one("the movie exists")
        self.assertEqual(result.label, "neutral")

    def test_score_batch_preserves_order(self):
        texts = ["trash worst", "loved it great", "ok movie"]
        results = self.scorer.score_batch(texts)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].label, "negative")
        self.assertEqual(results[1].label, "positive")

    def test_empty_batch(self):
        self.assertEqual(self.scorer.score_batch([]), [])


class EvaluatorTests(unittest.TestCase):
    def test_evaluator_runs_on_dataset(self):
        from pathlib import Path
        from moctale_moderation.evaluator import Evaluator
        dataset = Path(__file__).resolve().parents[1] / "data" / "moderation_examples.csv"
        if not dataset.exists():
            self.skipTest("Dataset not found")
        report = Evaluator().run(dataset)
        self.assertGreater(report.total, 0)
        self.assertGreaterEqual(report.macro_f1, 0.0)
        self.assertLessEqual(report.macro_f1, 1.0)
        # Should have non-zero accuracy on our own demo dataset
        self.assertGreater(report.accuracy, 0.50)

    def test_report_summary_is_valid_markdown(self):
        from pathlib import Path
        from moctale_moderation.evaluator import Evaluator
        dataset = Path(__file__).resolve().parents[1] / "data" / "moderation_examples.csv"
        if not dataset.exists():
            self.skipTest("Dataset not found")
        report = Evaluator().run(dataset)
        md = report.summary()
        self.assertIn("# Moctale", md)
        self.assertIn("Macro F1", md)
        self.assertIn("Confusion Matrix", md)

    def test_report_to_json(self):
        from pathlib import Path
        from moctale_moderation.evaluator import Evaluator
        dataset = Path(__file__).resolve().parents[1] / "data" / "moderation_examples.csv"
        if not dataset.exists():
            self.skipTest("Dataset not found")
        report = Evaluator().run(dataset)
        data = report.to_json()
        self.assertIn("macro_f1", data)
        self.assertIn("per_class", data)
        self.assertIn("confusion", data)


if __name__ == "__main__":
    unittest.main()
