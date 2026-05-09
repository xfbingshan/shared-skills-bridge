"""Bidirectional sync — detects new skills created in Hermes and backfills them
to the shared source directory so they can be installed to Kimi as well.
"""

import json
import shutil
from pathlib import Path
from typing import List, Set

from src.models import Skill
from src.scanner import scan_skills

_BASELINE_FILENAME = ".hermes-baseline.json"


def _load_baseline(path: Path) -> Set[str]:
    """Load the set of known Hermes skill names from a JSON file."""
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
    """Persist the set of known Hermes skill names to a JSON file."""
    path.write_text(json.dumps(sorted(names), indent=2), encoding="utf-8")


def _get_hermes_home() -> Path:
    """Return the Hermes home directory (~/.hermes)."""
    return Path.home() / ".hermes"


def discover_hermes_additions(
    hermes_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> List[Skill]:
    """Scan Hermes skills directory and return newly-added user skills.

    On the first run (no baseline file), the current contents of the
    Hermes skills directory are recorded as the baseline and an empty
    list is returned. Subsequent runs detect only directories that have
    appeared *after* the baseline was established.

    The ``shared/`` subdirectory is always ignored because it is managed
    by the forward-sync process.

    Args:
        hermes_skills_dir: Override path to ``~/.hermes/skills/``.
        baseline_path: Override path to the baseline JSON file.

    Returns:
        List of :class:`Skill` objects that are new since baseline.
    """
    if hermes_skills_dir is None:
        hermes_skills_dir = _get_hermes_home() / "skills"
    if baseline_path is None:
        baseline_path = hermes_skills_dir / _BASELINE_FILENAME

    baseline = _load_baseline(baseline_path)

    # Scan current Hermes skills (flat structure under ~/.hermes/skills/)
    current_skills = scan_skills(hermes_skills_dir)
    current_names = {s.name for s in current_skills}

    # On first run: establish baseline and return empty
    if not baseline:
        _save_baseline(current_names, baseline_path)
        return []

    # Find skills that exist now but were NOT in the baseline
    new_names = current_names - baseline

    # Filter out the 'shared' directory (managed by forward sync)
    new_names.discard("shared")

    return [s for s in current_skills if s.name in new_names]


def update_baseline(
    hermes_skills_dir: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    """Re-scan Hermes and update the baseline to match current state.

    Call this after intentionally installing new skills into Hermes
    that you do NOT want to be treated as user additions (e.g. after
    running ``hermes skills install`` for official skills).
    """
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
    """Copy Hermes-side additions into the shared source directory.

    Args:
        additions: Skills discovered by :func:`discover_hermes_additions`.
        shared_source_dir: Root of the shared skills source tree.

    Returns:
        List of skill names that were actually copied.
    """
    copied: List[str] = []
    for skill in additions:
        target = shared_source_dir / skill.name
        if target.exists():
            continue
        shutil.copytree(skill.source_dir, target)
        copied.append(skill.name)
    return copied
