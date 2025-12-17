"""
Async HTTP Client Manager

Provides shared async HTTP clients with connection pooling and retry logic.
Used to replace synchronous requests calls throughout the application.
"""

import httpx
import asyncio
import logging
from typing import Optional, TypeVar, Callable, Awaitable

logger = logging.getLogger(__name__)

T = TypeVar('T')


class HTTPClientManager:
    """
    Manages shared HTTP clients for connection pooling.

    Provides separate clients for different services (Epicor, Graph API)
    with appropriate timeout and connection settings.
    """

    _epicor_client: Optional[httpx.AsyncClient] = None
    _graph_client: Optional[httpx.AsyncClient] = None
    _general_client: Optional[httpx.AsyncClient] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_epicor_client(cls) -> httpx.AsyncClient:
        """
        Get the Epicor API client with proper settings.

        Returns:
            Configured async HTTP client for Epicor API calls.
        """
        async with cls._lock:
            if cls._epicor_client is None or cls._epicor_client.is_closed:
                cls._epicor_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=10,
                        max_connections=20,
                        keepalive_expiry=30.0
                    ),
                    http2=True
                )
                logger.info("Epicor HTTP client initialized with connection pooling")
            return cls._epicor_client

    @classmethod
    async def get_graph_client(cls) -> httpx.AsyncClient:
        """
        Get the Microsoft Graph API client.

        Returns:
            Configured async HTTP client for Graph API calls.
        """
        async with cls._lock:
            if cls._graph_client is None or cls._graph_client.is_closed:
                cls._graph_client = httpx.AsyncClient(
                    base_url="https://graph.microsoft.com/v1.0",
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        max_connections=10,
                        keepalive_expiry=30.0
                    )
                )
                logger.info("Graph HTTP client initialized with connection pooling")
            return cls._graph_client

    @classmethod
    async def get_general_client(cls) -> httpx.AsyncClient:
        """
        Get a general-purpose HTTP client.

        Returns:
            Configured async HTTP client for general HTTP calls.
        """
        async with cls._lock:
            if cls._general_client is None or cls._general_client.is_closed:
                cls._general_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        max_connections=10
                    )
                )
                logger.info("General HTTP client initialized")
            return cls._general_client

    @classmethod
    async def close_all(cls):
        """
        Close all HTTP clients.

        Call this during application shutdown to properly release resources.
        """
        async with cls._lock:
            if cls._epicor_client and not cls._epicor_client.is_closed:
                await cls._epicor_client.aclose()
                logger.info("Epicor HTTP client closed")
            if cls._graph_client and not cls._graph_client.is_closed:
                await cls._graph_client.aclose()
                logger.info("Graph HTTP client closed")
            if cls._general_client and not cls._general_client.is_closed:
                await cls._general_client.aclose()
                logger.info("General HTTP client closed")

            cls._epicor_client = None
            cls._graph_client = None
            cls._general_client = None


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (httpx.TimeoutException, httpx.ConnectError)
) -> T:
    """
    Execute an async function with retry logic and exponential backoff.

    Args:
        func: Async function to execute.
        max_retries: Maximum number of retry attempts.
        retry_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.
        retryable_exceptions: Exception types that trigger a retry.

    Returns:
        Result from the function.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = retry_delay * (backoff_factor ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
        except httpx.HTTPStatusError as e:
            # Don't retry 4xx client errors
            if 400 <= e.response.status_code < 500:
                raise
            last_exception = e
            if attempt < max_retries - 1:
                delay = retry_delay * (backoff_factor ** attempt)
                logger.warning(
                    f"HTTP {e.response.status_code} (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay}s"
                )
                await asyncio.sleep(delay)

    raise last_exception


async def make_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    **kwargs
) -> httpx.Response:
    """
    Make an HTTP request with automatic retry on failure.

    Args:
        client: The httpx AsyncClient to use.
        method: HTTP method (GET, POST, PATCH, PUT, DELETE).
        url: URL to request.
        max_retries: Maximum retry attempts.
        **kwargs: Additional arguments passed to the request method.

    Returns:
        httpx.Response object.
    """
    async def _do_request():
        request_method = getattr(client, method.lower())
        response = await request_method(url, **kwargs)
        return response

    return await with_retry(_do_request, max_retries=max_retries)
