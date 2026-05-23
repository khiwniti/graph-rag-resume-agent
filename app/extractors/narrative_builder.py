"""Narrative builder - generates LLM-powered career story chunks per project."""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.config import NVIDIA_API_KEY, NVIDIA_MODEL_ID

logger = logging.getLogger(__name__)


@dataclass
class ProjectNarrative:
    """Result of narrative generation for a project."""
    project_id: str
    text: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    mentioned_skills: List[str] = None
    mentioned_technologies: List[str] = None

    def __post_init__(self):
        if self.mentioned_skills is None:
            self.mentioned_skills = []
        if self.mentioned_technologies is None:
            self.mentioned_technologies = []


class NarrativeBuilder:
    """Builds career narrative summaries for projects using LLM inference."""

    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None):
        self.api_key = api_key or NVIDIA_API_KEY
        self.model_id = model_id or NVIDIA_MODEL_ID or "nvidia/nemotron-4-340b"
        self._available = bool(self.api_key)

    def is_available(self) -> bool:
        return self._available

    def _build_prompt(self, repo_data: Dict[str, Any]) -> str:
        """Compose a prompt from repository metadata for narrative generation."""
        name = repo_data.get("name", "Unknown Project")
        description = repo_data.get("description", "")
        readme = repo_data.get("readme", "")
        languages = list(repo_data.get("languages", {}).keys())
        skills = repo_data.get("extracted_skills", [])
        stars = repo_data.get("stars", 0)
        created = repo_data.get("created_at", "")
        pushed = repo_data.get("pushed_at", "")
        first_commit = repo_data.get("first_commit_at", "")
        last_commit = repo_data.get("last_commit_at", "")

        skill_names = [s.get("name", "") for s in skills if s.get("name")]
        skill_text = ", ".join(skill_names[:20]) if skill_names else "None extracted"

        prompt = f"""You are a technical career biographer. Write a concise 3-5 sentence narrative summary of this project as part of the developer's career story. Focus on what was built, which technologies were used, and what skills it demonstrates. Keep it factual and grounded in the evidence.

Project: {name}
Description: {description}
Languages: {', '.join(languages) if languages else 'N/A'}
Extracted Skills: {skill_text}
Stars: {stars}
Created: {created}
Last Push: {pushed}
First Commit: {first_commit}
Last Commit: {last_commit}

README excerpt (first 1000 chars):
{readme[:1000]}

Narrative summary:"""
        return prompt

    def generate(self, repo_data: Dict[str, Any]) -> Optional[ProjectNarrative]:
        """Generate a narrative for a single project."""
        if not self._available:
            logger.warning("NVIDIA API key not set; skipping narrative generation")
            return None

        try:
            import requests
        except ImportError:
            logger.error("requests not installed; cannot call NVIDIA API")
            return None

        prompt = self._build_prompt(repo_data)
        api_url = f"https://api.nvidia.com/v1/models/{self.model_id}/infer"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_tokens": 512,
                "temperature": 0.3,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            text = result.get("output", "")
            if isinstance(text, dict):
                text = text.get("text", "")
            if not text:
                text = str(result)
        except Exception as e:
            logger.error(f"NVIDIA API call failed for narrative: {e}")
            return None

        # Simple keyword extraction for mentioned skills/techs
        mentioned_skills = []
        mentioned_techs = []
        for skill in repo_data.get("extracted_skills", []):
            sname = skill.get("name", "").lower()
            if sname and sname in text.lower():
                mentioned_skills.append(skill.get("name", ""))

        for lang in repo_data.get("languages", {}).keys():
            if lang.lower() in text.lower():
                mentioned_techs.append(lang)

        project_id = repo_data.get("full_name", repo_data.get("name", "unknown"))

        return ProjectNarrative(
            project_id=project_id,
            text=text.strip(),
            period_start=repo_data.get("first_commit_at") or repo_data.get("created_at"),
            period_end=repo_data.get("last_commit_at") or repo_data.get("pushed_at"),
            mentioned_skills=mentioned_skills,
            mentioned_technologies=mentioned_techs,
        )

    def generate_for_repos(self, repos: List[Dict[str, Any]]) -> List[ProjectNarrative]:
        """Generate narratives for a list of repository data dicts."""
        results = []
        for repo in repos:
            narrative = self.generate(repo)
            if narrative:
                results.append(narrative)
        return results
