#!/usr/bin/env python3
"""
Build Knowledge Graph from CareerGraph Import

This script builds a knowledge graph from data imported from CareerGraph Wiki MCP UI.
It's an alternative to build_graph.py that works with the CareerGraph import format.
"""

import json
from pathlib import Path
from typing import Dict, Any
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.graph.builder import GraphBuilder
from app.config import DATA_DIR, RAW_DIR


def load_json_file(path: Path) -> Any:
    """Load JSON file if exists."""
    if path.exists() and path.is_file():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def process_github_data(builder: GraphBuilder, raw_dir: Path) -> Dict[str, Any]:
    """Process GitHub data from CareerGraph import."""
    print("\n" + "="*60)
    print("Processing GitHub Data (CareerGraph Format)")
    print("="*60)

    github_file = raw_dir / "github.json"
    data = load_json_file(github_file)

    if not data or 'repositories' not in data:
        print("⚠️ No GitHub data found")
        return {"repos": 0, "skills": 0}

    repos = data.get('repositories', [])
    print(f"Found {len(repos)} repositories to process")

    stats = {"repos": 0, "skills": 0}
    person_id = "person:main"

    for repo in repos:  # Process all repositories
        repo_name = repo.get('full_name', 'unknown')
        print(f"\n📦 Processing: {repo_name}")

        try:
            # Build repo properties
            repo_props = {
                'name': repo.get('name', repo_name),
                'full_name': repo_name,
                'url': repo.get('html_url', ''),
                'description': repo.get('description', ''),
                'stars': repo.get('stargazers_count', 0),
                'forks': repo.get('forks_count', 0),
                'language': repo.get('language', ''),
                'topics': repo.get('topics', []),
                'updated_at': repo.get('updated_at', datetime.utcnow().isoformat()),
            }

            # Add repository node
            repo_node = builder.add_repository_node(repo_name=repo_name, properties=repo_props)
            stats["repos"] += 1

            # Create OWNS edge: person -> repository
            builder.add_edge(
                person_id,
                repo_node.id,
                "OWNS",
                {"since": repo.get('updated_at', '')}
            )

            # Add skill from language and create USES edge
            language = repo.get('language', '')
            if language:
                lang_skill = builder.add_skill_node(
                    skill_name=language,
                    category='language',
                    properties={'usage_count': 1}
                )
                builder.add_edge(
                    repo_node.id,
                    lang_skill.id,
                    "USES",
                    {"evidence_type": "language_usage"}
                )
                stats["skills"] += 1

            # Add skills from topics with USES edges
            for topic in repo.get('topics', []):
                topic_lower = topic.lower()
                if topic_lower in ['python', 'javascript', 'typescript', 'react', 'node', 'api', 'docker', 'kubernetes', 'go', 'rust', 'java']:
                    topic_skill = builder.add_skill_node(
                        skill_name=topic_lower,
                        category='technology',
                        properties={'source': 'topic'}
                    )
                    builder.add_edge(
                        repo_node.id,
                        topic_skill.id,
                        "USES",
                        {"evidence_type": "topic"}
                    )

            # Extract skills from description and create USES edges
            description = repo.get('description', '')
            if description:
                desc_lower = description.lower()
                for skill in ['python', 'javascript', 'react', 'node', 'api', 'docker', 'kubernetes', 'typescript', 'go', 'rust', 'java', 'c++', 'c#']:
                    if skill in desc_lower:
                        desc_skill = builder.add_skill_node(
                            skill_name=skill,
                            category='technology',
                            properties={'source': 'description'}
                        )
                        builder.add_edge(
                            repo_node.id,
                            desc_skill.id,
                            "USES",
                            {"evidence_type": "description"}
                        )

            print(f" ✅ Processed: {repo_name}")
        except Exception as e:
            print(f" ⚠️ Error: {e}")

    return stats


def process_vercel_data(builder: GraphBuilder, raw_dir: Path) -> Dict[str, Any]:
    """Process Vercel data from CareerGraph import."""
    print("\n" + "="*60)
    print("Processing Vercel Data (CareerGraph Format)")
    print("="*60)

    vercel_file = raw_dir / "vercel.json"
    data = load_json_file(vercel_file)

    if not data or 'projects' not in data:
        print("⚠️ No Vercel data found")
        return {"projects": 0}

    projects = data.get('projects', [])
    print(f"Found {len(projects)} projects to process")

    stats = {"projects": 0}

    for project in projects:  # Process all projects
        project_name = project.get('name', 'unknown')
        print(f"\n📦 Processing: {project_name}")

        try:
            builder.add_project_node(
                project_name=project_name,
                platform='vercel',
                properties={
                    'name': project_name,
                    'url': project.get('url', ''),
                    'framework': project.get('framework', 'nextjs'),
                    'repo': project.get('gitRepository', ''),
                }
            )
            stats["projects"] += 1
            print(f" ✅ Processed: {project_name}")
        except Exception as e:
            print(f" ⚠️ Error: {e}")

    return stats


def process_cloudflare_data(builder: GraphBuilder, raw_dir: Path) -> Dict[str, Any]:
    """Process Cloudflare data from CareerGraph import."""
    print("\n" + "="*60)
    print("Processing Cloudflare Data (CareerGraph Format)")
    print("="*60)

    cloudflare_file = raw_dir / "cloudflare.json"
    data = load_json_file(cloudflare_file)

    if not data:
        print("⚠️ No Cloudflare data found")
        return {"workers": 0, "zones": 0}

    stats = {"workers": 0, "zones": 0}

    # Process workers
    workers = data.get('workers', [])
    print(f"Found {len(workers)} Workers to process")

    for worker in workers[:20]:
        worker_name = worker.get('name', 'unknown')
        try:
            builder.add_project_node(
                project_name=worker_name,
                platform='cloudflare-worker',
                properties={'type': 'worker'}
            )
            stats["workers"] += 1
        except Exception as e:
            pass

    # Process zones
    zones = data.get('zones', [])
    print(f"Found {len(zones)} Zones to process")

    for zone in zones[:20]:
        zone_name = zone.get('name', 'unknown')
        try:
            builder.add_project_node(
                project_name=zone_name,
                platform='cloudflare-zone',
                properties={'type': 'zone'}
            )
            stats["zones"] += 1
        except Exception as e:
            pass

    print(f" ✅ Processed {stats['workers']} Workers and {stats['zones']} Zones")
    return stats


def process_conversations(builder: GraphBuilder, raw_dir: Path) -> Dict[str, Any]:
    """Process conversation artifacts from CareerGraph import."""
    print("\n" + "="*60)
    print("Processing Conversation Artifacts (CareerGraph Format)")
    print("="*60)

    conv_file = raw_dir / "conversation.json"
    data = load_json_file(conv_file)

    if not data or 'artifacts' not in data:
        print("⚠️ No conversation data found")
        return {"artifacts": 0, "skills": 0}

    artifacts = data.get('artifacts', [])
    print(f"Found {len(artifacts)} artifacts to process")

    stats = {"artifacts": 0, "skills": 0}
    skill_counts = {}

    for artifact in artifacts:
        try:
            stats["artifacts"] += 1

            # Extract skills from metadata
            metadata = artifact.get('metadata', {})
            detected_skills = metadata.get('detected_skills', [])
            skill_categories = metadata.get('skill_categories', [])

            for skill in detected_skills:
                skill_lower = skill.lower()
                if skill_lower not in skill_counts:
                    skill_counts[skill_lower] = 0
                skill_counts[skill_lower] += 1

            for cat in skill_categories:
                if cat not in skill_counts:
                    skill_counts[cat] = 0
                skill_counts[cat] += 1

        except Exception as e:
            pass

    # Add top skills to graph
    for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:50]:
        builder.add_skill_node(
            skill_name=skill,
            category='technology',
            properties={
                'mention_count': count,
            }
        )
        stats["skills"] += 1

    print(f" ✅ Processed {stats['artifacts']} artifacts, extracted {stats['skills']} skills")
    return stats


def main():
    """Main function to build graph from CareerGraph data."""
    print("\n" + "="*70)
    print("Building Knowledge Graph from CareerGraph Import")
    print("="*70)

    # Initialize graph builder
    builder = GraphBuilder()

    # Add person node
    builder.add_person_node("person:main")

    raw_dir = RAW_DIR

    # Process each data source
    github_stats = process_github_data(builder, raw_dir)
    vercel_stats = process_vercel_data(builder, raw_dir)
    cloudflare_stats = process_cloudflare_data(builder, raw_dir)
    conv_stats = process_conversations(builder, raw_dir)

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
    print(f"GitHub: {github_stats.get('repos', 0)} repos, {github_stats.get('skills', 0)} skills")
    print(f"Vercel: {vercel_stats.get('projects', 0)} projects")
    print(f"Cloudflare: {cloudflare_stats.get('workers', 0)} workers, {cloudflare_stats.get('zones', 0)} zones")
    print(f"Conversations: {conv_stats.get('artifacts', 0)} artifacts, {conv_stats.get('skills', 0)} skills")

    stats = builder.get_stats()
    print(f"\nGraph Stats: {stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges")

    print("\n✅ Knowledge graph built successfully!")
    print("\nNext: Start the API server and query your skills!")


if __name__ == "__main__":
    main()
