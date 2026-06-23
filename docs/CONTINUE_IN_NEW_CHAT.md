# Continue In New Chat

This file is the handoff note for continuing Moctale Moderation AI in a fresh chat.

## Current Repo

Local path:

`/Users/sahilkumarsingh/Desktop/Moctale Moderation AI`

GitHub repo:

`https://github.com/SahilKumar75/moctale-moderation-ai`

## Current State

Already done:

- Created public GitHub repo.
- Added project README and full project brief.
- Built a 500-row demo moderation dataset.
- Added data provenance, dataset card, labeling guide, model plan, and agent review summary.
- Added dataset builder and validator scripts.
- Generated the first Kaggle/Jupyter notebook.

Generated but not yet committed at this handoff:

- `notebooks/moctale_moderation_ai_demo.ipynb`
- `scripts/create_notebook.py`

## Dataset

Main dataset:

`data/moderation_examples.csv`

Rows:

- 500 total
- 287 `allow`
- 114 `flag_for_review`
- 99 `flag_for_removal`
- 326 Hinglish-style rows
- 174 English rows

Source mix:

- 245 screenshot-inspired rows, rewritten from scratch
- 225 synthetic Moctale-style rows
- 30 sanitized open-source Jigsaw rows

Validation passed with:

```bash
python3 scripts/validate_dataset.py
```

Expected output:

```text
PASSED
```

## Notebook

Notebook path:

`notebooks/moctale_moderation_ai_demo.ipynb`

Generator:

`scripts/create_notebook.py`

Regenerate notebook:

```bash
python3 scripts/create_notebook.py
```

The notebook currently:

- loads `data/moderation_examples.csv`
- shows dataset distributions
- implements a hybrid moderation engine
- has optional Hugging Face model code
- runs with `USE_HF_MODEL = False` by default
- shows toy metrics
- displays an admin-style moderation table
- includes live demo comments

## Notebook Verification Already Done

The notebook code cells were executed locally through a lightweight Python runner because `nbconvert` and `nbclient` were not installed.

The notebook ran successfully after fixing indentation and live-demo argument handling.

Observed demo metrics from the first rule pass:

```text
Three-action accuracy: 0.73
False positive rate on harsh criticism: 0.000
Catch rate on person/group-targeted rows: 0.434
```

Interpretation:

- Good: it preserves harsh movie criticism.
- Needs work: it is too conservative and misses too much user/group abuse.

## Next Work To Do

Do not ask more discovery questions unless necessary. Continue implementation.

Recommended next steps:

1. Tune the hybrid decision rules in `scripts/create_notebook.py`.
2. Regenerate the notebook.
3. Re-run notebook code cells.
4. Improve catch rate on `reviewer_or_user`, `community_identity`, and `protected_class` rows.
5. Keep false positive rate on harsh movie criticism near zero.
6. Add a short result summary section in the notebook explaining:
   - why false positives on movie criticism matter
   - why recall on user/reviewer abuse matters
   - why metrics are toy demo metrics only
7. Commit and push the notebook and generator.

## Specific Rule Tuning Ideas

The first pass was too weak on abuse catch rate because the rule logic did not use existing dataset labels enough as examples of desired behavior.

Improve target detection:

- Treat `@user`, `you`, `tu`, `tum`, `tera`, `teri`, `reviewer`, `people`, `fans`, `log`, `kiddo`, `buddy` as stronger person/group signals when paired with negative or insulting terms.
- Treat `perfection dene wale`, `skip gang`, `people in comments`, and `fanbase` as community/group targets.
- Treat `review dena band kar`, `stop reviewing`, `get some brain`, `chup`, `real id se aao`, and `attention seeker` as review-worthy reply patterns.

Improve abuse detection:

- Expand soft abuse rules for Hinglish and English:
  - `bewakoof`
  - `gadha`
  - `idiot`
  - `clown`
  - `mand-buddhi`
  - `attention seeker`
  - `brain dead`
  - `trash taste`
  - `stupid`
  - `dumb`
- Keep severe abuse/acronyms as removal:
  - `chutiya`
  - `tmkc`
  - `mkl`
  - `bkl`
  - `teri maa`
  - `madarchod`

Keep allowed:

- negative movie terms when target is movie/craft:
  - `shit movie`
  - `bakwas film`
  - `weak acting`
  - `boring pacing`
  - `lazy script`
  - `bad direction`

## Model Plan

Keep the main model candidate:

`gravitee-io/distilbert-multilingual-toxicity-classifier`

Use it as a toxicity signal only, not the final decision-maker.

Notebook default should remain:

```python
USE_HF_MODEL = False
```

This keeps the demo runnable without internet or model download. The user can enable it in Kaggle later.

## Important Wording

Use:

- low-cost moderation prototype
- context-aware abuse-risk demo
- flags likely abusive or borderline comments for review
- toy metrics on a small demo set
- distinguishes harsh movie criticism from user-directed abuse

Avoid:

- production-ready
- accurate moderation AI
- automatically removes abusive comments
- safe for all Indian-language content
- replacement for human moderators

## Commit Status At Handoff

Run:

```bash
git status --short
```

Expected uncommitted files at this handoff:

```text
?? notebooks/
?? scripts/create_notebook.py
```

After tuning and verifying the notebook, commit with something like:

```bash
git add notebooks/moctale_moderation_ai_demo.ipynb scripts/create_notebook.py
git commit -m "Add Kaggle moderation demo notebook"
git push
```
