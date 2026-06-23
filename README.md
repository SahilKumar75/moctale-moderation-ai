# Moctale Moderation AI

Moctale Moderation AI is a low-cost comment moderation prototype for a movie and TV review platform.

The goal is simple: catch abusive replies without blocking honest movie criticism.

Tags: `moderation-ai`, `hinglish`, `toxicity-detection`, `movie-reviews`, `kaggle-notebook`, `nlp`, `human-review`

On a review site, negative comments are normal. People should be able to say a movie is boring, badly paced, poorly acted, overhyped, or badly written. The problem starts when the comment turns into a direct attack on another user, reviewer, actor outside the movie context, or a community.

## What This Project Handles

- English, Hindi, Hinglish, and Indian-style mixed language comments
- Review replies and comment threads
- Harsh movie criticism that should stay visible
- Direct user abuse that should be flagged
- Borderline comments that should go to review
- Simple explanations for every decision
- Basic benchmark metrics for the demo

## Main Rule

The system should care about the target of the comment.

```text
"This movie is shit" -> allow
"You are shit" -> flag for removal
```

That difference is the core of the project.

## Planned Demo

The first version will be a Kaggle or Jupyter notebook.

It should let someone enter 10 to 15 comments at a time and return:

- moderation action
- abuse category
- intent label
- sentiment score
- toxicity score
- target detected
- confidence
- reason
- why it was not flagged, when allowed

The notebook should also show charts and a small admin-style moderation table.

## Dataset

The repo now includes a 500-row demo seed dataset:

`data/moderation_examples.csv`

Content note: the dataset contains examples of abusive and hostile language for moderation testing.

Current mix:

- 245 screenshot-inspired rows, rewritten from scratch
- 225 synthetic Moctale-style rows
- 30 sanitized open-source Jigsaw rows

The dataset is for demo evaluation and policy testing. It is not production training data, and metrics from it should not be described as production performance.

Useful docs:

- `docs/DATA_PROVENANCE.md`
- `docs/dataset_card.md`
- `docs/labeling_guidelines.md`
- `docs/model_plan.md`
- `docs/synthetic_generation.md`

## Model Choice

The current best practical model candidate is:

`gravitee-io/distilbert-multilingual-toxicity-classifier`

Why it fits:

- multilingual
- tested on Hindi and Hinglish
- lighter than XLM-R large models
- usable in Kaggle
- has a quantized ONNX path for later production work

It should not be used alone. The model is only one signal inside a larger Moctale-specific moderation system.

## Hybrid Approach

The planned system combines:

- cheap text cleanup
- sentiment gate
- reply and mention risk
- rating disagreement risk
- target detection
- multilingual toxicity model
- Hinglish abuse rules
- custom decision logic
- explanation layer

This keeps costs down because the deeper checks only run on risky comments.

## Actions

```text
allow
flag_for_review
flag_for_removal
```

## Metrics To Show

- accuracy
- precision
- recall
- F1 score
- confusion matrix
- safe vs unsafe performance
- allow vs review vs removal performance

## Notebook

The first notebook has been generated locally at:

`notebooks/moctale_moderation_ai_demo.ipynb`

## Run On Kaggle

1. Create a Kaggle Notebook.
2. Upload `data/moderation_examples.csv` as an input dataset, or upload this repository as a Kaggle dataset.
3. Import or upload `notebooks/moctale_moderation_ai_demo.ipynb`.
4. Keep `USE_HF_MODEL = False` for the fast offline demo.
5. Run all cells.

Expected demo behavior:

- harsh movie criticism stays allowed
- likely user/reviewer abuse is flagged
- charts, toy metrics, and an admin-style moderation table are shown

Optional: set `USE_HF_MODEL = True` only if Kaggle internet is enabled and you want to test the Hugging Face toxicity model as an extra signal.
