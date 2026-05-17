"""Graph serializer - handles graph persistence and retrieval."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.schemas import GraphDocument, GraphNode, GraphEdge


class GraphSerializer:
    """
    Handles serialization and deserialization of the knowledge graph.
    
    Supports:
    - JSON format for human readability
    - NetworkX format for graph operations
    - Compressed format for storage efficiency
    """

    def __init__(self, output_path: Optional[str] = None):
        """Initialize with optional output path."""
        self.output_path = output_path or "data/graph/knowledge_graph.json"

    def serialize(
        self,
        graph_document: GraphDocument,
        path: Optional[str] = None
    ) -> str:
        """
        Serialize graph document to file.
        
        Args:
            graph_document: GraphDocument to serialize
            path: Output path (default: self.output_path)
            
        Returns:
            Path to saved file
        """
        output_path = path or self.output_path
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "nodes": graph_document.nodes,
            "edges": graph_document.edges,
            "skills": graph_document.skills,
            "metadata": graph_document.metadata,
            "serialized_at": datetime.utcnow().isoformat(),
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        return output_path

    def deserialize(self, path: Optional[str] = None) -> GraphDocument:
        """
        Deserialize graph document from file.
        
        Args:
            path: Input path (default: self.output_path)
            
        Returns:
            Deserialized GraphDocument
        """
        input_path = path or self.output_path
        
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Graph file not found: {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return GraphDocument(
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            skills=data.get("skills", []),
            metadata=data.get("metadata", {}),
        )

    def exists(self, path: Optional[str] = None) -> bool:
        """Check if graph file exists."""
        input_path = path or self.output_path
        return Path(input_path).exists()

    def get_summary(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of graph without full deserialization.
        
        Returns:
            Dict with node/edge counts and metadata
        """
        input_path = path or self.output_path
        
        if not self.exists(input_path):
            return {"error": "Graph file not found"}
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        metadata = data.get("metadata", {})
        
        return {
            "node_count": len(data.get("nodes", [])),
            "edge_count": len(data.get("edges", [])),
            "skill_count": len(data.get("skills", [])),
            "created_at": metadata.get("created_at", ""),
            "serialized_at": data.get("serialized_at", ""),
            "path": input_path,
        }

    def export_skills(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Export skills from graph.
        
        Returns:
            List of skill dictionaries
        """
        input_path = path or self.output_path
        
        if not self.exists(input_path):
            return []
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("skills", [])

    def export_node_edges(
        self,
        node_id: str,
        path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a specific node and its edges.
        
        Args:
            node_id: ID of node to export
            path: Graph file path
            
        Returns:
            Dict with node data and connected edges
        """
        input_path = path or self.output_path
        
        if not self.exists(input_path):
            return {"error": "Graph file not found"}
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Find node
        node = None
        for n in data.get("nodes", []):
            if n.get("id") == node_id:
                node = n
                break
        
        if not node:
            return {"error": f"Node not found: {node_id}"}
        
        # Find connected edges
        connected_edges = []
        for edge in data.get("edges", []):
            if edge.get("source") == node_id or edge.get("target") == node_id:
                connected_edges.append(edge)
        
        return {
            "node": node,
            "edges": connected_edges,
            "edge_count": len(connected_edges),
        }
