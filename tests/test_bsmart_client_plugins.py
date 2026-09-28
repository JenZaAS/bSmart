from __future__ import annotations

import importlib.util
import io
import json
import os
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


SELECTOR = "# bSmart current role\n\n```yaml\nrole_selection:\n  current_role: general\n```\n"
ROLE = (
    "# bSmart role\n\n```yaml\nstate:\n"
    "  active_project: \"none\"\n"
    "  active_workstream: \"none\"\n```\n"
)


class ClientAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = load("bsmart_client_adapter", SYSTEM / "integrations" / "bsmart_client_adapter.py")
        self.tmp = tempfile.TemporaryDirectory(prefix="bsmart-client-adapter-")
        home = Path(self.tmp.name)
        self.projects = home / "projects"
        self.roles = home / "roles"
        self.projects.mkdir()
        self.roles.mkdir()
        (self.roles / "current_role.md").write_text(SELECTOR, encoding="utf-8")
        (self.roles / "general_role.md").write_text(ROLE, encoding="utf-8")
        self.env = {
            "BSMART_SYSTEM_ROOT": str(SYSTEM),
            "BSMART_PROJECT_ROOT": str(self.projects),
            "BSMART_ROLES_ROOT": str(self.roles),
            "BSMART_ROLE_SELECTOR": str(self.roles / "current_role.md"),
            "BSMART_LEGACY_STATE_FILE": str(home / "bSmart_State.md"),
            "BSMART_ARCHIVE_ROOT": str(home / "archives"),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_adapter(self, kind: str, args: list[str]) -> str:
        with patch.dict(os.environ, self.env, clear=False):
            return self.adapter.run(kind, args, workspace=Path(self.tmp.name))

    def test_lists_and_creates_in_the_isolated_root(self):
        listed = self.run_adapter("project", ["list"])
        self.assertIn("Projects:", listed)
        self.assertIn("Free Mode", listed)
        created = self.run_adapter("project", ["add", "Alpha"])
        self.assertIn("Alpha", created)
        self.assertTrue((self.projects / "Alpha" / "project.md").is_file())
        self.assertIn("- Alpha (current)", self.run_adapter("projcet", ["list"]))

    def test_role_help_uses_the_shared_engine(self):
        self.assertIn("/role help", self.run_adapter("role", []))

    def test_flags_are_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.command_text("project", ["--root", "C:/elsewhere"])


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
        workspace = SYSTEM.parent / ".cursor" / "commands"
        plugin_commands = SYSTEM / "integrations" / "cursor" / "bsmart-plugin" / "commands"
        for name in ("project.md", "projcet.md", "role.md"):
            self.assertEqual((workspace / name).read_text(encoding="utf-8"), (plugin_commands / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
