# Phase 13: Design Document — Client Delivery Package

**Status:** 📋 Design Complete — Ready for Implementation
**Related:** [README](./README.md) | [PYTHON_CONCEPTS](./PYTHON_CONCEPTS.md)

> Full HLD, DLD, and test cases are in `docs/delivery-package/`. This document is a
> concise design summary for phase tracking consistency.

---

## High-Level Design

### Problem

Clients receive a combined JSON payload but LD has no bulk import endpoint. They must:
1. Manually extract each role/team object
2. Make individual API calls in the right order
3. Handle errors themselves

### Solution

A **self-contained ZIP package** with:
- Pre-split, API-ready JSON files (one per resource)
- A Python deployment script (`deploy.py`) — run once, deploys everything
- A `settings.json` for the API key
- A `README.md` deployment guide

```
{customer}_rbac_deployment.zip
├── README.md         ← deployment guide
├── deploy.py         ← python deploy.py
├── settings.json     ← add API key here
├── requirements.txt
├── rollback.json
├── 01_roles/         ← one JSON per role, numbered for order
│   ├── 01_create-flags.json
│   └── ...
└── 02_teams/         ← one JSON per team
    └── 01_voya-web-dev.json
```

---

## Detailed Low-Level Design

### PackageGenerator (`services/package_generator.py`)

```python
class PackageGenerator:
    def generate_package(self) -> bytes:
        """Returns ZIP as bytes → pass directly to st.download_button"""

    def _build_role_files(self) -> List[Tuple[str, str]]:
        """One (filename, json) per role. Strips to LD API fields only."""

    def _build_team_files(self) -> List[Tuple[str, str]]:
        """One (filename, json) per team."""

    def _build_deploy_script(self) -> str:
        """Returns complete deploy.py as a string."""

    def _build_settings_template(self) -> str:
        """Returns settings.json with API key placeholder."""
```

### Role file — LD API fields only

| Include | Exclude |
|---------|---------|
| key, name, description | metadata |
| base_permissions | deployment_order |
| policy | any rbac-builder internal fields |

### deploy.py behaviour

```
1. Load settings.json
2. Validate API key is not placeholder
3. Load all files from 01_roles/ sorted by filename
4. For each role: check exists → create → log result
5. If ALL roles failed → abort (teams would fail too)
6. Load all files from 02_teams/ sorted by filename
7. For each team: check exists → create → log result
8. Write rollback.json with created keys
9. Print summary
```

### HTTP status handling in deploy.py

| Status | Action |
|--------|--------|
| 201 | ✅ Created — log success |
| 409 | ⚠️ Already exists — skip, continue |
| 429 | ⏳ Rate limited — wait 1s, retry once |
| 401 | ❌ Bad API key — abort immediately |
| 4xx/5xx | ❌ Log error — continue to next resource |

---

## UI Change

**In `ui/deploy_tab.py`** — add third download button:

```
[ 📥 Download LD Payloads ]  [ 📄 Deployment Guide ]  [ 📦 Deployment Package (ZIP) ]
```

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/package_generator.py` | CREATE |
| `tests/test_package_generator.py` | CREATE |
| `services/__init__.py` | ADD `PackageGenerator` export |
| `ui/deploy_tab.py` | ADD ZIP download button |

---

## Full Documentation

- [HLD](../../delivery-package/HLD.md) — architecture, package structure, design decisions
- [DLD](../../delivery-package/DLD.md) — full class design, deploy.py structure, file formats
- [Pseudo Logic & Tests](../../delivery-package/PSEUDOLOGIC_AND_TESTS.md) — 20 test cases
