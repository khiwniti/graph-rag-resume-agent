# Graph RAG + MCP UI Integration

## Overview

This document describes how to integrate the Graph RAG Resume Agent with the MCP UI knowledge graph system for AI agent orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Graph RAG (Evidence Layer)                                     │
│  - Knowledge Graph: Skills, Projects, Companies, Domains       │
│  - Vector Store: FAISS embeddings for semantic search          │
│  - Evidence: Links to GitHub, Vercel, Cloudflare artifacts     │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ MCP Tool: query_knowledge_graph()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP Server (Orchestration Layer)                               │
│  - LangGraph Supervisor coordinates expert agents              │
│  - Each agent queries Graph RAG for section-specific data      │
│  - Agents rewrite resume sections with evidence-backed claims  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ Widget Protocol
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP UI (Presentation Layer)                                    │
│  - Resume Tab: Section cards with AI redesign                  │
│  - Agents Tab: Expert agent status and activity feed           │
│  - Graph Tab: Knowledge graph visualization                    │
│  - Schedule Tab: Automated redesign configuration              │
└─────────────────────────────────────────────────────────────────┘
```

## Knowledge Graph Schema

The Graph RAG knowledge graph uses this schema:

```typescript
interface KGNode {
  id: string;
  type: "person" | "skill" | "project" | "company" | "domain" | "tech";
  label: string;
  weight: number;      // 0-10 importance/relevance
  color?: string;      // Hex color for visualization
  confidence?: number; // 0-1 evidence-backed confidence
}

interface KGEdge {
  from: string;
  to: string;
  label: string;       // e.g., "USES_SKILL", "DEMONSTRATES", "BELONGS_TO"
  weight: number;      // 0-10 relationship strength
}
```

## MCP Tools

The Graph RAG MCP server exposes these tools:

### 1. `query_knowledge_graph`

Query the knowledge graph for nodes and edges.

```typescript
// Tool schema
{
  name: "query_knowledge_graph",
  description: "Query the resume knowledge graph",
  schema: z.object({
    node_type: z.enum(["person", "skill", "project", "company", "domain", "tech", "all"]),
    query: z.string().optional(), // Text search
  })
}
```

**Example usage:**
```typescript
// Get all skills
const skills = await query_knowledge_graph({ node_type: "skill" });

// Search for Python-related nodes
const pythonNodes = await query_knowledge_graph({ 
  node_type: "all", 
  query: "Python" 
});
```

### 2. `get_skill_evidence`

Get evidence-backed details for a specific skill.

```typescript
// Tool schema
{
  name: "get_skill_evidence",
  description: "Get evidence for a skill claim",
  schema: z.object({
    skill_name: z.string(),
  })
}
```

**Response:**
```json
{
  "skill": "FastAPI",
  "confidence": 0.92,
  "evidence": [
    { "type": "file", "path": "app/main.py", "repo": "graph-rag-resume-agent" },
    { "type": "dependency", "name": "fastapi>=0.104.0", "file": "requirements.txt" }
  ],
  "projects_using": ["graph-rag-resume-agent", "bitebase-api"]
}
```

### 3. `list_projects`

List all projects with metadata.

```typescript
// Tool schema
{
  name: "list_projects",
  description: "List all projects in the knowledge graph",
  schema: z.object({
    domain: z.string().optional(), // Filter by domain
    min_confidence: z.number().optional(),
  })
}
```

## Expert Agent Configuration

Each expert agent queries the knowledge graph for its section:

| Agent | Graph Query | Purpose |
|-------|-------------|---------|
| Profile Expert | `query_knowledge_graph({ node_type: "person" })` | Get person node, companies worked at |
| Summary Expert | `query_knowledge_graph({ node_type: "skill" })` + domains | Get top skills and domains for narrative |
| Experience Expert | `query_knowledge_graph({ node_type: "company" })` + projects | Get work history and roles |
| Projects Expert | `query_knowledge_graph({ node_type: "project" })` | Get project list with evidence |
| Skills Expert | `query_knowledge_graph({ node_type: "skill" })` | Get skills with confidence scores |
| Education Expert | `query_knowledge_graph({ node_type: "company" })` (universities) | Get education background |

## Integration Steps

### Step 1: Expose Graph RAG as MCP Server

```python
# app/mcp_server.py
from mcp.server.fastmcp import FastMCP
from app.graph.query import GraphQuerier

mcp = FastMCP("Graph RAG Resume Agent")
querier = GraphQuerier()

@mcp.tool()
def query_knowledge_graph(node_type: str = "all", query: str = None):
    """Query the knowledge graph."""
    nodes = querier.get_nodes_by_type(node_type)
    if query:
        nodes = [n for n in nodes if query.lower() in n.get("label", "").lower()]
    return {"nodes": nodes, "total": len(nodes)}

@mcp.tool()
def get_skill_evidence(skill_name: str):
    """Get evidence for a skill."""
    skill = querier.get_skill(skill_name)
    return skill

@mcp.tool()
def list_projects(domain: str = None, min_confidence: float = 0.0):
    """List all projects."""
    projects = querier.get_projects()
    if domain:
        projects = [p for p in projects if domain in p.get("domain", [])]
    return {"projects": projects, "total": len(projects)}
```

### Step 2: Update MCP UI to use Graph RAG tools

The MCP UI (`resume-mcp-ui/index.ts`) already has the knowledge graph hardcoded. Replace it with live data:

```typescript
// Before: hardcoded graph
const knowledgeGraph = { nodes: [...], edges: [...] };

// After: fetch from Graph RAG MCP server
const [knowledgeGraph, setKnowledgeGraph] = useState<KGData>({ nodes: [], edges: [] });

useEffect(() => {
  const fetchGraph = async () => {
    const result = await callTool("query_knowledge_graph", { node_type: "all" });
    setKnowledgeGraph(result);
  };
  fetchGraph();
}, []);
```

### Step 3: Agent prompts reference the graph

Update agent system prompts to query the graph:

```typescript
const EXPERT_AGENTS = {
  summary: {
    name: "Summary Expert",
    systemPrompt: `You are a professional resume writer.
    
    IMPORTANT: Before writing the summary, query the knowledge graph:
    1. Get all skills: query_knowledge_graph({ node_type: "skill" })
    2. Get domains: query_knowledge_graph({ node_type: "domain" })
    3. Get top projects: list_projects({ min_confidence: 0.7 })
    
    Use this data to craft a summary that highlights:
    - The person's core expertise (from skill nodes with high confidence)
    - Domain expertise (from domain nodes)
    - Impact projects (from project nodes with evidence)
    
    Current content: {currentContent}
    Knowledge graph: {graphData}
    `,
  },
  // ... other agents
};
```

## Metadata Extraction for Graph Size Reduction

To reduce graph size by 90%+, use the metadata extractor:

```bash
# Extract metadata from raw GitHub/Vercel/Cloudflare data
python scripts/extract_metadata.py

# Output: data/metadata/extracted_metadata.json
# This file contains condensed, hiring-manager-focused metadata
```

The extractor produces:
```json
{
  "projects": [
    {
      "name": "BiteBase Intelligence",
      "source_type": "github",
      "project_type": "fullstack",
      "domain": ["geospatial", "analytics", "ai"],
      "problem_statement": "Restaurant owners need location-based insights...",
      "primary_stack": ["Next.js", "FastAPI", "PostgreSQL"],
      "skills_demonstrated": ["React", "Python", "Geospatial Analysis"],
      "evidence_count": 47,
      "confidence": 0.92
    }
  ]
}
```

## Neo4j Integration (Optional)

For persistent graph storage:

```python
# app/graph/neo4j_store.py
from neo4j import GraphDatabase

class Neo4jStore:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def store_project(self, project: dict):
        with self.driver.session() as session:
            session.execute_write(self._create_project, project)
    
    @staticmethod
    def _create_project(tx, project):
        query = """
        MERGE (p:Project {name: $name})
        SET p.type = $project_type,
            p.domain = $domain,
            p.primary_stack = $primary_stack,
            p.evidence_count = $evidence_count,
            p.confidence = $confidence
        RETURN p
        """
        tx.run(query, project)
    
    def query_skills(self):
        with self.driver.session() as session:
            result = session.run("MATCH (s:Skill) RETURN s")
            return [record["s"] for record in result]
```

## Testing the Integration

```bash
# 1. Start Graph RAG backend
python app_gradio.py

# 2. Start MCP server
cd resume-mcp-ui
npm run dev

# 3. Test tools
curl http://localhost:3000/tools/query_knowledge_graph \
  -H "Content-Type: application/json" \
  -d '{"node_type": "skill"}'
```

## Deployment

### Hugging Face Spaces (Graph RAG)
```bash
python scripts/deploy_hf.py --repo-id getintheq/graph-rag-resume-agent
```

### Vercel (MCP UI)
```bash
cd resume-mcp-ui
npm run deploy
```

## Security Notes

- Authenticate MCP tools with API keys
- Rate limit graph queries
- Sanitize user input before graph queries
- Use private graph data for sensitive info
