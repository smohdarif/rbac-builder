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
7. [Quick Reference Card](#quick-reference-card)

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
    response = self.chat.send_message(user_message, stream=True)
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
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction="You are an RBAC advisor. Always recommend least privilege..."
)

# USER MESSAGE: The conversation (sent with each turn)
chat = model.start_chat()
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

```python
class RBACAdvisor:
    def __init__(self, api_key: str):
        # 1. Validate inputs early
        if not api_key:
            raise AdvisorError("API key required")

        # 2. Configure the library
        genai.configure(api_key=api_key)

        # 3. Create the model instance
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        # 4. Chat session (created later with context)
        self.chat = None

    def set_context(self, teams, envs, project_key):
        # 5. Reinitialize model with system prompt
        self.model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=build_system_prompt(...)
        )
        # 6. Start fresh chat session
        self.chat = self.model.start_chat(history=[])
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

## Quick Reference Card

```python
# === Generator (streaming) ===
def stream(prompt) -> Generator[str, None, None]:
    for chunk in api.generate(prompt, stream=True):
        yield chunk.text

# === Regex: extract JSON from markdown ===
import re, json
matches = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
data = json.loads(matches[-1]) if matches else None

# === Streamlit chat ===
if user_input := st.chat_input("Message..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        for chunk in stream(user_input):
            full += chunk
            placeholder.markdown(full + "▌")
        placeholder.markdown(full)

# === Chat history in session_state ===
st.session_state.messages.append({"role": "user", "content": text})

# === API client error wrapping ===
try:
    response = client.generate(prompt)
except Exception as e:
    raise CustomError(f"API failed: {e}") from e

# === System prompt with structured output ===
system = f"""You are an advisor.
Available options: {options}
End response with ```json ... ``` block."""

# === Walrus operator ===
if value := expensive_call():  # assign AND check in one line
    use(value)
```

---

## Next Steps

- [← DESIGN.md](./DESIGN.md)
