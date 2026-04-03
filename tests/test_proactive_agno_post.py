from __future__ import annotations

import json
from pathlib import Path

from tasks.proactive_agno_post import (
    _half_hour_bucket,
    build_proactive_post,
    mark_signal_posted,
    should_post_signal,
)


def test_build_proactive_post_for_commit() -> None:
    message = build_proactive_post(
        "agno",
        {
            "type": "commit",
            "sha": "abc123456789",
            "short_sha": "abc1234",
            "subject": "Improve agent memory wiring",
            "author": "alice",
            "files": "libs/agno/agno/memory/v2/memory.py",
            "url": "https://github.com/agno-agi/agno/commit/abc123456789",
        },
    )

    assert "Agno update 👀" in message
    assert "Improve agent memory wiring" in message
    assert "memory.py" in message


def test_build_proactive_post_for_spotlight() -> None:
    message = build_proactive_post(
        "agno",
        {
            "type": "spotlight",
            "path": "README.md",
            "headline": "# Agno",
            "detail": "Build multi-agent systems with memory, knowledge, and tools.",
            "url": "https://github.com/agno-agi/agno/blob/main/README.md",
        },
    )

    assert "Repo spotlight" in message
    assert "README.md" in message
    assert "Build multi-agent systems" in message


def test_dedupe_state_blocks_repeat_in_same_bucket(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("REPOS_DIR", str(tmp_path))
    from tasks import proactive_agno_post as module

    module.REPOS_DIR = tmp_path
    signal = {
        "type": "commit",
        "sha": "abc123456789",
        "short_sha": "abc1234",
        "subject": "Improve agent memory wiring",
        "author": "alice",
        "files": "libs/agno/agno/memory/v2/memory.py",
        "url": "https://github.com/agno-agi/agno/commit/abc123456789",
    }
    bucket = "2026-04-03T19:00Z"

    assert should_post_signal("agno", signal, bucket) is True
    mark_signal_posted("agno", signal, bucket)
    assert should_post_signal("agno", signal, bucket) is False

    state_path = tmp_path / ".coda-state" / "proactive-post-agno.json"
    payload = json.loads(state_path.read_text())
    assert payload["bucket"] == bucket
    assert payload["signal_type"] == "commit"


def test_half_hour_bucket_rounds_down() -> None:
    from datetime import datetime, timezone

    assert _half_hour_bucket(datetime(2026, 4, 3, 19, 4, tzinfo=timezone.utc)) == "2026-04-03T19:00Z"
    assert _half_hour_bucket(datetime(2026, 4, 3, 19, 48, tzinfo=timezone.utc)) == "2026-04-03T19:30Z"