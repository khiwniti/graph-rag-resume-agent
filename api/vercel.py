"""
Vercel Serverless Entry Point

This file serves as the entry point for Vercel deployment.
It imports the FastAPI app from app.main and exposes it for serverless execution.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app
from app.main import app

# Export for Vercel
__all__ = ["app"]
