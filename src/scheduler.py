"""Cross-platform scheduled task integration for automatic skills sync.

Backends:
  - Windows:  schtasks.exe
  - macOS:    launchd (~/Library/LaunchAgents/)
  - Linux:    cron (user crontab)

All backends support install, uninstall, status query, and are designed
to work without elevated privileges.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

_TASK_NAME = "SkillsBridgeSync"
_CRON_MARKER_START = "# === SkillsBridgeSync start ==="
_CRON_MARKER_END = "# === SkillsBridgeSync end ==="
_LAUNCHD_LABEL = "com.skillsbridge.sync"


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------

class SchedulerBackend(ABC):
    """Abstract base for platform-specific schedulers."""

    @abstractmethod
    def install(self, source_dir: Path, interval_minutes: int, target: str) -> bool:
        """Create the scheduled task."""

    @abstractmethod
    def uninstall(self) -> bool:
        """Remove the scheduled task."""

    @abstractmethod
    def is_installed(self) -> bool:
        """Return True if the task exists."""

    @abstractmethod
    def get_info(self) -> Dict:
        """Return metadata dict (installed, raw, interval_minutes, etc.)."""


def _build_command(source_dir: Path, target: str) -> str:
    """Build the shell command that the scheduler will execute."""
    source_dir = source_dir.resolve()
    script_path = (Path(__file__).parent.parent / "scripts" / "install.py").resolve()
    python_exe = Path(sys.executable).resolve()
    return (
        f'"{python_exe}" "{script_path}" '
        f'--source "{source_dir}" --target {target} --bidirectional'
    )


# ---------------------------------------------------------------------------
# Windows backend (schtasks.exe)
# ---------------------------------------------------------------------------

class WindowsScheduler(SchedulerBackend):
    """Windows Task Scheduler backend."""

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(["schtasks.exe"] + args, capture_output=True, text=True)

    def install(self, source_dir: Path, interval_minutes: int, target: str) -> bool:
        self.uninstall()  # idempotent
        task_cmd = _build_command(source_dir, target)
        result = self._run([
            "/create",
            "/tn", _TASK_NAME,
            "/tr", task_cmd,
            "/sc", "minute",
            "/mo", str(max(1, interval_minutes)),
            "/f",
        ])
        return result.returncode == 0

    def uninstall(self) -> bool:
        result = self._run(["/delete", "/tn", _TASK_NAME, "/f"])
        if result.returncode == 0:
            return True
        err = result.stderr.lower()
        return "cannot find" in err or "not found" in err

    def is_installed(self) -> bool:
        result = self._run(["/query", "/tn", _TASK_NAME, "/fo", "list"])
        return result.returncode == 0

    def get_info(self) -> Dict:
        result = self._run(["/query", "/tn", _TASK_NAME, "/fo", "list", "/v"])
        if result.returncode != 0:
            return {"installed": False, "raw": result.stderr, "interval_minutes": None}
        raw = result.stdout
        interval = None
        for line in raw.splitlines():
            if "schedule type" in line.lower() and "minute" in line.lower():
                if "interval" in line.lower():
                    try:
                        interval = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
        return {"installed": True, "raw": raw, "interval_minutes": interval}


# ---------------------------------------------------------------------------
# macOS backend (launchd)
# ---------------------------------------------------------------------------

class MacOSScheduler(SchedulerBackend):
    """macOS launchd backend."""

    def _plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{_LAUNCHD_LABEL}.plist"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True)

    def install(self, source_dir: Path, interval_minutes: int, target: str) -> bool:
        self.uninstall()
        plist = self._plist_path()
        plist.parent.mkdir(parents=True, exist_ok=True)

        task_cmd = _build_command(source_dir, target)
        # launchd StartInterval is in seconds
        interval_seconds = max(60, interval_minutes * 60)

        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{(Path(__file__).parent.parent / "scripts" / "install.py").resolve()}</string>
        <string>--source</string>
        <string>{source_dir.resolve()}</string>
        <string>--target</string>
        <string>{target}</string>
        <string>--bidirectional</string>
    </array>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{Path.home() / "Library" / "Logs" / "skillsbridge-sync.log"}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / "Library" / "Logs" / "skillsbridge-sync.log"}</string>
</dict>
</plist>
'''
        plist.write_text(plist_content, encoding="utf-8")
        load_result = self._run(["launchctl", "load", str(plist)])
        return load_result.returncode == 0

    def uninstall(self) -> bool:
        plist = self._plist_path()
        if plist.exists():
            self._run(["launchctl", "unload", str(plist)])
            plist.unlink()
        return True

    def is_installed(self) -> bool:
        return self._plist_path().exists()

    def get_info(self) -> Dict:
        plist = self._plist_path()
        if not plist.exists():
            return {"installed": False, "raw": "", "interval_minutes": None}
        # Parse interval from plist (rough)
        raw = plist.read_text(encoding="utf-8")
        interval = None
        if "<key>StartInterval</key>" in raw:
            try:
                after = raw.split("<key>StartInterval</key>")[1].split("</integer>")[0]
                interval = int(after.replace("<integer>", "").strip()) // 60
            except Exception:
                pass
        return {"installed": True, "raw": raw, "interval_minutes": interval}


# ---------------------------------------------------------------------------
# Linux backend (cron)
# ---------------------------------------------------------------------------

class LinuxCronScheduler(SchedulerBackend):
    """Linux cron backend (user crontab)."""

    def _read_crontab(self) -> str:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        # crontab -l returns error when no crontab exists
        return ""

    def _write_crontab(self, content: str) -> bool:
        result = subprocess.run(
            ["crontab", "-"],
            input=content,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _strip_existing_block(self, crontab: str) -> str:
        """Remove any existing SkillsBridgeSync block from crontab text."""
        lines = crontab.splitlines()
        result: list[str] = []
        in_block = False
        for line in lines:
            if line.strip() == _CRON_MARKER_START:
                in_block = True
                continue
            if line.strip() == _CRON_MARKER_END:
                in_block = False
                continue
            if not in_block:
                result.append(line)
        return "\n".join(result).rstrip("\n") + "\n"

    def install(self, source_dir: Path, interval_minutes: int, target: str) -> bool:
        interval_minutes = max(1, interval_minutes)
        task_cmd = _build_command(source_dir, target)

        existing = self._read_crontab()
        cleaned = self._strip_existing_block(existing)

        block = (
            f"{_CRON_MARKER_START}\n"
            f"*/{interval_minutes} * * * * {task_cmd}\n"
            f"{_CRON_MARKER_END}\n"
        )
        new_crontab = cleaned.rstrip("\n") + "\n\n" + block
        return self._write_crontab(new_crontab)

    def uninstall(self) -> bool:
        existing = self._read_crontab()
        cleaned = self._strip_existing_block(existing)
        # If nothing left, write empty crontab
        return self._write_crontab(cleaned)

    def is_installed(self) -> bool:
        return _CRON_MARKER_START in self._read_crontab()

    def get_info(self) -> Dict:
        raw = self._read_crontab()
        if _CRON_MARKER_START not in raw:
            return {"installed": False, "raw": raw, "interval_minutes": None}
        interval = None
        for line in raw.splitlines():
            if line.strip().startswith("*/") and _CRON_MARKER_START not in line:
                try:
                    interval = int(line.split("/")[1].split()[0])
                except ValueError:
                    pass
        return {"installed": True, "raw": raw, "interval_minutes": interval}


# ---------------------------------------------------------------------------
# Platform dispatch
# ---------------------------------------------------------------------------

def _get_scheduler_class():
    """Return the appropriate scheduler class for the current OS."""
    system = platform.system().lower()
    if system == "windows":
        return WindowsScheduler
    if system == "darwin":
        return MacOSScheduler
    if system == "linux":
        return LinuxCronScheduler
    raise RuntimeError(f"Unsupported platform for scheduler: {platform.system()}")


# ---------------------------------------------------------------------------
# Public API (kept for backward compatibility)
# ---------------------------------------------------------------------------

def install_scheduler(
    source_dir: Path,
    interval_minutes: int = 5,
    target: str = "both",
) -> bool:
    """Create a scheduled task for automatic bidirectional sync."""
    scheduler = _get_scheduler_class()()
    return scheduler.install(source_dir, interval_minutes, target)


def uninstall_scheduler() -> bool:
    """Remove the scheduled task."""
    scheduler = _get_scheduler_class()()
    return scheduler.uninstall()


def is_scheduler_installed() -> bool:
    """Check whether the scheduled task exists."""
    scheduler = _get_scheduler_class()()
    return scheduler.is_installed()


def get_scheduler_info() -> Dict:
    """Return metadata about the scheduled task."""
    scheduler = _get_scheduler_class()()
    return scheduler.get_info()
