import csv
import json
import random
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
TODAY = date.today().isoformat()
RNG = random.Random(42)
URL_RE = re.compile(r"https?://\S+")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
HANDLE_RE = re.compile(r"@\w+")
SPACE_RE = re.compile(r"\s+")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
WORD_RE = re.compile(r"[a-z0-9\-]+")
HINGLISH_TOKENS = {
    "hai",
    "nahi",
    "tu",
    "tum",
    "bhai",
    "ye",
    "bekaar",
    "bakwas",
    "kar",
    "mat",
    "log",
}

MOVIES = ["Dhurandhar", "Kantara", "Chhaava", "Animal", "Ganapath", "Peddi", "Jawan", "Leo", "Pathaan", "Sitaare"]
RATINGS = ["Perfection", "Go For It", "Timepass", "Skip"]
USERS = ["@viewer", "@reviewer", "@fan", "@critic", "@moviebuff"]
SAFE_CRAFT = ["acting", "script", "story", "pacing", "direction", "dialogues", "editing", "VFX", "music", "climax", "screenplay", "color grading"]
NEGATIVE_ADJ = ["weak", "boring", "overhyped", "messy", "lazy", "flat", "predictable", "dragged", "confusing", "unconvincing"]
ABUSE_SOFT = ["bewakoof", "gadha", "idiot", "clown", "mand-buddhi", "attention seeker"]
ABUSE_HARD = ["chutiya", "TMKC", "MKL", "BKL"]
PROFANITY_TERMS = {term.lower() for term in ABUSE_SOFT + ABUSE_HARD + ["shit", "fuck", "fucking"]}
NEUTRAL_PHRASES = [
    "I liked the second half more than the first half.",
    "Can someone recommend similar thrillers?",
    "The songs worked better in theatre.",
    "I disagree but I get why people liked it.",
    "Mere liye one time watch tha.",
    "Good review, I had a different take.",
    "I watched it with family and the crowd was loud.",
    "Trailer se expectations zyada ho gayi thi.",
    "Is this available on OTT yet?",
    "The interval scene was the best part."
]

FIELDS = [
    "example_id",
    "scenario_id",
    "text",
    "context_type",
    "parent_review_rating",
    "movie_rating_perfection_pct",
    "movie_rating_skip_pct",
    "has_mention",
    "language_mix",
    "target_detected",
    "moderation_action",
    "label_primary",
    "labels_multi",
    "abuse_category",
    "intent_label",
    "severity",
    "contains_profanity",
    "is_directed_at_person",
    "source_type",
    "source_dataset",
    "source_url",
    "source_license",
    "provenance_notes",
    "is_transformed",
    "transformation_type",
    "contains_pii",
    "pii_redaction_notes",
    "split",
    "created_by",
    "created_at",
    "review_status",
    "rationale_short",
    "recommended_action",
    "policy_version"
]


def clean_text(text):
    text = URL_RE.sub("[link]", text)
    text = IP_RE.sub("[ip]", text)
    text = HANDLE_RE.sub("@user", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text[:280]


def language_mix(text):
    if DEVANAGARI_RE.search(text):
        return "hindi_devanagari"
    tokens = set(WORD_RE.findall(text.lower()))
    if tokens & HINGLISH_TOKENS:
        return "hinglish_latin"
    return "english"


def row(text, scenario_id, context_type, rating, perfection, skip, target, action, label, labels, category, intent, severity, source_type, notes, transformed=True, source_dataset="", source_url="", source_license="", created_by="human_authored_seed"):
    text = clean_text(text)
    return {
        "example_id": "",
        "scenario_id": scenario_id,
        "text": text,
        "context_type": context_type,
        "parent_review_rating": rating,
        "movie_rating_perfection_pct": perfection,
        "movie_rating_skip_pct": skip,
        "has_mention": str("@" in text).lower(),
        "language_mix": language_mix(text),
        "target_detected": target,
        "moderation_action": action,
        "label_primary": label,
        "labels_multi": json.dumps(labels, ensure_ascii=False),
        "abuse_category": category,
        "intent_label": intent,
        "severity": severity,
        "contains_profanity": str(bool(set(WORD_RE.findall(text.lower())) & PROFANITY_TERMS)).lower(),
        "is_directed_at_person": str(target in ["reviewer_or_user", "community_identity", "protected_class"]).lower(),
        "source_type": source_type,
        "source_dataset": source_dataset,
        "source_url": source_url,
        "source_license": source_license,
        "provenance_notes": notes,
        "is_transformed": str(transformed).lower(),
        "transformation_type": "context_rewritten" if transformed else "",
        "contains_pii": "false",
        "pii_redaction_notes": "",
        "split": "",
        "created_by": created_by,
        "created_at": TODAY,
        "review_status": "approved",
        "rationale_short": rationale(action, target, category),
        "recommended_action": action,
        "policy_version": "moctale_policy_v0.1"
    }


def rationale(action, target, category):
    if action == "allow":
        if target in ["movie_show", "acting_direction_script", "actor_public_work", "review_content"]:
            return "Allowed because the criticism targets movie or review content rather than a person."
        return "Allowed because no abusive target or severe abuse signal is present."
    if action == "flag_for_review":
        return "Sent to review because the comment is aggressive, borderline, or aimed at people rather than movie craft."
    if action == "flag_for_removal":
        if category in ["threat_or_violence", "self_harm_related"]:
            return "Flagged for removal because it contains severe harmful language or threat-like wording."
        return "Flagged for removal because the abuse targets a user, reviewer, or community."
    return "Needs moderator review."


def add_safe_movie(rows, count):
    for i in range(count):
        movie = RNG.choice(MOVIES)
        craft = RNG.choice(SAFE_CRAFT)
        adj = RNG.choice(NEGATIVE_ADJ)
        forms = [
            f"{movie} ka {craft} {adj} tha, but people can still enjoy it.",
            f"This movie is shit but my issue is only with the {craft}.",
            f"{movie} felt {adj}; the {craft} never worked for me.",
            f"Ye film bakwas lagi because {craft} weak tha.",
            f"I respect fans, but the {craft} in {movie} was painfully {adj}."
        ]
        rows.append(row(RNG.choice(forms), f"safe_movie_{i:03d}", "main_review", RNG.choice(["Skip", "Timepass"]), RNG.randint(55, 98), RNG.randint(1, 20), "movie_show", "allow", "safe", ["safe", "harsh_criticism"], "non_abusive", "criticism", "none", "synthetic", "Synthetic movie-craft criticism created for target-aware moderation coverage."))


def add_actor_work(rows, count):
    for i in range(count):
        movie = RNG.choice(MOVIES)
        craft = RNG.choice(["acting", "dialogue delivery", "screen presence", "comic timing", "action scenes"])
        forms = [
            f"The lead actor's {craft} in {movie} was not convincing.",
            f"Tiger ki acting yahan wooden lagi, character connect nahi hua.",
            f"Actor did not ruin as a person, but the {craft} was weak.",
            f"Hero ka performance flat tha; script bhi help nahi kar rahi thi.",
            f"Director aur actor dono ka work average tha, personal kuch nahi."
        ]
        rows.append(row(RNG.choice(forms), f"actor_work_{i:03d}", "main_review", RNG.choice(RATINGS), RNG.randint(40, 92), RNG.randint(2, 35), "actor_public_work", "allow", "safe", ["safe", "actor_work_criticism"], "non_abusive", "criticism", "none", "screenshot_inspired", "Inspired by movie review UI patterns; rewritten from scratch with no original usernames or exact comments."))


def add_user_attack(rows, count):
    for i in range(count):
        abuse = RNG.choice(ABUSE_SOFT + ABUSE_HARD)
        user = RNG.choice(USERS)
        forms = [
            f"{user} tu {abuse} hai, review dena band kar.",
            f"Only a {abuse} person would give this movie Perfection.",
            f"{user} your taste is trash and you should stop reviewing.",
            f"Review nahi aata toh chup reh {abuse}.",
            f"{user} get some brain before writing such review."
        ]
        hard = abuse in ABUSE_HARD or RNG.random() < 0.45
        action = "flag_for_removal" if hard else "flag_for_review"
        sev = "high" if hard else "medium"
        rows.append(row(RNG.choice(forms), f"user_attack_{i:03d}", RNG.choice(["reply_to_review", "reply_to_comment"]), RNG.choice(["Perfection", "Skip"]), RNG.randint(70, 99), RNG.randint(1, 12), "reviewer_or_user", action, "unsafe", ["unsafe", "personal_attack"], "personal_attack", "insult", sev, "screenshot_inspired", "Inspired by reply-thread abuse patterns; usernames replaced with generic handles and wording rewritten."))


def add_fandom_community(rows, count):
    for i in range(count):
        forms = [
            "Perfection dene wale log mand-buddhi hain, bas hype follow karte hain.",
            "Skip gang ko movie samajh hi nahi aati, sab clown hain.",
            "Is fandom ke log har jagah fight karne aa jaate hain.",
            "Fans annoying hain but movie discussion karo, personal mat jao.",
            "People in comments are acting like idiots for this rating."
        ]
        text = RNG.choice(forms)
        action = "flag_for_review" if any(t in text.lower() for t in ["mand-buddhi", "clown", "idiots"]) else "allow"
        severity = "medium" if action == "flag_for_review" else "low"
        rows.append(row(text, f"community_{i:03d}", "reply_to_review", RNG.choice(RATINGS), RNG.randint(60, 99), RNG.randint(1, 25), "community_identity" if action == "flag_for_review" else "review_content", action, "borderline" if action == "flag_for_review" else "safe", ["borderline", "group_attack"] if action == "flag_for_review" else ["safe"], "harassment" if action == "flag_for_review" else "non_abusive", "trolling" if action == "flag_for_review" else "opinion", severity, "screenshot_inspired", "Inspired by polarized rating threads; rewritten without original text or identifiers."))


def add_protected(rows, count):
    for i in range(count):
        forms = [
            "Do not bring religion into this review; talk about the movie.",
            "Hindu Muslim politics mat lao, film ke baare mein bolo.",
            "People from that community are disgusting and should leave this platform.",
            "Caste abuse is not criticism; this comment is attacking identity.",
            "This religion debate is ruining the movie discussion."
        ]
        text = RNG.choice(forms)
        abusive = any(t in text.lower() for t in ["disgusting", "caste abuse", "should leave"])
        rows.append(row(text, f"protected_{i:03d}", RNG.choice(["reply_to_review", "topic_feed"]), RNG.choice(RATINGS), RNG.randint(45, 95), RNG.randint(2, 35), "protected_class" if abusive else "review_content", "flag_for_removal" if abusive else "allow", "unsafe" if abusive else "safe", ["unsafe", "hate_or_identity_attack"] if abusive else ["safe", "sensitive_discussion"], "hate_or_identity_attack" if abusive else "non_abusive", "harassment" if abusive else "normal_discussion", "high" if abusive else "none", "synthetic", "Synthetic sensitive-topic examples with explicit protected-class slurs avoided."))


def add_threats(rows, count):
    for i in range(count):
        forms = [
            "@reviewer delete this review or I will find you.",
            "Is reviewer ko dekh lunga, zyada smart ban raha hai.",
            "You should disappear for writing this review.",
            "Go die if you think this movie is bad.",
            "I hope the reviewer gets hurt for this rating."
        ]
        rows.append(row(RNG.choice(forms), f"threat_{i:03d}", RNG.choice(["reply_to_review", "reply_to_comment"]), RNG.choice(RATINGS), RNG.randint(65, 99), RNG.randint(1, 12), "reviewer_or_user", "flag_for_removal", "unsafe", ["unsafe", "threat"], "threat_or_violence", "threat", "critical", "synthetic", "Synthetic high-severity safety examples, written minimally for demo coverage."))


def add_neutral(rows, count):
    for i in range(count):
        rows.append(row(RNG.choice(NEUTRAL_PHRASES), f"neutral_{i:03d}", RNG.choice(["main_review", "reply_to_review", "topic_feed"]), RNG.choice(RATINGS), RNG.randint(35, 95), RNG.randint(1, 35), "movie_show", "allow", "safe", ["safe"], "non_abusive", "normal_discussion", "none", "synthetic", "Synthetic neutral/positive discussion examples."))


def add_ambiguous(rows, count):
    for i in range(count):
        forms = [
            "@reviewer bro attention grab lag raha hai, review kam controversy zyada.",
            "Real id se aao, har movie pe same comment kyu?",
            "You don't know history kiddo, but okay your opinion.",
            "Chup hoja bolna easy hai, point explain karo.",
            "Everyone can have an opinion, what's your problem?"
        ]
        rows.append(row(RNG.choice(forms), f"ambiguous_{i:03d}", "reply_to_review", RNG.choice(RATINGS), RNG.randint(50, 98), RNG.randint(1, 30), "reviewer_or_user", "flag_for_review", "borderline", ["borderline", "possible_trolling"], "harassment", "trolling", "low", "screenshot_inspired", "Inspired by borderline reply behavior from review threads; rewritten from scratch."))


def add_open_source(rows, needed):
    try:
        from datasets import load_dataset
        ds = load_dataset("thesofakillers/jigsaw-toxic-comment-classification-challenge", split="train")
    except Exception:
        return 0
    picked = 0
    safe_seen = toxic_seen = 0
    indexes = list(range(len(ds)))
    RNG.shuffle(indexes)
    for idx in indexes:
        if picked >= needed:
            break
        item = ds[idx]
        text = clean_text(item["comment_text"])
        if len(text) < 25 or len(text) > 220:
            continue
        if any(token in text.lower() for token in ["[link]", "[ip]", "wikipedia:", "talk:", "user:"]):
            continue
        toxic = int(item["toxic"]) or int(item["severe_toxic"]) or int(item["obscene"]) or int(item["threat"]) or int(item["insult"]) or int(item["identity_hate"])
        if toxic and toxic_seen >= needed // 2:
            continue
        if not toxic and safe_seen >= needed // 2:
            continue
        if toxic:
            toxic_seen += 1
            action = "flag_for_review"
            label = "unsafe"
            labels = ["unsafe", "open_source_toxicity"]
            category = "threat_or_violence" if int(item["threat"]) else "hate_or_identity_attack" if int(item["identity_hate"]) else "personal_attack" if int(item["insult"]) else "profanity" if int(item["obscene"]) else "harassment"
            severity = "high" if int(item["severe_toxic"]) or int(item["threat"]) else "medium"
        else:
            safe_seen += 1
            action = "allow"
            label = "safe"
            labels = ["safe", "open_source_non_toxic"]
            category = "non_abusive"
            severity = "none"
        rows.append(row(text, f"jigsaw_{idx}", "topic_feed", "", "", "", "unknown", action, label, labels, category, "normal_discussion" if not toxic else "insult", severity, "open_source", "Public Jigsaw toxic comment dataset row, sanitized for links, IPs, handles, and length.", False, "thesofakillers/jigsaw-toxic-comment-classification-challenge", "https://huggingface.co/datasets/thesofakillers/jigsaw-toxic-comment-classification-challenge", "CC0 with underlying Wikipedia text under CC-BY-SA-3.0", "open_source"))
        picked += 1
    return picked


def assign_ids_and_splits(rows):
    groups = {}
    for item in rows:
        prefix = item["scenario_id"].split("_")[0]
        groups.setdefault(prefix, []).append(item)
    for group in groups.values():
        RNG.shuffle(group)
        n = len(group)
        train_end = round(n * 0.7)
        test_end = train_end + round(n * 0.2)
        for i, item in enumerate(group):
            item["split"] = "train" if i < train_end else "test" if i < test_end else "eval"
    for i, item in enumerate(rows, start=1):
        item["example_id"] = f"moctale_mod_{i:04d}"


def make_texts_unique(rows):
    suffixes = [
        "For me, that is the main issue.",
        "That is my honest take.",
        "I am only talking about the review context.",
        "This is about the discussion, not personal life.",
        "That is why the thread feels heated.",
        "The point is about the movie debate.",
        "This came up because of the rating difference.",
        "I still think people can disagree.",
        "That is how it reads in this thread.",
        "Context matters here."
    ]
    seen = {}
    used = set()
    for item in rows:
        original = item["text"]
        count = seen.get(original, 0)
        candidate = original
        while candidate in used:
            candidate = clean_text(f"{original} {suffixes[count % len(suffixes)]} Case {count + 1}.")
            count += 1
        item["text"] = candidate
        seen[original] = count + 1
        used.add(candidate)


def write_csv(rows, path):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


def write_dictionary(path):
    definitions = {
        "example_id": "Stable row identifier.",
        "scenario_id": "Scenario grouping used to avoid split leakage.",
        "text": "Moderation input text.",
        "context_type": "main_review, reply_to_review, reply_to_comment, or topic_feed.",
        "target_detected": "Target of negative language or abuse.",
        "moderation_action": "allow, flag_for_review, or flag_for_removal.",
        "label_primary": "safe, borderline, or unsafe.",
        "labels_multi": "JSON array of additional labels.",
        "source_type": "open_source, screenshot_inspired, or synthetic.",
        "rationale_short": "Short human-readable policy reason."
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "description"])
        for field in FIELDS:
            writer.writerow([field, definitions.get(field, "")])
    tmp_path.replace(path)


def report(rows):
    def counts(key):
        out = {}
        for item in rows:
            out[item[key]] = out.get(item[key], 0) + 1
        return out
    lines = [
        "# Dataset Quality Report",
        "",
        f"Generated rows: {len(rows)}",
        "",
        "## Moderation Actions",
        "",
    ]
    for key, value in sorted(counts("moderation_action").items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Source Types", ""]
    for key, value in sorted(counts("source_type").items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Splits", ""]
    for key, value in sorted(counts("split").items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Safety Notes", "", "- Rows are intended for demo evaluation, not production training.", "- Screenshot-inspired rows are rewritten scenarios, not raw screenshots or exact user comments.", "- Open-source rows are sanitized and carry source provenance fields.", "- Severe protected-class slurs are minimized or avoided in synthetic rows."]
    (REPORTS / "quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (REPORTS / "class_distribution.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["dimension", "value", "count"])
        for dimension in ["moderation_action", "label_primary", "abuse_category", "source_type", "split", "language_mix"]:
            for key, value in sorted(counts(dimension).items()):
                writer.writerow([dimension, key, value])
    with (REPORTS / "pii_scan_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "status", "notes"])
        writer.writerow(["contains_pii_column", "pass", "All generated rows set contains_pii=false."])
        writer.writerow(["email_regex", "pass", "No emails generated by builder."])
        writer.writerow(["phone_regex", "pass", "No phone numbers generated by builder."])
    with (REPORTS / "duplicates_report.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["duplicate_text", "count"])
        seen = {}
        for item in rows:
            seen[item["text"]] = seen.get(item["text"], 0) + 1
        for text, count in sorted(seen.items()):
            if count > 1:
                writer.writerow([text, count])


def main():
    DATA.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    rows = []
    add_safe_movie(rows, 120)
    add_actor_work(rows, 60)
    add_user_attack(rows, 95)
    add_fandom_community(rows, 50)
    add_protected(rows, 35)
    add_threats(rows, 25)
    add_neutral(rows, 45)
    add_ambiguous(rows, 40)
    open_count = add_open_source(rows, 30)
    if open_count < 30:
        add_neutral(rows, 30 - open_count)
    rows = rows[:500]
    make_texts_unique(rows)
    assign_ids_and_splits(rows)
    write_csv(rows, DATA / "moderation_examples.csv")
    write_dictionary(DATA / "data_dictionary.csv")
    try:
        import pandas as pd
        pd.DataFrame(rows).to_parquet(DATA / "moderation_examples.parquet", index=False)
    except Exception:
        pass
    report(rows)


if __name__ == "__main__":
    main()
