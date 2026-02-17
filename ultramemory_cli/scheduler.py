"""Scheduler for automated agent tasks."""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import click

SCHEDULES_DIR = Path.home() / ".ulmemory" / "schedules"
SCHEDULES_FILE = SCHEDULES_DIR / "tasks.json"


def _ensure_schedules_dir():
    """Ensure schedules directory exists."""
    SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)


def _load_schedules() -> list[dict[str, Any]]:
    """Load scheduled tasks from file."""
    _ensure_schedules_dir()
    if SCHEDULES_FILE.exists():
        with open(SCHEDULES_FILE) as f:
            return json.load(f)
    return []


def _save_schedules(schedules: list[dict[str, Any]]):
    """Save scheduled tasks to file."""
    _ensure_schedules_dir()
    with open(SCHEDULES_FILE, "w") as f:
        json.dump(schedules, f, indent=2)


def _get_next_id() -> int:
    """Get next available task ID."""
    schedules = _load_schedules()
    if not schedules:
        return 1
    return max(s["id"] for s in schedules) + 1


def _cron_to_human(cron: str) -> str:
    """Convert cron expression to human readable Spanish."""
    parts = cron.split()
    if len(parts) != 5:
        return cron

    minute, hour, day_month, month, day_week = parts
    days = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]

    # Every N hours: 0 */N * * *
    if minute == "0" and hour.startswith("*/") and day_month == "*" and month == "*" and day_week == "*":
        n = hour[2:]
        return f"Cada {n} horas"

    # Every N minutes: */N * * * *
    if minute.startswith("*/") and hour == "*" and day_month == "*" and month == "*" and day_week == "*":
        n = minute[2:]
        return f"Cada {n} minutos"

    # Every hour: 0 * * * *
    if minute == "0" and hour == "*" and day_month == "*" and month == "*" and day_week == "*":
        return "Cada hora"

    # Daily at specific time: M H * * *
    if minute.isdigit() and hour.isdigit() and day_month == "*" and month == "*" and day_week == "*":
        m = int(minute)
        h = int(hour)
        time_str = f"{h:02d}:{m:02d}"
        if m == 0:
            time_str = f"{h}:00"
        return f"Cada día a las {time_str}"

    # Weekly on specific day: M H * * D
    if minute.isdigit() and hour.isdigit() and day_month == "*" and month == "*" and day_week.isdigit():
        m = int(minute)
        h = int(hour)
        day_name = days[int(day_week)]
        time_str = f"{h}:{m:02d}" if m > 0 else f"{h}:00"
        return f"Cada {day_name} a las {time_str}"

    # Monthly on specific day: M H D * *
    if minute.isdigit() and hour.isdigit() and day_month.isdigit() and month == "*" and day_week == "*":
        m = int(minute)
        h = int(hour)
        d = int(day_month)
        time_str = f"{h}:{m:02d}" if m > 0 else f"{h}:00"
        return f"Día {d} de cada mes a las {time_str}"

    # Weekdays only: M H * * 1-5
    if day_week == "1-5":
        m = int(minute)
        h = int(hour)
        time_str = f"{h}:{m:02d}" if m > 0 else f"{h}:00"
        return f"Días laborales a las {time_str}"

    # Weekends: M H * * 0,6
    if day_week in ["0,6", "6,0"]:
        m = int(minute)
        h = int(hour)
        time_str = f"{h}:{m:02d}" if m > 0 else f"{h}:00"
        return f"Fines de semana a las {time_str}"

    return cron


def _sync_to_crontab():
    """Sync schedules to system crontab."""
    schedules = _load_schedules()
    venv_python = Path.home() / ".ulmemory" / "venv" / "bin" / "python"

    # Get current ulmemory crontab entries
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    current_cron = result.stdout if result.returncode == 0 else ""

    # Filter out old ulmemory entries
    lines = [l for l in current_cron.split("\n") if "ulmemory-schedule" not in l and "ULMEMORY_TASK_ID" not in l]

    # Add new entries
    for schedule in schedules:
        if not schedule.get("enabled", True):
            continue

        cron = schedule["cron"]
        task_id = schedule["id"]
        agent = schedule["agent"]
        args = schedule.get("args", "")

        # Create command that runs the agent
        cmd = f'{venv_python} -m ultramemory_cli.main agent run {agent} "{args}" >> /tmp/ulmemory-task-{task_id}.log 2>&1'

        # Add with comment for identification
        lines.append(f"# ULMEMORY_TASK_ID={task_id}")
        lines.append(f"{cron} {cmd}")

    # Install new crontab (ensure newline at end)
    new_cron = "\n".join(lines)
    if new_cron and not new_cron.endswith("\n"):
        new_cron += "\n"
    result = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Warning: crontab sync failed: {result.stderr}")


@click.group(name="schedule")
def schedule_group():
    """Schedule automated agent tasks.

    Examples:
        ulmemory schedule add consolidator --cron "0 3 * * *"
        ulmemory schedule list
        ulmemory schedule remove 1
    """
    pass


@schedule_group.command(name="add")
@click.argument("agent")
@click.option("--cron", "-c", required=True, help="Cron expression (e.g., '0 3 * * *' for 3am daily)")
@click.option("--args", "-a", default="", help="Arguments for the agent")
@click.option("--name", "-n", help="Friendly name for the task")
@click.option("--enable/--disable", default=True, help="Enable or disable the task")
def add_command(agent: str, cron: str, args: str, name: str | None, enable: bool):
    """Add a scheduled task.

    AGENT is the agent to run (e.g., consolidator, librarian, researcher).

    \b
    Cron format:
        ┌───────────── minuto (0-59)
        │ ┌───────────── hora (0-23)
        │ │ ┌───────────── día del mes (1-31)
        │ │ │ ┌───────────── mes (1-12)
        │ │ │ │ ┌───────────── día semana (0-6, 0=domingo)
        │ │ │ │ │
        * * * * *

    \b
    Examples:
        ulmemory schedule add consolidator --cron "0 3 * * *"
        ulmemory schedule add librarian --cron "0 */6 * * *" --args "/path/to/docs"
        ulmemory schedule add researcher --cron "0 9 * * 1" --args "topic:AI"
    """
    schedules = _load_schedules()
    task_id = _get_next_id()

    task = {
        "id": task_id,
        "name": name or f"{agent}-task-{task_id}",
        "agent": agent,
        "cron": cron,
        "args": args,
        "enabled": enable,
        "created": datetime.now().isoformat(),
        "last_run": None,
        "next_run": None,
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Task created successfully!")
    click.echo(f"\n📋 Task Details:")
    click.echo(f"   ID: {task_id}")
    click.echo(f"   Name: {task['name']}")
    click.echo(f"   Agent: {agent}")
    click.echo(f"   Schedule: {cron} ({_cron_to_human(cron)})")
    click.echo(f"   Enabled: {'Yes' if enable else 'No'}")


@schedule_group.command(name="list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show disabled tasks too")
def list_command(show_all: bool):
    """List all scheduled tasks."""
    schedules = _load_schedules()

    if not schedules:
        click.echo("No scheduled tasks found.")
        click.echo("\nCreate one with: ulmemory schedule add <agent> --cron '<expression>'")
        return

    click.echo("\n╔══════════════════════════════════════════════════════════════════════╗")
    click.echo("║                          📋 SCHEDULED TASKS                           ║")
    click.echo("╚══════════════════════════════════════════════════════════════════════╝")

    for task in schedules:
        if not show_all and not task.get("enabled", True):
            continue

        status = "✅ Activo" if task.get("enabled", True) else "❌ Inactivo"
        cron_human = _cron_to_human(task["cron"])
        cron_expr = task["cron"]

        click.echo(f"\n┌─────────────────────────────────────────────────────────────────────┐")
        click.echo(f"│  #{task['id']:<3} {task['name'][:40]:<43} │")
        click.echo(f"├─────────────────────────────────────────────────────────────────────┤")
        click.echo(f"│  🤖 Agente: {task['agent']:<52}│")
        click.echo(f"│  ⏰ Horario: {cron_human:<51}│")
        click.echo(f"│  📝 Cron:    {cron_expr:<51}│")
        click.echo(f"│  📊 Estado:  {status:<51}│")

        if task.get("args"):
            args_display = task["args"][:50] + "..." if len(task["args"]) > 50 else task["args"]
            click.echo(f"│  📎 Args:    {args_display:<51}│")

        click.echo(f"└─────────────────────────────────────────────────────────────────────┘")

    click.echo(f"\n💡 Comandos: show <id> | edit <id> | run <id> | remove <id>")


@schedule_group.command(name="show")
@click.argument("task_id", type=int)
def show_command(task_id: int):
    """Show details of a scheduled task."""
    schedules = _load_schedules()
    task = next((t for t in schedules if t["id"] == task_id), None)

    if not task:
        click.echo(f"❌ Task {task_id} not found")
        return

    click.echo(f"\n📋 Task #{task_id}: {task['name']}")
    click.echo("=" * 50)
    click.echo(f"   Agent: {task['agent']}")
    click.echo(f"   Cron: {task['cron']}")
    click.echo(f"   Schedule: {_cron_to_human(task['cron'])}")
    click.echo(f"   Args: {task.get('args', 'none')}")
    click.echo(f"   Enabled: {'Yes' if task.get('enabled', True) else 'No'}")
    click.echo(f"   Created: {task.get('created', 'unknown')}")
    click.echo(f"   Last run: {task.get('last_run', 'never')}")

    log_file = f"/tmp/ulmemory-task-{task_id}.log"
    click.echo(f"\n📄 Log file: {log_file}")


@schedule_group.command(name="remove")
@click.argument("task_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def remove_command(task_id: int, force: bool):
    """Remove a scheduled task."""
    schedules = _load_schedules()
    task = next((t for t in schedules if t["id"] == task_id), None)

    if not task:
        click.echo(f"❌ Task {task_id} not found")
        return

    if not force:
        if not click.confirm(f"Remove task '{task['name']}' (#{task_id})?"):
            click.echo("Cancelled.")
            return

    schedules = [t for t in schedules if t["id"] != task_id]
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Task #{task_id} removed")


@schedule_group.command(name="enable")
@click.argument("task_id", type=int)
def enable_command(task_id: int):
    """Enable a scheduled task."""
    schedules = _load_schedules()
    for task in schedules:
        if task["id"] == task_id:
            task["enabled"] = True
            _save_schedules(schedules)
            _sync_to_crontab()
            click.echo(f"✅ Task #{task_id} enabled")
            return
    click.echo(f"❌ Task {task_id} not found")


@schedule_group.command(name="disable")
@click.argument("task_id", type=int)
def disable_command(task_id: int):
    """Disable a scheduled task."""
    schedules = _load_schedules()
    for task in schedules:
        if task["id"] == task_id:
            task["enabled"] = False
            _save_schedules(schedules)
            _sync_to_crontab()
            click.echo(f"✅ Task #{task_id} disabled")
            return
    click.echo(f"❌ Task {task_id} not found")


@schedule_group.command(name="edit")
@click.argument("task_id", type=int)
@click.option("--cron", "-c", help="New cron expression")
@click.option("--args", "-a", help="New arguments")
@click.option("--name", "-n", help="New name")
def edit_command(task_id: int, cron: str | None, args: str | None, name: str | None):
    """Edit a scheduled task."""
    schedules = _load_schedules()
    task = next((t for t in schedules if t["id"] == task_id), None)

    if not task:
        click.echo(f"❌ Task {task_id} not found")
        return

    if cron:
        task["cron"] = cron
    if args is not None:
        task["args"] = args
    if name:
        task["name"] = name

    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Task #{task_id} updated")
    click.echo(f"   Schedule: {task['cron']} ({_cron_to_human(task['cron'])})")


@schedule_group.command(name="logs")
@click.argument("task_id", type=int)
@click.option("--tail", "-t", default=20, help="Number of lines to show")
def logs_command(task_id: int, tail: int):
    """Show logs for a scheduled task."""
    log_file = Path(f"/tmp/ulmemory-task-{task_id}.log")

    if not log_file.exists():
        click.echo(f"No logs found for task #{task_id}")
        click.echo(f"Log file: {log_file}")
        return

    result = subprocess.run(["tail", "-n", str(tail), str(log_file)], capture_output=True, text=True)
    click.echo(f"📄 Logs for task #{task_id} (last {tail} lines):\n")
    click.echo(result.stdout)


@schedule_group.command(name="run")
@click.argument("task_id", type=int)
def run_command(task_id: int):
    """Run a scheduled task immediately."""
    schedules = _load_schedules()
    task = next((t for t in schedules if t["id"] == task_id), None)

    if not task:
        click.echo(f"❌ Task {task_id} not found")
        return

    click.echo(f"🚀 Running task #{task_id}: {task['name']}...")

    # Run the agent
    venv_python = Path.home() / ".ulmemory" / "venv" / "bin" / "python"
    agent = task["agent"]
    args = task.get("args", "")

    cmd = [str(venv_python), "-m", "ultramemory_cli.main", "agent", "run", agent]
    if args:
        cmd.append(args)

    result = subprocess.run(cmd, capture_output=True, text=True)

    click.echo(result.stdout)
    if result.stderr:
        click.echo(f"Errors: {result.stderr}")

    # Update last_run
    task["last_run"] = datetime.now().isoformat()
    _save_schedules(schedules)

    click.echo(f"\n✅ Task completed")


# === New Schedule Commands ===

@schedule_group.command(name="add-proactive")
def add_proactive_schedule():
    """Add proactive agent schedule (every 30 minutes)."""
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "proactive-heartbeat",
        "agent": "proactive",
        "cron": "*/30 * * * *",
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo("✅ Proactive agent scheduled: cada 30 minutos")


@schedule_group.command(name="add-researcher")
@click.option("--cron", "-c", default="0 * * * *", help="Cron (default: hourly)")
def add_researcher_schedule(cron: str):
    """Add researcher agent schedule."""
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "researcher-hourly",
        "agent": "auto-researcher",
        "cron": cron,
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Researcher agent scheduled: {_cron_to_human(cron)}")


@schedule_group.command(name="add-consolidator")
@click.option("--hour", "-h", default=5, type=int, help="Hour (default: 5am)")
def add_consolidator_schedule(hour: int):
    """Add consolidator agent schedule (daily)."""
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "consolidator-daily",
        "agent": "consolidator",
        "cron": f"0 {hour} * * *",
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Consolidator scheduled: daily at {hour}:00")
