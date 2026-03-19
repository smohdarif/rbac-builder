"""
LaunchDarkly API Client
=======================

This module provides two implementations of LDClientInterface:

1. LDClient - Real implementation that makes HTTP calls to LaunchDarkly API
2. MockLDClient - Mock implementation for testing without API calls

Usage:
    # Production
    client = LDClient(api_key="your-api-key")
    projects = client.list_projects()

    # Testing
    mock_client = MockLDClient()
    mock_client.add_test_project("proj1", "Project 1")
    projects = mock_client.list_projects()
"""

import time
import requests
from typing import List, Dict, Any, Optional, Tuple

from .ld_client_interface import (
    LDClientInterface,
    LDProject,
    LDEnvironment,
    LDTeam,
    LDCustomRole,
)
from .ld_exceptions import (
    LDClientError,
    LDAuthenticationError,
    LDNotFoundError,
    LDConflictError,
    LDRateLimitError,
    LDValidationError,
    LDServerError,
    exception_from_response,
)


# =============================================================================
# LESSON: Real API Client Implementation
# =============================================================================
# This class handles all the HTTP details: auth, retries, error mapping.
# The Deployer (Phase 7) uses this but doesn't need to know HTTP details.


class LDClient(LDClientInterface):
    """
    Real LaunchDarkly API client.

    Makes HTTP requests to the LaunchDarkly REST API.
    Includes retry logic for transient failures.

    Attributes:
        api_key: LaunchDarkly API key
        base_url: API base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Example:
        client = LDClient(api_key="api-xxx-yyy")
        projects = client.list_projects()
    """

    DEFAULT_BASE_URL = "https://app.launchdarkly.com"
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize the LaunchDarkly client.

        Args:
            api_key: LaunchDarkly API key (required)
            base_url: API base URL (default: https://app.launchdarkly.com)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Max retry attempts (default: 3)

        Raises:
            LDAuthenticationError: If api_key is empty
        """
        # =============================================================================
        # LESSON: Input Validation
        # =============================================================================
        # Fail fast with clear error message if required config is missing.
        if not api_key:
            raise LDAuthenticationError("API key is required")

        self.api_key = api_key
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES

        # =============================================================================
        # LESSON: Session for Connection Pooling
        # =============================================================================
        # requests.Session reuses TCP connections, making multiple requests faster.
        # We also set default headers here so they're sent with every request.
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: API path (e.g., "/api/v2/projects")
            data: Request body (for POST/PATCH)
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            LDClientError: On API errors after retries exhausted
        """
        url = f"{self.base_url}{path}"

        # =============================================================================
        # LESSON: Retry Loop with Exponential Backoff
        # =============================================================================
        # Network requests can fail temporarily. We retry a few times before giving up.
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )

                # Success - return parsed JSON
                if response.ok:
                    if response.content:
                        return response.json()
                    return {}

                # =============================================================================
                # LESSON: Handle Retryable Errors
                # =============================================================================
                # Some errors are temporary - we should retry with backoff.

                # Rate limited - wait and retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    # Last attempt - raise error
                    raise exception_from_response(
                        response.status_code,
                        self._get_error_message(response),
                        self._safe_json(response),
                        dict(response.headers)
                    )

                # Server error - retry with backoff
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

                # Non-retryable error - raise immediately
                raise exception_from_response(
                    response.status_code,
                    self._get_error_message(response),
                    self._safe_json(response),
                    dict(response.headers)
                )

            except requests.ConnectionError:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise LDClientError("Connection failed after retries")

            except requests.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise LDClientError("Request timed out after retries")

        # Should not reach here, but just in case
        raise LDClientError("Request failed after retries")

    def _get_error_message(self, response: requests.Response) -> str:
        """Extract error message from response."""
        try:
            body = response.json()
            return body.get("message", f"HTTP {response.status_code}")
        except Exception:
            return response.text or f"HTTP {response.status_code}"

    def _safe_json(self, response: requests.Response) -> Dict[str, Any]:
        """Safely parse JSON response."""
        try:
            return response.json()
        except Exception:
            return {}

    # =========================================================================
    # Read Operations
    # =========================================================================

    def health_check(self) -> bool:
        """Check if API is accessible."""
        try:
            self._request("GET", "/api/v2/projects?limit=1")
            return True
        except Exception:
            return False

    def list_projects(self) -> List[LDProject]:
        """List all projects in the account."""
        response = self._request("GET", "/api/v2/projects")
        items = response.get("items", [])

        return [
            LDProject(
                key=item["key"],
                name=item["name"],
                tags=item.get("tags", [])
            )
            for item in items
        ]

    def list_environments(self, project_key: str) -> List[LDEnvironment]:
        """List all environments in a project."""
        if not project_key:
            raise ValueError("project_key is required")

        path = f"/api/v2/projects/{project_key}/environments"
        response = self._request("GET", path)
        items = response.get("items", [])

        return [
            LDEnvironment(
                key=item["key"],
                name=item["name"],
                color=item.get("color", ""),
                project_key=project_key
            )
            for item in items
        ]

    def list_teams(self) -> List[LDTeam]:
        """List all teams in the account."""
        response = self._request("GET", "/api/v2/teams")
        items = response.get("items", [])

        return [
            LDTeam(
                key=item["key"],
                name=item["name"],
                description=item.get("description", ""),
                member_count=item.get("memberCount", 0),
                roles=item.get("customRoleKeys", [])
            )
            for item in items
        ]

    def list_custom_roles(self) -> List[LDCustomRole]:
        """List all custom roles in the account."""
        response = self._request("GET", "/api/v2/roles")
        items = response.get("items", [])

        return [
            LDCustomRole(
                key=item["key"],
                name=item["name"],
                description=item.get("description", ""),
                policy=item.get("policy", [])
            )
            for item in items
        ]

    # =========================================================================
    # Write Operations
    # =========================================================================

    def create_custom_role(self, role_data: Dict[str, Any]) -> LDCustomRole:
        """Create a new custom role."""
        # Validate required fields
        for field in ["key", "name", "policy"]:
            if field not in role_data:
                raise ValueError(f"Missing required field: {field}")

        response = self._request("POST", "/api/v2/roles", data=role_data)

        return LDCustomRole(
            key=response["key"],
            name=response["name"],
            description=response.get("description", ""),
            policy=response.get("policy", [])
        )

    def create_team(self, team_data: Dict[str, Any]) -> LDTeam:
        """Create a new team."""
        # Validate required fields
        for field in ["key", "name"]:
            if field not in team_data:
                raise ValueError(f"Missing required field: {field}")

        response = self._request("POST", "/api/v2/teams", data=team_data)

        return LDTeam(
            key=response["key"],
            name=response["name"],
            description=response.get("description", ""),
            member_count=response.get("memberCount", 0),
            roles=response.get("customRoleKeys", [])
        )

    def update_team(self, team_key: str, patch_data: List[Dict[str, Any]]) -> LDTeam:
        """Update an existing team using JSON Patch."""
        if not team_key:
            raise ValueError("team_key is required")
        if not patch_data:
            raise ValueError("patch_data is required")

        path = f"/api/v2/teams/{team_key}"
        response = self._request("PATCH", path, data=patch_data)

        return LDTeam(
            key=response["key"],
            name=response["name"],
            description=response.get("description", ""),
            member_count=response.get("memberCount", 0),
            roles=response.get("customRoleKeys", [])
        )

    def delete_role(self, role_key: str) -> bool:
        """Delete a custom role."""
        if not role_key:
            raise ValueError("role_key is required")

        path = f"/api/v2/roles/{role_key}"
        self._request("DELETE", path)
        return True

    def delete_team(self, team_key: str) -> bool:
        """Delete a team."""
        if not team_key:
            raise ValueError("team_key is required")

        path = f"/api/v2/teams/{team_key}"
        self._request("DELETE", path)
        return True


# =============================================================================
# LESSON: Mock Client for Testing
# =============================================================================
# MockLDClient stores data in memory instead of making API calls.
# This lets us test the Deployer without hitting the real API.


class MockLDClient(LDClientInterface):
    """
    Mock LaunchDarkly client for testing.

    Stores all data in memory. No real API calls are made.
    Useful for:
    - Unit testing the Deployer
    - UI testing without API credentials
    - Dry-run deployments

    Example:
        mock = MockLDClient()
        mock.add_test_project("mobile-app", "Mobile App")
        projects = mock.list_projects()  # Returns the test project
    """

    def __init__(self):
        """Initialize empty mock client."""
        self.projects: List[LDProject] = []
        self.environments: Dict[str, List[LDEnvironment]] = {}
        self.teams: List[LDTeam] = []
        self.roles: List[LDCustomRole] = []

        # =============================================================================
        # LESSON: Call Logging for Testing
        # =============================================================================
        # Track method calls so tests can verify the right methods were called.
        self.call_log: List[Tuple[str, Dict[str, Any]]] = []

    def _log_call(self, method: str, **kwargs) -> None:
        """Log a method call for test verification."""
        self.call_log.append((method, kwargs))

    # =========================================================================
    # Read Operations
    # =========================================================================

    def health_check(self) -> bool:
        """Always returns True for mock client."""
        self._log_call("health_check")
        return True

    def list_projects(self) -> List[LDProject]:
        """Return stored projects."""
        self._log_call("list_projects")
        return self.projects.copy()

    def list_environments(self, project_key: str) -> List[LDEnvironment]:
        """Return stored environments for project."""
        self._log_call("list_environments", project_key=project_key)

        if project_key not in self.environments:
            # Check if project exists
            if not any(p.key == project_key for p in self.projects):
                raise LDNotFoundError(f"Project '{project_key}' not found")
            return []

        return self.environments[project_key].copy()

    def list_teams(self) -> List[LDTeam]:
        """Return stored teams."""
        self._log_call("list_teams")
        return self.teams.copy()

    def list_custom_roles(self) -> List[LDCustomRole]:
        """Return stored roles."""
        self._log_call("list_custom_roles")
        return self.roles.copy()

    # =========================================================================
    # Write Operations
    # =========================================================================

    def create_custom_role(self, role_data: Dict[str, Any]) -> LDCustomRole:
        """Create a role in memory."""
        self._log_call("create_custom_role", role_data=role_data)

        # Validate required fields
        for field in ["key", "name", "policy"]:
            if field not in role_data:
                raise LDValidationError(f"Missing required field: {field}")

        # Check for conflict
        key = role_data["key"]
        if any(r.key == key for r in self.roles):
            raise LDConflictError(f"Role '{key}' already exists")

        # Create and store role
        role = LDCustomRole(
            key=key,
            name=role_data["name"],
            description=role_data.get("description", ""),
            policy=role_data.get("policy", [])
        )
        self.roles.append(role)
        return role

    def create_team(self, team_data: Dict[str, Any]) -> LDTeam:
        """Create a team in memory."""
        self._log_call("create_team", team_data=team_data)

        # Validate required fields
        for field in ["key", "name"]:
            if field not in team_data:
                raise LDValidationError(f"Missing required field: {field}")

        # Check for conflict
        key = team_data["key"]
        if any(t.key == key for t in self.teams):
            raise LDConflictError(f"Team '{key}' already exists")

        # Create and store team
        team = LDTeam(
            key=key,
            name=team_data["name"],
            description=team_data.get("description", ""),
            member_count=0,
            roles=team_data.get("customRoleKeys", [])
        )
        self.teams.append(team)
        return team

    def update_team(self, team_key: str, patch_data: List[Dict[str, Any]]) -> LDTeam:
        """Update a team in memory."""
        self._log_call("update_team", team_key=team_key, patch_data=patch_data)

        if not team_key:
            raise ValueError("team_key is required")
        if not patch_data:
            raise ValueError("patch_data is required")

        # Find team
        team = None
        for t in self.teams:
            if t.key == team_key:
                team = t
                break

        if not team:
            raise LDNotFoundError(f"Team '{team_key}' not found")

        # Apply patches (simplified)
        for patch in patch_data:
            op = patch.get("op")
            path = patch.get("path", "")
            value = patch.get("value")

            if op == "add" and "/customRoleKeys" in path:
                if value not in team.roles:
                    team.roles.append(value)
            elif op == "replace" and path == "/description":
                team.description = value
            elif op == "replace" and path == "/name":
                team.name = value

        return team

    def delete_role(self, role_key: str) -> bool:
        """Delete a role from memory."""
        self._log_call("delete_role", role_key=role_key)

        if not role_key:
            raise ValueError("role_key is required")

        for i, role in enumerate(self.roles):
            if role.key == role_key:
                del self.roles[i]
                return True

        raise LDNotFoundError(f"Role '{role_key}' not found")

    def delete_team(self, team_key: str) -> bool:
        """Delete a team from memory."""
        self._log_call("delete_team", team_key=team_key)

        if not team_key:
            raise ValueError("team_key is required")

        for i, team in enumerate(self.teams):
            if team.key == team_key:
                del self.teams[i]
                return True

        raise LDNotFoundError(f"Team '{team_key}' not found")

    # =========================================================================
    # Test Helper Methods
    # =========================================================================

    def add_test_project(self, key: str, name: str, tags: Optional[List[str]] = None) -> None:
        """Add a test project (helper for tests)."""
        self.projects.append(LDProject(key=key, name=name, tags=tags or []))

    def add_test_environment(
        self, project_key: str, key: str, name: str, color: str = ""
    ) -> None:
        """Add a test environment (helper for tests)."""
        if project_key not in self.environments:
            self.environments[project_key] = []
        self.environments[project_key].append(
            LDEnvironment(key=key, name=name, color=color, project_key=project_key)
        )

    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self.call_log if call[0] == method_name)

    def get_calls(self, method_name: str) -> List[Dict[str, Any]]:
        """Get all calls to a method."""
        return [call[1] for call in self.call_log if call[0] == method_name]

    def reset(self) -> None:
        """Clear all data and call log."""
        self.projects = []
        self.environments = {}
        self.teams = []
        self.roles = []
        self.call_log = []
