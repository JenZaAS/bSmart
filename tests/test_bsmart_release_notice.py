"""User-facing release news is announced once, including across skipped versions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICE = ROOT / "scripts" / "bsmart-release-notice"
UPGRADE = ROOT / "scripts" / "bsmart-instance-upgrade"
UPDATE = ROOT / "scripts" / "bsmart-update"
START = ROOT / "bStart.py"

ROLES_NEWS = (
    "Roles are gone. Each session starts in Free mode. Work happens in projects and "
    "workstreams, selected for this session with /project. Each project keeps its "
    "own handoff, which you write when switching away. projects/INDEX.md lists the "
    "projects. /role now only points to /project. Existing roles were migrated into "
    "project handoffs, and the old files were backed up under "
    ".bsmart-upgrade-backups/<timestamp>/roles-migration/. Leftover fields are in "
    "bSmart/State/role-migration-review.md. To restore the old files, run "
    "bsmart-instance-upgrade --restore-session-projects with that backup directory."
)

FIXTURE = """# fixture

```yaml
current_version: 0.1.4-draft
```

## 0.1.4-draft

```yaml
release_type: test
scope:
  - NOT-NEWS-CURRENT
```

## 0.1.3-draft

```yaml
release_type: test
news: |
  Second note about projects.
scope:
  - second scope
```

## 0.1.2-draft

```yaml
release_type: test
scope:
  - NOT-NEWS-MIDDLE
```

## 0.1.1-draft

```yaml
release_type: test
news: |
  First note about roles.
scope:
  - first scope
```

## 0.1.0-draft

```yaml
release_type: test
scope:
  - NOT-NEWS-OLD
```
"""


def write_state(content: Path, version: str, seen: list[str] | None = None) -> Path:
    state = content / "State" / "bsmart-release-notice.yaml"
    state.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"last_announced_version: {version}"]
    if seen:
        lines.append("seen_news:")
        lines.extend(f"  - {item}" for item in seen)
    else:
        lines.append("seen_news: []")
    state.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return state


def run_text(command: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Capture child output as UTF-8.

    Windows otherwise encodes an em dash in cp1252 (byte 0x97). Decoding that
    as strict UTF-8 drops stdout and hides the real assertion.
    """
    child = os.environ.copy() if env is None else env
    child["PYTHONIOENCODING"] = "utf-8"
    child["PYTHONUTF8"] = "1"
    return subprocess.run(
        command,
        cwd=None if cwd is None else str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=child,
        check=False,
    )


def tool_path() -> str:
    parts = []
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        folder = Path(directory)
        if any((folder / name).exists() for name in ("hermes", "hermes.exe", "hermes.cmd", "hermes.bat")):
            continue
        parts.append(directory)
    return os.pathsep.join(parts)


class ReleaseNoticeCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="bsmart-news-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.system = self.root / "bSmart-System"
        self.content = self.root / "bSmart"
        self.system.mkdir()
        self.content.mkdir()
        (self.system / "bSmart_Version.md").write_text(FIXTURE, encoding="utf-8")

    def run_notice(self, quiet: bool = True) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(NOTICE),
            "--content-root",
            str(self.content),
            "--system-root",
            str(self.system),
        ]
        if quiet:
            command.append("--quiet")
        return subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_skipped_versions_are_shown_once_oldest_first(self) -> None:
        write_state(self.content, "0.1.0-draft")
        first = self.run_notice()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stderr, "")
        self.assertIn("bSmart news:", first.stdout)
        self.assertIn("Relay this briefly to the user in your next reply. Say it once.", first.stdout)
        first_at = first.stdout.index("First note about roles.")
        second_at = first.stdout.index("Second note about projects.")
        self.assertLess(first_at, second_at)
        self.assertIn("0.1.1-draft:", first.stdout)
        self.assertIn("0.1.3-draft:", first.stdout)
        self.assertNotIn("NOT-NEWS-MIDDLE", first.stdout)
        self.assertNotIn("NOT-NEWS-CURRENT", first.stdout)
        self.assertNotIn("NOT-NEWS-OLD", first.stdout)
        self.assertNotIn("first scope", first.stdout)
        self.assertNotIn("second scope", first.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("last_announced_version: 0.1.4-draft", recorded)
        self.assertLess(recorded.index("0.1.1-draft"), recorded.index("0.1.3-draft"))
        self.assertNotIn("baseline: fresh", recorded)

        second = self.run_notice()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, "")
        self.assertNotIn("First note about roles.", second.stdout)
        self.assertNotIn("Second note about projects.", second.stdout)

    def test_no_repeat_after_the_news_has_been_seen(self) -> None:
        write_state(self.content, "0.1.4-draft", ["0.1.1-draft", "0.1.3-draft"])
        before = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        result = self.run_notice(quiet=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already announced", result.stdout)
        self.assertNotIn("First note about roles.", result.stdout)
        self.assertNotIn("Second note about projects.", result.stdout)
        self.assertNotIn("NOT-NEWS-CURRENT", result.stdout)
        self.assertEqual((self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"), before)

    def test_fresh_install_records_the_current_version_and_prints_nothing(self) -> None:
        result = self.run_notice(quiet=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("First note about roles.", result.stdout)
        self.assertNotIn("Second note about projects.", result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("last_announced_version: 0.1.4-draft", recorded)
        self.assertIn("seen_news: []", recorded)
        self.assertIn("baseline: fresh", recorded)
        again = self.run_notice()
        self.assertEqual(again.stdout, "")
        self.assertNotIn("First note about roles.", again.stdout)

    def test_non_news_version_advances_the_record_without_output(self) -> None:
        write_state(self.content, "0.1.3-draft", ["0.1.1-draft", "0.1.3-draft"])
        result = self.run_notice(quiet=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("has no user-facing news", result.stdout)
        self.assertNotIn("Second note about projects.", result.stdout)
        self.assertNotIn("NOT-NEWS-CURRENT", result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("last_announced_version: 0.1.4-draft", recorded)
        self.assertNotIn("0.1.4-draft\n", recorded.split("seen_news:", 1)[1])

    def test_unknown_previous_version_still_accumulates_flagged_news(self) -> None:
        write_state(self.content, "0.0.9-draft")
        result = self.run_notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stdout.index("First note about roles."), result.stdout.index("Second note about projects."))
        self.assertNotIn("NOT-NEWS-MIDDLE", result.stdout)

    def test_cp1252_stdout_can_print_news(self) -> None:
        marker = "\u2610"
        text = FIXTURE.replace("current_version: 0.1.4-draft", "current_version: 0.1.3-draft")
        text = text.replace("Second note about projects.", f"Second note {marker} projects.")
        (self.system / "bSmart_Version.md").write_text(text, encoding="utf-8")
        write_state(self.content, "0.1.0-draft")
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        env["PYTHONUTF8"] = "0"
        env["PYTHONIOENCODING"] = "cp1252:strict"
        result = subprocess.run(
            [
                sys.executable,
                str(NOTICE),
                "--quiet",
                "--content-root",
                str(self.content),
                "--system-root",
                str(self.system),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertEqual(result.returncode, 0, stderr)
        self.assertNotIn("UnicodeEncodeError", stderr)
        stdout = result.stdout.decode("utf-8")
        self.assertIn(marker, stdout)
        self.assertIn("First note about roles.", stdout)


class RealChangelogTests(unittest.TestCase):
    def test_roles_revamp_is_the_only_news_across_skipped_versions(self) -> None:
        self.assertTrue(ROLES_NEWS.isascii())
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "bSmart"
            content.mkdir()
            write_state(content, "0.1.40-draft")
            result = subprocess.run(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("0.1.45-draft:", result.stdout)
            self.assertIn(ROLES_NEWS, result.stdout)
            self.assertNotIn("0.1.45.2-draft:", result.stdout)
            self.assertNotIn("0.1.44.1-draft:", result.stdout)
            self.assertNotIn("Short paragraph for the user", result.stdout)
            self.assertNotIn("mark a version as user-facing news", result.stdout)
            self.assertNotIn("reconfigure bStart stdout", result.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("last_announced_version: 0.1.45.2-draft", recorded)
            self.assertIn("0.1.45-draft", recorded)
            again = subprocess.run(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(again.stdout, "")
            self.assertNotIn(ROLES_NEWS, again.stdout)

    def test_startup_instructions_tell_the_agent_to_relay_news(self) -> None:
        relay = "relay that news briefly in the first reply, once"
        for relative in (
            "bSmart_Templates/AGENTS.md",
            "bSmart_Templates/CLAUDE.md",
            "bSmart.md",
            "bSmart_Protocols/bootstrap.md",
        ):
            self.assertIn(relay, (ROOT / relative).read_text(encoding="utf-8"))
        version = (ROOT / "bSmart_Version.md").read_text(encoding="utf-8")
        self.assertIn("current_version: 0.1.45.2-draft", version)
        self.assertIn("it changes the user's workflow, the commands they type, or what they see", version)


class LayoutTests(unittest.TestCase):
    def make_instance(self, root: Path, last_seen: str | None) -> None:
        system = root / "bSmart-System"
        scripts = system / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(START, system / "bStart.py")
        shutil.copy2(NOTICE, scripts / "bsmart-release-notice")
        shutil.copy2(ROOT / "scripts" / "bsmart_instance.py", scripts / "bsmart_instance.py")
        (system / "bSmart_Version.md").write_text(FIXTURE, encoding="utf-8")
        content = root / "bSmart"
        content.mkdir()
        (content / "bSmart_Agent.md").write_text(
            "# Agent\n\n```yaml\nagent:\n  name: LayoutAgent\n  operator: Layout User\n```\n",
            encoding="utf-8",
        )
        if last_seen is not None:
            write_state(content, last_seen)
        projects = root / "projects"
        projects.mkdir()

    def run_bstart(self, script: Path, root: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["BSMART_PROJECT_ROOT"] = str(root / "projects")
        env.pop("BSMART_SESSION_PROJECT", None)
        env.pop("BSMART_SESSION_WORKSTREAM", None)
        return subprocess.run(
            [sys.executable, str(script), "--root", str(root), "--skip-update", "--skip-integrity"],
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )

    def assert_news_once(self, script: Path, root: Path) -> None:
        first = self.run_bstart(script, root)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stderr, "")
        self.assertIn("bSmart — Startup", first.stdout)
        self.assertIn("First note about roles.", first.stdout)
        self.assertIn("Second note about projects.", first.stdout)
        self.assertLess(first.stdout.index("First note about roles."), first.stdout.index("Second note about projects."))
        self.assertNotIn("NOT-NEWS-MIDDLE", first.stdout)
        second = self.run_bstart(script, root)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertNotIn("First note about roles.", second.stdout)
        self.assertNotIn("Second note about projects.", second.stdout)
        self.assertIn("bSmart — Startup", second.stdout)

    def test_hermes_container_layout_shows_news_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_instance(root, "0.1.0-draft")
            self.assert_news_once(root / "bSmart-System" / "bStart.py", root)

    def test_windows_workspace_root_bstart_shows_news_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_instance(root, "0.1.0-draft")
            shutil.copy2(START, root / "bStart.py")
            self.assert_news_once(root / "bStart.py", root)

    def test_fresh_bstart_in_both_layouts_prints_no_historical_news(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_instance(root, None)
            shutil.copy2(START, root / "bStart.py")
            for script in (root / "bSmart-System" / "bStart.py", root / "bStart.py"):
                result = self.run_bstart(script, root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("First note about roles.", result.stdout)
                self.assertNotIn("Second note about projects.", result.stdout)
                self.assertNotIn("bSmart news:", result.stdout)
            recorded = (root / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)
            self.assertIn("last_announced_version: 0.1.4-draft", recorded)

    def test_startup_check_in_hermes_layout_shows_news_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_instance(root, "0.1.0-draft")
            scripts = root / "bSmart-System" / "scripts"
            for name in ("bsmart-startup-check", "bsmart-content-upgrade", "bsmart_instance.py"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            templates = root / "bSmart-System" / "bSmart_Templates"
            templates.mkdir()
            shutil.copy2(ROOT / "bSmart_Templates" / "bHistory.template.md", templates / "bHistory.template.md")
            command = [
                sys.executable,
                str(scripts / "bsmart-startup-check"),
                "--skip-system-update",
                "--skip-project-storage",
                "--skip-project-integration",
            ]
            env = os.environ.copy()
            env["HOME"] = str(root / "home")
            env["PATH"] = tool_path()
            env.pop("HERMES_HOME", None)
            first = run_text(command, env=env, cwd=root)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("First note about roles.", first.stdout)
            self.assertIn("Second note about projects.", first.stdout)
            self.assertNotIn("NOT-NEWS-MIDDLE", first.stdout)
            second = run_text(command, env=env, cwd=root)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertNotIn("First note about roles.", second.stdout)
            self.assertNotIn("Second note about projects.", second.stdout)


class UpgradePathTests(unittest.TestCase):
    def test_instance_upgrade_prints_news_once_and_a_fresh_upgrade_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("Run `python bStart.py`.\n", encoding="utf-8")
            (system / "bSmart_Version.md").write_text(FIXTURE, encoding="utf-8")
            content = workspace / "bSmart"
            content.mkdir(parents=True)
            write_state(content, "0.1.0-draft")
            first = subprocess.run(
                [sys.executable, str(UPGRADE), "--workspace", str(workspace)],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("bSmart instance upgrade: verified", first.stdout)
            self.assertIn("First note about roles.", first.stdout)
            self.assertIn("Second note about projects.", first.stdout)
            self.assertNotIn("NOT-NEWS-MIDDLE", first.stdout)
            second = subprocess.run(
                [sys.executable, str(UPGRADE), "--workspace", str(workspace)],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertNotIn("First note about roles.", second.stdout)
            self.assertNotIn("Second note about projects.", second.stdout)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "fresh"
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
            (system / "bSmart_Version.md").write_text(FIXTURE, encoding="utf-8")
            (workspace / "bSmart").mkdir()
            result = subprocess.run(
                [sys.executable, str(UPGRADE), "--workspace", str(workspace)],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("First note about roles.", result.stdout)
            self.assertNotIn("bSmart news:", result.stdout)
            recorded = (workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)

    def test_bsmart_update_prints_news_for_a_version_jump(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            link = workspace / "bSmart-System"
            try:
                os.symlink(ROOT, link, target_is_directory=True)
            except OSError:
                shutil.copytree(ROOT, link, symlinks=True)
            content = workspace / "bSmart"
            write_state(content, "0.1.44.1-draft")
            env = os.environ.copy()
            env["HOME"] = str(root / "home")
            env["PATH"] = tool_path()
            env.pop("HERMES_HOME", None)
            result = run_text([sys.executable, str(UPDATE), "--workspace", str(workspace)], env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("bSmart update: complete", result.stdout)
            self.assertIn(ROLES_NEWS, result.stdout)
            self.assertNotIn("blocked", result.stdout)
            again = run_text([sys.executable, str(UPDATE), "--workspace", str(workspace)], env=env)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertNotIn(ROLES_NEWS, again.stdout)


class EstablishedInstanceTests(unittest.TestCase):
    """A missing notice file is a fresh install only when nothing older is there."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="bsmart-news-existing-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.system = self.root / "bSmart-System"
        self.content = self.root / "bSmart"
        self.system.mkdir()
        self.content.mkdir()
        shutil.copy2(ROOT / "bSmart_Version.md", self.system / "bSmart_Version.md")

    def notice(self) -> subprocess.CompletedProcess[str]:
        return run_text(
            [
                sys.executable,
                str(NOTICE),
                "--quiet",
                "--content-root",
                str(self.content),
                "--system-root",
                str(self.system),
            ]
        )

    def test_roles_directory_shows_the_045_news_once(self) -> None:
        roles = self.content / "Roles"
        roles.mkdir()
        (roles / "general_role.md").write_text("historical role\n", encoding="utf-8")
        first = self.notice()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn(ROLES_NEWS, first.stdout)
        self.assertIn(".bsmart-upgrade-backups/<timestamp>/roles-migration/", first.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertNotIn("baseline: fresh", recorded)
        self.assertIn("0.1.45-draft", recorded)
        second = self.notice()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, "")
        self.assertNotIn(ROLES_NEWS, second.stdout)

    def test_migration_marker_shows_the_045_news_at_most_once(self) -> None:
        marker = self.content / "State" / "role-migration.json"
        marker.parent.mkdir(parents=True)
        marker.write_text('{"marker": "session-projects-0.1.45", "backup": "/tmp/old"}\n', encoding="utf-8")
        first = self.notice()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn(ROLES_NEWS, first.stdout)
        second = self.notice()
        self.assertEqual(second.stdout, "")
        self.assertNotIn(ROLES_NEWS, second.stdout)

    def test_existing_state_file_is_an_upgrade(self) -> None:
        state = self.content / "State"
        state.mkdir()
        (state / "bsmart-startup-check.yaml").write_text("last_checked_utc_date: 2026-01-01\n", encoding="utf-8")
        result = self.notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(ROLES_NEWS, result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertNotIn("baseline: fresh", recorded)

    def test_agent_profile_alone_stays_a_fresh_install(self) -> None:
        (self.content / "bSmart_Agent.md").write_text("name: New\n", encoding="utf-8")
        result = self.notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(ROLES_NEWS, result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("baseline: fresh", recorded)

    def test_pre_pull_orig_head_is_the_previous_version(self) -> None:
        old = FIXTURE.replace("current_version: 0.1.4-draft", "current_version: 0.1.0-draft")
        version = self.system / "bSmart_Version.md"
        version.write_text(old, encoding="utf-8")
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "Test"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "Test"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"
        subprocess.run(["git", "init", "-q"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "add", "bSmart_Version.md"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "old"], cwd=self.system, check=True, env=env)
        old_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.system,
            check=True,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        version.write_text(FIXTURE, encoding="utf-8")
        subprocess.run(["git", "add", "bSmart_Version.md"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "new"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "update-ref", "ORIG_HEAD", old_head], cwd=self.system, check=True, env=env)
        result = run_text(
            [
                sys.executable,
                str(NOTICE),
                "--quiet",
                "--content-root",
                str(self.content),
                "--system-root",
                str(self.system),
            ],
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("First note about roles.", result.stdout)
        self.assertIn("Second note about projects.", result.stdout)
        self.assertNotIn("NOT-NEWS-MIDDLE", result.stdout)
        self.assertNotIn("baseline: fresh", (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"))

    def test_instance_upgrade_with_roles_shows_045_news_once(self) -> None:
        workspace = self.root / "workspace"
        system = workspace / "bSmart-System"
        (system / "bSmart_Templates").mkdir(parents=True)
        (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
        (system / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
        shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
        (workspace / "bSmart" / "Roles").mkdir(parents=True)
        (workspace / "bSmart" / "Roles" / "general_role.md").write_text("historical role\n", encoding="utf-8")
        command = [sys.executable, str(UPGRADE), "--workspace", str(workspace)]
        first = run_text(command)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn(ROLES_NEWS, first.stdout)
        self.assertTrue((workspace / "bSmart" / "State" / "role-migration.json").is_file())
        second = run_text(command)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertNotIn(ROLES_NEWS, second.stdout)


if __name__ == "__main__":
    unittest.main()
