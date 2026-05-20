"""
Résumé Agent - Uses the knowledge graph and RAG to answer skill queries.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from ..graph.builder import GraphBuilder
from ..graph.query import GraphQuerier
from ..rag.retriever import Retriever
from ..rag.embedder import Embedder
from ..rag.vector_store import VectorStore
from ..rag.chunker import TextChunker
from ..extractors.skill_extractor import SkillExtractor


@dataclass
class AgentResponse:
    """Response from the résumé agent."""
    answer: str
    skills: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    sources: List[str]
    confidence: float


class ResumeAgent:
    """
    Résumé agent that answers queries about skills and experience
    using the knowledge graph and RAG retrieval.
    """
    
    def __init__(
        self,
        graph_path: Optional[str] = None,
        vector_store_path: Optional[str] = None,
        chunks_path: Optional[str] = None
    ):
        """
        Initialize the résumé agent.
        
        Args:
            graph_path: Path to the serialized graph JSON
            vector_store_path: Path to the FAISS index
            chunks_path: Path to the text chunks
        """
        self.graph_path = graph_path or "data/graph/knowledge_graph.json"
        self.vector_store_path = vector_store_path or "data/embeddings/faiss_index"
        self.chunks_path = chunks_path or "data/chunks.json"
        
        # Lazy initialization
        self._graph_builder: Optional[GraphBuilder] = None
        self._graph_querier: Optional[GraphQuerier] = None
        self._retriever: Optional[Retriever] = None
        self._embedder: Optional[Embedder] = None
        
    @property
    def graph_builder(self) -> GraphBuilder:
        if self._graph_builder is None:
            self._graph_builder = GraphBuilder()
            # Load existing graph if available
            try:
                self._graph_builder.load_from_json(self.graph_path)
            except FileNotFoundError:
                pass  # Graph will be built from scratch
        return self._graph_builder
    
    @property
    def graph_querier(self) -> GraphQuerier:
        if self._graph_querier is None:
            self._graph_querier = GraphQuerier(self.graph_path)
        return self._graph_querier
    
    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            # Initialize components
            vector_store = VectorStore()
            graph_querier = self.graph_querier
            embedder = self.embedder
            chunker = TextChunker()
            
            self._retriever = Retriever(
                vector_store=vector_store,
                graph_querier=graph_querier,
                embedder=embedder,
                chunker=chunker,
                index_path=self.vector_store_path,
                graph_path=self.graph_path
            )
        return self._retriever
    
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder()
        return self._embedder
    
    def query(self, question: str, top_k: int = 5) -> AgentResponse:
        """
        Query the résumé agent with a question.

        Args:
            question: User's question (e.g., "What are my Python skills?")
            top_k: Number of top results to retrieve

        Returns:
            AgentResponse with answer, skills, evidence, and sources
        """
        # Retrieve relevant information
        retrieved = self.retriever.retrieve(question, k=top_k)

        # retrieved is a list of dicts with keys: type, text, metadata, source, score
        # Convert to chunks format for downstream methods
        chunks = []
        sources = []
        for item in retrieved:
            chunk = {
                "text": item.get("text", ""),
                "source": item.get("source", "unknown"),
                "metadata": item.get("metadata", {}),
                "score": item.get("score", 0.0)
            }
            chunks.append(chunk)
            if item.get("source"):
                sources.append(item["source"])

        # Extract skills from retrieved chunks
        skills = self._extract_skills_from_chunks(chunks)

        # Get graph-based evidence
        graph_evidence = self._get_graph_evidence(question)

        # Combine and rank evidence
        all_evidence = self._rank_evidence(chunks, graph_evidence)

        # Generate answer
        answer = self._generate_answer(question, skills, all_evidence, sources)

        # Calculate overall confidence
        confidence = self._calculate_confidence(skills, all_evidence)

        return AgentResponse(
            answer=answer,
            skills=skills,
            evidence=all_evidence,
            sources=list(set(sources)),
            confidence=confidence
        )
    
    def list_skills(self, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """
        List all extracted skills with evidence.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of skills with metadata
        """
        # Query graph for skill nodes
        skill_nodes = self.graph_querier.get_skills()
        
        skills = []
        for skill_data in skill_nodes:
            skill_name = skill_data.get("name", "")
            confidence = skill_data.get("confidence", 0.0)
            if confidence >= min_confidence:
                skills.append({
                    "skill": skill_name,
                    "confidence": confidence,
                    "evidence_count": skill_data.get("evidence_count", 0),
                    "sources": skill_data.get("sources", []),
                    "projects": skill_data.get("projects", [])
                })
        
        # Sort by confidence
        skills.sort(key=lambda x: x["confidence"], reverse=True)
        return skills
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in the knowledge graph.
        
        Returns:
            List of projects with metadata
        """
        return self.graph_querier.get_projects()
    
    def get_skill_evidence(self, skill: str) -> List[Dict[str, Any]]:
        """
        Get evidence for a specific skill.
        
        Args:
            skill: Skill name
            
        Returns:
            List of evidence items
        """
        return self.graph_querier.get_skill_evidence(skill)
    
    def _extract_skills_from_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract skills from retrieved chunks."""
        extractor = SkillExtractor()
        all_skills = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            skills = extractor.extract_from_text(text)
            all_skills.extend(skills)
        
        # Deduplicate and merge
        skill_map = {}
        for skill in all_skills:
            name = skill["name"]
            if name not in skill_map:
                skill_map[name] = skill
            else:
                # Merge evidence
                skill_map[name]["evidence"] = list(set(
                    skill_map[name]["evidence"] + skill["evidence"]
                ))
                skill_map[name]["confidence"] = max(
                    skill_map[name]["confidence"],
                    skill["confidence"]
                )
        
        return list(skill_map.values())
    
    def _get_graph_evidence(self, question: str) -> List[Dict[str, Any]]:
        """Get evidence from graph traversal."""
        # Extract keywords from question
        keywords = question.lower().split()
        tech_keywords = [
            k for k in keywords if k in [
                "python", "javascript", "react", "node", "api", "cloud",
                "aws", "gcp", "azure", "docker", "kubernetes"
            ]
        ]
        
        evidence = []
        for keyword in tech_keywords:
            skill_evidence = self.graph_querier.get_skill_evidence(keyword)
            evidence.extend(skill_evidence)
        
        return evidence
    
    def _rank_evidence(
        self,
        chunks: List[Dict[str, Any]],
        graph_evidence: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank and combine evidence from multiple sources."""
        all_evidence = []
        
        # Add chunk evidence
        for chunk in chunks:
            all_evidence.append({
                "type": "chunk",
                "text": chunk.get("text", "")[:200],  # Truncate for brevity
                "source": chunk.get("source", "unknown"),
                "score": chunk.get("score", 0.0)
            })
        
        # Add graph evidence
        all_evidence.extend(graph_evidence)
        
        # Sort by score/confidence
        all_evidence.sort(key=lambda x: x.get("score", 0.0) or x.get("confidence", 0.0), reverse=True)
        
        return all_evidence
    
    def _generate_answer(
        self,
        question: str,
        skills: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        sources: List[str]
    ) -> str:
        """Generate a natural language answer."""
        if not skills:
            return "I couldn't find specific skills matching your question. Try asking about specific technologies or projects."
        
        # Build answer
        skill_names = [s["name"] for s in skills[:5]]  # Top 5 skills
        skill_str = ", ".join(skill_names)
        
        answer = f"Based on your codebase and project history, I found the following relevant skills: {skill_str}.\n\n"
        
        # Add evidence summary
        if evidence:
            top_evidence = evidence[0]  # Top evidence
            answer += f"This is supported by evidence from {top_evidence.get('source', 'your projects')}.\n"
        
        # Add source count
        if sources:
            answer += f"\nSources analyzed: {len(sources)} files/repositories."
        
        return answer
    
    def _calculate_confidence(
        self,
        skills: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence in the answer."""
        if not skills or not evidence:
            return 0.0
        
        # Average confidence of top skills
        skill_confidences = [s.get("confidence", 0.0) for s in skills[:3]]
        avg_skill_confidence = sum(skill_confidences) / len(skill_confidences) if skill_confidences else 0.0
        
        # Evidence quality
        evidence_scores = [e.get("score", 0.0) or e.get("confidence", 0.0) for e in evidence[:5]]
        avg_evidence_score = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
        
        # Weighted average
        confidence = 0.6 * avg_skill_confidence + 0.4 * avg_evidence_score
        return min(confidence, 1.0)
