"""Windows Task Scheduler integration for automatic skills sync.

Provides one-click install/uninstall of a scheduled task that runs the
bridge script periodically (default: every 5 minutes).

All operations use the ``schtasks.exe`` command-line utility which is
available on every Windows installation.
"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict

_TASK_NAME = "SkillsBridgeSync"


def is_windows() -> bool:
    """Return True when running on Windows."""
    return platform.system().lower() == "windows"


def _run_schtasks(args: list[str]) -> subprocess.CompletedProcess:
    """Run schtasks.exe with the given arguments."""
    cmd = ["schtasks.exe"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def install_scheduler(
    source_dir: Path,
    interval_minutes: int = 5,
    target: str = "both",
) -> bool:
    """Create a Windows scheduled task for automatic bidirectional sync.

    Args:
        source_dir: Path to the shared skills source directory.
        interval_minutes: How often to run (minimum 1).
        target: Which platform(s) to sync (kimi, hermes, both).

    Returns:
        True on success, False on failure.
    """
    if not is_windows():
        raise RuntimeError("Scheduler is Windows only.")

    if interval_minutes < 1:
        interval_minutes = 1

    # Resolve absolute paths so the scheduled task works regardless of CWD
    source_dir = source_dir.resolve()
    script_path = (Path(__file__).parent.parent / "scripts" / "install.py").resolve()
    python_exe = Path(sys.executable).resolve()

    # Build the command that the task will execute
    task_cmd = (
        f'"{python_exe}" "{script_path}" '
        f'--source "{source_dir}" --target {target} --bidirectional'
    )

    # Remove any existing task first (idempotent)
    uninstall_scheduler()

    # Create the new task
    create_result = _run_schtasks([
        "/create",
        "/tn", _TASK_NAME,
        "/tr", task_cmd,
        "/sc", "minute",
        "/mo", str(interval_minutes),
        "/f",
    ])

    return create_result.returncode == 0


def uninstall_scheduler() -> bool:
    """Remove the scheduled task if it exists.

    Returns:
        True on success or if the task did not exist.
    """
    if not is_windows():
        raise RuntimeError("Scheduler is Windows only.")

    result = _run_schtasks(["/delete", "/tn", _TASK_NAME, "/f"])
    # Returncode 0 = deleted successfully.
    # Returncode 1 + "cannot find" = task didn't exist, which is fine.
    if result.returncode == 0:
        return True
    if "cannot find" in result.stderr.lower() or "not found" in result.stderr.lower():
        return True
    return False


def is_scheduler_installed() -> bool:
    """Check whether the scheduled task exists."""
    if not is_windows():
        return False

    result = _run_schtasks(["/query", "/tn", _TASK_NAME, "/fo", "list"])
    return result.returncode == 0


def get_scheduler_info() -> Dict:
    """Return metadata about the scheduled task.

    Returns:
        Dict with keys:
        - ``installed`` (bool)
        - ``raw`` (str): Raw schtasks output (when installed)
        - ``interval_minutes`` (int | None)
    """
    if not is_windows():
        return {"installed": False, "raw": "", "interval_minutes": None}

    result = _run_schtasks(["/query", "/tn", _TASK_NAME, "/fo", "list", "/v"])
    if result.returncode != 0:
        return {"installed": False, "raw": result.stderr, "interval_minutes": None}

    raw = result.stdout
    interval = None
    for line in raw.splitlines():
        if "schedule type" in line.lower() and "minute" in line.lower():
            # Try to extract the interval from a line like:
            # "Schedule Type:        One Time Only, Minutes Interval: 5"
            if "interval" in line.lower():
                try:
                    interval = int(line.split(":")[-1].strip())
                except ValueError:
                    pass

    return {
        "installed": True,
        "raw": raw,
        "interval_minutes": interval,
    }
