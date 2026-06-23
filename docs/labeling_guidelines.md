# Labeling Guidelines

## Core Principle

Moderate abuse, not taste.

Movie criticism can be angry, harsh, and negative. That alone is not abuse.

## Allowed

Use `allow` when the comment targets:

- movie
- show
- scene
- acting
- script
- story
- pacing
- direction
- dialogues
- editing
- VFX
- review content without attacking the reviewer

Examples:

```text
This movie is shit.
The acting was weak.
The script felt lazy.
The review missed the main point.
```

## Flag For Review

Use `flag_for_review` when the comment is aggressive but not clearly severe.

Common cases:

- mild personal attack
- trolling
- unclear target
- group insults about fans or comment sections
- aggressive reply to a reviewer
- borderline Hinglish insult

Examples:

```text
This reviewer is attention seeking.
Perfection dene wale log mand-buddhi hain.
Real id se aao.
Chup hoja and explain your point.
```

## Flag For Removal

Use `flag_for_removal` for direct severe abuse.

Common cases:

- direct user abuse
- severe Hinglish abuse acronym
- sexual abuse
- threat
- identity abuse
- self-harm encouragement
- harassment toward reviewer or commenter

Examples:

```text
You are shit.
@user tu chutiya hai.
TMKC
Go die if you liked this movie.
```

## Target Labels

Use `target_detected` to capture where the negative language points:

- `movie_show`
- `acting_direction_script`
- `actor_public_work`
- `review_content`
- `reviewer_or_user`
- `community_identity`
- `protected_class`
- `unknown`

## Source Labels

Use `source_type`:

- `synthetic`
- `screenshot_inspired`
- `open_source`

Never mark rewritten screenshot scenarios as real user data.

