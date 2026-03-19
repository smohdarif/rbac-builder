# Role Attributes Explained

> A beginner-friendly guide to understanding LaunchDarkly Role Attributes

## Think of it Like a Movie Ticket

### Without Role Attributes (Hardcoded)

Imagine a movie theater that prints **separate tickets for each movie**:

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ TICKET              │  │ TICKET              │  │ TICKET              │
│ Movie: Avatar       │  │ Movie: Titanic      │  │ Movie: Inception    │
│ Access: Screen 1    │  │ Access: Screen 2    │  │ Access: Screen 3    │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

**Problem:** If you have 100 movies, you need 100 different ticket types!

---

### With Role Attributes (Dynamic)

Instead, print **ONE ticket template** with a blank space:

```
┌─────────────────────────┐
│ TICKET                  │
│ Movie: ____________     │  ← Fill in at entry time
│ Access: Screen for      │
│         that movie      │
└─────────────────────────┘
```

When someone buys a ticket, you write the movie name. **Same ticket design, different movies.**

---

## LaunchDarkly Example

### Without Role Attributes (Hardcoded Approach)

We create **separate roles for each project**:

```
Role: "voya-dev-targeting"
  Can access: proj/voya:env/*:flag/*

Role: "mobile-dev-targeting"
  Can access: proj/mobile-app:env/*:flag/*

Role: "website-dev-targeting"
  Can access: proj/website:env/*:flag/*
```

**10 projects = 10 separate roles** (just for targeting!)

---

### With Role Attributes (Dynamic Approach)

Create **ONE role** with a placeholder:

```
Role: "dev-targeting"
  Can access: proj/{____}:env/*:flag/*
                    ↑
              Fill in later!
```

The placeholder is written as: `${roleAttribute/projects}`

```
Role: "dev-targeting"
  Can access: proj/${roleAttribute/projects}:env/*:flag/*
```

---

## How Teams Fill In The Blank

When you assign the role to a team, you specify **what goes in the blank**:

### Team A: Voya Developers
```
Team: "Voya Developers"
  Roles: dev-targeting
  Role Attributes:
    projects = "voya"         ← Fills the blank with "voya"

  Result: Can access proj/voya:env/*:flag/*
```

### Team B: Mobile Developers
```
Team: "Mobile Developers"
  Roles: dev-targeting        ← SAME role!
  Role Attributes:
    projects = "mobile-app"   ← Fills the blank with "mobile-app"

  Result: Can access proj/mobile-app:env/*:flag/*
```

---

## Visual Comparison

### Hardcoded Approach (Without Role Attributes)

```
                    ┌──────────────────────┐
                    │  voya-dev-targeting  │──→ Voya Team
                    └──────────────────────┘

                    ┌──────────────────────┐
                    │ mobile-dev-targeting │──→ Mobile Team
                    └──────────────────────┘

                    ┌──────────────────────┐
                    │website-dev-targeting │──→ Website Team
                    └──────────────────────┘

3 roles for 3 projects (just for targeting!)
Total: 3 projects × 10 permission types = 30 roles!
```

### Role Attributes Approach (Dynamic)

```
                                         ┌────────────────┐
                                    ┌───→│ voya-dev       │ projects = ["voya"]
                                    │    └────────────────┘
┌──────────────────┐                │
│  dev-targeting   │────────────────┼───→┌────────────────┐
│  (template)      │                │    │ mobile-dev     │ projects = ["mobile-app"]
└──────────────────┘                │    └────────────────┘
                                    │
                                    └───→┌────────────────┐
                                         │ website-dev    │ projects = ["website"]
                                         └────────────────┘

1 role serves ALL projects!
Each team has ONE project (project-prefixed key for isolation)
Total: 10 permission types = 10 roles (regardless of project count)
```

---

## Real Code Examples

### The Role (Template)

```json
{
  "key": "dev-targeting",
  "name": "Developer Targeting",
  "policy": [{
    "effect": "allow",
    "actions": ["updateOn", "updateRules", "updateTargets"],
    "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"]
  }]
}
```

Note: The `${roleAttribute/projects}` is a placeholder that gets filled in per-team.

---

### Team A: Voya Developers

```json
{
  "key": "voya-dev",
  "name": "Voya: Developer",
  "customRoleKeys": ["dev-targeting"],
  "roleAttributes": {
    "projects": ["voya"]
  }
}
```

**Result:** Team can access `proj/voya:env/*:flag/*`

Team key format: `{project}-{team}` (e.g., `voya-dev`)

---

### Team B: Mobile Developers

```json
{
  "key": "mobile-dev",
  "name": "Mobile App: Developer",
  "customRoleKeys": ["dev-targeting"],
  "roleAttributes": {
    "projects": ["mobile-app"]
  }
}
```

**Result:** Team can access `proj/mobile-app:env/*:flag/*`

---

### Important: One Project Per Team

Following the ps-terraform-private pattern:
- Each team has **ONE project** in roleAttributes
- Team keys are **prefixed with project name** (e.g., `voya-dev`, not `dev`)
- Team names include project prefix (e.g., `Voya: Developer`)

```json
{
  "key": "voya-dev",
  "name": "Voya: Developer",
  "customRoleKeys": ["dev-targeting"],
  "roleAttributes": {
    "projects": ["voya"]
  }
}
```

For users who need access to multiple projects, they should be added to **multiple teams** (one per project). For example, a user needing access to both Voya and Mobile projects would be added to both `voya-dev` and `mobile-dev` teams.

---

## Multiple Role Attributes

You can have multiple placeholders for different scoping:

### Role with Multiple Placeholders

```json
{
  "key": "dev-env-targeting",
  "name": "Developer Environment Targeting",
  "policy": [{
    "effect": "allow",
    "actions": ["updateOn", "updateRules"],
    "resources": ["proj/${roleAttribute/projects}:env/${roleAttribute/environments}:flag/*"]
  }]
}
```

### Team with Multiple Attributes

```json
{
  "key": "voya-dev",
  "name": "Voya: Developer",
  "customRoleKeys": ["dev-env-targeting"],
  "roleAttributes": {
    "projects": ["voya"],
    "environments": ["test", "staging"]
  }
}
```

**Result:** Team can access:
- `proj/voya:env/test:flag/*`
- `proj/voya:env/staging:flag/*`

But NOT `proj/voya:env/production:flag/*` (production not in their list)

---

## Common Role Attribute Patterns

| Attribute Name | Purpose | Example Values |
|----------------|---------|----------------|
| `projects` | Which project team can access | `["voya"]` (ONE project per team) |
| `environments` | Which environments team can access | `["test", "staging"]` |
| `update-targeting-environments` | Environments where targeting is allowed | `["test"]` |
| `apply-changes-environments` | Environments where applying changes is allowed | `["production"]` |

---

## Summary Table

| Concept | Analogy | LaunchDarkly |
|---------|---------|--------------|
| **Role** | Ticket template | Permission definition with placeholders |
| **Role Attribute Placeholder** | Blank space on ticket | `${roleAttribute/projects}` |
| **Team's roleAttributes** | Writing movie name on ticket | `"projects": ["voya"]` |

---

## Benefits of Role Attributes

| Benefit | Description |
|---------|-------------|
| **Scalability** | Add new projects without creating new roles |
| **Maintainability** | Change a role once, applies to all teams |
| **Flexibility** | Same role can grant different access per team |
| **Reduced Complexity** | Fewer roles to manage |
| **Consistency** | All teams use same role definitions |

---

## When to Use Each Approach

### Use Hardcoded Roles When:
- Single project deployment
- Simple RBAC requirements
- Quick setup needed
- No plans for multi-project expansion

### Use Role Attributes When:
- Multiple projects with similar team structures
- Enterprise deployments
- Need to scale to many projects
- Want centralized role management

---

## Terraform Syntax Note

In Terraform, you must escape the `$` with double `$$`:

```hcl
# In Terraform .tf files
resources = ["proj/$${roleAttribute/projects}:env/*:flag/*"]
#                 ^^
#                 Double $$ required in Terraform!
```

In JSON or API calls, use single `$`:

```json
{
  "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"]
}
```

---

## Related Documentation

- [LaunchDarkly Custom Roles](https://docs.launchdarkly.com/home/account/custom-roles)
- [LaunchDarkly Teams](https://docs.launchdarkly.com/home/account/teams)
- [ps-terraform-private Repository](../../../ps-terraform-private/CLAUDE.md)

---

*Last updated: 2026-03-16*
