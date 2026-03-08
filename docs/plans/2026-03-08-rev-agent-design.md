# Rev Agent — Design Document
*Date: 2026-03-08*

## Goal
Build an autonomous AI agent ("Rev") to apply for and perform RevenueCat's Agentic AI & Growth Advocate role.

## Identity
- **Name:** Rev
- **Tagline:** "Built to ship. Wired to grow."
- **Persona:** Technically sharp, developer-first, opinionated builder voice
- **Public presence:**
  - GitHub: `@rev-agent`
  - X/Twitter: `@rev_agent`
  - Blog: `revagent.dev`

## Architecture

### Core Stack
- **Runtime:** Python
- **AI:** Claude API (opus-4-6 for reasoning, haiku-4-5 for execution tasks)
- **Orchestration:** Custom agent loop (no heavy frameworks)
- **Memory:** SQLite + markdown files for context, content history, interactions
- **Tools:** Web search, browser automation, GitHub API, X API, RevenueCat API, CMS publishing

### Phase 1 — Application Agent
```
prompt → research → draft → publish → submit
```
1. Ingest RevenueCat docs, SDKs, API reference, blog
2. Research agent community discourse (X, GitHub, HN)
3. Draft application letter (~800-1200 words)
4. Deploy revagent.dev and publish letter
5. Set up X profile + GitHub presence
6. Submit URL to RevenueCat careers page

### Phase 2 — Production Agent (Weekly Loop)
```
Monday:  plan week → generate content → schedule posts
Daily:   monitor communities → engage → log interactions
Friday:  compile report → submit product feedback → async check-in
```

**Weekly KPIs:**
- 2+ published pieces (blog posts, tutorials, code samples, docs, case studies)
- 1+ growth experiment
- 50+ meaningful community interactions
- 3+ structured product feedback items
- 1 async check-in report

### Daily Knowledge Sync Pipeline
Poll and diff daily:
- RevenueCat docs site
- SDK changelogs (iOS, Android, Flutter, React Native, etc.)
- GitHub repos (release notes, issues, PRs)
- RevenueCat blog RSS

**Knowledge Store:**
```
knowledge/
  revenuecat/
    docs/        ← versioned snapshots + diffs
    sdk/         ← per-platform changelogs
    api/         ← OpenAPI spec versions
  community/
    trending/    ← hot topics from X, GitHub, Discord
    questions/   ← unanswered agent-dev questions
  content/
    published/   ← written content log (avoid duplication)
    queue/       ← ideas pipeline
```

Version-triggered content: SDK/API changes automatically queue relevant content ideas (e.g., migration guides, changelog summaries).

## Key Principles
- Agent's source code is open-sourced on GitHub as a portfolio piece
- Application letter itself demos capability (live API call, autonomous publishing)
- No competitor monitoring
- No heavy frameworks — auditable, clean Python

## Phases Timeline
- **Phase 1:** Application (no hard deadline, build it right)
- **Phase 2:** Production loop (if hired, 6-month contract at $60K)
