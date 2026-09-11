"""Hermes adapter and local policy core for bProtective."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any

_DEFAULT_STATE = Path.home() / ".hermes" / "bprotective.json"
_TERMINAL_TOOLS = {"terminal", "shell", "bash", "execute_shell"}

_BLOCK_RULES = (
    ("root-recursive-delete", re.compile(r"\brm\b(?:(?!\n).)*\s-[^\s]*r[^\s]*f[^\s]*\s+(?:/|/\*|~(?:/\*)?|\$HOME(?:/\*)?)(?:\s|$)", re.I), "recursive deletion of a protected root or home path"),
    ("device-format", re.compile(r"\b(?:mkfs(?:\.[\w-]+)?|diskutil\s+(?:eraseDisk|partitionDisk))\b|\bdd\b(?:(?!\n).)*\bof\s*=\s*/dev/", re.I), "disk formatting or raw-device overwrite"),
    ("fork-bomb", re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.I), "fork bomb"),
    ("secret-export", re.compile(r"\b(?:bw|bws|lpass|keepassxc-cli|rbw|nordpass|pass)\b|\b(?:op\s+(?:read|run|inject|document)|security\s+(?:find|dump-keychain))\b|\bgpg\s+--export-secret", re.I), "credential or secret-store access"),
    ("remote-installer", re.compile(r"\b(?:curl|wget)\b(?:(?!\n).)*(?:\||;|&&)\s*(?:sudo\s+)?(?:sh|bash|zsh)\b", re.I), "piped remote script execution"),
    ("destructive-git", re.compile(r"\bgit\s+(?:push\b(?:(?!\n).)*(?:--force\s*|\s-f\b)|reflog\s+expire\b|gc\b(?:(?!\n).)*--prune(?:=now|=all))|\bgh\s+(?:repo|release|secret|ssh-key|gpg-key)\s+delete\b", re.I), "destructive Git or GitHub history/resource operation"),
)

_APPROVAL_RULES = (
    ("privileged-command", re.compile(r"(?:^|[;&|]\s*)sudo\b|\b(?:systemctl|service|ufw|iptables|nft)\b", re.I), "privileged service or firewall operation"),
    ("docker-runtime", re.compile(r"\bdocker\b|\bdokploy\b", re.I), "Docker or Dokploy runtime operation"),
    ("permissions", re.compile(r"\b(?:chmod|chown|chgrp|setfacl)\b", re.I), "permission or ownership change"),
    ("external-publication", re.compile(r"\bgit\s+push\b|\bgh\s+(?:pr|release|repo|issue)\b", re.I), "external Git or GitHub operation"),
    ("package-install", re.compile(r"\b(?:apt|apt-get|brew|npm|pnpm|yarn|pip|uv)\s+(?:install|add)\b", re.I), "package installation"),
)


def _state_path() -> Path:
    return Path(os.environ.get("BPROTECTIVE_STATE_FILE", str(_DEFAULT_STATE))).expanduser().resolve()


def _read_state() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {"enabled": False, "pending": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "pending": None, "error": "state file is unreadable"}
    return value if isinstance(value, dict) else {"enabled": False, "pending": None, "error": "state file is invalid"}


def _write_state(value: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _confirmation(operation: str) -> str:
    state = _read_state()
    token = secrets.token_urlsafe(12)
    state["pending"] = {"id": token, "operation": operation, "expires_at": int(time.time()) + 300}
    _write_state(state)
    return token


def _command(raw_args: str) -> str:
    return (raw_args or "").strip()


def _handle_command(raw_args: str) -> str:
    args = _command(raw_args).split()
    state = _read_state()
    if state.get("error"):
        return f"bProtective unavailable: {state['error']}."
    if not args or args == ["status"]:
        return f"bProtective is {'on' if state.get('enabled') else 'off'}."
    if args in (["on"], ["off"]):
        operation = args[0]
        if bool(state.get("enabled")) == (operation == "on"):
            return f"bProtective is already {operation}."
        token = _confirmation(operation)
        return f"Confirmation required to turn bProtective {operation}. Reply: /bprotective yes {token}"
    if len(args) == 2 and args[0] == "yes":
        pending = state.get("pending") or {}
        if not pending or pending.get("id") != args[1]:
            return "No matching bProtective confirmation; it may be missing or already used."
        if int(pending.get("expires_at", 0)) < int(time.time()):
            state["pending"] = None
            _write_state(state)
            return "bProtective confirmation expired; request the change again."
        if pending.get("operation") not in {"on", "off"}:
            return "Invalid bProtective confirmation."
        state["enabled"] = pending["operation"] == "on"
        state["pending"] = None
        _write_state(state)
        return f"bProtective {pending['operation']} enabled." if state["enabled"] else "bProtective off; guard disabled."
    if len(args) == 2 and args[0] == "no":
        pending = state.get("pending") or {}
        if not pending or pending.get("id") != args[1]:
            return "No matching bProtective confirmation; it may be missing or already used."
        state["pending"] = None
        _write_state(state)
        return "bProtective change cancelled."
    return "Usage: /bprotective [status|on|off|yes ID|no ID]"


def evaluate(command: str) -> dict[str, str] | None:
    """Return a Hermes pre_tool_call directive, or None to allow."""
    for rule_key, pattern, reason in _BLOCK_RULES:
        if pattern.search(command):
            return {"action": "block", "rule_key": rule_key, "message": f"bProtective blocked this command: {reason}."}
    for rule_key, pattern, reason in _APPROVAL_RULES:
        if pattern.search(command):
            return {"action": "approve", "rule_key": rule_key, "message": f"bProtective requires operator approval: {reason}."}
    return None


def _pre_tool_call(*, tool_name: str = "", args: dict[str, Any] | None = None, **_: Any) -> dict[str, str] | None:
    state = _read_state()
    if tool_name not in _TERMINAL_TOOLS:
        return None
    if state.get("error"):
        return {"action": "block", "rule_key": "state-invalid", "message": "bProtective blocked the command because its policy state is unreadable."}
    if not state.get("enabled"):
        return None
    payload = args or {}
    command = payload.get("command") or payload.get("cmd") or ""
    return evaluate(str(command)) if command else None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_command(
        "bprotective",
        _handle_command,
        "Enable, disable, inspect, and approve bProtective command protection.",
        "[status|on|off|yes ID|no ID]",
    )
