from __future__ import annotations

import os
import shutil
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

    def test_workspace_root_and_system_copies_resolve_the_same_workspace(self):
        workspace = self.make_workspace()
        system = workspace / "bSmart-System"
        helper = system / "scripts" / "bsmart-system-update-check"
        helper.parent.mkdir(parents=True)
        helper.write_text(
            "#!/usr/bin/env python3\nprint('bSmart system update check: up to date')\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=system, check=True)
        shutil = __import__("shutil")
        shutil.copy(START, system / "bStart.py")
        shutil.copy(START, workspace / "bStart.py")
        env = dict(__import__("os").environ)
        env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
        for script in (workspace / "bStart.py", system / "bStart.py"):
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(workspace.parent),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                env=env,
            )
            self.assertEqual(result.stderr, "")
            self.assertIn("Agent: TestAgent", result.stdout)
            self.assertNotIn("bSmart-System: no Git repository", result.stdout)
            self.assertNotIn("update helper unavailable", result.stdout)
            self.assertIn("bSmart system update check: up to date", result.stdout)

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

    def test_startup_uses_the_storage_spec_when_env_is_unset(self):
        workspace = self.make_workspace()
        spec_root = workspace / "from-spec"
        (spec_root / "Demo").mkdir(parents=True)
        (spec_root / "Demo" / "project.md").write_text("# From spec\n", encoding="utf-8")
        (workspace / "projects" / "Demo" / "project.md").write_text("# Stale local\n", encoding="utf-8")
        spec = workspace / "bSmart" / "State" / "container-storage.yaml"
        spec.parent.mkdir(parents=True)
        spec.write_text("project_storage:\n  project_root: ./from-spec\n", encoding="utf-8")
        role_dir = workspace / "bSmart" / "Roles"
        role_dir.mkdir()
        (role_dir / "current_role.md").write_text(
            "```yaml\nrole_selection:\n  current_role: developer\n```\n", encoding="utf-8"
        )
        (role_dir / "developer_role.md").write_text(
            "```yaml\nstate:\n  active_project: Demo\n  active_workstream: none\n```\n", encoding="utf-8"
        )
        env = dict(__import__("os").environ)
        env.pop("BSMART_PROJECT_ROOT", None)
        result = subprocess.run(
            [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# From spec", result.stdout)
        self.assertNotIn("# Stale local", result.stdout)

    def test_cp1252_stdout_prints_characters_outside_that_code_page(self):
        workspace = self.make_workspace()
        marker = "\u2610"
        agent = workspace / "bSmart" / "bSmart_Agent.md"
        agent.write_text(agent.read_text(encoding="utf-8") + f"\n{marker} open item\n", encoding="utf-8")
        system = workspace / "bSmart-System"
        system.mkdir()
        shutil.copy(START, system / "bStart.py")
        shutil.copy(START, workspace / "bStart.py")
        env = dict(os.environ)
        env.pop("PYTHONUTF8", None)
        env["PYTHONUTF8"] = "0"
        env["PYTHONIOENCODING"] = "cp1252:strict"
        env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
        for script in (START, system / "bStart.py", workspace / "bStart.py"):
            result = subprocess.run(
                [sys.executable, str(script), "--root", str(workspace), "--skip-update", "--skip-integrity"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(workspace),
                check=False,
            )
            stderr = result.stderr.decode("utf-8", "replace")
            self.assertEqual(result.returncode, 0, stderr)
            self.assertNotIn("UnicodeEncodeError", stderr)
            stdout = result.stdout.decode("utf-8")
            self.assertIn(marker, stdout)
            self.assertIn(f"{marker} open item", stdout)


if __name__ == "__main__":
    unittest.main()
