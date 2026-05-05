from datetime import date

import pytest

from ai_news_alerts.models import BriefItem, GitHubMetadata, SourceStatus
from ai_news_alerts.slack import format_brief, send_slack, slack_escape, slack_link


def _item(index: int = 1, title: str = "[Open source] Runtime") -> BriefItem:
    return BriefItem(
        title=f"{title} {index}",
        why_it_matters="It affects serving cost and latency for AI platforms.",
        quick_read="A compact repo description explains the core change.",
        signal="HN 428 pts / 132 comments; GitHub 3.2k stars; Rust",
        phrase="production readiness",
        source_url=f"https://github.com/acme/runtime-{index}",
        discussion_url=f"https://news.ycombinator.com/item?id={index}",
        fingerprint=f"runtime-{index}",
        github=GitHubMetadata(
            repo=f"acme/runtime-{index}",
            description="Fast runtime",
            stars=3200,
            language="Rust",
            updated_at="2026-05-05T00:00:00Z",
        ),
    )


def test_slack_escape_and_link_use_mrkdwn_safely() -> None:
    assert slack_escape("A&B <C>") == "A&amp;B &lt;C&gt;"
    assert slack_link("https://example.com?a=1&b=2", "A&B <C>") == (
        "<https://example.com?a=1&b=2|A&amp;B &lt;C&gt;>"
    )


def test_slack_link_percent_encodes_mrkdwn_url_delimiters() -> None:
    assert slack_link("https://example.com/a>b|c", "Source") == (
        "<https://example.com/a%3Eb%7Cc|Source>"
    )


def test_format_brief_is_compact_english_and_includes_signals() -> None:
    text = format_brief(
        [_item(1)],
        [SourceStatus(source="rss:OpenAI", status="partial_failure", message="timeout")],
        run_date=date(2026, 5, 6),
        max_chars=12000,
    )

    assert "*Daily AI Trend Brief - May 6, 2026 KST*" in text
    assert "1 items | HN-first, official news, open-source trends" in text
    assert "1. *[Open source] Runtime 1*" in text
    assert "- Why it matters: It affects serving cost and latency for AI platforms." in text
    assert "- Quick read: A compact repo description explains the core change." in text
    assert "- Signal: HN 428 pts / 132 comments; GitHub 3.2k stars; Rust" in text
    assert '- Phrase: "production readiness"' in text
    assert (
        "- Links: <https://github.com/acme/runtime-1|Source> · "
        "<https://news.ycombinator.com/item?id=1|Discussion>"
    ) in text
    assert "Source warnings" in text


def test_format_brief_drops_lower_priority_items_to_fit_budget() -> None:
    text = format_brief([_item(i) for i in range(1, 12)], [], run_date=date(2026, 5, 6), max_chars=1100)

    assert len(text) <= 1100
    assert "1. *[Open source] Runtime 1*" in text
    assert "10. *[Open source] Runtime 10*" not in text


def test_send_slack_sanitizes_delivery_errors() -> None:
    class Response:
        status_code = 403

        def raise_for_status(self) -> None:
            raise RuntimeError("https://hooks.slack.com/services/secret-token")

    def post(*args, **kwargs):
        return Response()

    with pytest.raises(RuntimeError, match="Slack delivery failed: RuntimeError"):
        send_slack("https://hooks.slack.com/services/secret-token", "hello", post=post)
