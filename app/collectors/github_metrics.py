# -*- coding: utf-8 -*-
# GitHub API Integration for Real-Time Developer Metrics
# Addresses research requirement for API-driven components:
# - GlobalStatCardContainer (commits, PRs, issues)
# - CommunityImpactNode (stars as peer validation)
# - ContributionStreakVisualizer
# - LanguageDistributionChart

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class GitHubMetricsData:
    '''GitHub metrics data structure'''
    username: str = ''
    total_commits: int = 0
    total_prs_merged: int = 0
    total_issues_opened: int = 0
    total_stars: int = 0
    total_repos: int = 0
    contribution_streak_days: int = 0
    longest_streak_days: int = 0
    
    # Language distribution
    language_bytes: Dict[str, int] = field(default_factory=dict)
    language_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Top repositories
    top_repos: List[Dict] = field(default_factory=list)
    
    # Fetch timestamp
    fetched_at: str = ''


class GitHubMetricsCollector:
    '''
    GitHub API client for collecting real-time developer metrics.
    
    Addresses research requirements:
    1. GlobalStatCardContainer - fetches total commits, PRs merged, issues
    2. CommunityImpactNode - aggregates total stars across repos
    3. ContributionStreakVisualizer - analyzes commit history for streaks
    4. LanguageDistributionChart - generates language usage pie chart data
    '''
    
    GRAPHQL_API = 'https://api.github.com/graphql'
    REST_API = 'https://api.github.com'
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('GITHUB_TOKEN', '')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
    
    def get_user_metrics(self, username: str) -> GitHubMetricsData:
        '''
        Collect comprehensive GitHub metrics for a user.
        Uses both GraphQL (for detailed data) and REST (for fallback).
        '''
        metrics = GitHubMetricsData(username=username, fetched_at=datetime.now().isoformat())
        
        if not self.token:
            logger.warning('No GitHub token - using limited data collection')
            return self._get_basic_metrics(username, metrics)
        
        try:
            # Get user overview via GraphQL
            self._fetch_graphql_metrics(username, metrics)
            
            # Get contribution streaks
            self._fetch_contribution_streaks(username, metrics)
            
            # Get language distribution
            self._fetch_language_distribution(username, metrics)
            
            # Get top repositories
            self._fetch_top_repos(username, metrics)
            
        except Exception as e:
            logger.error(f'GitHub API error for {username}: {e}')
            # Fallback to basic REST data
            metrics = self._get_basic_metrics(username, metrics)
        
        return metrics
    
    def _fetch_graphql_metrics(self, username: str, metrics: GitHubMetricsData) -> None:
        '''Fetch detailed metrics via GraphQL API.'''
        query = '''
        query($login: String!) {
            user(login: $login) {
                contributionsCollection {
                    totalCommitContributions
                    totalPullRequestContributions
                    totalIssuesContributions
                }
                repositoryOwner {
                    ... on User {
                        repositories(first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
                            totalCount
                            nodes {
                                name
                                stargazerCount
                                primaryLanguage {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        '''
        
        variables = {'login': username}
        
        try:
            response = requests.post(
                self.GRAPHQL_API,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {}).get('user', {})
                
                if data:
                    contributions = data.get('contributionsCollection', {})
                    metrics.total_commits = contributions.get('totalCommitContributions', 0)
                    metrics.total_prs_merged = contributions.get('totalPullRequestContributions', 0)
                    metrics.total_issues_opened = contributions.get('totalIssuesContributions', 0)
                    
                    repos_data = data.get('repositoryOwner', {})
                    if repos_data:
                        metrics.total_repos = repos_data.get('repositories', {}).get('totalCount', 0)
            
        except Exception as e:
            logger.debug(f'GraphQL fetch error: {e}')
    
    def _fetch_contribution_streaks(self, username: str, metrics: GitHubMetricsData) -> None:
        '''Calculate contribution streaks from commit history.'''
        # Get contribution calendar for the past year
        query = '''
        query($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    contributionCalendar {
                        totalContributions
                        weeks {
                            contributionDays {
                                contributionCount
                                date
                            }
                        }
                    }
                }
            }
        }
        '''
        
        now = datetime.now()
        from_date = (now - timedelta(days=365)).isoformat() + 'Z'
        to_date = now.isoformat() + 'Z'
        
        variables = {'login': username, 'from': from_date, 'to': to_date}
        
        try:
            response = requests.post(
                self.GRAPHQL_API,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {}).get('user', {})
                if data:
                    calendar = data.get('contributionsCollection', {}).get('contributionCalendar', {})
                    weeks = calendar.get('weeks', [])
                    
                    current_streak = 0
                    longest_streak = 0
                    
                    for week in weeks:
                        days = week.get('contributionDays', [])
                        for day in days:
                            if day.get('contributionCount', 0) > 0:
                                current_streak += 1
                                longest_streak = max(longest_streak, current_streak)
                            else:
                                current_streak = 0
                    
                    metrics.contribution_streak_days = current_streak
                    metrics.longest_streak_days = longest_streak
                    
        except Exception as e:
            logger.debug(f'Contribution streak error: {e}')
    
    def _fetch_language_distribution(self, username: str, metrics: GitHubMetricsData) -> None:
        '''Get language distribution across repositories.'''
        query = '''
        query($login: String!) {
            user(login: $login) {
                repositories(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes {
                        primaryLanguage {
                            name
                        }
                        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
                            totalSize
                            edges {
                                size
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        '''
        
        variables = {'login': username}
        
        try:
            response = requests.post(
                self.GRAPHQL_API,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {}).get('user', {})
                if data:
                    repos = data.get('repositories', {}).get('nodes', [])
                    
                    lang_bytes = {}
                    for repo in repos:
                        languages = repo.get('languages', {}).get('edges', [])
                        for edge in languages:
                            lang_name = edge.get('node', {}).get('name', 'Unknown')
                            lang_size = edge.get('size', 0)
                            lang_bytes[lang_name] = lang_bytes.get(lang_name, 0) + lang_size
                    
                    metrics.language_bytes = lang_bytes
                    
                    # Calculate percentages
                    total = sum(lang_bytes.values())
                    if total > 0:
                        metrics.language_percentages = {
                            lang: round((size / total) * 100, 1)
                            for lang, size in sorted(lang_bytes.items(), key=lambda x: -x[1])
                        }
            
        except Exception as e:
            logger.debug(f'Language distribution error: {e}')
    
    def _fetch_top_repos(self, username: str, metrics: GitHubMetricsData) -> None:
        '''Get top repositories by stars.'''
        query = '''
        query($login: String!) {
            user(login: $login) {
                repositories(first: 20, orderBy: {field: STARGAZERS, direction: DESC}) {
                    nodes {
                        name
                        description
                        stargazerCount
                        forkCount
                        url
                    }
                }
            }
        }
        '''
        
        variables = {'login': username}
        
        try:
            response = requests.post(
                self.GRAPHQL_API,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {}).get('user', {})
                if data:
                    repos = data.get('repositories', {}).get('nodes', [])
                    metrics.top_repos = [
                        {
                            'name': r['name'],
                            'stars': r['stargazerCount'],
                            'forks': r['forkCount'],
                            'description': r.get('description', '')[:100],
                            'url': r['url']
                        }
                        for r in repos[:10]
                    ]
                    metrics.total_stars = sum(r['stargazerCount'] for r in metrics.top_repos)
            
        except Exception as e:
            logger.debug(f'Top repos error: {e}')
    
    def _get_basic_metrics(self, username: str, metrics: GitHubMetricsData) -> GitHubMetricsData:
        '''Fallback method using REST API when GraphQL fails.'''
        try:
            # Get user info
            user_response = requests.get(
                f'{self.REST_API}/users/{username}',
                headers=self.headers,
                timeout=10
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                metrics.total_repos = user_data.get('public_repos', 0)
            
            # Get repos
            repos_response = requests.get(
                f'{self.REST_API}/users/{username}/repos',
                headers=self.headers,
                params={'sort': 'updated', 'per_page': 100},
                timeout=10
            )
            
            if repos_response.status_code == 200:
                repos = repos_response.json()
                metrics.total_stars = sum(r.get('stargazer_count', 0) for r in repos)
                
                for repo in repos:
                    lang = repo.get('language')
                    if lang:
                        metrics.language_bytes[lang] = metrics.language_bytes.get(lang, 0) + 1
                
                # Calculate percentages
                total = sum(metrics.language_bytes.values())
                if total > 0:
                    metrics.language_percentages = {
                        lang: round((count / total) * 100, 1)
                        for lang, count in sorted(metrics.language_bytes.items(), key=lambda x: -x[1])
                    }
                
                metrics.top_repos = [
                    {
                        'name': r['name'],
                        'stars': r.get('stargazer_count', 0),
                        'forks': r.get('fork_count', 0),
                        'description': r.get('description', '')[:100],
                        'url': r['html_url']
                    }
                    for r in sorted(repos, key=lambda x: x.get('stargazer_count', 0), reverse=True)[:10]
                ]
            
        except Exception as e:
            logger.error(f'Basic metrics error: {e}')
        
        return metrics
    
    def get_repo_language_stats(self, username: str, repo_name: str) -> Dict[str, int]:
        '''Get per-repository language statistics (for StatCard per-project data).'''
        try:
            response = requests.get(
                f'{self.REST_API}/repos/{username}/{repo_name}/languages',
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.debug(f'Repo language stats error: {e}')
        
        return {}
    
    def get_repo_commit_history(self, username: str, repo_name: str) -> List[Dict]:
        '''Get commit history for a repository (for StatCard commit counts).'''
        commits = []
        try:
            response = requests.get(
                f'{self.REST_API}/repos/{username}/{repo_name}/commits',
                headers=self.headers,
                params={'per_page': 100},
                timeout=10
            )
            
            if response.status_code == 200:
                for commit in response.json():
                    commits.append({
                        'sha': commit.get('sha', '')[:7],
                        'message': commit.get('commit', {}).get('message', '').split('\n')[0][:80],
                        'date': commit.get('commit', {}).get('author', {}).get('date', ''),
                        'author': commit.get('commit', {}).get('author', {}).get('name', '')
                    })
            
        except Exception as e:
            logger.debug(f'Commit history error: {e}')
        
        return commits
    
    def get_pull_requests(self, username: str, repo_name: str) -> List[Dict]:
        '''Get merged PRs for a repository (for StatCard PR counts).'''
        prs = []
        try:
            response = requests.get(
                f'{self.REST_API}/repos/{username}/{repo_name}/pulls',
                headers=self.headers,
                params={'state': 'closed', 'per_page': 100},
                timeout=10
            )
            
            if response.status_code == 200:
                for pr in response.json():
                    if pr.get('merged_at'):
                        prs.append({
                            'number': pr.get('number'),
                            'title': pr.get('title', '')[:80],
                            'merged_at': pr.get('merged_at'),
                            'url': pr.get('html_url')
                        })
            
        except Exception as e:
            logger.debug(f'PR history error: {e}')
        
        return prs


def collect_and_store_github_metrics(github_username: str, store) -> GitHubMetricsData:
    '''
    Collect GitHub metrics and store in the production knowledge graph.
    
    This addresses the research requirement for:
    - Real-time developer statistics that auto-update
    - Objective, empirical proof of passion and consistency
    - Dynamic GitHub metrics embedded in the portfolio
    '''
    token = os.getenv('GITHUB_TOKEN', '')
    collector = GitHubMetricsCollector(token)
    
    metrics = collector.get_user_metrics(github_username)
    
    # Store in graph using production store's GitHubMetrics format
    # Note: We need to pass raw parameters, not a dataclass instance
    store.upsert_github_metrics(
        github_username,
        total_commits=metrics.total_commits,
        total_prs_merged=metrics.total_prs_merged,
        total_issues_opened=metrics.total_issues_opened,
        total_stars=metrics.total_stars,
        total_repos=metrics.total_repos,
        contribution_streak_days=metrics.contribution_streak_days,
        longest_streak_days=metrics.longest_streak_days,
        language_bytes=metrics.language_bytes,
        language_percentages=metrics.language_percentages,
        top_repos=metrics.top_repos
    )
    
    return metrics