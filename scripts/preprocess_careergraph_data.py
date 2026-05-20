#!/usr/bin/env python3
"""
Pre-process CareerGraph Data Before Ingestion

This script provides advanced filtering, transformation, and validation
options before ingesting data from careergraph-wiki-mcp-ui into the graph.

Features:
- Filter by type, tags, date range
- Validate data integrity
- Transform and enrich metadata
- Deduplicate entries
- Confidence scoring
- Skill extraction preview
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta


class DataPreprocessor:
    """Pre-process and validate data before graph ingestion."""

    # Known skill patterns for validation
    SKILL_PATTERNS = {
        'languages': ['python', 'javascript', 'typescript', 'go', 'rust', 'java', 'cpp', 'c#'],
        'frameworks': ['react', 'next.js', 'fastapi', 'django', 'flask', 'express', 'vue', 'svelte'],
        'platforms': ['vercel', 'cloudflare', 'aws', 'gcp', 'azure', 'docker', 'kubernetes'],
        'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'sqlite', 'd1', 'kv'],
    }

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.stats = {
            'original_count': 0,
            'filtered_count': 0,
            'validated_count': 0,
            'enriched_count': 0,
        }

    def filter_by_type(self, types: List[str]) -> 'DataPreprocessor':
        """Filter pages by type."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        filtered = [
            page for page in pages
            if page.get('metadata', {}).get('type', '') in types
        ]
        self.data['wiki_pages']['pages'] = filtered
        self.stats['filtered_count'] = len(filtered)
        print(f"  ✓ Filtered by types {types}: {len(filtered)} pages")
        return self

    def filter_by_tags(self, tags: List[str], match_all: bool = False) -> 'DataPreprocessor':
        """Filter pages by tags."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        tags_set = set(tags)

        if match_all:
            filtered = [
                page for page in pages
                if tags_set.issubset(set(page.get('tags', [])))
            ]
        else:
            filtered = [
                page for page in pages
                if any(tag in page.get('tags', []) for tag in tags)
            ]

        self.data['wiki_pages']['pages'] = filtered
        self.stats['filtered_count'] = len(filtered)
        print(f"  ✓ Filtered by tags: {len(filtered)} pages")
        return self

    def filter_by_date(self, after: str, before: Optional[str] = None) -> 'DataPreprocessor':
        """Filter pages by date range."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])

        try:
            after_dt = datetime.fromisoformat(after.replace('Z', '+00:00'))
        except:
            after_dt = datetime.min

        before_dt = datetime.fromisoformat(before.replace('Z', '+00:00')) if before else datetime.max

        filtered = []
        for page in pages:
            updated_at = page.get('metadata', {}).get('updated_at', '')
            try:
                page_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                if after_dt <= page_dt <= before_dt:
                    filtered.append(page)
            except:
                # Keep pages with invalid dates
                filtered.append(page)

        self.data['wiki_pages']['pages'] = filtered
        self.stats['filtered_count'] = len(filtered)
        print(f"  ✓ Filtered by date range: {len(filtered)} pages")
        return self

    def filter_by_min_confidence(self, min_confidence: float) -> 'DataPreprocessor':
        """Filter skills/entries by minimum confidence."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        filtered = [
            page for page in pages
            if page.get('metadata', {}).get('confidence', 1.0) >= min_confidence
        ]
        self.data['wiki_pages']['pages'] = filtered
        self.stats['filtered_count'] = len(filtered)
        print(f"  ✓ Filtered by min confidence ({min_confidence}): {len(filtered)} pages")
        return self

    def validate_integrity(self) -> 'DataPreprocessor':
        """Validate data integrity."""
        print("\n  Validating data integrity...")
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        valid_pages = []
        errors = []

        for i, page in enumerate(pages):
            # Check required fields
            if not page.get('slug'):
                errors.append(f"Page {i}: Missing slug")
                continue

            if not page.get('title'):
                errors.append(f"Page {i}: Missing title")
                continue

            # Check for valid metadata
            metadata = page.get('metadata', {})
            if not isinstance(metadata, dict):
                errors.append(f"Page {i}: Invalid metadata")
                continue

            valid_pages.append(page)

        self.data['wiki_pages']['pages'] = valid_pages
        self.stats['validated_count'] = len(valid_pages)

        print(f"  ✓ Validated: {len(valid_pages)}/{len(pages)} pages")
        if errors:
            print(f"  ⚠️ Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"    - {error}")

        return self

    def enrich_metadata(self) -> 'DataPreprocessor':
        """Enrich metadata with additional information."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        enriched = 0

        for page in pages:
            metadata = page.get('metadata', {})

            # Add word count
            content = page.get('content', '')
            word_count = len(content.split())
            metadata['word_count'] = word_count

            # Add skill keywords if content exists
            if content:
                skills_found = []
                content_lower = content.lower()
                for category, skills in self.SKILL_PATTERNS.items():
                    for skill in skills:
                        if skill.lower() in content_lower:
                            skills_found.append(skill)
                if skills_found:
                    metadata['detected_skills'] = skills_found
                    metadata['skill_categories'] = list(set(
                        category for category, skills in self.SKILL_PATTERNS.items()
                        if any(s.lower() in content_lower for s in skills)
                    ))

            # Add confidence score based on content quality
            if word_count > 100 and 'detected_skills' in metadata:
                metadata['confidence'] = min(1.0, 0.5 + (word_count / 1000))
            elif word_count > 50:
                metadata['confidence'] = 0.7
            else:
                metadata['confidence'] = 0.5

            page['metadata'] = metadata
            enriched += 1

        self.stats['enriched_count'] = enriched
        print(f"  ✓ Enriched {enriched} pages")
        return self

    def deduplicate(self) -> 'DataPreprocessor':
        """Remove duplicate entries."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        seen_slugs: Set[str] = set()
        unique_pages = []
        duplicates = 0

        for page in pages:
            slug = page.get('slug', '')
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                unique_pages.append(page)
            else:
                duplicates += 1

        self.data['wiki_pages']['pages'] = unique_pages
        self.stats['deduplicated_count'] = len(unique_pages)
        print(f"  ✓ Deduplicated: removed {duplicates} duplicates, {len(unique_pages)} remaining")
        return self

    def extract_skills_preview(self) -> Dict[str, Any]:
        """Extract and preview skills from the data."""
        pages = self.data.get('wiki_pages', {}).get('pages', [])
        skills: Dict[str, int] = {}
        categories: Dict[str, int] = {}

        for page in pages:
            metadata = page.get('metadata', {})
            detected = metadata.get('detected_skills', [])
            cats = metadata.get('skill_categories', [])

            for skill in detected:
                skills[skill] = skills.get(skill, 0) + 1
            for cat in cats:
                categories[cat] = categories.get(cat, 0) + 1

        # Sort by frequency
        sorted_skills = sorted(skills.items(), key=lambda x: x[1], reverse=True)
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)

        return {
            'top_skills': sorted_skills[:20],
            'top_categories': sorted_cats,
            'total_skill_mentions': sum(skills.values()),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get preprocessing statistics."""
        return self.stats


def main():
    """Main preprocessing function."""
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process CareerGraph data")
    parser.add_argument(
        "--input",
        required=True,
        help="Input file path"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path"
    )
    parser.add_argument(
        "--filter-types",
        nargs='+',
        help="Filter by types"
    )
    parser.add_argument(
        "--filter-tags",
        nargs='+',
        help="Filter by tags"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate data integrity"
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich metadata"
    )
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        help="Remove duplicates"
    )
    parser.add_argument(
        "--preview-skills",
        action="store_true",
        help="Preview extracted skills"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("Pre-processing CareerGraph Data")
    print("="*70)

    # Load data
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data.get('wiki_pages', {}).get('pages', []))
    print(f"\nLoaded {original_count} pages from {args.input}")

    # Create preprocessor
    preprocessor = DataPreprocessor(data)

    # Apply filters
    if args.filter_types:
        preprocessor.filter_by_type(args.filter_types)

    if args.filter_tags:
        preprocessor.filter_by_tags(args.filter_tags)

    if args.min_confidence > 0:
        preprocessor.filter_by_min_confidence(args.min_confidence)

    # Validate
    if args.validate:
        preprocessor.validate_integrity()

    # Enrich
    if args.enrich:
        preprocessor.enrich_metadata()

    # Deduplicate
    if args.deduplicate:
        preprocessor.deduplicate()

    # Preview skills
    if args.preview_skills:
        print("\n" + "="*60)
        print("Skills Preview")
        print("="*60)
        skills_info = preprocessor.extract_skills_preview()
        print(f"Top skills detected:")
        for skill, count in skills_info['top_skills'][:10]:
            print(f"  - {skill}: {count} mentions")
        print(f"\nTop categories:")
        for cat, count in skills_info['top_categories']:
            print(f"  - {cat}: {count} pages")

    # Save processed data
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n✅ Processed data saved to {output_path}")
    print(f"   Original: {original_count} pages")
    print(f"   Processed: {preprocessor.stats.get('filtered_count', original_count)} pages")


if __name__ == "__main__":
    main()
