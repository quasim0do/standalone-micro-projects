# Task Manager

A personal daily task prioritization system with two modes:

- **Python CLI** — runs in your terminal on Mac or Windows
- **Claude Skill** — runs inside Claude Enterprise chat via a `.md` skill file, with tasks stored on Slack

Both modes use the same `tasks.json` schema, so you can use the Python CLI on one machine and the Claude skill on another — they stay compatible.

---

## How It Prioritizes

Every task is scored out of 100 across five dimensions:

| Signal | Weight | Logic |
|---|---|---|
| Deadline proximity | 40 pts | Overdue=40, Today=35, 1-2d=28, 3-7d=20, 8-14d=12, 15+d=5 |
| Urgency | 25 pts | High=25, Medium=15, Low=5 |
| Importance | 20 pts | High=20, Medium=12, Low=4 |
| Timely context | 10 pts | Context note set, or updated in last 48h |
| Effort (tiebreaker) | 5 pts | Small=5, Medium=3, Large=1 (inferred from description) |

Urgency intentionally outweighs importance — urgent tasks surface before merely important ones. When scores tie, the quicker task wins.

---

## Commands

```
tasks              Show all active tasks ranked by priority
tasks show         Same as above
tasks add          Add a new task (interactive prompts)
tasks update       Update a task by name — fuzzy matched, no ID needed
tasks guide        Show the full command reference
tasks howto        Same as above
```

### Update flags

```
tasks update <name> --done              Mark as completed
tasks update <name> --reactivate        Restore a done/deprioritized task
tasks update <name> --deprioritize      Remove from active list (not deleted)
tasks update <name> --urgency high      Change urgency
tasks update <name> --importance low    Change importance
tasks update <name> --deadline 2026-06-15
tasks update <name> --context "reason priority shifted"
tasks update <name> --description "short description"
```

Names are fuzzy matched — `tasks update kyc agrim --done` finds "KYC verification for Agrim" without needing the exact title or an ID.

---

## Option 1 — Python CLI Setup

### Requirements
- Python 3.9+
- pip

### Mac Setup

```bash
cd task-manager
pip3 install -r requirements.txt
```

Add alias to `~/.zshrc`:
```bash
echo 'alias tasks="python3 /path/to/task-manager/task.py"' >> ~/.zshrc
source ~/.zshrc
```

### Windows Setup (PowerShell)

```powershell
pip install -r requirements.txt
```

Add to your PowerShell profile (`notepad $PROFILE`):
```powershell
function tasks { python C:\path\to\task-manager\task.py $args }
```

### First run

```bash
tasks add
tasks
```

---

## Option 2 — Claude Enterprise Skill Setup

Use this if you have Claude Enterprise and access to skill `.md` files, but not Claude Code CLI.

### How it works

- Upload `task-manager-skill.md` to your Claude Enterprise project alongside your other skill files
- Tasks are stored as `tasks.json` in a Slack channel of your choice
- Claude fetches the file at the start of each session automatically — no manual uploads
- After every add or update, Claude writes the updated file back to Slack

### Setup steps

1. Create a dedicated Slack channel (e.g. `#task-manager`) or use any existing channel
2. Upload `task-manager-skill.md` to your Claude Enterprise project
3. Invoke the skill and tell Claude which Slack channel to use — it will remember for the session

### First session

```
/task-manager
> tasks add
> tasks
```

On first use, Claude will ask for your Slack channel. After that, it fetches and writes automatically.

---

## Outlook Integration (Optional)

Flagged emails in Outlook are automatically pulled in as tasks. Each flagged email = one task. Already-imported emails are not duplicated across sessions.

### Python CLI (Mac/Windows)

Requires an Azure App Registration with `Mail.Read` permission.

1. Go to [portal.azure.com](https://portal.azure.com) → Azure Active Directory → App registrations → New registration
2. Note the **Application (client) ID** and **Directory (tenant) ID**
3. Under Certificates & secrets → New client secret
4. Under API permissions → Microsoft Graph → Application → `Mail.Read` → Grant admin consent

Create a `.env` file in the `task-manager/` folder (never commit this):
```
M365_CLIENT_ID=your-app-id
M365_TENANT_ID=your-tenant-id
M365_CLIENT_SECRET=your-secret
```

### Claude Skill

If your Claude Enterprise setup has the M365 tool available, Outlook sync happens automatically at session start. No configuration needed beyond what your IT team has provisioned.

---

## File Structure

```
task-manager/
├── task.py                  # Python CLI entrypoint
├── task-manager-skill.md    # Claude Enterprise skill file
├── requirements.txt         # Python dependencies
├── .env.example             # M365 credential template
├── .gitignore               # Excludes .env, tasks.json, logs/
├── README.md                # This file
├── SETUP.md                 # Detailed M365 setup walkthrough
├── tasks.json               # Your task store (auto-created, git-ignored)
├── logs/                    # Daily log files (auto-created, git-ignored)
└── shared/
    ├── task_store.py        # JSON read/write + fuzzy name matching
    ├── prioritizer.py       # Scoring algorithm
    ├── outlook_client.py    # M365 Graph API integration
    └── logger.py            # Structured daily logging
```

---

## Tasks Schema

Both the Python CLI and Claude skill use the same `tasks.json` format:

```json
[
  {
    "id": "1eb7b620",
    "title": "KYC verification for Agrim",
    "description": "",
    "deadline": "2026-06-09",
    "urgency": "high",
    "importance": "high",
    "status": "active",
    "effort": "medium",
    "effort_assumed": true,
    "context_note": "",
    "created_at": "2026-06-06T10:00:00",
    "updated_at": "2026-06-06T10:00:00",
    "source": "manual",
    "source_id": null
  }
]
```

---

## System Patterns Applied

This project follows six patterns for reliable automations:

1. **Environment Variables** — M365 credentials in `.env`, never in code
2. **Structured Logging** — daily log files in `logs/`
3. **Resilient API Calls** — Outlook falls back to cached data if API is unavailable
4. **Outcome Tracking** — every command prints `✅` or `❌`
5. **Shared Utilities** — reusable modules in `shared/`
6. **State Management** — `source_id` deduplication prevents re-importing the same Outlook email
