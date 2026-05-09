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
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def _save_baseline(names: Set[str], path: Path) -> None:
    """Persist the set of known skill names to a JSON file."""
    path.write_text(json.dumps(sorted(names), indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Generic helpers (DRY)
# ---------------------------------------------------------------------------

def _discover_additions(
    skills_dir: Path,
    baseline_path: Path,
    exclude: Set[str] | None = None,
) -> List[Skill]:
    """Scan *skills_dir* and return skills not recorded in *baseline_path*.

    On first run (no baseline), records current contents as baseline and
    returns an empty list.
    """
    baseline = _load_baseline(baseline_path)
    current_skills = scan_skills(skills_dir)
    current_names = {s.name for s in current_skills}

    if not baseline:
        _save_baseline(current_names, baseline_path)
        return []

    new_names = current_names - baseline
    if exclude:
        new_names -= exclude
    return [s for s in current_skills if s.name in new_names]


def _update_baseline(
    skills_dir: Path,
    baseline_path: Path,
    exclude: Set[str] | None = None,
) -> None:
    """Re-scan *skills_dir* and persist names to *baseline_path*."""
    current_skills = scan_skills(skills_dir)
    current_names = {s.name for s in current_skills}
    if exclude:
        current_names -= exclude
    _save_baseline(current_names, baseline_path)


def _sync_to_shared(
    additions: List[Skill],
    shared_source_dir: Path,
) -> List[str]:
    """Copy *additions* into the shared source directory."""
    copied: List[str] = []
    for skill in additions:
        target = shared_source_dir / skill.name
        if target.exists():
            continue
        shutil.copytree(skill.source_dir, target)
        copied.append(skill.name)
    return copied


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
    """Scan Hermes skills directory and return newly-added user skills."""
    if hermes_skills_dir is None:
        hermes_skills_dir = _get_hermes_home() / "skills"
    if baseline_path is None:
        baseline_path = hermes_skills_dir / _BASELINE_FILENAME
    return _discover_additions(hermes_skills_dir, baseline_path, exclude={"shared"})


def update_baseline(
    hermes_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    """Re-scan Hermes and update the baseline to match current state."""
    if hermes_skills_dir is None:
        hermes_skills_dir = _get_hermes_home() / "skills"
    if baseline_path is None:
        baseline_path = hermes_skills_dir / _BASELINE_FILENAME
    _update_baseline(hermes_skills_dir, baseline_path, exclude={"shared"})


def sync_hermes_to_shared(
    additions: List[Skill],
    shared_source_dir: Path,
) -> List[str]:
    """Copy Hermes-side additions into the shared source directory."""
    return _sync_to_shared(additions, shared_source_dir)


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
    """Scan Kimi skills directory and return newly-added user skills."""
    if kimi_skills_dir is None:
        kimi_skills_dir = _resolve_kimi_skills_dir()
    if baseline_path is None:
        baseline_path = kimi_skills_dir / _KIMI_BASELINE_FILENAME
    return _discover_additions(kimi_skills_dir, baseline_path)


def update_kimi_baseline(
    kimi_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    """Re-scan Kimi and update the baseline to match current state."""
    if kimi_skills_dir is None:
        kimi_skills_dir = _resolve_kimi_skills_dir()
    if baseline_path is None:
        baseline_path = kimi_skills_dir / _KIMI_BASELINE_FILENAME
    _update_baseline(kimi_skills_dir, baseline_path)


def sync_kimi_to_shared(
    additions: List[Skill],
    shared_source_dir: Path,
) -> List[str]:
    """Copy Kimi-side additions into the shared source directory."""
    return _sync_to_shared(additions, shared_source_dir)
