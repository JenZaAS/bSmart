"""Hermes adapter for the shared bProtective core."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_TERMINAL_TOOLS = {"terminal", "shell", "bash", "execute_shell"}


def _core_dir() -> Path:
    candidates: list[Path] = []
    if os.environ.get("BPROTECTIVE_CORE"):
        candidates.append(Path(os.environ["BPROTECTIVE_CORE"]).expanduser())
    if os.environ.get("BSMART_SYSTEM_ROOT"):
        candidates.append(Path(os.environ["BSMART_SYSTEM_ROOT"]).expanduser() / "integrations" / "bprotective")
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / "bprotective")
    for parent in here.parents:
        candidates.append(parent / "integrations" / "bprotective")
        candidates.append(parent / "bSmart-System" / "integrations" / "bprotective")
    candidates.append(Path("/workspace/bSmart-System/integrations/bprotective"))
    for candidate in candidates:
        if (candidate / "core.py").is_file():
            return candidate
    raise ImportError("bProtective core not found. Set BSMART_SYSTEM_ROOT to the bSmart-System checkout.")


def _load_core() -> Any:
    name = "bprotective_core"
    cached = sys.modules.get(name)
    if cached is not None and hasattr(cached, "guard"):
        return cached
    path = _core_dir() / "core.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"bProtective core not found: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_core = _load_core()


def evaluate(command: str) -> dict[str, str] | None:
    """Return a Hermes directive for the built-in and instance policy, ignoring the on/off gate."""
    config, error = _core.load_config()
    if error:
        return _core.to_hermes(_core.Decision("block", "config-invalid", error))
    return _core.to_hermes(_core.policy_decision(command, config))


def _handle_command(raw_args: str) -> str:
    args = (raw_args or "").strip().split()
    text, _code = _core.handle_control(args, reply_prefix="/bprotective")
    return text


def _pre_tool_call(*, tool_name: str = "", args: dict[str, Any] | None = None, **_: Any) -> dict[str, str] | None:
    if tool_name not in _TERMINAL_TOOLS:
        return None
    payload = args or {}
    command = payload.get("command") or payload.get("cmd") or ""
    if not command:
        return None
    return _core.to_hermes(_core.guard(str(command)))


def register(ctx: Any) -> None:
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_command(
        "bprotective",
        _handle_command,
        "Enable, disable, inspect, and approve bProtective command protection.",
        "[status|on|off|yes ID|no ID]",
    )
