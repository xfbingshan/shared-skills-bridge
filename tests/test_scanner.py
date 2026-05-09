"""Tests for shared_skills_bridge.scanner."""

import tempfile
import unittest
from pathlib import Path

from src.scanner import scan_skills


class TestScanSkills(unittest.TestCase):
    """Skill scanner tests."""

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])

    def test_single_valid_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "my-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: A great skill\n---\n# Hello\n",
                encoding="utf-8",
            )
            result = scan_skills(Path(tmpdir))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, "my-skill")
            self.assertEqual(result[0].description, "A great skill")

    def test_skill_with_resources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "my-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: desc\n---\n",
                encoding="utf-8",
            )
            (skill_dir / "scripts").mkdir()
            (skill_dir / "references").mkdir()
            result = scan_skills(Path(tmpdir))
            self.assertIn("scripts", result[0].resources)
            self.assertIn("references", result[0].resources)

    def test_missing_frontmatter_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "bad-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# No frontmatter\n", encoding="utf-8")
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])

    def test_missing_name_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "bad-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\ndescription: only desc\n---\n", encoding="utf-8"
            )
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])

    def test_missing_description_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "bad-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: only-name\n---\n", encoding="utf-8"
            )
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])

    def test_non_directory_items_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "random-file.txt").write_text("hello", encoding="utf-8")
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])

    def test_multiple_skills_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("zebra-skill", "apple-skill"):
                skill_dir = Path(tmpdir) / name
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: desc\n---\n",
                    encoding="utf-8",
                )
            result = scan_skills(Path(tmpdir))
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].name, "apple-skill")
            self.assertEqual(result[1].name, "zebra-skill")

    def test_deeply_nested_skill_not_scanned(self):
        """Only direct subdirectories of source are considered skill roots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "category" / "deep-skill"
            nested.mkdir(parents=True)
            (nested / "SKILL.md").write_text(
                "---\nname: deep-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
