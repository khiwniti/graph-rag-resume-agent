#!/usr/bin/env python3
"""
Build Knowledge Graph - Simple working version.
"""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.graph.builder import GraphBuilder

def main():
    print("\n" + "="*70)
    print("Building Knowledge Graph from Collected Data")
    print("="*70)
    
    builder = GraphBuilder()
    builder.add_person_node("person:main")
    
    data_dir = Path("data/raw")
    stats = {"repos": 0, "projects": 0, "workers": 0, "skills": 0}
    
    # Process GitHub
    print("\n📦 Processing GitHub data...")
    github_file = data_dir / "github" / "full_collection.json"
    if github_file.exists():
        with open(github_file) as f:
            github_data = json.load(f)
        
        repos = github_data.get('deep_analyses', [])
        print(f"   Found {len(repos)} repos to process")
        
        for repo in repos[:10]:
            repo_name = repo.get('full_name', repo.get('name', 'unknown'))
            language = repo.get('language', '')
            
            properties = {
                'name': repo_name,
                'url': repo.get('html_url', repo.get('url', '')),
                'description': (repo.get('description') or '')[:200],
                'language': language or '',
                'stars': repo.get('stargazers_count', repo.get('stars', 0)),
                'forks': repo.get('forks_count', repo.get('forks', 0))
            }
            
            builder.add_repository_node(repo_name, properties)
            
            if language:
                builder.add_skill_node(language, "language", {"confidence": 0.8})
                builder.add_edge(f"repo:{repo_name.lower().replace(' ', '_').replace('/', '_')}", f"skill:{language.lower().replace(' ', '_')}", "USES")
                stats["skills"] += 1
            
            stats["repos"] += 1
            print(f" ✅ {repo_name} ({language or 'N/A'})")
    
    # Process Vercel
    print("\n📦 Processing Vercel data...")
    vercel_file = data_dir / "vercel" / "full_collection.json"
    if vercel_file.exists():
        with open(vercel_file) as f:
            vercel_data = json.load(f)
        
        projects = vercel_data.get('deep_analyses', [])
        print(f"   Found {len(projects)} projects to process")
        
        for project in projects[:20]:
            project_name = project.get('name', project.get('project_name', 'unknown'))
            framework = project.get('framework', '')
            
            properties = {
                'name': project_name,
                'url': project.get('url', project.get('project_url', '')),
                'framework': framework or '',
                'description': (project.get('description') or '')[:200]
            }
            
            builder.add_project_node(project_name, "vercel", properties)
            
            if framework:
                builder.add_skill_node(framework, "framework", {"confidence": 0.7})
                builder.add_edge(f"project:{project_name.lower().replace(' ', '_').replace('/', '_')}", f"skill:{framework.lower().replace(' ', '_')}", "USES")
                stats["skills"] += 1
            
            stats["projects"] += 1
            if stats["projects"] <= 5:
                print(f" ✅ {project_name} ({framework or 'N/A'})")
    
    # Process Cloudflare
    print("\n📦 Processing Cloudflare data...")
    cf_file = data_dir / "cloudflare" / "full_collection.json"
    if cf_file.exists():
        with open(cf_file) as f:
            cf_data = json.load(f)
        
        workers = cf_data.get('workers', [])
        
        for worker in workers[:10]:
            worker_name = worker.get('name', 'unknown')
            builder.add_project_node(f"cf-{worker_name}", "cloudflare", {'type': 'cloudflare-worker'})
            stats["workers"] += 1
        
        if workers:
            builder.add_skill_node("Cloudflare Workers", "platform", {"confidence": 0.7})
            print(f"  ✅ {len(workers[:10])} Workers")
    
    # Save graph
    print("\n💾 Saving knowledge graph...")
    graph_path = Path("data/graph/knowledge_graph.json")
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    builder.save_json(str(graph_path))
    
    graph_stats = builder.get_stats()
    
    print("\n" + "="*70)
    print("✅ Knowledge Graph Built Successfully!")
    print("="*70)
    print(f"GitHub Repositories: {stats['repos']}")
    print(f"Vercel Projects: {stats['projects']}")
    print(f"Cloudflare Workers: {stats['workers']}")
    print(f"Skills Added: {stats['skills']}")
    print(f"\nGraph: {graph_stats.get('nodes', 0)} nodes, {graph_stats.get('edges', 0)} edges")
    print(f"\nSaved to: {graph_path}")
    print("\n🚀 Ready to query your skills!")

if __name__ == "__main__":
    main()
