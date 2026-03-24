"""
RBAC Builder for LaunchDarkly
=============================

A Streamlit application for designing RBAC policies through an interactive UI.

Run with: streamlit run app.py

Compatibility:
    - Localhost: Full functionality with persistent storage
    - Streamlit Cloud: Works but storage is ephemeral (use Download/Upload)

Architecture:
    This is the main entry point. Each tab is rendered by a separate module:
    - ui/setup_tab.py      → Tab 1: Setup
    - ui/matrix_tab.py     → Tab 2: Design Matrix
    - ui/deploy_tab.py     → Tab 3: Deploy
    - ui/reference_tab.py  → Tab 4: Reference Guide
"""

import streamlit as st

# =============================================================================
# LESSON: Environment Detection for Dual Compatibility
# =============================================================================
# This app works on both localhost AND Streamlit Cloud.
# We detect the environment and show appropriate warnings.
from core import get_storage_warning, is_streamlit_cloud
from core.session_tracker import heartbeat, get_active_count

# =============================================================================
# LESSON: UI Module Imports
# =============================================================================
# Each tab is now a separate module in the ui/ package.
# This makes the code more maintainable and testable.
from ui import (
    render_setup_tab,
    render_matrix_tab,
    render_deploy_tab,
    render_reference_tab,
    render_advisor_tab,
)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
# This MUST be the first Streamlit command in your app.
st.set_page_config(
    page_title="RBAC Builder for LaunchDarkly",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# LESSON: Session Heartbeat — Register This User as Active
# =============================================================================
# Must be called early (before sidebar renders) so the count is accurate.
# Every rerun (widget click) refreshes the heartbeat timestamp.
heartbeat()

# =============================================================================
# HEADER
# =============================================================================
st.title("🔧 RBAC Builder for LaunchDarkly")
st.markdown("*Design RBAC policies through an interactive UI*")

# =============================================================================
# LESSON: Environment-Specific Warnings
# =============================================================================
# Show a warning banner if running on Streamlit Cloud where storage is ephemeral.
storage_warning = get_storage_warning()
if storage_warning:
    st.warning(storage_warning, icon="☁️")

st.divider()

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.header("⚙️ Settings")

    # Customer name input
    # _advisor_customer_name is set by the RBAC Advisor's Apply button
    default_customer = st.session_state.get("_advisor_customer_name", "")
    customer_name = st.text_input(
        "Customer Name",
        value=default_customer,
        placeholder="Enter customer name...",
        help="This will be used to save your configuration",
    )

    # Mode selection
    mode = st.radio(
        "Mode",
        options=["Manual", "Connected"],
        help="Manual: Enter details manually\nConnected: Fetch from LaunchDarkly API"
    )

    st.divider()

    # Display current state
    st.caption("Current State:")
    st.json({
        "customer": customer_name or "(not set)",
        "mode": mode
    })

    # =================================================================
    # LESSON: Active User Count — shared across all sessions
    # =================================================================
    # get_active_count() reads the shared dict (via cache_resource),
    # cleans up stale sessions, and returns how many are active.
    st.divider()
    st.metric(label="Active Users", value=get_active_count())

# =============================================================================
# MAIN TABS
# =============================================================================
# Create four tabs - each rendered by its own module

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 1. Setup",
    "📊 2. Design Matrix",
    "🚀 3. Deploy",
    "🤖 4. Role Designer AI",
    "📚 5. Reference Guide",
])

# =============================================================================
# TAB 1: Setup
# =============================================================================
with tab1:
    render_setup_tab(customer_name=customer_name, mode=mode)

# =============================================================================
# TAB 2: Design Matrix
# =============================================================================
with tab2:
    render_matrix_tab(customer_name=customer_name)

# =============================================================================
# TAB 3: Deploy
# =============================================================================
with tab3:
    render_deploy_tab(customer_name=customer_name, mode=mode)

# =============================================================================
# TAB 4: Role Designer AI
# =============================================================================
with tab4:
    render_advisor_tab(customer_name=customer_name)

# =============================================================================
# TAB 5: Reference Guide
# =============================================================================
with tab5:
    render_reference_tab()

# =============================================================================
# FOOTER
# =============================================================================
# Track visit count in session state
if "visit_count" not in st.session_state:
    st.session_state.visit_count = 0
st.session_state.visit_count += 1

st.divider()
st.caption(f"RBAC Builder v1.0 | Page loaded {st.session_state.visit_count} times this session")
