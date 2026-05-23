"""Graph RAG Pipeline - orchestrates collection and knowledge graph building."""
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.config import (
    DATA_DIR,
    RAW_DIR,
    GITHUB_TOKEN,
    VERCEL_TOKEN,
    CLOUDFLARE_TOKEN,
    MAX_REPOS,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    MIN_FREE_DISK_GB,
    INCLUDE_FORKS,
    ENABLE_CONVERSATION_COLLECTOR,
)
from app.collectors.github_collector import GitHubCollector
from app.collectors.vercel_collector import VercelCollector
from app.collectors.cloudflare_collector import CloudflareCollector
from app.graph_store import Neo4jStore, KnowledgeGraphConfig
from app.extractors import NarrativeBuilder
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import EMBEDDINGS_DIR, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class GraphRAGPipeline:
    """Orchestrates the complete Graph RAG pipeline with per-repo transactional ingest
    and automatic repository cleanup only after successful Neo4j commit."""

    def __init__(self, max_repos: Optional[int] = None):
        self.max_repos = max_repos or MAX_REPOS
        self.results: Dict[str, Any] = {
            "stages": {},
            "errors": [],
            "started_at": None,
            "completed_at": None,
        }
        self.failed_repos_log = DATA_DIR / "failed_repos.json"

        # Initialize collectors
        self.github_collector = GitHubCollector()
        self.vercel_collector = VercelCollector()
        self.cloudflare_collector = CloudflareCollector()

        # Initialize narrative builder
        self.narrative_builder = NarrativeBuilder()

        # Initialize Neo4j store
        self.neo4j_config = KnowledgeGraphConfig(
            uri=NEO4J_URI or "bolt://localhost:7687",
            user=NEO4J_USER or "neo4j",
            password=NEO4J_PASSWORD or "password",
            database=NEO4J_DATABASE or "neo4j",
        )
        self.store = None

        # Initialize RAG components for indexing narratives
        self.chunker = TextChunker(chunk_size=500, overlap=50)
        self.embedder = Embedder(model_name=EMBEDDING_MODEL)
        self.vector_store = VectorStore(
            dimension=384,
            index_path=str(EMBEDDINGS_DIR / "faiss_index")
        )

    def _get_store(self) -> Neo4jStore:
        """Get or create Neo4j store connection."""
        if self.store is None:
            self.store = Neo4jStore(self.neo4j_config)
            self.store.connect()
            self.store.create_indexes()
            self.store.create_constraints()
        return self.store

    def _check_disk_space(self) -> bool:
        """Abort if free disk space is below MIN_FREE_DISK_GB."""
        try:
            stat = shutil.disk_usage(RAW_DIR)
            free_gb = stat.free / (1024 ** 3)
            if free_gb < MIN_FREE_DISK_GB:
                msg = f"Disk space too low: {free_gb:.2f} GB free (need {MIN_FREE_DISK_GB} GB)"
                logger.error(msg)
                self.results["errors"].append(msg)
                return False
            logger.info(f"Disk space OK: {free_gb:.2f} GB free")
            return True
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True

    def _log_failed_repo(self, repo_name: str, repo_path: str, error: str) -> None:
        """Record a failed repo for later retry/debug."""
        entry = {
            "repo": repo_name,
            "path": repo_path,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        existing = []
        if self.failed_repos_log.exists():
            try:
                existing = json.loads(self.failed_repos_log.read_text())
            except Exception:
                existing = []
        existing.append(entry)
        self.failed_repos_log.write_text(json.dumps(existing, indent=2))
        logger.info(f"Logged failed repo {repo_name} to {self.failed_repos_log}")

    def _ingest_github_repo(self, repo_data: Dict[str, Any], analysis: Dict[str, Any],
                            github_user: str) -> bool:
        """Ingest a single GitHub repo into Neo4j, generate narrative, cleanup on success.

        Returns True if ingestion succeeded and clone was cleaned up.
        Returns False on failure (clone left on disk for debug).
        """
        repo_name = repo_data.get("name", "unknown")
        project_id = f"github:{repo_name}"
        repo_path = analysis.get("repo_path", "")
        store = self._get_store()

        try:
            # 1. Upsert project with temporal properties
            store.upsert_project(
                project_id=project_id,
                name=repo_data.get("description") or repo_name,
                source="github",
                url=repo_data.get("url", ""),
                description=repo_data.get("description", ""),
                properties={
                    "created_at": repo_data.get("created_at", ""),
                    "pushed_at": repo_data.get("pushed_at", ""),
                    "updated_at": repo_data.get("updated_at", ""),
                    "first_commit_at": repo_data.get("first_commit_at", ""),
                    "last_commit_at": repo_data.get("last_commit_at", ""),
                    "stars": repo_data.get("stars", 0),
                    "language": repo_data.get("language", ""),
                }
            )

            # Link person to project
            if github_user:
                store.link_person_to_project(f"github:{github_user}", project_id)

            # 2. Store languages as skills
            for lang, bytes_count in repo_data.get("languages", {}).items():
                store.upsert_skill(lang, "language", 0.85)
                store.link_person_to_skill(
                    f"github:{github_user}" if github_user else "me",
                    lang, "language", 0.85,
                    evidence=f"GitHub repo: {repo_name}"
                )
                store.link_skill_to_project(
                    lang, "language", project_id,
                    evidence=f"{bytes_count} bytes in {repo_name}"
                )

            # 3. Store extracted skills
            for skill in repo_data.get("extracted_skills", []):
                skill_name = skill.get("name", "")
                category = skill.get("category", "tool")
                confidence = skill.get("confidence", 0.5)
                if skill_name:
                    store.upsert_skill(skill_name, category, confidence)
                    store.link_person_to_skill(
                        f"github:{github_user}" if github_user else "me",
                        skill_name, category, confidence,
                        evidence=skill.get("evidence", f"Extracted from {repo_name}")
                    )

            # 4. Generate and store narrative
            narrative = self.narrative_builder.generate(repo_data)
            if narrative and narrative.text:
                narrative_id = f"narrative:{project_id}"
                store.upsert_narrative(
                    narrative_id=narrative_id,
                    text=narrative.text,
                    source_project_id=project_id,
                    period_start=narrative.period_start,
                    period_end=narrative.period_end,
                )
                for skill_name in narrative.mentioned_skills:
                    # Best-effort link; skill may not exist in graph if category unknown
                    store.link_narrative_to_skill(narrative_id, skill_name, "language")
                for tech_name in narrative.mentioned_technologies:
                    store.link_narrative_to_technology(narrative_id, tech_name)

            # 5. Index narrative + description into vector store for RAG
            self._index_repo_vectors(repo_data, narrative)

            # 6. Cleanup cloned repo only after successful Neo4j + vector commit
            if repo_path and os.path.isdir(repo_path):
                self.github_collector.cleanup_repo(repo_path)

            return True

        except Exception as e:
            logger.error(f"Ingestion failed for {repo_name}: {e}")
            if repo_path:
                self._log_failed_repo(repo_name, repo_path, str(e))
            return False

    def _index_repo_vectors(self, repo_data: Dict[str, Any],
                            narrative: Optional[Any]) -> None:
        """Chunk and embed repo text into the FAISS vector store.

        Best-effort: failures are logged but do not block the pipeline.
        """
        try:
            repo_name = repo_data.get("name", "unknown")
            project_id = f"github:{repo_name}"
            texts_to_index = []

            # Build a composite document from description + readme excerpt + skills
            description = repo_data.get("description", "")
            readme = repo_data.get("readme", "")
            languages = ", ".join(repo_data.get("languages", {}).keys())
            skills = ", ".join(s.get("name", "") for s in repo_data.get("extracted_skills", []))

            doc_parts = [f"Project: {repo_name}"]
            if description:
                doc_parts.append(f"Description: {description}")
            if languages:
                doc_parts.append(f"Languages: {languages}")
            if skills:
                doc_parts.append(f"Skills: {skills}")
            if readme:
                doc_parts.append(f"README: {readme[:1500]}")

            composite_doc = "\n\n".join(doc_parts)
            texts_to_index.append((composite_doc, {
                "type": "project",
                "project_id": project_id,
                "source": "github",
                "text": composite_doc[:200],
            }))

            # Index narrative separately if present
            if narrative and narrative.text:
                texts_to_index.append((narrative.text, {
                    "type": "narrative",
                    "project_id": project_id,
                    "source": "github",
                    "text": narrative.text[:200],
                }))

            # Embed and add each document
            for text, metadata in texts_to_index:
                chunks = self.chunker.chunk(text, source=project_id)
                if not chunks:
                    continue
                texts = [c.text for c in chunks]
                embeddings = self.embedder.embed_batch(texts)
                for emb, chunk in zip(embeddings, chunks):
                    meta = {**metadata, "chunk_id": chunk.chunk_id}
                    self.vector_store.add(emb, meta)

            logger.info(f"Indexed {len(texts_to_index)} documents into vector store for {repo_name}")
        except Exception as e:
            logger.warning(f"Vector indexing failed for {repo_data.get('name', 'unknown')}: {e}")

    def _store_github_data(self, github_result: Dict[str, Any]):
        """Store GitHub collection results in Neo4j knowledge graph, repo by repo."""
        store = self._get_store()
        github_user = self.github_collector.get_authenticated_user()

        # Upsert person
        if github_user:
            store.upsert_person(
                person_id=f"github:{github_user}",
                name=github_user,
                email="",
                properties={"source": "github"}
            )

        analyses = {a["repo"]: a for a in github_result.get("deep_analyses", [])}
        ingested = 0
        failed = 0

        for repo_data in github_result.get("collected_repos", []):
            repo_name = repo_data.get("name", "unknown")
            analysis = analyses.get(repo_name, {})

            if analysis.get("status") == "success":
                if self._ingest_github_repo(repo_data, analysis, github_user):
                    ingested += 1
                else:
                    failed += 1
            else:
                # Store metadata-only project for repos that couldn't be cloned
                project_id = f"github:{repo_name}"
                store.upsert_project(
                    project_id=project_id,
                    name=repo_data.get("description") or repo_name,
                    source="github",
                    url=repo_data.get("url", ""),
                    description=repo_data.get("description", ""),
                    properties={
                        "created_at": repo_data.get("created_at", ""),
                        "pushed_at": repo_data.get("pushed_at", ""),
                        "updated_at": repo_data.get("updated_at", ""),
                        "stars": repo_data.get("stars", 0),
                    }
                )
                if github_user:
                    store.link_person_to_project(f"github:{github_user}", project_id)
                ingested += 1

        print(f" ✓ Ingested {ingested} GitHub repos into Neo4j ({failed} failed)")

    def _store_vercel_data(self, vercel_result: Dict[str, Any]):
        """Store Vercel collection results in Neo4j knowledge graph."""
        store = self._get_store()

        for project in vercel_result.get("collected_projects", []):
            project_name = project.get("name", "unknown")
            project_id = f"vercel:{project_name}"

            store.upsert_project(
                project_id=project_id,
                name=project_name,
                source="vercel",
                url=project.get("url", ""),
                description=f"Vercel project - {project.get('framework', 'unknown framework')}",
                properties={
                    "created_at": project.get("created_at", ""),
                    "updated_at": project.get("updated_at", ""),
                }
            )

            # Store framework as skill
            framework = project.get("framework")
            if framework:
                store.upsert_skill(framework, "framework", 0.80)
                store.link_skill_to_project(
                    framework, "framework", project_id,
                    evidence="Vercel project framework"
                )

        print(f" ✓ Stored {len(vercel_result.get('collected_projects', []))} Vercel projects in Neo4j")

    def _store_cloudflare_data(self, cloudflare_result: Dict[str, Any]):
        """Store Cloudflare collection results in Neo4j knowledge graph."""
        store = self._get_store()

        # Store workers
        for worker in cloudflare_result.get("collected_workers", []):
            worker_name = worker.get("name", "unknown")
            project_id = f"cloudflare:worker:{worker_name}"

            store.upsert_project(
                project_id=project_id,
                name=worker_name,
                source="cloudflare",
                url="",
                description="Cloudflare Worker",
                properties={
                    "created_at": worker.get("created_at", ""),
                }
            )

            store.upsert_skill("Cloudflare Workers", "platform", 0.80)
            store.link_skill_to_project(
                "Cloudflare Workers", "platform", project_id,
                evidence="Cloudflare Worker deployment"
            )

        # Store Pages
        for page in cloudflare_result.get("collected_pages", []):
            page_name = page.get("name", "unknown")
            project_id = f"cloudflare:pages:{page_name}"

            store.upsert_project(
                project_id=project_id,
                name=page_name,
                source="cloudflare",
                url="",
                description="Cloudflare Pages project",
                properties={
                    "created_at": page.get("created_at", ""),
                }
            )

            store.upsert_skill("Cloudflare Pages", "platform", 0.75)
            store.link_skill_to_project(
                "Cloudflare Pages", "platform", project_id,
                evidence="Cloudflare Pages deployment"
            )

        # Store zones
        for zone in cloudflare_result.get("collected_zones", []):
            store.upsert_technology(zone.get("name", "unknown-zone"))

        total = len(cloudflare_result.get("collected_workers", [])) + len(cloudflare_result.get("collected_pages", []))
        print(f" ✓ Stored {total} Cloudflare resources in Neo4j")

    def run(self) -> Dict[str, Any]:
        """Alias for run_full_pipeline for backward compatibility."""
        return self.run_full_pipeline()

    def run_full_pipeline(self) -> Dict[str, Any]:
        print("=" * 60)
        print("Graph RAG Resume Agent - Full Collection Pipeline")
        print("=" * 60)
        self.results["started_at"] = datetime.utcnow().isoformat()

        # Disk guard
        if not self._check_disk_space():
            self.results["stages"]["disk_guard"] = {"status": "blocked", "reason": "insufficient_disk_space"}
            return self.results

        # Stage 1: GitHub Collection
        print("\n" + "=" * 60)
        print("Stage 1: GitHub Collection")
        print("=" * 60)
        try:
            github_result = self.github_collector.collect_all(
                max_repos=self.max_repos,
                include_forks=INCLUDE_FORKS
            )
            self.results["stages"]["github"] = {
                "status": "success",
                "repos_collected": github_result.get("repos_collected", 0),
                "deep_analyses": github_result.get("deep_analyses", []),
                "collected_repos": github_result.get("collected_repos", []),
            }
            # Store GitHub data in Neo4j
            self._store_github_data(github_result)
        except Exception as e:
            self.results["stages"]["github"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"GitHub collection failed: {e}")
            logger.error(f"GitHub collection failed: {e}")

        # Stage 2: Vercel Collection
        print("\n" + "=" * 60)
        print("Stage 2: Vercel Collection")
        print("=" * 60)
        try:
            vercel_result = self.vercel_collector.collect_all()
            self.results["stages"]["vercel"] = {
                "status": "success",
                "projects_collected": vercel_result.get("total_projects", 0),
                "collected_projects": vercel_result.get("collected_projects", []),
            }
            # Store Vercel data in Neo4j
            self._store_vercel_data(vercel_result)
        except Exception as e:
            self.results["stages"]["vercel"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Vercel collection failed: {e}")
            logger.error(f"Vercel collection failed: {e}")

        # Stage 3: Cloudflare Collection
        print("\n" + "=" * 60)
        print("Stage 3: Cloudflare Collection")
        print("=" * 60)
        try:
            cloudflare_result = self.cloudflare_collector.collect_all()
            self.results["stages"]["cloudflare"] = {
                "workers_count": cloudflare_result.get("workers_count", 0),
                "pages_count": cloudflare_result.get("pages_count", 0),
                "zones_count": cloudflare_result.get("zones_count", 0),
                "status": "success",
            }
            # Store Cloudflare data in Neo4j
            self._store_cloudflare_data(cloudflare_result)
        except Exception as e:
            self.results["stages"]["cloudflare"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Cloudflare collection failed: {e}")
            logger.error(f"Cloudflare collection failed: {e}")

        # Stage 4: Conversation Collection (optional, disabled by default)
        if ENABLE_CONVERSATION_COLLECTOR:
            print("\n" + "=" * 60)
            print("Stage 4: Conversation Artifact Collection")
            print("=" * 60)
            try:
                from app.collectors.conversation_collector import ConversationCollector
                conversation_collector = ConversationCollector()
                conversation_result = conversation_collector.collect_all()
                self.results["stages"]["conversation"] = {
                    "artifacts_found": conversation_result.get("artifact_count", 0),
                    "status": "success",
                }
            except Exception as e:
                self.results["stages"]["conversation"] = {"status": "error", "error": str(e)}
                self.results["errors"].append(f"Conversation collection failed: {e}")

        # Stage 5: Save vector store index to disk
        print("\n" + "=" * 60)
        print("Stage 5: Save Vector Store")
        print("=" * 60)
        try:
            self.vector_store.save()
            print(" ✓ Vector store saved to disk")
            self.results["stages"]["vector_store"] = {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            self.results["stages"]["vector_store"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Vector store save failed: {e}")

        # Save pipeline results
        self.results["completed_at"] = datetime.utcnow().isoformat()
        self._save_pipeline_results()
        self._print_summary()

        # Close Neo4j connection
        if self.store:
            self.store.close()

        return self.results

    def _save_pipeline_results(self):
        results_path = DATA_DIR / "pipeline_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n Pipeline results saved to {results_path}")

    def _print_summary(self):
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)
        for stage, result in self.results.get("stages", {}).items():
            status = result.get("status", "unknown")
            if status == "success":
                print(f"  {stage.capitalize()}: OK")
            else:
                print(f"  {stage.capitalize()}: {status.upper()} - {result.get('error', '')}")

        # Print Neo4j stats
        if self.store:
            try:
                stats = self.store.get_stats()
                print(f"\nNeo4j Knowledge Graph:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            except Exception:
                pass

        if self.results.get("errors"):
            print(f"\n{len(self.results['errors'])} errors occurred:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        # Print failed repos if any
        if self.failed_repos_log.exists():
            try:
                failed = json.loads(self.failed_repos_log.read_text())
                if failed:
                    print(f"\nFailed repos log ({len(failed)} entries): {self.failed_repos_log}")
            except Exception:
                pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Graph RAG collection pipeline")
    parser.add_argument("--max-repos", type=int, default=0, help="Maximum number of repos to collect (0 = all)")
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories")
    args = parser.parse_args()
    pipeline = GraphRAGPipeline(max_repos=args.max_repos)
    results = pipeline.run_full_pipeline()
    has_errors = any(stage.get("status") == "error" for stage in results.get("stages", {}).values())
    return 1 if has_errors else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
