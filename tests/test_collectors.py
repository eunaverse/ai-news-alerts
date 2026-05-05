from datetime import timezone

from ai_news_alerts.collectors.hn import collect_hn, github_repo_urls_from
from ai_news_alerts.collectors.rss import collect_rss
from ai_news_alerts.enrich.github import GitHubClient, extract_github_repo


def test_collect_hn_parses_story_items_and_discussion_links() -> None:
    payloads = {
        "https://hacker-news.firebaseio.com/v0/topstories.json": [123],
        "https://hacker-news.firebaseio.com/v0/item/123.json": {
            "id": 123,
            "type": "story",
            "title": "Show HN: AI inference runtime",
            "url": "https://github.com/acme/runtime",
            "score": 428,
            "descendants": 132,
            "time": 1777939200,
            "text": "A fast model serving runtime",
        },
    }

    def get_json(url: str):
        return payloads[url]

    result = collect_hn(["topstories"], max_ids_per_feed=5, get_json=get_json)

    assert result.status.status == "success"
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "Show HN: AI inference runtime"
    assert candidate.discussion_url == "https://news.ycombinator.com/item?id=123"
    assert candidate.published_at is not None
    assert candidate.published_at.tzinfo == timezone.utc


def test_github_repo_url_helpers_ignore_non_repo_paths() -> None:
    assert extract_github_repo("https://github.com/acme/runtime/issues/1") == "acme/runtime"
    assert extract_github_repo("https://github.com/features/actions") is None
    assert github_repo_urls_from("See https://github.com/acme/runtime and https://example.com") == [
        "https://github.com/acme/runtime"
    ]


def test_collect_hn_preserves_github_href_urls_for_enrichment() -> None:
    payloads = {
        "https://hacker-news.firebaseio.com/v0/showstories.json": [123],
        "https://hacker-news.firebaseio.com/v0/item/123.json": {
            "id": 123,
            "type": "story",
            "title": "Show HN: Agent tool",
            "score": 100,
            "descendants": 20,
            "time": 1777939200,
            "text": 'Repo: <a href="https://github.com/acme/agent-tool">agent-tool</a>',
        },
    }

    result = collect_hn(["showstories"], max_ids_per_feed=5, get_json=lambda url: payloads[url])

    assert github_repo_urls_from(result.candidates[0].summary or "") == [
        "https://github.com/acme/agent-tool"
    ]


def test_collect_rss_parses_entries_with_injected_parser() -> None:
    def parser(url: str):
        return {
            "entries": [
                {
                    "title": "New agent infrastructure release",
                    "link": "https://example.com/agent",
                    "summary": "Official notes about AI platform infrastructure.",
                    "published_parsed": (2026, 5, 5, 1, 2, 3, 0, 0, 0),
                }
            ]
        }

    result = collect_rss([{"name": "Example", "url": "https://example.com/feed"}], parser=parser)

    assert result.status.status == "success"
    assert result.candidates[0].source == "rss:Example"
    assert result.candidates[0].summary == "Official notes about AI platform infrastructure."


def test_collect_rss_strips_html_from_summary() -> None:
    def parser(url: str):
        return {
            "entries": [
                {
                    "title": "Agent infrastructure release",
                    "link": "https://example.com/agent",
                    "summary": "<p>Official <strong>agent</strong> notes.</p><img src='x'>",
                    "published_parsed": (2026, 5, 5, 1, 2, 3, 0, 0, 0),
                }
            ]
        }

    result = collect_rss([{"name": "Example", "url": "https://example.com/feed"}], parser=parser)

    assert result.candidates[0].summary == "Official agent notes."


def test_github_client_fetches_metadata_with_injected_get_json() -> None:
    def get_json(url: str, headers=None):
        assert url == "https://api.github.com/repos/acme/runtime"
        return {
            "full_name": "acme/runtime",
            "description": "Fast model serving runtime",
            "stargazers_count": 3200,
            "language": "Rust",
            "pushed_at": "2026-05-05T00:00:00Z",
        }

    metadata = GitHubClient(get_json=get_json).fetch("acme/runtime")

    assert metadata is not None
    assert metadata.repo == "acme/runtime"
    assert metadata.stars == 3200


def test_github_client_uses_token_header_when_available(monkeypatch) -> None:
    captured_headers: list[dict[str, str] | None] = []

    def get_json(url: str, headers=None):
        captured_headers.append(headers)
        return {
            "full_name": "acme/runtime",
            "description": "Fast model serving runtime",
            "stargazers_count": 3200,
            "language": "Rust",
            "pushed_at": "2026-05-05T00:00:00Z",
        }

    monkeypatch.setenv("GITHUB_TOKEN", "token-123")

    GitHubClient(get_json=get_json).fetch("acme/runtime")

    assert captured_headers[0]["Authorization"] == "Bearer token-123"
