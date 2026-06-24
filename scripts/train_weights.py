"""Train risk weight coefficients from labeled dataset.

Fits a simple logistic regression on the moderation_examples.csv dataset
using binary heuristic signals as features. Outputs config/risk_weights.yaml
with learned coefficients.

Usage:
    python scripts/train_weights.py
    python scripts/train_weights.py --dataset data/moderation_examples.csv --out config/risk_weights.yaml
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_dataset(path: Path) -> tuple[list[list[float]], list[str]]:
    """Load CSV dataset and extract binary feature vectors."""
    from moctale_moderation import ModerationEngine, ModerationRequest
    from moctale_moderation.engine import normalize_text, token_set

    engine = ModerationEngine()
    features: list[list[float]] = []
    labels: list[str] = []

    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows from {path}")

    for row in rows:
        if not row.get("text") or not row.get("moderation_action"):
            continue
        label = str(row["moderation_action"]).strip().lower()
        if label not in ("allow", "flag_for_review", "flag_for_removal"):
            continue

        text = str(row["text"])
        context_type = str(row.get("context_type", "reply_to_review"))
        normalized = normalize_text(text)
        tokens = token_set(normalized)

        # Binary features
        is_reply = 1.0 if context_type in ("reply_to_review", "reply_to_comment") else 0.0
        has_mention = 1.0 if "usermention" in tokens else 0.0
        htox = engine.heuristic_toxicity(normalized, tokens)

        from moctale_moderation.engine import sentiment_signal
        sent_label, _ = sentiment_signal(normalized, tokens)
        neg_sent = 1.0 if sent_label == "negative" else 0.0

        features.append([is_reply, has_mention, neg_sent, htox])
        labels.append(label)

    return features, labels


def simple_logistic_regression(
    X: list[list[float]],
    y_binary: list[int],
    lr: float = 0.1,
    epochs: int = 200,
) -> list[float]:
    """Train logistic regression via gradient descent. Returns weights."""
    n_features = len(X[0])
    weights = [0.0] * n_features
    bias = 0.0

    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))

    for epoch in range(epochs):
        grad_w = [0.0] * n_features
        grad_b = 0.0
        for features, label in zip(X, y_binary):
            pred = sigmoid(sum(w * f for w, f in zip(weights, features)) + bias)
            err = pred - label
            for i, f in enumerate(features):
                grad_w[i] += err * f
            grad_b += err
        n = len(X)
        weights = [w - lr * g / n for w, g in zip(weights, grad_w)]
        bias -= lr * grad_b / n

    return weights


def main() -> None:
    parser = argparse.ArgumentParser(description="Train risk weights from labeled dataset")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "moderation_examples.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "config" / "risk_weights.yaml")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}")
        sys.exit(1)

    features, labels = load_dataset(args.dataset)
    if not features:
        print("No labeled rows found in dataset")
        sys.exit(1)

    # Binary: flagged (review + removal) vs allowed
    binary = [0 if l == "allow" else 1 for l in labels]
    weights = simple_logistic_regression(features, binary)

    feat_names = ["reply_context_base", "has_mention", "negative_sentiment", "toxicity_scale"]
    print("\nLearned weights:")
    for name, w in zip(feat_names, weights):
        print(f"  {name}: {w:.4f}")

    # Write YAML
    import yaml
    config = {
        "version": "1.1",
        "trained_on": str(args.dataset),
        "weights": {
            "reply_context_base": round(max(0.05, min(0.40, weights[0])), 4),
            "main_review_base": 0.05,
            "has_mention": round(max(0.05, min(0.30, weights[1])), 4),
            "negative_sentiment": round(max(0.05, min(0.30, weights[2])), 4),
            "toxicity_scale": round(max(0.30, min(0.65, weights[3])), 4),
        },
        "thresholds": {
            "flag_for_review_risk": 0.62,
            "flag_for_review_model": 0.82,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"\nWrote weights to {args.out}")


if __name__ == "__main__":
    main()
