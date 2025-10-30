"""Logging setup with loguru and request tracking."""

import uuid
import time
from typing import Callable
from fastapi import Request, Response
from loguru import logger


def setup_logging():
    """Configure loguru for the application."""
    logger.remove()  # Remove default handler
    
    def format_with_safe_request_id(record):
        """Format with safe handling of missing request_id."""
        request_id = record["extra"].get("request_id", "-")
        return f"{record['time']:YYYY-MM-DD HH:mm:ss} | {record['level']} | {record['name']}:{record['function']}:{record['line']} | {request_id} | {record['message']}"
    
    def format_console_with_safe_request_id(record):
        """Format console output with safe handling of missing request_id."""
        request_id = record["extra"].get("request_id", "-")
        return f"{record['time']:YYYY-MM-DD HH:mm:ss} | {record['level']} | {request_id} | {record['message']}\n"
    
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format=format_with_safe_request_id
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO", 
        format=format_console_with_safe_request_id
    )


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log requests with request ID tracking."""
    # Generate or get request ID
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    
    # Bind request ID to context
    with logger.contextualize(request_id=request_id):
        start_time = time.time()
        
        # Extract tenant/persona from query params if present
        tenant_id = request.query_params.get("tenant_id", "")
        persona_id = request.query_params.get("persona_id", "")
        
        logger.info(
            f"Started {request.method} {request.url.path} "
            f"tenant={tenant_id} persona={persona_id}"
        )
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            f"Completed {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-Id"] = request_id
        
        return response