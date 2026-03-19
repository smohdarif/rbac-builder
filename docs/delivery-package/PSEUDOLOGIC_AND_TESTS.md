# Pseudo Logic & Test Cases: Client Delivery Package

**Status:** Design — Ready for Implementation
**Related:** [HLD](./HLD.md) | [DLD](./DLD.md)

---

## Table of Contents

1. [Pseudo Logic](#pseudo-logic)
   - [PackageGenerator.generate_package()](#1-packagegeneratorgeneratepackage)
   - [deploy.py — Deployer.run()](#2-deploypy--deployerrun)
   - [deploy.py — LDClient API calls](#3-deploypy--ldclient-api-calls)
2. [Test Cases](#test-cases)
   - [PackageGenerator Tests](#group-1-packagegenerator-tests)
   - [Role File Tests](#group-2-role-file-tests)
   - [Team File Tests](#group-3-team-file-tests)
   - [deploy.py Script Tests](#group-4-deploypy-script-tests)
   - [Edge Case Tests](#group-5-edge-case-tests)
   - [Integration Tests](#group-6-integration-tests)

---

## Pseudo Logic

### 1. PackageGenerator.generate_package()

```
FUNCTION generate_package(payload, project_key, customer_name):

  customer_slug = slugify(customer_name)
  root_dir = customer_slug + "_rbac_deployment"

  zip_buffer = in-memory bytes buffer
  zip_file = ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED)

  # ── 01_roles/ ──────────────────────────────────────────────────────
  FOR index, role IN enumerate(payload.roles, start=1):

    # Strip to only LD API fields
    role_payload = {
      "key":              role["key"],
      "name":             role["name"],
      "description":      role.get("description", ""),
      "base_permissions": "no_access",
      "policy":           role["policy"]
    }

    # Zero-padded number prefix for correct sort order
    # e.g. index=1 → "01", index=10 → "10"
    prefix = str(index).zfill(2)
    filename = f"{root_dir}/01_roles/{prefix}_{role['key']}.json"

    zip_file.writestr(filename, json.dumps(role_payload, indent=2))

  # ── 02_teams/ ──────────────────────────────────────────────────────
  FOR index, team IN enumerate(payload.teams, start=1):

    team_payload = {
      "key":            team["key"],
      "name":           team["name"],
      "description":    team.get("description", ""),
      "customRoleKeys": team["customRoleKeys"],
      "roleAttributes": team["roleAttributes"]
    }

    prefix = str(index).zfill(2)
    filename = f"{root_dir}/02_teams/{prefix}_{team['key']}.json"

    zip_file.writestr(filename, json.dumps(team_payload, indent=2))

  # ── Supporting files ───────────────────────────────────────────────
  zip_file.writestr(f"{root_dir}/deploy.py",          build_deploy_script(customer_name, project_key))
  zip_file.writestr(f"{root_dir}/settings.json",      build_settings_template())
  zip_file.writestr(f"{root_dir}/requirements.txt",   "requests>=2.28.0\n")
  zip_file.writestr(f"{root_dir}/rollback.json",      "{}")
  zip_file.writestr(f"{root_dir}/README.md",          generate_deployment_guide(payload, project_key))

  zip_file.close()
  RETURN zip_buffer.getvalue()

END FUNCTION
```

---

### 2. deploy.py — Deployer.run()

This is the logic inside the generated `deploy.py` that the client runs.

```
FUNCTION run():

  settings = load_settings_from_file("settings.json")

  IF settings["api_key"] == "YOUR_API_KEY_HERE":
    PRINT "❌ Error: Please set your API key in settings.json"
    EXIT(1)

  client = LDClient(
    api_key  = settings["api_key"],
    base_url = settings.get("base_url", "https://app.launchdarkly.com")
  )
  dry_run = settings.get("dry_run", False)
  pause   = settings.get("rate_limit_pause_seconds", 0.2)

  # ── Step 1: Roles ──────────────────────────────────────────────────
  PRINT "── Step 1: Creating Custom Roles ──"

  role_files = load_json_files_sorted("01_roles/")
  role_result = DeployResult()

  FOR filename, role_data IN role_files:
    key = role_data["key"]

    IF dry_run:
      PRINT f"  [DRY RUN] would create role: {key}"
      role_result.created.append(key)
      CONTINUE

    IF client.role_exists(key):
      PRINT f"  ⚠️  {key} → already exists (skipped)"
      role_result.skipped.append(key)
      CONTINUE

    response = client.create_role(role_data)

    IF response.status == 201:
      PRINT f"  ✅  {key} → created"
      role_result.created.append(key)
    ELSE:
      PRINT f"  ❌  {key} → failed ({response.status}: {response.error})"
      role_result.failed.append(key)
      role_result.errors[key] = response.error

    SLEEP(pause)   # avoid rate limiting

  # Abort if ALL roles failed (teams will fail anyway)
  IF len(role_result.failed) == len(role_files) AND len(role_files) > 0:
    PRINT "❌ All roles failed. Aborting before teams."
    EXIT(1)

  # ── Step 2: Teams ──────────────────────────────────────────────────
  PRINT "── Step 2: Creating Teams ──"

  team_files = load_json_files_sorted("02_teams/")
  team_result = DeployResult()

  FOR filename, team_data IN team_files:
    key = team_data["key"]

    IF dry_run:
      PRINT f"  [DRY RUN] would create team: {key}"
      team_result.created.append(key)
      CONTINUE

    IF client.team_exists(key):
      PRINT f"  ⚠️  {key} → already exists (skipped)"
      team_result.skipped.append(key)
      CONTINUE

    response = client.create_team(team_data)

    IF response.status == 201:
      PRINT f"  ✅  {key} → created"
      team_result.created.append(key)
    ELSE:
      PRINT f"  ❌  {key} → failed ({response.status}: {response.error})"
      team_result.failed.append(key)
      team_result.errors[key] = response.error

    SLEEP(pause)

  # ── Summary ────────────────────────────────────────────────────────
  PRINT summary(role_result, team_result)

  IF NOT dry_run:
    write_rollback_file(role_result.created, team_result.created)
    PRINT "  Rollback file written: rollback.json"

END FUNCTION
```

---

### 3. deploy.py — LDClient API calls

```
FUNCTION create_role(role_data):
  url = f"{base_url}/api/v2/roles"
  headers = {
    "Authorization": api_key,
    "Content-Type": "application/json"
  }
  response = POST(url, headers=headers, body=json(role_data))

  IF response.status == 429:   # rate limited
    SLEEP(1)
    response = POST(url, headers=headers, body=json(role_data))   # retry once

  RETURN response

FUNCTION role_exists(key):
  url = f"{base_url}/api/v2/roles/{key}"
  response = GET(url, headers={"Authorization": api_key})
  RETURN response.status == 200

FUNCTION create_team(team_data):
  url = f"{base_url}/api/v2/teams"
  response = POST(url, headers=headers, body=json(team_data))

  IF response.status == 429:
    SLEEP(1)
    response = POST(...)   # retry once

  RETURN response
```

---

## Test Cases

### Group 1: PackageGenerator Tests

#### TC-PG-01: Returns bytes (valid ZIP)
```
GIVEN: a valid DeployPayload with 3 roles and 1 team
WHEN:  generate_package() is called
THEN:
  - result is bytes
  - result can be opened as a valid ZipFile
  - ZipFile contains files
```

#### TC-PG-02: ZIP contains expected folder structure
```
GIVEN: payload with 3 roles and 2 teams, customer_name="Voya"
WHEN:  generate_package() is called
THEN:  ZIP namelist contains:
  - "voya_rbac_deployment/README.md"
  - "voya_rbac_deployment/deploy.py"
  - "voya_rbac_deployment/settings.json"
  - "voya_rbac_deployment/requirements.txt"
  - "voya_rbac_deployment/rollback.json"
  - "voya_rbac_deployment/01_roles/" (3 files)
  - "voya_rbac_deployment/02_teams/" (2 files)
```

#### TC-PG-03: Role files are numbered and ordered
```
GIVEN: payload with roles in order: [create-flags, update-flags, archive-flags]
WHEN:  generate_package() is called
THEN:  01_roles/ contains:
  - "01_create-flags.json"
  - "02_update-flags.json"
  - "03_archive-flags.json"
  (order matches payload.roles order)
```

#### TC-PG-04: More than 9 roles are zero-padded correctly
```
GIVEN: payload with 12 roles
WHEN:  generate_package() is called
THEN:
  - First role file is "01_<key>.json"
  - Tenth role file is "10_<key>.json"
  - When sorted alphabetically, files are in correct order
```

#### TC-PG-05: Customer name with spaces is slugified in folder name
```
GIVEN: customer_name = "Voya Financial"
WHEN:  generate_package() is called
THEN:  root folder in ZIP is "voya_financial_rbac_deployment"
```

---

### Group 2: Role File Tests

#### TC-RF-01: Role file contains only LD API fields
```
GIVEN: a role with key="create-flags"
WHEN:  role file is extracted from ZIP and parsed
THEN:
  - file contains: key, name, description, base_permissions, policy
  - file does NOT contain: metadata, deployment_order, or any extra fields
```

#### TC-RF-02: base_permissions is always "no_access"
```
GIVEN: any role in the payload
WHEN:  role file is extracted and parsed
THEN:  role_data["base_permissions"] == "no_access"
```

#### TC-RF-03: Policy statements are preserved exactly
```
GIVEN: a role with 3 policy statements
WHEN:  role file is extracted and parsed
THEN:
  - len(role_data["policy"]) == 3
  - Each statement has effect, actions, resources
  - Resource strings contain ${roleAttribute/...} placeholders unchanged
```

#### TC-RF-04: Role file is valid JSON
```
GIVEN: any role in the payload
WHEN:  role file content is read from ZIP
THEN:  json.loads(content) succeeds without exception
```

---

### Group 3: Team File Tests

#### TC-TF-01: Team file contains only LD API fields
```
GIVEN: a team with key="voya-web-dev"
WHEN:  team file is extracted from ZIP and parsed
THEN:
  - file contains: key, name, description, customRoleKeys, roleAttributes
  - file does NOT contain: metadata or extra fields
```

#### TC-TF-02: roleAttributes format is correct
```
GIVEN: team with roleAttributes:
  [{"key": "projects", "values": ["voya-web"]},
   {"key": "update-targeting-environments", "values": ["production"]}]
WHEN:  team file is extracted and parsed
THEN:
  - roleAttributes is a list
  - Each entry has "key" (string) and "values" (list)
  - Values are preserved exactly
```

#### TC-TF-03: customRoleKeys are all present
```
GIVEN: team assigned 10 role keys
WHEN:  team file is extracted and parsed
THEN:  len(team_data["customRoleKeys"]) == 10
```

---

### Group 4: deploy.py Script Tests

#### TC-DS-01: deploy.py is valid Python syntax
```
GIVEN: the generated deploy.py content string
WHEN:  compile(content, "<string>", "exec") is called
THEN:  no SyntaxError is raised
```

#### TC-DS-02: deploy.py contains expected sections
```
GIVEN: the generated deploy.py content string
WHEN:  content is inspected
THEN:  content contains:
  - "class LDClient"
  - "class Deployer"
  - "def run(self)"
  - "settings.json"
  - "01_roles"
  - "02_teams"
  - "rollback.json"
  - "dry_run"
```

#### TC-DS-03: settings.json template has correct structure
```
GIVEN: the settings.json template content
WHEN:  parsed as JSON
THEN:
  - has key "api_key" with value "YOUR_API_KEY_HERE"
  - has key "base_url" with value "https://app.launchdarkly.com"
  - has key "dry_run" with value false
```

#### TC-DS-04: requirements.txt contains requests
```
GIVEN: the requirements.txt content
THEN:  "requests" is in content
```

---

### Group 5: Edge Case Tests

#### TC-EC-01: Empty roles list → ValueError
```
GIVEN: payload with 0 roles and 0 teams
WHEN:  generate_package() is called
THEN:  ValueError is raised with message about empty payload
```

#### TC-EC-02: Roles with special characters in key are handled
```
GIVEN: role with key = "update-ai-config-targeting"
WHEN:  generate_package() is called
THEN:  file is created as "01_update-ai-config-targeting.json" (no issues)
```

#### TC-EC-03: Many teams creates correctly numbered files
```
GIVEN: payload with 15 teams
WHEN:  generate_package() is called
THEN:  team files are "01_..." through "15_..." (no "1_" or "9_" without zero-padding)
```

#### TC-EC-04: Customer name with special characters is safe for filename
```
GIVEN: customer_name = "Voya & Financial (Inc)"
WHEN:  generate_package() is called
THEN:  root folder name is safe for filesystem (no &, (), spaces)
```

---

### Group 6: Integration Tests

#### TC-INT-01: Full round-trip — build payload → generate package → extract and validate

```
SETUP:
  Build a RoleAttributePayloadBuilder payload with:
    - 3 teams: Developer, SRE, Product Manager
    - 10 roles (standard set)
    - 2 environments: test (non-critical), production (critical)

STEPS:
  1. Call generate_package()
  2. Open resulting ZIP
  3. Extract and parse all role files
  4. Extract and parse all team files

VERIFY:
  - All role files parseable as JSON ✅
  - All role files have base_permissions = "no_access" ✅
  - Number of role files == payload.get_role_count() ✅
  - Number of team files == payload.get_team_count() ✅
  - No role file contains "metadata" key ✅
  - No team file contains "deployment_order" key ✅
  - README.md exists and is non-empty ✅
  - deploy.py exists and is valid Python ✅
  - settings.json exists and parses as JSON ✅
```

#### TC-INT-02: deploy.py dry run mode

```
SETUP:
  Extract deploy.py from a generated ZIP
  Create a mock HTTP server that records requests

STEPS:
  1. Set dry_run = true in settings.json
  2. Run deploy.py

VERIFY:
  - No HTTP requests made to mock server ✅
  - Output includes "[DRY RUN]" for every resource ✅
  - rollback.json is NOT written in dry run mode ✅
```

#### TC-INT-03: deploy.py handles 409 (already exists) gracefully

```
SETUP:
  Mock LD API that returns 409 for all role creation calls

STEPS:
  Run deploy.py against mock

VERIFY:
  - Script does NOT abort ✅
  - All roles logged as "skipped" ✅
  - Script continues to create teams ✅
  - Exit code is 0 (success) ✅
```

#### TC-INT-04: deploy.py aborts when all roles fail

```
SETUP:
  Mock LD API that returns 500 for all role creation calls

STEPS:
  Run deploy.py against mock

VERIFY:
  - Script logs all roles as failed ✅
  - Script does NOT attempt team creation ✅
  - Exit code is 1 (failure) ✅
  - Error message explains why teams were skipped ✅
```

---

## Summary: Pre-Implementation Checklist

| # | Check |
|---|-------|
| 1 | `services/package_generator.py` created with `PackageGenerator` class |
| 2 | `generate_package()` returns valid ZIP bytes |
| 3 | All role files stripped to LD API fields only |
| 4 | All role files include `base_permissions: "no_access"` |
| 5 | All team files stripped to LD API fields only |
| 6 | `deploy.py` is valid Python with no external deps except `requests` |
| 7 | `deploy.py` dry run mode works (no API calls) |
| 8 | `deploy.py` handles 409 gracefully (skip, not fail) |
| 9 | `deploy.py` aborts team creation if all roles fail |
| 10 | `deploy.py` writes `rollback.json` on completion |
| 11 | UI has "📦 Download Deployment Package" button |
| 12 | `services/__init__.py` exports `PackageGenerator` |
| 13 | `tests/test_package_generator.py` created and all cases passing |

---

## Navigation

- [← HLD](./HLD.md)
- [← DLD](./DLD.md)
