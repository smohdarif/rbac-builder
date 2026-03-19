# Phase 8: Python Concepts - Streamlit Advanced Patterns

## Table of Contents

1. [Streamlit Session State Deep Dive](#1-streamlit-session-state-deep-dive)
2. [Button Behavior and Callbacks](#2-button-behavior-and-callbacks)
3. [Progress Indicators](#3-progress-indicators)
4. [Password and Sensitive Inputs](#4-password-and-sensitive-inputs)
5. [Conditional Rendering](#5-conditional-rendering)
6. [Rerun and State Management](#6-rerun-and-state-management)
7. [Error Handling in UI](#7-error-handling-in-ui)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. Streamlit Session State Deep Dive

### The Rerun Problem

Every time a user interacts with a Streamlit widget, the ENTIRE script reruns from top to bottom. Without session state, all variables would reset.

```python
# =============================================================================
# LESSON: Without Session State - Variables Reset
# =============================================================================

# BAD: Counter resets to 0 on every button click!
counter = 0

if st.button("Increment"):
    counter += 1  # This runs, but...

st.write(f"Counter: {counter}")  # Always shows 0!

# WHY? The script reruns, counter = 0 executes again before we can use it


# GOOD: Session state persists across reruns
if "counter" not in st.session_state:
    st.session_state.counter = 0

if st.button("Increment"):
    st.session_state.counter += 1

st.write(f"Counter: {st.session_state.counter}")  # Works! Shows 1, 2, 3...
```

### Session State Patterns

```python
# =============================================================================
# LESSON: Common Session State Patterns
# =============================================================================

# Pattern 1: Initialize with default
if "value" not in st.session_state:
    st.session_state.value = "default"

# Pattern 2: Get with default (doesn't create key)
value = st.session_state.get("value", "default")

# Pattern 3: Direct access (raises KeyError if missing)
value = st.session_state.value  # Only if you're sure it exists

# Pattern 4: Update value
st.session_state.value = "new_value"

# Pattern 5: Delete key
if "temp_value" in st.session_state:
    del st.session_state.temp_value

# Pattern 6: Check existence
if "api_key" in st.session_state and st.session_state.api_key:
    # API key exists and is not empty
    pass
```

### Session State for Deployment

```python
# =============================================================================
# LESSON: Deployment State Management
# =============================================================================

def initialize_deploy_state():
    """Initialize all deployment-related session state."""

    defaults = {
        # API Configuration
        "ld_api_key": "",
        "ld_connection_verified": False,
        "ld_connection_error": None,

        # Deployment Options
        "deploy_dry_run": False,
        "deploy_skip_existing": True,

        # Deployment State
        "deploy_in_progress": False,
        "deploy_progress": 0.0,
        "deploy_steps": [],
        "deploy_result": None,

        # For rollback
        "deployer_instance": None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# Call at start of deploy tab
initialize_deploy_state()
```

---

## 2. Button Behavior and Callbacks

### Button Click Detection

```python
# =============================================================================
# LESSON: Button Returns True Once
# =============================================================================
# st.button returns True ONLY on the rerun triggered by clicking it

if st.button("Click Me"):
    # This code runs ONCE when button is clicked
    st.write("Button was clicked!")
    # On the NEXT rerun (any interaction), this won't run

# GOTCHA: If you have two buttons, clicking one causes a rerun
# where the other button's code won't execute

button1 = st.button("Button 1")
button2 = st.button("Button 2")

if button1:
    st.write("You clicked Button 1")
    # This only shows briefly, disappears on next rerun

if button2:
    st.write("You clicked Button 2")
```

### Persisting Button Results

```python
# =============================================================================
# LESSON: Persist Button Actions in Session State
# =============================================================================

# GOOD: Store the result of button action
if st.button("Test Connection"):
    # Do the test
    result = test_api_connection()

    # Store result in session state
    st.session_state.connection_result = result
    st.session_state.connection_tested = True

# Display result (persists across reruns)
if st.session_state.get("connection_tested"):
    if st.session_state.connection_result:
        st.success("Connection successful!")
    else:
        st.error("Connection failed!")
```

### Disabling Buttons Based on State

```python
# =============================================================================
# LESSON: Conditional Button States
# =============================================================================

# Button disabled based on conditions
api_key = st.session_state.get("api_key", "")
connection_verified = st.session_state.get("connection_verified", False)
is_deploying = st.session_state.get("deploy_in_progress", False)

# Build the disabled condition
deploy_disabled = (
    not api_key or          # No API key
    not connection_verified or  # Not verified
    is_deploying            # Already deploying
)

# Render button with disabled state
if st.button("Deploy", disabled=deploy_disabled):
    execute_deployment()

# Show why button is disabled
if deploy_disabled:
    if not api_key:
        st.caption("Enter API key to enable deployment")
    elif not connection_verified:
        st.caption("Test connection first")
    elif is_deploying:
        st.caption("Deployment in progress...")
```

---

## 3. Progress Indicators

### Simple Progress Bar

```python
# =============================================================================
# LESSON: st.progress for Simple Progress
# =============================================================================

import time

# Create progress bar (value 0.0 to 1.0)
progress_bar = st.progress(0)

for i in range(100):
    time.sleep(0.01)
    progress_bar.progress((i + 1) / 100)

st.success("Complete!")
```

### Progress with Status Text

```python
# =============================================================================
# LESSON: Progress with Dynamic Status
# =============================================================================

progress_bar = st.progress(0)
status_text = st.empty()  # Placeholder for status

items = ["Role 1", "Role 2", "Team 1"]

for i, item in enumerate(items):
    # Update status
    status_text.text(f"Processing: {item}")

    # Do work
    time.sleep(0.5)

    # Update progress
    progress_bar.progress((i + 1) / len(items))

status_text.text("All done!")
```

### Progress in Deployment (The Challenge)

```python
# =============================================================================
# LESSON: Progress Callbacks with Streamlit
# =============================================================================

# CHALLENGE: Streamlit doesn't update UI mid-script
# The progress callback runs, but UI only updates after script completes

# APPROACH 1: Show spinner during deployment, results after
with st.spinner("Deploying..."):
    result = deployer.deploy_all(payload)

# Display results after completion
st.progress(1.0)  # Show complete
for step in result.steps:
    if step.status == DeployStep.COMPLETED:
        st.success(f"✅ {step.resource_key}")
    elif step.status == DeployStep.SKIPPED:
        st.info(f"⏭️ {step.resource_key}")


# APPROACH 2: Store steps in session state, callback updates it
def create_progress_callback():
    def callback(step, current, total):
        # Store in session state (for display after completion)
        if "deploy_steps" not in st.session_state:
            st.session_state.deploy_steps = []
        st.session_state.deploy_steps.append(step)
        st.session_state.deploy_progress = current / total
    return callback


# APPROACH 3: Use experimental_rerun (advanced, can cause issues)
# Not recommended for long operations
```

---

## 4. Password and Sensitive Inputs

### Secure Password Input

```python
# =============================================================================
# LESSON: Password Input Field
# =============================================================================

# type="password" hides the input
api_key = st.text_input(
    "API Key",
    type="password",
    placeholder="Enter your API key...",
    help="Your LaunchDarkly API key"
)

# The value is still accessible in Python
if api_key:
    st.write(f"Key length: {len(api_key)} characters")
    # Never display the actual key!
```

### Security Best Practices

```python
# =============================================================================
# LESSON: Handling Sensitive Data
# =============================================================================

# DO: Store in session state only (not persisted)
st.session_state.api_key = api_key

# DON'T: Include in saved configuration
def save_config():
    config = {
        "customer_name": st.session_state.customer_name,
        "project_key": st.session_state.project_key,
        # "api_key": st.session_state.api_key  # NEVER save API keys!
    }
    return config


# DO: Clear sensitive data when done
def on_logout():
    if "api_key" in st.session_state:
        del st.session_state.api_key


# DO: Mask in logs/display
def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]

st.write(f"Using key: {mask_key(api_key)}")
```

---

## 5. Conditional Rendering

### Mode-Based UI

```python
# =============================================================================
# LESSON: Show Different UI Based on Mode
# =============================================================================

mode = st.sidebar.radio("Mode", ["Manual", "Connected"])

st.header("Deploy")

if mode == "Connected":
    # Show API configuration
    st.subheader("API Configuration")
    api_key = st.text_input("API Key", type="password")

    if st.button("Test Connection"):
        # Test connection logic
        pass

    # Show deploy button
    if st.button("Deploy to LaunchDarkly"):
        # Deploy logic
        pass

else:
    # Manual mode - no API deployment
    st.info("Switch to Connected mode to deploy via API")

    # Still allow download
    st.download_button("Download Config", data=config_json)
```

### State-Based UI Sections

```python
# =============================================================================
# LESSON: Progressive Disclosure Based on State
# =============================================================================

# Step 1: Always show validation
validation_result = validate_config()

if not validation_result.is_valid:
    st.error("Fix validation errors before deploying")
    return

# Step 2: Show API config if validated
st.subheader("API Configuration")
api_key = st.text_input("API Key", type="password")

if not api_key:
    st.caption("Enter API key to continue")
    return

# Step 3: Show connection test if API key entered
if st.button("Test Connection"):
    result = test_connection(api_key)
    st.session_state.connection_ok = result

if not st.session_state.get("connection_ok"):
    st.caption("Test connection to continue")
    return

# Step 4: Show deploy button only when ready
if st.button("Deploy"):
    deploy()
```

---

## 6. Rerun and State Management

### Manual Rerun

```python
# =============================================================================
# LESSON: Forcing a Rerun with st.rerun()
# =============================================================================

# Sometimes you need to force UI refresh after state change
if st.button("Test Connection"):
    result = test_api(api_key)

    # Store result
    st.session_state.connection_verified = result

    # Force rerun to update UI based on new state
    st.rerun()

# Now this will show immediately after button click
if st.session_state.get("connection_verified"):
    st.success("Connected!")
```

### Avoiding Infinite Reruns

```python
# =============================================================================
# LESSON: Preventing Rerun Loops
# =============================================================================

# BAD: This causes infinite rerun!
if st.session_state.get("should_rerun"):
    st.session_state.should_rerun = False
    st.rerun()  # Will set should_rerun again somehow? Loop!


# GOOD: Clear the trigger before rerunning
if st.session_state.get("trigger_rerun"):
    del st.session_state.trigger_rerun
    st.rerun()


# GOOD: Use a different pattern - action flags
if st.button("Do Something"):
    st.session_state.action_completed = True
    st.session_state.action_result = do_something()
    st.rerun()

# Display result (only after action)
if st.session_state.get("action_completed"):
    st.write(st.session_state.action_result)
```

---

## 7. Error Handling in UI

### Try-Except with User Feedback

```python
# =============================================================================
# LESSON: Graceful Error Handling
# =============================================================================

if st.button("Deploy"):
    try:
        with st.spinner("Deploying..."):
            result = deployer.deploy_all(payload)

        if result.success:
            st.success("Deployment successful!")
        else:
            st.warning(f"Completed with {len(result.errors)} errors")

    except LDAuthenticationError:
        st.error("❌ Invalid API key. Please check and try again.")

    except LDRateLimitError as e:
        st.error(f"❌ Rate limited. Please wait {e.retry_after} seconds.")

    except LDClientError as e:
        st.error(f"❌ API Error: {str(e)}")

    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        # Optionally show traceback in expander
        with st.expander("Error Details"):
            import traceback
            st.code(traceback.format_exc())
```

### Error Details in Expanders

```python
# =============================================================================
# LESSON: Expandable Error Details
# =============================================================================

result = deployer.deploy_all(payload)

if result.errors:
    st.error(f"Deployment had {len(result.errors)} error(s)")

    with st.expander("View Error Details", expanded=False):
        for i, error in enumerate(result.errors, 1):
            st.markdown(f"**{i}.** {error}")

    # Offer solutions
    st.info("💡 **Tips:**\n"
            "- Check that roles exist before creating teams\n"
            "- Verify API key has correct permissions\n"
            "- Try enabling 'Skip existing resources'")
```

### Confirmation Dialogs

```python
# =============================================================================
# LESSON: Confirmation Before Dangerous Actions
# =============================================================================

# Using session state for two-step confirmation
if st.button("🗑️ Rollback All"):
    st.session_state.confirm_rollback = True

if st.session_state.get("confirm_rollback"):
    st.warning("This will delete all resources created in this session!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Yes, Rollback", type="primary"):
            success = deployer.rollback()
            st.session_state.confirm_rollback = False
            if success:
                st.success("Rollback complete!")
            else:
                st.error("Rollback had errors")
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.session_state.confirm_rollback = False
            st.rerun()
```

---

## 8. Quick Reference Card

### Session State

```python
# Initialize
if "key" not in st.session_state:
    st.session_state.key = "default"

# Get with default
value = st.session_state.get("key", "default")

# Set
st.session_state.key = "value"

# Delete
del st.session_state.key

# Check
if "key" in st.session_state:
    pass
```

### Buttons

```python
# Basic button
if st.button("Click"):
    do_something()

# Disabled button
if st.button("Deploy", disabled=not_ready):
    deploy()

# Button with type
if st.button("Delete", type="primary"):  # or "secondary"
    delete()
```

### Progress

```python
# Progress bar
progress = st.progress(0)
progress.progress(0.5)  # 50%
progress.progress(1.0)  # Complete

# Spinner
with st.spinner("Loading..."):
    do_work()
```

### Password Input

```python
secret = st.text_input(
    "API Key",
    type="password",
    placeholder="Enter key..."
)
```

### Status Messages

```python
st.success("Success message")
st.error("Error message")
st.warning("Warning message")
st.info("Info message")
```

### Columns

```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Created", 5)
with col2:
    st.metric("Skipped", 2)
with col3:
    st.metric("Failed", 0)
```

### Expanders

```python
with st.expander("Details", expanded=False):
    st.write("Hidden content here")
```

### Rerun

```python
# Force UI refresh
st.rerun()
```

---

## Next Steps

Now that you understand the Streamlit concepts for Phase 8, proceed to:
- [DESIGN.md](DESIGN.md) - Implementation details and test cases
- [README.md](README.md) - Quick overview and checklist

---

[← Back to Phase 8 README](README.md) | [Phase 8 DESIGN →](DESIGN.md)
