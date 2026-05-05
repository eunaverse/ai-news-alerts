from __future__ import annotations

from collections.abc import Callable
import os
import re

import requests

from ai_news_alerts.models import GitHubMetadata

GITHUB_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s#?]+)")
RESERVED_OWNERS = {
    "about",
    "apps",
    "collections",
    "customer-stories",
    "enterprise",
    "events",
    "explore",
    "features",
    "github",
    "login",
    "marketplace",
    "new",
    "orgs",
    "pricing",
    "search",
    "settings",
    "showcases",
    "sponsors",
    "topics",
}


GetJson = Callable[..., dict[str, object]]


def extract_github_repo(url: str | None) -> str | None:
    if not url:
        return None
    match = GITHUB_RE.search(url)
    if not match:
        return None
    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    if owner.lower() in RESERVED_OWNERS or not owner or not repo:
        return None
    return f"{owner}/{repo}"


class GitHubClient:
    def __init__(self, get_json: GetJson | None = None) -> None:
        self.get_json = get_json or self._request_json

    def fetch(self, repo: str) -> GitHubMetadata | None:
        try:
            payload = self.get_json(
                f"https://api.github.com/repos/{repo}",
                headers=_headers(),
            )
        except Exception:
            return None
        full_name = str(payload.get("full_name") or repo)
        description = str(payload.get("description") or "")
        stars = int(payload.get("stargazers_count") or 0)
        language_value = payload.get("language")
        language = str(language_value) if language_value else None
        updated_at_value = payload.get("pushed_at") or payload.get("updated_at")
        updated_at = str(updated_at_value) if updated_at_value else None
        return GitHubMetadata(
            repo=full_name,
            description=description,
            stars=stars,
            language=language,
            updated_at=updated_at,
        )

    @staticmethod
    def _request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, object]:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("GitHub API returned a non-object payload")
        return payload


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "ai-news-alerts"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
