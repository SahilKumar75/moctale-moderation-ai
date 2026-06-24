import asyncio
import unittest

from moctale_moderation import ModerationEngine, ModerationRequest


class ModerationEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ModerationEngine()

    def test_allows_harsh_movie_criticism(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="This movie is shit but the issue is pacing, not the actors personally.",
                context_type="main_review",
            )
        )
        self.assertEqual(result.predicted_action, "allow")
        self.assertEqual(result.target_detected_pred, "movie_show")

    def test_removes_direct_user_abuse(self):
        result = self.engine.analyze("@reviewer tu chutiya hai, review dena band kar.")
        self.assertEqual(result.predicted_action, "flag_for_removal")
        self.assertIn("SEVERE_ABUSE_SIGNAL", result.reason_codes)

    def test_batches_keep_order(self):
        results = self.engine.analyze_many(["The script was weak.", "@user go die."])
        self.assertEqual([item.predicted_action for item in results], ["allow", "flag_for_removal"])

    def test_async_batch_keeps_order(self):
        async def run():
            return await self.engine.analyze_many_async(["The script was weak.", "@user go die."], concurrency=2)

        results = asyncio.run(run())
        self.assertEqual([item.predicted_action for item in results], ["allow", "flag_for_removal"])

    def test_real_moctale_review_allows_obfuscated_movie_profanity(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="waste of time. I like dc universe. Marvel is sh*t.",
                context_type="main_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "allow")
        self.assertEqual(result.target_detected_pred, "movie_show")
        self.assertIn("PROFANITY_SIGNAL", result.reason_codes)

    def test_real_moctale_slang_reply_goes_to_review(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="bc",
                context_type="reply_to_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "flag_for_review")

    def test_real_moctale_hinglish_severe_variant_is_removed(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="haa toh movie fiction hi hain, CINEMA IS SUBJECTIVE CHUTIYE",
                context_type="reply_to_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "flag_for_removal")
        self.assertEqual(result.target_detected_pred, "reviewer_or_user")

    def test_real_moctale_bhadwa_variant_is_removed(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="@Nafis Jaka kaam khojo berojgar Bhadwa",
                context_type="reply_to_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "flag_for_removal")

    def test_real_moctale_vulgar_reply_goes_to_review(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="Toh mat dekh na laure rating kyu de rha hain agar jhaat bhar kuch samajh Nhi aaya",
                context_type="reply_to_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "flag_for_review")

    def test_symbol_mixed_indian_abuse_is_canonicalized(self):
        samples = [
            "tu m@d@rch0d hai",
            "ye kya b h a d w a comment hai",
            "l@wde jaake movie samajh",
            "chut!ye opinion mat de",
            "b#s#d#k review band kar",
        ]
        for text in samples:
            with self.subTest(text=text):
                result = self.engine.analyze(
                    ModerationRequest(
                        text=text,
                        context_type="reply_to_review",
                        parent_review_rating="Skip",
                        movie_rating_perfection_pct=30,
                        movie_rating_skip_pct=65,
                    )
                )
                self.assertEqual(result.predicted_action, "flag_for_removal")
                self.assertIn("SEVERE_ABUSE_SIGNAL", result.reason_codes)

    def test_mention_survives_symbol_normalization(self):
        result = self.engine.analyze(
            ModerationRequest(
                text="@Nafis tu nalla hai",
                context_type="reply_to_review",
                parent_review_rating="Skip",
                movie_rating_perfection_pct=30,
                movie_rating_skip_pct=65,
            )
        )
        self.assertEqual(result.predicted_action, "flag_for_review")
        self.assertIn("MENTION_OR_DIRECT_REPLY", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
