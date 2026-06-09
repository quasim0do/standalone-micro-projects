import json
import uuid
import os
from datetime import datetime
from difflib import SequenceMatcher

# Pattern 6: State Management — tasks persisted to local JSON
TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tasks.json")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE) as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def add_task(data):
    tasks = load_tasks()
    task = {
        "id": str(uuid.uuid4())[:8],
        "title": data["title"],
        "description": data.get("description", ""),
        "deadline": data.get("deadline"),
        "urgency": data.get("urgency", "medium"),
        "importance": data.get("importance", "medium"),
        "status": "active",
        "effort": data.get("effort", "medium"),
        "effort_assumed": data.get("effort_assumed", True),
        "context_note": data.get("context_note", ""),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source": data.get("source", "manual"),
        "source_id": data.get("source_id"),
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def update_task_by_id(task_id, updates):
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id or task["id"].startswith(task_id):
            task.update(updates)
            task["updated_at"] = datetime.now().isoformat()
            save_tasks(tasks)
            return task
    return None


def get_task_by_id(task_id):
    for task in load_tasks():
        if task["id"] == task_id or task["id"].startswith(task_id):
            return task
    return None


def _score_match(query, title):
    """Return a 0–1 similarity score between query and title using multiple signals."""
    q, t = query.lower().strip(), title.lower().strip()
    if q == t:
        return 1.0
    # token overlap: fraction of query words found in title
    q_words = set(q.split())
    t_words = set(t.split())
    token_score = len(q_words & t_words) / len(q_words) if q_words else 0
    # substring containment
    substr_score = 1.0 if q in t or t in q else 0.0
    # sequence similarity
    seq_score = SequenceMatcher(None, q, t).ratio()
    return max(token_score, substr_score, seq_score)


def find_task_by_name(query, include_inactive=False):
    """
    Fuzzy-match a task by name. Returns (best_match, [close_alternatives]).
    best_match is None if nothing scores above threshold.
    close_alternatives are other tasks with scores within 0.15 of best.
    """
    tasks = load_tasks()
    candidates = tasks if include_inactive else [t for t in tasks if t.get("status") == "active"]
    if not candidates:
        return None, []

    scored = sorted(
        [(t, _score_match(query, t["title"])) for t in candidates],
        key=lambda x: x[1],
        reverse=True,
    )

    best_task, best_score = scored[0]
    if best_score < 0.3:
        return None, []

    # Surface other tasks within 0.15 of best so caller can ask user to confirm
    close = [t for t, s in scored[1:] if s >= best_score - 0.15 and s >= 0.3]
    return best_task, close
