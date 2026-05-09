"""Tests for shared_skills_bridge.installer."""

import tempfile
import unittest
from pathlib import Path

from src.installer import (
    InstallResult,
    SyncDiff,
    check_sync,
    install_skill,
    resolve_target_dir,
)
from src.models import InstallMode, Platform, Skill


class TestResolveTargetDir(unittest.TestCase):
    """Target directory resolution tests."""

    def test_kimi_prefers_config_agents(self):
        """Should prefer ~/.config/agents/skills/ if it exists."""
        # This test is environment-dependent; we mainly verify the function
        # returns a Path under the user's home directory.
        result = resolve_target_dir(Platform.KIMI)
        self.assertIsInstance(result, Path)
        self.assertIn("skills", str(result).lower().replace("\\", "/"))

    def test_hermes_returns_shared_subdir(self):
        result = resolve_target_dir(Platform.HERMES)
        self.assertIsInstance(result, Path)
        self.assertTrue(str(result).endswith("shared") or str(result).endswith("shared/"))


class TestInstallSkillCopy(unittest.TestCase):
    """Copy-mode installation tests."""

    def test_copy_to_kimi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: desc\n---\n# Hello\n",
                encoding="utf-8",
            )
            (source / "references").mkdir()
            (source / "references" / "ref.md").write_text("ref", encoding="utf-8")

            skill = Skill(
                name="my-skill",
                description="desc",
                source_dir=source,
                resources=["references"],
            )

            target_root = Path(tmpdir) / "kimi"
            result = install_skill(skill, Platform.KIMI, InstallMode.COPY, target_root=target_root)

            self.assertEqual(result, InstallResult.COPIED)
            self.assertTrue((target_root / "my-skill" / "SKILL.md").exists())
            self.assertTrue((target_root / "my-skill" / "references" / "ref.md").exists())

    def test_copy_to_hermes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: desc\n---\n# Hello\n",
                encoding="utf-8",
            )

            skill = Skill(
                name="my-skill",
                description="desc",
                source_dir=source,
            )

            target_root = Path(tmpdir) / "hermes"
            result = install_skill(skill, Platform.HERMES, InstallMode.COPY, target_root=target_root)

            self.assertEqual(result, InstallResult.COPIED)
            # target_root already includes the 'shared' subdir for Hermes
            self.assertTrue((target_root / "my-skill" / "SKILL.md").exists())

    def test_skip_existing_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: my-skill\ndescription: desc\n---\nV2\n", encoding="utf-8")

            target_root = Path(tmpdir) / "kimi"
            (target_root / "my-skill").mkdir(parents=True)
            (target_root / "my-skill" / "SKILL.md").write_text("old content", encoding="utf-8")

            skill = Skill(name="my-skill", description="desc", source_dir=source)
            result = install_skill(skill, Platform.KIMI, InstallMode.COPY, force=False, target_root=target_root)

            self.assertEqual(result, InstallResult.SKIPPED)
            self.assertEqual((target_root / "my-skill" / "SKILL.md").read_text(encoding="utf-8"), "old content")

    def test_force_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: my-skill\ndescription: desc\n---\nV2\n", encoding="utf-8")

            target_root = Path(tmpdir) / "kimi"
            (target_root / "my-skill").mkdir(parents=True)
            (target_root / "my-skill" / "SKILL.md").write_text("old content", encoding="utf-8")

            skill = Skill(name="my-skill", description="desc", source_dir=source)
            result = install_skill(skill, Platform.KIMI, InstallMode.COPY, force=True, target_root=target_root)

            self.assertEqual(result, InstallResult.COPIED)
            self.assertIn("V2", (target_root / "my-skill" / "SKILL.md").read_text(encoding="utf-8"))

    def test_copy_adapts_content_for_kimi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: desc\n---\nPath: ${HERMES_SKILL_DIR}\n",
                encoding="utf-8",
            )

            skill = Skill(name="my-skill", description="desc", source_dir=source)
            target_root = Path(tmpdir) / "kimi"
            install_skill(skill, Platform.KIMI, InstallMode.COPY, target_root=target_root)

            content = (target_root / "my-skill" / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("${HERMES_SKILL_DIR}", content)


class TestCheckSync(unittest.TestCase):
    """Sync diff detection tests."""

    def test_detects_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "new-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: new-skill\ndescription: desc\n---\n", encoding="utf-8")

            skill = Skill(name="new-skill", description="desc", source_dir=source)
            target_root = Path(tmpdir) / "kimi"

            diffs = check_sync([skill], Platform.KIMI, target_root=target_root)
            self.assertEqual(len(diffs), 1)
            self.assertEqual(diffs[0].status, "ADD")

    def test_detects_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: my-skill\ndescription: desc\n---\nV2\n", encoding="utf-8")

            target_root = Path(tmpdir) / "kimi"
            (target_root / "my-skill").mkdir(parents=True)
            (target_root / "my-skill" / "SKILL.md").write_text("old", encoding="utf-8")

            skill = Skill(name="my-skill", description="desc", source_dir=source)
            diffs = check_sync([skill], Platform.KIMI, target_root=target_root)
            self.assertEqual(len(diffs), 1)
            self.assertEqual(diffs[0].status, "UPDATE")

    def test_no_diff_for_identical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source" / "my-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: my-skill\ndescription: desc\n---\nSame\n", encoding="utf-8")

            target_root = Path(tmpdir) / "kimi"
            (target_root / "my-skill").mkdir(parents=True)
            (target_root / "my-skill" / "SKILL.md").write_text("---\nname: my-skill\ndescription: desc\n---\nSame\n", encoding="utf-8")

            skill = Skill(name="my-skill", description="desc", source_dir=source)
            diffs = check_sync([skill], Platform.KIMI, target_root=target_root)
            self.assertEqual(len(diffs), 0)


if __name__ == "__main__":
    unittest.main()
