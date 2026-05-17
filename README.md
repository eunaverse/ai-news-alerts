# ai-news-alerts

Daily English Slack briefs for AI trends that matter to backend, platform, data
infrastructure, AI infrastructure, inference, agents, databases, and developer
tooling work.

## What It Does

- Sends one Slack brief every day at 06:00 KST.
- Uses Hacker News as the primary community trend signal.
- Checks official AI and infrastructure blog RSS feeds.
- Includes open-source repositories when they become visible through HN or
  official posts.
- Adds GitHub metadata only as context, not as the discovery source.
- Keeps the brief English-only for light English practice.
- Sends 6-7 items on a normal day and up to 10 when strong candidates exist.
- Does not use `OPENAI_API_KEY`, paid LLM summarization, or Hugging Face in v1.

## Slack Format

```text
*Daily AI Trend Brief - May 6, 2026 KST*
7 items | HN-first, official news, open-source trends

1. *[Open source] Title*
Why it matters: It can affect serving cost, latency, and production AI platform design.
Quick read: A compact repo or source description explains the core change.
Signal: HN 428 pts / 132 comments; GitHub 3.2k stars; Rust
Phrase: "production readiness"
May-Aug career action: Interview angle: serving latency; Resume/JD keyword: inference runtime; Watch: AI infrastructure/platform teams; Follow-up: skim the source and note one production trade-off.
<https://example.com/source|Source> · <https://news.ycombinator.com/item?id=123|Discussion>
```

## Local Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider
ai-news-alerts --dry-run
```

If the console script is unavailable:

```bash
python -m ai_news_alerts.main --dry-run
```

## Required GitHub Actions Secret

- `SLACK_WEBHOOK_URL`

The value must be the full Slack incoming webhook URL:

```text
https://hooks.slack.com/services/...
```

The app validates the URL shape and sanitizes Slack delivery errors so the raw
secret is not printed.

## Manual Verification

```bash
ai-news-alerts --dry-run --date 2026-05-06
```

Dry runs print the brief only. They do not send Slack messages and do not mutate
`data/seen_news.json`.

For a real send:

```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." ai-news-alerts --date 2026-05-06
```

## Source Strategy

Primary discovery:

- Hacker News `topstories`, `beststories`, and `showstories`.
- Official RSS feeds configured in `config/sources.yaml`.

Secondary enrichment:

- If a discovered item links to a GitHub repo, the app fetches repo description,
  stars, primary language, and last update time.

Selection favors:

- AI infrastructure and inference runtime discussions.
- Agents, coding tools, evals, model-serving, and deployment workflows.
- Databases, data platforms, distributed systems, and developer tools related to
  AI workloads.
- Official announcements with backend or platform engineering impact.

Selection skips:

- Consumer-only AI apps with little engineering relevance.
- Prompt collections.
- Low-signal listicles.
- Crypto/AI hype without infrastructure relevance.
- Model benchmark posts with no practical engineering angle.
- Duplicate reposts of the same announcement.

RSS source expansion:

- Add only stable public RSS URLs from official AI, infrastructure, database,
  cloud, or developer tooling sources.
- Do not guess feed URLs. If an official source looks useful but the exact RSS
  URL is uncertain, document it for later verification instead of adding it to
  `config/sources.yaml`.
