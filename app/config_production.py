# -*- coding: utf-8 -*-
# Production configuration with validation and environment checks
import os
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class CollectionConfig(BaseModel):
    max_repos: int = Field(default=0, ge=0, description='Maximum repos to collect (0=all)')
    max_files_per_repo: int = Field(default=50, ge=1, le=500)
    max_file_bytes: int = Field(default=50000, ge=1024)
    max_commits_per_repo: int = Field(default=30, ge=1, le=100)
    include_forks: bool = False
    enable_conversation_collector: bool = False
    min_free_disk_gb: float = Field(default=5.0, ge=0.5)


class Neo4jConfig(BaseModel):
    uri: str = Field(default_factory=lambda: os.getenv('NEO4J_URI', 'bolt://localhost:7687'))
    user: str = Field(default_factory=lambda: os.getenv('NEO4J_USER', 'neo4j'))
    password: str = Field(default_factory=lambda: os.getenv('NEO4J_PASSWORD', ''))
    database: str = Field(default_factory=lambda: os.getenv('NEO4J_DATABASE', 'neo4j'))
    connection_timeout: int = Field(default=30, ge=1, le=300)
    max_connection_lifetime: int = Field(default=3600, ge=60)
    max_connection_pool_size: int = Field(default=50, ge=1, le=200)


class RateLimitConfig(BaseModel):
    enabled: bool = Field(default=True)
    requests_per_minute: int = Field(default=60, ge=1, le=1000)
    burst_size: int = Field(default=10, ge=1, le=100)


class SecurityConfig(BaseModel):
    api_keys: List[str] = Field(default_factory=list, description='Allowed API keys for authentication')
    cors_origins: List[str] = Field(default=['*'], description='Allowed CORS origins')
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default=['*'])
    cors_allow_headers: List[str] = Field(default=['*'])
    secret_key: Optional[str] = Field(default=None, description='Secret key for JWT/sessions')


class LoggingConfig(BaseModel):
    level: str = Field(default='INFO', description='Log level (DEBUG, INFO, WARNING, ERROR)')
    format: str = Field(default='json', description='Log format: json or text')
    include_request_id: bool = True
    include_traceback: bool = True


class VectorStoreConfig(BaseModel):
    dimension: int = Field(default=384, ge=64, le=4096)
    index_type: str = Field(default='flat', description='FAISS index type: flat, ivf, hnsw')
    nlist: int = Field(default=100, ge=10, description='Number of clusters for IVF')
    nprobe: int = Field(default=10, ge=1, description='Number of clusters to search')
    enable_compression: bool = Field(default=False)


class ProductionConfig(BaseModel):
    # Environment detection
    environment: str = Field(default_factory=lambda: os.getenv('ENVIRONMENT', 'development'))
    debug: bool = Field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes'))
    reload: bool = False
    
    # Sub-configurations
    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    
    # Server settings
    host: str = Field(default='0.0.0.0')
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=16)
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {'development', 'staging', 'production', 'test'}
        if v.lower() not in allowed:
            return 'development'
        return v.lower()
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'
    
    @property
    def should_reload(self) -> bool:
        return self.reload and not self.is_production


def load_production_config() -> ProductionConfig:
    '''Load production configuration from environment variables.'''
    
    collection = CollectionConfig(
        max_repos=int(os.getenv('MAX_REPOS', '0')),
        max_files_per_repo=int(os.getenv('MAX_FILES_PER_REPO', '50')),
        max_file_bytes=int(os.getenv('MAX_FILE_BYTES', '50000')),
        max_commits_per_repo=int(os.getenv('MAX_COMMITS_PER_REPO', '30')),
        include_forks=os.getenv('INCLUDE_FORKS', 'false').lower() in ('true', '1', 'yes'),
        enable_conversation_collector=os.getenv('ENABLE_CONVERSATION_COLLECTOR', 'false').lower() in ('true', '1', 'yes'),
        min_free_disk_gb=float(os.getenv('MIN_FREE_DISK_GB', '5.0')),
    )
    
    neo4j = Neo4jConfig(
        uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        user=os.getenv('NEO4J_USER', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD', ''),
        database=os.getenv('NEO4J_DATABASE', 'neo4j'),
        connection_timeout=int(os.getenv('NEO4J_CONNECTION_TIMEOUT', '30')),
        max_connection_lifetime=int(os.getenv('NEO4J_MAX_CONNECTION_LIFETIME', '3600')),
        max_connection_pool_size=int(os.getenv('NEO4J_POOL_SIZE', '50')),
    )
    
    rate_limit = RateLimitConfig(
        enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() in ('true', '1', 'yes'),
        requests_per_minute=int(os.getenv('RATE_LIMIT_RPM', '60')),
        burst_size=int(os.getenv('RATE_LIMIT_BURST', '10')),
    )
    
    # Parse API keys (comma-separated)
    api_keys_str = os.getenv('API_KEYS', '')
    api_keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    
    security = SecurityConfig(
        api_keys=api_keys,
        cors_origins=[o.strip() for o in os.getenv('CORS_ORIGINS', '*').split(',') if o.strip()],
        cors_allow_credentials=os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() in ('true', '1', 'yes'),
        secret_key=os.getenv('SECRET_KEY'),
    )
    
    logging_cfg = LoggingConfig(
        level=os.getenv('LOG_LEVEL', 'INFO').upper(),
        format=os.getenv('LOG_FORMAT', 'json'),
        include_request_id=os.getenv('LOG_INCLUDE_REQUEST_ID', 'true').lower() in ('true', '1', 'yes'),
        include_traceback=os.getenv('LOG_INCLUDE_TRACEBACK', 'true').lower() in ('true', '1', 'yes'),
    )
    
    vector_store = VectorStoreConfig(
        dimension=int(os.getenv('VECTOR_DIMENSION', '384')),
        index_type=os.getenv('VECTOR_INDEX_TYPE', 'flat'),
        nlist=int(os.getenv('VECTOR_NLIST', '100')),
        nprobe=int(os.getenv('VECTOR_NPROBE', '10')),
        enable_compression=os.getenv('VECTOR_COMPRESSION', 'false').lower() in ('true', '1', 'yes'),
    )
    
    return ProductionConfig(
        environment=os.getenv('ENVIRONMENT', 'development'),
        debug=os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes'),
        reload=os.getenv('RELOAD', 'false').lower() in ('true', '1', 'yes'),
        collection=collection,
        neo4j=neo4j,
        rate_limit=rate_limit,
        security=security,
        logging=logging_cfg,
        vector_store=vector_store,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', '8000')),
        workers=int(os.getenv('WORKERS', '1')),
    )


# Global singleton
_config: Optional[ProductionConfig] = None


def get_production_config() -> ProductionConfig:
    '''Get the global production configuration.'''
    global _config
    if _config is None:
        _config = load_production_config()
    return _config


def reload_config() -> ProductionConfig:
    '''Force reload of configuration.'''
    global _config
    _config = load_production_config()
    return _config