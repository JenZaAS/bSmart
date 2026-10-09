from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SYSTEM = Path(__file__).parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClientAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = load("bsmart_client_adapter", SYSTEM / "integrations" / "bsmart_client_adapter.py")
        self.tmp = tempfile.TemporaryDirectory(prefix="bsmart-client-adapter-")
        home = Path(self.tmp.name)
        self.projects = home / "projects"
        self.projects.mkdir()
        self.env = {
            "BSMART_SYSTEM_ROOT": str(SYSTEM),
            "BSMART_PROJECT_ROOT": str(self.projects),
            "BSMART_INSTANCE_HOME": str(home),
            "BSMART_ARCHIVE_ROOT": str(home / "archives"),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_adapter(self, kind: str, args: list[str]) -> str:
        with patch.dict(os.environ, self.env, clear=False):
            for key in (
                "BSMART_SESSION_ID",
                "BSMART_SESSION_PROJECT",
                "BSMART_SESSION_WORKSTREAM",
                "BSMART_SESSION_HANDOFF",
                "HERMES_SESSION_KEY",
                "HERMES_SESSION_ID",
                "CLAUDE_SESSION_ID",
                "CURSOR_CONVERSATION_ID",
                "CURSOR_SESSION_ID",
                "CODEX_THREAD_ID",
                "CODEX_SESSION_ID",
            ):
                if key not in self.env:
                    os.environ.pop(key, None)
            return self.adapter.run(kind, args, workspace=Path(self.tmp.name))

    def test_lists_and_creates_in_the_isolated_root(self):
        listed = self.run_adapter("project", ["list"])
        self.assertIn("Projects:", listed)
        self.assertIn("Free Mode", listed)
        created = self.run_adapter("project", ["add", "Alpha"])
        self.assertIn("Alpha", created)
        self.assertTrue((self.projects / "Alpha" / "project.md").is_file())
        self.assertFalse((Path(self.tmp.name) / "Roles" / "current_role.md").exists())
        self.env["BSMART_SESSION_PROJECT"] = "Alpha"
        self.assertIn("- Alpha (current)", self.run_adapter("project", ["list"]))
        self.env["BSMART_SESSION_PROJECT"] = "Beta"
        other = self.run_adapter("project", ["list"])
        self.assertNotIn("- Alpha (current)", other)
        self.assertIn("Current: Beta", other)

    def test_selected_project_is_remembered_for_delete_and_handoff(self):
        self.assertIn("Current: Gamma", self.run_adapter("project", ["add", "Gamma"]))
        blocked = self.run_adapter("project", ["add", "Beta"])
        self.assertIn("handoff:", blocked)
        self.assertFalse((self.projects / "Beta").exists())
        switched = self.run_adapter("project", ["add", "Beta", "handoff:", "Wrapped", "Gamma"])
        self.assertIn("Current: Beta", switched)
        self.assertIn("Wrapped Gamma", (self.projects / "Gamma" / "handoff.md").read_text(encoding="utf-8"))
        prompt = self.run_adapter("project", ["delete"])
        self.assertIn("Confirmation required: delete exact target", prompt)
        pending_id = next(line for line in prompt.splitlines() if line.startswith("Yes:")).rsplit(" ", 1)[1]
        removed = self.run_adapter("project", ["yes", pending_id])
        self.assertIn("Free Mode", removed)
        self.assertFalse((self.projects / "Beta").exists())

    def test_named_delete_does_not_need_the_remembered_session(self):
        self.run_adapter("project", ["add", "Gamma"])
        self.env["BSMART_SESSION_ID"] = "other-chat"
        prompt = self.run_adapter("project", ["delete", "Gamma"])
        self.assertIn("Confirmation required: delete exact target", prompt)
        self.env.pop("BSMART_SESSION_ID")
        pending_id = next(line for line in prompt.splitlines() if line.startswith("Yes:")).rsplit(" ", 1)[1]
        removed = self.run_adapter("project", ["yes", pending_id])
        self.assertIn("Free Mode", removed)
        self.assertFalse((self.projects / "Gamma").exists())

    def test_role_command_is_deprecated(self):
        text = self.run_adapter("role", [])
        self.assertIn("deprecated", text.lower())
        self.assertIn("/project", text)

    def test_flags_are_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.command_text("project", ["--root", "C:/elsewhere"])

    def test_unset_env_uses_the_storage_spec(self):
        workspace = Path(self.tmp.name)
        spec_root = workspace / "from-spec"
        spec_root.mkdir()
        (workspace / "projects").mkdir(exist_ok=True)
        spec = workspace / "bSmart" / "State" / "container-storage.yaml"
        spec.parent.mkdir(parents=True)
        spec.write_text("project_storage:\n  project_root: ./from-spec\n", encoding="utf-8")
        env = dict(self.env)
        env.pop("BSMART_PROJECT_ROOT", None)
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("BSMART_PROJECT_ROOT", None)
            self.adapter.ensure_environment(workspace)
            self.assertEqual(Path(os.environ["BSMART_PROJECT_ROOT"]).resolve(), spec_root.resolve())


class SessionHookTests(unittest.TestCase):
    def setUp(self):
        self.session = load("client_session_start", SYSTEM / "integrations" / "client_session_start.py")

    def test_payload_shapes(self):
        cursor = self.session.payload("cursor", "hello")
        claude = self.session.payload("claude", "hello")
        self.assertEqual(cursor["additional_context"], "hello")
        self.assertEqual(claude["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertEqual(claude["hookSpecificOutput"]["additionalContext"], "hello")
        self.assertEqual(self.session.payload("codex", "hello"), claude)

    def test_cursor_context_asks_for_a_fence(self):
        cursor = self.session.context_text("Hi, there!", 0, "cursor")
        claude = self.session.context_text("Hi, there!", 0, "claude")
        self.assertIn("fenced code block with no language tag", cursor)
        self.assertNotIn("fenced code block", claude)
        self.assertEqual(claude, self.session.context_text("Hi, there!", 0, "codex"))

    def test_missing_workspace_does_not_run_bstart(self):
        with patch.object(self.session, "workspace_from", return_value=None), \
             patch.object(self.session, "run_bstart") as run_bstart, \
             patch("sys.stdin", io.StringIO("{}")):
            buffer = io.BytesIO()
            with patch.object(self.session.sys, "stdout") as stdout:
                stdout.buffer = buffer
                code = self.session.main(["--client", "cursor"])
        self.assertEqual(code, 0)
        run_bstart.assert_not_called()
        self.assertIn("could not find", json.loads(buffer.getvalue().decode())["additional_context"])

    def test_plugin_copies_match_the_canonical_hook(self):
        canonical = (SYSTEM / "integrations" / "client_session_start.py").read_bytes()
        for relative in (
            "integrations/cursor/bsmart-plugin/scripts/session_start.py",
            "integrations/codex/bsmart-plugin/scripts/session_start.py",
            "integrations/claude/bsmart-plugin/scripts/session_start.py",
        ):
            self.assertEqual((SYSTEM / relative).read_bytes(), canonical)

    def test_manifests_and_cursor_workspace_commands(self):
        manifests = {
            "integrations/cursor/bsmart-plugin/.cursor-plugin/plugin.json": "bsmart",
            "integrations/codex/bsmart-plugin/plugin.json": "bsmart",
            "integrations/codex/bsmart-plugin/.codex-plugin/plugin.json": "bsmart",
            "integrations/claude/bsmart-plugin/.claude-plugin/plugin.json": "bsmart",
        }
        for relative, name in manifests.items():
            data = json.loads((SYSTEM / relative).read_text(encoding="utf-8"))
            self.assertEqual(data["name"], name)
        plugin_commands = SYSTEM / "integrations" / "cursor" / "bsmart-plugin" / "commands"
        self.assertTrue((plugin_commands / "project.md").is_file())
        self.assertTrue((plugin_commands / "role.md").is_file())
        self.assertFalse((plugin_commands / "projcet.md").exists())
        for installed in (SYSTEM / ".cursor" / "commands", SYSTEM.parent / ".cursor" / "commands"):
            if not (installed / "project.md").is_file():
                continue
            for name in ("project.md", "role.md"):
                self.assertEqual((installed / name).read_text(encoding="utf-8"), (plugin_commands / name).read_text(encoding="utf-8"))
            self.assertFalse((installed / "projcet.md").exists())

    def test_session_hook_preserves_characters_outside_cp1252(self):
        workspace = Path(tempfile.mkdtemp(prefix="bsmart-hook-encoding-"))
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        system = workspace / "bSmart-System"
        system.mkdir()
        shutil.copy(SYSTEM / "bStart.py", system / "bStart.py")
        content = workspace / "bSmart"
        content.mkdir()
        marker = "\u2610"
        (content / "bSmart_Agent.md").write_text(
            "# Agent\n\n```yaml\nagent:\n  name: TestAgent\n  operator: Test User\n```\n\n" + marker + " open item\n",
            encoding="utf-8",
        )
        projects = workspace / "projects"
        projects.mkdir()
        env = dict(os.environ)
        env["PYTHONUTF8"] = "0"
        env["PYTHONIOENCODING"] = "cp1252:strict"
        env["BSMART_PROJECT_ROOT"] = str(projects)
        result = subprocess.run(
            [sys.executable, str(SYSTEM / "integrations" / "client_session_start.py"), "--client", "cursor"],
            input=json.dumps({"cwd": str(workspace)}).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(workspace),
            check=False,
        )
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertEqual(result.returncode, 0, stderr)
        payload = json.loads(result.stdout.decode("utf-8"))
        text = payload["additional_context"]
        self.assertIn("bStart.py finished.", text)
        self.assertIn(marker + " open item", text)
        self.assertNotIn("UnicodeEncodeError", text)

    def test_session_hooks_fall_back_when_python3_fails(self):
        for relative in (
            "integrations/cursor/bsmart-plugin/hooks/hooks.json",
            "integrations/codex/bsmart-plugin/hooks/hooks.json",
            "integrations/claude/bsmart-plugin/hooks/hooks.json",
        ):
            text = (SYSTEM / relative).read_text(encoding="utf-8")
            self.assertIn("python3", text)
            self.assertIn("|| python ", text)
            self.assertIn("py -3", text)


if __name__ == "__main__":
    unittest.main()
