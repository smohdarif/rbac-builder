# Phase 16: Terraform Export

| Field | Value |
|-------|-------|
| **Phase** | 16 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Priority** | 🔴 High |
| **Goal** | Generate a complete, runnable Terraform package — `.tf` files the client runs with `terraform apply` |
| **Depends on** | Phase 13 (Delivery ZIP pattern), Phase 11 (Role Attribute Pattern) |

---

## What the Client Gets

```
voya_terraform.zip
└── voya_terraform/
    ├── main.tf        ← custom roles + teams as inline HCL resources
    ├── providers.tf   ← launchdarkly provider + required version
    ├── variables.tf   ← api_key variable (sensitive)
    └── README.md      ← how to run terraform init + apply
```

Client runs:
```bash
unzip voya_terraform.zip && cd voya_terraform
terraform init
terraform plan    # preview
terraform apply   # create roles + teams in LD
```

---

## Key Design Decision: Inline vs Module-based

The sa-demo uses module-based Terraform (`source = "./roles/flag-lifecycle/per-project"`), which requires bundling the entire `roles/` directory from ps-terraform-private (~50 files).

**We use inline resources** — standalone, no module dependencies:

| | Inline ✅ | Module-based |
|-|-----------|--------------|
| Standalone `terraform apply`? | ✅ | ❌ needs bundled modules |
| Output size | Small (1 `main.tf`) | Large (~50 module files) |
| Matches sa-demo? | ❌ different structure | ✅ exact match |
| Best for | One-time delivery | Ongoing IaC management |

Module-based Terraform can be a future Phase 16b enhancement.

---

## Critical HCL Escaping Note

JSON uses `${roleAttribute/projects}`. HCL uses `${...}` for interpolation.

**Must escape: `${` → `$${` in all generated HCL strings.**

```python
resource.replace("${", "$${")
# "proj/${roleAttribute/projects}:..." → "proj/$${roleAttribute/projects}:..."
```

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, 15 test cases, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | String escaping, HCL generation, set() lookup |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/terraform_generator.py` | CREATE — `TerraformGenerator` class |
| `services/__init__.py` | ADD `TerraformGenerator` export |
| `ui/deploy_tab.py` | ADD 4th download card "🏗️ Download Terraform" |
| `tests/test_terraform_generator.py` | CREATE — 15 test cases |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [ ] `services/terraform_generator.py` created
- [ ] `services/__init__.py` updated
- [ ] `ui/deploy_tab.py` updated
- [ ] `tests/test_terraform_generator.py` created — all 15 tests passing
- [ ] Validate: generated `main.tf` has no unescaped `${` in strings
- [ ] Validate: `terraform validate` passes on sample output
