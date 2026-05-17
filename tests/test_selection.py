from datetime import date, datetime, timezone

from ai_news_alerts.models import GitHubMetadata, TrendCandidate
from ai_news_alerts.selection import build_brief_items, is_relevant


def _candidate(index: int, *, url: str | None = None, score: int = 100) -> TrendCandidate:
    return TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title=f"Show HN: AI inference platform {index}",
        url=url or f"https://example.com/item-{index}",
        discussion_url=f"https://news.ycombinator.com/item?id={index}",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=score,
        comments_count=10,
        summary="An open source inference platform for model serving.",
    )


class Store:
    def __init__(self, seen: set[str] | None = None) -> None:
        self.seen = seen or set()

    def is_seen_fingerprint(self, fingerprint: str) -> bool:
        return fingerprint in self.seen


def test_relevance_filter_matches_career_keywords() -> None:
    assert is_relevant(_candidate(1), ["inference", "agents"]) is True
    unrelated = TrendCandidate(
        source="hn",
        source_type="hn",
        title="A consumer photo filter app",
        url="https://example.com/photo",
        discussion_url=None,
        published_at=None,
        score=200,
        comments_count=100,
        summary="A social photo tool.",
    )
    assert is_relevant(unrelated, ["inference", "agents"]) is False


def test_relevance_filter_does_not_match_keywords_inside_unrelated_words_or_urls() -> None:
    spirit = TrendCandidate(
        source="hn",
        source_type="hn",
        title="Let's Buy Spirit Air",
        url="https://letsbuyspiritair.com/",
        discussion_url=None,
        published_at=None,
        score=500,
        comments_count=100,
        summary="A consumer travel discussion.",
    )
    nullagent_url = TrendCandidate(
        source="hn",
        source_type="hn",
        title="New LoRa mesh radio offers more bandwidth",
        url="https://partyon.xyz/@nullagent/116499715071759135",
        discussion_url=None,
        published_at=None,
        score=400,
        comments_count=100,
        summary="A radio hardware discussion.",
    )

    assert is_relevant(spirit, ["ai", "agent", "inference"]) is False
    assert is_relevant(nullagent_url, ["ai", "agent", "inference"]) is False


def test_relevance_filter_does_not_treat_open_source_alone_as_ai_trend() -> None:
    cable_tool = TrendCandidate(
        source="hn",
        source_type="hn",
        title="Show HN: WhatCable, a tiny menu bar app for inspecting USB-C cables",
        url="https://github.com/example/whatcable",
        discussion_url=None,
        published_at=None,
        score=500,
        comments_count=100,
        summary="Built in Swift. Open source, free, no tracking.",
    )

    assert is_relevant(cable_tool, ["open source", "inference", "agent"]) is False


def test_build_brief_items_skips_low_value_consumer_prompt_listicle_and_crypto_hype() -> None:
    low_value = [
        TrendCandidate(
            source="hn:topstories",
            source_type="hn",
            title="10 best AI photo apps for your selfies",
            url="https://example.com/ai-photo-apps",
            discussion_url=None,
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            score=500,
            comments_count=100,
            summary="A consumer-only AI app listicle with no engineering detail.",
        ),
        TrendCandidate(
            source="hn:topstories",
            source_type="hn",
            title="Ultimate ChatGPT prompt collection",
            url="https://example.com/prompts",
            discussion_url=None,
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            score=400,
            comments_count=90,
            summary="Copy these prompts for AI productivity.",
        ),
        TrendCandidate(
            source="hn:topstories",
            source_type="hn",
            title="AI crypto token moonshot",
            url="https://example.com/ai-token",
            discussion_url=None,
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            score=300,
            comments_count=80,
            summary="Hype around a new crypto AI coin.",
        ),
        TrendCandidate(
            source="hn:topstories",
            source_type="hn",
            title="New model benchmark leaderboard",
            url="https://example.com/leaderboard",
            discussion_url=None,
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            score=300,
            comments_count=80,
            summary="A benchmark table with scores only.",
        ),
    ]
    useful = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="AI inference platform cuts serving latency",
        url="https://example.com/serving",
        discussion_url=None,
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=100,
        comments_count=10,
        summary="Engineering details for runtime, deployment, and model serving reliability.",
    )

    items = build_brief_items(
        [*low_value, useful],
        keywords=["ai", "benchmark", "inference", "model", "platform"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert [item.source_url for item in items] == ["https://example.com/serving"]


def test_build_brief_items_keeps_ai_tokenization_posts() -> None:
    candidate = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Multi-token prediction improves LLM inference",
        url="https://example.com/multi-token-inference",
        discussion_url=None,
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=250,
        comments_count=80,
        summary="Model serving details about tokenization, latency, and inference runtime.",
    )

    items = build_brief_items(
        [candidate],
        keywords=["llm", "inference", "runtime", "model"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert [item.source_url for item in items] == ["https://example.com/multi-token-inference"]


def test_brief_item_includes_deterministic_career_action() -> None:
    item = build_brief_items(
        [_candidate(1)],
        keywords=["inference", "platform"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )[0]

    assert item.career_action == (
        "Interview angle: serving latency; Resume/JD keyword: inference runtime; "
        "Watch: AI infrastructure/platform teams; Follow-up: skim the source and note one production trade-off."
    )


def test_build_brief_items_prefers_hn_dedupes_seen_and_caps_at_max() -> None:
    candidates = [_candidate(i, score=200 - i) for i in range(1, 13)]
    duplicate = _candidate(99, url="https://example.com/item-1", score=500)
    rss = TrendCandidate(
        source="rss:OpenAI",
        source_type="rss",
        title="New agent platform API",
        url="https://openai.com/news/agent-platform",
        discussion_url=None,
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=None,
        comments_count=None,
        summary="Official update about agent infrastructure.",
    )
    metadata = {
        "https://example.com/item-2": GitHubMetadata(
            repo="acme/runtime",
            description="Fast runtime",
            stars=1500,
            language="Rust",
            updated_at="2026-05-05T00:00:00Z",
        )
    }

    items = build_brief_items(
        [rss, *candidates, duplicate],
        keywords=["ai", "inference", "agent", "platform"],
        seen_store=Store(seen={"https://example.com/item-3"}),
        github_metadata=metadata,
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert len(items) == 7
    assert items[0].discussion_url == "https://news.ycombinator.com/item?id=99"
    assert all(item.fingerprint != "https://example.com/item-3" for item in items)
    assert len({item.fingerprint for item in items}) == len(items)
    assert any("GitHub 1.5k stars; Rust" in item.signal for item in items)


def test_build_brief_items_expands_past_target_only_for_strong_extra_signals() -> None:
    candidates = [_candidate(i, score=220 - i) for i in range(1, 8)]
    strong_extra = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Show HN: AI inference platform 8",
        url="https://example.com/item-8",
        discussion_url="https://news.ycombinator.com/item?id=8",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=100,
        comments_count=120,
        summary="An open source inference platform for model serving.",
    )
    weak_extra = _candidate(9, score=90)

    items = build_brief_items(
        [*candidates, strong_extra, weak_extra],
        keywords=["ai", "inference", "platform"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert len(items) == 8
    assert items[-1].discussion_url == "https://news.ycombinator.com/item?id=8"


def test_build_brief_items_does_not_expand_past_target_for_github_stars_only() -> None:
    candidates = [_candidate(i, score=220 - i) for i in range(1, 8)]
    weak_popular_repo = _candidate(8, score=90)
    metadata = {
        "https://example.com/item-8": GitHubMetadata(
            repo="acme/popular",
            description="Popular repo",
            stars=50000,
            language="Go",
            updated_at="2026-05-05T00:00:00Z",
        )
    }

    items = build_brief_items(
        [*candidates, weak_popular_repo],
        keywords=["ai", "inference", "platform"],
        seen_store=Store(),
        github_metadata=metadata,
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert len(items) == 7


def test_text_only_hn_repo_uses_canonical_repo_url_fingerprint() -> None:
    candidate = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://news.ycombinator.com/item?id=123",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=200,
        comments_count=50,
        summary="Repo: https://github.com/acme/agent-tool",
    )
    metadata = {
        "https://news.ycombinator.com/item?id=123": GitHubMetadata(
            repo="acme/agent-tool",
            description="Agent tool",
            stars=120,
            language="Python",
            updated_at="2026-05-05T00:00:00Z",
        )
    }

    items = build_brief_items(
        [candidate],
        keywords=["agent"],
        seen_store=Store(),
        github_metadata=metadata,
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert items[0].source_url == "https://github.com/acme/agent-tool"
    assert items[0].fingerprint == "https://github.com/acme/agent-tool"


def test_text_only_hn_repo_uses_effective_fingerprint_for_seen_and_same_run_dedupe() -> None:
    text_only = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://news.ycombinator.com/item?id=123",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=200,
        comments_count=50,
        summary="Repo: https://github.com/acme/agent-tool",
    )
    direct = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Agent tool repo",
        url="https://github.com/acme/agent-tool",
        discussion_url="https://news.ycombinator.com/item?id=456",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=190,
        comments_count=40,
        summary="Agent infrastructure tool.",
    )
    metadata = {
        "https://news.ycombinator.com/item?id=123": GitHubMetadata(
            repo="acme/agent-tool",
            description="Agent tool",
            stars=120,
            language="Python",
            updated_at="2026-05-05T00:00:00Z",
        ),
        "https://github.com/acme/agent-tool": GitHubMetadata(
            repo="acme/agent-tool",
            description="Agent tool",
            stars=120,
            language="Python",
            updated_at="2026-05-05T00:00:00Z",
        ),
    }

    seen_items = build_brief_items(
        [text_only],
        keywords=["agent"],
        seen_store=Store(seen={"https://github.com/acme/agent-tool"}),
        github_metadata=metadata,
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )
    same_run_items = build_brief_items(
        [text_only, direct],
        keywords=["agent"],
        seen_store=Store(),
        github_metadata=metadata,
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert seen_items == []
    assert len(same_run_items) == 1
    assert same_run_items[0].fingerprint == "https://github.com/acme/agent-tool"


def test_text_only_hn_repo_dedupe_does_not_depend_on_github_metadata_success() -> None:
    text_only = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://news.ycombinator.com/item?id=123",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=200,
        comments_count=50,
        summary="Repo: https://github.com/acme/agent-tool",
    )
    direct = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Agent tool repo",
        url="https://github.com/acme/agent-tool",
        discussion_url="https://news.ycombinator.com/item?id=456",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=190,
        comments_count=40,
        summary="Agent infrastructure tool.",
    )

    seen_items = build_brief_items(
        [text_only],
        keywords=["agent"],
        seen_store=Store(seen={"https://github.com/acme/agent-tool"}),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )
    same_run_items = build_brief_items(
        [text_only, direct],
        keywords=["agent"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert seen_items == []
    assert len(same_run_items) == 1
    assert same_run_items[0].fingerprint == "https://github.com/acme/agent-tool"


def test_same_run_repo_dedupe_keeps_strongest_hn_signal() -> None:
    weak_first = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://news.ycombinator.com/item?id=123",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=10,
        comments_count=1,
        summary="Repo: https://github.com/acme/agent-tool",
    )
    strong_later = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Agent tool repo",
        url="https://github.com/acme/agent-tool",
        discussion_url="https://news.ycombinator.com/item?id=456",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=500,
        comments_count=200,
        summary="Agent infrastructure tool.",
    )

    items = build_brief_items(
        [weak_first, strong_later],
        keywords=["agent"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert len(items) == 1
    assert items[0].signal == "HN 500 pts / 200 comments"
    assert items[0].discussion_url == "https://news.ycombinator.com/item?id=456"


def test_github_repo_fingerprints_are_case_insensitive() -> None:
    upper = TrendCandidate(
        source="hn:showstories",
        source_type="hn",
        title="Show HN: Agent tool",
        url="https://github.com/Acme/Agent-Tool",
        discussion_url="https://news.ycombinator.com/item?id=123",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=100,
        comments_count=20,
        summary="Agent infrastructure tool.",
    )
    lower = TrendCandidate(
        source="hn:topstories",
        source_type="hn",
        title="Agent tool repo",
        url="https://github.com/acme/agent-tool",
        discussion_url="https://news.ycombinator.com/item?id=456",
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        score=90,
        comments_count=10,
        summary="Agent infrastructure tool.",
    )

    seen_items = build_brief_items(
        [upper],
        keywords=["agent"],
        seen_store=Store(seen={"https://github.com/acme/agent-tool"}),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )
    same_run_items = build_brief_items(
        [upper, lower],
        keywords=["agent"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
    )

    assert seen_items == []
    assert len(same_run_items) == 1
    assert same_run_items[0].fingerprint == "https://github.com/acme/agent-tool"


def test_build_brief_items_skips_stale_rss_candidates() -> None:
    stale = TrendCandidate(
        source="rss:OpenAI",
        source_type="rss",
        title="Old inference platform update",
        url="https://example.com/old",
        discussion_url=None,
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        summary="An old official post about inference infrastructure.",
    )
    fresh = TrendCandidate(
        source="rss:OpenAI",
        source_type="rss",
        title="Fresh inference platform update",
        url="https://example.com/fresh",
        discussion_url=None,
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        summary="A fresh official post about inference infrastructure.",
    )

    items = build_brief_items(
        [stale, fresh],
        keywords=["inference", "platform"],
        seen_store=Store(),
        github_metadata={},
        target_items=7,
        max_items=10,
        run_date=date(2026, 5, 6),
        rss_max_age_days=7,
    )

    assert [item.source_url for item in items] == ["https://example.com/fresh"]
