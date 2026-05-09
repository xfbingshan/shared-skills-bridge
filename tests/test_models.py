"""Tests for shared_skills_bridge.models."""

import unittest
from pathlib import Path

from src.models import Skill, Platform, InstallMode, parse_frontmatter


class TestParseFrontmatter(unittest.TestCase):
    """Frontmatter parsing tests."""

    def test_valid_frontmatter(self):
        content = "---\nname: my-skill\ndescription: A test skill\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm["name"], "my-skill")
        self.assertEqual(fm["description"], "A test skill")
        self.assertEqual(body.strip(), "# Body")

    def test_no_frontmatter(self):
        content = "# No frontmatter\nJust body."
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm, {})
        self.assertEqual(body, content)

    def test_empty_frontmatter(self):
        content = "---\n---\n# Body"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm, {})
        self.assertEqual(body.strip(), "# Body")

    def test_multiline_description(self):
        content = (
            "---\n"
            "name: my-skill\n"
            "description: |\n"
            "  A multi-line\n"
            "  description\n"
            "---\n"
            "# Body"
        )
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm["name"], "my-skill")
        self.assertIn("multi-line", fm["description"])
        self.assertEqual(body.strip(), "# Body")

    def test_extra_fields_preserved(self):
        content = (
            "---\n"
            "name: my-skill\n"
            "description: desc\n"
            "version: 1.0.0\n"
            "platforms: [linux, macos]\n"
            "---\n"
            "Body"
        )
        fm, _ = parse_frontmatter(content)
        self.assertEqual(fm["version"], "1.0.0")
        self.assertEqual(fm["platforms"], ["linux", "macos"])


class TestSkillModel(unittest.TestCase):
    """Skill dataclass tests."""

    def test_skill_creation(self):
        skill = Skill(
            name="test-skill",
            description="A test skill",
            source_dir=Path("/tmp/test-skill"),
            resources=["scripts", "references"],
            frontmatter={"name": "test-skill", "description": "A test skill"},
        )
        self.assertEqual(skill.name, "test-skill")
        self.assertEqual(skill.resources, ["scripts", "references"])

    def test_skill_default_resources(self):
        skill = Skill(
            name="test-skill",
            description="A test skill",
            source_dir=Path("/tmp/test-skill"),
        )
        self.assertEqual(skill.resources, [])
        self.assertEqual(skill.frontmatter, {})


class TestEnums(unittest.TestCase):
    """Enumeration tests."""

    def test_platform_values(self):
        self.assertEqual(Platform.KIMI.value, "kimi")
        self.assertEqual(Platform.HERMES.value, "hermes")

    def test_install_mode_values(self):
        self.assertEqual(InstallMode.COPY.value, "copy")
        self.assertEqual(InstallMode.LINK.value, "link")


if __name__ == "__main__":
    unittest.main()
