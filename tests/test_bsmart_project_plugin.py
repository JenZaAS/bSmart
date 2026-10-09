from __future__ import annotations

import importlib.util
import json
import os
import shutil
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
        self.env = {
            "BSMART_SYSTEM_ROOT": str(SYSTEM_ROOT),
            "BSMART_PROJECT_ROOT": str(self.projects),
            "BSMART_ARCHIVE_ROOT": str(home / "archives"),
            "BSMART_INSTANCE_HOME": str(home),
        }
        self.plugin = load_plugin()
        self.ctx = FakeContext()
        self.plugin.register(self.ctx)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, command, args=""):
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
            return self.ctx.commands[command]["handler"](args)

    def test_registers_project_and_deprecated_role_and_lists(self):
        self.assertEqual(set(self.ctx.commands), {"project", "role"})
        self.assertIn("Projects:", self.call("project"))
        self.assertIn("Free Mode", self.call("project", "list"))
        self.assertIn("deprecated", self.call("role", "list").lower())
        self.assertIn("/project", self.call("role"))

    def test_real_cross_process_yes_continuation(self):
        self.assertIn("Project created", self.call("project", "add Alpha"))
        self.env["BSMART_SESSION_PROJECT"] = "Alpha"
        prompt = self.call("project", "rename Beta")
        self.assertIn("Confirmation required: rename exact target", prompt)
        yes_line = next(line for line in prompt.splitlines() if line.startswith("Yes:"))
        pending_id = yes_line.rsplit(" ", 1)[1]
        result = self.call("project", f"yes {pending_id}")
        self.assertIn("Current: Beta", result)
        self.assertTrue((self.projects / "Beta").is_dir())
        self.assertFalse((self.projects / "Alpha").exists())

    def test_two_sessions_do_not_share_a_selector(self):
        self.call("project", "add Alpha")
        self.call("project", "add Beta handoff: left Alpha")
        self.assertFalse((Path(self.tmp.name) / "Roles" / "current_role.md").exists())
        env_a = dict(self.env)
        env_b = dict(self.env)
        env_a["BSMART_SESSION_PROJECT"] = "Alpha"
        env_b["BSMART_SESSION_PROJECT"] = "Beta"
        with patch.dict(os.environ, env_a, clear=False):
            os.environ.pop("BSMART_SESSION_ID", None)
            listed_a = self.ctx.commands["project"]["handler"]("list")
        with patch.dict(os.environ, env_b, clear=False):
            os.environ.pop("BSMART_SESSION_ID", None)
            listed_b = self.ctx.commands["project"]["handler"]("list")
        self.assertIn("- Alpha (current)", listed_a)
        self.assertNotIn("- Beta (current)", listed_a)
        self.assertIn("- Beta (current)", listed_b)
        self.assertNotIn("- Alpha (current)", listed_b)
        self.assertFalse((Path(self.tmp.name) / "Roles" / "current_role.md").exists())

    def test_select_then_delete_without_a_session_env(self):
        self.assertIn("Current: Gamma", self.call("project", "add Gamma"))
        prompt = self.call("project", "delete")
        self.assertIn("Confirmation required: delete exact target", prompt)
        pending_id = next(line for line in prompt.splitlines() if line.startswith("Yes:")).rsplit(" ", 1)[1]
        result = self.call("project", f"yes {pending_id}")
        self.assertIn("Free Mode", result)
        self.assertFalse((self.projects / "Gamma").exists())
        stored = json.loads((Path(self.tmp.name) / "State" / "sessions" / "channel-client.json").read_text(encoding="utf-8"))
        self.assertIsNone(stored["project"])

    def test_real_no_continuation(self):
        self.call("project", "add Keep")
        self.env["BSMART_SESSION_PROJECT"] = "Keep"
        prompt = self.call("project", "delete")
        pending_id = next(line for line in prompt.splitlines() if line.startswith("No:")).rsplit(" ", 1)[1]
        result = self.call("project", f"no {pending_id}")
        self.assertIn("Cancelled", result)
        self.assertTrue((self.projects / "Keep").is_dir())

    def test_storage_spec_selects_the_project_root_when_env_is_unset(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            system = workspace / "bSmart-System" / "scripts"
            system.mkdir(parents=True)
            shutil.copy2(SYSTEM_ROOT / "scripts" / "bsmart_instance.py", system / "bsmart_instance.py")
            spec_root = workspace / "from-spec"
            spec_root.mkdir()
            (workspace / "projects").mkdir()
            spec = workspace / "bSmart" / "State" / "container-storage.yaml"
            spec.parent.mkdir(parents=True)
            spec.write_text("project_storage:\n  project_root: ./from-spec\n", encoding="utf-8")
            env = dict(self.env)
            env.pop("BSMART_PROJECT_ROOT", None)
            env["BSMART_SYSTEM_ROOT"] = str(workspace / "bSmart-System")
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop("BSMART_PROJECT_ROOT", None)
                selected = Path(self.plugin._context()["projectsRoot"]).resolve()
            self.assertEqual(selected, spec_root.resolve())

    def test_installed_copy_reads_the_spec_without_system_root_env(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            system = workspace / "bSmart-System"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(SYSTEM_ROOT / "scripts" / "bsmart_instance.py", scripts / "bsmart_instance.py")
            spec_root = workspace / "from-spec"
            spec_root.mkdir()
            (workspace / "projects").mkdir()
            spec = workspace / "bSmart" / "State" / "container-storage.yaml"
            spec.parent.mkdir(parents=True)
            spec.write_text("project_storage:\n  project_root: ./from-spec\n", encoding="utf-8")
            installed = workspace / "hermes-home" / "plugins" / "bsmart-project" / "__init__.py"
            installed.parent.mkdir(parents=True)
            shutil.copy2(PLUGIN, installed)
            spec_mod = importlib.util.spec_from_file_location("bsmart_project_plugin_installed", installed)
            assert spec_mod is not None and spec_mod.loader is not None
            plugin = importlib.util.module_from_spec(spec_mod)
            spec_mod.loader.exec_module(plugin)
            plugin._DEFAULT_SYSTEM_ROOT = str(system)
            env = os.environ.copy()
            env.pop("BSMART_SYSTEM_ROOT", None)
            env.pop("BSMART_PROJECT_ROOT", None)
            with patch.dict(os.environ, env, clear=True):
                selected = Path(plugin._projects_root()).resolve()
            self.assertEqual(selected, spec_root.resolve())
            self.assertFalse((workspace / "scripts" / "bsmart_instance.py").exists())

    def test_chat_arguments_cannot_override_context(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        response = self.call("project", f"list --projectsRoot {other}")
        self.assertIn("failed", response.lower())
        self.assertEqual(json.loads((Path(self.tmp.name) / ".bsmart-project-pending.json").read_text()) if (Path(self.tmp.name) / ".bsmart-project-pending.json").exists() else None, None)


if __name__ == "__main__":
    unittest.main()
