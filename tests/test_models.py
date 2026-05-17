from datetime import datetime, timezone

from ai_news_alerts.models import BriefItem, GitHubMetadata, SourceStatus, TrendCandidate


def test_model_contracts_hold_trend_and_brief_fields() -> None:
    candidate = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Show HN: Fast LLM inference runtime",
        url="https://github.com/acme/runtime",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=428,
        comments_count=132,
        summary="A runtime for cheaper LLM serving.",
    )
    github = GitHubMetadata(
        repo="acme/runtime",
        description="Fast LLM inference runtime",
        stars=3200,
        language="Rust",
        updated_at="2026-05-05T00:00:00Z",
    )
    item = BriefItem(
        title="[Open source] Fast LLM inference runtime",
        why_it_matters="Inference runtimes shape serving cost and latency.",
        quick_read="A runtime for cheaper LLM serving.",
        signal="HN 428 pts / 132 comments; GitHub 3.2k stars; Rust",
        phrase="production readiness",
        career_action=(
            "Interview angle: serving latency; Resume/JD keyword: inference runtime; "
            "Watch: AI infrastructure teams; Follow-up: skim the source and save one system-design trade-off."
        ),
        source_url=candidate.url,
        discussion_url=candidate.discussion_url,
        fingerprint="github.com/acme/runtime",
        github=github,
    )
    status = SourceStatus(source="hn", status="success", message="ok", item_count=1)

    assert candidate.is_hn is True
    assert item.career_action.startswith("Interview angle:")
    assert item.github == github
    assert status.status == "success"
