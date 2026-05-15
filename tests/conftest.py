"""
Test fixtures for coda HITL.

Lifted from agno's test conftest at:
agno/libs/agno/tests/unit/os/routers/conftest.py
"""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

SIGNING_SECRET = "test-secret"


def make_signed_request(client: TestClient, body: dict, signing_secret: str = SIGNING_SECRET):
    """Sign a Slack payload and POST to /events."""
    body_bytes = json.dumps(body).encode()
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body_bytes.decode()}"
    signature = "v0=" + hmac.new(signing_secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    return client.post(
        "/events",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature,
        },
    )


def build_app(agent_mock: Mock, **kwargs) -> FastAPI:
    """Build a FastAPI app with agno's Slack router attached."""
    from agno.os.interfaces.slack.router import attach_routes

    kwargs.setdefault("streaming", False)
    app = FastAPI()
    router = APIRouter()
    attach_routes(router, agent=agent_mock, **kwargs)
    app.include_router(router)
    return app


def make_agent_mock():
    """Mock an agent with a successful arun() response."""
    agent_mock = AsyncMock()
    agent_mock.arun = AsyncMock(
        return_value=Mock(
            status="OK", content="done", reasoning_content=None,
            images=None, files=None, videos=None, audio=None,
        )
    )
    return agent_mock


def make_slack_mock(**kwargs):
    """Mock SlackTools."""
    mock_slack = Mock()
    mock_slack.send_message = Mock()
    mock_slack.upload_file = Mock()
    mock_slack.max_file_size = 1_073_741_824
    for k, v in kwargs.items():
        setattr(mock_slack, k, v)
    return mock_slack


def make_stream_mock():
    """Mock a Slack chat stream."""
    stream = AsyncMock()
    stream.append = AsyncMock()
    stream.stop = AsyncMock()
    return stream


def make_async_client_mock(stream_mock=None):
    """Mock Slack AsyncWebClient with sensible defaults."""
    client = AsyncMock()
    client.assistant_threads_setStatus = AsyncMock()
    client.assistant_threads_setTitle = AsyncMock()
    client.assistant_threads_setSuggestedPrompts = AsyncMock()
    client.chat_stream = AsyncMock(return_value=stream_mock or make_stream_mock())
    client.chat_postMessage = AsyncMock()
    client.users_info = AsyncMock(
        return_value={
            "ok": True,
            "user": {
                "id": "U123",
                "name": "testuser",
                "profile": {
                    "email": "test@example.com",
                    "display_name": "Test User",
                    "real_name": "Test User",
                },
            },
        }
    )
    client.conversations_info = AsyncMock(return_value={"ok": True, "channel": {"name": "general"}})
    return client


async def wait_for_call(mock_method, timeout: float = 5.0):
    """Wait for an AsyncMock to be called, with timeout."""
    import asyncio
    elapsed = 0.0
    while not mock_method.called and elapsed < timeout:
        await asyncio.sleep(0.1)
        elapsed += 0.1


def make_requirement(req_id: str = "r1", **tool_overrides):
    """Build a RunRequirement for HITL tests."""
    from agno.models.response import ToolExecution
    from agno.run.requirement import RunRequirement

    defaults = {
        "tool_name": "delete_file",
        "tool_args": {"path": "/tmp/demo.txt"},
        "requires_confirmation": True,
    }
    defaults.update(tool_overrides)
    return RunRequirement(tool_execution=ToolExecution(**defaults), id=req_id)


# ---------------------------------------------------------------------------
# Pytest fixtures (auto-injected by name)
# ---------------------------------------------------------------------------


@pytest.fixture
def agent_mock():
    return make_agent_mock()


@pytest.fixture
def slack_mock():
    return make_slack_mock()


@pytest.fixture
def stream_mock():
    return make_stream_mock()


@pytest.fixture
def async_client_mock(stream_mock):
    return make_async_client_mock(stream_mock)
