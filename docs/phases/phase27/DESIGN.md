# Phase 27: Design Document — RBAC Advisor (AI Chat Tab)

| Field | Value |
|-------|-------|
| **Phase** | 27 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Goal** | AI-powered chat tab that recommends RBAC configurations based on team descriptions and LD best practices |
| **Dependencies** | Phase 5 (UI module pattern) |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |
| **Master System Prompt** | [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) |
| Token Budget & Cost Analysis | [SYSTEM_PROMPT.md — Token Budget](./SYSTEM_PROMPT.md#token-budget-analysis) |
| LD Custom Roles Docs | https://docs.launchdarkly.com/home/account/custom-roles |
| Gemini API Reference | https://ai.google.dev/gemini-api/docs |

---

## High-Level Design (HLD)

### What Are We Building and Why?

SAs need tribal knowledge to design RBAC — which teams get which permissions, why production needs approvals, when to use deny rules. This knowledge exists in LD docs, PS best practices, and SA experience. We're putting an AI advisor in the app that:

1. Reads the customer's setup (teams, environments) from session state
2. Accepts natural language descriptions of access needs
3. Recommends a concrete permission matrix grounded in LD best practices
4. Explains the reasoning behind each recommendation
5. Lets the SA apply recommendations directly to the matrix tab

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RBAC ADVISOR FLOW                            │
│                                                                      │
│  ┌────────────┐     ┌──────────────────┐     ┌───────────────────┐  │
│  │ Setup Tab  │────►│  session_state    │────►│  Advisor Tab      │  │
│  │ (teams,    │     │  teams, envs,     │     │  (reads context)  │  │
│  │  envs,     │     │  project          │     │                   │  │
│  │  project)  │     └──────────────────┘     │  Chat UI          │  │
│  └────────────┘                               │    │              │  │
│                                               │    ▼              │  │
│                                               │  ┌────────────┐  │  │
│                                               │  │ Build      │  │  │
│                                               │  │ Prompt     │  │  │
│                                               │  └─────┬──────┘  │  │
│                                               │        │         │  │
│                                               │        ▼         │  │
│  ┌─────────────────────────────────────┐     │  ┌────────────┐  │  │
│  │  core/rbac_knowledge.py             │────►│  │ Gemini API │  │  │
│  │  - Team archetypes & best practices │     │  │ Call       │  │  │
│  │  - Permission explanations          │     │  └─────┬──────┘  │  │
│  │  - Environment patterns             │     │        │         │  │
│  │  - Common anti-patterns             │     │        ▼         │  │
│  └─────────────────────────────────────┘     │  ┌────────────┐  │  │
│                                               │  │ Parse      │  │  │
│                                               │  │ Response   │  │  │
│                                               │  └─────┬──────┘  │  │
│                                               │        │         │  │
│                                               │        ▼         │  │
│                                               │  Display in chat │  │
│                                               │  + "Apply" btn   │  │
│                                               └───────┬──────────┘  │
│                                                       │              │
│                                                       ▼              │
│                                               ┌───────────────────┐  │
│                                               │  session_state    │  │
│                                               │  project_matrix   │  │
│                                               │  env_matrix       │  │
│                                               └───────────────────┘  │
│                                                       │              │
│                                                       ▼              │
│                                               ┌───────────────────┐  │
│                                               │  Matrix Tab       │  │
│                                               │  (pre-filled)     │  │
│                                               └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Features Table

| Feature | Description |
|---------|-------------|
| Context auto-load | Reads teams, envs, project from Setup tab's session_state |
| Conversational chat | Multi-turn chat with st.chat_message / st.chat_input |
| RBAC knowledge base | Embedded best practices (team archetypes, environment patterns, LD actions) |
| Structured recommendations | AI returns both markdown (display) and JSON (apply) |
| Apply to matrix | One-click button writes recommendations to project_matrix and env_matrix |
| Streaming responses | Token-by-token streaming for responsive UX |
| Chat history | Full conversation preserved in session_state |

### Data Flow

```
SA types: "Developers need to create flags in test, view only in prod"
        │
        ▼
ui/advisor_tab.py
  1. Read context from session_state (teams, envs, project)
  2. Append user message to chat history
        │
        ▼
services/ai_advisor.py — RBACAdvisor.get_recommendation()
  1. Build system prompt with:
     - RBAC knowledge base (core/rbac_knowledge.py)
     - Customer context (teams, envs, project)
     - Available permissions list (from core/ld_actions.py)
  2. Append conversation history
  3. Call Gemini API (streaming)
        │
        ▼
Gemini returns structured response:
  {
    "explanation": "### Developer\n- Project: Create Flags ✅...",
    "matrix": {
      "project": {
        "Developer": {"Create Flags": true, "Update Flags": true, ...},
        "QA": {"View Project": true, ...}
      },
      "environment": {
        "Developer": {
          "test": {"Update Targeting": true, "Manage Segments": true},
          "production": {}
        },
        "QA": {
          "test": {"Update Targeting": true},
          "production": {"Review Changes": true}
        }
      }
    }
  }
        │
        ▼
ui/advisor_tab.py
  1. Display explanation in chat (streamed)
  2. Store structured matrix in session_state
  3. Show "Apply to Matrix" button
        │
        ▼
SA clicks "Apply to Matrix"
  1. Convert JSON matrix → project_matrix DataFrame
  2. Convert JSON matrix → env_matrix DataFrame
  3. Write to session_state
  4. SA switches to Matrix tab — pre-filled
```

---

## Detailed Low-Level Design (DLD)

### 1. `core/rbac_knowledge.py` — Embedded Knowledge Base

This is the **system prompt context** — not a database, just a carefully curated string of RBAC best practices that gets injected into every Gemini call.

```python
"""
RBAC Knowledge Base for the AI Advisor.

This module contains curated LaunchDarkly RBAC best practices that are
injected into the AI's system prompt. The AI uses this knowledge to
ground its recommendations in real LD patterns.
"""

TEAM_ARCHETYPES = """
## Common Team Archetypes and Recommended Permissions

### Developer / Engineering
- Project: Create Flags, Update Flags, View Project, Manage Metrics
- Non-critical envs (dev/test/staging): Update Targeting, Manage Segments, Apply Changes
- Critical envs (production): NO direct targeting. Use Review Changes if needed.
- Why: Developers iterate freely in lower environments. Production changes go through approvals.

### QA / Quality Assurance
- Project: View Project (read-only at project level)
- Non-critical envs: Update Targeting, Manage Segments (test flag states)
- Critical envs: Review Changes (can review but not apply)
- Why: QA validates flag behavior in test environments and reviews prod changes.

### Product Owner / Product Manager
- Project: View Project, Update Flags (metadata only — descriptions, tags)
- Non-critical envs: View only (or Update Targeting for feature rollouts)
- Critical envs: Review Changes (stakeholder approval)
- Why: POs own flag lifecycle at the metadata level, not targeting rules.

### SRE / Platform / DevOps
- Project: View Project, Archive Flags, Manage Metrics
- Non-critical envs: Update Targeting, Apply Changes, View SDK Key
- Critical envs: Update Targeting, Apply Changes, Review Changes, View SDK Key
- Why: SRE owns production stability. They need full env access for incident response.

### Release Manager
- Project: View Project, Archive Flags, Manage Release Pipelines
- Non-critical envs: Apply Changes
- Critical envs: Apply Changes, Review Changes
- Why: Release managers control the deployment gate, not flag design.

### Read-Only / Stakeholder / Executive
- Project: View Project
- All envs: No environment permissions
- Why: View-only access for dashboards and reporting.
"""

ENVIRONMENT_PATTERNS = """
## Environment Classification Best Practices

### Critical Environments (require approvals)
- Production, Staging (pre-prod)
- Characteristics: Real user traffic, compliance requirements, SLA impact
- Pattern: Require Review Changes + Apply Changes (separation of duties)
- Anti-pattern: Giving developers direct Update Targeting in production

### Non-Critical Environments (direct access)
- Development, Test, QA, Sandbox
- Characteristics: Internal traffic only, safe to experiment
- Pattern: Broader access — most teams get Update Targeting + Manage Segments
- Anti-pattern: Restricting dev environments too tightly (slows iteration)

### Separation of Duties (Critical Environments)
- The person who REQUESTS a change should NOT be the same person who APPROVES it
- Update Targeting: Creates the change (but held for approval in critical envs)
- Review Changes: Can approve/reject the change
- Apply Changes: Can apply an approved change
- Best practice: Developers get Update Targeting, SRE/Lead gets Review + Apply
"""

PERMISSION_REFERENCE = """
## Permission Quick Reference

### Project-Scoped (apply to all environments)
- Create Flags: Create new feature flags
- Update Flags: Edit flag name, description, tags, variations
- Archive Flags: Archive/unarchive flags (soft delete)
- View Project: View project details (EVERY team needs this)
- Manage Metrics: Create/edit metrics for experiments
- Manage Release Pipelines: Manage release pipeline configurations
- Update Client Side Availability: Control client-side flag visibility

### Environment-Scoped (per environment)
- Update Targeting: Modify flag targeting rules, toggle on/off
- Review Changes: Approve/reject approval requests
- Apply Changes: Apply approved changes
- Manage Segments: Create/edit user segments
- View SDK Key: View environment SDK keys
- Manage Experiments: Start/stop experiments
- Manage Triggers: Configure flag triggers

### Key Rules
1. EVERY team needs "View Project" — without it they can't see anything
2. Update Targeting in critical envs creates an approval request (not a direct change)
3. Create Flags is project-scoped — you can't restrict flag creation to specific environments
4. Archive Flags is project-scoped and does NOT support approvals
"""

ANTI_PATTERNS = """
## Common Anti-Patterns to Avoid

1. **Giving everyone Admin** — Defeats the purpose of RBAC. Always use least privilege.
2. **No View Project** — Team can't see anything. Every team needs View Project.
3. **Developer with Apply Changes in prod** — Developers should create changes, not approve their own.
4. **QA with Create Flags** — QA validates flags, they don't create them. Flag creation is a developer task.
5. **No separation of duties in prod** — Same person can target + review + apply = no approval gate.
6. **Restricting dev environments too tightly** — Slows down iteration. Dev/test should be permissive.
7. **Forgetting Manage Segments** — Teams that need Update Targeting usually also need Manage Segments.
8. **Giving Archive Flags broadly** — Archiving affects ALL environments. Only leads/SRE should have this.
"""

def build_system_prompt(
    teams: list[str],
    environments: list[dict],
    project_key: str,
    available_project_permissions: list[str],
    available_env_permissions: list[str],
) -> str:
    """
    Build the complete system prompt for the AI advisor.

    Combines:
    - Role definition (you are an RBAC advisor)
    - RBAC knowledge base (archetypes, patterns, anti-patterns)
    - Customer context (their specific teams, envs, project)
    - Available permissions (from core/ld_actions.py)
    - Output format instructions (markdown + JSON)
    """
    env_descriptions = []
    for env in environments:
        critical = "critical" if env.get("critical", False) else "non-critical"
        env_descriptions.append(f"  - {env['key']} ({critical})")
    env_text = "\n".join(env_descriptions) if env_descriptions else "  - (none configured yet)"

    team_text = "\n".join(f"  - {t}" for t in teams) if teams else "  - (none configured yet)"

    return f"""You are an expert LaunchDarkly RBAC Advisor built into the RBAC Builder tool.
Your job is to recommend custom role configurations based on the customer's team structure
and LaunchDarkly best practices.

## Customer Context
- Project: {project_key or "(not set yet)"}
- Teams:
{team_text}
- Environments:
{env_text}

## Available Permissions
Project-scoped: {", ".join(available_project_permissions)}
Environment-scoped: {", ".join(available_env_permissions)}

{TEAM_ARCHETYPES}

{ENVIRONMENT_PATTERNS}

{PERMISSION_REFERENCE}

{ANTI_PATTERNS}

## Response Guidelines

1. Always recommend specific permissions from the available lists above.
2. Explain WHY each team gets (or doesn't get) each permission.
3. Flag any anti-patterns you see in the user's description.
4. Default to least privilege — only add permissions that are clearly needed.
5. Always include "View Project" for every team.
6. For critical environments, recommend separation of duties (different people target vs review vs apply).
7. When the user asks for a recommendation, include a structured JSON block at the end.

## Structured Output Format

When providing a recommendation, end your response with a JSON block wrapped in
```json``` fences. This JSON will be parsed by the app to populate the matrix.

The JSON format:
```json
{{
  "recommendation": {{
    "project": {{
      "TeamName": {{
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true
      }}
    }},
    "environment": {{
      "TeamName": {{
        "env-key": {{
          "Update Targeting": true,
          "Manage Segments": true
        }}
      }}
    }}
  }}
}}
```

Only include permissions that are TRUE. Omit permissions that should be false.
Use the exact permission names from the available permissions list above.
Use the exact team names and environment keys from the customer context above.
"""
```

### 2. `services/ai_advisor.py` — Gemini Integration

```python
"""
AI Advisor Service — Gemini-powered RBAC recommendations.
"""

import json
import re
from typing import Generator, Optional

import google.generativeai as genai

from core.rbac_knowledge import build_system_prompt
from core.ld_actions import (
    get_all_project_permissions,
    get_all_env_permissions,
)


class AdvisorError(Exception):
    """Raised when the AI advisor encounters an error."""
    pass


class RBACAdvisor:
    """
    Manages conversations with Gemini for RBAC recommendations.

    Usage:
        advisor = RBACAdvisor(api_key="gemini-key-here")
        advisor.set_context(teams, environments, project_key)

        # Streaming response
        for chunk in advisor.stream_recommendation("Developers need..."):
            print(chunk, end="")

        # Parse structured output
        matrix = advisor.parse_recommendation(full_response)
    """

    # Gemini model to use
    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self, api_key: str):
        if not api_key or not api_key.strip():
            raise AdvisorError("Gemini API key is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.MODEL_NAME)
        self.chat: Optional[genai.ChatSession] = None
        self.system_prompt: str = ""

    def set_context(
        self,
        teams: list[str],
        environments: list[dict],
        project_key: str,
    ) -> None:
        """
        Set customer context and initialize a new chat session.
        Call this when the user's setup changes or on first load.

        Enables Google Search grounding so the model can search
        docs.launchdarkly.com for edge-case questions not covered
        in the embedded knowledge base.
        """
        self.system_prompt = build_system_prompt(
            teams=teams,
            environments=environments,
            project_key=project_key,
            available_project_permissions=get_all_project_permissions(),
            available_env_permissions=get_all_env_permissions(),
        )

        # Google Search grounding — model searches LD docs when needed
        from google.genai import types
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        # Start a new chat with system instruction + search tool
        self.model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.system_prompt,
            tools=[grounding_tool],
        )

        # Disable thinking tokens to keep costs low
        self.generation_config = genai.GenerationConfig(
            thinking_config=genai.ThinkingConfig(thinking_budget=0)
        )

        self.chat = self.model.start_chat(history=[])

    def stream_recommendation(
        self, user_message: str
    ) -> Generator[str, None, None]:
        """
        Send a message and yield response chunks as they arrive.

        Yields:
            str: Text chunks from the Gemini streaming response
        """
        if self.chat is None:
            raise AdvisorError(
                "Context not set. Call set_context() before sending messages."
            )

        try:
            response = self.chat.send_message(
                user_message,
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            raise AdvisorError(f"Gemini API error: {e}") from e

    def get_recommendation(self, user_message: str) -> str:
        """
        Send a message and return the complete response (non-streaming).
        Useful for testing.
        """
        chunks = list(self.stream_recommendation(user_message))
        return "".join(chunks)

    @staticmethod
    def parse_recommendation(response_text: str) -> Optional[dict]:
        """
        Extract the structured JSON recommendation from the AI response.

        The AI is instructed to include a ```json block at the end of
        its response. This method finds and parses it.

        Returns:
            dict with "project" and "environment" keys, or None if no
            JSON block found.
        """
        # Find the last ```json ... ``` block in the response
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, response_text, re.DOTALL)

        if not matches:
            return None

        try:
            parsed = json.loads(matches[-1])
            # Handle both direct matrix and wrapped {"recommendation": ...}
            if "recommendation" in parsed:
                return parsed["recommendation"]
            return parsed
        except json.JSONDecodeError:
            return None
```

### 3. `ui/advisor_tab.py` — Chat UI

```python
"""
Advisor Tab — AI-powered RBAC recommendations.
"""

import streamlit as st
import pandas as pd

from services.ai_advisor import RBACAdvisor, AdvisorError


# Session state keys for this tab
ADVISOR_MESSAGES_KEY = "advisor_messages"
ADVISOR_INSTANCE_KEY = "advisor_instance"
ADVISOR_LAST_RECOMMENDATION_KEY = "advisor_last_recommendation"


def _get_gemini_api_key() -> str:
    """
    Get the Gemini API key from Streamlit secrets or environment variable.
    Admin-provided — SAs do NOT enter their own key.
    """
    # Streamlit Cloud: secrets management (.streamlit/secrets.toml)
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]

    # Localhost: environment variable
    import os
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

    teams = teams_df["Name"].tolist() if "Name" in teams_df.columns else []

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


def _render_context_panel(context: dict) -> None:
    """Show what the AI knows about the customer's setup."""
    with st.expander("📋 Context from Setup", expanded=False):
        if context["project_key"]:
            st.markdown(f"**Project:** `{context['project_key']}`")
        else:
            st.warning("No project configured in Setup tab")

        if context["teams"]:
            st.markdown("**Teams:** " + ", ".join(context["teams"]))
        else:
            st.warning("No teams configured in Setup tab")

        if context["environments"]:
            for env in context["environments"]:
                badge = "🔴 critical" if env["critical"] else "🟢 non-critical"
                st.markdown(f"- `{env['key']}` ({badge})")
        else:
            st.warning("No environments configured in Setup tab")

        st.caption("Go to the Setup tab to configure these, then come back here.")


def _render_chat_history() -> None:
    """Render all previous messages in the conversation."""
    for msg in st.session_state[ADVISOR_MESSAGES_KEY]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _apply_recommendation_to_matrix(recommendation: dict) -> bool:
    """
    Write the AI's recommendation to project_matrix and env_matrix
    in session_state.

    Returns True if applied successfully.
    """
    try:
        teams_df = st.session_state.get("teams", pd.DataFrame())
        env_df = st.session_state.get("env_groups", pd.DataFrame())

        if teams_df.empty or env_df.empty:
            st.error("Setup tab must have teams and environments configured first.")
            return False

        project_rec = recommendation.get("project", {})
        env_rec = recommendation.get("environment", {})

        # Build project matrix from recommendation
        team_names = teams_df["Name"].tolist()
        project_perms = list(
            set().union(*(perms.keys() for perms in project_rec.values()))
        ) if project_rec else []

        if project_perms:
            project_data = {"Team": team_names}
            for perm in sorted(project_perms):
                project_data[perm] = [
                    project_rec.get(team, {}).get(perm, False)
                    for team in team_names
                ]
            st.session_state.project_matrix = pd.DataFrame(project_data)

        # Build env matrix from recommendation
        env_keys = env_df["Key"].tolist()
        env_perms = set()
        for team_envs in env_rec.values():
            for env_perms_dict in team_envs.values():
                env_perms.update(env_perms_dict.keys())
        env_perms = sorted(env_perms)

        if env_perms:
            env_rows = []
            for team in team_names:
                for env_key in env_keys:
                    row = {"Team": team, "Environment": env_key}
                    for perm in env_perms:
                        row[perm] = (
                            env_rec
                            .get(team, {})
                            .get(env_key, {})
                            .get(perm, False)
                        )
                    env_rows.append(row)
            st.session_state.env_matrix = pd.DataFrame(env_rows)

        return True

    except Exception as e:
        st.error(f"Failed to apply recommendation: {e}")
        return False


def render_advisor_tab(customer_name: str = "") -> None:
    """
    Main entry point for Tab 5: RBAC Advisor.
    Called from app.py.
    """
    _initialize_session_state()

    st.header("🤖 RBAC Advisor")
    st.markdown(
        "Describe your teams and access needs. "
        "The AI will recommend a permission matrix based on LaunchDarkly best practices."
    )

    # --- API Key (admin-provided, not SA-entered) ---
    api_key = _get_gemini_api_key()

    if not api_key:
        st.info(
            "RBAC Advisor requires configuration. "
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

    # --- Apply Button (if recommendation available) ---
    last_rec = st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY]
    if last_rec is not None:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📋 Apply to Matrix", type="primary"):
                if _apply_recommendation_to_matrix(last_rec):
                    st.success("Recommendation applied! Switch to the Matrix tab to review.")
                    st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = None

    # --- Chat Input ---
    if user_input := st.chat_input("Describe your teams and access needs..."):
        # Display user message
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

                for chunk in advisor.stream_recommendation(user_input):
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)

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
```

### 4. `app.py` Changes

```python
# Add import
from ui import render_advisor_tab

# Update tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 1. Setup",
    "📊 2. Design Matrix",
    "🚀 3. Deploy",
    "📚 4. Reference Guide",
    "🤖 5. RBAC Advisor",
])

# Add tab5 block
with tab5:
    render_advisor_tab(customer_name=customer_name)
```

### 5. `requirements.txt` Addition

```
google-generativeai>=0.8.0
```

---

## Pseudo Logic

### 1. Building the System Prompt

```
FUNCTION build_system_prompt(teams, environments, project_key, project_perms, env_perms):

  role_definition = "You are an expert LaunchDarkly RBAC Advisor..."

  customer_context = FORMAT teams, envs, project into readable text

  knowledge = CONCATENATE:
    TEAM_ARCHETYPES          (Developer, QA, PO, SRE patterns)
    ENVIRONMENT_PATTERNS     (critical vs non-critical best practices)
    PERMISSION_REFERENCE     (what each permission does)
    ANTI_PATTERNS           (common mistakes to flag)

  output_instructions = "Include a ```json block with the recommendation..."

  RETURN role_definition + customer_context + knowledge + output_instructions
```

### 2. Streaming a Recommendation

```
FUNCTION stream_recommendation(user_message):

  IF chat session not initialized:
    RAISE AdvisorError("Call set_context() first")

  TRY:
    response = gemini.chat.send_message(user_message, stream=True)
    FOR each chunk in response:
      IF chunk has text:
        YIELD chunk.text
  CATCH any exception:
    RAISE AdvisorError with details
```

### 3. Parsing the Structured Response

```
FUNCTION parse_recommendation(response_text):

  # Find the last ```json ... ``` block
  matches = regex.findall("```json (.*?) ```", response_text)

  IF no matches:
    RETURN None

  TRY:
    parsed = json.loads(last match)
    IF "recommendation" key exists:
      RETURN parsed["recommendation"]
    RETURN parsed
  CATCH JSONDecodeError:
    RETURN None
```

### 4. Applying Recommendation to Matrix

```
FUNCTION apply_recommendation_to_matrix(recommendation):

  teams = session_state.teams     (from Setup tab)
  envs  = session_state.env_groups (from Setup tab)

  IF teams or envs empty:
    SHOW error "Configure Setup first"
    RETURN False

  # Build project matrix DataFrame
  project_rec = recommendation["project"]
  FOR each team in teams:
    FOR each permission:
      value = project_rec.get(team, {}).get(permission, False)

  session_state.project_matrix = DataFrame(project_data)

  # Build env matrix DataFrame
  env_rec = recommendation["environment"]
  FOR each team in teams:
    FOR each environment in envs:
      FOR each permission:
        value = env_rec.get(team, {}).get(env_key, {}).get(permission, False)

  session_state.env_matrix = DataFrame(env_rows)

  RETURN True
```

### 5. Chat UI Flow

```
FUNCTION render_advisor_tab():

  initialize_session_state()

  api_key = text_input(type=password)
  IF no api_key: SHOW info message, RETURN

  context = read teams/envs/project from session_state
  render_context_panel(context)

  IF advisor not in session_state:
    advisor = RBACAdvisor(api_key)
    advisor.set_context(**context)
    session_state.advisor_instance = advisor

  render_chat_history()

  IF last_recommendation exists:
    SHOW "Apply to Matrix" button
    IF clicked: apply_recommendation_to_matrix(rec)

  IF user_input from chat_input:
    APPEND to history
    DISPLAY user message

    WITH assistant chat bubble:
      full_response = ""
      FOR each chunk in advisor.stream_recommendation(user_input):
        full_response += chunk
        UPDATE placeholder with full_response + cursor

      DISPLAY final response
      APPEND to history

      recommendation = parse_recommendation(full_response)
      IF recommendation exists:
        session_state.last_recommendation = recommendation
        RERUN (to show Apply button)
```

---

## Test Cases

**Test file:** `tests/test_ai_advisor.py`

> **Note:** Tests mock the Gemini API — we test prompt building, response parsing,
> matrix application, and error handling without making real API calls.

### Group 1: Knowledge Base & Prompt Building

#### TC-AI-01: System prompt includes customer context
```
GIVEN: teams=["Developer", "QA"], envs=[{key: "test", critical: false}], project="voya-web"
WHEN:  build_system_prompt() is called
THEN:  result contains "voya-web"
       result contains "Developer"
       result contains "QA"
       result contains "test"
       result contains "non-critical"
```

#### TC-AI-02: System prompt includes all knowledge sections
```
GIVEN: any valid inputs
WHEN:  build_system_prompt() is called
THEN:  result contains "Team Archetypes"
       result contains "Environment Classification"
       result contains "Permission Quick Reference"
       result contains "Anti-Patterns"
```

#### TC-AI-03: System prompt includes available permissions
```
GIVEN: project_perms=["Create Flags", "Update Flags"], env_perms=["Update Targeting"]
WHEN:  build_system_prompt() is called
THEN:  result contains "Create Flags"
       result contains "Update Targeting"
```

#### TC-AI-04: System prompt handles empty context gracefully
```
GIVEN: teams=[], envs=[], project=""
WHEN:  build_system_prompt() is called
THEN:  result contains "(not set yet)" or "(none configured yet)"
       No exceptions raised
```

### Group 2: Response Parsing

#### TC-AI-05: Parse valid JSON recommendation
```
GIVEN: response containing:
  "Here is my recommendation:\n```json\n{\"recommendation\": {\"project\": {\"Dev\": {\"Create Flags\": true}}}}\n```"
WHEN:  parse_recommendation() is called
THEN:  returns {"project": {"Dev": {"Create Flags": true}}}
```

#### TC-AI-06: Parse response with no JSON block
```
GIVEN: response = "I recommend giving developers access to create flags."
WHEN:  parse_recommendation() is called
THEN:  returns None
```

#### TC-AI-07: Parse response with invalid JSON
```
GIVEN: response containing:
  "```json\n{invalid json here}\n```"
WHEN:  parse_recommendation() is called
THEN:  returns None (no exception raised)
```

#### TC-AI-08: Parse response with multiple JSON blocks (uses last)
```
GIVEN: response with two ```json blocks
WHEN:  parse_recommendation() is called
THEN:  returns the content of the LAST block
```

### Group 3: Matrix Application

#### TC-AI-09: Apply recommendation creates correct project_matrix
```
GIVEN: teams=["Developer", "QA"], recommendation.project = {
  "Developer": {"Create Flags": true, "View Project": true},
  "QA": {"View Project": true}
}
WHEN:  apply_recommendation_to_matrix() is called
THEN:  session_state.project_matrix is a DataFrame with:
       rows: Developer, QA
       Developer.Create Flags = True
       Developer.View Project = True
       QA.Create Flags = False
       QA.View Project = True
```

#### TC-AI-10: Apply recommendation creates correct env_matrix
```
GIVEN: teams=["Developer"], envs=["test", "prod"], recommendation.environment = {
  "Developer": {
    "test": {"Update Targeting": true},
    "prod": {}
  }
}
WHEN:  apply_recommendation_to_matrix() is called
THEN:  session_state.env_matrix is a DataFrame with:
       Developer/test/Update Targeting = True
       Developer/prod/Update Targeting = False
```

### Group 4: Error Handling

#### TC-AI-11: Empty API key raises AdvisorError
```
GIVEN: api_key = ""
WHEN:  RBACAdvisor("") is created
THEN:  raises AdvisorError("Gemini API key is required")
```

#### TC-AI-12: stream_recommendation before set_context raises error
```
GIVEN: advisor created but set_context() not called
WHEN:  stream_recommendation("hello") is called
THEN:  raises AdvisorError("Context not set...")
```

---

## Implementation Plan

| Step | Task | File |
|------|------|------|
| 1 | Create RBAC knowledge base constants | `core/rbac_knowledge.py` |
| 2 | Implement `build_system_prompt()` | `core/rbac_knowledge.py` |
| 3 | Create `RBACAdvisor` class with `__init__` and `set_context` | `services/ai_advisor.py` |
| 4 | Implement `stream_recommendation()` | `services/ai_advisor.py` |
| 5 | Implement `get_recommendation()` (non-streaming) | `services/ai_advisor.py` |
| 6 | Implement `parse_recommendation()` | `services/ai_advisor.py` |
| 7 | Export from `services/__init__.py` | `services/__init__.py` |
| 8 | Create `_initialize_session_state()` | `ui/advisor_tab.py` |
| 9 | Create `_get_context_from_setup()` | `ui/advisor_tab.py` |
| 10 | Create `_render_context_panel()` | `ui/advisor_tab.py` |
| 11 | Create `_render_chat_history()` | `ui/advisor_tab.py` |
| 12 | Create `_apply_recommendation_to_matrix()` | `ui/advisor_tab.py` |
| 13 | Create `render_advisor_tab()` | `ui/advisor_tab.py` |
| 14 | Export from `ui/__init__.py` | `ui/__init__.py` |
| 15 | Add Tab 5 to `app.py` | `app.py` |
| 16 | Add `google-generativeai` to `requirements.txt` | `requirements.txt` |
| 17 | Write all 12 tests | `tests/test_ai_advisor.py` |
| 18 | Run full test suite | `pytest tests/ -v` |

### Python Concepts in This Phase

| Concept | Used for |
|---------|---------|
| Generator functions (`yield`) | Streaming API responses chunk by chunk |
| `re.findall()` with `re.DOTALL` | Extracting JSON from markdown-formatted response |
| `json.loads()` | Parsing structured AI output |
| `st.chat_message` / `st.chat_input` | Streamlit's native chat UI components |
| `st.empty()` + `.markdown()` | Live-updating placeholder for streaming text |
| System prompts / prompt engineering | Instructing the AI to produce structured + readable output |
| `type="password"` on `st.text_input` | Hiding API key input |

---

## Navigation

- [← README](./README.md)
- [Python Concepts →](./PYTHON_CONCEPTS.md)
