"""
FastAPI server entry point.
Run with: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Or: python scripts/run_server.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
