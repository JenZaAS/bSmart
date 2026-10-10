"""bProtective command-line check and on/off confirmation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_EXIT = {"allow": 0, "escalate": 1, "block": 2}


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


def main(argv: list[str] | None = None) -> int:
    core = load_core()
    core.configure_output_streams()
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "check":
        return _check(core, args[1:])
    json_output = "--json" in args
    control = [item for item in args if item != "--json"]
    if json_output and (not control or control == ["status"]):
        return _status_json(core)
    text, code = core.handle_control(control, reply_prefix="bprotective")
    print(text)
    return code


def _check(core: Any, args: list[str]) -> int:
    json_output = False
    if "--" in args:
        split = args.index("--")
        flags = args[:split]
        command_args = args[split + 1 :]
    else:
        flags = [item for item in args if item.startswith("-")]
        command_args = [item for item in args if not item.startswith("-")]
    if flags not in ([], ["--json"]):
        print("Usage: bprotective check [--json] -- <command>", file=sys.stderr)
        return 3
    json_output = flags == ["--json"]
    command = " ".join(command_args).strip()
    if not command:
        print("Usage: bprotective check [--json] -- <command>", file=sys.stderr)
        return 3
    decision = core.guard(command)
    state = core.read_state()
    payload = {
        "decision": decision.action,
        "rule_key": decision.rule_key,
        "reason": decision.reason,
        "message": decision.message,
        "enabled": bool(state.get("enabled")) and not state.get("error"),
    }
    if state.get("error"):
        payload["enabled"] = None
        payload["state_error"] = state["error"]
    if json_output:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        print(f"{decision.action}: {decision.message}")
    return _EXIT[decision.action]


def _status_json(core: Any) -> int:
    state = core.read_state()
    if state.get("error"):
        print(json.dumps({"enabled": None, "pending": False, "error": state["error"]}, sort_keys=True))
        return 1
    pending = state.get("pending") or state.get("command_pending")
    print(json.dumps({"enabled": bool(state.get("enabled")), "pending": bool(pending)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
