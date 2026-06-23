from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
NOTEBOOKS.mkdir(exist_ok=True)


def md(text):
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text):
    return nbf.v4.new_code_cell(dedent(text).strip())


nb = nbf.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {
        "name": "python",
        "pygments_lexer": "ipython3"
    }
}

cells = [
    md(
        """
        # Moctale Moderation AI

        A Kaggle-ready demo for target-aware comment moderation on a movie and TV review platform.

        The goal is not to block negative opinions. The goal is to flag abuse aimed at users, reviewers, or communities.

        ```text
        "This movie is shit" -> allow
        "You are shit" -> flag_for_removal
        ```

        Content note: this notebook contains examples of hostile and abusive language for moderation testing.
        """
    ),
    md(
        """
        ## What This Notebook Shows

        - Loads the 500-row demo dataset
        - Shows label and source distribution
        - Implements a low-cost hybrid moderation engine
        - Separates movie criticism from user-directed abuse
        - Produces reasons and reason codes
        - Reports toy metrics on the demo dataset
        - Shows an admin-style moderation table

        These are demo metrics, not production performance claims.
        """
    ),
    code(
        """
        import json
        import math
        import os
        import re
        import warnings

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns
        from IPython.display import display
        from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score

        warnings.filterwarnings("ignore")
        pd.set_option("display.max_colwidth", 140)
        sns.set_theme(style="whitegrid")
        """
    ),
    md(
        """
        ## Load Dataset

        In Kaggle, upload the repo dataset or place `moderation_examples.csv` in the notebook input directory.
        """
    ),
    code(
        """
        possible_paths = [
            "../input/moctale-moderation-ai-demo/moderation_examples.csv",
            "../input/moctale-moderation-ai-demo/data/moderation_examples.csv",
            "../input/moctale-moderation-ai/moderation_examples.csv",
            "../input/moctale-moderation-ai/data/moderation_examples.csv",
            "data/moderation_examples.csv",
            "../data/moderation_examples.csv",
        ]

        data_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if data_path is None:
            raise FileNotFoundError("Could not find moderation_examples.csv. Upload it to Kaggle or run this notebook from the repo root.")

        df = pd.read_csv(data_path)
        print(df.shape)
        display(df.head(5))
        """
    ),
    code(
        """
        print("Moderation action distribution")
        display(df["moderation_action"].value_counts().rename_axis("action").reset_index(name="count"))

        print("Source distribution")
        display(df["source_type"].value_counts().rename_axis("source_type").reset_index(name="count"))

        print("Language mix")
        display(df["language_mix"].value_counts().rename_axis("language_mix").reset_index(name="count"))
        """
    ),
    code(
        """
        fig, axes = plt.subplots(1, 3, figsize=(16, 4))

        df["moderation_action"].value_counts().plot(kind="bar", ax=axes[0], color=["#2E7D32", "#F9A825", "#C62828"])
        axes[0].set_title("Actions")
        axes[0].set_xlabel("")
        axes[0].set_ylabel("rows")

        df["source_type"].value_counts().plot(kind="bar", ax=axes[1], color="#5B6CFF")
        axes[1].set_title("Sources")
        axes[1].set_xlabel("")
        axes[1].set_ylabel("")

        df["target_detected"].value_counts().plot(kind="bar", ax=axes[2], color="#00897B")
        axes[2].set_title("Targets")
        axes[2].set_xlabel("")
        axes[2].set_ylabel("")

        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## Hybrid Moderation Engine

        The engine uses cheap signals first:

        - text normalization
        - direct reply and mention risk
        - rating disagreement risk
        - Hinglish abuse rules
        - target detection
        - optional toxicity model score

        Final decisions come from policy logic, not from a toxicity score alone.
        """
    ),
    code(
        """
        MOVIE_TERMS = {
            "movie", "film", "show", "series", "acting", "actor", "actress", "script", "story", "pacing", "direction",
            "dialogue", "dialogues", "screenplay", "editing", "vfx", "music", "song", "climax", "interval", "scene",
            "character", "plot", "performance", "cinematography", "color", "grading", "theatre", "ott", "hero", "villain"
        }

        USER_TERMS = {
            "you", "your", "u", "ur", "tu", "tum", "tera", "teri", "tere", "aap", "reviewer", "user", "people",
            "fans", "fanbase", "comment", "comments", "log", "banda", "aadmi", "person", "kiddo", "buddy"
        }

        GROUP_TARGET_PHRASES = {
            "perfection dene wale", "skip gang", "people in comments", "comment section", "fanbase",
            "fans of", "perfection wale", "skip wale"
        }

        DIRECTED_ATTACK_PHRASES = {
            "review dena band kar", "stop reviewing", "get some brain", "chup", "chup reh",
            "real id se aao", "attention seeker", "trash taste", "your taste is trash",
            "attention grab", "what s your problem", "whats your problem", "don t know history",
            "dont know history", "you don t know", "you dont know",
            "review nahi aata", "only a clown person", "only a idiot person", "only an idiot person",
            "only a gadha person", "only a bewakoof person", "only a stupid person",
            "only a dumb person", "only a mand-buddhi person", "only a tmkc person",
            "only a mkl person", "only a bkl person", "shut up", "you suck", "little shit",
            "asshole", "douche", "sadcase"
        }

        PROTECTED_ABUSE_PHRASES = {
            "people from that community are disgusting", "should leave this platform", "caste abuse",
            "attacking identity", "faggot", "faggots", "nigger"
        }

        SOFT_ABUSE = {
            "idiot", "clown", "stupid", "dumb", "bewakoof", "gadha", "mand-buddhi", "attention seeker",
            "brain dead", "brain-dead", "trash taste", "get some brain", "review nahi aata",
            "chup reh", "real id se aao"
        }

        SEVERE_ABUSE = {
            "chutiya", "tmkc", "mkl", "bkl", "teri maa", "madarchod", "bhosd", "randi", "whore",
            "fucked your mom"
        }

        THREAT_TERMS = {
            "i will find you", "dekh lunga", "hurt", "kill", "go die", "just die", "please die",
            "die if you like", "disappear", "hope you get hurt"
        }

        PROFANITY = {"shit", "fuck", "fucking", "bakwas", "ghatiya"}

        POSITIVE_TERMS = {"good", "great", "liked", "love", "best", "amazing", "perfect", "perfection", "salute", "agree"}
        NEGATIVE_TERMS = {"bad", "weak", "boring", "worst", "trash", "shit", "bakwas", "ghatiya", "overhyped", "mess", "lazy", "flat", "dragged"}

        ACTION_ORDER = ["allow", "flag_for_review", "flag_for_removal"]
        """
    ),
    code(
        """
        def normalize_text(text):
            value = str(text).lower()
            value = re.sub(r"@\\w+", "@user", value)
            value = re.sub(r"(.)\\1{2,}", r"\\1\\1", value)
            value = re.sub(r"[^a-z0-9@\\s\\-]", " ", value)
            value = re.sub(r"\\s+", " ", value).strip()
            return value


        def contains_any(text, terms):
            return any(term in text for term in terms)


        def token_set(text):
            return set(re.findall(r"[a-z0-9@\\-]+", text))


        def sentiment_signal(text):
            tokens = token_set(text)
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


        def detect_target(text, context_type="reply_to_review"):
            tokens = token_set(text)
            has_user = "@user" in tokens or bool(tokens & USER_TERMS)
            has_movie = bool(tokens & MOVIE_TERMS)
            has_group_target = contains_any(text, GROUP_TARGET_PHRASES)
            has_directed_attack = contains_any(text, DIRECTED_ATTACK_PHRASES)

            if contains_any(text, PROTECTED_ABUSE_PHRASES):
                return "protected_class"

            if contains_any(text, {"community", "religion", "caste", "hindu", "muslim"}):
                if contains_any(text, {"disgusting", "leave", "hate", "dirty", "cheap", "identity"}):
                    return "protected_class"
                return "review_content"

            if has_group_target:
                return "community_identity"

            if has_directed_attack:
                return "reviewer_or_user"

            if has_user and contains_any(text, SOFT_ABUSE | SEVERE_ABUSE | THREAT_TERMS):
                return "reviewer_or_user"

            if has_user and context_type in {"reply_to_review", "reply_to_comment"} and not has_movie:
                return "reviewer_or_user"

            if has_movie:
                return "movie_show"

            if contains_any(text, {"fans", "fanbase", "people in comments", "perfection dene wale", "skip gang"}):
                return "community_identity"

            return "unknown"


        def rating_disagreement_risk(parent_review_rating, perfection_pct, skip_pct):
            try:
                perfection = float(perfection_pct)
                skip = float(skip_pct)
            except Exception:
                return 0.0
            rating = str(parent_review_rating).lower()
            if rating == "skip" and perfection >= 80:
                return 0.25
            if rating == "perfection" and skip >= 35:
                return 0.15
            return 0.0


        def heuristic_toxicity(text):
            score = 0.0
            if contains_any(text, PROFANITY):
                score += 0.18
            if contains_any(text, SOFT_ABUSE):
                score += 0.35
            if contains_any(text, DIRECTED_ATTACK_PHRASES):
                score += 0.30
            if contains_any(text, PROTECTED_ABUSE_PHRASES):
                score += 0.60
            if contains_any(text, SEVERE_ABUSE):
                score += 0.65
            if contains_any(text, THREAT_TERMS):
                score += 0.75
            return round(min(score, 1.0), 3)
        """
    ),
    code(
        """
        def analyze_comment(text, context_type="reply_to_review", parent_review_rating="Skip", perfection_pct=90, skip_pct=5, model_toxicity_score=None):
            normalized = normalize_text(text)
            sentiment_label, sentiment_score = sentiment_signal(normalized)
            target = detect_target(normalized, context_type=context_type)
            htox = heuristic_toxicity(normalized)
            model_score = htox if model_toxicity_score is None or pd.isna(model_toxicity_score) else float(model_toxicity_score)
            disagreement = rating_disagreement_risk(parent_review_rating, perfection_pct, skip_pct)

            has_mention = "@user" in normalized
            severe = contains_any(normalized, SEVERE_ABUSE)
            threat = contains_any(normalized, THREAT_TERMS)
            soft = contains_any(normalized, SOFT_ABUSE)
            profanity = contains_any(normalized, PROFANITY)
            directed_attack = contains_any(normalized, DIRECTED_ATTACK_PHRASES)
            protected_abuse = contains_any(normalized, PROTECTED_ABUSE_PHRASES)

            risk_score = 0.0
            risk_score += 0.20 if context_type in {"reply_to_review", "reply_to_comment"} else 0.05
            risk_score += 0.15 if has_mention else 0.0
            risk_score += 0.15 if sentiment_label == "negative" else 0.0
            risk_score += disagreement
            risk_score += max(htox, model_score) * 0.45
            risk_score = round(min(risk_score, 1.0), 3)

            reason_codes = []
            if has_mention:
                reason_codes.append("MENTION_OR_DIRECT_REPLY")
            if disagreement:
                reason_codes.append("RATING_DISAGREEMENT_RISK")
            if sentiment_label == "negative":
                reason_codes.append("NEGATIVE_SENTIMENT")
            if target in {"movie_show", "actor_public_work", "review_content"}:
                reason_codes.append("TARGETS_MOVIE_OR_REVIEW_CONTENT")
            if target in {"reviewer_or_user", "community_identity", "protected_class"}:
                reason_codes.append("TARGETS_PERSON_OR_GROUP")
            if profanity:
                reason_codes.append("PROFANITY_SIGNAL")
            if soft:
                reason_codes.append("SOFT_ABUSE_SIGNAL")
            if directed_attack:
                reason_codes.append("DIRECTED_ATTACK_PATTERN")
            if severe:
                reason_codes.append("SEVERE_ABUSE_SIGNAL")
            if threat:
                reason_codes.append("THREAT_SIGNAL")
            if protected_abuse:
                reason_codes.append("PROTECTED_CLASS_ABUSE_PATTERN")

            if threat:
                action = "flag_for_removal"
                category = "threat_or_violence"
                intent = "threat"
                severity = "critical"
            elif protected_abuse and target == "protected_class":
                action = "flag_for_removal"
                category = "hate_or_identity_attack"
                intent = "insult"
                severity = "high"
            elif severe and target in {"reviewer_or_user", "community_identity", "protected_class", "unknown"}:
                action = "flag_for_removal"
                category = "personal_attack" if target != "protected_class" else "hate_or_identity_attack"
                intent = "insult"
                severity = "high"
            elif directed_attack and target in {"reviewer_or_user", "community_identity", "protected_class", "unknown"}:
                action = "flag_for_review"
                category = "harassment"
                intent = "trolling"
                severity = "medium"
            elif soft and target in {"reviewer_or_user", "community_identity", "protected_class"}:
                action = "flag_for_review"
                category = "harassment"
                intent = "trolling"
                severity = "medium"
            elif model_score >= 0.82 and target not in {"movie_show", "actor_public_work", "review_content"}:
                action = "flag_for_review"
                category = "harassment"
                intent = "insult"
                severity = "medium"
            elif risk_score >= 0.62 and target in {"reviewer_or_user", "community_identity", "protected_class", "unknown"}:
                action = "flag_for_review"
                category = "harassment"
                intent = "trolling"
                severity = "low"
            else:
                action = "allow"
                category = "non_abusive"
                intent = "criticism" if sentiment_label == "negative" else "normal_discussion"
                severity = "none"

            if action == "allow":
                if target in {"movie_show", "actor_public_work", "review_content"}:
                    reason = "Allowed because the negative language targets movie or review content rather than a user."
                else:
                    reason = "Allowed because no severe abuse or user-directed attack was detected."
            elif action == "flag_for_review":
                reason = "Sent to review because the comment is aggressive, borderline, or aimed at people rather than movie craft."
            else:
                reason = "Flagged for removal because the comment contains severe user-directed abuse or threat-like language."

            return {
                "predicted_action": action,
                "predicted_category": category,
                "predicted_intent": intent,
                "predicted_severity": severity,
                "target_detected_pred": target,
                "sentiment_label": sentiment_label,
                "sentiment_score": sentiment_score,
                "risk_score": risk_score,
                "heuristic_toxicity_score": htox,
                "model_toxicity_score": round(model_score, 3),
                "reason_codes": reason_codes,
                "reason": reason
            }
        """
    ),
    md(
        """
        ## Optional Hugging Face Toxicity Model

        Keep `USE_HF_MODEL = False` when you want a fast demo with no download.

        Set it to `True` in Kaggle if internet is enabled. The model score will become one signal inside the hybrid policy.
        """
    ),
    code(
        """
        USE_HF_MODEL = False
        MODEL_ID = "gravitee-io/distilbert-multilingual-toxicity-classifier"


        def load_toxicity_model():
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
            return pipeline("text-classification", model=model, tokenizer=tokenizer, truncation=True)


        def score_with_hf_model(texts, batch_size=32):
            pipe = load_toxicity_model()
            scores = []
            for start in range(0, len(texts), batch_size):
                batch = texts[start:start + batch_size]
                outputs = pipe(batch)
                for output in outputs:
                    label = str(output["label"]).lower()
                    score = float(output["score"])
                    scores.append(score if "toxic" in label else 1 - score)
            return scores


        if USE_HF_MODEL:
            df["external_toxicity_score"] = score_with_hf_model(df["text"].tolist())
        else:
            df["external_toxicity_score"] = np.nan
        """
    ),
    md("## Run Hybrid Moderation On Dataset"),
    code(
        """
        predictions = []

        for record in df.to_dict("records"):
            predictions.append(
                analyze_comment(
                    record["text"],
                    context_type=record["context_type"],
                    parent_review_rating=record["parent_review_rating"],
                    perfection_pct=record["movie_rating_perfection_pct"],
                    skip_pct=record["movie_rating_skip_pct"],
                    model_toxicity_score=record.get("external_toxicity_score")
                )
            )

        pred_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(predictions)], axis=1)
        display(pred_df[[
            "text", "moderation_action", "predicted_action", "target_detected", "target_detected_pred",
            "risk_score", "model_toxicity_score", "reason"
        ]].head(12))
        """
    ),
    md("## Metrics"),
    code(
        """
        print("Three-action report")
        print(classification_report(pred_df["moderation_action"], pred_df["predicted_action"], labels=ACTION_ORDER, zero_division=0))

        y_true_binary = pred_df["moderation_action"].map(lambda x: "safe" if x == "allow" else "unsafe")
        y_pred_binary = pred_df["predicted_action"].map(lambda x: "safe" if x == "allow" else "unsafe")

        print("Safe vs unsafe report")
        print(classification_report(y_true_binary, y_pred_binary, labels=["safe", "unsafe"], zero_division=0))

        harsh = pred_df[pred_df["labels_multi"].str.contains("harsh_criticism|actor_work_criticism", regex=True)]
        false_positive_rate = (harsh["predicted_action"] != "allow").mean() if len(harsh) else np.nan

        user_abuse = pred_df[pred_df["target_detected"].isin(["reviewer_or_user", "community_identity", "protected_class"])]
        abuse_recall = (user_abuse["predicted_action"] != "allow").mean() if len(user_abuse) else np.nan

        print(f"False positive rate on harsh criticism: {false_positive_rate:.3f}")
        print(f"Recall-like catch rate on person/group-targeted rows: {abuse_recall:.3f}")
        """
    ),
    code(
        """
        cm = confusion_matrix(pred_df["moderation_action"], pred_df["predicted_action"], labels=ACTION_ORDER)

        plt.figure(figsize=(7, 5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=ACTION_ORDER, yticklabels=ACTION_ORDER)
        plt.title("Confusion Matrix: Demo Policy Actions")
        plt.xlabel("Predicted")
        plt.ylabel("Expected")
        plt.show()
        """
    ),
    md(
        """
        ## Reading These Results

        False positives on harsh movie criticism matter because Moctale is a movie and TV discussion platform. The demo should not punish users for saying a film is boring, badly acted, weakly written, overhyped, or even profane when the target is clearly the movie or craft.

        Recall on user, reviewer, community, and protected-class abuse matters because reply threads are where disagreement can turn into harassment. The moderation system should catch likely person-directed abuse early enough for human review or removal recommendations.

        These are toy demo metrics on a small seed dataset. They are useful for policy walkthroughs, error analysis, and threshold tuning, but they are not production performance claims.
        """
    ),
    code(
        """
        metric_rows = []
        for label in ACTION_ORDER:
            metric_rows.append({
                "action": label,
                "precision": precision_score(pred_df["moderation_action"], pred_df["predicted_action"], labels=ACTION_ORDER, average=None, zero_division=0)[ACTION_ORDER.index(label)],
                "recall": recall_score(pred_df["moderation_action"], pred_df["predicted_action"], labels=ACTION_ORDER, average=None, zero_division=0)[ACTION_ORDER.index(label)],
                "f1": f1_score(pred_df["moderation_action"], pred_df["predicted_action"], labels=ACTION_ORDER, average=None, zero_division=0)[ACTION_ORDER.index(label)]
            })

        metric_df = pd.DataFrame(metric_rows)
        display(metric_df)

        metric_df.set_index("action")[["precision", "recall", "f1"]].plot(kind="bar", figsize=(8, 4), ylim=(0, 1), color=["#1976D2", "#00897B", "#C62828"])
        plt.title("Per-action Demo Metrics")
        plt.xlabel("")
        plt.ylabel("score")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.show()
        """
    ),
    md("## Admin-style Moderation Table"),
    code(
        """
        admin_cols = [
            "example_id", "text", "context_type", "parent_review_rating", "moderation_action",
            "predicted_action", "target_detected_pred", "predicted_category", "predicted_intent",
            "risk_score", "reason"
        ]

        review_queue = pred_df[pred_df["predicted_action"] != "allow"].sort_values(["predicted_action", "risk_score"], ascending=[False, False])
        display(review_queue[admin_cols].head(20))
        """
    ),
    md("## Live Demo Comments"),
    code(
        """
        demo_comments = pd.DataFrame([
            {
                "text": "This movie is shit but the issue is pacing, not the actors personally.",
                "context_type": "main_review",
                "parent_review_rating": "Skip",
                "movie_rating_perfection_pct": 91,
                "movie_rating_skip_pct": 3
            },
            {
                "text": "@reviewer tu chutiya hai, review dena band kar.",
                "context_type": "reply_to_review",
                "parent_review_rating": "Skip",
                "movie_rating_perfection_pct": 97,
                "movie_rating_skip_pct": 1
            },
            {
                "text": "You don't know history kiddo, but okay your opinion.",
                "context_type": "reply_to_review",
                "parent_review_rating": "Timepass",
                "movie_rating_perfection_pct": 76,
                "movie_rating_skip_pct": 9
            },
            {
                "text": "The dialogue delivery was weak and the climax felt lazy.",
                "context_type": "main_review",
                "parent_review_rating": "Skip",
                "movie_rating_perfection_pct": 69,
                "movie_rating_skip_pct": 18
            },
            {
                "text": "Go die if you think this movie is bad.",
                "context_type": "reply_to_comment",
                "parent_review_rating": "Perfection",
                "movie_rating_perfection_pct": 93,
                "movie_rating_skip_pct": 2
            },
            {
                "text": "Perfection dene wale log mand-buddhi hain.",
                "context_type": "reply_to_review",
                "parent_review_rating": "Perfection",
                "movie_rating_perfection_pct": 88,
                "movie_rating_skip_pct": 6
            }
        ])

        demo_predictions = []
        for record in demo_comments.to_dict("records"):
            demo_predictions.append(
                analyze_comment(
                    record["text"],
                    context_type=record["context_type"],
                    parent_review_rating=record["parent_review_rating"],
                    perfection_pct=record["movie_rating_perfection_pct"],
                    skip_pct=record["movie_rating_skip_pct"]
                )
            )

        demo_result = pd.concat([demo_comments, pd.DataFrame(demo_predictions)], axis=1)
        display(demo_result[["text", "predicted_action", "target_detected_pred", "risk_score", "reason_codes", "reason"]])
        """
    ),
    md(
        """
        ## What To Tell The Owner

        This is a low-cost moderation prototype. It is designed to flag likely abusive or borderline comments for review while allowing harsh movie criticism.

        Before production, it needs real consent-cleared Moctale data, moderator-reviewed labels, threshold calibration, and an appeal/human-review workflow.
        """
    )
]

nb["cells"] = cells
output_path = NOTEBOOKS / "moctale_moderation_ai_demo.ipynb"
nbf.write(nb, output_path)
print(output_path)
