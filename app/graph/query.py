"""Graph query - query operations for the knowledge graph."""
import json
from typing import Dict, Any, List, Optional, Set
from pathlib import Path


class GraphQuerier:
    """
    Provides query operations for the knowledge graph.
    
    Supports:
    - Node lookup by ID or type
    - Edge traversal
    - Skill queries
    - Path finding
    - Neighborhood queries
    """

    def __init__(self, graph_path: Optional[str] = None):
        """Initialize with graph file path."""
        self.graph_path = graph_path or "data/graph/knowledge_graph.json"
        self._cache = None
        self._nodes_by_id = None
        self._nodes_by_type = None

    def _load_graph(self):
        """Load graph data if not already loaded."""
        if self._cache is not None:
            return
        
        if not Path(self.graph_path).exists():
            raise FileNotFoundError(f"Graph file not found: {self.graph_path}")
        
        with open(self.graph_path, "r", encoding="utf-8") as f:
            self._cache = json.load(f)
        
        # Build indexes
        self._nodes_by_id = {}
        self._nodes_by_type = {}
        
        for node in self._cache.get("nodes", []):
            node_id = node.get("id", "")
            node_type = node.get("type", "")
            
            self._nodes_by_id[node_id] = node
            
            if node_type not in self._nodes_by_type:
                self._nodes_by_type[node_type] = []
            self._nodes_by_type[node_type].append(node)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: ID of node to retrieve
            
        Returns:
            Node data or None if not found
        """
        self._load_graph()
        return self._nodes_by_id.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        Get all nodes of a specific type.
        
        Args:
            node_type: Type of nodes to retrieve
            
        Returns:
            List of node data
        """
        self._load_graph()
        return self._nodes_by_type.get(node_type, [])

    def get_connected_nodes(
        self,
        node_id: str,
        edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get nodes connected to a specific node.
        
        Args:
            node_id: ID of source node
            edge_type: Optional filter by edge type
            
        Returns:
            List of connected nodes
        """
        self._load_graph()
        connected = []
        
        for edge in self._cache.get("edges", []):
            if edge.get("source") == node_id or edge.get("target") == node_id:
                if edge_type and edge.get("type") != edge_type:
                    continue
                
                # Get the other node ID
                other_id = edge.get("target") if edge.get("source") == node_id else edge.get("source")
                other_node = self._nodes_by_id.get(other_id)
                if other_node:
                    connected.append(other_node)
        
        return connected

    def get_skills(self) -> List[Dict[str, Any]]:
        """Get all skills from graph (from skill nodes)."""
        self._load_graph()
        skills = []
        for node in self._cache.get("nodes", []):
            if node.get("type") == "skill":
                props = node.get("properties", {})
                mention_count = props.get("mention_count", 0)
                skills.append({
                    "name": props.get("name", node.get("id", "")),
                    "category": props.get("category", "general"),
                    "confidence": min(mention_count / 100.0, 1.0) if mention_count else 0.5,
                    "mention_count": mention_count,
                })
        return skills

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects from the graph."""
        self._load_graph()
        projects = []
        for node in self._cache.get("nodes", []):
            if node.get("type") == "project":
                props = node.get("properties", {})
                projects.append({
                    "name": props.get("name", node.get("id", "")),
                    "platform": props.get("platform", "unknown"),
                    "url": props.get("url", ""),
                })
        return projects

    def get_top_skills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top skills by confidence.
        
        Args:
            limit: Maximum number of skills to return
            
        Returns:
            List of top skill data
        """
        skills = self.get_skills()
        sorted_skills = sorted(
            skills,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        return sorted_skills[:limit]

    def get_skill_evidence(self, skill_name: str) -> List[Dict[str, Any]]:
        """
        Get evidence for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of evidence items for the skill
        """
        self._load_graph()
        skill_lower = skill_name.lower()
        evidence = []

        # Search for skill node
        for node in self._cache.get("nodes", []):
            if node.get("type") == "skill":
                props = node.get("properties", {})
                name = props.get("name", "").lower()
                if name == skill_lower or skill_lower in name:
                    evidence.append({
                        "type": "skill_node",
                        "text": f"Skill: {props.get('name', '')}",
                        "source": node.get("id", ""),
                        "confidence": min(props.get("mention_count", 0) / 100.0, 1.0) if props.get("mention_count") else 0.5,
                    })

        # Search edges for USES relationships involving this skill
        for edge in self._cache.get("edges", []):
            if edge.get("type") == "USES":
                target = edge.get("target", "")
                if skill_lower in target.lower():
                    source_node = self._nodes_by_id.get(edge.get("source", ""))
                    if source_node:
                        evidence.append({
                            "type": "edge",
                            "text": f"Used by: {source_node.get('properties', {}).get('name', source_node.get('id', ''))}",
                            "source": source_node.get("id", ""),
                            "confidence": 0.6,
                        })

        return evidence

    def search_skills(
        self,
        query: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search skills by name or category.
        
        Args:
            query: Search query string
            category: Optional category filter
            
        Returns:
            List of matching skills
        """
        skills = self.get_skills()
        query_lower = query.lower()
        
        matches = []
        for skill in skills:
            skill_name = skill.get("name", "").lower()
            skill_category = skill.get("category", "").lower()
            
            # Check category filter
            if category and category.lower() not in skill_category:
                continue
            
            # Check name match
            if query_lower in skill_name or query_lower in skill_category:
                matches.append(skill)
        
        return matches

    def get_person_projects(self, person_id: str = "person:main") -> List[Dict[str, Any]]:
        """
        Get all projects associated with a person.
        
        Args:
            person_id: ID of person node
            
        Returns:
            List of project nodes
        """
        self._load_graph()
        projects = []
        
        for edge in self._cache.get("edges", []):
            if edge.get("source") == person_id and edge.get("type") == "BUILT":
                project_id = edge.get("target")
                project_node = self._nodes_by_id.get(project_id)
                if project_node and project_node.get("type") == "project":
                    projects.append(project_node)
        
        return projects

    def get_repository_skills(
        self,
        repo_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get skills associated with a repository.
        
        Args:
            repo_name: Name of repository
            
        Returns:
            List of skill data
        """
        self._load_graph()
        repo_id = f"repo:{repo_name}"
        
        # Find repo node
        repo_node = self._nodes_by_id.get(repo_id)
        if not repo_node:
            return []
        
        # Find connected skills
        skills = []
        for edge in self._cache.get("edges", []):
            if edge.get("source") == repo_id and edge.get("type") == "USES":
                skill_id = edge.get("target")
                skill_node = self._nodes_by_id.get(skill_id)
                if skill_node and skill_node.get("type") == "skill":
                    skills.append(skill_node)
        
        return skills

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects from the graph."""
        self._load_graph()
        projects = []
        for node in self._cache.get("nodes", []):
            if node.get("type") == "project":
                props = node.get("properties", {})
                projects.append({
                    "name": props.get("name", node.get("id", "")),
                    "platform": props.get("platform", "unknown"),
                    "url": props.get("url", ""),
                })
        return projects

    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Dict with graph stats
        """
        self._load_graph()
        
        nodes = self._cache.get("nodes", [])
        edges = self._cache.get("edges", [])
        skills = self._cache.get("skills", [])
        
        node_types = {}
        for node in nodes:
            t = node.get("type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1
        
        edge_types = {}
        for edge in edges:
            t = edge.get("type", "unknown")
            edge_types[t] = edge_types.get(t, 0) + 1
        
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_skills": len(skills),
            "node_types": node_types,
            "edge_types": edge_types,
            "file_path": self.graph_path,
        }
