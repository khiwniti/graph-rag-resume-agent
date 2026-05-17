"""Cloudflare data normalizer - converts raw Cloudflare collector output to normalized format."""
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.models.schemas import CloudflareResource, SourceFileEvidence


class CloudflareNormalizer:
    """
    Normalizes raw Cloudflare collector data into structured formats for graph building.
    
    Converts raw JSON from CloudflareCollector into:
    - CloudflareResource objects
    - SourceFileEvidence for Worker code
    - Normalized infrastructure metadata
    """

    def __init__(self):
        pass

    def normalize_worker(
        self,
        worker_data: Dict[str, Any],
        account_id: str = ""
    ) -> CloudflareResource:
        """
        Normalize a Cloudflare Worker's data.
        
        Args:
            worker_data: Raw dict from CloudflareCollector.analyze_worker_deep()
            account_id: Cloudflare account ID
            
        Returns:
            CloudflareResource object
        """
        return CloudflareResource(
            resource_type="worker",
            resource_id=worker_data.get("script_id", ""),
            resource_name=worker_data.get("script_id", ""),
            bindings=worker_data.get("bindings", []),
            source_code_preview=worker_data.get("source_code_preview", ""),
            detected_patterns=worker_data.get("detected_api_patterns", []),
            created_at=worker_data.get("created_on", ""),
            modified_at=worker_data.get("modified_on", ""),
        )

    def normalize_pages(
        self,
        pages_data: Dict[str, Any]
    ) -> CloudflareResource:
        """
        Normalize a Cloudflare Pages project.
        
        Args:
            pages_data: Raw dict from CloudflareCollector
            
        Returns:
            CloudflareResource object
        """
        return CloudflareResource(
            resource_type="pages",
            resource_id=pages_data.get("name", ""),
            resource_name=pages_data.get("name", ""),
            bindings=[],
            source_code_preview="",
            detected_patterns=[],
            created_at=pages_data.get("created_on", ""),
            modified_at="",
        )

    def normalize_kv_namespace(
        self,
        kv_data: Dict[str, Any]
    ) -> CloudflareResource:
        """Normalize a KV namespace."""
        return CloudflareResource(
            resource_type="kv",
            resource_id=kv_data.get("id", ""),
            resource_name=kv_data.get("title", ""),
            bindings=[],
            source_code_preview="",
            detected_patterns=[],
            created_at=kv_data.get("created_on", ""),
            modified_at=kv_data.get("modified_on", ""),
        )

    def normalize_d1_database(
        self,
        d1_data: Dict[str, Any]
    ) -> CloudflareResource:
        """Normalize a D1 database."""
        return CloudflareResource(
            resource_type="d1",
            resource_id=d1_data.get("uuid", ""),
            resource_name=d1_data.get("name", ""),
            bindings=[],
            source_code_preview="",
            detected_patterns=[],
            created_at=d1_data.get("created_at", ""),
            modified_at=d1_data.get("created_at", ""),
        )

    def normalize_r2_bucket(
        self,
        r2_data: Dict[str, Any]
    ) -> CloudflareResource:
        """Normalize an R2 bucket."""
        return CloudflareResource(
            resource_type="r2",
            resource_id=r2_data.get("name", ""),
            resource_name=r2_data.get("name", ""),
            bindings=[],
            source_code_preview="",
            detected_patterns=[],
            created_at=r2_data.get("created", ""),
            modified_at=r2_data.get("created", ""),
        )

    def extract_worker_evidence(
        self,
        worker_data: Dict[str, Any]
    ) -> Optional[SourceFileEvidence]:
        """
        Extract SourceFileEvidence from Worker source code.
        
        Args:
            worker_data: Raw Worker data with source code
            
        Returns:
            SourceFileEvidence or None if no source
        """
        source_code = worker_data.get("source_code_preview", "")
        if not source_code:
            return None
        
        script_id = worker_data.get("script_id", "")
        
        # Detect concepts in Worker code
        detected_concepts = self._detect_worker_concepts(source_code)
        
        return SourceFileEvidence(
            file_path=f"workers/{script_id}.js",
            repo_name="",
            project_name=script_id,
            source_system="cloudflare",
            file_type="source",
            content_preview=source_code[:500],
            content_hash=hashlib.sha256(source_code.encode()).hexdigest()[:16],
            detected_concepts=detected_concepts,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _detect_worker_concepts(self, source_code: str) -> List[str]:
        """Detect concepts in Worker source code."""
        concepts = []
        code_lower = source_code.lower()
        
        # Framework detection
        if "hono" in code_lower:
            concepts.append("hono")
        if "itty-router" in code_lower or "Router()" in source_code:
            concepts.append("itty-router")
        
        # API patterns
        if "fetch(" in source_code:
            concepts.append("fetch_api")
        if "new Request(" in source_code:
            concepts.append("request_api")
        if "new Response(" in source_code:
            concepts.append("response_api")
        
        # Bindings
        if "KV" in source_code or ".kv." in code_lower:
            concepts.append("kv_binding")
        if "D1" in source_code or ".d1." in code_lower:
            concepts.append("d1_binding")
        if "R2" in source_code or ".r2." in code_lower:
            concepts.append("r2_binding")
        
        # Patterns
        if "addEventListener" in source_code:
            concepts.append("worker_event_listener")
        if "export default" in source_code:
            concepts.append("esm_export")
        if "cron(" in source_code:
            concepts.append("scheduled_worker")
        
        return list(set(concepts))

    def normalize_collection_results(
        self,
        collection_result: Dict[str, Any]
    ) -> Dict[str, List[CloudflareResource]]:
        """
        Normalize entire Cloudflare collection results.
        
        Args:
            collection_result: Raw result from CloudflareCollector.collect_all()
            
        Returns:
            Dict with categorized resources
        """
        resources = {
            "workers": [],
            "pages": [],
            "kv": [],
            "d1": [],
            "r2": [],
            "durable_objects": [],
            "queues": [],
            "zones": [],
        }
        
        # Normalize workers
        worker_analyses = collection_result.get("worker_analyses", [])
        for worker_data in worker_analyses:
            try:
                resource = self.normalize_worker(worker_data)
                resources["workers"].append(resource)
            except Exception as e:
                print(f"⚠️ Error normalizing worker: {e}")
        
        # Normalize Pages
        pages_analyses = collection_result.get("pages_analyses", [])
        for pages_data in pages_analyses:
            try:
                resource = self.normalize_pages(pages_data)
                resources["pages"].append(resource)
            except Exception as e:
                print(f"⚠️ Error normalizing Pages: {e}")
        
        # Normalize KV
        kv_namespaces = collection_result.get("kv_namespaces", [])
        for kv_data in kv_namespaces:
            try:
                resource = self.normalize_kv_namespace(kv_data)
                resources["kv"].append(resource)
            except Exception as e:
                print(f"⚠️ Error normalizing KV: {e}")
        
        # Normalize D1
        d1_databases = collection_result.get("d1_databases", [])
        for d1_data in d1_databases:
            try:
                resource = self.normalize_d1_database(d1_data)
                resources["d1"].append(resource)
            except Exception as e:
                print(f"⚠️ Error normalizing D1: {e}")
        
        # Normalize R2
        r2_buckets = collection_result.get("r2_buckets", [])
        for r2_data in r2_buckets:
            try:
                resource = self.normalize_r2_bucket(r2_data)
                resources["r2"].append(resource)
            except Exception as e:
                print(f"⚠️ Error normalizing R2: {e}")
        
        return resources
