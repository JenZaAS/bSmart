"""Dependency-free bProtective policy, state, and confirmation gate.

The Hermes plugin, the CLI, and the hook adapters all call this module.
Protection stays off until an operator confirms `on`. Instance config can add
protected paths and patterns; it cannot turn the guard on.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIRMATION_TTL_SECONDS = 300
_LEGACY_STATE = Path.home() / ".hermes" / "bprotective.json"

_BLOCK_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "root-recursive-delete",
        re.compile(
            r"\brm\b(?:(?!\n).)*\s-[^\s]*r[^\s]*f[^\s]*\s+(?:/|/\*|~(?:/\*)?|\$HOME(?:/\*)?)(?:\s|$)",
            re.I,
        ),
        "recursive deletion of a protected root or home path",
    ),
    (
        "device-format",
        re.compile(
            r"\b(?:mkfs(?:\.[\w-]+)?|diskutil\s+(?:eraseDisk|partitionDisk))\b|\bdd\b(?:(?!\n).)*\bof\s*=\s*/dev/",
            re.I,
        ),
        "disk formatting or raw-device overwrite",
    ),
    ("fork-bomb", re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.I), "fork bomb"),
    (
        "secret-export",
        re.compile(
            r"\b(?:bw|bws|lpass|keepassxc-cli|rbw|nordpass|pass)\b|\b(?:op\s+(?:read|run|inject|document)|security\s+(?:find|dump-keychain))\b|\bgpg\s+--export-secret",
            re.I,
        ),
        "credential or secret-store access",
    ),
    (
        "remote-installer",
        re.compile(r"\b(?:curl|wget)\b(?:(?!\n).)*(?:\||;|&&)\s*(?:sudo\s+)?(?:sh|bash|zsh)\b", re.I),
        "piped remote script execution",
    ),
    (
        "destructive-git",
        re.compile(
            r"\bgit\s+(?:push\b(?:(?!\n).)*(?:--force\s*|\s-f\b)|reflog\s+expire\b|gc\b(?:(?!\n).)*--prune(?:=now|=all))|\bgh\s+(?:repo|release|secret|ssh-key|gpg-key)\s+delete\b",
            re.I,
        ),
        "destructive Git or GitHub history/resource operation",
    ),
)

_APPROVAL_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "privileged-command",
        re.compile(r"(?:^|[;&|]\s*)sudo\b|\b(?:systemctl|ufw|iptables|nft)\b|(?<![\w-])service\b", re.I),
        "privileged service or firewall operation",
    ),
    ("docker-runtime", re.compile(r"\bdocker\b|\bdokploy\b", re.I), "Docker or Dokploy runtime operation"),
    ("permissions", re.compile(r"\b(?:chmod|chown|chgrp|setfacl)\b", re.I), "permission or ownership change"),
    (
        "external-publication",
        re.compile(r"\bgit\s+push\b|\bgh\s+(?:pr|release|repo|issue)\b", re.I),
        "external Git or GitHub operation",
    ),
    (
        "package-install",
        re.compile(
            r"\b(?:apt|apt-get|brew|npm|pnpm|yarn|pip|uv)\s+(?:install|add)\b|\b(?:winget|choco|scoop)\s+(?:install|upgrade)\b",
            re.I,
        ),
        "package installation",
    ),
)

_DELETE_VERB = re.compile(r"(?i)\b(?:remove-item|rmdir|erase|del|rd|ri|rm)\b")
_FORMAT = re.compile(
    r"(?i)\bformat(?:\.com)?\s+[a-z]:(?=$|[\s\\/])|\bformat-volume\b|\bclear-disk\b|\binitialize-disk\b"
)
_DISKPART = re.compile(r"(?i)\bdiskpart(?:\.exe)?\b")
_CIPHER_WIPE = re.compile(r"(?i)\bcipher(?:\.exe)?\s+/w\b")
_EXECUTION_POLICY = re.compile(r"(?i)\bset-executionpolicy\b")
_WIN_PERMISSIONS = re.compile(r"(?i)\b(?:icacls|takeown)(?:\.exe)?\b")
_WIN_SERVICE = re.compile(
    r"(?i)\b(?:stop-service|restart-service|start-service|set-service|netsh|set-netfirewallprofile|set-netfirewallrule)\b"
)
_REG_DELETE = re.compile(r"(?i)\breg(?:\.exe)?\s+delete\s+(\S+)")
_MUTATE = re.compile(
    r"(?i)\b(?:remove-item|rmdir|erase|del|rd|ri|rm|move-item|rename-item|ren|move|clear-content|set-content)\b"
)
_HIVE_ROOTS = {
    "hklm",
    "hkcu",
    "hkcr",
    "hku",
    "hkcc",
    "hkey_local_machine",
    "hkey_current_user",
    "hkey_classes_root",
    "hkey_users",
    "hkey_current_config",
}
_CRITICAL_HIVE_TAILS = {"system", "software", "sam", "security"}
_CONFIG_KEYS = {"protected_paths", "extra_block", "extra_escalate"}
_MAX_PATTERN_LENGTH = 500


@dataclass(frozen=True)
class ExtraRule:
    key: str
    pattern: re.Pattern[str]
    reason: str


@dataclass(frozen=True)
class Config:
    protected_paths: tuple[str, ...] = ()
    extra_block: tuple[ExtraRule, ...] = ()
    extra_escalate: tuple[ExtraRule, ...] = ()


EMPTY_CONFIG = Config()


@dataclass(frozen=True)
class Decision:
    action: str
    rule_key: str
    reason: str

    @property
    def message(self) -> str:
        if self.rule_key == "state-invalid":
            return "bProtective blocked the command because its policy state is unreadable."
        if self.rule_key == "config-invalid":
            return "bProtective blocked the command because its instance config is unreadable."
        if self.action == "block":
            return f"bProtective blocked this command: {self.reason}."
        if self.action == "escalate":
            return f"bProtective requires operator approval: {self.reason}."
        if self.rule_key == "disabled":
            return "bProtective is off."
        return self.reason


def to_hermes(decision: Decision | None) -> dict[str, str] | None:
    """Map a core decision to a Hermes pre_tool_call directive. Allow stays None."""
    if decision is None or decision.action == "allow":
        return None
    action = "approve" if decision.action == "escalate" else "block"
    return {"action": action, "rule_key": decision.rule_key, "message": decision.message}


def configure_output_streams() -> None:
    """Print without raising UnicodeEncodeError on a legacy Windows code page.

    UTF-8 keeps characters a cp1252 pipe cannot encode. When a stream cannot
    change encoding, escape characters it cannot represent.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            try:
                reconfigure(errors="backslashreplace")
            except (AttributeError, OSError, ValueError):
                continue


def _system_root() -> Path:
    """Checkout that owns scripts/bsmart_instance.py. absolute() does not follow symlinks."""
    override = os.environ.get("BSMART_SYSTEM_ROOT")
    if override:
        return Path(override).expanduser().absolute()
    return Path(__file__).absolute().parents[2]


def _load_instance_helper() -> Any | None:
    """Load bsmart_instance.py by path. A missing helper does not invent a content root."""
    here = Path(__file__).absolute()
    checkout = here.parents[2]
    candidates = [
        _system_root() / "scripts" / "bsmart_instance.py",
        checkout / "scripts" / "bsmart_instance.py",
        Path("/workspace/bSmart-System/scripts/bsmart_instance.py"),
    ]
    seen: set[str] = set()
    for path in candidates:
        key = os.path.normcase(os.path.normpath(str(path.absolute())))
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        name = "bsmart_instance_" + str(abs(hash(key)))
        cached = sys.modules.get(name)
        if cached is not None and hasattr(cached, "default_content_root"):
            return cached
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        if hasattr(module, "default_content_root"):
            return module
    return None


def content_root() -> Path | None:
    """Per-instance bSmart directory.

    BSMART_CONTENT_ROOT is an explicit override. Otherwise this is
    bsmart_instance.default_content_root for the checkout: the sibling bSmart
    directory, with /workspace/bSmart only when this checkout is the container
    checkout. A missing helper leaves no content root.
    """
    override = os.environ.get("BSMART_CONTENT_ROOT")
    if override:
        return Path(override).expanduser().absolute()
    helper = _load_instance_helper()
    if helper is None:
        return None
    return helper.default_content_root(_system_root())


def _restrict_private(fd: int, temp_name: str) -> None:
    """Best-effort owner-only access for the private state file.

    On POSIX, mode 0o600 is owner read/write. On Windows, os.chmod only
    toggles the read-only attribute, so it does not limit access to the
    owner. There, call System32\\icacls.exe by full path, drop inherited
    ACEs, and grant the current user read, write, and delete. Delete is
    required to replace the file on a share where the user only has Modify.
    A failed or timed-out ACL change must not block the write.
    """
    if hasattr(os, "fchmod"):
        os.fchmod(fd, 0o600)
    else:
        os.chmod(temp_name, 0o600)
    if os.name != "nt":
        return
    user = os.environ.get("USERNAME")
    if not user:
        return
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    icacls = system_root.rstrip("\\/") + "\\System32\\icacls.exe"
    try:
        subprocess.run(
            [icacls, temp_name, "/inheritance:r", "/grant:r", f"{user}:(R,W,D)"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def state_path() -> Path:
    override = os.environ.get("BPROTECTIVE_STATE_FILE")
    if override:
        return Path(override).expanduser().resolve()
    legacy = _LEGACY_STATE
    content = content_root()
    if content is not None:
        preferred = content / "State" / "bprotective.json"
        if preferred.is_file() or not legacy.is_file():
            return preferred
        return legacy
    return legacy


def read_state() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return {"enabled": False, "pending": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "pending": None, "error": "state file is unreadable"}
    return value if isinstance(value, dict) else {"enabled": False, "pending": None, "error": "state file is invalid"}


def write_state(value: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    opened = False
    try:
        _restrict_private(fd, temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            opened = True
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
        os.replace(temp_name, path)
    except Exception:
        if not opened:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _config_candidates() -> list[Path]:
    override = os.environ.get("BPROTECTIVE_CONFIG_FILE")
    if override:
        return [Path(override).expanduser().resolve()]
    content = content_root()
    if content is None:
        return []
    return [content / "State" / "bprotective.yaml", content / "State" / "bprotective.config.json"]


def load_config() -> tuple[Config, str | None]:
    paths = [path for path in _config_candidates() if path.is_file()]
    if not paths:
        return EMPTY_CONFIG, None
    if len(paths) > 1:
        return EMPTY_CONFIG, "bprotective.yaml and bprotective.config.json are both present"
    try:
        text = paths[0].read_text(encoding="utf-8")
        data = _parse_config_text(text)
        return _config_from_data(data), None
    except (OSError, ValueError, json.JSONDecodeError, re.error) as exc:
        return EMPTY_CONFIG, str(exc)


def policy_decision(command: str, config: Config | None = None) -> Decision:
    """Return allow, escalate, or block from the command text. Ignores on/off state."""
    active = config or EMPTY_CONFIG
    for rule_key, pattern, reason in _BLOCK_RULES:
        if pattern.search(command):
            return Decision("block", rule_key, reason)
    windows_block = _windows_block(command)
    if windows_block is not None:
        return windows_block
    protected_block = _protected_block(command, active)
    if protected_block is not None:
        return protected_block
    for rule in active.extra_block:
        if rule.pattern.search(command):
            return Decision("block", rule.key, rule.reason)
    protected_escalate = _protected_escalate(command, active)
    if protected_escalate is not None:
        return protected_escalate
    for rule_key, pattern, reason in _APPROVAL_RULES:
        if pattern.search(command):
            return Decision("escalate", rule_key, reason)
    windows_escalate = _windows_escalate(command)
    if windows_escalate is not None:
        return windows_escalate
    for rule in active.extra_escalate:
        if rule.pattern.search(command):
            return Decision("escalate", rule.key, rule.reason)
    return Decision("allow", "allow", "command is allowed")


def guard(command: str) -> Decision:
    """Apply on/off state, instance config, and a one-shot operator approval."""
    state = read_state()
    if state.get("error"):
        return Decision("block", "state-invalid", "policy state is unreadable")
    if not state.get("enabled"):
        return Decision("allow", "disabled", "bProtective is off")
    config, error = load_config()
    if error:
        return Decision("block", "config-invalid", error)
    decision = policy_decision(command, config)
    if decision.action == "block":
        return decision
    allowed = state.get("allow_once")
    if isinstance(allowed, str) and allowed == command.strip():
        state["allow_once"] = None
        write_state(state)
        return Decision("allow", "allow-once", "operator approved this command once")
    return decision


def request_command_approval(command: str) -> str:
    """Store a confirmation that allows this exact command once. Reuses an unexpired token."""
    state = read_state()
    if state.get("error"):
        raise OSError(state["error"])
    command = command.strip()
    now = int(time.time())
    pending = state.get("command_pending") or {}
    if pending.get("command") == command and int(pending.get("expires_at", 0)) >= now and pending.get("id"):
        return str(pending["id"])
    token = secrets.token_urlsafe(12)
    state["command_pending"] = {
        "id": token,
        "operation": "allow-once",
        "command": command,
        "expires_at": now + CONFIRMATION_TTL_SECONDS,
    }
    write_state(state)
    return token


def handle_control(args: list[str], *, reply_prefix: str) -> tuple[str, int]:
    """On/off/status/yes/no. `reply_prefix` is `/bprotective` for Hermes and `bprotective` for the CLI."""
    state = read_state()
    if state.get("error"):
        return f"bProtective unavailable: {state['error']}.", 1
    if not args or args == ["status"]:
        return f"bProtective is {'on' if state.get('enabled') else 'off'}.", 0
    if args in (["on"], ["off"]):
        operation = args[0]
        if bool(state.get("enabled")) == (operation == "on"):
            return f"bProtective is already {operation}.", 0
        token = _confirmation(operation)
        return f"Confirmation required to turn bProtective {operation}. Reply: {reply_prefix} yes {token}", 0
    if len(args) == 2 and args[0] == "yes":
        return _resolve_confirmation(args[1], accept=True)
    if len(args) == 2 and args[0] == "no":
        return _resolve_confirmation(args[1], accept=False)
    return f"Usage: {reply_prefix} [status|on|off|yes ID|no ID]", 1


def _confirmation(operation: str) -> str:
    state = read_state()
    token = secrets.token_urlsafe(12)
    state["pending"] = {"id": token, "operation": operation, "expires_at": int(time.time()) + CONFIRMATION_TTL_SECONDS}
    write_state(state)
    return token


def _resolve_confirmation(token: str, *, accept: bool) -> tuple[str, int]:
    state = read_state()
    slot, pending = _matching_pending(state, token)
    if slot is None or pending is None:
        return "No matching bProtective confirmation; it may be missing or already used.", 1
    if int(pending.get("expires_at", 0)) < int(time.time()):
        state[slot] = None
        write_state(state)
        return "bProtective confirmation expired; request the change again.", 1
    if not accept:
        state[slot] = None
        write_state(state)
        return "bProtective change cancelled.", 0
    if slot == "command_pending":
        command = pending.get("command")
        if not isinstance(command, str) or not command:
            return "Invalid bProtective confirmation.", 1
        state["allow_once"] = command
        state["command_pending"] = None
        write_state(state)
        return "bProtective will allow that command once.", 0
    if pending.get("operation") not in {"on", "off"}:
        return "Invalid bProtective confirmation.", 1
    state["enabled"] = pending["operation"] == "on"
    state["pending"] = None
    write_state(state)
    if state["enabled"]:
        return f"bProtective {pending['operation']} enabled.", 0
    return "bProtective off; guard disabled.", 0


def _matching_pending(state: dict[str, Any], token: str) -> tuple[str | None, dict[str, Any] | None]:
    for slot in ("pending", "command_pending"):
        pending = state.get(slot) or {}
        if isinstance(pending, dict) and pending.get("id") == token:
            return slot, pending
    return None, None


def _windows_block(command: str) -> Decision | None:
    if _FORMAT.search(command):
        return Decision("block", "windows-format", "disk formatting")
    if _DISKPART.search(command):
        return Decision("block", "diskpart", "diskpart can erase or repartition disks")
    if _CIPHER_WIPE.search(command):
        return Decision("block", "disk-wipe", "cipher wipe of free space or a volume")
    registry = _registry_severity(command)
    if registry == "block":
        return Decision("block", "registry-hive-delete", "deletion of a registry hive or critical registry root")
    if _recursive_root_delete(command):
        return Decision("block", "windows-root-recursive-delete", "recursive deletion of a Windows root, system, or home path")
    return None


def _windows_escalate(command: str) -> Decision | None:
    if _EXECUTION_POLICY.search(command):
        return Decision("escalate", "execution-policy", "PowerShell execution-policy change")
    if _registry_severity(command) == "escalate":
        return Decision("escalate", "registry-delete", "registry deletion")
    if _WIN_PERMISSIONS.search(command):
        return Decision("escalate", "windows-permissions", "Windows permission or ownership change")
    if _WIN_SERVICE.search(command):
        return Decision("escalate", "windows-service", "Windows service, firewall, or network configuration change")
    return None


def _recursive_root_delete(command: str) -> bool:
    if not _DELETE_VERB.search(command) or not _has_recurse_flag(command):
        return False
    return _mentions_windows_root(command)


def _has_recurse_flag(command: str) -> bool:
    if re.search(r"(?i)(?:^|[\s;|&])-Recurse\b", command):
        return True
    if re.search(r"(?:^|[\s;|&])-r(?=\s|$)", command):
        return True
    if re.search(r"(?:^|[\s;|&])-[a-z]*r[a-z]*(?=\s|$)", command):
        return True
    return re.search(r"(?i)(?:^|[\s;|&])/s(?=\s|$)", command) is not None


def _mentions_windows_root(command: str) -> bool:
    normalized = command.replace("/", "\\").lower()
    pattern = re.compile(
        r"""(?ix)
        (?:^|[\s"'=`])
        (?:\\\\\?\\)?
        (?:
            [a-z]:(?:\\(?:\*|windows|users|program\ files(?:\ \(x86\))?)?)?
            | %(?:systemdrive|systemroot|userprofile|homedrive)%\\?\*?
            | \$(?:env:)?(?:systemdrive|systemroot|userprofile|home)\\?\*?
            | ~\\?\*?
            | \\\\[^\\\s"'`]+\\[^\\\s"'`]+\\?\*?
        )
        (?=$|[\s"'`])
        """
    )
    return pattern.search(normalized) is not None


def _registry_severity(command: str) -> str | None:
    match = _REG_DELETE.search(command)
    if not match:
        return None
    key = match.group(1).strip("\"'").replace("/", "\\")
    parts = [part for part in key.split("\\") if part]
    if not parts:
        return "block"
    head = parts[0].lower()
    if head not in _HIVE_ROOTS:
        return "escalate"
    if len(parts) == 1:
        return "block"
    if len(parts) == 2 and parts[1].lower() in _CRITICAL_HIVE_TAILS:
        return "block"
    return "escalate"


def _protected_block(command: str, config: Config) -> Decision | None:
    if not config.protected_paths or not _DELETE_VERB.search(command) or not _has_recurse_flag(command):
        return None
    for path in config.protected_paths:
        if _mentions_path(command, path):
            return Decision("block", "protected-path-delete", f"recursive deletion under protected path {path}")
    return None


def _protected_escalate(command: str, config: Config) -> Decision | None:
    if not config.protected_paths or not _MUTATE.search(command):
        return None
    for path in config.protected_paths:
        if _mentions_path(command, path):
            return Decision("escalate", "protected-path-change", f"change under protected path {path}")
    return None


def _mentions_path(command: str, protected: str) -> bool:
    path = _normalize_path(protected)
    if len(path) < 3:
        return False
    command_text = re.sub(r"\\+", r"\\", command.replace("/", "\\").lower())
    start = 0
    while True:
        index = command_text.find(path, start)
        if index < 0:
            return False
        before = command_text[index - 1] if index else " "
        after_index = index + len(path)
        after = command_text[after_index] if after_index < len(command_text) else " "
        if before in " \t\"'=`" and after in " \t\"'\\":
            return True
        start = index + 1


def _normalize_path(value: str) -> str:
    text = value.strip().strip("\"'")
    text = re.sub(r"\\+", r"\\", text.replace("/", "\\"))
    return text.lower().rstrip("\\")


def _parse_config_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped[0] == "{":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("instance config must be an object")
        return data
    return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_item: dict[str, str] | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("\t") or "\t" in raw[: len(raw) - len(raw.lstrip(" "))]:
            raise ValueError("instance config must be indented with spaces")
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            if not line.endswith(":") or line.startswith("-"):
                raise ValueError(f"invalid instance config line: {line}")
            current_key = line[:-1].strip()
            data[current_key] = []
            current_item = None
            continue
        if current_key is None:
            raise ValueError("invalid instance config")
        if line.startswith("- "):
            value = line[2:].strip()
            key, parsed, is_map = _split_yaml_value(value)
            if is_map:
                current_item = {key: parsed}
                data[current_key].append(current_item)
            else:
                current_item = None
                data[current_key].append(parsed)
            continue
        if current_item is None or ":" not in line:
            raise ValueError(f"invalid instance config line: {line}")
        key, parsed, is_map = _split_yaml_value(line)
        if not is_map:
            raise ValueError(f"invalid instance config line: {line}")
        current_item[key] = parsed
    return data


def _split_yaml_value(value: str) -> tuple[str, str, bool]:
    if ":" not in value:
        return "", _unquote(value), False
    key, raw = value.split(":", 1)
    stripped_key = key.strip()
    if not stripped_key or stripped_key.startswith(("'", '"')):
        return "", _unquote(value), False
    # Unquoted Windows paths such as E:\VPS\share contain a drive colon.
    if len(stripped_key) == 1 and stripped_key.isalpha() and raw.startswith(("\\", "/")):
        return "", _unquote(value), False
    return stripped_key, _unquote(raw.strip()), True


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _config_from_data(data: dict[str, Any]) -> Config:
    unknown = sorted(set(data) - _CONFIG_KEYS)
    if unknown:
        raise ValueError("unknown instance config keys: " + ", ".join(unknown))
    paths = _string_list(data.get("protected_paths", []), "protected_paths")
    if len(paths) > 100:
        raise ValueError("too many protected paths")
    return Config(
        protected_paths=tuple(dict.fromkeys(paths)),
        extra_block=_extra_rules(data.get("extra_block", []), "extra-block"),
        extra_escalate=_extra_rules(data.get("extra_escalate", []), "extra-escalate"),
    )


def _string_list(value: Any, label: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label} entries must be non-empty strings")
        items.append(item.strip())
    return items


def _extra_rules(value: Any, prefix: str) -> tuple[ExtraRule, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{prefix} must be a list")
    if len(value) > 50:
        raise ValueError(f"too many {prefix} rules")
    rules: list[ExtraRule] = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} entries must be pattern/reason maps")
        unknown = sorted(set(item) - {"key", "pattern", "reason"})
        if unknown:
            raise ValueError(f"unknown {prefix} fields: " + ", ".join(unknown))
        pattern_text = item.get("pattern")
        reason = item.get("reason")
        if not isinstance(pattern_text, str) or not pattern_text.strip():
            raise ValueError(f"{prefix} pattern is required")
        if len(pattern_text) > _MAX_PATTERN_LENGTH:
            raise ValueError(f"{prefix} pattern is too long")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{prefix} reason is required")
        key = item.get("key") or f"{prefix}-{index}"
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", key):
            raise ValueError(f"invalid {prefix} key")
        if key in seen:
            raise ValueError(f"duplicate {prefix} key: {key}")
        seen.add(key)
        rules.append(ExtraRule(key=key, pattern=re.compile(pattern_text, re.I), reason=reason.strip()))
    return tuple(rules)
