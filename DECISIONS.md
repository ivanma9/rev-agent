# Architecture Decisions

## 2026-03-14 — Deployment: GitHub Actions Cron over VPS

**Context:** Rev needs to run 24/7 autonomously (weekly content generation, daily community scans, publishing, reports). We evaluated three deployment options.

**Decision:** GitHub Actions with cron-triggered workflows.

**Alternatives considered:**

| Approach | Cost | Ops burden | Tradeoffs |
|----------|------|------------|-----------|
| **GitHub Actions cron** (chosen) | Free | None | No long-running process, DB committed to repo, cron can be delayed 5-30 min, no interactive CLI |
| **Hetzner VPS** | ~$5.50/mo | Medium — patches, SSH, systemd, firewall, disk failures | Full control, real-time capable, interactive CLI works |
| **Fly.io / Railway** | ~$5/mo | Low — managed, auto-deploy | Requires Dockerfile or Postgres migration |

**Also ruled out:**
- **Serverless (Lambda, Cloud Run)** — no persistent filesystem for SQLite
- **Railway free tier / Render** — ephemeral filesystem, DB wiped on redeploy

**Why GitHub Actions wins for Rev:**
- Zero server maintenance — no patches, SSH hardening, or disk failures to worry about
- Free for public repos, 2000 min/month for private (Rev uses <30 min/month)
- Secrets management built-in via GitHub Secrets dashboard
- Deploy = git push — workflows live in the repo
- No new infrastructure to learn

**Known tradeoffs we accept:**
- **DB in git history** — `rev.db` (<1MB) committed back to repo after each run. Bloats history over months. Mitigation: git LFS or migrate to free external DB (Turso) if it becomes a problem.
- **Cron imprecision** — GitHub Actions cron can delay 5-30 minutes during peak. Acceptable for weekly/daily tasks.
- **No interactive CLI in prod** — `review_drafts` only works locally. Drafts accumulate in DB and are reviewed from a local machine.
- **Cold start each run** — installs deps from scratch every time (~30s). Cached with `actions/setup-python` + pip cache.
- **6-hour max runtime** — per job limit. Rev's tasks take seconds, so irrelevant.

**What changes from current code:**
- Replace `scheduler.py` long-running loop with individual `.github/workflows/*.yml` files on cron schedules
- SQLite DB committed back to repo after each workflow run
- Secrets moved to GitHub Settings > Secrets
- No changes to any tool code (`content_generator`, `community_scanner`, `publisher`, `build_site`, `analytics`)
