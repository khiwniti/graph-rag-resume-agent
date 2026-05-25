"""Hybrid retriever combining graph and vector search."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..graph_store import Neo4jStore

if TYPE_CHECKING:
    from .vector_store import VectorStore
    from .embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from hybrid retrieval."""
    skill_name: str
    category: str
    confidence: float
    source: str  # "graph", "vector", or "hybrid"
    evidence: Optional[str] = None
    projects: List[str] = field(default_factory=list)
    score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "category": self.category,
            "confidence": self.confidence,
            "source": self.source,
            "evidence": self.evidence,
            "projects": self.projects,
            "score": self.score,
        }


@dataclass
class NarrativeResult:
    """Result from narrative retrieval."""
    project_id: str
    project_name: str
    narrative_text: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    mentioned_skills: List[str] = field(default_factory=list)
    mentioned_technologies: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "narrative_text": self.narrative_text,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "mentioned_skills": self.mentioned_skills,
            "mentioned_technologies": self.mentioned_technologies,
        }


class HybridRetriever:
    """
    Hybrid retriever combining Neo4j graph queries with vector search.

    For resume RAG queries:
    1. Graph layer: Find skills and projects directly from Neo4j
    2. Vector layer: Search embeddings for semantic similarity
    3. Fusion: Combine results with Reciprocal Rank Fusion (RRF)
    """

    def __init__(self, neo4j_store: Neo4jStore,
                 vector_store: Optional["VectorStore"] = None,
                 embedder: Optional["Embedder"] = None):
        """
        Initialize hybrid retriever.

        Args:
            neo4j_store: Neo4j graph store
            vector_store: Optional vector store for semantic search
            embedder: Optional embedder to convert text queries to vectors
        """
        self.neo4j_store = neo4j_store
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, person_id: str = "me",
                 top_k: int = 10) -> List[RetrievalResult]:
        """
        Retrieve skills using hybrid approach.

        Args:
            query: Search query (e.g., "Python skills", "backend experience")
            person_id: Person ID to search for
            top_k: Maximum number of results

        Returns:
            List of retrieval results sorted by relevance
        """
        results: List[RetrievalResult] = []

        # Step 1: Graph-based retrieval
        graph_results = self._retrieve_from_graph(query, person_id, top_k)

        # Step 2: Vector-based retrieval (if available)
        vector_results = []
        if self.vector_store:
            vector_results = self._retrieve_from_vectors(query, top_k)

        # Step 3: Combine results
        results = self._combine_results(graph_results, vector_results, top_k)

        return results

    def _retrieve_from_graph(self, query: str, person_id: str,
                              top_k: int) -> List[RetrievalResult]:
        """Retrieve skills from graph based on query."""
        results = []
        query_lower = query.lower()

        # Step 1: Person skills, but only return the generic "top skills" list when the query is broad.
        # For specific queries, filter by query tokens so we don't always return TypeScript/React/etc.
        skills = self.neo4j_store.get_person_skills(person_id)

        # crude tokenization + stopwords
        words = [w.strip().lower() for w in query_lower.replace("?", " ").replace(",", " ").split()]
        stop = {
            "how","have","you","the","and","for","with","your","from","this","that","what","where","when",
            "is","are","was","were","do","does","did","in","on","to","of","a","an","my","me","used","use"
        }
        tokens = [w for w in words if len(w) > 2 and w not in stop]

        def matches_skill(name: str) -> bool:
            n = (name or "").lower()
            return any(t in n for t in tokens)

        if tokens:
            filtered_skills = [s for s in skills if matches_skill(s.get("name", ""))]
        else:
            filtered_skills = skills

        # If the query is specific but we found no matches, DO NOT return generic top skills.
        if tokens and not filtered_skills:
            filtered_skills = []

        for skill in filtered_skills[:top_k]:
            results.append(RetrievalResult(
                skill_name=skill["name"],
                category=skill["category"],
                confidence=skill.get("confidence", 1.0),
                source="graph",
                evidence=skill.get("evidence"),
            ))

        # Step 2: Schema-aware skill search with project counts (Person/Project/Skill only)
        cypher = """
        MATCH (me:Person {id: $person_id})-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (p:Project)-[:REQUIRES_SKILL]->(s)
        WITH s, count(p) as project_count
        WITH s, project_count
        WHERE $query = '' OR toLower(s.name) CONTAINS toLower($query)
        RETURN s.name as name,
               s.category as category,
               coalesce(s.confidence, 0.0) as confidence,
               project_count as project_count
        ORDER BY project_count DESC, confidence DESC
        LIMIT $limit
        """
        try:
            # Only run if (a) query looks specific or (b) we have no results yet
            if tokens or not results:
                with self.neo4j_store.driver.session() as session:
                    rows = session.run(cypher, {
                        "person_id": person_id,
                        "query": (query.strip() if len(query.strip()) > 2 else ""),
                        "limit": top_k,
                    })
                    for record in rows:
                        results.append(RetrievalResult(
                            skill_name=record["name"],
                            category=record["category"] or "skill",
                            confidence=float(record.get("confidence") or 0.0),
                            source="graph",
                            evidence=f"Used in {record['project_count']} projects" if record.get("project_count") is not None else None,
                        ))
        except Exception as e:
            logger.debug(f"Graph skill search failed: {e}")

        # Step 3: Generic skill search if no person-specific results
        if not results:
            categories = self._extract_categories_from_query(query)
            if categories:
                for category in categories:
                    skills = self.neo4j_store.search_skills(category, limit=top_k)
                    for skill in skills:
                        results.append(RetrievalResult(
                            skill_name=skill["name"],
                            category=skill["category"],
                            confidence=skill.get("confidence", 1.0),
                            source="graph",
                        ))
            else:
                # Substring search on all skills
                skills = self.neo4j_store.search_skills(query, limit=top_k)
                for skill in skills:
                    results.append(RetrievalResult(
                        skill_name=skill["name"],
                        category=skill["category"],
                        confidence=skill.get("confidence", 1.0),
                        source="graph",
                    ))

        return self._deduplicate_results(results, top_k)

    def _deduplicate_results(self, results: List[RetrievalResult], top_k: int) -> List[RetrievalResult]:
        """Deduplicate results by skill name."""
        seen = set()
        deduped = []
        for r in results:
            key = r.skill_name.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return sorted(deduped, key=lambda x: x.confidence, reverse=True)[:top_k]

    def _retrieve_from_vectors(self, query: str,
                                top_k: int) -> List[RetrievalResult]:
        """Retrieve skills using vector similarity."""
        results = []

        if not self.vector_store or not self.embedder:
            return results

        # Embed query and search vector store
        try:
            query_embedding = self.embedder.embed(query)
            matches = self.vector_store.search(query_embedding, top_k=top_k)
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return results

        for metadata, distance in matches:
            # Convert L2 distance to a rough confidence score (closer = higher confidence)
            confidence = max(0.0, 1.0 - (distance / 10.0))

            # This repo's vector index may store wiki pages, not explicit skills.
            # In that case, treat the vector hit as an evidence-backed "concept/document" result.
            title = metadata.get("title") or metadata.get("skill_name") or metadata.get("text", "")[:50]
            wiki_path = metadata.get("wiki_path")
            wiki_type = metadata.get("wiki_type")

            if wiki_path:
                results.append(RetrievalResult(
                    skill_name=str(title),
                    category=f"wiki:{wiki_type or 'document'}",
                    confidence=confidence,
                    source="vector",
                    score=confidence,
                    evidence=f"wiki:{wiki_path}",
                ))
            else:
                results.append(RetrievalResult(
                    skill_name=str(title),
                    category=metadata.get("category", "skill"),
                    confidence=confidence,
                    source="vector",
                    score=confidence,
                    evidence=metadata.get("source", ""),
                ))

        return results

    def _extract_categories_from_query(self, query: str) -> List[str]:
        """Extract skill categories from query."""
        categories = []
        query_lower = query.lower()

        # Category keywords
        category_map = {
            "language": ["language", "programming", "python", "javascript", "rust"],
            "framework": ["framework", "react", "vue", "fastapi", "django"],
            "tool": ["tool", "docker", "git", "ci/cd"],
            "cloud": ["cloud", "aws", "gcp", "azure", "vercel", "cloudflare"],
            "database": ["database", "sql", "neo4j", "postgres", "mongodb"],
        }

        for category, keywords in category_map.items():
            if any(keyword in query_lower for keyword in keywords):
                categories.append(category)

        return categories

    def _combine_results(self, graph_results: List[RetrievalResult],
                          vector_results: List[RetrievalResult],
                          top_k: int) -> List[RetrievalResult]:
        """Combine graph and vector results using RRF."""
        # Simple deduplication by skill name
        seen = set()
        combined = []

        # Prioritize graph results
        for result in graph_results:
            key = f"{result.skill_name}:{result.category}"
            if key not in seen:
                seen.add(key)
                combined.append(result)

        # Add vector results not in graph
        for result in vector_results:
            key = f"{result.skill_name}:{result.category}"
            if key not in seen:
                seen.add(key)
                combined.append(result)

        # Sort by confidence/score
        combined.sort(key=lambda x: x.confidence, reverse=True)

        return combined[:top_k]

    def search_skills(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search skills by query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of skill dictionaries
        """
        results = self.retrieve(query, top_k=limit)
        return [r.to_dict() for r in results]

    def retrieve_narratives(self, query: str = "",
                              top_k: int = 5) -> List[NarrativeResult]:
        """Retrieve narrative chunks from the graph matching a query topic."""
        results = []
        store = self.neo4j_store

        # Simple keyword search on narrative text + linked project names
        cypher = """
        MATCH (n:Narrative)<-[:DESCRIBED_BY]-(p:Project)
        WHERE n.text CONTAINS $query OR p.name CONTAINS $query OR p.description CONTAINS $query
        RETURN n.id as id, n.text as text, n.period_start as period_start,
               n.period_end as period_end, p.id as project_id, p.name as project_name
        LIMIT $limit
        """

        try:
            with store.driver.session() as session:
                for record in session.run(cypher, {"query": query.lower(), "limit": top_k}):
                    results.append(NarrativeResult(
                        project_id=record["project_id"],
                        project_name=record["project_name"],
                        narrative_text=record["text"],
                        period_start=record["period_start"],
                        period_end=record["period_end"],
                    ))
        except Exception as e:
            logger.warning(f"Narrative retrieval failed: {e}")

        return results

    def retrieve_career_story(self, period_start: Optional[str] = None,
                              period_end: Optional[str] = None,
                              topic: str = "",
                              top_k: int = 5) -> Dict[str, Any]:
        """Retrieve a career story combining projects, skills, and narratives.

        Args:
            period_start: ISO date string (inclusive)
            period_end: ISO date string (inclusive)
            topic: Optional topic keyword
            top_k: Max projects to return

        Returns:
            Dict with projects, skills, and narratives for the period/topic.
        """
        store = self.neo4j_store
        projects = []
        skills = []
        narratives = []

        # Query projects in the period
        cypher = """
        MATCH (p:Project)
        WHERE ($topic = '' OR toLower(p.name) CONTAINS toLower($topic)
               OR toLower(p.description) CONTAINS toLower($topic))
        AND ($period_start = '' OR p.pushed_at >= $period_start)
        AND ($period_end = '' OR p.pushed_at <= $period_end)
        RETURN p.id as id, p.name as name, p.description as description,
               p.pushed_at as pushed_at, p.created_at as created_at
        ORDER BY p.pushed_at DESC
        LIMIT $limit
        """

        try:
            with store.driver.session() as session:
                for record in session.run(cypher, {
                    "topic": topic, "period_start": period_start or "",
                    "period_end": period_end or "", "limit": top_k
                }):
                    projects.append({
                        "id": record["id"],
                        "name": record["name"],
                        "description": record["description"],
                        "pushed_at": record["pushed_at"],
                        "created_at": record["created_at"],
                    })
        except Exception as e:
            logger.warning(f"Career story project query failed: {e}")

        # Gather narratives for those projects
        project_ids = [p["id"] for p in projects]
        if project_ids:
            try:
                with store.driver.session() as session:
                    for pid in project_ids:
                        result = session.run("""
                            MATCH (p:Project {id: $pid})-[:DESCRIBED_BY]->(n:Narrative)
                            RETURN n.text as text, n.period_start as period_start,
                                   n.period_end as period_end
                        """, {"pid": pid}).single()
                        if result:
                            narratives.append({
                                "project_id": pid,
                                "text": result["text"],
                                "period_start": result["period_start"],
                                "period_end": result["period_end"],
                            })
            except Exception as e:
                logger.warning(f"Career story narrative query failed: {e}")

        # Gather skills linked to those projects
        if project_ids:
            try:
                with store.driver.session() as session:
                    result = session.run("""
                        MATCH (p:Project)-[:REQUIRES_SKILL]->(s:Skill)
                        WHERE p.id IN $project_ids
                        RETURN DISTINCT s.name as name, s.category as category
                    """, {"project_ids": project_ids})
                    for record in result:
                        skills.append({"name": record["name"], "category": record["category"]})
            except Exception as e:
                logger.warning(f"Career story skill query failed: {e}")

        return {
            "projects": projects,
            "skills": skills,
            "narratives": narratives,
        }

    def get_skill_evidence(self, skill_name: str,
                            person_id: str = "me") -> List[Dict[str, Any]]:
        """
        Get evidence for a specific skill.

        Args:
            skill_name: Name of the skill
            person_id: Person ID

        Returns:
            List of evidence items
        """
        store = self.neo4j_store
        try:
            with store.driver.session() as session:
                result = session.run("""
                    MATCH (p:Person {id: $person_id})-[r:HAS_SKILL]->(s:Skill)
                    WHERE s.name = $skill_name
                    RETURN r.evidence as evidence,
                           r.confidence as confidence,
                           s.category as category
                """, {"person_id": person_id, "skill_name": skill_name})
                return [record.data() for record in result]
        except Exception as e:
            logger.warning(f"Skill evidence query failed: {e}")
            return []
