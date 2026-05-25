"""Build the universal knowledge graph and export it as JSON + markdown vault.

Usage examples
--------------

# Single local repo:
    python scripts/build_universal_graph.py \
        --repo-root . --owner khiwniti --name graph-rag-resume-agent \
        --person-login khiwniti

# All repos under a parent directory (one repo per subfolder):
    python scripts/build_universal_graph.py --repos-dir ./data/raw/repos \
        --person-login khiwniti

Outputs:
    data/graph/knowledge_graph.json    (consumer: careergraph-wiki-mcp-ui)
    data/wiki/                         (consumer: wiki app)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.builders import RepoSpec  # noqa: E402
from app.pipeline_universal import UniversalPipeline, UniversalPipelineConfig  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build universal knowledge graph")
    p.add_argument("--repo-root", help="Path to a single local repo")
    p.add_argument("--owner", help="GitHub owner (required with --repo-root)")
    p.add_argument("--name", help="Repo name (required with --repo-root)")

    p.add_argument("--repos-dir",
                   help="Directory whose subfolders are individual repos")
    p.add_argument("--default-owner", default="khiwniti",
                   help="Owner to use for repos discovered via --repos-dir")

    p.add_argument("--person-login",
                   help="Owner login for the central Person node")
    p.add_argument("--no-llm", action="store_true",
                   help="Disable LLM concept augmentation")
    p.add_argument("--llm-top-n", type=int, default=25,
                   help="Augment at most N repos with LLM (cost guard)")

    p.add_argument("--collected-json",
                   help="Optional path to a pre-collected JSON with "
                        "'vercel', 'cloudflare', 'conversations' arrays")

    p.add_argument("--output-graph", default="data/graph/knowledge_graph.json")
    p.add_argument("--output-vault", default="data/wiki")
    p.add_argument("--max-files", type=int, default=200)
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    repo_specs = []
    if args.repo_root:
        if not (args.owner and args.name):
            print("ERROR: --owner and --name required with --repo-root",
                  file=sys.stderr)
            return 2
        repo_specs.append(RepoSpec(
            owner=args.owner, name=args.name,
            local_path=args.repo_root, max_files=args.max_files,
        ))

    if args.repos_dir:
        root = Path(args.repos_dir)
        if not root.is_dir():
            print(f"ERROR: --repos-dir not a directory: {root}", file=sys.stderr)
            return 2
        for sub in sorted(p for p in root.iterdir() if p.is_dir()):
            repo_specs.append(RepoSpec(
                owner=args.default_owner, name=sub.name,
                local_path=str(sub), max_files=args.max_files,
            ))

    if not repo_specs:
        print("ERROR: provide --repo-root or --repos-dir", file=sys.stderr)
        return 2

    vercel_projects = []
    cloudflare_workers = []
    conversations = []
    if args.collected_json:
        data = json.loads(Path(args.collected_json).read_text())
        vercel_projects = data.get("vercel", []) or data.get("vercel_projects", [])
        cloudflare_workers = data.get("cloudflare", []) or data.get("cloudflare_workers", [])
        conversations = data.get("conversations", [])

    cfg = UniversalPipelineConfig(
        person_login=args.person_login,
        output_graph_path=args.output_graph,
        output_vault_dir=args.output_vault,
        use_llm=not args.no_llm,
        llm_top_n_repos=args.llm_top_n,
        repo_specs=repo_specs,
        vercel_projects=vercel_projects,
        cloudflare_workers=cloudflare_workers,
        conversations=conversations,
    )

    stats = UniversalPipeline(cfg).run()
    print(json.dumps(stats, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
