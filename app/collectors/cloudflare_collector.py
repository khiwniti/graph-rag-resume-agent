"""Deep Cloudflare collector - extracts Workers code, Pages, KV, D1, domains, DNS."""
import json
import time
import re
from pathlib import Path
from typing import Optional

import httpx

from app.config import CLOUDFLARE_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API, RAW_DIR


class CloudflareCollector:
    """Collects deep data from Cloudflare: Workers code, Pages, KV, D1, domains."""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(headers=self.headers, timeout=30.0)
        self.account_id = CLOUDFLARE_ACCOUNT_ID
        self.base = f"{CLOUDFLARE_API}/accounts/{self.account_id}"
        self.cache_dir = RAW_DIR / "cloudflare"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Workers Scripts (with code) ───────────────────────────────

    def get_workers(self) -> list[dict]:
        r = self.client.get(f"{self.base}/workers/scripts")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    def get_worker_detail(self, script_id: str) -> Optional[dict]:
        """Get worker metadata including bindings."""
        r = self.client.get(f"{self.base}/workers/scripts/{script_id}")
        if r.status_code == 200:
            return r.json().get("result", {})
        return None

    def get_worker_source(self, script_id: str) -> str:
        """Download actual worker source code."""
        r = self.client.get(f"{self.base}/workers/scripts/{script_id}/content")
        if r.status_code == 200:
            return r.text
        return ""

    # ── Workers KV Namespaces ─────────────────────────────────────

    def get_kv_namespaces(self) -> list[dict]:
        r = self.client.get(f"{self.base}/storage/kv/namespaces")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── D1 Databases ──────────────────────────────────────────────

    def get_d1_databases(self) -> list[dict]:
        r = self.client.get(f"{self.base}/d1/database")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── Pages Projects ────────────────────────────────────────────

    def get_pages_projects(self) -> list[dict]:
        r = self.client.get(f"{self.base}/pages/projects")
        if r.status_code == 200:
            data = r.json()
            return data.get("result", [])
        return []

    def get_pages_project_detail(self, project_name: str) -> Optional[dict]:
        r = self.client.get(f"{self.base}/pages/projects/{project_name}")
        if r.status_code == 200:
            return r.json().get("result", {})
        return None

    # ── Domains / Zones ───────────────────────────────────────────

    def get_zones(self) -> list[dict]:
        r = self.client.get(f"{CLOUDFLARE_API}/zones", params={"per_page": 100})
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    def get_zone_dns_records(self, zone_id: str) -> list[dict]:
        r = self.client.get(
            f"{CLOUDFLARE_API}/zones/{zone_id}/dns_records",
            params={"per_page": 50},
        )
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── R2 Buckets ────────────────────────────────────────────────

    def get_r2_buckets(self) -> list[dict]:
        r = self.client.get(f"{self.base}/r2/buckets")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── Durable Objects ───────────────────────────────────────────

    def get_durable_objects(self) -> list[dict]:
        r = self.client.get(f"{self.base}/workers/durable-objects/namespaces")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── Queues ────────────────────────────────────────────────────

    def get_queues(self) -> list[dict]:
        r = self.client.get(f"{self.base}/workers/queues")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    # ── Deep Worker Analysis ──────────────────────────────────────

    def analyze_worker_deep(self, script_id: str) -> dict:
        """Deep analysis of a Cloudflare Worker: source code, bindings, metadata."""
        print(f"  🔍 Analyzing Worker: {script_id} ...")

        # Get metadata
        detail = self.get_worker_detail(script_id) or {}

        # Get actual source code
        source_code = self.get_worker_source(script_id)
        source_preview = source_code[:5000] if source_code else ""

        # Parse bindings
        bindings = detail.get("bindings", []) or []
        binding_summary = []
        for b in bindings:
            binding_summary.append({
                "name": b.get("name", ""),
                "type": b.get("type", ""),  # KV, D1, R2, secret, var, etc.
            })

        # Detect patterns from source code
        detected_imports = []
        detected_apis = []
        if source_code:
            # Import detection
            import_matches = re.findall(r'import\s+.*?from\s+["\']([^"\']+)["\']', source_code)
            detected_imports = list(set(import_matches))[:20]

            # API pattern detection
            api_patterns = [
                r'fetch\(', r'new Request\(', r'new Response\(',
                r'c\.env\.', r'env\.', r'KV\.', r'D1\.',
                r'Hono', r'itty\s*Router', r'Router',
            ]
            for pattern in api_patterns:
                if re.search(pattern, source_code):
                    detected_apis.append(pattern.replace(r'\\', '').replace(r'\.', '.'))

        # Modifying properties
        modified = detail.get("modified_on", "")
        created = detail.get("created_on", "")

        analysis = {
            "script_id": script_id,
            "source_code_preview": source_preview,
            "source_code_length": len(source_code),
            "has_source": bool(source_code),
            "bindings": binding_summary,
            "binding_types": list(set(b.get("type", "") for b in binding_summary)),
            "detected_imports": detected_imports,
            "detected_api_patterns": detected_apis,
            "modified_on": modified,
            "created_on": created,
        }

        time.sleep(0.3)
        return analysis

    # ── Full Collection Pipeline ──────────────────────────────────

    def collect_all(self) -> dict:
        """Run full Cloudflare collection."""
        print("☁️ Fetching Cloudflare account info...")
        accounts = self._get_accounts()

        print("⚡ Fetching Workers scripts...")
        workers = self.get_workers()
        print(f"   Found {len(workers)} Workers")

        print("📄 Fetching Pages projects...")
        pages = self.get_pages_projects()
        print(f"   Found {len(pages)} Pages projects")

        print("🌐 Fetching zones/domains...")
        zones = self.get_zones()
        print(f"   Found {len(zones)} zones")

        print("💾 Fetching KV namespaces...")
        kv = self.get_kv_namespaces()

        print("🗄️ Fetching D1 databases...")
        d1 = self.get_d1_databases()

        print("🪣 Fetching R2 buckets...")
        r2 = self.get_r2_buckets()

        print("📦 Fetching Durable Objects...")
        durable = self.get_durable_objects()

        print("📬 Fetching Queues...")
        queues = self.get_queues()

        # Deep worker analysis
        print(f"🔧 Deep analyzing {len(workers)} Workers...")
        worker_analyses = []
        for i, w in enumerate(workers):
            sid = w.get("id", "")
            print(f"  [{i+1}/{len(workers)}]", end="")
            try:
                analysis = self.analyze_worker_deep(sid)
                worker_analyses.append(analysis)
            except Exception as e:
                print(f"  ⚠️ Error: {e}")

        # Pages detail
        print(f"📄 Analyzing Pages projects...")
        pages_analyses = []
        for p in pages[:50]:
            pname = p.get("name", "")
            try:
                detail = self.get_pages_project_detail(pname)
                if detail:
                    pages_analyses.append({
                        "name": pname,
                        "subdomain": detail.get("subdomain", ""),
                        "domains": detail.get("domains", []),
                        "framework": detail.get("framework", ""),
                        "production_branch": detail.get("productionBranch", ""),
                        "created_on": detail.get("created_on", ""),
                        "latest_deployment": detail.get("latest_deployment", {}),
                    })
            except Exception:
                pass
            time.sleep(0.2)

        # Zone details with DNS
        print(f"🌐 Analyzing zones...")
        zone_analyses = []
        for z in zones:
            zid = z.get("id", "")
            dns = self.get_zone_dns_records(zid)
            zone_analyses.append({
                "name": z.get("name", ""),
                "status": z.get("status", ""),
                "type": z.get("type", ""),
                "nameservers": z.get("name_servers", []),
                "dns_records_count": len(dns),
                "dns_record_types": list(set(r.get("type", "") for r in dns)) if dns else [],
            })
            time.sleep(0.2)

        result = {
            "accounts": accounts,
            "workers_count": len(workers),
            "worker_analyses": worker_analyses,
            "pages_count": len(pages),
            "pages_analyses": pages_analyses,
            "zones": zone_analyses,
            "kv_namespaces": kv,
            "d1_databases": d1,
            "r2_buckets": r2,
            "durable_objects": durable,
            "queues": queues,
        }

        self._save_json("full_collection", result)
        print(f"\n✅ Cloudflare collection complete")
        return result

    def _get_accounts(self) -> list[dict]:
        r = self.client.get(f"{CLOUDFLARE_API}/accounts")
        if r.status_code == 200:
            return r.json().get("result", [])
        return []

    def _save_json(self, name: str, data: dict):
        path = self.cache_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)