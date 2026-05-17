"""Pipeline runner - orchestrates the full Graph RAG collection and build process."""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import (
    DATA_DIR, RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR,
    GITHUB_TOKEN, VERCEL_TOKEN, CLOUDFLARE_TOKEN,
    MAX_REPOS, CONVERSATION_ZIP_PATH
)
from app.collectors.github_collector import GitHubCollector
from app.collectors.vercel_collector import VercelCollector
from app.collectors.cloudflare_collector import CloudflareCollector
from app.collectors.conversation_collector import ConversationCollector
from app.collectors.code_fetcher import CodeFetcher


class GraphRAGPipeline:
    """
    Orchestrates the complete Graph RAG pipeline:
    1. Collect from GitHub, Vercel, Cloudflare, conversations
    2. Normalize and extract evidence
    3. Build knowledge graph
    4. Create vector embeddings
    5. Serve via API
    
    This is the main entry point for running the full pipeline.
    """

    def __init__(self, max_repos: Optional[int] = None):
        """Initialize pipeline with optional repo limit."""
        self.max_repos = max_repos or MAX_REPOS
        self.results: Dict[str, Any] = {
            "stages": {},
            "errors": [],
            "started_at": None,
            "completed_at": None,
        }
        
        # Initialize collectors
        self.github_collector = GitHubCollector()
        self.vercel_collector = VercelCollector()
        self.cloudflare_collector = CloudflareCollector()
        self.conversation_collector = ConversationCollector()
        self.code_fetcher = CodeFetcher(self.github_collector)

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete collection pipeline.
        
        Returns:
            Dict with all collection results and metadata
        """
        print("=" * 60)
        print("Graph RAG Resume Agent - Full Collection Pipeline")
        print("=" * 60)
        
        self.results["started_at"] = datetime.utcnow().isoformat()
        
        # Stage 1: GitHub Collection
        print("\n" + "=" * 60)
        print("Stage 1: GitHub Collection")
        print("=" * 60)
        try:
            github_result = self.github_collector.collect_all(max_repos=self.max_repos)
            self.results["stages"]["github"] = {
                "status": "success",
                "repos_collected": github_result.get("original_repos_count", 0),
                "deep_analyses": len(github_result.get("deep_analyses", [])),
            }
        except Exception as e:
            self.results["stages"]["github"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"GitHub collection failed: {e}")
        
        # Stage 2: Vercel Collection
        print("\n" + "=" * 60)
        print("Stage 2: Vercel Collection")
        print("=" * 60)
        try:
            vercel_result = self.vercel_collector.collect_all()
            self.results["stages"]["vercel"] = {
                "status": "success",
                "projects_collected": vercel_result.get("total_projects", 0),
            }
        except Exception as e:
            self.results["stages"]["vercel"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Vercel collection failed: {e}")
        
        # Stage 3: Cloudflare Collection
        print("\n" + "=" * 60)
        print("Stage 3: Cloudflare Collection")
        print("=" * 60)
        try:
            cloudflare_result = self.cloudflare_collector.collect_all()
            self.results["stages"]["cloudflare"] = {
                "status": "success",
                "workers_count": cloudflare_result.get("workers_count", 0),
                "pages_count": cloudflare_result.get("pages_count", 0),
            }
        except Exception as e:
            self.results["stages"]["cloudflare"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Cloudflare collection failed: {e}")
        
        # Stage 4: Conversation Collection
        print("\n" + "=" * 60)
        print("Stage 4: Conversation Artifact Collection")
        print("=" * 60)
        try:
            conversation_result = self.conversation_collector.collect_all()
            self.results["stages"]["conversation"] = {
                "status": "success",
                "artifacts_found": conversation_result.get("artifact_count", 0),
            }
        except Exception as e:
            self.results["stages"]["conversation"] = {"status": "error", "error": str(e)}
            self.results["errors"].append(f"Conversation collection failed: {e}")
        
        # Save pipeline results
        self.results["completed_at"] = datetime.utcnow().isoformat()
        self._save_pipeline_results()
        
        print("\n" + "=" * 60)
        print("Pipeline Complete")
        print("=" * 60)
        self._print_summary()
        
        return self.results

    def _save_pipeline_results(self):
        """Save pipeline results to disk."""
        results_path = DATA_DIR / "pipeline_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n💾 Pipeline results saved to {results_path}")

    def _print_summary(self):
        """Print pipeline execution summary."""
        print("\n📊 Summary:")
        for stage, result in self.results.get("stages", {}).items():
            status = result.get("status", "unknown")
            if status == "success":
                print(f"  ✓ {stage.capitalize()}: {status}")
            else:
                print(f"  ✗ {stage.capitalize()}: {status} - {result.get('error', '')}")
        
        if self.results.get("errors"):
            print(f"\n⚠️  {len(self.results['errors'])} errors occurred:")
            for error in self.results["errors"]:
                print(f"    - {error}")


def main():
    """Main entry point for pipeline execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Graph RAG collection pipeline")
    parser.add_argument(
        "--max-repos",
        type=int,
        default=0,
        help="Maximum number of repos to collect (0 = all)"
    )
    args = parser.parse_args()
    
    pipeline = GraphRAGPipeline(max_repos=args.max_repos)
    results = pipeline.run_full_pipeline()
    
    # Exit with error code if any stage failed
    has_errors = any(
        stage.get("status") == "error"
        for stage in results.get("stages", {}).values()
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
