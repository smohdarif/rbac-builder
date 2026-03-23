# Phase 27: RBAC Advisor — AI-Powered Role Recommendations

| Field | Value |
|-------|-------|
| **Phase** | 27 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Priority** | 🔴 High |
| **Goal** | Add an AI chat tab where SAs describe their customer's team structure and get RBAC best-practice recommendations before building the matrix |
| **Depends on** | Phase 15 (Tabbed Permission Groups — for structured output), Phase 5 (UI module pattern) |

---

## The Problem

SAs sit down with a customer and face this question: *"We have 5 teams, 3 environments — who should get what permissions?"*

Today, the SA needs to already know LaunchDarkly RBAC best practices, the principle of least privilege for each team archetype, and which permissions map to which roles. That's a lot of tribal knowledge.

## The Solution

A new **Tab 5: RBAC Advisor** where the SA has a chat conversation with an AI that:

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
| Gemini (google-generativeai) | ✅ Chosen | User has API keys, generous free tier, good for structured output |
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
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, 12 test cases, implementation plan |
| [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) | **Master system prompt** with guardrails, token budget, cost analysis, API key management |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: API clients, streaming, system prompts, JSON parsing, Streamlit chat components |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/ai_advisor.py` | CREATE — `RBACAdvisor` class (Gemini client, system prompt, structured output) |
| `core/rbac_knowledge.py` | CREATE — Embedded RBAC best practices knowledge base |
| `ui/advisor_tab.py` | CREATE — Tab 5 chat UI with context panel |
| `ui/__init__.py` | ADD `render_advisor_tab` export |
| `app.py` | ADD Tab 5 |
| `.streamlit/secrets.toml` | ADD `GEMINI_API_KEY` (not committed to git) |
| `requirements.txt` | ADD `google-generativeai>=0.8.0` |
| `tests/test_ai_advisor.py` | CREATE — 12 test cases |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [ ] `core/rbac_knowledge.py` created — embedded LD RBAC knowledge
- [ ] `services/ai_advisor.py` created — Gemini integration + structured output
- [ ] `ui/advisor_tab.py` created — chat UI + context panel + apply button
- [ ] `ui/__init__.py` updated
- [ ] `app.py` updated — Tab 5 + API key input
- [ ] `requirements.txt` updated
- [ ] `tests/test_ai_advisor.py` created — all 12 tests passing
- [ ] Manual test: full conversation → apply to matrix → verify matrix populated
