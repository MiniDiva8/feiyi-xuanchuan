import json
import subprocess
import sys
import unittest
from pathlib import Path

class ThreeCloneSimulationTests(unittest.TestCase):
    def test_three_deliveries_integrate_and_new_task_reads_all_changes(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "scripts/simulate_team.py")],
                                cwd=root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["independent_clones"], 3)
        self.assertEqual(report["feature_branches_pushed"], 3)
        self.assertEqual(report["simulated_integrations"], 3)
        self.assertTrue(report["new_task_contains_all_changes"])
        self.assertTrue(report["intentional_conflict_blocked_without_changes"])
        self.assertFalse(report["github_prs_created"])
        self.assertFalse(report["cloud_accounts_tested"])
        self.assertTrue(report["temporary_directory_removed"])

if __name__ == "__main__":
    unittest.main()
