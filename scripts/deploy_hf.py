#!/usr/bin/env python3
"""
Deploy Graph RAG Resume Agent to Hugging Face Spaces

Usage:
    python scripts/deploy_hf.py --repo-id your-username/space-name

Requirements:
    pip install huggingface_hub
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_prerequisites():
    """Check if required tools are installed."""
    missing = []

    # Check huggingface_hub
    try:
        import huggingface_hub
    except ImportError:
        missing.append("huggingface_hub")

    # Check git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("git")

    if missing:
        print("Missing required tools:")
        for tool in missing:
            print(f"  - {tool}")
        print("\nInstall with: pip install huggingface_hub")
        sys.exit(1)


def login_to_hf():
    """Login to Hugging Face Hub."""
    print("Logging in to Hugging Face Hub...")
    from huggingface_hub import login

    try:
        login()
        print("✓ Logged in successfully")
    except Exception as e:
        print(f"✗ Login failed: {e}")
        print("\nYou can also run: huggingface-cli login")
        sys.exit(1)


def create_space(repo_id: str, private: bool = False):
    """Create a new Hugging Face Space."""
    from huggingface_hub import HfApi

    api = HfApi()

    # Parse repo_id
    if "/" not in repo_id:
        print("Repository ID must be in format 'username/space-name'")
        sys.exit(1)

    try:
        # Try to create the space
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=private,
            exist_ok=True
        )
        print(f"✓ Space created/exists: {repo_id}")
    except Exception as e:
        print(f"✗ Failed to create space: {e}")
        sys.exit(1)


def push_to_hub(repo_id: str):
    """Push files to Hugging Face Space."""
    from huggingface_hub import HfApi

    api = HfApi()

    print("Pushing files to Hugging Face Space...")

    # Files to upload
    files_to_upload = [
        "Dockerfile",
        "requirements.txt",
        "README.md",
        ".gitignore",
    ]

    # Add app directory
    for path in Path("app").rglob("*"):
        if path.is_file() and not path.name.startswith("__"):
            files_to_upload.append(str(path))

    # Add scripts directory
    for path in Path("scripts").rglob("*"):
        if path.is_file() and path.suffix in [".py"]:
            files_to_upload.append(str(path))

    try:
        for file_path in files_to_upload:
            if Path(file_path).exists():
                api.upload_file(
                    path_or_fileobj=str(file_path),
                    path_in_repo=file_path,
                    repo_id=repo_id,
                    repo_type="space",
                )
                print(f"  ✓ Uploaded: {file_path}")
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        sys.exit(1)

    print(f"\n✓ Pushed to https://huggingface.co/spaces/{repo_id}")


def main():
    parser = argparse.ArgumentParser(description="Deploy to Hugging Face Spaces")
    parser.add_argument("--repo-id", required=True, help="Repository ID (username/space-name)")
    parser.add_argument("--private", action="store_true", help="Make the space private")
    args = parser.parse_args()

    print("=" * 60)
    print("Deploying Graph RAG Resume Agent to Hugging Face Spaces")
    print("=" * 60)

    # Check prerequisites
    check_prerequisites()

    # Login
    login_to_hf()

    # Create space
    create_space(args.repo_id, private=args.private)

    # Push files
    push_to_hub(args.repo_id)

    print("\n" + "=" * 60)
    print("Deployment complete!")
    print(f"View your Space at: https://huggingface.co/spaces/{args.repo_id}")
    print("API will be available at: https://{username}-graph-rag-resume-agent.hf.space")
    print("=" * 60)


if __name__ == "__main__":
    main()
