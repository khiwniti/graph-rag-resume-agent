# -*- coding: utf-8 -*-
# Health check system for production monitoring
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: Optional[datetime] = None


@dataclass
class SystemHealth:
    status: HealthStatus
    timestamp: datetime
    components: Dict[str, ComponentHealth]
    version: str = '1.0.0'
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'uptime_seconds': round(self.uptime_seconds, 2),
            'version': self.version,
            'components': {
                name: {
                    'status': comp.status.value,
                    'latency_ms': comp.latency_ms,
                    'message': comp.message,
                    'details': comp.details,
                    'last_check': comp.last_check.isoformat() if comp.last_check else None,
                }
                for name, comp in self.components.items()
            }
        }


class HealthChecker:
    '''System health checker for production use.'''
    
    def __init__(self):
        self._start_time = time.time()
        self._component_checkers: Dict[str, Callable] = {}
    
    def register_checker(self, name: str, checker: Callable) -> None:
        '''Register a health check function for a component.'''
        self._component_checkers[name] = checker
    
    async def check_all(self) -> SystemHealth:
        '''Run all health checks and return system status.'''
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, checker in self._component_checkers.items():
            try:
                start = time.time()
                result = await checker()
                latency_ms = (time.time() - start) * 1000
                
                if isinstance(result, ComponentHealth):
                    result.last_check = datetime.utcnow()
                    result.latency_ms = latency_ms
                    components[name] = result
                else:
                    # Assume simple boolean or status
                    status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                    components[name] = ComponentHealth(
                        name=name,
                        status=status,
                        latency_ms=latency_ms,
                        last_check=datetime.utcnow(),
                    )
            except Exception as e:
                logger.warning(f'Health check failed for {name}: {e}')
                components[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    last_check=datetime.utcnow(),
                )
        
        # Determine overall status
        statuses = [c.status for c in components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.UNKNOWN
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            components=components,
            uptime_seconds=time.time() - self._start_time,
        )


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# Pre-built health check functions
async def check_neo4j() -> ComponentHealth:
    '''Check Neo4j database connectivity with proper resource management.'''
    from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    
    driver = None
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            NEO4J_URI or 'bolt://localhost:7687',
            auth=(NEO4J_USER or 'neo4j', NEO4J_PASSWORD or ''),
            max_connection_lifetime=30,  # Short lifetime for health checks
        )
        with driver.session() as session:
            result = session.run('RETURN 1 as check').single()
            if result and result['check'] == 1:
                return ComponentHealth(
                    name='neo4j',
                    status=HealthStatus.HEALTHY,
                    message='Connected',
                )
    except Exception as e:
        return ComponentHealth(
            name='neo4j',
            status=HealthStatus.UNHEALTHY,
            message=f'Connection failed: {str(e)[:100]}',
        )
    finally:
        # Always close the driver to prevent connection leaks
        if driver:
            try:
                driver.close()
            except Exception:
                pass
    
    return ComponentHealth(
        name='neo4j',
        status=HealthStatus.UNKNOWN,
        message='Not configured',
    )


async def check_vector_store() -> ComponentHealth:
    '''Check FAISS vector store availability.'''
    from app.config import EMBEDDINGS_DIR
    
    try:
        import faiss
        index_path = EMBEDDINGS_DIR / 'faiss_index'
        
        if index_path.exists():
            index = faiss.read_index(str(index_path))
            return ComponentHealth(
                name='vector_store',
                status=HealthStatus.HEALTHY,
                message=f'Index loaded with {index.ntotal} vectors',
                details={'dimension': index.d, 'total_vectors': index.ntotal},
            )
        else:
            return ComponentHealth(
                name='vector_store',
                status=HealthStatus.DEGRADED,
                message='Index file not found (no data collected yet)',
            )
    except ImportError:
        return ComponentHealth(
            name='vector_store',
            status=HealthStatus.DEGRADED,
            message='FAISS not installed',
        )
    except Exception as e:
        return ComponentHealth(
            name='vector_store',
            status=HealthStatus.UNHEALTHY,
            message=f'Error: {str(e)[:100]}',
        )


async def check_disk_space() -> ComponentHealth:
    '''Check available disk space.'''
    import shutil
    from app.config import DATA_DIR, MIN_FREE_DISK_GB
    
    try:
        stat = shutil.disk_usage(DATA_DIR)
        free_gb = stat.free / (1024 ** 3)
        total_gb = stat.total / (1024 ** 3)
        used_percent = (stat.used / stat.total) * 100
        
        if free_gb < MIN_FREE_DISK_GB:
            return ComponentHealth(
                name='disk_space',
                status=HealthStatus.UNHEALTHY,
                message=f'Low disk space: {free_gb:.1f}GB free (minimum {MIN_FREE_DISK_GB}GB)',
                details={'free_gb': round(free_gb, 2), 'total_gb': round(total_gb, 2)},
            )
        elif free_gb < MIN_FREE_DISK_GB * 2:
            return ComponentHealth(
                name='disk_space',
                status=HealthStatus.DEGRADED,
                message=f'Moderate disk space: {free_gb:.1f}GB free',
                details={'free_gb': round(free_gb, 2), 'total_gb': round(total_gb, 2)},
            )
        else:
            return ComponentHealth(
                name='disk_space',
                status=HealthStatus.HEALTHY,
                message=f'Disk space OK: {free_gb:.1f}GB free ({used_percent:.1f}% used)',
                details={'free_gb': round(free_gb, 2), 'total_gb': round(total_gb, 2), 'used_percent': round(used_percent, 1)},
            )
    except Exception as e:
        return ComponentHealth(
            name='disk_space',
            status=HealthStatus.UNKNOWN,
            message=f'Could not check disk space: {str(e)[:100]}',
        )


async def check_api_keys() -> ComponentHealth:
    '''Check if required API keys are configured.'''
    from app.config import GITHUB_TOKEN, CLOUDFLARE_TOKEN, CLOUDFLARE_ACCOUNT_ID
    
    missing = []
    if not GITHUB_TOKEN:
        missing.append('GITHUB_TOKEN')
    if not CLOUDFLARE_TOKEN:
        missing.append('CLOUDFLARE_TOKEN')
    if not CLOUDFLARE_ACCOUNT_ID:
        missing.append('CLOUDFLARE_ACCOUNT_ID')
    
    if missing:
        return ComponentHealth(
            name='api_keys',
            status=HealthStatus.DEGRADED,
            message=f"Missing keys: {', '.join(missing)}",
            details={'missing': missing},
        )
    
    return ComponentHealth(
        name='api_keys',
        status=HealthStatus.HEALTHY,
        message='All required API keys configured',
    )


async def check_data_directory() -> ComponentHealth:
    '''Check if data directory and subdirectories exist.'''
    from app.config import DATA_DIR, RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR
    import os
    
    issues = []
    for dir_path in [DATA_DIR, RAW_DIR, GRAPH_DIR, EMBEDDINGS_DIR]:
        if not os.path.exists(dir_path):
            issues.append(f'{dir_path} does not exist')
    
    if issues:
        return ComponentHealth(
            name='data_directory',
            status=HealthStatus.DEGRADED,
            message='Some directories missing (will be created on collection)',
            details={'issues': issues},
        )
    
    return ComponentHealth(
        name='data_directory',
        status=HealthStatus.HEALTHY,
        message='All data directories present',
    )


def register_default_health_checks():
    '''Register standard health checks with the health checker.'''
    checker = get_health_checker()
    checker.register_checker('neo4j', check_neo4j)
    checker.register_checker('vector_store', check_vector_store)
    checker.register_checker('disk_space', check_disk_space)
    checker.register_checker('api_keys', check_api_keys)
    checker.register_checker('data_directory', check_data_directory)