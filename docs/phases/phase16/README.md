# Phase 16: Terraform Export

| Field | Value |
|-------|-------|
| **Phase** | 16 |
| **Status** | ⏳ Upcoming |
| **Priority** | 🔴 High |
| **Goal** | Generate `.tf` files matching `ps-terraform-private` module patterns as a Terraform deliverable |
| **Depends on** | Phase 13 (Delivery Package), Phase 11 (Role Attribute Pattern) |

## Summary

SAs who deliver via Terraform receive a `main.tf` + `variables.tf` + `providers.tf` package instead of JSON + deploy.py. Uses `ps-terraform-private` module sources.

## Full Design

See [ROADMAP.md — Phase 16](../../ROADMAP.md#phase-16-terraform-export)

## Checklist

- [ ] DESIGN.md written
- [ ] PYTHON_CONCEPTS.md written
- [ ] `services/terraform_generator.py` created
- [ ] `ui/deploy_tab.py` — 🏗️ Terraform Export button added
- [ ] Tests created and passing
