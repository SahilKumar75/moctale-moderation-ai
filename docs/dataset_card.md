# Dataset Card

## Dataset Name

Moctale Moderation AI Demo Dataset

## Size

500 rows.

## Purpose

This dataset supports a prototype moderation notebook for a movie and TV review platform.

The main moderation problem is target-aware:

```text
"This movie is shit" -> allow
"You are shit" -> flag
```

The dataset is built to test that distinction.

## Languages

The dataset includes:

- English
- Hinglish in Latin script
- small Hindi/Hinglish-style examples

It is not representative of all Indian languages.

## Labels

Main action labels:

- `allow`
- `flag_for_review`
- `flag_for_removal`

Primary labels:

- `safe`
- `borderline`
- `unsafe`

Important supporting fields:

- `target_detected`
- `abuse_category`
- `intent_label`
- `severity`
- `language_mix`
- `source_type`
- `rationale_short`

## Source Mix

Current generated mix:

- screenshot-inspired rewritten examples
- synthetic examples
- sanitized open-source Jigsaw examples

See `docs/DATA_PROVENANCE.md` for details.

## Intended Use

Good uses:

- demo notebook
- policy walkthrough
- rule testing
- target-aware moderation evaluation
- baseline metric examples

Bad uses:

- production moderation claims
- final model training
- legal or compliance certification
- fully automated removal decisions
- benchmarking across Indian languages

## Known Limitations

- Synthetic and screenshot-inspired data may not match real platform distribution.
- Hinglish coverage is useful for a demo, but not exhaustive.
- Open-source examples are not movie-platform native.
- Severe protected-class slurs are minimized, so hate-speech model behavior is not fully stress-tested.
- Metrics from this dataset are toy metrics unless validated against real consent-cleared Moctale data.

## Human Review

Removal should be treated as a recommendation until owner policy, moderator workflow, appeal handling, and production evaluation are defined.

