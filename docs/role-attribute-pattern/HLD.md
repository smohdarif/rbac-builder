# High-Level Design: Role Attribute Pattern for Environment Scoping

**Status:** Reference Document
**Pattern Source:** ps-terraform-private-customer-sa-demo
**Purpose:** Explains how LaunchDarkly RBAC uses role attributes to scope permissions to specific environments explicitly, instead of relying on the `{critical:true}` environment property filter.

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Two Approaches Compared](#two-approaches-compared)
3. [How the Role Attribute Pattern Works](#how-the-role-attribute-pattern-works)
4. [Architecture Overview](#architecture-overview)
5. [Key Components](#key-components)
6. [Data Flow](#data-flow)
7. [Why This Pattern is Preferred](#why-this-pattern-is-preferred)

---

## The Problem

When scoping LaunchDarkly RBAC roles to specific environments, you need a way to say:

> "This team can update targeting in Production and Staging, but NOT in Test or Dev."

There are two ways to achieve this in LaunchDarkly:

---

## Two Approaches Compared

### Approach A: `{critical:true}` Property Filter (NOT used in sa-demo)

```
proj/${roleAttribute/projects}:env/*;{critical:true}:flag/*
```

- Uses LD's built-in `critical` boolean property on environments
- Requires an LD admin to mark each environment as `critical` via `updateCritical` action
- **Risk:** If environments are not tagged, the role silently grants no access or wrong access
- **Risk:** Not verified to evaluate correctly without live testing
- **Flexibility:** Only two tiers — critical and non-critical

### Approach B: Role Attribute Pattern (USED in sa-demo) ✅

```
proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
```

- Uses named role attributes to pass exact environment keys per team
- No dependency on environment properties being set in LD
- Deterministic — you can read exactly which environments a team has access to
- **Flexible:** Each team can have a completely different set of environments per permission

---

## How the Role Attribute Pattern Works

The pattern has two parts that work together:

### Part 1: Shared Role Template (defined once)

A single role is created with a placeholder for the environment:

```
Resource: proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
```

This role is **shared by all teams**. The placeholder `${roleAttribute/update-targeting-environments}` is empty until a team is assigned this role.

### Part 2: Team Assignment with Role Attributes (defined per team)

When a team is assigned the role, `role_attributes` blocks fill in the placeholders:

```hcl
role_attributes {
  key    = "update-targeting-environments"
  values = ["production", "staging"]
}
```

LaunchDarkly substitutes these values at evaluation time:

```
proj/my-project:env/production:flag/*   ← one resolved resource
proj/my-project:env/staging:flag/*      ← another resolved resource
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAUNCHDARKLY ACCOUNT                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               SHARED ROLE TEMPLATES                     │   │
│  │  (created once, reused by all teams)                    │   │
│  │                                                         │   │
│  │  update-targeting                                       │   │
│  │  ├─ resource: proj/${projects}:env/${ut-envs}:flag/*   │   │
│  │  └─ actions: [updateOn, updateRules, updateTargets...] │   │
│  │                                                         │   │
│  │  apply-changes                                          │   │
│  │  ├─ resource: proj/${projects}:env/${ac-envs}:flag/*   │   │
│  │  └─ actions: [applyApprovalRequest]                    │   │
│  │                                                         │   │
│  │  view-sdk-key                                           │   │
│  │  ├─ resource: proj/${projects}:env/${vsk-envs}         │   │
│  │  └─ actions: [viewSdkKey]                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                    assigned to teams                            │
│                           │                                     │
│  ┌──────────────────┐     │    ┌──────────────────────────┐    │
│  │  TEAM: Developers│─────┘    │  TEAM: Senior Developers │    │
│  │                  │          │                          │    │
│  │  Roles:          │          │  Roles:                  │    │
│  │  - update-target │          │  - review-changes        │    │
│  │  - apply-changes │          │  - manage-segments       │    │
│  │  - view-sdk-key  │          │                          │    │
│  │                  │          │  role_attributes:        │    │
│  │  role_attributes:│          │  projects = [default]    │    │
│  │  projects =      │          │  review-changes-envs =   │    │
│  │    [default]     │          │    [production, staging] │    │
│  │  ut-envs =       │          │                          │    │
│  │    [prod,staging]│          └──────────────────────────┘    │
│  │  ac-envs =       │                                          │
│  │    [production]  │                                          │
│  └──────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Role Template
A LaunchDarkly custom role with `${roleAttribute/...}` placeholders in resource strings.

| Field | Example Value |
|-------|--------------|
| key | `update-targeting` |
| resource | `proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*` |
| actions | `[updateOn, updateRules, updateFallthrough, ...]` |
| base_permissions | `no_access` |

### 2. Team
A LaunchDarkly team that holds:
- A list of role keys (which shared roles it uses)
- `role_attributes` blocks that fill in the placeholders for every role it holds

### 3. Role Attribute
A key-value pair on a team that substitutes into role resource strings at evaluation time.

| Attribute Key | Attribute Values | Fills Placeholder |
|--------------|-----------------|-------------------|
| `projects` | `["default"]` | `${roleAttribute/projects}` |
| `update-targeting-environments` | `["production", "staging"]` | `${roleAttribute/update-targeting-environments}` |
| `apply-changes-environments` | `["production"]` | `${roleAttribute/apply-changes-environments}` |

---

## Data Flow

```
1. SA configures requirements
        │
        ▼
2. Role templates created in LD (once per account)
   update-targeting → resource uses ${roleAttribute/update-targeting-environments}
        │
        ▼
3. Teams created in LD
   Each team assigned role keys
        │
        ▼
4. role_attributes added to each team
   update-targeting-environments = ["production", "staging"]
        │
        ▼
5. User assigned to team
        │
        ▼
6. User takes action (e.g., updates flag in production)
        │
        ▼
7. LD policy engine resolves role attributes
   ${roleAttribute/update-targeting-environments} → ["production", "staging"]
        │
        ▼
8. LD evaluates: does action match any resolved resource?
   proj/default:env/production:flag/* → YES ✅
   proj/default:env/test:flag/*       → NO  ❌
```

---

## Why This Pattern is Preferred

| Concern | `{critical:true}` Filter | Role Attribute Pattern |
|---------|--------------------------|----------------------|
| Requires env setup in LD? | Yes — admin must set `critical` on each env | No — env keys used directly |
| Readable? | Need to know which envs are marked critical | Explicit — env names visible in team config |
| Flexible tiers? | Only 2: critical / non-critical | Unlimited — per role, per team |
| Fails safely? | Unknown (untested) | Yes — wrong env key = no match = no access |
| Testable? | Hard without live LD account | Easy — inspect role_attributes directly |
| Per-role scoping? | No — one env set for all env roles | Yes — different envs for update vs apply |

---

## Navigation

- [DLD →](./DLD.md)
- [Pseudo Logic & Test Cases →](./PSEUDOLOGIC_AND_TESTS.md)
