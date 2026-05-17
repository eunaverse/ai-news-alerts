from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


SourceType = Literal["hn", "rss"]
Status = Literal["success", "partial_failure", "failed"]


@dataclass(frozen=True)
class GitHubMetadata:
    repo: str
    description: str
    stars: int
    language: str | None
    updated_at: str | None


@dataclass(frozen=True)
class TrendCandidate:
    source: str
    source_type: SourceType
    title: str
    url: str | None
    discussion_url: str | None
    published_at: datetime | None
    score: int | None = None
    comments_count: int | None = None
    summary: str | None = None

    @property
    def is_hn(self) -> bool:
        return self.source_type == "hn"


@dataclass(frozen=True)
class BriefItem:
    title: str
    why_it_matters: str
    quick_read: str
    signal: str
    phrase: str
    career_action: str
    source_url: str | None
    discussion_url: str | None
    fingerprint: str
    github: GitHubMetadata | None = None


@dataclass(frozen=True)
class SourceStatus:
    source: str
    status: Status
    message: str
    item_count: int = 0


@dataclass(frozen=True)
class CollectorResult:
    candidates: list[TrendCandidate]
    status: SourceStatus
