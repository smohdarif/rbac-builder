# Phase 27: RBAC Advisor — AI-Powered Role Recommendations

| Field | Value |
|-------|-------|
| **Phase** | 27 |
| **Status** | ✅ Implemented |
| **Priority** | 🔴 High |
| **Goal** | Add an AI chat tab where SAs describe their customer's team structure and get RBAC best-practice recommendations before building the matrix |
| **Depends on** | Phase 15 (Tabbed Permission Groups — for structured output), Phase 5 (UI module pattern) |

---

## The Problem

SAs sit down with a customer and face this question: *"We have 5 teams, 3 environments — who should get what permissions?"*

Today, the SA needs to already know LaunchDarkly RBAC best practices, the principle of least privilege for each team archetype, and which permissions map to which roles. That's a lot of tribal knowledge.

## The Solution

A new **Tab 5: Role Designer AI** where the SA has a chat conversation with an AI that:

1. **Understands** the customer's team structure, environments, and goals
2. **Recommends** a concrete permission matrix based on LD RBAC best practices
3. **Explains** the reasoning behind each recommendation
4. **Outputs** a structured suggestion the SA can review and apply to the matrix

The SA goes from *"I think dev should have targeting in test?"* to *"The AI recommends this, here's why, and I can apply it with one click."*

---

## What the SA Sees

```
┌──────────────────────────────────────────────────────────────────────┐
│  🤖 RBAC Advisor                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─ Context Panel (sidebar/expander) ─────────────────────────────┐  │
│  │  Project: voya-web                                              │  │
│  │  Teams: Developer, QA, PO, SRE                                  │  │
│  │  Environments: test (non-critical), production (critical)       │  │
│  │  [✓] Auto-loaded from Setup tab                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─ Chat ──────────────────────────────────────────────────────────┐  │
│  │  🧑 We have 4 teams working on voya-web. Developers need to     │  │
│  │     create and manage flags in test but only view in prod.       │  │
│  │     QA needs to update targeting in test. POs just need to       │  │
│  │     view everything. SRE needs full access to prod.              │  │
│  │                                                                  │  │
│  │  🤖 Based on your setup and LaunchDarkly RBAC best practices,    │  │
│  │     here's my recommendation:                                    │  │
│  │                                                                  │  │
│  │     **Developer**                                                │  │
│  │     • Project: Create Flags ✅, Update Flags ✅, View Project ✅ │  │
│  │     • test: Update Targeting ✅, Manage Segments ✅              │  │
│  │     • production: View only (no targeting permissions)            │  │
│  │     💡 Why: Developers should iterate freely in test but prod    │  │
│  │        changes should go through approvals via SRE.              │  │
│  │                                                                  │  │
│  │     **QA**                                                       │  │
│  │     • Project: View Project ✅                                   │  │
│  │     • test: Update Targeting ✅, Manage Segments ✅              │  │
│  │     • production: Review Changes ✅ (can review but not apply)   │  │
│  │     💡 Why: QA validates in test, reviews prod changes.          │  │
│  │                                                                  │  │
│  │     ... (PO, SRE recommendations) ...                            │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────┐                      │  │
│  │  │ 📋 Apply to Matrix  │  💾 Save Chat    │                      │  │
│  │  └────────────────────────────────────────┘                      │  │
│  │                                                                  │  │
│  └─ [Type your message...] ────────────────────────── [Send] ──────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. LLM Provider: Google Gemini

| Option | Verdict | Reason |
|--------|---------|--------|
| Gemini (`google-genai` new SDK) | ✅ Chosen | User has API keys, generous free tier, good for structured output |
| Claude (anthropic) | ❌ | Potential conflict of interest (we ARE Claude building this) |
| OpenAI (openai) | ❌ | User didn't mention, extra cost |

### 2. Knowledge Source: Embedded Context + LD Docs

| Approach | Verdict | Reason |
|----------|---------|--------|
| System prompt with embedded RBAC knowledge | ✅ Primary | Fast, reliable, no network dependency at chat time |
| Live web fetch of LD docs | ✅ Supplementary | Can fetch latest docs on-demand for edge cases |
| RAG with vector DB | ❌ | Over-engineered for this use case |

### 3. Structured Output: Markdown + Parseable JSON

The AI returns both:
- **Human-readable markdown** (displayed in chat)
- **Structured JSON** (parsed to populate the matrix on "Apply")

### 4. Chat History: Session State

| Approach | Verdict | Reason |
|----------|---------|--------|
| `st.session_state.advisor_messages` | ✅ | Simple, matches Streamlit chat pattern |
| External DB | ❌ | Overkill for session-scoped conversations |

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, 20 test cases, implementation plan |
| [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) | **Master system prompt** with guardrails, token budget, cost analysis, API key management |
| [FEW_SHOT_EXAMPLES.md](./FEW_SHOT_EXAMPLES.md) | **6 grounded examples** from real customer data (sa-demo, Epassi, Voya, S2 template) — simple to complex |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: API clients, streaming, system prompts, JSON parsing, Streamlit chat components |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/ai_advisor.py` | CREATED — `RBACAdvisor` class (Gemini client via `google.genai`, system prompt, structured output) |
| `core/rbac_knowledge.py` | CREATED — Embedded RBAC best practices knowledge base |
| `ui/advisor_tab.py` | CREATED — Tab 5 "Role Designer AI" chat UI with context panel, versioned widget keys, thinking indicator, collapsible JSON |
| `ui/__init__.py` | UPDATED — Added `render_advisor_tab` export |
| `app.py` | UPDATED — Added Tab 5 |
| `.streamlit/secrets.toml` | ADD `GEMINI_API_KEY` (not committed to git) |
| `requirements.txt` | UPDATED — Added `google-genai>=1.0.0` |
| `tests/test_ai_advisor.py` | CREATED — 20 test cases |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [x] `core/rbac_knowledge.py` created — embedded LD RBAC knowledge
- [x] `services/ai_advisor.py` created — Gemini integration via `google.genai` SDK + structured output
- [x] `ui/advisor_tab.py` created — chat UI + context panel + apply button + versioned widget keys + thinking indicator + collapsible JSON
- [x] `ui/__init__.py` updated
- [x] `app.py` updated — Tab 5 "Role Designer AI"
- [x] `requirements.txt` updated — `google-genai>=1.0.0`
- [x] `tests/test_ai_advisor.py` created — all 20 tests passing
- [x] Manual test: full conversation → apply to matrix → verify matrix populated

---

## Known Issues / Lessons Learned

### Streamlit Widget Caching (Biggest Challenge)

Streamlit caches widget values by key. When the Advisor's Apply button writes `True` values into DataFrames (`project_matrix`, `env_matrix`), Streamlit's checkbox widgets in the Matrix tab still hold their old `False` values from the previous render. The DataFrame data is correct, but the widgets override it on the next rerun.

**Fix: Version-based widget keys.** Each time Apply runs, a version counter increments in `session_state`. Widget keys include this version (e.g., `key_prefix=f"proj_v{version}_{group}"`), forcing Streamlit to create fresh widgets that read from the updated DataFrame instead of using cached values.

The same issue affected `st.data_editor` widgets for teams and `env_groups` in the Setup tab. Fix: versioned keys like `key=f"teams_editor_v{version}"`.

### env_groups Stale Data

The Setup tab's `data_editor` restores old default `env_groups` (e.g., Test, Production) even after the Advisor writes 4 environments. Fix: The Matrix tab reads environment keys directly from `env_matrix` when the `_advisor_applied` flag is `True`, bypassing the stale `env_groups` data.

### st.secrets Crash on Missing secrets.toml

`"GEMINI_API_KEY" in st.secrets` raises `StreamlitSecretNotFoundError` when no `secrets.toml` file exists. Fix: wrap the check in `try/except` and use `st.secrets.get()`.

### API Timeout on First Call

The first Gemini call with a large system prompt can timeout. Fix: set `http_options={"timeout": 120_000}` (120 seconds) on the client.

### Two-Phase Apply with _advisor_applied Flag

The Matrix tab checks the `_advisor_applied` flag to skip its normal stale-data sync logic and trust the Advisor's data directly. The success banner persists across `st.rerun()` via a session_state flag.
