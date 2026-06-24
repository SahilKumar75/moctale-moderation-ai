import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "moderation_examples.csv"
EMAIL_RE = re.compile(r"[\w.-]+@[\w.-]+\.\w+")
PHONE_RE = re.compile(r"\b\d{10,}\b")

ENUMS = {
    "context_type": {"main_review", "reply_to_review", "reply_to_comment", "topic_feed"},
    "target_detected": {"movie_show", "acting_direction_script", "actor_public_work", "review_content", "reviewer_or_user", "community_identity", "protected_class", "unknown"},
    "moderation_action": {"allow", "flag_for_review", "flag_for_removal"},
    "label_primary": {"safe", "borderline", "unsafe"},
    "severity": {"none", "low", "medium", "high", "critical"},
    "source_type": {"open_source", "screenshot_inspired", "synthetic"},
    "split": {"train", "test", "eval"},
    "review_status": {"draft", "reviewed", "approved"}
}

REQUIRED = [
    "example_id",
    "scenario_id",
    "text",
    "context_type",
    "target_detected",
    "moderation_action",
    "label_primary",
    "labels_multi",
    "source_type",
    "split",
    "rationale_short"
]


def fail(errors, message):
    errors.append(message)


def main():
    errors = []
    ids = set()
    texts = Counter()
    row_count = 0
    with PATH.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            row_count += 1
            for field in REQUIRED:
                if not row.get(field):
                    fail(errors, f"Row {i}: missing {field}")
            if row.get("example_id") in ids:
                fail(errors, f"Row {i}: duplicate example_id {row.get('example_id')}")
            ids.add(row.get("example_id"))
            for field, allowed in ENUMS.items():
                if row.get(field) not in allowed:
                    fail(errors, f"Row {i}: invalid {field}={row.get(field)}")
            try:
                value = json.loads(row.get("labels_multi", ""))
                if not isinstance(value, list):
                    fail(errors, f"Row {i}: labels_multi must be a JSON list")
            except Exception:
                fail(errors, f"Row {i}: labels_multi is not valid JSON")
            text = row.get("text", "")
            if EMAIL_RE.search(text):
                fail(errors, f"Row {i}: possible email in text")
            if PHONE_RE.search(text):
                fail(errors, f"Row {i}: possible phone number in text")
            texts[text] += 1
            if row.get("source_type") == "open_source":
                for field in ["source_dataset", "source_url", "source_license"]:
                    if not row.get(field):
                        fail(errors, f"Row {i}: open_source row missing {field}")
    if row_count != 500:
        fail(errors, f"Expected 500 rows, found {row_count}")
    duplicates = [text for text, count in texts.items() if count > 1]
    if duplicates:
        fail(errors, f"Found {len(duplicates)} duplicate text values")
    if errors:
        print("FAILED")
        for error in errors:
            print(error)
        sys.exit(1)
    print("PASSED")


if __name__ == "__main__":
    main()
