"""
LaunchDarkly Action Mappings
============================

This module maps our UI permission names to LaunchDarkly's actual API action codes.

LESSON 19: Enum for Type-Safe Mappings
======================================
We use Enums to define constants that can't be accidentally misspelled.
Each enum value contains the list of LD actions that permission grants.
"""

from enum import Enum
from typing import List, Dict


# =============================================================================
# LESSON 20: Project-Level Action Mappings
# =============================================================================
# These actions apply at the project level (not environment-specific)
# Resource format: proj/{project-key}

class ProjectAction(Enum):
    """
    Maps UI permission names to LaunchDarkly project-level actions.

    Usage:
        >>> actions = ProjectAction.CREATE_FLAGS.value
        >>> print(actions)
        ['createFlag']
    """

    # Flag lifecycle actions
    # Terraform: per-project/create-flags uses cloneFlag + createFlag
    CREATE_FLAGS = [
        "cloneFlag",
        "createFlag"
    ]

    # Terraform: per-project/manage-flags with update_metadata=true, update_tags=true, update_variations=true
    UPDATE_FLAGS = [
        # Metadata actions
        "createFlagLink",
        "deleteFlagLink",
        "updateDescription",
        "updateFlagCustomProperties",
        "updateFlagDefaultVariations",
        "updateFlagLink",
        "manageFlagFollowers",
        "updateDeprecated",
        "updateMaintainer",
        "updateName",
        "updateTemporary",
        # Tags
        "updateTags",
        # Variations
        "updateFlagVariations"
    ]
    # =================================================================
    # LESSON: Archive vs Delete
    # =================================================================
    # "updateGlobalArchived" = soft delete (can be unarchived)
    # "deleteFlag" = permanent deletion (NOT used here - too destructive)
    # Archive is the standard pattern for flag lifecycle management
    ARCHIVE_FLAGS = ["updateGlobalArchived"]

    # Client-side availability
    CLIENT_SIDE = ["updateClientSideFlagAvailability"]

    # =================================================================
    # LESSON: "Manage" = Full CRUD (Create, Read, Update, Delete)
    # =================================================================
    # Terraform uses "*" for metrics (all actions including delete)
    # If you need granular control, split into separate UI permissions
    MANAGE_METRICS = [
        "createMetric",
        "updateMetric",
        "deleteMetric"  # NOTE: Includes delete - this is full "manage" access
    ]

    # Release pipelines - full CRUD access
    # Terraform: per-project/manage-release-pipelines with all toggles enabled
    MANAGE_PIPELINES = [
        "createReleasePipeline",
        "deleteReleasePipeline",
        "updateReleasePipelineDescription",
        "updateReleasePipelineName",
        "updateReleasePipelinePhase",
        "updateReleasePipelinePhaseName",
        "updateReleasePipelineTags"
    ]

    # View project (read-only)
    VIEW_PROJECT = ["viewProject"]

    # =================================================================
    # AI Configs - Project Level (from terraform per-project modules)
    # =================================================================
    # Terraform: per-project/create-ai-configs
    CREATE_AI_CONFIGS = ["createAIConfig"]

    # Terraform: per-project/update-ai-configs
    UPDATE_AI_CONFIGS = ["updateAIConfig"]

    # Terraform: per-project/create-update-ai-configs (combined)
    CREATE_UPDATE_AI_CONFIGS = [
        "createAIConfig",
        "updateAIConfig"
    ]

    # Terraform: per-project/delete-ai-configs
    DELETE_AI_CONFIGS = ["deleteAIConfig"]

    # Terraform: per-project/manage-ai-config-variations
    MANAGE_AI_CONFIG_VARIATIONS = [
        "updateAIConfigVariation",
        "deleteAIConfigVariation"
    ]


# =============================================================================
# LESSON 21: Environment-Level Action Mappings
# =============================================================================
# These actions apply within a specific environment
# Resource format: proj/{project-key}:env/{env-key}

class EnvironmentAction(Enum):
    """
    Maps UI permission names to LaunchDarkly environment-level actions.

    These are scoped to specific environments (e.g., production, staging).
    """

    # Flag targeting - the core feature flag operations
    # Terraform: per-environment/update-targeting includes ALL these actions
    UPDATE_TARGETING = [
        # Core targeting actions
        "copyFlagConfigFrom",
        "copyFlagConfigTo",
        "createApprovalRequest",  # NOTE: Terraform puts this HERE, not in Apply Changes
        "updateExpiringTargets",
        "updateFallthrough",
        "updateFeatureWorkflows",
        "updateOffVariation",
        "updateOn",
        "updatePrerequisites",
        "updateRules",
        "updateScheduledChanges",
        "updateTargets",
        # Measured rollout actions
        "updateMeasuredRolloutConfiguration",
        "updateFallthroughWithMeasuredRollout",
        "stopMeasuredRolloutOnFlagFallthrough",
        "stopMeasuredRolloutOnFlagRule"
    ]

    # Approval workflow actions
    # Terraform: per-environment/review-changes
    REVIEW_CHANGES = [
        "reviewApprovalRequest",
        "updateApprovalRequest"
    ]

    # Terraform: per-environment/apply-changes (only applyApprovalRequest)
    # NOTE: createApprovalRequest is in UPDATE_TARGETING per terraform pattern
    APPLY_CHANGES = [
        "applyApprovalRequest"
    ]
    BYPASS_APPROVAL = ["bypassRequiredApproval"]

    # Segments within environment
    # Terraform: per-environment/manage-segments combines CRUD + targeting
    MANAGE_SEGMENTS = [
        # CRUD actions (from manage-segments module)
        "createSegment",
        "deleteSegment",
        "updateDescription",
        "updateName",
        "updateTags",
        # Targeting actions (from update_targeting option)
        "updateExcluded",
        "updateExpiringTargets",
        "updateIncluded",
        "updateRules",
        # Approval actions for segments
        "createApprovalRequest",
        "updateApprovalRequest"
    ]

    # =================================================================
    # Experiments (from Gonfalon ExperimentKind)
    # =================================================================
    # Terraform uses actions = ["*"] for experiments
    # Valid actions from Gonfalon: createExperiment, updateExperiment, updateExperimentArchived
    # Note: There is NO startExperiment or stopExperiment - use updateExperimentArchived
    MANAGE_EXPERIMENTS = [
        "createExperiment",
        "updateExperiment",
        "updateExperimentArchived"  # Archives/unarchives (effectively start/stop)
    ]

    # SDK Key visibility
    VIEW_SDK_KEY = ["viewSdkKey"]

    # Holdouts (experiment exclusions)
    MANAGE_HOLDOUTS = [
        "createHoldout",
        "updateHoldout",
        "deleteHoldout"
    ]

    # Triggers (webhooks that toggle flags)
    MANAGE_TRIGGERS = [
        "createTrigger",
        "updateTrigger",
        "deleteTrigger"
    ]

    # AI Config Targeting (added Jun 2025)
    UPDATE_AI_CONFIG_TARGETING = ["updateAIConfigTargeting"]


# =============================================================================
# LESSON 22: UI Column to Action Mapping
# =============================================================================
# These dictionaries map the DataFrame column names to our Enum values
# This is the "glue" between the UI and the action codes

# Project-level: Maps DataFrame column name -> ProjectAction enum
# These match the columns in the Project Permissions matrix UI
PROJECT_PERMISSION_MAP: Dict[str, ProjectAction] = {
    "Create Flags": ProjectAction.CREATE_FLAGS,
    "Update Flags": ProjectAction.UPDATE_FLAGS,
    "Archive Flags": ProjectAction.ARCHIVE_FLAGS,
    "Update Client Side Availability": ProjectAction.CLIENT_SIDE,
    "Manage Metrics": ProjectAction.MANAGE_METRICS,
    "Manage Release Pipelines": ProjectAction.MANAGE_PIPELINES,
    "Create AI Configs": ProjectAction.CREATE_AI_CONFIGS,
    "Update AI Configs": ProjectAction.UPDATE_AI_CONFIGS,
    "Delete AI Configs": ProjectAction.DELETE_AI_CONFIGS,
    "Manage AI Variations": ProjectAction.MANAGE_AI_CONFIG_VARIATIONS,
    "View Project": ProjectAction.VIEW_PROJECT,
}

# Environment-level: Maps DataFrame column name -> EnvironmentAction enum
# These match the columns in the Environment Permissions matrix UI
ENV_PERMISSION_MAP: Dict[str, EnvironmentAction] = {
    "Update Targeting": EnvironmentAction.UPDATE_TARGETING,
    "Review Changes": EnvironmentAction.REVIEW_CHANGES,
    "Apply Changes": EnvironmentAction.APPLY_CHANGES,
    "Manage Segments": EnvironmentAction.MANAGE_SEGMENTS,
    "Manage Experiments": EnvironmentAction.MANAGE_EXPERIMENTS,
    "Update AI Config Targeting": EnvironmentAction.UPDATE_AI_CONFIG_TARGETING,
    "View SDK Key": EnvironmentAction.VIEW_SDK_KEY,
}


# =============================================================================
# LESSON 23: Helper Functions
# =============================================================================

def get_project_actions(permission_name: str) -> List[str]:
    """
    Get LaunchDarkly actions for a project-level permission.

    Args:
        permission_name: The UI column name (e.g., "Create Flags")

    Returns:
        List of LD action strings, or empty list if not found

    Example:
        >>> get_project_actions("Create Flags")
        ['createFlag']
    """
    if permission_name in PROJECT_PERMISSION_MAP:
        return PROJECT_PERMISSION_MAP[permission_name].value
    return []


def get_env_actions(permission_name: str) -> List[str]:
    """
    Get LaunchDarkly actions for an environment-level permission.

    Args:
        permission_name: The UI column name (e.g., "Update Targeting")

    Returns:
        List of LD action strings, or empty list if not found

    Example:
        >>> get_env_actions("Update Targeting")
        ['updateOn', 'updateFallthrough', 'updateTargets', ...]
    """
    if permission_name in ENV_PERMISSION_MAP:
        return ENV_PERMISSION_MAP[permission_name].value
    return []


def get_all_project_permissions() -> List[str]:
    """Return all project-level permission names (UI column names)."""
    return list(PROJECT_PERMISSION_MAP.keys())


def get_all_env_permissions() -> List[str]:
    """Return all environment-level permission names (UI column names)."""
    return list(ENV_PERMISSION_MAP.keys())


# =============================================================================
# LESSON 24: Resource String Builders
# =============================================================================

def build_project_resource(project_key: str) -> str:
    """
    Build a project-level resource string.

    Example:
        >>> build_project_resource("mobile-app")
        'proj/mobile-app'
    """
    return f"proj/{project_key}"


def build_flag_resource(project_key: str, env_key: str = None) -> str:
    """
    Build a flag resource string.

    Args:
        project_key: The project key
        env_key: Optional environment key. If None, uses env/* for all envs.

    Examples:
        >>> build_flag_resource("mobile-app")
        'proj/mobile-app:env/*:flag/*'
        >>> build_flag_resource("mobile-app", "production")
        'proj/mobile-app:env/production:flag/*'

    Note:
        LaunchDarkly requires env/* in the path even for project-level flag actions.
        This matches the terraform pattern: proj/%s:env/*:flag/%s
    """
    if env_key:
        return f"proj/{project_key}:env/{env_key}:flag/*"
    return f"proj/{project_key}:env/*:flag/*"


def build_segment_resource(project_key: str, env_key: str = None) -> str:
    """
    Build a segment resource string.

    Examples:
        >>> build_segment_resource("mobile-app")
        'proj/mobile-app:env/*:segment/*'
        >>> build_segment_resource("mobile-app", "production")
        'proj/mobile-app:env/production:segment/*'

    Note:
        LaunchDarkly requires env/* in the path even for project-level segment actions.
    """
    if env_key:
        return f"proj/{project_key}:env/{env_key}:segment/*"
    return f"proj/{project_key}:env/*:segment/*"


def build_env_resource(project_key: str, env_key: str) -> str:
    """
    Build an environment resource string.

    Example:
        >>> build_env_resource("mobile-app", "production")
        'proj/mobile-app:env/production'
    """
    return f"proj/{project_key}:env/{env_key}"


def build_experiment_resource(project_key: str, env_key: str) -> str:
    """
    Build an experiment resource string.

    Experiments are environment-scoped resources.

    Example:
        >>> build_experiment_resource("mobile-app", "production")
        'proj/mobile-app:env/production:experiment/*'
    """
    return f"proj/{project_key}:env/{env_key}:experiment/*"


# =============================================================================
# LESSON 33: Role Attribute Resource Builders (Phase 11)
# =============================================================================
# These functions build resource strings with ${roleAttribute/...} placeholders
# instead of hardcoded project/environment values.
#
# The placeholders are filled in at team level via roleAttributes.
# This enables ONE role template to work for MANY teams/projects.

def build_role_attribute_resource(
    project_attr: str = "projects",
    resource_type: str = "flag"
) -> str:
    """
    Build a project-level resource string with role attribute placeholder.

    Args:
        project_attr: Name of the role attribute for projects (default: "projects")
        resource_type: Type of resource (flag, segment, experiment, etc.)

    Returns:
        Resource string with ${roleAttribute/...} placeholder

    Example:
        >>> build_role_attribute_resource("projects", "flag")
        'proj/${roleAttribute/projects}:env/*:flag/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/*:{resource_type}/*"


def build_env_role_attribute_resource(
    project_attr: str,
    env_attr: str,
    resource_type: str = "flag"
) -> str:
    """
    Build an environment-scoped resource with role attribute placeholders.

    This is used for environment-level permissions where we need to scope
    by BOTH project AND environment using role attributes.

    Args:
        project_attr: Name of role attribute for projects (e.g., "projects")
        env_attr: Name of role attribute for environments (e.g., "updateTargetingEnvironments")
        resource_type: Type of resource (flag, segment, experiment)

    Returns:
        Resource string with two ${roleAttribute/...} placeholders

    Example:
        >>> build_env_role_attribute_resource("projects", "updateTargetingEnvironments", "flag")
        'proj/${roleAttribute/projects}:env/${roleAttribute/updateTargetingEnvironments}:flag/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/${{roleAttribute/{env_attr}}}:{resource_type}/*"


def build_project_only_role_attribute_resource(project_attr: str = "projects") -> str:
    """
    Build a project-only resource with role attribute placeholder.

    Used for actions like viewProject that don't need env/flag scope.

    Example:
        >>> build_project_only_role_attribute_resource("projects")
        'proj/${roleAttribute/projects}'
    """
    return f"proj/${{roleAttribute/{project_attr}}}"


def build_context_kind_role_attribute_resource(project_attr: str = "projects") -> str:
    """
    Build a context-kind resource with role attribute placeholder.

    Context kinds are project-scoped resources. By default, flag creation/update
    roles include context kind permissions so users can create context kinds when
    creating or updating flags.

    This matches the ps-terraform default behaviour where:
      create_context_kind = coalesce(manage_context_kinds_in_flag_roles, !manage_context_kinds)
      = coalesce(null, !false) = true  (included by default)

    Example:
        >>> build_context_kind_role_attribute_resource("projects")
        'proj/${roleAttribute/projects}:context-kind/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:context-kind/*"


# =============================================================================
# Context Kind actions included by default in flag roles
# =============================================================================
# Matches ps-terraform manage-flags/main.tf default behaviour:
# - create-flags role gets: createContextKind
# - update-flags role gets: updateContextKind, updateAvailabilityForExperiments
#
# These are separate policy statements on context-kind/* resource.

CONTEXT_KIND_ACTIONS_FOR_PERMISSION: Dict[str, List[str]] = {
    "Create Flags": ["createContextKind"],
    "Update Flags": ["updateContextKind", "updateAvailabilityForExperiments"],
}


# =============================================================================
# LESSON 42: Critical Environment Resource Builders (Phase 12)
# =============================================================================
# These functions build resource strings with the LaunchDarkly critical
# environment specifier: *;{critical:true} or *;{critical:false}
#
# This allows a single role to match ALL environments that have the
# matching critical flag set in LaunchDarkly.
#
# Example:
#   - *;{critical:true} matches Production, DR (all critical envs)
#   - *;{critical:false} matches Dev, QA, Staging, INT (all non-critical envs)

def build_critical_env_role_attribute_resource(
    project_attr: str = "projects",
    resource_type: str = "flag"
) -> str:
    """
    Build a resource string for CRITICAL environments using wildcard specifier.

    Uses *;{critical:true} to match ALL environments in LaunchDarkly that
    have their critical flag set to true.

    Args:
        project_attr: Name of role attribute for projects (default: "projects")
        resource_type: Type of resource (flag, segment, experiment)

    Returns:
        Resource string with critical environment wildcard

    Example:
        >>> build_critical_env_role_attribute_resource("projects", "flag")
        'proj/${roleAttribute/projects}:env/*;{critical:true}:flag/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:true}}:{resource_type}/*"


def build_non_critical_env_role_attribute_resource(
    project_attr: str = "projects",
    resource_type: str = "flag"
) -> str:
    """
    Build a resource string for NON-CRITICAL environments using wildcard specifier.

    Uses *;{critical:false} to match ALL environments in LaunchDarkly that
    have their critical flag set to false.

    Args:
        project_attr: Name of role attribute for projects (default: "projects")
        resource_type: Type of resource (flag, segment, experiment)

    Returns:
        Resource string with non-critical environment wildcard

    Example:
        >>> build_non_critical_env_role_attribute_resource("projects", "flag")
        'proj/${roleAttribute/projects}:env/*;{critical:false}:flag/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:false}}:{resource_type}/*"


def build_critical_env_only_resource(project_attr: str = "projects") -> str:
    """
    Build environment-only resource for critical environments.

    Used for actions like viewSdkKey that target the environment itself,
    not resources within it.

    Example:
        >>> build_critical_env_only_resource("projects")
        'proj/${roleAttribute/projects}:env/*;{critical:true}'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:true}}"


def build_non_critical_env_only_resource(project_attr: str = "projects") -> str:
    """
    Build environment-only resource for non-critical environments.

    Used for actions like viewSdkKey that target the environment itself,
    not resources within it.

    Example:
        >>> build_non_critical_env_only_resource("projects")
        'proj/${roleAttribute/projects}:env/*;{critical:false}'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:false}}"


# =============================================================================
# LESSON 34: Permission to Role Attribute Name Mapping
# =============================================================================
# Maps UI permission names to the role attribute names used in templates.
#
# - Project-level permissions all use "projects" attribute
# - Environment-level permissions each get their own attribute
#   (e.g., "updateTargetingEnvironments", "manageSegmentsEnvironments")
#
# This follows the ps-terraform-private pattern where teams specify
# which environments they can perform each action in.

PERMISSION_ATTRIBUTE_MAP: Dict[str, str] = {
    # =========================================================================
    # Project-Level Permissions (all use "projects" attribute)
    # =========================================================================
    "Create Flags": "projects",
    "Update Flags": "projects",
    "Archive Flags": "projects",
    "Update Client Side Availability": "projects",
    "Manage Metrics": "projects",
    "Manage Release Pipelines": "projects",
    "Create AI Configs": "projects",
    "Update AI Configs": "projects",
    "Delete AI Configs": "projects",
    "Manage AI Variations": "projects",
    "View Project": "projects",

    # =========================================================================
    # Environment-Level Permissions (each has own attribute for env scoping)
    # =========================================================================
    # LESSON: Kebab-case matches the sa-demo/ps-terraform pattern exactly.
    # These keys must match the ${roleAttribute/...} placeholder in the role
    # AND the role_attributes block key on the team — they are the same string.
    "Update Targeting": "update-targeting-environments",
    "Review Changes": "review-changes-environments",
    "Apply Changes": "apply-changes-environments",
    "Manage Segments": "manage-segments-environments",
    "Manage Experiments": "manage-experiments-environments",
    "Update AI Config Targeting": "update-ai-config-targeting-environments",
    "View SDK Key": "view-sdk-key-environments",
}


def get_attribute_name(permission_name: str) -> str:
    """
    Get the role attribute name for a permission.

    Args:
        permission_name: UI column name (e.g., "Update Targeting")

    Returns:
        Role attribute name (e.g., "updateTargetingEnvironments")

    Example:
        >>> get_attribute_name("Update Targeting")
        'updateTargetingEnvironments'
        >>> get_attribute_name("Create Flags")
        'projects'
    """
    return PERMISSION_ATTRIBUTE_MAP.get(permission_name, "projects")


def is_project_level_permission(permission_name: str) -> bool:
    """
    Check if a permission is project-level (not environment-specific).

    Project-level permissions use just "projects" attribute.
    Environment-level permissions have their own environment attribute.

    Example:
        >>> is_project_level_permission("Create Flags")
        True
        >>> is_project_level_permission("Update Targeting")
        False
    """
    return permission_name in PROJECT_PERMISSION_MAP


def is_env_level_permission(permission_name: str) -> bool:
    """
    Check if a permission is environment-level.

    Example:
        >>> is_env_level_permission("Update Targeting")
        True
        >>> is_env_level_permission("Create Flags")
        False
    """
    return permission_name in ENV_PERMISSION_MAP


def get_resource_type_for_permission(permission_name: str) -> str:
    """
    Get the LaunchDarkly resource type for a permission.

    Most permissions target flags, but some target segments or experiments.

    Example:
        >>> get_resource_type_for_permission("Manage Segments")
        'segment'
        >>> get_resource_type_for_permission("Update Targeting")
        'flag'
    """
    if permission_name == "Manage Segments":
        return "segment"
    elif permission_name == "Manage Experiments":
        return "experiment"
    else:
        return "flag"


# =============================================================================
# Module test (runs when file is executed directly)
# =============================================================================
if __name__ == "__main__":
    print("=== LaunchDarkly Action Mappings Test ===\n")

    # Test project actions
    print("Project Actions for 'Create Flags':")
    print(f"  {get_project_actions('Create Flags')}")

    print("\nProject Actions for 'Update Flags':")
    print(f"  {get_project_actions('Update Flags')}")

    # Test environment actions
    print("\nEnvironment Actions for 'Update Targeting':")
    print(f"  {get_env_actions('Update Targeting')}")

    # Test resource builders
    print("\nResource String Examples:")
    print(f"  Project: {build_project_resource('mobile-app')}")
    print(f"  Flag (all envs): {build_flag_resource('mobile-app')}")
    print(f"  Flag (prod): {build_flag_resource('mobile-app', 'production')}")
    print(f"  Segment: {build_segment_resource('mobile-app', 'production')}")

    # Test critical environment resource builders (Phase 12)
    print("\nCritical Environment Resource Examples:")
    print(f"  Critical flag: {build_critical_env_role_attribute_resource('projects', 'flag')}")
    print(f"  Non-critical flag: {build_non_critical_env_role_attribute_resource('projects', 'flag')}")
    print(f"  Critical segment: {build_critical_env_role_attribute_resource('projects', 'segment')}")
    print(f"  Critical env only: {build_critical_env_only_resource('projects')}")
    print(f"  Non-critical env only: {build_non_critical_env_only_resource('projects')}")

    print("\n✅ All tests passed!")
