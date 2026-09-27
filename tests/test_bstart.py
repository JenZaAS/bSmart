from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "bStart.py"


class BStartTests(unittest.TestCase):
    def run_start(self, workspace: Path) -> str:
        env = dict(__import__("os").environ)
        env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
        result = subprocess.run(
            [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=env,
        )
        self.assertEqual(result.stderr, "")
        return result.stdout

    def make_workspace(self, with_projects: bool = True) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="bsmart-start-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(temp, ignore_errors=True))
        content = temp / "bSmart"
        content.mkdir()
        (content / "bSmart_Agent.md").write_text(
            "# Agent\n\n```yaml\nagent:\n  name: TestAgent\n  operator: Test User\n```\n",
            encoding="utf-8",
        )
        if with_projects:
            projects = temp / "projects"
            (projects / "Demo").mkdir(parents=True)
            (projects / "Demo" / "project.md").write_text("# Demo\n", encoding="utf-8")
        return temp

    def test_bootstraps_general_role_and_selector(self):
        workspace = self.make_workspace()
        output = self.run_start(workspace)
        roles = workspace / "bSmart" / "Roles"
        self.assertTrue((roles / "current_role.md").is_file())
        self.assertTrue((roles / "general_role.md").is_file())
        self.assertIn("Hi, Test!", output)
        self.assertIn("Agent: TestAgent", output)
        self.assertIn("Role: General", output)
        self.assertIn("Project: none", output)
        self.assertIn("bSmart-Instance: no Git repository", output)

    def test_reports_project_mount_unavailable(self):
        workspace = self.make_workspace(with_projects=False)
        output = self.run_start(workspace)
        self.assertIn("Project: unavailable", output)
        self.assertIn("project mount appears to be down", output)

    def test_loads_selected_project_metadata(self):
        workspace = self.make_workspace()
        role_dir = workspace / "bSmart" / "Roles"
        role_dir.mkdir()
        (role_dir / "current_role.md").write_text(
            "```yaml\nrole_selection:\n  current_role: developer\n```\n", encoding="utf-8"
        )
        (role_dir / "developer_role.md").write_text(
            "```yaml\nstate:\n  active_project: Demo\n  active_workstream: Build\n```\n", encoding="utf-8"
        )
        output = self.run_start(workspace)
        self.assertIn("Role: Developer", output)
        self.assertIn("Project: Demo", output)
        self.assertIn("Workstream: Build", output)
        self.assertIn("project.md", output)
        self.assertIn("# Demo", output)


if __name__ == "__main__":
    unittest.main()
