from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from moctale_moderation import ModerationEngine, ModerationRequest

DATASET = ROOT / "data" / "moderation_examples.csv"


def load_requests(limit: int | None = None) -> list[ModerationRequest]:
    with DATASET.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if limit:
        rows = rows[:limit]
    return [
        ModerationRequest(
            text=row["text"],
            context_type=row["context_type"],
            parent_review_rating=row["parent_review_rating"],
            movie_rating_perfection_pct=float(row["movie_rating_perfection_pct"] or 0),
            movie_rating_skip_pct=float(row["movie_rating_skip_pct"] or 0),
        )
        for row in rows
    ]


def main() -> None:
    engine = ModerationEngine()
    base = load_requests()
    requests = base * 200
    start = time.perf_counter()
    engine.analyze_many(requests)
    elapsed = time.perf_counter() - start
    total = len(requests)
    print(f"requests={total}")
    print(f"elapsed_seconds={elapsed:.4f}")
    print(f"requests_per_second={total / elapsed:.0f}")
    print(f"cache={engine.cache_info()}")


if __name__ == "__main__":
    main()
