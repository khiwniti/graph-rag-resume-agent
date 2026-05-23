# -*- coding: utf-8 -*-
# Retry utilities and circuit breaker for production collectors
import time
import functools
from typing import Callable, Any, Optional, TypeVar, List, Type
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = 'closed'      # Normal operation
    OPEN = 'open'          # Failing, reject requests
    HALF_OPEN = 'half_open'  # Testing recovery


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    '''Circuit breaker pattern implementation for fault tolerance.'''
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        '''Execute function with circuit breaker protection.'''
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info('Circuit breaker entering HALF_OPEN state')
            else:
                raise CircuitBreakerOpenError(
                    f'Circuit breaker is OPEN. Last failure: {self.last_failure_time}'
                )
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    'Circuit breaker HALF_OPEN max calls exceeded'
                )
            self.half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        '''Handle successful call.'''
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                logger.info('Circuit breaker CLOSED after successful recovery')
    
    def _on_failure(self):
        '''Handle failed call.'''
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning('Circuit breaker OPEN after HALF_OPEN failure')
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f'Circuit breaker OPEN after {self.failure_count} failures')
    
    def _should_attempt_reset(self) -> bool:
        '''Check if enough time has passed to attempt reset.'''
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    def reset(self):
        '''Manually reset circuit breaker.'''
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    '''Raised when circuit breaker is open.'''
    pass


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    '''
    Decorator to add retry logic with exponential backoff.
    
    Args:
        config: Retry configuration
        on_retry: Optional callback for retry events (exception, attempt_number)
    '''
    retry_config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt == retry_config.max_attempts:
                        logger.error(
                            f'Retry exhausted for {func.__name__} after {attempt} attempts: {e}'
                        )
                        raise
                    
                    delay = calculate_retry_delay(attempt, retry_config)
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    logger.warning(
                        f'Retry {attempt}/{retry_config.max_attempts} for {func.__name__} '
                        f'in {delay:.1f}s due to: {e}'
                    )
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError('Retry logic error')
        
        return wrapper
    return decorator


def calculate_retry_delay(attempt: int, config: RetryConfig) -> float:
    '''Calculate delay for retry attempt with optional jitter.'''
    delay = min(
        config.base_delay * (config.exponential_base ** (attempt - 1)),
        config.max_delay
    )
    
    if config.jitter:
        import random
        # Add jitter between 0% and 25% of the delay
        jitter_amount = delay * random.uniform(0, 0.25)
        delay += jitter_amount
    
    return delay


def with_circuit_breaker(
    breaker: CircuitBreaker,
    fallback: Optional[Callable[..., Any]] = None
):
    '''
    Decorator to add circuit breaker protection.
    
    Args:
        breaker: CircuitBreaker instance
        fallback: Optional fallback function to call when circuit is open
    '''
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError:
                if fallback:
                    logger.info(f'Using fallback for {func.__name__} due to open circuit')
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(
                    f'Circuit breaker is open for {func.__name__}'
                )
        return wrapper
    return decorator


class BatchRetry:
    '''Handle batch operations with partial failure support.'''
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(
        self,
        items: List[Any],
        func: Callable[[Any], Any],
        max_failures: int = 0,
    ) -> tuple:
        '''
        Execute function on list of items with retry support.
        
        Args:
            items: List of items to process
            func: Function to apply to each item
            max_failures: Maximum allowed failures before stopping (0 = allow all failures)
        
        Returns:
            Tuple of (successful_results, failed_items)
        '''
        results = []
        failures = []
        
        for i, item in enumerate(items):
            try:
                result = with_retry(self.config)(func)(item)
                results.append(result)
            except Exception as e:
                logger.warning(f'Failed to process item {i}: {e}')
                failures.append({'item': item, 'error': str(e)})
                
                if max_failures > 0 and len(failures) >= max_failures:
                    logger.error(f'Max failures ({max_failures}) reached, stopping batch')
                    # Add remaining items to failures
                    for remaining in items[i + 1:]:
                        failures.append({'item': remaining, 'error': 'Not processed due to early termination'})
                    break
        
        return results, failures


# Pre-configured retry configs for different scenarios
RETRY_CONFIG_FAST = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=True,
)

RETRY_CONFIG_SLOW = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)

RETRY_CONFIG_API = RetryConfig(
    max_attempts=4,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_exceptions=(ConnectionError, TimeoutError, IOError),
)