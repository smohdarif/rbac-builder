# Enhancement Tracker

Tracks enhancements, fixes, and improvements identified from customer guides, field feedback, and gap analysis.

**Last updated:** 2026-07-23

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| OPEN | Not started |
| IN PROGRESS | Currently being worked on |
| DONE | Implemented and tested |
| WONT DO | Decided against — reason noted |

## Type Key

| Label | Description |
|-------|-------------|
| Enhancement | New feature or capability |
| Fix | Bug fix or correction |
| Knowledge | System prompt / knowledge base update |
| Validation | New validation rule |
| UX | User experience improvement |

## Priority Key

| Label | Description |
|-------|-------------|
| P0 | Critical — blocks core workflows |
| P1 | High — quick win or high value |
| P2 | Medium — important but not urgent |
| P3 | Low — nice to have |

---

## Tracker

### Source: Cority + LaunchDarkly AI-Assisted Custom Roles Self-Service Guide (May 2026)

| ID | Type | Priority | Status | Title | Description | Affected Files | Phase |
|----|------|----------|--------|-------|-------------|----------------|-------|
| ENH-001 | Knowledge | P1 | OPEN | Add `bypassRequiredApproval` wildcard gotcha to Sage | `actions: ["*"]` does NOT include `bypassRequiredApproval`. Sage should warn users when recommending wildcard actions and advise explicit handling. | `core/rbac_knowledge.py` | 27 |
| ENH-002 | Knowledge | P1 | OPEN | Add cumulative permissions warning to Sage | Writer base role + restrictive custom role = Writer wins. Sage should warn that custom roles cannot subtract from built-in base roles. | `core/rbac_knowledge.py` | 27 |
| ENH-003 | Knowledge | P1 | OPEN | Add role attribute key consistency gotcha to Sage | Mismatched role attribute keys (e.g., `project-key` vs `projectKey`) silently break roles. Sage should flag this when discussing role attributes. | `core/rbac_knowledge.py` | 27 |
| ENH-004 | Knowledge | P1 | OPEN | Add env key vs display name warning to Sage | Environment keys may differ from display names (e.g., key=`develop`, display=`Development`). Sage should remind users to verify keys from project settings, not guess from names. | `core/rbac_knowledge.py` | 27 |
| ENH-005 | Validation | P2 | OPEN | Add cross-env flag actions intentionality check | Warn when cross-environment actions (`createFlag`, `deleteFlag`, `updateName`, `updateDescription`, `updateFlagVariations`, `updateMaintainer`, `updateTemporary`, `updateTags`) are scoped to a single env in the resource specifier — they apply to ALL envs regardless. | `services/validation.py` | 4 |
| ENH-006 | Validation | P2 | OPEN | Add role attribute key consistency validation | Check that role attribute keys are identical (casing, formatting) across every resource specifier in the generated policy. Flag mismatches as errors. | `services/validation.py` | 4 |
| ENH-007 | Validation | P2 | OPEN | Add base role conflict warning | When deploying, warn if target members have Writer or Admin base role — custom restrictive roles will NOT reduce their access. | `services/validation.py`, `services/deployer.py` | 7 |
| ENH-008 | Validation | P2 | OPEN | Add `bypassRequiredApproval` explicit handling check | If any generated role uses `actions: ["*"]`, warn that `bypassRequiredApproval` is not included and must be handled explicitly (allow or deny). | `services/validation.py` | 4 |
| ENH-009 | Enhancement | P2 | OPEN | Permission Debugger tab — member audit | New tab: enter a member email (connected mode), fetch their base role + custom roles (direct + team), display consolidated effective permissions as a read-only matrix. Uses existing `ld_client.py` API calls. | `ui/debugger_tab.py`, `services/ld_client.py` | New |
| ENH-010 | Enhancement | P2 | OPEN | Consolidated role viewer | Given a member's role assignments, merge all policy JSON arrays into one consolidated view. Equivalent to the Cority `consolidate-ld-role.sh` script but built into the UI. | `services/role_consolidator.py`, `ui/debugger_tab.py` | New |
| ENH-011 | Enhancement | P3 | OPEN | Permission conflict explainer | In the Debugger tab, when a user reports "member can/can't do X", trace through the allow/deny algorithm across all roles to identify which role + statement is producing the behavior. Feed context to Sage for AI-assisted diagnosis. | `ui/debugger_tab.py`, `services/ai_advisor.py` | New |
| ENH-012 | Enhancement | P3 | OPEN | Sage: debug mode prompt template | Add a second prompt template to Sage for debugging existing permissions (not just drafting new ones). User pastes consolidated role JSON + symptom description, Sage acts as consolidated-permissions calculator. | `core/rbac_knowledge.py`, `ui/advisor_tab.py` | 27 |
| ENH-013 | UX | P3 | OPEN | Pre-deployment validation checklist UI | Show an interactive checklist before deploy (matching Cority guide Section 7): resource keys lowercase, viewProject present, cross-env actions intentional, role attribute keys consistent, bypassRequiredApproval handled, not relying on custom role to restrict Writer. | `ui/deploy_tab.py` | 8 |
| ENH-014 | Enhancement | P3 | OPEN | Leverage LD `.md` suffix for Sage doc fetching | When Sage fetches LD docs via web search, prefer the `.md` URL variant (e.g., `role-actions.md`) which returns clean markdown without accordion rendering issues. | `core/rbac_knowledge.py` | 27 |
| ENH-015 | Enhancement | P3 | OPEN | Reference `llms.txt` index in Sage | Point Sage at `launchdarkly.com/docs/llms.txt` as a fallback index when searching for LD docs it doesn't have in its knowledge base. | `core/rbac_knowledge.py` | 27 |

### Source: RF-SMART — LaunchDarkly Process and Governance Guide

| ID | Type | Priority | Status | Title | Description | Affected Files | Phase |
|----|------|----------|--------|-------|-------------|----------------|-------|
| ENH-016 | Knowledge | P1 | OPEN | Add QA Automation / SDET archetype to Sage | RF-SMART distinguishes Manual QA (test in non-PRD, can't create flags) from QA Automation/SDET (can create test-specific flags in Dev/QA only, read-only PRD). Current archetypes lump all QA into one role. | `core/rbac_knowledge.py` | 27 |
| ENH-017 | Knowledge | P1 | OPEN | Add PSM / Scrum Master archetype to Sage | RF-SMART PSM has broader access than current PO archetype: full flag CRUD, approve PRD changes, modify permissions, view audit logs. Current PO archetype is too restrictive for this pattern. | `core/rbac_knowledge.py` | 27 |
| ENH-018 | Knowledge | P1 | OPEN | Add Platform / Release Executor archetype to Sage | RF-SMART Platform role focuses on infrastructure: manage environments, SDK key rotation, integration config, API key management, execute approved PRD changes. Different from current SRE archetype which focuses on flag operations. | `core/rbac_knowledge.py` | 27 |
| ENH-019 | Knowledge | P1 | OPEN | Add Eng Leadership archetype to Sage | RF-SMART Eng Leader: view all envs, toggle Dev/QA/STG, archive/delete flags, modify permissions, view audit logs. More active than current Read-Only/Stakeholder archetype — acts as final authority escalation. | `core/rbac_knowledge.py` | 27 |
| ENH-020 | Knowledge | P2 | OPEN | Add risk classification model to Sage knowledge base | RF-SMART classifies flag changes as High/Medium/Low risk based on impact + blast radius + reversibility. Each level has different governance requirements (approval gates, QA sign-off, staged rollout). Sage should ask about risk level when designing roles for critical envs. | `core/rbac_knowledge.py` | 27 |
| ENH-021 | Enhancement | P2 | OPEN | Segment-scoped prod access pattern | RF-SMART QA gets prod toggle ONLY for a QA-only segment (`qa-prod-testers`), not global prod toggle. This is a segment-based targeting restriction pattern not supported in the matrix UI today. Would need a way to express "Update Targeting in prod, but only for segment X". | `ui/matrix_tab.py`, `services/payload_builder.py` | New |
| ENH-022 | Enhancement | P2 | OPEN | Audit Log viewing as a permission | RF-SMART matrix includes "View Audit Logs" as an explicit capability for all roles. This maps to LD `viewAuditLog` action at the account level. Not currently in the rbac-builder's permission columns. | `core/ld_actions.py`, `ui/matrix_tab.py` | 17 |
| ENH-023 | Enhancement | P2 | OPEN | Platform admin actions in matrix | RF-SMART Platform role needs: manage environments, SDK key rotation, integration config, API key management. These map to LD project-admin and account-level actions not yet in the builder. Overlaps with BACKLOG item #3 (Project Admin Roles). | `core/ld_actions.py`, `ui/matrix_tab.py` | 22/25 |
| ENH-024 | Knowledge | P2 | OPEN | Add "Modify Perms" capability awareness to Sage | RF-SMART has "Modify Perms" as a capability given only to PSM/Dev/Platform. Sage should understand that managing custom roles themselves (`createRole`, `updateRole`, `deleteRole`) is a distinct capability and warn about giving it broadly. | `core/rbac_knowledge.py` | 27 |
| ENH-025 | Knowledge | P2 | OPEN | Add gradual rollout governance pattern to Sage | RF-SMART documents a 4-step rollout: (1) internal users enabled, (2) small % rollout, (3) gradual increase based on metrics, (4) full release. Sage should reference this when recommending prod environment permissions — who needs Update Targeting for each rollout stage. | `core/rbac_knowledge.py` | 27 |
| ENH-026 | Knowledge | P2 | OPEN | Add kill switch / rollback pattern to Sage | RF-SMART documents "Rollback = toggle OFF (no redeploy)" and Platform team owns kill switch execution. Sage should factor this into recommendations — Platform/SRE needs Update Targeting in prod for emergency kill switch even if they don't own the feature. | `core/rbac_knowledge.py` | 27 |
| ENH-027 | Knowledge | P3 | OPEN | Add flag lifecycle ownership guidance to Sage | RF-SMART principle: "Flags are temporary — every flag must have a removal plan." Product owns removing flags post-release. Sage should recommend Archive Flags for PO/Product roles and warn when no team has archive capability. | `core/rbac_knowledge.py` | 27 |
| ENH-028 | Validation | P3 | OPEN | Warn when no team has Archive Flags | If no team in the matrix has Archive Flags permission, warn that flag cleanup ownership is unassigned. Based on RF-SMART principle that every flag needs a removal plan. | `services/validation.py` | 4 |
| ENH-029 | Knowledge | P3 | OPEN | Add "false low-risk bug fix" awareness to Sage | RF-SMART callout: teams often misclassify bug fixes as low risk. Sage should note that bug fixes touching data writes, business logic, shared components, or critical flows are high risk and need the same approval gates. | `core/rbac_knowledge.py` | 27 |
| ENH-030 | Enhancement | P3 | OPEN | Environment-specific testing strategy in delivery docs | RF-SMART defines different testing strategies per env (Dev=validate ON, QA=regression OFF + functional ON, Prod=gradual + metrics). The delivery package doc generator could include an environment testing strategy section. | `services/doc_generator.py` | 13 |

### Source: RBAC Builder Deployment Fixes — Hands-on Lab (May 20-22, 2026)

| ID | Type | Priority | Status | Title | Description | Affected Files | Phase |
|----|------|----------|--------|-------|-------------|----------------|-------|
| FIX-001 | Fix | P0 | OPEN | Remove `base_permissions` from generated role JSON | LD API v2 `/api/v2/roles` does not accept `base_permissions` field. All 25 role files included `"base_permissions": "no_access"` which caused 400 errors on every role creation. Must strip this field before API calls. | `services/payload_builder.py` | 3 |
| FIX-002 | Fix | P0 | OPEN | Fix invalid metric action names | `manage-metrics` role used `createMetric`, `updateMetric`, `deleteMetric` — these are not valid LD action specifiers. Fix: use wildcard `actions: ["*"]` on `metric/*` resource. Also fix resource path from `env/*:flag/*` to `metric/*` (metrics are project-level, not flag-level). | `core/ld_actions.py`, `services/payload_builder.py` | 3 |
| FIX-003 | Fix | P0 | OPEN | Increase default rate limit pause and add exponential backoff | Default `rate_limit_pause_seconds` of 0.2s is too fast — hits 429 after ~5-6 calls. Increase default to at least 1.0s. Replace single-retry on 429 with exponential backoff (1s, 2s, 4s, 8s). Also read `X-RateLimit-Reset` header from LD API for exact wait time. | `services/deployer.py`, config | 7 |
| FIX-004 | Fix | P1 | OPEN | Fix `role_exists` check failing under rate limiting | `role_exists()` GET returns 429 when rate-limited, causing it to return False. Script then tries to create the role, gets 409 Duplicate conflict. Fix: retry GET on 429 with backoff. Also treat 409 as "skip" in deployment logic, not a failure. | `services/deployer.py` | 7 |
| ENH-031 | Enhancement | P1 | OPEN | Add bypass-approval as 26th atomic role | New role for incident response: `bypassRequiredApproval` + flag update actions (`updateOn`, `updateRules`, `updateTargets`, `updateFlagVariations`), scoped via `bypass-approval-environments` role attribute. Needed for Phase 14 approval workflows. | `core/ld_actions.py`, `services/payload_builder.py`, templates | 14 |
| ENH-032 | Validation | P1 | OPEN | Validate action names against LD API before deployment | Build an action name registry from LD docs/API. Before generating payloads, validate all action specifiers against the registry. Would have caught `createMetric`/`updateMetric`/`deleteMetric` error (FIX-002). | `services/validation.py`, `core/ld_actions.py` | 4 |
| ENH-033 | Validation | P2 | OPEN | Validate role payload schema before API call | Strip any fields not accepted by the LD API (`base_permissions`, custom metadata) before sending. Maintain an allowlist of valid role payload fields: `key`, `name`, `description`, `policy`. Would have caught FIX-001. | `services/payload_builder.py`, `services/deployer.py` | 3/7 |
| ENH-034 | Enhancement | P2 | OPEN | Treat 409 Duplicate as "skip" in deployer | When deployer gets a 409 Conflict, classify it as a skip (already exists) not a failure. Log it clearly: `SKIP  role-key (already exists)`. Currently causes confusing error output on re-runs. | `services/deployer.py` | 7 |
| ENH-035 | Enhancement | P2 | OPEN | Add `X-RateLimit-Reset` header parsing to deployer | LD API returns rate limit headers. Parse `X-RateLimit-Reset` to calculate exact wait time instead of fixed/guessed delays. More efficient than conservative fixed pauses. | `services/deployer.py` | 7 |
| ENH-036 | Enhancement | P3 | OPEN | Validate resource paths match resource type | Metrics resource should be `proj/X:metric/*`, not `proj/X:env/*:flag/*`. Add validation that resource specifier structure matches the action type (flag actions use flag resource, metric actions use metric resource, etc.). | `services/validation.py` | 4 |

### Source: iSeatz — Field Request (Upload Config button, 2026-07-23)

> Raised by Dan Berkowitz (iSeatz) by email: *"Hey, Arif! Were you able to get the Upload
> Config button added?"* Sample file: `configs/customers/iseatz/2026.05.12iseatz_rbac_config.json`.
> Full analysis: `docs/phases/phase28/REQUIREMENT-iseatz-upload.md`.

| ID | Type | Priority | Status | Title | Description | Affected Files | Phase |
|----|------|----------|--------|-------|-------------|----------------|-------|
| ENH-037 | Enhancement | P1 | DONE | Implement "Upload Config" button (client-requested) | Phase 28 uploader shipped on the Setup tab (`_render_upload_section` + `_restore_config_to_session`). SA/customer can re-upload a downloaded config and resume; all tabs rehydrate. | `ui/setup_tab.py`, `tests/test_config_upload.py` | 28 |
| FIX-005 | Fix | P0 | DONE | Upload/Download config schema mismatch | Resolved via `config_importer`, which autodetects and normalises **both** Schema A (storage, snake_case) and Schema B (download, Title-Case, team-by-name). The iSeatz downloaded file now restores correctly (6 teams, 10 envs, 6+60 perms). See ENH-040 — the two schemas are now unified to A at the source. | `ui/setup_tab.py`, `services/config_importer.py` | 28 |
| ENH-040 | Enhancement | P1 | DONE | Unify config write format to Schema A | Extended `ProjectPermission` with observability + `manage_ai_variations` fields (model now holds all 18 project columns), making `to_rbac_config()` lossless. Repointed the Download button (`_build_config_dict`) at `RBACConfig.to_dict()` so Save and Download emit ONE canonical schema (A). Importer still reads legacy Schema B for files already in the field. | `models/permissions.py`, `ui/deploy_tab.py`, `services/config_importer.py`, `tests/test_config_upload.py` | 28 |
| FIX-006 | Fix | P1 | DONE | Save button wrote configs with zero permissions | `build_config_from_session()` built `RBACConfig` from teams + env_groups ONLY, omitting both permission matrices — so 💾 Save Configuration persisted configs with 0 project + 0 env permissions (confirmed on the saved iSeatz `config.json`). Rerouted it through the same importer path as Download (`_build_session_snapshot` → `normalize_config` → `to_rbac_config`) so Save now writes complete, Schema-A configs identical to Download. | `ui/deploy_tab.py` | 28 |
| ENH-038 | Enhancement | P1 | DONE | Config import normalisation service | `services/config_importer.py` added: schema autodetect, team-name→key resolution, null coalescing, lossless `NormalizedConfig` (keeps observability columns the models lack), `to_rbac_config()`, and pure DataFrame builders. 21 unit tests. | `services/config_importer.py`, `tests/test_config_upload.py` | 28 |
| ENH-039 | Validation | P3 | OPEN | Warn on mislabeled / null env-group metadata on import | Surface a soft warning when imported env groups have null approval/critical flags or suspicious notes (e.g. iSeatz `dev` group noted "Production environments"). Not a hard failure. Importer coalesces silently today. | `services/config_importer.py`, `services/validation.py` | 28/4 |

---

## Implementation Notes

### FIX-001 through FIX-004 (Deployment Blockers)

These are real bugs found during live deployment. FIX-001 and FIX-002 are P0 blockers — every deployment will hit them.

**FIX-001 — `base_permissions` removal:**
Find where `payload_builder.py` adds `"base_permissions": "no_access"` to role dicts and remove it. If needed for internal documentation, move to a separate metadata section that gets stripped before API calls:
```python
# In payload_builder.py — strip non-API fields before output
API_ROLE_FIELDS = {"key", "name", "description", "policy"}

def _clean_role_for_api(role_dict: dict) -> dict:
    return {k: v for k, v in role_dict.items() if k in API_ROLE_FIELDS}
```

**FIX-002 — Metric actions:**
Update `core/ld_actions.py` MANAGE_METRICS entry. The correct actions are NOT `createMetric`/`updateMetric`/`deleteMetric`. Use wildcard on `metric/*` resource:
```python
# Before (wrong):
"Manage Metrics": {
    "actions": ["createMetric", "updateMetric", "deleteMetric"],
    "resource": "proj/${roleAttribute/projects}:env/*:flag/*"
}

# After (correct):
"Manage Metrics": {
    "actions": ["*"],
    "resource": "proj/${roleAttribute/projects}:metric/*"
}
```

**FIX-003 — Exponential backoff:**
```python
def _post(self, path, data):
    url = self.base_url + path
    for attempt in range(4):
        resp = requests.post(url, headers=self.headers, json=data, timeout=30)
        if resp.status_code != 429:
            return resp
        wait = 2 ** attempt  # 1s, 2s, 4s, 8s
        time.sleep(wait)
    return resp
```

**FIX-004 — `role_exists` retry + 409 handling:**
```python
def role_exists(self, key):
    resp = self._get("/api/v2/roles/" + key)
    if resp.status_code == 429:
        time.sleep(2)
        resp = self._get("/api/v2/roles/" + key)
    return resp.status_code == 200
```

### ENH-031 (Bypass Approval Role)

New atomic role #26. JSON template:
```json
{
  "key": "bypass-approval",
  "name": "Bypass Approval",
  "description": "Template role for Bypass Approval",
  "policy": [
    {
      "effect": "allow",
      "actions": ["bypassRequiredApproval"],
      "resources": ["proj/${roleAttribute/projects}:env/${roleAttribute/bypass-approval-environments}:flag/*"]
    },
    {
      "effect": "allow",
      "actions": ["updateOn", "updateRules", "updateTargets", "updateFlagVariations"],
      "resources": ["proj/${roleAttribute/projects}:env/${roleAttribute/bypass-approval-environments}:flag/*"]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

Pairs with existing approval workflow roles:
- Approver persona: review-changes + apply-changes
- Incident responder persona: bypass-approval

### ENH-001 through ENH-004 (Sage Knowledge Gaps — Cority)

These are all quick wins — add rules to the `ANTI_PATTERNS` or `PERMISSION_REFERENCE` sections in `core/rbac_knowledge.py`. No UI changes needed, just system prompt updates.

Suggested addition to `rbac_knowledge.py`:

```
POLICY_GOTCHAS = """
## Policy Gotchas (Common Mistakes)

1. actions: ["*"] does NOT include bypassRequiredApproval — handle it explicitly
2. Permissions are cumulative across roles — Writer base + restrictive custom role = Writer wins
3. Role attribute keys must be identical everywhere — mismatched keys silently break the role
4. Environment keys may differ from display names — always verify from project settings
5. Cross-environment flag actions apply to ALL environments regardless of env in resource specifier
6. Custom roles cannot subtract permissions granted by built-in base roles (Reader/Writer/Admin)
"""
```

### ENH-009 and ENH-010 (Permission Debugger)

Largest new feature. Requires:
- New API calls in `ld_client.py`: `get_member_by_email()`, `get_role_by_key()`, `get_team_members()`
- New service: `role_consolidator.py` to merge policy arrays
- New UI tab: `debugger_tab.py` with member lookup + consolidated matrix view
- Only available in connected mode (needs API key)

### ENH-013 (Validation Checklist)

Could be a simple `st.expander("Pre-Deployment Checklist")` in `deploy_tab.py` with checkboxes that auto-check based on validation results and manual confirmation for items that need human review.

### ENH-016 through ENH-019 (RF-SMART — New Archetypes)

Quick wins — add new entries to `TEAM_ARCHETYPES` in `core/rbac_knowledge.py`. The RF-SMART guide reveals 4 role patterns that don't cleanly map to existing archetypes:

```
### QA Automation / SDET
- Project: Create Flags (test-specific only), View Project
- Non-critical envs (dev/qa): Update Targeting, Manage Segments, Apply Changes
- Critical envs (production): Read-only (no toggle, no targeting)
- Reasoning: Creates test flags for automation coverage. Broader than Manual QA but no prod access.

### PSM / Scrum Master
- Project: Create Flags, Update Flags, Archive Flags, View Project, Manage Metrics
- Non-critical envs: Update Targeting, Manage Segments, Apply Changes, View SDK Key
- Critical envs: Review Changes, Apply Changes, Update Targeting
- Reasoning: Owns release process. Approves PRD changes. Full flag CRUD. More active than PO.

### Platform / Release Executor
- Project: View Project, Manage Release Pipelines
- Non-critical envs: Update Targeting, Apply Changes, View SDK Key
- Critical envs: Update Targeting (kill switch), Apply Changes, View SDK Key
- Admin: Manage environments, SDK key rotation, integration config
- Reasoning: Executes deployments. Does NOT own rollout strategy or flag logic. Kill switch authority.

### Engineering Leadership
- Project: View Project, Archive Flags, Update Flags
- Non-critical envs: Update Targeting (Dev/QA/STG)
- Critical envs: View only (escalation authority, not daily operator)
- Admin: Modify custom roles, View Audit Logs
- Reasoning: Final authority when needed. Audit access for governance. Not a daily operator role.
```

### ENH-020 (Risk Classification Model)

Add a new `RISK_CLASSIFICATION` constant to `rbac_knowledge.py`. Sage uses it to ask clarifying questions about change risk when designing prod permissions:

```
RISK_CLASSIFICATION = """
## Risk Classification for Flag Changes

### High Risk — Requires full approval gate + staged rollout
- Data corruption potential, core user flow breakage, high blast radius
- Governance: Flag default=OFF, explicit QA sign-off (ON+OFF), kill switch validated
- Permissions: Requires Review Changes + Apply Changes separation in prod

### Medium Risk — Requires approval gate
- UX/logic changes, limited systemic impact, scoped features
- Governance: Flag default=OFF, QA validation required, monitor metrics
- Permissions: Update Targeting creates approval request in prod

### Low Risk — Lightweight governance
- UI-only, cosmetic, non-critical toggles, easily reversible
- Governance: Flag optional, QA lightweight, can enable broadly
- Permissions: May allow direct Apply Changes in prod for low-risk flags
"""
```

### ENH-021 (Segment-Scoped Prod Access)

Most complex RF-SMART finding. The pattern: QA toggles prod flags ONLY within a `qa-prod-testers` segment. This requires:
- A way in the matrix UI to express "Update Targeting in prod, but scoped to segment X"
- `payload_builder.py` to generate a resource specifier like `proj/*:env/production:segment/qa-prod-testers`
- Or a targeting rule restriction (more complex, may need LD approval workflows instead)

This overlaps with BACKLOG item #10 (Flag/Segment Specifiers). Consider implementing together.

### ENH-028 (No Team Has Archive)

Simple validation rule — iterate `project_matrix_df`, check if any team has "Archive Flags" = True. If none, add a warning. Quick to implement alongside other validation rules.

---

## Changelog

| Date | ID(s) | Change |
|------|-------|--------|
| 2026-05-26 | ENH-001 to ENH-015 | Initial tracker created from Cority guide gap analysis |
| 2026-05-26 | ENH-016 to ENH-030 | Added RF-SMART Process and Governance guide gap analysis |
| 2026-05-26 | FIX-001 to FIX-004, ENH-031 to ENH-036 | Added deployment fixes from May 20-22 hands-on lab |
| 2026-07-23 | ENH-037 to ENH-039, FIX-005 | Added iSeatz field request (Upload Config button) + Download/Upload schema-mismatch finding; sample config saved to `configs/customers/iseatz/` |
| 2026-07-23 | ENH-037, ENH-038, FIX-005 | **Implemented** — `services/config_importer.py` + Phase 28 uploader in `ui/setup_tab.py`; 21 tests in `tests/test_config_upload.py` (all passing). ENH-039 (import warnings) remains open. |
| 2026-07-23 | ENH-040 | **Schema unified to A** — extended `ProjectPermission` with observability + `manage_ai_variations`; Download now emits `RBACConfig.to_dict()` (Schema A). 25 tests total in `test_config_upload.py`, all passing. Importer still reads legacy Schema B. |
| 2026-07-23 | FIX-006 | **Save button config completeness** — `build_config_from_session()` omitted permission matrices; rerouted through the importer so Save writes complete Schema-A configs (teams + envs + both matrices), matching Download. |
