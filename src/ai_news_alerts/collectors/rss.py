from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import html
import re
import time

import feedparser
import requests

from ai_news_alerts.models import CollectorResult, SourceStatus, TrendCandidate

Parser = Callable[[str], object]


def collect_rss(feeds: list[Mapping[str, object]], parser: Parser | None = None) -> CollectorResult:
    parse = parser or _parse_url
    candidates: list[TrendCandidate] = []
    failures: list[str] = []

    for feed in feeds:
        name = str(feed.get("name") or "unknown")
        url = str(feed.get("url") or "")
        if not url:
            continue
        try:
            parsed = parse(url)
            entries = _entries(parsed)
            for entry in entries:
                candidate = _candidate_from_entry(name, entry)
                if candidate is not None:
                    candidates.append(candidate)
        except Exception as exc:
            failures.append(f"{name}: {exc.__class__.__name__}")

    if failures and candidates:
        status = SourceStatus("rss", "partial_failure", "; ".join(failures), len(candidates))
    elif failures:
        status = SourceStatus("rss", "failed", "; ".join(failures), 0)
    else:
        status = SourceStatus("rss", "success", "ok", len(candidates))

    return CollectorResult(candidates=candidates, status=status)


def _parse_url(url: str) -> object:
    response = requests.get(url, timeout=8, headers={"User-Agent": "ai-news-alerts"})
    response.raise_for_status()
    return feedparser.parse(response.content)


def _entries(parsed: object) -> list[Mapping[str, object]]:
    if isinstance(parsed, Mapping):
        entries = parsed.get("entries", [])
    else:
        entries = getattr(parsed, "entries", [])
    return [entry for entry in entries if isinstance(entry, Mapping)]


def _candidate_from_entry(name: str, entry: Mapping[str, object]) -> TrendCandidate | None:
    title = str(entry.get("title") or "").strip()
    link = str(entry.get("link") or "").strip()
    if not title or not link:
        return None
    summary = _strip_html(str(entry.get("summary") or entry.get("description") or "")) or None
    published_at = _published_at(entry)
    return TrendCandidate(
        source=f"rss:{name}",
        source_type="rss",
        title=title,
        url=link,
        discussion_url=None,
        published_at=published_at,
        summary=summary,
    )


def _published_at(entry: Mapping[str, object]) -> datetime | None:
    value = entry.get("published_parsed") or entry.get("updated_parsed")
    if isinstance(value, time.struct_time):
        parts = value[:6]
    elif isinstance(value, tuple) and len(value) >= 6:
        parts = value[:6]
    else:
        return None
    return datetime(*parts, tzinfo=timezone.utc)


TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()
