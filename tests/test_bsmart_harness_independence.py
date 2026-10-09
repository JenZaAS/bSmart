from __future__ import annotations

import os
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "scripts" / "bsmart-project-integration-check"
UPDATE = ROOT / "scripts" / "bsmart-update"
STARTUP = ROOT / "scripts" / "bsmart-startup-check"
STORAGE = ROOT / "scripts" / "bsmart-project-storage-check"
CONTENT_ROOT_SCRIPTS = (
    "bsmart-startup-check",
    "bsmart-system-update-check",
    "bsmart-content-upgrade",
    "bsmart-release-notice",
    "bsmart-project-storage-check",
)


def isolated_env(home: Path, path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PATH"] = path
    env.pop("HERMES_HOME", None)
    env.pop("BSMART_WORKSPACE_ROOT", None)
    env.pop("BSMART_PROJECT_ROOT", None)
    env.pop("BSMART_SANDBOX_ROOT", None)
    return env


class HermesIntegrationTests(unittest.TestCase):
    def test_absent_hermes_is_skipped_without_creating_a_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "hermes-home"
            env = isolated_env(root / "user-home", "/usr/bin:/bin")
            result = subprocess.run(
                [sys.executable, str(INTEGRATION), "--install", "--hermes-home", str(home)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("skipped", result.stdout)
            self.assertIn("not applicable", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(home.exists())
            self.assertFalse((root / "user-home" / ".hermes").exists())

    def test_present_hermes_cli_still_installs_and_enables(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log = root / "hermes.log"
            hermes = bin_dir / "hermes"
            hermes.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$HERMES_LOG\"\nexit 0\n",
                encoding="utf-8",
            )
            hermes.chmod(hermes.stat().st_mode | stat.S_IEXEC)
            node = shutil.which("node")
            self.assertIsNotNone(node)
            node_dir = str(Path(node).resolve().parent)
            home = root / "hermes-home"
            env = isolated_env(root / "user-home", f"{bin_dir}:{node_dir}:/usr/bin:/bin")
            env["HERMES_LOG"] = str(log)
            result = subprocess.run(
                [sys.executable, str(INTEGRATION), "--install", "--quiet", "--hermes-home", str(home)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((home / "plugins" / "bsmart-project" / "plugin.yaml").is_file())
            self.assertTrue((home / "plugins" / "bsmart-project" / "__init__.py").is_file())
            self.assertIn("plugins enable bsmart-project", log.read_text(encoding="utf-8"))

    def test_profile_without_cli_does_not_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "hermes-home"
            home.mkdir()
            (home / "config.yaml").write_text("model: local\n", encoding="utf-8")
            node = shutil.which("node")
            self.assertIsNotNone(node)
            node_dir = str(Path(node).resolve().parent)
            env = isolated_env(root / "user-home", f"{node_dir}:/usr/bin:/bin")
            result = subprocess.run(
                [sys.executable, str(INTEGRATION), "--install", "--hermes-home", str(home)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("hermes CLI is not on PATH", result.stdout)


class UpdateAndStartupTests(unittest.TestCase):
    def test_update_finishes_when_hermes_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            os.symlink(ROOT, workspace / "bSmart-System")
            env = isolated_env(root / "home", "/usr/bin:/bin")
            result = subprocess.run(
                [sys.executable, str(UPDATE), "--workspace", str(workspace)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("bSmart update: complete", result.stdout)
            self.assertNotIn("blocked", result.stdout)
            self.assertNotIn("restart Hermes", result.stdout)
            self.assertIn("python3 bSmart-System/bStart.py", (workspace / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertFalse((root / "home" / ".hermes").exists())
            self.assertTrue((workspace / "bSmart" / "bHistory.md").is_file())

    def test_startup_check_skips_hermes_without_a_python_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            for name in (
                "bsmart-startup-check",
                "bsmart-content-upgrade",
                "bsmart-release-notice",
                "bsmart-project-integration-check",
            ):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            templates = system / "bSmart_Templates"
            templates.mkdir()
            shutil.copy2(ROOT / "bSmart_Templates" / "bHistory.template.md", templates / "bHistory.template.md")
            shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
            (root / "bSmart").mkdir()
            env = isolated_env(root / "home", "/usr/bin:/bin")
            result = subprocess.run(
                [
                    sys.executable,
                    str(scripts / "bsmart-startup-check"),
                    "--skip-system-update",
                    "--skip-project-storage",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("skipped", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("FileNotFoundError", result.stderr)
            self.assertFalse((root / "home" / ".hermes").exists())


class ProjectStorageTests(unittest.TestCase):
    def test_configure_internal_writes_local_spec_without_mount_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "bSmart" / "State" / "container-storage.yaml"
            env = isolated_env(root / "home", "/usr/bin:/bin")
            result = subprocess.run(
                [
                    sys.executable,
                    str(STORAGE),
                    "--workspace",
                    str(root),
                    "--spec",
                    str(spec),
                    "--configure-internal",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No host mount or Compose volume is required", result.stdout)
            self.assertNotIn("Compose/Dokploy volume", result.stdout)
            text = spec.read_text(encoding="utf-8")
            self.assertIn("mode: internal", text)
            self.assertIn("backing: workspace-local", text)
            self.assertIn(str((root / "projects").resolve()), text)
            self.assertTrue((root / "projects").is_dir())
            self.assertTrue((root / "sandboxes").is_dir())
            status = subprocess.run(
                [sys.executable, str(STORAGE), "--workspace", str(root), "--spec", str(spec)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(status.returncode, 0, status.stdout)
            self.assertIn("configured", status.stdout)

    def test_configure_internal_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "container-storage.yaml"
            spec.write_text("keep\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(STORAGE),
                    "--workspace",
                    str(root),
                    "--spec",
                    str(spec),
                    "--configure-internal",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(spec.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((root / "projects").exists())

    def test_missing_findmnt_skips_host_mount_inference(self):
        module = runpy.run_path(str(STORAGE))

        def missing(cmd: list[str]):
            raise FileNotFoundError(cmd[0])

        module["run"] = missing
        self.assertIsNone(module["infer_workspace_host_path"]())
        self.assertIsNone(module["infer_sandbox_host_path"]())


class ContentRootTests(unittest.TestCase):
    def test_sibling_content_root_wins_over_container_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            sibling = root / "bSmart"
            system.mkdir()
            sibling.mkdir()
            missing_parent = root / "elsewhere"
            missing_system = missing_parent / "bSmart-System"
            missing_system.mkdir(parents=True)
            for name in CONTENT_ROOT_SCRIPTS:
                module = runpy.run_path(str(ROOT / "scripts" / name))
                self.assertEqual(module["default_content_root"](system), sibling)
                # A checkout that is not the /workspace container keeps its own
                # sibling path even when that directory does not exist yet.
                self.assertEqual(module["default_content_root"](missing_system), missing_parent / "bSmart")


class TwoInstanceTests(unittest.TestCase):
    """A main instance and /agents/GrokAdmin must not share state files."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="bsmart-two-instances-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.container = Path("/workspace/bSmart")
        self.stray = Path("/bSmart")
        self.container_existed = self.container.exists()
        self.stray_existed = self.stray.exists()
        self.addCleanup(self.cleanup_strays)
        self.main = self.root / "workspace"
        self.nested = self.main / "agents" / "GrokAdmin"
        self.populate(symlink_system=True)

    def cleanup_strays(self):
        if not self.container_existed and self.container.exists():
            shutil.rmtree(self.container, ignore_errors=True)
        if not self.stray_existed and self.stray.exists():
            shutil.rmtree(self.stray, ignore_errors=True)

    def populate(self, symlink_system: bool) -> None:
        system = self.main / "bSmart-System"
        scripts = system / "scripts"
        scripts.mkdir(parents=True)
        for name in (
            "bsmart-system-update-check",
            "bsmart-startup-check",
            "bsmart-content-upgrade",
            "bsmart-release-notice",
            "bsmart-project-integration-check",
            "bsmart-project-storage-check",
        ):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        templates = system / "bSmart_Templates"
        templates.mkdir()
        shutil.copy2(ROOT / "bSmart_Templates" / "bHistory.template.md", templates / "bHistory.template.md")
        shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
        shutil.copy2(ROOT / "bStart.py", system / "bStart.py")
        shutil.copy2(ROOT / "bStart.py", self.main / "bStart.py")
        self.write_agent(self.main / "bSmart", "MainAgent", "Main User")
        (self.main / "bSmart" / "sentinel.txt").write_text("main\n", encoding="utf-8")
        self.nested.mkdir(parents=True)
        if symlink_system:
            os.symlink(system, self.nested / "bSmart-System")
        else:
            shutil.copytree(system, self.nested / "bSmart-System")
        shutil.copy2(ROOT / "bStart.py", self.nested / "bStart.py")
        self.write_agent(self.nested / "bSmart", "GrokAdmin", "Nested User")

    def write_agent(self, content: Path, name: str, operator: str) -> None:
        content.mkdir(parents=True, exist_ok=True)
        (content / "bSmart_Agent.md").write_text(
            f"# Agent\n\n```yaml\nagent:\n  name: {name}\n  operator: {operator}\n```\n",
            encoding="utf-8",
        )

    def env(self) -> dict[str, str]:
        home = self.root / "home"
        home.mkdir(exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = "/usr/bin:/bin"
        env.pop("HERMES_HOME", None)
        return env

    def assert_main_untouched(self) -> None:
        state = self.main / "bSmart" / "State"
        self.assertFalse((state / "bsmart-system-update.yaml").exists())
        self.assertFalse((state / "bsmart-startup-check.yaml").exists())
        self.assertFalse((state / "bsmart-release-notice.yaml").exists())
        self.assertFalse((self.main / "bSmart" / "bHistory.md").exists())
        self.assertFalse((self.main / "bSmart" / "Roles").exists())
        self.assertEqual((self.main / "bSmart" / "sentinel.txt").read_text(encoding="utf-8"), "main\n")
        self.assertFalse((self.stray / "State" / "bsmart-system-update.yaml").exists())
        if not self.container_existed:
            self.assertFalse((self.container / "State" / "bsmart-system-update.yaml").exists())

    def test_both_bstart_entry_points_cache_only_in_the_nested_instance(self):
        env = self.env()
        for script in (self.nested / "bStart.py", self.nested / "bSmart-System" / "bStart.py"):
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=self.nested,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Agent: GrokAdmin", result.stdout)
            self.assertNotIn("Agent: MainAgent", result.stdout)
            self.assertTrue((self.nested / "bSmart" / "State" / "bsmart-system-update.yaml").is_file(), result.stdout)
            self.assert_main_untouched()

    def test_direct_update_check_through_system_symlink_uses_nested_content(self):
        result = subprocess.run(
            [sys.executable, str(self.nested / "bSmart-System" / "scripts" / "bsmart-system-update-check")],
            cwd=self.nested,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
        )
        self.assertTrue(
            (self.nested / "bSmart" / "State" / "bsmart-system-update.yaml").is_file(),
            result.stdout + result.stderr,
        )
        self.assert_main_untouched()

    def test_startup_check_through_system_symlink_writes_only_nested_state(self):
        result = subprocess.run(
            [
                sys.executable,
                str(self.nested / "bSmart-System" / "scripts" / "bsmart-startup-check"),
                "--skip-project-integration",
            ],
            cwd=self.nested,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
        )
        nested_state = self.nested / "bSmart" / "State"
        self.assertTrue((nested_state / "bsmart-startup-check.yaml").is_file(), result.stdout + result.stderr)
        self.assertTrue((nested_state / "bsmart-system-update.yaml").is_file(), result.stdout + result.stderr)
        self.assertTrue((nested_state / "bsmart-release-notice.yaml").is_file(), result.stdout + result.stderr)
        self.assertTrue((self.nested / "bSmart" / "bHistory.md").is_file())
        self.assert_main_untouched()

    def test_separate_system_checkout_does_not_write_the_main_instance(self):
        shutil.rmtree(self.nested)
        self.nested.mkdir(parents=True)
        shutil.copytree(self.main / "bSmart-System", self.nested / "bSmart-System")
        shutil.copy2(ROOT / "bStart.py", self.nested / "bStart.py")
        self.write_agent(self.nested / "bSmart", "GrokAdmin", "Nested User")
        result = subprocess.run(
            [sys.executable, str(self.nested / "bSmart-System" / "bStart.py")],
            cwd=self.nested,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Agent: GrokAdmin", result.stdout)
        self.assertTrue((self.nested / "bSmart" / "State" / "bsmart-system-update.yaml").is_file())
        self.assert_main_untouched()


if __name__ == "__main__":
    unittest.main()
