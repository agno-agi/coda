"""Cron HITL plumbing tests."""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Triager's GithubTools() construction at module import requires GITHUB_ACCESS_TOKEN.
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")


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
        args = mock_post.await_args[0]  # type: ignore[index]
        assert args[1] is mock_paused
        assert args[2] == "C123"
        assert args[3] == "1234.5678"


def test_build_session_id_uses_triager_prefix_with_header():
    """With a header_ts, _build_session_id yields agno's resume contract: '{triager.id}:{ts}'."""
    from coda.agents.triager import triager
    from tasks.review_issues import _build_session_id

    session_id = _build_session_id("agno", "1234567890.123456")

    assert session_id == f"{triager.id}:1234567890.123456"
    assert session_id.startswith("triager:")


def test_build_session_id_falls_back_to_synthetic_when_no_header():
    """Without a header_ts, _build_session_id uses a synthetic cron-triage id."""
    from tasks.review_issues import _build_session_id

    with patch("time.time", return_value=1700000000):
        session_id = _build_session_id("agno", None)

    assert session_id == "cron-triage-agno-1700000000"
