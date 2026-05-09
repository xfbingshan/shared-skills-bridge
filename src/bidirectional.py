"""Bidirectional sync — detects new skills created in either Hermes or Kimi
and backfills them to the shared source directory so they propagate to both
platforms.
"""

import json
import shutil
from pathlib import Path
from typing import List, Set

from src.models import Skill
from src.scanner import scan_skills

_BASELINE_FILENAME = ".hermes-baseline.json"
_KIMI_BASELINE_FILENAME = ".kimi-baseline.json"


def _load_baseline(path: Path) -> Set[str]:
    """Load the set of known skill names from a JSON file."""
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def _save_baseline(names: Set[str], path: Path) -> None:
    """Persist the set of known skill names to a JSON file."""
    path.write_text(json.dumps(sorted(names), indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Hermes side
# ---------------------------------------------------------------------------

def _get_hermes_home() -> Path:
    """Return the Hermes home directory (~/.hermes)."""
    return Path.home() / ".hermes"


def discover_hermes_additions(
    hermes_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> List[Skill]:
    """Scan Hermes skills directory and return newly-added user skills.

    On the first run (no baseline file), the current contents are recorded
    as the baseline and an empty list is returned.
    """
    if hermes_skills_dir is None:
        hermes_skills_dir = _get_hermes_home() / "skills"
    if baseline_path is None:
        baseline_path = hermes_skills_dir / _BASELINE_FILENAME

    baseline = _load_baseline(baseline_path)
    current_skills = scan_skills(hermes_skills_dir)
    current_names = {s.name for s in current_skills}

    if not baseline:
        _save_baseline(current_names, baseline_path)
        return []

    new_names = current_names - baseline
    new_names.discard("shared")
    return [s for s in current_skills if s.name in new_names]


def update_baseline(
    hermes_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    """Re-scan Hermes and update the baseline to match current state."""
    if hermes_skills_dir is None:
        hermes_skills_dir = _get_hermes_home() / "skills"
    if baseline_path is None:
        baseline_path = hermes_skills_dir / _BASELINE_FILENAME

    current_skills = scan_skills(hermes_skills_dir)
    current_names = {s.name for s in current_skills}
    current_names.discard("shared")
    _save_baseline(current_names, baseline_path)


def sync_hermes_to_shared(
    additions: List[Skill],
    shared_source_dir: Path,
) -> List[str]:
    """Copy Hermes-side additions into the shared source directory."""
    copied: List[str] = []
    for skill in additions:
        target = shared_source_dir / skill.name
        if target.exists():
            continue
        shutil.copytree(skill.source_dir, target)
        copied.append(skill.name)
    return copied


# ---------------------------------------------------------------------------
# Kimi side
# ---------------------------------------------------------------------------

def _resolve_kimi_skills_dir() -> Path:
    """Return the active Kimi skills directory (first existing candidate)."""
    home = Path.home()
    candidates = [
        home / ".config" / "agents" / "skills",
        home / ".kimi" / "skills",
        home / ".claude" / "skills",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


def discover_kimi_additions(
    kimi_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> List[Skill]:
    """Scan Kimi skills directory and return newly-added user skills.

    On the first run (no baseline file), the current contents are recorded
    as the baseline and an empty list is returned.
    """
    if kimi_skills_dir is None:
        kimi_skills_dir = _resolve_kimi_skills_dir()
    if baseline_path is None:
        baseline_path = kimi_skills_dir / _KIMI_BASELINE_FILENAME

    baseline = _load_baseline(baseline_path)
    current_skills = scan_skills(kimi_skills_dir)
    current_names = {s.name for s in current_skills}

    if not baseline:
        _save_baseline(current_names, baseline_path)
        return []

    new_names = current_names - baseline
    return [s for s in current_skills if s.name in new_names]


def update_kimi_baseline(
    kimi_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    """Re-scan Kimi and update the baseline to match current state."""
    if kimi_skills_dir is None:
        kimi_skills_dir = _resolve_kimi_skills_dir()
    if baseline_path is None:
        baseline_path = kimi_skills_dir / _KIMI_BASELINE_FILENAME

    current_skills = scan_skills(kimi_skills_dir)
    current_names = {s.name for s in current_skills}
    _save_baseline(current_names, baseline_path)


def sync_kimi_to_shared(
    additions: List[Skill],
    shared_source_dir: Path,
) -> List[str]:
    """Copy Kimi-side additions into the shared source directory."""
    copied: List[str] = []
    for skill in additions:
        target = shared_source_dir / skill.name
        if target.exists():
            continue
        shutil.copytree(skill.source_dir, target)
        copied.append(skill.name)
    return copied
