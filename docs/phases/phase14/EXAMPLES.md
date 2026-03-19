# Phase 14: Output Examples Explained

Real examples from the rbac-builder output, explained line by line.
Use this as a reference when reviewing generated JSON with customers.

---

## Table of Contents

1. [A Role Object — Talk to Vega](#1-a-role-object--talk-to-vega)
2. [A Team Object — Voya Web Developer](#2-a-team-object--voya-web-developer)
3. [How They Connect at Runtime](#3-how-they-connect-at-runtime)
4. [Key Patterns to Remember](#4-key-patterns-to-remember)

---

## 1. A Role Object — Talk to Vega

This is one entry from the `custom_roles` array in the payload JSON.

```json
{
  "key": "talk-to-vega",
  "name": "Talk to Vega",
  "description": "Template role for Talk to Vega",
  "base_permissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": ["talkToVega"],
      "resources": ["proj/${roleAttribute/projects}:vega/*"]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

### Line by line

| Field | What it means |
|-------|--------------|
| `key` | Unique ID used internally by LD. Lowercase + hyphens. Must exist before a team can reference it. |
| `name` | Display name shown in the LD UI. |
| `description` | Short explanation shown as a subtitle in the LD UI. |
| `base_permissions` | Starting point before any policy applies. `no_access` = deny everything by default (least privilege). Policy statements below then add back specific access. |
| `policy` | Array of permission rules. Each rule says: allow or deny these actions on these resources. |

### Policy Statement 1 — the actual Vega permission

```json
{
  "effect": "allow",
  "actions": ["talkToVega"],
  "resources": ["proj/${roleAttribute/projects}:vega/*"]
}
```

| Part | Meaning |
|------|---------|
| `effect: allow` | Grant access (opposite is `deny`) |
| `talkToVega` | The LD action code for using the Vega AI assistant. Verified against `gonfalon/internal/roles/action.go` |
| `proj/` | This is a project-level resource |
| `${roleAttribute/projects}` | Placeholder — filled in at runtime with the team's project key (e.g. `voya-web`) |
| `:vega/*` | The vega resource type, `*` = all Vega resources |

> **No `:env/*` segment** — all observability resources are project-scoped, confirmed in Gonfalon source code.
> See [DESIGN.md — Why No Environment-Level Observability Permissions](./DESIGN.md#why-no-environment-level-observability-permissions)

### Policy Statement 2 — viewProject (always included)

```json
{
  "effect": "allow",
  "actions": ["viewProject"],
  "resources": ["proj/${roleAttribute/projects}"]
}
```

Every role includes this. Without `viewProject`, the user can't see the project in the LD UI at all — they get a blank screen. The resource here targets the **project itself** (no suffix) rather than resources inside it.

### In plain English

> "A user with this role can use the Vega AI assistant in any project assigned to their team, and can see that project in the LD UI."

---

## 2. A Team Object — Voya Web Developer

This is one entry from the `teams` array in the payload JSON.

```json
{
  "key": "voya-web-dev",
  "name": "Voya Web: Developer",
  "description": "Development team",
  "customRoleKeys": [
    "view-errors",
    "view-project",
    "view-logs",
    "view-sessions",
    "manage-alerts",
    "talk-to-vega",
    "update-targeting",
    "view-traces",
    "manage-observability-dashboards"
  ],
  "roleAttributes": [
    {
      "key": "projects",
      "values": ["voya-web"]
    },
    {
      "key": "update-targeting-environments",
      "values": ["Test", "Production"]
    }
  ]
}
```

### Line by line

| Field | What it means |
|-------|--------------|
| `key` | Unique team ID. Format: `{project}-{team}`. Built automatically from your project key + team key. |
| `name` | Display name. Format: `{Project}: {Team}`. |
| `description` | Free text you entered in the Setup tab. |
| `customRoleKeys` | The list of custom roles assigned to this team. Every key here must already exist in LD as a custom role (deploy roles first, then teams). |
| `roleAttributes` | The substitution values that fill in `${roleAttribute/...}` placeholders in each role's resource string. |

### customRoleKeys — what this team can do

The Developer team has 9 roles:

| Role key | Type | What it allows |
|----------|------|---------------|
| `view-errors` | Observability | View error tracking data |
| `view-logs` | Observability | View log data |
| `view-sessions` | Observability | View session replays |
| `view-traces` | Observability | View distributed traces |
| `manage-alerts` | Observability | Create, delete, update alerts |
| `manage-observability-dashboards` | Observability | Full dashboard management |
| `talk-to-vega` | Observability | Use the Vega AI assistant |
| `update-targeting` | Flags | Update flag targeting rules |
| `view-project` | Project | See the project in LD UI |

### roleAttributes — where they can do it

**Attribute 1: projects**
```json
{ "key": "projects", "values": ["voya-web"] }
```
Fills in `${roleAttribute/projects}` across **every role** this team has.

Example resolution: `proj/${roleAttribute/projects}:session/*` → `proj/voya-web:session/*`

Only one project per team — this enforces project isolation. The Developer team can only act within `voya-web`, not any other LD project.

**Attribute 2: update-targeting-environments**
```json
{ "key": "update-targeting-environments", "values": ["Test", "Production"] }
```
Fills in `${roleAttribute/update-targeting-environments}` for the `update-targeting` role only.

Example resolution:
```
proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
        ↓
proj/voya-web:env/Test:flag/*        ← Developer can target flags in Test
proj/voya-web:env/Production:flag/*  ← Developer can target flags in Production
```

### Why no environment attributes for observability roles?

Notice there is no `view-sessions-environments` or `view-errors-environments` attribute. That's because **observability resources are project-scoped** — LD doesn't use an environment segment to resolve them. The `projects` attribute alone is sufficient.

```
Observability resource:  proj/${roleAttribute/projects}:session/*
Only needs one attr:     projects = ["voya-web"]
Resolves to:             proj/voya-web:session/*   ✅

Flag resource:           proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
Needs two attrs:         projects = ["voya-web"]
                         update-targeting-environments = ["Test", "Production"]
Resolves to:             proj/voya-web:env/Test:flag/*
                         proj/voya-web:env/Production:flag/*   ✅
```

### In plain English

> "The Voya Web Developer team can view all observability data (sessions, errors, logs, traces), manage alerts and dashboards, and use the Vega AI assistant — all within the `voya-web` project. They can also update flag targeting, but only in the Test and Production environments."

---

## 3. How They Connect at Runtime

When a Developer team member tries to do something in LD, this is what happens:

```
User action: "I want to use Vega AI in project voya-web"
        │
        ▼
LD finds user's teams → ["voya-web-dev"]
        │
        ▼
LD looks up team's customRoleKeys → includes "talk-to-vega"
        │
        ▼
LD looks up "talk-to-vega" role → resource: "proj/${roleAttribute/projects}:vega/*"
        │
        ▼
LD looks up team's roleAttributes → projects = ["voya-web"]
        │
        ▼
LD resolves placeholder → "proj/voya-web:vega/*"
        │
        ▼
LD checks: does user's action match this resource? YES ✅ → ALLOWED

---

User action: "I want to use Vega AI in project other-project"
        │
        ▼
LD resolves → "proj/voya-web:vega/*"
Does "proj/other-project:vega/*" match "proj/voya-web:vega/*"? NO ❌ → DENIED
```

---

## 4. Key Patterns to Remember

### Role vs Team — what each does

| | Role (`customRoles`) | Team |
|-|---------------------|------|
| **Defines** | What actions are possible | Who gets those actions and where |
| **Contains** | `policy` statements with actions + resources | `customRoleKeys` + `roleAttributes` |
| **Created** | Once, shared by all teams | One per logical group of users |
| **Deploy order** | **First** | **Second** (after roles exist) |

### When you see `${roleAttribute/...}` in a resource

It's a placeholder. The actual value comes from the team's `roleAttributes` block.
The role is a template — the team fills it in.

### When a permission has an `-environments` attribute

That permission is **environment-scoped** (like flag targeting).
Different teams can have different environments for the same permission:
- Dev team: `update-targeting-environments = ["Test"]`
- Senior Dev team: `update-targeting-environments = ["Test", "Production"]`

Same role template, different access.

### When a permission has NO `-environments` attribute

That permission is **project-scoped** (like all observability).
The `projects` attribute alone is enough — no environment qualifier needed.
