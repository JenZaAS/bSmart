from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN = Path(__file__).parents[1] / "integrations/hermes/bprotective-plugin/__init__.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("bprotective_plugin_test", PLUGIN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeContext:
    def __init__(self):
        self.commands = {}
        self.hooks = {}

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = {"handler": handler, "description": description, "args_hint": args_hint}

    def register_hook(self, name, handler):
        self.hooks[name] = handler


class BProtectiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bprotective-")
        self.home = Path(self.tmp.name)
        self.state = self.home / "bprotective.json"
        self.env = {"BPROTECTIVE_STATE_FILE": str(self.state)}
        self.plugin = load_plugin()
        self.ctx = FakeContext()
        self.plugin.register(self.ctx)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, args=""):
        with patch.dict(os.environ, self.env, clear=False):
            return self.ctx.commands["bprotective"]["handler"](args)

    def hook(self, tool_name="terminal", args=None):
        with patch.dict(os.environ, self.env, clear=False):
            return self.ctx.hooks["pre_tool_call"](
                tool_name=tool_name,
                args=args or {},
                task_id="task",
                session_id="session",
            )

    def test_registers_hermes_hook_and_control_command(self):
        self.assertIn("pre_tool_call", self.ctx.hooks)
        self.assertIn("bprotective", self.ctx.commands)
        self.assertEqual(self.call(), "bProtective is off.")

    def test_enable_requires_confirmation_then_blocks_dangerous_commands(self):
        prompt = self.call("on")
        self.assertIn("Confirmation required", prompt)
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.assertIn("enabled", self.call(f"yes {confirmation_id}"))
        self.assertEqual(self.call(), "bProtective is on.")
        decision = self.hook(args={"command": "rm -rf /"})
        self.assertEqual(decision["action"], "block")

    def test_disable_requires_confirmation(self):
        prompt = self.call("on")
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.call(f"yes {confirmation_id}")
        prompt = self.call("off")
        self.assertIn("Confirmation required", prompt)
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.assertIn("disabled", self.call(f"yes {confirmation_id}"))
        self.assertIsNone(self.hook(args={"command": "rm -rf /"}))

    def test_safe_command_is_allowed_and_risky_command_escalates(self):
        prompt = self.call("on")
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.call(f"yes {confirmation_id}")
        self.assertIsNone(self.hook(args={"command": "git status"}))
        decision = self.hook(args={"command": "docker compose down"})
        self.assertEqual(decision["action"], "approve")

    def test_shell_variants_are_blocked_or_escalated(self):
        prompt = self.call("on")
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.call(f"yes {confirmation_id}")
        self.assertEqual(self.hook(args={"command": "rm -rf / --no-preserve-root"})["action"], "block")
        self.assertEqual(self.hook(args={"command": "git push --force origin main"})["action"], "block")
        self.assertEqual(self.hook(args={"command": "sudo lsof -i :3000"})["action"], "approve")

    def test_invalid_state_fails_closed(self):
        self.state.write_text("not json", encoding="utf-8")
        decision = self.hook(args={"command": "printf safe"})
        self.assertEqual(decision["action"], "block")
        self.assertIsNone(self.hook(tool_name="read_file", args={"path": "/etc/shadow"}))

    def test_private_state_write_succeeds(self):
        self.call("on")
        self.assertTrue(self.state.is_file())
        if os.name != "nt":
            mode = stat.S_IMODE(self.state.stat().st_mode)
            self.assertEqual(mode & 0o077, 0)

    def test_windows_acl_uses_full_icacls_and_survives_timeout(self):
        fd, name = tempfile.mkstemp(prefix="bprotective-acl-", dir=self.home)
        os.close(fd)
        calls: list[tuple[list[str], dict]] = []

        def fake_run(args, **kwargs):
            calls.append((list(args), kwargs))
            raise self.plugin.subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 10))

        patches = [
            patch.object(self.plugin.os, "name", "nt"),
            patch.dict(self.plugin.os.environ, {"USERNAME": "TestUser", "SystemRoot": r"C:\Windows"}, clear=False),
            patch.object(self.plugin.subprocess, "run", side_effect=fake_run),
        ]
        if hasattr(self.plugin.os, "fchmod"):
            patches.append(patch.object(self.plugin.os, "fchmod", lambda *_args, **_kwargs: None))
        for item in patches:
            item.start()
        try:
            self.plugin._restrict_private(fd, name)
        finally:
            for item in reversed(patches):
                item.stop()
        self.assertEqual(len(calls), 1)
        argv, kwargs = calls[0]
        self.assertEqual(argv[0], r"C:\Windows\System32\icacls.exe")
        self.assertEqual(argv[-1], "TestUser:(R,W,D)")
        self.assertEqual(kwargs["timeout"], 10)

    def test_non_terminal_tools_are_ignored(self):
        prompt = self.call("on")
        confirmation_id = prompt.rsplit(" ", 1)[-1]
        self.call(f"yes {confirmation_id}")
        self.assertIsNone(self.hook(tool_name="read_file", args={"path": "/etc/shadow"}))


if __name__ == "__main__":
    unittest.main()
