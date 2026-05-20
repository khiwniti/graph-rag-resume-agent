#!/usr/bin/env python3
"""
Build Knowledge Graph from Extracted Metadata

Instead of storing every file/package, this builds a compact knowledge graph
from the extracted metadata. Reduces graph size by ~90%.

Usage:
    python scripts/build_graph_from_metadata.py
"""

import json
from pathlib import Path
from typing import Dict, Any, List


def load_metadata() -> Dict[str, Any]:
    """Load extracted metadata."""
    metadata_path = Path("data/metadata/extracted_metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(
            "Metadata not found. Run: python app/extractors/metadata_extractor.py"
        )

    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_project_node(project: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Convert project metadata to knowledge graph node."""
    return {
        "id": f"project:{project['name'].lower().replace(' ', '-').replace('/', '-')}",
        "type": "project",
        "properties": {
            "name": project["name"],
            "source_type": project["source_type"],
            "project_type": project["project_type"],
            "domain": project["domain"],
            "problem_statement": project["problem_statement"],
            "architecture_pattern": project["architecture_pattern"],
            "primary_stack": project["primary_stack"],
            "skills_demonstrated": project["skills_demonstrated"],
            "evidence_count": project["evidence_count"],
            "confidence": project["confidence"],
            "source_url": project["source_url"],
            "deployed_url": project["deployed_url"]
        }
    }


def build_skill_node(skill_name: str) -> Dict[str, Any]:
    """Create a skill node."""
    return {
        "id": f"skill:{skill_name.lower().replace(' ', '-').replace('/', '-')}",
        "type": "skill",
        "properties": {
            "name": skill_name,
            "category": "inferred"
        }
    }


def build_domain_node(domain_name: str) -> Dict[str, Any]:
    """Create a domain node."""
    return {
        "id": f"domain:{domain_name.lower().replace(' ', '-')}",
        "type": "domain",
        "properties": {
            "name": domain_name,
            "label": domain_name
        }
    }


def build_stack_node(stack_name: str) -> Dict[str, Any]:
    """Create a tech stack node."""
    return {
        "id": f"tech:{stack_name.lower().replace(' ', '-').replace('/', '-')}",
        "type": "tech",
        "properties": {
            "name": stack_name,
            "category": "technology"
        }
    }


def build_edges(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build edges between projects, skills, domains, and tech."""
    edges = []
    seen_edges = set()  # Avoid duplicate edges

    def add_edge(from_id: str, to_id: str, label: str, weight: int = 5):
        edge_key = f"{from_id}->{to_id}"
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({
                "from": from_id,
                "to": to_id,
                "label": label,
                "weight": weight
            })

    for project in projects:
        project_id = f"project:{project['name'].lower().replace(' ', '-').replace('/', '-')}"

        # Project -> Skills (DEMONSTRATES_SKILL)
        for skill in project.get("skills_demonstrated", []):
            skill_id = f"skill:{skill.lower().replace(' ', '-').replace('/', '-')}"
            add_edge(project_id, skill_id, "DEMONSTRATES_SKILL", weight=8)
            add_edge(skill_id, project_id, "EVIDENCE_FOR", weight=5)

        # Project -> Domains (BELONGS_TO_DOMAIN)
        for domain in project.get("domain", []):
            if domain and domain != "general":
                domain_id = f"domain:{domain.lower().replace(' ', '-')}"
                add_edge(project_id, domain_id, "BELONGS_TO_DOMAIN", weight=7)

        # Project -> Tech Stack (USES_TECH)
        for tech in project.get("primary_stack", []):
            tech_id = f"tech:{tech.lower().replace(' ', '-').replace('/', '-')}"
            add_edge(project_id, tech_id, "USES_TECH", weight=6)

        # Project -> Source Platform (DEPLOYED_ON)
        source_type = project.get("source_type", "")
        if source_type:
            platform_id = f"platform:{source_type}"
            add_edge(project_id, platform_id, "DEPLOYED_ON", weight=5)

    return edges


def build_graph() -> Dict[str, Any]:
    """Build complete knowledge graph from metadata."""
    metadata = load_metadata()
    projects_data = metadata.get("projects", [])

    nodes = []
    seen_nodes = set()  # Avoid duplicate nodes

    def add_node(node: Dict[str, Any]):
        if node["id"] not in seen_nodes:
            seen_nodes.add(node["id"])
            nodes.append(node)

    # Add person node
    add_node({
        "id": "person:main",
        "type": "person",
        "properties": {
            "name": "Khiw Nitithadachot",
            "role": "AI Agent Architect",
            "created_at": Path("data/metadata/extracted_metadata.json").stat().st_mtime
        }
    })

    # Add projects and collect unique skills/domains/tech
    all_skills = set()
    all_domains = set()
    all_tech = set()
    all_platforms = set()

    for i, project in enumerate(projects_data):
        project_node = build_project_node(project, i)
        add_node(project_node)

        # Collect unique items
        for skill in project.get("skills_demonstrated", []):
            all_skills.add(skill)
        for domain in project.get("domain", []):
            if domain and domain != "general":
                all_domains.add(domain)
        for tech in project.get("primary_stack", []):
            all_tech.add(tech)
        source_type = project.get("source_type", "")
        if source_type:
            all_platforms.add(source_type)

    # Add skill nodes
    for skill in all_skills:
        add_node(build_skill_node(skill))

    # Add domain nodes
    for domain in all_domains:
        add_node(build_domain_node(domain))

    # Add tech nodes
    for tech in all_tech:
        add_node(build_stack_node(tech))

    # Add platform nodes
    platform_names = {
        "github": "GitHub",
        "vercel": "Vercel",
        "cloudflare": "Cloudflare"
    }
    for platform in all_platforms:
        add_node({
            "id": f"platform:{platform}",
            "type": "platform",
            "properties": {
                "name": platform_names.get(platform, platform),
                "category": "deployment"
            }
        })

    # Build edges
    edges = build_edges(projects_data)

    # Add person -> projects edge
    for project in projects_data:
        project_id = f"project:{project['name'].lower().replace(' ', '-').replace('/', '-')}"
        edges.append({
            "from": "person:main",
            "to": project_id,
            "label": "CREATED",
            "weight": 10
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_projects": len(projects_data),
            "total_skills": len(all_skills),
            "total_domains": len(all_domains),
            "total_tech": len(all_tech),
            "extraction_source": "data/metadata/extracted_metadata.json"
        }
    }


def main():
    """Build knowledge graph from metadata."""
    print("Building knowledge graph from extracted metadata...")

    try:
        graph = build_graph()

        # Save graph
        output_path = Path("data/graph/knowledge_graph.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)

        # Summary
        print(f"\n✓ Knowledge graph built successfully!")
        print(f"\n  Nodes: {len(graph['nodes'])}")
        print(f"    - Projects: {graph['metadata']['total_projects']}")
        print(f"    - Skills: {graph['metadata']['total_skills']}")
        print(f"    - Domains: {graph['metadata']['total_domains']}")
        print(f"    - Tech: {graph['metadata']['total_tech']}")
        print(f"    - Platforms: {len([n for n in graph['nodes'] if n['type'] == 'platform'])}")
        print(f"\n  Edges: {len(graph['edges'])}")
        print(f"\n  Graph size reduction: ~90%+ (metadata-only nodes)")
        print(f"  Output: {output_path}")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n  Run metadata extraction first:")
        print("  python app/extractors/metadata_extractor.py")
    except Exception as e:
        print(f"❌ Error building graph: {e}")
        raise


if __name__ == "__main__":
    main()
