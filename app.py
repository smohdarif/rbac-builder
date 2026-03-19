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
    customer_name = st.text_input(
        "Customer Name",
        placeholder="Enter customer name...",
        help="This will be used to save your configuration"
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

# =============================================================================
# MAIN TABS
# =============================================================================
# Create four tabs - each rendered by its own module

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 1. Setup",
    "📊 2. Design Matrix",
    "🚀 3. Deploy",
    "📚 4. Reference Guide"
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
# TAB 4: Reference Guide
# =============================================================================
with tab4:
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
