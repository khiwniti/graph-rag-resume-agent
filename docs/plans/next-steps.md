# Next Steps Plan - CareerGraph to Graph RAG Integration

## Context
The pre-ingestion pipeline is complete and functional. The Graph RAG API now serves:
- 8 skills (via `/skills` endpoint)
- 46 projects (via `/projects` endpoint)
- Knowledge graph with 97 nodes

## Remaining Tasks

### Task 1: Fix Query Endpoint
**Priority:** HIGH  
**Description:** The `/query` endpoint returns "list index out of range" error. Need to debug and fix the query functionality so users can ask questions like "What are my Python skills?"

**Files involved:**
- `app/agent/resume_agent.py` - query method
- `app/rag/retriever.py` - retrieve method
- `app/graph/query.py` - graph queries

**Success criteria:**
- Query endpoint returns meaningful answers
- No errors when querying with top_k=5
- Response includes answer, skills, evidence, sources, confidence

### Task 2: Add Confidence Field to Graph Skills
**Priority:** MEDIUM  
**Description:** Skills show confidence > 1.0 (e.g., languages: 1.11) which is incorrect. Need to cap confidence at 1.0 or use better calculation.

**Files involved:**
- `app/graph/query.py` - get_skills method
- `scripts/build_graph_from_careergraph.py` - skill node creation

**Success criteria:**
- All confidence values between 0.0 and 1.0
- Confidence correlates with mention_count
- Skills sorted by confidence correctly

### Task 3: Add Repository Data to Graph
**Priority:** MEDIUM  
**Description:** 140 repositories were imported but not all are showing in the graph. Need to ensure repository nodes are properly created with correct properties.

**Files involved:**
- `scripts/build_graph_from_careergraph.py`
- `app/graph/builder.py`

**Success criteria:**
- All 30 processed repos visible in graph
- Repository nodes have correct properties (name, url, description, language)
- Skills extracted from repo languages

### Task 4: Build Vector Embeddings
**Priority:** LOW  
**Description:** The vector store is not loaded (`vector_store_loaded: false`). Need to build FAISS embeddings for RAG retrieval.

**Files involved:**
- `scripts/build_embeddings.py`
- `app/rag/vector_store.py`
- `app/rag/embedder.py`

**Success criteria:**
- Vector store loads successfully
- Health check shows `vector_store_loaded: true`
- Queries use both graph and vector retrieval

### Task 5: Create Integration Test Suite
**Priority:** LOW  
**Description:** Add tests to verify the CareerGraph import pipeline works correctly.

**Files involved:**
- `tests/test_careergraph_import.py` (new file)

**Success criteria:**
- Tests verify export/import/build pipeline
- Tests verify skills and projects endpoints
- Tests verify query functionality

---

## Execution Order
1. Fix Query Endpoint (Task 1) - BLOCKER for core functionality
2. Add Confidence Field (Task 2) - Quality improvement
3. Add Repository Data (Task 3) - Data completeness
4. Build Vector Embeddings (Task 4) - RAG functionality
5. Integration Tests (Task 5) - Quality assurance

## Notes
- Server runs on port 8001
- Data directory: `data/`
- Graph location: `data/graph/knowledge_graph.json`
- CareerGraph data exported to: `data/careergraph_export.json`
