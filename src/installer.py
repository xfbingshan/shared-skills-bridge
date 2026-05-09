"""Installer — copies or links skills to target platform directories."""

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List

from src.adapter import adapt_skill_content
from src.models import InstallMode, Platform, Skill


class InstallResult(Enum):
    """Outcome of a single skill installation."""

    COPIED = "copied"
    LINKED = "linked"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class SyncDiff:
    """Represents a difference between source and target."""

    skill_name: str
    status: str  # "ADD", "UPDATE", "REMOVE"
    source_dir: Path
    target_dir: Path


def resolve_target_dir(platform: Platform) -> Path:
    """Return the default target skills directory for *platform*.

    Kimi priority:
        1. ~/.config/agents/skills/
        2. ~/.kimi/skills/

    Hermes:
        ~/.hermes/skills/shared/
    """
    home = Path.home()

    if platform is Platform.KIMI:
        candidates = [
            home / ".config" / "agents" / "skills",
            home / ".kimi" / "skills",
        ]
        for cand in candidates:
            if cand.exists():
                return cand
        # Default to the highest-priority path even if it doesn't exist yet
        return candidates[0]

    if platform is Platform.HERMES:
        hermes_home = home / ".hermes"
        return hermes_home / "skills" / "shared"

    raise ValueError(f"Unsupported platform: {platform}")


def _compute_target_path(skill: Skill, platform: Platform, target_root: Path) -> Path:
    """Compute the destination path for a skill."""
    if platform is Platform.KIMI:
        return target_root / skill.name
    if platform is Platform.HERMES:
        return target_root / "shared" / skill.name
    raise ValueError(f"Unsupported platform: {platform}")


def _copy_skill(skill: Skill, target: Path, platform: Platform) -> None:
    """Copy skill directory to *target*, adapting content for Kimi."""
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(skill.source_dir, target)

    if platform is Platform.KIMI:
        # Adapt SKILL.md content for Kimi
        skill_md = target / "SKILL.md"
        if skill_md.exists():
            original = skill_md.read_text(encoding="utf-8")
            adapted = adapt_skill_content(original, Platform.KIMI, skill_dir=target)
            skill_md.write_text(adapted, encoding="utf-8")


def _create_link(source: Path, target: Path) -> None:
    """Create a symbolic link or junction from *target* -> *source*.

    On Windows, falls back to a directory junction when symlinks require
    elevated privileges.
    """
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()

    try:
        os.symlink(source, target, target_is_directory=True)
    except OSError:
        # Windows fallback: directory junction via mklink /J
        import subprocess

        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            check=True,
            capture_output=True,
        )


def install_skill(
    skill: Skill,
    platform: Platform,
    mode: InstallMode = InstallMode.COPY,
    force: bool = False,
    target_root: Path | None = None,
) -> InstallResult:
    """Install a single skill to the target platform.

    Args:
        skill: Skill to install.
        platform: Target platform.
        mode: COPY or LINK.
        force: Overwrite existing installation.
        target_root: Override the default target directory (used in tests).

    Returns:
        InstallResult enum value.
    """
    if target_root is None:
        target_root = resolve_target_dir(platform)

    target = _compute_target_path(skill, platform, target_root)

    if target.exists() and not force:
        return InstallResult.SKIPPED

    try:
        if mode is InstallMode.COPY:
            _copy_skill(skill, target, platform)
            return InstallResult.COPIED
        if mode is InstallMode.LINK:
            _create_link(skill.source_dir, target)
            return InstallResult.LINKED
    except Exception:
        return InstallResult.ERROR

    return InstallResult.ERROR


def check_sync(
    skills: List[Skill],
    platform: Platform,
    target_root: Path | None = None,
) -> List[SyncDiff]:
    """Compare source skills against installed ones and report differences.

    Returns:
        List of SyncDiff objects (ADD or UPDATE only).
    """
    if target_root is None:
        target_root = resolve_target_dir(platform)

    diffs: List[SyncDiff] = []

    for skill in skills:
        target = _compute_target_path(skill, platform, target_root)
        if not target.exists():
            diffs.append(
                SyncDiff(
                    skill_name=skill.name,
                    status="ADD",
                    source_dir=skill.source_dir,
                    target_dir=target,
                )
            )
            continue

        # Compare SKILL.md content
        source_md = skill.source_dir / "SKILL.md"
        target_md = target / "SKILL.md"
        if source_md.exists() and target_md.exists():
            source_content = source_md.read_text(encoding="utf-8")
            target_content = target_md.read_text(encoding="utf-8")
            if source_content != target_content:
                diffs.append(
                    SyncDiff(
                        skill_name=skill.name,
                        status="UPDATE",
                        source_dir=skill.source_dir,
                        target_dir=target,
                    )
                )

    return diffs
