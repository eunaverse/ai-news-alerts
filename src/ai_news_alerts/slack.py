from __future__ import annotations

from collections.abc import Callable
from datetime import date
import re
from typing import Protocol
from urllib.parse import quote

import requests

from ai_news_alerts.models import BriefItem, SourceStatus

TRUNCATION_NOTICE = "... trimmed to fit Slack message budget ..."


class SlackResponse(Protocol):
    def raise_for_status(self) -> None: ...


PostFunction = Callable[..., SlackResponse]


def slack_escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slack_link(url: str, label: str) -> str:
    return f"<{_safe_slack_url(url)}|{slack_escape(label)}>"


def format_brief(
    items: list[BriefItem],
    statuses: list[SourceStatus],
    *,
    run_date: date,
    max_chars: int = 12000,
) -> str:
    kept_items = list(items)
    while kept_items:
        text = _render_brief(kept_items, statuses, run_date)
        if len(text) <= max_chars:
            return text
        kept_items.pop()

    text = _render_brief([], statuses, run_date)
    if len(text) <= max_chars:
        return text
    return _truncate(text, max_chars)


def send_slack(webhook_url: str, text: str, post: PostFunction | None = None) -> None:
    post_message = post or requests.post
    try:
        response = post_message(webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Slack delivery failed: {_safe_slack_error(exc)}") from None


def _render_brief(items: list[BriefItem], statuses: list[SourceStatus], run_date: date) -> str:
    lines = [
        f"*Daily AI Trend Brief - {run_date.strftime('%B')} {run_date.day}, {run_date.year} KST*",
        f"{len(items)} items | HN-first, official news, open-source trends",
        "",
    ]

    if not items:
        lines.append("No strong AI trends found today.")
    else:
        for index, item in enumerate(items, start=1):
            lines.extend(_format_item(index, item))
            lines.append("")

    warnings = [status for status in statuses if status.status != "success"]
    if warnings:
        if lines[-1] != "":
            lines.append("")
        lines.append(f"*Source warnings ({len(warnings)})*")
        for status in warnings:
            lines.append(
                f"- {slack_escape(status.source)}: {slack_escape(status.status)} - "
                f"{slack_escape(status.message)}"
            )

    return "\n".join(lines).rstrip()


def _format_item(index: int, item: BriefItem) -> list[str]:
    links = []
    if item.source_url:
        links.append(slack_link(item.source_url, "Source"))
    if item.discussion_url:
        links.append(slack_link(item.discussion_url, "Discussion"))

    return [
        f"{index}. *{slack_escape(item.title)}*",
        f"Why it matters: {slack_escape(_clean(item.why_it_matters))}",
        f"Quick read: {slack_escape(_clean(item.quick_read))}",
        f"Signal: {slack_escape(_clean(item.signal))}",
        f"Phrase: \"{slack_escape(_clean(item.phrase))}\"",
        " · ".join(links),
    ]


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _safe_slack_url(url: str) -> str:
    return quote(url, safe=":/?#[]@!$&'()*+,;=%")


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= len(TRUNCATION_NOTICE):
        return TRUNCATION_NOTICE[:max_chars]
    return text[: max_chars - len(TRUNCATION_NOTICE) - 1].rstrip() + "\n" + TRUNCATION_NOTICE


def _safe_slack_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code:
        return f"HTTP {status_code}"
    return exc.__class__.__name__
