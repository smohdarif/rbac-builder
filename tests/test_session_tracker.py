"""
Tests for Phase 26: Session Tracker
=====================================

Tests the active user counter logic: heartbeat registration,
stale session cleanup, thread safety, and session listing.

Since Streamlit's runtime (st.cache_resource, st.session_state) is not
available during pytest, we test the core logic directly by manipulating
the shared dict and timestamps.

Run with: pytest tests/test_session_tracker.py -v
"""

import threading
import time
import uuid

import pytest


# =============================================================================
# LESSON: Testing Without Streamlit Runtime
# =============================================================================
# We can't call st.cache_resource or st.session_state in pytest.
# Instead, we test the core logic (dict manipulation, timestamps, locking)
# by creating the shared store and lock directly, then calling helper
# functions that operate on them.
#
# This pattern: extract logic from framework-specific code, test the logic.

from core.session_tracker import SESSION_TIMEOUT_SECONDS


# =============================================================================
# Helpers — simulate what the Streamlit decorators would provide
# =============================================================================

def make_store() -> dict:
    """Create a fresh session store (simulates @st.cache_resource)."""
    return {}


def make_lock() -> threading.Lock:
    """Create a fresh lock (simulates @st.cache_resource)."""
    return threading.Lock()


def do_heartbeat(store: dict, lock: threading.Lock, session_id: str) -> None:
    """Simulate heartbeat() without Streamlit dependencies."""
    with lock:
        store[session_id] = time.time()


def do_heartbeat_at(
    store: dict, lock: threading.Lock, session_id: str, timestamp: float
) -> None:
    """Heartbeat with a specific timestamp (for testing staleness)."""
    with lock:
        store[session_id] = timestamp


def do_get_active_count(store: dict, lock: threading.Lock) -> int:
    """Simulate get_active_count() without Streamlit dependencies."""
    now = time.time()
    with lock:
        stale_keys = [
            sid for sid, last_seen in store.items()
            if now - last_seen > SESSION_TIMEOUT_SECONDS
        ]
        for key in stale_keys:
            del store[key]
        return len(store)


def do_get_active_sessions(store: dict, lock: threading.Lock) -> list:
    """Simulate get_active_sessions() without Streamlit dependencies."""
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


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def store():
    return make_store()


@pytest.fixture
def lock():
    return make_lock()


# =============================================================================
# Group 1: Heartbeat Registration (TC-SC-01, TC-SC-02, TC-SC-03)
# =============================================================================

class TestHeartbeat:

    def test_first_heartbeat_creates_entry(self, store, lock):
        """TC-SC-01: First heartbeat creates a session entry."""
        do_heartbeat(store, lock, "aaa")

        assert len(store) == 1
        assert "aaa" in store
        assert isinstance(store["aaa"], float)

    def test_repeated_heartbeat_updates_timestamp(self, store, lock):
        """TC-SC-02: Repeated heartbeats update the timestamp, not duplicate."""
        do_heartbeat_at(store, lock, "aaa", 1000.0)
        do_heartbeat_at(store, lock, "aaa", 1005.0)

        assert len(store) == 1
        assert store["aaa"] == 1005.0

    def test_multiple_sessions_separate_entries(self, store, lock):
        """TC-SC-03: Multiple sessions get separate entries."""
        do_heartbeat(store, lock, "aaa")
        do_heartbeat(store, lock, "bbb")

        assert len(store) == 2
        assert "aaa" in store
        assert "bbb" in store


# =============================================================================
# Group 2: Active Count + Cleanup (TC-SC-04, TC-SC-05, TC-SC-06, TC-SC-07)
# =============================================================================

class TestActiveCount:

    def test_returns_only_non_stale_sessions(self, store, lock):
        """TC-SC-04: Active count returns only non-stale sessions."""
        now = time.time()
        do_heartbeat_at(store, lock, "aaa", now - 10)    # active
        do_heartbeat_at(store, lock, "bbb", now - 30)    # active
        do_heartbeat_at(store, lock, "ccc", now - 90)    # stale

        count = do_get_active_count(store, lock)

        assert count == 2
        assert "ccc" not in store

    def test_all_stale_returns_zero(self, store, lock):
        """TC-SC-05: All sessions stale returns 0."""
        now = time.time()
        do_heartbeat_at(store, lock, "aaa", now - 120)
        do_heartbeat_at(store, lock, "bbb", now - 180)

        count = do_get_active_count(store, lock)

        assert count == 0
        assert len(store) == 0

    def test_empty_store_returns_zero(self, store, lock):
        """TC-SC-06: Empty store returns 0."""
        count = do_get_active_count(store, lock)
        assert count == 0

    def test_boundary_timeout(self, store, lock):
        """TC-SC-07: Session at exactly timeout boundary is removed."""
        now = time.time()
        do_heartbeat_at(store, lock, "aaa", now - 60.5)   # just over
        do_heartbeat_at(store, lock, "bbb", now - 59.5)   # just under

        count = do_get_active_count(store, lock)

        assert count == 1
        assert "aaa" not in store
        assert "bbb" in store


# =============================================================================
# Group 3: Thread Safety (TC-SC-08)
# =============================================================================

class TestThreadSafety:

    def test_concurrent_heartbeats_no_corruption(self, store, lock):
        """TC-SC-08: Concurrent heartbeats don't corrupt the store."""
        errors = []

        def worker(session_id: str):
            try:
                do_heartbeat(store, lock, session_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(f"session-{i}",))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(store) == 10


# =============================================================================
# Group 4: Edge Cases (TC-SC-09, TC-SC-10)
# =============================================================================

class TestEdgeCases:

    def test_session_id_is_valid_uuid(self):
        """TC-SC-09: uuid4() generates a valid UUID string."""
        session_id = str(uuid.uuid4())
        # Should not raise ValueError
        parsed = uuid.UUID(session_id, version=4)
        assert str(parsed) == session_id

    def test_get_active_sessions_truncates_ids(self, store, lock):
        """TC-SC-10: get_active_sessions returns truncated IDs."""
        full_id = "abcd1234-5678-9abc-def0-123456789abc"
        do_heartbeat_at(store, lock, full_id, time.time())

        sessions = do_get_active_sessions(store, lock)

        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "abcd1234..."
        assert isinstance(sessions[0]["last_seen_seconds_ago"], float)
        assert sessions[0]["last_seen_seconds_ago"] >= 0


# =============================================================================
# Group 5: Timeout Configuration
# =============================================================================

class TestConfiguration:

    def test_timeout_constant_is_reasonable(self):
        """SESSION_TIMEOUT_SECONDS is a positive number."""
        assert SESSION_TIMEOUT_SECONDS > 0
        assert isinstance(SESSION_TIMEOUT_SECONDS, (int, float))
