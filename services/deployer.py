"""
Deployer Service
================

Orchestrates deployment of custom roles and teams to LaunchDarkly.

This module provides:
1. DeployStep enum - Status of each deployment step
2. DeployStepResult - Result of a single step
3. DeployResult - Overall deployment result with counters
4. Deployer - Main deployment orchestrator

Usage:
    from services import Deployer, MockLDClient

    client = MockLDClient()  # or LDClient(api_key="...")
    deployer = Deployer(client)

    result = deployer.deploy_all(payload)
    print(f"Created {result.roles_created} roles")
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from .ld_client_interface import LDClientInterface
from .ld_exceptions import (
    LDClientError,
    LDConflictError,
    LDValidationError,
    LDNotFoundError,
)
from .payload_builder import DeployPayload


# =============================================================================
# LESSON: Enum for Deployment States
# =============================================================================
# Using an Enum ensures we only use valid states.
# IDE autocomplete helps, and typos become impossible.


class DeployStep(Enum):
    """
    Status of a deployment step.

    States:
        PENDING: Not yet started
        IN_PROGRESS: Currently executing
        COMPLETED: Successfully finished
        SKIPPED: Skipped (dry-run or already exists)
        FAILED: Failed with error
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


# =============================================================================
# LESSON: Dataclass for Step Results
# =============================================================================
# Each deployment step (creating a role or team) produces a result.
# We track what happened so we can report to the user.


@dataclass
class DeployStepResult:
    """
    Result of a single deployment step.

    Attributes:
        resource_type: Type of resource ("role" or "team")
        resource_key: Unique key of the resource
        status: Final status of the step
        message: Human-readable status message
        error: Error message if failed
    """
    resource_type: str  # "role" or "team"
    resource_key: str   # e.g., "developer-test-env"
    status: DeployStep
    message: str = ""
    error: Optional[str] = None

    def is_success(self) -> bool:
        """Check if step was successful (completed or skipped)."""
        return self.status in (DeployStep.COMPLETED, DeployStep.SKIPPED)


# =============================================================================
# LESSON: Dataclass for Overall Results
# =============================================================================
# The DeployResult aggregates all step results and provides summary counts.
# It has helper methods to add steps and generate summaries.


@dataclass
class DeployResult:
    """
    Overall deployment result.

    Tracks counts of created/skipped/failed resources and
    collects all individual step results.

    Attributes:
        success: True if no failures occurred
        roles_created: Number of roles successfully created
        roles_skipped: Number of roles skipped (existing or dry-run)
        roles_failed: Number of roles that failed to create
        teams_created: Number of teams successfully created
        teams_skipped: Number of teams skipped
        teams_failed: Number of teams that failed to create
        steps: List of all step results
        errors: List of error messages
        duration_seconds: Total deployment duration
    """
    success: bool = True
    roles_created: int = 0
    roles_skipped: int = 0
    roles_failed: int = 0
    teams_created: int = 0
    teams_skipped: int = 0
    teams_failed: int = 0
    steps: List[DeployStepResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    def get_summary(self) -> str:
        """Generate human-readable summary."""
        status = "succeeded" if self.success else "failed"
        lines = [
            f"Deployment {status}",
            f"  Roles: {self.roles_created} created, {self.roles_skipped} skipped, {self.roles_failed} failed",
            f"  Teams: {self.teams_created} created, {self.teams_skipped} skipped, {self.teams_failed} failed",
            f"  Duration: {self.duration_seconds:.1f}s"
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)

    def add_step(self, step: DeployStepResult) -> None:
        """
        Add a step result and update counters.

        Args:
            step: The step result to add
        """
        self.steps.append(step)

        # Update appropriate counter based on resource type and status
        if step.resource_type == "role":
            if step.status == DeployStep.COMPLETED:
                self.roles_created += 1
            elif step.status == DeployStep.SKIPPED:
                self.roles_skipped += 1
            elif step.status == DeployStep.FAILED:
                self.roles_failed += 1
                self.success = False

        elif step.resource_type == "team":
            if step.status == DeployStep.COMPLETED:
                self.teams_created += 1
            elif step.status == DeployStep.SKIPPED:
                self.teams_skipped += 1
            elif step.status == DeployStep.FAILED:
                self.teams_failed += 1
                self.success = False

        # Collect error messages
        if step.error:
            self.errors.append(f"{step.resource_type}/{step.resource_key}: {step.error}")


# =============================================================================
# LESSON: Progress Callback Type
# =============================================================================
# Define the callback signature for type hints.
# Callbacks let the UI update progress bars, logs, etc.

# Callback signature: (step_result, current_step, total_steps) -> None
ProgressCallback = Callable[[DeployStepResult, int, int], None]


# =============================================================================
# LESSON: Deployer Class - Main Orchestrator
# =============================================================================
# The Deployer coordinates the deployment process:
# 1. Creates roles first (teams reference roles)
# 2. Creates teams after roles exist
# 3. Tracks progress and errors
# 4. Supports dry-run and rollback


class Deployer:
    """
    Deployment orchestrator for LaunchDarkly resources.

    Handles the deployment of custom roles and teams in the correct order.
    Supports dry-run mode, progress callbacks, and rollback.

    Attributes:
        client: LaunchDarkly client (real or mock)
        dry_run: If True, validate only without creating resources
        skip_existing: If True, skip resources that already exist
        progress_callback: Called after each step for UI updates

    Example:
        deployer = Deployer(client, dry_run=False)
        result = deployer.deploy_all(payload)
        print(result.get_summary())
    """

    def __init__(
        self,
        client: LDClientInterface,
        dry_run: bool = False,
        skip_existing: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ):
        """
        Initialize the deployer.

        Args:
            client: LaunchDarkly client instance (required)
            dry_run: If True, skip actual API calls
            skip_existing: If True, skip conflicting resources
            progress_callback: Optional callback for progress updates

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("client is required")

        self.client = client
        self.dry_run = dry_run
        self.skip_existing = skip_existing
        self.progress_callback = progress_callback

        # =============================================================================
        # LESSON: Tracking Created Resources for Rollback
        # =============================================================================
        # We track what we create so we can delete it if something goes wrong.
        # This implements the "Saga" pattern for distributed transactions.
        self.created_roles: List[str] = []
        self.created_teams: List[str] = []

    def deploy_all(self, payload: DeployPayload) -> DeployResult:
        """
        Deploy all roles and teams from payload.

        Deploys in order:
        1. All custom roles
        2. All teams (which reference the roles)

        Args:
            payload: LDPayload containing roles and teams to deploy

        Returns:
            DeployResult with counts and step details
        """
        start_time = time.time()
        result = DeployResult()

        # Calculate total steps for progress reporting
        total_steps = len(payload.roles) + len(payload.teams)
        current_step = 0

        # =============================================================================
        # LESSON: Deployment Order Matters!
        # =============================================================================
        # Roles must exist before teams can reference them.
        # If we created teams first, they'd fail with "role not found".

        # Phase 1: Deploy all roles
        for role in payload.roles:
            current_step += 1
            step_result = self._deploy_role(role)
            result.add_step(step_result)
            self._notify_progress(step_result, current_step, total_steps)

            # Track created roles for potential rollback
            if step_result.status == DeployStep.COMPLETED:
                self.created_roles.append(role["key"])

        # Phase 2: Deploy all teams
        for team in payload.teams:
            current_step += 1
            step_result = self._deploy_team(team)
            result.add_step(step_result)
            self._notify_progress(step_result, current_step, total_steps)

            # Track created teams for potential rollback
            if step_result.status == DeployStep.COMPLETED:
                self.created_teams.append(team["key"])

        result.duration_seconds = time.time() - start_time
        return result

    def deploy_roles(self, roles: List[Dict[str, Any]]) -> DeployResult:
        """
        Deploy only roles (partial deployment).

        Useful when you want to create roles without teams,
        or when retrying failed role deployments.

        Args:
            roles: List of role data dictionaries

        Returns:
            DeployResult for role deployment
        """
        start_time = time.time()
        result = DeployResult()
        total_steps = len(roles)

        for i, role in enumerate(roles):
            step_result = self._deploy_role(role)
            result.add_step(step_result)
            self._notify_progress(step_result, i + 1, total_steps)

            if step_result.status == DeployStep.COMPLETED:
                self.created_roles.append(role["key"])

        result.duration_seconds = time.time() - start_time
        return result

    def deploy_teams(self, teams: List[Dict[str, Any]]) -> DeployResult:
        """
        Deploy only teams (partial deployment).

        Assumes required roles already exist.
        Useful when retrying failed team deployments.

        Args:
            teams: List of team data dictionaries

        Returns:
            DeployResult for team deployment
        """
        start_time = time.time()
        result = DeployResult()
        total_steps = len(teams)

        for i, team in enumerate(teams):
            step_result = self._deploy_team(team)
            result.add_step(step_result)
            self._notify_progress(step_result, i + 1, total_steps)

            if step_result.status == DeployStep.COMPLETED:
                self.created_teams.append(team["key"])

        result.duration_seconds = time.time() - start_time
        return result

    def _deploy_role(self, role: Dict[str, Any]) -> DeployStepResult:
        """
        Deploy a single custom role.

        Args:
            role: Role data dictionary with key, name, policy

        Returns:
            DeployStepResult indicating success/failure
        """
        role_key = role.get("key", "unknown")
        role_name = role.get("name", role_key)

        # =============================================================================
        # LESSON: Dry-Run Mode
        # =============================================================================
        # In dry-run mode, we don't make any API calls.
        # This lets users preview what would happen before committing.
        if self.dry_run:
            return DeployStepResult(
                resource_type="role",
                resource_key=role_key,
                status=DeployStep.SKIPPED,
                message=f"Dry-run: would create role '{role_name}'"
            )

        # =============================================================================
        # LESSON: Error Handling with Continue-on-Error
        # =============================================================================
        # We catch specific exceptions and continue to the next item.
        # This lets us deploy as much as possible even if some items fail.
        try:
            self.client.create_custom_role(role)
            return DeployStepResult(
                resource_type="role",
                resource_key=role_key,
                status=DeployStep.COMPLETED,
                message=f"Created role: {role_name}"
            )

        except LDConflictError:
            # Role already exists
            if self.skip_existing:
                return DeployStepResult(
                    resource_type="role",
                    resource_key=role_key,
                    status=DeployStep.SKIPPED,
                    message=f"Role already exists: {role_name}"
                )
            else:
                return DeployStepResult(
                    resource_type="role",
                    resource_key=role_key,
                    status=DeployStep.FAILED,
                    error=f"Role already exists: {role_name}"
                )

        except LDValidationError as e:
            return DeployStepResult(
                resource_type="role",
                resource_key=role_key,
                status=DeployStep.FAILED,
                error=f"Validation error: {str(e)}"
            )

        except LDClientError as e:
            return DeployStepResult(
                resource_type="role",
                resource_key=role_key,
                status=DeployStep.FAILED,
                error=str(e)
            )

    def _deploy_team(self, team: Dict[str, Any]) -> DeployStepResult:
        """
        Deploy a single team.

        Args:
            team: Team data dictionary with key, name, customRoleKeys

        Returns:
            DeployStepResult indicating success/failure
        """
        team_key = team.get("key", "unknown")
        team_name = team.get("name", team_key)

        if self.dry_run:
            return DeployStepResult(
                resource_type="team",
                resource_key=team_key,
                status=DeployStep.SKIPPED,
                message=f"Dry-run: would create team '{team_name}'"
            )

        try:
            self.client.create_team(team)
            return DeployStepResult(
                resource_type="team",
                resource_key=team_key,
                status=DeployStep.COMPLETED,
                message=f"Created team: {team_name}"
            )

        except LDConflictError:
            if self.skip_existing:
                return DeployStepResult(
                    resource_type="team",
                    resource_key=team_key,
                    status=DeployStep.SKIPPED,
                    message=f"Team already exists: {team_name}"
                )
            else:
                return DeployStepResult(
                    resource_type="team",
                    resource_key=team_key,
                    status=DeployStep.FAILED,
                    error=f"Team already exists: {team_name}"
                )

        except LDValidationError as e:
            # Check for common "role not found" error
            error_msg = str(e).lower()
            if "role" in error_msg and "not found" in error_msg:
                return DeployStepResult(
                    resource_type="team",
                    resource_key=team_key,
                    status=DeployStep.FAILED,
                    error="Referenced role not found. Ensure roles are created first."
                )

            return DeployStepResult(
                resource_type="team",
                resource_key=team_key,
                status=DeployStep.FAILED,
                error=f"Validation error: {str(e)}"
            )

        except LDClientError as e:
            return DeployStepResult(
                resource_type="team",
                resource_key=team_key,
                status=DeployStep.FAILED,
                error=str(e)
            )

    def _notify_progress(
        self,
        step: DeployStepResult,
        current: int,
        total: int
    ) -> None:
        """
        Notify progress callback if set.

        Safely calls the callback, catching any errors to prevent
        callback issues from stopping deployment.

        Args:
            step: The step result
            current: Current step number (1-based)
            total: Total number of steps
        """
        if self.progress_callback is None:
            return

        try:
            self.progress_callback(step, current, total)
        except Exception:
            # =============================================================================
            # LESSON: Never Let Callbacks Crash Main Logic
            # =============================================================================
            # The callback is for UI updates. If it fails, we should still
            # continue deploying. Log the error but don't raise.
            pass

    def rollback(self) -> bool:
        """
        Delete all resources created in this deployment session.

        Deletes in reverse order (teams first, then roles) because
        teams reference roles.

        Returns:
            True if all deletions succeeded, False if any failed
        """
        success = True

        # =============================================================================
        # LESSON: Rollback in Reverse Order
        # =============================================================================
        # We delete teams before roles because teams reference roles.
        # Also, we delete in reverse order of creation.

        # Delete teams first
        for team_key in reversed(self.created_teams):
            try:
                self.client.delete_team(team_key)
            except LDNotFoundError:
                # Already deleted, that's fine
                pass
            except LDClientError:
                success = False

        # Delete roles after teams are gone
        for role_key in reversed(self.created_roles):
            try:
                self.client.delete_role(role_key)
            except LDNotFoundError:
                # Already deleted, that's fine
                pass
            except LDClientError:
                success = False

        # Clear tracking lists
        self.created_roles = []
        self.created_teams = []

        return success

    def reset_tracking(self) -> None:
        """Clear the created resource tracking lists."""
        self.created_roles = []
        self.created_teams = []
