# Phase 13: Client Delivery Package

| Field | Value |
|-------|-------|
| **Phase** | 13 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Goal** | Generate a self-contained ZIP with API-ready JSON files + Python deployment script so clients can deploy RBAC with one command |
| **Depends on** | Phase 3 (Payload Builder), Phase 8 (Deploy UI), doc_generator (Phase 13 pre-work) |

---

## What This Phase Delivers

A **"📦 Download Deployment Package"** button in the Deploy tab that generates a ZIP containing:

```
{customer}_rbac_deployment/
├── README.md              ← deployment guide
├── deploy.py              ← run this: python deploy.py
├── requirements.txt       ← pip install requests
├── settings.json          ← fill in API key here
├── rollback.json          ← written after deployment
├── 01_roles/              ← one JSON per role, numbered
│   ├── 01_create-flags.json
│   └── ...
└── 02_teams/              ← one JSON per team, numbered
    └── 01_voya-web-dev.json
```

**Client workflow:**
```bash
unzip voya_rbac_deployment.zip
cd voya_rbac_deployment

# 1. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 2. Install dependency
pip install requests

# 3. Add your API key to settings.json

# 4. Run
python deploy.py
# Done — all roles and teams created in LaunchDarkly
```

**Requirements:**
- Python **3.8 or higher** (3.10+ recommended)
- `requests` library (`pip install requests`)
- LaunchDarkly API key with **Admin** or **Owner** role

---

## Why This Phase

Before this phase, clients received a combined JSON payload and had to manually:
- Extract each role and team from the combined file
- Make individual API calls (no LD bulk import)
- Know the correct deployment order
- Handle errors themselves

This phase eliminates all of that.

---

## Design Documents

| Document | Description |
|----------|-------------|
| [HLD.md](../../delivery-package/HLD.md) | Architecture, package structure, data flow |
| [DLD.md](../../delivery-package/DLD.md) | PackageGenerator class, deploy.py design, file formats |
| [PSEUDOLOGIC_AND_TESTS.md](../../delivery-package/PSEUDOLOGIC_AND_TESTS.md) | Full pseudo logic + 20 test cases |

---

## Implementation Checklist

### Code
- [ ] `services/package_generator.py` — `PackageGenerator` class
- [ ] `services/__init__.py` — export `PackageGenerator`
- [ ] `ui/deploy_tab.py` — add "📦 Download Deployment Package" button

### Tests
- [ ] `tests/test_package_generator.py` — all 20 test cases from PSEUDOLOGIC doc

### Verification
- [ ] ZIP opens correctly on macOS, Windows, Linux
- [ ] Extracted `deploy.py` runs with `python deploy.py --dry-run`
- [ ] `deploy.py` creates roles before teams
- [ ] `deploy.py` handles 409 (already exists) gracefully
- [ ] `rollback.json` written after successful run
- [ ] All tests passing: `venv/bin/python -m pytest tests/test_package_generator.py -v`

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Format | ZIP | Single download, self-contained, works everywhere |
| Script language | Python (stdlib + requests only) | Client doesn't need rbac-builder installed |
| File naming | `NN_<key>.json` | Number prefix ensures correct sort/apply order |
| Error handling | Skip on 409, abort on all-fail | Safe to re-run; prevents orphaned teams |
| Dry run | `"dry_run": true` in settings.json | Client can preview before committing |
| Rollback | `rollback.json` written after run | Client has record of what was created |

---

## Files to Create

```
services/package_generator.py    ← NEW
tests/test_package_generator.py  ← NEW
```

## Files to Modify

```
services/__init__.py             ← add PackageGenerator export
ui/deploy_tab.py                 ← add download ZIP button
```
