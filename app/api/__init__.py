"""HTTP route modules — registered by app.main."""
from .mcp_context import router as mcp_router

__all__ = ["mcp_router"]
