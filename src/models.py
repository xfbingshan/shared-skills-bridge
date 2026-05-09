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


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_DELIMITER = re.compile(r"\n---\s*\n")


def _strip_bom(content: str) -> str:
    """Strip UTF-8 BOM if present (common on Windows)."""
    if content.startswith("\ufeff"):
        return content[1:]
    return content


def _extract_yaml_block(content: str) -> Tuple[str | None, str]:
    """Extract YAML frontmatter block and remaining body from markdown.

    Returns:
        (yaml_block, body) — yaml_block is None if no frontmatter found.
    """
    if not content.startswith("---"):
        return None, content

    end_match = _FRONTMATTER_DELIMITER.search(content[3:])
    if not end_match:
        return None, content

    yaml_block = content[3 : end_match.start() + 3]
    body = content[end_match.end() + 3 :]
    return yaml_block, body


def _parse_scalar_value(value: str) -> Any:
    """Parse a single scalar YAML value.

    Handles:
    - Empty list: []
    - Non-empty list: [a, b, c]
    - Quoted strings: "foo", 'bar'
    - Plain strings
    """
    value = value.strip()

    # List values
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"\'') for item in inner.split(",")]

    # Strip quotes from scalar strings
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]

    return value


def _parse_multiline_value(lines: list[str], start_idx: int) -> Tuple[str, int]:
    """Parse a multiline YAML value (| or >).

    Returns:
        (collected_value, next_index)
    """
    i = start_idx

    # Determine base indentation from next non-empty line
    base_indent = 0
    while i < len(lines):
        if lines[i].strip():
            base_indent = len(lines[i]) - len(lines[i].lstrip())
            break
        i += 1

    collected: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Stop at new top-level key (less indented, contains colon)
        if stripped and ":" in stripped:
            indent = len(line) - len(stripped)
            if indent < base_indent:
                break

        if line.strip():
            collected.append(line.strip())
        i += 1

    return "\n".join(collected), i


def _parse_yaml_block(yaml_content: str) -> Dict[str, Any]:
    """Parse a YAML frontmatter string into a dictionary.

    Supports simple scalars, lists, and multiline values (|, >).
    """
    frontmatter: Dict[str, Any] = {}
    lines = yaml_content.strip().split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1

        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        # Multiline values
        if raw_value in ("|", ">"):
            value, i = _parse_multiline_value(lines, i)
            frontmatter[key] = value
            continue

        frontmatter[key] = _parse_scalar_value(raw_value)

    return frontmatter


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns:
        (frontmatter_dict, remaining_body)
    """
    content = _strip_bom(content)
    yaml_block, body = _extract_yaml_block(content)

    if yaml_block is None:
        return {}, body

    frontmatter = _parse_yaml_block(yaml_block)
    return frontmatter, body
