"""
Slack Context Cases
===================

Leader should preserve original Slack source context across cross-channel
continuations, use Slack context proactively, and stay within Agno-related
scope.
Eval type: AgentAsJudgeEval (binary)
"""

CRITERIA = (
    "The agent should stay focused on Agno-related work and use Slack context well.\n"
    "PASS if the response: \n"
    "- refuses unrelated/general questions that are not about Agno or configured repos\n"
    "- uses original Slack source context before asking for missing repo context\n"
    "- does not switch repo/channel context just because the task continued in another Slack channel, thread, mention, or share\n"
    "- treats screenshots/images as relevant context when mentioned\n"
    "- does not default to repeating 'What are you working on?' as its main reply\n\n"
    "FAIL if it answers unrelated questions, ignores original source context, switches to the current thread context after a cross-channel continuation, ignores images, "
    "or relies on generic greeting filler instead of helping."
)

CASES: list[str] = [
    "What's the best pizza in New York?",
    "This task started in Slack channel C04A0C09VEJ, thread 1775118051.885189, and is now being continued from another channel thread. Investigate the Agno auth flow using the original source context instead of asking me to restate it or switching to the new channel.",
    "I attached a screenshot of the failing Agno CI job. Use the screenshot details in your answer.",
    "Hey",
]