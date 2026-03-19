# Phase 6: LaunchDarkly API Client - Design Document

| Attribute | Value |
|-----------|-------|
| **Phase** | 6 of 10 |
| **Status** | 📋 Planned |
| **Goal** | Create LaunchDarkly API client for REST API communication |
| **Dependencies** | Phase 1 (Models) |
| **Estimated Lessons** | HTTP Requests, REST APIs, Abstract Classes, Error Handling |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Quick overview and checklist |
| [PYTHON_CONCEPTS.md](PYTHON_CONCEPTS.md) | Deep dive into Python concepts |
| [Phase 7 DESIGN.md](../phase7/DESIGN.md) | Deployer that uses this client |
| [LaunchDarkly API Docs](https://apidocs.launchdarkly.com/) | Official API reference |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Test Cases](#test-cases)
5. [Implementation Plan](#implementation-plan)

---

## High-Level Design (HLD)

### What Are We Building?

A Python client that wraps the LaunchDarkly REST API, providing:
- **Authentication** - API key management
- **Fetch Operations** - List projects, environments, teams, roles
- **Create Operations** - Create custom roles and teams
- **Error Handling** - Graceful handling of API errors

### Why Do We Need This?

```
┌─────────────────────────────────────────────────────────────────┐
│                      RBAC Builder App                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Setup     │    │   Matrix    │    │      Deploy         │ │
│  │    Tab      │    │    Tab      │    │       Tab           │ │
│  └──────┬──────┘    └─────────────┘    └──────────┬──────────┘ │
│         │                                         │             │
│         │  "Connected Mode"                       │  "Deploy"   │
│         ▼                                         ▼             │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                    LDClient (Phase 6)                      ││
│  │  • list_projects()     • create_custom_role()              ││
│  │  • list_environments() • create_team()                     ││
│  │  • list_teams()        • update_team()                     ││
│  └────────────────────────────────────────────────────────────┘│
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  LaunchDarkly API   │
                    │  api.launchdarkly.com│
                    └─────────────────────┘
```

### LaunchDarkly API Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/projects` | GET | List all projects |
| `/api/v2/projects/{key}/environments` | GET | List environments in project |
| `/api/v2/teams` | GET | List all teams |
| `/api/v2/roles` | GET | List custom roles |
| `/api/v2/roles` | POST | Create custom role |
| `/api/v2/teams` | POST | Create team |
| `/api/v2/teams/{key}` | PATCH | Update team (add roles) |

### Authentication

LaunchDarkly uses API keys passed in the `Authorization` header:

```http
GET /api/v2/projects HTTP/1.1
Host: app.launchdarkly.com
Authorization: api-key-xxxxx
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Interface Pattern** | Abstract base class allows mock/real implementations |
| **Retry Logic** | Automatic retry on transient failures (429, 503) |
| **Rate Limiting** | Respect API rate limits with backoff |
| **Error Mapping** | Convert HTTP errors to typed exceptions |
| **Response Parsing** | Parse JSON responses into model objects |

---

## Detailed Low-Level Design (DLD)

### File Structure

```
services/
├── __init__.py              # Export LDClient, MockLDClient
├── ld_client_interface.py   # Abstract interface (ABC)
├── ld_client.py             # Real implementation
└── ld_exceptions.py         # Custom exceptions
```

### Class Diagram

```
┌─────────────────────────────────────┐
│      LDClientInterface (ABC)        │
├─────────────────────────────────────┤
│ + list_projects() -> List[Project]  │
│ + list_environments(proj) -> List   │
│ + list_teams() -> List[Team]        │
│ + list_roles() -> List[Role]        │
│ + create_custom_role(data) -> Role  │
│ + create_team(data) -> Team         │
│ + update_team(key, data) -> Team    │
│ + health_check() -> bool            │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌───────────────┐    ┌────────────────┐
│   LDClient    │    │  MockLDClient  │
├───────────────┤    ├────────────────┤
│ - api_key     │    │ - projects     │
│ - base_url    │    │ - teams        │
│ - session     │    │ - roles        │
│ - timeout     │    │ - call_log     │
└───────────────┘    └────────────────┘
```

### LDClientInterface (Abstract Base Class)

```python
# services/ld_client_interface.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LDProject:
    """Represents a LaunchDarkly project."""
    key: str
    name: str
    tags: List[str]


@dataclass
class LDEnvironment:
    """Represents a LaunchDarkly environment."""
    key: str
    name: str
    color: str
    project_key: str


@dataclass
class LDTeam:
    """Represents a LaunchDarkly team."""
    key: str
    name: str
    description: str
    member_count: int
    roles: List[str]


@dataclass
class LDCustomRole:
    """Represents a LaunchDarkly custom role."""
    key: str
    name: str
    description: str
    policy: List[Dict[str, Any]]


class LDClientInterface(ABC):
    """Abstract interface for LaunchDarkly API client."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check if API is accessible."""
        pass

    @abstractmethod
    def list_projects(self) -> List[LDProject]:
        """List all projects in the account."""
        pass

    @abstractmethod
    def list_environments(self, project_key: str) -> List[LDEnvironment]:
        """List all environments in a project."""
        pass

    @abstractmethod
    def list_teams(self) -> List[LDTeam]:
        """List all teams in the account."""
        pass

    @abstractmethod
    def list_custom_roles(self) -> List[LDCustomRole]:
        """List all custom roles in the account."""
        pass

    @abstractmethod
    def create_custom_role(self, role_data: Dict[str, Any]) -> LDCustomRole:
        """Create a new custom role."""
        pass

    @abstractmethod
    def create_team(self, team_data: Dict[str, Any]) -> LDTeam:
        """Create a new team."""
        pass

    @abstractmethod
    def update_team(self, team_key: str, patch_data: List[Dict]) -> LDTeam:
        """Update an existing team using JSON Patch."""
        pass
```

### Attribute Tables

#### LDClient Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | LaunchDarkly API key |
| `base_url` | `str` | API base URL (default: `https://app.launchdarkly.com`) |
| `session` | `requests.Session` | Reusable HTTP session |
| `timeout` | `int` | Request timeout in seconds (default: 30) |
| `max_retries` | `int` | Max retry attempts (default: 3) |

#### LDClient Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `api_key, base_url, timeout` | `None` | Initialize client |
| `health_check` | None | `bool` | Verify API connectivity |
| `list_projects` | None | `List[LDProject]` | Get all projects |
| `list_environments` | `project_key: str` | `List[LDEnvironment]` | Get project environments |
| `list_teams` | None | `List[LDTeam]` | Get all teams |
| `list_custom_roles` | None | `List[LDCustomRole]` | Get all custom roles |
| `create_custom_role` | `role_data: Dict` | `LDCustomRole` | Create new role |
| `create_team` | `team_data: Dict` | `LDTeam` | Create new team |
| `update_team` | `team_key, patch_data` | `LDTeam` | Update team with patch |
| `_request` | `method, path, data` | `Dict` | Internal HTTP request |
| `_handle_error` | `response` | `None` | Raise typed exception |

### Custom Exceptions

```python
# services/ld_exceptions.py

class LDClientError(Exception):
    """Base exception for LD client errors."""
    pass


class LDAuthenticationError(LDClientError):
    """Invalid or missing API key."""
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
    def __init__(self, message: str, errors: List[Dict] = None):
        self.errors = errors or []
        super().__init__(message)


class LDServerError(LDClientError):
    """Server error (5xx)."""
    pass
```

### HTTP Error Mapping

| Status Code | Exception | Description |
|-------------|-----------|-------------|
| 400 | `LDValidationError` | Invalid request body |
| 401 | `LDAuthenticationError` | Invalid API key |
| 403 | `LDAuthenticationError` | Insufficient permissions |
| 404 | `LDNotFoundError` | Resource not found |
| 409 | `LDConflictError` | Resource already exists |
| 429 | `LDRateLimitError` | Too many requests |
| 500+ | `LDServerError` | Server-side error |

### API Request/Response Examples

#### Create Custom Role

**Request:**
```http
POST /api/v2/roles HTTP/1.1
Authorization: api-key-xxxxx
Content-Type: application/json

{
  "key": "developer-test-env",
  "name": "Developer - Test Environment",
  "description": "Developer access for test environments",
  "policy": [
    {
      "effect": "allow",
      "actions": ["updateTargets", "updateRules"],
      "resources": ["proj/*:env/*;test:flag/*"]
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "key": "developer-test-env",
  "name": "Developer - Test Environment",
  "description": "Developer access for test environments",
  "policy": [...],
  "_links": {...}
}
```

#### Create Team

**Request:**
```http
POST /api/v2/teams HTTP/1.1
Authorization: api-key-xxxxx
Content-Type: application/json

{
  "key": "developers",
  "name": "Developers",
  "description": "Development team",
  "customRoleKeys": ["developer-test-env", "developer-prod-env"]
}
```

**Response (201 Created):**
```json
{
  "key": "developers",
  "name": "Developers",
  "description": "Development team",
  "customRoleKeys": ["developer-test-env", "developer-prod-env"],
  "_links": {...}
}
```

---

## Pseudo Logic

### 1. LDClient Initialization

```
FUNCTION __init__(api_key, base_url, timeout):
    1. VALIDATE api_key is not empty
       IF empty:
           RAISE LDAuthenticationError("API key required")

    2. STORE configuration
       self.api_key = api_key
       self.base_url = base_url OR "https://app.launchdarkly.com"
       self.timeout = timeout OR 30
       self.max_retries = 3

    3. CREATE requests Session for connection pooling
       self.session = requests.Session()
       self.session.headers = {
           "Authorization": api_key,
           "Content-Type": "application/json"
       }

    4. RETURN initialized client
```

### 2. Generic Request Handler

```
FUNCTION _request(method, path, data=None, params=None):
    1. BUILD full URL
       url = self.base_url + path

    2. RETRY loop (up to max_retries)
       FOR attempt IN range(max_retries):
           TRY:
               3. MAKE HTTP request
                  response = session.request(
                      method=method,
                      url=url,
                      json=data,
                      params=params,
                      timeout=self.timeout
                  )

               4. CHECK response status
                  IF response.ok (200-299):
                      IF response has content:
                          RETURN response.json()
                      ELSE:
                          RETURN {}

                  5. HANDLE errors
                  IF status == 429 (rate limit):
                      retry_after = response.headers.get("Retry-After", 60)
                      IF attempt < max_retries - 1:
                          SLEEP(retry_after)
                          CONTINUE
                      ELSE:
                          RAISE LDRateLimitError(retry_after)

                  IF status == 503 (service unavailable):
                      IF attempt < max_retries - 1:
                          SLEEP(2 ** attempt)  # Exponential backoff
                          CONTINUE

                  6. MAP error to exception
                  _handle_error(response)

           EXCEPT ConnectionError:
               IF attempt < max_retries - 1:
                   SLEEP(1)
                   CONTINUE
               RAISE LDClientError("Connection failed")
```

### 3. Error Handler

```
FUNCTION _handle_error(response):
    status = response.status_code

    TRY:
        body = response.json()
        message = body.get("message", "Unknown error")
    EXCEPT:
        message = response.text OR "Unknown error"

    IF status == 400:
        RAISE LDValidationError(message, body.get("errors", []))

    IF status == 401 OR status == 403:
        RAISE LDAuthenticationError(message)

    IF status == 404:
        RAISE LDNotFoundError(message)

    IF status == 409:
        RAISE LDConflictError(message)

    IF status == 429:
        retry_after = response.headers.get("Retry-After", 60)
        RAISE LDRateLimitError(int(retry_after))

    IF status >= 500:
        RAISE LDServerError(message)

    # Default
    RAISE LDClientError(f"HTTP {status}: {message}")
```

### 4. List Projects

```
FUNCTION list_projects() -> List[LDProject]:
    1. MAKE request to list projects
       response = _request("GET", "/api/v2/projects")

    2. PARSE response items
       items = response.get("items", [])

    3. CONVERT to LDProject objects
       projects = []
       FOR item IN items:
           project = LDProject(
               key=item["key"],
               name=item["name"],
               tags=item.get("tags", [])
           )
           projects.append(project)

    4. RETURN list of projects
       RETURN projects
```

### 5. List Environments

```
FUNCTION list_environments(project_key: str) -> List[LDEnvironment]:
    1. VALIDATE project_key
       IF NOT project_key:
           RAISE ValueError("project_key required")

    2. MAKE request to list environments
       path = f"/api/v2/projects/{project_key}/environments"
       response = _request("GET", path)

    3. PARSE response items
       items = response.get("items", [])

    4. CONVERT to LDEnvironment objects
       environments = []
       FOR item IN items:
           env = LDEnvironment(
               key=item["key"],
               name=item["name"],
               color=item.get("color", ""),
               project_key=project_key
           )
           environments.append(env)

    5. RETURN list of environments
       RETURN environments
```

### 6. Create Custom Role

```
FUNCTION create_custom_role(role_data: Dict) -> LDCustomRole:
    1. VALIDATE required fields
       required = ["key", "name", "policy"]
       FOR field IN required:
           IF field NOT IN role_data:
               RAISE ValueError(f"Missing required field: {field}")

    2. MAKE POST request
       response = _request("POST", "/api/v2/roles", data=role_data)

    3. PARSE response
       role = LDCustomRole(
           key=response["key"],
           name=response["name"],
           description=response.get("description", ""),
           policy=response.get("policy", [])
       )

    4. RETURN created role
       RETURN role
```

### 7. Create Team

```
FUNCTION create_team(team_data: Dict) -> LDTeam:
    1. VALIDATE required fields
       required = ["key", "name"]
       FOR field IN required:
           IF field NOT IN team_data:
               RAISE ValueError(f"Missing required field: {field}")

    2. MAKE POST request
       response = _request("POST", "/api/v2/teams", data=team_data)

    3. PARSE response
       team = LDTeam(
           key=response["key"],
           name=response["name"],
           description=response.get("description", ""),
           member_count=response.get("memberCount", 0),
           roles=response.get("customRoleKeys", [])
       )

    4. RETURN created team
       RETURN team
```

### 8. Update Team (JSON Patch)

```
FUNCTION update_team(team_key: str, patch_data: List[Dict]) -> LDTeam:
    1. VALIDATE inputs
       IF NOT team_key:
           RAISE ValueError("team_key required")
       IF NOT patch_data:
           RAISE ValueError("patch_data required")

    2. MAKE PATCH request
       path = f"/api/v2/teams/{team_key}"
       # Note: PATCH requires Content-Type: application/json
       # patch_data is a JSON Patch array
       response = _request("PATCH", path, data=patch_data)

    3. PARSE response
       team = LDTeam(
           key=response["key"],
           name=response["name"],
           description=response.get("description", ""),
           member_count=response.get("memberCount", 0),
           roles=response.get("customRoleKeys", [])
       )

    4. RETURN updated team
       RETURN team
```

### 9. MockLDClient Implementation

```
CLASS MockLDClient(LDClientInterface):
    """Mock client for testing without real API calls."""

    FUNCTION __init__():
        # In-memory storage
        self.projects = []
        self.environments = {}  # project_key -> List[LDEnvironment]
        self.teams = []
        self.roles = []
        self.call_log = []  # Track method calls for testing

    FUNCTION health_check() -> bool:
        self.call_log.append(("health_check", {}))
        RETURN True

    FUNCTION list_projects() -> List[LDProject]:
        self.call_log.append(("list_projects", {}))
        RETURN self.projects.copy()

    FUNCTION create_custom_role(role_data: Dict) -> LDCustomRole:
        self.call_log.append(("create_custom_role", role_data))

        # Check for conflicts
        FOR role IN self.roles:
            IF role.key == role_data["key"]:
                RAISE LDConflictError(f"Role {role.key} already exists")

        # Create role
        role = LDCustomRole(
            key=role_data["key"],
            name=role_data["name"],
            description=role_data.get("description", ""),
            policy=role_data.get("policy", [])
        )
        self.roles.append(role)
        RETURN role

    # ... similar implementations for other methods

    FUNCTION add_test_project(key, name):
        """Helper to add test data."""
        self.projects.append(LDProject(key=key, name=name, tags=[]))

    FUNCTION get_call_count(method_name: str) -> int:
        """Get number of times a method was called."""
        RETURN sum(1 FOR call IN self.call_log IF call[0] == method_name)

    FUNCTION reset():
        """Clear all data and call log."""
        self.projects = []
        self.teams = []
        self.roles = []
        self.call_log = []
```

---

## Test Cases

### Test File: `tests/test_ld_client.py`

```python
"""
Tests for Phase 6: LaunchDarkly API Client
==========================================

Tests cover:
1. Client initialization
2. Authentication handling
3. Fetch operations (projects, environments, teams, roles)
4. Create operations (roles, teams)
5. Update operations (teams)
6. Error handling
7. Mock client functionality

Run with: pytest tests/test_ld_client.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {}
    return response


@pytest.fixture
def ld_client():
    """Create LDClient instance with mocked session."""
    from services.ld_client import LDClient
    with patch('services.ld_client.requests.Session'):
        client = LDClient(api_key="test-api-key")
    return client


@pytest.fixture
def mock_client():
    """Create MockLDClient instance."""
    from services.ld_client import MockLDClient
    return MockLDClient()


# =============================================================================
# Initialization Tests
# =============================================================================

class TestLDClientInit:
    """Tests for client initialization."""

    def test_init_with_api_key(self):
        """Test client initializes with API key."""
        from services.ld_client import LDClient
        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_init_with_empty_api_key_raises_error(self):
        """Test that empty API key raises error."""
        from services.ld_client import LDClient
        from services.ld_exceptions import LDAuthenticationError

        with pytest.raises(LDAuthenticationError):
            LDClient(api_key="")

    def test_init_with_custom_base_url(self):
        """Test client accepts custom base URL."""
        from services.ld_client import LDClient
        with patch('services.ld_client.requests.Session'):
            client = LDClient(
                api_key="test-key",
                base_url="https://custom.launchdarkly.com"
            )
        assert client.base_url == "https://custom.launchdarkly.com"

    def test_init_default_base_url(self):
        """Test default base URL is set."""
        from services.ld_client import LDClient
        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test-key")
        assert client.base_url == "https://app.launchdarkly.com"

    def test_init_creates_session_with_headers(self):
        """Test session is created with auth headers."""
        from services.ld_client import LDClient
        with patch('services.ld_client.requests.Session') as mock_session:
            client = LDClient(api_key="test-key")
            mock_session.return_value.headers.__setitem__.assert_called()


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_returns_true_on_success(self, ld_client, mock_response):
        """Test health check returns True when API is accessible."""
        mock_response.ok = True
        ld_client.session.request.return_value = mock_response

        result = ld_client.health_check()
        assert result is True

    def test_health_check_returns_false_on_failure(self, ld_client, mock_response):
        """Test health check returns False when API is down."""
        ld_client.session.request.side_effect = requests.ConnectionError()

        result = ld_client.health_check()
        assert result is False


# =============================================================================
# List Projects Tests
# =============================================================================

class TestListProjects:
    """Tests for listing projects."""

    def test_list_projects_returns_empty_list(self, ld_client, mock_response):
        """Test empty project list is handled."""
        mock_response.json.return_value = {"items": []}
        ld_client.session.request.return_value = mock_response

        projects = ld_client.list_projects()
        assert projects == []

    def test_list_projects_parses_response(self, ld_client, mock_response):
        """Test projects are parsed from response."""
        mock_response.json.return_value = {
            "items": [
                {"key": "proj1", "name": "Project 1", "tags": ["tag1"]},
                {"key": "proj2", "name": "Project 2", "tags": []}
            ]
        }
        ld_client.session.request.return_value = mock_response

        projects = ld_client.list_projects()

        assert len(projects) == 2
        assert projects[0].key == "proj1"
        assert projects[0].name == "Project 1"
        assert projects[0].tags == ["tag1"]

    def test_list_projects_calls_correct_endpoint(self, ld_client, mock_response):
        """Test correct API endpoint is called."""
        mock_response.json.return_value = {"items": []}
        ld_client.session.request.return_value = mock_response

        ld_client.list_projects()

        ld_client.session.request.assert_called_with(
            method="GET",
            url="https://app.launchdarkly.com/api/v2/projects",
            json=None,
            params=None,
            timeout=30
        )


# =============================================================================
# List Environments Tests
# =============================================================================

class TestListEnvironments:
    """Tests for listing environments."""

    def test_list_environments_requires_project_key(self, ld_client):
        """Test that project_key is required."""
        with pytest.raises(ValueError, match="project_key required"):
            ld_client.list_environments("")

    def test_list_environments_parses_response(self, ld_client, mock_response):
        """Test environments are parsed from response."""
        mock_response.json.return_value = {
            "items": [
                {"key": "dev", "name": "Development", "color": "green"},
                {"key": "prod", "name": "Production", "color": "red"}
            ]
        }
        ld_client.session.request.return_value = mock_response

        envs = ld_client.list_environments("my-project")

        assert len(envs) == 2
        assert envs[0].key == "dev"
        assert envs[0].project_key == "my-project"

    def test_list_environments_calls_correct_endpoint(self, ld_client, mock_response):
        """Test correct API endpoint is called."""
        mock_response.json.return_value = {"items": []}
        ld_client.session.request.return_value = mock_response

        ld_client.list_environments("my-project")

        call_args = ld_client.session.request.call_args
        assert "/api/v2/projects/my-project/environments" in call_args[1]["url"]


# =============================================================================
# Create Custom Role Tests
# =============================================================================

class TestCreateCustomRole:
    """Tests for creating custom roles."""

    def test_create_role_validates_required_fields(self, ld_client):
        """Test that required fields are validated."""
        with pytest.raises(ValueError, match="Missing required field"):
            ld_client.create_custom_role({})

    def test_create_role_validates_key_field(self, ld_client):
        """Test that key field is required."""
        with pytest.raises(ValueError, match="key"):
            ld_client.create_custom_role({"name": "Test", "policy": []})

    def test_create_role_returns_role_object(self, ld_client, mock_response):
        """Test created role is returned."""
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "key": "dev-role",
            "name": "Developer Role",
            "description": "For developers",
            "policy": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]
        }
        ld_client.session.request.return_value = mock_response

        role = ld_client.create_custom_role({
            "key": "dev-role",
            "name": "Developer Role",
            "policy": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]
        })

        assert role.key == "dev-role"
        assert role.name == "Developer Role"

    def test_create_role_handles_conflict(self, ld_client, mock_response):
        """Test conflict error when role exists."""
        from services.ld_exceptions import LDConflictError

        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.json.return_value = {"message": "Role already exists"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDConflictError):
            ld_client.create_custom_role({
                "key": "existing-role",
                "name": "Existing Role",
                "policy": []
            })


# =============================================================================
# Create Team Tests
# =============================================================================

class TestCreateTeam:
    """Tests for creating teams."""

    def test_create_team_validates_required_fields(self, ld_client):
        """Test that required fields are validated."""
        with pytest.raises(ValueError, match="Missing required field"):
            ld_client.create_team({})

    def test_create_team_returns_team_object(self, ld_client, mock_response):
        """Test created team is returned."""
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "key": "developers",
            "name": "Developers",
            "description": "Dev team",
            "memberCount": 0,
            "customRoleKeys": ["dev-role"]
        }
        ld_client.session.request.return_value = mock_response

        team = ld_client.create_team({
            "key": "developers",
            "name": "Developers",
            "customRoleKeys": ["dev-role"]
        })

        assert team.key == "developers"
        assert team.roles == ["dev-role"]

    def test_create_team_handles_conflict(self, ld_client, mock_response):
        """Test conflict error when team exists."""
        from services.ld_exceptions import LDConflictError

        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.json.return_value = {"message": "Team already exists"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDConflictError):
            ld_client.create_team({"key": "existing", "name": "Existing"})


# =============================================================================
# Update Team Tests
# =============================================================================

class TestUpdateTeam:
    """Tests for updating teams."""

    def test_update_team_requires_key(self, ld_client):
        """Test that team_key is required."""
        with pytest.raises(ValueError, match="team_key required"):
            ld_client.update_team("", [])

    def test_update_team_requires_patch_data(self, ld_client):
        """Test that patch_data is required."""
        with pytest.raises(ValueError, match="patch_data required"):
            ld_client.update_team("my-team", [])

    def test_update_team_returns_updated_team(self, ld_client, mock_response):
        """Test updated team is returned."""
        mock_response.json.return_value = {
            "key": "developers",
            "name": "Developers",
            "description": "Updated description",
            "memberCount": 5,
            "customRoleKeys": ["role1", "role2"]
        }
        ld_client.session.request.return_value = mock_response

        patch = [{"op": "add", "path": "/customRoleKeys/-", "value": "role2"}]
        team = ld_client.update_team("developers", patch)

        assert team.roles == ["role1", "role2"]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_authentication_error_on_401(self, ld_client, mock_response):
        """Test 401 raises authentication error."""
        from services.ld_exceptions import LDAuthenticationError

        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid token"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDAuthenticationError):
            ld_client.list_projects()

    def test_not_found_error_on_404(self, ld_client, mock_response):
        """Test 404 raises not found error."""
        from services.ld_exceptions import LDNotFoundError

        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not found"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDNotFoundError):
            ld_client.list_environments("nonexistent")

    def test_rate_limit_error_on_429(self, ld_client, mock_response):
        """Test 429 raises rate limit error."""
        from services.ld_exceptions import LDRateLimitError

        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"message": "Rate limited"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDRateLimitError) as exc_info:
            ld_client.list_projects()

        assert exc_info.value.retry_after == 60

    def test_validation_error_on_400(self, ld_client, mock_response):
        """Test 400 raises validation error."""
        from services.ld_exceptions import LDValidationError

        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid request",
            "errors": [{"field": "key", "message": "Key is required"}]
        }
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDValidationError) as exc_info:
            ld_client.create_custom_role({"name": "Test", "policy": []})

        assert len(exc_info.value.errors) > 0

    def test_server_error_on_500(self, ld_client, mock_response):
        """Test 500 raises server error."""
        from services.ld_exceptions import LDServerError

        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal error"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDServerError):
            ld_client.list_projects()


# =============================================================================
# Retry Logic Tests
# =============================================================================

class TestRetryLogic:
    """Tests for retry functionality."""

    def test_retries_on_connection_error(self, ld_client):
        """Test client retries on connection failure."""
        # First call fails, second succeeds
        ld_client.session.request.side_effect = [
            requests.ConnectionError(),
            Mock(ok=True, json=Mock(return_value={"items": []}))
        ]

        projects = ld_client.list_projects()

        assert ld_client.session.request.call_count == 2

    def test_retries_on_503(self, ld_client, mock_response):
        """Test client retries on 503 Service Unavailable."""
        fail_response = Mock(ok=False, status_code=503)
        success_response = Mock(ok=True, json=Mock(return_value={"items": []}))

        ld_client.session.request.side_effect = [fail_response, success_response]

        projects = ld_client.list_projects()

        assert ld_client.session.request.call_count == 2

    def test_max_retries_exceeded_raises_error(self, ld_client):
        """Test error raised after max retries."""
        from services.ld_exceptions import LDClientError

        ld_client.session.request.side_effect = requests.ConnectionError()

        with pytest.raises(LDClientError, match="Connection failed"):
            ld_client.list_projects()


# =============================================================================
# Mock Client Tests
# =============================================================================

class TestMockLDClient:
    """Tests for mock client functionality."""

    def test_mock_client_health_check(self, mock_client):
        """Test mock health check returns True."""
        assert mock_client.health_check() is True

    def test_mock_client_add_project(self, mock_client):
        """Test adding test projects."""
        mock_client.add_test_project("proj1", "Project 1")

        projects = mock_client.list_projects()

        assert len(projects) == 1
        assert projects[0].key == "proj1"

    def test_mock_client_create_role(self, mock_client):
        """Test creating roles in mock client."""
        role = mock_client.create_custom_role({
            "key": "test-role",
            "name": "Test Role",
            "policy": []
        })

        assert role.key == "test-role"
        assert len(mock_client.roles) == 1

    def test_mock_client_create_duplicate_role_raises_conflict(self, mock_client):
        """Test conflict error on duplicate role."""
        from services.ld_exceptions import LDConflictError

        mock_client.create_custom_role({
            "key": "test-role",
            "name": "Test Role",
            "policy": []
        })

        with pytest.raises(LDConflictError):
            mock_client.create_custom_role({
                "key": "test-role",
                "name": "Test Role 2",
                "policy": []
            })

    def test_mock_client_tracks_calls(self, mock_client):
        """Test call logging functionality."""
        mock_client.health_check()
        mock_client.list_projects()
        mock_client.list_projects()

        assert mock_client.get_call_count("health_check") == 1
        assert mock_client.get_call_count("list_projects") == 2

    def test_mock_client_reset(self, mock_client):
        """Test reset clears all data."""
        mock_client.add_test_project("proj1", "Project 1")
        mock_client.list_projects()

        mock_client.reset()

        assert len(mock_client.projects) == 0
        assert len(mock_client.call_log) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestLDClientIntegration:
    """Integration tests for LDClient."""

    def test_interface_compliance(self):
        """Test both clients implement interface correctly."""
        from services.ld_client_interface import LDClientInterface
        from services.ld_client import LDClient, MockLDClient

        # Check MockLDClient
        mock = MockLDClient()
        assert isinstance(mock, LDClientInterface)

        # Check LDClient (with mocked session)
        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test")
        assert isinstance(client, LDClientInterface)

    def test_deployer_works_with_mock_client(self, mock_client):
        """Test that deployer can use mock client."""
        # This tests the interface contract between Phase 6 and Phase 7
        mock_client.add_test_project("default", "Default Project")

        # Simulate deployer workflow
        projects = mock_client.list_projects()
        assert len(projects) == 1

        role = mock_client.create_custom_role({
            "key": "dev-test",
            "name": "Developer - Test",
            "policy": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]
        })
        assert role.key == "dev-test"

        team = mock_client.create_team({
            "key": "developers",
            "name": "Developers",
            "customRoleKeys": ["dev-test"]
        })
        assert team.key == "developers"
```

---

## Implementation Plan

### Step-by-Step Implementation

| Step | Task | File | Est. Lines |
|------|------|------|------------|
| 1 | Create exceptions module | `services/ld_exceptions.py` | ~50 |
| 2 | Create interface (ABC) | `services/ld_client_interface.py` | ~80 |
| 3 | Create MockLDClient | `services/ld_client.py` | ~120 |
| 4 | Create LDClient | `services/ld_client.py` | ~200 |
| 5 | Add retry logic | `services/ld_client.py` | +30 |
| 6 | Update exports | `services/__init__.py` | +5 |
| 7 | Create tests | `tests/test_ld_client.py` | ~400 |

### Python Concepts Used

| Concept | Where Used |
|---------|------------|
| Abstract Base Classes (ABC) | `LDClientInterface` |
| Dataclasses | `LDProject`, `LDEnvironment`, etc. |
| Custom Exceptions | `ld_exceptions.py` |
| HTTP Requests (requests library) | `LDClient._request()` |
| Retry/Backoff | `LDClient._request()` |
| Context Managers | Session handling |
| Type Hints | All methods |
| Unit Testing | `test_ld_client.py` |
| Mocking | `unittest.mock.patch` |

---

## Learning Resources

| Topic | Resource |
|-------|----------|
| LaunchDarkly API | [API Reference](https://apidocs.launchdarkly.com/) |
| Python requests | [Requests Docs](https://docs.python-requests.org/) |
| Abstract Base Classes | [Python ABC](https://docs.python.org/3/library/abc.html) |
| Custom Exceptions | [Python Exceptions](https://docs.python.org/3/tutorial/errors.html) |
| unittest.mock | [Mock Docs](https://docs.python.org/3/library/unittest.mock.html) |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [← Phase 5: UI Modules](../phase5/) | [📋 All Phases](../) | [Phase 7: Deployer →](../phase7/) |
