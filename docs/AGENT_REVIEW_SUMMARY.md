# Agent Review Summary

This project was reviewed from five angles before dataset implementation.

## AI Engineer

Main point: do not treat toxicity as the product label.

The model should answer how toxic a comment looks. Moctale Moderation AI should answer whether the comment is abusive toward a person or community, or only harsh criticism of movie content.

Recommendations:

- Use multi-field labels, not one binary label.
- Keep `target_detected` as a first-class field.
- Use `gravitee-io/distilbert-multilingual-toxicity-classifier` as a baseline signal.
- Avoid fine-tuning on only 500 rows.
- Use the 500 rows for evaluation, threshold calibration, and error analysis.
- Track false positives on harsh movie criticism separately.

## Data Engineer

Main point: provenance and quality checks matter as much as row count.

Recommendations:

- Use explicit `source_type`: `open_source`, `screenshot_inspired`, `synthetic`.
- Do not publish raw screenshot text, usernames, handles, timestamps, avatars, or private identifiers.
- Use stable IDs and scenario IDs.
- Include a data dictionary.
- Validate schemas, splits, labels, duplicates, and PII risk.
- Treat this as a demo benchmark, not a production corpus.

## Software Architect

Main point: use a staged hybrid moderation pipeline.

Recommended flow:

```text
comment ingest
-> normalize text
-> language/script detection
-> Hinglish abuse rule pass
-> cheap sentiment/risk gate
-> target detection
-> selective toxicity model
-> policy decision
-> explanation and audit event
```

Key architecture decision:

- Keep models, rules, and policy separate.
- Run heavier toxicity inference only on risky comments.
- Use batch processing to fit the 2-5 minute cost and latency target.
- Keep human review for ambiguous and high-impact cases.

## Product Manager

Main point: the demo should prove one thing clearly.

Moctale Moderation AI should preserve passionate movie debate while reducing abuse toward people.

Owner demo should show:

- 500 labeled examples.
- Harsh criticism that is allowed.
- User/reviewer abuse that is flagged.
- Target-aware explanations.
- Charts and a simple admin-style review table.
- Honest metrics and error analysis.

## Reality Check And AppSec

Main point: do not overclaim and do not publish private user content.

Controls:

- Keep live screenshots private.
- Use rewritten screenshot-inspired rows.
- Add provenance docs.
- Avoid claims like production-ready, accurate, or automatic removal.
- Label metrics as demo metrics unless evaluated on real consent-cleared Moctale data.
- Treat removal as a recommendation until owner policy, appeals, and human review exist.
- Avoid unsafe model artifacts and leaked secrets in the repo.

## Resulting Implementation

The first dataset is a 500-row public demo seed set:

- 245 screenshot-inspired rows, rewritten from scratch.
- 225 synthetic Moctale-style rows.
- 30 sanitized open-source Jigsaw rows with provenance.

It is designed for notebook demos, target-aware rule testing, and small benchmark-style reporting. It is not production training data.

