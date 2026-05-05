# Daily AI Trend Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a private Slack automation app that sends an English HN-first AI trend brief every day at 06:00 KST.

**Architecture:** The app is a small Python CLI with focused modules for models, Slack formatting, seen-state persistence, collectors, selection, and orchestration. HN and official RSS are primary discovery sources; GitHub metadata is enrichment only for repo URLs already discovered elsewhere.

**Tech Stack:** Python 3.12, pytest, requests, feedparser, PyYAML, GitHub Actions, Slack incoming webhooks.

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, test config, `ai-news-alerts` CLI entry point.
- `README.md`: setup, secrets, local verification, source strategy, manual workflow usage.
- `.gitignore`: Python caches, venvs, local scratch state.
- `.github/workflows/daily.yml`: daily 06:00 KST workflow with manual dry-run support.
- `config/sources.yaml`: HN thresholds, keywords, official RSS feeds, item count limits.
- `data/seen_news.json`: committed empty seen-state file.
- `src/ai_news_alerts/models.py`: dataclasses and typed literals.
- `src/ai_news_alerts/slack.py`: Slack escaping, link formatting, message budget handling, webhook send.
- `src/ai_news_alerts/seen.py`: duplicate detection and atomic state persistence.
- `src/ai_news_alerts/collectors/hn.py`: Hacker News API collection.
- `src/ai_news_alerts/collectors/rss.py`: official RSS collection.
- `src/ai_news_alerts/enrich/github.py`: GitHub repo metadata enrichment.
- `src/ai_news_alerts/selection.py`: relevance filtering, dedupe, item limits.
- `src/ai_news_alerts/main.py`: CLI orchestration and dry-run/send behavior.
- `tests/`: focused tests for formatting, state, selection, collectors, enrichment, and CLI behavior.

## Tasks

### Task 1: Project Skeleton and Model Contracts

- [ ] Write tests that construct `TrendCandidate`, `BriefItem`, and source status objects.
- [ ] Add package skeleton and dataclasses in `src/ai_news_alerts/models.py`.
- [ ] Add `pyproject.toml`, `.gitignore`, `config/sources.yaml`, and empty `data/seen_news.json`.
- [ ] Run `python -m pytest tests/test_models.py -q` and make it pass.

### Task 2: Slack Formatting and Delivery Boundary

- [ ] Write tests for Slack escaping, Slack links, item count display, compact English formatting, and hard message cap behavior.
- [ ] Implement `src/ai_news_alerts/slack.py` with `format_brief`, `slack_link`, `slack_escape`, and `send_slack`.
- [ ] Ensure webhook errors are sanitized and never include the raw webhook URL.
- [ ] Run `python -m pytest tests/test_slack.py -q` and make it pass.

### Task 3: Seen-State Persistence

- [ ] Write tests proving dry-run does not save state, non-dry-run can mark seen, invalid JSON is treated as empty, and atomic save writes the expected schema.
- [ ] Implement `src/ai_news_alerts/seen.py`.
- [ ] Run `python -m pytest tests/test_seen.py -q` and make it pass.

### Task 4: Selection Rules

- [ ] Write tests for HN-first candidate selection, career-relevance keyword filtering, duplicate URL removal, seen-item skipping, target 6-7 item behavior, and max 10 item cap.
- [ ] Implement `src/ai_news_alerts/selection.py`.
- [ ] Run `python -m pytest tests/test_selection.py -q` and make it pass.

### Task 5: Collectors and Enrichment

- [ ] Write tests for HN item parsing, GitHub URL extraction, RSS entry parsing, and GitHub metadata enrichment.
- [ ] Implement HN, RSS, and GitHub modules using injectable HTTP/session boundaries for tests.
- [ ] Treat collector failures as source warnings instead of crashing the whole brief.
- [ ] Run collector/enrichment tests and make them pass.

### Task 6: CLI Orchestration

- [ ] Write tests for `--dry-run`, Slack send path, missing webhook failure, Slack failure not marking seen, and environment timezone/default config parsing.
- [ ] Implement `src/ai_news_alerts/main.py`.
- [ ] Run `python -m pytest tests/test_main.py -q` and make it pass.

### Task 7: Docs and GitHub Actions

- [ ] Add README setup and manual verification instructions.
- [ ] Add GitHub Actions daily workflow with KST cron and manual dry-run input.
- [ ] Run the full suite with `python -m pytest -q -p no:cacheprovider`.
- [ ] Run `ai-news-alerts --dry-run` locally.
- [ ] Run a fresh subagent review loop until there are no actionable findings.
