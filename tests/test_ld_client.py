"""
Tests for Phase 6: LaunchDarkly API Client
==========================================

Tests cover:
1. Custom exceptions
2. LDClient initialization
3. LDClient request handling
4. MockLDClient operations
5. Error handling
6. Interface compliance

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
    """Create a mock HTTP response."""
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.content = b'{"items": []}'
    response.json.return_value = {"items": []}
    response.headers = {}
    response.text = ""
    return response


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock()
    return session


@pytest.fixture
def ld_client(mock_session):
    """Create LDClient with mocked session."""
    from services.ld_client import LDClient

    with patch('services.ld_client.requests.Session', return_value=mock_session):
        client = LDClient(api_key="test-api-key")
        client.session = mock_session
    return client


@pytest.fixture
def mock_client():
    """Create MockLDClient instance."""
    from services.ld_client import MockLDClient
    return MockLDClient()


# =============================================================================
# Exception Tests
# =============================================================================

class TestLDExceptions:
    """Tests for custom exception classes."""

    def test_ld_client_error_base(self):
        """Test LDClientError is base exception."""
        from services.ld_exceptions import LDClientError, LDAuthenticationError

        with pytest.raises(LDClientError):
            raise LDAuthenticationError("test")

    def test_ld_rate_limit_error_has_retry_after(self):
        """Test LDRateLimitError stores retry_after."""
        from services.ld_exceptions import LDRateLimitError

        error = LDRateLimitError(retry_after=120)
        assert error.retry_after == 120
        assert "120" in str(error)

    def test_ld_validation_error_has_errors_list(self):
        """Test LDValidationError stores errors list."""
        from services.ld_exceptions import LDValidationError

        errors = [{"field": "key", "message": "required"}]
        error = LDValidationError("Invalid request", errors=errors)

        assert error.errors == errors

    def test_exception_from_response_400(self):
        """Test factory creates LDValidationError for 400."""
        from services.ld_exceptions import exception_from_response, LDValidationError

        exc = exception_from_response(400, "Bad request")
        assert isinstance(exc, LDValidationError)

    def test_exception_from_response_401(self):
        """Test factory creates LDAuthenticationError for 401."""
        from services.ld_exceptions import exception_from_response, LDAuthenticationError

        exc = exception_from_response(401, "Unauthorized")
        assert isinstance(exc, LDAuthenticationError)

    def test_exception_from_response_403(self):
        """Test factory creates LDAuthenticationError for 403."""
        from services.ld_exceptions import exception_from_response, LDAuthenticationError

        exc = exception_from_response(403, "Forbidden")
        assert isinstance(exc, LDAuthenticationError)

    def test_exception_from_response_404(self):
        """Test factory creates LDNotFoundError for 404."""
        from services.ld_exceptions import exception_from_response, LDNotFoundError

        exc = exception_from_response(404, "Not found")
        assert isinstance(exc, LDNotFoundError)

    def test_exception_from_response_409(self):
        """Test factory creates LDConflictError for 409."""
        from services.ld_exceptions import exception_from_response, LDConflictError

        exc = exception_from_response(409, "Conflict")
        assert isinstance(exc, LDConflictError)

    def test_exception_from_response_429(self):
        """Test factory creates LDRateLimitError for 429."""
        from services.ld_exceptions import exception_from_response, LDRateLimitError

        exc = exception_from_response(429, "Rate limited", headers={"Retry-After": "30"})
        assert isinstance(exc, LDRateLimitError)
        assert exc.retry_after == 30

    def test_exception_from_response_500(self):
        """Test factory creates LDServerError for 500."""
        from services.ld_exceptions import exception_from_response, LDServerError

        exc = exception_from_response(500, "Server error")
        assert isinstance(exc, LDServerError)


# =============================================================================
# LDClient Initialization Tests
# =============================================================================

class TestLDClientInit:
    """Tests for LDClient initialization."""

    def test_init_with_api_key(self):
        """Test client initializes with API key."""
        from services.ld_client import LDClient

        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test-key")

        assert client.api_key == "test-key"

    def test_init_with_empty_api_key_raises_error(self):
        """Test empty API key raises error."""
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

    def test_init_default_timeout(self):
        """Test default timeout is set."""
        from services.ld_client import LDClient

        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test-key")

        assert client.timeout == 30

    def test_init_custom_timeout(self):
        """Test custom timeout is set."""
        from services.ld_client import LDClient

        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test-key", timeout=60)

        assert client.timeout == 60


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

    def test_health_check_returns_false_on_failure(self, ld_client):
        """Test health check returns False when API fails."""
        ld_client.session.request.side_effect = requests.ConnectionError()

        result = ld_client.health_check()
        assert result is False

    def test_mock_client_health_check(self, mock_client):
        """Test mock client health check always returns True."""
        assert mock_client.health_check() is True


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

    def test_mock_client_list_projects_empty(self, mock_client):
        """Test mock client returns empty list initially."""
        projects = mock_client.list_projects()
        assert projects == []

    def test_mock_client_list_projects_with_data(self, mock_client):
        """Test mock client returns added projects."""
        mock_client.add_test_project("proj1", "Project 1")
        mock_client.add_test_project("proj2", "Project 2")

        projects = mock_client.list_projects()

        assert len(projects) == 2
        assert projects[0].key == "proj1"


# =============================================================================
# List Environments Tests
# =============================================================================

class TestListEnvironments:
    """Tests for listing environments."""

    def test_list_environments_requires_project_key(self, ld_client):
        """Test project_key is required."""
        with pytest.raises(ValueError, match="project_key"):
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

    def test_mock_client_list_environments_not_found(self, mock_client):
        """Test mock client raises error for nonexistent project."""
        from services.ld_exceptions import LDNotFoundError

        with pytest.raises(LDNotFoundError):
            mock_client.list_environments("nonexistent")

    def test_mock_client_list_environments_with_data(self, mock_client):
        """Test mock client returns added environments."""
        mock_client.add_test_project("proj1", "Project 1")
        mock_client.add_test_environment("proj1", "dev", "Development")
        mock_client.add_test_environment("proj1", "prod", "Production")

        envs = mock_client.list_environments("proj1")

        assert len(envs) == 2
        assert envs[0].key == "dev"


# =============================================================================
# Create Custom Role Tests
# =============================================================================

class TestCreateCustomRole:
    """Tests for creating custom roles."""

    def test_create_role_validates_required_fields(self, ld_client):
        """Test required fields are validated."""
        with pytest.raises(ValueError, match="Missing required field"):
            ld_client.create_custom_role({})

    def test_create_role_validates_key_field(self, ld_client):
        """Test key field is required."""
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

    def test_mock_client_create_role(self, mock_client):
        """Test mock client creates role."""
        role = mock_client.create_custom_role({
            "key": "test-role",
            "name": "Test Role",
            "policy": []
        })

        assert role.key == "test-role"
        assert len(mock_client.roles) == 1

    def test_mock_client_create_duplicate_role_raises_conflict(self, mock_client):
        """Test mock client raises conflict on duplicate."""
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


# =============================================================================
# Create Team Tests
# =============================================================================

class TestCreateTeam:
    """Tests for creating teams."""

    def test_create_team_validates_required_fields(self, ld_client):
        """Test required fields are validated."""
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

    def test_mock_client_create_team(self, mock_client):
        """Test mock client creates team."""
        team = mock_client.create_team({
            "key": "developers",
            "name": "Developers"
        })

        assert team.key == "developers"
        assert len(mock_client.teams) == 1

    def test_mock_client_create_duplicate_team_raises_conflict(self, mock_client):
        """Test mock client raises conflict on duplicate."""
        from services.ld_exceptions import LDConflictError

        mock_client.create_team({"key": "team1", "name": "Team 1"})

        with pytest.raises(LDConflictError):
            mock_client.create_team({"key": "team1", "name": "Team 1 Again"})


# =============================================================================
# Update Team Tests
# =============================================================================

class TestUpdateTeam:
    """Tests for updating teams."""

    def test_update_team_requires_key(self, ld_client):
        """Test team_key is required."""
        with pytest.raises(ValueError, match="team_key"):
            ld_client.update_team("", [{"op": "add"}])

    def test_update_team_requires_patch_data(self, ld_client):
        """Test patch_data is required."""
        with pytest.raises(ValueError, match="patch_data"):
            ld_client.update_team("my-team", [])

    def test_mock_client_update_team_adds_role(self, mock_client):
        """Test mock client can add role to team."""
        mock_client.create_team({
            "key": "developers",
            "name": "Developers"
        })

        patch = [{"op": "add", "path": "/customRoleKeys/-", "value": "new-role"}]
        updated = mock_client.update_team("developers", patch)

        assert "new-role" in updated.roles

    def test_mock_client_update_team_not_found(self, mock_client):
        """Test mock client raises error for nonexistent team."""
        from services.ld_exceptions import LDNotFoundError

        with pytest.raises(LDNotFoundError):
            mock_client.update_team("nonexistent", [{"op": "add"}])


# =============================================================================
# Delete Operations Tests
# =============================================================================

class TestDeleteOperations:
    """Tests for delete operations."""

    def test_delete_role_requires_key(self, ld_client):
        """Test role_key is required."""
        with pytest.raises(ValueError, match="role_key"):
            ld_client.delete_role("")

    def test_delete_team_requires_key(self, ld_client):
        """Test team_key is required."""
        with pytest.raises(ValueError, match="team_key"):
            ld_client.delete_team("")

    def test_mock_client_delete_role(self, mock_client):
        """Test mock client deletes role."""
        mock_client.create_custom_role({
            "key": "test-role",
            "name": "Test",
            "policy": []
        })
        assert len(mock_client.roles) == 1

        result = mock_client.delete_role("test-role")

        assert result is True
        assert len(mock_client.roles) == 0

    def test_mock_client_delete_role_not_found(self, mock_client):
        """Test mock client raises error for nonexistent role."""
        from services.ld_exceptions import LDNotFoundError

        with pytest.raises(LDNotFoundError):
            mock_client.delete_role("nonexistent")

    def test_mock_client_delete_team(self, mock_client):
        """Test mock client deletes team."""
        mock_client.create_team({"key": "team1", "name": "Team 1"})
        assert len(mock_client.teams) == 1

        result = mock_client.delete_team("team1")

        assert result is True
        assert len(mock_client.teams) == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in LDClient."""

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

    def test_conflict_error_on_409(self, ld_client, mock_response):
        """Test 409 raises conflict error."""
        from services.ld_exceptions import LDConflictError

        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.json.return_value = {"message": "Already exists"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDConflictError):
            ld_client.create_custom_role({
                "key": "existing",
                "name": "Existing",
                "policy": []
            })

    def test_validation_error_on_400(self, ld_client, mock_response):
        """Test 400 raises validation error."""
        from services.ld_exceptions import LDValidationError

        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid request",
            "errors": [{"field": "key", "message": "required"}]
        }
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDValidationError) as exc_info:
            ld_client.create_custom_role({
                "key": "test",
                "name": "Test",
                "policy": []
            })

        assert len(exc_info.value.errors) > 0

    def test_server_error_on_500(self, ld_client, mock_response):
        """Test 500 raises server error after retries."""
        from services.ld_exceptions import LDServerError

        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal error"}
        ld_client.session.request.return_value = mock_response

        with pytest.raises(LDServerError):
            ld_client.list_projects()


# =============================================================================
# Mock Client Helper Tests
# =============================================================================

class TestMockClientHelpers:
    """Tests for mock client helper methods."""

    def test_get_call_count(self, mock_client):
        """Test call counting."""
        mock_client.health_check()
        mock_client.list_projects()
        mock_client.list_projects()

        assert mock_client.get_call_count("health_check") == 1
        assert mock_client.get_call_count("list_projects") == 2
        assert mock_client.get_call_count("create_team") == 0

    def test_get_calls(self, mock_client):
        """Test getting call arguments."""
        mock_client.create_custom_role({
            "key": "role1",
            "name": "Role 1",
            "policy": []
        })
        mock_client.create_custom_role({
            "key": "role2",
            "name": "Role 2",
            "policy": []
        })

        calls = mock_client.get_calls("create_custom_role")

        assert len(calls) == 2
        assert calls[0]["role_data"]["key"] == "role1"
        assert calls[1]["role_data"]["key"] == "role2"

    def test_reset(self, mock_client):
        """Test reset clears all data."""
        mock_client.add_test_project("proj1", "Project 1")
        mock_client.create_custom_role({
            "key": "role1",
            "name": "Role 1",
            "policy": []
        })
        mock_client.list_projects()

        mock_client.reset()

        assert len(mock_client.projects) == 0
        assert len(mock_client.roles) == 0
        assert len(mock_client.call_log) == 0


# =============================================================================
# Interface Compliance Tests
# =============================================================================

class TestInterfaceCompliance:
    """Tests that both clients implement the interface."""

    def test_ld_client_implements_interface(self):
        """Test LDClient implements LDClientInterface."""
        from services.ld_client_interface import LDClientInterface
        from services.ld_client import LDClient

        with patch('services.ld_client.requests.Session'):
            client = LDClient(api_key="test")

        assert isinstance(client, LDClientInterface)

    def test_mock_client_implements_interface(self):
        """Test MockLDClient implements LDClientInterface."""
        from services.ld_client_interface import LDClientInterface
        from services.ld_client import MockLDClient

        client = MockLDClient()
        assert isinstance(client, LDClientInterface)

    def test_both_clients_have_same_methods(self):
        """Test both clients have the same public methods."""
        from services.ld_client import LDClient, MockLDClient

        with patch('services.ld_client.requests.Session'):
            real = LDClient(api_key="test")
        mock = MockLDClient()

        # Get public methods (not starting with _)
        real_methods = {m for m in dir(real) if not m.startswith('_') and callable(getattr(real, m))}
        mock_methods = {m for m in dir(mock) if not m.startswith('_') and callable(getattr(mock, m))}

        # Interface methods should exist in both
        interface_methods = {
            'health_check', 'list_projects', 'list_environments',
            'list_teams', 'list_custom_roles', 'create_custom_role',
            'create_team', 'update_team', 'delete_role', 'delete_team'
        }

        assert interface_methods.issubset(real_methods)
        assert interface_methods.issubset(mock_methods)


# =============================================================================
# Integration Test
# =============================================================================

class TestMockClientIntegration:
    """Integration tests with MockLDClient."""

    def test_full_workflow_with_mock_client(self, mock_client):
        """Test a complete deployment workflow."""
        # 1. Add a project
        mock_client.add_test_project("mobile-app", "Mobile App")

        # 2. Add environments
        mock_client.add_test_environment("mobile-app", "dev", "Development")
        mock_client.add_test_environment("mobile-app", "prod", "Production")

        # 3. Verify setup
        projects = mock_client.list_projects()
        assert len(projects) == 1

        envs = mock_client.list_environments("mobile-app")
        assert len(envs) == 2

        # 4. Create roles
        role1 = mock_client.create_custom_role({
            "key": "dev-role",
            "name": "Developer",
            "policy": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]
        })
        assert role1.key == "dev-role"

        # 5. Create team with role
        team = mock_client.create_team({
            "key": "developers",
            "name": "Developers",
            "customRoleKeys": ["dev-role"]
        })
        assert team.key == "developers"
        assert "dev-role" in team.roles

        # 6. Verify state
        assert len(mock_client.roles) == 1
        assert len(mock_client.teams) == 1

        # 7. Cleanup
        mock_client.delete_team("developers")
        mock_client.delete_role("dev-role")

        assert len(mock_client.roles) == 0
        assert len(mock_client.teams) == 0


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
