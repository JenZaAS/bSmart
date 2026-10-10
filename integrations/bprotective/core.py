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
            r"(?:^|[;&|\n]\s*)(?:sudo\s+)?(?:bw|bws|lpass|keepassxc-cli|rbw|nordpass|pass)(?![\w-])"
            r"|\b(?:op\s+(?:read|run|inject|document)|security\s+(?:find|dump-keychain))\b"
            r"|\bgpg\s+--export-secret",
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
            r"\bgit\s+(?:reflog\s+expire\b|gc\b(?:(?!\n).)*--prune(?:=now|=all))"
            r"|\bgh\s+(?:repo|release|secret|ssh-key|gpg-key)\s+delete\b",
            re.I,
        ),
        "destructive Git or GitHub history/resource operation",
    ),
    (
        "shadow-copy-delete",
        re.compile(r"(?i)\bvssadmin(?:\.exe)?\s+delete\s+shadows\b"),
        "deletion of Windows shadow copies",
    ),
)

_APPROVAL_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "privileged-command",
        re.compile(
            r"(?:^|[;&|]\s*)sudo\b|\b(?:systemctl|ufw|iptables|nft)\b|(?<![\w-])service(?![\w-])",
            re.I,
        ),
        "privileged service or firewall operation",
    ),
    (
        "docker-runtime",
        re.compile(r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:docker|dokploy)(?![\w-])", re.I),
        "Docker or Dokploy runtime operation",
    ),
    ("permissions", re.compile(r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:chmod|chown|chgrp|setfacl)(?![\w-])", re.I), "permission or ownership change"),
    (
        "external-publication",
        re.compile(r"(?:^|[;&|]\s*)(?:sudo\s+)?git\s+push\b|\bgh\s+(?:pr|release|repo|issue)\b", re.I),
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

_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_POSIX_ROOTS = (
    "/etc",
    "/usr",
    "/home",
    "/var",
    "/opt",
    "/root",
    "/boot",
    "/srv",
    "/lib",
    "/lib32",
    "/lib64",
    "/libexec",
)
_HOME_OPERANDS = {"~", "~/", "~/*", "$home", "${home}", "$home/*", "${home}/*"}
_MAX_COMMAND_CHARS = 100_000
_MAX_TOKENS = 20_000
_MAX_SCAN_SECONDS = 0.5
_WRAPPERS = {"sudo", "command", "exec", "env", "nice", "nohup", "timeout", "busybox"}
_VALUE_FLAGS = {
    "sudo": {
        "-u",
        "--user",
        "-g",
        "--group",
        "-h",
        "--host",
        "-p",
        "--prompt",
        "-C",
        "--close-from",
        "-t",
        "--type",
        "-r",
        "--role",
        "-U",
        "--other-user",
        "-D",
        "--chdir",
    },
    "env": {"-u", "--unset", "-c", "--chdir"},
    "nice": {"-n", "--adjustment"},
    "timeout": {"-k", "--kill-after", "-s", "--signal"},
}
_ROOT_PATHS = {"/", "/*", "/.", "/./", "//"}
_DEVICE_REDIRECT = re.compile(
    r"(?:^|[\s;&|])>{1,2}\s*(/dev/(?:sd|nvme|vd|xvd|mmcblk|disk)\S*)",
    re.I,
)
_CONTROL_RE = re.compile(
    r"""(?ix)
    (?:^|[;&|\n]\s*|(?:python(?:3)?|py)\s+(?:-3\s+)?)
    (?:\S*[/\\])?
    (?:/?bprotective(?:[/\\]cli\.py)?|scripts[/\\]bprotective)
    \s+(on|off|yes|no|recover)\b
    """
)
_STATE_NAME_RE = re.compile(r"(?i)bprotective\.json(?:\.armed)?")
_WRITE_TOOL_RE = re.compile(
    r"""(?ix)
    (?:^|[;&|\n]\s*)
    (?:(?:sudo|command|exec|env|nice|nohup|timeout|busybox)\s+)*
    (?:python(?:3)?|py|perl|sed|ruby|node|dd|git|find|rm|mv|cp|tee|truncate|shred|unlink|ln|rsync|install|busybox)
    (?:\.exe)?(?![\w-])
    """
)
_GUARD_PATH_RE = re.compile(
    r"""(?ix)
    bprotective[/\\]cli\.py
    | scripts[/\\]bprotective\b
    | integrations[/\\]bprotective\b
    | bprotective\.json(?:\.armed)?
    | \.bprotective[/\\]armed\.json
    | (?:^|[\s'"=])(?:\./|\.\\)?state(?:[/\\\s'"]|$)
    | [/\\]state(?:[/\\]|$)
    """
)
_STATE_MUTATE_RE = re.compile(
    r"""(?ix)
    (?:^|[;&|\n]\s*)(?:sudo\s+)?
    (?:rm|unlink|mv|cp|tee|truncate|shred|del|erase|rd|rmdir
      |remove-item|move-item|rename-item|copy-item|set-content|clear-content|out-file)
    (?![\w-])
    """
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
            detail = f" {self.reason}." if self.reason and self.reason != "policy state is unreadable" else ""
            return f"bProtective blocked the command because its policy state is unreadable.{detail}"
        if self.rule_key == "scan-limit":
            return f"bProtective blocked this command because it hit a scan limit: {self.reason}."
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
    bsmart_instance.default_content_root for the checkout, the sibling bSmart
    directory of that checkout. A missing helper leaves no content root.
    """
    override = os.environ.get("BSMART_CONTENT_ROOT")
    if override:
        return Path(override).expanduser().absolute()
    helper = _load_instance_helper()
    if helper is None:
        return None
    return helper.default_content_root(_system_root())


def _lookup_windows_sid() -> str | None:
    """Current user SID, or None when this is not Windows or the lookup fails."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None
    try:
        token_query = 0x0008
        token_user = 1
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _SidAndAttributes(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class _TokenUser(ctypes.Structure):
            _fields_ = [("User", _SidAndAttributes)]

        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), token_query, ctypes.byref(token)):
            return None
        try:
            length = wintypes.DWORD(0)
            advapi32.GetTokenInformation(token, token_user, None, 0, ctypes.byref(length))
            buf = ctypes.create_string_buffer(length.value)
            if not advapi32.GetTokenInformation(token, token_user, buf, length, ctypes.byref(length)):
                return None
            user = ctypes.cast(buf, ctypes.POINTER(_TokenUser)).contents
            sid_ptr = wintypes.LPWSTR()
            if not advapi32.ConvertSidToStringSidW(user.User.Sid, ctypes.byref(sid_ptr)):
                return None
            try:
                value = ctypes.wstring_at(sid_ptr)
            finally:
                kernel32.LocalFree(sid_ptr)
            if value and value.startswith("S-"):
                return value
            return None
        finally:
            kernel32.CloseHandle(token)
    except Exception:
        return None


def _acl_principal() -> str | None:
    """SID or DOMAIN\\user. A bare account name is not used; it can lock the file."""
    sid = _lookup_windows_sid()
    if sid:
        return "*" + sid
    domain = os.environ.get("USERDOMAIN")
    user = os.environ.get("USERNAME")
    if domain and user and "\\" not in user:
        return domain + "\\" + user
    if user and "\\" in user:
        return user
    return None


def _restrict_private(fd: int, temp_name: str) -> None:
    """Best-effort owner-only access for the private state file.

    On POSIX, mode 0o600 is owner read/write. On Windows, os.chmod only
    toggles the read-only attribute, so it does not limit access to the
    owner. There, call System32\\icacls.exe by full path, drop inherited
    ACEs, and grant the current user read, write, and delete. The grant is
    the user SID or DOMAIN\\user. A bare username is skipped so a failed
    match cannot remove inheritance and lock the owner out. Delete is
    required to replace the file on a share where the user only has Modify.
    A failed or timed-out ACL change must not block the write.
    """
    if hasattr(os, "fchmod"):
        os.fchmod(fd, 0o600)
    else:
        os.chmod(temp_name, 0o600)
    if os.name != "nt":
        return
    principal = _acl_principal()
    if not principal:
        return
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    icacls = system_root.rstrip("\\/") + "\\System32\\icacls.exe"
    try:
        subprocess.run(
            [icacls, temp_name, "/inheritance:r", "/grant:r", f"{principal}:(R,W,D)"],
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
        # absolute() keeps a symlink as the state path. resolve() would follow it
        # and lose the armed record that sits beside the link.
        return Path(override).expanduser().absolute()
    legacy = _LEGACY_STATE
    content = content_root()
    if content is not None:
        preferred = content / "State" / "bprotective.json"
        if preferred.is_file() or not legacy.is_file():
            return preferred
        return legacy
    return legacy


def armed_record_path() -> Path:
    """Armed record outside the instance State directory.

    Deleting State/bprotective.json together with its sibling marker must not
    look like a fresh install. BPROTECTIVE_ARMED_FILE overrides the path so
    tests do not write the operator's home directory.
    """
    override = os.environ.get("BPROTECTIVE_ARMED_FILE")
    if override:
        return Path(override).expanduser().absolute()
    return Path.home() / ".bprotective" / "armed.json"


def _armed_path(path: Path) -> Path:
    return path.with_name(path.name + ".armed")


def _state_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.absolute())))


def _write_armed_marker(path: Path) -> None:
    marker = _armed_path(path)
    marker.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, b"enabled\n")
    finally:
        os.close(fd)


def _clear_armed_marker(path: Path) -> None:
    try:
        _armed_path(path).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _read_armed_file() -> tuple[dict[str, Any], str | None]:
    path = armed_record_path()
    if not path.is_file():
        return {"states": {}}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "armed record is unreadable"
    if not isinstance(data, dict) or not isinstance(data.get("states", {}), dict):
        return {}, "armed record is unreadable"
    data.setdefault("states", {})
    return data, None


def _write_armed_file(data: dict[str, Any]) -> None:
    path = armed_record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".armed.", dir=str(path.parent))
    opened = False
    try:
        _restrict_private(fd, temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            opened = True
            json.dump(data, stream, sort_keys=True)
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


def _armed_entry(data: dict[str, Any], key: str) -> dict[str, Any]:
    states = data.get("states")
    if not isinstance(states, dict):
        return {}
    entry = states.get(key)
    return entry if isinstance(entry, dict) else {}


def _store_armed_entry(key: str, entry: dict[str, Any]) -> None:
    data, error = _read_armed_file()
    if error:
        data = {"states": {}}
    states = data.setdefault("states", {})
    if not isinstance(states, dict):
        data["states"] = {}
        states = data["states"]
    states[key] = entry
    _write_armed_file(data)


def _still_armed(entry: dict[str, Any], local_marker: bool) -> bool:
    if entry.get("confirmed_off"):
        return False
    return bool(entry.get("armed")) or local_marker


def read_state() -> dict[str, Any]:
    path = state_path()
    data, error = _read_armed_file()
    if error:
        return {"enabled": False, "pending": None, "error": error}
    key = _state_key(path)
    entry = _armed_entry(data, key)
    local_marker = _armed_path(path).is_file()
    if not path.is_file():
        if _still_armed(entry, local_marker):
            return {"enabled": False, "pending": None, "error": "state file is missing"}
        return {"enabled": False, "pending": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "pending": None, "error": "state file is unreadable"}
    if not isinstance(value, dict):
        return {"enabled": False, "pending": None, "error": "state file is invalid"}
    if value.get("enabled"):
        if not local_marker:
            try:
                _write_armed_marker(path)
            except OSError:
                pass
        if not entry.get("armed") or entry.get("confirmed_off"):
            try:
                _store_armed_entry(key, {"armed": True, "confirmed_off": False, "pending": entry.get("pending")})
            except OSError:
                pass
        return value
    if _still_armed(entry, local_marker):
        return {"enabled": False, "pending": None, "error": "state file does not match the armed record"}
    return value


def write_state(value: dict[str, Any], *, operator_off: bool = False) -> None:
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
        key = _state_key(path)
        if value.get("enabled"):
            _write_armed_marker(path)
            _store_armed_entry(key, {"armed": True, "confirmed_off": False, "pending": None})
        elif operator_off:
            _store_armed_entry(key, {"armed": False, "confirmed_off": True, "pending": None})
            _clear_armed_marker(path)
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


def path_targets_guard(path: str) -> bool:
    """True when a file-edit path is the state file, its marker, or the outside armed record."""
    text = path.strip().strip("\"'")
    if not text:
        return False
    name = text.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    if name in {"bprotective.json", "bprotective.json.armed"}:
        return True
    try:
        candidate = os.path.normcase(os.path.normpath(str(Path(text).expanduser().absolute())))
    except OSError:
        return False
    guarded = (
        state_path(),
        _armed_path(state_path()),
        armed_record_path(),
    )
    for item in guarded:
        if os.path.normcase(os.path.normpath(str(item.absolute()))) == candidate:
            return True
    return False


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


class ScanLimit(Exception):
    """The command is too large or took too long to scan. Callers fail closed."""


def _check_budget(deadline: float | None, tokens: list[str]) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise ScanLimit("command scan exceeded the time limit")
    if len(tokens) > _MAX_TOKENS:
        raise ScanLimit("command exceeds the token limit")


def _tokenize(text: str, deadline: float | None = None) -> list[str]:
    """Split a shell command into words. Quotes are removed; their contents stay one word.

    A single ``&`` is its own token. The word scan treats ``&`` as a stop
    character, so it must be consumed here. Leaving it in place appends an
    empty token forever.
    """
    if len(text) > _MAX_COMMAND_CHARS:
        raise ScanLimit("command exceeds the scan size limit")
    tokens: list[str] = []
    i = 0
    n = len(text)
    steps = 0
    while i < n:
        steps += 1
        if steps % 64 == 0:
            _check_budget(deadline, tokens)
        while i < n and text[i] in " \t\r":
            i += 1
        if i >= n:
            break
        if text.startswith("&&", i) or text.startswith("||", i):
            tokens.append(text[i : i + 2])
            i += 2
            continue
        if text[i] in {";", "|", "\n"}:
            tokens.append(text[i])
            i += 1
            continue
        if text[i] == "&":
            if i + 1 < n and text[i + 1] in "<>":
                j = i
                while j < n and text[j] in "<>&":
                    j += 1
                tokens.append(text[i:j])
                i = j
                continue
            tokens.append("&")
            i += 1
            continue
        if text[i] in {">", "<"}:
            j = i
            while j < n and text[j] in "<>&":
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        if text[i] in {"'", '"'}:
            quote = text[i]
            i += 1
            buf: list[str] = []
            while i < n and text[i] != quote:
                if text[i] == "\\" and quote == '"' and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                buf.append(text[i])
                i += 1
            if i < n and text[i] == quote:
                i += 1
            tokens.append("".join(buf))
            continue
        start = i
        buf = []
        while i < n and text[i] not in " \t\r\n;|&<>":
            if text[i] == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            buf.append(text[i])
            i += 1
        if i == start:
            i += 1
            continue
        tokens.append("".join(buf))
    _check_budget(deadline, tokens)
    return tokens


def _statements(tokens: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in {"&&", "||", ";", "|", "&", "\n"}:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(token)
    if current:
        groups.append(current)
    return groups


def _basename(word: str) -> str:
    name = word.replace("\\", "/").rsplit("/", 1)[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name.lower()


def _unwrap_sudo(argv: list[str]) -> list[str]:
    """Drop wrappers and the values their flags take. ``/bin/rm`` becomes ``rm``."""
    words = list(argv)
    while words:
        name = _basename(words[0])
        if name not in _WRAPPERS:
            break
        words.pop(0)
        flags = _VALUE_FLAGS.get(name, set())
        while words and words[0].startswith("-") and words[0] != "-":
            flag = words.pop(0)
            key = flag.split("=", 1)[0]
            if "=" not in flag and key in flags and words:
                words.pop(0)
        if name == "env":
            while words and "=" in words[0] and not words[0].startswith("-"):
                words.pop(0)
        if name == "timeout" and words and words[0][:1].isdigit():
            words.pop(0)
    if words:
        words[0] = _basename(words[0])
    return words


def _strip_quotes(text: str) -> str:
    return re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"", " ", text)


def _posix_root_operand(value: str, cwd: str | None) -> bool:
    if value in _ROOT_PATHS:
        return True
    for root in _POSIX_ROOTS:
        if value in {root, root + "/", root + "/*"}:
            return True
    if value.lower() in _HOME_OPERANDS:
        return True
    if cwd == "/" and value in {"*", "./*", ".", "./"}:
        return True
    return False


def _rm_block(argv: list[str], cwd: str | None) -> Decision | None:
    if not argv or argv[0] != "rm":
        return None
    recursive = False
    operands: list[str] = []
    ended = False
    for arg in argv[1:]:
        if ended:
            operands.append(arg)
            continue
        if arg == "--":
            ended = True
            continue
        if arg in {"--recursive", "--force"} or arg.startswith("--recursive=") or arg.startswith("--force="):
            if arg.startswith("--recursive"):
                recursive = True
            continue
        if arg.startswith("--"):
            continue
        if arg.startswith("-") and len(arg) > 1:
            letters = arg[1:]
            if "r" in letters.lower():
                recursive = True
            continue
        operands.append(arg)
    if not recursive:
        return None
    if any(_posix_root_operand(item, cwd) for item in operands):
        return Decision("block", "root-recursive-delete", "recursive deletion of a protected root or home path")
    return None


def _find_block(argv: list[str]) -> Decision | None:
    if not argv or argv[0] != "find" or "-delete" not in argv:
        return None
    paths = [arg for arg in argv[1:] if arg != "-delete" and not arg.startswith("-")]
    if any(_posix_root_operand(path, None) for path in paths):
        return Decision("block", "find-delete", "find -delete of a protected root")
    return None


def _shred_block(argv: list[str]) -> Decision | None:
    if not argv or argv[0] != "shred":
        return None
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        if arg.startswith("/dev/"):
            return Decision("block", "device-shred", "shred of a device node")
    return None


def _chmod_root_block(argv: list[str]) -> Decision | None:
    if not argv or argv[0] != "chmod":
        return None
    recursive = False
    mode: str | None = None
    operands: list[str] = []
    for arg in argv[1:]:
        if arg in {"-R", "--recursive"}:
            recursive = True
            continue
        if arg.startswith("-"):
            continue
        if mode is None:
            mode = arg
            continue
        operands.append(arg)
    if not recursive or mode not in {"777", "0777", "a+rwx", "000", "0000", "a-rwx"}:
        return None
    if any(item in _ROOT_PATHS for item in operands):
        return Decision("block", "chmod-root", "recursive mode change of the filesystem root")
    return None


def _chown_root_block(argv: list[str]) -> Decision | None:
    if not argv or argv[0] not in {"chown", "chgrp"}:
        return None
    recursive = False
    saw_owner = False
    operands: list[str] = []
    for arg in argv[1:]:
        if arg in {"-R", "--recursive"} or (arg.startswith("-") and not arg.startswith("--") and "R" in arg):
            recursive = True
            continue
        if arg.startswith("-"):
            continue
        if not saw_owner:
            saw_owner = True
            continue
        operands.append(arg)
    if not recursive:
        return None
    if any(item in _ROOT_PATHS for item in operands):
        return Decision("block", "chown-root", "recursive ownership change of the filesystem root")
    return None


def _docker_prune_block(argv: list[str]) -> Decision | None:
    if len(argv) < 3 or argv[0] != "docker" or argv[1] != "system" or argv[2] != "prune":
        return None
    flags = argv[3:]
    all_flag = any(item in {"-a", "--all"} or (item.startswith("-") and not item.startswith("--") and "a" in item) for item in flags)
    volumes = "--volumes" in flags
    if all_flag and volumes:
        return Decision("block", "docker-prune", "docker system prune that removes volumes")
    return None


def _git_decision(argv: list[str]) -> Decision | None:
    if len(argv) < 2 or argv[0] != "git":
        return None
    if argv[1] == "reset" and "--hard" in argv[2:]:
        return Decision("escalate", "git-reset-hard", "git reset --hard discards local commits and changes")
    if argv[1] == "clean":
        letters = "".join(arg[1:] for arg in argv[2:] if arg.startswith("-") and not arg.startswith("--"))
        if "f" in letters and "d" in letters and "x" in letters:
            return Decision("escalate", "git-clean", "git clean -fdx deletes untracked files")
    if argv[1] != "push":
        return None
    force = False
    lease = False
    delete = False
    refs: list[str] = []
    for arg in argv[2:]:
        if arg in {"--force", "-f"}:
            force = True
            continue
        if arg.startswith("-") and not arg.startswith("--") and "f" in arg[1:]:
            force = True
            continue
        if arg == "--force-with-lease" or arg.startswith("--force-with-lease="):
            lease = True
            continue
        if arg in {"--delete", "-d"}:
            delete = True
            continue
        if arg.startswith("-"):
            continue
        refs.append(arg)
    protected_ref = any(_git_ref_protected(ref) for ref in refs)
    forced_update = any(ref.startswith("+") and _git_ref_protected(ref) for ref in refs)
    if force or forced_update or (delete and protected_ref) or (lease and protected_ref):
        return Decision("block", "destructive-git", "destructive Git or GitHub history/resource operation")
    return None


def _git_ref_protected(ref: str) -> bool:
    name = ref[1:] if ref[:1] in {"+", ":"} else ref
    tail = name.split("/")[-1]
    return tail in {"main", "master"} or name in {"main", "master"}


def _shell_bodies(argv: list[str]) -> list[str]:
    if not argv:
        return []
    bodies: list[str] = []
    if argv[0] in _SHELLS or argv[0] == "eval":
        if argv[0] == "eval" and len(argv) > 1:
            bodies.append(" ".join(argv[1:]))
        else:
            for index, arg in enumerate(argv):
                script = _shell_script_arg(argv, index, arg)
                if script is not None:
                    bodies.append(script)
    return bodies


def _shell_script_arg(argv: list[str], index: int, arg: str) -> str | None:
    """Return the script after ``-c`` or a short cluster that contains ``c``, such as ``-lc``."""
    if arg == "-c" or (arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:]):
        if index + 1 < len(argv):
            return argv[index + 1]
    if arg == "--command" and index + 1 < len(argv):
        return argv[index + 1]
    if arg.startswith("--command="):
        return arg.split("=", 1)[1]
    return None


def _redirect_block(surface: str) -> Decision | None:
    if _DEVICE_REDIRECT.search(surface):
        return Decision("block", "device-redirect", "redirect onto a disk device")
    return None


def _channel_block(command: str) -> Decision | None:
    """Block shell control of the guard and writes that name its files.

    This is a heuristic for accidental commands. It is not a complete list of
    every way to edit a file. The armed record outside State is what fails
    closed after a tamper the heuristic missed.
    """
    surface = _strip_quotes(command)
    if _CONTROL_RE.search(surface):
        return Decision("block", "guard-control", "changing bProtective from a shell command")
    if _WRITE_TOOL_RE.search(surface) and _GUARD_PATH_RE.search(command):
        return Decision("block", "state-file", "write, delete, or move of the bProtective state file")
    if not _STATE_NAME_RE.search(command):
        return None
    if re.search(r"(?i)(?:>{1,2}|set-content|out-file|tee)\s+\S*bprotective\.json", surface):
        return Decision("block", "state-file", "write, delete, or move of the bProtective state file")
    if _STATE_MUTATE_RE.search(surface):
        return Decision("block", "state-file", "write, delete, or move of the bProtective state file")
    return None


def _python_rmtree_block(argv: list[str]) -> Decision | None:
    if not argv or argv[0] not in {"python", "python3", "py"}:
        return None
    body: str | None = None
    for index, arg in enumerate(argv):
        if arg == "-c" and index + 1 < len(argv):
            body = argv[index + 1]
            break
    if not body or not re.search(r"rmtree|removedirs", body):
        return None
    for match in re.finditer(r"""['"]([^'"]+)['"]""", body):
        if _posix_root_operand(match.group(1), None):
            return Decision("block", "root-recursive-delete", "recursive deletion of a protected root or home path")
    return None


def _xargs_rm_block(statements: list[list[str]], tokens: list[str], cwd: str | None) -> Decision | None:
    for statement in statements:
        argv = _unwrap_sudo(statement)
        if not argv or argv[0] != "xargs":
            continue
        names = [_basename(word) for word in argv]
        if "rm" not in names:
            continue
        rm_at = names.index("rm")
        rm_argv = ["rm", *argv[rm_at + 1 :]]
        direct = _rm_block(rm_argv, cwd)
        if direct is not None:
            return direct
        if any(_posix_root_operand(token, cwd) for token in tokens if token not in {"&&", "||", ";", "|", "&", "\n"}):
            return Decision("block", "root-recursive-delete", "recursive deletion of a protected root or home path")
    return None


def _structured_decision(command: str, tokens: list[str]) -> Decision | None:
    channel = _channel_block(command)
    if channel is not None:
        return channel
    surface = _strip_quotes(command)
    redirect = _redirect_block(surface)
    if redirect is not None:
        return redirect
    statements = _statements(tokens)
    cwd: str | None = None
    escalation: Decision | None = None
    xargs_block = _xargs_rm_block(statements, tokens, cwd)
    if xargs_block is not None:
        return xargs_block
    for statement in statements:
        argv = _unwrap_sudo([token for token in statement if not token.startswith((">", "<", ">&"))])
        if not argv:
            continue
        if argv[0] == "cd" and len(argv) > 1:
            cwd = argv[1]
            continue
        checks = (
            _rm_block(argv, cwd),
            _find_block(argv),
            _shred_block(argv),
            _chmod_root_block(argv),
            _chown_root_block(argv),
            _docker_prune_block(argv),
            _git_decision(argv),
            _python_rmtree_block(argv),
        )
        for decision in checks:
            if decision is None:
                continue
            if decision.action == "block":
                return decision
            if escalation is None:
                escalation = decision
    return escalation


def policy_decision(
    command: str,
    config: Config | None = None,
    _depth: int = 0,
    _deadline: float | None = None,
) -> Decision:
    """Return allow, escalate, or block from the command text. Ignores on/off state."""
    if _depth > 3:
        return Decision("block", "nested-shell", "nested shell command was not expanded")
    if len(command) > _MAX_COMMAND_CHARS:
        return Decision("block", "scan-limit", "command exceeds the scan size limit")
    deadline = _deadline if _deadline is not None else time.monotonic() + _MAX_SCAN_SECONDS
    if time.monotonic() >= deadline:
        return Decision("block", "scan-limit", "command scan exceeded the time limit")
    try:
        tokens = _tokenize(command, deadline)
    except ScanLimit as exc:
        return Decision("block", "scan-limit", str(exc))
    active = config or EMPTY_CONFIG
    structured = _structured_decision(command, tokens)
    if structured is not None and structured.action == "block":
        return structured
    surface = _strip_quotes(command)
    for rule_key, pattern, reason in _BLOCK_RULES:
        if pattern.search(surface):
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
    statements = _statements(tokens)
    if _depth < 3:
        for statement in statements:
            words = [token for token in statement if not token.startswith((">", "<"))]
            for body in _shell_bodies(_unwrap_sudo(words)):
                nested = policy_decision(body, active, _depth + 1, deadline)
                if nested.action == "block":
                    return nested
    protected_escalate = _protected_escalate(command, active)
    if protected_escalate is not None:
        return protected_escalate
    git_only = None
    for statement in statements:
        decision = _git_decision(_unwrap_sudo(statement))
        if decision is not None and decision.action == "block":
            return decision
        if decision is not None:
            git_only = decision
    if git_only is not None:
        return git_only
    for rule_key, pattern, reason in _APPROVAL_RULES:
        if pattern.search(surface):
            return Decision("escalate", rule_key, reason)
    windows_escalate = _windows_escalate(command)
    if windows_escalate is not None:
        return windows_escalate
    for rule in active.extra_escalate:
        if rule.pattern.search(command):
            return Decision("escalate", rule.key, rule.reason)
    if _depth < 3:
        for statement in statements:
            for body in _shell_bodies(_unwrap_sudo(statement)):
                nested = policy_decision(body, active, _depth + 1, deadline)
                if nested.action != "allow":
                    return nested
    return Decision("allow", "allow", "command is allowed")


def guard(command: str, *, via_hook: bool = False) -> Decision:
    """Apply on/off state, instance config, and a one-shot operator approval.

    Shell hooks pass via_hook=True. Those calls block guard control commands
    and state-file changes even while protection is off, so the agent cannot
    approve or disable itself through the shell.
    """
    if len(command) > _MAX_COMMAND_CHARS:
        return Decision("block", "scan-limit", "command exceeds the scan size limit")
    state = read_state()
    if state.get("error"):
        return Decision("block", "state-invalid", str(state["error"]))
    if via_hook:
        channel = _channel_block(command)
        if channel is not None:
            return channel
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
    """On/off/status/yes/no/recover. `reply_prefix` is `/bprotective` for Hermes and `bprotective` for the CLI."""
    if args == ["recover"]:
        state = read_state()
        if not state.get("error"):
            return f"bProtective does not need recovery. Use {reply_prefix} off to turn it off.", 1
        token = _queue_recover()
        return f"Confirmation required to recover bProtective. Reply: {reply_prefix} yes {token}", 0
    if len(args) == 2 and args[0] in {"yes", "no"}:
        recovered = _resolve_recover(args[1], accept=args[0] == "yes")
        if recovered is not None:
            return recovered
    state = read_state()
    if state.get("error"):
        return (
            f"bProtective unavailable: {state['error']}. "
            f"Run {reply_prefix} recover from your own terminal, then {reply_prefix} yes <ID>.",
            1,
        )
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
    return f"Usage: {reply_prefix} [status|on|off|recover|yes ID|no ID]", 1


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
    turning_on = pending["operation"] == "on"
    state["enabled"] = turning_on
    state["pending"] = None
    write_state(state, operator_off=not turning_on)
    if state["enabled"]:
        return f"bProtective {pending['operation']} enabled.", 0
    return "bProtective off; guard disabled.", 0


def _queue_recover() -> str:
    path = state_path()
    key = _state_key(path)
    data, _error = _read_armed_file()
    entry = _armed_entry(data, key)
    token = secrets.token_urlsafe(12)
    entry = {
        "armed": True,
        "confirmed_off": False,
        "pending": {"id": token, "operation": "recover", "expires_at": int(time.time()) + CONFIRMATION_TTL_SECONDS},
    }
    _store_armed_entry(key, entry)
    return token


def _resolve_recover(token: str, *, accept: bool) -> tuple[str, int] | None:
    path = state_path()
    key = _state_key(path)
    data, error = _read_armed_file()
    if error:
        data = {"states": {}}
    entry = _armed_entry(data, key)
    pending = entry.get("pending") if isinstance(entry.get("pending"), dict) else None
    if not pending or pending.get("id") != token or pending.get("operation") != "recover":
        return None
    if int(pending.get("expires_at", 0)) < int(time.time()):
        entry["pending"] = None
        _store_armed_entry(key, entry)
        return "bProtective confirmation expired; request the change again.", 1
    if not accept:
        entry["pending"] = None
        _store_armed_entry(key, entry)
        return "bProtective change cancelled.", 0
    write_state({"enabled": False, "pending": None, "allow_once": None, "command_pending": None}, operator_off=True)
    return "bProtective recovered; guard disabled.", 0


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
    # Unquoted Windows paths such as E:\demo\data contain a drive colon.
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
