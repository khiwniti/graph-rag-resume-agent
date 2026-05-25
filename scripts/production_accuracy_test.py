#!/usr/bin/env python3
"""
Production Accuracy Test for the Graph RAG Resume Agent.
Designs questions an HR would ask and checks the source attribution accuracy.
"""

import sys
import random
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.resume_agent import ResumeAgent
from app.graph_store import Neo4jStore, KnowledgeGraphConfig
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

HR_QUESTIONS = [
    "What are your top 3 technical skills and how have you applied them?",
    "Tell me about a project where you used Python to solve a complex problem.",
    "What is your experience with cloud deployments (AWS, GCP, or Vercel)?",
    "How have you implemented CI/CD in your previous projects?",
    "Describe your experience with graph databases like Neo4j.",
    "What is the most complex architecture you've worked on?",
    "Tell me about your experience with React and frontend development.",
    "How do you ensure data quality and cleaning in your data pipelines?",
    "What backend frameworks are you most comfortable with?",
    "Describe a time you had to optimize the performance of a system."
]

class AccuracyTester:
    def __init__(self):
        self.agent = ResumeAgent()
        self.store = None
        self._init_store()

    def _init_store(self):
        config = KnowledgeGraphConfig(
            uri=NEO4J_URI or "bolt://localhost:7687",
            user=NEO4J_USER or "neo4j",
            password=NEO4J_PASSWORD or "",
            database=NEO4J_DATABASE or "neo4j",
        )
        try:
            self.store = Neo4jStore(config)
            self.store.connect()
            logger.info("Connected to Neo4j for verification.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    def verify_source(self, source_id: str, label: Optional[str] = None) -> bool:
        """Verify if a source node exists in the graph by ID or Label."""
        if not self.store:
            return False
        
        query = "MATCH (n) WHERE n.id = $id OR n.label = $label RETURN count(n) as count"
        try:
            with self.store.driver.session() as session:
                result = session.run(query, {"id": source_id, "label": label or source_id}).single()
                return result["count"] > 0
        except Exception as e:
            logger.error(f"Error verifying source {source_id}: {e}")
            return False

    def get_projects_for_skill(self, skill_label: str) -> List[str]:
        """Fetch project names that use a specific skill/technology."""
        if not self.store:
            return []
        
        # Universal schema query
        query = """
        MATCH (p:Person)-[:AUTHORED]->(r)-[:USES]->(t:Technology)
        WHERE toLower(t.label) = toLower($label)
        RETURN r.label as project_name
        LIMIT 5
        """
        try:
            with self.store.driver.session() as session:
                records = session.run(query, {"label": skill_label})
                return [r["project_name"] for r in records]
        except Exception as e:
            logger.error(f"Error fetching projects for {skill_label}: {e}")
            return []

    def run_test(self, num_questions: int = 3, random_select: bool = True):
        print("\n" + "=" * 80)
        print(f"RUNNING PRODUCTION ACCURACY TEST ({num_questions} questions)")
        print("=" * 80)

        questions = HR_QUESTIONS
        if random_select:
            questions = random.sample(HR_QUESTIONS, min(num_questions, len(HR_QUESTIONS)))
        else:
            questions = HR_QUESTIONS[:num_questions]

        results = []

        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{num_questions}] Question: {q}")
            print("-" * 40)
            
            try:
                response = self.agent.query(q)
                
                print(f"Answer summary: {response.answer[:200]}...")
                print(f"Confidence: {response.confidence:.2f}")
                
                evidence_items = response.evidence
                print(f"Evidence items found: {len(evidence_items)}")
                
                verified_count = 0
                total_to_verify = len(evidence_items)
                
                for ev in evidence_items:
                    skill_name = ev.get('skill_name') or ev.get('skill')
                    category = ev.get('category')
                    source_id = category if (category and ':' in category) else skill_name
                    
                    is_valid = self.verify_source(source_id, label=skill_name)
                    status = "✅ VERIFIED" if is_valid else "❌ NOT FOUND"
                    print(f"  - Skill: {skill_name} ({category}): {status}")
                    
                    if is_valid:
                        verified_count += 1
                        
                        # Deep check: fetch actual projects that back this claim
                        projects = self.get_projects_for_skill(skill_name)
                        if projects:
                            print(f"    Source Projects in Graph: {', '.join(projects)}")
                        else:
                            print(f"    ⚠️ No specific projects found linking person to {skill_name}")
                
                accuracy_score = verified_count / total_to_verify if total_to_verify > 0 else 0
                print(f"Accuracy Score: {accuracy_score:.2%}")
                
                results.append({
                    "question": q,
                    "accuracy": accuracy_score,
                    "confidence": response.confidence,
                    "num_evidence": len(evidence_items)
                })

            except Exception as e:
                print(f"❌ Error testing question: {e}")
                results.append({
                    "question": q,
                    "error": str(e)
                })

        self.print_summary(results)

    def print_summary(self, results):
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_acc = 0.0
        count = 0
        
        for r in results:
            if "accuracy" in r:
                total_acc += r["accuracy"]
                count += 1
        
        avg_acc = total_acc / count if count > 0 else 0
        print(f"Average Source Accuracy: {avg_acc:.2%}")
        print(f"Total Questions Tested: {len(results)}")
        
        if avg_acc > 0.8:
            print("Status: 🟢 PASSING")
        elif avg_acc > 0.5:
            print("Status: 🟡 MARGINAL")
        else:
            print("Status: 🔴 FAILING")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    num = 3
    if len(sys.argv) > 1:
        num = int(sys.argv[1])
    
    tester = AccuracyTester()
    tester.run_test(num_questions=num)
