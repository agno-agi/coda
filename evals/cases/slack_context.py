"""
Slack Context Cases
===================

Leader should use Slack thread context and images proactively, and stay
within Agno-related scope.
Eval type: AgentAsJudgeEval (binary)
"""

CRITERIA = (
    "The agent should stay focused on Agno-related work and use Slack context well.\n"
    "PASS if the response: \n"
    "- refuses unrelated/general questions that are not about Agno or configured repos\n"
    "- uses prior Slack thread context before asking for missing repo context\n"
    "- treats screenshots/images as relevant context when mentioned\n"
    "- does not default to repeating 'What are you working on?' as its main reply\n\n"
    "FAIL if it answers unrelated questions, ignores thread context, ignores images, "
    "or relies on generic greeting filler instead of helping."
)

CASES: list[str] = [
    "What's the best pizza in New York?",
    "In this Slack thread we're debugging the Agno auth flow. The latest message says 'can you investigate this?' — use the thread context instead of asking me to restate it.",
    "I attached a screenshot of the failing Agno CI job. Use the screenshot details in your answer.",
    "Hey",
]