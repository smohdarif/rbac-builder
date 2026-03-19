"""
LaunchDarkly Client Interface
=============================

Abstract base class defining the contract for LaunchDarkly API clients.

This module defines:
1. Data classes for API response objects (LDProject, LDEnvironment, etc.)
2. Abstract interface that both real and mock clients implement

Why use an interface?
- Enables dependency injection
- Real client for production, mock client for tests
- Code depends on interface, not implementation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# =============================================================================
# LESSON: Data Classes for API Responses
# =============================================================================
# These represent resources returned by the LaunchDarkly API.
# Using dataclasses gives us type hints, __repr__, and clean code.


@dataclass
class LDProject:
    """
    Represents a LaunchDarkly project.

    A project is a container for feature flags and environments.

    Attributes:
        key: Unique identifier (e.g., "mobile-app")
        name: Display name (e.g., "Mobile Application")
        tags: List of tags for organization
    """
    key: str
    name: str
    tags: List[str] = field(default_factory=list)


@dataclass
class LDEnvironment:
    """
    Represents a LaunchDarkly environment.

    Environments are isolated flag configurations within a project
    (e.g., development, staging, production).

    Attributes:
        key: Unique identifier within project (e.g., "production")
        name: Display name (e.g., "Production")
        color: Hex color for UI display
        project_key: Key of parent project
    """
    key: str
    name: str
    color: str = ""
    project_key: str = ""


@dataclass
class LDTeam:
    """
    Represents a LaunchDarkly team.

    Teams are groups of members with shared roles.

    Attributes:
        key: Unique identifier (e.g., "developers")
        name: Display name (e.g., "Developers")
        description: Team description
        member_count: Number of members in team
        roles: List of custom role keys assigned to team
    """
    key: str
    name: str
    description: str = ""
    member_count: int = 0
    roles: List[str] = field(default_factory=list)


@dataclass
class LDCustomRole:
    """
    Represents a LaunchDarkly custom role.

    Custom roles define specific permissions through policies.

    Attributes:
        key: Unique identifier (e.g., "developer-test-env")
        name: Display name (e.g., "Developer - Test Environment")
        description: Role description
        policy: List of policy statements
    """
    key: str
    name: str
    description: str = ""
    policy: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# LESSON: Abstract Base Class (ABC)
# =============================================================================
# An ABC defines methods that subclasses MUST implement.
# This creates a contract - both LDClient and MockLDClient must have
# the same methods, making them interchangeable.


class LDClientInterface(ABC):
    """
    Abstract interface for LaunchDarkly API client.

    This interface defines all methods that an LD client must implement.
    Both the real LDClient and MockLDClient implement this interface,
    allowing them to be used interchangeably.

    Usage:
        def deploy(client: LDClientInterface):
            # Works with real or mock client
            projects = client.list_projects()

    Methods:
        health_check: Verify API connectivity
        list_projects: Get all projects
        list_environments: Get environments in a project
        list_teams: Get all teams
        list_custom_roles: Get all custom roles
        create_custom_role: Create a new custom role
        create_team: Create a new team
        update_team: Update an existing team
        delete_role: Delete a custom role
        delete_team: Delete a team
    """

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the API is accessible.

        Returns:
            True if API responds successfully, False otherwise
        """
        pass

    @abstractmethod
    def list_projects(self) -> List[LDProject]:
        """
        List all projects in the account.

        Returns:
            List of LDProject objects
        """
        pass

    @abstractmethod
    def list_environments(self, project_key: str) -> List[LDEnvironment]:
        """
        List all environments in a project.

        Args:
            project_key: Key of the project

        Returns:
            List of LDEnvironment objects

        Raises:
            LDNotFoundError: If project doesn't exist
        """
        pass

    @abstractmethod
    def list_teams(self) -> List[LDTeam]:
        """
        List all teams in the account.

        Returns:
            List of LDTeam objects
        """
        pass

    @abstractmethod
    def list_custom_roles(self) -> List[LDCustomRole]:
        """
        List all custom roles in the account.

        Returns:
            List of LDCustomRole objects
        """
        pass

    @abstractmethod
    def create_custom_role(self, role_data: Dict[str, Any]) -> LDCustomRole:
        """
        Create a new custom role.

        Args:
            role_data: Role configuration dict with keys:
                - key: Unique identifier
                - name: Display name
                - description: Optional description
                - policy: List of policy statements

        Returns:
            Created LDCustomRole object

        Raises:
            LDConflictError: If role with key already exists
            LDValidationError: If role_data is invalid
        """
        pass

    @abstractmethod
    def create_team(self, team_data: Dict[str, Any]) -> LDTeam:
        """
        Create a new team.

        Args:
            team_data: Team configuration dict with keys:
                - key: Unique identifier
                - name: Display name
                - description: Optional description
                - customRoleKeys: List of role keys to assign

        Returns:
            Created LDTeam object

        Raises:
            LDConflictError: If team with key already exists
            LDValidationError: If team_data is invalid
        """
        pass

    @abstractmethod
    def update_team(self, team_key: str, patch_data: List[Dict[str, Any]]) -> LDTeam:
        """
        Update an existing team using JSON Patch.

        Args:
            team_key: Key of team to update
            patch_data: JSON Patch operations, e.g.:
                [{"op": "add", "path": "/customRoleKeys/-", "value": "new-role"}]

        Returns:
            Updated LDTeam object

        Raises:
            LDNotFoundError: If team doesn't exist
            LDValidationError: If patch is invalid
        """
        pass

    @abstractmethod
    def delete_role(self, role_key: str) -> bool:
        """
        Delete a custom role.

        Args:
            role_key: Key of role to delete

        Returns:
            True if deleted successfully

        Raises:
            LDNotFoundError: If role doesn't exist
        """
        pass

    @abstractmethod
    def delete_team(self, team_key: str) -> bool:
        """
        Delete a team.

        Args:
            team_key: Key of team to delete

        Returns:
            True if deleted successfully

        Raises:
            LDNotFoundError: If team doesn't exist
        """
        pass
