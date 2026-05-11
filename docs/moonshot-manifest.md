# Moonshots XXIII Launch Manifest: RBAC Builder

## Page Properties

| Field | Value |
|-------|-------|
| **Team Name / Title** | RBAC Builder |
| **Summary** | An interactive Streamlit tool that lets Solution Architects visually design, validate, and deploy LaunchDarkly RBAC policies through a spreadsheet-like permission matrix — with an AI advisor ("Sage") that recommends role configurations based on customer team structure. Replaces hours of manual JSON authoring and tribal knowledge with a guided, API-ready workflow. |
| **Participants** | @Arif Shaikh |
| **Needed** | Anyone interested in SA tooling, AI-assisted workflows, or LaunchDarkly RBAC/custom roles. Engineering help for API integration polish and demo video production would be great. |
| **Mission Debrief** | Build a tool that eliminates the #1 friction point in enterprise customer onboarding: designing and deploying custom RBAC policies. Today, SAs manually author JSON policies from tribal knowledge, cross-referencing Terraform modules and internal action definitions. RBAC Builder replaces that with a visual matrix UI, AI-powered role recommendations (Sage, powered by Gemini), Terraform export, and one-click deployment to the LD API — turning a multi-hour manual process into a 15-minute guided workflow. |
| **Demo Link** | https://customroles.streamlit.app |
| **Project Status** | WIP |

---

## Problem

**Enterprise customers struggle to implement LaunchDarkly RBAC correctly, and SAs spend hours manually building policies.**

LaunchDarkly's custom roles system is powerful but complex: dozens of actions, project vs. environment scoping, resource specifier syntax, tag-based filtering, and approval workflows. Customers need RBAC to meet compliance and security requirements, but designing the right policy matrix requires deep tribal knowledge that lives in scattered Terraform modules, internal docs, and individual SA experience.

### Scenario #1: The Blank Page Problem

An SA sits down with a new enterprise customer (say, 5 teams, 3 projects, 4 environments) and faces: *"Who should get what permissions?"* Today, the SA opens a Google Sheet, manually cross-references Terraform modules, looks up action names in internal source code, hand-writes JSON policy statements, and hopes they got the scoping right. One missed environment tag or a typo in an action name means a broken deployment. This process takes 2-4 hours per customer and is error-prone.

### Scenario #2: No Visibility Into Existing RBAC Health

Customers with existing RBAC have orphaned roles, inactive users with elevated permissions, and no way to audit their policy posture. The companion Policy Explorer tool analyzes this, but there's no bridge from "here's what's broken" to "here's how to fix it."

### Scenario #3: AI Configs Permissions Gap

AI Configs (LLM management) added new project-level and environment-level actions in 2024-2025. Most SAs and customers don't know these permissions exist, let alone how to scope them. The builder includes them natively, keeping SAs ahead of the product.

---

## Proposal

**RBAC Builder is a Python/Streamlit application with three core capabilities:**

### 1. Visual Permission Matrix

A spreadsheet-like UI where SAs check/uncheck permissions across a Teams x Permissions x Environments grid. Project-scoped actions (createFlag, archiveFlag, manageMetrics) and environment-scoped actions (updateTargeting, applyChanges, manageSegments) are cleanly separated. The matrix supports critical/non-critical environment grouping, AI Config permissions, observability actions, and tag-based environment filtering — all driven by authoritative action definitions.

### 2. Sage — AI Role Designer

A Gemini-powered chat tab where the SA describes the customer's team structure in natural language ("We have 4 teams, developers need targeting in test but only view in prod") and Sage recommends a complete permission matrix with reasoning. The SA reviews, adjusts, and applies the recommendation directly to the matrix. This turns tribal knowledge into an AI-guided conversation.

### 3. Deployment Pipeline

The builder generates:

- **LaunchDarkly API-ready JSON** for custom roles and teams (via RoleAttributePayloadBuilder)
- **Terraform HCL export** for infrastructure-as-code workflows
- **Delivery ZIP packages** matching the standard SA delivery pattern
- **Direct API deployment** to LaunchDarkly with validation

### Companion Tool: Policy Explorer

A separate Streamlit app that connects to a customer's existing LD account and generates RBAC health metrics — orphaned roles, inactive users with elevated access, role utilization rates, permission-per-policy ratios. Together, Explorer diagnoses and Builder prescribes.

### Architecture

28 implementation phases, 16+ completed, with data models, storage, payload builder, validation, UI, API client, deployer, Terraform generator, and AI advisor. The codebase is designed as a learning project with extensive documentation (RBAC concepts guide, architecture flow diagrams, per-phase design docs).

### Impact

- Reduces SA RBAC delivery time from hours to minutes
- Ensures customers get correctly-scoped, least-privilege policies
- Keeps pace with new LD features (AI Configs, observability, context kinds) automatically
- Makes RBAC expertise accessible to every SA, not just the few who've memorized the action list
