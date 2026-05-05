from __future__ import annotations

import argparse
from datetime import date, datetime
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from ai_news_alerts.collectors.hn import collect_hn, github_repo_urls_from
from ai_news_alerts.collectors.rss import collect_rss
from ai_news_alerts.enrich.github import GitHubClient, extract_github_repo
from ai_news_alerts.models import GitHubMetadata, SourceStatus, TrendCandidate
from ai_news_alerts.seen import SeenStore
from ai_news_alerts.selection import build_brief_items
from ai_news_alerts.slack import format_brief, send_slack


def run(args: argparse.Namespace) -> str:
    config = load_yaml(args.config)
    run_date = parse_run_date(args.date, args.timezone)
    seen_store = SeenStore(args.seen)

    candidates, statuses = collect_candidates(config)
    github_metadata = enrich_github_metadata(candidates)
    items = build_brief_items(
        candidates=candidates,
        keywords=[str(keyword) for keyword in config.get("keywords", [])],
        seen_store=seen_store,
        github_metadata=github_metadata,
        target_items=int(config.get("target_items", 7)),
        max_items=int(config.get("max_items", 10)),
        run_date=run_date,
        rss_max_age_days=int(config.get("rss_max_age_days", 7)),
    )
    digest = format_brief(
        items,
        statuses,
        run_date=run_date,
        max_chars=int(config.get("message_max_chars", 12000)),
    )

    if args.dry_run:
        print(digest)
        return digest

    webhook_url = require_slack_webhook()
    send_slack(webhook_url, digest)
    for item in items:
        seen_store.mark_seen(item)
    seen_store.save()
    return digest


def cli() -> None:
    parser = argparse.ArgumentParser(description="Send a daily AI trend Slack brief.")
    parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--seen", type=Path, default=Path("data/seen_news.json"))
    parser.add_argument("--timezone", default=os.environ.get("TIMEZONE", "Asia/Seoul"))
    parser.add_argument("--date", help="Override local date as YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args())


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return dict(payload)


def collect_candidates(config: dict[str, Any]) -> tuple[list[TrendCandidate], list[SourceStatus]]:
    candidates: list[TrendCandidate] = []
    statuses: list[SourceStatus] = []

    hn_config = config.get("hacker_news", {})
    if isinstance(hn_config, dict):
        try:
            hn_result = collect_hn(
                [str(feed) for feed in hn_config.get("feeds", [])],
                max_ids_per_feed=int(hn_config.get("max_ids_per_feed", 80)),
            )
            min_score = int(hn_config.get("min_score", 0))
            min_comments = int(hn_config.get("min_comments", 0))
            hn_candidates = [
                candidate
                for candidate in hn_result.candidates
                if (candidate.score or 0) >= min_score
                or (candidate.comments_count or 0) >= min_comments
            ]
            candidates.extend(hn_candidates)
            statuses.append(
                SourceStatus("hn", hn_result.status.status, hn_result.status.message, len(hn_candidates))
            )
        except Exception as exc:
            statuses.append(SourceStatus("hn", "failed", exc.__class__.__name__, 0))

    feeds = config.get("official_feeds", [])
    if isinstance(feeds, list):
        rss_result = collect_rss([feed for feed in feeds if isinstance(feed, dict)])
        candidates.extend(rss_result.candidates)
        statuses.append(rss_result.status)

    return candidates, statuses


def enrich_github_metadata(candidates: list[TrendCandidate]) -> dict[str, GitHubMetadata]:
    client = GitHubClient()
    metadata: dict[str, GitHubMetadata] = {}
    repo_cache: dict[str, GitHubMetadata | None] = {}

    for candidate in candidates:
        if not candidate.url:
            continue
        for repo in github_repos_for_candidate(candidate):
            if repo not in repo_cache:
                repo_cache[repo] = client.fetch(repo)
            if repo_cache[repo] is not None:
                metadata[candidate.url] = repo_cache[repo]
                break

    return metadata


def github_repos_for_candidate(candidate: TrendCandidate) -> list[str]:
    repos: list[str] = []
    seen: set[str] = set()

    direct_repo = extract_github_repo(candidate.url)
    if direct_repo is not None:
        repos.append(direct_repo)
        seen.add(direct_repo)

    for url in github_repo_urls_from(candidate.summary or ""):
        repo = extract_github_repo(url)
        if repo is not None and repo not in seen:
            repos.append(repo)
            seen.add(repo)

    return repos


def parse_run_date(value: str | None, timezone: str) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(ZoneInfo(timezone)).date()


def require_slack_webhook() -> str:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url.startswith("https://hooks.slack.com/services/"):
        raise RuntimeError("SLACK_WEBHOOK_URL must be a full Slack incoming webhook URL")
    return webhook_url


if __name__ == "__main__":
    cli()
