#!/usr/bin/env python3
# Enhanced Collection Pipeline - Memory-efficient with proper cleanup
# Features:
# - Streamlined repo processing (no accumulate in memory)
# - Immediate cleanup after successful Neo4j commit
# - No SkillEvidence type errors (serialize to dict)
# - Compact results logging (no full repo data)
# - Source-separated processing for GitHub, Vercel, Cloudflare

import json
import logging
import os
import shutil
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

from app.config import (
    DATA_DIR,
    RAW_DIR,
    GITHUB_TOKEN,
    VERCEL_TOKEN,
    CLOUDFLARE_TOKEN,
    CLOUDFLARE_ACCOUNT_ID,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
)
from app.graph_store.neo4j_store import Neo4jStore, KnowledgeGraphConfig
from app.collectors.github_collector import GitHubCollector
from app.collectors.vercel_collector import VercelCollector
from app.collectors.cloudflare_collector import CloudflareCollector
from app.cleaner import DataCleaner, CleanedProject

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Memory limits
MAX_REPOS_IN_MEMORY = 5  # Process repos in small batches
CHUNK_SIZE = 50  # For file processing


class EnhancedPipeline:
    def __init__(self, max_repos: int = 50, clean_graph: bool = False):
        self.max_repos = max_repos
        self.clean_graph = clean_graph
        self.results = {
            'github': {'ingested': 0, 'failed': 0, 'repos': []},
            'vercel': {'ingested': 0, 'failed': 0},
            'cloudflare': {'ingested': 0, 'failed': 0}
        }
        
        # Initialize Neo4j store
        self.store = self._create_store()
        
        # Optionally clear graph for fresh start
        if self.clean_graph:
            logger.info('Clearing Neo4j graph for fresh start...')
            self.store.clear()
            logger.info('Neo4j graph cleared')
        
        # Initialize data cleaner (normalizes before Neo4j ingest)
        self.cleaner = DataCleaner()
        
        # Initialize collectors
        self.github_collector = GitHubCollector()
        self.vercel_collector = VercelCollector()
        self.cloudflare_collector = CloudflareCollector()
        
        # Ensure clean state
        self._ensure_clean_directories()

    def _create_store(self) -> Neo4jStore:
        config = KnowledgeGraphConfig(
            uri=NEO4J_URI or 'bolt://localhost:7687',
            user=NEO4J_USER or 'neo4j',
            password=NEO4J_PASSWORD or 'password',
            database=NEO4J_DATABASE or 'neo4j',
        )
        store = Neo4jStore(config)
        store.connect()
        store.create_indexes()
        store.create_constraints()
        return store

    def _ensure_clean_directories(self):
        # Clean raw directory but keep structure
        if RAW_DIR.exists():
            for item in RAW_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
        else:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clean failed repos log
        failed_log = DATA_DIR / 'failed_repos.json'
        if failed_log.exists():
            failed_log.unlink()

    def _cleanup_repo(self, repo_path: Path) -> bool:
        try:
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)
            return True
        except Exception as e:
            logger.warning(f'Failed to cleanup {repo_path}: {e}')
            return False

    def _upsert_cleaned_project(self, project: CleanedProject, github_user: str = "") -> None:
        """Upsert a CleanedProject into Neo4j with all its skills and links."""
        self.store.upsert_project(
            project_id=project.project_id,
            name=project.name,
            source=project.source,
            url=project.url,
            description=project.description,
            properties=project.properties,
        )

        if github_user:
            self.store.link_person_to_project(f"github:{github_user}", project.project_id)

        for skill in project.skills:
            try:
                self.store.upsert_skill(
                    skill.name, skill.category, skill.confidence,
                    {"evidence_count": skill.evidence_count},
                )
                if github_user:
                    self.store.link_person_to_skill(
                        f"github:{github_user}", skill.name, skill.category,
                        skill.confidence, evidence=skill.evidence_summary,
                    )
                self.store.link_skill_to_project(
                    skill.name, skill.category, project.project_id,
                    evidence=skill.evidence_summary,
                )
            except Exception as e:
                logger.warning(f"Skill upsert failed for {skill.name}: {e}")

        # Cross-source links (e.g. Vercel project linked to GitHub repo)
        # Uses Neo4j's generic relationship creation via Cypher
        for linked_id in project.linked_project_ids:
            try:
                # Create a RELATED_TO relationship between projects
                with self.store.driver.session() as session:
                    session.run(
                        """
                        MATCH (a:Project {id: $id_a}), (b:Project {id: $id_b})
                        MERGE (a)-[:RELATED_TO]->(b)
                        """,
                        {"id_a": project.project_id, "id_b": linked_id},
                    )
            except Exception as e:
                logger.debug(f"Cross-source link failed ({project.project_id} -> {linked_id}): {e}")

    def process_github_repos(self) -> Dict[str, int]:
        logger.info('=' * 60)
        logger.info('Processing GitHub repositories (streaming mode)')
        logger.info('=' * 60)
        
        github_user = self.github_collector.get_authenticated_user()
        if not github_user:
            logger.warning('No GitHub user - skipping GitHub collection')
            return {'ingested': 0, 'failed': 0}
        
        # Upsert person
        self.store.upsert_person(
            person_id=f'github:{github_user}',
            name=github_user,
            properties={'source': 'github'}
        )
        
        ingested = 0
        failed = 0

        # Use streaming collection: one repo at a time → ingest → cleanup
        try:
            for repo_data, analysis in self.github_collector.collect_streaming(
                max_repos=self.max_repos,
                include_forks=False
            ):
                repo_name = repo_data.get('name', 'unknown')
                repo_path = analysis.get('repo_path')

                try:
                    # Clean and normalize data before Neo4j ingestion
                    cleaned = self.cleaner.clean_github_repo(repo_data)

                    # Upsert into Neo4j via the cleaned project
                    self._upsert_cleaned_project(cleaned, github_user)

                    # Cleanup cloned repo IMMEDIATELY after successful ingest
                    if repo_path:
                        self._cleanup_repo(Path(repo_path))
                    
                    ingested += 1
                    self.results['github']['repos'].append({
                        'name': repo_name,
                        'status': 'success',
                        'skills_count': len(cleaned.skills),
                        'languages': list(repo_data.get('languages', {}).keys())
                    })
                    
                    # Force garbage collection after each repo
                    gc.collect()
                    
                except Exception as e:
                    logger.error(f'Failed to ingest {repo_name}: {e}')
                    failed += 1
                    self.results['github']['repos'].append({
                        'name': repo_name,
                        'status': 'failed',
                        'error': str(e)
                    })
                    if repo_path:
                        self._cleanup_repo(Path(repo_path))
                    self._log_failed_repo(repo_name, repo_path or '', str(e))
                    
        except Exception as e:
            logger.error(f'GitHub collection failed: {e}')
        
        self.results['github']['ingested'] = ingested
        self.results['github']['failed'] = failed
        
        logger.info(f'GitHub: {ingested} ingested, {failed} failed')
        return {'ingested': ingested, 'failed': failed}

    def process_vercel(self) -> Dict[str, int]:
        logger.info('=' * 60)
        logger.info('Processing Vercel projects')
        logger.info('=' * 60)

        if not VERCEL_TOKEN:
            logger.warning('No VERCEL_TOKEN - skipping Vercel collection')
            return {'ingested': 0, 'failed': 0}

        try:
            vercel_result = self.vercel_collector.collect_all()
        except Exception as e:
            logger.error(f'Vercel collection failed: {e}')
            return {'ingested': 0, 'failed': 0}

        ingested = 0
        for project in vercel_result.get('collected_projects', []):
            project_name = project.get('name', 'unknown')

            try:
                # Clean and normalize data before Neo4j ingestion
                cleaned = self.cleaner.clean_vercel_project(project)
                self._upsert_cleaned_project(cleaned)
                ingested += 1

            except Exception as e:
                logger.error(f'Failed to ingest Vercel project {project_name}: {e}')

        self.results['vercel']['ingested'] = ingested
        logger.info(f'Vercel: {ingested} projects ingested')
        return {'ingested': ingested, 'failed': 0}

    def process_cloudflare(self) -> Dict[str, int]:
        logger.info('=' * 60)
        logger.info('Processing Cloudflare resources')
        logger.info('=' * 60)

        if not CLOUDFLARE_TOKEN:
            logger.warning('No CLOUDFLARE_TOKEN - skipping Cloudflare collection')
            return {'ingested': 0, 'failed': 0}

        try:
            cf_result = self.cloudflare_collector.collect_all()
        except Exception as e:
            logger.error(f'Cloudflare collection failed: {e}')
            return {'ingested': 0, 'failed': 0}

        ingested = 0

        # Workers - clean and normalize each one
        for worker in cf_result.get('collected_workers', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_worker(worker)
                self._upsert_cleaned_project(cleaned)
                ingested += 1
            except Exception as e:
                logger.error(f'Failed to ingest Cloudflare worker {worker.get("name", "?")}: {e}')

        # Pages - clean and normalize each one
        for page in cf_result.get('collected_pages', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_page(page)
                self._upsert_cleaned_project(cleaned)
                ingested += 1
            except Exception as e:
                logger.error(f'Failed to ingest Cloudflare page {page.get("name", "?")}: {e}')

        # Zones - clean and normalize each one
        for zone in cf_result.get('collected_zones', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_zone(zone)
                self._upsert_cleaned_project(cleaned)
                ingested += 1
            except Exception as e:
                logger.error(f'Failed to ingest Cloudflare zone {zone.get("name", "?")}: {e}')

        self.results['cloudflare']['ingested'] = ingested
        logger.info(f'Cloudflare: {ingested} resources ingested')
        return {'ingested': ingested, 'failed': 0}

    def _log_failed_repo(self, repo_name: str, repo_path: str, error: str):
        failed_log = DATA_DIR / 'failed_repos.json'
        existing = []
        if failed_log.exists():
            try:
                existing = json.loads(failed_log.read_text())
            except Exception:
                pass
        
        existing.append({
            'repo': repo_name,
            'path': repo_path,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        try:
            failed_log.write_text(json.dumps(existing, indent=2))
        except Exception:
            pass

    def run(self) -> Dict[str, Any]:
        logger.info('=' * 70)
        logger.info('ENHANCED COLLECTION PIPELINE - Memory Efficient')
        logger.info('=' * 70)
        
        start_time = datetime.now()
        
        # Process each source
        self.process_github_repos()
        gc.collect()
        
        self.process_vercel()
        gc.collect()
        
        self.process_cloudflare()
        gc.collect()
        
        # Save compact results (no full repo data)
        end_time = datetime.now()
        summary = {
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'duration_seconds': (end_time - start_time).total_seconds(),
            'sources': {
                'github': self.results['github'],
                'vercel': self.results['vercel'],
                'cloudflare': self.results['cloudflare']
            },
            'graph_stats': self.store.get_stats()
        }
        
        # Save only summary, not full data
        summary_path = DATA_DIR / 'pipeline_summary.json'
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        logger.info(f'Summary saved to {summary_path}')
        
        # Print summary
        logger.info('=' * 70)
        logger.info('PIPELINE COMPLETE')
        logger.info('=' * 70)
        logger.info(f'GitHub: {self.results["github"]["ingested"]} ingested, {self.results["github"]["failed"]} failed')
        logger.info(f'Vercel: {self.results["vercel"]["ingested"]} ingested')
        logger.info(f'Cloudflare: {self.results["cloudflare"]["ingested"]} ingested')
        
        stats = self.store.get_stats()
        logger.info(f'Graph stats: {stats}')
        
        # Clean up raw directory one final time (belt and suspenders)
        self._ensure_clean_directories()
        gc.collect()
        logger.info(f'Disk clean: raw dir cleared, graph uses {stats.get("total_projects", 0)} projects')
        
        # Close store
        self.store.close()
        
        return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Graph RAG collection pipeline')
    parser.add_argument('--max-repos', type=int, default=50, help='Maximum GitHub repos')
    parser.add_argument('--clean', action='store_true', help='Clear Neo4j graph before running (fresh start)')
    args = parser.parse_args()
    
    pipeline = EnhancedPipeline(max_repos=args.max_repos, clean_graph=args.clean)
    results = pipeline.run()
    
    return 0 if results else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())