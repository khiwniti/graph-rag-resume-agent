"""Evidence ranker - ranks and weights evidence for skill claims."""
from typing import Dict, Any, List, Tuple
from collections import defaultdict


class EvidenceRanker:
    """
    Ranks evidence by reliability and relevance.
    
    Evidence hierarchy (most to least reliable):
    1. Source code usage - actual implementation
    2. Dependency declarations - explicit dependencies
    3. Configuration files - framework/tool configs
    4. Deployment metadata - where code runs
    5. Conversation mentions - stated intentions
    
    This class provides methods to:
    - Score evidence quality
    - Weight evidence by type
    - Aggregate evidence across sources
    - Filter low-confidence claims
    """

    # Base weights by evidence type
    EVIDENCE_TYPE_WEIGHTS = {
        "source_code_usage": 1.0,
        "dependency_declaration": 0.7,
        "config_file": 0.6,
        "deployment_metadata": 0.5,
        "conversation_mention": 0.3,
    }

    # Source system reliability multipliers
    SOURCE_RELIABILITY = {
        "github": 1.0,
        "vercel": 0.9,
        "cloudflare": 0.9,
        "conversation": 0.5,
    }

    # Minimum confidence threshold
    MIN_CONFIDENCE = 0.2

    def __init__(self):
        pass

    def score_evidence(
        self,
        evidence_type: str,
        source_system: str = "github",
        frequency: int = 1,
        recency_score: float = 1.0
    ) -> float:
        """
        Calculate confidence score for a piece of evidence.
        
        Args:
            evidence_type: Type of evidence (source_code_usage, etc.)
            source_system: Source system (github, vercel, cloudflare, conversation)
            frequency: Number of occurrences
            recency_score: Score based on how recent the evidence is (0-1)
            
        Returns:
            Confidence score (0-1)
        """
        # Get base weight
        base_weight = self.EVIDENCE_TYPE_WEIGHTS.get(evidence_type, 0.3)
        
        # Apply source reliability multiplier
        source_mult = self.SOURCE_RELIABILITY.get(source_system, 0.5)
        
        # Calculate raw score
        raw_score = base_weight * source_mult
        
        # Boost for frequency (diminishing returns)
        frequency_boost = min(2.0, 1 + (frequency - 1) * 0.2)
        
        # Apply recency
        final_score = raw_score * frequency_boost * recency_score
        
        return min(1.0, final_score)

    def aggregate_evidence(
        self,
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate evidence by skill/technology.
        
        Args:
            evidence_list: List of evidence dicts with keys:
                - skill_name
                - evidence_type
                - source_system
                - frequency (optional)
                - details (optional)
                
        Returns:
            Dict mapping skill_name to aggregated evidence data
        """
        skill_evidence = defaultdict(lambda: {
            "evidence_items": [],
            "total_score": 0.0,
            "evidence_types": set(),
            "sources": set(),
            "frequency": 0,
        })
        
        for evidence in evidence_list:
            skill_name = evidence.get("skill_name", "")
            if not skill_name:
                continue
            
            # Calculate score for this evidence
            score = self.score_evidence(
                evidence_type=evidence.get("evidence_type", "conversation_mention"),
                source_system=evidence.get("source_system", "unknown"),
                frequency=evidence.get("frequency", 1),
            )
            
            # Aggregate
            skill_evidence[skill_name]["evidence_items"].append(evidence)
            skill_evidence[skill_name]["total_score"] += score
            skill_evidence[skill_name]["evidence_types"].add(
                evidence.get("evidence_type", "")
            )
            skill_evidence[skill_name]["sources"].add(
                evidence.get("source_system", "")
            )
            skill_evidence[skill_name]["frequency"] += evidence.get("frequency", 1)
        
        # Convert sets to lists and normalize scores
        result = {}
        for skill_name, data in skill_evidence.items():
            # Normalize score to 0-1 range
            normalized_score = min(1.0, data["total_score"] / len(data["evidence_items"]))
            
            result[skill_name] = {
                "evidence_items": data["evidence_items"],
                "confidence": normalized_score,
                "evidence_types": list(data["evidence_types"]),
                "sources": list(data["sources"]),
                "frequency": data["frequency"],
                "evidence_count": len(data["evidence_items"]),
            }
        
        return result

    def filter_low_confidence(
        self,
        aggregated_evidence: Dict[str, Dict[str, Any]],
        threshold: float = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Filter out low-confidence evidence.
        
        Args:
            aggregated_evidence: Output from aggregate_evidence()
            threshold: Minimum confidence threshold (default: MIN_CONFIDENCE)
            
        Returns:
            Filtered evidence dict
        """
        if threshold is None:
            threshold = self.MIN_CONFIDENCE
        
        filtered = {}
        for skill_name, data in aggregated_evidence.items():
            if data["confidence"] >= threshold:
                filtered[skill_name] = data
        
        return filtered

    def rank_skills(
        self,
        aggregated_evidence: Dict[str, Dict[str, Any]]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Rank skills by confidence score.
        
        Args:
            aggregated_evidence: Output from aggregate_evidence()
            
        Returns:
            List of (skill_name, data) tuples sorted by confidence
        """
        ranked = sorted(
            aggregated_evidence.items(),
            key=lambda x: x[1]["confidence"],
            reverse=True
        )
        return ranked

    def get_evidence_summary(
        self,
        skill_name: str,
        aggregated_evidence: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Generate human-readable evidence summary for a skill.
        
        Args:
            skill_name: Name of the skill
            aggregated_evidence: Output from aggregate_evidence()
            
        Returns:
            Summary string
        """
        if skill_name not in aggregated_evidence:
            return f"No evidence found for {skill_name}"
        
        data = aggregated_evidence[skill_name]
        
        summary_parts = [
            f"Skill: {skill_name}",
            f"Confidence: {data['confidence']:.2f}",
            f"Evidence count: {data['evidence_count']}",
            f"Frequency: {data['frequency']}",
            f"Evidence types: {', '.join(data['evidence_types'])}",
            f"Sources: {', '.join(data['sources'])}",
        ]
        
        return "\n".join(summary_parts)

    def cross_validate_evidence(
        self,
        skill_name: str,
        github_evidence: List[Dict],
        vercel_evidence: List[Dict],
        cloudflare_evidence: List[Dict]
    ) -> Dict[str, Any]:
        """
        Cross-validate evidence across multiple sources.
        
        Args:
            skill_name: Name of the skill to validate
            github_evidence: Evidence from GitHub
            vercel_evidence: Evidence from Vercel
            cloudflare_evidence: Evidence from Cloudflare
            
        Returns:
            Validation result with cross-source confidence boost
        """
        all_evidence = []
        source_counts = defaultdict(int)
        
        for ev in github_evidence:
            all_evidence.append(ev)
            source_counts["github"] += 1
        
        for ev in vercel_evidence:
            all_evidence.append(ev)
            source_counts["vercel"] += 1
        
        for ev in cloudflare_evidence:
            all_evidence.append(ev)
            source_counts["cloudflare"] += 1
        
        # Count unique sources
        unique_sources = sum(1 for count in source_counts.values() if count > 0)
        
        # Boost confidence for multi-source evidence
        multi_source_boost = 1.0 + (unique_sources - 1) * 0.2
        
        return {
            "skill_name": skill_name,
            "total_evidence": len(all_evidence),
            "unique_sources": unique_sources,
            "source_breakdown": dict(source_counts),
            "multi_source_boost": multi_source_boost,
            "is_cross_validated": unique_sources > 1,
        }
