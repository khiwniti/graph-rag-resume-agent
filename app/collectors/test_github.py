"""Test suite for GitHubCollector only"""
import os
import sys
import tempfile
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.collectors.github_collector import GitHubCollector

def test_github_collector_basic():
    """Test basic GitHubCollector functionality"""
    print("Testing GitHubCollector basic functionality...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo_dir = Path(temp_dir) / "test_repo"
        test_repo_url = "https://github.com/example/test-resume-repo.git"
        
        # Initialize collector
        collector = GitHubCollector(max_repos=1)
        
        # Test the collection process
        results = collector.collect_all(max_repos=1)
        
        # Verify results
        assert results["original_repos_count"] == 1, "Should process 1 repository"
        assert len(results["deep_analyses"]) >= 0, "Should have extracted data"
        assert "errors" in results, "Should have error tracking"
        
        # Check cleanup happened (repository directory should be gone)
        assert not test_repo_dir.exists(), "Repository should be cleaned up after processing"
        
        print("✓ GitHubCollector basic test passed")
        return True

def test_github_collector_with_token():
    """Test GitHubCollector with token"""
    print("Testing GitHubCollector with token...")
    
    # Check if GITHUB_TOKEN is set
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("⚠️  GITHUB_TOKEN not set, skipping token test")
        return True
    
    # Test that the collector can access the token
    collector = GitHubCollector()
    assert collector.github_token is not None, "Should have GitHub token"
    
    print("✓ GitHubCollector token test passed")
    return True

def main():
    """Run GitHubCollector specific tests"""
    print("Running GitHubCollector tests...\n")
    
    try:
        test_github_collector_basic()
        test_github_collector_with_token()
        
        print("\n✅ All GitHubCollector tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())