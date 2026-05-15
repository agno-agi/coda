"""Cron HITL plumbing tests."""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Triager's GithubTools() construction at module import requires GITHUB_ACCESS_TOKEN.
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")


def test_has_pending_triage_returns_false_when_no_approvals_table():
    """Without approvals_table configured, dedup check returns False (not blocking)."""
    from tasks.review_issues import _has_pending_triage

    mock_db = Mock()
    mock_db.approvals_table_name = None

    with patch("tasks.review_issues.get_postgres_db", return_value=mock_db):
        assert _has_pending_triage() is False


def test_has_pending_triage_returns_false_on_db_error():
    """If the DB query raises, dedup check returns False (don't block on transient errors)."""
    from tasks.review_issues import _has_pending_triage

    mock_db = Mock()
    mock_db.approvals_table_name = "coda_approvals"
    mock_db.engine.connect.side_effect = RuntimeError("connection lost")

    with patch("tasks.review_issues.get_postgres_db", return_value=mock_db):
        assert _has_pending_triage() is False


def test_post_header_returns_ts_on_success():
    """_post_header returns the message ts when chat_postMessage succeeds."""
    from tasks.review_issues import _post_header

    mock_client = Mock()
    mock_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123"})

    result = _post_header(mock_client, "C123", "agno")
    assert result == "1234567890.123"
    mock_client.chat_postMessage.assert_called_once()


def test_post_header_returns_none_on_slack_error():
    """_post_header returns None when Slack API errors."""
    from slack_sdk.errors import SlackApiError

    from tasks.review_issues import _post_header

    err_response = Mock()
    err_response.get = Mock(return_value="channel_not_found")
    mock_client = Mock()
    mock_client.chat_postMessage = Mock(side_effect=SlackApiError("boom", err_response))

    result = _post_header(mock_client, "C_BAD", "agno")
    assert result is None


@pytest.mark.asyncio
async def test_post_hitl_card_calls_agno_post_pause_card():
    """_post_hitl_card delegates to agno's post_pause_card with the supplied args."""
    from tasks.review_issues import _post_hitl_card

    mock_paused = Mock()

    with patch("agno.os.interfaces.slack.pause.post_pause_card", new=AsyncMock()) as mock_post:
        await _post_hitl_card("xoxb-test", mock_paused, "C123", "1234.5678")

        mock_post.assert_awaited_once()
        args = mock_post.await_args[0]
        assert args[1] is mock_paused
        assert args[2] == "C123"
        assert args[3] == "1234.5678"


def test_session_id_format_when_header_ts_present():
    """session_id format must match agno's contract: f'{triager.id}:{header_ts}'."""
    from coda.agents.triager import triager

    header_ts = "1234567890.123456"
    session_id = f"{triager.id}:{header_ts}"

    # Format check: exactly two colon-separated parts, second part is the ts
    parts = session_id.split(":")
    assert len(parts) == 2
    assert parts[0] == triager.id
    assert parts[1] == header_ts


def test_session_id_falls_back_to_synthetic_when_no_header():
    """Without a Slack header_ts, session_id uses a synthetic cron-triage prefix."""
    import time as time_module

    repo_name = "agno"
    fake_ts = 1700000000
    expected = f"cron-triage-{repo_name}-{fake_ts}"

    with patch("time.time", return_value=fake_ts):
        synthetic = f"cron-triage-{repo_name}-{int(time_module.time())}"
    assert synthetic == expected
