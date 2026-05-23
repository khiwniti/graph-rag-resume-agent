# Knowledge Graph Pipeline for Resume RAG

## Goal
Create a pipeline that ingests data from GitHub, Vercel, and Cloudera into a knowledge graph for Resume Knowledge Graph RAG, then removes local GitHub repository clones after successful ingestion to save disk space.

## Research Summary
- GitHub: Source code repositories requiring cloning and structured data extraction
- Vercel: Hosting platform for web applications; potential data source for UI/components
- Cloudera: Enterprise data platform with potential datasets for enrichment
- Tools identified: Git for cloning, custom extraction scripts, Neo4j for knowledge graph storage, automated cleanup workflows

## Approach
1. Clone GitHub repositories to local storage
2. Extract and normalize code/documentation from all three sources
3. Structure data into graph nodes/edges (classes, functions, relationships)
4. Ingest into Neo4j knowledge graph database
5. Implement automated repository removal post-ingestion
6. Build verification dashboard for RAG functionality

## Subtasks
1. Clone target GitHub repositories to /tmp/repos
   - Expected output: Local repository copies
   - Verification: Directory listing confirms clone completion

2. Develop extraction scripts for:
   - GitHub code files (.py, .js, .md)
   - Vercel deployment artifacts
   - Cloudera datasets
   - Expected output: Normalized JSON/Lucene index files
   - Verification: Sample file processing test

3. Implement graph schema design for code entities
   - Expected output: Neo4j schema definition
   - Verification: Schema validation script passes

4. Build ingestion pipeline with error handling
   - Expected output: Successful Neo4j data load
   - Verification: Database query returns expected structure

5. Create repository cleanup mechanism
   - Expected output: Repo directories removed after ingestion
   - Verification: Disk space monitoring shows reduction

## Deliverables
- /teamspace/studios/this_studio/graph-rag-resume-agent/pipeline.py
- /teamspace/studios/this_studio/graph-rag-resume-agent/extractors/
- /teamspace/studios/this_studio/graph-rag-resume-agent/neo4j_setup.cypher
- /teamspace/studios/this_studio/graph-rag-resume-agent/cleanup.sh

## Evaluation Criteria
- Test accuracy ≥ 90% on sample RAG queries
- Local disk space reduction ≥ 70% post-ingestion
- Zero repository remnants in /tmp/repos after cleanup