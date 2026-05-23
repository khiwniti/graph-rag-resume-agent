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
from app.extractors.code_structure import CodeStructureExtractor, entity_id as code_entity_id
from app.extractors.cross_file_linker import CrossFileLinker, file_id as cross_file_id
from app.extractors.architecture_detector import ArchitectureDetector
from app.extractors.deployment_analyzer import DeploymentAnalyzer, DeploymentAnalysis, config_id, route_id
from app.extractors.doc_code_linker import DocCodeLinker, narrative_id_from_section

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

    def _ingest_deep_analysis(self, cleaned: CleanedProject, repo_path: str,
                               readme_content: str = "") -> int:
        """Ingest deep code structure, cross-file links, architecture, and doc-code
        links into Neo4j. Returns count of new nodes created."""
        count = 0
        project_id = cleaned.project_id

        # --- 1. Code Structure (Functions, Classes, Modules) ---
        if repo_path and os.path.isdir(repo_path):
            try:
                code_structure = CodeStructureExtractor.extract_directory(
                    repo_path, max_files=200
                )
                if code_structure and code_structure.entities:
                    # Ingest File nodes
                    file_entities = {}
                    for entity in code_structure.entities:
                        fid = code_entity_id("file", entity.file_path, "")
                        if entity.file_path not in file_entities:
                            self.store.upsert_file(
                                file_id=fid,
                                path=entity.file_path,
                                project_id=project_id,
                            )
                            file_entities[entity.file_path] = fid
                            count += 1

                    # Ingest Function nodes
                    for entity in code_structure.entities:
                        if entity.entity_type == "function":
                            fid = file_entities.get(entity.file_path,
                                code_entity_id("file", entity.file_path, ""))
                            fn_id = code_entity_id("function", entity.file_path, entity.name)
                            self.store.upsert_function(
                                function_id=fn_id,
                                name=entity.name,
                                file_id=fid,
                                signature=entity.signature,
                                line_start=entity.line_start,
                                line_end=entity.line_end,
                            )
                            count += 1

                    # Ingest Class nodes
                    for entity in code_structure.entities:
                        if entity.entity_type == "class":
                            fid = file_entities.get(entity.file_path,
                                code_entity_id("file", entity.file_path, ""))
                            cls_id = code_entity_id("class", entity.file_path, entity.name)
                            self.store.upsert_class(
                                class_id=cls_id,
                                name=entity.name,
                                file_id=fid,
                                bases=entity.bases,
                                line_start=entity.line_start,
                                line_end=entity.line_end,
                            )
                            count += 1

                    # Ingest relationships (CALLS, CONTAINS, INHERITS, etc.)
                    for rel in code_structure.relationships:
                        try:
                            if rel.rel_type == "CALLS":
                                self.store.link_function_call(rel.source_id, rel.target_id)
                            elif rel.rel_type == "CONTAINS_METHOD":
                                self.store.link_class_to_method(rel.source_id, rel.target_id)
                        except Exception as e:
                            logger.debug(f"Relationship ingestion failed ({rel.rel_type} {rel.source_id} -> {rel.target_id}): {e}")

                    logger.info(f"Deep code structure: {code_structure.function_count} functions, "
                                f"{code_structure.class_count} classes, "
                                f"{code_structure.file_count} files ingested")
            except Exception as e:
                logger.warning(f"Code structure extraction failed for {project_id}: {e}")

        # --- 2. Cross-File Dependencies ---
        if repo_path and os.path.isdir(repo_path):
            try:
                dep_map = CrossFileLinker.build_dependency_map(repo_path, max_files=200)
                if dep_map:
                    # Pre-upsert File nodes for all files in the dependency graph
                    # so IMPORTS relationships don't silently fail on missing targets
                    all_files = set(dep_map.file_graph.keys())
                    for imported_set in dep_map.file_graph.values():
                        for imported in imported_set:
                            if not imported.startswith("package:"):
                                all_files.add(imported)

                    for file_path in all_files:
                        fid = cross_file_id(file_path, project_id)
                        try:
                            self.store.upsert_file(fid, file_path, project_id)
                        except Exception as e:
                            logger.debug(f"Failed to upsert file {file_path}: {e}")

                    for source_file, imported_files in dep_map.file_graph.items():
                        source_fid = cross_file_id(source_file, project_id)
                        for imported in imported_files:
                            if imported.startswith("package:"):
                                continue  # Skip external packages (handled by skill extractor)
                            imported_fid = cross_file_id(imported, project_id)
                            try:
                                self.store.link_file_import(source_fid, imported_fid)
                                count += 1
                            except Exception as e:
                                logger.debug(f"File import link failed ({source_fid} -> {imported_fid}): {e}")
                    logger.info(f"Cross-file links: {len(dep_map.imports)} imports mapped")
            except Exception as e:
                logger.debug(f"Cross-file linking failed for {project_id}: {e}")

        # --- 3. Architecture Detection ---
        if repo_path and os.path.isdir(repo_path):
            try:
                arch = ArchitectureDetector.analyze(repo_path)
                if arch and arch.patterns:
                    for pattern in arch.patterns:
                        # Store architecture patterns as Skills for RAG queries
                        self.store.upsert_skill(
                            pattern.pattern_type.replace("_", " ").title(),
                            "architecture",
                            pattern.confidence,
                            {"evidence": " | ".join(pattern.evidence[:3]),
                             "details": str(pattern.details)}
                        )
                        self.store.link_skill_to_project(
                            pattern.pattern_type.replace("_", " ").title(),
                            "architecture", project_id,
                            evidence=" | ".join(pattern.evidence[:3])
                        )
                        count += 1

                    # Ingest Route nodes from REST detection
                    for rdef in arch.route_definitions:
                        rid = route_id(project_id, rdef["method"], rdef["path"])
                        self.store.upsert_route(
                            route_id=rid,
                            method=rdef["method"],
                            path=rdef["path"],
                        )
                        self.store.link_project_to_route(project_id, rid)
                        count += 1

                    logger.info(f"Architecture: {len(arch.patterns)} patterns, "
                                f"{len(arch.route_definitions)} routes detected")
            except Exception as e:
                logger.debug(f"Architecture detection failed for {project_id}: {e}")

        # --- 4. Doc-Code Linking (README -> source files) ---
        if readme_content and repo_path and os.path.isdir(repo_path):
            try:
                doc_map = DocCodeLinker.analyze(readme_content, repo_path, project_id)
                if doc_map and doc_map.sections:
                    for i, section in enumerate(doc_map.sections):
                        nid = narrative_id_from_section(project_id, section.heading, i)
                        self.store.upsert_narrative(
                            narrative_id=nid,
                            text=f"## {section.heading}\n\n{section.content[:800]}",
                            source_project_id=project_id,
                        )
                        count += 1

                    for link in doc_map.links:
                        try:
                            idx = next((j for j, s in enumerate(doc_map.sections)
                                        if s.heading == link.section_heading), 0)
                            nid = narrative_id_from_section(project_id, link.section_heading, idx)
                            fid = cross_file_id(link.file_path, project_id)
                            self.store.link_file_to_documentation(fid, nid)
                            count += 1
                        except Exception as e:
                            logger.debug(f"Doc-code link failed ({link.section_heading} -> {link.file_path}): {e}")

                    logger.info(f"Doc-code links: {len(doc_map.sections)} README sections, "
                                f"{len(doc_map.links)} file links")
            except Exception as e:
                logger.debug(f"Doc-code linking failed for {project_id}: {e}")

        return count

    def _upsert_deployment_analysis(self, cleaned: CleanedProject,
                                     deployment: Optional[DeploymentAnalysis]) -> int:
        """Ingest deep deployment analysis (routes, configs, domains) into Neo4j."""
        count = 0
        project_id = cleaned.project_id

        if not deployment:
            return 0

        try:
            # Routes
            for route in deployment.routes:
                rid = route_id(project_id, route.method, route.path or route.source)
                self.store.upsert_route(
                    route_id=rid,
                    method=route.method,
                    path=route.path or route.source,
                )
                self.store.link_project_to_route(project_id, rid)
                count += 1

            # Configs
            for cfg in deployment.configs:
                cid = config_id(project_id, cfg.key)
                self.store.upsert_config(
                    config_id=cid,
                    key=cfg.key,
                    value=cfg.value[:100] if not cfg.is_secret else "***",
                    config_type=cfg.config_type,
                )
                self.store.link_project_to_config(project_id, cid)
                count += 1

            # Domains
            for domain in deployment.domains:
                if domain.name:
                    self.store.upsert_domain(domain.name)
                    self.store.link_project_to_domain(project_id, domain.name)
                    count += 1

            logger.info(f"Deployment analysis: {len(deployment.routes)} routes, "
                        f"{len(deployment.configs)} configs, "
                        f"{len(deployment.domains)} domains")
        except Exception as e:
            logger.debug(f"Deployment ingestion failed for {project_id}: {e}")

        return count

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

                    # Deep analysis: code structure, cross-file links, architecture, doc-code
                    repo_path_str = analysis.get('repo_path', '')
                    readme = repo_data.get('readme', '')
                    deep_count = self._ingest_deep_analysis(
                        cleaned, repo_path_str, readme
                    )

                    # Cleanup cloned repo IMMEDIATELY after successful ingest
                    if repo_path:
                        self._cleanup_repo(Path(repo_path))
                    
                    ingested += 1
                    self.results['github']['repos'].append({
                        'name': repo_name,
                        'status': 'success',
                        'skills_count': len(cleaned.skills),
                        'languages': list(repo_data.get('languages', {}).keys()),
                        'deep_nodes': deep_count,
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

                # Deep deployment analysis
                dep_analysis = DeploymentAnalyzer.analyze_vercel_project(project)
                if dep_analysis:
                    self._upsert_deployment_analysis(cleaned, dep_analysis)
                    # Also look for vercel.json in any linked GitHub repo
                    if dep_analysis.linked_github_repo:
                        cleaned.linked_project_ids.append(dep_analysis.linked_github_repo)

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

        # Workers - clean, normalize, and deep-analyze each one
        for worker in cf_result.get('collected_workers', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_worker(worker)
                self._upsert_cleaned_project(cleaned)
                dep = DeploymentAnalyzer.analyze_cloudflare_worker(worker)
                if dep:
                    self._upsert_deployment_analysis(cleaned, dep)
                ingested += 1
            except Exception as e:
                logger.error(f'Failed to ingest Cloudflare worker {worker.get("name", "?")}: {e}')

        # Pages - clean, normalize, and deep-analyze each one
        for page in cf_result.get('collected_pages', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_page(page)
                self._upsert_cleaned_project(cleaned)
                dep = DeploymentAnalyzer.analyze_cloudflare_page(page)
                if dep:
                    self._upsert_deployment_analysis(cleaned, dep)
                ingested += 1
            except Exception as e:
                logger.error(f'Failed to ingest Cloudflare page {page.get("name", "?")}: {e}')

        # Zones - clean, normalize, and deep-analyze each one
        for zone in cf_result.get('collected_zones', []):
            try:
                cleaned = self.cleaner.clean_cloudflare_zone(zone)
                self._upsert_cleaned_project(cleaned)
                dep = DeploymentAnalyzer.analyze_cloudflare_zone(zone)
                if dep:
                    self._upsert_deployment_analysis(cleaned, dep)
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