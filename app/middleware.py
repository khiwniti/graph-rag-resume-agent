# -*- coding: utf-8 -*-
# FastAPI middleware for production features: rate limiting, logging, error handling, auth
import time
import asyncio
import uuid
from typing import Callable, Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger, set_request_id, get_request_id, RequestLogger
from app.config_production import get_production_config


logger = get_logger(__name__)


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    '''Token bucket rate limiter implementation using asyncio-safe locks.'''
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.rpm = requests_per_minute
        self.burst_size = burst_size
        self.tokens_per_second = self.rpm / 60.0
        self.buckets: Dict[str, Dict] = defaultdict(self._create_bucket)
        self._lock = asyncio.Lock()
    
    def _create_bucket(self) -> Dict:
        return {
            'tokens': float(self.burst_size),
            'last_update': time.time(),
        }
    
    def _refill_bucket(self, bucket: Dict) -> None:
        now = time.time()
        elapsed = now - bucket['last_update']
        bucket['tokens'] = min(
            self.burst_size,
            bucket['tokens'] + elapsed * self.tokens_per_second
        )
        bucket['last_update'] = now
    
    async def is_allowed(self, key: str) -> bool:
        '''Check if request is allowed under rate limit (async-safe).'''
        async with self._lock:
            bucket = self.buckets[key]
            self._refill_bucket(bucket)
            
            if bucket['tokens'] >= 1.0:
                bucket['tokens'] -= 1.0
                return True
            return False
    
    async def get_retry_after(self, key: str) -> float:
        '''Get seconds until next request is allowed.'''
        async with self._lock:
            bucket = self.buckets[key]
            self._refill_bucket(bucket)
            
            if bucket['tokens'] >= 1.0:
                return 0.0
            
            tokens_needed = 1.0 - bucket['tokens']
            return tokens_needed / self.tokens_per_second


# Global rate limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        config = get_production_config()
        _rate_limiter = RateLimiter(
            requests_per_minute=config.rate_limit.requests_per_minute,
            burst_size=config.rate_limit.burst_size,
        )
    return _rate_limiter


# =============================================================================
# Request ID Middleware
# =============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    '''Middleware to add request ID to all requests.'''
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
        set_request_id(request_id)
        
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        
        return response


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    '''Middleware to log all requests with timing and status.'''
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_logger = RequestLogger(logger, get_request_id())
        
        # Log request start
        request_logger.log_request_start(
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request end
            request_logger.log_request_end(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            # Add timing header
            response.headers['X-Response-Time'] = f'{duration_ms:.1f}ms'
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            request_logger.log_error(e, context=f'{request.method} {request.url.path}')
            raise


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    '''Middleware to enforce rate limiting.'''
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        config = get_production_config()
        
        if not config.rate_limit.enabled:
            return await call_next(request)
        
        # Use client IP as rate limit key, fallback to header-based identifier
        client_key = request.client.host if request.client else 'unknown'
        
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_key = forwarded_for.split(',')[0].strip()
        
        rate_limiter = get_rate_limiter()
        
        if not await rate_limiter.is_allowed(client_key):
            retry_after = await rate_limiter.get_retry_after(client_key)
            
            return JSONResponse(
                status_code=429,
                headers={
                    'Retry-After': str(int(retry_after) + 1),
                    'X-RateLimit-Limit': str(config.rate_limit.requests_per_minute),
                    'X-RateLimit-Remaining': '0',
                },
                content={
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please retry after {int(retry_after) + 1} seconds.',
                    'retry_after': int(retry_after) + 1,
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers['X-RateLimit-Limit'] = str(config.rate_limit.requests_per_minute)
        
        return response


# =============================================================================
# API Key Authentication Middleware
# =============================================================================

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    '''Middleware to validate API key authentication.'''
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        '/', '/docs', '/openapi.json', '/health', '/redoc',
        '/health/detailed', '/health/ready', '/health/live'
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        config = get_production_config()
        
        # Skip auth if no API keys configured (development mode)
        if not config.security.api_keys:
            return await call_next(request)
        
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    'error': 'Authentication required',
                    'message': 'Please provide API key in X-API-Key header',
                }
            )
        
        if api_key not in config.security.api_keys:
            return JSONResponse(
                status_code=403,
                content={
                    'error': 'Invalid API key',
                    'message': 'The provided API key is not valid',
                }
            )
        
        return await call_next(request)


# =============================================================================
# Error Handling Middleware
# =============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    '''Middleware to handle exceptions uniformly.'''
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f'Unhandled exception: {str(e)}')
            
            return JSONResponse(
                status_code=500,
                content={
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred. Please try again later.',
                    'request_id': get_request_id(),
                }
            )


# =============================================================================
# CORS Middleware (Production-Ready)
# =============================================================================

def setup_cors(app: ASGIApp, config: Optional = None) -> None:
    '''Setup CORS with production configuration.'''
    if config is None:
        config = get_production_config()
    
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.cors_origins,
        allow_credentials=config.security.cors_allow_credentials,
        allow_methods=config.security.cors_allow_methods,
        allow_headers=config.security.cors_allow_headers,
    )


# =============================================================================
# Middleware Registration Helper
# =============================================================================

def register_middleware(app: ASGIApp) -> None:
    '''Register all production middleware in correct order.'''
    config = get_production_config()
    
    # Order matters: error handling first, then logging, then rate limiting, then auth
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    if config.rate_limit.enabled:
        app.add_middleware(RateLimitMiddleware)
    
    if config.security.api_keys:
        app.add_middleware(APIKeyAuthMiddleware)
    
    setup_cors(app, config)