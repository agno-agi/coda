"""GitHub REST API toolkit for Coda.

Provides read/write access to pull requests and issues via the GitHub REST API.
Requires a ``GITHUB_TOKEN`` environment variable with appropriate scopes.
"""

from __future__ import annotations

from os import getenv
from typing import Any

import httpx
from agno.tools import Toolkit


class GitHubTools(Toolkit):
    """Agno toolkit that wraps the GitHub REST API.

    Every public method is registered as a tool the agent can call.  All
    methods return human-readable strings (never raw JSON) and handle errors
    gracefully so the agent always gets a useful message.
    """

    def __init__(self) -> None:
        super().__init__(
            name="github_tools",
            tools=[
                self.get_pr,
                self.get_pr_diff,
                self.get_pr_comments,
                self.list_open_prs,
                self.get_issue,
                self.create_pr,
            ],
        )
        self.token: str = getenv("GITHUB_TOKEN", "")
        self.base_url: str = "https://api.github.com"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build default request headers, optionally merged with *extra*."""
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send an HTTP request to the GitHub API and return the response.

        Centralises auth, base-URL handling, and timeout configuration so
        every tool method stays concise.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            endpoint: API path **without** the base URL (e.g. ``/repos/o/r/pulls``).
            headers: Extra headers merged on top of the defaults.
            json: JSON body for ``POST`` / ``PATCH`` requests.
            params: Query-string parameters.

        Returns:
            The raw :class:`httpx.Response`.
        """
        url = f"{self.base_url}{endpoint}"
        return httpx.request(
            method,
            url,
            headers=self._headers(headers),
            json=json,
            params=params,
            timeout=30.0,
        )

    @staticmethod
    def _truncate(text: str | None, max_len: int = 1000) -> str:
        """Return *text* truncated to *max_len* characters."""
        if not text:
            return "(empty)"
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"\n... (truncated, {len(text)} chars total)"

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_pr(self, repo: str, pr_number: int) -> str:
        """Fetch details for a single pull request.

        Args:
            repo: Repository in ``owner/repo`` format (e.g. ``"org/backend-api"``).
            pr_number: The pull request number.

        Returns:
            A formatted summary of the PR including title, author, state,
            creation date, body excerpt, and number of changed files.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            resp = self._request("GET", f"/repos/{repo}/pulls/{pr_number}")
            if resp.status_code != 200:
                return f"GitHub API error {resp.status_code}: {resp.text}"

            pr: dict[str, Any] = resp.json()

            lines = [
                f"PR #{pr_number} in {repo}",
                f"  Title:         {pr.get('title', 'N/A')}",
                f"  Author:        {pr.get('user', {}).get('login', 'unknown')}",
                f"  State:         {pr.get('state', 'unknown')}",
                f"  Created:       {pr.get('created_at', 'N/A')}",
                f"  Files changed: {pr.get('changed_files', 'N/A')}",
                f"  Body:\n{self._truncate(pr.get('body'))}",
            ]
            return "\n".join(lines)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the raw diff for a pull request.

        Args:
            repo: Repository in ``owner/repo`` format.
            pr_number: The pull request number.

        Returns:
            The unified diff text, truncated to 10 000 characters if necessary.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            resp = self._request(
                "GET",
                f"/repos/{repo}/pulls/{pr_number}",
                headers={"Accept": "application/vnd.github.v3.diff"},
            )
            if resp.status_code != 200:
                return f"GitHub API error {resp.status_code}: {resp.text}"

            diff = resp.text
            return self._truncate(diff, max_len=10_000)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    def get_pr_comments(self, repo: str, pr_number: int) -> str:
        """Fetch review comments on a pull request.

        Args:
            repo: Repository in ``owner/repo`` format.
            pr_number: The pull request number.

        Returns:
            A formatted list of review comments with author, file path,
            line number, and body for each.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            resp = self._request("GET", f"/repos/{repo}/pulls/{pr_number}/comments")
            if resp.status_code != 200:
                return f"GitHub API error {resp.status_code}: {resp.text}"

            comments: list[dict[str, Any]] = resp.json()
            if not comments:
                return f"No review comments on PR #{pr_number}."

            parts: list[str] = [f"Review comments on PR #{pr_number} ({len(comments)} total):"]
            for i, c in enumerate(comments, 1):
                author = c.get("user", {}).get("login", "unknown")
                path = c.get("path", "N/A")
                line = c.get("line") or c.get("original_line") or "N/A"
                body = self._truncate(c.get("body"), max_len=500)
                parts.append(f"\n  [{i}] {author} on {path}:{line}\n      {body}")

            return "\n".join(parts)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    def list_open_prs(self, repo: str) -> str:
        """List open pull requests for a repository (up to 20).

        Args:
            repo: Repository in ``owner/repo`` format.

        Returns:
            A formatted table of open PRs with number, title, author, and
            creation date.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            resp = self._request(
                "GET",
                f"/repos/{repo}/pulls",
                params={"state": "open", "per_page": 20},
            )
            if resp.status_code != 200:
                return f"GitHub API error {resp.status_code}: {resp.text}"

            prs: list[dict[str, Any]] = resp.json()
            if not prs:
                return f"No open PRs in {repo}."

            lines: list[str] = [f"Open PRs in {repo} ({len(prs)}):"]
            for pr in prs:
                number = pr.get("number", "?")
                title = pr.get("title", "N/A")
                author = pr.get("user", {}).get("login", "unknown")
                created = pr.get("created_at", "N/A")
                lines.append(f"  #{number}  {title}  ({author}, {created})")

            return "\n".join(lines)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    def get_issue(self, repo: str, issue_number: int) -> str:
        """Fetch details for a single issue.

        Args:
            repo: Repository in ``owner/repo`` format.
            issue_number: The issue number.

        Returns:
            A formatted summary of the issue including title, author, state,
            labels, and body excerpt.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            resp = self._request("GET", f"/repos/{repo}/issues/{issue_number}")
            if resp.status_code != 200:
                return f"GitHub API error {resp.status_code}: {resp.text}"

            issue: dict[str, Any] = resp.json()

            labels = ", ".join(label.get("name", "") for label in issue.get("labels", [])) or "none"

            lines = [
                f"Issue #{issue_number} in {repo}",
                f"  Title:   {issue.get('title', 'N/A')}",
                f"  Author:  {issue.get('user', {}).get('login', 'unknown')}",
                f"  State:   {issue.get('state', 'unknown')}",
                f"  Labels:  {labels}",
                f"  Body:\n{self._truncate(issue.get('body'))}",
            ]
            return "\n".join(lines)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    def create_pr(
        self, repo: str, branch: str, title: str, body: str, base: str = "", draft: bool = False
    ) -> str:
        """Create a new pull request.

        Args:
            repo: Repository in ``owner/repo`` format.
            branch: The head branch containing the changes.
            title: PR title.
            body: PR description / body text.
            base: The base branch to merge into. If empty, auto-detects the repo's default branch.
            draft: If True, create a draft PR instead of a ready-for-review PR.

        Returns:
            The URL of the newly created PR, or an error message on failure.
        """
        if not self.token:
            return "GitHub token not configured."

        try:
            # Auto-detect default branch if base not specified
            if not base:
                repo_resp = self._request("GET", f"/repos/{repo}")
                if repo_resp.status_code == 200:
                    base = repo_resp.json().get("default_branch", "main")
                else:
                    base = "main"

            payload: dict[str, Any] = {
                "head": branch,
                "base": base,
                "title": title,
                "body": body,
            }
            if draft:
                payload["draft"] = True

            resp = self._request("POST", f"/repos/{repo}/pulls", json=payload)
            if resp.status_code not in (200, 201):
                return f"GitHub API error {resp.status_code}: {resp.text}"

            pr: dict[str, Any] = resp.json()
            return f"PR created: {pr.get('html_url', 'unknown URL')}"
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"
