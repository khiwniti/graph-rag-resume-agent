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
from app.schema.graph import UniversalGraph
from app.schema.nodes import NodeType
from app.schema.edges import EdgeType

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

        # Try to find a valid person_id if "me" doesn't return anything
        person_id = "me"
        
        # Check if "me" exists, otherwise use the first person found
        try:
            with self._store.driver.session() as session:
                result = session.run("MATCH (p:Person {id: 'me'}) RETURN p LIMIT 1").single()
                if not result:
                    result = session.run("MATCH (p:Person) RETURN p.id LIMIT 1").single()
                    if result:
                        person_id = result["p.id"]
                        logger.info(f"Using person_id: {person_id}")
        except Exception as e:
            logger.warning(f"Failed to find person: {e}")

        # Try career story retrieval for period/topic queries
        q_lower = question.lower()
        if any(word in q_lower for word in ["career", "story", "timeline", "period", "202", "2023", "2024", "2025"]):
            return self._answer_career_story(question, top_k)

        # Project-focused / HR-style questions: "tell me about X project", "what's about carbonscopes"
        if self._looks_like_project_question(question):
            resp = self._answer_project_overview(question, person_id=person_id, top_k=top_k)
            if resp and resp.answer:
                return resp

        # Standard skill search
        results = self._retriever.retrieve(question, person_id=person_id, top_k=top_k)

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

    def _looks_like_project_question(self, question: str) -> bool:
        q = (question or "").lower()
        if any(k in q for k in [" project", "project ", "repo", "repository", "github"]):
            return True
        if any(k in q for k in ["tell me about", "what's about", "whats about", "overview", "summarize", "summary"]):
            return True
        return False

    def _extract_project_candidates(self, question: str) -> List[str]:
        import re
        q = (question or "").lower()
        words = re.findall(r"[a-z0-9_\-/]{3,}", q)
        stop = {
            "what","whats","what's","about","tell","me","project","repo","repository","github",
            "is","are","was","were","do","does","did","in","on","to","of","a","an","my","your","you",
            "overview","summarize","summary","please","this","that","it","for","with"
        }
        toks = [w for w in words if w not in stop]
        toks.sort(key=len, reverse=True)
        out: List[str] = []
        seen = set()
        for t in toks:
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out[:8]

    def _answer_project_overview(self, question: str, person_id: str = "me", top_k: int = 5) -> AgentResponse:
        """Answer project overview questions with evidence-backed details."""
        candidates = self._extract_project_candidates(question)
        if not candidates or not self._store:
            return AgentResponse(answer="", confidence=0.0)

        project = None
        with self._store.driver.session() as session:
            for c in candidates:
                rec = session.run(
                    "MATCH (p:Project) WHERE toLower(p.name) = $name RETURN p LIMIT 1",
                    {"name": c},
                ).single()
                if rec:
                    project = rec["p"]
                    break
            if not project:
                for c in candidates:
                    rec = session.run(
                        """
                        MATCH (p:Project)
                        WHERE toLower(p.name) CONTAINS $q OR toLower(p.id) CONTAINS $q
                        RETURN p
                        LIMIT 1
                        """,
                        {"q": c},
                    ).single()
                    if rec:
                        project = rec["p"]
                        break

        if not project:
            return AgentResponse(
                answer=f"I couldn't find a project matching '{question}'.",
                confidence=0.0,
            )

        pid = project.get("id", "")
        name = project.get("name", pid)
        url = project.get("url", "")
        description = project.get("description", "")

        proj_skills: List[Dict[str, Any]] = []
        try:
            with self._store.driver.session() as session:
                rows = session.run(
                    """
                    MATCH (p:Project {id: $pid})-[:REQUIRES_SKILL]->(s:Skill)
                    RETURN s.name as name,
                           s.category as category,
                           coalesce(s.confidence, 0.0) as confidence
                    ORDER BY confidence DESC, name ASC
                    LIMIT $limit
                    """,
                    {"pid": pid, "limit": max(12, top_k * 4)},
                )
                for r in rows:
                    proj_skills.append({
                        "skill": r.get("name"),
                        "category": r.get("category") or "skill",
                        "confidence": float(r.get("confidence") or 0.0),
                        "evidence": f"Required by project {name}",
                        "source": "neo4j",
                    })
        except Exception as e:
            logger.debug(f"Project skill lookup failed: {e}")

        # Evidence excerpt from wiki repo page (data/wiki/repos/<owner>--<repo>.md)
        wiki_excerpt = ""
        wiki_rel = ""
        try:
            if pid.startswith("repo:") and "/" in pid.split("repo:", 1)[1]:
                owner_repo = pid.split("repo:", 1)[1]
                owner, repo = owner_repo.split("/", 1)
                wiki_rel = f"repos/{owner}--{repo}.md"
                wiki_path = str((DATA_DIR / "wiki" / wiki_rel))
                if Path(wiki_path).exists():
                    lines = Path(wiki_path).read_text(encoding="utf-8", errors="ignore").splitlines()
                    excerpt_lines: List[str] = []
                    in_info = False
                    in_tech = False
                    tech_count = 0
                    for line in lines:
                        if line.strip() == "## Info":
                            in_info = True
                            in_tech = False
                            excerpt_lines.append("## Info")
                            continue
                        if line.strip() == "## Technologies / Stack":
                            in_info = False
                            in_tech = True
                            excerpt_lines.append("## Technologies / Stack")
                            continue
                        if line.startswith("## ") and line.strip() not in ("## Info", "## Technologies / Stack"):
                            in_info = False
                            in_tech = False
                        if in_info and line.strip():
                            excerpt_lines.append(line)
                        if in_tech and line.strip().startswith("-"):
                            excerpt_lines.append(line)
                            tech_count += 1
                            if tech_count >= 12:
                                in_tech = False
                        if len(excerpt_lines) >= 80:
                            break
                    wiki_excerpt = "\n".join(excerpt_lines).strip()
        except Exception as e:
            logger.debug(f"Wiki excerpt read failed: {e}")

        answer_parts = [f"Project overview: {name}"]
        if description:
            answer_parts.append(description)
        if url:
            answer_parts.append(f"URL: {url}")
        if pid:
            answer_parts.append(f"ID: {pid}")

        if proj_skills:
            answer_parts.append("\nLikely stack / key technologies (from graph edges):")
            for s in proj_skills[:12]:
                answer_parts.append(f"- {s.get('skill')} ({s.get('category')}), confidence {s.get('confidence', 0):.2f}")

        evidence: List[Dict[str, Any]] = []
        sources = ["neo4j"]
        if wiki_excerpt and wiki_rel:
            sources.append("wiki")
            evidence.append({
                "skill_name": name,
                "category": "wiki:repo",
                "confidence": 1.0,
                "source": "wiki",
                "evidence": f"wiki:{wiki_rel}",
                "projects": [pid] if pid else [],
                "score": 1.0,
                "snippet": wiki_excerpt,
            })

        if wiki_excerpt:
            answer_parts.append("\nEvidence excerpt (wiki):")
            answer_parts.append(wiki_excerpt)

        return AgentResponse(
            answer="\n".join(answer_parts),
            skills=proj_skills[:top_k] if proj_skills else [],
            evidence=evidence,
            sources=list(dict.fromkeys(sources)),
            confidence=0.9 if (proj_skills or wiki_excerpt) else 0.6,
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
        # Preferred path: Neo4j-backed skills (fallback to JSON if Neo4j is empty)
        if self._ensure_connection():
            skills = self._store.get_person_skills("me")
            filtered = [s for s in skills if s.get("confidence", 0) >= min_confidence]
            filtered.sort(key=lambda s: s.get("confidence", 0), reverse=True)
            if filtered:
                return [
                    {
                        "skill": s["name"],
                        "category": s["category"],
                        "confidence": s.get("confidence", 0),
                        "evidence": s.get("evidence", ""),
                    }
                    for s in filtered
                ]
            logger.info("Neo4j returned 0 skills; falling back to JSON graph")

        # Fallback path: universal graph JSON (data/graph/knowledge_graph.json)
        try:
            g = UniversalGraph.load_json(self.graph_path)
        except Exception as e:
            logger.warning(f"list_skills fallback failed to load graph JSON: {e}")
            return []

        # Count usage: repo -> technology edges
        uses_counts: Dict[str, int] = {}
        for e in g.edges.values():
            if e.type == EdgeType.USES:
                uses_counts[e.target] = uses_counts.get(e.target, 0) + 1

        out: List[Dict[str, Any]] = []
        for n in g.nodes.values():
            if n.type != NodeType.TECHNOLOGY:
                continue
            conf = float(n.confidence or 0.0)
            if conf < min_confidence:
                continue
            count = uses_counts.get(n.id, 0)
            out.append({
                "skill": n.label,
                "category": n.id,
                "confidence": conf,
                "evidence": f"Used in {count} projects" if count else "",
            })

        out.sort(key=lambda s: (s.get("confidence", 0), uses_counts.get(s.get("category", ""), 0)), reverse=True)
        return out

    def get_skill_evidence(self, skill_name: str) -> List[Dict[str, Any]]:
        """Get evidence for a specific skill."""
        if not self._ensure_connection():
            return []

        return self._retriever.get_skill_evidence(skill_name, person_id="me")

    def get_projects(self) -> List[Dict[str, Any]]:
        """List all projects from the knowledge graph."""
        # Preferred path: Neo4j-backed projects (fallback to JSON if Neo4j is empty)
        if self._ensure_connection():
            query = """
            MATCH (p:Project)
            RETURN p.id as id, p.name as name, p.description as description,
                   p.source as source, p.url as url, p.pushed_at as pushed_at
            ORDER BY p.pushed_at DESC
            """
            try:
                with self._store.driver.session() as session:
                    result = session.run(query)
                    rows = [record.data() for record in result]
                    if rows:
                        return rows
                    logger.info("Neo4j returned 0 projects; falling back to JSON graph")
            except Exception as e:
                logger.warning(f"Failed to get projects from Neo4j: {e}")
                # fall through to JSON

        # Fallback path: universal graph JSON
        try:
            g = UniversalGraph.load_json(self.graph_path)
        except Exception as e:
            logger.warning(f"get_projects fallback failed to load graph JSON: {e}")
            return []

        projects: List[Dict[str, Any]] = []
        for n in g.nodes.values():
            if n.type not in (NodeType.REPO, NodeType.DEPLOYMENT):
                continue
            props = n.properties or {}
            projects.append({
                "id": n.id,
                "name": n.label,
                "description": props.get("description") or props.get("summary") or "",
                "source": n.provider or ("github" if n.type == NodeType.REPO else "deployment"),
                "url": props.get("url") or props.get("html_url") or props.get("production_url") or "",
                "pushed_at": props.get("pushed_at") or props.get("updated_at") or props.get("updated") or "",
            })

        projects.sort(key=lambda p: p.get("pushed_at") or "", reverse=True)
        return projects
