# Phase 15: Python Concepts

Concepts introduced when adding the tab-based grouped UI layout.

---

## Table of Contents

1. [st.tabs() — Streamlit Tabbed Layout](#1-sttabs--streamlit-tabbed-layout)
2. [Dict of Lists as a Grouping Structure](#2-dict-of-lists-as-a-grouping-structure)
3. [zip() — Pairing Two Lists Together](#3-zip--pairing-two-lists-together)
4. [List Slicing — tabs\[:-1\]](#4-list-slicing--tabs-1)
5. [Unique Widget Keys — Avoiding DuplicateWidgetID](#5-unique-widget-keys--avoiding-duplicatewidgetid)
6. [DataFrame.replace() — Display Formatting](#6-dataframereplace--display-formatting)
7. [Quick Reference Card](#quick-reference-card)
8. [Next Steps](#next-steps)

---

## 1. st.tabs() — Streamlit Tabbed Layout

### The concept

`st.tabs()` creates a row of clickable tabs. Each tab has its own content block. Only one tab is visible at a time.

```python
import streamlit as st

# Create 3 tabs — returns a list of tab objects
tabs = st.tabs(["🚩 Flags", "📊 Metrics", "🤖 AI Configs"])

# Use 'with' to put content inside each tab
with tabs[0]:
    st.write("Flag permissions go here")

with tabs[1]:
    st.write("Metrics permissions go here")

with tabs[2]:
    st.write("AI Config permissions go here")
```

### Unpacking tabs directly (cleaner syntax)

```python
# Instead of using index numbers, unpack into named variables
flag_tab, metrics_tab, ai_tab = st.tabs(["🚩 Flags", "📊 Metrics", "🤖 AI Configs"])

with flag_tab:
    st.write("Flag content")

with metrics_tab:
    st.write("Metrics content")
```

### Dynamic tab creation (our approach)

When you don't know how many tabs there are at write-time (it's driven by data), create them dynamically:

```python
group_names = list(PROJECT_PERMISSION_GROUPS.keys())
# → ["🚩 Flag Lifecycle", "📊 Metrics & Pipelines", "🤖 AI Configs", "🔭 Observability"]

tab_labels = group_names + ["📋 Summary"]
# → add Summary as the last tab

tabs = st.tabs(tab_labels)
# → list of tab objects, same length as tab_labels

# Pair each tab with its group name using zip (see section 3)
for tab, group_name in zip(tabs[:-1], group_names):
    with tab:
        render_group(group_name)

with tabs[-1]:
    render_summary()
```

### Streamlit gotcha: state is preserved across tabs

Streamlit re-runs the whole script when any widget changes. Tab selection is part of session state — the app remembers which tab the user was on.

```python
# GOTCHA: if you use st.tabs() in a loop, make sure tab labels are unique!
# Duplicate labels cause confusing behaviour (both tabs look the same)

# BAD
for group in groups:
    tabs = st.tabs(["Edit", "View"])   # "Edit" appears in every group!

# GOOD
tabs = st.tabs([name for name in groups] + ["Summary"])
```

---

## 2. Dict of Lists as a Grouping Structure

### The concept

`PROJECT_PERMISSION_GROUPS` maps a tab name to the list of permissions shown in that tab.

```python
PROJECT_PERMISSION_GROUPS: Dict[str, List[str]] = {
    "🚩 Flag Lifecycle": [
        "Create Flags",
        "Update Flags",
        "Archive Flags",
        "Update Client Side Availability",
    ],
    "🤖 AI Configs": [
        "Create AI Configs",
        "Update AI Configs",
        "Delete AI Configs",
        "Manage AI Variations",
    ],
    # ...
}
```

### Why a dict of lists?

This structure answers two questions simultaneously:
1. **What tabs exist?** → `PROJECT_PERMISSION_GROUPS.keys()`
2. **What permissions are in each tab?** → `PROJECT_PERMISSION_GROUPS[tab_name]`

```python
# Get all tab names
tab_names = list(PROJECT_PERMISSION_GROUPS.keys())
# → ["🚩 Flag Lifecycle", "📊 Metrics & Pipelines", ...]

# Get permissions for a specific tab
flag_perms = PROJECT_PERMISSION_GROUPS["🚩 Flag Lifecycle"]
# → ["Create Flags", "Update Flags", "Archive Flags", "Update Client Side Availability"]

# Iterate over all groups
for group_name, perms in PROJECT_PERMISSION_GROUPS.items():
    print(f"{group_name}: {len(perms)} permissions")
```

### The single source of truth principle

By putting groups in one constant, we avoid having the same list in multiple places. If we add a new permission, we change it in ONE place and the tabs, summary view, and matrix initialisation all update automatically.

```python
# BAD — same list in multiple places
FLAG_TAB_PERMS    = ["Create Flags", "Update Flags"]
SUMMARY_PERMS     = ["Create Flags", "Update Flags", ...]  # duplicate!
DEFAULT_MATRIX    = ["Create Flags", "Update Flags", ...]  # another duplicate!

# GOOD — one dict drives everything
PROJECT_PERMISSION_GROUPS = {"🚩 Flag Lifecycle": ["Create Flags", "Update Flags"]}

# Summary: flatten all groups
all_perms = [p for perms in PROJECT_PERMISSION_GROUPS.values() for p in perms]

# Matrix columns: same list
columns = all_perms
```

---

## 3. zip() — Pairing Two Lists Together

### The concept

`zip()` takes two (or more) iterables and pairs them element by element, stopping at the shortest.

```python
names  = ["Alice", "Bob", "Carol"]
scores = [85, 92, 78]

for name, score in zip(names, scores):
    print(f"{name}: {score}")
# Alice: 85
# Bob: 92
# Carol: 78
```

### Why we need it here

We have two parallel lists:
1. `tabs` — the tab objects from `st.tabs()`
2. `group_names` — the group name strings

We need to pair each tab with its group name to know which permissions to render inside it.

```python
group_names = list(PROJECT_PERMISSION_GROUPS.keys())
tabs        = st.tabs(group_names + ["📋 Summary"])

# Pair each tab (except last "Summary") with its group name
for tab, group_name in zip(tabs[:-1], group_names):
    with tab:
        perms = PROJECT_PERMISSION_GROUPS[group_name]
        render_permission_group(perms)
```

### zip() stops at the shortest list

```python
# tabs has 5 elements (4 groups + Summary)
# group_names has 4 elements
# zip stops after 4 pairs — Summary tab is handled separately

tabs       = [t1, t2, t3, t4, t5]   # 5 tabs
group_names = ["Flags", "Metrics", "AI", "Obs"]  # 4 names

list(zip(tabs, group_names))
# → [(t1, "Flags"), (t2, "Metrics"), (t3, "AI"), (t4, "Obs")]
# t5 (Summary) is NOT included — handled separately with tabs[-1]
```

---

## 4. List Slicing — tabs[:-1]

### The concept

Python list slicing lets you get a portion of a list using `[start:stop:step]`.

```python
my_list = [1, 2, 3, 4, 5]

my_list[0]    # → 1        (first element)
my_list[-1]   # → 5        (last element)
my_list[:-1]  # → [1,2,3,4] (all except last)
my_list[1:]   # → [2,3,4,5] (all except first)
my_list[1:3]  # → [2,3]    (index 1 up to but not including 3)
```

### Why we use `tabs[:-1]`

The last tab is always "📋 Summary". We want to loop over all tabs EXCEPT the last one (because Summary is rendered differently — read-only).

```python
tabs = st.tabs(["🚩 Flags", "📊 Metrics", "🤖 AI", "🔭 Obs", "📋 Summary"])
#                                                                 ↑ index [-1]

# Loop over all except Summary
for tab, group_name in zip(tabs[:-1], group_names):
    with tab:
        render_group(group_name)

# Handle Summary separately
with tabs[-1]:
    render_summary()
```

### Negative indexing

In Python, negative indices count from the end:

```python
my_list = ["a", "b", "c", "d"]
my_list[-1]   # → "d"   (last)
my_list[-2]   # → "c"   (second from last)
my_list[:-1]  # → ["a", "b", "c"]  (all except last)
my_list[:-2]  # → ["a", "b"]       (all except last two)
```

---

## 5. Unique Widget Keys — Avoiding DuplicateWidgetID

### The problem

Streamlit requires every interactive widget (checkbox, button, etc.) to have a unique `key`. If two checkboxes have the same key, Streamlit throws a `DuplicateWidgetID` error.

With multiple tabs, the same team + permission combination could generate the same key if we're not careful.

### Our solution: include the group name in the key

```python
# BAD — same key across tabs!
key = f"proj_{team_idx}_{perm_idx}"
# "proj_0_0" appears in Flag tab AND AI Config tab → DuplicateWidgetID!

# GOOD — group name makes key unique across tabs
key = f"proj_{group_key}_{team_idx}_{perm_idx}"
# "proj_🚩 Flag Lifecycle_0_0"   ← unique to Flag tab
# "proj_🤖 AI Configs_0_0"       ← unique to AI tab
```

### Why Streamlit needs unique keys

Streamlit re-runs the entire script on every interaction. Widget keys are how it tracks which widget changed. If two widgets share a key, it can't tell them apart.

```python
# Streamlit widget key rules:
# 1. Must be unique within the entire page
# 2. Can be any string or number
# 3. Should be stable across reruns (don't use random values)
# 4. Used to preserve widget state between reruns

st.checkbox("My checkbox", key="my_unique_key_123")
```

---

## 6. DataFrame.replace() — Display Formatting

### The concept

`DataFrame.replace()` swaps values in a DataFrame. We use it to convert `True`/`False` to more readable symbols for the Summary tab.

```python
import pandas as pd

df = pd.DataFrame({
    "Team":         ["Developer", "QA"],
    "Create Flags": [True,        False],
    "Update Flags": [True,        True],
})

# Replace booleans with display symbols
display_df = df.replace({True: "✅", False: "—"})

print(display_df)
#          Team  Create Flags  Update Flags
# 0  Developer            ✅            ✅
# 1         QA             —            ✅
```

### Why not modify the original DataFrame?

`.replace()` returns a **new** DataFrame — it doesn't modify the original. This is important because the original `project_matrix` must keep True/False values for the payload builder to work.

```python
# GOOD — display_df is a copy with symbols, original df unchanged
display_df = df.replace({True: "✅", False: "—"})
st.dataframe(display_df)

# BAD — this would corrupt the original data!
df.replace({True: "✅", False: "—"}, inplace=True)
# Now payload builder gets "✅" instead of True → broken
```

### `.copy()` vs `.replace()`

```python
# .copy() makes a shallow copy (same data)
df2 = df.copy()

# .replace() makes a copy AND transforms values
df2 = df.replace({True: "✅"})

# For our use case, .replace() alone is enough
# (it already creates a new object, no need for .copy() first)
```

---

## Quick Reference Card

```python
# st.tabs() — create tabbed sections
tabs = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
with tabs[0]: st.write("Tab 1 content")
with tabs[1]: st.write("Tab 2 content")

# dict.items() — iterate key + value pairs
for group_name, perms in MY_DICT.items():
    print(group_name, perms)

# zip() — pair two lists
for tab, name in zip(tabs, names):
    with tab: render(name)

# List slicing
my_list[:-1]    # all except last
my_list[-1]     # last element only
my_list[1:]     # all except first

# Unique widget keys across tabs
key = f"proj_{group_key}_{team_idx}_{perm_idx}"

# DataFrame.replace() for display (non-destructive)
display_df = df.replace({True: "✅", False: "—"})
# original df is unchanged
```

---

## Next Steps

→ [DESIGN.md](./DESIGN.md) — Full implementation plan
