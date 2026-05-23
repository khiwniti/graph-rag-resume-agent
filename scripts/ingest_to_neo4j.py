#!/usr/bin/env python3
# Quick script to ingest all collected raw data into Neo4j
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph_store import Neo4jStore, KnowledgeGraphConfig
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

def ingest_all_data():
    print('=' * 60)
    print('Ingesting all collected data into Neo4j')
    print('=' * 60)
    
    config = KnowledgeGraphConfig(
        uri=NEO4J_URI or 'bolt://localhost:7687',
        user=NEO4J_USER or 'neo4j',
        password=NEO4J_PASSWORD or 'password',
        database=NEO4J_DATABASE or 'neo4j',
    )
    store = Neo4jStore(config)
    store.connect()
    store.create_indexes()
    store.create_constraints()
    
    person_id = 'github:kiwbrobrw'
    store.upsert_person(person_id, 'kiwbrobrw', email='', properties={'source': 'github'})
    print('Created Person node: ' + person_id)
    
    raw_dir = Path('data/raw')
    ingested_count = 0
    
    for repo_dir in sorted(raw_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        
        metadata_file = repo_dir / 'metadata.json'
        if not metadata_file.exists():
            continue
        
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            repo_name = repo_dir.name
            project_id = 'github:' + repo_name
            
            description = metadata.get('description', '')
            url = metadata.get('url', '')
            language = metadata.get('language', '')
            stars = metadata.get('stars', 0)
            created_at = metadata.get('created_at', '')
            pushed_at = metadata.get('pushed_at', '')
            
            store.upsert_project(
                project_id=project_id,
                name=description or repo_name,
                source='github',
                url=url,
                description=description,
                properties={
                    'created_at': created_at,
                    'pushed_at': pushed_at,
                    'stars': stars,
                    'language': language,
                }
            )
            
            store.link_person_to_project(person_id, project_id)
            
            if language:
                store.upsert_skill(language, 'language', 0.85)
                store.link_person_to_skill(person_id, language, 'language', 0.85, 'GitHub repo: ' + repo_name)
                store.link_skill_to_project(language, 'language', project_id, language + ' project')
            
            skills_file = repo_dir / 'skills.json'
            if skills_file.exists():
                with open(skills_file) as f:
                    skills = json.load(f)
                for skill in skills:
                    skill_name = skill.get('name', '')
                    category = skill.get('category', 'tool')
                    confidence = skill.get('confidence', 0.5)
                    if skill_name:
                        store.upsert_skill(skill_name, category, confidence)
                        store.link_person_to_skill(person_id, skill_name, category, confidence, 'From ' + repo_name)
                        store.link_skill_to_project(skill_name, category, project_id, 'Evidence from ' + repo_name)
            
            deps_file = repo_dir / 'dependencies.json'
            if deps_file.exists():
                with open(deps_file) as f:
                    deps = json.load(f)
                for dep in deps:
                    dep_name = dep.get('name', '')
                    dep_type = dep.get('type', 'library')
                    if dep_name:
                        store.upsert_technology(dep_name, dep_type)
                        store.link_project_to_technology(project_id, dep_name, 'dependency')
            
            ingested_count += 1
            print('  [OK] ' + repo_name)
            
        except Exception as e:
            print('  [FAIL] ' + repo_dir.name + ': ' + str(e))
    
    store.close()
    
    print('\n' + '=' * 60)
    print('Ingestion complete!')
    print('Total repos ingested: ' + str(ingested_count))
    print('=' * 60)
    
    store = Neo4jStore(config)
    store.connect()
    stats = store.get_stats()
    print('\nNeo4j Knowledge Graph Stats:')
    for key, value in stats.items():
        print('  ' + key + ': ' + str(value))
    store.close()

if __name__ == '__main__':
    ingest_all_data()