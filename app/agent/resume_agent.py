"""Resume Agent - main interface for querying the knowledge graph."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.config import (
    DATA_DIR, GRAPH_DIR, EMBEDDINGS_DIR,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
    EMBEDDING_MODEL,
)
from app.graph_store import Neo4jStore, KnowledgeGraphConfig
from app.rag.retriever import HybridRetriever
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the resume agent."""
    answer: str = ""
    skills: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0


class ResumeAgent:
    """Resume agent that answers career queries using the knowledge graph."""

    def __init__(self, neo4j_uri: Optional[str] = None,
                 neo4j_user: Optional[str] = None,
                 neo4j_password: Optional[str] = None):
        self.graph_path = str(GRAPH_DIR / "knowledge_graph.json")
        self.vector_store_path = str(EMBEDDINGS_DIR / "faiss_index")

        self._store: Optional[Neo4jStore] = None
        self._retriever: Optional[HybridRetriever] = None
        self._embedder: Optional[Embedder] = None
        self._vector_store: Optional[VectorStore] = None
        self._connected = False

        self.neo4j_config = KnowledgeGraphConfig(
            uri=neo4j_uri or NEO4J_URI or "bolt://localhost:7687",
            user=neo4j_user or NEO4J_USER or "neo4j",
            password=neo4j_password or NEO4J_PASSWORD or "",
            database=NEO4J_DATABASE or "neo4j",
        )

    def _ensure_connection(self) -> bool:
        """Lazy-connect to Neo4j and load vector store. Returns True if connected."""
        if self._connected:
            return True
        try:
            self._store = Neo4jStore(self.neo4j_config)
            self._store.connect()
        except Exception as e:
            logger.warning(f"ResumeAgent could not connect to Neo4j: {e}")
            return False

        # Load vector store and embedder for hybrid search
        try:
            self._embedder = Embedder(model_name=EMBEDDING_MODEL)
            self._vector_store = VectorStore(
                dimension=384,
                index_path=self.vector_store_path
            )
            # Force lazy-load of index
            _ = self._vector_store.index
            logger.info("ResumeAgent loaded vector store")
        except Exception as e:
            logger.warning(f"ResumeAgent could not load vector store: {e}")
            self._vector_store = None
            self._embedder = None

        self._retriever = HybridRetriever(
            self._store,
            vector_store=self._vector_store,
            embedder=self._embedder
        )
        self._connected = True
        logger.info("ResumeAgent connected to Neo4j")
        return True

    def query(self, question: str, top_k: int = 5) -> AgentResponse:
        """Answer a career query using the knowledge graph."""
        if not self._ensure_connection():
            return AgentResponse(
                answer="Knowledge graph is not available. Please run the collection pipeline first.",
                confidence=0.0
            )

        # Try career story retrieval for period/topic queries
        q_lower = question.lower()
        if any(word in q_lower for word in ["career", "story", "timeline", "period", "202", "2023", "2024", "2025"]):
            return self._answer_career_story(question, top_k)

        # Standard skill search
        results = self._retriever.retrieve(question, person_id="me", top_k=top_k)

        if not results:
            return AgentResponse(
                answer="I couldn't find relevant skills or projects for that query.",
                confidence=0.0
            )

        skills = [r.to_dict() for r in results]
        answer_parts = [f"Here are the top results for '{question}':"]
        for r in results[:top_k]:
            answer_parts.append(
                f"- {r.skill_name} ({r.category}): confidence {r.confidence:.2f}"
            )
            if r.evidence:
                answer_parts.append(f"  Evidence: {r.evidence}")

        return AgentResponse(
            answer="\n".join(answer_parts),
            skills=skills,
            evidence=[s for s in skills if s.get("evidence")],
            sources=list({s.get("source", "graph") for s in skills}),
            confidence=sum(s.get("confidence", 0) for s in skills) / max(len(skills), 1)
        )

    def _answer_career_story(self, question: str, top_k: int = 5) -> AgentResponse:
        """Answer a career-story style query using narratives and timeline data."""
        # Extract potential year from question
        import re
        years = re.findall(r"20\d{2}", question)
        period_start = f"{years[0]}-01-01" if years else ""
        period_end = f"{years[-1]}-12-31" if years else ""

        story = self._retriever.retrieve_career_story(
            period_start=period_start,
            period_end=period_end,
            topic=question,
            top_k=top_k
        )

        projects = story.get("projects", [])
        narratives = story.get("narratives", [])
        skills = story.get("skills", [])

        if not projects:
            return AgentResponse(
                answer=f"I couldn't find projects matching '{question}'.",
                confidence=0.0
            )

        answer_parts = [f"Career story for '{question}':"]
        for p in projects:
            answer_parts.append(f"\n### {p.get('name', 'Unknown Project')}")
            if p.get('description'):
                answer_parts.append(p['description'])
            if p.get('pushed_at'):
                answer_parts.append(f"Last active: {p['pushed_at']}")

        for n in narratives:
            if n.get('text'):
                answer_parts.append(f"\n{n['text']}")

        return AgentResponse(
            answer="\n".join(answer_parts),
            skills=[{"skill": s["name"], "category": s["category"]} for s in skills],
            sources=["graph"],
            confidence=0.85 if projects else 0.0
        )

    def list_skills(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """List all skills with confidence >= min_confidence."""
        if not self._ensure_connection():
            return []

        skills = self._store.get_person_skills("me")
        filtered = [s for s in skills if s.get("confidence", 0) >= min_confidence]
        filtered.sort(key=lambda s: s.get("confidence", 0), reverse=True)
        return [
            {
                "skill": s["name"],
                "category": s["category"],
                "confidence": s.get("confidence", 0),
                "evidence": s.get("evidence", ""),
            }
            for s in filtered
        ]

    def get_skill_evidence(self, skill_name: str) -> List[Dict[str, Any]]:
        """Get evidence for a specific skill."""
        if not self._ensure_connection():
            return []

        return self._retriever.get_skill_evidence(skill_name, person_id="me")

    def get_projects(self) -> List[Dict[str, Any]]:
        """List all projects from the knowledge graph."""
        if not self._ensure_connection():
            return []

        query = """
        MATCH (p:Project)
        RETURN p.id as id, p.name as name, p.description as description,
               p.source as source, p.url as url, p.pushed_at as pushed_at
        ORDER BY p.pushed_at DESC
        """
        try:
            with self._store.driver.session() as session:
                result = session.run(query)
                return [record.data() for record in result]
        except Exception as e:
            logger.warning(f"Failed to get projects: {e}")
            return []
