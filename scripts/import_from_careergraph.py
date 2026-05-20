#!/usr/bin/env python3
"""
Import Data from CareerGraph Wiki MCP UI

This script imports exported wiki data from careergraph-wiki-mcp-ui
into the graph-rag-resume-agent's raw data format.

Usage:
    python scripts/import_from_careergraph.py --input exported_wiki_data.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def load_export_data(input_path: str) -> Dict[str, Any]:
    """Load exported data from careergraph-wiki-mcp-ui."""
    print(f"Loading export data from {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def transform_to_github_format(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform wiki pages to GitHub collector format."""
    print("\n" + "="*60)
    print("Transforming to GitHub Format")
    print("="*60)

    wiki_pages = export_data.get('wiki_pages', {})
    pages = wiki_pages.get('pages', [])

    # Group pages by type
    repos = []
    for page in pages:
        metadata = page.get('metadata', {})
        page_type = metadata.get('type', '')

        # Check if it's a repo page (type contains 'repo' or metadata suggests it)
        if 'repo' in page_type.lower() or 'repository' in page_type.lower():
            repos.append({
                'full_name': metadata.get('full_name', page.get('slug')),
                'name': metadata.get('name', page.get('title')),
                'description': metadata.get('description', ''),
                'html_url': metadata.get('url', ''),
                'language': metadata.get('language', ''),
                'stargazers_count': metadata.get('stars', 0),
                'forks_count': metadata.get('forks', 0),
                'topics': metadata.get('topics', []),
                'updated_at': metadata.get('updated_at', datetime.utcnow().isoformat()),
                'files': [],  # Would need to fetch from API if needed
            })

    print(f"  ✓ Transformed {len(repos)} repositories")

    return {
        'repositories': repos,
        'original_repos_count': len(repos),
    }


def transform_to_vercel_format(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform wiki pages to Vercel collector format."""
    print("\n" + "="*60)
    print("Transforming to Vercel Format")
    print("="*60)

    wiki_pages = export_data.get('wiki_pages', {})
    pages = wiki_pages.get('pages', [])

    # Group pages by type
    projects = []
    for page in pages:
        metadata = page.get('metadata', {})
        page_type = metadata.get('type', '')

        # Check if it's a Vercel project
        if 'vercel' in page_type.lower() or 'project' in page_type.lower():
            projects.append({
                'name': metadata.get('name', page.get('title')),
                'id': metadata.get('id', page.get('slug')),
                'url': metadata.get('url', ''),
                'framework': metadata.get('framework', 'nextjs'),
                'gitRepository': metadata.get('repo', ''),
                'updatedAt': metadata.get('updated_at', datetime.utcnow().isoformat()),
            })

    print(f"  ✓ Transformed {len(projects)} Vercel projects")

    return {
        'projects': projects,
        'total_projects': len(projects),
    }


def transform_to_cloudflare_format(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform wiki pages to Cloudflare collector format."""
    print("\n" + "="*60)
    print("Transforming to Cloudflare Format")
    print("="*60)

    wiki_pages = export_data.get('wiki_pages', {})
    pages = wiki_pages.get('pages', [])

    workers = []
    zones = []

    for page in pages:
        metadata = page.get('metadata', {})
        page_type = metadata.get('type', '')

        if 'cloudflare_worker' in page_type.lower() or 'worker' in page_type.lower():
            workers.append({
                'name': metadata.get('name', page.get('title')),
                'id': metadata.get('id', page.get('slug')),
                'created_on': metadata.get('created_at', datetime.utcnow().isoformat()),
                'updated_on': metadata.get('updated_at', datetime.utcnow().isoformat()),
            })
        elif 'cloudflare_zone' in page_type.lower() or 'zone' in page_type.lower():
            zones.append({
                'name': metadata.get('name', page.get('title')),
                'id': metadata.get('id', page.get('slug')),
                'created_on': metadata.get('created_at', datetime.utcnow().isoformat()),
            })

    print(f"  ✓ Transformed {len(workers)} Workers and {len(zones)} Zones")

    return {
        'workers': workers,
        'zones': zones,
        'workers_count': len(workers),
        'zones_count': len(zones),
    }


def transform_to_conversation_format(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform wiki pages to conversation artifacts format."""
    print("\n" + "="*60)
    print("Transforming to Conversation Format")
    print("="*60)

    wiki_pages = export_data.get('wiki_pages', {})
    pages = wiki_pages.get('pages', [])

    artifacts = []
    for page in pages:
        # All pages can be considered as conversation artifacts
        artifacts.append({
            'id': page.get('slug', ''),
            'title': page.get('title', ''),
            'text': page.get('content', ''),
            'type': page.get('type', 'page'),
            'tags': page.get('tags', []),
            'metadata': page.get('metadata', {}),
        })

    print(f"  ✓ Transformed {len(artifacts)} conversation artifacts")

    return {
        'artifacts': artifacts,
        'artifact_count': len(artifacts),
    }


def save_raw_data(data: Dict[str, Any], output_dir: str):
    """Save transformed data to raw directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for source, content in data.items():
        if source == 'metadata':
            continue

        file_path = output_path / f"{source}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, default=str)

        print(f"  ✓ Saved {file_path}")


def main():
    """Main import function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import data from CareerGraph Wiki")
    parser.add_argument(
        "--input",
        required=True,
        help="Input file path (exported JSON from careergraph)"
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Output directory for raw data"
    )
    parser.add_argument(
        "--filter-types",
        nargs='+',
        help="Filter by page types (e.g., repo, vercel_project, cloudflare_worker)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold for skills"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("Importing Data from CareerGraph Wiki MCP UI")
    print("="*70)

    # Load export data
    export_data = load_export_data(args.input)

    # Apply filters if specified
    if args.filter_types:
        print(f"\nFiltering by types: {args.filter_types}")
        wiki_pages = export_data.get('wiki_pages', {})
        pages = wiki_pages.get('pages', [])
        filtered_pages = [
            page for page in pages
            if page.get('metadata', {}).get('type', '') in args.filter_types
        ]
        export_data['wiki_pages']['pages'] = filtered_pages
        print(f"  ✓ Filtered to {len(filtered_pages)} pages")

    # Transform to various formats
    github_data = transform_to_github_format(export_data)
    vercel_data = transform_to_vercel_format(export_data)
    cloudflare_data = transform_to_cloudflare_format(export_data)
    conversation_data = transform_to_conversation_format(export_data)

    # Save raw data
    print("\n" + "="*60)
    print("Saving Raw Data")
    print("="*60)

    raw_data = {
        'github': github_data,
        'vercel': vercel_data,
        'cloudflare': cloudflare_data,
        'conversation': conversation_data,
        'metadata': {
            'imported_at': datetime.utcnow().isoformat(),
            'source': 'careergraph-wiki-mcp-ui',
            'input_file': args.input,
        }
    }

    save_raw_data(raw_data, args.output_dir)

    # Print summary
    print("\n" + "="*70)
    print("Import Complete - Summary")
    print("="*70)
    print(f"GitHub: {github_data.get('original_repos_count', 0)} repositories")
    print(f"Vercel: {vercel_data.get('total_projects', 0)} projects")
    print(f"Cloudflare: {cloudflare_data.get('workers_count', 0)} workers, {cloudflare_data.get('zones_count', 0)} zones")
    print(f"Conversations: {conversation_data.get('artifact_count', 0)} artifacts")

    print("\n✅ Import complete! You can now run the graph builder.")
    print("   Next: python scripts/build_graph.py")


if __name__ == "__main__":
    main()
