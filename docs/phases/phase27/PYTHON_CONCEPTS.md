# Phase 27: Python Concepts

Concepts introduced when building an AI-powered chat advisor with Gemini integration.

---

## Table of Contents

1. [Generator Functions and `yield` — Streaming Responses](#1-generator-functions-and-yield--streaming-responses)
2. [Regex with `re.DOTALL` — Extracting JSON from Markdown](#2-regex-with-redotall--extracting-json-from-markdown)
3. [Prompt Engineering — System Prompts and Structured Output](#3-prompt-engineering--system-prompts-and-structured-output)
4. [Streamlit Chat Components — `st.chat_message` and `st.chat_input`](#4-streamlit-chat-components--stchat_message-and-stchat_input)
5. [Live Streaming UI with `st.empty()`](#5-live-streaming-ui-with-stempty)
6. [API Client Pattern — Configuration, Sessions, Error Handling](#6-api-client-pattern--configuration-sessions-error-handling)
7. [Streamlit Widget Key Versioning — Solving the Caching Bug](#7-streamlit-widget-key-versioning--solving-the-caching-bug)
8. [JavaScript Injection — Controlling the Browser from Python](#8-javascript-injection--controlling-the-browser-from-python)
9. [Collapsible Content — `st.expander` for Long Outputs](#9-collapsible-content--stexpander-for-long-outputs)
10. [Session State Flags — Coordinating Across Tabs](#10-session-state-flags--coordinating-across-tabs)
11. [Quick Reference Card](#quick-reference-card)

---

## 1. Generator Functions and `yield` — Streaming Responses

### The concept

A **generator function** uses `yield` instead of `return`. It produces values one at a time, pausing between each one. This is perfect for streaming API responses — show each chunk to the user as it arrives instead of waiting for the full response.

```python
# REGULAR function: computes everything, returns once
def get_full_response(prompt):
    response = api.generate(prompt)     # waits for entire response
    return response.text                 # returns all at once

# GENERATOR function: yields chunks as they arrive
def stream_response(prompt):
    response = api.generate(prompt, stream=True)
    for chunk in response:               # API sends chunks
        yield chunk.text                  # yield each one immediately
```

### How generators work under the hood

```python
def count_up_to(n):
    i = 1
    while i <= n:
        yield i      # pause here, return i to caller
        i += 1       # resume here on next call

# Usage
gen = count_up_to(3)   # creates the generator (doesn't run yet!)
next(gen)              # 1 (runs until first yield)
next(gen)              # 2 (resumes, runs to next yield)
next(gen)              # 3
next(gen)              # StopIteration (no more yields)

# Usually consumed with a for loop:
for num in count_up_to(3):
    print(num)         # 1, 2, 3
```

### In our AI advisor

```python
def stream_recommendation(self, user_message: str) -> Generator[str, None, None]:
    """Yield response chunks as they arrive from Gemini."""
    # New SDK: send_message_stream() instead of send_message(stream=True)
    response = self.chat.send_message_stream(user_message)
    for chunk in response:
        if chunk.text:
            yield chunk.text

# In the UI — show text as it streams:
full_response = ""
for chunk in advisor.stream_recommendation("What should dev get?"):
    full_response += chunk
    placeholder.markdown(full_response + "▌")  # cursor effect
```

### `Generator[str, None, None]` type hint explained

```python
from typing import Generator

# Generator[YieldType, SendType, ReturnType]
#   YieldType: what yield produces   → str (text chunks)
#   SendType:  what .send() accepts  → None (we don't send values in)
#   ReturnType: what return produces → None (no final return value)

def my_gen() -> Generator[str, None, None]:
    yield "hello"
    yield "world"
```

### When to use generators vs lists

```python
# Use a LIST when you need all values at once
all_items = [process(x) for x in data]  # entire list in memory

# Use a GENERATOR when:
# 1. Data arrives over time (streaming API)
# 2. Data is too large to fit in memory
# 3. You want to start processing before everything is ready
for chunk in stream_response(prompt):   # process each chunk immediately
    display(chunk)
```

---

## 2. Regex with `re.DOTALL` — Extracting JSON from Markdown

### The problem

The AI returns a response like:
```
Here's my recommendation for your team...

```json
{"recommendation": {"project": {"Dev": {"Create Flags": true}}}}
```​

We need to extract just the JSON part.
```

### The solution

```python
import re

pattern = r"```json\s*(.*?)\s*```"
matches = re.findall(pattern, response_text, re.DOTALL)

if matches:
    json_str = matches[-1]    # use the LAST match
    data = json.loads(json_str)
```

### Breaking down the regex

```
```json      ← literal text (the opening fence)
\s*          ← optional whitespace/newlines after the fence
(.*?)        ← capture group: the JSON content (non-greedy)
\s*          ← optional whitespace/newlines before closing fence
```​          ← literal text (the closing fence)
```

### Why `re.DOTALL`?

```python
# Without DOTALL: . matches any character EXCEPT newlines
# The JSON spans multiple lines, so .* would stop at the first \n

text = "```json\n{\n  \"key\": true\n}\n```"

re.findall(r"```json\s*(.*?)\s*```", text)            # [] — no match!
re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)  # ['{\n  "key": true\n}']
#                                          ^^^^^^^^^ now . matches \n too
```

### Why `.*?` (non-greedy) and `matches[-1]`?

```python
# .*  (greedy) — matches as MUCH as possible
# .*? (non-greedy) — matches as LITTLE as possible

# Non-greedy ensures we match each ```json...``` block individually,
# not one giant match from first ``` to last ```.

# We use matches[-1] because the AI might include example JSON early
# in the response, and the actual recommendation is always at the end.
```

---

## 3. Prompt Engineering — System Prompts and Structured Output

### System prompt vs user message

```python
# SYSTEM PROMPT: Sets the AI's persona and rules (sent once)
# Think of it as the AI's "job description"
# New SDK: system_instruction goes in GenerateContentConfig, not model constructor
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction="You are an RBAC advisor. Always recommend least privilege..."
    ),
)

# USER MESSAGE: The conversation (sent with each turn)
response = chat.send_message("What should my dev team get?")
```

### Structured output technique

The key challenge: we need the AI to return both **readable explanation** (for the SA) and **parseable JSON** (for the Apply button). The trick: instruct it to include a JSON block at the end.

```python
system_prompt = """
...

When providing a recommendation, end your response with a JSON block:

```json
{
  "recommendation": {
    "project": {
      "TeamName": {"Create Flags": true, "View Project": true}
    },
    "environment": {
      "TeamName": {
        "env-key": {"Update Targeting": true}
      }
    }
  }
}
```​

Only include permissions that are TRUE.
Use the exact permission names from the available list.
"""
```

### Why not ask for ONLY JSON?

```python
# BAD — AI returns only JSON, no explanation
# The SA can't understand WHY each permission was chosen
"Return only a JSON object with the recommendation."

# GOOD — AI explains reasoning AND includes structured data
# SA reads the explanation, then clicks "Apply" to use the JSON
"Explain your reasoning, then include a ```json block at the end."
```

### Grounding with domain knowledge

```python
# Without grounding: AI makes up plausible-sounding but wrong recommendations
# With grounding: AI is constrained to real LD permissions and patterns

system_prompt = f"""
## Available Permissions (ONLY use these exact names)
Project-scoped: {", ".join(project_perms)}
Environment-scoped: {", ".join(env_perms)}

## Customer Context
Teams: {teams}
Environments: {envs}

## Best Practices
{TEAM_ARCHETYPES}
{ENVIRONMENT_PATTERNS}
{ANTI_PATTERNS}
"""
```

---

## 4. Streamlit Chat Components — `st.chat_message` and `st.chat_input`

### The basics

Streamlit has built-in chat UI components (added in v1.26):

```python
# Chat input — text box pinned to bottom of the page
user_input = st.chat_input("Type your message...")

# Chat message — displays a message with an avatar
with st.chat_message("user"):
    st.markdown("Hello, I need RBAC help")

with st.chat_message("assistant"):
    st.markdown("Sure! Tell me about your teams.")
```

### Chat history pattern

```python
# Initialize history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if user_input := st.chat_input("Message..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate and display response
    with st.chat_message("assistant"):
        response = get_ai_response(user_input)
        st.markdown(response)

    # Add response to history
    st.session_state.messages.append({"role": "assistant", "content": response})
```

### The walrus operator `:=`

```python
# Standard way:
user_input = st.chat_input("Message...")
if user_input:
    process(user_input)

# Walrus operator (Python 3.8+): assign AND check in one line
if user_input := st.chat_input("Message..."):
    process(user_input)

# Works because:
# 1. st.chat_input() returns the text or None
# 2. := assigns the value to user_input
# 3. if checks if it's truthy (not None, not empty string)
```

---

## 5. Live Streaming UI with `st.empty()`

### The concept

`st.empty()` creates a placeholder element that can be **overwritten** repeatedly. This is how we show streaming text — update the same element with progressively longer text.

```python
# Create a placeholder
placeholder = st.empty()

# Update it repeatedly (each call REPLACES the previous content)
placeholder.markdown("H")
placeholder.markdown("He")
placeholder.markdown("Hel")
placeholder.markdown("Hell")
placeholder.markdown("Hello")

# The user sees the text "typing" character by character
```

### Streaming pattern for AI responses

```python
with st.chat_message("assistant"):
    placeholder = st.empty()
    full_response = ""

    for chunk in advisor.stream_recommendation(user_input):
        full_response += chunk
        placeholder.markdown(full_response + "▌")   # cursor effect
        #                                    ^^^ Unicode "▌" looks like a typing cursor

    placeholder.markdown(full_response)   # final render without cursor
```

### Why `st.empty()` and not `st.markdown()` in a loop?

```python
# BAD — each st.markdown() adds a NEW element
for chunk in chunks:
    st.markdown(chunk)
# Result: dozens of separate text blocks on the page

# GOOD — st.empty() replaces the SAME element
placeholder = st.empty()
for chunk in chunks:
    full += chunk
    placeholder.markdown(full)
# Result: one text block that grows over time
```

---

## 6. API Client Pattern — Configuration, Sessions, Error Handling

### The pattern

**Important:** We use `google.genai` (new SDK), not `google.generativeai` (deprecated).
The key differences:
- Client: `genai.Client(api_key=...)` instead of `genai.configure()`
- Chat: `client.chats.create()` instead of `model.start_chat()`
- Streaming: `chat.send_message_stream()` instead of `chat.send_message(stream=True)`

```python
from google import genai
from google.genai import types

class RBACAdvisor:
    def __init__(self, api_key: str):
        # 1. Validate inputs early
        if not api_key:
            raise AdvisorError("API key required")

        # 2. Create client (new SDK pattern — replaces genai.configure())
        self.client = genai.Client(
            api_key=api_key,
            http_options={"timeout": 120_000},  # 120s for first call with large system prompt
        )

        # 3. Chat session (created later with context)
        self.chat = None

    def set_context(self, teams, envs, project_key):
        # 4. Create chat with system prompt (replaces model.start_chat())
        self.chat = self.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(...),
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
```

### Error wrapping

```python
# BAD — let library exceptions bubble up (confusing for caller)
response = self.chat.send_message(msg)   # raises google.api_core.exceptions.InvalidArgument

# GOOD — wrap in domain-specific exception
try:
    response = self.chat.send_message(msg)
except Exception as e:
    raise AdvisorError(f"Gemini API error: {e}") from e
    #                                            ^^^^^^^^
    # 'from e' chains the exceptions — the original error is preserved
    # in __cause__ for debugging, but the caller sees AdvisorError
```

### Why `from e`?

```python
try:
    risky_operation()
except ValueError as e:
    raise CustomError("Something went wrong") from e

# Without 'from e': Python prints both exceptions but with a confusing
# "During handling of the above exception, another exception occurred"

# With 'from e': Python prints "The above exception was the direct cause
# of the following exception" — much clearer for debugging
```

---

## 7. Streamlit Widget Key Versioning — Solving the Caching Bug

### The problem

This was the biggest challenge in Phase 27. Streamlit caches widget values by their `key`. When the Advisor's Apply button writes `True` values into DataFrames (`project_matrix`, `env_matrix`), the checkbox widgets in the Matrix tab still hold their old `False` values from a previous render.

```python
# BAD — widget key is static. Streamlit returns the CACHED value (False),
# ignoring the updated DataFrame value (True).
st.checkbox(perm, value=df_value, key=f"proj_{group}_{team}_{perm}")
# Even though df_value is now True, the widget returns its cached False!
```

### Why this happens

Streamlit's widget lifecycle:
1. First render: widget created with `key="proj_flagMgmt_Dev_CreateFlags"`, value=False
2. User interacts, Streamlit caches `False` for that key
3. Apply writes `True` to the DataFrame
4. Next render: same key exists in cache, so Streamlit uses cached `False` — ignores the DataFrame

### The fix: version-based keys

```python
# GOOD — include a version number in the key. When version changes,
# Streamlit sees a NEW key and creates a fresh widget from the DataFrame.
version = st.session_state.get("_widget_version", 0)
st.checkbox(perm, value=df_value, key=f"proj_v{version}_{group}_{team}_{perm}")

# In _apply_recommendation():
st.session_state["_widget_version"] = st.session_state.get("_widget_version", 0) + 1
```

### Same fix for st.data_editor

The Setup tab's `st.data_editor` for teams and `env_groups` had the exact same issue:

```python
# BAD — static key, data_editor restores old cached values
st.data_editor(teams_df, key="teams_editor")

# GOOD — versioned key forces fresh widget
version = st.session_state.get("_widget_version", 0)
st.data_editor(teams_df, key=f"teams_editor_v{version}")
```

### When you need this pattern

Use version-based keys whenever:
1. Code (not the user) writes data to session_state
2. Widgets need to reflect that programmatic change
3. The widget key would otherwise stay the same between reruns

You do NOT need this when the user directly interacts with the widget (Streamlit handles that natively).

---

## 8. JavaScript Injection — Controlling the Browser from Python

### The concept

Streamlit doesn't support programmatic tab switching. But we can inject JavaScript into the page via `streamlit.components.v1.html()`. This creates a tiny invisible iframe that runs our script in the browser.

```python
import streamlit.components.v1 as components

# Inject invisible JS into the page
components.html(
    """
    <script>
    // This runs in the USER'S BROWSER, not on the server
    console.log("Hello from injected JS!");
    </script>
    """,
    height=0,         # invisible — no UI footprint
    scrolling=False,
)
```

### Accessing the parent page's DOM

The injected iframe can access the main Streamlit page via `window.parent.document`:

```python
components.html("""
    <script>
    // Find all tab buttons in the Streamlit page
    var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
    // Click the second tab (Design Matrix)
    if (tabs.length >= 2) {
        tabs[1].click();
    }
    </script>
""", height=0)
```

### Why index-based, not text-based?

```javascript
// BAD — tab labels include emojis and numbering ("📊 2. Design Matrix")
// innerText.indexOf('Design Matrix') works in theory but is fragile
if (tabs[i].innerText.indexOf('Design Matrix') !== -1) { ... }

// GOOD — target by position (more reliable)
// Tab order: 0=Setup, 1=Design Matrix, 2=Deploy, 3=Reference, 4=Role Designer
tabs[1].click();
```

### Retry pattern for DOM timing

The tab buttons may not exist in the DOM when our script first runs (Streamlit renders progressively). Solution: retry with `setInterval`:

```javascript
var attempts = 0;
var interval = setInterval(function() {
    attempts++;
    var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
    if (tabs.length >= 2) {
        tabs[1].click();
        clearInterval(interval);   // stop retrying
    } else if (attempts >= 10) {
        clearInterval(interval);   // give up after 2 seconds
    }
}, 200);  // try every 200ms
```

### GOTCHA: `st.markdown` strips `<script>` tags

```python
# BAD — Streamlit sanitizes script tags, even with unsafe_allow_html
st.markdown("<script>alert('hi')</script>", unsafe_allow_html=True)
# Result: script tag is REMOVED, nothing happens

# GOOD — components.html creates an iframe that CAN run scripts
components.html("<script>alert('hi')</script>", height=0)
# Result: script runs in the iframe
```

### Graceful degradation

If the JS fails (DOM changes, browser blocks), nothing breaks — the success banner is still visible and the user can click the tab manually. This is the "Option D" pattern: try the best approach, fall back silently.

---

## 9. Collapsible Content — `st.expander` for Long Outputs

### The concept

AI responses include both readable explanation and a large JSON block. Showing the raw JSON inline is overwhelming. `st.expander` collapses it into a toggleable section:

```python
# Before: JSON clutters the chat
st.markdown(full_response)  # explanation + huge JSON blob

# After: JSON tucked away
st.markdown(explanation_text)
with st.expander("📋 View JSON Recommendation", expanded=False):
    st.markdown(json_block)
```

### Splitting response into explanation + JSON

```python
import re

def _render_message_content(content: str) -> None:
    """Render message with collapsible JSON blocks."""
    # Split on the last ```json ... ``` block
    pattern = r"(```json\s*.*?\s*```)"
    parts = re.split(pattern, content, flags=re.DOTALL)

    if len(parts) > 1:
        # Everything before JSON
        before = "".join(parts[:-2]).strip()
        json_block = parts[-2]       # the ```json...``` block
        after = parts[-1].strip()    # anything after

        if before:
            st.markdown(before)
        with st.expander("📋 View JSON Recommendation", expanded=False):
            st.markdown(json_block)
        if after:
            st.markdown(after)
    else:
        st.markdown(content)
```

### `re.split` with a capture group

```python
# re.split WITHOUT capture group — delimiters are REMOVED
re.split(r"---", "a---b---c")
# → ['a', 'b', 'c']  (delimiters gone)

# re.split WITH capture group () — delimiters are KEPT
re.split(r"(---)", "a---b---c")
# → ['a', '---', 'b', '---', 'c']  (delimiters preserved as elements)

# We use a capture group so the JSON block is preserved in the output:
re.split(r"(```json\s*.*?\s*```)", response, flags=re.DOTALL)
# → ['explanation text', '```json\n{...}\n```', 'trailing text']
```

### Rendering in chat history vs streaming

```python
# During streaming: show raw markdown (can't use expander inside st.empty)
placeholder = st.empty()
placeholder.markdown(full_response + "▌")

# After streaming completes: replace with collapsible version
placeholder.empty()
_render_message_content(full_response)

# In chat history replay: always use collapsible version
for msg in messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            _render_message_content(msg["content"])
        else:
            st.markdown(msg["content"])
```

---

## 10. Session State Flags — Coordinating Across Tabs

### The concept

Streamlit reruns ALL tabs on every interaction. When the Advisor (Tab 5) writes data that the Matrix tab (Tab 2) needs to read differently, we use session_state flags to coordinate:

```python
# Tab 5 (Advisor) — sets flags during Apply
st.session_state["_advisor_applied"] = True       # Matrix tab: skip stale sync
st.session_state["_advisor_show_success"] = True   # Advisor tab: show banner + navigate
st.session_state["_matrix_version"] = version + 1  # All tabs: fresh widget keys
st.session_state["_advisor_customer_name"] = name   # Sidebar: pre-fill customer name

# Tab 2 (Matrix) — reads the flag
if st.session_state.get("_advisor_applied"):
    # Trust the Advisor's data, don't sync from Setup
    env_keys = env_matrix["Environment"].unique().tolist()
```

### Flag lifecycle

```
Apply clicked (Tab 5)
  → _advisor_applied = True
  → _advisor_show_success = True
  → _matrix_version += 1
  → st.rerun()

Rerun starts:
  Tab 1 (Setup):  reads _matrix_version → versioned data_editor keys
  Tab 2 (Matrix): reads _advisor_applied → skips stale sync, trusts data
  Tab 5 (Advisor): reads _advisor_show_success → shows banner + JS navigate
                   sets _advisor_show_success = False (consumed)
```

### Naming convention

```python
# Prefix with _ to indicate "internal, not user-facing"
st.session_state["_advisor_applied"]         # bool flag
st.session_state["_advisor_show_success"]    # bool flag
st.session_state["_advisor_customer_name"]   # str value
st.session_state["_matrix_version"]          # int counter

# No prefix for user-facing data
st.session_state["teams"]                    # DataFrame
st.session_state["env_groups"]               # DataFrame
st.session_state["project_matrix"]           # DataFrame
```

### GOTCHA: Flags must be consumed

```python
# BAD — flag stays True forever, re-triggers on every rerun
if st.session_state.get("_advisor_applied"):
    do_special_thing()
# Next rerun: still True → does the special thing again!

# GOOD — consume the flag after use
if st.session_state.get("_advisor_show_success"):
    show_banner()
    st.session_state["_advisor_show_success"] = False  # consumed
```

---

## Quick Reference Card

```python
# === Generator (streaming) ===
def stream(prompt) -> Generator[str, None, None]:
    for chunk in chat.send_message_stream(prompt):  # new SDK
        yield chunk.text

# === Regex: extract JSON from markdown ===
import re, json
matches = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
data = json.loads(matches[-1]) if matches else None

# === re.split with capture group (keep delimiters) ===
parts = re.split(r"(```json\s*.*?\s*```)", text, flags=re.DOTALL)
# → ['explanation', '```json\n{...}\n```', 'trailing']

# === Streamlit chat with thinking indicator ===
if user_input := st.chat_input("Message..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("*Thinking...*")
        full = ""
        for chunk in stream(user_input):
            full += chunk
            placeholder.markdown(full + "▌")
        placeholder.empty()
        _render_message_content(full)  # collapsible JSON

# === Collapsible content ===
with st.expander("📋 View JSON", expanded=False):
    st.markdown(json_block)

# === Chat history in session_state ===
st.session_state.messages.append({"role": "user", "content": text})

# === API client (google.genai new SDK) ===
from google import genai
from google.genai import types
client = genai.Client(api_key=key, http_options={"timeout": 120_000})
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(system_instruction=system),
)

# === API client error wrapping ===
try:
    response = chat.send_message(prompt)
except Exception as e:
    raise CustomError(f"API failed: {e}") from e

# === Widget key versioning (Streamlit caching fix) ===
version = st.session_state.get("_matrix_version", 0)
st.checkbox(label, value=df_val, key=f"proj_v{version}_{group}_{idx}")
st.data_editor(df, key=f"editor_v{version}")

# === JS injection (tab switching, browser control) ===
import streamlit.components.v1 as components
components.html("<script>window.parent.document...</script>", height=0)
# NOTE: st.markdown strips <script> tags — use components.html instead

# === Session state flags (cross-tab coordination) ===
st.session_state["_advisor_applied"] = True       # matrix: skip sync
st.session_state["_advisor_show_success"] = True   # advisor: navigate
st.session_state["_matrix_version"] += 1           # all: fresh widgets
# Always consume flags after use:
st.session_state["_advisor_show_success"] = False

# === st.secrets safe access ===
try:
    key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    key = ""  # no secrets.toml

# === Walrus operator ===
if value := expensive_call():  # assign AND check in one line
    use(value)
```

---

## Next Steps

- [← DESIGN.md](./DESIGN.md)
