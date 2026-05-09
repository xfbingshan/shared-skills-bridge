"""Tests for shared_skills_bridge.scheduler (Windows Task Scheduler integration)."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.scheduler import (
    _TASK_NAME,
    get_scheduler_info,
    install_scheduler,
    is_scheduler_installed,
    uninstall_scheduler,
)


class TestSchedulerInstall(unittest.TestCase):
    """Scheduler installation tests."""

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_install_creates_task(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        source = Path("C:/skills/shared-skills")

        result = install_scheduler(source, interval_minutes=10, target="both")

        self.assertTrue(result)
        # Should call schtasks /create
        calls = [c for c in mock_run.call_args_list if "/create" in str(c)]
        self.assertEqual(len(calls), 1)
        # Command should contain our task name
        cmd = calls[0][0][0]
        self.assertIn(_TASK_NAME, cmd)
        # Should reference the source directory (escaped in repr, so check via path parts)
        self.assertIn("shared-skills", str(calls[0]))

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_install_deletes_existing_first(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        source = Path("C:/skills/shared-skills")

        install_scheduler(source, interval_minutes=5)

        # Should first delete existing task, then create new one
        calls = mock_run.call_args_list
        delete_calls = [c for c in calls if "/delete" in str(c)]
        create_calls = [c for c in calls if "/create" in str(c)]
        self.assertEqual(len(delete_calls), 1)
        self.assertEqual(len(create_calls), 1)

    @patch("src.scheduler.is_windows", return_value=False)
    def test_install_refuses_on_non_windows(self, _mock_is_win):
        with self.assertRaises(RuntimeError) as ctx:
            install_scheduler(Path("/tmp/skills"))
        self.assertIn("Windows only", str(ctx.exception))

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_install_fails_when_schtasks_errors(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="Access denied")
        result = install_scheduler(Path("C:/skills"))
        self.assertFalse(result)


class TestSchedulerUninstall(unittest.TestCase):
    """Scheduler uninstallation tests."""

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_uninstall_deletes_task(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = uninstall_scheduler()
        self.assertTrue(result)
        calls = [c for c in mock_run.call_args_list if "/delete" in str(c)]
        self.assertEqual(len(calls), 1)
        self.assertIn(_TASK_NAME, str(calls[0]))

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_uninstall_succeeds_when_task_not_found(self, _mock_is_win, mock_run):
        """Uninstall should succeed if task doesn't exist (nothing to delete)."""
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: The system cannot find")
        result = uninstall_scheduler()
        self.assertTrue(result)

    @patch("src.scheduler.is_windows", return_value=False)
    def test_uninstall_refuses_on_non_windows(self, _mock_is_win):
        with self.assertRaises(RuntimeError):
            uninstall_scheduler()


class TestSchedulerStatus(unittest.TestCase):
    """Scheduler status query tests."""

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_is_installed_when_task_exists(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="TaskName: SkillsBridgeSync")
        self.assertTrue(is_scheduler_installed())

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_is_not_installed_when_task_missing(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: The system cannot find")
        self.assertFalse(is_scheduler_installed())

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_get_info_returns_dict(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="TaskName: SkillsBridgeSync\nNext Run Time: 2026/5/10 12:00:00",
        )
        info = get_scheduler_info()
        self.assertIsInstance(info, dict)
        self.assertIn("installed", info)
        self.assertTrue(info["installed"])
        self.assertIn("raw", info)

    @patch("subprocess.run")
    @patch("src.scheduler.is_windows", return_value=True)
    def test_get_info_when_not_installed(self, _mock_is_win, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: Task not found")
        info = get_scheduler_info()
        self.assertFalse(info["installed"])


class TestTaskName(unittest.TestCase):
    def test_task_name_is_constant(self):
        self.assertEqual(_TASK_NAME, "SkillsBridgeSync")


if __name__ == "__main__":
    unittest.main()
