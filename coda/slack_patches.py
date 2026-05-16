"""
Slack HITL patches.

Caps ``_build_confirmation_card`` body text at 190 chars so Slack accepts
the multi-row pause card. Without this, long tool_args (e.g.,
``comment_on_issue`` with a 250+ char body) cause Slack Block Kit to reject
the entire card with ``invalid_blocks`` and no approval UI ever renders —
all paused actions get stuck waiting forever.

Upstream agno bug: ``agno/os/interfaces/slack/builders.py``'s
``_build_confirmation_card`` already imports the ``truncate`` helper but
never applies it to ``Card.body.text``. Worth filing as an upstream PR.
"""

from agno.os.interfaces.slack import builders as _builders
from agno.os.interfaces.slack.types import truncate

# Slack's card-block body has a ~201 char limit; 190 leaves room for the
# trailing ellipsis appended by truncate().
_MAX_BODY = 190
_orig_build = _builders._build_confirmation_card


def _build_confirmation_card_capped(requirement, run_id="", awaiting_ts=None):
    card = _orig_build(requirement, run_id=run_id, awaiting_ts=awaiting_ts)
    if card.body and getattr(card.body, "text", None):
        card.body.text = truncate(card.body.text, _MAX_BODY)
    return card


def install() -> None:
    """Idempotently install the body-text cap on agno's confirmation card builder."""
    if getattr(_builders._build_confirmation_card, "_coda_capped", False):
        return
    _build_confirmation_card_capped._coda_capped = True  # type: ignore[attr-defined]
    _builders._build_confirmation_card = _build_confirmation_card_capped
