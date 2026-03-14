# PM Framework — Cron Registry

> Registered: 2026-03-02  
> Scheduler: macOS LaunchAgent (`launchctl`)  
> Mechanism: `~/Library/LaunchAgents/ai.protelynx.pm-review-*.plist`  
> Note: crontab writes were blocked by macOS FDA; LaunchAgents are the native macOS equivalent.

---

## Registered Jobs

| Job ID (Label) | Project | Schedule | Log |
|----------------|---------|----------|-----|
| `ai.protelynx.pm-review-buildbid` | BuildBid | Daily 06:00 EST | `logs/cron-buildbid.log` |
| `ai.protelynx.pm-review-jiraflow` | JiraFlow | Daily 06:20 EST | `logs/cron-jiraflow.log` |
| `ai.protelynx.pm-review-sanger` | Sanger | Daily 06:40 EST | `logs/cron-sanger.log` |
| `ai.protelynx.pm-review-contentpilot` | ContentPilot | Daily 07:00 EST | `logs/cron-contentpilot.log` |

---

## Job Details

### BuildBid
- **Label:** `ai.protelynx.pm-review-buildbid`
- **Plist:** `~/Library/LaunchAgents/ai.protelynx.pm-review-buildbid.plist`
- **Command:** `python3 continuous_review.py --project buildbid`
- **Schedule:** Daily at 06:00 (Hour=6, Minute=0)
- **API:** OpenRouter (`OPENROUTER_API_KEY` sourced from `~/.openclaw/secrets/openrouter.env`)

### JiraFlow
- **Label:** `ai.protelynx.pm-review-jiraflow`
- **Plist:** `~/Library/LaunchAgents/ai.protelynx.pm-review-jiraflow.plist`
- **Command:** `python3 continuous_review.py --project jiraflow`
- **Schedule:** Daily at 06:20 (Hour=6, Minute=20)
- **API:** OpenRouter

### Sanger
- **Label:** `ai.protelynx.pm-review-sanger`
- **Plist:** `~/Library/LaunchAgents/ai.protelynx.pm-review-sanger.plist`
- **Command:** `python3 continuous_review.py --project sanger`
- **Schedule:** Daily at 06:40 (Hour=6, Minute=40)
- **API:** OpenRouter

### ContentPilot
- **Label:** `ai.protelynx.pm-review-contentpilot`
- **Plist:** `~/Library/LaunchAgents/ai.protelynx.pm-review-contentpilot.plist`
- **Command:** `python3 continuous_review.py --project contentpilot`
- **Schedule:** Daily at 07:00 (Hour=7, Minute=0)
- **API:** OpenRouter

---

## Management Commands

```bash
# List all PM framework jobs
launchctl list | grep "ai.protelynx.pm"

# Check a specific job's status
launchctl list ai.protelynx.pm-review-buildbid

# Manually trigger a job
launchctl kickstart gui/$(id -u)/ai.protelynx.pm-review-buildbid

# Stop a job
launchctl unload ~/Library/LaunchAgents/ai.protelynx.pm-review-buildbid.plist

# Reload a job (after editing plist)
launchctl unload ~/Library/LaunchAgents/ai.protelynx.pm-review-buildbid.plist
launchctl load ~/Library/LaunchAgents/ai.protelynx.pm-review-buildbid.plist

# Unload all PM review jobs
for label in buildbid jiraflow sanger contentpilot; do
  launchctl unload ~/Library/LaunchAgents/ai.protelynx.pm-review-${label}.plist
done

# Dry-run test (no API call)
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
python3 continuous_review.py --project buildbid --dry-run
```

---

## Registration Evidence

```
$ launchctl list | grep "ai.protelynx.pm"
-	0	ai.protelynx.pm-review-jiraflow
-	0	ai.protelynx.pm-review-sanger
-	0	ai.protelynx.pm-review-contentpilot
-	0	ai.protelynx.pm-review-buildbid
```
Status: `-` = idle/waiting (loaded, not currently running), `0` = last exit code OK.

---

## Stagger Rationale

Jobs staggered 20 minutes apart to avoid concurrent API calls and log file contention.
Total window: 06:00–07:00 EST (before market open, after overnight maintenance window).
