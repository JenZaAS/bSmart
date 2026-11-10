"""Read-only Git checks must never create or leave `.git/index.lock`."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


BSTART = load(ROOT / "bStart.py", "bstart_optional_locks_test")
UPDATE = load(ROOT / "scripts" / "bsmart-system-update-check", "bsmart_update_check_optional_locks_test")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class OptionalLockTests(unittest.TestCase):
    def make_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="bsmart-locks-"))
        self.addCleanup(shutil.rmtree, repo, True)
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Test")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "commit.gpgsign", "false")
        (repo / "file.txt").write_text("hello\n", encoding="utf-8")
        git(repo, "add", "file.txt")
        git(repo, "commit", "-q", "-m", "init")
        return repo

    def test_bstart_git_status_does_not_rewrite_the_index(self):
        repo = self.make_repo()
        target = repo / "file.txt"
        # Same content, new timestamp: a normal `git status` would refresh
        # and rewrite the index under .git/index.lock.
        stat = target.stat()
        os.utime(target, (stat.st_atime + 100, stat.st_mtime + 100))
        index = repo / ".git" / "index"
        before = index.read_bytes()
        line = BSTART.git_status(repo, "bSmart-System")
        self.assertIn("bSmart-System:", line)
        self.assertNotIn("unavailable", line)
        self.assertEqual(index.read_bytes(), before)
        self.assertFalse((repo / ".git" / "index.lock").exists())

    def test_update_check_status_does_not_rewrite_the_index(self):
        repo = self.make_repo()
        target = repo / "file.txt"
        stat = target.stat()
        os.utime(target, (stat.st_atime + 100, stat.st_mtime + 100))
        index = repo / ".git" / "index"
        before = index.read_bytes()
        result = UPDATE.git(["status", "--porcelain"], repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(index.read_bytes(), before)
        self.assertFalse((repo / ".git" / "index.lock").exists())


class GitCommandShapeTests(unittest.TestCase):
    def capture(self, module, call):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            call()
        return seen

    def test_bstart_git_calls_skip_optional_locks(self):
        seen = self.capture(BSTART, lambda: BSTART.git_run(Path("."), ["status", "--porcelain"]))
        self.assertEqual(seen["cmd"][:2], ["git", "--no-optional-locks"])
        self.assertEqual(seen["env"]["GIT_OPTIONAL_LOCKS"], "0")

    def test_update_check_git_calls_skip_optional_locks(self):
        seen = self.capture(UPDATE, lambda: UPDATE.git(["status", "--porcelain"], Path(".")))
        self.assertEqual(seen["cmd"][:2], ["git", "--no-optional-locks"])
        self.assertEqual(seen["env"]["GIT_OPTIONAL_LOCKS"], "0")


class TimeoutTests(unittest.TestCase):
    def test_bstart_reports_a_git_timeout_without_crashing(self):
        repo = Path(tempfile.mkdtemp(prefix="bsmart-timeout-"))
        self.addCleanup(shutil.rmtree, repo, True)
        (repo / ".git").mkdir()
        boom = subprocess.TimeoutExpired(["git", "status"], 20)
        with mock.patch.object(BSTART.subprocess, "run", side_effect=boom):
            line = BSTART.git_status(repo, "bSmart-System")
        self.assertEqual(line, "bSmart-System: Git status skipped (timed out; slow disk?)")

    def test_update_check_reports_a_git_timeout_without_crashing(self):
        temp = Path(tempfile.mkdtemp(prefix="bsmart-timeout-"))
        self.addCleanup(shutil.rmtree, temp, True)
        repo = temp / "repo"
        (repo / ".git").mkdir(parents=True)
        state = temp / "state.yaml"

        def fake_run(cmd, **kwargs):
            if "status" in cmd:
                raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
            return subprocess.CompletedProcess(cmd, 0, "main\n", "")

        argv = ["bsmart-system-update-check", "--repo", str(repo), "--state", str(state), "--force"]
        with mock.patch.object(UPDATE.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch("builtins.print"):
            code = UPDATE.main()
        self.assertEqual(code, 1)
        text = state.read_text(encoding="utf-8")
        self.assertIn("status: unavailable", text)
        self.assertIn("timed out", text)


if __name__ == "__main__":
    unittest.main()
