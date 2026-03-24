"""
Advisor Tab — AI-Powered RBAC Recommendations
================================================

This module renders Tab 4: Sage (Role Designer AI).

Responsibilities:
- Chat interface with Gemini-powered AI
- Context panel showing current Setup state
- Starter prompts for quick-start scenarios
- Context preamble injection (first message)
- Apply button to populate Setup + Matrix tabs

LESSON: Streamlit Chat Components
===================================
st.chat_message: renders a message with an avatar (user/assistant)
st.chat_input: text box pinned to bottom of page
st.empty(): placeholder that can be overwritten (for streaming)

See docs/phases/phase27/PYTHON_CONCEPTS.md for detailed explanations.
"""

import os
import streamlit as st
import pandas as pd
from typing import Optional

from services.ai_advisor import RBACAdvisor, AdvisorError


# =============================================================================
# Session State Keys
# =============================================================================

ADVISOR_MESSAGES_KEY = "advisor_messages"
ADVISOR_INSTANCE_KEY = "advisor_instance"
ADVISOR_LAST_RECOMMENDATION_KEY = "advisor_last_recommendation"
ADVISOR_CONTEXT_SENT_KEY = "_advisor_context_sent"


# =============================================================================
# LESSON: Starter Prompts — Pre-Built Use Cases
# =============================================================================
# SAs pick a scenario and optionally edit before sending.
# Based on real engagement patterns from sa-demo, Epassi, Voya, S2 template.

STARTER_PROMPTS = [
    {
        "label": "🏁 Standard S2 — 5 Teams, 4 Environments",
        "prompt": (
            "We follow the standard LaunchDarkly S2 structure. "
            "Teams: Developer, Senior Developer, QA, Product Manager, Release Manager. "
            "Environments: development, test, staging (all non-critical), production (critical). "
            "We need approval workflows in production with proper separation of duties."
        ),
    },
    {
        "label": "🚀 Startup — Small Team, 2 Environments",
        "prompt": (
            "We're a small team with just Developers and one Admin. "
            "Two environments: development (non-critical) and production (critical). "
            "Developers should have full access in dev but no production access. "
            "Admin handles everything in production."
        ),
    },
    {
        "label": "🏢 Enterprise — Dev, QA, SRE with Observability",
        "prompt": (
            "We have 4 teams: Frontend Dev, Backend Dev, QA, and SRE. "
            "Environments: test (non-critical) and production (critical). "
            "Backend also manages AI configs. "
            "SRE needs full observability access (sessions, errors, logs, traces, alerts, dashboards) "
            "for incident response. Strict separation of duties in production."
        ),
    },
    {
        "label": "🤝 With Contractors — Internal + External Teams",
        "prompt": (
            "We have internal Developers and external Contractors working on the same project. "
            "Environments: dev (non-critical) and production (critical). "
            "Contractors should have the same productivity as developers in dev, "
            "but limited access in production. No destructive operations for contractors."
        ),
    },
    {
        "label": "🔬 Experimentation Focus — A/B Testing Teams",
        "prompt": (
            "We run heavy experimentation. Teams: Developer, Data Scientist, QA, Product Manager. "
            "Environments: test (non-critical), staging (non-critical), production (critical). "
            "Data Scientists need to manage experiments and metrics in staging and production. "
            "Developers create flags and configure targeting. QA validates in test."
        ),
    },
    {
        "label": "📋 Just Tell Me Best Practices",
        "prompt": (
            "What are the LaunchDarkly RBAC best practices for a typical engineering org? "
            "What teams should I create, and what's the recommended permission split "
            "between critical and non-critical environments?"
        ),
    },
]


# =============================================================================
# Helper Functions
# =============================================================================

def _get_gemini_api_key() -> str:
    """
    Get the Gemini API key from Streamlit secrets or environment variable.
    Admin-provided — SAs do NOT enter their own key.
    """
    # Streamlit Cloud: secrets management (.streamlit/secrets.toml)
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        # No secrets.toml file exists — fall through to env var
        pass

    # Localhost: environment variable
    return os.environ.get("GEMINI_API_KEY", "")


def _initialize_session_state() -> None:
    """Set up session state keys for the advisor tab."""
    if ADVISOR_MESSAGES_KEY not in st.session_state:
        st.session_state[ADVISOR_MESSAGES_KEY] = []
    if ADVISOR_LAST_RECOMMENDATION_KEY not in st.session_state:
        st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = None


def _get_context_from_setup() -> dict:
    """
    Read teams, environments, and project from Setup tab's session state.
    Returns a dict with the context, or empty values if not configured.
    """
    teams_df = st.session_state.get("teams", pd.DataFrame())
    env_df = st.session_state.get("env_groups", pd.DataFrame())
    project = st.session_state.get("project", "")

    teams = teams_df["Name"].tolist() if not teams_df.empty and "Name" in teams_df.columns else []

    environments = []
    if not env_df.empty and "Key" in env_df.columns:
        for _, row in env_df.iterrows():
            environments.append({
                "key": row.get("Key", ""),
                "critical": bool(row.get("Critical", False)),
            })

    return {
        "teams": teams,
        "environments": environments,
        "project_key": project,
    }


def _build_user_message(raw_input: str, context: dict) -> str:
    """
    Wrap the SA's first message with current context as a preamble.

    LESSON: Context Preamble
    =========================
    System prompt has guardrails + knowledge (static).
    Context preamble has customer data (dynamic, per-session).
    Injected on FIRST message only — chat history carries it forward.
    SA never sees the preamble in the chat UI.
    """
    if not st.session_state.get(ADVISOR_CONTEXT_SENT_KEY):
        parts = []
        if context.get("project_key"):
            parts.append(f"Project: {context['project_key']}")
        if context.get("teams"):
            parts.append(f"Teams: {', '.join(context['teams'])}")
        if context.get("environments"):
            env_strs = []
            for e in context["environments"]:
                crit = "critical" if e.get("critical") else "non-critical"
                env_strs.append(f"{e['key']} ({crit})")
            parts.append(f"Environments: {', '.join(env_strs)}")

        st.session_state[ADVISOR_CONTEXT_SENT_KEY] = True

        if parts:
            preamble = "[Customer context: " + ", ".join(parts) + "]\n\n"
            return preamble + raw_input

    return raw_input


# =============================================================================
# Render Functions
# =============================================================================

def _render_context_panel(context: dict) -> None:
    """Show what the AI knows about the customer's setup."""
    with st.expander("📋 Context from Setup", expanded=False):
        if context["project_key"]:
            st.markdown(f"**Project:** `{context['project_key']}`")
        else:
            st.info("No project configured yet — the AI will work from your description.")

        if context["teams"]:
            st.markdown("**Teams:** " + ", ".join(context["teams"]))
        else:
            st.info("No teams configured yet — describe them in chat.")

        if context["environments"]:
            for env in context["environments"]:
                badge = "🔴 critical" if env["critical"] else "🟢 non-critical"
                st.markdown(f"- `{env['key']}` ({badge})")
        else:
            st.info("No environments configured yet — describe them in chat.")

        st.caption("Tip: Configure the Setup tab first for best results, or just describe everything in chat.")


def _render_message_content(content: str) -> None:
    """
    Render a message, collapsing any ```json blocks into an expander.
    The explanation stays visible; the JSON is tucked away.
    """
    import re
    # Split on the LAST ```json ... ``` block
    pattern = r"(```json\s*.*?\s*```)"
    parts = re.split(pattern, content, flags=re.DOTALL)

    has_json = len(parts) > 1

    if has_json:
        # Everything before the JSON block
        before = "".join(parts[:-2]).strip() if len(parts) > 2 else ""
        json_block = parts[-2]  # the ```json ... ``` block
        after = parts[-1].strip() if parts[-1].strip() else ""

        if before:
            st.markdown(before)
        with st.expander("📋 View JSON Recommendation", expanded=False):
            st.markdown(json_block)
        if after:
            st.markdown(after)
    else:
        st.markdown(content)


def _render_chat_history() -> None:
    """Render all previous messages in the conversation."""
    for msg in st.session_state[ADVISOR_MESSAGES_KEY]:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_message_content(msg["content"])
            else:
                st.markdown(msg["content"])


def _render_starter_prompts() -> Optional[str]:
    """
    Render clickable starter prompt buttons when chat is empty.
    Returns the selected prompt text, or None if nothing clicked.
    """
    st.markdown("**Quick start — pick a scenario:**")

    # 2 columns, 3 rows
    for i in range(0, len(STARTER_PROMPTS), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(STARTER_PROMPTS):
                starter = STARTER_PROMPTS[idx]
                with col:
                    if st.button(
                        starter["label"],
                        key=f"starter_{idx}",
                        use_container_width=True,
                    ):
                        return starter["prompt"]

    st.divider()
    st.caption("Or type your own scenario below.")
    return None


def _apply_recommendation(recommendation: dict, context: dict) -> bool:
    """
    Write the AI's recommendation to BOTH Setup and Matrix in session_state.

    Phase A — Populate Setup (Step 1):
      Create teams/envs from recommendation if not already configured.
    Phase B — Populate Matrix (Step 2):
      Write project_matrix and env_matrix DataFrames.
    """
    try:
        project_rec = recommendation.get("project", {})
        env_rec = recommendation.get("environment", {})

        # =============================================================
        # Phase A: Populate Setup tab
        # =============================================================

        # Teams — derive from recommendation keys
        rec_team_names = list(project_rec.keys())
        if not rec_team_names:
            st.error("No team data found in the recommendation.")
            return False

        teams_df = st.session_state.get("teams", pd.DataFrame())
        existing_team_names = (
            set(teams_df["Name"].tolist())
            if not teams_df.empty and "Name" in teams_df.columns
            else set()
        )

        if not existing_team_names or existing_team_names != set(rec_team_names):
            st.session_state.teams = pd.DataFrame({
                "Key": [name.lower().replace(" ", "-") for name in rec_team_names],
                "Name": rec_team_names,
                "Description": ["" for _ in rec_team_names],
            })
            # Clear old data_editor widget keys (all versions)
            for k in [k for k in st.session_state if isinstance(k, str) and k.startswith("teams_editor")]:
                del st.session_state[k]

        # Environments — derive from recommendation env keys
        rec_env_keys: set = set()
        for team_envs in env_rec.values():
            rec_env_keys.update(team_envs.keys())
        rec_env_keys_sorted = sorted(rec_env_keys)

        env_df = st.session_state.get("env_groups", pd.DataFrame())
        existing_env_keys = (
            set(env_df["Key"].tolist())
            if not env_df.empty and "Key" in env_df.columns
            else set()
        )

        if not existing_env_keys or existing_env_keys != rec_env_keys:
            # Clear old data_editor widget keys (all versions)
            for k in [k for k in st.session_state if isinstance(k, str) and k.startswith("env_groups_editor")]:
                del st.session_state[k]
            env_rows = []
            for env_key in rec_env_keys_sorted:
                # Infer critical from context or naming convention
                is_critical = (
                    env_key.lower() in ("production", "prod")
                    or any(
                        e.get("key") == env_key and e.get("critical", False)
                        for e in context.get("environments", [])
                    )
                )
                env_rows.append({
                    "Key": env_key,
                    "Requires Approvals": is_critical,
                    "Critical": is_critical,
                    "Notes": "",
                })
            st.session_state.env_groups = pd.DataFrame(env_rows)

        # Project key — use context if available, otherwise generate from customer name
        if not st.session_state.get("project"):
            if context.get("project_key"):
                st.session_state.project = context["project_key"]
            else:
                # Derive from customer name or use a sensible default
                customer = st.session_state.get("_advisor_customer_name", "")
                if customer and customer != "AI-Generated":
                    st.session_state.project = customer.lower().replace(" ", "-")
                else:
                    st.session_state.project = "my-project"

        # Generation mode default
        if "generation_mode" not in st.session_state:
            st.session_state.generation_mode = "role_attributes"

        # Customer name — set via a separate session_state key
        # that the sidebar text_input reads as its default value.
        # Can't modify the widget directly after it renders.
        if not st.session_state.get("_advisor_customer_name"):
            st.session_state["_advisor_customer_name"] = (
                context.get("project_key") or "AI-Generated"
            )

        # =============================================================
        # Phase B: Populate Matrix tab
        # =============================================================
        # Force the matrix tab to regenerate by clearing ALL related
        # session state — matrices, widget keys, everything.
        keys_to_clear = [
            k for k in list(st.session_state.keys())
            if isinstance(k, str) and (
                k.startswith("proj_")
                or k.startswith("env_")
                or k in ("project_matrix", "env_matrix")
            )
        ]
        for k in keys_to_clear:
            del st.session_state[k]

        teams_df = st.session_state.get("teams", pd.DataFrame())
        env_df = st.session_state.get("env_groups", pd.DataFrame())

        team_names = (
            teams_df["Name"].tolist()
            if not teams_df.empty and "Name" in teams_df.columns
            else rec_team_names
        )
        env_keys = (
            env_df["Key"].tolist()
            if not env_df.empty and "Key" in env_df.columns
            else rec_env_keys_sorted
        )

        # Build project matrix using ALL known permissions (not just
        # the ones in the recommendation). This ensures the matrix tab
        # sees every column and renders checkboxes correctly.
        from core.ld_actions import get_all_project_permissions, get_all_env_permissions
        all_project_perms = get_all_project_permissions()
        all_env_perms = get_all_env_permissions()

        project_data: dict = {"Team": team_names}
        for perm in all_project_perms:
            project_data[perm] = [
                project_rec.get(team, {}).get(perm, False)
                for team in team_names
            ]
        st.session_state.project_matrix = pd.DataFrame(project_data)

        # Build env matrix using ALL known env permissions
        env_rows = []
        for team in team_names:
            for env_key in env_keys:
                row: dict = {"Team": team, "Environment": env_key}
                for perm in all_env_perms:
                    row[perm] = (
                        env_rec
                        .get(team, {})
                        .get(env_key, {})
                        .get(perm, False)
                    )
                env_rows.append(row)
        st.session_state.env_matrix = pd.DataFrame(env_rows)

        # Signal to the matrix tab to trust this data (skip sync)
        st.session_state["_advisor_applied"] = True
        # Bump the matrix version so widget keys change and Streamlit
        # creates fresh checkboxes instead of restoring cached values
        st.session_state["_matrix_version"] = st.session_state.get("_matrix_version", 0) + 1

        return True

    except Exception as e:
        st.error(f"Failed to apply recommendation: {e}")
        return False


# =============================================================================
# Main Entry Point
# =============================================================================

def render_advisor_tab(customer_name: str = "") -> None:
    """
    Main entry point for Tab 4: Sage (Role Designer AI).
    Called from app.py.
    """
    _initialize_session_state()

    st.header("🤖 Sage — Role Designer AI")
    st.markdown(
        "Describe your teams and access needs — get an instant RBAC blueprint powered by AI."
    )

    # --- API Key (admin-provided) ---
    api_key = _get_gemini_api_key()

    if not api_key:
        st.info(
            "Sage requires configuration. "
            "Set the `GEMINI_API_KEY` environment variable or add it to "
            "`.streamlit/secrets.toml`."
        )
        return

    # --- Context Panel ---
    context = _get_context_from_setup()
    _render_context_panel(context)

    # --- Initialize or refresh advisor ---
    advisor = st.session_state.get(ADVISOR_INSTANCE_KEY)
    if advisor is None:
        try:
            advisor = RBACAdvisor(api_key=api_key)
            advisor.set_context(**context)
            st.session_state[ADVISOR_INSTANCE_KEY] = advisor
        except AdvisorError as e:
            st.error(str(e))
            return

    # --- Chat History ---
    _render_chat_history()

    # --- Success banner after Apply ---
    if st.session_state.get("_advisor_show_success"):
        st.session_state["_advisor_show_success"] = False
        st.balloons()
        st.success(
            "Recommendation applied! "
            "Click the **📊 2. Design Matrix** tab above to see your permissions."
        )

    # --- Apply Button (if recommendation available) ---
    last_rec = st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY]
    if last_rec is not None:
        if st.button("📋 Apply to Matrix", type="primary", use_container_width=False):
            if _apply_recommendation(last_rec, context):
                st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = None
                st.session_state["_advisor_show_success"] = True
                st.session_state["_advisor_applied"] = True
                st.rerun()

    # --- Starter Prompts (only when chat is empty) ---
    selected_starter = None
    if not st.session_state[ADVISOR_MESSAGES_KEY]:
        selected_starter = _render_starter_prompts()

    # --- Chat Input ---
    chat_input = st.chat_input("Describe your teams and access needs...")
    user_input = selected_starter or chat_input

    if user_input:
        # Wrap with context preamble on first message
        message_to_send = _build_user_message(user_input, context)

        # Display the original user input (not the preamble)
        st.session_state[ADVISOR_MESSAGES_KEY].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        # Stream AI response
        with st.chat_message("assistant"):
            try:
                full_response = ""
                placeholder = st.empty()

                # Show thinking indicator until first chunk arrives
                placeholder.markdown("*Thinking...*")
                first_chunk = True

                for chunk in advisor.stream_recommendation(message_to_send):
                    full_response += chunk
                    if first_chunk:
                        first_chunk = False
                    placeholder.markdown(full_response + "▌")

                # Clear streaming placeholder and render with collapsible JSON
                placeholder.empty()
                _render_message_content(full_response)

                # Save to history
                st.session_state[ADVISOR_MESSAGES_KEY].append(
                    {"role": "assistant", "content": full_response}
                )

                # Parse structured recommendation if present
                recommendation = RBACAdvisor.parse_recommendation(full_response)
                if recommendation:
                    st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = recommendation
                    st.rerun()

            except AdvisorError as e:
                st.error(f"AI error: {e}")
