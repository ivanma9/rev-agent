# Running Rev

## Background Service (macOS LaunchAgent)

Rev can run as a persistent background service that starts automatically on login and restarts if it crashes.

### Start the service

```bash
launchctl load ~/Desktop/agents/RevCat/com.revenuecat.rev.plist
```

### Stop the service

```bash
launchctl unload ~/Desktop/agents/RevCat/com.revenuecat.rev.plist
```

### Check service status

```bash
launchctl list | grep revenuecat
```

### View logs

```bash
# Live stdout (scheduler activity)
tail -f ~/Desktop/agents/RevCat/logs/rev.log

# Live stderr (errors and tracebacks)
tail -f ~/Desktop/agents/RevCat/logs/rev.err

# Both streams together
tail -f ~/Desktop/agents/RevCat/logs/rev.log ~/Desktop/agents/RevCat/logs/rev.err
```

## Run Manually

### Start the scheduler (blocking, Ctrl-C to stop)

```bash
cd ~/Desktop/agents/RevCat
source .venv/bin/activate
python -m src.scheduler
```

### Run a single task immediately

```bash
cd ~/Desktop/agents/RevCat
source .venv/bin/activate
python -m src.scheduler <task>
```

Available tasks: `sync`, `content`, `publish`, `community`, `report`, `feedback`, `feedback_submit`, `scan_communities`, `build_site`, `x_post`

Example:

```bash
python -m src.scheduler sync
```

## Schedule

| Job | When |
|-----|------|
| Knowledge Sync | Daily at 06:00 |
| Weekly Content + Feedback | Monday at 08:00 |
| Publish Content + Build Site | Tuesday at 10:00 |
| Community Scan | Daily at 10:30 |
| Weekly Report + Submit Feedback | Friday at 16:00 |
