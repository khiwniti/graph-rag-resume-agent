"""Streaming universal collector: pulls EVERY data source into the universal graph.

Flow per run
------------

1. Stream GitHub repos one-at-a-time via ``GitHubCollector.collect_streaming``.
   For each repo:
     a. clone (already done by the collector)
     b. feed it to ``UniversalGraphBuilder.add_repo`` (deep extraction)
     c. (optional) run ``LLMConceptExtractor`` for that repo
     d. cleanup the clone (unless ``--keep-repos``)
2. Pull Vercel projects (raw API data), feed to ``add_vercel_project``.
3. Pull Cloudflare workers, feed to ``add_cloudflare_worker``.
4. Pull conversations, feed to ``add_conversation``.
5. Finalise the graph and export:
     - ``data/graph/knowledge_graph.json`` (wiki/mcp consumer)
     - ``data/wiki/`` (Obsidian-style markdown vault)
     - (optional) push to Neo4j via ``app.exporters.neo4j_export``

Usage
-----

    # All sources, push to Neo4j, no LLM (fast):
    python scripts/collect_universal.py --neo4j --no-llm

    # Same, but keep clones on disk for inspection:
    python scripts/collect_universal.py --neo4j --keep-repos

    # Cap how many repos to fetch:
    python scripts/collect_universal.py --max-repos 30 --neo4j

    # Skip GitHub collection, just rebuild from local clones in data/raw:
    python scripts/collect_universal.py --from-local data/raw --neo4j
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import shutil
import signal
import sys
import time
from contextlib import contextmanager
from pathlib import Path


class _RepoTimeout(Exception):
    pass


@contextmanager
def _repo_timeout(seconds: int):
    """SIGALRM-based per-repo wall-clock guard. No-op if seconds <= 0."""
    if seconds <= 0:
        yield
        return

    def _handler(signum, frame):
        raise _RepoTimeout(f"repo exceeded {seconds}s wall-clock budget")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.builders import RepoSpec, UniversalGraphBuilder  # noqa: E402
from app.collectors.cloudflare_collector import CloudflareCollector  # noqa: E402
from app.collectors.conversation_collector import ConversationCollector  # noqa: E402
from app.collectors.github_collector import GitHubCollector  # noqa: E402
from app.collectors.vercel_collector import VercelCollector  # noqa: E402
from app.config import RAW_DIR  # noqa: E402
from app.exporters import export_graph_json, export_to_neo4j, export_wiki_vault  # noqa: E402
from app.extractors.llm_concept_extractor import LLMConceptExtractor  # noqa: E402

logger = logging.getLogger(__name__)


# ── arg parsing ───────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)

    # source selection
    p.add_argument("--max-repos", type=int, default=0,
                   help="0 = all repos (default)")
    p.add_argument("--skip-github", action="store_true")
    p.add_argument("--skip-vercel", action="store_true")
    p.add_argument("--skip-cloudflare", action="store_true")
    p.add_argument("--skip-conversations", action="store_true",
                   help="Skip the conversation collector")
    p.add_argument("--from-local", metavar="DIR",
                   help="Skip GitHub clone, ingest existing clones under DIR")
    p.add_argument("--include-forks", action="store_true")

    # LLM
    p.add_argument("--no-llm", action="store_true",
                   help="Disable NVIDIA NIM concept extraction")
    p.add_argument("--llm-top-n", type=int, default=25,
                   help="Augment at most N repos with LLM (cost guard)")

    # processing
    p.add_argument("--max-files", type=int, default=200,
                   help="Per-repo cap on files to AST-parse")
    p.add_argument("--repo-timeout", type=int, default=180,
                   help="Per-repo ingestion timeout in seconds (0 = no limit)")
    p.add_argument("--checkpoint-every", type=int, default=10,
                   help="Export graph_json checkpoint every N repos (0 = off)")
    p.add_argument("--keep-repos", action="store_true",
                   help="Do not delete clones after ingestion")
    p.add_argument("--person-login",
                   help="Owner login for the central Person node")

    # outputs
    p.add_argument("--output-graph", default="data/graph/knowledge_graph.json")
    p.add_argument("--output-vault", default="data/wiki")
    p.add_argument("--neo4j", action="store_true",
                   help="Also push to Neo4j (uses NEO4J_* env vars)")
    p.add_argument("--neo4j-wipe", action="store_true",
                   help="Wipe :UniversalNode subgraph before push")

    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


# ── main flow ─────────────────────────────────────────────────────────────


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    person = args.person_login or _detect_person_login()
    logger.info("Person node = %s", person or "(none)")

    builder = UniversalGraphBuilder(person_login=person)
    llm = None if args.no_llm else LLMConceptExtractor()
    if llm and not llm.available:
        logger.warning("NVIDIA_API_KEY not set — disabling LLM augmentation")
        llm = None

    stats = {
        "github_ingested": 0, "github_failed": 0,
        "vercel_ingested": 0, "cloudflare_ingested": 0,
        "conversations_ingested": 0,
        "llm_augmentations": 0,
    }
    t0 = time.time()

    # ── 1. GitHub (streaming) ──────────────────────────────────────────────
    if args.from_local:
        local_root = Path(args.from_local)
        if not local_root.is_dir():
            logger.error("--from-local dir not found: %s", local_root)
            return 2
        for sub in sorted(p for p in local_root.iterdir() if p.is_dir()):
            try:
                _ingest_local_repo(builder, sub, args, person, llm, stats)
            except Exception as e:
                stats["github_failed"] += 1
                logger.exception("Local repo %s failed: %s", sub.name, e)
    elif not args.skip_github:
        try:
            collector = GitHubCollector()
            max_repos = args.max_repos if args.max_repos > 0 else None
            for repo_data, analysis in collector.collect_streaming(
                max_repos=max_repos, include_forks=args.include_forks
            ):
                _ingest_streamed_repo(builder, repo_data, analysis, args,
                                      person, llm, stats)
                if (args.checkpoint_every > 0
                        and stats["github_ingested"] > 0
                        and stats["github_ingested"] % args.checkpoint_every == 0):
                    try:
                        cp = export_graph_json(builder.graph,
                                               args.output_graph + ".checkpoint")
                        logger.info("    checkpoint after %d repos -> %s",
                                    stats["github_ingested"], cp)
                    except Exception as e:
                        logger.warning("    checkpoint failed: %s", e)
        except Exception as e:
            logger.exception("GitHub streaming failed: %s", e)

    # ── 2. Vercel ──────────────────────────────────────────────────────────
    if not args.skip_vercel:
        try:
            v = VercelCollector()
            projects = v.get_projects_from_vercel()
            for proj in projects:
                try:
                    builder.add_vercel_project(proj)
                    stats["vercel_ingested"] += 1
                except Exception as e:
                    logger.warning("vercel ingest failed for %s: %s",
                                   proj.get("name"), e)
            logger.info("Vercel: ingested %s projects", stats["vercel_ingested"])
        except Exception as e:
            logger.warning("Vercel collection skipped: %s", e)

    # ── 3. Cloudflare ──────────────────────────────────────────────────────
    if not args.skip_cloudflare:
        try:
            cf = CloudflareCollector()
            workers = cf.fetch_workers() if hasattr(cf, "fetch_workers") else []
            for w in workers:
                try:
                    builder.add_cloudflare_worker(w)
                    stats["cloudflare_ingested"] += 1
                except Exception as e:
                    logger.warning("cloudflare ingest failed: %s", e)
            logger.info("Cloudflare: ingested %s workers", stats["cloudflare_ingested"])
        except Exception as e:
            logger.warning("Cloudflare collection skipped: %s", e)

    # ── 4. Conversations ───────────────────────────────────────────────────
    if not args.skip_conversations:
        try:
            cc = ConversationCollector()
            r = cc.collect_all()
            for c in r.get("collected_conversations", []):
                try:
                    builder.add_conversation({
                        "provider": c.get("source", "manual"),
                        "id": c.get("id"),
                        "title": c.get("name"),
                        "created_at": c.get("created_at"),
                        "summary": c.get("summary", ""),
                    })
                    stats["conversations_ingested"] += 1
                except Exception as e:
                    logger.warning("conversation ingest failed: %s", e)
            logger.info("Conversations: ingested %s",
                        stats["conversations_ingested"])
        except Exception as e:
            logger.warning("Conversation collection skipped: %s", e)

    # ── 5. Finalize + export ───────────────────────────────────────────────
    graph = builder.finalize()
    graph_stats = graph.stats()
    logger.info("Graph built: %s nodes / %s edges / %s evidence",
                graph_stats["nodes_total"], graph_stats["edges_total"],
                graph_stats["evidence_total"])

    out_json = export_graph_json(graph, args.output_graph)
    out_vault = export_wiki_vault(graph, args.output_vault)
    logger.info("Wrote %s and %s", out_json, out_vault)

    neo4j_stats = None
    if args.neo4j:
        try:
            neo4j_stats = export_to_neo4j(graph, wipe_first=args.neo4j_wipe)
        except Exception as e:
            logger.exception("Neo4j export failed: %s", e)

    summary = {
        "elapsed_seconds": round(time.time() - t0, 1),
        "collected": stats,
        "graph_stats": graph_stats,
        "outputs": {
            "graph_json": str(out_json),
            "wiki_vault": str(out_vault),
            "neo4j": neo4j_stats,
        },
    }
    Path("data").mkdir(exist_ok=True)
    Path("data/universal_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return 0


# ── helpers ───────────────────────────────────────────────────────────────


def _ingest_streamed_repo(
    builder: UniversalGraphBuilder,
    repo_data: dict,
    analysis: dict,
    args: argparse.Namespace,
    person: str,
    llm: LLMConceptExtractor | None,
    stats: dict,
) -> None:
    full = repo_data.get("full_name") or repo_data.get("name", "")
    if "/" in full:
        owner, name = full.split("/", 1)
    else:
        owner, name = person or "unknown", repo_data.get("name", "unknown")
    repo_path = analysis.get("repo_path")

    # Pre-flight: huge repos with vendored upstreams (e.g. carbonscope/suna,
    # pinn-rainmaking-dashboard) hang AST parsers in C-level extensions where
    # SIGALRM can't preempt them. Downgrade to metadata-only.
    if repo_path:
        try:
            size_mb = _dir_size_mb(repo_path)
        except Exception:
            size_mb = 0
        if size_mb > 250:
            logger.warning(
                "    %s/%s is %.0f MB — too large, downgrading to metadata-only",
                owner, name, size_mb,
            )
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
            except Exception:
                pass
            repo_path = None
            analysis["repo_path"] = None

    spec = RepoSpec(
        owner=owner, name=name, local_path=repo_path,
        max_files=args.max_files,
        readme=repo_data.get("readme", ""),
        metadata=repo_data,
    )
    try:
        before = builder.graph.stats()
        with _repo_timeout(args.repo_timeout):
            rid = builder.add_repo(spec)
        after = builder.graph.stats()
        delta = {k: after.get(k, 0) - before.get(k, 0)
                 for k in ("node:file", "node:function", "node:class",
                           "node:technology", "node:document", "node:section")}
        stats["github_ingested"] += 1
        clone_status = "cloned" if repo_path else "metadata-only"
        logger.info(
            "[%3d] %s/%s (%s) — files=%d funcs=%d classes=%d techs=%d docs=%d sections=%d",
            stats["github_ingested"], owner, name, clone_status,
            delta["node:file"], delta["node:function"], delta["node:class"],
            delta["node:technology"], delta["node:document"], delta["node:section"],
        )
        if (
            llm and llm.available
            and stats["github_ingested"] <= args.llm_top_n
        ):
            _llm_augment(llm, builder, spec, rid, stats)
    except _RepoTimeout as e:
        stats["github_failed"] += 1
        logger.warning("    TIMED OUT ingesting %s/%s: %s", owner, name, e)
    except Exception as e:
        stats["github_failed"] += 1
        logger.exception("Failed to ingest %s/%s: %s", owner, name, e)
    finally:
        if repo_path and not args.keep_repos:
            try:
                size_mb = _dir_size_mb(repo_path)
                shutil.rmtree(repo_path, ignore_errors=True)
                logger.info("    cleaned up clone %s (freed %.1f MB)",
                            repo_path, size_mb)
            except Exception as e:
                logger.warning("    cleanup failed for %s: %s", repo_path, e)
        gc.collect()


def _ingest_local_repo(
    builder: UniversalGraphBuilder,
    repo_dir: Path,
    args: argparse.Namespace,
    person: str,
    llm: LLMConceptExtractor | None,
    stats: dict,
) -> None:
    spec = RepoSpec(
        owner=person or "local", name=repo_dir.name,
        local_path=str(repo_dir),
        max_files=args.max_files,
    )
    rid = builder.add_repo(spec)
    stats["github_ingested"] += 1
    logger.info("[%3d] ingested local %s", stats["github_ingested"], repo_dir.name)
    if llm and llm.available and stats["github_ingested"] <= args.llm_top_n:
        _llm_augment(llm, builder, spec, rid, stats)


def _llm_augment(
    llm: LLMConceptExtractor,
    builder: UniversalGraphBuilder,
    spec: RepoSpec,
    rid: str,
    stats: dict,
) -> None:
    excerpts = _collect_excerpts(spec.local_path, max_files=4, max_chars=1200) \
        if spec.local_path else []
    readme = spec.readme or (spec.metadata or {}).get("readme", "")
    if not (readme or excerpts):
        return
    result = llm.extract(
        repo_label=f"{spec.owner}/{spec.name}",
        readme=readme,
        code_excerpts=excerpts,
        languages=list((spec.metadata or {}).get("languages", {}).keys()),
    )
    if result:
        emitted = llm.emit_into_graph(builder.graph, rid, result)
        stats["llm_augmentations"] += sum(emitted.values())


def _collect_excerpts(root: str, *, max_files: int, max_chars: int) -> list[dict]:
    if not root:
        return []
    base = Path(root)
    if not base.exists():
        return []
    cands: list[Path] = []
    for cand in ("main.py", "app.py", "src/main.py", "src/app.py",
                 "src/index.ts", "src/index.js", "index.ts", "index.js",
                 "package.json", "pyproject.toml", "Cargo.toml",
                 "go.mod", "main.go"):
        p = base / cand
        if p.is_file():
            cands.append(p)
    if len(cands) < max_files:
        for ext in (".py", ".ts", ".js", ".go", ".rs"):
            for p in base.rglob(f"*{ext}"):
                if p in cands:
                    continue
                cands.append(p)
                if len(cands) >= max_files:
                    break
            if len(cands) >= max_files:
                break
    out = []
    for p in cands[:max_files]:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        out.append({"path": str(p.relative_to(base)), "excerpt": text[:max_chars]})
    return out


def _dir_size_mb(path: str) -> float:
    p = Path(path)
    if not p.exists():
        return 0.0
    total = 0
    for f in p.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                total += f.stat().st_size
            except Exception:
                pass
    return total / (1024 * 1024)


def _detect_person_login() -> str | None:
    # Prefer env, fall back to GitHub /user.
    if os.getenv("GITHUB_LOGIN"):
        return os.getenv("GITHUB_LOGIN")
    try:
        from app.collectors.github_collector import GitHubCollector
        return GitHubCollector().get_authenticated_user()
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
