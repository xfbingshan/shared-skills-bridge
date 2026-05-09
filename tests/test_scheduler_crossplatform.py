"""Tests for cross-platform scheduler backends."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.scheduler import (
    LinuxCronScheduler,
    MacOSScheduler,
    WindowsScheduler,
    _get_scheduler_class,
)


class TestSchedulerDispatch(unittest.TestCase):
    """Platform dispatch tests."""

    @patch("platform.system", return_value="Windows")
    def test_windows_returns_windows_scheduler(self, _mock):
        cls = _get_scheduler_class()
        self.assertIs(cls, WindowsScheduler)

    @patch("platform.system", return_value="Darwin")
    def test_darwin_returns_macos_scheduler(self, _mock):
        cls = _get_scheduler_class()
        self.assertIs(cls, MacOSScheduler)

    @patch("platform.system", return_value="Linux")
    def test_linux_returns_linux_scheduler(self, _mock):
        cls = _get_scheduler_class()
        self.assertIs(cls, LinuxCronScheduler)


class TestMacOSScheduler(unittest.TestCase):
    """macOS launchd scheduler tests."""

    def setUp(self):
        self.scheduler = MacOSScheduler()

    @patch("subprocess.run")
    def test_install_creates_plist_and_loads(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()
            result = self.scheduler.install(source, interval_minutes=10, target="both")

        self.assertTrue(result)
        calls = mock_run.call_args_list
        load_calls = [c for c in calls if "launchctl" in str(c) and "load" in str(c)]
        self.assertEqual(len(load_calls), 1)
        # Should contain the plist path
        self.assertIn("com.skillsbridge.sync.plist", str(load_calls[0]))

    @patch("subprocess.run")
    def test_uninstall_unloads_and_removes_plist(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = self.scheduler.uninstall()
        self.assertTrue(result)
        calls = mock_run.call_args_list
        unload_calls = [c for c in calls if "unload" in str(c)]
        self.assertEqual(len(unload_calls), 1)

    @patch("subprocess.run")
    def test_is_installed_checks_plist_exists(self, mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            plist = Path(tmpdir) / "com.skillsbridge.sync.plist"
            plist.write_text("<plist/>", encoding="utf-8")
            scheduler = MacOSScheduler()
            scheduler._plist_path = lambda: plist
            self.assertTrue(scheduler.is_installed())

    @patch("subprocess.run")
    def test_is_not_installed_when_plist_missing(self, mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            plist = Path(tmpdir) / "com.skillsbridge.sync.plist"
            scheduler = MacOSScheduler()
            scheduler._plist_path = lambda: plist
            self.assertFalse(scheduler.is_installed())


class TestLinuxCronScheduler(unittest.TestCase):
    """Linux cron scheduler tests."""

    def setUp(self):
        self.scheduler = LinuxCronScheduler()

    @patch("subprocess.run")
    def test_install_adds_crontab_entry(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()
            result = self.scheduler.install(source, interval_minutes=5, target="both")

        self.assertTrue(result)
        # Should call crontab with new content containing our marker
        calls = mock_run.call_args_list
        crontab_calls = [c for c in calls if "crontab" in str(c)]
        self.assertTrue(len(crontab_calls) > 0)

    @patch("subprocess.run")
    def test_uninstall_removes_crontab_entry(self, mock_run):
        # Simulate existing crontab with our entry
        existing = (
            "0 9 * * * echo hello\n"
            "# === SkillsBridgeSync start ===\n"
            "*/5 * * * * python /app/scripts/install.py\n"
            "# === SkillsBridgeSync end ===\n"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=existing),  # crontab -l
            MagicMock(returncode=0),                     # crontab -
        ]
        result = self.scheduler.uninstall()
        self.assertTrue(result)
        # The install call should have our lines stripped
        write_call = [c for c in mock_run.call_args_list if "-" in str(c) and "crontab" in str(c)]
        self.assertTrue(len(write_call) > 0)
        written = write_call[-1][1]["input"]
        self.assertNotIn("SkillsBridgeSync", written)
        self.assertIn("echo hello", written)

    @patch("subprocess.run")
    def test_is_installed_when_marker_present(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="# === SkillsBridgeSync start ===")
        self.assertTrue(self.scheduler.is_installed())

    @patch("subprocess.run")
    def test_is_not_installed_when_marker_absent(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="0 9 * * * echo hello")
        self.assertFalse(self.scheduler.is_installed())

    @patch("subprocess.run")
    def test_install_is_idempotent(self, mock_run):
        """Installing twice should not duplicate entries."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # first crontab -l
            MagicMock(returncode=0),              # first crontab -
            MagicMock(returncode=0, stdout="# === SkillsBridgeSync start ===\n*/5 * * * * cmd\n# === SkillsBridgeSync end ==="),
            MagicMock(returncode=0),              # second crontab -
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "shared-skills"
            source.mkdir()
            self.scheduler.install(source, interval_minutes=5, target="both")
            self.scheduler.install(source, interval_minutes=5, target="both")

        # Second install should replace, not duplicate
        calls = mock_run.call_args_list
        write_calls = [c for c in calls if c[0][0][1] == "-"]
        # Only 2 writes total (first install + second install)
        self.assertEqual(len(write_calls), 2)


class TestWindowsSchedulerStillWorks(unittest.TestCase):
    """Ensure Windows scheduler is preserved after refactoring."""

    @patch("subprocess.run")
    def test_windows_install_uses_schtasks(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        scheduler = WindowsScheduler()
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "skills"
            source.mkdir()
            result = scheduler.install(source, interval_minutes=5, target="both")

        self.assertTrue(result)
        calls = [c for c in mock_run.call_args_list if "/create" in str(c)]
        self.assertEqual(len(calls), 1)
        self.assertIn("SkillsBridgeSync", str(calls[0]))


if __name__ == "__main__":
    unittest.main()
