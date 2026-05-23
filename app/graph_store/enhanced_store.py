# -*- coding: utf-8 -*-
# Enhanced Neo4j Knowledge Graph Store - Optimized Second Brain System
# Designed for comprehensive career intelligence and talent representation

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import ServiceUnavailable, AuthError
    _NEO4J_AVAILABLE = True
except ImportError:
    GraphDatabase = None
    Driver = None
    ServiceUnavailable = Exception
    AuthError = Exception
    _NEO4J_AVAILABLE = False


class SkillCategory(Enum):
    LANGUAGE = 'language'
    FRAMEWORK = 'framework'
    LIBRARY = 'library'
    TOOL = 'tool'
    PLATFORM = 'platform'
    CLOUD = 'cloud'
    DATABASE = 'database'
    METHODOLOGY = 'methodology'
    DOMAIN = 'domain'


class Domain(Enum):
    AI_ML = 'ai_ml'
    WEB_DEVELOPMENT = 'web_development'
    CLOUD_INFRASTRUCTURE = 'cloud_infrastructure'
    DATA_ENGINEERING = 'data_engineering'
    IoT_EMBEDDED = 'iot_embedded'
    GIS_MAPPING = 'gis_mapping'
    SIMULATION = 'simulation'
    ENTERPRISE_SOFTWARE = 'enterprise_software'
    MOBILE = 'mobile'
    DEV_OPS = 'devops'


@dataclass
class EnhancedGraphConfig:
    uri: str = 'bolt://localhost:7687'
    user: str = 'neo4j'
    password: str = ''
    database: str = 'neo4j'


class EnhancedNeo4jStore:
    '''
    Enhanced Neo4j-based knowledge graph store optimized as a career second brain.
    
    Enhanced Schema:
    
    Node Types:
    - Person: Career entity with timeline and growth trajectory
    - Project: Work experience with impact metrics and evidence
    - Skill: Hierarchical skill with mastery levels and evidence
    - Technology: Tech stack components
    - Domain: Industry/domain expertise areas
    - Narrative: Career stories with context and impact
    - CareerPhase: Periods of professional growth
    
    Enhanced Relationships:
    - (:Person)-[:WORKED_ON]->(:Project) with role, duration, impact
    - (:Person)-[:MASTERED]->(:Skill) with level, years, evidence count
    - (:Person)-[:OPERATES_IN]->(:Domain) with seniority
    - (:Project)-[:DEMONSTRATES]->(:Skill) with specific evidence
    - (:Project)-[:BELONGS_TO]->(:Domain)
    - (:Skill)-[:BUILDS_ON]->(:Skill) skill hierarchy
    - (:Project)-[:PRECEDES]->(:Project) career progression
    '''

    # Enhanced Node Labels
    PERSON = 'Person'
    PROJECT = 'Project'
    SKILL = 'Skill'
    TECHNOLOGY = 'Technology'
    DOMAIN = 'Domain'
    NARRATIVE = 'Narrative'
    CAREER_PHASE = 'CareerPhase'

    def __init__(self, config: Optional[EnhancedGraphConfig] = None):
        self.config = config or EnhancedGraphConfig()
        self._driver: Optional[Driver] = None
        self._connected = False

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self.connect()
        return self._driver

    def connect(self) -> None:
        if self._connected:
            return
        if not _NEO4J_AVAILABLE:
            raise ImportError('neo4j package required')
        try:
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                database=self.config.database
            )
            with self._driver.session() as session:
                session.run('RETURN 1').single()
            self._connected = True
            logger.info('Connected to Neo4j at ' + self.config.uri)
        except Exception as e:
            logger.error('Neo4j connection failed: ' + str(e))
            raise

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_enhanced_schema(self) -> None:
        '''Create comprehensive indexes and constraints for intelligent queries.'''
        indexes = [
            # Person indexes
            'CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)',
            'CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.github_username)',
            
            # Project indexes
            'CREATE INDEX project_id IF NOT EXISTS FOR (p:Project) ON (p.id)',
            'CREATE INDEX project_name IF NOT EXISTS FOR (p:Project) ON (p.name)',
            'CREATE INDEX project_domain IF NOT EXISTS FOR (p:Project) ON (p.domain)',
            'CREATE INDEX project_created IF NOT EXISTS FOR (p:Project) ON (p.created_at)',
            'CREATE INDEX project_stars IF NOT EXISTS FOR (p:Project) ON (p.stars)',
            
            # Skill indexes
            'CREATE INDEX skill_name IF NOT EXISTS FOR (s:Skill) ON (s.name)',
            'CREATE INDEX skill_category IF NOT EXISTS FOR (s:Skill) ON (s.category)',
            'CREATE INDEX skill_mastery IF NOT EXISTS FOR (s:Skill) ON (s.mastery_level)',
            
            # Domain indexes
            'CREATE INDEX domain_name IF NOT EXISTS FOR (d:Domain) ON (d.name)',
            
            # Technology indexes
            'CREATE INDEX tech_name IF NOT EXISTS FOR (t:Technology) ON (t.name)',
        ]
        
        constraints = [
            'CREATE CONSTRAINT person_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE',
            'CREATE CONSTRAINT project_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE',
            'CREATE CONSTRAINT skill_unique IF NOT EXISTS FOR (s:Skill) REQUIRE (s.name, s.category) IS UNIQUE',
            'CREATE CONSTRAINT domain_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE',
        ]
        
        with self.driver.session() as session:
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.debug('Index note: ' + str(e))
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.debug('Constraint note: ' + str(e))
        
        logger.info('Created enhanced Neo4j schema')

    def clear_graph(self) -> None:
        '''Clear all data from the graph.'''
        with self.driver.session() as session:
            session.run('MATCH (n) DETACH DELETE n')
        logger.info('Cleared all data from Neo4j')

    # =========================================================================
    # Person Operations - Enhanced with career context
    # =========================================================================

    def upsert_person(self, person_id: str, name: str, github_username: str = '',
                      email: str = '', properties: Optional[Dict] = None) -> str:
        '''Create or update a Person with career context.'''
        query = '''
        MERGE (p:Person {id: $person_id})
        SET p.name = $name,
            p.github_username = $github_username,
            p.email = $email,
            p.updated_at = datetime(),
            p.created_at = coalesce(p.created_at, datetime())
        '''
        
        props = properties or {}
        for key, value in props.items():
            query += ', p.' + key + ' = $' + key
        
        params = {
            'person_id': person_id,
            'name': name,
            'github_username': github_username,
            'email': email,
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        return person_id

    def link_person_to_project(self, person_id: str, project_id: str,
                               role: str = 'developer',
                               impact_level: str = 'medium') -> None:
        '''Link person to project with role and impact.'''
        query = '''
        MATCH (person:Person {id: $person_id})
        MATCH (project:Project {id: $project_id})
        MERGE (person)-[r:WORKED_ON]->(project)
        SET r.role = $role,
            r.impact_level = $impact_level,
            r.started_at = coalesce(r.started_at, project.created_at),
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'person_id': person_id,
                'project_id': project_id,
                'role': role,
                'impact_level': impact_level
            })

    def upsert_career_phase(self, person_id: str, phase_name: str,
                           start_year: int, end_year: Optional[int] = None,
                           description: str = '', domain: str = '') -> str:
        '''Create a career phase for timeline tracking.'''
        phase_id = 'phase:' + person_id + ':' + phase_name.lower().replace(' ', '-')
        
        query = '''
        MERGE (phase:CareerPhase {id: $phase_id})
        SET phase.name = $phase_name,
            phase.start_year = $start_year,
            phase.end_year = $end_year,
            phase.description = $description,
            phase.domain = $domain
        WITH phase
        MATCH (person:Person {id: $person_id})
        MERGE (person)-[r:EXPERIENCED_THROUGH]->(phase)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'phase_id': phase_id,
                'person_id': person_id,
                'phase_name': phase_name,
                'start_year': start_year,
                'end_year': end_year,
                'description': description,
                'domain': domain
            })
        
        return phase_id

    # =========================================================================
    # Project Operations - Enhanced with impact metrics
    # =========================================================================

    def upsert_project(self, project_id: str, name: str, source: str,
                       url: str = '', description: str = '',
                       domain: str = '', impact_level: str = 'medium',
                       properties: Optional[Dict] = None) -> str:
        '''Create or update a Project with domain and impact classification.'''
        query = '''
        MERGE (p:Project {id: $project_id})
        SET p.name = $name,
            p.source = $source,
            p.url = $url,
            p.description = $description,
            p.domain = $domain,
            p.impact_level = $impact_level,
            p.updated_at = datetime(),
            p.created_at = coalesce(p.created_at, datetime())
        '''
        
        props = properties or {}
        for key, value in props.items():
            query += ', p.' + key + ' = $' + key
        
        params = {
            'project_id': project_id,
            'name': name,
            'source': source,
            'url': url,
            'description': description,
            'domain': domain,
            'impact_level': impact_level,
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        # Link to domain if specified
        if domain:
            self.link_project_to_domain(project_id, domain)
        
        return project_id

    def link_project_to_domain(self, project_id: str, domain: str) -> None:
        '''Link project to domain expertise area.'''
        # First ensure domain exists
        self.upsert_domain(domain)
        
        query = '''
        MATCH (p:Project {id: $project_id})
        MATCH (d:Domain {name: $domain})
        MERGE (p)-[r:BELONGS_TO]->(d)
        SET r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {'project_id': project_id, 'domain': domain})

    # =========================================================================
    # Skill Operations - Hierarchical with mastery tracking
    # =========================================================================

    def upsert_skill(self, name: str, category: str,
                     mastery_level: float = 0.5,
                     years_experience: int = 0,
                     evidence_count: int = 0,
                     properties: Optional[Dict] = None) -> str:
        '''Create or update a Skill with mastery and evidence tracking.'''
        query = '''
        MERGE (s:Skill {name: $name, category: $category})
        SET s.mastery_level = $mastery_level,
            s.years_experience = $years_experience,
            s.evidence_count = $evidence_count,
            s.updated_at = datetime()
        '''
        
        props = properties or {}
        for key, value in props.items():
            query += ', s.' + key + ' = $' + key
        
        params = {
            'name': name,
            'category': category,
            'mastery_level': mastery_level,
            'years_experience': years_experience,
            'evidence_count': evidence_count,
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        return name + ':' + category

    def link_skill_hierarchy(self, child_skill: str, child_category: str,
                            parent_skill: str, parent_category: str) -> None:
        '''Link skills in hierarchy (e.g., React -> JavaScript).'''
        query = '''
        MATCH (child:Skill {name: $child_name, category: $child_cat})
        MATCH (parent:Skill {name: $parent_name, category: $parent_cat})
        MERGE (child)-[r:BUILDS_ON]->(parent)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'child_name': child_skill,
                'child_cat': child_category,
                'parent_name': parent_skill,
                'parent_cat': parent_category
            })

    def link_person_skill_mastery(self, person_id: str, skill_name: str,
                                  skill_category: str, level: float,
                                  evidence: str = '') -> None:
        '''Link person to skill with mastery level.'''
        query = '''
        MATCH (person:Person {id: $person_id})
        MATCH (skill:Skill {name: $skill_name, category: $skill_cat})
        MERGE (person)-[r:MASTERED]->(skill)
        SET r.mastery_level = $level,
            r.evidence = $evidence,
            r.updated_at = datetime(),
            r.first_demonstrated = coalesce(r.first_demonstrated, datetime())
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'person_id': person_id,
                'skill_name': skill_name,
                'skill_cat': skill_category,
                'level': level,
                'evidence': evidence
            })

    def link_project_skill_demonstration(self, project_id: str,
                                        skill_name: str, skill_category: str,
                                        evidence: str = '') -> None:
        '''Link project to skill with evidence of demonstration.'''
        query = '''
        MATCH (project:Project {id: $project_id})
        MATCH (skill:Skill {name: $skill_name, category: $skill_cat})
        MERGE (project)-[r:DEMONSTRATES]->(skill)
        SET r.evidence = $evidence,
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'project_id': project_id,
                'skill_name': skill_name,
                'skill_cat': skill_category,
                'evidence': evidence
            })

    # =========================================================================
    # Domain Operations
    # =========================================================================

    def upsert_domain(self, name: str, description: str = '',
                      seniority: str = 'mid') -> str:
        '''Create or update a Domain node.'''
        query = '''
        MERGE (d:Domain {name: $name})
        SET d.description = $description,
            d.seniority = $seniority,
            d.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'name': name,
                'description': description,
                'seniority': seniority
            })
        
        return name

    def link_person_domain_expertise(self, person_id: str, domain: str,
                                     seniority: str = 'mid') -> None:
        '''Link person to domain with seniority level.'''
        query = '''
        MATCH (person:Person {id: $person_id})
        MATCH (d:Domain {name: $domain})
        MERGE (person)-[r:OPERATES_IN]->(d)
        SET r.seniority = $seniority,
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'person_id': person_id,
                'domain': domain,
                'seniority': seniority
            })

    # =========================================================================
    # Technology Operations
    # =========================================================================

    def upsert_technology(self, name: str, tech_type: str = 'library',
                          category: str = 'general') -> str:
        '''Create or update a Technology node.'''
        query = '''
        MERGE (t:Technology {name: $name})
        SET t.type = $tech_type,
            t.category = $category,
            t.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'name': name,
                'tech_type': tech_type,
                'category': category
            })
        
        return name

    def link_project_technology(self, project_id: str, tech_name: str,
                                evidence_type: str = 'dependency') -> None:
        '''Link project to technology with evidence type.'''
        query = '''
        MATCH (p:Project {id: $project_id})
        MATCH (t:Technology {name: $tech_name})
        MERGE (p)-[r:USES_TECHNOLOGY]->(t)
        SET r.evidence_type = $evidence_type,
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'project_id': project_id,
                'tech_name': tech_name,
                'evidence_type': evidence_type
            })

    # =========================================================================
    # Narrative Operations - Career stories
    # =========================================================================

    def upsert_narrative(self, narrative_id: str, text: str,
                        source_project_id: str,
                        impact_summary: str = '',
                        period_start: Optional[str] = None,
                        period_end: Optional[str] = None) -> str:
        '''Create career narrative linked to project.'''
        query = '''
        MERGE (n:Narrative {id: $narrative_id})
        SET n.text = $text,
            n.impact_summary = $impact_summary,
            n.period_start = $period_start,
            n.period_end = $period_end,
            n.updated_at = datetime()
        WITH n
        MATCH (p:Project {id: $project_id})
        MERGE (p)-[r:GENERATED_NARRATIVE]->(n)
        SET r.created_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'narrative_id': narrative_id,
                'text': text,
                'project_id': source_project_id,
                'impact_summary': impact_summary,
                'period_start': period_start,
                'period_end': period_end
            })
        
        return narrative_id

    def link_narrative_skill(self, narrative_id: str, skill_name: str,
                            skill_category: str) -> None:
        '''Link narrative to skills mentioned.'''
        query = '''
        MATCH (n:Narrative {id: $narrative_id})
        MATCH (s:Skill {name: $skill_name, category: $skill_cat})
        MERGE (n)-[r:HIGHLIGHTS_SKILL]->(s)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'narrative_id': narrative_id,
                'skill_name': skill_name,
                'skill_cat': skill_category
            })

    # =========================================================================
    # Intelligent Query Operations - Second Brain Capabilities
    # =========================================================================

    def get_career_timeline(self, person_id: str) -> List[Dict]:
        '''Get complete career timeline with projects and skills.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)
        OPTIONAL MATCH (project)-[:BELONGS_TO]->(domain:Domain)
        OPTIONAL MATCH (project)-[:DEMONSTRATES]->(skill:Skill)
        RETURN project.id as project_id,
               project.name as name,
               project.domain as domain,
               project.description as description,
               project.created_at as created_at,
               project.stars as stars,
               collect(DISTINCT skill.name) as skills,
               collect(DISTINCT domain.name) as domains
        ORDER BY project.created_at DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            return [dict(record) for record in result]

    def get_skill_hierarchy(self, person_id: str) -> Dict[str, List[Dict]]:
        '''Get hierarchical skill map for person.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:MASTERED]->(skill:Skill)
        OPTIONAL MATCH (child:Skill)-[:BUILDS_ON]->(skill)
        RETURN skill.name as skill_name,
               skill.category as category,
               skill.mastery_level as mastery_level,
               collect(DISTINCT child.name) as built_on_skills
        ORDER BY skill.mastery_level DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            
            hierarchy = {
                'languages': [],
                'frameworks': [],
                'tools': [],
                'platforms': [],
                'domains': []
            }
            
            for record in result:
                skill_data = {
                    'name': record['skill_name'],
                    'mastery': record['mastery_level'],
                    'builds_on': record['built_on_skills']
                }
                
                cat = record['category']
                if cat == 'language':
                    hierarchy['languages'].append(skill_data)
                elif cat in ['framework', 'library']:
                    hierarchy['frameworks'].append(skill_data)
                elif cat in ['tool', 'methodology']:
                    hierarchy['tools'].append(skill_data)
                elif cat in ['platform', 'cloud']:
                    hierarchy['platforms'].append(skill_data)
                elif cat == 'domain':
                    hierarchy['domains'].append(skill_data)
            
            return hierarchy

    def get_domain_expertise(self, person_id: str) -> List[Dict]:
        '''Get domain expertise with project counts and skill evidence.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:OPERATES_IN]->(domain:Domain)
        OPTIONAL MATCH (person)-[:WORKED_ON]->(project:Project)-[:BELONGS_TO]->(domain)
        OPTIONAL MATCH (project)-[:DEMONSTRATES]->(skill:Skill)
        RETURN domain.name as domain,
               domain.description as description,
               count(DISTINCT project) as project_count,
               collect(DISTINCT skill.name)[0..5] as top_skills
        ORDER BY count(DISTINCT project) DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            return [dict(record) for record in result]

    def get_skill_evidence(self, person_id: str, skill_name: str) -> List[Dict]:
        '''Get all evidence for a specific skill.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)-[d:DEMONSTRATES]->(skill:Skill {name: $skill_name})
        RETURN project.id as project_id,
               project.name as project_name,
               project.description as description,
               d.evidence as evidence,
               project.stars as stars
        ORDER BY project.stars DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id, 'skill_name': skill_name})
            return [dict(record) for record in result]

    def get_career_progression(self, person_id: str) -> List[Dict]:
        '''Analyze career progression through projects.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)
        OPTIONAL MATCH (project)-[:BELONGS_TO]->(domain:Domain)
        RETURN project.name as project,
               project.domain as primary_domain,
               project.description as description,
               project.created_at as date,
               project.stars as stars,
               project.impact_level as impact
        ORDER BY project.created_at ASC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            return [dict(record) for record in result]

    def get_comprehensive_profile(self, person_id: str) -> Dict[str, Any]:
        '''Get comprehensive career profile for resume/portfolio.'''
        profile = {
            'person': None,
            'domains': [],
            'skills': {},
            'projects': [],
            'career_timeline': [],
            'total_metrics': {}
        }
        
        # Get person info
        query = 'MATCH (p:Person {id: $person_id}) RETURN p.name as name, p.github_username as github'
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id}).single()
            if result:
                profile['person'] = dict(result)
        
        # Get domain expertise
        profile['domains'] = self.get_domain_expertise(person_id)
        
        # Get skill hierarchy
        profile['skills'] = self.get_skill_hierarchy(person_id)
        
        # Get career timeline
        profile['career_timeline'] = self.get_career_timeline(person_id)
        
        # Get stats
        profile['total_metrics'] = self.get_enhanced_stats()
        
        return profile

    def get_enhanced_stats(self) -> Dict[str, int]:
        '''Get comprehensive graph statistics.'''
        queries = {
            'total_persons': 'MATCH (p:Person) RETURN count(p) as count',
            'total_projects': 'MATCH (p:Project) RETURN count(p) as count',
            'total_skills': 'MATCH (s:Skill) RETURN count(s) as count',
            'total_domains': 'MATCH (d:Domain) RETURN count(d) as count',
            'total_technologies': 'MATCH (t:Technology) RETURN count(t) as count',
            'total_narratives': 'MATCH (n:Narrative) RETURN count(n) as count',
            'total_career_phases': 'MATCH (c:CareerPhase) RETURN count(c) as count',
            'total_relationships': 'MATCH ()-[r]->() RETURN count(r) as count',
            'high_impact_projects': 'MATCH (p:Project {impact_level: \"high\"}) RETURN count(p) as count',
            'stars_total': 'MATCH (p:Project) RETURN sum(p.stars) as total',
        }
        
        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query).single()
                if result:
                    # Handle both 'count' and direct value access
                    try:
                        stats[key] = result['count'] if 'count' in result.keys() else result[0]
                    except (KeyError, IndexError):
                        stats[key] = 0
                else:
                    stats[key] = 0
        
        return stats

    def search_by_skill_stack(self, skill_list: List[str]) -> List[Dict]:
        '''Find projects that demonstrate a set of skills.'''
        query = '''
        MATCH (project:Project)-[:DEMONSTRATES]->(skill:Skill)
        WHERE skill.name IN $skills
        WITH project, collect(skill.name) as matched_skills, count(skill) as skill_count
        WHERE skill_count >= size($skills) / 2
        RETURN project.id as project_id,
               project.name as name,
               project.description as description,
               project.domain as domain,
               matched_skills,
               skill_count
        ORDER BY skill_count DESC, project.stars DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'skills': skill_list})
            return [dict(record) for record in result]

    def get_gap_analysis(self, person_id: str, target_domain: str) -> Dict[str, Any]:
        '''Analyze skill gaps for a target domain.'''
        # Get skills in target domain
        query = '''
        MATCH (d:Domain {name: $domain})
        <-[r:BELONGS_TO]-(project:Project)-[:DEMONSTRATES]->(skill:Skill)
        WITH d, collect(DISTINCT skill.name) as domain_skills
        
        MATCH (person:Person {id: $person_id})-[:MASTERED]->(mastered:Skill)
        WITH d, domain_skills, collect(DISTINCT mastered.name) as person_skills
        
        RETURN domain_skills,
               person_skills,
               [s IN domain_skills WHERE NOT s IN person_skills] as gaps,
               [s IN domain_skills WHERE s IN person_skills] as coverage
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id, 'domain': target_domain}).single()
            if result:
                return {
                    'target_domain': target_domain,
                    'required_skills': result['domain_skills'],
                    'covered_skills': result['coverage'],
                    'skill_gaps': result['gaps'],
                    'coverage_percentage': len(result['coverage']) / len(result['domain_skills']) * 100 if result['domain_skills'] else 0
                }
            return {}