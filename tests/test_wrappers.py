import os
import shutil
import subprocess
import unittest
from pathlib import Path

class LauncherTests(unittest.TestCase):
    def test_bash_launcher_finds_a_working_python_even_when_python3_is_a_windows_alias(self):
        root = Path(__file__).resolve().parents[1]
        if os.name == "nt":
            git = shutil.which("git")
            candidate = Path(git).resolve().parents[1] / "bin/bash.exe" if git else None
            bash = str(candidate) if candidate and candidate.is_file() else None
        else:
            bash = shutil.which("bash")
        if not bash:
            self.skipTest("Bash is not installed; actual Cloud/Linux launch remains unverified here.")
        result = subprocess.run([bash, str(root / "collab.sh"), "--help"],
                                cwd=root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("start", result.stdout)
        self.assertIn("publish", result.stdout)

    def test_powershell_launcher_forwards_cli_arguments(self):
        root = Path(__file__).resolve().parents[1]
        shell = shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)
        if not shell:
            self.skipTest("PowerShell not installed on this host.")
        result = subprocess.run([shell, "-NoProfile", "-File", str(root / "collab.ps1"), "--help"],
                                cwd=root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("start", result.stdout)
        self.assertIn("publish", result.stdout)

if __name__ == "__main__":
    unittest.main()
