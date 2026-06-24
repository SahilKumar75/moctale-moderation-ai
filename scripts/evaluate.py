"""CLI evaluation script for Moctale Moderation AI.

Usage:
    python scripts/evaluate.py
    python scripts/evaluate.py --dataset data/moderation_examples.csv --out reports/eval.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Moctale moderation engine accuracy")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "data" / "moderation_examples.csv",
        help="Path to labeled CSV dataset",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output Markdown path (default: print to stdout)",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Output JSON instead of Markdown",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Error: dataset not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    from moctale_moderation.evaluator import Evaluator
    report = Evaluator().run(args.dataset)

    if args.as_json:
        output = json.dumps(report.to_json(), indent=2)
    else:
        output = report.summary()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"Report written to {args.out}")
        # Print key metrics to console regardless
        print(f"Total: {report.total} | Accuracy: {report.accuracy:.3f} | Macro F1: {report.macro_f1:.3f}")
    else:
        print(output)


if __name__ == "__main__":
    main()
