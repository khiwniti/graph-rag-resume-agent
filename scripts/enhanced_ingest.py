#!/usr/bin/env python3
# Enhanced Ingestion Script - Build Intelligent Second Brain
# Optimized for comprehensive career representation
# Works with actual collected data: metadata.json + package.json

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph_store.enhanced_store import EnhancedNeo4jStore, EnhancedGraphConfig
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# ============================================================================
# TECHNOLOGY TAXONOMY - Comprehensive mapping for intelligent classification
# ============================================================================

# Skill taxonomy - maps technologies to categories and parent skills
SKILL_TAXONOMY = {
    # Languages (base skills)
    'typescript': {'category': 'language', 'parent': None},
    'javascript': {'category': 'language', 'parent': None},
    'python': {'category': 'language', 'parent': None},
    'java': {'category': 'language', 'parent': None},
    'go': {'category': 'language', 'parent': None},
    
    # AI/ML Frameworks & Libraries
    'langchain': {'category': 'library', 'parent': 'python'},
    'openai': {'category': 'library', 'parent': 'python'},
    'gemini': {'category': 'library', 'parent': 'python'},
    'anthropic': {'category': 'library', 'parent': 'python'},
    'tensorflow': {'category': 'library', 'parent': 'python'},
    'pytorch': {'category': 'library', 'parent': 'python'},
    'transformers': {'category': 'library', 'parent': 'python'},
    'gradio': {'category': 'library', 'parent': 'python'},
    'streamlit': {'category': 'library', 'parent': 'python'},
    
    # Frontend Frameworks
    'next': {'category': 'framework', 'parent': 'typescript'},
    'react': {'category': 'framework', 'parent': 'javascript'},
    'vue': {'category': 'framework', 'parent': 'javascript'},
    
    # Backend Frameworks
    'fastapi': {'category': 'framework', 'parent': 'python'},
    'django': {'category': 'framework', 'parent': 'python'},
    'flask': {'category': 'framework', 'parent': 'python'},
    'express': {'category': 'framework', 'parent': 'javascript'},
    
    # Databases
    'neo4j': {'category': 'database', 'parent': None},
    'postgresql': {'category': 'database', 'parent': None},
    'mongodb': {'category': 'database', 'parent': None},
    'firebase': {'category': 'database', 'parent': None},
    'redis': {'category': 'database', 'parent': None},
    
    # Cloud & DevOps
    'vercel': {'category': 'platform', 'parent': None},
    'cloudflare': {'category': 'platform', 'parent': None},
    'aws': {'category': 'platform', 'parent': None},
    'docker': {'category': 'platform', 'parent': None},
    
    # UI & Visualization
    'tailwind': {'category': 'tool', 'parent': None},
    'threejs': {'category': 'library', 'parent': 'javascript'},
    'mapbox': {'category': 'library', 'parent': 'javascript'},
}

# Domain classification based on keywords
DOMAIN_PATTERNS = {
    'ai_ml': {
        'keywords': ['ai', 'ml', 'agent', 'llm', 'gpt', 'gemini', 'claude', 'nlp', 'vision', 'chatbot', 'assistant', 'rag'],
        'tech_indicators': ['langchain', 'openai', 'gemini', 'anthropic', 'tensorflow', 'pytorch', 'gradio']
    },
    'web_development': {
        'keywords': ['web', 'frontend', 'backend', 'api', 'dashboard', 'ui'],
        'tech_indicators': ['next', 'react', 'vue', 'fastapi', 'django', 'express', 'tailwind']
    },
    'gis_mapping': {
        'keywords': ['gis', 'map', 'geo', 'spatial', 'facility', '3d'],
        'tech_indicators': ['mapbox', 'threejs']
    },
    'cloud_infrastructure': {
        'keywords': ['cloud', 'deploy', 'devops', 'infrastructure'],
        'tech_indicators': ['docker', 'vercel', 'cloudflare', 'aws']
    },
}


def extract_language_from_package(package_json: Dict) -> str:
    '''Extract programming language from package.json.'''
    deps = package_json.get('dependencies', {})
    dev_deps = package_json.get('devDependencies', {})
    all_deps = {**deps, **dev_deps}
    
    if 'typescript' in all_deps or 'ts-node' in all_deps:
        return 'TypeScript'
    if 'react' in all_deps or 'vue' in all_deps or 'express' in all_deps:
        return 'JavaScript'
    if 'fastapi' in all_deps or 'django' in all_deps:
        return 'Python'
    
    return 'JavaScript'


def extract_technologies(package_json: Dict) -> List[str]:
    '''Extract technology stack from package.json dependencies.'''
    deps = package_json.get('dependencies', {})
    dev_deps = package_json.get('devDependencies', {})
    all_deps = {**deps, **dev_deps}
    
    techs = []
    for dep in all_deps:
        normalized = dep.lower()
        for tech in SKILL_TAXONOMY:
            if tech in normalized or tech.replace('_', '') in normalized.replace('-', ''):
                if tech not in techs:
                    techs.append(tech)
    
    return techs[:20]


def classify_domain(description: str, name: str, techs: List[str]) -> str:
    '''Classify project domain based on description and technologies.'''
    combined = (description + ' ' + name).lower()
    scores = {}
    
    for domain, pattern in DOMAIN_PATTERNS.items():
        score = sum(1 for kw in pattern['keywords'] if kw in combined)
        score += sum(2 for t in pattern['tech_indicators'] if t in techs)
        if score > 0:
            scores[domain] = score
    
    return max(scores, key=scores.get) if scores else 'web_development'


def classify_impact(description: str, name: str, techs: List[str]) -> str:
    '''Classify project impact level.'''
    combined = (description + ' ' + name).lower()
    
    high_keywords = ['ai', 'agent', 'platform', 'system', 'studio', 'manager', 'assistant']
    if sum(1 for kw in high_keywords if kw in combined) >= 2:
        return 'high'
    if 'ai' in techs and len(techs) >= 3:
        return 'high'
    
    low_keywords = ['demo', 'poc', 'prototype', 'sample']
    if sum(1 for kw in low_keywords if kw in combined) >= 1:
        return 'low'
    
    return 'medium'


def get_skill_info(tech: str) -> Dict:
    '''Get skill category and parent from taxonomy.'''
    if tech in SKILL_TAXONOMY:
        return SKILL_TAXONOMY[tech]
    
    if tech in ['typescript', 'javascript', 'python', 'java', 'go']:
        return {'category': 'language', 'parent': None}
    if tech in ['react', 'vue', 'next']:
        return {'category': 'framework', 'parent': 'javascript'}
    
    return {'category': 'tool', 'parent': None}


def load_repo_data(repo_dir: Path) -> Dict:
    '''Load all available data for a repository.'''
    data = {'metadata': None, 'package_json': None}
    
    meta_file = repo_dir / 'metadata.json'
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                data['metadata'] = json.load(f)
        except Exception:
            pass
    
    pkg_file = repo_dir / 'package.json'
    if pkg_file.exists():
        try:
            with open(pkg_file) as f:
                data['package_json'] = json.load(f)
        except Exception:
            pass
    
    return data


def build_second_brain():
    '''Main function to build the intelligent second brain.'''
    print('=' * 70)
    print('BUILDING INTELLIGENT SECOND BRAIN')
    print('=' * 70)
    
    config = EnhancedGraphConfig(
        uri=NEO4J_URI or 'bolt://localhost:7687',
        user=NEO4J_USER or 'neo4j',
        password=NEO4J_PASSWORD or 'password'
    )
    
    store = EnhancedNeo4jStore(config)
    store.connect()
    store.create_enhanced_schema()
    
    print('\n[1/7] Clearing existing graph data...')
    store.clear_graph()
    
    person_id = 'person:kiwbrobrw'
    print('\n[2/7] Creating career profile...')
    store.upsert_person(
        person_id=person_id,
        name='Kittipong Eiamsakul',
        github_username='kiwbrobrw',
        email='',
        properties={'title': 'AI & Full-Stack Developer', 'location': 'Thailand'}
    )
    
    raw_dir = Path('data/raw')
    processed_count = 0
    skill_counts = {}
    domain_counts = {}
    tech_counts = {}
    
    print('\n[3/7] Processing repositories...')
    repo_dirs = [d for d in raw_dir.iterdir() if d.is_dir() and d.name != 'conversations']
    total = len(repo_dirs)
    
    for idx, repo_dir in enumerate(sorted(repo_dirs), 1):
        repo_data = load_repo_data(repo_dir)
        metadata = repo_data['metadata']
        package_json = repo_data['package_json']
        
        if metadata is None:
            continue
        
        try:
            repo_name = repo_dir.name
            project_id = 'project:' + repo_name
            
            name = metadata.get('name', repo_name.replace('-', ' ').replace('_', ' ').title())
            description = metadata.get('description', '')
            
            language = 'JavaScript'
            techs = []
            
            if package_json:
                language = extract_language_from_package(package_json)
                techs = extract_technologies(package_json)
            
            domain = classify_domain(description, name, techs)
            impact = classify_impact(description, name, techs)
            
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            store.upsert_project(
                project_id=project_id,
                name=name,
                source='github',
                url='https://github.com/kiwbrobrw/' + repo_name,
                description=description[:500] if description else '',
                domain=domain,
                impact_level=impact,
                properties={'language': language, 'technologies': ','.join(techs[:8])}
            )
            
            store.link_person_to_project(person_id, project_id, 'developer', impact)
            
            for tech in techs:
                tech_counts[tech] = tech_counts.get(tech, 0) + 1
            
            # Language skill
            lang_lower = language.lower()
            skill_counts[lang_lower] = skill_counts.get(lang_lower, 0) + 1
            
            store.upsert_skill(language, 'language', 0.8, skill_counts[lang_lower])
            store.link_person_skill_mastery(person_id, language, 'language', 0.8, 'Used in ' + name)
            store.link_project_skill_demonstration(project_id, language, 'language', 'Primary language')
            
            # Technology skills
            for tech in techs:
                info = get_skill_info(tech)
                cat = info['category']
                parent = info['parent']
                
                skill_counts[tech] = skill_counts.get(tech, 0) + 1
                
                store.upsert_skill(tech, cat, 0.7, skill_counts[tech])
                store.link_person_skill_mastery(person_id, tech, cat, 0.7, 'From ' + name)
                store.link_project_skill_demonstration(project_id, tech, cat, 'Dependency in package.json')
                
                if parent and parent in SKILL_TAXONOMY:
                    parent_cat = SKILL_TAXONOMY[parent]['category']
                    store.link_skill_hierarchy(tech, cat, parent, parent_cat)
            
            store.link_person_domain_expertise(person_id, domain, 'senior')
            
            for tech in techs:
                info = get_skill_info(tech)
                store.upsert_technology(tech, info['category'], domain)
                store.link_project_technology(project_id, tech, 'dependency')
            
            processed_count += 1
            
            if idx % 25 == 0:
                print('  Processed ' + str(idx) + '/' + str(total) + ' repos (' + str(processed_count) + ' with metadata)...')
                
        except Exception as e:
            logger.error('Error processing ' + repo_dir.name + ': ' + str(e))
            continue
    
    print('\n  Processed ' + str(processed_count) + ' repositories')
    
    # Career phases
    print('\n[4/7] Creating career timeline...')
    store.upsert_career_phase(person_id, 'Early Career', 2018, None, 'Web development foundation', 'web_development')
    store.upsert_career_phase(person_id, 'AI & ML Focus', 2020, None, 'Deep dive into AI/ML and agents', 'ai_ml')
    store.upsert_career_phase(person_id, 'Platform Engineering', 2023, None, 'Scalable platforms and multi-agent systems', 'cloud_infrastructure')
    
    # Narratives
    print('\n[5/7] Generating career narratives...')
    narratives_query = '''
    MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)
    WHERE project.impact_level = 'high' OR project.domain = 'ai_ml'
    RETURN project.id as id, project.name as name, project.description as description, project.domain as domain
    LIMIT 15
    '''
    
    narratives_created = 0
    with store.driver.session() as session:
        result = session.run(narratives_query, {'person_id': person_id})
        for record in result:
            try:
                nid = 'narrative:' + record['id']
                pname = record['name'] or 'this project'
                pdesc = (record['description'] or 'demonstrates expertise')[:200]
                pdomain = (record['domain'] or 'tech').replace('_', ' ')
                
                narrative_text = 'Built ' + pname + ': ' + pdesc + '. This ' + pdomain + ' project showcases production-ready systems with scalable architecture and AI integration.'
                
                store.upsert_narrative(nid, narrative_text, record['id'], pdesc[:100])
                narratives_created += 1
            except Exception as e:
                logger.debug('Narrative skipped: ' + str(e))
    
    print('  Generated ' + str(narratives_created) + ' career narratives')
    
    # Domain nodes
    print('\n[6/7] Creating domain nodes...')
    for domain, count in domain_counts.items():
        desc = domain.replace('_', ' ').title() + ' expertise - ' + str(count) + ' projects'
        store.upsert_domain(domain, desc, 'senior')
    
    store.close()
    
    # Stats
    print('\n[7/7] Computing final statistics...')
    store = EnhancedNeo4jStore(config)
    store.connect()
    
    print('\n' + '=' * 70)
    print('SECOND BRAIN BUILD COMPLETE')
    print('=' * 70)
    
    stats = store.get_enhanced_stats()
    print('\nGraph Statistics:')
    print('  Projects:', stats.get('total_projects', 0))
    print('  Skills:', stats.get('total_skills', 0))
    print('  Technologies:', stats.get('total_technologies', 0))
    print('  Domains:', stats.get('total_domains', 0))
    print('  Relationships:', stats.get('total_relationships', 0))
    
    print('\nDomain Expertise:')
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1])[:5]:
        print('  ' + domain.replace('_', ' ').title() + ': ' + str(count) + ' projects')
    
    print('\nTop Technologies:')
    for tech, count in sorted(tech_counts.items(), key=lambda x: -x[1])[:10]:
        print('  ' + tech.title() + ': ' + str(count) + ' projects')
    
    hierarchy = store.get_skill_hierarchy(person_id)
    print('\nSkill Hierarchy:')
    for cat, skills in hierarchy.items():
        if skills:
            print('  ' + cat.title() + ': ' + str(len(skills)) + ' skills')
    
    domains = store.get_domain_expertise(person_id)
    print('\nPerson Domain Expertise:')
    for d in domains[:5]:
        print('  ' + d['domain'].replace('_', ' ').title() + ': ' + str(d['project_count']) + ' projects')
    
    store.close()
    
    print('\n' + '=' * 70)
    print('Your intelligent second brain is ready!')
    print('=' * 70)


if __name__ == '__main__':
    build_second_brain()