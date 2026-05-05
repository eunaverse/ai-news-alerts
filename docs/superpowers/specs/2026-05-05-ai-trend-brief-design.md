# Daily AI Trend Brief Design

## Goal

Build a private Slack automation app that sends a daily English AI trend brief at
06:00 KST. The brief should help the user track career-relevant AI trends and
practice professional technical English.

The app should prioritize practical backend, platform, distributed systems, data
infrastructure, AI infrastructure, inference, agents, databases, and developer
tooling signals.

## Non-Goals

- Do not use `OPENAI_API_KEY` or any paid LLM summarization API.
- Do not include Hugging Face in v1.
- Do not rank items by visible review scores.
- Do not use GitHub stars as the primary discovery mechanism.
- Do not scrape LinkedIn, X/Twitter, or other fragile/social sources in v1.
- Do not force the brief to contain ten items when the candidate quality is low.

## Sources

### Primary Discovery

The app should discover trend candidates from:

- Hacker News top, best, show, and relevant search results.
- Official or technical blog RSS feeds from AI companies and infra vendors.

Hacker News is the primary community signal. If a GitHub repository becomes
visible through Hacker News, the app may fetch GitHub metadata as enrichment.

### Secondary Enrichment

For GitHub repository links discovered through HN or official posts, fetch:

- Repository description.
- Star count.
- Primary language.
- Last pushed or updated timestamp.

These fields are context only. They should not be the main selection criterion.

## Item Selection

The brief should select items that are already getting community or official
attention and are relevant to the user's career direction.

Prefer:

- AI infrastructure and inference runtime discussions.
- Agents, coding tools, evals, model-serving, and deployment workflows.
- Databases, data platforms, distributed systems, and developer tools related to
  AI workloads.
- Official announcements that are also likely to affect backend or platform
  engineering work.
- Open-source repositories that become visible through HN discussion.

Skip:

- Consumer-only AI apps with little engineering relevance.
- Prompt collections.
- Low-signal listicles.
- Crypto/AI hype unless there is a clear infrastructure angle.
- Model benchmark posts with no practical engineering angle.
- Duplicate reposts of the same announcement.

## Brief Size

- Target: 6 to 7 items per day.
- Maximum: 10 items per day.
- Minimum to send: 1 item.
- Do not fill weak items just to reach the maximum.
- Apply a full-message hard cap around 12,000 Slack message characters.
- If the message is too long, drop lower-priority items before truncating text.

## Slack Format

The Slack message is English-only and uses Slack `mrkdwn` links.

Template:

```text
*Daily AI Trend Brief - May 6, 2026 KST*
7 items | HN-first, official news, open-source trends

1. *[Open source] Title*
Why it matters: One short career-relevant sentence.
Quick read: One short sentence from source metadata, RSS description, HN text, or repo description.
Signal: HN 428 pts / 132 comments; GitHub 3.2k stars; Rust
Phrase: "production readiness"
<https://example.com/source|Source> · <https://news.ycombinator.com/item?id=123|Discussion>
```

Per-item rules:

- Keep each item to about four short content lines plus links.
- Use `Why it matters` for backend/platform/AI-infra relevance.
- Use `Quick read`, not LLM-generated long summaries.
- Use `Signal` for visible evidence such as HN score/comment count and GitHub
  metadata when available.
- Use `Phrase` for one useful professional English phrase from the item.
- Escape Slack labels before inserting them into `mrkdwn` links.

## CLI Behavior

The app should follow the existing private Slack automation pattern:

- Python package and CLI.
- `--dry-run` prints the brief without sending Slack or saving seen state.
- Non-dry-run sends Slack and persists seen items.
- Missing or malformed `SLACK_WEBHOOK_URL` fails clearly without printing the
  secret value.

## State

Use `data/seen_news.json` to prevent duplicate alerts.

Dry runs must not create or mutate this file. If Slack delivery fails, the app
must not mark items as seen.

## GitHub Actions

Run daily at 06:00 KST.

Use:

- `SLACK_WEBHOOK_URL` as the only required secret in v1.
- `workflow_dispatch` with dry-run support for manual verification.
- Local tests in the workflow before sending.

## Verification Expectations

Implementation should include tests for:

- Slack formatting and label escaping.
- HN candidate filtering.
- GitHub metadata enrichment when a GitHub repo URL is present.
- Dry-run no-op state behavior.
- Slack failure not marking items as seen.
- Message size limiting and maximum item count.

Manual verification should include:

- A dry-run command that prints a readable English brief.
- A normal-send path using a mocked or test webhook boundary.
- Confirmation that no secrets appear in logs or errors.
