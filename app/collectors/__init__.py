"""Collector modules for Graph RAG Resume Agent"""
import logging
_log = logging.getLogger(__name__)

_COLLECTOR_IMPORT_ERRORS = []

try:
    from .github_collector import GitHubCollector
except Exception as e:
    GitHubCollector = None  # type: ignore
    _COLLECTOR_IMPORT_ERRORS.append(f"github_collector: {e}")

try:
    from .vercel_collector import VercelCollector
except Exception as e:
    VercelCollector = None  # type: ignore
    _COLLECTOR_IMPORT_ERRORS.append(f"vercel_collector: {e}")

try:
    from .cloudflare_collector import CloudflareCollector
except Exception as e:
    CloudflareCollector = None  # type: ignore
    _COLLECTOR_IMPORT_ERRORS.append(f"cloudflare_collector: {e}")

try:
    from .code_fetcher import CodeFetcher
except Exception as e:
    CodeFetcher = None  # type: ignore
    _COLLECTOR_IMPORT_ERRORS.append(f"code_fetcher: {e}")

if _COLLECTOR_IMPORT_ERRORS:
    _log.warning("Some collectors failed to load (non-fatal): %s", "; ".join(_COLLECTOR_IMPORT_ERRORS), exc_info=True)