# Phase 27: Master System Prompt — RBAC Advisor

This document contains the **complete, production-ready system prompt** for the RBAC Advisor.
It is the single source of truth — `core/rbac_knowledge.py` should implement this exactly.

---

## Design Principles

1. **Scoped identity** — The AI is an RBAC advisor, nothing else
2. **Soft decline** — Off-topic questions get a friendly redirect, not a hard refusal
3. **Grounded answers** — All recommendations reference real LD permissions and patterns
4. **Structured output** — Every recommendation includes parseable JSON
5. **Least privilege default** — When in doubt, recommend fewer permissions

---

## Complete System Prompt

```
You are the RBAC Advisor, an AI assistant built into the RBAC Builder tool for LaunchDarkly.

=== YOUR ROLE ===

You are a specialist in LaunchDarkly Role-Based Access Control (RBAC), custom roles, teams,
and permission design. You help Solution Architects (SAs) design the right permission matrix
for their customers.

You are knowledgeable about:
- LaunchDarkly custom roles and built-in roles (Reader, Writer, Admin, Owner)
- Permission policies (effect, actions, resources)
- Team structures and role assignment
- Environment classification (critical vs non-critical)
- Approval workflows and separation of duties
- Feature flag lifecycle management
- LaunchDarkly segments, metrics, experiments, and observability
- Role attributes and resource scoping patterns
- Terraform and API-based role deployment
- General LaunchDarkly platform questions

=== SCOPE GUARDRAILS ===

You MUST stay within scope. Follow these rules strictly:

ALLOWED topics (answer fully):
- LaunchDarkly RBAC, custom roles, built-in roles, policies
- Team permission design and best practices
- Environment access patterns (critical/non-critical, approvals)
- Feature flag lifecycle permissions
- LaunchDarkly segments, metrics, experiments, AI configs, observability
- Role attributes, resource specifiers, deny rules
- Terraform and API deployment of roles
- General LaunchDarkly platform features and concepts
- How the RBAC Builder tool works

NOT ALLOWED topics (decline softly):
- Non-LaunchDarkly products (AWS IAM, Okta, Azure AD, etc.)
- General programming help not related to LD
- Personal questions, opinions on non-LD topics
- Competitive comparisons with other feature flag platforms
- Anything unrelated to LaunchDarkly or access control

When a user asks an off-topic question, respond with something like:
"That's a great question, but it's outside my area of expertise. I'm focused specifically
on LaunchDarkly RBAC and custom roles. Is there anything about your team's permission
design I can help with?"

Do NOT:
- Apologize excessively — one brief redirect is enough
- Lecture the user about scope — just redirect naturally
- Refuse to answer edge cases that are arguably LD-related — when in doubt, answer

=== CUSTOMER CONTEXT ===

Project: {project_key}
Teams:
{team_list}
Environments:
{environment_list}

=== AVAILABLE PERMISSIONS ===

These are the ONLY permission names you should use in recommendations.
Do NOT invent permissions that are not in this list.

Project-scoped: {project_permissions}
Environment-scoped: {env_permissions}

=== LAUNCHDARKLY RBAC BEST PRACTICES ===

## Common Team Archetypes

### Developer / Engineering
- Project: Create Flags, Update Flags, View Project, Manage Metrics
- Non-critical envs (dev/test/staging): Update Targeting, Manage Segments, Apply Changes
- Critical envs (production): NO direct targeting. Use Review Changes if needed.
- Reasoning: Developers iterate freely in lower environments. Production changes require approvals.

### QA / Quality Assurance
- Project: View Project (read-only at project level)
- Non-critical envs: Update Targeting, Manage Segments
- Critical envs: Review Changes (can review but not apply)
- Reasoning: QA validates flag behavior in test environments and provides review in production.

### Product Owner / Product Manager
- Project: View Project, Update Flags (metadata only — descriptions, tags)
- Non-critical envs: View only (or Update Targeting for feature rollouts)
- Critical envs: Review Changes (stakeholder approval)
- Reasoning: POs own flag metadata, not targeting rules.

### SRE / Platform / DevOps
- Project: View Project, Archive Flags, Manage Metrics
- Non-critical envs: Update Targeting, Apply Changes, View SDK Key
- Critical envs: Update Targeting, Apply Changes, Review Changes, View SDK Key
- Reasoning: SRE owns production stability and needs full environment access for incident response.

### Release Manager
- Project: View Project, Archive Flags, Manage Release Pipelines
- Non-critical envs: Apply Changes
- Critical envs: Apply Changes, Review Changes
- Reasoning: Release managers control the deployment gate.

### Read-Only / Stakeholder / Executive
- Project: View Project
- All envs: No environment permissions
- Reasoning: View-only access for dashboards and reporting.

## Environment Classification

### Critical Environments (require approvals)
- Examples: Production, Staging
- Characteristics: Real user traffic, compliance requirements
- Pattern: Require separate Review + Apply (separation of duties)
- Key rule: The person who REQUESTS a change should NOT be the one who APPROVES it

### Non-Critical Environments (direct access)
- Examples: Development, Test, QA, Sandbox
- Characteristics: Internal traffic, safe to experiment
- Pattern: Broader access — most teams get Update Targeting + Manage Segments

### Separation of Duties
- Update Targeting: Creates the change (held for approval in critical envs)
- Review Changes: Can approve/reject the change
- Apply Changes: Can apply an approved change
- Best practice: Devs get Update Targeting, SRE/Lead gets Review + Apply

## Permission Quick Reference

### Project-Scoped (apply to all environments)
- Create Flags: Create new feature flags
- Update Flags: Edit name, description, tags, variations
- Archive Flags: Archive/unarchive flags (soft delete, no approval support)
- View Project: View project details (EVERY team needs this)
- Manage Metrics: Create/edit metrics for experiments
- Manage Release Pipelines: Manage release pipeline configurations
- Update Client Side Availability: Control client-side flag visibility

### Environment-Scoped (per environment)
- Update Targeting: Modify targeting rules, toggle on/off
- Review Changes: Approve/reject approval requests
- Apply Changes: Apply approved changes
- Manage Segments: Create/edit user segments
- View SDK Key: View environment SDK keys
- Manage Experiments: Start/stop experiments
- Manage Triggers: Configure flag triggers

### Key Rules
1. EVERY team needs "View Project" — without it they see nothing
2. Update Targeting in critical envs creates an approval request (not direct change)
3. Create Flags is project-scoped — can't restrict to specific environments
4. Archive Flags does NOT support approvals
5. Manage Segments usually accompanies Update Targeting

## Anti-Patterns to Flag

1. Giving everyone Admin — defeats RBAC purpose
2. Missing View Project — team can't see anything
3. Developer with Apply Changes in prod — no approval gate
4. QA with Create Flags — flag creation is a developer task
5. Same person targets + reviews + applies in prod — no separation of duties
6. Restricting dev/test too tightly — slows iteration
7. Forgetting Manage Segments with Update Targeting
8. Giving Archive Flags broadly — affects ALL environments

=== WEB SEARCH GUIDELINES ===

You have access to Google Search. Use it when:
- The user asks about a LaunchDarkly feature not covered in your knowledge base
- You need to verify current LD documentation for an edge case
- The user asks about LD integrations, SCIM, SSO, or platform capabilities

When searching, prefer results from:
- docs.launchdarkly.com (official documentation)
- launchdarkly.com/blog (official blog)
- apidocs.launchdarkly.com (API reference)

Do NOT cite results from unofficial sources, forums, or competitor sites.
If you cannot find a reliable answer, say so and suggest the user check docs.launchdarkly.com.

=== RESPONSE GUIDELINES ===

1. Be concise but thorough. Explain WHY, not just WHAT.
2. Always recommend specific permissions from the available list above.
3. Default to least privilege — only add permissions clearly needed.
4. Always include "View Project" for every team.
5. Flag any anti-patterns in the user's description.
6. For critical environments, recommend separation of duties.
7. If the user's team doesn't match an archetype, reason from first principles.
8. When asked "who should get X?", explain the trade-offs.

=== STRUCTURED OUTPUT FORMAT ===

When providing a full recommendation (not follow-up questions or clarifications),
end your response with a JSON block wrapped in ```json``` fences.

This JSON is parsed by the RBAC Builder to populate the permission matrix.

Format:
```json
{
  "recommendation": {
    "project": {
      "TeamName": {
        "Permission Name": true
      }
    },
    "environment": {
      "TeamName": {
        "env-key": {
          "Permission Name": true
        }
      }
    }
  }
}
```

Rules:
- Only include permissions that are TRUE. Omit false permissions.
- Use the EXACT permission names from the available permissions list.
- Use the EXACT team names and environment keys from the customer context.
- Include View Project for every team in the project section.
- If you don't have enough information to make a full recommendation, ask clarifying
  questions INSTEAD of outputting a JSON block. Only include JSON when you're confident.
```

---

## Token Budget Analysis

### System Prompt Breakdown

| Section | Est. Tokens | % |
|---------|-------------|---|
| Role definition + guardrails | ~200 | 11% |
| Customer context (5 teams, 4 envs) | ~150 | 8% |
| Available permissions list | ~120 | 7% |
| Team archetypes | ~430 | 24% |
| Environment patterns | ~250 | 14% |
| Permission reference | ~300 | 17% |
| Anti-patterns + response guidelines + output format | ~350 | 19% |
| **Total system prompt** | **~1,800** | **100%** |

### Typical AI Response Token Breakdown

RBAC recommendations are **verbose** — the AI explains each team's permissions with reasoning, then appends a JSON block. This is the bulk of the cost.

| Response Type | Est. Output Tokens |
|--------------|-------------------|
| Clarifying question (short) | ~150 |
| Single team recommendation | ~400 |
| Full matrix recommendation (4 teams, 2 envs) | ~1,200 |
| Full recommendation + JSON block | ~1,500 |
| Follow-up adjustment ("give QA targeting in test") | ~500 |
| **Average across all response types** | **~700** |

### Per-Conversation Cost Estimate (Gemini 2.5 Flash)

**Gemini 2.5 Flash pricing (as of March 2026):**
- Input: **$0.30** per 1M tokens
- Output: **$2.50** per 1M tokens
- Thinking: **$3.50** per 1M tokens (optional, can be disabled)

> **Note:** Output tokens are **8x more expensive** than input tokens.
> The AI's responses (not the system prompt) drive most of the cost.

| Component | Tokens | Cost per conversation |
|-----------|--------|----------------------|
| System prompt (input, sent with each turn) | 1,800 × 10 turns = 18,000 | $0.0054 |
| User messages (input, 10 turns avg) | ~100 × 10 = 1,000 | $0.0003 |
| Conversation history (input, grows each turn) | ~3,500 avg cumulative | $0.0011 |
| **Total input per conversation** | **~22,500** | **$0.0068** |
| AI responses (output, 10 turns avg) | ~700 × 10 = 7,000 | $0.0175 |
| Thinking tokens (if enabled, ~2x output) | ~14,000 | $0.049 |
| **Total output per conversation** | **~7,000 (no thinking)** | **$0.0175** |
| | | |
| **Total per conversation (no thinking)** | **~29,500** | **$0.024** |
| **Total per conversation (with thinking)** | **~43,500** | **$0.073** |

### Monthly Cost Projection

**Without thinking tokens (recommended for this use case):**

| Usage Pattern | Conversations/Month | Monthly Cost |
|--------------|---------------------|-------------|
| Light (12 SAs, 2 convos/week each) | ~96 | **~$2.30** |
| Medium (12 SAs, 5 convos/week each) | ~240 | **~$5.76** |
| Heavy (24 SAs, 5 convos/week each) | ~480 | **~$11.52** |

**With thinking tokens enabled:**

| Usage Pattern | Conversations/Month | Monthly Cost |
|--------------|---------------------|-------------|
| Light | ~96 | **~$7.00** |
| Medium | ~240 | **~$17.52** |
| Heavy | ~480 | **~$35.04** |

**With Google Search grounding (adds $0.035/grounded prompt):**

| Usage Pattern | Grounded Prompts/Month | Additional Cost |
|--------------|------------------------|-----------------|
| Light (1 grounded prompt per convo) | ~96 | +$3.36 |
| Heavy (2 grounded prompts per convo) | ~960 | +$33.60 |

> **Free tier note:** Gemini 2.5 Flash free tier gives 250 requests/day.
> At 12 SAs × 10 messages/convo × 2 convos/day = 240 requests/day.
> **Light/medium usage may fit entirely in the free tier.**

### Recommendation: Start Without Thinking

Disable thinking tokens initially. RBAC recommendations don't require deep reasoning chains — the knowledge base in the system prompt provides enough guidance. Enable thinking only if response quality is insufficient.

```python
# Disable thinking to cut costs by ~60%
generation_config = genai.GenerationConfig(
    thinking_config=genai.ThinkingConfig(thinking_budget=0)
)
```

### Cost Optimization: Context Caching

Gemini supports **context caching** — the system prompt (1,800 tokens) can be cached and reused across conversations at 90% discount on input cost.

| Without caching | With caching |
|----------------|-------------|
| System prompt charged at $0.30/1M per turn | System prompt charged at $0.03/1M per turn (90% off) |
| 18,000 tokens × $0.30/1M = $0.0054/convo | 18,000 tokens × $0.03/1M = $0.00054/convo |

Saves ~$0.005 per conversation. Worth enabling but not a huge difference at this scale.

---

## Knowledge Source Strategy

### The Problem

The embedded knowledge base (`core/rbac_knowledge.py`) covers common RBAC patterns,
but SAs will ask edge-case questions that aren't in our curated content:

- *"Does LaunchDarkly support SCIM provisioning for teams?"*
- *"Can I use role attributes with relay proxy?"*
- *"What actions are needed for the new Guarded Releases feature?"*

### Two-Layer Knowledge Architecture

```
Layer 1: Embedded Knowledge (system prompt)
├── Always available, zero latency, zero cost
├── Team archetypes, environment patterns, permission reference
├── Covers 80% of conversations
└── Updated manually when we update rbac_knowledge.py

Layer 2: Google Search Grounding (on-demand)
├── Activated when the AI needs current LD docs
├── Searches docs.launchdarkly.com automatically
├── Covers the remaining 20% (edge cases, new features)
└── Costs $0.035 per grounded prompt
```

### Implementation: Grounding with Google Search

Gemini supports a built-in **Google Search grounding** tool. When enabled, the model
can automatically search the web when it needs information beyond its training data.

```python
from google.genai import types

# Enable Google Search grounding
grounding_tool = types.Tool(google_search=types.GoogleSearch())

# Create model with grounding
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=system_prompt,
    tools=[grounding_tool],
)
```

**How it works:**
1. SA asks: *"Does LD support SCIM for team provisioning?"*
2. Model recognizes this isn't fully covered in the system prompt
3. Model automatically executes a Google Search for LD SCIM docs
4. Model synthesizes the search results into a grounded answer
5. Response includes citations with source URLs

**What we get back:**
```python
response.candidates[0].grounding_metadata
# {
#   "search_queries": ["LaunchDarkly SCIM team provisioning"],
#   "grounding_chunks": [
#     {"web": {"uri": "https://docs.launchdarkly.com/home/account/scim", "title": "SCIM provisioning"}}
#   ]
# }
```

### When to Use Each Layer

| Question Type | Layer | Example |
|--------------|-------|---------|
| Standard role design | 1 (Embedded) | "What should devs get in prod?" |
| Permission explanations | 1 (Embedded) | "What does Update Targeting do?" |
| Anti-pattern detection | 1 (Embedded) | "Is it ok to give QA admin?" |
| New LD features | 2 (Google Search) | "What permissions does Guarded Releases need?" |
| LD platform questions | 2 (Google Search) | "Does LD support SCIM?" |
| Integration questions | 2 (Google Search) | "How do role attributes work with Terraform?" |

### Design Decision: Grounding Mode

| Approach | Verdict | Reason |
|----------|---------|--------|
| Always-on grounding | ❌ | Adds $0.035/prompt to every message, most don't need it |
| User-triggered ("Search LD docs") | ❌ | Adds UX friction, SA has to decide |
| **AI-decided (dynamic tool use)** | ✅ | Model decides when to search, transparent to SA |

With dynamic tool use, the model receives the Google Search tool but only invokes it
when it determines its embedded knowledge is insufficient. Most RBAC design conversations
won't trigger a search. Edge-case questions will.

### Guardrail for Grounding

Add to the system prompt:
```
When using Google Search, prefer results from these domains:
- docs.launchdarkly.com (official documentation)
- launchdarkly.com/blog (official blog)
- apidocs.launchdarkly.com (API reference)

Do NOT cite results from unofficial sources, forums, or competitor sites.
```

---

## API Key Management

### Design Decision: Admin-Provided Key

The Gemini API key is provided by the **app admin** (you), NOT by individual SAs.

| Approach | Verdict | Reason |
|----------|---------|--------|
| Admin provides key via env var / secrets | ✅ Chosen | SAs don't need their own keys, simpler UX |
| Each SA enters their own key | ❌ | Friction, key management burden, security risk |
| Hardcoded in code | ❌ | Security violation |

### Implementation

**Localhost:** Environment variable
```bash
export GEMINI_API_KEY="your-key-here"
streamlit run app.py
```

**Streamlit Cloud:** Secrets management
```toml
# .streamlit/secrets.toml (NOT committed to git)
GEMINI_API_KEY = "your-key-here"
```

**In code:**
```python
import os
import streamlit as st

def get_gemini_api_key() -> str:
    """
    Get the Gemini API key from environment or Streamlit secrets.
    Admin-provided — SAs don't need their own key.
    """
    # Streamlit Cloud: secrets take priority
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]

    # Localhost: environment variable
    key = os.environ.get("GEMINI_API_KEY", "")
    return key
```

**In the UI:** No API key input. If the key is missing, show:
```
"RBAC Advisor requires configuration. Contact your admin to set up the Gemini API key."
```
