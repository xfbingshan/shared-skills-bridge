"""Tests for shared_skills_bridge.scheduler (Windows backend)."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.scheduler import (
    _TASK_NAME,
    WindowsScheduler,
    get_scheduler_info,
    install_scheduler,
    is_scheduler_installed,
    uninstall_scheduler,
)


class TestSchedulerInstall(unittest.TestCase):
    """Scheduler installation tests."""

    @patch("subprocess.run")
    def test_install_creates_task(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        scheduler = WindowsScheduler()
        source = Path("C:/skills/shared-skills")

        result = scheduler.install(source, interval_minutes=10, target="both")

        self.assertTrue(result)
        calls = [c for c in mock_run.call_args_list if "/create" in str(c)]
        self.assertEqual(len(calls), 1)
        cmd = calls[0][0][0]
        self.assertIn(_TASK_NAME, cmd)
        self.assertIn("shared-skills", str(calls[0]))

    @patch("subprocess.run")
    def test_install_deletes_existing_first(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        scheduler = WindowsScheduler()
        source = Path("C:/skills/shared-skills")

        scheduler.install(source, interval_minutes=5, target="both")

        calls = mock_run.call_args_list
        delete_calls = [c for c in calls if "/delete" in str(c)]
        create_calls = [c for c in calls if "/create" in str(c)]
        self.assertEqual(len(delete_calls), 1)
        self.assertEqual(len(create_calls), 1)

    @patch("subprocess.run")
    def test_install_fails_when_schtasks_errors(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="Access denied")
        scheduler = WindowsScheduler()
        result = scheduler.install(Path("C:/skills"), interval_minutes=5, target="both")
        self.assertFalse(result)


class TestSchedulerUninstall(unittest.TestCase):
    """Scheduler uninstallation tests."""

    @patch("subprocess.run")
    def test_uninstall_deletes_task(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        scheduler = WindowsScheduler()
        result = scheduler.uninstall()
        self.assertTrue(result)
        calls = [c for c in mock_run.call_args_list if "/delete" in str(c)]
        self.assertEqual(len(calls), 1)
        self.assertIn(_TASK_NAME, str(calls[0]))

    @patch("subprocess.run")
    def test_uninstall_succeeds_when_task_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: The system cannot find")
        scheduler = WindowsScheduler()
        result = scheduler.uninstall()
        self.assertTrue(result)


class TestSchedulerStatus(unittest.TestCase):
    """Scheduler status query tests."""

    @patch("subprocess.run")
    def test_is_installed_when_task_exists(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="TaskName: SkillsBridgeSync")
        scheduler = WindowsScheduler()
        self.assertTrue(scheduler.is_installed())

    @patch("subprocess.run")
    def test_is_not_installed_when_task_missing(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: The system cannot find")
        scheduler = WindowsScheduler()
        self.assertFalse(scheduler.is_installed())

    @patch("subprocess.run")
    def test_get_info_returns_dict(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="TaskName: SkillsBridgeSync\nNext Run Time: 2026/5/10 12:00:00",
        )
        scheduler = WindowsScheduler()
        info = scheduler.get_info()
        self.assertIsInstance(info, dict)
        self.assertIn("installed", info)
        self.assertTrue(info["installed"])
        self.assertIn("raw", info)

    @patch("subprocess.run")
    def test_get_info_when_not_installed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: Task not found")
        scheduler = WindowsScheduler()
        info = scheduler.get_info()
        self.assertFalse(info["installed"])


class TestPublicApi(unittest.TestCase):
    """Public API compatibility tests."""

    @patch("src.scheduler._get_scheduler_class")
    def test_install_scheduler_uses_backend(self, mock_get_class):
        mock_backend = MagicMock()
        mock_backend.return_value.install.return_value = True
        mock_get_class.return_value = mock_backend

        result = install_scheduler(Path("/tmp/skills"), interval_minutes=5, target="both")
        self.assertTrue(result)
        mock_backend.return_value.install.assert_called_once()

    @patch("src.scheduler._get_scheduler_class")
    def test_uninstall_scheduler_uses_backend(self, mock_get_class):
        mock_backend = MagicMock()
        mock_backend.return_value.uninstall.return_value = True
        mock_get_class.return_value = mock_backend

        result = uninstall_scheduler()
        self.assertTrue(result)
        mock_backend.return_value.uninstall.assert_called_once()

    @patch("src.scheduler._get_scheduler_class")
    def test_is_scheduler_installed_uses_backend(self, mock_get_class):
        mock_backend = MagicMock()
        mock_backend.return_value.is_installed.return_value = False
        mock_get_class.return_value = mock_backend

        result = is_scheduler_installed()
        self.assertFalse(result)

    @patch("src.scheduler._get_scheduler_class")
    def test_get_scheduler_info_uses_backend(self, mock_get_class):
        mock_backend = MagicMock()
        mock_backend.return_value.get_info.return_value = {"installed": True}
        mock_get_class.return_value = mock_backend

        result = get_scheduler_info()
        self.assertTrue(result["installed"])


class TestTaskName(unittest.TestCase):
    def test_task_name_is_constant(self):
        self.assertEqual(_TASK_NAME, "SkillsBridgeSync")


if __name__ == "__main__":
    unittest.main()
