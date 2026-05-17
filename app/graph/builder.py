"""Graph builder - constructs knowledge graph from extracted evidence."""
import json
import networkx as nx
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime

from app.models.schemas import GraphNode, GraphEdge, GraphDocument, SkillEvidenceRanked


class GraphBuilder:
    """
    Builds a knowledge graph representing the user's work life.
    
    Node types:
    - person: The user
    - repository: GitHub repositories
    - project: Vercel/Cloudflare projects
    - skill: Extracted skills/technologies
    - organization: Companies, platforms
    - deployment: Specific deployments
    - resource: Cloud infrastructure resources
    
    Edge types:
    - OWNS: person -> repository
    - BUILT: person -> project
    - USES: person/repository/project -> skill
    - DEPLOYED_ON: project -> platform
    - CONTRIBUTED_TO: person -> repository
    - RELATES_TO: skill -> skill (related technologies)
    """

    def __init__(self):
        self.graph = nx.MultiGraph()
        self.node_index = {}  # node_id -> node_data
        self.edge_index = []  # list of (source, target, type, data)

    def add_person_node(self, person_id: str = "person:main") -> GraphNode:
        """Add or get the main person node."""
        if person_id in self.node_index:
            return self.node_index[person_id]
        
        node = GraphNode(
            id=person_id,
            type="person",
            properties={
                "name": "",
                "login": "",
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        self._add_node(node)
        return node

    def add_repository_node(
        self,
        repo_name: str,
        properties: Dict[str, Any]
    ) -> GraphNode:
        """Add a repository node."""
        node_id = f"repo:{repo_name}"
        if node_id in self.node_index:
            return self.node_index[node_id]
        
        node = GraphNode(
            id=node_id,
            type="repository",
            properties={
                "name": repo_name,
                **properties,
            }
        )
        self._add_node(node)
        return node

    def add_project_node(
        self,
        project_name: str,
        platform: str,
        properties: Dict[str, Any]
    ) -> GraphNode:
        """Add a project node (Vercel/Cloudflare project)."""
        node_id = f"project:{platform}:{project_name}"
        if node_id in self.node_index:
            return self.node_index[node_id]
        
        node = GraphNode(
            id=node_id,
            type="project",
            properties={
                "name": project_name,
                "platform": platform,
                **properties,
            }
        )
        self._add_node(node)
        return node

    def add_skill_node(
        self,
        skill_name: str,
        category: str,
        properties: Dict[str, Any]
    ) -> GraphNode:
        """Add a skill/technology node."""
        node_id = f"skill:{skill_name.lower().replace(' ', '_')}"
        if node_id in self.node_index:
            # Update existing node with new properties
            existing = self.node_index[node_id]
            existing.properties.update(properties)
            return existing
        
        node = GraphNode(
            id=node_id,
            type="skill",
            properties={
                "name": skill_name,
                "category": category,
                **properties,
            }
        )
        self._add_node(node)
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> GraphEdge:
        """Add an edge between nodes."""
        edge = GraphEdge(
            source=source_id,
            target=target_id,
            type=edge_type,
            properties=properties or {}
        )
        self.edge_index.append(edge)
        return edge

    def _add_node(self, node: GraphNode):
        """Internal method to add node to index and graph."""
        self.node_index[node.id] = node
        self.graph.add_node(node.id, **node.properties)

    def build_from_repositories(
        self,
        repo_snapshots: List[Dict[str, Any]],
        person_id: str = "person:main"
    ) -> int:
        """
        Build graph from repository snapshots.
        
        Args:
            repo_snapshots: List of normalized repository data
            person_id: ID of the person node
            
        Returns:
            Number of nodes added
        """
        nodes_added = 0
        self.add_person_node(person_id)
        
        for repo_data in repo_snapshots:
            repo_name = repo_data.get("repo_name", "")
            if not repo_name:
                continue
            
            # Add repository node
            repo_node = self.add_repository_node(repo_name, repo_data)
            nodes_added += 1
            
            # Add edge: person OWNS repository
            self.add_edge(
                person_id,
                repo_node.id,
                "OWNS",
                {"since": repo_data.get("created_at", "")}
            )
            
            # Add skills from languages
            languages = repo_data.get("languages", {})
            for lang in languages.keys():
                skill_node = self.add_skill_node(
                    lang,
                    "language",
                    {"usage_count": languages.get(lang, 0)}
                )
                self.add_edge(
                    repo_node.id,
                    skill_node.id,
                    "USES",
                    {"evidence_type": "language_usage"}
                )
            
            # Add skills from frameworks in dependency files
            dep_files = repo_data.get("dependency_files", {})
            for file_name, content in dep_files.items():
                frameworks = self._extract_frameworks_from_deps(file_name, content)
                for fw in frameworks:
                    skill_node = self.add_skill_node(fw, "framework", {})
                    self.add_edge(
                        repo_node.id,
                        skill_node.id,
                        "USES",
                        {"evidence_type": "dependency", "file": file_name}
                    )
        
        return nodes_added

    def build_from_projects(
        self,
        projects: List[Dict[str, Any]],
        platform: str,
        person_id: str = "person:main"
    ) -> int:
        """
        Build graph from project data (Vercel, Cloudflare, etc.).
        
        Args:
            projects: List of normalized project data
            platform: Platform name (vercel, cloudflare)
            person_id: ID of the person node
            
        Returns:
            Number of nodes added
        """
        nodes_added = 0
        self.add_person_node(person_id)
        
        for proj_data in projects:
            proj_name = proj_data.get("project_name", "")
            if not proj_name:
                continue
            
            # Add project node
            proj_node = self.add_project_node(proj_name, platform, proj_data)
            nodes_added += 1
            
            # Add edge: person BUILT project
            self.add_edge(
                person_id,
                proj_node.id,
                "BUILT",
                {"platform": platform}
            )
            
            # Add platform skill
            platform_skill = platform.lower()
            skill_node = self.add_skill_node(platform_skill, "platform", {})
            self.add_edge(
                proj_node.id,
                skill_node.id,
                "DEPLOYED_ON",
                {"evidence_type": "deployment"}
            )
            
            # Link to git repo if available
            git_repo = proj_data.get("git_repo", "")
            if git_repo:
                repo_node_id = f"repo:{git_repo}"
                if repo_node_id in self.node_index:
                    self.add_edge(
                        proj_node.id,
                        repo_node_id,
                        "LINKED_TO_REPO",
                        {}
                    )
        
        return nodes_added

    def build_from_skills(
        self,
        skills: List[SkillEvidenceRanked],
        person_id: str = "person:main"
    ) -> int:
        """
        Build graph from extracted skills.
        
        Args:
            skills: List of ranked skills
            person_id: ID of the person node
            
        Returns:
            Number of nodes added
        """
        nodes_added = 0
        self.add_person_node(person_id)
        
        for skill in skills:
            skill_node = self.add_skill_node(
                skill.skill_name,
                skill.category,
                {
                    "proficiency": skill.proficiency_indicator,
                    "confidence": skill.confidence,
                    "frequency": skill.frequency,
                    "evidence_types": skill.evidence_types,
                }
            )
            
            # Add edge: person USES skill
            self.add_edge(
                person_id,
                skill_node.id,
                "USES",
                {
                    "proficiency": skill.proficiency_indicator,
                    "confidence": skill.confidence,
                }
            )
            nodes_added += 1
        
        return nodes_added

    def _extract_frameworks_from_deps(
        self,
        file_name: str,
        content: str
    ) -> List[str]:
        """Extract framework names from dependency file content."""
        frameworks = []
        content_lower = content.lower()
        
        # Simple pattern matching
        if "react" in content_lower:
            frameworks.append("react")
        if "next" in content_lower:
            frameworks.append("nextjs")
        if "vue" in content_lower:
            frameworks.append("vue")
        if "fastapi" in content_lower:
            frameworks.append("fastapi")
        if "django" in content_lower:
            frameworks.append("django")
        if "flask" in content_lower:
            frameworks.append("flask")
        
        return list(set(frameworks))

    def to_document(self) -> GraphDocument:
        """Convert graph to GraphDocument for serialization."""
        nodes = [
            {"id": node.id, "type": node.type, "properties": node.properties}
            for node in self.node_index.values()
        ]
        
        edges = [
            {
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "properties": edge.properties,
            }
            for edge in self.edge_index
        ]
        
        # Extract skills
        skills = []
        for node in self.node_index.values():
            if node.type == "skill":
                skills.append({
                    "name": node.properties.get("name", ""),
                    "category": node.properties.get("category", ""),
                    **node.properties,
                })
        
        return GraphDocument(
            nodes=nodes,
            edges=edges,
            skills=skills,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    def save_json(self, path: str):
        """Save graph to JSON file."""
        doc = self.to_document()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "nodes": doc.nodes,
                "edges": doc.edges,
                "skills": doc.skills,
                "metadata": doc.metadata,
            }, f, indent=2, default=str)

    def load_from_json(self, path: str) -> bool:
        """Load graph from JSON file."""
        import json as json_lib
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json_lib.load(f)
            
            # Rebuild nodes
            for node_data in data.get("nodes", []):
                node_id = node_data.get("id", "")
                node_type = node_data.get("type", "")
                properties = node_data.get("properties", {})
                
                # Recreate node based on type
                if node_type == "person":
                    self.add_person_node(node_id.replace("person:", ""))
                elif node_type == "repository":
                    self.add_repository_node(
                        properties.get("name", ""),
                        properties
                    )
                elif node_type == "project":
                    platform = properties.get("platform", "unknown")
                    node_name = node_id.replace(f"project:{platform}:", "")
                    self.add_project_node(node_name, platform, properties)
                elif node_type == "skill":
                    self.add_skill_node(
                        properties.get("name", node_id.replace("skill:", "")),
                        properties.get("category", "general"),
                        properties
                    )
            
            # Recreate edges
            for edge_data in data.get("edges", []):
                source = edge_data.get("source", "")
                target = edge_data.get("target", "")
                edge_type = edge_data.get("type", "RELATED_TO")
                props = edge_data.get("properties", {})
                self.add_edge(source, target, edge_type, props)
            
            return True
        except Exception as e:
            print(f"Error loading graph: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        node_types = {}
        for node in self.node_index.values():
            t = node.type
            node_types[t] = node_types.get(t, 0) + 1
        
        edge_types = {}
        for edge in self.edge_index:
            t = edge.type
            edge_types[t] = edge_types.get(t, 0) + 1
        
        return {
            "total_nodes": len(self.node_index),
            "total_edges": len(self.edge_index),
            "node_types": node_types,
            "edge_types": edge_types,
        }
