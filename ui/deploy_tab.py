"""
Deploy Tab - Validation, Payload Generation, Save/Download, API Deployment
===========================================================================

This module renders Tab 3: Deploy.

Responsibilities:
- Configuration validation display
- LaunchDarkly payload generation
- Save configuration to server
- Download JSON export
- API key configuration and connection testing
- Real deployment to LaunchDarkly API
- Progress tracking and results display
- Rollback on failure

Phase 8 Update: Added real LaunchDarkly API deployment functionality.
"""

import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict, Any, Callable

from models import RBACConfig, Team, EnvironmentGroup


# =============================================================================
# LESSON: Type Aliases for Clarity
# =============================================================================
# Type aliases make complex types more readable
# This callback receives: step result, current index, total count

ProgressCallback = Callable[['DeployStepResult', int, int], None]


# =============================================================================
# Helper Functions (Public - for testing)
# =============================================================================

def build_config_from_session() -> RBACConfig:
    """
    Build an RBACConfig object from current session state.

    Returns:
        RBACConfig object populated from session state
    """
    # Convert teams DataFrame to Team objects
    teams = []
    if "teams" in st.session_state:
        for row in st.session_state.teams.to_dict(orient="records"):
            key = row.get("Key", row.get("key", ""))
            if key:  # Skip empty rows
                teams.append(Team(
                    key=key,
                    name=row.get("Name", row.get("name", "")),
                    description=row.get("Description", row.get("description", ""))
                ))

    # Convert env_groups DataFrame to EnvironmentGroup objects
    env_groups = []
    if "env_groups" in st.session_state:
        for row in st.session_state.env_groups.to_dict(orient="records"):
            key = row.get("Key", row.get("key", ""))
            if key:  # Skip empty rows
                env_groups.append(EnvironmentGroup(
                    key=key,
                    requires_approval=row.get("Requires Approvals", row.get("requires_approval", False)),
                    is_critical=row.get("Critical", row.get("is_critical", False)),
                    notes=row.get("Notes", row.get("notes", ""))
                ))

    # Build and return config
    return RBACConfig(
        customer_name=st.session_state.get("_customer_name", ""),
        project_key=st.session_state.get("project", "default"),
        mode=st.session_state.get("_mode", "Manual"),
        teams=teams,
        env_groups=env_groups
    )


def _build_config_dict(customer_name: str, mode: str) -> Dict[str, Any]:
    """
    Build configuration dictionary for JSON export.

    Args:
        customer_name: Customer name
        mode: Mode (Manual/Connected)

    Returns:
        Dictionary ready for JSON serialization
    """
    return {
        "version": "1.0",
        "customer_name": customer_name,
        "project_key": st.session_state.get("project", "default"),
        "mode": mode,
        "teams": st.session_state.teams.to_dict(orient="records") if "teams" in st.session_state else [],
        "env_groups": st.session_state.env_groups.to_dict(orient="records") if "env_groups" in st.session_state else [],
        "project_permissions": st.session_state.project_matrix.to_dict(orient="records") if "project_matrix" in st.session_state else [],
        "env_permissions": st.session_state.env_matrix.to_dict(orient="records") if "env_matrix" in st.session_state else []
    }


# =============================================================================
# LESSON: Session State Initialization
# =============================================================================
# Always initialize session state keys with defaults to avoid KeyError
# This pattern ensures consistent state across reruns

def _initialize_deploy_state():
    """
    Initialize all deployment-related session state.

    LESSON: This is called at the start of render_deploy_tab to ensure
    all required session state keys exist before we try to use them.
    """
    defaults = {
        # API Configuration
        "ld_api_key": "",
        "ld_connection_verified": False,
        "ld_connection_error": None,

        # Deployment Options
        "deploy_dry_run": False,
        "deploy_skip_existing": True,

        # Deployment State
        "deploy_in_progress": False,
        "deploy_progress": 0.0,
        "deploy_steps": [],
        "deploy_result": None,

        # For rollback capability
        "deployer_instance": None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# =============================================================================
# Private Render Functions - Original
# =============================================================================

def _render_summary(customer_name: str) -> None:
    """Render deployment summary metrics."""
    st.subheader("Deployment Summary")

    num_teams = len(st.session_state.teams) if "teams" in st.session_state else 0
    num_env_groups = len(st.session_state.env_groups) if "env_groups" in st.session_state else 0
    generation_mode = st.session_state.get("generation_mode", "hardcoded")

    # =============================================================================
    # LESSON 42: Role Count Calculation Differs by Mode
    # =============================================================================
    # Hardcoded mode:
    #   - 1 project role per team + 1 environment role per team × environment
    #   - Total = num_teams + (num_teams × num_env_groups)
    #
    # Role Attributes mode:
    #   - 1 template role per permission type (regardless of teams)
    #   - Roughly ~10-15 template roles (project + env permissions used)
    #
    if generation_mode == "role_attributes":
        # Count unique permissions enabled in matrices
        from core.ld_actions import PROJECT_PERMISSION_MAP, ENV_PERMISSION_MAP

        num_project_perms = 0
        num_env_perms = 0

        if "project_matrix" in st.session_state:
            for col in PROJECT_PERMISSION_MAP.keys():
                if col in st.session_state.project_matrix.columns:
                    if st.session_state.project_matrix[col].any():
                        num_project_perms += 1

        if "env_matrix" in st.session_state:
            for col in ENV_PERMISSION_MAP.keys():
                if col in st.session_state.env_matrix.columns:
                    if st.session_state.env_matrix[col].any():
                        num_env_perms += 1

        num_custom_roles = num_project_perms + num_env_perms
        mode_label = "Role Attributes"
    else:
        # Hardcoded mode calculation
        num_project_roles = num_teams
        num_env_roles = num_teams * num_env_groups
        num_custom_roles = num_project_roles + num_env_roles
        mode_label = "Hardcoded"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Custom Roles", num_custom_roles)
    with col2:
        st.metric("Teams", num_teams)
    with col3:
        st.metric("Environment Groups", num_env_groups)
    with col4:
        st.metric("Mode", mode_label)


def _render_validation(customer_name: str):
    """
    Render validation section and return validation result.

    Returns:
        ValidationResult object
    """
    st.subheader("✅ Configuration Validation")

    from services import validate_from_session, Severity

    validation_result = validate_from_session(
        customer_name=customer_name,
        project_key=st.session_state.get("project", "default"),
        session_state=st.session_state
    )

    # Display validation status
    if validation_result.is_valid:
        if validation_result.warning_count == 0:
            st.success("✅ Configuration is valid! Ready to generate payloads.")
        else:
            st.warning(f"⚠️ Configuration is valid but has {validation_result.warning_count} warning(s)")
    else:
        st.error(f"❌ Configuration has {validation_result.error_count} error(s) that must be fixed")

    # Show errors
    if validation_result.errors:
        with st.expander(f"🚫 Errors ({validation_result.error_count})", expanded=True):
            for issue in validation_result.errors:
                st.markdown(f"**{issue.code}**: {issue.message}")
                if issue.suggestion:
                    st.caption(f"💡 {issue.suggestion}")

    # Show warnings
    if validation_result.warnings:
        with st.expander(f"⚠️ Warnings ({validation_result.warning_count})", expanded=False):
            for issue in validation_result.warnings:
                st.markdown(f"**{issue.code}**: {issue.message}")
                if issue.suggestion:
                    st.caption(f"💡 {issue.suggestion}")

    return validation_result


def _render_preview_json(customer_name: str, mode: str) -> None:
    """Render JSON preview expander."""
    with st.expander("📄 Preview JSON Payload", expanded=False):
        st.json({
            "customer": customer_name,
            "mode": mode,
            "teams": st.session_state.teams["Key"].tolist() if "teams" in st.session_state else [],
            "environment_groups": st.session_state.env_groups["Key"].tolist() if "env_groups" in st.session_state else [],
            "project_permissions": st.session_state.project_matrix.to_dict(orient="records") if "project_matrix" in st.session_state else [],
            "env_permissions": st.session_state.env_matrix.to_dict(orient="records") if "env_matrix" in st.session_state else []
        })


def _render_save_download_buttons(customer_name: str, mode: str, config_json: str) -> None:
    """Render save and download action buttons."""
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Configuration", use_container_width=True):
            try:
                from services import StorageService

                # Build config using helper
                # Store customer_name temporarily for build_config_from_session
                st.session_state._customer_name = customer_name
                st.session_state._mode = mode
                config = build_config_from_session()

                storage = StorageService()
                saved_path = storage.save(config)
                st.success(f"Configuration saved to: {saved_path.name}")
            except Exception as e:
                st.error(f"Error saving: {str(e)}")

    with col2:
        st.download_button(
            label="📥 Download JSON",
            data=config_json,
            file_name=f"{customer_name.lower().replace(' ', '_')}_rbac_config.json",
            mime="application/json",
            use_container_width=True
        )


# =============================================================================
# LESSON: Phase 8 - API Configuration Functions (NEW)
# =============================================================================
# These functions handle the LaunchDarkly API connection and deployment

def _render_api_config() -> None:
    """
    Render API configuration section with key input and connection test.

    LESSON: We use st.text_input with type="password" to hide the API key.
    The value is stored in session_state only (never persisted to disk).
    """
    st.subheader("🔑 API Configuration")

    # Create columns for input and button alignment
    col1, col2 = st.columns([3, 1])

    with col1:
        # LESSON: type="password" hides the characters
        api_key = st.text_input(
            "LaunchDarkly API Key",
            type="password",
            value=st.session_state.get("ld_api_key", ""),
            placeholder="Enter your API key...",
            help="API key with createRole and createTeam permissions"
        )

        # Store in session state (not persisted to disk)
        st.session_state.ld_api_key = api_key

    with col2:
        # Add spacing to align button with input field
        st.write("")  # Empty space for alignment
        if st.button("🔌 Test Connection", use_container_width=True):
            _test_connection(api_key)

    # Show connection status
    if st.session_state.get("ld_connection_verified"):
        st.success("✅ Connection verified!")
    elif st.session_state.get("ld_connection_error"):
        st.error(f"❌ {st.session_state.ld_connection_error}")


def _test_connection(api_key: str) -> None:
    """
    Test connection to LaunchDarkly API.

    LESSON: We catch specific exception types to provide helpful error messages.
    After updating session state, we use st.rerun() to refresh the UI.

    Args:
        api_key: The API key to test
    """
    # Import exceptions here to avoid circular imports
    from services import LDClient, LDAuthenticationError, LDClientError

    # Validate API key not empty
    if not api_key or api_key.strip() == "":
        st.session_state.ld_connection_verified = False
        st.session_state.ld_connection_error = "API key is required"
        st.rerun()
        return

    # Try to connect
    try:
        client = LDClient(api_key=api_key)
        success = client.health_check()

        if success:
            st.session_state.ld_connection_verified = True
            st.session_state.ld_connection_error = None
        else:
            st.session_state.ld_connection_verified = False
            st.session_state.ld_connection_error = "Health check failed"

    except LDAuthenticationError:
        st.session_state.ld_connection_verified = False
        st.session_state.ld_connection_error = "Invalid API key"

    except LDClientError as e:
        st.session_state.ld_connection_verified = False
        st.session_state.ld_connection_error = str(e)

    except Exception as e:
        st.session_state.ld_connection_verified = False
        st.session_state.ld_connection_error = f"Unexpected error: {str(e)}"

    # LESSON: st.rerun() forces the script to restart from the top
    # This is needed to update the UI based on the new session state values
    st.rerun()


def _render_deploy_options() -> None:
    """
    Render deployment options checkboxes.

    LESSON: st.checkbox returns the current value, so we store it
    directly back into session_state to persist across reruns.
    """
    st.subheader("⚙️ Deployment Options")

    col1, col2 = st.columns(2)

    with col1:
        dry_run = st.checkbox(
            "🧪 Dry-run mode",
            value=st.session_state.get("deploy_dry_run", False),
            help="Preview deployment without making changes"
        )
        st.session_state.deploy_dry_run = dry_run

    with col2:
        skip_existing = st.checkbox(
            "⏭️ Skip existing resources",
            value=st.session_state.get("deploy_skip_existing", True),
            help="Don't fail if role/team already exists"
        )
        st.session_state.deploy_skip_existing = skip_existing


def _render_deploy_button(payload) -> None:
    """
    Render the deploy button with appropriate enabled/disabled state.

    LESSON: Button disabled state depends on multiple session state values.
    We build the condition and show a helpful message explaining why
    the button is disabled.

    Args:
        payload: The DeployPayload to deploy
    """
    # Determine if button should be enabled
    api_key = st.session_state.get("ld_api_key", "")
    connection_verified = st.session_state.get("ld_connection_verified", False)
    deploy_in_progress = st.session_state.get("deploy_in_progress", False)

    has_resources = payload.get_role_count() + payload.get_team_count() > 0

    button_enabled = (
        api_key and
        connection_verified and
        not deploy_in_progress and
        has_resources
    )

    # Render deploy button
    if st.button(
        "🚀 Deploy to LaunchDarkly",
        type="primary",
        disabled=not button_enabled,
        use_container_width=True
    ):
        _execute_deployment(payload)

    # Show helpful message if disabled
    if not button_enabled:
        if not api_key:
            st.caption("Enter API key above")
        elif not connection_verified:
            st.caption("Test connection first")
        elif deploy_in_progress:
            st.caption("Deployment in progress...")
        elif not has_resources:
            st.caption("No resources to deploy")


def _create_progress_callback():
    """
    Create a progress callback that updates session state.

    LESSON: Streamlit doesn't update the UI mid-script execution.
    We store progress in session_state, then display accumulated
    results after deployment completes. This callback is called
    by the Deployer for each step.

    Returns:
        Callback function for Deployer progress tracking
    """
    def callback(step, current: int, total: int):
        # Update progress in session state
        st.session_state.deploy_progress = current / total if total > 0 else 0

        # Append step to list (for display after completion)
        if "deploy_steps" not in st.session_state:
            st.session_state.deploy_steps = []
        st.session_state.deploy_steps.append(step)

    return callback


def _execute_deployment(payload) -> None:
    """
    Execute the deployment to LaunchDarkly.

    LESSON: We use st.spinner to show a loading indicator during
    the blocking operation. After completion, we store the result
    in session_state and use st.rerun() to refresh the UI.

    Args:
        payload: The DeployPayload to deploy
    """
    from services import LDClient, Deployer, LDAuthenticationError, LDClientError

    # Set deployment in progress
    st.session_state.deploy_in_progress = True
    st.session_state.deploy_steps = []
    st.session_state.deploy_result = None
    st.session_state.deploy_progress = 0.0

    # Get options from session state
    api_key = st.session_state.ld_api_key
    dry_run = st.session_state.get("deploy_dry_run", False)
    skip_existing = st.session_state.get("deploy_skip_existing", True)

    try:
        # Create client and deployer
        client = LDClient(api_key=api_key)
        deployer = Deployer(
            client=client,
            dry_run=dry_run,
            skip_existing=skip_existing,
            progress_callback=_create_progress_callback()
        )

        # Store deployer for potential rollback
        st.session_state.deployer_instance = deployer

        # Execute deployment with spinner
        with st.spinner("Deploying to LaunchDarkly..."):
            result = deployer.deploy_all(payload)

        # Store result
        st.session_state.deploy_result = result

    except LDAuthenticationError:
        st.session_state.deploy_result = None
        st.error("❌ Authentication failed. Check your API key.")

    except LDClientError as e:
        st.session_state.deploy_result = None
        st.error(f"❌ Deployment failed: {str(e)}")

    except Exception as e:
        st.session_state.deploy_result = None
        st.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

    finally:
        st.session_state.deploy_in_progress = False

    # Rerun to show results
    st.rerun()


def _render_deploy_progress() -> None:
    """
    Render deployment progress bar and step details.

    LESSON: st.progress takes a value from 0.0 to 1.0.
    We display accumulated steps from session_state.
    """
    from services import DeployStep

    st.subheader("📊 Deployment Progress")

    # Get progress from session state
    progress = st.session_state.get("deploy_progress", 0.0)
    steps = st.session_state.get("deploy_steps", [])

    # Render progress bar
    st.progress(progress)

    # Render step details
    for step in steps:
        if step.status == DeployStep.COMPLETED:
            st.success(f"✅ {step.resource_key} (created)")
        elif step.status == DeployStep.SKIPPED:
            st.info(f"⏭️ {step.resource_key} (skipped)")
        elif step.status == DeployStep.FAILED:
            st.error(f"❌ {step.resource_key}: {step.error}")
        elif step.status == DeployStep.IN_PROGRESS:
            st.write(f"🔄 {step.resource_key} (in progress...)")


def _render_deploy_results(result) -> None:
    """
    Render deployment results summary.

    LESSON: st.metric is great for displaying key numbers.
    We use columns to show multiple metrics side by side.

    Args:
        result: DeployResult from the deployment
    """
    st.subheader("📋 Deployment Results")

    # Render summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("✅ Created", result.roles_created + result.teams_created)
    with col2:
        st.metric("⏭️ Skipped", result.roles_skipped + result.teams_skipped)
    with col3:
        st.metric("❌ Failed", result.roles_failed + result.teams_failed)
    with col4:
        st.metric("⏱️ Duration", f"{result.duration_seconds:.1f}s")

    # Show overall status
    if result.success:
        if st.session_state.get("deploy_dry_run"):
            st.success("🧪 Dry-run completed! No changes were made.")
        else:
            st.success("🎉 Deployment completed successfully!")
    else:
        st.error(f"⚠️ Deployment completed with {len(result.errors)} error(s)")

    # Show error details if any
    if result.errors:
        with st.expander(f"🚫 Error Details ({len(result.errors)})", expanded=True):
            for error in result.errors:
                st.error(error)

    # Show detailed steps
    with st.expander("📝 Detailed Steps", expanded=False):
        from services import DeployStep

        for step in result.steps:
            status_icon = {
                DeployStep.COMPLETED: "✅",
                DeployStep.SKIPPED: "⏭️",
                DeployStep.FAILED: "❌"
            }.get(step.status, "❓")

            st.write(f"{status_icon} **{step.resource_type}**: {step.resource_key}")
            if step.message:
                st.caption(f"   {step.message}")
            if step.error:
                st.caption(f"   Error: {step.error}")


def _render_rollback_button() -> None:
    """
    Render rollback button for failed deployments.

    LESSON: We only show rollback when:
    1. Deployment had errors
    2. Some resources were created (something to rollback)
    3. We have a deployer instance with rollback capability
    """
    result = st.session_state.get("deploy_result")
    deployer = st.session_state.get("deployer_instance")

    # Check if rollback is applicable
    if not result or not deployer:
        return
    if result.success:
        return  # No need to rollback success
    if result.roles_created + result.teams_created == 0:
        return  # Nothing to rollback

    # Render rollback section
    st.warning("Some resources were created before the failure.")

    if st.button("🔙 Rollback Created Resources", type="secondary"):
        with st.spinner("Rolling back..."):
            success = deployer.rollback()

        if success:
            st.success("✅ Rollback completed. Created resources have been deleted.")
            # Clear deployer instance
            st.session_state.deployer_instance = None
            st.rerun()
        else:
            st.error("⚠️ Rollback encountered errors. Some resources may remain.")


def _render_ld_payload_generator(customer_name: str, validation_result) -> None:
    """Render LaunchDarkly payload generator section."""
    generation_mode = st.session_state.get("generation_mode", "hardcoded")

    st.subheader("🚀 LaunchDarkly API Payloads")

    if generation_mode == "role_attributes":
        st.caption(
            "Generate **template roles** with `${roleAttribute/...}` placeholders "
            "and **teams** with roleAttributes"
        )
    else:
        st.caption("Generate API-ready JSON for creating custom roles and teams in LaunchDarkly")

    # Generate button - disabled if validation has errors
    generate_disabled = not validation_result.is_valid

    # Additional check for role_attributes mode: need project key
    if generation_mode == "role_attributes":
        project_key = st.session_state.get("project", "")
        if not project_key:
            generate_disabled = True
            generate_help = "Enter project key in Setup tab first"
        else:
            generate_help = "Fix validation errors first" if not validation_result.is_valid else "Generate template roles and teams"
    else:
        generate_help = "Fix validation errors first" if generate_disabled else "Generate LaunchDarkly API payloads"

    if st.button(
        "⚡ Generate LaunchDarkly Payloads",
        use_container_width=True,
        type="primary",
        disabled=generate_disabled,
        help=generate_help
    ):
        try:
            # =================================================================
            # LESSON 43: Choose Builder Based on Generation Mode
            # =================================================================
            if generation_mode == "role_attributes":
                from services import build_role_attribute_payload_from_session

                # Get project isolation options
                project_key = st.session_state.get("project", "default")
                prefix_team_keys = st.session_state.get("prefix_team_keys", True)
                team_name_format = st.session_state.get("team_name_format", "{project}: {team}")

                ld_payload = build_role_attribute_payload_from_session(
                    customer_name=customer_name,
                    project_key=project_key,
                    session_state=st.session_state,
                    prefix_team_keys=prefix_team_keys,
                    team_name_format=team_name_format
                )

                st.session_state.ld_payload = ld_payload
                st.success(
                    f"Generated {ld_payload.get_role_count()} template roles "
                    f"and {ld_payload.get_team_count()} teams with roleAttributes!"
                )
            else:
                from services import build_payload_from_session

                ld_payload = build_payload_from_session(
                    customer_name=customer_name,
                    project_key=st.session_state.get("project", "default"),
                    session_state=st.session_state
                )

                st.session_state.ld_payload = ld_payload
                st.success(f"Generated {ld_payload.get_role_count()} custom roles and {ld_payload.get_team_count()} teams!")

        except Exception as e:
            st.error(f"Error generating payloads: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    # Display generated payload
    if "ld_payload" in st.session_state and st.session_state.ld_payload:
        _render_ld_payload_display(customer_name)


def _render_ld_payload_display(customer_name: str) -> None:
    """Render the generated LD payload preview and download."""
    ld_payload = st.session_state.ld_payload

    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Custom Roles", ld_payload.get_role_count())
    with col2:
        st.metric("Teams", ld_payload.get_team_count())

    # Preview tabs
    role_tab, team_tab, full_tab = st.tabs(["📋 Custom Roles", "👥 Teams", "📄 Full Payload"])

    with role_tab:
        st.markdown("**Custom Roles** - Create these first in LaunchDarkly")
        for i, role in enumerate(ld_payload.roles):
            with st.expander(f"🔑 {role['name']}", expanded=(i == 0)):
                st.json(role)

    with team_tab:
        st.markdown("**Teams** - Create after custom roles exist")
        for team in ld_payload.teams:
            with st.expander(f"👥 {team['name']}"):
                st.json(team)

    with full_tab:
        st.markdown("**Complete Deployment Package**")
        st.json(ld_payload.to_dict())

    # Download buttons row
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download LD Payloads (JSON)",
            data=ld_payload.to_json(),
            file_name=f"{customer_name.lower().replace(' ', '_')}_ld_payloads.json",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )

    with col2:
        # =================================================================
        # LESSON: Dynamically generated Markdown documentation
        # =================================================================
        # We generate a human-readable deployment guide from the payload.
        # The customer receives both the JSON (to deploy) and the Markdown
        # (to understand what was built and how to apply it).
        from services import generate_deployment_guide
        project_key = st.session_state.get("project_key", "")
        doc_content = generate_deployment_guide(ld_payload, project_key)

        st.download_button(
            label="📄 Download Deployment Guide (Markdown)",
            data=doc_content,
            file_name=f"{customer_name.lower().replace(' ', '_')}_deployment_guide.md",
            mime="text/markdown",
            use_container_width=True
        )

    # =================================================================
    # LESSON: In-memory ZIP for the complete deployment package
    # =================================================================
    # Phase 13: PackageGenerator builds a ZIP in memory (no disk write).
    # The client unzips and runs: python deploy.py
    # See: services/package_generator.py
    st.divider()
    st.markdown("##### 📦 Complete Deployment Package")
    st.caption(
        "Everything the client needs in one ZIP: "
        "API-ready JSON files, a Python deploy script, and instructions. "
        "Client runs `python deploy.py` — no manual steps."
    )

    try:
        from services import PackageGenerator
        generator  = PackageGenerator(ld_payload, project_key)
        zip_bytes  = generator.generate_package()
        slug       = customer_name.lower().replace(" ", "_")

        st.download_button(
            label="📦 Download Deployment Package (ZIP)",
            data=zip_bytes,
            file_name=f"{slug}_rbac_deployment.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
    except Exception as e:
        st.error(f"Could not generate package: {e}")


# =============================================================================
# Main Render Function (Public)
# =============================================================================

def render_deploy_tab(customer_name: str = "", mode: str = "Manual") -> None:
    """
    Render the Deploy tab UI.

    This is the main entry point for Tab 3. It manages:
    - Configuration validation
    - Payload generation
    - Save/download functionality
    - API deployment (Connected mode)

    Args:
        customer_name: Customer name from sidebar
        mode: Mode selection (Manual/Connected) from sidebar
    """
    # Initialize deployment session state
    _initialize_deploy_state()

    st.header("Step 3: Review & Deploy")

    if not customer_name:
        st.info("Complete Step 1 first.")
        return

    # Summary section
    _render_summary(customer_name)

    st.divider()

    # Validation section
    validation_result = _render_validation(customer_name)

    st.divider()

    # JSON preview
    _render_preview_json(customer_name, mode)

    st.divider()

    # Build config JSON for save/download
    config_data = _build_config_dict(customer_name, mode)
    config_json = json.dumps(config_data, indent=2, default=str)

    # Save/download buttons
    _render_save_download_buttons(customer_name, mode, config_json)

    st.divider()

    # =====================================================================
    # LESSON: Mode-Based UI - Connected Mode Shows Deployment UI
    # =====================================================================
    # In Connected mode, we show the API configuration and deployment UI
    # In Manual mode, we just show a message to switch modes

    if mode == "Connected":
        # API Configuration
        _render_api_config()
        st.divider()

        # Deployment Options
        _render_deploy_options()
        st.divider()

        # Deploy section - only show if we have a payload
        if validation_result.is_valid:
            if "ld_payload" in st.session_state and st.session_state.ld_payload:
                payload = st.session_state.ld_payload

                # Deploy button
                _render_deploy_button(payload)

                # Progress (during deployment - though usually too fast to see)
                if st.session_state.get("deploy_in_progress"):
                    _render_deploy_progress()

                # Results (after deployment)
                if st.session_state.get("deploy_result"):
                    _render_deploy_results(st.session_state.deploy_result)
                    _render_rollback_button()

                st.divider()
            else:
                st.info("👆 Generate LaunchDarkly payload below to enable deployment")
    else:
        st.info("💡 Switch to **Connected** mode in the sidebar to deploy via API.")

    st.divider()

    # LD payload generator (always available)
    _render_ld_payload_generator(customer_name, validation_result)
