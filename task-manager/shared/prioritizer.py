from datetime import datetime, date

_LARGE_SIGNALS = [
    "coordinate", "multiple", "depends", "team", "approval",
    "review", "stakeholder", "meeting", "presentation", "report",
]


def infer_effort(description):
    """Pattern 1 assumption: effort inferred from description — always flagged to user."""
    if not description:
        return "medium", True
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in _LARGE_SIGNALS):
        return "large", True
    if len(description.split()) <= 30:
        return "small", True
    return "medium", True


def _deadline_score(deadline_str):
    if not deadline_str:
        return 0
    try:
        days = (datetime.strptime(deadline_str, "%Y-%m-%d").date() - date.today()).days
    except ValueError:
        return 0
    if days < 0:   return 40  # overdue
    if days == 0:  return 35
    if days <= 2:  return 28
    if days <= 7:  return 20
    if days <= 14: return 12
    return 5


def _urgency_score(urgency):
    return {"high": 25, "medium": 15, "low": 5}.get(urgency or "medium", 15)


def _importance_score(importance):
    # Intentionally lower than urgency weight per spec
    return {"high": 20, "medium": 12, "low": 4}.get(importance or "medium", 12)


def _context_score(task):
    """Boost tasks whose priority has shifted — via explicit note or recent update."""
    if task.get("context_note"):
        return 10
    updated_at = task.get("updated_at")
    if updated_at:
        try:
            hours_since = (datetime.now() - datetime.fromisoformat(updated_at)).total_seconds() / 3600
            if hours_since <= 48:
                return 10
        except (ValueError, TypeError):
            pass
    return 0


def _effort_score(effort):
    return {"small": 5, "medium": 3, "large": 1}.get(effort or "medium", 3)


def score_task(task):
    effort, assumed = infer_effort(task.get("description", ""))
    task["effort"] = effort
    task["effort_assumed"] = assumed

    breakdown = {
        "deadline":   _deadline_score(task.get("deadline")),
        "urgency":    _urgency_score(task.get("urgency")),
        "importance": _importance_score(task.get("importance")),
        "context":    _context_score(task),
        "effort":     _effort_score(effort),
    }
    breakdown["total"] = sum(breakdown.values())
    return breakdown["total"], breakdown, effort


def score_and_rank(tasks, top_n=5):
    scored = []
    for task in tasks:
        if task.get("status") != "active":
            continue
        total, breakdown, effort = score_task(task)
        scored.append((total, task, breakdown, effort))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]
