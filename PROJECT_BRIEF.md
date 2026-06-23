# Text-Buster: Abuse Detection Demo Brief

## Project Goal

Build a low-cost demo for detecting abusive comments on a movie / TV recommendation and review platform. The demo will likely be a Kaggle / Jupyter notebook where comments can be entered, analyzed, flagged, explained, and shown visually with charts, labels, and metrics.

Important correction from the conversation: this is a moderation **model/system**, not a UI modal.

## Platform Context

The owner website is a movie and TV show recommendation and review site. Comments appear in multiple places:

- Under each movie or TV show.
- Under user reviews.
- In topic/feed discussions, such as a FIFA topic.
- As replies to comments and reviews.

The main abuse risk appears to be higher in replies and comment threads than in the original review itself. Abuse often happens when users have strong opposite opinions, especially around the site's rating matrix:

- Perfection
- Go For It
- Timepass
- Skip

Example risk scenario:

If a movie has 97 percent `Perfection` and 1 percent `Skip`, then a `Skip` review may attract hostile replies from users with the opposite opinion.

## Constraints

- The owner does not have enough funding for an expensive moderation system.
- Avoid paid API calls for every comment.
- Avoid hosting a heavy model that creates high AWS compute cost.
- The solution should be financially cheap.
- The system should still address comments within roughly 2-5 minutes.
- The first deliverable is only a demo.
- Later, if the owner likes it, the demo can be converted into production form.

## Demo Format

The preferred demo format is a Kaggle / Jupyter notebook.

The user wants to:

- Add a comment as input.
- Add replies as input.
- Test multiple comments later.
- Show output visually.
- Include text labels, charts, and a moderation table.
- Process around 10-15 comments at a time in the demo.
- Include Hinglish, Hindi, English, and Indian-language style examples.
- Include benchmark-style metrics like F1 score.

## Questions Asked And Answers Given

### 1. What's this for -- where do these comments live?

Answer: A website/app the user is building.

### 2. How do you want to detect abuse?

Answer: Not sure. The user wanted a recommendation.

### 3. What should happen when abuse is detected?

Answer: The owner has not given the correct direction yet. In the end, they want abusive comments removed, but the system has to be sure.

### 4. What's the website backend built with or planned to be?

Answer: Unknown. The user does not know the owner website stack. The current goal is only to show a demo. The site is a movie and TV recommendation and review site. Comments appear under movies, TV shows, topics/feeds, and replies to reviews.

### 5. What languages will comments mostly be in?

Answer: The main user base is Indian, so comments may be in Indian languages, English, and mainly Hinglish.

### 6. Roughly how many comments per day are we designing for?

Answer: Unknown. This is only for a demo, and there are cost constraints.

### 7. What format should the demo take?

Answer: A Jupyter/Kaggle notebook should be enough. The user will put comments and replies in it and test comments later. If the owner likes it, it can be converted into a usable form.

### 8. What is the main constraint?

Answer: The owner does not have enough funding. The solution cannot rely on paid API keys for every comment. It should not run a heavy model on the server. The owner may use AWS, so inference and compute cost matter. The system should be cheap and should address comments within 2-5 minutes.

### 9. What kinds of abuse matter most?

Answer: All types of abusive comments.

Categories to include:

- Personal attack
- Hate or identity attack
- Threat or violence
- Sexual abuse
- Profanity
- Spam or promotion, although later the user clarified the first demo should focus only on abuse
- Harassment
- Political or religious abuse
- Doxxing or private information
- Self-harm related
- Non-abusive

### 10. Should normal profanity always be removed?

Answer: No. If profanity is used for movie criticism and is not attacking a person, it should stay.

Example:

- "This movie is shit" should be allowed.
- "You are shit" should be flagged.

### 11. Should we remove only abusive words or remove the full comment?

Answer: The user is not sure yet. For now, the demo should give flagged data and let the owner decide.

### 12. What should happen to borderline comments?

Answer: The user initially did not know what borderline means. Later decision: borderline or unclear aggressive comments should be flagged for review.

### 13. Should detection happen before posting or after posting?

Answer: The owner is not clear yet. For now, make an assumption. Recommended assumption: after-posting moderation, with background scanning and flagging within 2-5 minutes.

### 14. Is human review possible?

Answer: For the demo, just show flagged data so the owner can see the model works. Later it can be optimized based on owner needs.

### 15. Should the demo show confidence scores and reasons?

Answer: Yes, definitely. Also add user intent and bot/human language if useful.

### 16. Should we discuss feasibility/usefulness of open-source models?

Answer: Yes. The user wants to discuss how feasible and useful they are for the user's and owner's Moctale website needs.

### 17. What machine will the demo run on?

Answer: Kaggle notebook.

### 18. Do you have sample abusive and non-abusive comments?

Answer: The owner has not given a dataset. The user can share screenshots to show how comments look on the website.

### 19. Should the demo include abuse categories?

Answer: Yes.

### 20. Should the notebook classify comments into three actions?

Answer: Yes.

Actions:

- `allow`
- `flag_for_review`
- `flag_for_removal`

### 21. Should movie-related criticism be acceptable?

Answer: Yes. Comments about the movie, show, acting, script, story, coloring, set, pacing, direction, dialogues, and related craft should be acceptable.

### 22. Should comments unrelated to the movie/show be treated differently?

Answer: Yes. If the negativity is not related to the movie/show or craft, it becomes more suspicious.

### 23. What is the most important abuse area?

Answer: Replies to user reviews. Abuse toward a reviewer or commenter is the main concern.

### 24. Should "this movie is shit" stay but "you are shit" be flagged?

Answer: Yes.

### 25. Are intent labels useful?

Answer: Yes. Add these and more if useful.

Useful intent labels:

- Opinion
- Criticism
- Insult
- Threat
- Trolling
- Harassment
- Spam
- Normal discussion
- Support request
- Bot-like

### 26. Should bot/human language be a separate score?

Answer: Yes, add a separate score.

### 27. What kind of Kaggle demo is preferred?

Answer: The user will add input and show output visually with charts, text, etc.

### 28. Should the demo include Hinglish examples?

Answer: Yes.

### 29. Should criticism of actors/directors/creators be treated less strictly than criticism of normal users?

Answer: If the user is criticizing the actor's acting, script, story, coloring, set, pacing, direction, dialogues, or anything related to the movie/show, it is fine. If it is unrelated to the movie/show, it should not be treated as normal criticism.

### 30. Should abuse toward public figures be allowed, reviewed, or removed?

Answer: Allow harsh criticism if related to the movie/show. Do not allow unrelated abuse.

### 31. Should religion/politics mentions be flagged even if not abusive?

Answer: No. Allow them until there is abuse.

### 32. Should sexually vulgar Hinglish/Hindi gaali always be flagged?

Answer: If directed to a user/reviewer/person, it is bad and should be flagged. Direct severe abuse should be removal.

### 33. Should the demo show why a comment was allowed?

Answer: Yes. It should show why not flagged.

### 34. Should the notebook include an admin moderation table?

Answer: Yes.

### 35. Should the notebook process one comment or a batch?

Answer: Batch of 10-15 comments at a time.

### 36. Should screenshots be manually converted into sample rows?

Answer: The user will share as much as possible, but may need online, open-source, or synthetic data. Screenshots are being used to give an idea.

### 37. Should usernames/reviewer names be included as context?

Answer: Yes, if it helps flag more accurately and precisely.

### 38. Is using a small open-source model plus rule logic okay?

Answer: Yes. Also add metrics like F1 score to show benchmark performance if making our own model, using someone else's, or using a combined approach.

### 39. Should the benchmark test set be synthetic only or mixed?

Answer: The demo can use examples inspired by screenshots plus synthetic/open-source style data. The user will share references, and the first prototype can use synthetic data.

### 40. Should the demo be 3-class or binary?

Answer: Show both:

- `safe` vs `unsafe`
- `allow` vs `flag_for_review` vs `flag_for_removal`

### 41. What is more important: not removing valid criticism or catching every abusive comment?

Answer: The policy became: allow movie/show criticism even if negative. Abuse toward users/reviewers should be flagged. Unclear aggressive comments go to review.

### 42. Should the notebook include cost-saving moderation architecture?

Answer: Yes.

### 43. Should the demo compare approaches?

Answer: Recommended:

- Rule-only baseline
- Model-only
- Hybrid rules + model

### 44. Should the demo include fake cost explanation?

Answer: Yes, in principle. The low-cost story matters: no paid API call per comment, batch process comments, and only deep-scan risky comments.

### 45. Should output include context type?

Answer: Yes.

Context types:

- `main_review`
- `reply_to_review`
- `reply_to_comment`
- `topic_feed`

### 46. Should comments like "Dhruv bhai real id se aao" be allowed, review, or trolling?

Answer: The user later clarified mild things like this should not be flagged if not abusive, but aggressive borderline comments can go to review. Focus on abuse.

### 47. Should comments like "attention grab hi lag raha hai" be allowed or reviewed?

Answer: User said the core is sentiment/risk. If negative, deep dive. If it attacks a user/reviewer's intent and is borderline, flag for review.

### 48. Should Indian-language romanized abuse words be in the rule layer?

Answer: Yes, because it helps Hinglish, but the demo should avoid blindly flagging non-abusive mentions.

### 49. Is the user okay if the first demo is not perfect ML but a strong prototype?

Answer: Yes.

### 50. Should "chup hoja" / "shut up" be review or removal?

Answer: It will not be flagged as removal. It should show why not flagged unless the context becomes abusive.

### 51. Should "you don't know history kiddo" be allowed or reviewed?

Answer: Will not flag. Show why not flagged.

### 52. Should comments attacking a group like "mand-buddhi people in comments" be removal or review?

Answer: Flag for review.

### 53. Should short abusive acronyms like TMKC, MKL, BKL always be removal?

Answer: Yes, flag for removal.

### 54. Should fake account / impersonation accusations be a moderation category?

Answer: No, not in this demo.

### 55. Should spam/self-promotion links be included?

Answer: No, only abuse for now.

### 56. Should metrics show safe vs unsafe and three actions?

Answer: Yes, both.

### 57. Should output include `target_detected`?

Answer: Yes.

### 58. Should religious/political debate be allowed unless direct abuse occurs?

Answer: Yes. Allowed until abuse.

### 59. Is the user ready to create the notebook?

Answer: Yes, but before jumping into implementation, create a folder on Desktop and save this brief with all questions, answers, and the latest algorithm.

## Important Moderation Policy

### Allow

Allow harsh criticism when it targets movie/show content or craft:

- Acting
- Script
- Story
- Coloring
- Set design
- Pacing
- Direction
- Dialogues
- Cinematography
- VFX
- Songs
- Casting
- Review content, if phrased as criticism rather than abuse

Examples:

- "This movie is shit" -> allow / profane but allowed
- "The acting was terrible" -> allow
- "The direction was awful" -> allow
- "The pacing is unbearable" -> allow
- "The review is badly argued" -> allow or review depending on tone

### Flag For Review

Use review for borderline or unclear aggressive comments:

- Mild personal attacks
- Trolling
- Aggressive but not severe replies
- Attacks on a reviewer's intent
- Group insults that are not severe enough for direct removal
- Comments with negative sentiment and unclear target

Examples:

- "This reviewer is attention hungry" -> review
- "Mand-buddhi people in comments" -> review
- "Real id se aao" -> likely trolling/review if context is hostile
- "Chup hoja" -> usually not removal; may be review if hostile thread context

### Flag For Removal

Use removal for direct abuse:

- Severe personal abuse
- Sexual gaali directed at a user/person
- Threats
- Hate or identity abuse
- Severe harassment
- Direct abusive acronyms like TMKC, MKL, BKL

Examples:

- "You are shit" -> removal
- "Teri maa..." style direct abuse -> removal
- "TMKC" -> removal
- "MKL" -> removal
- "BKL" -> removal

### Do Not Flag

Do not flag only because a comment is:

- Negative
- A harsh movie opinion
- About politics/religion without abuse
- A disagreement
- Mildly dismissive without abuse
- Accusing a movie of being bad, boring, overhyped, loud, messy, or poorly acted

The demo should also show why comments are **not flagged**, not only why they are flagged.

## Reference Observations From Screenshots

The screenshots showed the platform has a dark review/comment UI with:

- A review on the left side.
- Comments/replies on the right side.
- Usernames and replies with `@username`.
- Rating tags such as `Skip`, `Timepass`, and `Perfection`.
- Like counts and comment counts.
- Many Hinglish comments.
- Some direct abuses and some valid harsh criticism.

Patterns observed:

- Main reviews often contain harsh movie criticism but are usually about the movie/show.
- Replies are more likely to contain direct user attacks.
- Direct `@username` replies increase risk.
- Extreme disagreement around ratings creates higher risk.
- Abuse may be short, acronym-based, or Hinglish.
- Negative comments about movie craft should remain allowed.
- Negative comments aimed at users or reviewers should be flagged.

## Recommended Output Schema

Each analyzed comment should output:

- `comment_id`
- `comment_text`
- `context_type`
- `parent_review_rating`
- `movie_rating_distribution`
- `has_mention`
- `target_detected`
- `sentiment_label`
- `sentiment_score`
- `risk_score`
- `toxicity_score`
- `personal_attack_score`
- `profanity_score`
- `bot_likelihood_score`
- `abuse_category`
- `intent_label`
- `action`
- `confidence`
- `reason`
- `why_not_flagged`, when action is `allow`

## Categories

Abuse categories:

- `personal_attack`
- `hate_or_identity_attack`
- `threat_or_violence`
- `sexual_abuse`
- `profanity`
- `harassment`
- `political_religious_abuse`
- `doxxing_or_private_info`
- `self_harm_related`
- `non_abusive`

Intent labels:

- `opinion`
- `criticism`
- `insult`
- `threat`
- `trolling`
- `harassment`
- `normal_discussion`
- `support_request`
- `bot_like`

Actions:

- `allow`
- `flag_for_review`
- `flag_for_removal`

Target labels:

- `movie_show`
- `acting_direction_script`
- `actor_public_figure`
- `review_content`
- `reviewer_or_user`
- `community_identity`
- `unknown`

Context labels:

- `main_review`
- `reply_to_review`
- `reply_to_comment`
- `topic_feed`

## Latest Recommended Algorithm

The core algorithm should be a **hybrid risk-based moderation system**, not just a model.

The user's idea of starting with sentiment analysis is good, but sentiment should not be the final decision-maker. Negative sentiment is often valid on a movie review platform.

Example:

- "This movie is terrible" -> negative but allowed
- "Your review is terrible, you idiot" -> negative plus personal attack

### Step 1: Cheap Pre-Filter

Clean and normalize text:

- Lowercase
- Normalize repeated characters
- Normalize common Hinglish spellings
- Detect `@username` mentions
- Detect direct replies
- Detect links, although spam is not the focus of this first demo
- Detect short abusive acronyms

### Step 2: Context Risk Score

Give higher risk to comments with:

- `reply_to_review`
- `reply_to_comment`
- Direct `@username` mention
- Negative sentiment
- Severe abuse-like tokens
- Extreme rating disagreement zones
- Threads where one rating is heavily dominant and opposite opinion is being attacked

Example:

If a movie has 97 percent `Perfection` and someone posts a `Skip` review, replies under that review are higher risk because opposite-opinion conflict is more likely.

### Step 3: Sentiment Gate

Use sentiment as a cheap gate:

- If sentiment is positive/neutral and there are no abuse signals, allow quickly.
- If sentiment is negative/aggressive, deep scan.

Do not flag just because sentiment is negative.

### Step 4: Target Detection

Detect what the negativity is aimed at:

- Movie/show/craft -> usually allow
- Actor/director in relation to performance/craft -> usually allow
- Review content -> allow or review depending on tone
- Reviewer/user/commenter -> review or removal
- Community/religion/caste/gender -> review or removal
- Unknown target with aggression -> review

This is the most important distinction:

- "Movie is shit" -> allow
- "You are shit" -> removal

### Step 5: Abuse Detection

Check for:

- Personal insults
- Sexual abuse
- Threats
- Harassment
- Identity attack
- Hinglish/Hindi gaali
- Abusive acronyms
- Repeated hostile replies

### Step 6: Action Decision

Decision policy:

```text
allow:
negative but about movie/show/craft

flag_for_review:
mild personal attack, trolling, unclear aggressive target, group insult

flag_for_removal:
direct abuse, sexual gaali, threats, identity abuse, severe harassment, severe abusive acronyms
```

### Step 7: Explainability

Always output why:

```text
Allowed because negative words target movie/craft, not a user.
Flagged for review because the comment is aggressive and targets people in the comment section.
Flagged for removal because the comment contains severe Hinglish abuse directed at another user.
```

Also show `why_not_flagged` for allowed comments.

### Step 8: Cost-Saving Production Idea

Run full checks only on risky comments:

- Replies
- Mentions
- Negative sentiment
- Extreme rating disagreement zones
- Comments with abuse-like tokens

Use batch processing every 2-5 minutes instead of real-time paid API calls per comment.

## Proposed Notebook Sections

1. Project introduction
2. Moderation policy
3. Sample comments and context
4. Text normalization
5. Risk scoring
6. Sentiment gate
7. Target detection
8. Abuse rule layer
9. Optional lightweight model section
10. Hybrid decision function
11. Demo input: 10-15 comments
12. Admin moderation table
13. Charts:
    - Allowed vs review vs removal
    - Category breakdown
    - Risk score distribution
    - Sentiment vs moderation action
14. Metrics:
    - Safe vs unsafe accuracy, precision, recall, F1
    - 3-action accuracy, precision, recall, F1
    - Confusion matrix
15. Cost-saving architecture explanation
16. Limitations and next steps

## Metrics To Show

Show both binary and 3-class metrics.

Binary:

- `safe`
- `unsafe`

Three-action:

- `allow`
- `flag_for_review`
- `flag_for_removal`

Metrics:

- Accuracy
- Precision
- Recall
- F1 score
- Confusion matrix
- Category-wise performance if enough sample labels exist

Important explanation:

- Precision means: when the system flags a comment, how often it is right.
- Recall means: how many abusive comments the system catches.
- F1 balances precision and recall.

For this platform, the demo should prioritize:

1. Not removing valid movie/show criticism.
2. Catching direct user/reviewer abuse.
3. Sending uncertain aggressive comments to review.

## Key Demo Message To Owner

This is not a simple profanity blocker. It is a low-cost, context-aware moderation prototype.

It saves computation by using cheap signals first:

- Sentiment
- Reply/mention context
- Rating-disagreement risk
- Target detection
- Abuse token/rule detection

Then it deep-scans only risky comments.

The important demo distinction:

```text
"This movie is shit" -> allowed because the target is the movie.
"You are shit" -> flagged because the target is a user.
```

## Model Research Decision

The best practical model to combine with the custom Moctale logic is:

`gravitee-io/distilbert-multilingual-toxicity-classifier`

Why this model fits the project:

- It is multilingual.
- It includes Hindi and Hinglish evaluation.
- It is lighter than XLM-R large toxicity models.
- It can run in a Kaggle notebook.
- It has a quantized ONNX option that may help later if the owner wants a cheaper production path.
- It gives a simple toxic / not-toxic signal, which is enough for the first version because our custom layer decides the final action.

The model should not be trusted alone. It may mark harsh movie criticism as toxic even when it should be allowed.

Example:

```text
"This movie is shit" -> model may say toxic, but Moctale logic should allow it because the target is the movie.
"You are shit" -> model says toxic, and Moctale logic should flag it because the target is a user.
```

Recommended notebook comparison:

1. Primary candidate: `gravitee-io/distilbert-multilingual-toxicity-classifier`
2. Benchmark comparison: `textdetox/xlmr-large-toxicity-classifier-v2`
3. Optional category model: `oleksiizirka/xlm-roberta-toxicity-classifier`

Final system name:

`Moctale Moderation AI`

