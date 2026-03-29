"""
Synthesis Cases
===============

Leader synthesizes specialist output well: concise, includes file paths,
suggests next steps, uses good formatting.
Eval type: AgentAsJudgeEval (numeric, threshold 7)
"""

CRITERIA = (
    "Evaluate the quality of a code assistant's response. Score 1-10:\n"
    "1. Conciseness — leads with the answer, not the process. "
    'No filler like "I\'ll search for..." or "Let me look into...".\n'
    "2. Evidence — includes file paths with line numbers (path/to/file.py:42).\n"
    "3. Accuracy — claims are specific, not vague hedging.\n"
    "4. Actionability — suggests concrete next steps when appropriate.\n"
    "5. Formatting — uses code blocks for snippets, markdown for structure.\n\n"
    "A score of 7+ means the response is useful to a working engineer. "
    "A score below 5 means the response is vague, missing paths, or too verbose."
)

CASES: list[str] = [
    "Where is the authentication middleware?",
    "How does the API handle errors?",
    "Walk me through the request lifecycle",
    "What changed in the last 5 commits?",
    "Is there anything concerning about the security setup?",
    "What are the open issues and which are most urgent?",
]
