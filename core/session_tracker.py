"""
Session Tracker
================

Tracks how many users are currently active in the RBAC Builder app.

LESSON: Sharing State Across Streamlit Sessions
=================================================
Each Streamlit session has its own st.session_state — isolated from other users.
But we need a counter visible to ALL sessions. The trick: st.cache_resource
returns the SAME Python object to every session. Since dicts are mutable, all
sessions read and write the same dict — no database needed.

See docs/phases/phase26/PYTHON_CONCEPTS.md for a full explanation.
"""

import time
import uuid
import threading
from typing import List, Dict

import streamlit as st


# =============================================================================
# LESSON: Configuration constant
# =============================================================================
# If a session hasn't interacted in this many seconds, we consider it gone.
# 60s is a reasonable default — users actively clicking will heartbeat
# on every rerun. Idle tabs (open but not interacting) will drop off.
SESSION_TIMEOUT_SECONDS = 60


# =============================================================================
# LESSON: Shared Singletons via @st.cache_resource
# =============================================================================
# cache_resource runs the function ONCE, then returns the SAME object
# to every caller. This is how all sessions share one dict and one lock.
# Compare with cache_data, which returns COPIES (not shared).

@st.cache_resource
def _get_session_store() -> Dict[str, float]:
    """
    Returns a dict shared across ALL sessions in this process.
    Key = session_id (str), Value = last_seen timestamp (float).

    Because this is cache_resource (not cache_data), every session
    gets the exact same dict object. Mutations by one session are
    visible to all others.
    """
    return {}


@st.cache_resource
def _get_lock() -> threading.Lock:
    """
    A shared lock to prevent race conditions on the dict.

    Multiple sessions can rerun concurrently (threads in the same process).
    Without a lock, two sessions could modify the dict at the same time.
    The lock ensures one-at-a-time access.
    """
    return threading.Lock()


# =============================================================================
# LESSON: Public API — heartbeat / get_active_count / get_active_sessions
# =============================================================================

def heartbeat() -> None:
    """
    Register the current session as active.

    Call this once at the top of app.py. On every Streamlit rerun
    (every widget interaction), this updates the session's timestamp
    in the shared dict.

    First call per session: generates a unique UUID and stores it
    in st.session_state so it persists across reruns.
    """
    # =================================================================
    # LESSON: Generate session ID once, reuse on subsequent reruns
    # =================================================================
    # st.session_state persists across reruns within the same session.
    # uuid4() generates a random 128-bit ID — practically unique.
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    store = _get_session_store()
    lock = _get_lock()

    # =================================================================
    # LESSON: 'with lock' — context manager for thread safety
    # =================================================================
    # The 'with' statement acquires the lock, runs the block, then
    # releases the lock — even if an exception occurs. This prevents
    # deadlocks where a crash leaves the lock permanently held.
    with lock:
        store[st.session_state.session_id] = time.time()


def get_active_count() -> int:
    """
    Returns the number of sessions that sent a heartbeat within the
    timeout window. Also removes stale entries as a side effect.

    LESSON: Cleanup on read
    ========================
    We clean up stale sessions every time someone asks for the count.
    This is simpler than running a background thread — Streamlit doesn't
    support background tasks well, but every active user triggers reruns
    frequently, so cleanup happens naturally.
    """
    store = _get_session_store()
    lock = _get_lock()
    now = time.time()

    with lock:
        # =============================================================
        # LESSON: Don't modify a dict while iterating it
        # =============================================================
        # Collect stale keys first, then delete in a separate loop.
        # Deleting during iteration causes RuntimeError.
        stale_keys = [
            sid for sid, last_seen in store.items()
            if now - last_seen > SESSION_TIMEOUT_SECONDS
        ]
        for key in stale_keys:
            del store[key]

        return len(store)


def get_active_sessions() -> List[Dict]:
    """
    Returns a list of active sessions with their age in seconds.
    Useful for debugging or an admin view.

    Each entry: {"session_id": "abcd1234...", "last_seen_seconds_ago": 12.3}
    Session IDs are truncated for privacy.
    """
    store = _get_session_store()
    lock = _get_lock()
    now = time.time()

    with lock:
        return [
            {
                "session_id": sid[:8] + "...",
                "last_seen_seconds_ago": round(now - last_seen, 1),
            }
            for sid, last_seen in store.items()
            if now - last_seen <= SESSION_TIMEOUT_SECONDS
        ]
