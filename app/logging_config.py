# -*- coding: utf-8 -*-
# Structured logging with request tracing for production
import logging
import sys
import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for request ID tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    '''Get current request ID from context.'''
    return request_id_var.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    '''Set request ID in context. Returns the ID.'''
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


class JSONFormatter(logging.Formatter):
    '''JSON log formatter for production.'''
    
    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available
        request_id = get_request_id()
        if request_id:
            log_data['request_id'] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else 'UnknownError',
                'message': str(record.exc_info[1]) if record.exc_info[1] else '',
            }
            if self.include_traceback:
                log_data['traceback'] = traceback.format_exception(*record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add process info
        log_data['process_id'] = record.process
        log_data['thread_id'] = record.thread
        
        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    '''Human-readable text formatter for development.'''
    
    def __init__(self, include_request_id: bool = True):
        super().__init__()
        self.include_request_id = include_request_id
    
    def format(self, record: logging.LogRecord) -> str:
        parts = [
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            f'[{record.levelname}]',
        ]
        
        if self.include_request_id:
            request_id = get_request_id()
            if request_id:
                parts.append(f'[{request_id}]')
        
        parts.extend([
            f'{record.name}',
            f'{record.module}:{record.lineno}',
            '-',
            record.getMessage(),
        ])
        
        # Add exception info if present
        if record.exc_info:
            parts.append('\n')
            parts.append(''.join(traceback.format_exception(*record.exc_info)))
        
        return ' '.join(str(p) for p in parts)


def setup_logging(
    level: str = 'INFO',
    format_type: str = 'json',
    include_request_id: bool = True,
    include_traceback: bool = True,
    logger_name: Optional[str] = None
) -> logging.Logger:
    '''Setup structured logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: Format type ('json' or 'text')
        include_request_id: Whether to include request ID in logs
        include_traceback: Whether to include full traceback in exception logs
        logger_name: Optional specific logger name
        
    Returns:
        Configured logger
    '''
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Set formatter
    if format_type == 'json':
        handler.setFormatter(JSONFormatter(include_traceback=include_traceback))
    else:
        handler.setFormatter(TextFormatter(include_request_id=include_request_id))
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    '''Get a logger with the given name.'''
    return logging.getLogger(name)


class LogContext:
    '''Context manager for adding temporary context to logs.'''
    
    def __init__(self, **context):
        self.context = context
        self._token = None
    
    def __enter__(self):
        # We store context in the logger's extra data
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class StructuredLogger:
    '''Logger wrapper that supports structured logging with extra data.'''
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, message: str, **kwargs):
        extra = {'extra_data': kwargs} if kwargs else None
        if extra:
            self.logger.log(level, message, extra=extra)
        else:
            self.logger.log(level, message)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self.logger.exception(message, extra={'extra_data': kwargs} if kwargs else None)


# Convenience function for creating structured loggers
def get_structured_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


# Initialize default logging
_default_logger_initialized = False


def init_default_logging():
    '''Initialize default logging configuration.'''
    global _default_logger_initialized
    if _default_logger_initialized:
        return
    
    setup_logging(level='INFO', format_type='json')
    _default_logger_initialized = True


# Request logging middleware helper
class RequestLogger:
    '''Helper for logging request lifecycle.'''
    
    def __init__(self, logger: logging.Logger, request_id: Optional[str] = None):
        self.logger = logger
        self.request_id = request_id or get_request_id()
    
    def log_request_start(self, method: str, path: str, **kwargs):
        # Standard library logging only supports structured fields via `extra=`.
        extra = {"method": method, "path": path, "request_id": self.request_id}
        if kwargs:
            extra.update(kwargs)
        self.logger.info(f"Request started: {method} {path}", extra=extra)

    def log_request_end(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        level = logging.INFO if status_code < 400 else logging.WARNING
        if status_code >= 500:
            level = logging.ERROR

        extra = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": self.request_id,
        }
        if kwargs:
            extra.update(kwargs)

        self.logger.log(
            level,
            f"Request completed: {method} {path} - {status_code} ({duration_ms:.1f}ms)",
            extra=extra,
        )

    def log_error(self, error: Exception, context: str = ''):
        extra = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_id": self.request_id,
        }
        self.logger.exception(
            f"Error in request: {context}" if context else "Error in request",
            extra=extra,
        )