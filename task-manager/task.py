#!/usr/bin/env python3
"""
Task Manager CLI — daily priority engine.
Usage:
  python task.py           # same as show
  python task.py show
  python task.py add
  python task.py update <id> [--done | --urgency high | ...]
"""
import os
import sys
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(__file__))

import click
from shared.task_store import load_tasks, add_task, update_task_by_id, get_task_by_id, find_task_by_name
from shared.prioritizer import score_and_rank, infer_effort
from shared.outlook_client import is_m365_configured, get_flagged_emails, emails_to_tasks
from shared.logger import log

_RANK_ICONS = ["🔴", "🟠", "🟡", "🔵", "⚪"]


def _deadline_label(deadline_str):
    if not deadline_str:
        return "No deadline"
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        days = (d - date.today()).days
        label = d.strftime("%b %d")
        if days < 0:   return f"{label} · OVERDUE"
        if days == 0:  return f"{label} · Today"
        if days == 1:  return f"{label} · Tomorrow"
        return f"{label} · {days} days"
    except ValueError:
        return deadline_str


def _why_reasons(task, breakdown):
    reasons = []
    if breakdown["deadline"] >= 28 and task.get("deadline"):
        days = (datetime.strptime(task["deadline"], "%Y-%m-%d").date() - date.today()).days
        if days < 0:   reasons.append("Overdue")
        elif days == 0: reasons.append("Due today")
        else:           reasons.append(f"Due in {days} days")
    if task.get("urgency") == "high":       reasons.append("High urgency")
    if task.get("importance") == "high":    reasons.append("High importance")
    if breakdown["context"] > 0:
        reasons.append("Context recently updated" if task.get("context_note") else "Recently updated")
    return reasons or ["Ranked by composite score"]


# Pattern 4: Outcome Tracking — every command reports ✅ / ❌ result
def _outcome(ok, msg):
    prefix = "✅" if ok else "❌"
    click.echo(f"\n  {prefix} {msg}")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(show)


@cli.command()
def show():
    """Score and display today's top 3–5 priorities."""
    log.info("show invoked")
    tasks = load_tasks()
    existing_source_ids = {t["source_id"] for t in tasks if t.get("source_id")}

    # M365 sync (optional — Pattern 3: resilient with cache fallback)
    m365_line = "M365: not configured — standalone mode"
    if is_m365_configured():
        emails, live = get_flagged_emails()
        new_tasks = emails_to_tasks(emails, existing_source_ids)
        for td in new_tasks:
            add_task(td)
        if new_tasks:
            click.echo(f"  Synced {len(new_tasks)} new Outlook task(s)")
        tasks = load_tasks()
        m365_line = "M365: connected ✓" if live else "M365: cache (API unavailable)"

    # Prompt for missing deadlines
    changed = False
    for task in [t for t in tasks if t.get("status") == "active" and not t.get("deadline")]:
        val = click.prompt(
            f'\n  "{task["title"]}" has no deadline — enter one (YYYY-MM-DD) or Enter to skip',
            default="", show_default=False
        )
        if val.strip():
            update_task_by_id(task["id"], {"deadline": val.strip()})
            task["deadline"] = val.strip()
            changed = True
    if changed:
        tasks = load_tasks()

    ranked = score_and_rank([t for t in tasks if t.get("status") == "active"])

    click.echo(f"\nDaily Priorities — {datetime.now().strftime('%B %d, %Y')}")
    click.echo("─" * 42)

    if not ranked:
        click.echo("  No active tasks. Run: python task.py add")
        log.info("show: no active tasks")
    else:
        for i, (score, task, breakdown, effort) in enumerate(ranked):
            icon = _RANK_ICONS[i] if i < len(_RANK_ICONS) else "  "
            source_tag = " [Outlook]" if task.get("source") == "outlook" else ""
            click.echo(f"\n{icon} {i+1}. {task['title']}{source_tag}")
            click.echo(f"   Due: {_deadline_label(task.get('deadline'))}")
            click.echo(f"   Why: {' · '.join(_why_reasons(task, breakdown))}")
            click.echo(f"   Effort: {effort.capitalize()} (assumed from description — verify)")
            click.echo(f"   Score: {score}/100  |  ID: {task['id']}")

    click.echo(f"\n{'─' * 42}")
    outlook_n = sum(1 for t in tasks if t.get("source") == "outlook")
    click.echo(f"  {len(tasks)} tasks  |  {len(tasks)-outlook_n} manual  |  {outlook_n} from Outlook")
    click.echo(f"  {m365_line}")
    log.info(f"show: {len(ranked)} priorities from {len(tasks)} tasks — {m365_line}")


@cli.command()
def add():
    """Interactively add a new task."""
    click.echo("\nNew Task")
    click.echo("─" * 30)

    title = click.prompt("Title")
    description = click.prompt("Description (optional)", default="", show_default=False)

    deadline = click.prompt("Deadline (YYYY-MM-DD)", default="", show_default=False).strip()
    if not deadline:
        deadline = click.prompt(
            "No deadline set — enter one or press Enter to skip",
            default="", show_default=False
        ).strip()

    urgency = click.prompt(
        "Urgency", type=click.Choice(["high", "medium", "low"]), default="medium"
    )
    importance = click.prompt(
        "Importance", type=click.Choice(["high", "medium", "low"]), default="medium"
    )
    context_note = click.prompt(
        "Context note — why is this a priority now? (optional)",
        default="", show_default=False
    )

    effort, _ = infer_effort(description)
    task = add_task({
        "title": title,
        "description": description,
        "deadline": deadline or None,
        "urgency": urgency,
        "importance": importance,
        "context_note": context_note,
        "effort": effort,
        "effort_assumed": True,
    })
    _outcome(True, f"Task added (ID: {task['id']})")
    click.echo(f"     Effort: {effort.capitalize()} (assumed from description — verify)")
    log.info(f"add: {task['id']} — {title}")


@cli.command()
@click.argument("task_name", nargs=-1, required=True)
@click.option("--done",         is_flag=True,                              help="Mark as done")
@click.option("--reactivate",   is_flag=True,                              help="Restore a done/deprioritized task to active")
@click.option("--deprioritize", is_flag=True,                              help="Remove from active list")
@click.option("--urgency",      type=click.Choice(["high", "medium", "low"]))
@click.option("--importance",   type=click.Choice(["high", "medium", "low"]))
@click.option("--deadline",     metavar="YYYY-MM-DD")
@click.option("--context",      "context_note",                            help="Note on why priority shifted")
@click.option("--description",  "description",                             help="Update task description (affects effort inference)")
def update(task_name, done, reactivate, deprioritize, urgency, importance, deadline, context_note, description):
    """Update a task by name — fuzzy matched, no ID needed."""
    query = " ".join(task_name)
    task, alternatives = find_task_by_name(query, include_inactive=reactivate)

    if not task:
        _outcome(False, f"No task found matching '{query}'")
        click.echo("  Run 'python task.py show' to see active tasks.")
        return

    # If close alternatives exist, confirm with user before proceeding
    if alternatives:
        click.echo(f"\n  Matched: \"{task['title']}\"")
        click.echo("  Similar tasks also found:")
        for i, alt in enumerate(alternatives[:3], 1):
            click.echo(f"    {i}. {alt['title']}")
        if not click.confirm(f"\n  Update \"{task['title']}\"?", default=True):
            choice = click.prompt(
                "  Enter number of the task you meant (or Enter to cancel)",
                default="", show_default=False
            )
            if choice.strip() and choice.strip().isdigit():
                idx = int(choice.strip()) - 1
                if 0 <= idx < len(alternatives):
                    task = alternatives[idx]
                else:
                    click.echo("  Invalid selection. Cancelled.")
                    return
            else:
                click.echo("  Cancelled.")
                return

    updates = {}
    if done:          updates["status"] = "done"
    if reactivate:    updates["status"] = "active"
    if deprioritize:  updates["status"] = "deprioritized"
    if urgency:       updates["urgency"] = urgency
    if importance:    updates["importance"] = importance
    if deadline:      updates["deadline"] = deadline
    if context_note:  updates["context_note"] = context_note
    if description:   updates["description"] = description

    if not updates:
        # Interactive mode
        click.echo(f"\nTask: {task['title']}")
        click.echo(f"  Status:     {task.get('status')}")
        click.echo(f"  Urgency:    {task.get('urgency')}   Importance: {task.get('importance')}")
        click.echo(f"  Deadline:   {task.get('deadline') or 'none'}")
        click.echo(f"  Context:    {task.get('context_note') or 'none'}")
        click.echo("")

        field = click.prompt(
            "What to update?",
            type=click.Choice(["done", "deprioritize", "urgency", "importance", "deadline", "context", "cancel"]),
            default="cancel",
        )
        if field == "cancel":
            return
        elif field == "done":
            updates["status"] = "done"
        elif field == "deprioritize":
            updates["status"] = "deprioritized"
        elif field == "urgency":
            updates["urgency"] = click.prompt("New urgency", type=click.Choice(["high", "medium", "low"]))
        elif field == "importance":
            updates["importance"] = click.prompt("New importance", type=click.Choice(["high", "medium", "low"]))
        elif field == "deadline":
            updates["deadline"] = click.prompt("New deadline (YYYY-MM-DD)")
        elif field == "context":
            updates["context_note"] = click.prompt("Context note")

    updated = update_task_by_id(task["id"], updates)
    _outcome(True, f"Updated: {updated['title']}  ({', '.join(updates.keys())})")
    log.info(f"update: '{query}' → {task['id']} — {list(updates.keys())}")


@cli.command()
def guide():
    """Show all available commands and how to use them."""
    click.echo("""
Task Manager — Command Guide
════════════════════════════════════════════

  tasks
  tasks show
    Show all active tasks ranked by priority.
    Scores each task on deadline, urgency, importance,
    timely context, and effort. Prompts for deadlines
    if any task is missing one.

  tasks add
    Add a new task interactively.
    Prompts for: title, description, deadline,
    urgency (high/medium/low), importance (high/medium/low),
    and an optional context note.

  tasks update <name> [options]
    Update any field on a task. Name is fuzzy matched —
    you don't need the exact title or an ID.

    Options:
      --done            Mark the task as completed
      --reactivate      Restore a done/deprioritized task
      --deprioritize    Remove from active list (not deleted)
      --urgency         high / medium / low
      --importance      high / medium / low
      --deadline        New deadline (YYYY-MM-DD)
      --context "note"  Explain why priority shifted
      --description     Update description (affects effort score)

    Examples:
      tasks update stoplight --done
      tasks update "kyc agrim" --urgency high
      tasks update onelot --deadline 2026-06-10
      tasks update triply --reactivate

  tasks guide
  tasks howto
    Show this guide.

════════════════════════════════════════════
Prioritization order: deadline → urgency → importance
→ timely context → effort (quickest wins ties)
""")


cli.add_command(guide, name="howto")


if __name__ == "__main__":
    cli()
