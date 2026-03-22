# Phase 16: Terraform & HCL Concepts

A complete guide to Terraform concepts used in this phase — written for someone new to Terraform.
By the end of this document you will understand exactly what we are generating and why each part exists.

---

## Table of Contents

1. [What is Terraform?](#1-what-is-terraform)
2. [What is HCL? (Terraform's Language)](#2-what-is-hcl-terraforms-language)
3. [The Three Core Files We Generate](#3-the-three-core-files-we-generate)
4. [Providers — Connecting to LaunchDarkly](#4-providers--connecting-to-launchdarkly)
5. [Variables — Keeping Secrets Safe](#5-variables--keeping-secrets-safe)
6. [Resources — Creating Things in LD](#6-resources--creating-things-in-ld)
7. [Resource References — How Teams Know About Roles](#7-resource-references--how-teams-know-about-roles)
8. [Role Attributes in Terraform](#8-role-attributes-in-terraform)
9. [The lifecycle Block](#9-the-lifecycle-block)
10. [Modules vs Inline Resources](#10-modules-vs-inline-resources)
11. [The ${ Escaping Problem](#11-the--escaping-problem)
12. [How terraform init / plan / apply Works](#12-how-terraform-init--plan--apply-works)
13. [Complete Worked Example](#13-complete-worked-example)
14. [Quick Reference Card](#quick-reference-card)

---

## 1. What is Terraform?

**Terraform** is a tool for managing infrastructure as code (IaC). Instead of clicking buttons in a UI to create cloud resources, you write a text file describing what you want, and Terraform creates it.

```
YOU WRITE:                         TERRAFORM CREATES:
──────────────────────────────     ──────────────────────────────
resource "launchdarkly_team"       → LaunchDarkly team "Developers"
resource "launchdarkly_team"       → LaunchDarkly team "SRE"
resource "launchdarkly_custom_role"→ LaunchDarkly role "update-targeting"
```

### Why use Terraform instead of the LD UI?

| LD UI | Terraform |
|-------|-----------|
| Click buttons | Write code |
| Changes not tracked | Changes in git history |
| Easy to forget what you did | Everything documented in `.tf` files |
| Hard to reproduce | Run `terraform apply` again on a new account |
| One person at a time | Team reviews config in pull requests |

### The workflow

```
1. Write .tf files        → describes desired state
2. terraform init         → downloads the LaunchDarkly provider plugin
3. terraform plan         → shows what WOULD be created/changed (no changes yet)
4. terraform apply        → actually creates the resources
5. terraform destroy      → deletes everything (careful!)
```

---

## 2. What is HCL? (Terraform's Language)

**HCL** = HashiCorp Configuration Language. It's the language you write Terraform files in.

### Basic syntax rules

```hcl
# This is a comment

# A block has a type, optional labels, and a body
block_type "label1" "label2" {
  attribute = "value"
  number    = 42
  bool_val  = true
  list_val  = ["item1", "item2"]
}

# Nested blocks
outer_block {
  inner_block {
    key = "value"
  }
}
```

### HCL vs JSON comparison

Our rbac-builder generates JSON like this:
```json
{
  "key": "update-targeting",
  "name": "Update Targeting",
  "base_permissions": "no_access"
}
```

The same thing in HCL looks like:
```hcl
resource "launchdarkly_custom_role" "update_targeting" {
  key              = "update-targeting"
  name             = "Update Targeting"
  base_permissions = "no_access"
}
```

They describe the same thing — HCL is just more readable for humans.

### HCL files use `.tf` extension

All Terraform configuration lives in `.tf` files. Terraform reads ALL `.tf` files in a directory together — so `main.tf`, `providers.tf`, and `variables.tf` are all read as one configuration.

---

## 3. The Three Core Files We Generate

```
voya_terraform/
├── providers.tf   ← WHO to connect to (LaunchDarkly) and HOW
├── variables.tf   ← WHAT inputs the user must provide (API key)
└── main.tf        ← WHAT to create (roles + teams)
```

Think of it like cooking:
- `providers.tf` = the kitchen equipment setup (what tools we have)
- `variables.tf` = the ingredients list (what the user provides)
- `main.tf` = the recipe (what to make with those ingredients)

---

## 4. Providers — Connecting to LaunchDarkly

A **provider** is a plugin that knows how to talk to a specific service. The LaunchDarkly provider knows how to make API calls to create LD roles, teams, flags, etc.

```hcl
# providers.tf

terraform {
  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      #          ↑           ↑
      #          publisher    plugin name
      #          (on registry.terraform.io)

      version = "~> 2.25"
      #          ↑
      #          "~> 2.25" means "2.25 or higher but less than 3.0"
      #          Prevents breaking changes from major version bumps
    }
  }
  required_version = ">= 1.0"   # minimum Terraform CLI version
}

provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
  #              ↑
  #              reads from variables.tf (explained next)
}
```

### What `terraform init` does with this

When the client runs `terraform init`, Terraform reads this file and downloads the LaunchDarkly provider plugin from the Terraform registry. This is a one-time setup step.

---

## 5. Variables — Keeping Secrets Safe

A **variable** is an input that the user provides at runtime. We use it for the API key so it's never hardcoded in the `.tf` files.

```hcl
# variables.tf

variable "launchdarkly_access_token" {
  type        = string
  description = "LaunchDarkly API access token with createRole and createTeam permissions"
  sensitive   = true
  #             ↑
  #             Terraform will never print this value in logs or output
}
```

### How the client provides the value

```bash
# Option 1: Environment variable (recommended)
export TF_VAR_launchdarkly_access_token="api-xxxxxxxxxxxx"
terraform apply

# Option 2: Prompted at runtime
terraform apply
# Enter a value: [types API key, not shown on screen]

# Option 3: terraform.tfvars file (never commit this to git!)
# launchdarkly_access_token = "api-xxxxxxxxxxxx"
```

### Why NOT hardcode the API key in main.tf?

```hcl
# BAD — never do this!
provider "launchdarkly" {
  access_token = "api-xxxxxxxxxxxx"   # ← anyone who sees this file has full LD access!
}

# GOOD — reference a variable
provider "launchdarkly" {
  access_token = var.launchdarkly_access_token   # ← value provided at runtime
}
```

---

## 6. Resources — Creating Things in LD

A **resource** represents one thing that Terraform will create, manage, or destroy. Each resource has a **type** and a **name**.

```hcl
resource "launchdarkly_custom_role" "create_flags" {
#         ↑                          ↑
#         resource type              local name (used only within this Terraform config)
#         (LaunchDarkly provider)
```

### The two-part name

```hcl
resource "launchdarkly_custom_role" "create_flags" { ... }
#                                    ^^^^^^^^^^^^
#                                    This is NOT the LD role key.
#                                    It's Terraform's internal reference name.
#                                    Must be valid HCL identifier (letters, digits, underscores)
#                                    Hyphens NOT allowed → use underscores
```

### `launchdarkly_custom_role` resource

```hcl
resource "launchdarkly_custom_role" "update_targeting" {
  key              = "update-targeting"          # ← LD role key (can have hyphens)
  name             = "Update Targeting"          # ← display name in LD UI
  description      = "Template role for Update Targeting"
  base_permissions = "no_access"                 # ← MUST be "no_access" or "reader"

  policy_statements {                            # ← one block per policy statement
    effect    = "allow"
    actions   = ["updateOn", "updateRules", "updateTargets"]
    resources = ["proj/$${roleAttribute/projects}:env/$${roleAttribute/update-targeting-environments}:flag/*"]
  }

  policy_statements {
    effect    = "allow"
    actions   = ["viewProject"]
    resources = ["proj/$${roleAttribute/projects}"]
  }
}
```

### `launchdarkly_team` resource

```hcl
resource "launchdarkly_team" "voya_web_dev" {
  key         = "voya-web-dev"          # ← LD team key
  name        = "Voya Web: Developer"   # ← display name
  description = "Development team"

  custom_role_keys = [
    launchdarkly_custom_role.create_flags.key,      # ← reference to role resource
    launchdarkly_custom_role.update_targeting.key,  # ← NOT a string literal!
  ]

  role_attributes {                                 # ← one block per role attribute
    key    = "projects"
    values = ["voya-web"]
  }

  role_attributes {
    key    = "update-targeting-environments"
    values = ["production", "staging"]
  }

  lifecycle {
    ignore_changes = [member_ids, maintainers]      # ← explained in section 9
  }
}
```

---

## 7. Resource References — How Teams Know About Roles

This is one of the most important concepts. Teams need to include role keys in `custom_role_keys`. But instead of typing the key as a string, Terraform lets you **reference** the role resource directly.

### String literal (bad — no dependency)

```hcl
custom_role_keys = [
  "create-flags",       # ← just a string — Terraform doesn't know this is a role
  "update-targeting",   # ← Terraform won't guarantee roles exist before teams!
]
```

### Resource reference (good — creates dependency)

```hcl
custom_role_keys = [
  launchdarkly_custom_role.create_flags.key,
  #                        ^^^^^^^^^^^^
  #                        This is the Terraform resource name (underscores)
  #                                               ^^^
  #                                               .key = the actual LD key attribute
  launchdarkly_custom_role.update_targeting.key,
]
```

### Why references matter: the dependency graph

When Terraform sees a reference, it builds a **dependency graph**:

```
launchdarkly_custom_role.create_flags     ←─┐
launchdarkly_custom_role.update_targeting ←─┤─ launchdarkly_team.voya_web_dev
launchdarkly_custom_role.view_project     ←─┘
```

Terraform automatically creates roles BEFORE teams because the team references the roles.
Without references (just strings), Terraform might try to create the team first — which fails because the roles don't exist yet.

### The `.key` attribute

Every `launchdarkly_custom_role` resource has a `.key` attribute that holds the actual LD key string. When Terraform applies:

```
launchdarkly_custom_role.create_flags.key
                                      ↓
Terraform resolves this to:  "create-flags"   (the value of key = "create-flags" in that resource)
```

---

## 8. Role Attributes in Terraform

Role attributes are how teams specify which project/environments they can act on. In Terraform they appear as repeated `role_attributes` blocks on a team resource.

```hcl
resource "launchdarkly_team" "voya_web_dev" {
  # ...

  role_attributes {                              # Block 1 — project scoping
    key    = "projects"
    values = ["voya-web"]
  }

  role_attributes {                              # Block 2 — env scoping for update-targeting
    key    = "update-targeting-environments"
    values = ["production", "staging"]
  }

  role_attributes {                              # Block 3 — env scoping for apply-changes
    key    = "apply-changes-environments"
    values = ["production"]                      # Narrower than update-targeting
  }
}
```

### How they connect to roles

The team's `role_attributes` fill in the `${roleAttribute/...}` placeholders in each role's resource string at runtime in LD:

```
Role resource:   "proj/$${roleAttribute/projects}:env/$${roleAttribute/update-targeting-environments}:flag/*"
Team attribute:  projects = ["voya-web"], update-targeting-environments = ["production", "staging"]

LD resolves to:  "proj/voya-web:env/production:flag/*"
                 "proj/voya-web:env/staging:flag/*"
```

Note: `$${...}` in HCL becomes `${...}` in the actual string sent to LD. More on this in section 11.

---

## 9. The `lifecycle` Block

Every team resource includes this block:

```hcl
lifecycle {
  ignore_changes = [member_ids, maintainers]
}
```

### What it does

`ignore_changes` tells Terraform: "even if these attributes change outside of Terraform, don't try to revert them."

### Why we need it for teams

Members are usually managed by:
- SSO/SCIM (Azure AD, Okta) — automatically adds/removes members
- HR processes — managers add people in the LD UI

If we don't include this, Terraform would try to "fix" the team back to having no members every time you run `terraform apply` — removing everyone!

```
Without ignore_changes:
  Terraform plan shows: "~ member_ids = [...100 members...] → []"
  Terraform apply:      removes all 100 members!  ← catastrophic

With ignore_changes:
  Terraform plan shows: (nothing for member_ids — it's ignored)
  Terraform apply:      leaves members untouched  ← correct
```

---

## 10. Modules vs Inline Resources

This is the key design decision for Phase 16.

### The sa-demo approach: modules

The sa-demo uses pre-built Terraform modules from ps-terraform-private:

```hcl
# sa-demo main.tf
module "project_roles" {
  source = "./roles/flag-lifecycle/per-project"   # ← module source path
  #         ↑ requires this directory to exist with 50+ .tf files
  create_flags = true
  update_flags = true
}
```

**Modules** are reusable packages of Terraform code. Like importing a Python library — the module handles the details.

**Problem:** To use this, you need to bundle the entire `roles/` directory from ps-terraform-private. That's ~50 files the client needs alongside their `main.tf`.

### Our approach: inline resources

We write the `launchdarkly_custom_role` and `launchdarkly_team` resources directly in `main.tf` with no modules:

```hcl
# Our generated main.tf
resource "launchdarkly_custom_role" "create_flags" {
  key              = "create-flags"
  base_permissions = "no_access"
  policy_statements {
    effect    = "allow"
    actions   = ["cloneFlag", "createFlag"]
    resources = ["proj/$${roleAttribute/projects}:env/*:flag/*"]
  }
}
```

**One file. `terraform apply`. Done.**

### When would you use modules instead?

Modules make sense when:
- The client is managing LD configuration **long-term** via Terraform
- They want to add more teams/roles over time using the same patterns
- They have a Terraform-first workflow

For a one-time PS delivery, inline resources are simpler.

---

## 11. The `${` Escaping Problem

This is the trickiest part of generating HCL from Python.

### The conflict

LaunchDarkly role attribute placeholders use `${...}`:
```
proj/${roleAttribute/projects}:env/*:flag/*
```

HCL also uses `${...}` for its own variable interpolation:
```hcl
name = "Hello ${var.customer_name}"   # HCL interpolation
```

**If you put `${roleAttribute/projects}` inside an HCL string, Terraform tries to evaluate it as a variable called `roleAttribute/projects` — which doesn't exist — and fails.**

### The fix: `$${ ` produces literal `${`

In HCL, `$$` is an escape sequence that produces a literal `$`. So `$${` produces `${` without triggering interpolation.

```hcl
# WRONG — Terraform tries to interpolate ${roleAttribute/projects}
resources = ["proj/${roleAttribute/projects}:env/*:flag/*"]
#                   ↑ HCL tries to evaluate this as a variable!

# CORRECT — $$ produces literal $, so ${roleAttribute/projects} passes through unchanged
resources = ["proj/$${roleAttribute/projects}:env/*:flag/*"]
#                   ↑ $$ → $ in output, no interpolation
```

### In Python code

```python
# JSON payload has:
json_resource = "proj/${roleAttribute/projects}:env/*:flag/*"

# For HCL output, escape all ${ occurrences:
hcl_resource = json_resource.replace("${", "$${")
# → "proj/$${roleAttribute/projects}:env/*:flag/*"

# When terraform applies, LD receives:
# "proj/${roleAttribute/projects}:env/*:flag/*"   ← correct!
```

### Why doesn't JSON need escaping?

JSON has no interpolation syntax. `${...}` is just a regular string in JSON — no special meaning. Only HCL needs the escaping.

---

## 12. How `terraform init / plan / apply` Works

### `terraform init`

Downloads the LaunchDarkly provider plugin (~50MB). Only needed once per project (or when provider version changes).

```bash
terraform init

# Output:
# Initializing provider plugins...
# - Finding launchdarkly/launchdarkly versions matching "~> 2.25"...
# - Installing launchdarkly/launchdarkly v2.25.0...
# Terraform has been successfully initialized!
```

### `terraform plan`

Connects to LD, checks what already exists, shows what WOULD change. **No changes are made.**

```bash
terraform plan

# Output:
# Terraform will perform the following actions:
#
#   + launchdarkly_custom_role.create_flags
#       key              = "create-flags"
#       name             = "Create Flags"
#       base_permissions = "no_access"
#
#   + launchdarkly_team.voya_web_dev
#       key  = "voya-web-dev"
#       name = "Voya Web: Developer"
#
# Plan: 10 to add, 0 to change, 0 to destroy.
```

### `terraform apply`

Executes the plan — actually creates/updates/deletes resources in LD.

```bash
terraform apply

# Shows the plan first, then asks:
# Do you want to perform these actions? [yes/no]: yes
#
# launchdarkly_custom_role.create_flags: Creating...
# launchdarkly_custom_role.create_flags: Creation complete after 1s
# launchdarkly_team.voya_web_dev: Creating...
# launchdarkly_team.voya_web_dev: Creation complete after 2s
#
# Apply complete! Resources: 10 added, 0 changed, 0 destroyed.
```

### `terraform.tfstate` — Terraform's memory

After `apply`, Terraform writes a `terraform.tfstate` file that remembers what it created. This is how it knows what to change on subsequent `apply` runs.

```
⚠️ Never delete terraform.tfstate!
   If you lose it, Terraform forgets what it created.
   For production use, store state remotely (Terraform Cloud, S3, etc.)
```

---

## 13. Complete Worked Example

Let's trace through a complete example from rbac-builder session state to running `terraform apply`.

### Input: rbac-builder configuration

```
Customer: Voya
Project:  voya-web
Team:     Developer
  Project perms: Create Flags ✅, View Project ✅
  Env perms:     Update Targeting ✅ → ["production", "staging"]
                 Apply Changes ✅   → ["production"]
```

### Step 1: rbac-builder generates payload (existing functionality)

```json
{
  "custom_roles": [
    {
      "key": "create-flags",
      "base_permissions": "no_access",
      "policy": [{"effect": "allow", "actions": ["cloneFlag", "createFlag"],
                  "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"]}]
    },
    {
      "key": "update-targeting",
      "policy": [{"effect": "allow", "actions": ["updateOn", "..."],
                  "resources": ["proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"]}]
    }
  ],
  "teams": [{
    "key": "voya-web-dev",
    "customRoleKeys": ["create-flags", "update-targeting", "apply-changes", "view-project"],
    "roleAttributes": [
      {"key": "projects", "values": ["voya-web"]},
      {"key": "update-targeting-environments", "values": ["production", "staging"]},
      {"key": "apply-changes-environments", "values": ["production"]}
    ]
  }]
}
```

### Step 2: TerraformGenerator converts to HCL

**providers.tf:**
```hcl
terraform {
  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      version = "~> 2.25"
    }
  }
}

provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
}
```

**variables.tf:**
```hcl
variable "launchdarkly_access_token" {
  type      = string
  sensitive = true
}
```

**main.tf:**
```hcl
/**
 * Generated by RBAC Builder
 * Customer: Voya | Project: voya-web
 */

# ── Custom Roles ──────────────────────────────────────────────────────────────

resource "launchdarkly_custom_role" "create_flags" {
  key              = "create-flags"
  name             = "Create Flags"
  base_permissions = "no_access"

  policy_statements {
    effect    = "allow"
    actions   = ["cloneFlag", "createFlag"]
    resources = ["proj/$${roleAttribute/projects}:env/*:flag/*"]
    #                  ↑↑ $$ → $ in output → LD sees ${roleAttribute/projects}
  }

  policy_statements {
    effect    = "allow"
    actions   = ["viewProject"]
    resources = ["proj/$${roleAttribute/projects}"]
  }
}

resource "launchdarkly_custom_role" "update_targeting" {
  key              = "update-targeting"
  name             = "Update Targeting"
  base_permissions = "no_access"

  policy_statements {
    effect    = "allow"
    actions   = ["updateOn", "updateRules", "updateTargets"]
    resources = ["proj/$${roleAttribute/projects}:env/$${roleAttribute/update-targeting-environments}:flag/*"]
  }

  policy_statements {
    effect    = "allow"
    actions   = ["viewProject"]
    resources = ["proj/$${roleAttribute/projects}"]
  }
}

# ── Teams ──────────────────────────────────────────────────────────────────────

resource "launchdarkly_team" "voya_web_dev" {
  key         = "voya-web-dev"
  name        = "Voya Web: Developer"
  description = "Development team"

  custom_role_keys = [
    launchdarkly_custom_role.create_flags.key,      # → "create-flags"
    launchdarkly_custom_role.update_targeting.key,  # → "update-targeting"
    launchdarkly_custom_role.apply_changes.key,     # → "apply-changes"
    launchdarkly_custom_role.view_project.key,      # → "view-project"
  ]

  role_attributes {
    key    = "projects"
    values = ["voya-web"]
  }

  role_attributes {
    key    = "update-targeting-environments"
    values = ["production", "staging"]
  }

  role_attributes {
    key    = "apply-changes-environments"
    values = ["production"]
  }

  lifecycle {
    ignore_changes = [member_ids, maintainers]
  }
}
```

### Step 3: Client runs Terraform

```bash
unzip voya_terraform.zip && cd voya_terraform
export TF_VAR_launchdarkly_access_token="api-xxxx"
terraform init    # downloads launchdarkly provider
terraform plan    # shows: 5 to add (4 roles + 1 team)
terraform apply   # creates everything in LD
```

---

## Quick Reference Card

```
TERRAFORM CONCEPTS
──────────────────
provider       = plugin that talks to a service (LaunchDarkly)
resource       = one thing to create (role, team)
variable       = input the user provides at runtime
module         = reusable package of Terraform code (we don't use these)
lifecycle      = special instructions (ignore_changes = [member_ids])

LAUNCHDARKLY RESOURCES
──────────────────────
launchdarkly_custom_role  → LD custom role
launchdarkly_team         → LD team

RESOURCE NAME RULES
───────────────────
"create-flags"  → resource name "create_flags"  (hyphens → underscores)
"voya-web-dev"  → resource name "voya_web_dev"

REFERENCING RESOURCES
─────────────────────
launchdarkly_custom_role.create_flags.key
       ↑                  ↑            ↑
  resource type      resource name   attribute

THE ${} ESCAPING RULE
─────────────────────
JSON:  "proj/${roleAttribute/projects}..."      (no escaping needed)
HCL:   "proj/$${roleAttribute/projects}..."     ($ doubled to escape)
LD:    "proj/${roleAttribute/projects}..."      (Terraform removes the extra $)

COMMANDS
────────
terraform init     → download providers (once)
terraform plan     → preview changes (safe, no changes made)
terraform apply    → create/update resources
terraform destroy  → delete everything (careful!)
```
