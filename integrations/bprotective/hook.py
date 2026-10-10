"""Map a bProtective decision onto Cursor, Claude Code, and Codex hook responses.

Formats follow the vendor docs checked on 2026-10-08. These adapters are not
live-tested in those products; see integrations/bprotective/README.md.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

_SHELL_TOOLS = {"bash", "powershell", "shell", "terminal", "cmd"}
_PATH_KEYS = {"file_path", "path", "target_file", "filepath", "file"}
_PATCH_FILE_RE = re.compile(r"(?m)^\*\*\* (?:Update|Add|Delete) File: (.+)$")


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
        if isinstance(command, str):
            return command
    tool_name = str(payload.get("tool_name") or "").lower()
    if tool_name and tool_name not in _SHELL_TOOLS and adapter != "cursor":
        return None
    tool_input = _tool_input(payload)
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str) and (adapter == "cursor" or not tool_name or tool_name in _SHELL_TOOLS):
            return command
    return None


def _tool_input(payload: dict[str, Any]) -> Any:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, str):
        try:
            return json.loads(tool_input)
        except json.JSONDecodeError:
            return tool_input
    return tool_input


def edited_paths(payload: dict[str, Any]) -> list[str]:
    """Paths a Write, Edit, or apply_patch payload would change."""
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in _PATH_KEYS and isinstance(value, str):
                    found.append(value)
                elif key == "command" and isinstance(value, str):
                    found.extend(match.group(1).strip() for match in _PATCH_FILE_RE.finditer(value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def _deny(adapter: str, message: str, *, event: str = "pretool") -> dict[str, Any]:
    if adapter == "cursor":
        return {"permission": "deny", "user_message": message, "agent_message": message}
    if event == "permission":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": message},
            }
        }
    return _tool_decision("deny", message)


def respond(adapter: str, payload: dict[str, Any], core: Any | None = None) -> dict[str, Any] | None:
    """Return the hook JSON object, or None when the harness should see no decision."""
    core = core or load_core()
    try:
        guarded = _guard_edit(adapter, payload, core)
    except Exception as exc:  # noqa: BLE001 — a hook crash must still return a decision
        guarded = _deny(adapter, f"bProtective hook failed: {exc}")
    if guarded is not None:
        return guarded
    command = command_from(adapter, payload)
    if command is None or not command.strip():
        return {"permission": "allow"} if adapter == "cursor" else None
    try:
        decision = core.guard(command, via_hook=True)
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
        # ask is parsed and then ignored, so the tool would run. Return no
        # decision for an escalation and let PermissionRequest show the prompt.
        # The reason is model-visible. It must not carry an approval token.
        if decision.action == "block":
            return _tool_decision("deny", decision.message)
        return None
    raise ValueError(f"Unknown bProtective adapter: {adapter}")


def _guard_edit(adapter: str, payload: dict[str, Any], core: Any, *, event: str = "pretool") -> dict[str, Any] | None:
    paths = edited_paths(payload)
    if not paths:
        return None
    for path in paths:
        if core.path_targets_guard(path):
            return _deny(
                adapter,
                "bProtective blocked this command: write to a bProtective state or armed-record path.",
                event=event,
            )
    return None


def respond_permission(payload: dict[str, Any], core: Any | None = None) -> dict[str, Any] | None:
    """Codex PermissionRequest. Never auto-allow, and never return a token.

    A block or a shell attempt to change the guard is denied. An escalation
    returns no decision so Codex keeps the operator prompt. An allow returns
    no decision so this hook does not skip Codex's own approval prompt.
    """
    core = core or load_core()
    guarded = _guard_edit("codex", payload, core, event="permission")
    if guarded is not None:
        return guarded
    command = command_from("codex", payload)
    if command is None or not command.strip():
        return None
    try:
        decision = core.guard(command, via_hook=True)
    except Exception as exc:  # noqa: BLE001
        decision = core.Decision("block", "hook-error", f"bProtective hook failed: {exc}")
    if decision.action == "block":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": decision.message},
            }
        }
    return None


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
    parser.add_argument("--event", default="pretool", choices=("pretool", "permission"))
    args = parser.parse_args(argv)
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if args.event == "permission":
        result = respond_permission(payload)
    else:
        result = respond(args.adapter, payload)
    if result is not None:
        sys.stdout.write(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
