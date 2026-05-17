#!/usr/bin/env python3
"""
Build Knowledge Graph - Processes all collected data into the knowledge graph.

This script:
1. Loads raw collected data from GitHub, Vercel, Cloudflare, Conversations
2. Normalizes data into standard formats
3. Extracts skills and dependencies
4. Builds the knowledge graph
5. Creates vector embeddings
6. Saves everything for the RAG agent
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.graph.builder import GraphBuilder
from app.graph.serializer import GraphSerializer
from app.normalizers.github_normalizer import GitHubNormalizer
from app.normalizers.vercel_normalizer import VercelNormalizer
from app.normalizers.cloudflare_normalizer import CloudflareNormalizer
from app.normalizers.conversation_normalizer import ConversationNormalizer
from app.extractors.dependency_parser import DependencyParser
from app.extractors.source_analyzer import SourceAnalyzer
from app.extractors.skill_extractor import SkillExtractor
from app.extractors.evidence_ranker import EvidenceRanker
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore

from app.config import DATA_DIR, RAW_DIR

def load_json_file(path: Path) -> Any:
    """Load JSON file if exists."""
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return None

def process_github_data(builder: GraphBuilder) -> Dict[str, Any]:
    """Process GitHub collected data."""
    print("\n" + "="*60)
    print("Processing GitHub Data")
    print("="*60)
    
    github_dir = RAW_DIR / "github"
    if not github_dir.exists():
        print("⚠️  No GitHub data found")
        return {"repos": 0, "files": 0, "skills": 0}
    
    stats = {"repos": 0, "files": 0, "skills": 0}
    normalizer = GitHubNormalizer()
    dep_parser = DependencyParser()
    source_analyzer = SourceAnalyzer()
    skill_extractor = SkillExtractor()
    ranker = EvidenceRanker()
    
    # Load repository data
    repos_file = github_dir / "repositories.json"
    repos_data = load_json_file(repos_file)
    
    if repos_data and 'repositories' in repos_data:
        repos = repos_data['repositories'][:10]  # Limit to 10 for now
        print(f"Found {len(repos)} repositories to process")
        
        for repo in repos:
            repo_name = repo.get('full_name', 'unknown')
            print(f"\n📦 Processing: {repo_name}")
            
            # Normalize repository
            try:
                normalized = normalizer.normalize_repo(repo)
                
                # Add repository node to graph
                builder.add_repository_node(
                    repo_id=repo_name,
                    name=normalized.repo_name,
                    full_name=normalized.full_name,
                    url=normalized.url,
                    description=normalized.description,
                    stars=normalized.stars,
                    forks=normalized.forks,
                    language=normalized.metadata.get('language', ''),
                    topics=normalized.topics
                )
                stats["repos"] += 1
                
                # Process files if available
                if hasattr(normalized, 'files') and normalized.files:
                    for file_data in normalized.files[:5]:  # Limit files per repo
                        stats["files"] += 1
                        
                        # Analyze source code
                        if 'content' in file_data:
                            analysis = source_analyzer.analyze(
                                file_data['content'],
                                file_data.get('filename', '')
                            )
                            
                            # Extract skills
                            skills = skill_extractor.extract_from_text(file_data['content'])
                            for skill in skills:
                                builder.add_skill_node(
                                    skill_name=skill['name'],
                                    confidence=skill['confidence'],
                                    category=skill['category']
                                )
                                builder.add_edge(
                                    repo_name,
                                    skill['name'],
                                    "USES",
                                    {"evidence": file_data.get('filename', ''), "confidence": skill['confidence']}
                                )
                                stats["skills"] += 1
                            
                            # Parse dependencies
                            deps = dep_parser.parse(file_data['content'], file_data.get('filename', ''))
                            if deps:
                                for dep in deps:
                                    builder.add_skill_node(
                                        skill_name=dep.get('name', ''),
                                        confidence=0.7,
                                        category="dependency"
                                    )
                
                print(f"  ✅ Processed: {repo_name}")
            except Exception as e:
                print(f"  ⚠️  Error processing {repo_name}: {e}")
    
    return stats

def process_vercel_data(builder: GraphBuilder) -> Dict[str, Any]:
    """Process Vercel collected data."""
    print("\n" + "="*60)
    print("Processing Vercel Data")
    print("="*60)
    
    vercel_dir = RAW_DIR / "vercel"
    if not vercel_dir.exists():
        print("⚠️  No Vercel data found")
        return {"projects": 0}
    
    stats = {"projects": 0}
    normalizer = VercelNormalizer()
    
    projects_file = vercel_dir / "projects.json"
    projects_data = load_json_file(projects_file)
    
    if projects_data and 'projects' in projects_data:
        projects = projects_data['projects'][:20]  # Limit to 20
        print(f"Found {len(projects)} Vercel projects to process")
        
        for project in projects:
            project_name = project.get('name', 'unknown')
            print(f"\n📦 Processing Vercel project: {project_name}")
            
            try:
                normalized = normalizer.normalize_project(project)
                
                builder.add_project_node(
                    project_id=project_name,
                    name=normalized.name,
                    url=normalized.url,
                    framework=normalized.metadata.get('framework', ''),
                    repo=normalized.metadata.get('repo', '')
                )
                
                # Link to repository if exists
                if normalized.metadata.get('repo'):
                    builder.add_edge(
                        normalized.metadata['repo'],
                        project_name,
                        "DEPLOYED_ON",
                        {"platform": "vercel"}
                    )
                
                stats["projects"] += 1
                print(f"  ✅ Processed: {project_name}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
    
    return stats

def process_cloudflare_data(builder: GraphBuilder) -> Dict[str, Any]:
    """Process Cloudflare collected data."""
    print("\n" + "="*60)
    print("Processing Cloudflare Data")
    print("="*60)
    
    cf_dir = RAW_DIR / "cloudflare"
    if not cf_dir.exists():
        print("⚠️  No Cloudflare data found")
        return {"workers": 0, "pages": 0}
    
    stats = {"workers": 0, "pages": 0}
    normalizer = CloudflareNormalizer()
    
    # Process Workers
    workers_file = cf_dir / "workers.json"
    workers_data = load_json_file(workers_file)
    
    if workers_data and 'workers' in workers_data:
        workers = workers_data['workers'][:10]  # Limit
        print(f"Found {len(workers)} Cloudflare Workers")
        
        for worker in workers:
            worker_name = worker.get('name', 'unknown')
            try:
                normalized = normalizer.normalize_worker(worker)
                builder.add_project_node(
                    project_id=f"cf-worker-{worker_name}",
                    name=normalized.name,
                    url="",
                    framework="cloudflare-worker",
                    metadata=normalized.metadata
                )
                stats["workers"] += 1
            except Exception as e:
                pass
    
    # Process Pages
    pages_file = cf_dir / "pages.json"
    pages_data = load_json_file(pages_file)
    
    if pages_data and 'pages' in pages_data:
        pages = pages_data['pages'][:10]
        for page in pages:
            page_name = page.get('name', 'unknown')
            try:
                normalized = normalizer.normalize_pages_project(page)
                builder.add_project_node(
                    project_id=f"cf-pages-{page_name}",
                    name=normalized.name,
                    url=normalized.url,
                    framework="cloudflare-pages",
                    metadata=normalized.metadata
                )
                stats["pages"] += 1
            except Exception as e:
                pass
    
    print(f"  ✅ Processed {stats['workers']} Workers and {stats['pages']} Pages")
    return stats

def process_conversations(builder: GraphBuilder) -> Dict[str, Any]:
    """Process conversation artifacts."""
    print("\n" + "="*60)
    print("Processing Conversation Artifacts")
    print("="*60)
    
    conv_dir = RAW_DIR / "conversation"
    if not conv_dir.exists():
        print("⚠️  No conversation data found")
        return {"artifacts": 0, "mentions": 0}
    
    stats = {"artifacts": 0, "mentions": 0}
    normalizer = ConversationNormalizer()
    skill_extractor = SkillExtractor()
    
    # Load conversation data
    conv_file = conv_dir / "artifacts.json"
    conv_data = load_json_file(conv_file)
    
    if conv_data:
        artifacts = conv_data.get('artifacts', [])
        print(f"Found {len(artifacts)} conversation artifacts")
        
        for artifact in artifacts[:20]:  # Limit
            stats["artifacts"] += 1
            
            # Extract technology mentions
            if 'text' in artifact:
                skills = skill_extractor.extract_from_text(artifact['text'])
                for skill in skills:
                    builder.add_skill_node(
                        skill_name=skill['name'],
                        confidence=skill['confidence'] * 0.5,  # Lower confidence for conversation
                        category=skill['category']
                    )
                    stats["mentions"] += 1
    
    print(f"  ✅ Processed {stats['artifacts']} artifacts, {stats['mentions']} tech mentions")
    return stats

def build_embeddings(builder: GraphBuilder) -> Dict[str, Any]:
    """Build vector embeddings from the graph."""
    print("\n" + "="*60)
    print("Building Vector Embeddings")
    print("="*60)
    
    try:
        chunker = TextChunker()
        embedder = Embedder()
        vector_store = VectorStore()
        
        # Get all text from graph nodes
        documents = []
        for node_id, node_data in builder.graph.nodes(data=True):
            if 'description' in node_data:
                documents.append({
                    'id': node_id,
                    'text': f"{node_id}: {node_data.get('description', '')}",
                    'type': 'node'
                })
        
        print(f"Creating embeddings for {len(documents)} documents...")
        
        if documents:
            # Chunk documents
            all_chunks = []
            for doc in documents:
                chunks = chunker.chunk(doc['text'])
                for chunk in chunks:
                    all_chunks.append({
                        'id': f"{doc['id']}_{chunks.index(chunk)}",
                        'text': chunk,
                        'source': doc['id']
                    })
            
            # Create embeddings
            if all_chunks:
                texts = [c['text'] for c in all_chunks]
                embeddings = embedder.embed_batch(texts)
                
                # Add to vector store
                vector_store.add_batch(
                    texts=texts,
                    embeddings=embeddings,
                    metadatas=[{'source': c['source']} for c in all_chunks]
                )
                
                print(f"  ✅ Created {len(all_chunks)} embeddings")
                return {"chunks": len(all_chunks)}
    
    except Exception as e:
        print(f"  ⚠️  Embedding error: {e}")
    
    return {"chunks": 0}

def main():
    """Main pipeline to build knowledge graph from collected data."""
    print("\n" + "="*70)
    print("Building Knowledge Graph from Collected Data")
    print("="*70)
    
    # Initialize graph builder
    builder = GraphBuilder()
    
    # Add person node
    builder.add_person_node("person:main")
    
    total_stats = {
        "github": {},
        "vercel": {},
        "cloudflare": {},
        "conversation": {},
        "embeddings": {}
    }
    
    # Process each data source
    total_stats["github"] = process_github_data(builder)
    total_stats["vercel"] = process_vercel_data(builder)
    total_stats["cloudflare"] = process_cloudflare_data(builder)
    total_stats["conversation"] = process_conversations(builder)
    
    # Build embeddings
    total_stats["embeddings"] = build_embeddings(builder)
    
    # Save graph
    print("\n" + "="*60)
    print("Saving Knowledge Graph")
    print("="*60)
    
    graph_path = DATA_DIR / "graph" / "knowledge_graph.json"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    
    builder.save_json(str(graph_path))
    print(f"✅ Graph saved to: {graph_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("Pipeline Complete - Summary")
    print("="*70)
    print(f"GitHub: {total_stats['github'].get('repos', 0)} repos, {total_stats['github'].get('files', 0)} files, {total_stats['github'].get('skills', 0)} skills")
    print(f"Vercel: {total_stats['vercel'].get('projects', 0)} projects")
    print(f"Cloudflare: {total_stats['cloudflare'].get('workers', 0)} workers, {total_stats['cloudflare'].get('pages', 0)} pages")
    print(f"Conversations: {total_stats['conversation'].get('artifacts', 0)} artifacts, {total_stats['conversation'].get('mentions', 0)} mentions")
    print(f"Embeddings: {total_stats['embeddings'].get('chunks', 0)} chunks")
    
    stats = builder.get_stats()
    print(f"\nGraph Stats: {stats['nodes']} nodes, {stats['edges']} edges")
    
    print("\n✅ Knowledge graph built successfully!")
    print("\nNext: Start the API server and query your skills!")

if __name__ == "__main__":
    main()
