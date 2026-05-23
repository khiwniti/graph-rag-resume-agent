#!/usr/bin/env python3
"""
Run collection pipeline - collects data from all sources.

Usage:
    python scripts/run_collection.py --max-repos 10
    python scripts/run_collection.py  # Collect all repos
"""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline import GraphRAGPipeline


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Graph RAG collection pipeline")
    parser.add_argument(
        "--max-repos",
        type=int,
        default=0,
        help="Maximum number of GitHub repos to collect (0 = all)"
    )
    parser.add_argument(
        "--include-forks",
        action="store_true",
        help="Include forked repositories in GitHub collection"
    )

    args = parser.parse_args()

    print("🚀 Starting Graph RAG Resume Agent Collection")
    print(f"   Max repos: {args.max_repos or 'all'}")
    print(f"   Include forks: {args.include_forks}")

    pipeline = GraphRAGPipeline(max_repos=args.max_repos)
    results = pipeline.run_full_pipeline()

    return 0 if not results.get("errors") else 1


if __name__ == "__main__":
    sys.exit(main())
