# Phase 27: Design Document — RBAC Advisor (AI Chat Tab)

| Field | Value |
|-------|-------|
| **Phase** | 27 |
| **Status** | ✅ Implemented |
| **Goal** | AI-powered chat tab that recommends RBAC configurations based on team descriptions and LD best practices |
| **Dependencies** | Phase 5 (UI module pattern) |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |
| **Master System Prompt** | [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) |
| **Few-Shot Examples** | [FEW_SHOT_EXAMPLES.md](./FEW_SHOT_EXAMPLES.md) |
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

from google import genai
from google.genai import types

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

    Uses the new google.genai SDK (not the deprecated google.generativeai).
    Client pattern: genai.Client(api_key=...) instead of genai.configure().
    Chat pattern: client.chats.create() instead of model.start_chat().
    Streaming: chat.send_message_stream() instead of chat.send_message(stream=True).

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

        # New SDK: client pattern instead of genai.configure()
        self.client = genai.Client(
            api_key=api_key,
            http_options={"timeout": 120_000},  # 120s timeout for large system prompts
        )
        self.chat = None
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

        # New SDK: client.chats.create() instead of model.start_chat()
        # Google Search grounding — model searches LD docs when needed
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        self.chat = self.client.chats.create(
            model=self.MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                tools=[grounding_tool],
            ),
        )

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
            # New SDK: send_message_stream() instead of send_message(stream=True)
            response = self.chat.send_message_stream(user_message)
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
ADVISOR_CONTEXT_SENT_KEY = "_advisor_context_sent"


# =============================================================================
# LESSON: Starter Prompts — Pre-Built Use Cases
# =============================================================================
# SAs pick a scenario and optionally edit before sending.
# These are based on real engagement patterns from sa-demo, Epassi,
# Voya, and the S2 template.

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
        "label": "🏢 Enterprise — Dev, QA, PO, SRE with Observability",
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


def _get_gemini_api_key() -> str:
    """
    Get the Gemini API key from Streamlit secrets or environment variable.
    Admin-provided — SAs do NOT enter their own key.

    GOTCHA: "GEMINI_API_KEY" in st.secrets raises StreamlitSecretNotFoundError
    when no secrets.toml file exists. Must wrap in try/except.
    """
    # Streamlit Cloud: secrets management (.streamlit/secrets.toml)
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass  # No secrets.toml — fall through to env var

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


def _build_user_message(raw_input: str, context: dict) -> str:
    """
    Wrap the SA's first message with current context as a preamble.

    LESSON: Context Preamble vs System Prompt
    ==========================================
    System prompt: guardrails, knowledge, output format (static, hidden)
    Context preamble: customer-specific data (dynamic, per-session)

    We inject context on the FIRST message only. After that, the chat
    history carries the context forward naturally.
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


def _render_starter_prompts() -> str | None:
    """
    Render clickable starter prompt buttons when chat is empty.
    Returns the selected prompt text, or None if nothing clicked.

    LESSON: Streamlit Button Columns
    =================================
    We use st.columns() to lay out buttons in a grid.
    Each button returns True when clicked (for that rerun only).
    We store the selected prompt in session_state so the chat
    input can pick it up.
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


def _render_chat_history() -> None:
    """Render all previous messages in the conversation."""
    for msg in st.session_state[ADVISOR_MESSAGES_KEY]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _apply_recommendation(recommendation: dict, context: dict) -> bool:
    """
    Write the AI's recommendation to BOTH Setup and Matrix in session_state.

    LESSON: Two-Phase Apply
    ========================
    Phase A — Populate Setup (Step 1):
      If teams/envs/project aren't configured yet, create them from the
      recommendation's team names and environment keys. This lets SAs start
      on the Advisor tab without configuring Setup first.

    Phase B — Populate Matrix (Step 2):
      Write project_matrix and env_matrix DataFrames from the recommendation.

    Returns True if applied successfully.
    """
    try:
        project_rec = recommendation.get("project", {})
        env_rec = recommendation.get("environment", {})

        # =============================================================
        # Phase A: Populate Setup tab if not already configured
        # =============================================================

        # Teams — derive from recommendation keys
        teams_df = st.session_state.get("teams", pd.DataFrame())
        rec_team_names = list(project_rec.keys())

        if teams_df.empty or set(teams_df["Name"].tolist()) != set(rec_team_names):
            # Build teams DataFrame from recommendation team names
            st.session_state.teams = pd.DataFrame({
                "Key": [name.lower().replace(" ", "-") for name in rec_team_names],
                "Name": rec_team_names,
                "Description": ["" for _ in rec_team_names],
            })
            teams_df = st.session_state.teams

        # Environments — derive from recommendation env keys
        env_df = st.session_state.get("env_groups", pd.DataFrame())
        rec_env_keys = set()
        for team_envs in env_rec.values():
            rec_env_keys.update(team_envs.keys())
        rec_env_keys = sorted(rec_env_keys)

        if env_df.empty or set(env_df["Key"].tolist()) != set(rec_env_keys):
            # Build env_groups DataFrame from recommendation env keys
            # Use context hints for critical flag, default production=critical
            env_rows = []
            for env_key in rec_env_keys:
                # Infer critical from context or naming convention
                is_critical = any([
                    env_key.lower() in ("production", "prod"),
                    any(
                        e.get("key") == env_key and e.get("critical", False)
                        for e in context.get("environments", [])
                    ),
                ])
                env_rows.append({
                    "Key": env_key,
                    "Requires Approvals": is_critical,
                    "Critical": is_critical,
                    "Notes": "",
                })
            st.session_state.env_groups = pd.DataFrame(env_rows)
            env_df = st.session_state.env_groups

        # Project key — use context if available
        if not st.session_state.get("project") and context.get("project_key"):
            st.session_state.project = context["project_key"]

        # Generation mode — default to role_attributes
        if "generation_mode" not in st.session_state:
            st.session_state.generation_mode = "role_attributes"

        # =============================================================
        # Phase B: Populate Matrix tab (same as before)
        # =============================================================

        team_names = teams_df["Name"].tolist()

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

    st.header("🤖 Role Designer AI")
    st.markdown(
        "Describe your teams and access needs — "
        "get an instant RBAC blueprint powered by AI."
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
    # Success banner persistence — survives st.rerun() via session_state flag
    if st.session_state.get("_advisor_apply_success"):
        st.success(
            "Recommendation applied! "
            "Check the **Setup** tab (teams & environments) "
            "and **Design Matrix** tab (permissions)."
        )
        st.session_state["_advisor_apply_success"] = False

    last_rec = st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY]
    if last_rec is not None:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📋 Apply to Matrix", type="primary"):
                if _apply_recommendation(last_rec, context):
                    # Set _advisor_applied flag — Matrix tab checks this
                    # to skip stale env_groups sync and trust Advisor's data
                    st.session_state["_advisor_applied"] = True
                    st.session_state["_advisor_apply_success"] = True
                    st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = None
                    st.rerun()  # success message shown on next rerun

    # --- Starter Prompts (only shown when chat is empty) ---
    selected_starter = None
    if not st.session_state[ADVISOR_MESSAGES_KEY]:
        selected_starter = _render_starter_prompts()

    # --- Chat Input ---
    # Use starter prompt if one was clicked, otherwise use chat input
    user_input = selected_starter or st.chat_input(
        "Describe your teams and access needs..."
    )

    if user_input:
        # Wrap with context preamble on first message
        message_to_send = _build_user_message(user_input, context)

        # Display the original user input (not the preamble)
        st.session_state[ADVISOR_MESSAGES_KEY].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        # Stream AI response (send the preamble-wrapped version)
        with st.chat_message("assistant"):
            try:
                full_response = ""
                placeholder = st.empty()

                # Thinking indicator — show while waiting for first chunk
                placeholder.markdown("*Thinking...*")

                for chunk in advisor.stream_recommendation(message_to_send):
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")

                # Final render — collapsible JSON blocks
                # If response contains ```json blocks, render explanation as
                # markdown and JSON inside an expander ("View JSON Recommendation")
                placeholder.markdown(full_response)

                # Save to history
                st.session_state[ADVISOR_MESSAGES_KEY].append(
                    {"role": "assistant", "content": full_response}
                )

                # Parse structured recommendation if present
                recommendation = RBACAdvisor.parse_recommendation(full_response)
                if recommendation:
                    st.session_state[ADVISOR_LAST_RECOMMENDATION_KEY] = recommendation
                    # Set _advisor_applied flag — Matrix tab checks this
                    # to skip stale sync and trust Advisor's data
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
    "🤖 5. Role Designer AI",
])

# Add tab5 block
with tab5:
    render_advisor_tab(customer_name=customer_name)
```

### 5. `requirements.txt` Addition

```
google-genai>=1.0.0
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

### 4. Applying Recommendation — Setup + Matrix

```
FUNCTION apply_recommendation(recommendation, context):

  project_rec = recommendation["project"]
  env_rec     = recommendation["environment"]

  # ── PHASE A: Populate Setup tab (Step 1) ──────────────────────

  # Teams — derive from recommendation keys if not configured
  rec_team_names = keys of project_rec   # e.g. ["Developer", "QA", "SRE"]

  IF session_state.teams is empty OR team names don't match:
    session_state.teams = DataFrame({
      Key:         slugify each team name  (e.g. "developer", "qa", "sre")
      Name:        rec_team_names
      Description: empty strings (SA can fill in later)
    })

  # Environments — derive from recommendation env keys if not configured
  rec_env_keys = collect all env keys from env_rec  # e.g. ["test", "production"]

  IF session_state.env_groups is empty OR env keys don't match:
    FOR each env_key:
      is_critical = env_key contains "prod" OR context says it's critical
    session_state.env_groups = DataFrame({
      Key:                rec_env_keys
      Requires Approvals: is_critical for each
      Critical:           is_critical for each
      Notes:              empty strings
    })

  # Project key — use context if available
  IF session_state.project is empty AND context has project_key:
    session_state.project = context["project_key"]

  # Generation mode — default to role_attributes
  IF generation_mode not set:
    session_state.generation_mode = "role_attributes"

  # ── PHASE B: Populate Matrix tab (Step 2) ─────────────────────

  # Build project matrix DataFrame
  team_names = session_state.teams["Name"]
  FOR each team in team_names:
    FOR each permission in project_rec:
      value = project_rec.get(team, {}).get(permission, False)

  session_state.project_matrix = DataFrame(project_data)

  # Build env matrix DataFrame
  env_keys = session_state.env_groups["Key"]
  FOR each team in team_names:
    FOR each env_key in env_keys:
      FOR each permission in env_rec:
        value = env_rec.get(team, {}).get(env_key, {}).get(permission, False)

  session_state.env_matrix = DataFrame(env_rows)

  RETURN True
```

**What this means for the SA:**
- SA can start on the Advisor tab with ZERO setup — just chat
- Click "Apply" → Setup tab gets teams + environments auto-populated
- Matrix tab gets permissions pre-filled from the recommendation
- SA reviews both tabs and adjusts anything before deploying
- Defaults applied: `generation_mode = "role_attributes"`, `Critical = True` for production

### 5. Context Preamble (first message only)

```
FUNCTION build_user_message(raw_input, context):

  IF context not yet sent this session:
    parts = []
    IF context has project_key:  parts.append("Project: voya-web")
    IF context has teams:        parts.append("Teams: Developer, QA, SRE")
    IF context has environments: parts.append("Environments: test (non-critical), prod (critical)")

    MARK context as sent (session_state flag)

    IF parts not empty:
      preamble = "[Customer context: " + join(parts) + "]\n\n"
      RETURN preamble + raw_input

  RETURN raw_input   # subsequent messages — no preamble

# What the model sees on first message:
#   "[Customer context: Project: voya-web, Teams: Developer, QA, SRE, Environments: test (non-critical), prod (critical)]
#
#    Developers need full access in test but only targeting in prod."
#
# What the SA sees in chat:
#   "Developers need full access in test but only targeting in prod."
#   (preamble is transparent — injected but not shown)
```

### 6. Starter Prompts (empty chat only)

```
FUNCTION render_starter_prompts():

  # Only shown when chat history is empty
  IF session_state.messages is not empty:
    RETURN None

  DISPLAY "Quick start — pick a scenario:"

  FOR each starter in STARTER_PROMPTS (6 total):
    DISPLAY button with starter.label
    IF button clicked:
      RETURN starter.prompt   # used as the user input

  DISPLAY "Or type your own scenario below."
  RETURN None
```

### 7. Chat UI Flow (updated)

```
FUNCTION render_advisor_tab():

  initialize_session_state()

  api_key = get_gemini_api_key()   # admin-provided, from env/secrets
  IF no api_key: SHOW config message, RETURN

  context = read teams/envs/project from session_state
  render_context_panel(context)

  IF advisor not in session_state:
    advisor = RBACAdvisor(api_key)
    advisor.set_context(**context)
    session_state.advisor_instance = advisor

  render_chat_history()

  IF last_recommendation exists:
    SHOW "Apply to Matrix" button
    IF clicked: apply_recommendation(rec, context)  # populates Setup + Matrix

  # ── Starter prompts (only when chat is empty) ──
  selected_starter = None
  IF chat history is empty:
    selected_starter = render_starter_prompts()

  # ── Chat input (starter takes priority if clicked) ──
  user_input = selected_starter OR st.chat_input("Describe your teams...")

  IF user_input:
    # Wrap first message with context preamble (transparent to SA)
    message_to_send = build_user_message(user_input, context)

    APPEND user_input to history (display version, no preamble)
    DISPLAY user_input in chat bubble

    WITH assistant chat bubble:
      full_response = ""
      FOR each chunk in advisor.stream_recommendation(message_to_send):
        full_response += chunk
        UPDATE placeholder with full_response + cursor

      DISPLAY final response
      APPEND to history

      recommendation = parse_recommendation(full_response)
      IF recommendation exists:
        session_state.last_recommendation = recommendation
        RERUN (to show Apply button, hide starter prompts)
```

---

## Streamlit Widget Caching Workaround

The biggest implementation challenge was Streamlit's widget value caching. When the Advisor's Apply button writes `True` values into DataFrames (`project_matrix`, `env_matrix`), Streamlit's checkbox widgets in the Matrix tab still hold their old `False` values from a previous render. The DataFrame data is correct in `session_state`, but widgets override it on the next rerun because Streamlit caches widget values by key.

### The Fix: Version-Based Widget Keys

Each time Apply runs, a version counter increments in `session_state`:

```python
# In _apply_recommendation():
st.session_state["_widget_version"] = st.session_state.get("_widget_version", 0) + 1

# In matrix_tab.py — checkbox widgets include the version:
version = st.session_state.get("_widget_version", 0)
key = f"proj_v{version}_{group}_{team}_{perm}"
st.checkbox(perm, value=df_value, key=key)
```

When the version changes, Streamlit sees new keys and creates fresh widgets that read from the updated DataFrame. Old keys are abandoned.

### Same Fix for data_editor Widgets

The Setup tab's `st.data_editor` for teams and `env_groups` had the same caching problem:

```python
version = st.session_state.get("_widget_version", 0)
st.data_editor(teams_df, key=f"teams_editor_v{version}")
st.data_editor(env_groups_df, key=f"env_groups_editor_v{version}")
```

### env_groups Stale Data Bypass

Even with versioned keys, the Setup tab's `data_editor` would restore default `env_groups` (Test, Production) after Apply wrote 4 environments. The Matrix tab now reads environment keys directly from `env_matrix` when `_advisor_applied` is `True`:

```python
if st.session_state.get("_advisor_applied"):
    # Trust Advisor's data — bypass stale env_groups
    env_keys = st.session_state.env_matrix["Environment"].unique().tolist()
else:
    env_keys = st.session_state.env_groups["Key"].tolist()
```

---

## Test Cases

**Test file:** `tests/test_ai_advisor.py`

> **Note:** Tests mock the Gemini API — we test prompt building, response parsing,
> matrix application, and error handling without making real API calls.
> **20 tests total** (expanded from the original 12 design spec).

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
| 12 | Create `_apply_recommendation()` | `ui/advisor_tab.py` |
| 13 | Create `render_advisor_tab()` | `ui/advisor_tab.py` |
| 14 | Export from `ui/__init__.py` | `ui/__init__.py` |
| 15 | Add Tab 5 to `app.py` | `app.py` |
| 16 | Add `google-genai>=1.0.0` to `requirements.txt` | `requirements.txt` |
| 17 | Write all 20 tests | `tests/test_ai_advisor.py` |
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
