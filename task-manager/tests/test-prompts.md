# Task Manager — Test Prompts

## Positive Tests (skill should trigger and succeed)

### Test 1: Show priorities
**Prompt:** `tasks`

**Setup:** tasks.json in Slack channel contains at least 3 active tasks with varying deadlines, urgency, and importance.

**Expected output:**
- Claude fetches tasks.json from the designated Slack channel without being asked
- Scores all active tasks and displays them ranked highest to lowest
- Each task shows: title, due date, why it ranked there, inferred effort (marked assumed), and score out of 100
- Footer shows total task count and Slack channel confirmation

---

### Test 2: Add a new task
**Prompt:** `tasks add Review Field PRD deadline June 9 urgency high importance low`

**Expected output:**
- Claude creates a new task with title "Review Field PRD", deadline 2026-06-09, urgency high, importance low
- Effort is inferred from the title/description and flagged as assumed
- Task is written back to tasks.json in Slack
- Confirmation printed: `✅ Task added: Review Field PRD (ID: [id])`
- On the next `tasks show`, the new task appears ranked according to its score

---

### Test 3: Mark a task done
**Prompt:** `tasks update stoplight --done`

**Expected output:**
- Claude fuzzy-matches "stoplight" to "Stoplight work" without requiring exact title or ID
- Status is set to "done", updated_at is refreshed
- tasks.json is written back to Slack
- Confirmation: `✅ Updated: Stoplight work (status)`
- On the next `tasks show`, "Stoplight work" no longer appears in the active list

---

## Negative Test (skill should NOT trigger)

### Test 4: General reminder — not a task manager request
**Prompt:** `remind me to call Agrim tomorrow`

**Expected behavior:**
- This is a general calendar reminder, NOT a task manager command
- The skill should not trigger
- Claude should handle this as a normal conversational request (e.g., note that it can't set reminders natively, or suggest adding it as a task via `tasks add`)
- tasks.json should NOT be fetched or modified
