"""Skill extractor - extracts and ranks skills from evidence."""
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from app.models.schemas import SkillEvidenceRanked


class SkillExtractor:
    """
    Extracts skills from various evidence sources and ranks them by confidence.
    
    Evidence weighting (highest to lowest confidence):
    1. Source code usage (actual imports, function calls)
    2. Dependency declarations (package.json, requirements.txt)
    3. Configuration files (framework configs, deployment configs)
    4. Deployment metadata (Vercel projects, Cloudflare Workers)
    5. Conversation mentions (user statements, agent actions)
    """

    # Skill category mappings
    SKILL_CATEGORIES = {
        # Languages
        "python": "language",
        "javascript": "language",
        "typescript": "language",
        "rust": "language",
        "go": "language",
        "sql": "language",
        
        # Frontend frameworks
        "react": "frontend",
        "nextjs": "frontend",
        "vue": "frontend",
        "angular": "frontend",
        "svelte": "frontend",
        
        # Backend frameworks
        "fastapi": "backend",
        "django": "backend",
        "flask": "backend",
        "express": "backend",
        "hono": "backend",
        
        # Databases
        "postgresql": "database",
        "mysql": "database",
        "mongodb": "database",
        "redis": "database",
        "sqlite": "database",
        "d1": "database",
        
        # Cloud platforms
        "cloudflare": "platform",
        "vercel": "platform",
        "aws": "platform",
        "gcp": "platform",
        "azure": "platform",
        
        # Tools
        "git": "tool",
        "docker": "tool",
        "kubernetes": "tool",
        "terraform": "tool",
        
        # Testing
        "pytest": "testing",
        "jest": "testing",
        "playwright": "testing",
        "cypress": "testing",
    }

    # Evidence type weights
    EVIDENCE_WEIGHTS = {
        "source_code_usage": 1.0,
        "dependency_declaration": 0.7,
        "config_file": 0.6,
        "deployment_metadata": 0.5,
        "conversation_mention": 0.3,
    }

    def __init__(self):
        self.skill_evidence = defaultdict(list)  # skill_name -> list of evidence

    def extract_from_dependencies(
        self,
        dependencies: List[Dict[str, Any]],
        repo_name: str = ""
    ) -> List[SkillEvidenceRanked]:
        """
        Extract skills from dependency list.
        
        Args:
            dependencies: List of dependency dicts
            repo_name: Source repository name
            
        Returns:
            List of SkillEvidenceRanked objects
        """
        skills = []
        
        for dep in dependencies:
            dep_name = dep.get("name", "").lower()
            category = dep.get("category", "library")
            
            # Check if this maps to a known skill
            skill_name = self._normalize_skill_name(dep_name)
            if skill_name and skill_name in self.SKILL_CATEGORIES:
                skill_category = self.SKILL_CATEGORIES[skill_name]
                
                # Calculate confidence based on evidence type
                confidence = self.EVIDENCE_WEIGHTS["dependency_declaration"]
                
                skills.append(SkillEvidenceRanked(
                    skill_name=skill_name,
                    category=skill_category,
                    proficiency_indicator=self._estimate_proficiency(1, confidence),
                    confidence=confidence,
                    frequency=1,
                    evidence_sources=[repo_name] if repo_name else [],
                    evidence_types=["dependency_declaration"],
                    first_seen=datetime.utcnow().isoformat(),
                    last_seen=datetime.utcnow().isoformat(),
                ))
        
        return skills

    def extract_from_source_code(
        self,
        file_analyses: List[Dict[str, Any]],
        repo_name: str = ""
    ) -> List[SkillEvidenceRanked]:
        """
        Extract skills from analyzed source files.
        
        Args:
            file_analyses: List of file analysis results
            repo_name: Source repository name
            
        Returns:
            List of SkillEvidenceRanked objects
        """
        skills = []
        skill_files = defaultdict(set)  # skill_name -> set of file paths
        
        for analysis in file_analyses:
            frameworks = analysis.get("frameworks", [])
            patterns = analysis.get("architecture_patterns", [])
            file_path = analysis.get("file_path", "")
            
            # Extract framework skills
            for framework in frameworks:
                skill_name = self._normalize_skill_name(framework)
                if skill_name in self.SKILL_CATEGORIES:
                    skill_files[skill_name].add(file_path)
            
            # Extract pattern skills
            for pattern in patterns:
                if pattern in ["api_first", "component_based", "event_driven"]:
                    skill_files[pattern].add(file_path)
        
        # Convert to SkillEvidenceRanked objects
        for skill_name, files in skill_files.items():
            category = self.SKILL_CATEGORIES.get(skill_name, "technology")
            confidence = self.EVIDENCE_WEIGHTS["source_code_usage"]
            
            skills.append(SkillEvidenceRanked(
                skill_name=skill_name,
                category=category,
                proficiency_indicator=self._estimate_proficiency(len(files), confidence),
                confidence=confidence,
                frequency=len(files),
                evidence_sources=[repo_name] if repo_name else [],
                evidence_types=["source_code_usage"],
                first_seen=datetime.utcnow().isoformat(),
                last_seen=datetime.utcnow().isoformat(),
            ))
        
        return skills

    def extract_from_cloudflare_resources(
        self,
        resources: List[Dict[str, Any]]
    ) -> List[SkillEvidenceRanked]:
        """
        Extract skills from Cloudflare resources.
        
        Args:
            resources: List of Cloudflare resource data
            
        Returns:
            List of SkillEvidenceRanked objects
        """
        skills = []
        
        # Detect Cloudflare-specific skills
        has_worker = False
        has_pages = False
        has_kv = False
        has_d1 = False
        has_r2 = False
        
        for resource in resources:
            resource_type = resource.get("resource_type", "")
            
            if resource_type == "worker":
                has_worker = True
                patterns = resource.get("detected_patterns", [])
                if "hono" in str(patterns).lower():
                    skills.append(self._create_skill("hono", "backend", 0.8, ["cloudflare_worker"]))
                if "itty-router" in str(patterns).lower():
                    skills.append(self._create_skill("itty-router", "backend", 0.7, ["cloudflare_worker"]))
            
            elif resource_type == "pages":
                has_pages = True
            
            elif resource_type == "kv":
                has_kv = True
            
            elif resource_type == "d1":
                has_d1 = True
                skills.append(self._create_skill("d1", "database", 0.7, ["cloudflare"]))
            
            elif resource_type == "r2":
                has_r2 = True
        
        # Add Cloudflare platform skill
        if has_worker or has_pages:
            skills.append(self._create_skill("cloudflare", "platform", 0.9, ["cloudflare"]))
        
        return skills

    def merge_and_rank_skills(
        self,
        all_skills: List[SkillEvidenceRanked]
    ) -> List[SkillEvidenceRanked]:
        """
        Merge duplicate skills and recalculate confidence.
        
        Args:
            all_skills: List of all extracted skills
            
        Returns:
            Merged and ranked skill list
        """
        skill_map = {}  # skill_name -> SkillEvidenceRanked
        
        for skill in all_skills:
            if skill.skill_name not in skill_map:
                skill_map[skill.skill_name] = skill
            else:
                # Merge evidence
                existing = skill_map[skill.skill_name]
                existing.confidence = min(1.0, existing.confidence + skill.confidence * 0.3)
                existing.frequency += skill.frequency
                existing.evidence_sources.extend(skill.evidence_sources)
                existing.evidence_types.extend(skill.evidence_types)
                existing.proficiency_indicator = self._estimate_proficiency(
                    existing.frequency,
                    existing.confidence
                )
        
        # Sort by confidence
        ranked = sorted(
            skill_map.values(),
            key=lambda x: x.confidence,
            reverse=True
        )
        
        return ranked

    def _normalize_skill_name(self, name: str) -> str:
        """Normalize skill name to canonical form."""
        name_lower = name.lower().replace("-", "").replace(".", "").replace("_", "")
        
        # Map variations to canonical names
        canonical_map = {
            "nextjs": "nextjs",
            "next": "nextjs",
            "react": "react",
            "fastapi": "fastapi",
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "mongo": "mongodb",
            "cloudflareworkers": "cloudflare",
        }
        
        return canonical_map.get(name_lower, name_lower)

    def _estimate_proficiency(self, frequency: int, confidence: float) -> str:
        """Estimate proficiency level from frequency and confidence."""
        score = frequency * confidence
        
        if score >= 5.0:
            return "expert"
        elif score >= 3.0:
            return "advanced"
        elif score >= 1.5:
            return "intermediate"
        else:
            return "beginner"

    def _create_skill(
        self,
        name: str,
        category: str,
        confidence: float,
        sources: List[str]
    ) -> SkillEvidenceRanked:
        """Helper to create a SkillEvidenceRanked object."""
        return SkillEvidenceRanked(
            skill_name=name,
            category=category,
            proficiency_indicator=self._estimate_proficiency(1, confidence),
            confidence=confidence,
            frequency=1,
            evidence_sources=sources,
            evidence_types=[category],
            first_seen=datetime.utcnow().isoformat(),
            last_seen=datetime.utcnow().isoformat(),
        )
