#!/usr/bin/env python3
"""Canonical career graph builder (disk-safe, conversation-excluded, Aura-free-tier aware).

This script is intended to become the main entrypoint for building the *career*
knowledge graph used by the resume agent.

Key guarantees (per user requirements):
- Conversation artifacts are excluded by default.
- Any git repository cloned locally is cloned into a temp dir and deleted
  immediately after extraction.
- Supports Neo4j Aura free-tier mode by default: disables heavy code-structure
  extraction (functions/classes/calls) unless explicitly enabled.

Outputs:
- data/graph/knowledge_graph.json
- data/wiki/
- data/quality/graph_audit_report.json

Usage:
  python scripts/run_career_graph.py --max-repos 30 --person-login khiwniti

"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Allow running from repo root without install
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.builders.universal_builder import RepoSpec, UniversalGraphBuilder  # noqa: E402
from app.collectors.github_collector import GitHubCollector  # noqa: E402
from app.collectors.vercel_collector import VercelCollector  # noqa: E402
from app.collectors.cloudflare_collector import CloudflareCollector  # noqa: E402
from app.exporters import export_graph_json, export_wiki_vault  # noqa: E402


logger = logging.getLogger("run_career_graph")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build career knowledge graph (canonical runner)")

    p.add_argument("--person-login", required=True, help="GitHub login for the central Person node")
    p.add_argument("--max-repos", type=int, default=50, help="Max repos to ingest (0 = no limit)")
    p.add_argument("--include-forks", action="store_true", help="Include forked repos")

    # Conversations are excluded per user requirement.
    # We keep no CLI to include them to avoid accidental ingestion.

    p.add_argument("--neo4j-free-tier", action="store_true", default=True,
                   help="Enable compact graph mode suitable for Neo4j Aura free tier (default: true)")
    p.add_argument("--full-code", action="store_true", default=False,
                   help="Enable heavy code structure extraction (functions/classes/calls). Not Aura-free-tier safe.")

    p.add_argument("--max-files", type=int, default=120,
                   help="Max files per repo to scan when code parsing is enabled")

    p.add_argument("--no-llm", action="store_true", help="Disable LLM augmentation")
    p.add_argument("--llm-top-n", type=int, default=25, help="LLM augment at most N repos")

    p.add_argument("--output-graph", default="data/graph/knowledge_graph.json")
    p.add_argument("--output-vault", default="data/wiki")

    p.add_argument("--keep-clones-for-debug", action="store_true",
                   help="Do NOT delete temp clones (debug only; violates disk-saving requirement)")

    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def _repo_meta_from_api(repo: Dict[str, Any], owner: str, languages: Dict[str, int], readme: str) -> Dict[str, Any]:
    return {
        "owner": owner,
        "url": repo.get("html_url"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "languages": languages,
        "stars": repo.get("stargazers_count"),
        "forks": repo.get("forks_count"),
        "topics": repo.get("topics", []) or [],
        "default_branch": repo.get("default_branch"),
        "license": (repo.get("license") or {}).get("name") if isinstance(repo.get("license"), dict) else repo.get("license"),
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "updated_at": repo.get("updated_at"),
        "readme": readme,
    }


def _clone_to_temp(gh: GitHubCollector, clone_url: str, name_hint: str) -> str:
    temp_root = tempfile.mkdtemp(prefix=f"careergraph-{name_hint}-")
    ok = gh.clone_repo(clone_url, temp_root)
    if not ok:
        # cleanup directory if clone failed
        shutil.rmtree(temp_root, ignore_errors=True)
        raise RuntimeError("clone failed")
    return temp_root


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Conversations excluded by design.

    # Aura/free-tier defaults: disable heavy code structure unless explicitly overridden.
    parse_code = bool(args.full_code) and (not args.neo4j_free_tier)
    if args.neo4j_free_tier and args.full_code:
        logger.warning("--full-code requested but --neo4j-free-tier is on; keeping parse_code disabled.")
        parse_code = False

    gh = GitHubCollector(max_repos=args.max_repos)
    username = gh.get_authenticated_user()
    if not username:
        raise SystemExit("ERROR: GitHub auth failed (check GITHUB_TOKEN)")

    repos = gh.get_user_repos(username)
    if not args.include_forks:
        repos = [r for r in repos if not r.get("fork", False)]
    if args.max_repos and args.max_repos > 0:
        repos = repos[: args.max_repos]

    logger.info("GitHub user=%s repos_to_process=%d", username, len(repos))

    # Optional collectors for deployments
    vercel_projects: List[Dict[str, Any]] = []
    cloudflare_workers: List[Dict[str, Any]] = []
    try:
        vercel_projects = VercelCollector().collect_all().get("projects", [])
    except Exception as e:
        logger.warning("Vercel collection failed: %s", e)
    try:
        cloudflare_workers = CloudflareCollector().collect_all().get("workers", [])
    except Exception as e:
        logger.warning("Cloudflare collection failed: %s", e)

    # Conversations intentionally excluded (user requirement)
    # NOTE: Even if flags are passed, we keep this empty for now.
    conversations: List[Dict[str, Any]] = []

    builder = UniversalGraphBuilder(person_login=args.person_login)

    processed = 0
    failures: List[Dict[str, Any]] = []

    for repo in repos:
        name = repo.get("name") or "unknown"
        full_name = repo.get("full_name") or f"{username}/{name}"
        owner = (full_name.split("/")[0] if "/" in full_name else username)

        clone_url = repo.get("clone_url")
        if not clone_url:
            logger.warning("Skipping repo with no clone_url: %s", full_name)
            continue

        temp_path: Optional[str] = None
        try:
            languages = gh.get_repo_languages(owner, name)
            readme = gh.get_repo_readme(owner, name) or ""
            readme = readme[:20_000]  # cap for memory

            temp_path = _clone_to_temp(gh, clone_url, name_hint=name)

            # Enrich meta with commit dates from local clone (cheap, useful for timeline)
            dates = gh.get_repo_dates(temp_path)

            meta = _repo_meta_from_api(repo, owner, languages, readme)
            meta.update(dates)

            # In Neo4j free-tier mode we keep docs compact:
            # - README is ingested from `readme` above
            # - we skip ingesting ALL other markdown docs to avoid section/concept explosion
            parse_docs = False if args.neo4j_free_tier else True

            spec = RepoSpec(
                owner=owner,
                name=name,
                local_path=temp_path,
                metadata=meta,
                readme=readme,
                max_files=args.max_files,
                parse_code=parse_code,
                parse_dependencies=True,
                parse_docs=parse_docs,
                parse_deployment_configs=True,
            )

            rid = builder.add_repo(spec)
            processed += 1
            logger.info("Ingested repo %s as %s", full_name, rid)

        except Exception as e:
            failures.append({"repo": full_name, "error": str(e)})
            logger.exception("Failed repo ingest: %s", full_name)

        finally:
            if temp_path and not args.keep_clones_for_debug:
                # Immediate cleanup per requirement
                shutil.rmtree(temp_path, ignore_errors=True)

    # Deployments
    for vp in vercel_projects:
        try:
            builder.add_vercel_project(vp)
        except Exception as e:
            logger.warning("vercel ingest failed: %s", e)

    for cw in cloudflare_workers:
        try:
            builder.add_cloudflare_worker(cw)
        except Exception as e:
            logger.warning("cloudflare ingest failed: %s", e)

    # Conversations excluded
    for conv in conversations:
        try:
            builder.add_conversation(conv)
        except Exception as e:
            logger.warning("conversation ingest failed: %s", e)

    graph = builder.finalize()

    # Export JSON + wiki
    graph_path = export_graph_json(graph, args.output_graph)
    vault_path = export_wiki_vault(graph, args.output_vault)

    out = {
        "person_login": args.person_login,
        "repos_processed": processed,
        "repos_failed": len(failures),
        "failures": failures[:50],
        "graph_stats": graph.stats(),
        "graph_json": str(graph_path),
        "wiki_vault": str(vault_path),
        "neo4j_free_tier_mode": args.neo4j_free_tier,
        "parse_code_enabled": parse_code,
        "conversations_included": bool(conversations),
    }

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
