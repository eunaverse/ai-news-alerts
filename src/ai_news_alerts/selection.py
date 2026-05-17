from __future__ import annotations

from datetime import date, timedelta
import re
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_news_alerts.collectors.hn import github_repo_urls_from
from ai_news_alerts.enrich.github import extract_github_repo
from ai_news_alerts.models import BriefItem, GitHubMetadata, TrendCandidate


CONTEXT_ONLY_KEYWORDS = {"open source"}


class SeenLookup(Protocol):
    def is_seen_fingerprint(self, fingerprint: str) -> bool: ...


def is_relevant(candidate: TrendCandidate, keywords: list[str]) -> bool:
    if _is_low_value(candidate):
        return False
    haystack = " ".join(
        value
        for value in [
            candidate.title,
            candidate.summary or "",
        ]
        if value
    ).lower()
    return any(
        _keyword_matches(haystack, keyword)
        for keyword in keywords
        if keyword.lower().strip() not in CONTEXT_ONLY_KEYWORDS
    )


def build_brief_items(
    candidates: list[TrendCandidate],
    *,
    keywords: list[str],
    seen_store: SeenLookup,
    github_metadata: dict[str, GitHubMetadata],
    target_items: int,
    max_items: int,
    run_date: date | None = None,
    rss_max_age_days: int = 7,
) -> list[BriefItem]:
    best_by_fingerprint: dict[str, TrendCandidate] = {}

    for candidate in candidates:
        github = github_metadata.get(candidate.url or "")
        fingerprint = effective_fingerprint(candidate, github)
        if seen_store.is_seen_fingerprint(fingerprint):
            continue
        if _is_stale_rss(candidate, run_date, rss_max_age_days):
            continue
        if _is_low_value(candidate):
            continue
        if not is_relevant(candidate, keywords):
            continue
        current = best_by_fingerprint.get(fingerprint)
        if current is None or _candidate_sort_key(candidate) < _candidate_sort_key(current):
            best_by_fingerprint[fingerprint] = candidate

    unique = list(best_by_fingerprint.values())
    unique.sort(key=_candidate_sort_key)
    selected = _select_target_then_strong_extras(unique, github_metadata, target_items, max_items)
    return [
        _brief_item_from_candidate(candidate, github_metadata.get(candidate.url or ""))
        for candidate in selected
    ]


def candidate_fingerprint(candidate: TrendCandidate) -> str:
    if candidate.url:
        return canonical_url(candidate.url)
    if candidate.discussion_url:
        return canonical_url(candidate.discussion_url)
    return re.sub(r"\s+", "-", candidate.title.strip().lower())


def effective_fingerprint(candidate: TrendCandidate, github: GitHubMetadata | None) -> str:
    if github is not None and extract_github_repo(candidate.url) is None:
        return canonical_url(f"https://github.com/{github.repo}")
    repo_url = _first_candidate_repo_url(candidate)
    if repo_url is not None:
        return canonical_url(repo_url)
    return candidate_fingerprint(candidate)


def _first_candidate_repo_url(candidate: TrendCandidate) -> str | None:
    direct_repo = extract_github_repo(candidate.url)
    if direct_repo is not None:
        return f"https://github.com/{direct_repo}"
    summary_urls = github_repo_urls_from(candidate.summary or "")
    if summary_urls:
        return summary_urls[0]
    return None


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    normalized_query = urlencode(sorted(query))
    path = parts.path.rstrip("/") or parts.path
    if parts.netloc.lower() == "github.com":
        path = path.lower()
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, normalized_query, ""))


def _candidate_sort_key(candidate: TrendCandidate) -> tuple[int, int, int, float]:
    timestamp = candidate.published_at.timestamp() if candidate.published_at else 0.0
    return (
        0 if candidate.source_type == "hn" else 1,
        -(candidate.score or 0),
        -(candidate.comments_count or 0),
        -timestamp,
    )


def _select_target_then_strong_extras(
    candidates: list[TrendCandidate],
    github_metadata: dict[str, GitHubMetadata],
    target_items: int,
    max_items: int,
) -> list[TrendCandidate]:
    selected = candidates[:target_items]
    for candidate in candidates[target_items:]:
        if len(selected) >= max_items:
            break
        if _has_strong_extra_signal(candidate, github_metadata.get(candidate.url or "")):
            selected.append(candidate)
    return selected


def _has_strong_extra_signal(candidate: TrendCandidate, github: GitHubMetadata | None) -> bool:
    if candidate.source_type == "rss":
        return False
    if (candidate.score or 0) >= 250:
        return True
    if (candidate.comments_count or 0) >= 100:
        return True
    return False


def _is_stale_rss(candidate: TrendCandidate, run_date: date | None, rss_max_age_days: int) -> bool:
    if candidate.source_type != "rss" or run_date is None:
        return False
    if candidate.published_at is None:
        return True
    return candidate.published_at.date() < run_date - timedelta(days=rss_max_age_days)


def _brief_item_from_candidate(candidate: TrendCandidate, github: GitHubMetadata | None) -> BriefItem:
    detected_repo = extract_github_repo(candidate.url)
    detected_repo_url = _first_candidate_repo_url(candidate)
    category = _category(candidate, github, detected_repo)
    title = f"[{category}] {_shorten(candidate.title, 120)}"
    source_url = candidate.url
    if detected_repo is None and detected_repo_url is not None:
        source_url = detected_repo_url
    elif github is not None and detected_repo is None:
        source_url = f"https://github.com/{github.repo}"
    fingerprint = effective_fingerprint(candidate, github)
    return BriefItem(
        title=title,
        why_it_matters=_why_it_matters(candidate),
        quick_read=_quick_read(candidate, github),
        signal=_signal(candidate, github),
        phrase=_phrase(candidate),
        career_action=_career_action(candidate),
        source_url=source_url,
        discussion_url=candidate.discussion_url,
        fingerprint=fingerprint,
        github=github,
    )


def _category(candidate: TrendCandidate, github: GitHubMetadata | None, detected_repo: str | None) -> str:
    if github is not None or detected_repo is not None:
        return "Open source"
    if candidate.source_type == "rss":
        return "Official"
    return "Community"


def _why_it_matters(candidate: TrendCandidate) -> str:
    text = _combined_text(candidate)
    if any(term in text for term in ["inference", "serving", "runtime", "latency"]):
        return "It can affect serving cost, latency, and production AI platform design."
    if any(term in text for term in ["agent", "coding", "developer tool", "ide"]):
        return "It can change developer workflows and automation patterns."
    if any(term in text for term in ["database", "retrieval", "rag", "vector", "data platform"]):
        return "It is relevant to AI data infrastructure and retrieval quality."
    if any(term in text for term in ["eval", "benchmark", "reliability"]):
        return "It helps evaluate model quality and production readiness."
    return "It is relevant to backend, platform, and AI infrastructure decisions."


def _quick_read(candidate: TrendCandidate, github: GitHubMetadata | None) -> str:
    if candidate.summary:
        return _shorten(_clean(candidate.summary), 180)
    if github and github.description:
        return _shorten(_clean(github.description), 180)
    return _shorten(_clean(candidate.title), 180)


def _signal(candidate: TrendCandidate, github: GitHubMetadata | None) -> str:
    parts: list[str] = []
    if candidate.source_type == "hn":
        parts.append(f"HN {candidate.score or 0} pts / {candidate.comments_count or 0} comments")
    else:
        parts.append(f"Official feed: {candidate.source.removeprefix('rss:')}")
    if github is not None:
        github_part = f"GitHub {_format_stars(github.stars)} stars"
        if github.language:
            github_part += f"; {github.language}"
        parts.append(github_part)
    return "; ".join(parts)


def _phrase(candidate: TrendCandidate) -> str:
    text = _combined_text(candidate)
    if "production" in text:
        return "production readiness"
    if "deploy" in text or "serving" in text:
        return "deployment trade-off"
    if "latency" in text:
        return "latency budget"
    if "agent" in text:
        return "agent workflow"
    if "inference" in text:
        return "serving cost"
    if "eval" in text or "benchmark" in text:
        return "reliability signal"
    return "career-relevant signal"


def _career_action(candidate: TrendCandidate) -> str:
    text = _combined_text(candidate)
    if any(term in text for term in ["inference", "serving", "runtime", "latency"]):
        return (
            "Interview angle: serving latency; Resume/JD keyword: inference runtime; "
            "Watch: AI infrastructure/platform teams; Follow-up: skim the source and note one production trade-off."
        )
    if any(term in text for term in ["agent", "coding", "developer tool", "ide"]):
        return (
            "Interview angle: agent workflow design; Resume/JD keyword: developer tooling; "
            "Watch: agent platform/dev-experience teams; Follow-up: save one workflow automation example."
        )
    if any(term in text for term in ["database", "retrieval", "rag", "vector", "data platform"]):
        return (
            "Interview angle: retrieval architecture; Resume/JD keyword: RAG/vector search; "
            "Watch: data platform/search infrastructure teams; Follow-up: sketch the data path in 3 steps."
        )
    if any(term in text for term in ["eval", "benchmark", "reliability"]):
        return (
            "Interview angle: evaluation design; Resume/JD keyword: model reliability; "
            "Watch: ML platform/reliability teams; Follow-up: capture one metric or failure mode."
        )
    return (
        "Interview angle: backend platform trade-offs; Resume/JD keyword: AI infrastructure; "
        "Watch: platform/infrastructure teams; Follow-up: save one practical engineering takeaway."
    )


def _combined_text(candidate: TrendCandidate) -> str:
    return f"{candidate.title} {candidate.summary or ''} {candidate.url or ''}".lower()


def _is_low_value(candidate: TrendCandidate) -> bool:
    text = _combined_text(candidate)
    title = candidate.title.lower()
    has_engineering_angle = any(
        term in text
        for term in [
            "architecture",
            "backend",
            "database",
            "data platform",
            "deploy",
            "developer tool",
            "distributed",
            "eval harness",
            "inference",
            "infrastructure",
            "latency",
            "model serving",
            "platform",
            "production",
            "rag",
            "reliability",
            "retrieval",
            "runtime",
            "serving",
            "vector",
        ]
    )
    if any(term in text for term in ["prompt collection", "prompt pack", "prompt library", "chatgpt prompts"]):
        return True
    crypto_hype_terms = [
        "airdrop",
        "blockchain",
        "coin",
        "crypto",
        "crypto token",
        "defi",
        "memecoin",
        "nft",
        "token moonshot",
        "web3",
    ]
    if any(term in text for term in crypto_hype_terms) and not has_engineering_angle:
        return True
    if any(term in text for term in ["photo app", "selfie", "avatar app", "dating app", "social app"]) and not has_engineering_angle:
        return True
    if any(term in title for term in ["best ai", "top ai", "list of ai", "10 best", "ultimate guide"]) and not has_engineering_angle:
        return True
    if any(term in text for term in ["leaderboard", "scores only", "benchmark table"]) and not has_engineering_angle:
        return True
    return False


def _keyword_matches(haystack: str, keyword: str) -> bool:
    normalized = keyword.lower().strip()
    if not normalized:
        return False
    pattern = re.escape(normalized).replace(r"\ ", r"[\s-]+")
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack) is not None


def _format_stars(stars: int) -> str:
    if stars >= 1000:
        value = stars / 1000
        return f"{value:.1f}k".replace(".0k", "k")
    return str(stars)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
