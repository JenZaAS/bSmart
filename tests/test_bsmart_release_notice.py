"""User-facing release news is announced once, including across skipped versions."""

from __future__ import annotations

import os
import re
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
    "projects. /role now only points to /project. Existing roles were migrated where "
    "unambiguous (anything skipped is listed as a question)."
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


def repo_current_version() -> str:
    text = (ROOT / "bSmart_Version.md").read_text(encoding="utf-8")
    match = re.search(r"^current_version:\s*(\S+)\s*$", text, re.MULTILINE)
    if not match:
        raise AssertionError("current_version is missing from bSmart_Version.md")
    return match.group(1)


def version_has_news(version: str) -> bool:
    text = (ROOT / "bSmart_Version.md").read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(version)}\s*$", text, re.MULTILINE)
    if not match:
        return False
    rest = text[match.end():]
    nxt = re.search(r"^## \d+\.\d+", rest, re.MULTILINE)
    section = rest[: nxt.start()] if nxt else rest
    fence = re.search(r"```(?:yaml|yml)?\s*\n(.*?)```", section, re.DOTALL)
    body = fence.group(1) if fence else section
    return bool(re.search(r"^news:\s*\S", body, re.MULTILINE))


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


def write_old_state(content: Path, version: str) -> Path:
    """The 0.1.20 record: last_announced_version only, no seen_news key."""
    state = content / "State" / "bsmart-release-notice.yaml"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(f"last_announced_version: {version}\n", encoding="utf-8")
    return state


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


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

    def run_notice(self, quiet: bool = True, record: bool = True) -> subprocess.CompletedProcess[str]:
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
        command.append("--record" if record else "--preview")
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

    def test_parsed_version_missing_from_the_changelog_is_ordered_by_number(self) -> None:
        write_state(self.content, "0.0.9-draft")
        result = self.run_notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stdout.index("First note about roles."), result.stdout.index("Second note about projects."))
        self.assertNotIn("NOT-NEWS-MIDDLE", result.stdout)

    def test_newer_or_unparseable_unknown_versions_are_not_older_than_everything(self) -> None:
        write_state(self.content, "9.9.9-draft")
        before = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        newer = self.run_notice()
        self.assertEqual(newer.returncode, 0, newer.stderr)
        self.assertNotIn("First note about roles.", newer.stdout)
        self.assertNotIn("bSmart news:", newer.stdout)
        self.assertEqual((self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"), before)

        write_state(self.content, "topic/unmerged")
        before = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        garbage = self.run_notice()
        self.assertEqual(garbage.returncode, 0, garbage.stderr)
        self.assertNotIn("First note about roles.", garbage.stdout)
        self.assertEqual((self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"), before)

    def test_old_format_includes_the_recorded_version_and_new_format_excludes_it(self) -> None:
        write_old_state(self.content, "0.1.1-draft")
        first = self.run_notice()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("First note about roles.", first.stdout)
        self.assertIn("Second note about projects.", first.stdout)
        self.assertLess(first.stdout.index("First note about roles."), first.stdout.index("Second note about projects."))
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("seen_news:", recorded)
        self.assertIn("0.1.1-draft", recorded)
        again = self.run_notice()
        self.assertEqual(again.stdout, "")

        shutil.rmtree(self.content / "State")
        write_state(self.content, "0.1.1-draft")
        excluded = self.run_notice()
        self.assertEqual(excluded.returncode, 0, excluded.stderr)
        self.assertNotIn("First note about roles.", excluded.stdout)
        self.assertIn("Second note about projects.", excluded.stdout)

    def test_out_of_order_headings_are_sorted_numerically(self) -> None:
        text = """# fixture

```yaml
current_version: 0.1.32-draft
```

## 0.1.32-draft

```yaml
news: |
  Thirty two.
scope:
  - later
```

## 0.1.19-draft

```yaml
news: |
  Nineteen.
scope:
  - misplaced
```

## 0.1.31-draft

```yaml
news: |
  Thirty one.
scope:
  - middle
```
"""
        (self.system / "bSmart_Version.md").write_text(text, encoding="utf-8")
        write_state(self.content, "0.1.18-draft")
        result = self.run_notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        nineteen = result.stdout.index("Nineteen.")
        thirty_one = result.stdout.index("Thirty one.")
        thirty_two = result.stdout.index("Thirty two.")
        self.assertLess(nineteen, thirty_one)
        self.assertLess(thirty_one, thirty_two)

    def test_a_held_lock_suppresses_a_second_print(self) -> None:
        write_state(self.content, "0.1.0-draft")
        lock = self.content / "State" / "bsmart-release-notice.lock"
        lock.write_text("held\n", encoding="utf-8")
        env = os.environ.copy()
        env["BSMART_NOTICE_LOCK_WAIT"] = "0"
        held = subprocess.run(
            [
                sys.executable,
                str(NOTICE),
                "--quiet",
                "--record",
                "--content-root",
                str(self.content),
                "--system-root",
                str(self.system),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(held.returncode, 0, held.stderr)
        self.assertNotIn("First note about roles.", held.stdout)
        self.assertIn("last_announced_version: 0.1.0-draft", lock.with_name("bsmart-release-notice.yaml").read_text(encoding="utf-8"))
        lock.unlink()
        released = self.run_notice()
        self.assertIn("First note about roles.", released.stdout)
        self.assertFalse(lock.exists())
        leftovers = list((self.content / "State").glob(".bsmart-release-notice.yaml.*.tmp"))
        self.assertEqual(leftovers, [])

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
                "--record",
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
        current = repo_current_version()
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "bSmart"
            content.mkdir()
            write_state(content, "0.1.40-draft")
            result = subprocess.run(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
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
            self.assertIn("where unambiguous (anything skipped is listed as a question)", result.stdout)
            self.assertNotIn(".bsmart-upgrade-backups/", result.stdout)
            self.assertNotIn("role-migration-review.md", result.stdout)
            self.assertNotIn("--restore-session-projects", result.stdout)
            if not version_has_news(current):
                self.assertNotIn(f"{current}:", result.stdout)
            self.assertNotIn("0.1.44.1-draft:", result.stdout)
            self.assertNotIn("Short paragraph for the user", result.stdout)
            self.assertNotIn("mark a version as user-facing news", result.stdout)
            self.assertNotIn("reconfigure bStart stdout", result.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn(f"last_announced_version: {current}", recorded)
            self.assertIn("0.1.45-draft", recorded)
            again = subprocess.run(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
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

    def test_old_format_record_at_045_includes_that_news(self) -> None:
        current = repo_current_version()
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "bSmart"
            write_old_state(content, "0.1.45-draft")
            result = subprocess.run(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
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
            self.assertIn(ROLES_NEWS, result.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("seen_news:", recorded)
            self.assertIn(f"last_announced_version: {current}", recorded)
            self.assertIn("0.1.45-draft", recorded.split("seen_news:", 1)[1])

    def test_old_style_0451_with_roles_shows_045_news_once(self) -> None:
        """A daily check between #7 and this change recorded 0.1.45.1-draft only."""
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "bSmart"
            roles = content / "Roles"
            roles.mkdir(parents=True)
            (roles / "general_role.md").write_text("historical role\n", encoding="utf-8")
            state = write_old_state(content, "0.1.45.1-draft")
            before = state.read_text(encoding="utf-8")
            preview = run_text(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--preview",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ]
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn(ROLES_NEWS, preview.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), before)
            first = run_text(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ]
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn(ROLES_NEWS, first.stdout)
            recorded = state.read_text(encoding="utf-8")
            self.assertIn("seen_news:", recorded)
            self.assertIn("0.1.45-draft", recorded.split("seen_news:", 1)[1])
            self.assertIn(f"last_announced_version: {repo_current_version()}", recorded)
            second = run_text(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ]
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(second.stdout, "")
            self.assertNotIn(ROLES_NEWS, second.stdout)

    def test_old_style_0451_without_a_signal_does_not_replay_older_news(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "bSmart"
            write_old_state(content, "0.1.45.1-draft")
            result = run_text(
                [
                    sys.executable,
                    str(NOTICE),
                    "--quiet",
                    "--record",
                    "--content-root",
                    str(content),
                    "--system-root",
                    str(ROOT),
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(ROLES_NEWS, result.stdout)
            self.assertNotIn("bSmart news:", result.stdout)

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
        self.assertRegex(version, r"(?m)^current_version:\s*\S+\s*$")
        self.assertIn("it changes the user's workflow, the commands they type, or what they see", version)
        self.assertIn("no seen_news key", version)
        self.assertIn("`ORIG_HEAD` is not a signal", version)


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

    def test_startup_check_previews_and_bstart_records(self) -> None:
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
            recorded_after_preview = (root / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("last_announced_version: 0.1.0-draft", recorded_after_preview)
            self.assertNotIn("0.1.1-draft", recorded_after_preview)
            second = run_text(command, env=env, cwd=root)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("First note about roles.", second.stdout)
            startup = self.run_bstart(root / "bSmart-System" / "bStart.py", root)
            self.assertEqual(startup.returncode, 0, startup.stdout + startup.stderr)
            self.assertIn("First note about roles.", startup.stdout)
            recorded = (root / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("last_announced_version: 0.1.4-draft", recorded)
            self.assertIn("0.1.1-draft", recorded)
            third = run_text(command, env=env, cwd=root)
            self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
            self.assertNotIn("First note about roles.", third.stdout)
            self.assertNotIn("Second note about projects.", third.stdout)


class UpgradePathTests(unittest.TestCase):
    def test_instance_upgrade_previews_without_recording_and_bstart_records(self) -> None:
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
            before = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            command = [sys.executable, str(UPGRADE), "--workspace", str(workspace)]
            first = run_text(command)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("bSmart instance upgrade: verified", first.stdout)
            self.assertIn("First note about roles.", first.stdout)
            self.assertIn("Second note about projects.", first.stdout)
            self.assertNotIn("NOT-NEWS-MIDDLE", first.stdout)
            self.assertEqual((content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"), before)
            second = run_text(command)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("First note about roles.", second.stdout)
            self.assertEqual((content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8"), before)
            env = os.environ.copy()
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text(
                [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertIn("First note about roles.", started.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("last_announced_version: 0.1.4-draft", recorded)
            self.assertIn("0.1.1-draft", recorded)
            again = run_text(
                [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertNotIn("First note about roles.", again.stdout)
            third = run_text(command)
            self.assertNotIn("First note about roles.", third.stdout)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "fresh"
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
            (system / "bSmart_Version.md").write_text(FIXTURE, encoding="utf-8")
            (workspace / "bSmart").mkdir()
            result = run_text([sys.executable, str(UPGRADE), "--workspace", str(workspace)])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("First note about roles.", result.stdout)
            self.assertNotIn("bSmart news:", result.stdout)
            self.assertFalse((workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").exists())
            env = os.environ.copy()
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text(
                [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertNotIn("bSmart news:", started.stdout)
            recorded = (workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)

    def test_a_failed_notice_does_not_fail_a_successful_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            system = workspace / "bSmart-System"
            (system / "bSmart_Templates").mkdir(parents=True)
            (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
            (system / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
            (system / "bSmart_Version.md").write_text("# no current version\n", encoding="utf-8")
            (workspace / "bSmart").mkdir()
            result = run_text([sys.executable, str(UPGRADE), "--workspace", str(workspace)])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("bSmart instance upgrade: verified", result.stdout)
            self.assertFalse((workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").exists())

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
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("last_announced_version: 0.1.44.1-draft", recorded)
            self.assertNotIn("0.1.45-draft", recorded)
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text(
                [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertIn(ROLES_NEWS, started.stdout)
            marked = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn(f"last_announced_version: {repo_current_version()}", marked)
            self.assertIn("0.1.45-draft", marked)
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

    def notice(self, record: bool = True) -> subprocess.CompletedProcess[str]:
        return run_text(
            [
                sys.executable,
                str(NOTICE),
                "--quiet",
                "--record" if record else "--preview",
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
        self.assertNotIn("--restore-session-projects", first.stdout)
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

    def test_state_cache_files_and_version_keys_are_not_an_upgrade(self) -> None:
        state = self.content / "State"
        state.mkdir()
        (state / "bsmart-startup-check.yaml").write_text("last_checked_utc_date: 2026-01-01\n", encoding="utf-8")
        (state / "bsmart-system-update.yaml").write_text("status: up_to_date\n", encoding="utf-8")
        (state / "container-storage.yaml").write_text("projects:\n  status: internal\n", encoding="utf-8")
        (state / "notes.md").write_text("bsmart_version: 0.1.0-draft\nsystem_version: 0.1.1-draft\n", encoding="utf-8")
        result = self.notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(ROLES_NEWS, result.stdout)
        self.assertEqual(result.stdout, "")
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("baseline: fresh", recorded)

    def test_legacy_state_file_shows_the_045_news_once(self) -> None:
        (self.content / "bSmart_State.md").write_text("# bSmart state\n\n- Mode: `Free`\n", encoding="utf-8")
        first = self.notice()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn(ROLES_NEWS, first.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertNotIn("baseline: fresh", recorded)
        second = self.notice()
        self.assertEqual(second.stdout, "")

    def test_agent_profile_alone_stays_a_fresh_install(self) -> None:
        (self.content / "bSmart_Agent.md").write_text("name: New\n", encoding="utf-8")
        result = self.notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(ROLES_NEWS, result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("baseline: fresh", recorded)

    def test_orig_head_is_not_an_upgrade_signal(self) -> None:
        old = FIXTURE.replace("current_version: 0.1.4-draft", "current_version: 0.1.0-draft")
        version = self.system / "bSmart_Version.md"
        version.write_text(old, encoding="utf-8")
        env = git_env()
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
        shutil.copy2(ROOT / "bSmart_Version.md", version)
        subprocess.run(["git", "add", "bSmart_Version.md"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "new"], cwd=self.system, check=True, env=env)
        subprocess.run(["git", "update-ref", "ORIG_HEAD", old_head], cwd=self.system, check=True, env=env)
        result = self.notice()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(ROLES_NEWS, result.stdout)
        self.assertNotIn("bSmart news:", result.stdout)
        recorded = (self.content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("baseline: fresh", recorded)
        self.assertIn(f"last_announced_version: {repo_current_version()}", recorded)

    def test_instance_upgrade_with_roles_previews_and_bstart_records_once(self) -> None:
        workspace = self.root / "workspace"
        system = workspace / "bSmart-System"
        (system / "bSmart_Templates").mkdir(parents=True)
        (system / "bStart.py").write_text("new bStart\n", encoding="utf-8")
        (system / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
        shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
        (workspace / "bSmart" / "Roles").mkdir(parents=True)
        (workspace / "bSmart" / "Roles" / "general_role.md").write_text("historical role\n", encoding="utf-8")
        (workspace / "projects").mkdir()
        command = [sys.executable, str(UPGRADE), "--workspace", str(workspace)]
        first = run_text(command)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn(ROLES_NEWS, first.stdout)
        self.assertIn(".bsmart-upgrade-backups", first.stdout)
        self.assertTrue(any((workspace / ".bsmart-upgrade-backups").glob("*/roles-migration")))
        self.assertTrue((workspace / "bSmart" / "State" / "role-migration.json").is_file())
        self.assertFalse((workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").exists())
        second = run_text(command)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn(ROLES_NEWS, second.stdout)
        self.assertFalse((workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").exists())
        env = os.environ.copy()
        env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
        started = run_text(
            [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
            env=env,
        )
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertIn(ROLES_NEWS, started.stdout)
        recorded = (workspace / "bSmart" / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
        self.assertIn("0.1.45-draft", recorded)
        self.assertNotIn("baseline: fresh", recorded)
        quiet = run_text(
            [sys.executable, str(START), "--root", str(workspace), "--skip-update", "--skip-integrity"],
            env=env,
        )
        self.assertNotIn(ROLES_NEWS, quiet.stdout)
        third = run_text(command)
        self.assertNotIn(ROLES_NEWS, third.stdout)


class CallOrderTests(unittest.TestCase):
    """Bootstrap, bStart, and upgrade in the order a real instance runs them."""

    def init_origin(self, path: Path) -> None:
        scripts = path / "scripts"
        scripts.mkdir(parents=True)
        (path / "bSmart_Templates").mkdir()
        shutil.copy2(ROOT / "bSmart_Version.md", path / "bSmart_Version.md")
        shutil.copy2(ROOT / "bStart.py", path / "bStart.py")
        for name in (
            "bsmart-release-notice",
            "bsmart_instance.py",
            "bsmart-system-update-check",
            "bsmart_session_projects.py",
        ):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        (path / "bSmart_Templates" / "AGENTS.md").write_text("hook\n", encoding="utf-8")
        (path / "bSmart_Templates" / "bHistory.template.md").write_text("# History\n", encoding="utf-8")
        env = git_env()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True, env=env)
        subprocess.run(["git", "add", "."], cwd=path, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "origin"], cwd=path, check=True, env=env)

    def test_bootstrap_then_bstart_prints_no_historical_news(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin"
            self.init_origin(origin)
            workspace = root / "workspace"
            uid = str(getattr(os, "getuid", lambda: 10000)())
            gid = str(getattr(os, "getgid", lambda: 10000)())
            env = git_env()
            boot = run_text(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "bsmart-bootstrap-workspace"),
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "Fresh",
                    "--operator",
                    "Tester",
                    "--repo-url",
                    str(origin),
                    "--uid",
                    uid,
                    "--gid",
                    gid,
                ],
                env=env,
            )
            self.assertEqual(boot.returncode, 0, boot.stdout + boot.stderr)
            self.assertNotIn("bSmart news:", boot.stdout)
            self.assertNotIn(ROLES_NEWS, boot.stdout)
            content = workspace / "bSmart"
            self.assertFalse((content / "bSmart_State.md").exists())
            self.assertTrue((content / "State" / "container-storage.yaml").is_file())
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)
            self.assertIn(f"last_announced_version: {repo_current_version()}", recorded)
            system = workspace / "bSmart-System"
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=system,
                check=True,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            subprocess.run(["git", "update-ref", "ORIG_HEAD", head], cwd=system, check=True, env=env)
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text([sys.executable, str(workspace / "bStart.py"), "--root", str(workspace)], env=env)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertIn("bSmart — Startup", started.stdout)
            self.assertNotIn("bSmart news:", started.stdout)
            self.assertNotIn(ROLES_NEWS, started.stdout)
            self.assertTrue((content / "State" / "bsmart-system-update.yaml").is_file(), started.stdout + started.stderr)
            after = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", after)
            self.assertNotIn("0.1.45-draft", after.split("seen_news:", 1)[1])

    def test_bstart_ignores_state_files_that_already_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(START, system / "bStart.py")
            shutil.copy2(NOTICE, scripts / "bsmart-release-notice")
            shutil.copy2(ROOT / "scripts" / "bsmart_instance.py", scripts / "bsmart_instance.py")
            shutil.copy2(ROOT / "scripts" / "bsmart-system-update-check", scripts / "bsmart-system-update-check")
            shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
            content = root / "bSmart"
            state = content / "State"
            state.mkdir(parents=True)
            (state / "container-storage.yaml").write_text("projects:\n  status: internal\n", encoding="utf-8")
            (content / "bSmart_Agent.md").write_text("agent:\n  name: Fresh\n  operator: Tester\n", encoding="utf-8")
            env = os.environ.copy()
            env["BSMART_PROJECT_ROOT"] = str(root / "projects")
            (root / "projects").mkdir()
            checked = run_text(
                [
                    sys.executable,
                    str(scripts / "bsmart-system-update-check"),
                    "--repo",
                    str(system),
                    "--state",
                    str(state / "bsmart-system-update.yaml"),
                ],
                env=env,
            )
            self.assertTrue((state / "bsmart-system-update.yaml").is_file(), checked.stdout + checked.stderr)
            started = run_text(
                [sys.executable, str(system / "bStart.py"), "--root", str(root)],
                env=env,
            )
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertNotIn("bSmart news:", started.stdout)
            self.assertNotIn(ROLES_NEWS, started.stdout)
            recorded = (state / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)

    def test_bstart_records_old_format_045_news_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(START, system / "bStart.py")
            shutil.copy2(NOTICE, scripts / "bsmart-release-notice")
            shutil.copy2(ROOT / "scripts" / "bsmart_instance.py", scripts / "bsmart_instance.py")
            shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
            content = root / "bSmart"
            content.mkdir()
            write_old_state(content, "0.1.45-draft")
            (content / "bSmart_Agent.md").write_text("agent:\n  name: Existing\n  operator: Tester\n", encoding="utf-8")
            env = os.environ.copy()
            env["BSMART_PROJECT_ROOT"] = str(root / "projects")
            (root / "projects").mkdir()
            first = run_text(
                [sys.executable, str(system / "bStart.py"), "--root", str(root), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn(ROLES_NEWS, first.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("seen_news:", recorded)
            self.assertIn("0.1.45-draft", recorded.split("seen_news:", 1)[1])
            self.assertIn(f"last_announced_version: {repo_current_version()}", recorded)
            second = run_text(
                [sys.executable, str(system / "bStart.py"), "--root", str(root), "--skip-update", "--skip-integrity"],
                env=env,
            )
            self.assertNotIn(ROLES_NEWS, second.stdout)
            self.assertNotIn("bSmart news:", second.stdout)

    def test_bstart_no_record_flag_and_env_leave_the_news_unseen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(START, system / "bStart.py")
            shutil.copy2(NOTICE, scripts / "bsmart-release-notice")
            shutil.copy2(ROOT / "scripts" / "bsmart_instance.py", scripts / "bsmart_instance.py")
            shutil.copy2(ROOT / "bSmart_Version.md", system / "bSmart_Version.md")
            content = root / "bSmart"
            roles = content / "Roles"
            roles.mkdir(parents=True)
            (roles / "general_role.md").write_text("historical role\n", encoding="utf-8")
            state = write_old_state(content, "0.1.45.1-draft")
            before = state.read_text(encoding="utf-8")
            (content / "bSmart_Agent.md").write_text("agent:\n  name: Cron\n  operator: Tester\n", encoding="utf-8")
            env = os.environ.copy()
            env["BSMART_PROJECT_ROOT"] = str(root / "projects")
            (root / "projects").mkdir()
            command = [
                sys.executable,
                str(system / "bStart.py"),
                "--root",
                str(root),
                "--skip-update",
                "--skip-integrity",
                "--no-record",
            ]
            flagged = run_text(command, env=env)
            self.assertEqual(flagged.returncode, 0, flagged.stdout + flagged.stderr)
            self.assertIn(ROLES_NEWS, flagged.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), before)
            automated = env.copy()
            automated["BSMART_NEWS_NO_RECORD"] = "1"
            cron = run_text(command[:-1], env=automated)
            self.assertEqual(cron.returncode, 0, cron.stdout + cron.stderr)
            self.assertIn(ROLES_NEWS, cron.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), before)
            interactive = run_text(command[:-1], env=env)
            self.assertEqual(interactive.returncode, 0, interactive.stdout + interactive.stderr)
            self.assertIn(ROLES_NEWS, interactive.stdout)
            recorded = state.read_text(encoding="utf-8")
            self.assertIn("seen_news:", recorded)
            self.assertIn("0.1.45-draft", recorded.split("seen_news:", 1)[1])
            quiet = run_text(command[:-1], env=env)
            self.assertNotIn(ROLES_NEWS, quiet.stdout)
            self.assertNotIn("bSmart news:", quiet.stdout)

    def test_bootstrap_retries_a_failing_baseline(self) -> None:
        wrapper = """#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
counter = here / ".baseline-attempts"
seen = int(counter.read_text(encoding="utf-8")) if counter.is_file() else 0
counter.write_text(str(seen + 1), encoding="utf-8")
if seen < 2:
    print("baseline failed", file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(
    subprocess.call([sys.executable, str(here / "bsmart-release-notice.real"), *sys.argv[1:]])
)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin"
            self.init_origin(origin)
            notice = origin / "scripts" / "bsmart-release-notice"
            notice.replace(origin / "scripts" / "bsmart-release-notice.real")
            notice.write_text(wrapper, encoding="utf-8")
            env = git_env()
            subprocess.run(["git", "add", "scripts"], cwd=origin, check=True, env=env)
            subprocess.run(["git", "commit", "-q", "-m", "flaky baseline"], cwd=origin, check=True, env=env)
            workspace = root / "workspace"
            uid = str(getattr(os, "getuid", lambda: 10000)())
            gid = str(getattr(os, "getgid", lambda: 10000)())
            boot = run_text(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "bsmart-bootstrap-workspace"),
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "Fresh",
                    "--operator",
                    "Tester",
                    "--repo-url",
                    str(origin),
                    "--uid",
                    uid,
                    "--gid",
                    gid,
                ],
                env=env,
            )
            self.assertEqual(boot.returncode, 0, boot.stdout + boot.stderr)
            content = workspace / "bSmart"
            self.assertFalse((content / "bSmart_State.md").exists())
            attempts = workspace / "bSmart-System" / "scripts" / ".baseline-attempts"
            self.assertEqual(attempts.read_text(encoding="utf-8"), "3")
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)
            self.assertNotIn("bSmart news:", boot.stdout)
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text([sys.executable, str(workspace / "bStart.py"), "--root", str(workspace)], env=env)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertNotIn(ROLES_NEWS, started.stdout)
            self.assertNotIn("bSmart news:", started.stdout)

    def test_failed_baseline_does_not_turn_a_fresh_install_into_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin"
            self.init_origin(origin)
            failing = origin / "scripts" / "bsmart-release-notice"
            failing.write_text(
                "#!/usr/bin/env python3\nimport sys\nprint('baseline failed', file=sys.stderr)\nraise SystemExit(1)\n",
                encoding="utf-8",
            )
            env = git_env()
            subprocess.run(["git", "add", "scripts/bsmart-release-notice"], cwd=origin, check=True, env=env)
            subprocess.run(["git", "commit", "-q", "-m", "fail baseline"], cwd=origin, check=True, env=env)
            workspace = root / "workspace"
            uid = str(getattr(os, "getuid", lambda: 10000)())
            gid = str(getattr(os, "getgid", lambda: 10000)())
            boot = run_text(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "bsmart-bootstrap-workspace"),
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "Fresh",
                    "--operator",
                    "Tester",
                    "--repo-url",
                    str(origin),
                    "--uid",
                    uid,
                    "--gid",
                    gid,
                ],
                env=env,
            )
            self.assertEqual(boot.returncode, 0, boot.stdout + boot.stderr)
            self.assertIn("WARNING: could not record a fresh release-news baseline", boot.stdout)
            content = workspace / "bSmart"
            self.assertFalse((content / "bSmart_State.md").exists())
            self.assertFalse((content / "State" / "bsmart-release-notice.yaml").exists())
            cloned = workspace / "bSmart-System" / "scripts" / "bsmart-release-notice"
            shutil.copy2(NOTICE, cloned)
            env["BSMART_PROJECT_ROOT"] = str(workspace / "projects")
            (workspace / "projects").mkdir()
            started = run_text([sys.executable, str(workspace / "bStart.py"), "--root", str(workspace)], env=env)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertNotIn(ROLES_NEWS, started.stdout)
            self.assertNotIn("bSmart news:", started.stdout)
            recorded = (content / "State" / "bsmart-release-notice.yaml").read_text(encoding="utf-8")
            self.assertIn("baseline: fresh", recorded)
            self.assertNotIn("0.1.45-draft", recorded.split("seen_news:", 1)[1])


if __name__ == "__main__":
    unittest.main()
