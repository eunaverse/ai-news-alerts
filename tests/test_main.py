from argparse import Namespace
from datetime import date
import json

import pytest

from ai_news_alerts.models import BriefItem, SourceStatus


def _config(path):
    path.write_text(
        "\n".join(
            [
                "timezone: Asia/Seoul",
                "target_items: 7",
                "max_items: 10",
                "message_max_chars: 12000",
                "hacker_news:",
                "  feeds: [topstories]",
                "  max_ids_per_feed: 10",
                "keywords: [ai, inference, platform]",
                "official_feeds: []",
            ]
        ),
        encoding="utf-8",
    )


def _item() -> BriefItem:
    return BriefItem(
        title="[Community] AI inference platform",
        why_it_matters="It affects serving cost and latency for AI platforms.",
        quick_read="A compact description explains the core change.",
        signal="HN 100 pts / 20 comments",
        phrase="production readiness",
        source_url="https://example.com",
        discussion_url="https://news.ycombinator.com/item?id=1",
        fingerprint="https://example.com",
    )


def test_run_dry_run_prints_without_slack_or_seen_write(tmp_path, monkeypatch, capsys) -> None:
    import ai_news_alerts.main as main

    config = tmp_path / "sources.yaml"
    seen = tmp_path / "seen.json"
    _config(config)
    monkeypatch.setattr(main, "collect_candidates", lambda cfg: ([], []))
    monkeypatch.setattr(main, "enrich_github_metadata", lambda candidates: {})
    monkeypatch.setattr(main, "build_brief_items", lambda **kwargs: [_item()])
    monkeypatch.setattr(main, "send_slack", lambda url, text: pytest.fail("should not send"))

    digest = main.run(Namespace(config=config, seen=seen, timezone="Asia/Seoul", dry_run=True, date="2026-05-06"))

    assert digest in capsys.readouterr().out
    assert "Daily AI Trend Brief" in digest
    assert not seen.exists()


def test_run_sends_slack_and_marks_seen_after_success(tmp_path, monkeypatch) -> None:
    import ai_news_alerts.main as main

    config = tmp_path / "sources.yaml"
    seen = tmp_path / "seen.json"
    _config(config)
    monkeypatch.setattr(main, "collect_candidates", lambda cfg: ([], []))
    monkeypatch.setattr(main, "enrich_github_metadata", lambda candidates: {})
    monkeypatch.setattr(main, "build_brief_items", lambda **kwargs: [_item()])
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/C")
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(main, "send_slack", lambda url, text: sent.append((url, text)))

    digest = main.run(Namespace(config=config, seen=seen, timezone="Asia/Seoul", dry_run=False, date="2026-05-06"))

    assert sent == [("https://hooks.slack.com/services/T/B/C", digest)]
    assert "https://example.com" in json.loads(seen.read_text(encoding="utf-8"))["seen"]


def test_run_does_not_mark_seen_when_slack_fails(tmp_path, monkeypatch) -> None:
    import ai_news_alerts.main as main

    config = tmp_path / "sources.yaml"
    seen = tmp_path / "seen.json"
    _config(config)
    monkeypatch.setattr(main, "collect_candidates", lambda cfg: ([], []))
    monkeypatch.setattr(main, "enrich_github_metadata", lambda candidates: {})
    monkeypatch.setattr(main, "build_brief_items", lambda **kwargs: [_item()])
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/C")
    monkeypatch.setattr(main, "send_slack", lambda url, text: (_ for _ in ()).throw(RuntimeError("slack failed")))

    with pytest.raises(RuntimeError, match="slack failed"):
        main.run(Namespace(config=config, seen=seen, timezone="Asia/Seoul", dry_run=False, date="2026-05-06"))

    assert not seen.exists()


def test_run_fails_clearly_when_webhook_missing_or_malformed(tmp_path, monkeypatch) -> None:
    import ai_news_alerts.main as main

    config = tmp_path / "sources.yaml"
    _config(config)
    monkeypatch.setattr(main, "collect_candidates", lambda cfg: ([], []))
    monkeypatch.setattr(main, "enrich_github_metadata", lambda candidates: {})
    monkeypatch.setattr(main, "build_brief_items", lambda **kwargs: [_item()])
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/not-slack")

    with pytest.raises(RuntimeError, match="SLACK_WEBHOOK_URL must be a full Slack incoming webhook URL"):
        main.run(
            Namespace(
                config=config,
                seen=tmp_path / "seen.json",
                timezone="Asia/Seoul",
                dry_run=False,
                date="2026-05-06",
            )
        )


def test_parse_run_date_uses_explicit_date() -> None:
    from ai_news_alerts.main import parse_run_date

    assert parse_run_date("2026-05-06", "Asia/Seoul") == date(2026, 5, 6)


def test_github_repos_for_candidate_includes_repo_link_from_hn_text() -> None:
    from ai_news_alerts.main import github_repos_for_candidate
    from ai_news_alerts.models import TrendCandidate

    candidate = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://news.ycombinator.com/item?id=123",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=None,
        summary="Repo: https://github.com/acme/agent-tool",
    )

    assert github_repos_for_candidate(candidate) == ["acme/agent-tool"]
