"""Tests for shared_skills_bridge.adapter."""

import unittest
from pathlib import Path

from src.adapter import adapt_skill_content, Platform


class TestAdaptSkillContent(unittest.TestCase):
    """Content adaptation tests."""

    def test_kimi_replaces_hermes_skill_dir(self):
        content = "Run scripts in ${HERMES_SKILL_DIR}/scripts/setup.sh"
        result = adapt_skill_content(content, Platform.KIMI, skill_dir=Path("/home/user/skills/my-skill"))
        self.assertIn("/home/user/skills/my-skill/scripts/setup.sh", result)
        self.assertNotIn("${HERMES_SKILL_DIR}", result)

    def test_kimi_replaces_hermes_session_id(self):
        content = "Session: ${HERMES_SESSION_ID}"
        result = adapt_skill_content(content, Platform.KIMI)
        self.assertNotIn("${HERMES_SESSION_ID}", result)
        # Should be removed or replaced with empty
        self.assertNotIn("${HERMES_SESSION_ID}", result)

    def test_kimi_replaces_inline_shell(self):
        content = "Today is !`date +%Y-%m-%d`"
        result = adapt_skill_content(content, Platform.KIMI)
        self.assertNotIn("!`", result)
        # Should contain a placeholder
        self.assertIn("[shell:", result)

    def test_kimi_no_change_for_clean_content(self):
        content = "# Hello\nThis is a normal skill.\nUse Python."
        result = adapt_skill_content(content, Platform.KIMI)
        self.assertEqual(result, content)

    def test_hermes_no_change(self):
        content = "Use ${HERMES_SKILL_DIR} and !`date`"
        result = adapt_skill_content(content, Platform.HERMES)
        self.assertEqual(result, content)

    def test_kimi_mixed_markers(self):
        content = (
            "Skill dir: ${HERMES_SKILL_DIR}\n"
            "Session: ${HERMES_SESSION_ID}\n"
            "Date: !`date`\n"
            "Normal text."
        )
        result = adapt_skill_content(content, Platform.KIMI, skill_dir=Path("/skills/x"))
        self.assertIn("/skills/x", result)
        self.assertNotIn("${HERMES_SKILL_DIR}", result)
        self.assertNotIn("${HERMES_SESSION_ID}", result)
        self.assertNotIn("!`", result)
        self.assertIn("Normal text.", result)

    def test_kimi_none_skill_dir(self):
        content = "Path: ${HERMES_SKILL_DIR}"
        result = adapt_skill_content(content, Platform.KIMI, skill_dir=None)
        # When no skill_dir provided, should replace with a placeholder
        self.assertNotIn("${HERMES_SKILL_DIR}", result)


if __name__ == "__main__":
    unittest.main()
