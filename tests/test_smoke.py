"""Smoke test for the agno bump and DB config (commit 1)."""

import agno


def test_agno_version_is_2_6_x():
    """Verify agno 2.6.x is installed (we bumped to 2.6.6)."""
    assert agno.__version__.startswith("2.6"), f"Expected 2.6.x, got {agno.__version__}"


def test_db_session_has_approvals_table():
    """Verify get_postgres_db() returns DB with coda_approvals table configured."""
    from db.session import get_postgres_db

    db = get_postgres_db()
    assert getattr(db, "approvals_table_name", None) == "coda_approvals"
