import json
import subprocess
import unittest
from unittest.mock import patch

from windows_tools import launch_regedit, powershell_process_snapshot, registry_demo, tool_status, wmi_process_snapshot


def completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


class WindowsToolTests(unittest.TestCase):
    @patch("windows_tools._require_windows")
    @patch("windows_tools.shutil.which", return_value=r"C:\Windows\regedit.exe")
    @patch("windows_tools.os.startfile", create=True)
    def test_regedit_requests_uac_without_elevating_server(self, startfile, which, require):
        result = launch_regedit()
        startfile.assert_called_once_with(r"C:\Windows\regedit.exe", "runas")
        self.assertEqual(result["status"], "launched")

    def test_tool_status_reports_three_guided_labs(self):
        tools = tool_status()
        self.assertEqual([tool["id"] for tool in tools], ["powershell", "wmi", "registry"])

    @patch("windows_tools._run")
    def test_powershell_snapshot_normalizes_thread_count(self, run_mock):
        run_mock.return_value = completed(
            json.dumps(
                {
                    "Id": 42,
                    "ProcessName": "python",
                    "Threads": [{"Id": 1}, {"Id": 2}],
                    "Handles": 80,
                    "WorkingSet64": 4096,
                }
            )
        )
        result = powershell_process_snapshot(42)
        self.assertEqual(result["target_pid"], 42)
        self.assertEqual(result["data"]["ThreadCount"], 2)
        self.assertNotIn("Threads", result["data"])

    @patch("windows_tools._run")
    def test_wmi_snapshot_identifies_win32_process(self, run_mock):
        run_mock.return_value = completed(json.dumps({"ProcessId": 42, "Name": "python.exe"}))
        result = wmi_process_snapshot(42)
        self.assertEqual(result["class"], "Win32_Process")
        self.assertEqual(result["data"]["ProcessId"], 42)

    @patch("windows_tools._run")
    def test_registry_demo_uses_project_owned_hkcu_key(self, run_mock):
        run_mock.side_effect = [completed(), completed(), completed(), completed("HKCU\\Software\\SyncScopeLab")]
        result = registry_demo(42)
        self.assertEqual(result["registry_key"], r"HKCU\Software\SyncScopeLab")
        self.assertEqual(result["values"]["TargetPID"], "42")
        self.assertEqual(run_mock.call_count, 4)


if __name__ == "__main__":
    unittest.main()
