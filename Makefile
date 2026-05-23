# ============================================================================
# Graph RAG Resume Agent - Makefile
# ============================================================================
#
# Quick Reference:
#   make help          Show all targets
#   make install       Install dependencies
#   make setup         Create .env from template
#   make run           Start dev server (hot reload)
#   make collect       Run full collection pipeline (streaming, memory-safe)
#   make test          Run all tests
#   make clean         Clean up temp and cache files
#   make docker-build  Build Docker image
#   make deploy-gcp    Deploy to Google Cloud Run
#
# ============================================================================

# ── Defaults ────────────────────────────────────────────────────────────────
PYTHON      := python
PIP         := pip
UVICORN     := uvicorn
DOCKER      := docker
MAX_REPOS   ?= 50
PORT        ?= 8000
HOST        ?= 0.0.0.0
ENV_FILE    ?= .env
.DEFAULT_GOAL := help

# ── Load .env if present ────────────────────────────────────────────────────
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

# ============================================================================
# Help
# ============================================================================
.PHONY: help
help: ## Show this help message
	@echo "Graph RAG Resume Agent - Available Commands"
	@echo "============================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment Variables:"
	@echo "  MAX_REPOS  Number of GitHub repos to collect (default: 50)"
	@echo "  PORT       Server port (default: 8000)"
	@echo "  ENV_FILE   Path to .env file (default: .env)"

# ============================================================================
# Setup & Installation
# ============================================================================
.PHONY: install install-dev setup env

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: install ## Install dev + test extras
	$(PIP) install pytest pytest-asyncio respx

setup: env ## Full setup: create .env then install

env: ## Create .env from .env.example (if it exists)
	@if [ -f .env.example ] && [ ! -f $(ENV_FILE) ]; then \
		echo "Creating $(ENV_FILE) from .env.example..."; \
		cp .env.example $(ENV_FILE); \
		echo "Done! Edit $(ENV_FILE) with your API tokens."; \
	elif [ ! -f .env.example ]; then \
		echo "No .env.example found. Create $(ENV_FILE) manually."; \
	else \
		echo "$(ENV_FILE) already exists."; \
	fi

# ============================================================================
# Development Server
# ============================================================================
.PHONY: run run-dev run-prod

run: run-dev ## Start dev server (hot reload)

run-dev: ## Start FastAPI dev server with hot reload
	$(PYTHON) -m $(UVICORN) app.main:app --reload --host $(HOST) --port $(PORT)

run-prod: ## Start production server (no reload)
	$(PYTHON) -m $(UVICORN) app.main:app --host $(HOST) --port $(PORT)

# ============================================================================
# Data Collection
# ============================================================================
.PHONY: collect collect-clean collect-small

collect: ## Run enhanced collection pipeline (streaming, memory-safe)
	PYTHONPATH=. $(PYTHON) scripts/enhanced_collection.py --max-repos $(MAX_REPOS)

collect-clean: ## Run collection with fresh Neo4j graph
	PYTHONPATH=. $(PYTHON) scripts/enhanced_collection.py --clean --max-repos $(MAX_REPOS)

collect-small: ## Quick collection test (5 repos)
	PYTHONPATH=. $(PYTHON) scripts/enhanced_collection.py --clean --max-repos 5

collect-legacy: ## Run legacy collection pipeline
	PYTHONPATH=. $(PYTHON) scripts/run_collection.py

# ============================================================================
# Knowledge Graph
# ============================================================================
.PHONY: graph-sample graph-stats graph-reset

graph-sample: ## Create sample knowledge graph for testing
	PYTHONPATH=. $(PYTHON) scripts/build_knowledge_graph.py create_sample

graph-stats: ## Show knowledge graph statistics
	PYTHONPATH=. $(PYTHON) -c "\
import os; \
os.environ.pop('NEO4J_URI', None); \
os.environ.pop('NEO4J_USER', None); \
os.environ.pop('NEO4J_PASSWORD', None); \
os.environ.pop('NEO4J_DATABASE', None); \
from app.graph_store.neo4j_store import Neo4jStore, KnowledgeGraphConfig; \
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE; \
s = Neo4jStore(KnowledgeGraphConfig(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, database=NEO4J_DATABASE)); \
s.connect(); \
import json; print(json.dumps(s.get_stats(), indent=2)); \
s.close()"

graph-reset: ## Wipe Neo4j graph completely
	PYTHONPATH=. $(PYTHON) -c "\
import os; \
os.environ.pop('NEO4J_URI', None); \
os.environ.pop('NEO4J_USER', None); \
os.environ.pop('NEO4J_PASSWORD', None); \
os.environ.pop('NEO4J_DATABASE', None); \
from app.graph_store.neo4j_store import Neo4jStore, KnowledgeGraphConfig; \
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE; \
s = Neo4jStore(KnowledgeGraphConfig(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, database=NEO4J_DATABASE)); \
s.connect(); s.clear(); print('Graph cleared'); s.close()"

# ============================================================================
# Ingestion (Direct to Neo4j)
# ============================================================================
.PHONY: ingest ingest-production

ingest: ## Ingest data into Neo4j
	PYTHONPATH=. $(PYTHON) scripts/ingest_to_neo4j.py

ingest-production: ## Production-scale ingestion
	PYTHONPATH=. $(PYTHON) scripts/production_ingest.py

# ============================================================================
# Testing
# ============================================================================
.PHONY: test test-quick test-agent test-integration test-api lint

test: test-quick ## Run all quick tests

test-quick: ## Run agent test suite
	PYTHONPATH=. $(PYTHON) scripts/test_agent.py

test-agent: ## Run agent tests
	PYTHONPATH=. $(PYTHON) scripts/test_agent.py

test-integration: ## Run integration tests
	PYTHONPATH=. $(PYTHON) scripts/test_integration.py

test-api: ## Test NVIDIA API connectivity
	PYTHONPATH=. $(PYTHON) scripts/test_nvidia_api.py

lint: ## Syntax-check all Python files
	@find app scripts -name '*.py' -exec $(PYTHON) -m py_compile {} + && \
		echo "All files pass syntax check"

# ============================================================================
# Validation
# ============================================================================
.PHONY: validate

validate: ## Validate the knowledge graph integrity
	PYTHONPATH=. $(PYTHON) scripts/validate.py

# ============================================================================
# API Queries (curl shortcuts)
# ============================================================================
.PHONY: api-health api-skills api-projects api-query

api-health: ## Check API health
	curl -s http://localhost:$(PORT)/health | $(PYTHON) -m json.tool

api-skills: ## List all skills via API
	curl -s "http://localhost:$(PORT)/skills?min_confidence=0.3" | $(PYTHON) -m json.tool

api-projects: ## List all projects via API
	curl -s http://localhost:$(PORT)/projects | $(PYTHON) -m json.tool

api-query: ## Query the agent (usage: make api-query Q="What are my Python skills?")
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make api-query Q=\"your question here\""; \
	else \
		curl -s -X POST http://localhost:$(PORT)/query \
			-H "Content-Type: application/json" \
			-d "{\"question\": \"$(Q)\", \"top_k\": 5}" | $(PYTHON) -m json.tool; \
	fi

# ============================================================================
# Neo4j Setup
# ============================================================================
.PHONY: neo4j-setup

neo4j-setup: ## Set up local Neo4j indexes and constraints
	PYTHONPATH=. $(PYTHON) scripts/setup_neo4j.py

# ============================================================================
# Cleanup
# ============================================================================
.PHONY: clean clean-all clean-data

clean: ## Remove Python cache and temp files
	@echo "Cleaning Python cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '*.pyo' -delete 2>/dev/null || true
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

clean-data: ## Remove collected data (raw, graph, embeddings)
	@echo "Cleaning data directories..."
	@rm -rf data/raw data/graph data/embeddings 2>/dev/null || true
	@rm -f data/pipeline_results.json data/pipeline_summary.json data/failed_repos.json 2>/dev/null || true
	@echo "Done."

clean-all: clean clean-data ## Full cleanup (cache + data)

# ============================================================================
# Docker
# ============================================================================
.PHONY: docker-build docker-run docker-stop

docker-build: ## Build Docker image
	$(DOCKER) build -t graph-rag-agent:latest .

docker-run: ## Run Docker container locally
	$(DOCKER) run -d --name graph-rag-agent \
		-p $(PORT):8000 \
		--env-file $(ENV_FILE) \
		graph-rag-agent:latest

docker-stop: ## Stop and remove Docker container
	$(DOCKER) stop graph-rag-agent 2>/dev/null || true
	$(DOCKER) rm graph-rag-agent 2>/dev/null || true

# ============================================================================
# Deployment
# ============================================================================
.PHONY: deploy-gcp deploy-vercel

deploy-gcp: ## Deploy to Google Cloud Run
	bash deploy-cloud-run.sh

deploy-vercel: ## Deploy to Vercel
	bash deploy-vercel.sh

# ============================================================================
# Demo
# ============================================================================
.PHONY: demo

demo: ## Run the knowledge graph demo
	PYTHONPATH=. $(PYTHON) scripts/demo_knowledge_graph.py
