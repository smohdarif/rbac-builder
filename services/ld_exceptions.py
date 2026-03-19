"""
LaunchDarkly Client Exceptions
==============================

Custom exceptions for LaunchDarkly API client errors.

This module defines a hierarchy of exceptions that map HTTP errors
to meaningful Python exceptions for easier error handling.

Exception Hierarchy:
    LDClientError (base)
    ├── LDAuthenticationError (401, 403)
    ├── LDNotFoundError (404)
    ├── LDConflictError (409)
    ├── LDRateLimitError (429)
    ├── LDValidationError (400)
    └── LDServerError (5xx)
"""

from typing import List, Dict, Any, Optional


# =============================================================================
# LESSON: Custom Exception Hierarchy
# =============================================================================
# Creating a hierarchy of exceptions allows:
# 1. Catching specific errors (LDConflictError)
# 2. Catching all API errors (LDClientError)
# 3. Adding extra data to exceptions (retry_after, errors list)


class LDClientError(Exception):
    """
    Base exception for all LaunchDarkly client errors.

    All other LD exceptions inherit from this, so you can catch
    LDClientError to handle any API error.

    Example:
        try:
            client.create_role(data)
        except LDClientError as e:
            print(f"API error: {e}")
    """
    pass


class LDAuthenticationError(LDClientError):
    """
    Authentication or authorization failed.

    Raised when:
    - API key is invalid (401 Unauthorized)
    - API key lacks required permissions (403 Forbidden)

    Example:
        try:
            client.list_projects()
        except LDAuthenticationError:
            print("Check your API key!")
    """
    pass


class LDNotFoundError(LDClientError):
    """
    Requested resource was not found.

    Raised when:
    - Project doesn't exist
    - Team doesn't exist
    - Role doesn't exist

    Example:
        try:
            client.list_environments("nonexistent-project")
        except LDNotFoundError:
            print("Project not found")
    """
    pass


class LDConflictError(LDClientError):
    """
    Resource already exists (conflict).

    Raised when:
    - Creating a role with a key that already exists
    - Creating a team with a key that already exists

    This is often expected behavior - you can skip existing resources.

    Example:
        try:
            client.create_role(role_data)
        except LDConflictError:
            print("Role already exists - skipping")
    """
    pass


class LDRateLimitError(LDClientError):
    """
    API rate limit exceeded.

    Raised when too many requests are made in a short time.
    The retry_after attribute tells you how long to wait.

    Attributes:
        retry_after: Seconds to wait before retrying

    Example:
        try:
            client.create_role(data)
        except LDRateLimitError as e:
            print(f"Rate limited, wait {e.retry_after} seconds")
            time.sleep(e.retry_after)
    """

    def __init__(self, retry_after: int = 60, message: str = ""):
        self.retry_after = retry_after
        msg = message or f"Rate limited. Retry after {retry_after} seconds."
        super().__init__(msg)


class LDValidationError(LDClientError):
    """
    Request data failed validation.

    Raised when the API rejects the request body due to:
    - Missing required fields
    - Invalid field values
    - Malformed policy syntax

    Attributes:
        errors: List of specific validation errors from API

    Example:
        try:
            client.create_role({"name": "Test"})  # Missing 'key'
        except LDValidationError as e:
            print(f"Validation failed: {e}")
            for error in e.errors:
                print(f"  - {error}")
    """

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        self.errors = errors or []
        super().__init__(message)


class LDServerError(LDClientError):
    """
    Server-side error (5xx status codes).

    Raised when LaunchDarkly's servers have an issue:
    - 500 Internal Server Error
    - 502 Bad Gateway
    - 503 Service Unavailable

    These are usually temporary - retry with backoff.

    Example:
        try:
            client.list_projects()
        except LDServerError:
            print("LaunchDarkly is having issues, try again later")
    """
    pass


# =============================================================================
# LESSON: Exception Factory Function
# =============================================================================
# A factory function creates the right exception type from HTTP status codes.
# This centralizes error mapping logic in one place.


def exception_from_response(
    status_code: int,
    message: str = "",
    response_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> LDClientError:
    """
    Create the appropriate exception from an HTTP response.

    Args:
        status_code: HTTP status code
        message: Error message (from response or default)
        response_body: Parsed JSON response body
        headers: Response headers (for Retry-After, etc.)

    Returns:
        Appropriate LDClientError subclass

    Example:
        if not response.ok:
            raise exception_from_response(
                response.status_code,
                response.json().get("message", "Unknown error"),
                response.json(),
                dict(response.headers)
            )
    """
    body = response_body or {}
    hdrs = headers or {}

    if status_code == 400:
        return LDValidationError(
            message or "Invalid request",
            errors=body.get("errors", [])
        )

    if status_code in (401, 403):
        return LDAuthenticationError(
            message or "Authentication failed"
        )

    if status_code == 404:
        return LDNotFoundError(
            message or "Resource not found"
        )

    if status_code == 409:
        return LDConflictError(
            message or "Resource already exists"
        )

    if status_code == 429:
        retry_after = int(hdrs.get("Retry-After", hdrs.get("retry-after", "60")))
        return LDRateLimitError(
            retry_after=retry_after,
            message=message
        )

    if status_code >= 500:
        return LDServerError(
            message or f"Server error (HTTP {status_code})"
        )

    # Default fallback
    return LDClientError(
        message or f"HTTP error {status_code}"
    )
