"""Integration tests for the full bridge workflow."""

import tempfile
import unittest
from pathlib import Path

from src.installer import InstallResult, check_sync, install_skill, resolve_target_dir
from src.models import InstallMode, Platform, Skill
from src.scanner import scan_skills


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end workflow tests."""

    def test_full_copy_to_kimi(self):
        """Scan source -> install to Kimi -> verify adapted content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()

            skill_dir = source / "git-best-practices"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: git-best-practices\n"
                "description: Guidelines for writing good Git commits and branches\n"
                "---\n"
                "# Git Best Practices\n"
                "\n"
                "Run setup from ${HERMES_SKILL_DIR}/scripts/setup.sh\n"
                "Session: ${HERMES_SESSION_ID}\n"
                "Today: !`date +%Y-%m-%d`\n",
                encoding="utf-8",
            )
            (skill_dir / "scripts").mkdir()
            (skill_dir / "scripts" / "setup.sh").write_text("#!/bin/bash\necho ok\n", encoding="utf-8")

            skills = scan_skills(source)
            self.assertEqual(len(skills), 1)

            target_root = Path(tmpdir) / "kimi"
            result = install_skill(skills[0], Platform.KIMI, InstallMode.COPY, target_root=target_root)
            self.assertEqual(result, InstallResult.COPIED)

            # Verify adapted content
            installed_md = target_root / "git-best-practices" / "SKILL.md"
            content = installed_md.read_text(encoding="utf-8")
            self.assertNotIn("${HERMES_SKILL_DIR}", content)
            self.assertNotIn("${HERMES_SESSION_ID}", content)
            self.assertNotIn("!`", content)
            self.assertIn("[shell:", content)

            # Verify scripts copied
            self.assertTrue((target_root / "git-best-practices" / "scripts" / "setup.sh").exists())

    def test_full_copy_to_hermes(self):
        """Scan source -> install to Hermes -> verify structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()

            skill_dir = source / "docker-guide"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: docker-guide\n"
                "description: How to write efficient Dockerfiles\n"
                "---\n"
                "# Docker Guide\n",
                encoding="utf-8",
            )

            skills = scan_skills(source)
            target_root = Path(tmpdir) / "hermes"
            result = install_skill(skills[0], Platform.HERMES, InstallMode.COPY, target_root=target_root)
            self.assertEqual(result, InstallResult.COPIED)

            # target_root already includes the 'shared' subdir for Hermes
            installed_md = target_root / "docker-guide" / "SKILL.md"
            self.assertTrue(installed_md.exists())

            # Hermes content should NOT be adapted
            content = installed_md.read_text(encoding="utf-8")
            self.assertIn("docker-guide", content)

    def test_sync_check_detects_changes(self):
        """Check sync after modifying source skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()

            skill_dir = source / "python-patterns"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: python-patterns\ndescription: Python design patterns\n---\nV1\n",
                encoding="utf-8",
            )

            skills = scan_skills(source)
            target_root = Path(tmpdir) / "kimi"

            # Install V1
            install_skill(skills[0], Platform.KIMI, InstallMode.COPY, target_root=target_root)

            # Modify source to V2
            (skill_dir / "SKILL.md").write_text(
                "---\nname: python-patterns\ndescription: Python design patterns\n---\nV2\n",
                encoding="utf-8",
            )
            skills = scan_skills(source)

            diffs = check_sync(skills, Platform.KIMI, target_root=target_root)
            self.assertEqual(len(diffs), 1)
            self.assertEqual(diffs[0].status, "UPDATE")

    def test_empty_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "empty"
            source.mkdir()
            skills = scan_skills(source)
            self.assertEqual(skills, [])

    def test_multiple_skills_both_platforms(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()

            for name, desc in (("skill-a", "First"), ("skill-b", "Second")):
                d = source / name
                d.mkdir()
                (d / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: {desc}\n---\n",
                    encoding="utf-8",
                )

            skills = scan_skills(source)
            self.assertEqual(len(skills), 2)

            # Install both to Kimi
            target_root = Path(tmpdir) / "kimi"
            for s in skills:
                install_skill(s, Platform.KIMI, InstallMode.COPY, target_root=target_root)

            self.assertTrue((target_root / "skill-a" / "SKILL.md").exists())
            self.assertTrue((target_root / "skill-b" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
