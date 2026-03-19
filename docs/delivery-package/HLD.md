# High-Level Design: Client Delivery Package

**Status:** Design — Ready for Implementation
**Goal:** Generate a self-contained ZIP that a client can unzip and run one command to deploy all RBAC resources to LaunchDarkly — no manual steps.

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Solution Overview](#solution-overview)
3. [Package Contents](#package-contents)
4. [Architecture](#architecture)
5. [Data Flow](#data-flow)
6. [Key Design Decisions](#key-design-decisions)

---

## The Problem

Currently the client receives:
- A JSON file with all roles and teams combined
- A Markdown guide explaining how to deploy manually

**What's wrong with this:**
- LD has no bulk import endpoint — each role/team is a separate API call
- Client must manually extract each object and call the API individually
- Error-prone: easy to miss a resource or apply in wrong order
- No feedback on what succeeded or failed

---

## Solution Overview

Generate a **self-contained delivery ZIP** containing:

1. Individual JSON files per resource (pre-formatted for the LD API)
2. A Python deployment script (`deploy.py`) that reads those files and calls the LD API
3. A `settings.json` for the client to fill in their API key
4. A `README.md` with exact steps

Client workflow:
```
1. Unzip the package
2. Open settings.json → add API key
3. Run: python deploy.py
4. Done — all roles and teams created in LD
```

---

## Package Contents

```
{customer}_rbac_deployment/
│
├── README.md                        ← Step-by-step instructions
├── deploy.py                        ← Run this to deploy everything
├── requirements.txt                 ← Just: requests>=2.28.0
│
├── settings.json                    ← Client fills in API key here
│   {
│     "api_key": "YOUR_API_KEY_HERE",
│     "base_url": "https://app.launchdarkly.com",
│     "dry_run": false
│   }
│
├── 01_roles/                        ← Create these FIRST
│   ├── 01_create-flags.json
│   ├── 02_update-flags.json
│   ├── 03_archive-flags.json
│   └── ...  (one file per role, numbered for order)
│
└── 02_teams/                        ← Create these SECOND
    ├── 01_voya-web-dev.json
    └── ...  (one file per team, numbered for order)
```

### Individual role file format (`01_roles/01_create-flags.json`)
```json
{
  "key": "create-flags",
  "name": "Create Flags",
  "description": "Template role for Create Flags",
  "base_permissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": ["cloneFlag", "createFlag"],
      "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"]
    }
  ]
}
```
> **Exactly what `POST /api/v2/roles` expects — no wrapper, no extra fields.**

### Individual team file format (`02_teams/01_voya-web-dev.json`)
```json
{
  "key": "voya-web-dev",
  "name": "Voya Web: Developer",
  "description": "Development team",
  "customRoleKeys": ["create-flags", "update-flags", "..."],
  "roleAttributes": [
    { "key": "projects", "values": ["voya-web"] },
    { "key": "update-targeting-environments", "values": ["production"] }
  ]
}
```
> **Exactly what `POST /api/v2/teams` expects.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   rbac-builder UI                       │
│                                                         │
│   [ Deploy Tab ]                                        │
│   ┌──────────────────────────────────────────────┐     │
│   │  📦 Download Deployment Package (ZIP)        │     │
│   └──────────────────────────────────────────────┘     │
└──────────────────┬──────────────────────────────────────┘
                   │ calls
                   ▼
┌─────────────────────────────────────────────────────────┐
│           services/package_generator.py                 │
│                                                         │
│   PackageGenerator                                      │
│   ├── generate_package(payload, project_key, name)      │
│   │     → bytes (ZIP file)                              │
│   │                                                     │
│   ├── _build_role_files(roles)                          │
│   │     → List[(filename, json_content)]                │
│   │                                                     │
│   ├── _build_team_files(teams)                          │
│   │     → List[(filename, json_content)]                │
│   │                                                     │
│   ├── _build_deploy_script()                            │
│   │     → str (Python script content)                   │
│   │                                                     │
│   ├── _build_settings_template()                        │
│   │     → str (settings.json content)                   │
│   │                                                     │
│   └── _build_readme(payload, project_key)               │
│         → str (Markdown content)                        │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
DeployPayload (from RoleAttributePayloadBuilder)
        │
        ▼
PackageGenerator.generate_package()
        │
        ├─→ For each role in payload.roles:
        │     Strip metadata fields (metadata, deployment_order)
        │     Write to 01_roles/NN_<role-key>.json
        │
        ├─→ For each team in payload.teams:
        │     Write to 02_teams/NN_<team-key>.json
        │
        ├─→ Generate deploy.py (static template)
        ├─→ Generate settings.json template
        ├─→ Generate README.md (from doc_generator)
        │
        └─→ Zip all files → return bytes
                │
                ▼
        st.download_button(data=zip_bytes, filename="..._deployment.zip")
```

---

## Key Design Decisions

### 1. Numbered file prefixes (`01_`, `02_`)
Files are numbered to make the deployment order visually obvious in any file browser. Within roles and teams, numbering follows the original order from the payload.

### 2. `deploy.py` uses only stdlib + `requests`
The script must be runnable by any client without complex setup:
```
pip install requests
python deploy.py
```
No pandas, no streamlit, no internal rbac-builder modules.

### 3. `dry_run` mode in deploy.py
Client can set `"dry_run": true` in `settings.json` to preview what would be created without making any API calls. Prints what would happen.

### 4. Resume-safe deployment
If a resource already exists (HTTP 409), the script logs a warning and continues rather than failing. This means the script is safe to re-run.

### 5. Rollback file
On success, `deploy.py` writes a `rollback.json` listing all created resource keys so the client can undo if needed.

---

## Navigation

- [DLD →](./DLD.md)
- [Pseudo Logic & Test Cases →](./PSEUDOLOGIC_AND_TESTS.md)
