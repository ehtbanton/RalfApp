from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .redis_client import redis_client
import time
import logging
from typing import Dict
import hashlib

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

        # Create rate limit key
        rate_limit_key = f"rate_limit:{client_ip}"

        try:
            # Check current request count
            current_requests = await redis_client.get(rate_limit_key)
            if current_requests is None:
                current_requests = 0

            if current_requests >= self.calls:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )

            # Increment counter
            await redis_client.set(rate_limit_key, current_requests + 1, expire=self.period)

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")

        response = await call_next(request)
        return response

class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cache_ttl: int = 300):  # 5 minutes default
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = ["GET"]

    def _generate_cache_key(self, request: Request) -> str:
        # Generate cache key from URL and query parameters
        key_parts = [request.url.path]
        if request.query_params:
            key_parts.append(str(request.query_params))

        # Include user info if authenticated
        if "authorization" in request.headers:
            auth_header = request.headers["authorization"]
            # Hash the token for privacy
            token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
            key_parts.append(token_hash)

        cache_key = "cache:" + hashlib.md5(":".join(key_parts).encode()).hexdigest()
        return cache_key

    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests to specific endpoints
        if (request.method not in self.cacheable_methods or
            not any(endpoint in request.url.path for endpoint in ["/api/videos", "/api/analysis"])):
            return await call_next(request)

        cache_key = self._generate_cache_key(request)

        try:
            # Try to get cached response
            cached_response = await redis_client.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {request.url.path}")
                return JSONResponse(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"],
                    headers=cached_response.get("headers", {})
                )

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")

        # Get fresh response
        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            try:
                if hasattr(response, 'body'):
                    import json
                    response_data = {
                        "content": json.loads(response.body.decode()),
                        "status_code": response.status_code,
                        "headers": dict(response.headers)
                    }
                    await redis_client.set(cache_key, response_data, expire=self.cache_ttl)
                    logger.info(f"Cached response for {request.url.path}")
            except Exception as e:
                logger.error(f"Cache storage error: {e}")

        return response

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Add Redis client to request state for easy access
        request.state.redis = redis_client
        response = await call_next(request)
        return response