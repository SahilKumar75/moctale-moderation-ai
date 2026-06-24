"""CLI to add or update rules dynamically without code changes."""

import argparse
import sys
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a new policy rule dynamically.")
    parser.add_argument("--id", type=str, required=True, help="Unique rule ID")
    parser.add_argument("--description", type=str, required=True, help="Rule description")
    parser.add_argument(
        "--action", type=str, required=True, choices=["allow", "flag_for_review", "flag_for_removal"]
    )
    parser.add_argument("--category", type=str, required=True, help="Harm category")
    parser.add_argument(
        "--severity", type=str, required=True, choices=["none", "low", "medium", "high", "critical"]
    )
    parser.add_argument("--examples", type=str, nargs="+", default=[], help="List of examples")

    args = parser.parse_args()

    config_path = Path(__file__).resolve().parents[1] / "config" / "policy_rules.yaml"

    if not config_path.exists():
        data = {"rules": []}
    else:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {"rules": []}

    if "rules" not in data:
        data["rules"] = []

    # Check if rule exists
    existing = next((r for r in data["rules"] if r.get("id") == args.id), None)
    if existing:
        print(f"Updating existing rule '{args.id}'...")
        existing.update({
            "description": args.description,
            "action": args.action,
            "category": args.category,
            "severity": args.severity,
            "examples": args.examples,
        })
    else:
        print(f"Adding new rule '{args.id}'...")
        data["rules"].append({
            "id": args.id,
            "description": args.description,
            "action": args.action,
            "category": args.category,
            "severity": args.severity,
            "examples": args.examples,
        })

    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

    print("Rule saved successfully.")
    print("Run `python scripts/index_policy.py` to update the active ChromaDB index.")


if __name__ == "__main__":
    main()
