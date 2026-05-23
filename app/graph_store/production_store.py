# -*- coding: utf-8 -*-
# Production-Ready Enhanced Neo4j Knowledge Graph Store
# Designed for comprehensive career intelligence following portfolio research blueprint
#
# Key Production Features:
# - StatCard data model (LOC, commits, PRs per language per project)
# - GitHub API integration for real-time metrics
# - Evidence-based skills (no percentage bars)
# - Project role transparency and outcomes tracking
# - Career timeline with phases
# - Accessibility and i18n support

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import os

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


# =============================================================================
# ENUMS - For type-safe, consistent naming (addresses research concern about
# hardcoded strings vs enum usage)
# =============================================================================

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


class ImpactLevel(Enum):
    HIGH = 'high'      # Platform/systems that solve complex real-world problems
    MEDIUM = 'medium'  # Production applications with measurable impact
    LOW = 'low'        # Demos, prototypes, experiments


class SeniorityLevel(Enum):
    JUNIOR = 'junior'
    MID = 'mid'
    SENIOR = 'senior'
    LEAD = 'lead'


# =============================================================================
# DATA CLASSES - For structured data modeling
# =============================================================================

@dataclass
class StatCardData:
    '''
    Statistical Summary Card (Stat Card) - per language per project
    Addresses the research requirement for granular, language-specific metrics:
    - Quantitative Output Metrics (LOC, commit frequency)
    - Architectural Responsibility Profile
    - Performance Impact Node
    - External Validation Anchors
    '''
    language: str
    project_id: str
    
    # Quantitative metrics
    lines_of_code: int = 0
    commit_count: int = 0
    pr_count: int = 0
    files_modified: int = 0
    
    # Percentage of total project
    percentage_of_project: float = 0.0
    
    # Context
    role_description: str = ''
    architectural_responsibility: str = ''
    performance_impact: str = ''
    
    # Evidence links
    sample_pr_urls: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    
    # Evidence-based proficiency (NOT percentage bars per research)
    evidence_sources: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'language': self.language,
            'lines_of_code': self.lines_of_code,
            'commit_count': self.commit_count,
            'percentage': round(self.percentage_of_project * 100, 1),
            'architectural_role': self.architectural_responsibility,
            'evidence_sources': self.evidence_sources[:3]  # Top 3
        }


@dataclass
class GitHubMetrics:
    '''
    API-Driven Components for GitHub Integration
    Real-time metrics from GitHub API (addresses research requirement for
    objective, empirical proof of skills)
    '''
    github_username: str = ''
    total_commits: int = 0
    total_prs_merged: int = 0
    total_issues_opened: int = 0
    total_stars: int = 0
    total_repos: int = 0
    contribution_streak_days: int = 0
    longest_streak_days: int = 0
    
    # Language distribution across all repos
    language_bytes: Dict[str, int] = field(default_factory=dict)
    language_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Top repositories by stars
    top_repos: List[Dict] = field(default_factory=list)
    
    # Last updated timestamp
    fetched_at: str = ''
    
    def to_dict(self) -> Dict:
        return {
            'commits': self.total_commits,
            'prs_merged': self.total_prs_merged,
            'issues_opened': self.total_issues_opened,
            'stars': self.total_stars,
            'contribution_streak': self.contribution_streak_days,
            'top_languages': list(self.language_percentages.keys())[:5],
            'top_repos': [r['name'] for r in self.top_repos[:3]]
        }


@dataclass
class ProjectOutcome:
    '''
    Project outcomes tracking - addresses research requirement for
    measurable business/technical outcomes, not just responsibilities
    '''
    metric_name: str = ''
    metric_value: str = ''
    metric_type: str = 'improvement'  # improvement, reduction, achievement
    
    def to_dict(self) -> Dict:
        return {
            'metric': self.metric_name,
            'value': self.metric_value,
            'type': self.metric_type
        }


@dataclass
class ProductionGraphConfig:
    '''Configuration for production deployment'''
    uri: str = 'bolt://localhost:7687'
    user: str = 'neo4j'
    password: str = ''
    database: str = 'neo4j'
    github_token: str = ''
    batch_size: int = 50  # Transaction batching for performance
    enable_i18n: bool = True
    accessibility_mode: bool = True


# =============================================================================
# PRODUCTION ENHANCED NEO4J STORE
# =============================================================================

class ProductionNeo4jStore:
    '''
    Production-ready Neo4j-based knowledge graph store.
    
    Enhanced Schema (addresses research blueprint):
    
    Node Types:
    - Person: Career entity with GitHub integration
    - Project: Work with role transparency, outcomes tracking
    - Skill: Evidence-based proficiency (NO percentage bars)
    - StatCard: Per-language metrics per project (LOC, commits, PRs)
    - GitHubMetrics: Real-time GitHub API data
    - Domain: Industry expertise areas
    - CareerPhase: Professional growth periods
    - TimelineEvent: Detailed career events
    
    Enhanced Relationships:
    - (:Person)-[:WORKED_ON]->(:Project) with role, impact, outcomes
    - (:Person)-[:MASTERED]->(:Skill) with evidence, NOT level percentages
    - (:Project)-[:HAS_STAT_CARD]->(:StatCard) per-language metrics
    - (:Person)-[:HAS_GITHUB_METRICS]->(:GitHubMetrics)
    - (:Project)-[:DEMONSTRATES]->(:Skill) with evidence links
    - (:Skill)-[:BUILDS_ON]->(:Skill) skill hierarchy
    '''

    # Node Labels
    PERSON = 'Person'
    PROJECT = 'Project'
    SKILL = 'Skill'
    STAT_CARD = 'StatCard'
    GITHUB_METRICS = 'GitHubMetrics'
    DOMAIN = 'Domain'
    CAREER_PHASE = 'CareerPhase'
    TIMELINE_EVENT = 'TimelineEvent'
    NARRATIVE = 'Narrative'
    TECHNOLOGY = 'Technology'

    def __init__(self, config: Optional[ProductionGraphConfig] = None):
        self.config = config or ProductionGraphConfig()
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

    # =========================================================================
    # SCHEMA CREATION - Production indexes and constraints
    # =========================================================================

    def create_production_schema(self) -> None:
        '''Create comprehensive indexes and constraints for production queries.'''
        indexes = [
            # Person indexes
            'CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)',
            'CREATE INDEX person_github IF NOT EXISTS FOR (p:Person) ON (p.github_username)',
            
            # Project indexes
            'CREATE INDEX project_id IF NOT EXISTS FOR (p:Project) ON (p.id)',
            'CREATE INDEX project_name IF NOT EXISTS FOR (p:Project) ON (p.name)',
            'CREATE INDEX project_domain IF NOT EXISTS FOR (p:Project) ON (p.domain)',
            'CREATE INDEX project_created IF NOT EXISTS FOR (p:Project) ON (p.created_at)',
            'CREATE INDEX project_impact IF NOT EXISTS FOR (p:Project) ON (p.impact_level)',
            
            # Skill indexes - unique constraint on name+category for hierarchical skills
            'CREATE INDEX skill_name IF NOT EXISTS FOR (s:Skill) ON (s.name)',
            'CREATE INDEX skill_category IF NOT EXISTS FOR (s:Skill) ON (s.category)',
            'CREATE CONSTRAINT skill_unique IF NOT EXISTS FOR (s:Skill) REQUIRE (s.name, s.category) IS UNIQUE',
            
            # StatCard indexes
            'CREATE INDEX statcard_project IF NOT EXISTS FOR (s:StatCard) ON (s.project_id)',
            'CREATE INDEX statcard_language IF NOT EXISTS FOR (s:StatCard) ON (s.language)',
            
            # GitHubMetrics
            'CREATE INDEX github_user IF NOT EXISTS FOR (g:GitHubMetrics) ON (g.username)',
            
            # Domain indexes
            'CREATE INDEX domain_name IF NOT EXISTS FOR (d:Domain) ON (d.name)',
            
            # Career Phase indexes
            'CREATE INDEX career_phase_person IF NOT EXISTS FOR (c:CareerPhase) ON (c.person_id)',
        ]
        
        with self.driver.session() as session:
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.debug('Index note: ' + str(e))
        
        logger.info('Created production Neo4j schema')

    def clear_graph(self) -> None:
        '''Clear all data from the graph.'''
        with self.driver.session() as session:
            session.run('MATCH (n) DETACH DELETE n')
        logger.info('Cleared all data from Neo4j')

    # =========================================================================
    # PERSON OPERATIONS - Enhanced with GitHub integration
    # =========================================================================

    def upsert_person(self, person_id: str, name: str, github_username: str = '',
                      email: str = '', title: str = '', location: str = '',
                      properties: Optional[Dict] = None) -> str:
        '''Create or update a Person with full career context.'''
        query = '''
        MERGE (p:Person {id: $person_id})
        SET p.name = $name,
            p.github_username = $github_username,
            p.email = $email,
            p.title = $title,
            p.location = $location,
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
            'title': title,
            'location': location,
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        return person_id

    def link_person_to_project(self, person_id: str, project_id: str,
                               role: str = 'Developer',
                               impact_level: str = 'medium',
                               team_size: int = 1,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> None:
        '''Link person to project with full role transparency (addresses research requirement for explicit role definition).'''
        query = '''
        MATCH (person:Person {id: $person_id})
        MATCH (project:Project {id: $project_id})
        MERGE (person)-[r:WORKED_ON]->(project)
        SET r.role = $role,
            r.impact_level = $impact_level,
            r.team_size = $team_size,
            r.start_date = $start_date,
            r.end_date = $end_date,
            r.updated_at = datetime(),
            r.started_at = coalesce(r.started_at, $start_date)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'person_id': person_id,
                'project_id': project_id,
                'role': role,
                'impact_level': impact_level,
                'team_size': team_size,
                'start_date': start_date,
                'end_date': end_date
            })

    # =========================================================================
    # PROJECT OPERATIONS - Enhanced with outcomes and role transparency
    # =========================================================================

    def upsert_project(self, project_id: str, name: str, source: str,
                       url: str = '', description: str = '',
                       domain: str = '', impact_level: str = 'medium',
                       role: str = 'Developer',
                       outcomes: Optional[List[Dict]] = None,
                       properties: Optional[Dict] = None) -> str:
        '''Create or update a Project with outcomes tracking.'''
        import json
        
        query = '''
        MERGE (p:Project {id: $project_id})
        SET p.name = $name,
            p.source = $source,
            p.url = $url,
            p.description = $description,
            p.domain = $domain,
            p.impact_level = $impact_level,
            p.primary_role = $role,
            p.updated_at = datetime(),
            p.created_at = coalesce(p.created_at, datetime())
        '''
        
        # Store outcomes as JSON string (Neo4j doesn't support nested objects)
        if outcomes:
            query += ', p.outcomes_json = $outcomes_json'
        
        props = properties or {}
        for key, value in props.items():
            query += ', p.' + key + ' = $' + key
        
        params = {
            'project_id': project_id,
            'name': name,
            'source': source,
            'url': url,
            'description': description[:1000] if description else '',
            'domain': domain,
            'impact_level': impact_level,
            'role': role,
            'outcomes_json': json.dumps(outcomes) if outcomes else '[]',
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        # Link to domain
        if domain:
            self.link_project_to_domain(project_id, domain)
        
        return project_id

    def add_project_outcome(self, project_id: str, outcome: Dict) -> None:
        '''Add a measurable outcome to a project.'''
        import json
        
        # Get existing outcomes and append new one
        query = '''
        MATCH (p:Project {id: $project_id})
        SET p.outcomes_json = coalesce(p.outcomes_json, '[]')
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'project_id': project_id})
            # Read current outcomes, append, and write back
            select_query = '''
            MATCH (p:Project {id: $project_id})
            RETURN p.outcomes_json as outcomes_json
            '''
            result = session.run(select_query, {'project_id': project_id}).single()
            if result:
                current = json.loads(result['outcomes_json']) if result['outcomes_json'] else []
                current.append(outcome)
                update_query = '''
                MATCH (p:Project {id: $project_id})
                SET p.outcomes_json = $outcomes
                '''
                session.run(update_query, {'project_id': project_id, 'outcomes': json.dumps(current)})

    def link_project_to_domain(self, project_id: str, domain: str) -> None:
        '''Link project to domain expertise area.'''
        self.upsert_domain(domain)
        
        query = '''
        MATCH (p:Project {id: $project_id})
        MATCH (d:Domain {name: $domain})
        MERGE (p)-[r:BELONGS_TO]->(d)
        '''
        
        with self.driver.session() as session:
            session.run(query, {'project_id': project_id, 'domain': domain})

    # =========================================================================
    # SKILL OPERATIONS - Evidence-based (NO percentage bars)
    # =========================================================================

    def upsert_skill(self, name: str, category: str,
                     evidence_count: int = 0,
                     years_experience: int = 0,
                     first_demonstrated: Optional[str] = None,
                     properties: Optional[Dict] = None) -> str:
        '''
        Create or update a Skill with EVIDENCE-BASED proficiency.
        
        NOTE: No mastery_level percentage! Per research: percentage bars are
        'technically meaningless (as there is no standard denominator for
        all of JavaScript), and broadly discouraged within the professional industry.'
        
        Instead, we track:
        - evidence_count: number of projects demonstrating this skill
        - years_experience: duration of skill usage
        - first_demonstrated: when skill was first used
        - evidence_sources: specific project/file references
        '''
        query = '''
        MERGE (s:Skill {name: $name, category: $category})
        SET s.evidence_count = $evidence_count,
            s.years_experience = $years_experience,
            s.first_demonstrated = coalesce($first_demonstrated, s.first_demonstrated),
            s.updated_at = datetime()
        '''
        
        props = properties or {}
        for key, value in props.items():
            query += ', s.' + key + ' = $' + key
        
        params = {
            'name': name,
            'category': category,
            'evidence_count': evidence_count,
            'years_experience': years_experience,
            'first_demonstrated': first_demonstrated,
            **props
        }
        
        with self.driver.session() as session:
            session.run(query, params)
        
        return name + ':' + category

    def link_person_skill_mastery(self, person_id: str, skill_name: str,
                                  skill_category: str,
                                  evidence_project: str = '',
                                  evidence_url: str = '') -> None:
        '''Link person to skill with EVIDENCE (not level percentage).'''
        query = '''
        MATCH (person:Person {id: $person_id})
        MATCH (skill:Skill {name: $skill_name, category: $skill_cat})
        MERGE (person)-[r:MASTERED]->(skill)
        SET r.evidence_project = $evidence_project,
            r.evidence_url = $evidence_url,
            r.demonstrated_at = coalesce(r.demonstrated_at, datetime()),
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'person_id': person_id,
                'skill_name': skill_name,
                'skill_cat': skill_category,
                'evidence_project': evidence_project,
                'evidence_url': evidence_url
            })

    def link_project_skill_demonstration(self, project_id: str,
                                        skill_name: str, skill_category: str,
                                        evidence_type: str = 'code',
                                        evidence_url: str = '',
                                        role_description: str = '') -> None:
        '''Link project to skill with specific evidence.'''
        query = '''
        MATCH (project:Project {id: $project_id})
        MATCH (skill:Skill {name: $skill_name, category: $skill_cat})
        MERGE (project)-[r:DEMONSTRATES]->(skill)
        SET r.evidence_type = $evidence_type,
            r.evidence_url = $evidence_url,
            r.role_description = $role_description,
            r.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'project_id': project_id,
                'skill_name': skill_name,
                'skill_cat': skill_category,
                'evidence_type': evidence_type,
                'evidence_url': evidence_url,
                'role_description': role_description
            })

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

    # =========================================================================
    # STAT CARD OPERATIONS - Per-language metrics per project
    # =========================================================================

    def upsert_stat_card(self, project_id: str, language: str,
                        lines_of_code: int = 0,
                        commit_count: int = 0,
                        pr_count: int = 0,
                        files_modified: int = 0,
                        percentage_of_project: float = 0.0,
                        architectural_role: str = '',
                        performance_impact: str = '',
                        key_files: Optional[List[str]] = None,
                        pr_urls: Optional[List[str]] = None) -> str:
        '''
        Create StatCard - per language per project metrics.
        Addresses research requirement for Statistical Summary Card sub-sub-component:
        - Quantitative Output Metrics (LOC, commit frequency)
        - Architectural Responsibility Profile
        - Performance Impact Node
        - External Validation Anchors
        '''
        statcard_id = 'statcard:' + project_id + ':' + language.lower().replace(' ', '_')
        
        query = '''
        MERGE (s:StatCard {id: $statcard_id})
        SET s.language = $language,
            s.project_id = $project_id,
            s.lines_of_code = $lines_of_code,
            s.commit_count = $commit_count,
            s.pr_count = $pr_count,
            s.files_modified = $files_modified,
            s.percentage_of_project = $percentage,
            s.architectural_role = $architectural_role,
            s.performance_impact = $performance_impact,
            s.key_files = $key_files,
            s.pr_urls = $pr_urls,
            s.updated_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'statcard_id': statcard_id,
                'language': language,
                'project_id': project_id,
                'lines_of_code': lines_of_code,
                'commit_count': commit_count,
                'pr_count': pr_count,
                'files_modified': files_modified,
                'percentage': percentage_of_project,
                'architectural_role': architectural_role,
                'performance_impact': performance_impact,
                'key_files': key_files or [],
                'pr_urls': pr_urls or []
            })
        
        # Link statcard to project
        self.link_stat_card_to_project(project_id, statcard_id)
        
        return statcard_id

    def link_stat_card_to_project(self, project_id: str, statcard_id: str) -> None:
        '''Link StatCard to Project.'''
        query = '''
        MATCH (p:Project {id: $project_id})
        MATCH (s:StatCard {id: $statcard_id})
        MERGE (p)-[r:HAS_STAT_CARD]->(s)
        '''
        
        with self.driver.session() as session:
            session.run(query, {'project_id': project_id, 'statcard_id': statcard_id})

    def get_project_stat_cards(self, project_id: str) -> List[Dict]:
        '''Get all StatCards for a project.'''
        query = '''
        MATCH (p:Project {id: $project_id})-[:HAS_STAT_CARD]->(s:StatCard)
        RETURN s.language as language,
               s.lines_of_code as loc,
               s.commit_count as commits,
               s.pr_count as prs,
               s.percentage_of_project as percentage,
               s.architectural_role as role,
               s.key_files as files
        ORDER BY s.lines_of_code DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'project_id': project_id})
            return [dict(record) for record in result]

    # =========================================================================
    # GITHUB METRICS OPERATIONS - Real-time GitHub API integration
    # =========================================================================

    def upsert_github_metrics(self, github_username: str,
                             total_commits: int = 0,
                             total_prs_merged: int = 0,
                             total_issues_opened: int = 0,
                             total_stars: int = 0,
                             total_repos: int = 0,
                             contribution_streak_days: int = 0,
                             longest_streak_days: int = 0,
                             language_bytes: Optional[Dict] = None,
                             language_percentages: Optional[Dict] = None,
                             top_repos: Optional[List[Dict]] = None) -> str:
        '''
        Store GitHub metrics from API integration.
        Addresses research requirement for:
        - GlobalStatCardContainer (commits, PRs, issues)
        - CommunityImpactNode (stars as peer validation)
        - ContributionStreakVisualizer
        - LanguageDistributionChart
        
        NOTE: Neo4j properties must be primitive types. Complex types (dicts, lists)
        are stored as JSON strings.
        '''
        import json
        
        query = '''
        MERGE (g:GitHubMetrics {username: $username})
        SET g.total_commits = $total_commits,
            g.total_prs_merged = $total_prs,
            g.total_issues_opened = $total_issues,
            g.total_stars = $total_stars,
            g.total_repos = $total_repos,
            g.contribution_streak_days = $streak_days,
            g.longest_streak_days = $longest_streak,
            g.language_bytes_json = $lang_bytes_json,
            g.language_percentages_json = $lang_percentages_json,
            g.top_repos_json = $top_repos_json,
            g.fetched_at = datetime()
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'username': github_username,
                'total_commits': total_commits,
                'total_prs': total_prs_merged,
                'total_issues': total_issues_opened,
                'total_stars': total_stars,
                'total_repos': total_repos,
                'streak_days': contribution_streak_days,
                'longest_streak': longest_streak_days,
                'lang_bytes_json': json.dumps(language_bytes) if language_bytes else '{}',
                'lang_percentages_json': json.dumps(language_percentages) if language_percentages else '{}',
                'top_repos_json': json.dumps(top_repos) if top_repos else '[]'
            })
        
        # Link to person
        person_query = '''
        MATCH (p:Person {github_username: $username})
        MATCH (g:GitHubMetrics {username: $username})
        MERGE (p)-[r:HAS_GITHUB_METRICS]->(g)
        '''
        
        try:
            with self.driver.session() as session:
                session.run(person_query, {'username': github_username})
        except Exception as e:
            logger.debug('Link to person note: ' + str(e))
        
        return github_username

    def get_github_metrics(self, github_username: str) -> Optional[Dict]:
        '''Get GitHub metrics for a user.'''
        import json
        
        query = '''
        MATCH (g:GitHubMetrics {username: $username})
        RETURN g.total_commits as commits,
               g.total_prs_merged as prs,
               g.total_issues_opened as issues,
               g.total_stars as stars,
               g.total_repos as repos,
               g.contribution_streak_days as streak,
               g.longest_streak_days as longest_streak,
               g.language_bytes_json as lang_bytes_json,
               g.language_percentages_json as lang_percentages_json,
               g.top_repos_json as top_repos_json,
               g.fetched_at as fetched_at
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'username': github_username}).single()
            if result:
                data = dict(result)
                # Parse JSON fields
                data['lang_bytes'] = json.loads(data['lang_bytes_json']) if data.get('lang_bytes_json') else {}
                data['lang_percentages'] = json.loads(data['lang_percentages_json']) if data.get('lang_percentages_json') else {}
                data['top_repos'] = json.loads(data['top_repos_json']) if data.get('top_repos_json') else []
                return data
            return None

    # =========================================================================
    # DOMAIN OPERATIONS
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
    # CAREER PHASE & TIMELINE OPERATIONS
    # =========================================================================

    def upsert_career_phase(self, person_id: str, phase_name: str,
                           start_year: int, end_year: Optional[int] = None,
                           description: str = '', domain: str = '',
                           key_achievements: Optional[List[str]] = None) -> str:
        '''
        Create a career phase for timeline tracking.
        Addresses research requirement for interactive timeline component.
        '''
        import json
        
        phase_id = 'phase:' + person_id + ':' + phase_name.lower().replace(' ', '-')
        
        query = '''
        MERGE (phase:CareerPhase {id: $phase_id})
        SET phase.name = $phase_name,
            phase.start_year = $start_year,
            phase.end_year = $end_year,
            phase.description = $description,
            phase.domain = $domain,
            phase.key_achievements_json = $achievements_json,
            phase.person_id = $person_id
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
                'domain': domain,
                'achievements_json': json.dumps(key_achievements) if key_achievements else '[]'
            })
        
        return phase_id

    def upsert_timeline_event(self, person_id: str, event_id: str,
                             title: str, event_type: str,
                             date: str, description: str = '',
                             tech_badges: Optional[List[str]] = None,
                             project_id: Optional[str] = None) -> str:
        '''Create a timeline event for detailed career history.'''
        query = '''
        MERGE (e:TimelineEvent {id: $event_id})
        SET e.title = $title,
            e.event_type = $event_type,
            e.date = $date,
            e.description = $description,
            e.tech_badges = $tech_badges,
            e.project_id = $project_id,
            e.person_id = $person_id
        WITH e
        MATCH (person:Person {id: $person_id})
        MERGE (person)-[r:HAS_EVENT]->(e)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'event_id': event_id,
                'person_id': person_id,
                'title': title,
                'event_type': event_type,
                'date': date,
                'description': description,
                'tech_badges': tech_badges or [],
                'project_id': project_id
            })
        
        return event_id

    # =========================================================================
    # NARRATIVE OPERATIONS - Career stories with impact
    # =========================================================================

    def upsert_narrative(self, narrative_id: str, text: str,
                        source_project_id: str,
                        impact_summary: str = '',
                        outcomes: Optional[List[str]] = None,
                        period_start: Optional[str] = None,
                        period_end: Optional[str] = None) -> str:
        '''Create career narrative with outcomes.'''
        import json
        
        query = '''
        MERGE (n:Narrative {id: $narrative_id})
        SET n.text = $text,
            n.impact_summary = $impact_summary,
            n.outcomes_json = $outcomes_json,
            n.period_start = $period_start,
            n.period_end = $period_end,
            n.updated_at = datetime()
        WITH n
        MATCH (p:Project {id: $project_id})
        MERGE (p)-[r:GENERATED_NARRATIVE]->(n)
        '''
        
        with self.driver.session() as session:
            session.run(query, {
                'narrative_id': narrative_id,
                'text': text,
                'project_id': source_project_id,
                'impact_summary': impact_summary,
                'outcomes_json': json.dumps(outcomes) if outcomes else '[]',
                'period_start': period_start,
                'period_end': period_end
            })
        
        return narrative_id

    # =========================================================================
    # TECHNOLOGY OPERATIONS
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
    # PRODUCTION QUERY OPERATIONS
    # =========================================================================

    def get_career_timeline(self, person_id: str) -> List[Dict]:
        '''Get complete career timeline with projects, skills, and roles.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)
        OPTIONAL MATCH (project)-[:BELONGS_TO]->(domain:Domain)
        OPTIONAL MATCH (project)-[:DEMONSTRATES]->(skill:Skill)
        OPTIONAL MATCH (project)-[:HAS_STAT_CARD]->(statcard:StatCard)
        RETURN project.id as project_id,
               project.name as name,
               project.domain as domain,
               project.description as description,
               project.primary_role as role,
               project.outcomes as outcomes,
               project.created_at as created_at,
               project.impact_level as impact_level,
               collect(DISTINCT skill.name) as skills,
               collect(DISTINCT statcard.language) as languages_with_metrics
        ORDER BY project.created_at DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            return [dict(record) for record in result]

    def get_skill_hierarchy(self, person_id: str) -> Dict[str, List[Dict]]:
        '''Get hierarchical skill map for person (evidence-based).'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:MASTERED]->(skill:Skill)
        OPTIONAL MATCH (child:Skill)-[:BUILDS_ON]->(skill)
        RETURN skill.name as skill_name,
               skill.category as category,
               skill.evidence_count as evidence_count,
               skill.years_experience as years,
               collect(DISTINCT child.name) as built_on_skills
        ORDER BY skill.evidence_count DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            
            hierarchy = {
                'languages': [],
                'frameworks': [],
                'tools': [],
                'platforms': [],
                'databases': [],
                'domains': []
            }
            
            for record in result:
                skill_data = {
                    'name': record['skill_name'],
                    'evidence_count': record['evidence_count'],
                    'years_experience': record['years'],
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
                elif cat == 'database':
                    hierarchy['databases'].append(skill_data)
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
        '''Get all evidence for a specific skill (per research: external validation anchors).'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)-[d:DEMONSTRATES]->(skill:Skill {name: $skill_name})
        RETURN project.id as project_id,
               project.name as project_name,
               project.primary_role as role,
               d.evidence_type as evidence_type,
               d.evidence_url as evidence_url,
               d.role_description as role_description,
               project.url as project_url,
               project.stars as stars
        ORDER BY project.stars DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id, 'skill_name': skill_name})
            return [dict(record) for record in result]

    def get_comprehensive_profile(self, person_id: str) -> Dict[str, Any]:
        '''Get comprehensive career profile for resume/portfolio.'''
        profile = {
            'person': None,
            'domains': [],
            'skills': {},
            'projects': [],
            'career_timeline': [],
            'github_metrics': None,
            'total_metrics': {}
        }
        
        # Get person info
        query = '''
        MATCH (p:Person {id: $person_id})
        RETURN p.name as name, 
               p.github_username as github,
               p.title as title,
               p.location as location
        '''
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id}).single()
            if result:
                profile['person'] = dict(result)
                # Get GitHub metrics
                if result['github']:
                    profile['github_metrics'] = self.get_github_metrics(result['github'])
        
        # Get domain expertise
        profile['domains'] = self.get_domain_expertise(person_id)
        
        # Get skill hierarchy
        profile['skills'] = self.get_skill_hierarchy(person_id)
        
        # Get career timeline
        profile['career_timeline'] = self.get_career_timeline(person_id)
        
        # Get stats
        profile['total_metrics'] = self.get_production_stats()
        
        return profile

    def get_production_stats(self) -> Dict[str, int]:
        '''Get comprehensive graph statistics for production.'''
        queries = {
            'total_persons': 'MATCH (p:Person) RETURN count(p) as count',
            'total_projects': 'MATCH (p:Project) RETURN count(p) as count',
            'total_skills': 'MATCH (s:Skill) RETURN count(s) as count',
            'total_stat_cards': 'MATCH (s:StatCard) RETURN count(s) as count',
            'total_domains': 'MATCH (d:Domain) RETURN count(d) as count',
            'total_technologies': 'MATCH (t:Technology) RETURN count(t) as count',
            'total_narratives': 'MATCH (n:Narrative) RETURN count(n) as count',
            'total_career_phases': 'MATCH (c:CareerPhase) RETURN count(c) as count',
            'total_timeline_events': 'MATCH (e:TimelineEvent) RETURN count(e) as count',
            'total_relationships': 'MATCH ()-[r]->() RETURN count(r) as count',
            'high_impact_projects': 'MATCH (p:Project {impact_level: \"high\"}) RETURN count(p) as count',
            'stars_total': 'MATCH (p:Project) RETURN sum(p.stars) as total',
        }
        
        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query).single()
                if result:
                    try:
                        stats[key] = result['count'] if 'count' in result.keys() else result[0]
                    except (KeyError, IndexError):
                        stats[key] = 0
                else:
                    stats[key] = 0
        
        return stats

    def get_career_progression(self, person_id: str) -> List[Dict]:
        '''Analyze career progression through projects.'''
        query = '''
        MATCH (person:Person {id: $person_id})-[:WORKED_ON]->(project:Project)
        OPTIONAL MATCH (project)-[:BELONGS_TO]->(domain:Domain)
        RETURN project.name as project,
               project.domain as primary_domain,
               project.primary_role as role,
               project.description as description,
               project.outcomes as outcomes,
               project.created_at as date,
               project.stars as stars,
               project.impact_level as impact
        ORDER BY project.created_at ASC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'person_id': person_id})
            return [dict(record) for record in result]

    def get_gap_analysis(self, person_id: str, target_domain: str) -> Dict[str, Any]:
        '''Analyze skill gaps for a target domain.'''
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

    def search_projects_by_skill_stack(self, skill_list: List[str]) -> List[Dict]:
        '''Find projects that demonstrate a set of skills.'''
        query = '''
        MATCH (project:Project)-[:DEMONSTRATES]->(skill:Skill)
        WHERE skill.name IN $skills
        WITH project, collect(skill.name) as matched_skills, count(skill) as skill_count
        WHERE skill_count >= size($skills) / 2
        OPTIONAL MATCH (project)-[:HAS_STAT_CARD]->(stat:StatCard)
        RETURN project.id as project_id,
               project.name as name,
               project.description as description,
               project.domain as domain,
               project.primary_role as role,
               matched_skills,
               skill_count,
               collect(stat.language) as languages_with_data
        ORDER BY skill_count DESC, project.stars DESC
        '''
        
        with self.driver.session() as session:
            result = session.run(query, {'skills': skill_list})
            return [dict(record) for record in result]