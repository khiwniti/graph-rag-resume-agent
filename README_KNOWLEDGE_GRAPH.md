# Knowledge Graph Setup Guide

This guide will help you set up and use the Neo4j-based knowledge graph for the Resume RAG system.

## Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set Up Neo4j

**Option A: Using Docker (Recommended)**

```bash
# Start Neo4j container
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5-community
```

Wait 30 seconds for Neo4j to start.

**Option B: Neo4j Desktop**

1. Download from: https://neo4j.com/download/
2. Install and create a new DBMS
3. Set password: `password`
4. Start the database

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Data sources (add your tokens)
GITHUB_TOKEN=ghp_your_token_here
VERCEL_TOKEN=vcp_your_token_here
CLOUDFLARE_TOKEN=cfat_your_token_here
CLOUDFLARE_ACCOUNT_ID=your_account_id
```

### Step 4: Test Connection

```bash
python scripts/build_knowledge_graph.py stats
```

### Step 5: Create Sample Graph

```bash
python scripts/build_knowledge_graph.py create_sample
```

## Usage Examples

### Query Skills

```bash
python scripts/build_knowledge_graph.py query --person-id me
```

### Clear Graph

```bash
python scripts/build_knowledge_graph.py clear
```

## Python API Usage

### Basic Example

```python
from app.graph_store import Neo4jStore, KnowledgeGraphConfig, KnowledgeGraphBuilder

# Configure connection
config = KnowledgeGraphConfig(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Create graph builder
builder = KnowledgeGraphBuilder(config)
builder.initialize_schema()

# Add a person
builder.store.upsert_person(
    person_id="me",
    name="John Doe",
    email="john@example.com"
)

# Add a project
builder.store.upsert_project(
    project_id="github:myproject",
    name="My Project",
    source="github",
    url="https://github.com/user/myproject"
)

# Add skills
builder.store.upsert_skill("Python", "language", confidence=0.95)
builder.store.upsert_skill("FastAPI", "framework", confidence=0.85)

# Link person to project
builder.store.link_person_to_project("me", "github:myproject")

# Link person to skills
builder.store.link_person_to_skill("me", "Python", "language", confidence=0.95)
builder.store.link_person_to_skill("me", "FastAPI", "framework", confidence=0.85)

# Query skills
skills = builder.store.get_person_skills("me")
for skill in skills:
    print(f"{skill['name']}: {skill['confidence']}")

# Get stats
stats = builder.store.get_stats()
print(stats)

builder.close()
```

### Extract Skills from Code

```python
from app.extractors import SkillExtractor, DependencyParser, SourceAnalyzer

# Extract skills from a file
extractor = SkillExtractor()
skills = extractor.extract_from_file("app/main.py", open("app/main.py").read())

for skill in skills:
    print(f"Skill: {skill.name} ({skill.category})")
    print(f"Confidence: {skill.confidence}")
    print(f"Evidence: {skill.evidence}")

# Parse dependencies
parser = DependencyParser()
deps = parser.parse_file("requirements.txt")

for dep in deps:
    print(f"Dependency: {dep.name} ({dep.version})")
```

### Build Graph from Collection

```python
from app.graph_store import KnowledgeGraphBuilder, KnowledgeGraphConfig
from app.collectors.github_collector import GitHubCollector

config = KnowledgeGraphConfig(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

builder = KnowledgeGraphBuilder(config)
builder.initialize_schema()

# Collect GitHub data
collector = GitHubCollector()
github_data = collector.collect_all(max_repos=5)

# Build graph from collection
stats = builder.build_from_collection(github_data)
print(f"Built graph: {stats}")

builder.close()
```

## Neo4j Browser

Access Neo4j Browser at: http://localhost:7474

Default credentials:
- Username: `neo4j`
- Password: `password`

### Useful Cypher Queries

```cypher
// Get all skills for a person
MATCH (p:Person {id: "me"})-[r:HAS_SKILL]->(s:Skill)
RETURN s.name, s.category, r.confidence
ORDER BY r.confidence DESC;

// Get project skills
MATCH (p:Project {id: "github:myproject"})-[:REQUIRES_SKILL]->(s:Skill)
RETURN s.name, s.category;

// Graph statistics
MATCH (n)
RETURN labels(n) as type, count(*) as count
GROUP BY labels(n);

// Find related skills
MATCH (p:Person {id: "me"})-[:HAS_SKILL]->(s:Skill)
<-[:REQUIRES_SKILL]-(proj:Project)
-[:REQUIRES_SKILL]->(related:Skill)
RETURN related.name, related.category, count(*) as frequency
ORDER BY frequency DESC;

// Clear graph
MATCH (n) DETACH DELETE n;
```

## Troubleshooting

### Connection Failed

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs neo4j

# Restart container
docker restart neo4j
```

### Authentication Error

Make sure your password in `.env` matches the one set in Neo4j.

### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## Next Steps

1. **Add your data sources** - Configure GitHub, Vercel, Cloudflare tokens
2. **Run collection** - `python scripts/run_collection.py`
3. **Build graph** - Skills will be automatically extracted
4. **Query via API** - Use FastAPI endpoints at `/docs`
