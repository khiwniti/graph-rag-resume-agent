#!/usr/bin/env python3
"""
Test script for the Graph RAG Resume Agent.
Runs the collection pipeline and tests the agent queries.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline import CollectionPipeline
from app.agent.resume_agent import ResumeAgent


async def test_pipeline():
    """Test the collection pipeline."""
    print("=" * 60)
    print("Testing Collection Pipeline")
    print("=" * 60)
    
    pipeline = CollectionPipeline()
    
    try:
        result = await pipeline.run()
        print("\n✅ Collection completed successfully!")
        print(f"  Repositories: {result.get('repositories', 0)}")
        print(f"  Files: {result.get('files', 0)}")
        print(f"  Skills extracted: {result.get('skills', 0)}")
        print(f"  Graph nodes: {result.get('graph_nodes', 0)}")
        print(f"  Graph edges: {result.get('graph_edges', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        return False


def test_agent():
    """Test the résumé agent."""
    print("\n" + "=" * 60)
    print("Testing Résumé Agent")
    print("=" * 60)
    
    agent = ResumeAgent()
    
    # Test queries
    queries = [
        "What are my Python skills?",
        "Which projects use React?",
        "What cloud technologies have I used?",
        "Show me my backend development experience"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 60)
        
        try:
            response = agent.query(query, top_k=3)
            print(f"Answer: {response.answer}")
            print(f"Confidence: {response.confidence:.2f}")
            print(f"Skills found: {len(response.skills)}")
            print(f"Sources: {len(response.sources)}")
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    # Test skill listing
    print("\n" + "-" * 60)
    print("Listing all skills (min confidence: 0.3)")
    print("-" * 60)
    
    try:
        skills = agent.list_skills(min_confidence=0.3)
        print(f"Total skills: {len(skills)}")
        
        if skills:
            print("\nTop 10 skills:")
            for i, skill in enumerate(skills[:10], 1):
                print(f"  {i}. {skill['skill']} (confidence: {skill['confidence']:.2f})")
    except Exception as e:
        print(f"❌ Failed to list skills: {e}")
    
    # Test project listing
    print("\n" + "-" * 60)
    print("Listing projects")
    print("-" * 60)
    
    try:
        projects = agent.get_projects()
        print(f"Total projects: {len(projects)}")
        
        if projects:
            print("\nProjects:")
            for i, project in enumerate(projects[:5], 1):
                print(f"  {i}. {project.get('name', 'Unknown')}")
    except Exception as e:
        print(f"❌ Failed to list projects: {e}")


async def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("Graph RAG Resume Agent - Test Suite")
    print("=" * 60)
    
    # Test pipeline
    pipeline_success = await test_pipeline()
    
    # Test agent (requires pipeline to complete first)
    if pipeline_success:
        test_agent()
    else:
        print("\n⚠️  Skipping agent tests - pipeline failed")
    
    print("\n" + "=" * 60)
    print("Test suite completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
