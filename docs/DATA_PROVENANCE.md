# Data Provenance

This repository contains a 500-row demo dataset for Moctale Moderation AI.

The dataset is designed to test moderation policy and notebook behavior. It is not a production training corpus.

## Source Types

### `synthetic`

Rows written from scratch to cover moderation cases needed for a movie and TV review platform.

Examples include:

- Harsh but allowed movie criticism.
- Actor performance criticism.
- Neutral discussion.
- Threat-like comments.
- Sensitive-topic comments.

### `screenshot_inspired`

Rows inspired by patterns seen in Moctale-style screenshots, but rewritten from scratch.

Important:

- No raw screenshot text is copied.
- No usernames are retained.
- No handles are retained.
- No timestamps are retained.
- No avatars or profile identifiers are included.
- Wording is generalized into moderation scenarios.

### `open_source`

Rows sampled from:

`thesofakillers/jigsaw-toxic-comment-classification-challenge`

Source:

https://huggingface.co/datasets/thesofakillers/jigsaw-toxic-comment-classification-challenge

License note from dataset card:

The Toxic Comment Classification dataset is redistributed as permitted under CC0, with underlying comment text sourced from Wikipedia comments governed by Creative Commons Attribution-ShareAlike 3.0.

In this repo, open-source rows are:

- limited to a small sample
- sanitized for links, IP-like strings, and handles
- marked with source fields
- not treated as Moctale-native data

## What Is Not Included

This dataset does not include:

- raw Moctale exports
- raw screenshots
- usernames
- profile handles
- profile images
- email addresses
- phone numbers
- private messages
- live user identifiers

## Why Not Use Raw Screenshots

Screenshots can contain identifiable user content. Publishing exact comments or handles from screenshots would create privacy and rights risk.

For this reason, screenshot rows are rewritten as scenario-inspired examples only.

## Intended Use

Use this dataset for:

- Kaggle or Jupyter demo notebooks
- target-aware moderation logic
- product walkthroughs
- small toy metrics
- rule and threshold testing

Do not use this dataset to claim production performance.

## Before Production

Before production use, Moctale should create a separate private dataset from consent-cleared, policy-approved, labeled platform data.

