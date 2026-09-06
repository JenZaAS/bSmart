from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN = Path(__file__).parents[1] / "integrations/hermes/bsmart-project-plugin/__init__.py"
SYSTEM_ROOT = Path(__file__).parents[1]


def load_plugin():
    spec = importlib.util.spec_from_file_location("bsmart_project_plugin_test", PLUGIN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeContext:
    def __init__(self):
        self.commands = {}

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = {
            "handler": handler,
            "description": description,
            "args_hint": args_hint,
        }


class ProjectPluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bsmart-hermes-plugin-")
        home = Path(self.tmp.name)
        self.projects = home / "projects"
        self.projects.mkdir()
        self.state = home / "bSmart_State.md"
        self.state.write_text(
            "# bSmart state\n- Mode: `Free Mode`\n- Active project (short name): `none`\n",
            encoding="utf-8",
        )
        self.env = {
            "BSMART_SYSTEM_ROOT": str(SYSTEM_ROOT),
            "BSMART_PROJECT_ROOT": str(self.projects),
            "BSMART_STATE_FILE": str(self.state),
            "BSMART_ARCHIVE_ROOT": str(home / "archives"),
        }
        self.plugin = load_plugin()
        self.ctx = FakeContext()
        self.plugin.register(self.ctx)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, command, args=""):
        with patch.dict(os.environ, self.env, clear=False):
            return self.ctx.commands[command]["handler"](args)

    def test_registers_both_commands_and_lists(self):
        self.assertEqual(set(self.ctx.commands), {"project", "projcet"})
        self.assertIn("Projects:", self.call("project"))
        self.assertIn("Free Mode", self.call("projcet", "list"))

    def test_real_cross_process_yes_continuation(self):
        self.assertIn("Project created", self.call("project", "add Alpha"))
        prompt = self.call("project", "rename Beta")
        self.assertIn("Confirmation required: rename exact target", prompt)
        yes_line = next(line for line in prompt.splitlines() if line.startswith("Yes:"))
        pending_id = yes_line.rsplit(" ", 1)[1]
        result = self.call("project", f"yes {pending_id}")
        self.assertIn("Current: Beta", result)
        self.assertTrue((self.projects / "Beta").is_dir())
        self.assertFalse((self.projects / "Alpha").exists())

    def test_real_no_continuation_via_typo_alias(self):
        self.call("project", "add Keep")
        prompt = self.call("projcet", "delete")
        pending_id = next(line for line in prompt.splitlines() if line.startswith("No:")).rsplit(" ", 1)[1]
        result = self.call("projcet", f"no {pending_id}")
        self.assertIn("Cancelled", result)
        self.assertTrue((self.projects / "Keep").is_dir())

    def test_chat_arguments_cannot_override_context(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        response = self.call("project", f"list --projectsRoot {other}")
        self.assertIn("failed", response.lower())
        self.assertEqual(json.loads((Path(self.tmp.name) / ".bsmart-project-pending.json").read_text()) if (Path(self.tmp.name) / ".bsmart-project-pending.json").exists() else None, None)


if __name__ == "__main__":
    unittest.main()
