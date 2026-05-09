"""Content adapter — cleans platform-specific syntax for cross-platform skills."""

import re
from pathlib import Path
from typing import Callable

from src.models import Platform

# Patterns for Hermes-specific syntax
_HERMES_SKILL_DIR_RE = re.compile(r"\$\{HERMES_SKILL_DIR\}")
_HERMES_SESSION_ID_RE = re.compile(r"\$\{HERMES_SESSION_ID\}")
_INLINE_SHELL_RE = re.compile(r"!`([^`\n]+)`")


def _shell_placeholder(match: re.Match) -> str:
    """Replace inline shell !`cmd` with a safe placeholder."""
    cmd = match.group(1).strip()
    return f"[shell: {cmd}]"


def _adapt_for_kimi(content: str, skill_dir: Path | None = None) -> str:
    """Adapt skill content for Kimi Code CLI.

    - Replaces ${HERMES_SKILL_DIR} with the actual path (or placeholder)
    - Strips ${HERMES_SESSION_ID}
    - Replaces inline shell !`cmd` with placeholders
    """
    # 1. Replace ${HERMES_SKILL_DIR} with the actual path
    if skill_dir is not None:
        skill_dir_str = str(skill_dir).replace("\\", "/")
        content = _HERMES_SKILL_DIR_RE.sub(lambda _m: skill_dir_str, content)
    else:
        content = _HERMES_SKILL_DIR_RE.sub(lambda _m: "[skill-dir]", content)

    # 2. Strip ${HERMES_SESSION_ID}
    content = _HERMES_SESSION_ID_RE.sub("", content)

    # 3. Replace inline shell !`cmd` with a placeholder
    content = _INLINE_SHELL_RE.sub(_shell_placeholder, content)

    return content


def _adapt_for_hermes(content: str, _skill_dir: Path | None = None) -> str:
    """Hermes natively understands all syntax; pass through unchanged."""
    return content


# Strategy registry: Platform -> adapter function
_ADAPTERS: dict[Platform, Callable[[str, Path | None], str]] = {
    Platform.KIMI: _adapt_for_kimi,
    Platform.HERMES: _adapt_for_hermes,
}


def adapt_skill_content(
    content: str,
    platform: Platform,
    skill_dir: Path | None = None,
) -> str:
    """Adapt skill content for the target platform.

    Args:
        content: Original SKILL.md content.
        platform: Target platform.
        skill_dir: Absolute path to the skill directory (used for
            ``${HERMES_SKILL_DIR}`` replacement).

    Returns:
        Adapted content string.

    Raises:
        ValueError: If *platform* has no registered adapter.
    """
    adapter = _ADAPTERS.get(platform)
    if adapter is None:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter(content, skill_dir)
