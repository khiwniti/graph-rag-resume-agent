#!/usr/bin/env python3
"""
Production-ready server for Graph RAG Resume Agent.
Includes proper error handling, logging, and health checks.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Verify dependencies
try:
    import sentence_transformers
    import faiss
    import numpy as np
    from fastapi import FastAPI
    import uvicorn
    logger.info("✅ All dependencies loaded successfully")
except ImportError as e:
    logger.error(f"❌ Missing dependency: {e}")
    logger.error("Install with: pip install sentence-transformers faiss-cpu numpy fastapi uvicorn")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Verify graph exists
GRAPH_PATH = project_root / "data" / "graph" / "knowledge_graph.json"
if not GRAPH_PATH.exists():
    logger.warning(f"⚠️  Graph file not found at {GRAPH_PATH}")
    logger.warning("Run: python scripts/build_graph_simple.py first")
else:
    logger.info(f"✅ Graph file found: {GRAPH_PATH}")

# Import and create app
from app.main import app as fastapi_app

def create_production_app() -> FastAPI:
    """Create and configure the production FastAPI application."""
    
    # Add startup event
    @fastapi_app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Starting Graph RAG Resume Agent API")
        logger.info(f"Graph path: {GRAPH_PATH}")
        
        # Verify graph can be loaded
        try:
            from app.graph.builder import GraphBuilder
            builder = GraphBuilder()
            if builder.load_from_json(str(GRAPH_PATH)):
                logger.info(f"✅ Graph loaded successfully: {builder.get_stats()}")
            else:
                logger.error("❌ Failed to load graph")
        except Exception as e:
            logger.error(f"❌ Error loading graph: {e}")
    
    return fastapi_app

def main():
    """Run the production server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    logger.info(f"📖 Interactive docs: http://{host}:{port}/docs")
    logger.info(f"📋 ReDoc: http://{host}:{port}/redoc")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
