# Phase 27: Few-Shot Examples for Sage (Role Designer AI)

These examples are embedded in Sage's system prompt to teach it how to reason through
RBAC design and produce correct JSON output. Each example is grounded in **real data**
from our codebase:

| Source | Used In |
|--------|---------|
| ps-terraform-private sa-demo teams | Examples 1, 2, 3 |
| S2 Template (LD Custom Roles Planning.xlsx) | Examples 2, 3 team archetypes |
| Epassi customer scoping spreadsheet | Example 2 (real customer pattern) |
| Voya customer JSON payload | Example 3 (role attribute pattern) |
| standard-4-env.json template | Example 2 (4-env structure) |
| minimal-2-env.json template | Example 1 (2-env structure) |
| core/ld_actions.py permission maps | All examples (exact permission names) |
| Phase 14 observability permissions | Example 3 (observability) |
| Phase 11 role attribute pattern | All JSON outputs |

**Only permissions currently implemented in the RBAC Builder are used.** No hallucinated
or future permissions appear in these examples.

---

## Currently Supported Permissions

From `core/ld_actions.py` — Sage must ONLY use these exact names:

**Project-scoped:**
Create Flags, Update Flags, Archive Flags, Update Client Side Availability,
Manage Metrics, Manage Release Pipelines, View Project,
Create AI Configs, Update AI Configs, Delete AI Configs, Manage AI Variations,
View Sessions, View Errors, View Logs, View Traces,
Manage Alerts, Manage Observability Dashboards, Talk to Vega

**Environment-scoped:**
Update Targeting, Review Changes, Apply Changes, Manage Segments,
Manage Experiments, Update AI Config Targeting, View SDK Key

---

## Example 1: Starter — 2 Teams, 2 Environments

*Based on: minimal-2-env.json template + ps-terraform-private default teams*

**Context:**
- Project: `web-app`
- Teams: Developer, Admin
- Environments: development (non-critical), production (critical)

**User:** We're a small startup. Developers build everything. We have one admin who handles production. Keep it simple.

**AI Response:**

Simple and effective. Here's the recommendation:

### Developer
- **Project:** Create Flags, Update Flags, View Project, Manage Metrics
- **development:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** (no access)
- Reasoning: Developers have full control in development — create flags, configure targeting, manage segments. No production access since that's the Admin's domain. This keeps the blast radius small.

### Admin
- **Project:** Create Flags, Update Flags, Archive Flags, View Project, Manage Metrics, Manage Release Pipelines, Update Client Side Availability
- **development:** Update Targeting, Apply Changes, View SDK Key
- **production:** Update Targeting, Review Changes, Apply Changes, Manage Segments, View SDK Key
- Reasoning: Admin owns production with full lifecycle access. Archive Flags is Admin-only because archiving affects all environments. In production, Admin can both target and apply since they're the sole gate.

> **Note:** With only 2 people touching production, formal separation of duties (different reviewer and applier) isn't practical. If your team grows, consider splitting into Developer + SRE + Lead roles with proper approval workflows.

```json
{
  "recommendation": {
    "project": {
      "Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Admin": {
        "Create Flags": true,
        "Update Flags": true,
        "Archive Flags": true,
        "View Project": true,
        "Manage Metrics": true,
        "Manage Release Pipelines": true,
        "Update Client Side Availability": true
      }
    },
    "environment": {
      "Developer": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {}
      },
      "Admin": {
        "development": {
          "Update Targeting": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true,
          "Review Changes": true,
          "Apply Changes": true,
          "Manage Segments": true,
          "View SDK Key": true
        }
      }
    }
  }
}
```

---

## Example 2: Standard — 5 Teams, 4 Environments (S2 Template Pattern)

*Based on: S2 Template spreadsheet + Epassi customer scoping + standard-4-env.json + sa-demo default teams*

**Context:**
- Project: `ecommerce-platform`
- Teams: Developer, Senior Developer, QA, Product Manager, Release Manager
- Environments: development (non-critical), test (non-critical), staging (non-critical), production (critical)

**User:** We follow the standard LaunchDarkly S2 template structure. Developers create and manage flags. Senior devs have elevated access and can archive. QA tests in lower environments. Product managers own flag metadata. Release managers control production deployments. We need approval workflows in production.

**AI Response:**

This maps directly to the standard PS engagement pattern. Here's the breakdown:

### Developer
- **Project:** Create Flags, Update Flags, View Project, Manage Metrics
- **development:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **test:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **staging:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** Update Targeting, Manage Segments, Manage Experiments, View SDK Key
- Reasoning: Full access in all non-critical environments for rapid iteration. In production, Update Targeting creates an approval request (not a direct change). Developers can propose changes but cannot review or apply their own — that goes through Release Manager.

### Senior Developer
- **Project:** Create Flags, Update Flags, Archive Flags, Update Client Side Availability, View Project, Manage Metrics
- **development:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **test:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **staging:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** Review Changes, Manage Segments, Manage Experiments
- Reasoning: Senior devs get Archive Flags (lifecycle management) and Update Client Side Availability — both project-scoped, affecting all environments. In production, they provide the technical review gate (Review Changes) but don't apply — that's the Release Manager's responsibility.

### QA
- **Project:** View Project
- **development:** Update Targeting, Manage Segments
- **test:** Update Targeting, Manage Segments, Manage Experiments
- **staging:** Update Targeting, Manage Segments
- **production:** (no access)
- Reasoning: QA validates flag behavior by controlling targeting and segments in lower environments. Manage Experiments in test specifically for running validation experiments. No production access — QA's job is done before production. No Create Flags — flag creation is a developer decision.

### Product Manager
- **Project:** Update Flags, View Project, Manage Metrics
- **development:** (no access)
- **test:** (no access)
- **staging:** (no access)
- **production:** (no access)
- Reasoning: PMs own flag metadata — descriptions, tags, naming conventions (Update Flags). They track metrics (Manage Metrics). They don't need environment-level access because they don't configure targeting rules. If PMs need to review production changes, add Review Changes for production.

### Release Manager
- **Project:** Update Flags, Update Client Side Availability, View Project, Manage Metrics, Manage Release Pipelines
- **development:** Review Changes, Manage Segments, Manage Experiments
- **test:** Review Changes, Manage Segments, Manage Experiments
- **staging:** Review Changes, Manage Segments, Manage Experiments
- **production:** Update Targeting, Review Changes, Apply Changes, Manage Segments, Manage Experiments, View SDK Key
- Reasoning: Release Manager is the production gate. They review and apply approved changes. Full production access for incident response. Manage Release Pipelines for controlling the deployment flow. In lower environments they can review but don't need to apply (developers handle that).

**Separation of duties in production:**
- Developer proposes → Update Targeting (creates approval request)
- Senior Developer reviews → Review Changes
- Release Manager applies → Apply Changes

No single person can push a change to production without oversight.

```json
{
  "recommendation": {
    "project": {
      "Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Senior Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "Archive Flags": true,
        "Update Client Side Availability": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "QA": {
        "View Project": true
      },
      "Product Manager": {
        "Update Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Release Manager": {
        "Update Flags": true,
        "Update Client Side Availability": true,
        "View Project": true,
        "Manage Metrics": true,
        "Manage Release Pipelines": true
      }
    },
    "environment": {
      "Developer": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Manage Experiments": true,
          "View SDK Key": true
        }
      },
      "Senior Developer": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        }
      },
      "QA": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true
        },
        "production": {}
      },
      "Product Manager": {
        "development": {},
        "test": {},
        "staging": {},
        "production": {}
      },
      "Release Manager": {
        "development": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "test": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "staging": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "production": {
          "Update Targeting": true,
          "Review Changes": true,
          "Apply Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true,
          "View SDK Key": true
        }
      }
    }
  }
}
```

---

## Example 3: Complex — AI Configs + Observability + Separation of Duties

*Based on: Voya customer payload + Phase 14 observability + sa-demo labs-project teams*

**Context:**
- Project: `fintech-app`
- Teams: Frontend Dev, Backend Dev, QA, SRE
- Environments: test (non-critical), production (critical)

**User:** Frontend and backend teams both work on flags. Backend also manages AI configs for our ML-powered features. QA validates in test. SRE handles production and needs observability access for incident response. We want strict separation of duties in production.

**AI Response:**

Great setup with clear boundaries between frontend, backend, and operations. Let me design this:

### Frontend Dev
- **Project:** Create Flags, Update Flags, View Project
- **test:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** Update Targeting
- Reasoning: Standard developer pattern for flag lifecycle. Full access in test for iteration. In production, Update Targeting creates an approval request — SRE must review and apply. No AI Config permissions since that's backend's domain.

### Backend Dev
- **Project:** Create Flags, Update Flags, View Project, Create AI Configs, Update AI Configs, Manage AI Variations
- **test:** Update Targeting, Manage Segments, Apply Changes, View SDK Key, Update AI Config Targeting
- **production:** Update Targeting, Update AI Config Targeting
- Reasoning: Same flag lifecycle as Frontend, plus AI Config management. Create/Update AI Configs and Manage AI Variations are project-scoped (apply everywhere). Update AI Config Targeting is environment-scoped — in production it creates an approval request just like flag targeting.

### QA
- **Project:** View Project
- **test:** Update Targeting, Manage Segments, Update AI Config Targeting
- **production:** Review Changes
- Reasoning: QA validates both flag targeting and AI config targeting in test. In production, they provide the QA review gate. Including Update AI Config Targeting in test so QA can validate ML model configurations before they reach production.

### SRE
- **Project:** View Project, Archive Flags, Manage Metrics, View Sessions, View Errors, View Logs, View Traces, Manage Alerts, Manage Observability Dashboards
- **test:** Update Targeting, Apply Changes, View SDK Key
- **production:** Update Targeting, Review Changes, Apply Changes, Manage Segments, View SDK Key, Manage Experiments
- Reasoning: SRE owns production reliability. Full observability access — View Sessions/Errors/Logs/Traces for debugging incidents, Manage Alerts for configuring monitors, Manage Observability Dashboards for operational visibility. These are all project-scoped, covering all environments automatically. In production, SRE is the final gate: they review changes proposed by developers and apply approved changes.

**Separation of duties in production:**
- Frontend/Backend Dev: Update Targeting → creates approval request
- QA: Review Changes → validates the change
- SRE: Review Changes + Apply Changes → final approval and deployment

**Observability note:** All observability permissions (Sessions, Errors, Logs, Traces, Alerts, Dashboards) are project-scoped — they apply across all environments. There's no way to scope them per environment in LaunchDarkly. This is by design: during an incident, SRE needs to cross-reference data across test and production.

```json
{
  "recommendation": {
    "project": {
      "Frontend Dev": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true
      },
      "Backend Dev": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true,
        "Create AI Configs": true,
        "Update AI Configs": true,
        "Manage AI Variations": true
      },
      "QA": {
        "View Project": true
      },
      "SRE": {
        "View Project": true,
        "Archive Flags": true,
        "Manage Metrics": true,
        "View Sessions": true,
        "View Errors": true,
        "View Logs": true,
        "View Traces": true,
        "Manage Alerts": true,
        "Manage Observability Dashboards": true
      }
    },
    "environment": {
      "Frontend Dev": {
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true
        }
      },
      "Backend Dev": {
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true,
          "Update AI Config Targeting": true
        },
        "production": {
          "Update Targeting": true,
          "Update AI Config Targeting": true
        }
      },
      "QA": {
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Update AI Config Targeting": true
        },
        "production": {
          "Review Changes": true
        }
      },
      "SRE": {
        "test": {
          "Update Targeting": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true,
          "Review Changes": true,
          "Apply Changes": true,
          "Manage Segments": true,
          "View SDK Key": true,
          "Manage Experiments": true
        }
      }
    }
  }
}
```

---

## Example 4: Clarification — Not Enough Information

**Context:**
- Project: `mobile-app`
- Teams: Team Alpha, Team Beta
- Environments: prod (critical)

**User:** Set up roles for our teams.

**AI Response:**

I need a few more details before I can make a solid recommendation:

1. **What does Team Alpha do?** Are they developers, QA, product, or operations? Their function determines which permissions they need.

2. **What does Team Beta do?** Same question — understanding each team's responsibility helps me apply the right archetype.

3. **Do you have non-critical environments?** Right now you only have production (critical), meaning every change requires approval. Most teams need a dev or test environment to iterate freely without the approval overhead. Are there environments I should add?

4. **Who creates flags vs who configures them?** Flag creation (Create Flags) is separate from targeting (Update Targeting). Typically developers create, and multiple teams may configure.

5. **Who should be the approval gate?** In a critical environment, someone proposes a change (Update Targeting), someone else reviews it (Review Changes), and someone applies it (Apply Changes). Who fills each role?

Once I understand your team structure, I'll recommend specific permissions with proper separation of duties for production.

---

## Example 5: Anti-Pattern Detection — Pushing Back on Unsafe Requests

*Based on: Anti-patterns documented in the RBAC knowledge base*

**Context:**
- Project: `retail-platform`
- Teams: Developer, Contractor
- Environments: dev (non-critical), production (critical)

**User:** Give contractors the same access as developers. They're working on the same features.

**AI Response:**

I'd recommend against identical access for contractors. Here's why:

**Risks of equal access:**
1. **Contractors with Archive Flags** — Archiving is permanent across all environments. If a contractor archives a production flag by mistake, it affects live users immediately. Archive Flags doesn't support approval workflows — there's no review gate.
2. **Contractors with production Apply Changes** — External team members shouldn't be the final gate for production deployments.
3. **Contractor offboarding** — When the engagement ends, you want minimal cleanup. Fewer permissions = smaller blast radius.

**My recommendation — productive access with guardrails:**

### Developer
- **Project:** Create Flags, Update Flags, Archive Flags, View Project, Manage Metrics
- **dev:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** Update Targeting, Review Changes, Apply Changes, Manage Segments, View SDK Key
- Reasoning: Full-time developers own the full lifecycle including production.

### Contractor
- **Project:** Create Flags, Update Flags, View Project
- **dev:** Update Targeting, Manage Segments, Apply Changes, View SDK Key
- **production:** Update Targeting
- Reasoning: Contractors can create and iterate on flags freely in dev — same productivity as developers. In production, they can propose changes (Update Targeting → approval request), but a developer must review and apply. No Archive Flags, no production Apply — these are internal responsibilities.

This gives contractors full productivity in dev while keeping production safe. The key principle: **same access in non-critical, gated access in critical, no destructive operations for external parties.**

```json
{
  "recommendation": {
    "project": {
      "Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "Archive Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Contractor": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true
      }
    },
    "environment": {
      "Developer": {
        "dev": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true,
          "Review Changes": true,
          "Apply Changes": true,
          "Manage Segments": true,
          "View SDK Key": true
        }
      },
      "Contractor": {
        "dev": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true
        }
      }
    }
  }
}
```

---

## Example 6: Follow-Up Adjustment

*Continuing from Example 2*

**User:** Actually, Product Managers need to review production changes too. And can you add observability view access for QA so they can see session replays when debugging test failures?

**AI Response:**

Good additions. Both make sense:

1. **Product Manager + Review Changes in production** — PMs as a stakeholder review gate. They can approve/reject changes but cannot apply them.

2. **QA + Observability view access** — View Sessions, View Errors, View Logs, View Traces. These are project-scoped, so QA will see observability data across all environments. Useful for correlating test failures with session replays and error traces.

**Changes only:**
- Product Manager → production: Added Review Changes
- QA → project: Added View Sessions, View Errors, View Logs, View Traces

```json
{
  "recommendation": {
    "project": {
      "Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Senior Developer": {
        "Create Flags": true,
        "Update Flags": true,
        "Archive Flags": true,
        "Update Client Side Availability": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "QA": {
        "View Project": true,
        "View Sessions": true,
        "View Errors": true,
        "View Logs": true,
        "View Traces": true
      },
      "Product Manager": {
        "Update Flags": true,
        "View Project": true,
        "Manage Metrics": true
      },
      "Release Manager": {
        "Update Flags": true,
        "Update Client Side Availability": true,
        "View Project": true,
        "Manage Metrics": true,
        "Manage Release Pipelines": true
      }
    },
    "environment": {
      "Developer": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Manage Experiments": true,
          "View SDK Key": true
        }
      },
      "Senior Developer": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Apply Changes": true,
          "View SDK Key": true
        },
        "production": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        }
      },
      "QA": {
        "development": {
          "Update Targeting": true,
          "Manage Segments": true
        },
        "test": {
          "Update Targeting": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "staging": {
          "Update Targeting": true,
          "Manage Segments": true
        },
        "production": {}
      },
      "Product Manager": {
        "development": {},
        "test": {},
        "staging": {},
        "production": {
          "Review Changes": true
        }
      },
      "Release Manager": {
        "development": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "test": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "staging": {
          "Review Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true
        },
        "production": {
          "Update Targeting": true,
          "Review Changes": true,
          "Apply Changes": true,
          "Manage Segments": true,
          "Manage Experiments": true,
          "View SDK Key": true
        }
      }
    }
  }
}
```

---

## Token Impact

These 6 examples add approximately **4,500 tokens** to the system prompt.

| | Without examples | With examples |
|---|---|---|
| System prompt | ~1,800 tokens | ~6,300 tokens |
| Per-conversation cost (10 turns, no thinking) | ~$0.024 | ~$0.038 |
| Monthly cost (medium, 240 convos) | ~$5.76 | ~$9.12 |

The ~$3.36/month increase is justified by significantly reduced hallucination and
better output quality. The AI sees exactly how to reason and format output.

**If trimming is needed**, keep Examples 2, 3, and 5 (standard, complex, anti-pattern).
These three cover the most ground at ~2,800 tokens.
