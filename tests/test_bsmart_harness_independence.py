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


COPIED_WITH_INSTANCE = (
    "bsmart_instance.py",
    "bsmart-startup-check",
    "bsmart-system-update-check",
    "bsmart-content-upgrade",
    "bsmart-release-notice",
    "bsmart-project-integration-check",
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


def tool_path(*front: Path) -> str:
    """Keep git and the system tools, and leave a real hermes binary out."""
    parts = [str(path) for path in front]
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        folder = Path(directory)
        if any((folder / name).exists() for name in ("hermes", "hermes.exe", "hermes.cmd", "hermes.bat")):
            continue
        parts.append(directory)
    return os.pathsep.join(parts)


def write_fake_hermes(bin_dir: Path) -> None:
    """Hermes stand-in: a Python script, plus a cmd shim on Windows."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    body = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "log = os.environ.get('HERMES_LOG')\n"
        "if log:\n"
        "    with Path(log).open('a', encoding='utf-8') as handle:\n"
        "        handle.write(' '.join(sys.argv[1:]) + '\\n')\n"
        "raise SystemExit(0)\n"
    )
    if os.name == "nt":
        (bin_dir / "hermes.py").write_text(body, encoding="utf-8")
        (bin_dir / "hermes.cmd").write_text(
            f'@echo off\r\n"{sys.executable}" "%~dp0hermes.py" %*\r\n',
            encoding="utf-8",
        )
        return
    launcher = bin_dir / "hermes"
    launcher.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)


def node_dir(test: unittest.TestCase) -> str:
    node = shutil.which("node")
    if not node:
        test.skipTest("node is not installed")
    return str(Path(node).resolve().parent)


class HermesIntegrationTests(unittest.TestCase):
    def test_absent_hermes_is_skipped_without_creating_a_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "hermes-home"
            env = isolated_env(root / "user-home", tool_path())
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
            log = root / "hermes.log"
            write_fake_hermes(bin_dir)
            home = root / "hermes-home"
            env = isolated_env(root / "user-home", tool_path(bin_dir, Path(node_dir(self))))
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
            env = isolated_env(root / "user-home", tool_path())
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
            self.assertFalse((home / "plugins" / "bsmart-project" / "plugin.yaml").exists())

    def test_enabled_current_adapter_without_cli_stays_successful(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "hermes-home"
            plugin = home / "plugins" / "bsmart-project"
            plugin.mkdir(parents=True)
            source = ROOT / "integrations" / "hermes" / "bsmart-project-plugin"
            for name in ("plugin.yaml", "__init__.py"):
                shutil.copy2(source / name, plugin / name)
            (home / "config.yaml").write_text(
                "plugins:\n  enabled:\n    - bsmart-project\n",
                encoding="utf-8",
            )
            env = isolated_env(root / "user-home", tool_path(Path(node_dir(self))))
            result = subprocess.run(
                [sys.executable, str(INTEGRATION), "--install", "--hermes-home", str(home)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("setup_blocked", result.stdout)
            self.assertEqual((plugin / "plugin.yaml").read_bytes(), (source / "plugin.yaml").read_bytes())

    def test_windows_hermes_command_is_a_single_comspec_string(self):
        module = runpy.run_path(str(INTEGRATION))
        hermes = r"C:\Users\Erling Jensen\bin\hermes.cmd"
        comspec = r"C:\Windows\System32\cmd.exe"
        command = module["windows_hermes_command"](
            hermes, ["plugins", "enable", "bsmart-project"], comspec
        )
        self.assertIsInstance(command, str)
        self.assertIn("/d /s /c", command)
        self.assertIn("Erling Jensen", command)
        self.assertNotIn('\\"', command)
        self.assertTrue(command.startswith(f'"{comspec}"'))

    @unittest.skipUnless(os.name == "nt", "cmd.exe quoting is Windows-specific")
    def test_install_enables_when_hermes_directory_contains_a_space(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "Erling Jensen" / "bin"
            log = root / "hermes.log"
            write_fake_hermes(bin_dir)
            home = root / "hermes-home"
            env = isolated_env(root / "user-home", tool_path(bin_dir, Path(node_dir(self))))
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
            self.assertIn("plugins enable bsmart-project", log.read_text(encoding="utf-8"))

    def test_spec_project_root_beats_a_stale_mount(self):
        module = runpy.run_path(str(ROOT / "scripts" / "bsmart_instance.py"))
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            spec_projects = workspace / "from-spec"
            local = workspace / "projects"
            mounted = workspace / "mounted-projects"
            for path in (spec_projects, local, mounted):
                path.mkdir()
            spec = workspace / "bSmart" / "State" / "container-storage.yaml"
            spec.parent.mkdir(parents=True)
            spec.write_text("project_storage:\n  project_root: ./from-spec\n", encoding="utf-8")
            selected = module["select_instance_project_root"](
                workspace, environ={}, spec_path=spec, mounted=mounted
            )
            self.assertEqual(selected, spec_projects.resolve())
            env_choice = workspace / "from-env"
            env_choice.mkdir()
            selected = module["select_instance_project_root"](
                workspace,
                environ={"BSMART_PROJECT_ROOT": str(env_choice)},
                spec_path=spec,
                mounted=mounted,
            )
            self.assertEqual(selected, env_choice.resolve())


class UpdateAndStartupTests(unittest.TestCase):
    def test_update_finishes_when_hermes_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            link = workspace / "bSmart-System"
            try:
                os.symlink(ROOT, link, target_is_directory=True)
            except OSError:
                shutil.copytree(ROOT, link, symlinks=True)
            env = isolated_env(root / "home", tool_path())
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
            hook = (workspace / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("python3 bSmart-System/bStart.py", hook)
            self.assertIn("py -3 bSmart-System/bStart.py", hook)
            self.assertNotIn("not on PATH", hook)
            self.assertFalse((root / "home" / ".hermes").exists())
            self.assertTrue((workspace / "bSmart" / "bHistory.md").is_file())

    def test_startup_check_skips_hermes_without_a_python_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            for name in (
                "bsmart_instance.py",
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
            env = isolated_env(root / "home", tool_path())
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
            env = isolated_env(root / "home", tool_path())
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
            self.assertIn("path_in_container: ./projects", text)
            self.assertIn("path_in_container: ./sandboxes", text)
            self.assertNotIn(str((root / "projects").resolve()), text)
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

        # runpy returns a copy of the module dict, so patch the function globals.
        module["infer_workspace_host_path"].__globals__["run"] = missing
        self.assertIsNone(module["infer_workspace_host_path"]())
        self.assertIsNone(module["infer_sandbox_host_path"]())

    def test_relative_spec_resolves_against_the_workspace_at_read_time(self):
        module = runpy.run_path(str(STORAGE))
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "instance"
            recorded = module["resolve_recorded_path"](workspace, "./projects")
            self.assertEqual(recorded, (workspace / "projects").absolute())
            absolute = (Path(directory) / "fixed-projects").absolute()
            self.assertEqual(module["resolve_recorded_path"](workspace, str(absolute)), absolute)

    def test_absolute_spec_is_selected_when_relative_projects_are_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            projects = root / "fixed-projects"
            sandboxes = root / "fixed-sandboxes"
            projects.mkdir()
            sandboxes.mkdir()
            spec = workspace / "bSmart" / "State" / "container-storage.yaml"
            spec.parent.mkdir(parents=True)
            spec.write_text(
                "project_storage:\n"
                f"  project_root: {projects.as_posix()}\n"
                "sandbox_storage:\n"
                f"  sandbox_root: {sandboxes.as_posix()}\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(STORAGE), "--workspace", str(workspace), "--spec", str(spec)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=isolated_env(root / "home", tool_path()),
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(str(projects.absolute()), result.stdout)
            self.assertIn(str(sandboxes.absolute()), result.stdout)


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

    def test_update_workspace_prefers_the_checkout_over_another_container(self):
        module = runpy.run_path(str(ROOT / "scripts" / "bsmart_instance.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            container = root / "container"
            (container / "bSmart-System" / "scripts").mkdir(parents=True)
            checkout = root / "agents" / "GrokAdmin"
            system = checkout / "bSmart-System"
            system.mkdir(parents=True)
            self.assertEqual(module["workspace_for_system"](system, container), checkout)
            orphan = root / "loose"
            orphan.mkdir()
            self.assertEqual(module["workspace_for_system"](orphan, container), container)

    def test_update_workspace_keeps_a_symlinked_checkout_with_its_instance(self):
        module = runpy.run_path(str(ROOT / "scripts" / "bsmart_instance.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            container = root / "container"
            (container / "bSmart-System").mkdir(parents=True)
            system = root / "real" / "bSmart-System"
            system.mkdir(parents=True)
            launched = root / "instance" / "bSmart-System"
            launched.parent.mkdir()
            try:
                os.symlink(system, launched, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            self.assertEqual(module["workspace_for_system"](launched, container), launched.parent)


class TwoInstanceTests(unittest.TestCase):
    """A main instance and /agents/GrokAdmin must not share state files."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="bsmart-two-instances-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.main = self.root / "workspace"
        self.nested = self.main / "agents" / "GrokAdmin"
        self.populate_main()

    def populate_main(self) -> None:
        system = self.main / "bSmart-System"
        scripts = system / "scripts"
        scripts.mkdir(parents=True)
        for name in COPIED_WITH_INSTANCE:
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        templates = system / "bSmart_Templates"
        templates.mkdir()
        shutil.copy2(ROOT / "bSmart_Templates" / "bHistory.template.md", templates / "bHistory.template.md")
        shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
        shutil.copy2(ROOT / "bStart.py", system / "bStart.py")
        shutil.copy2(ROOT / "bStart.py", self.main / "bStart.py")
        self.write_agent(self.main / "bSmart", "MainAgent", "Main User")
        (self.main / "bSmart" / "sentinel.txt").write_text("main\n", encoding="utf-8")

    def link_nested(self) -> None:
        self.nested.mkdir(parents=True)
        try:
            os.symlink(self.main / "bSmart-System", self.nested / "bSmart-System", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks are unavailable: {exc}")
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
        env["PATH"] = tool_path()
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

    def test_both_bstart_entry_points_cache_only_in_the_nested_instance(self):
        self.link_nested()
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
        self.link_nested()
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
        self.link_nested()
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
        if self.nested.exists():
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
