# Model Plan

## Recommended Baseline Model

`gravitee-io/distilbert-multilingual-toxicity-classifier`

Why:

- multilingual
- Hindi and Hinglish evaluation reported on the model card
- lighter than XLM-R large models
- usable in Kaggle
- binary toxicity score is enough as one signal
- ONNX path can help later production cost

## Important Limitation

The model should not decide final moderation action alone.

It detects toxicity. It does not fully understand Moctale policy.

Example:

```text
This movie is shit.
```

A toxicity model may flag that as toxic, but Moctale should allow it because the target is the movie.

## Hybrid Decision

Use:

- text normalization
- sentiment/risk gate
- target detection
- Hinglish abuse rules
- toxicity model score
- policy decision layer
- explanation output

## Evaluation

Report:

- false positive rate on harsh movie criticism
- recall on direct user abuse
- precision on removal recommendations
- F1 for safe vs unsafe
- F1 for allow vs review vs removal
- confusion matrix
- language-mix breakdown

Use careful wording:

These are demo metrics on a small seed dataset, not production performance.

