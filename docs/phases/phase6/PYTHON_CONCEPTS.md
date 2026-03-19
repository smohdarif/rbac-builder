# Phase 6: Python Concepts - HTTP Requests & API Clients

## Table of Contents

1. [HTTP Requests with `requests` Library](#1-http-requests-with-requests-library)
2. [REST API Concepts](#2-rest-api-concepts)
3. [Abstract Base Classes (ABC)](#3-abstract-base-classes-abc)
4. [Custom Exceptions](#4-custom-exceptions)
5. [Retry Logic and Backoff](#5-retry-logic-and-backoff)
6. [Session Management](#6-session-management)
7. [Testing HTTP Clients](#7-testing-http-clients)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. HTTP Requests with `requests` Library

### What is the `requests` library?

The `requests` library is Python's most popular HTTP client. It makes API calls simple and readable.

### Installation

```bash
pip install requests
```

### Basic Usage

```python
import requests

# =============================================================================
# LESSON: Basic HTTP Methods
# =============================================================================
# HTTP has different methods for different operations:
# - GET: Read data
# - POST: Create data
# - PUT: Replace data
# - PATCH: Partial update
# - DELETE: Remove data

# GET request - retrieve data
response = requests.get("https://api.example.com/users")

# POST request - create data
response = requests.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"}
)

# PATCH request - update data
response = requests.patch(
    "https://api.example.com/users/123",
    json={"name": "Alice Smith"}
)

# DELETE request - remove data
response = requests.delete("https://api.example.com/users/123")
```

### Working with Responses

```python
# =============================================================================
# LESSON: Response Object
# =============================================================================
# The response object contains all HTTP response data

response = requests.get("https://api.example.com/users")

# Status code (200 = OK, 404 = Not Found, etc.)
print(response.status_code)  # 200

# Check if successful (status 200-299)
print(response.ok)  # True

# Get JSON body (most APIs return JSON)
data = response.json()  # {"users": [...]}

# Get raw text
text = response.text  # '{"users": [...]}'

# Get headers
print(response.headers["Content-Type"])  # "application/json"
```

### Headers and Authentication

```python
# =============================================================================
# LESSON: Custom Headers
# =============================================================================
# APIs often require headers for authentication and content type

headers = {
    "Authorization": "Bearer your-api-key",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

response = requests.get(
    "https://api.example.com/users",
    headers=headers
)

# LaunchDarkly uses a simple API key header
headers = {
    "Authorization": "api-key-xxxxx"  # No "Bearer" prefix
}
```

### Timeout Handling

```python
# =============================================================================
# LESSON: Timeouts
# =============================================================================
# Always set timeouts to prevent hanging requests!
# Without timeout, request can hang forever if server doesn't respond

try:
    # Timeout after 30 seconds
    response = requests.get(
        "https://api.example.com/users",
        timeout=30
    )
except requests.Timeout:
    print("Request timed out!")
```

### Error Handling

```python
# =============================================================================
# LESSON: Request Exceptions
# =============================================================================
# Requests can fail in various ways - handle each appropriately

import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
    RequestException
)

try:
    response = requests.get("https://api.example.com/users", timeout=30)
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx

except ConnectionError:
    print("Could not connect to server")

except Timeout:
    print("Request timed out")

except HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")

except RequestException as e:
    print(f"Request failed: {e}")
```

---

## 2. REST API Concepts

### What is REST?

REST (Representational State Transfer) is a pattern for designing web APIs.

```
┌─────────────────────────────────────────────────────────────────┐
│                      REST API Structure                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  URL Pattern: /api/v2/{resource}/{id}                          │
│                                                                 │
│  Examples:                                                      │
│    GET    /api/v2/projects           → List all projects       │
│    GET    /api/v2/projects/mobile    → Get one project         │
│    POST   /api/v2/projects           → Create project          │
│    PATCH  /api/v2/projects/mobile    → Update project          │
│    DELETE /api/v2/projects/mobile    → Delete project          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### HTTP Status Codes

```python
# =============================================================================
# LESSON: HTTP Status Codes
# =============================================================================
# Status codes tell you what happened with your request

STATUS_CODES = {
    # Success (2xx)
    200: "OK - Request succeeded",
    201: "Created - Resource created",
    204: "No Content - Success with no body",

    # Client Errors (4xx)
    400: "Bad Request - Invalid data sent",
    401: "Unauthorized - Authentication required",
    403: "Forbidden - Not allowed",
    404: "Not Found - Resource doesn't exist",
    409: "Conflict - Resource already exists",
    429: "Too Many Requests - Rate limited",

    # Server Errors (5xx)
    500: "Internal Server Error - Server problem",
    502: "Bad Gateway - Upstream server error",
    503: "Service Unavailable - Server overloaded",
}
```

### JSON Patch (for PATCH requests)

```python
# =============================================================================
# LESSON: JSON Patch Format
# =============================================================================
# LaunchDarkly uses JSON Patch (RFC 6902) for PATCH requests
# This is an array of operations to apply

# Add a value
patch = [
    {"op": "add", "path": "/customRoleKeys/-", "value": "new-role"}
]

# Replace a value
patch = [
    {"op": "replace", "path": "/description", "value": "New description"}
]

# Remove a value
patch = [
    {"op": "remove", "path": "/customRoleKeys/0"}
]

# Multiple operations
patch = [
    {"op": "replace", "path": "/name", "value": "New Name"},
    {"op": "add", "path": "/customRoleKeys/-", "value": "extra-role"}
]

# Making the request
response = requests.patch(
    "https://app.launchdarkly.com/api/v2/teams/my-team",
    headers={"Authorization": "api-key-xxx"},
    json=patch
)
```

---

## 3. Abstract Base Classes (ABC)

### What is an ABC?

An Abstract Base Class defines a "contract" that subclasses must follow.

```python
# =============================================================================
# LESSON: Abstract Base Class Pattern
# =============================================================================
# ABCs let you define what methods a class MUST have
# without implementing them

from abc import ABC, abstractmethod

class Shape(ABC):
    """Abstract base class - cannot be instantiated directly."""

    @abstractmethod
    def area(self) -> float:
        """Subclasses MUST implement this method."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """Subclasses MUST implement this method."""
        pass


# This will raise TypeError - can't instantiate ABC
# shape = Shape()  # ❌ Error!


class Circle(Shape):
    """Concrete class - implements all abstract methods."""

    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14159 * self.radius ** 2

    def perimeter(self) -> float:
        return 2 * 3.14159 * self.radius


# This works - Circle implements all abstract methods
circle = Circle(5)  # ✅ Works!
print(circle.area())  # 78.54
```

### Why Use ABCs?

```python
# =============================================================================
# LESSON: Interface Pattern
# =============================================================================
# ABCs let you swap implementations without changing code

from abc import ABC, abstractmethod
from typing import List


class LDClientInterface(ABC):
    """Interface for LaunchDarkly client."""

    @abstractmethod
    def list_projects(self) -> List[dict]:
        pass

    @abstractmethod
    def create_role(self, data: dict) -> dict:
        pass


class RealLDClient(LDClientInterface):
    """Real client - makes actual API calls."""

    def list_projects(self) -> List[dict]:
        # Real HTTP call
        response = requests.get("https://app.launchdarkly.com/api/v2/projects")
        return response.json()["items"]

    def create_role(self, data: dict) -> dict:
        # Real HTTP call
        response = requests.post("https://app.launchdarkly.com/api/v2/roles", json=data)
        return response.json()


class MockLDClient(LDClientInterface):
    """Mock client - no API calls, for testing."""

    def __init__(self):
        self.projects = []
        self.roles = []

    def list_projects(self) -> List[dict]:
        return self.projects  # Return test data

    def create_role(self, data: dict) -> dict:
        self.roles.append(data)  # Store in memory
        return data


# =============================================================================
# LESSON: Dependency Injection
# =============================================================================
# Code depends on interface, not implementation

class Deployer:
    """Uses any client that implements LDClientInterface."""

    def __init__(self, client: LDClientInterface):
        self.client = client  # Can be real or mock!

    def deploy(self, role_data: dict):
        self.client.create_role(role_data)


# In production
deployer = Deployer(RealLDClient())

# In tests
deployer = Deployer(MockLDClient())
```

---

## 4. Custom Exceptions

### Why Custom Exceptions?

Custom exceptions make error handling more specific and meaningful.

```python
# =============================================================================
# LESSON: Exception Hierarchy
# =============================================================================
# Create a hierarchy of exceptions for different error types

class LDClientError(Exception):
    """Base exception for all LD client errors."""
    pass


class LDAuthenticationError(LDClientError):
    """Authentication failed (401/403)."""
    pass


class LDNotFoundError(LDClientError):
    """Resource not found (404)."""
    pass


class LDConflictError(LDClientError):
    """Resource already exists (409)."""
    pass


class LDRateLimitError(LDClientError):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


class LDValidationError(LDClientError):
    """Invalid request data (400)."""

    def __init__(self, message: str, errors: list = None):
        self.errors = errors or []
        super().__init__(message)
```

### Using Custom Exceptions

```python
# =============================================================================
# LESSON: Raising Custom Exceptions
# =============================================================================

def handle_response(response):
    """Convert HTTP errors to custom exceptions."""

    if response.ok:
        return response.json()

    status = response.status_code
    message = response.json().get("message", "Unknown error")

    if status == 401 or status == 403:
        raise LDAuthenticationError(message)

    if status == 404:
        raise LDNotFoundError(message)

    if status == 409:
        raise LDConflictError(message)

    if status == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        raise LDRateLimitError(retry_after)

    if status == 400:
        errors = response.json().get("errors", [])
        raise LDValidationError(message, errors)

    raise LDClientError(f"HTTP {status}: {message}")


# =============================================================================
# LESSON: Catching Custom Exceptions
# =============================================================================

try:
    client.create_role(role_data)

except LDConflictError:
    print("Role already exists - skipping")

except LDRateLimitError as e:
    print(f"Rate limited, waiting {e.retry_after} seconds")
    time.sleep(e.retry_after)

except LDAuthenticationError:
    print("Invalid API key!")

except LDClientError as e:
    print(f"Unexpected error: {e}")
```

---

## 5. Retry Logic and Backoff

### Why Retry?

Network requests can fail temporarily. Retrying makes your code more robust.

```python
# =============================================================================
# LESSON: Simple Retry Pattern
# =============================================================================

import time

def request_with_retry(url: str, max_retries: int = 3) -> dict:
    """Make request with automatic retry on failure."""

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
                continue
            raise  # Last attempt - raise error

        except requests.HTTPError as e:
            if e.response.status_code >= 500:
                # Server error - might be temporary
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            raise  # Client error or last attempt
```

### Exponential Backoff

```python
# =============================================================================
# LESSON: Exponential Backoff
# =============================================================================
# Each retry waits longer: 1s, 2s, 4s, 8s...
# This prevents overwhelming a struggling server

import time
import random

def exponential_backoff(attempt: int, base: float = 1.0) -> float:
    """Calculate wait time with exponential backoff."""
    # 2^attempt * base, with some randomness
    wait = (2 ** attempt) * base
    # Add jitter to prevent "thundering herd"
    jitter = random.uniform(0, wait * 0.1)
    return wait + jitter


def request_with_backoff(url: str, max_retries: int = 3) -> dict:
    """Make request with exponential backoff."""

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()

        except (requests.ConnectionError, requests.HTTPError) as e:
            if attempt < max_retries - 1:
                wait_time = exponential_backoff(attempt)
                print(f"Retry {attempt + 1} in {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            raise


# Attempt 0: immediate
# Attempt 1: wait ~1s
# Attempt 2: wait ~2s
# Attempt 3: wait ~4s
```

### Rate Limit Handling

```python
# =============================================================================
# LESSON: Respecting Rate Limits
# =============================================================================
# APIs tell you when to retry via "Retry-After" header

def handle_rate_limit(response) -> None:
    """Wait if rate limited."""

    if response.status_code == 429:
        # Get wait time from header (default 60s)
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
```

---

## 6. Session Management

### Why Use Sessions?

Sessions provide connection pooling and persistent settings.

```python
# =============================================================================
# LESSON: requests.Session
# =============================================================================
# Without session - new connection for each request (slow)
# With session - reuses connections (fast)

import requests

# BAD: New connection each time
response1 = requests.get("https://api.example.com/a")
response2 = requests.get("https://api.example.com/b")
response3 = requests.get("https://api.example.com/c")


# GOOD: Reuse connection
session = requests.Session()
response1 = session.get("https://api.example.com/a")
response2 = session.get("https://api.example.com/b")
response3 = session.get("https://api.example.com/c")
```

### Persistent Headers

```python
# =============================================================================
# LESSON: Session Headers
# =============================================================================
# Set headers once, used for all requests

session = requests.Session()

# These headers apply to ALL requests
session.headers.update({
    "Authorization": "api-key-xxxxx",
    "Content-Type": "application/json",
    "Accept": "application/json"
})

# No need to pass headers each time
response = session.get("https://api.example.com/projects")
response = session.post("https://api.example.com/roles", json=data)
```

### Context Manager Pattern

```python
# =============================================================================
# LESSON: Session as Context Manager
# =============================================================================
# Session closes automatically when done

with requests.Session() as session:
    session.headers["Authorization"] = "api-key-xxx"

    response = session.get("https://api.example.com/projects")
    projects = response.json()

# Session closed here automatically
```

---

## 7. Testing HTTP Clients

### Mocking HTTP Requests

```python
# =============================================================================
# LESSON: Mocking with unittest.mock
# =============================================================================
# Never make real HTTP calls in tests!

from unittest.mock import Mock, patch
import pytest


def test_list_projects():
    """Test listing projects without real API calls."""

    # Create a mock response
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "items": [
            {"key": "proj1", "name": "Project 1"},
            {"key": "proj2", "name": "Project 2"}
        ]
    }

    # Patch requests.get to return our mock
    with patch("requests.get", return_value=mock_response):
        response = requests.get("https://api.example.com/projects")
        data = response.json()

        assert len(data["items"]) == 2
        assert data["items"][0]["key"] == "proj1"
```

### Mocking Session Requests

```python
# =============================================================================
# LESSON: Mocking Session
# =============================================================================

@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    session = Mock()
    session.request = Mock()
    return session


def test_client_list_projects(mock_session):
    """Test client with mocked session."""

    # Setup mock response
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {"items": []}
    mock_session.request.return_value = mock_response

    # Create client with mocked session
    client = LDClient.__new__(LDClient)
    client.session = mock_session
    client.base_url = "https://app.launchdarkly.com"
    client.timeout = 30

    # Call method
    projects = client.list_projects()

    # Verify correct endpoint was called
    mock_session.request.assert_called_with(
        method="GET",
        url="https://app.launchdarkly.com/api/v2/projects",
        json=None,
        params=None,
        timeout=30
    )
```

### Testing Error Handling

```python
# =============================================================================
# LESSON: Testing Error Scenarios
# =============================================================================

def test_authentication_error():
    """Test that 401 raises LDAuthenticationError."""

    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Invalid token"}

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(LDAuthenticationError):
            client.list_projects()


def test_rate_limit_error():
    """Test that 429 raises LDRateLimitError with retry info."""

    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "120"}
    mock_response.json.return_value = {"message": "Rate limited"}

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(LDRateLimitError) as exc_info:
            client.list_projects()

        assert exc_info.value.retry_after == 120
```

### Mock Client Pattern

```python
# =============================================================================
# LESSON: Test Double Pattern
# =============================================================================
# Create a fake client for testing other components

class MockLDClient(LDClientInterface):
    """Fake client that stores data in memory."""

    def __init__(self):
        self.projects = []
        self.roles = []
        self.teams = []
        self.call_log = []  # Track all method calls

    def list_projects(self):
        self.call_log.append(("list_projects", {}))
        return self.projects

    def create_role(self, data):
        self.call_log.append(("create_role", data))
        # Simulate conflict check
        if any(r["key"] == data["key"] for r in self.roles):
            raise LDConflictError(f"Role {data['key']} exists")
        self.roles.append(data)
        return data

    # Helper methods for tests
    def add_test_project(self, key, name):
        self.projects.append({"key": key, "name": name})

    def get_call_count(self, method):
        return sum(1 for call in self.call_log if call[0] == method)


# Usage in tests
def test_deployer_creates_roles():
    """Test deployer with mock client."""
    mock_client = MockLDClient()
    deployer = Deployer(mock_client)

    deployer.deploy_role({"key": "dev", "name": "Developer", "policy": []})

    assert len(mock_client.roles) == 1
    assert mock_client.get_call_count("create_role") == 1
```

---

## 8. Quick Reference Card

### HTTP Requests Cheat Sheet

```python
import requests

# GET request
response = requests.get(url, headers=headers, params=params, timeout=30)

# POST request (JSON body)
response = requests.post(url, headers=headers, json=data, timeout=30)

# PATCH request
response = requests.patch(url, headers=headers, json=patch_data, timeout=30)

# DELETE request
response = requests.delete(url, headers=headers, timeout=30)

# Response handling
response.ok           # True if 200-299
response.status_code  # 200, 404, etc.
response.json()       # Parse JSON body
response.headers      # Response headers
```

### ABC Cheat Sheet

```python
from abc import ABC, abstractmethod

class MyInterface(ABC):
    @abstractmethod
    def my_method(self) -> ReturnType:
        """Must be implemented by subclasses."""
        pass

class MyClass(MyInterface):
    def my_method(self) -> ReturnType:
        # Implementation here
        pass
```

### Custom Exceptions Cheat Sheet

```python
class MyBaseError(Exception):
    """Base exception."""
    pass

class MySpecificError(MyBaseError):
    """Specific error with extra data."""
    def __init__(self, message: str, code: int):
        self.code = code
        super().__init__(message)

# Raising
raise MySpecificError("Something failed", code=123)

# Catching
try:
    do_something()
except MySpecificError as e:
    print(f"Error {e.code}: {e}")
except MyBaseError:
    print("Some other error")
```

### Mock Cheat Sheet

```python
from unittest.mock import Mock, patch

# Create mock object
mock_obj = Mock()
mock_obj.method.return_value = "result"
mock_obj.method()  # Returns "result"

# Patch a module
with patch("module.requests.get") as mock_get:
    mock_get.return_value = Mock(ok=True, json=Mock(return_value={}))
    result = module.fetch_data()

# Verify calls
mock_obj.method.assert_called_once()
mock_obj.method.assert_called_with(arg1, arg2)
```

---

## Next Steps

Now that you understand the Python concepts for Phase 6, proceed to:
- [DESIGN.md](DESIGN.md) - Implementation details and test cases
- [README.md](README.md) - Quick overview and checklist

---

[← Back to Phase 6 README](README.md) | [Phase 6 DESIGN →](DESIGN.md)
