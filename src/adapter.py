"""Content adapter — cleans platform-specific syntax for cross-platform skills."""

import re
from pathlib import Path

from src.models import Platform

# Patterns for Hermes-specific syntax
_HERMES_SKILL_DIR_RE = re.compile(r"\$\{HERMES_SKILL_DIR\}")
_HERMES_SESSION_ID_RE = re.compile(r"\$\{HERMES_SESSION_ID\}")
_INLINE_SHELL_RE = re.compile(r"!`([^`\n]+)`")


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
    """
    if platform is Platform.HERMES:
        # Hermes natively understands all syntax; pass through unchanged.
        return content

    if platform is not Platform.KIMI:
        raise ValueError(f"Unsupported platform: {platform}")

    # Kimi adaptations ───────────────────────────────────────────────

    # 1. Replace ${HERMES_SKILL_DIR} with the actual path
    if skill_dir is not None:
        # Use forward slashes for cross-platform path references in Markdown
        skill_dir_str = str(skill_dir).replace("\\", "/")
        content = _HERMES_SKILL_DIR_RE.sub(lambda _m: skill_dir_str, content)
    else:
        content = _HERMES_SKILL_DIR_RE.sub(lambda _m: "[skill-dir]", content)

    # 2. Strip ${HERMES_SESSION_ID}
    content = _HERMES_SESSION_ID_RE.sub("", content)

    # 3. Replace inline shell !`cmd` with a placeholder
    def _shell_placeholder(match: re.Match) -> str:
        cmd = match.group(1).strip()
        return f"[shell: {cmd}]"

    content = _INLINE_SHELL_RE.sub(_shell_placeholder, content)

    return content
