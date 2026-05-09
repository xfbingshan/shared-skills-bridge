"""Tests for bidirectional sync: Hermes -> shared-source -> Kimi."""

import json
import tempfile
import unittest
from pathlib import Path

from src.bidirectional import (
    _BASELINE_FILENAME,
    _load_baseline,
    _save_baseline,
    discover_hermes_additions,
    sync_hermes_to_shared,
)
from src.models import Skill


class TestBaseline(unittest.TestCase):
    """Baseline persistence tests."""

    def test_save_and_load_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "baseline.json"
            data = {"skill-a", "skill-b"}
            _save_baseline(data, path)
            loaded = _load_baseline(path)
            self.assertEqual(loaded, data)

    def test_load_missing_baseline_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            self.assertEqual(_load_baseline(path), set())

    def test_baseline_filename_constant(self):
        self.assertEqual(_BASELINE_FILENAME, ".hermes-baseline.json")


class TestDiscoverHermesAdditions(unittest.TestCase):
    """Hermes-side new skill discovery tests."""

    def test_no_additions_when_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            hermes_dir.mkdir()
            baseline_path = Path(tmpdir) / _BASELINE_FILENAME
            _save_baseline(set(), baseline_path)

            additions = discover_hermes_additions(hermes_dir, baseline_path)
            self.assertEqual(additions, [])

    def test_detects_new_skill_not_in_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            hermes_dir.mkdir()
            (hermes_dir / "new-skill").mkdir()
            (hermes_dir / "new-skill" / "SKILL.md").write_text(
                "---\nname: new-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            # baseline only knows old-skill
            baseline_path = Path(tmpdir) / _BASELINE_FILENAME
            _save_baseline({"old-skill"}, baseline_path)

            additions = discover_hermes_additions(hermes_dir, baseline_path)
            self.assertEqual(len(additions), 1)
            self.assertEqual(additions[0].name, "new-skill")

    def test_ignores_shared_subdir(self):
        """The 'shared' subdir is managed by us; should not be treated as a new skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            hermes_dir.mkdir()
            (hermes_dir / "shared").mkdir()
            (hermes_dir / "shared" / "git-commit-guide").mkdir()
            (hermes_dir / "shared" / "git-commit-guide" / "SKILL.md").write_text(
                "---\nname: git-commit-guide\ndescription: desc\n---\n", encoding="utf-8"
            )
            baseline_path = Path(tmpdir) / _BASELINE_FILENAME
            _save_baseline(set(), baseline_path)

            additions = discover_hermes_additions(hermes_dir, baseline_path)
            self.assertEqual(additions, [])

    def test_ignores_non_skill_dirs(self):
        """Directories without SKILL.md should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            hermes_dir.mkdir()
            (hermes_dir / "random-folder").mkdir()
            (hermes_dir / "random-folder" / "readme.txt").write_text("hi", encoding="utf-8")
            baseline_path = Path(tmpdir) / _BASELINE_FILENAME
            _save_baseline(set(), baseline_path)

            additions = discover_hermes_additions(hermes_dir, baseline_path)
            self.assertEqual(additions, [])

    def test_auto_baseline_creation_on_first_run(self):
        """If no baseline exists, treat current Hermes skills as baseline and return empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            hermes_dir.mkdir()
            (hermes_dir / "existing-skill").mkdir()
            (hermes_dir / "existing-skill" / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: desc\n---\n", encoding="utf-8"
            )
            baseline_path = Path(tmpdir) / _BASELINE_FILENAME

            # baseline does not exist yet
            self.assertFalse(baseline_path.exists())
            additions = discover_hermes_additions(hermes_dir, baseline_path)

            # Should create baseline and return no additions
            self.assertEqual(additions, [])
            self.assertTrue(baseline_path.exists())
            loaded = _load_baseline(baseline_path)
            self.assertIn("existing-skill", loaded)


class TestSyncHermesToShared(unittest.TestCase):
    """Reverse sync tests."""

    def test_copies_new_skill_to_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            shared_dir = Path(tmpdir) / "shared-skills"
            hermes_dir.mkdir()
            shared_dir.mkdir()

            skill_dir = hermes_dir / "my-hermes-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: my-hermes-skill\ndescription: Created in Hermes\n---\n# Body\n",
                encoding="utf-8",
            )
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "ref.md").write_text("ref", encoding="utf-8")

            skill = Skill(
                name="my-hermes-skill",
                description="Created in Hermes",
                source_dir=skill_dir,
            )

            copied = sync_hermes_to_shared([skill], shared_dir)
            self.assertEqual(copied, ["my-hermes-skill"])

            # Verify copied content
            target = shared_dir / "my-hermes-skill"
            self.assertTrue((target / "SKILL.md").exists())
            self.assertTrue((target / "references" / "ref.md").exists())
            content = (target / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Created in Hermes", content)

    def test_skips_already_existing_in_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_dir = Path(tmpdir) / "hermes"
            shared_dir = Path(tmpdir) / "shared-skills"
            hermes_dir.mkdir()
            shared_dir.mkdir()

            skill_dir = hermes_dir / "existing-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: desc\n---\n", encoding="utf-8"
            )

            # Pre-populate shared
            (shared_dir / "existing-skill").mkdir()
            (shared_dir / "existing-skill" / "SKILL.md").write_text("old", encoding="utf-8")

            skill = Skill(name="existing-skill", description="desc", source_dir=skill_dir)
            copied = sync_hermes_to_shared([skill], shared_dir)
            self.assertEqual(copied, [])


if __name__ == "__main__":
    unittest.main()
