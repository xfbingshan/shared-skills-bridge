"""Data models for Shared Skills Bridge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Tuple


class Platform(Enum):
    """Target AI agent platform."""

    KIMI = "kimi"
    HERMES = "hermes"


class InstallMode(Enum):
    """Installation strategy."""

    COPY = "copy"
    LINK = "link"


@dataclass
class Skill:
    """Represents a discovered skill package."""

    name: str
    description: str
    source_dir: Path
    resources: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)

    @property
    def skill_md_path(self) -> Path:
        """Return path to SKILL.md."""
        return self.source_dir / "SKILL.md"


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns:
        (frontmatter_dict, remaining_body)
    """
    # Strip UTF-8 BOM if present (common on Windows)
    if content.startswith("\ufeff"):
        content = content[1:]

    frontmatter: Dict[str, Any] = {}
    body = content

    if not content.startswith("---"):
        return frontmatter, body

    # Find the closing ---
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return frontmatter, body

    yaml_content = content[3 : end_match.start() + 3]
    body = content[end_match.end() + 3 :]

    # Parse YAML frontmatter line by line
    lines = yaml_content.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Multiline values: |  or  >
        if value in ("|", ">"):
            collected: list[str] = []
            # Determine base indentation from next non-empty line
            while i < len(lines):
                if lines[i].strip():
                    base_indent = len(lines[i]) - len(lines[i].lstrip())
                    break
                i += 1
            else:
                base_indent = 0

            while i < len(lines):
                next_line = lines[i]
                # Stop if we hit a new top-level key (no indent or less indent)
                if next_line.strip() and not next_line.startswith(" " * (base_indent + 1)) and not next_line.startswith("\t"):
                    # Check if it's a new key
                    stripped = next_line.lstrip()
                    if ":" in stripped and len(next_line) - len(next_line.lstrip()) < base_indent:
                        break
                if next_line.strip():
                    collected.append(next_line.strip())
                i += 1
            value = "\n".join(collected)
            frontmatter[key] = value
            continue

        # List values: [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            if not inner.strip():
                frontmatter[key] = []
            else:
                items = [item.strip().strip('"\'') for item in inner.split(",")]
                frontmatter[key] = items
            continue

        # Strip quotes from scalar values
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        frontmatter[key] = value

    return frontmatter, body
