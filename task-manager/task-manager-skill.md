---
name: task-manager
version: 1.0.0
description: >
  Personal daily task prioritization system. Invoke when the user types "tasks",
  "tasks show", "tasks add", "tasks update", "tasks guide", or "tasks howto".
  Fetches tasks.json from a designated Slack channel at session start, scores all
  active tasks across deadline proximity, urgency, importance, timely context, and
  effort, and surfaces ranked priorities. Writes back to Slack after every add or
  update. Do NOT use for general reminders, calendar management, or team-scale
  project tracking.
author: Devraj
last_updated: 2026-06-09
use_cases:
  - "Morning prioritization: 'tasks' or 'tasks show' to see what to focus on today"
  - "Capturing work: 'tasks add KYC verification for Agrim deadline June 9 high urgency'"
  - "Closing out: 'tasks update stoplight --done'"
  - "Re-prioritizing after a context shift: 'tasks update triply --context investor joining call'"
  - "Onboarding: 'tasks guide' or 'tasks howto' for full command reference"
tested_with:
  - "tasks"
  - "tasks add Prepare board deck"
  - "tasks update kyc agrim --done"
  - "tasks update stoplight --context quick task"
  - "tasks show"
dependencies: >
  Slack tool (required — read/write tasks.json to a designated channel);
  M365 tool (optional — syncs flagged Outlook emails as tasks if available)
---

# Task Manager

## What it does
Scores and ranks your active tasks daily using deadline, urgency, importance, timely context, and effort — then shows you what to work on first. All tasks are stored as `tasks.json` in a Slack channel you designate, auto-fetched at session start and written back after every change.

## When to use it
- User types `tasks`, `tasks show`, `tasks add`, `tasks update`, `tasks guide`, or `tasks howto`
- User says "what should I work on today" or "show me my priorities"
- User says "add a task" or "mark [task] as done"
- User asks "how do I use the task manager"

## When NOT to use it
- General reminders or calendar events ("remind me to call X at 3pm")
- Team project management or shared task lists
- One-off notes with no follow-through needed
- Anything not related to personal work task tracking

---

## Instructions

### Initialization (First Use Only)

If no Slack channel has been set for task storage, ask:
> "Which Slack channel should I use to store your tasks? (e.g. #task-manager or a DM)"

Store this as `TASK_CHANNEL` for the session. Then proceed to Session Start.

---

### Session Start Protocol

Every time this skill is invoked:

1. Use the Slack tool to search `TASK_CHANNEL` for a file named `tasks.json`
2. If found: fetch and parse the file contents as a JSON array of task objects
3. If not found: start with an empty task list `[]` and inform the user:
   > "No tasks.json found in [channel]. Starting fresh."
4. Confirm load silently — do not narrate the fetch unless it fails
5. Attempt Outlook sync if M365 tool is available (see Outlook section below)

---

### Commands

#### `tasks` or `tasks show`
Run the full prioritization algorithm on all tasks with `status: active`. Display ALL active tasks ranked by score — no cap on list length.

#### `tasks add [title]`
If title is given inline, use it. Otherwise prompt interactively:
1. Title (required)
2. Description (optional — used to infer effort)
3. Deadline (YYYY-MM-DD) — if skipped, re-prompt once: "No deadline set — are you sure?"
4. Urgency: high / medium / low (default: medium)
5. Importance: high / medium / low (default: medium)
6. Context note (optional): "Why is this a priority now?"

Create task object, append to list, write back to Slack. Confirm: `✅ Task added: [title] (ID: [id])`

#### `tasks update [name] [--flags]`
Fuzzy-match the name against active task titles using token overlap and sequence similarity — do not require exact match or ID. If ambiguous (multiple close matches), show options and ask user to confirm before updating.

Accepted flags:
- `--done` → status: done
- `--reactivate` → status: active (search all tasks including done/deprioritized)
- `--deprioritize` → status: deprioritized
- `--urgency high|medium|low`
- `--importance high|medium|low`
- `--deadline YYYY-MM-DD`
- `--context "note"` → sets context_note; triggers timely context boost
- `--description "text"` → updates description; re-infers effort on next show

If no flags given, show current task fields and ask what to change interactively.

Update `updated_at` on every change. Write back to Slack. Confirm: `✅ Updated: [title] ([changed fields])`

#### `tasks guide` or `tasks howto`
Print the full command reference:

```
Task Manager — Command Guide
════════════════════════════════════════════

  tasks / tasks show
    Show all active tasks ranked by priority.

  tasks add [title]
    Add a new task. Prompts for deadline, urgency,
    importance, and optional context note.

  tasks update [name] [--flags]
    Update a task by name (fuzzy matched — no ID needed).

    --done              Mark as completed
    --reactivate        Restore a done/deprioritized task
    --deprioritize      Remove from active list
    --urgency           high / medium / low
    --importance        high / medium / low
    --deadline          YYYY-MM-DD
    --context "note"    Why priority shifted
    --description       Update description

  tasks guide / tasks howto
    Show this guide.

════════════════════════════════════════════
Priority order: deadline → urgency → importance
→ timely context → effort (quickest wins ties)
```

---

## Prioritization Algorithm

Score each active task out of 100. Rank descending. Show all.

### 1. Deadline Proximity (40 pts)
| Deadline | Points |
|---|---|
| Overdue | 40 |
| Due today | 35 |
| Due in 1–2 days | 28 |
| Due in 3–7 days | 20 |
| Due in 8–14 days | 12 |
| Due in 15+ days | 5 |
| No deadline | 0 |

### 2. Urgency (25 pts)
High = 25 · Medium = 15 · Low = 5

> Urgency intentionally outweighs importance — urgent tasks must be completed before merely important ones.

### 3. Importance (20 pts)
High = 20 · Medium = 12 · Low = 4

### 4. Timely Context (10 pts)
Award 10 pts if `context_note` is non-empty OR `updated_at` is within the last 48 hours. Surfaces tasks whose priority has recently shifted.

### 5. Effort Tiebreaker (5 pts)
Infer from description — always flag as assumed in output:
- **Small** (5 pts): ≤ 30 words, no complexity signals
- **Large** (1 pt): contains "coordinate", "multiple", "depends", "team", "approval", "review", "stakeholder", "presentation", "report"
- **Medium** (3 pts): everything else

---

## Output Format

```
Daily Priorities — [Date]
──────────────────────────────────────────

🔴 1. [Title]  [Outlook tag if applicable]
   Due: [deadline label]
   Why: [reason list]
   Effort: [Small/Medium/Large] (assumed from description — verify)
   Score: [X]/100

[repeat for all active tasks]

──────────────────────────────────────────
[N] tasks total  |  [N] manual  |  [N] from Outlook
Tasks loaded from: #[channel] ✓
```

Deadline label rules: No deadline · OVERDUE · Today · Tomorrow · [N] days

---

## Edge Cases

**Slack write fails:** Output the full JSON to chat so the user can save manually. Print: `❌ Slack write failed — copy the JSON below to save manually`

**No active tasks:** Print "No active tasks. Try: tasks add [title]"

**M365 unavailable:** Skip Outlook sync silently. Note "M365: not configured" in footer.

**Ambiguous task name on update:** Show top 2–3 matches, ask user to confirm before proceeding. Example:
> Matched: "Stoplight work" — is this right? (y/n, or enter the number of the task you meant)

**Missing deadline on show:** For any active task with `deadline: null`, prompt inline before displaying priorities:
> "[Task title]" has no deadline — enter one (YYYY-MM-DD) or press Enter to skip

---

## Outlook Flagged Emails (if M365 tool available)

On session start, after loading tasks.json:
1. Fetch flagged emails from Outlook using the M365 tool
2. For each flagged email not already in tasks (match by `source_id`):
   - Title = email subject
   - Description = sender + first 100 chars of body preview
   - Urgency = high if email importance is high, else medium
   - Source = "outlook", source_id = email ID
   - Deadline = null (prompted on next show)
3. Append new tasks, write back to Slack

---

## Notes for Users

**First session:** Claude will ask which Slack channel to use. Pick a dedicated channel (e.g. `#task-manager`) or a DM. Claude remembers it for the session.

**Mac ↔ ThinkPad sync:** If you also use the Python CLI on a Mac, both systems read and write the same `tasks.json` schema. They do not auto-sync — use one system consistently, or manually copy `tasks.json` between them via Slack.

**Effort is always inferred:** The effort score is estimated from your task description. It will say "(assumed — verify)" in output. To improve accuracy, add a short description when creating tasks.

---

## Data Contract (tasks.json schema)

```json
[
  {
    "id": "string (8 chars)",
    "title": "string",
    "description": "string",
    "deadline": "YYYY-MM-DD | null",
    "urgency": "high | medium | low",
    "importance": "high | medium | low",
    "status": "active | done | deprioritized",
    "effort": "small | medium | large",
    "effort_assumed": true,
    "context_note": "string",
    "created_at": "ISO 8601",
    "updated_at": "ISO 8601",
    "source": "manual | outlook",
    "source_id": "string | null"
  }
]
```
