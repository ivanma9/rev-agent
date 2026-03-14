# GitHub Actions Deployment Plan

**Goal:** Replace the local APScheduler loop with GitHub Actions cron workflows so Rev runs 24/7 without a VPS.

**Decision context:** See `DECISIONS.md` — GitHub Actions was chosen over VPS for zero ops overhead, free tier, and built-in secrets management.

## Workflow Schedule

| Scheduler Task | Cron | Workflow File |
|---|---|---|
| `sync` (knowledge_sync) | `0 6 * * *` daily | `daily-sync.yml` |
| `community` + `scan_communities` | `30 10 * * *` daily | `community-scan.yml` |
| `content` + `feedback` | `0 8 * * 1` Monday | `weekly-content.yml` |
| `publish` + `build_site` | `0 10 * * 2` Tuesday | `weekly-publish.yml` |
| `report` + `feedback_submit` | `0 16 * * 5` Friday | `weekly-report.yml` |

## Tasks

### Task 1 — Verify `.env` is gitignored
- Check `.gitignore` includes `data/rev.db` and `.env`
- Ensure no secrets are committed to git history

### Task 2 — Create `.github/actions/rev-setup/action.yml`
Composite action: checkout (with PAT), Python 3.12 setup, pip install with cache.

### Task 3 — Create `.github/actions/commit-db/action.yml`
Composite action: git config, `git add data/rev.db`, commit with `[skip ci]`, pull --rebase, push.

### Tasks 4-8 — Create workflow files
Each follows the pattern: setup → run task(s) → commit DB back.
Includes `workflow_dispatch` for manual triggering and `concurrency` to prevent overlapping runs.

### Task 9 — Add secrets to GitHub repository settings
Required secrets (all from `.env`):
- `REV_GITHUB_TOKEN` — PAT with repo scope (not the default GITHUB_TOKEN)
- `ANTHROPIC_API_KEY`
- `REVENUECAT_EMAIL`, `REVENUECAT_PASSWORD`
- `GMAIL`, `GMAIL_PASSWORD`
- `REVENUECAT_API_KEY`, `REVENUECAT_PROJECT_ID`
- `LANGSMITH_API_KEY`
- `X_API_KEY`, `X_API_SECRET`, `X_BEARER_TOKEN`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

Repository variables (non-sensitive):
- `GITHUB_USERNAME`, `GITHUB_REPO`, `LANGSMITH_PROJECT`, `LANGCHAIN_TRACING_V2`

### Task 10 — Remove APScheduler
After workflows verified working: remove APScheduler from requirements.txt, simplify scheduler.py to just `run_now()` + `_build_tasks()`.

## Key Design Decisions

- **Inline steps, not composite actions** — Start with inline YAML steps in each workflow. Extract to composite actions only if duplication becomes painful (5 workflows × ~15 lines = manageable).
- **`[skip ci]` on DB commits** — Prevents infinite workflow trigger loops.
- **`pull --rebase` before push** — Handles rare case of concurrent runs writing to DB simultaneously.
- **PAT required** — Default `GITHUB_TOKEN` cannot push commits that trigger other workflows; `REV_GITHUB_TOKEN` PAT is required.
- **`workflow_dispatch`** — All workflows have manual trigger for testing without waiting for cron.
- **Concurrency groups** — Prevent two instances of the same workflow running simultaneously (could corrupt DB commit-back).
