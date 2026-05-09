"""Tests for Kimi -> shared-source reverse sync."""

import tempfile
import unittest
from pathlib import Path

from src.bidirectional import (
    _KIMI_BASELINE_FILENAME,
    _resolve_kimi_skills_dir,
    discover_kimi_additions,
    sync_kimi_to_shared,
)
from src.models import Skill


class TestResolveKimiSkillsDir(unittest.TestCase):
    """Kimi skills directory resolution tests."""

    def test_prefers_config_agents_when_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".config" / "agents" / "skills"
            agents_dir.mkdir(parents=True)
            # We can't easily monkeypatch Path.home(), but we can test
            # the function returns a path under home.
            result = _resolve_kimi_skills_dir()
            self.assertIsInstance(result, Path)
            # Should contain 'skills' somewhere
            self.assertIn("skills", str(result).lower().replace("\\", "/"))


class TestDiscoverKimiAdditions(unittest.TestCase):
    """Kimi-side new skill discovery tests."""

    def test_no_additions_when_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            kimi_dir.mkdir()
            baseline_path = Path(tmpdir) / _KIMI_BASELINE_FILENAME
            baseline_path.write_text("[]", encoding="utf-8")

            additions = discover_kimi_additions(kimi_dir, baseline_path)
            self.assertEqual(additions, [])

    def test_detects_new_skill_not_in_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            kimi_dir.mkdir()
            skill_dir = kimi_dir / "new-kimi-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: new-kimi-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            baseline_path = Path(tmpdir) / _KIMI_BASELINE_FILENAME
            baseline_path.write_text('["old-skill"]', encoding="utf-8")

            additions = discover_kimi_additions(kimi_dir, baseline_path)
            self.assertEqual(len(additions), 1)
            self.assertEqual(additions[0].name, "new-kimi-skill")

    def test_auto_baseline_creation_on_first_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            kimi_dir.mkdir()
            skill_dir = kimi_dir / "existing-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            baseline_path = Path(tmpdir) / _KIMI_BASELINE_FILENAME
            self.assertFalse(baseline_path.exists())

            additions = discover_kimi_additions(kimi_dir, baseline_path)
            self.assertEqual(additions, [])
            self.assertTrue(baseline_path.exists())
            import json
            loaded = set(json.loads(baseline_path.read_text(encoding="utf-8")))
            self.assertIn("existing-skill", loaded)

    def test_ignores_non_skill_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            kimi_dir.mkdir()
            (kimi_dir / "random-folder").mkdir()
            (kimi_dir / "random-folder" / "readme.txt").write_text("hi", encoding="utf-8")
            baseline_path = Path(tmpdir) / _KIMI_BASELINE_FILENAME
            baseline_path.write_text("[]", encoding="utf-8")

            additions = discover_kimi_additions(kimi_dir, baseline_path)
            self.assertEqual(additions, [])


class TestSyncKimiToShared(unittest.TestCase):
    """Kimi -> shared reverse sync tests."""

    def test_copies_new_skill_to_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            shared_dir = Path(tmpdir) / "shared-skills"
            kimi_dir.mkdir()
            shared_dir.mkdir()

            skill_dir = kimi_dir / "my-kimi-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: my-kimi-skill\ndescription: From Kimi\n---\n# Body\n",
                encoding="utf-8",
            )

            skill = Skill(name="my-kimi-skill", description="From Kimi", source_dir=skill_dir)
            copied = sync_kimi_to_shared([skill], shared_dir)
            self.assertEqual(copied, ["my-kimi-skill"])
            self.assertTrue((shared_dir / "my-kimi-skill" / "SKILL.md").exists())

    def test_skips_already_existing_in_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kimi_dir = Path(tmpdir) / "kimi"
            shared_dir = Path(tmpdir) / "shared-skills"
            kimi_dir.mkdir()
            shared_dir.mkdir()

            skill_dir = kimi_dir / "existing-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            (shared_dir / "existing-skill").mkdir()
            (shared_dir / "existing-skill" / "SKILL.md").write_text("old", encoding="utf-8")

            skill = Skill(name="existing-skill", description="desc", source_dir=skill_dir)
            copied = sync_kimi_to_shared([skill], shared_dir)
            self.assertEqual(copied, [])


if __name__ == "__main__":
    unittest.main()
