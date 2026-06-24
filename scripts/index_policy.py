"""Script to build or rebuild the ChromaDB policy index from YAML."""

import argparse
import logging
from pathlib import Path

from moctale_moderation.policy.store import PolicyStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index policy rules into ChromaDB.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "config" / "policy_rules.yaml"),
        help="Path to policy_rules.yaml",
    )
    args = parser.parse_args()

    store = PolicyStore()
    store.build_from_yaml(args.config)
    
    # Test retrieval
    print("\nTest Retrieval:")
    test_queries = [
        "chutiya admin",
        "i will hunt you down and kill you",
        "this movie has the worst script ever",
    ]
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        rules = store.retrieve(q, k=2)
        for r in rules:
            print(f"  - [{r.action}] {r.id}: {r.category} ({r.severity})")

if __name__ == "__main__":
    main()
