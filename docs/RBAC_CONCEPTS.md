# RBAC Concepts & Flows for LaunchDarkly

> A comprehensive guide to understanding Role-Based Access Control (RBAC) in LaunchDarkly

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [What is RBAC?](#11-what-is-rbac)
   - 1.2 [Why RBAC Matters](#12-why-rbac-matters)
   - 1.3 [RBAC in LaunchDarkly](#13-rbac-in-launchdarkly)

2. [LaunchDarkly RBAC Terminology](#2-launchdarkly-rbac-terminology)
   - 2.1 [Account](#21-account)
   - 2.2 [Members](#22-members)
   - 2.3 [Teams](#23-teams)
   - 2.4 [Built-in Roles](#24-built-in-roles)
   - 2.5 [Custom Roles](#25-custom-roles)
   - 2.6 [Policies](#26-policies)
   - 2.7 [Resources](#27-resources)
   - 2.8 [Actions](#28-actions)
   - 2.9 [How It All Connects](#29-how-it-all-connects)

3. [Core Concepts](#3-core-concepts)
   - 3.1 [Projects](#31-projects)
   - 3.2 [Environments](#32-environments)
   - 3.3 [Environment Groups](#33-environment-groups)
   - 3.4 [Teams](#34-teams)
   - 3.5 [Custom Roles](#35-custom-roles)
   - 3.6 [Permissions](#36-permissions)

4. [Permission Scopes](#4-permission-scopes)
   - 4.1 [Project-Level Permissions](#41-project-level-permissions)
   - 4.2 [Environment-Level Permissions](#42-environment-level-permissions)
   - 4.3 [Scope Comparison](#43-scope-comparison)

5. [AI Configs Permissions](#5-ai-configs-permissions)
   - 5.1 [What are AI Configs?](#51-what-are-ai-configs)
   - 5.2 [AI Config Actions](#52-ai-config-actions)
   - 5.3 [AI Config Resource Syntax](#53-ai-config-resource-syntax)

6. [Common Scenarios & Flows](#6-common-scenarios--flows)
   - 6.1 [Developer Creating a Feature Flag](#61-developer-creating-a-feature-flag)
   - 6.2 [QA Testing a Flag](#62-qa-testing-a-flag)
   - 6.3 [Release Manager Deploying to Production](#63-release-manager-deploying-to-production)
   - 6.4 [Read-Only Stakeholder Access](#64-read-only-stakeholder-access)

7. [Designing Your RBAC Matrix](#7-designing-your-rbac-matrix)
   - 7.1 [Step 1: Identify Teams/Personas](#71-step-1-identify-teamspersonas)
   - 7.2 [Step 2: Define Environment Groups](#72-step-2-define-environment-groups)
   - 7.3 [Step 3: Assign Project Permissions](#73-step-3-assign-project-permissions)
   - 7.4 [Step 4: Assign Environment Permissions](#74-step-4-assign-environment-permissions)

8. [Best Practices](#8-best-practices)

9. [Appendix](#9-appendix)
   - A. [Glossary](#a-glossary)
   - B. [Permission Reference Table](#b-permission-reference-table)
   - C. [Example RBAC Configurations](#c-example-rbac-configurations)
   - D. [Official LaunchDarkly Documentation Links](#d-official-launchdarkly-documentation-links)

---

## 1. Introduction

### 1.1 What is RBAC?

**Role-Based Access Control (RBAC)** is a security model that restricts system access based on the roles of individual users within an organization.

Instead of assigning permissions directly to each user, you:
1. Define **roles** (e.g., Developer, QA, Admin)
2. Assign **permissions** to roles
3. Assign **users** to roles

```
┌─────────────────────────────────────────────────────────────┐
│                    RBAC Model                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Users ────────► Roles ────────► Permissions               │
│                                                             │
│   Alice ──┐                                                 │
│           ├────► Developer ────► Create Flags               │
│   Bob ────┘                      Update Flags               │
│                                  View Project               │
│                                                             │
│   Carol ───────► Admin ────────► All Permissions            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Why RBAC Matters

| Benefit | Description |
|---------|-------------|
| **Security** | Users only access what they need (Principle of Least Privilege) |
| **Compliance** | Audit trails show who can do what |
| **Scalability** | Add new users by assigning roles, not individual permissions |
| **Consistency** | Same role = same permissions everywhere |
| **Reduced Errors** | Prevent accidental changes to production |

### 1.3 RBAC in LaunchDarkly

LaunchDarkly's RBAC system allows you to control:
- Who can create, modify, or delete feature flags
- Who can change flag targeting in which environments
- Who can approve changes in critical environments
- Who can manage experiments, segments, and metrics

---

## 2. LaunchDarkly RBAC Terminology

> **Official Documentation:** [LaunchDarkly Role Concepts](https://launchdarkly.com/docs/home/account/roles/role-concepts)

This section explains LaunchDarkly's RBAC terminology in logical sequence, from the broadest concepts to the most specific.

### 2.1 Account

The **Account** is the top-level container in LaunchDarkly. Everything exists within an account:

```
LaunchDarkly Account (your-company)
├── Members (people)
├── Teams (groups of members)
├── Projects (containers for flags)
│   └── Environments (dev, staging, prod)
├── Custom Roles (permission definitions)
└── Integrations, SSO, etc.
```

An account is typically your organization or company.

### 2.2 Members

A **Member** is an individual user who has access to your LaunchDarkly account.

> "Each member must have at least one role assigned to them, either directly or through a team."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/account/roles/role-concepts)

**Key characteristics:**
- Members are people (employees, contractors, partners)
- Every member must have at least one role
- Members can belong to zero or more teams
- Members can have roles assigned directly OR inherited through teams

```
┌─────────────────────────────────────────────────────────────┐
│                        MEMBER                               │
├─────────────────────────────────────────────────────────────┤
│  Email: alice@company.com                                   │
│                                                             │
│  Direct Roles:        Teams:                                │
│  ├── Reader           ├── frontend-team                     │
│  └── (base role)      │   └── Custom Role: "frontend-dev"  │
│                       └── mobile-team                       │
│                           └── Custom Role: "mobile-dev"    │
│                                                             │
│  Effective Permissions = Direct Roles + All Team Roles     │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Teams

A **Team** is a group of members who share common access needs.

> "Teams are groups of your organization's members that allow administrators to assign specific permissions for performing actions on resources."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/guides/teams-roles/teams)

**Key characteristics:**
- Teams contain one or more members
- Teams can have custom roles assigned to them
- All members of a team inherit the team's roles
- A member's total access = individual roles + all team roles

**Why use teams?**

| Without Teams | With Teams |
|---------------|------------|
| Assign roles to 50 developers individually | Create "Developers" team, assign role once |
| New hire = assign 5 roles manually | New hire = add to 2 teams |
| Role change = update 50 members | Role change = update 1 team |

### 2.4 Built-in Roles

LaunchDarkly provides four **built-in roles** (also called "base roles"):

| Role | Access Level | Description |
|------|--------------|-------------|
| **Reader** | View only | Can view all resources but cannot make changes |
| **Writer** | Standard access | Can modify most resources (flags, segments, etc.) |
| **Admin** | Full access | Can do everything except manage billing |
| **Owner** | Complete control | Full access including billing and account deletion |

Additionally, some accounts have:
| Role | Access Level | Description |
|------|--------------|-------------|
| **No Access** | Restricted | Explicitly denies all access (special cases) |

**Preset Roles** (available to some customers):
| Role | Description |
|------|-------------|
| **Developer** | Flag-focused actions for engineering |
| **Contributor** | Limited flag modifications |
| **Maintainer** | Project maintenance tasks |

### 2.5 Custom Roles

A **Custom Role** is a user-defined role with specific permissions.

> "Custom roles let you define specific permissions and assign them to members or teams. By default, new roles cannot take any actions on any resources."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/account/roles/role-concepts)

**Key characteristics:**
- You define exactly what the role can and cannot do
- Custom roles start with NO permissions (deny by default)
- You explicitly grant access through policies
- Can be scoped to specific projects or environments

**Example Custom Roles:**

| Role Key | Description | Permissions |
|----------|-------------|-------------|
| `frontend-developer` | Frontend team flag access | Create/update flags in `web` project |
| `qa-tester` | QA testing access | Update targeting in test environments |
| `release-manager` | Production deployer | Apply changes in production |
| `read-only-stakeholder` | Observers | View everything, change nothing |

### 2.6 Policies

A **Policy** is a JSON document that defines what actions are allowed or denied on which resources.

> "Policies combine resources and actions into a set of statements that define what members can or cannot do in LaunchDarkly."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/account/roles/role-policies)

**Policy Structure:**

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

**Policy Statement Attributes:**

| Attribute | Required | Description |
|-----------|----------|-------------|
| `effect` | Yes | `"allow"` or `"deny"` |
| `actions` | Yes* | List of actions this statement applies to |
| `notActions` | Yes* | List of actions this statement does NOT apply to |
| `resources` | Yes* | List of resources this statement applies to |
| `notResources` | Yes* | List of resources this statement does NOT apply to |

*Use either `actions` OR `notActions`, and either `resources` OR `notResources`.

**Policy Evaluation Rules:**

```
┌─────────────────────────────────────────────────────────────┐
│                  POLICY EVALUATION ORDER                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EXPLICIT DENY wins                                      │
│     If any statement denies access → ACCESS DENIED          │
│                                                             │
│  2. EXPLICIT ALLOW grants access                            │
│     If a statement allows and none deny → ACCESS GRANTED    │
│                                                             │
│  3. DEFAULT DENY                                            │
│     If no statement mentions it → ACCESS DENIED             │
│                                                             │
│  4. MOST PERMISSIVE wins (across roles)                     │
│     If Role A allows and Role B denies → ACCESS GRANTED     │
│                                                             │
│  ⚠️  Statement order does NOT matter                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.7 Resources

A **Resource** is something you can control access to in LaunchDarkly.

> "Resources are specific elements or types of elements that you can allow or restrict access to."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/account/roles/role-resources)

**Resource Types:**

| Resource Type | Key | Description |
|---------------|-----|-------------|
| Project | `proj` | Container for flags and environments |
| Environment | `env` | Deployment stage within a project |
| Feature Flag | `flag` | Feature toggle |
| Segment | `segment` | Reusable user group |
| Metric | `metric` | Success measurement |
| Experiment | `experiment` | A/B test |
| Member | `member` | Account user |
| Team | `team` | Group of members |
| Integration | `integration` | Third-party connection |

**Resource Syntax:**

```
resource-type/name;tag1,tag2
```

**Scoped Resources (hierarchical):**

Some resources exist within other resources. Feature flags, for example, exist within environments, which exist within projects:

```
proj/mobile-app:env/production:flag/new-checkout
│              │              │
└── Project    └── Environment└── Flag
```

**Wildcards:**

| Pattern | Meaning |
|---------|---------|
| `proj/*` | All projects |
| `proj/mobile-app:env/*` | All environments in mobile-app |
| `proj/*:env/*:flag/*` | All flags in all projects |
| `proj/*:env/*;critical:flag/*` | All flags in critical environments |

**Important:** Resource keys are case-sensitive and must use keys, not display names.

### 2.8 Actions

An **Action** is a specific operation that can be performed on a resource.

> "Actions represent changes you can make to resources."
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/account/roles/role-actions)

**Common Flag Actions:**

| Action | Description |
|--------|-------------|
| `createFlag` | Create a new feature flag |
| `deleteFlag` | Delete a feature flag |
| `updateName` | Rename a flag |
| `updateDescription` | Update flag description |
| `updateTags` | Modify flag tags |
| `updateOn` | Toggle the kill switch (on/off) |
| `updateTargets` | Change individual user targeting |
| `updateRules` | Modify targeting rules |
| `updateFallthrough` | Change default variation |
| `updateOffVariation` | Change "off" variation |
| `updatePrerequisites` | Modify flag prerequisites |
| `archiveFlag` | Archive (retire) a flag |
| `restoreFlag` | Restore an archived flag |
| `updateFlagVariations` | Modify variation values |
| `updateClientSideFlagAvailability` | Control client-side SDK exposure |

**Wildcard Actions:**

| Pattern | Meaning |
|---------|---------|
| `*` | All actions |
| `update*` | All update actions |
| `create*` | All create actions |

### 2.9 How It All Connects

Here's how all the pieces work together:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAUNCHDARKLY RBAC HIERARCHY                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ACCOUNT                                                                │
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
│                           │            │          │            │    ││
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
│                           │                                     │   ││
│                           │  proj/mobile ──► env/prod ──► flag  │   ││
│                           │  proj/web ────► env/test ──► flag   │   ││
│                           │                                     │   ││
│                           └─────────────────────────────────────┘   ││
│                                                                      ││
└──────────────────────────────────────────────────────────────────────┘│
```

**The Flow:**

1. **Member** joins the account
2. Member is assigned to **Teams** (and/or given direct roles)
3. Teams have **Custom Roles** (or built-in roles)
4. Custom Roles contain **Policies**
5. Policies define **Actions** allowed on **Resources**
6. When member tries an action, LaunchDarkly evaluates all applicable policies

---

## 3. Core Concepts

### 3.1 Projects

A **Project** is the top-level container in LaunchDarkly, typically representing:
- A product (e.g., "Mobile App", "Web Platform")
- A team boundary (e.g., "Platform Team", "Growth Team")
- A business unit

```
LaunchDarkly Account
├── Project: mobile-app
│   ├── Flags, Segments, Metrics...
│   └── Environments: dev, staging, prod
├── Project: web-platform
│   └── Environments: dev, staging, prod
└── Project: internal-tools
    └── Environments: dev, prod
```

**Key:** Projects have a unique `key` (e.g., `mobile-app`) used in API calls.

### 3.2 Environments

An **Environment** represents a deployment stage within a project:

| Environment | Purpose | Typical Access |
|-------------|---------|----------------|
| `development` | Local/dev testing | All developers |
| `test` | QA testing | QA team |
| `staging` | Pre-production validation | Limited team |
| `production` | Live users | Restricted (approvals required) |

**Important:** Each environment has its own:
- Flag targeting rules
- SDK keys
- User data

### 3.3 Environment Groups

Instead of managing permissions per individual environment, you can group them:

| Group Key | Environments Included | Characteristics |
|-----------|----------------------|-----------------|
| `non-critical` | development, test, staging | No approvals needed, safe to experiment |
| `critical` | production | Requires approvals, impacts real users |

**Why use groups?**
- Simpler permission management
- One role covers multiple environments
- Easy to add new environments to existing groups

### 3.4 Teams

A **Team** represents a group of users with similar responsibilities:

| Team | Description | Example Members |
|------|-------------|-----------------|
| Developers | Build features | Engineers |
| Senior Developers | Lead engineers with more access | Tech leads |
| QA | Test and validate | QA engineers |
| Product Managers | Define requirements, view metrics | PMs |
| Release Managers | Deploy to production | Release engineers |
| SRE | Maintain reliability | Site reliability engineers |

### 3.5 Custom Roles

A **Custom Role** is a named collection of permissions. Each role defines:
- What actions are allowed
- On which resources (projects, environments)
- Under what conditions

Example role: `developer-non-critical`
- Can update targeting in non-critical environments
- Cannot touch production
- Can create flags but not archive them

### 3.6 Permissions

A **Permission** is a specific action that can be allowed or denied:

```
Permission = Action + Resource + (Optional) Conditions
```

Examples:
- `createFlag` on `project/mobile-app`
- `updateTargeting` on `project/mobile-app/environment/production`
- `deleteFlag` on `project/*` (all projects)

---

## 4. Permission Scopes

### 4.1 Project-Level Permissions

These permissions affect **ALL environments** within a project simultaneously.

| Permission | Description | Use Case |
|------------|-------------|----------|
| **Create Flags** | Create new feature flags | Developer adds `show-new-checkout` flag |
| **Update Flags** | Edit flag metadata (name, description, tags) | PM renames flag for clarity |
| **Archive Flags** | Remove flags from the system | Cleanup after feature is fully rolled out |
| **Update Client Side Availability** | Control if flag is exposed to browser/mobile SDKs | Security: hide sensitive flags from frontend |
| **Manage Metrics** | Define success metrics for experiments | Data team sets up conversion metrics |
| **Manage Release Pipelines** | Configure automated rollout sequences | Set up dev → staging → prod pipeline |
| **View Project** | Read-only access to project | Stakeholder observation |

#### When to Use Project-Level Permissions

Use project-level permissions when the action:
- Creates or deletes a resource (flags exist across all envs)
- Changes structural/metadata aspects
- Is environment-agnostic

### 4.2 Environment-Level Permissions

These permissions are **scoped to specific environments** or environment groups.

| Permission | Description | Use Case |
|------------|-------------|----------|
| **Update Targeting** | Modify flag targeting rules | Turn flag on/off for specific users |
| **Review Changes** | Review pending changes in approval workflow | See what changes are waiting |
| **Apply Changes** | Approve/apply pending changes | Final approval for production changes |
| **Manage Segments** | Create and manage user segments | Define "beta-users" segment |
| **Manage Experiments** | Run A/B tests and experiments | Test new feature variations |
| **View SDK Key** | View the SDK key for the environment | Developers need this for integration |

#### When to Use Environment-Level Permissions

Use environment-level permissions when:
- The action affects flag behavior (targeting, rules)
- Different environments need different access levels
- Production needs stricter controls than development

### 4.3 Scope Comparison

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Permission Scope Visualization                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PROJECT: mobile-app                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PROJECT-LEVEL PERMISSIONS                                   │   │
│  │  (Apply to entire project)                                   │   │
│  │                                                              │   │
│  │  • Create Flags    • Archive Flags    • View Project        │   │
│  │  • Update Flags    • Manage Metrics   • Manage Pipelines    │   │
│  │  • Update Client Side Availability                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │ ENV: development │ │ ENV: staging     │ │ ENV: production  │   │
│  │ (non-critical)   │ │ (non-critical)   │ │ (critical)       │   │
│  │                  │ │                  │ │                  │   │
│  │ • Update Target  │ │ • Update Target  │ │ • Update Target  │   │
│  │ • Manage Segment │ │ • Manage Segment │ │ • Review Changes │   │
│  │ • Experiments    │ │ • Experiments    │ │ • Apply Changes  │   │
│  │ • View SDK Key   │ │ • View SDK Key   │ │ • Manage Segment │   │
│  │                  │ │                  │ │                  │   │
│  │ [Open Access]    │ │ [Limited Access] │ │ [Restricted]     │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. AI Configs Permissions

> **Added:** December 2024 (project-level) / June 2025 (environment-level)

AI Configs is a newer LaunchDarkly feature for managing Large Language Models (LLMs). This section covers the RBAC permissions specific to AI Configs.

### 5.1 What are AI Configs?

**AI Configs** is a LaunchDarkly resource for managing large language models in generative AI applications.

> *"An AI Config is a single resource that you create in LaunchDarkly to control how your application uses large language models."*
> — [LaunchDarkly Documentation](https://launchdarkly.com/docs/home/ai-configs/)

**Key Capabilities:**

| Capability | Description |
|------------|-------------|
| Runtime Updates | Update model details without code deployment |
| Gradual Rollouts | Gradually roll out new model versions and providers |
| Experimentation | Run experiments comparing variations (cost, latency, satisfaction) |
| Safety Filters | Apply targeted safety filters by user segment, geography, or context |
| Evaluation | Evaluate outputs using judges and online evaluations |

**Two Operational Modes:**

| Mode | Description |
|------|-------------|
| **Completion Mode** | Uses messages and roles for single-step responses |
| **Agent Mode** | Uses instructions for multi-step workflows |

### 5.2 AI Config Actions

AI Configs have both project-level and environment-level actions.

#### Project-Level Actions

| Action | Description | Added |
|--------|-------------|-------|
| `createAIConfig` | Create a new AI Config | Dec 2024 |
| `updateAIConfig` | Update AI Config settings and properties | Dec 2024 |
| `deleteAIConfig` | Delete an AI Config | Dec 2024 |
| `updateAIConfigVariation` | Update an AI Config variation | Dec 2024 |
| `deleteAIConfigVariation` | Delete an AI Config variation | Dec 2024 |

#### Environment-Level Actions

| Action | Description | Added |
|--------|-------------|-------|
| `updateAIConfigTargeting` | Update AI Config targeting rules in an environment | Jun 2025 |

#### Approval Workflow Actions (for AI Configs)

| Action | Description |
|--------|-------------|
| `createApprovalRequest` | Create an approval request for AI Config changes |
| `reviewApprovalRequest` | Review a pending approval request |
| `applyApprovalRequest` | Apply approved changes |
| `updateApprovalRequest` | Update an existing approval request |
| `deleteApprovalRequest` | Delete an approval request |

### 5.3 AI Config Resource Syntax

AI Configs follow the standard LaunchDarkly resource syntax but use the `aiconfig` resource type.

**Project-Level AI Configs:**

```
proj/*:aiconfig/*                           # All AI Configs in all projects
proj/mobile-app:aiconfig/*                  # All AI Configs in mobile-app project
proj/mobile-app:aiconfig/my-llm-config      # Specific AI Config
```

**Environment-Level AI Configs:**

```
proj/*:env/*:aiconfig/*                              # All AI Configs in all environments
proj/mobile-app:env/production:aiconfig/*            # All AI Configs in production
proj/mobile-app:env/production:aiconfig/my-llm       # Specific AI Config in production
```

**Example Policy for AI Configs:**

```json
[
  {
    "effect": "allow",
    "actions": ["createAIConfig", "updateAIConfig"],
    "resources": ["proj/mobile-app:aiconfig/*"]
  },
  {
    "effect": "allow",
    "actions": ["updateAIConfigTargeting"],
    "resources": ["proj/mobile-app:env/development:aiconfig/*"]
  },
  {
    "effect": "deny",
    "actions": ["deleteAIConfig"],
    "resources": ["proj/*:aiconfig/*"]
  }
]
```

### 5.4 Default Access for AI Configs

The following roles have AI Config permissions by default:

| Role Type | Roles |
|-----------|-------|
| **Project Roles** | Project Admin, Maintainer, Developer |
| **Base Roles** | Admin, Owner |

**Note:** AI Configs is an add-on feature. Contact your LaunchDarkly account team for access.

---

## 6. Common Scenarios & Flows

### 6.1 Developer Creating a Feature Flag

**Scenario:** A developer wants to add a new feature behind a flag.

```
Step 1: Create Flag (Project-Level)
├── Permission needed: "Create Flags"
├── Action: Creates flag "new-dashboard"
└── Result: Flag appears in ALL environments (OFF by default)

Step 2: Enable in Development (Environment-Level)
├── Permission needed: "Update Targeting" on development
├── Action: Turn flag ON for themselves
└── Result: Can test locally

Step 3: Request QA Testing
├── Developer cannot enable in staging (no permission)
└── QA team enables flag in staging environment

Step 4: Production Release
├── Developer cannot touch production
├── Release Manager reviews and applies changes
└── Flag goes live
```

### 6.2 QA Testing a Flag

**Scenario:** QA needs to test a feature flag in the test environment.

```
Permissions QA typically has:
├── Project-Level: View Project (read-only)
├── Environment: test
│   ├── Update Targeting ✓
│   ├── Manage Segments ✓
│   └── View SDK Key ✓
└── Environment: production
    └── (No permissions - cannot affect prod)
```

### 6.3 Release Manager Deploying to Production

**Scenario:** A feature is ready for production rollout.

```
Permissions Release Manager has:
├── Project-Level:
│   ├── Update Flags ✓ (metadata)
│   └── Manage Release Pipelines ✓
├── Environment: critical (production)
│   ├── Review Changes ✓
│   ├── Apply Changes ✓
│   └── Update Targeting ✓
└── Cannot: Create Flags, Archive Flags (developers do this)
```

### 6.4 Read-Only Stakeholder Access

**Scenario:** A PM or executive needs to view flag status without making changes.

```
Permissions for Read-Only:
├── Project-Level:
│   └── View Project ✓
├── All Environments:
│   └── (No write permissions)
└── Can see: Flag status, metrics, experiments
    Cannot: Make any changes
```

---

## 7. Designing Your RBAC Matrix

### 7.1 Step 1: Identify Teams/Personas

List all distinct roles in your organization that interact with LaunchDarkly:

| Team Key | Name | Description |
|----------|------|-------------|
| `dev` | Developers | Build features, create flags |
| `senior-dev` | Senior Developers | More access, can archive |
| `qa` | QA Engineers | Test in non-prod environments |
| `pm` | Product Managers | View metrics, some flag updates |
| `release` | Release Managers | Production deployments |
| `sre` | SRE | Reliability, segments |
| `admin` | Administrators | Full access |

### 7.2 Step 2: Define Environment Groups

Group your environments by criticality:

| Group Key | Requires Approvals | Critical | Environments |
|-----------|-------------------|----------|--------------|
| `non-critical` | No | No | development, test, staging |
| `critical` | Yes | Yes | production |

### 7.3 Step 3: Assign Project Permissions

Create the project-level permission matrix:

| Team | Create Flags | Update Flags | Archive Flags | Client Side | Metrics | Pipelines | View |
|------|-------------|--------------|---------------|-------------|---------|-----------|------|
| Developers | ✓ | ✓ | | | ✓ | | ✓ |
| Senior Dev | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| QA | | | | | | | ✓ |
| PM | | ✓ | | | ✓ | | ✓ |
| Release | | ✓ | | ✓ | ✓ | ✓ | ✓ |
| SRE | | | | | ✓ | | ✓ |
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### 7.4 Step 4: Assign Environment Permissions

Create the environment-level permission matrix:

| Team | Environment | Targeting | Review | Apply | Segments | Experiments | SDK Key |
|------|-------------|-----------|--------|-------|----------|-------------|---------|
| Developers | non-critical | ✓ | ✓ | | | ✓ | ✓ |
| Developers | critical | | ✓ | | | | |
| Senior Dev | non-critical | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Senior Dev | critical | ✓ | ✓ | | ✓ | ✓ | |
| QA | non-critical | ✓ | ✓ | | | ✓ | ✓ |
| Release | critical | ✓ | ✓ | ✓ | | | ✓ |
| SRE | critical | | ✓ | | ✓ | | ✓ |
| Admin | * | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 8. Best Practices

### Principle of Least Privilege
> Grant only the minimum permissions required for a role to function.

**Do:** Give developers access to create flags and update in dev
**Don't:** Give everyone admin access "just in case"

### Separate Production Access
> Production should have stricter controls than other environments.

**Do:** Require approvals for production changes
**Don't:** Let the same people who write code also deploy to production

### Use Environment Groups
> Group environments by criticality, not individual environments.

**Do:** Use "critical" and "non-critical" groups
**Don't:** Create separate roles for dev, test, staging, prod individually

### Regular Audits
> Review permissions periodically.

**Do:** Quarterly review of who has what access
**Don't:** Set and forget - roles accumulate over time

### Document Your Decisions
> Record why certain roles have certain permissions.

**Do:** Keep this document updated with your RBAC rationale
**Don't:** Rely on tribal knowledge

---

## 9. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Account** | The top-level container in LaunchDarkly; represents your organization |
| **Action** | A specific operation that can be performed on a resource (e.g., `createFlag`, `updateTargets`) |
| **AI Config** | A LaunchDarkly resource for managing LLM configurations in generative AI applications (added Dec 2024) |
| **Built-in Role** | Pre-defined roles provided by LaunchDarkly: Reader, Writer, Admin, Owner |
| **Custom Role** | A user-defined role with specific permissions defined by policies |
| **Effect** | The result of a policy statement: `allow` or `deny` |
| **Environment** | A deployment stage (dev, staging, prod) within a project |
| **Environment Group** | A category of environments (critical, non-critical) for permission scoping |
| **Feature Flag** | A toggle that controls feature availability without code deployment |
| **Member** | An individual user with access to a LaunchDarkly account |
| **Permission** | The combination of an action allowed on a resource |
| **Policy** | A JSON document containing statements that define allowed/denied actions on resources |
| **Policy Statement** | A single rule within a policy: effect + actions + resources |
| **Project** | Top-level container for flags and environments, typically representing a product |
| **RBAC** | Role-Based Access Control - security model based on roles |
| **Resource** | Something you can control access to (project, environment, flag, segment, etc.) |
| **Resource Specifier** | Syntax for identifying resources in policies (e.g., `proj/mobile-app:env/prod:flag/*`) |
| **Segment** | A reusable group of users for targeting |
| **Targeting** | Rules that determine which users see which flag variation |
| **Team** | A group of members who share common roles and permissions |
| **Wildcard** | The `*` character used to match multiple resources or actions |

### B. Permission Reference Table

#### Project-Level Permissions

| Permission Key | Display Name | Description | Impact |
|---------------|--------------|-------------|--------|
| `createFlag` | Create Flags | Create new feature flags | All environments |
| `updateFlag` | Update Flags | Edit flag metadata | All environments |
| `deleteFlag` | Archive Flags | Archive/delete flags | All environments |
| `updateClientSideAvailability` | Client Side Availability | Control SDK exposure | All environments |
| `createMetric` | Manage Metrics | Create/edit metrics | All environments |
| `updateReleasePipeline` | Manage Pipelines | Configure release pipelines | All environments |
| `viewProject` | View Project | Read-only project access | All environments |
| `createAIConfig` | Create AI Configs | Create new AI Configs for LLM management | All environments |
| `updateAIConfig` | Update AI Configs | Update AI Config settings and variations | All environments |
| `deleteAIConfig` | Delete AI Configs | Delete AI Configs | All environments |

#### Environment-Level Permissions

| Permission Key | Display Name | Description | Impact |
|---------------|--------------|-------------|--------|
| `updateTargeting` | Update Targeting | Modify flag targeting rules | Specific environment |
| `reviewChanges` | Review Changes | View pending approvals | Specific environment |
| `applyChanges` | Apply Changes | Approve/apply changes | Specific environment |
| `createSegment` | Manage Segments | Create/edit segments | Specific environment |
| `createExperiment` | Manage Experiments | Run A/B tests | Specific environment |
| `viewSdkKey` | View SDK Key | See SDK credentials | Specific environment |
| `updateAIConfigTargeting` | AI Config Targeting | Update AI Config targeting rules | Specific environment |

### C. Example RBAC Configurations

#### Small Team (5-10 people)

```
Teams:
├── developers (everyone)
└── admin (1-2 leads)

Environments:
├── non-critical: dev, staging
└── critical: production

Approach: Simple two-tier access
```

#### Medium Team (10-50 people)

```
Teams:
├── developers
├── senior-developers
├── qa
├── product
└── admin

Environments:
├── non-critical: dev, test, staging
└── critical: production

Approach: Role-based with production restrictions
```

#### Enterprise (50+ people)

```
Teams:
├── developers (by squad)
├── senior-developers
├── qa
├── product-managers
├── release-managers
├── sre
├── security
└── admin

Environments:
├── development: dev
├── testing: test, qa
├── pre-production: staging, uat
└── production: prod, prod-eu, prod-asia

Approach: Fine-grained with approval workflows
```

### D. Official LaunchDarkly Documentation Links

| Topic | URL |
|-------|-----|
| **Role Concepts** | [launchdarkly.com/docs/home/account/roles/role-concepts](https://launchdarkly.com/docs/home/account/roles/role-concepts) |
| **Building Teams** | [launchdarkly.com/docs/guides/teams-roles/teams](https://launchdarkly.com/docs/guides/teams-roles/teams) |
| **Creating Custom Roles** | [launchdarkly.com/docs/guides/teams-roles/custom-roles](https://launchdarkly.com/docs/guides/teams-roles/custom-roles) |
| **Using Policies** | [launchdarkly.com/docs/home/account/roles/role-policies](https://launchdarkly.com/docs/home/account/roles/role-policies) |
| **Using Resources** | [launchdarkly.com/docs/home/account/roles/role-resources](https://launchdarkly.com/docs/home/account/roles/role-resources) |
| **Using Actions** | [launchdarkly.com/docs/home/account/roles/role-actions](https://launchdarkly.com/docs/home/account/roles/role-actions) |
| **Managing Members** | [launchdarkly.com/docs/home/account/manage-members](https://launchdarkly.com/docs/home/account/manage-members) |
| **Feature Flags API** | [launchdarkly.com/docs/api/feature-flags](https://launchdarkly.com/docs/api/feature-flags) |

---

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Last Updated** | 2024 |
| **Author** | RBAC Builder Project |
| **Related Files** | `RBAC_BUILDER_DESIGN.md`, `app.py` |

---

*This document is part of the RBAC Builder for LaunchDarkly project.*
