"""Conversation artifact collector - extracts evidence from conversation exports."""
import json
import zipfile
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import CONVERSATION_ZIP_PATH, RAW_DIR


class ConversationCollector:
    """
    Collects evidence from conversation exports (e.g., conversation_acc97712a9c1482992c7523a4ed73e08.zip).
    
    This collector:
    1. Parses JSON events from conversation zip files
    2. Extracts user messages, agent actions, file creations, and task mentions
    3. Identifies technology references, repo names, and project intents
    4. Outputs normalized conversation evidence documents
    
    Evidence from conversations is weighted lower than actual code evidence,
    but provides valuable context about work history and project intentions.
    """

    def __init__(self, zip_path: Optional[str] = None):
        """Initialize with optional path to conversation zip file."""
        self.zip_path = zip_path or CONVERSATION_ZIP_PATH
        self.cache_dir = RAW_DIR / "conversation"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Patterns for extracting technical information
        self.repo_pattern = re.compile(r'github\.com/([^/\s]+)/([^/\s]+)')
        self.tech_pattern = re.compile(r'\b(python|javascript|typescript|react|next\.?js|fastapi|docker|kubernetes|aws|gcp|cloudflare|vercel|github|node\.?js|vue|angular|django|flask|postgresql|mongodb|redis|graphql|rest|api|git|linux|bash|rust|go|java|scala|tensorflow|pytorch|llm|rag|graph|neo4j|faiss|sentence-transformers)\b', re.IGNORECASE)

    def collect_all(self) -> Dict[str, Any]:
        """
        Run full conversation collection pipeline.
        
        Returns:
            Dict with all extracted artifacts and evidence
        """
        print(f"💬 Collecting conversation artifacts from {self.zip_path}...")
        
        if not Path(self.zip_path).exists():
            print(f" ⚠️ Conversation zip not found: {self.zip_path}")
            return self._empty_result()
        
        try:
            artifacts = self._parse_conversation_zip()
            print(f" Found {len(artifacts)} artifacts")
            
            # Extract technology mentions
            tech_evidence = self._extract_technology_evidence(artifacts)
            print(f" Extracted {len(tech_evidence)} technology mentions")
            
            # Extract repo references
            repo_evidence = self._extract_repo_references(artifacts)
            print(f" Found {len(repo_evidence)} repo references")
            
            # Extract file creation events
            file_events = self._extract_file_events(artifacts)
            print(f" Found {len(file_events)} file events")
            
            result = {
                "source": self.zip_path,
                "artifact_count": len(artifacts),
                "artifacts": artifacts[:100],  # Limit stored artifacts
                "technology_evidence": tech_evidence,
                "repo_references": repo_evidence,
                "file_events": file_events,
                "collected_at": datetime.utcnow().isoformat(),
            }
            
            self._save_json("conversation_evidence", result)
            print(f"✅ Conversation collection complete")
            return result
            
        except Exception as e:
            print(f" ⚠️ Error collecting conversation artifacts: {e}")
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "source": self.zip_path,
            "artifact_count": 0,
            "artifacts": [],
            "technology_evidence": [],
            "repo_references": [],
            "file_events": [],
            "error": "Collection failed or zip not found",
            "collected_at": datetime.utcnow().isoformat(),
        }

    def _parse_conversation_zip(self) -> List[Dict[str, Any]]:
        """Parse conversation zip file and extract events."""
        artifacts = []
        
        with zipfile.ZipFile(self.zip_path, 'r') as z:
            # Get all JSON event files
            json_files = sorted([f for f in z.namelist() if f.endswith('.json')])
            
            for json_file in json_files:
                try:
                    data = json.loads(z.read(json_file))
                    artifact = self._process_event(data, json_file)
                    if artifact:
                        artifacts.append(artifact)
                except (json.JSONDecodeError, KeyError) as e:
                    continue
        
        return artifacts

    def _process_event(self, data: Dict[str, Any], source_file: str) -> Optional[Dict[str, Any]]:
        """Process a single conversation event into an artifact."""
        source = data.get('source', 'unknown')
        event_type = data.get('type', 'unknown')
        
        # Extract text content
        content = self._extract_content(data)
        if not content:
            return None
        
        # Extract timestamp
        timestamp = data.get('timestamp', '')
        
        # Extract tool information if present
        tool_name = data.get('tool_name', '')
        tool_call_id = data.get('tool_call_id', '')
        
        # Create artifact
        artifact = {
            "artifact_id": f"conv_{source_file}_{len(content)}",
            "artifact_type": f"{source}_{event_type}",
            "source": source,
            "event_type": event_type,
            "content": content[:5000],  # Limit content length
            "content_length": len(content),
            "timestamp": timestamp,
            "source_file": source_file,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        }
        
        # Extract metadata based on source
        if source == 'user':
            artifact['artifact_type'] = 'user_message'
        elif source == 'agent':
            artifact['artifact_type'] = 'agent_action'
        elif source == 'environment':
            artifact['artifact_type'] = 'environment_response'
        
        return artifact

    def _extract_content(self, data: Dict[str, Any]) -> str:
        """Extract text content from event data."""
        # Try llm_message.content
        llm_msg = data.get('llm_message', {})
        if llm_msg:
            content_list = llm_msg.get('content', [])
            if isinstance(content_list, list):
                texts = []
                for item in content_list:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        texts.append(item.get('text', ''))
                if texts:
                    return '\n'.join(texts)
        
        # Try direct content
        content = data.get('content', '')
        if content and isinstance(content, str):
            return content
        
        # Try observation field
        observation = data.get('observation', {})
        if observation:
            obs_content = observation.get('content', '')
            if obs_content and isinstance(obs_content, str):
                return obs_content
        
        # Try action field
        action = data.get('action', {})
        if action:
            action_str = json.dumps(action) if isinstance(action, dict) else str(action)
            if action_str:
                return action_str
        
        return ''

    def _extract_technology_evidence(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract technology mentions from artifacts."""
        tech_evidence = []
        tech_counts = {}
        
        for artifact in artifacts:
            content = artifact.get('content', '')
            
            # Find technology mentions
            matches = self.tech_pattern.findall(content)
            for tech in matches:
                tech_lower = tech.lower()
                if tech_lower not in tech_counts:
                    tech_counts[tech_lower] = {'count': 0, 'artifacts': []}
                tech_counts[tech_lower]['count'] += 1
                if len(tech_counts[tech_lower]['artifacts']) < 5:
                    tech_counts[tech_lower]['artifacts'].append(artifact.get('artifact_id', ''))
        
        # Convert to list
        for tech, data in tech_counts.items():
            tech_evidence.append({
                "technology": tech,
                "mention_count": data['count'],
                "artifact_ids": data['artifacts'],
                "evidence_type": "conversation_mention",
                "confidence": min(0.3 + (data['count'] * 0.05), 0.7),  # Cap confidence
            })
        
        # Sort by count
        tech_evidence.sort(key=lambda x: x['mention_count'], reverse=True)
        return tech_evidence

    def _extract_repo_references(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract GitHub repo references from artifacts."""
        repo_refs = []
        repos_found = set()
        
        for artifact in artifacts:
            content = artifact.get('content', '')
            
            # Find repo references
            matches = self.repo_pattern.findall(content)
            for owner, repo in matches:
                repo_key = f"{owner}/{repo}"
                if repo_key not in repos_found:
                    repos_found.add(repo_key)
                    repo_refs.append({
                        "repo_name": repo,
                        "owner": owner,
                        "full_name": repo_key,
                        "source_artifact": artifact.get('artifact_id', ''),
                        "evidence_type": "conversation_reference",
                    })
        
        return repo_refs

    def _extract_file_events(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract file creation/modification events."""
        file_events = []
        
        for artifact in artifacts:
            content = artifact.get('content', '')
            tool_name = artifact.get('tool_name', '')
            
            # Look for file editor actions
            if tool_name == 'file_editor' or 'file' in content.lower():
                # Extract file paths
                file_matches = re.findall(r'(/[\w/.-]+\.(py|js|ts|tsx|jsx|json|yaml|yml|toml|txt|md|sh|bash))', content)
                for file_path, _ in file_matches:
                    file_events.append({
                        "file_path": file_path,
                        "event_type": "file_mentioned",
                        "source_artifact": artifact.get('artifact_id', ''),
                        "tool": tool_name,
                    })
        
        return file_events

    def _save_json(self, name: str, data: Dict[str, Any]):
        """Save JSON data to cache directory."""
        path = self.cache_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
