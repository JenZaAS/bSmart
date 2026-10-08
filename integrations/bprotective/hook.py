"""Map a bProtective decision onto Cursor, Claude Code, and Codex hook responses.

Formats follow the vendor docs checked on 2026-10-08. These adapters are not
live-tested in those products; see integrations/bprotective/README.md.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_SHELL_TOOLS = {"bash", "powershell", "shell", "terminal", "cmd"}
_IGNORE_TOOLS = {"apply_patch", "edit", "write", "read", "grep", "glob"}


def load_core() -> Any:
    name = "bprotective_core"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().with_name("core.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"bProtective core not found: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def command_from(adapter: str, payload: dict[str, Any]) -> str | None:
    """Return the shell command, or None when this payload is not a shell call."""
    if adapter == "cursor":
        command = payload.get("command")
        return command if isinstance(command, str) else None
    tool_name = str(payload.get("tool_name") or "").lower()
    if tool_name in _IGNORE_TOOLS:
        return None
    if tool_name and tool_name not in _SHELL_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            return None
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        return command if isinstance(command, str) else None
    return None


def respond(adapter: str, payload: dict[str, Any], core: Any | None = None) -> dict[str, Any] | None:
    """Return the hook JSON object, or None when the harness should see no decision."""
    core = core or load_core()
    command = command_from(adapter, payload)
    if command is None or not command.strip():
        return {"permission": "allow"} if adapter == "cursor" else None
    try:
        decision = core.guard(command)
    except Exception as exc:  # noqa: BLE001 — a hook crash must still return a decision
        decision = core.Decision("block", "hook-error", f"bProtective hook failed: {exc}")
    if decision.action == "allow":
        return {"permission": "allow"} if adapter == "cursor" else None
    if adapter == "cursor":
        permission = "deny" if decision.action == "block" else "ask"
        return {"permission": permission, "user_message": decision.message, "agent_message": decision.message}
    if adapter == "claude":
        permission = "deny" if decision.action == "block" else "ask"
        return _tool_decision(permission, decision.message)
    if adapter == "codex":
        message = decision.message
        if decision.action == "escalate":
            try:
                token = core.request_command_approval(command)
            except OSError:
                token = ""
            if token:
                message = f"{decision.message} Reply: bprotective yes {token}"
        return _tool_decision("deny", message)
    raise ValueError(f"Unknown bProtective adapter: {adapter}")


def _tool_decision(permission: str, message: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": message,
        }
    }


def main(argv: list[str] | None = None) -> int:
    load_core().configure_output_streams()
    parser = argparse.ArgumentParser(description="bProtective pre-execution hook.")
    parser.add_argument("--adapter", required=True, choices=("cursor", "claude", "codex"))
    args = parser.parse_args(argv)
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    result = respond(args.adapter, payload)
    if result is not None:
        sys.stdout.write(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
