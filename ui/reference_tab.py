"""
Reference Tab - RBAC Documentation and Reference Guide
========================================================

This module renders Tab 4: Reference Guide.

Responsibilities:
- RBAC hierarchy diagram
- Key terms and definitions
- Members & teams explanation
- Built-in roles reference
- Policies and JSON structure
- Resources and actions reference
"""

import streamlit as st
import pandas as pd

# =============================================================================
# Content Constants (Public - for testing)
# =============================================================================

HIERARCHY_DIAGRAM = """
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAUNCHDARKLY RBAC HIERARCHY                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ACCOUNT (your-company)                                                 │
│  └── MEMBERS ─────────────────────┬───────────────────────────────────┐│
│      (alice@co.com)               │                                   ││
│      (bob@co.com)                 │                                   ││
│                                   ▼                                   ││
│                              ┌─────────┐                              ││
│                              │  TEAMS  │                              ││
│                              └────┬────┘                              ││
│                                   │                                   ││
│         ┌─────────────────────────┼─────────────────────────┐        ││
│         │                         │                         │        ││
│         ▼                         ▼                         ▼        ││
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐  ││
│  │ BUILT-IN    │          │ CUSTOM      │          │ CUSTOM      │  ││
│  │ ROLE        │          │ ROLE        │          │ ROLE        │  ││
│  │ (Reader)    │          │ (dev-role)  │          │ (qa-role)   │  ││
│  └─────────────┘          └──────┬──────┘          └──────┬──────┘  ││
│                                  │                        │          ││
│                                  ▼                        ▼          ││
│                           ┌────────────┐          ┌────────────┐    ││
│                           │   POLICY   │          │   POLICY   │    ││
│                           │ effect:    │          │ effect:    │    ││
│                           │   allow    │          │   allow    │    ││
│                           │ actions:   │          │ actions:   │    ││
│                           │  [create]  │          │  [update]  │    ││
│                           │ resources: │          │ resources: │    ││
│                           │  [proj/*]  │          │  [env/test]│    ││
│                           └─────┬──────┘          └─────┬──────┘    ││
│                                 │                       │            ││
│                                 ▼                       ▼            ││
│                           ┌─────────────────────────────────────┐   ││
│                           │           RESOURCES                 │   ││
│                           │  proj/mobile ──► env/prod ──► flag  │   ││
│                           └─────────────────────────────────────┘   ││
└─────────────────────────────────────────────────────────────────────┘│
```
"""

KEY_TERMS = [
    ("Account", "Top-level container in LaunchDarkly; represents your organization"),
    ("Member", "An individual user with access to a LaunchDarkly account"),
    ("Team", "A group of members who share common roles and permissions"),
    ("Built-in Role", "Pre-defined roles: Reader, Writer, Admin, Owner"),
    ("Custom Role", "User-defined role with specific permissions defined by policies"),
    ("Policy", "JSON document defining allowed/denied actions on resources"),
    ("Resource", "Something you control access to (project, environment, flag, etc.)"),
    ("Action", "Specific operation on a resource (e.g., createFlag, updateTargets)"),
    ("Effect", "Result of a policy statement: 'allow' or 'deny'"),
]

BUILTIN_ROLES = [
    ("Reader", "View only", "Can view all resources but cannot make changes"),
    ("Writer", "Standard access", "Can modify most resources (flags, segments, etc.)"),
    ("Admin", "Full access", "Can do everything except manage billing"),
    ("Owner", "Complete control", "Full access including billing and account deletion"),
    ("No Access", "Restricted", "Explicitly denies all access (special cases)"),
]


# =============================================================================
# Private Render Functions
# =============================================================================

def _render_hierarchy() -> None:
    """Render RBAC hierarchy diagram section."""
    with st.expander("🔗 How It All Connects (Visual Overview)", expanded=True):
        st.markdown(HIERARCHY_DIAGRAM)

        st.markdown("""
**The Flow:**
1. **Member** joins the account
2. Member is assigned to **Teams** (and/or given direct roles)
3. Teams have **Custom Roles** (or built-in roles)
4. Custom Roles contain **Policies**
5. Policies define **Actions** allowed on **Resources**
        """)


def _render_key_terms() -> None:
    """Render key terms section."""
    with st.expander("📖 Key Terms & Definitions", expanded=False):
        st.markdown("### Core Terminology")

        terms_data = pd.DataFrame({
            "Term": [t[0] for t in KEY_TERMS],
            "Definition": [t[1] for t in KEY_TERMS]
        })

        st.dataframe(terms_data, use_container_width=True, hide_index=True)


def _render_members_teams() -> None:
    """Render members and teams explanation section."""
    with st.expander("👥 Members & Teams", expanded=False):
        st.markdown("""
### Members

A **Member** is an individual user who has access to your LaunchDarkly account.

> *"Each member must have at least one role assigned to them, either directly or through a team."*

**Key points:**
- Members are people (employees, contractors, partners)
- Every member must have at least one role
- Members can belong to zero or more teams
- Member's total access = Direct roles + All team roles

---

### Teams

A **Team** is a group of members who share common access needs.

**Why use teams?**

| Without Teams | With Teams |
|---------------|------------|
| Assign roles to 50 developers individually | Create "Developers" team, assign role once |
| New hire = assign 5 roles manually | New hire = add to 2 teams |
| Role change = update 50 members | Role change = update 1 team |

**Permission aggregation:**
Access granted to an individual member is *combined* with access granted through teams.
        """)


def _render_builtin_roles() -> None:
    """Render built-in roles section."""
    with st.expander("🏷️ Built-in Roles", expanded=False):
        st.markdown("### LaunchDarkly Built-in Roles")

        roles_data = pd.DataFrame({
            "Role": [r[0] for r in BUILTIN_ROLES],
            "Access Level": [r[1] for r in BUILTIN_ROLES],
            "Description": [r[2] for r in BUILTIN_ROLES]
        })

        st.dataframe(roles_data, use_container_width=True, hide_index=True)


def _render_policies() -> None:
    """Render policies JSON structure section."""
    with st.expander("📜 Policies (JSON Structure)", expanded=False):
        st.markdown("""
### What is a Policy?

A **Policy** is a JSON document that defines what actions are allowed or denied on which resources.

### Policy Structure

```json
[
  {
    "effect": "allow",
    "actions": ["createFlag", "updateFlag"],
    "resources": ["proj/mobile-app:env/*:flag/*"]
  },
  {
    "effect": "deny",
    "actions": ["deleteFlag"],
    "resources": ["proj/*"]
  }
]
```

### Policy Evaluation Rules

```
┌─────────────────────────────────────────────────────────────┐
│                  POLICY EVALUATION ORDER                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EXPLICIT DENY wins                                      │
│     If any statement denies access → ACCESS DENIED          │
│                                                             │
│  2. EXPLICIT ALLOW grants access                            │
│     If allowed and none deny → ACCESS GRANTED               │
│                                                             │
│  3. DEFAULT DENY                                            │
│     If no statement mentions it → ACCESS DENIED             │
│                                                             │
│  4. MOST PERMISSIVE wins (across multiple roles)            │
│     If Role A allows and Role B denies → ACCESS GRANTED     │
│                                                             │
│  ⚠️  Statement order does NOT matter                        │
└─────────────────────────────────────────────────────────────┘
```
        """)


def _render_resources() -> None:
    """Render resources section."""
    with st.expander("🎯 Resources & Resource Syntax", expanded=False):
        st.markdown("""
### What is a Resource?

A **Resource** is something you can control access to in LaunchDarkly.

### Resource Types

| Type | Key | Example | Scoped to env? |
|------|-----|---------|:--------------:|
| Project | `proj` | `proj/mobile-app` | — |
| Environment | `env` | `proj/mobile-app:env/production` | ✅ |
| Feature Flag | `flag` | `proj/mobile-app:env/prod:flag/new-checkout` | ✅ |
| Segment | `segment` | `proj/mobile-app:env/prod:segment/beta-users` | ✅ |
| Metric | `metric` | `proj/mobile-app:metric/conversion-rate` | ❌ |
| AI Config | `aiconfig` | `proj/mobile-app:env/prod:aiconfig/my-llm-config` | ✅ |
| Session | `session` | `proj/mobile-app:session/*` | ❌ |
| Error | `error` | `proj/mobile-app:error/*` | ❌ |
| Log | `log` | `proj/mobile-app:log/*` | ❌ |
| Trace | `trace` | `proj/mobile-app:trace/*` | ❌ |
| Alert | `alert` | `proj/mobile-app:alert/*` | ❌ |
| Observability Dashboard | `observability-dashboard` | `proj/mobile-app:observability-dashboard/*` | ❌ |
| Vega AI | `vega` | `proj/mobile-app:vega/*` | ❌ |

### Resource Syntax (Hierarchical)

```
proj/mobile-app:env/production:flag/new-checkout
│              │              │
└── Project    └── Environment└── Flag
```

### Wildcards

| Pattern | Meaning |
|---------|---------|
| `proj/*` | All projects |
| `proj/mobile-app:env/*` | All environments in mobile-app |
| `proj/*:env/*:flag/*` | All flags in all projects |
| `proj/*:env/*;Production:flag/*` | All flags in Production environments |

⚠️ **Important:** Resource keys are case-sensitive and must use keys, not display names.
        """)


def _render_actions() -> None:
    """Render actions reference section."""
    with st.expander("⚡ Actions Reference", expanded=False):
        st.markdown("### Common Flag Actions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Project-Level Actions**")
            project_actions = pd.DataFrame({
                "Action": ["createFlag", "deleteFlag", "archiveFlag", "updateName", "updateDescription", "updateTags", "updateClientSideFlagAvailability"],
                "Description": [
                    "Create a new feature flag",
                    "Delete a feature flag",
                    "Archive (retire) a flag",
                    "Rename a flag",
                    "Update flag description",
                    "Modify flag tags",
                    "Control client-side SDK exposure"
                ]
            })
            st.dataframe(project_actions, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Environment-Level Actions**")
            env_actions = pd.DataFrame({
                "Action": ["updateOn", "updateTargets", "updateRules", "updateFallthrough", "updateOffVariation", "updatePrerequisites"],
                "Description": [
                    "Toggle the kill switch (on/off)",
                    "Change individual user targeting",
                    "Modify targeting rules",
                    "Change default variation",
                    "Change 'off' variation",
                    "Modify flag prerequisites"
                ]
            })
            st.dataframe(env_actions, use_container_width=True, hide_index=True)

        st.markdown("""
### Wildcard Actions

| Pattern | Meaning |
|---------|---------|
| `*` | All actions |
| `update*` | All update actions |
| `create*` | All create actions |
        """)


def _render_ai_configs() -> None:
    """Render AI Configs section."""
    with st.expander("🤖 AI Configs Permissions (Dec 2024)", expanded=False):
        st.markdown("""
### What are AI Configs?

**AI Configs** is a LaunchDarkly feature for managing Large Language Models (LLMs) in generative AI applications.

> *"An AI Config is a single resource that you create in LaunchDarkly to control how your application uses large language models."*

### Key Capabilities

- Update model details at runtime without code deployment
- Gradually roll out new model versions and providers
- Run experiments comparing variations (cost, latency, satisfaction)
- Apply targeted safety filters by user segment, geography, or context
- Evaluate outputs using judges and online evaluations

### Resource Syntax

```
# Project-level AI Configs
proj/*:aiconfig/*

# Environment-level AI Configs
proj/*:env/*:aiconfig/*
```

### AI Config Actions

**Project-Level Actions:**

| Action | Description | Added |
|--------|-------------|-------|
| `createAIConfig` | Create a new AI Config | Dec 2024 |
| `updateAIConfig` | Update AI Config settings | Dec 2024 |
| `deleteAIConfig` | Delete an AI Config | Dec 2024 |
| `updateAIConfigVariation` | Update a variation | Dec 2024 |
| `deleteAIConfigVariation` | Delete a variation | Dec 2024 |

**Environment-Level Actions:**

| Action | Description | Added |
|--------|-------------|-------|
| `updateAIConfigTargeting` | Update targeting rules | Jun 2025 |

### Default Access

These roles have AI Config permissions by default:
- **Project roles:** Project Admin, Maintainer, Developer
- **Base roles:** Admin, Owner

### Official Documentation

- [AI Configs Overview](https://launchdarkly.com/docs/home/ai-configs/)
- [Create AI Configs](https://launchdarkly.com/docs/home/ai-configs/create)
- [AI Configs API (Beta)](https://launchdarkly.com/docs/api/ai-configs-beta)
        """)


def _render_observability() -> None:
    """Render Observability permissions section."""
    with st.expander("🔭 Observability Permissions", expanded=False):
        st.markdown("""
### What is LaunchDarkly Observability?

**LaunchDarkly Observability** is a suite of features for monitoring and debugging applications —
Sessions, Errors, Logs, Traces, Alerts, Dashboards, and the Vega AI assistant.

---

### Key Difference from Flag Permissions

> ⚠️ **All observability resources are project-scoped — there is no environment segment.**

| Type | Flag (for comparison) | Observability |
|------|-----------------------|---------------|
| Resource path | `proj/*:env/*:flag/*` | `proj/*:session/*` |
| Has `:env/*`? | ✅ Yes | ❌ No |
| Scoped to env? | Yes | No — project-wide |

**Why?** Observability data (traces, logs, sessions) is collected across all environments.
When debugging, you typically need visibility across production AND staging simultaneously.

---

### Resource Syntax

```
proj/${roleAttribute/projects}:session/*
proj/${roleAttribute/projects}:error/*
proj/${roleAttribute/projects}:log/*
proj/${roleAttribute/projects}:trace/*
proj/${roleAttribute/projects}:alert/*
proj/${roleAttribute/projects}:observability-dashboard/*
proj/${roleAttribute/projects}:vega/*
```

---

### Observability Actions by Resource Type

**Sessions** — `proj/*:session/*`

| Action | Description |
|--------|-------------|
| `viewSession` | View session replay data |

---

**Errors** — `proj/*:error/*`

| Action | Description |
|--------|-------------|
| `viewError` | View error tracking data |
| `updateErrorStatus` | Update error status (resolve, ignore, etc.) |

---

**Logs** — `proj/*:log/*`

| Action | Description |
|--------|-------------|
| `viewLog` | View log data |

---

**Traces** — `proj/*:trace/*`

| Action | Description |
|--------|-------------|
| `viewTrace` | View distributed trace data |

> ⚠️ **Traces are project-scoped** (`proj/*:trace/*`), **not** `proj/*:env/*:trace/*`.

---

**Alerts** — `proj/*:alert/*`

| Action | Description |
|--------|-------------|
| `viewAlert` | View alerts |
| `createAlert` | Create a new alert |
| `deleteAlert` | Delete an alert |
| `updateAlertOn` | Enable or disable an alert |
| `updateAlertConfiguration` | Update alert settings |

---

**Observability Dashboards** — `proj/*:observability-dashboard/*`

| Action | Description |
|--------|-------------|
| `viewObservabilityDashboard` | View dashboards |
| `createObservabilityDashboard` | Create a dashboard |
| `deleteObservabilityDashboard` | Delete a dashboard |
| `addObservabilityGraphToDashboard` | Add a graph to a dashboard |
| `removeObservabilityGraphFromDashboard` | Remove a graph from a dashboard |
| `updateObservabilityDashboardConfiguration` | Update dashboard settings |
| `updateObservabilityGraphConfiguration` | Update graph settings |
| `updateObservabilitySettings` | Update account-level observability settings |

---

**Vega AI Assistant** — `proj/*:vega/*`

| Action | Description |
|--------|-------------|
| `talkToVega` | Use the LaunchDarkly Vega AI assistant |

> ⚠️ **Vega is project-scoped** (`proj/*:vega/*`), **not** `proj/*:env/*:vega/*`.

---

### RBAC Builder Grouping

In the RBAC Builder matrix, observability permissions are in the **🔭 Observability** tab:

| Default (shown by default) | Optional |
|---------------------------|---------|
| View Sessions | Manage Alerts |
| View Errors | Manage Observability Dashboards |
| View Logs | Talk to Vega |
| View Traces | |

---

### Official Documentation

- [LaunchDarkly Observability](https://launchdarkly.com/docs/home/observability/)
- [Sessions](https://launchdarkly.com/docs/home/observability/sessions)
- [Errors](https://launchdarkly.com/docs/home/observability/errors)
        """)


def _render_permission_scopes() -> None:
    """Render permission scopes section."""
    with st.expander("🔐 Permission Scopes (Project vs Environment)", expanded=False):
        st.markdown("""
### Project-Level Permissions

These affect **ALL environments** simultaneously:

| Permission | Impact |
|------------|--------|
| Create Flags | Flag appears in ALL environments (OFF by default) |
| Update Flags | Metadata changes reflect everywhere |
| Archive Flags | Removes from ALL environments |
| Client Side Availability | Controls SDK exposure everywhere |
| Manage Metrics | Metrics used across environments |
| View Project | Read-only access to project |

---

### Environment-Level Permissions

These are **scoped to specific environments**:

| Permission | Impact |
|------------|--------|
| Update Targeting | Only affects targeting in THIS environment |
| Review Changes | See pending changes for THIS environment |
| Apply Changes | Approve changes in THIS environment |
| Manage Segments | Segments in THIS environment |
| Manage Experiments | Experiments in THIS environment |
| View SDK Key | See SDK key for THIS environment |

---

### Visual Comparison

```
PROJECT: mobile-app
┌─────────────────────────────────────────────────────────┐
│  PROJECT-LEVEL PERMISSIONS (apply everywhere)          │
│  • Create Flags  • Archive Flags  • View Project       │
└─────────────────────────────────────────────────────────┘

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ ENV: dev        │ │ ENV: staging    │ │ ENV: production │
│ (Test)          │ │ (Test)          │ │ (Production)    │
│                 │ │                 │ │                 │
│ • Update Target │ │ • Update Target │ │ • Review Changes│
│ • Segments      │ │ • Segments      │ │ • Apply Changes │
│ • Experiments   │ │ • Experiments   │ │ • Segments      │
│                 │ │                 │ │                 │
│ [Open Access]   │ │ [Limited]       │ │ [Restricted]    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```
        """)


def _render_upcoming_features() -> None:
    """Render upcoming features roadmap section."""
    with st.expander("🗺️ Upcoming Features & Roadmap", expanded=False):
        st.markdown("""
### What's Coming Next

| Phase | Feature | Priority | What it adds |
|-------|---------|----------|-------------|
| **16** | Terraform Export | 🔴 High | Generate `.tf` files for ps-terraform-private delivery |
| **17** | Global / Account-Level Roles | 🔴 High | `view_teams`, `manage_personal_access_tokens` in every team |
| **18** | LD Views Support | 🔴 High | RBAC for LaunchDarkly saved flag filter Views |
| **19** | Manage Context Kinds | 🔴 High | Standalone Context Kinds column in matrix |
| **20** | Deny Lists | 🟡 Medium | Explicit exclusions for environments/flags/projects |
| **21** | Visible Teams | 🟡 Medium | `visibleTeams` role attribute in all teams |
| **22** | Project Admin Roles | 🟡 Medium | Destructive admin actions (delete project, rotate SDK keys) |
| **23** | Environment Tag Specifiers | 🟢 Lower | `env/*;tag1,tag2` filtering |
| **24** | Flag / Segment Specifiers | 🟢 Lower | `flags=["feature-*"]` scoping |
| **25** | Team Management Global Roles | 🟢 Lower | `manage_members`, `manage_integrations` |

---

### Current Coverage (Phases 1–15)

- ✅ Full permission matrix (Flags, Metrics, AI Configs, Observability)
- ✅ Role attribute pattern (sa-demo compatible)
- ✅ Client delivery ZIP with `deploy.py` script
- ✅ Markdown deployment guide
- ✅ Direct LD API deployment (Connected mode)
- ✅ Tab-based grouped UI

📄 **Full roadmap:** See `docs/ROADMAP.md` in this project.
        """)


def _render_documentation_links() -> None:
    """Render official documentation links section."""
    with st.expander("🔗 Official LaunchDarkly Documentation", expanded=False):
        st.markdown("""
### Official Documentation Links

| Topic | Link |
|-------|------|
| Role Concepts | [docs.launchdarkly.com/home/account/roles/role-concepts](https://launchdarkly.com/docs/home/account/roles/role-concepts) |
| Building Teams | [docs.launchdarkly.com/guides/teams-roles/teams](https://launchdarkly.com/docs/guides/teams-roles/teams) |
| Custom Roles | [docs.launchdarkly.com/guides/teams-roles/custom-roles](https://launchdarkly.com/docs/guides/teams-roles/custom-roles) |
| Using Policies | [docs.launchdarkly.com/home/account/roles/role-policies](https://launchdarkly.com/docs/home/account/roles/role-policies) |
| Using Resources | [docs.launchdarkly.com/home/account/roles/role-resources](https://launchdarkly.com/docs/home/account/roles/role-resources) |
| Using Actions | [docs.launchdarkly.com/home/account/roles/role-actions](https://launchdarkly.com/docs/home/account/roles/role-actions) |

📄 **Full documentation:** See `docs/RBAC_CONCEPTS.md` in this project for detailed explanations.
        """)


# =============================================================================
# Main Render Function (Public)
# =============================================================================

def render_reference_tab() -> None:
    """
    Render the Reference Guide tab UI.

    This is the main entry point for Tab 4. It displays static reference
    content about LaunchDarkly RBAC concepts.
    """
    st.header("📚 LaunchDarkly RBAC Reference Guide")
    st.markdown("*Quick reference for RBAC concepts while designing your permission matrix*")

    # Render all sections
    _render_hierarchy()
    _render_key_terms()
    _render_members_teams()
    _render_builtin_roles()
    _render_policies()
    _render_resources()
    _render_actions()
    _render_ai_configs()
    _render_observability()
    _render_permission_scopes()
    _render_upcoming_features()
    _render_documentation_links()
