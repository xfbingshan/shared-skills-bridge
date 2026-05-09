"""Skill scanner — discovers valid skill packages in a source directory."""

from pathlib import Path
from typing import List

from src.models import Skill, parse_frontmatter


def scan_skills(source_dir: Path) -> List[Skill]:
    """Scan *source_dir* for valid skill packages.

    A valid skill is a direct subdirectory containing a ``SKILL.md`` file
    with at least ``name`` and ``description`` in its YAML frontmatter.

    Args:
        source_dir: Root directory to scan.

    Returns:
        Sorted list of :class:`Skill` objects (by name).
    """
    if not source_dir.exists() or not source_dir.is_dir():
        return []

    skills: List[Skill] = []

    for entry in sorted(source_dir.iterdir()):
        if not entry.is_dir():
            continue

        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue

        frontmatter, _ = parse_frontmatter(content)
        name = frontmatter.get("name", "").strip()
        description = frontmatter.get("description", "").strip()

        if not name or not description:
            continue

        # Collect resource subdirectories/files (excluding SKILL.md itself)
        resources = [
            child.name
            for child in entry.iterdir()
            if child.name != "SKILL.md"
        ]
        resources.sort()

        skills.append(
            Skill(
                name=name,
                description=description,
                source_dir=entry,
                resources=resources,
                frontmatter=frontmatter,
            )
        )

    skills.sort(key=lambda s: s.name)
    return skills
