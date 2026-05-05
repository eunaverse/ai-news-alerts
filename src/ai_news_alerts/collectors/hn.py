from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import html
import re

import requests

from ai_news_alerts.enrich.github import extract_github_repo
from ai_news_alerts.models import CollectorResult, SourceStatus, TrendCandidate

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_DISCUSSION_BASE = "https://news.ycombinator.com/item?id="
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r"""href=["'](https?://[^"']+)["']""", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\"]+")

GetJson = Callable[[str], object]


def collect_hn(
    feeds: Iterable[str],
    *,
    max_ids_per_feed: int,
    get_json: GetJson | None = None,
) -> CollectorResult:
    fetch = get_json or _request_json
    candidates: list[TrendCandidate] = []
    seen_ids: set[int] = set()
    item_jobs: list[tuple[str, int]] = []

    for feed in feeds:
        ids_payload = fetch(f"{HN_BASE}/{feed}.json")
        if not isinstance(ids_payload, list):
            continue
        for item_id in ids_payload[:max_ids_per_feed]:
            if not isinstance(item_id, int) or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            item_jobs.append((feed, item_id))

    with ThreadPoolExecutor(max_workers=12) as executor:
        for candidate in executor.map(lambda job: _fetch_candidate(fetch, job), item_jobs):
            if candidate is not None:
                candidates.append(candidate)

    return CollectorResult(
        candidates=candidates,
        status=SourceStatus(
            source="hn",
            status="success",
            message="ok",
            item_count=len(candidates),
        ),
    )


def _fetch_candidate(fetch: GetJson, job: tuple[str, int]) -> TrendCandidate | None:
    feed, item_id = job
    item_payload = fetch(f"{HN_BASE}/item/{item_id}.json")
    if not isinstance(item_payload, dict):
        return None
    return _candidate_from_item(feed, item_payload)


def github_repo_urls_from(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.findall(text):
        cleaned = match.rstrip(".,")
        repo = extract_github_repo(cleaned)
        if repo is None:
            continue
        normalized = f"https://github.com/{repo}"
        if normalized not in seen:
            urls.append(normalized)
            seen.add(normalized)
    return urls


def _candidate_from_item(feed: str, payload: dict[object, object]) -> TrendCandidate | None:
    if payload.get("type") != "story":
        return None
    title = str(payload.get("title") or "").strip()
    if not title:
        return None
    item_id = payload.get("id")
    if not isinstance(item_id, int):
        return None
    raw_text = str(payload.get("text") or "")
    summary = _strip_html(raw_text) if raw_text else None
    timestamp = payload.get("time")
    published_at = (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if isinstance(timestamp, int)
        else None
    )
    url_value = payload.get("url")
    url = str(url_value) if url_value else f"{HN_DISCUSSION_BASE}{item_id}"
    return TrendCandidate(
        source=f"hn:{feed}",
        source_type="hn",
        title=title,
        url=url,
        discussion_url=f"{HN_DISCUSSION_BASE}{item_id}",
        published_at=published_at,
        score=int(payload.get("score") or 0),
        comments_count=int(payload.get("descendants") or 0),
        summary=summary,
    )


def _strip_html(value: str) -> str:
    hrefs = " ".join(HREF_RE.findall(value))
    stripped = html.unescape(TAG_RE.sub(" ", value)).strip()
    return f"{stripped} {hrefs}".strip()


def _request_json(url: str) -> object:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
