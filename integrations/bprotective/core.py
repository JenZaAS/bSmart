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
            r"\b(?:mkfs(?:\.[\w-]+)?|diskutil\s+(?:eraseDisk|partitionDisk))\b|\bdd\b(?:(?!\n).)*\bof\s*=\s*[\"']?/dev/",
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
_HOME_OPERANDS = {"~", "~/", "~/.", "~/*", "$home", "${home}", "$home/*", "${home}/*"}
# About 16k, under the 15s hook timeout. Past this size the full tokenizer
# does not run. A single linear scan still blocks hard cases and stops when
# the scan time limit is reached, so a hook does not sit until the harness
# gives up and runs the command.
_MAX_COMMAND_CHARS = 16_000
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
_STATEMENT_SEPARATORS = {"&&", "||", ";", "|", "&", "\n", "(", ")", "{", "}", "$(", "`"}
_DEVICE_REDIRECT = re.compile(
    r"(?:^|[\s;&|])>{1,2}\s*(/dev/(?:sd|nvme|vd|xvd|mmcblk|disk)\S*)",
    re.I,
)
_GUARD_REDIRECT_RE = re.compile(
    r"(?:^|[\s;&|])>{1,2}|\b(?:set-content|out-file|tee)\b",
    re.I,
)
_CONTROL_VERBS = frozenset({"on", "off", "yes", "no", "recover"})
_STATE_FILE_NAMES = frozenset({"bprotective.json", "bprotective.json.armed"})
_WRITE_TOOL_RE = re.compile(
    r"""(?ix)
    (?:^|[;&|\n]\s*)
    (?:(?:sudo|command|exec|env|nice|nohup|timeout|busybox)\s+)*
    (?:python(?:3)?|py|perl|sed|ruby|node|dd|git|find|rm|mv|cp|tee|truncate|shred|unlink|ln|rsync|install|busybox)
    (?:\.exe)?(?![\w-])
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
            return f"bProtective requires operator approval because this command hit a scan limit: {self.reason}."
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
    """True when a file edit targets the state file, its marker, or ~/.bprotective."""
    text = path.strip().strip("\"'")
    if not text:
        return False
    return _token_is_guard(text, _guard_path_keys())


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
    """The command is too large or took too long to scan. Callers ask for approval."""


def _scan_limit(reason: str) -> Decision:
    return Decision("escalate", "scan-limit", reason)


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
        if text.startswith("$(", i):
            tokens.append("$(")
            i += 2
            continue
        if text[i] in "(){}`":
            tokens.append(text[i])
            i += 1
            continue
        if text[i] in {"'", '"'}:
            quote = text[i]
            i += 1
            buf: list[str] = []
            interrupted = False
            while i < n and text[i] != quote:
                # $(...) and backticks run inside double quotes. A plain
                # parenthesis does not, so a quoted "(rm ...)" stays text.
                if quote == '"' and (text[i] == "`" or text.startswith("$(", i)):
                    if buf:
                        tokens.append("".join(buf))
                    tokens.append("`" if text[i] == "`" else "$(")
                    i += 1 if text[i] == "`" else 2
                    interrupted = True
                    break
                if text[i] == "\\" and quote == '"' and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                buf.append(text[i])
                i += 1
            if interrupted:
                continue
            if i < n and text[i] == quote:
                i += 1
            tokens.append("".join(buf))
            continue
        start = i
        buf = []
        param = 0
        while i < n and text[i] not in " \t\r\n;|&<>(){}`":
            if text.startswith("$(", i):
                break
            buf.append(text[i])
            i += 1
        # The stop set above leaves ${HOME} intact: "{" after "$" is the
        # expansion, not a brace group. Resume when the word loop parked on it.
        while i < n and param == 0 and i > start and buf and buf[-1] == "$" and text[i] == "{":
            param = 1
            buf.append("{")
            i += 1
            while i < n and param:
                if text[i] == "{":
                    param += 1
                elif text[i] == "}":
                    param -= 1
                elif text[i] in " \t\r\n;|&<>()`" or text.startswith("$(", i):
                    break
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
        if token in _STATEMENT_SEPARATORS:
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


def _drop_wrappers(argv: list[str]) -> list[str]:
    """Drop wrappers and the values their flags take. The command path stays intact."""
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
    return words


def _unwrap_sudo(argv: list[str]) -> list[str]:
    """Drop wrappers and the values their flags take. ``/bin/rm`` becomes ``rm``."""
    words = _drop_wrappers(argv)
    if words:
        words[0] = _basename(words[0])
    return words


def _strip_quotes(text: str) -> str:
    return re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"", " ", text)


def _posix_root_operand(value: str, cwd: str | None) -> bool:
    if value and set(value) <= {"/"}:
        return True
    if value in _ROOT_PATHS:
        return True
    for root in _POSIX_ROOTS:
        if value in {root, root + "/", root + "/*"}:
            return True
    if value.startswith("/home/"):
        rest = value[len("/home/") :]
        if rest.endswith("/*"):
            rest = rest[:-2]
        rest = rest.rstrip("/")
        if rest and "/" not in rest and rest not in {".", ".."}:
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


def _split_statements(text: str) -> list[str]:
    """Split on statement separators, groups, and substitutions. One pass.

    ``( ) { } $(`` and backticks are boundaries, so a grouped ``rm`` is its
    own statement. Quotes stay intact, and ``${name}`` stays one span.
    ``$(`` and a backtick inside double quotes are still boundaries, because
    the shell runs them. A parenthesis inside quotes is not.
    """
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(text)
    quote = ""
    param = 0
    while i < n:
        ch = text[i]
        if quote == "'":
            buf.append(ch)
            if ch == "'":
                quote = ""
            i += 1
            continue
        if quote == '"':
            if ch == "\\" and i + 1 < n:
                buf.append(ch)
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == "`" or text.startswith("$(", i):
                parts.append("".join(buf))
                buf = []
                i += 1 if ch == "`" else 2
                quote = ""
                continue
            buf.append(ch)
            if ch == '"':
                quote = ""
            i += 1
            continue
        if param:
            buf.append(ch)
            if ch == "{":
                param += 1
            elif ch == "}":
                param -= 1
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if text.startswith("&&", i) or text.startswith("||", i) or text.startswith("$(", i):
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch == "{" and buf and buf[-1] == "$":
            buf.append(ch)
            param = 1
            i += 1
            continue
        if ch in ";&|\n(){}`":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _is_cli_word(word: str) -> bool:
    slash = word.replace("\\", "/")
    if slash.startswith("./"):
        slash = slash[2:]
    if slash.endswith("/cli.py") and "bprotective/cli.py" in slash:
        return True
    if slash in {"bprotective", "scripts/bprotective"}:
        return True
    if slash.endswith("/bprotective"):
        return True
    if slash.endswith("/scripts/bprotective") or slash == "scripts/bprotective":
        return True
    return False


def _argv_is_control(words: list[str]) -> bool:
    if len(words) < 2 or words[1] not in _CONTROL_VERBS:
        return False
    return _is_cli_word(words[0])


def _statement_is_control(statement: str) -> bool:
    words = _drop_wrappers(statement.split())
    if not words:
        return False
    if words[0] in {"python", "python3", "py"}:
        rest = words[1:]
        if rest and rest[0] == "-3":
            rest = rest[1:]
        return _argv_is_control(rest)
    return _argv_is_control(words)


def _is_control_command(surface: str) -> bool:
    """True for a shell command that runs bprotective on, off, yes, no, or recover.

    The scan is a straight walk. It does not use a nested ``\\S*`` pattern,
    which backtracked on long runs of ``&`` and ``;``.
    """
    lowered = surface.lower()
    if "bprotective" not in lowered:
        return False
    statements = _split_statements(lowered)
    if any(_statement_is_control(statement) for statement in statements):
        return True
    # `B=scripts/bprotective; python3 $B off` names the launcher, then the verb.
    if "scripts/bprotective" not in lowered and "scripts\\bprotective" not in lowered:
        if "bprotective/cli.py" not in lowered and "bprotective\\cli.py" not in lowered:
            return False
    for statement in statements:
        words = _drop_wrappers(statement.split())
        if not words or words[0] not in {"python", "python3", "py"}:
            continue
        rest = words[1:]
        if rest and rest[0] == "-3":
            rest = rest[1:]
        if any(word in _CONTROL_VERBS for word in rest):
            return True
    return False


def _path_key(path: Path) -> str:
    """Stable path key. An unknown ``~user`` must not raise and become a deny."""
    try:
        expanded = path.expanduser()
    except (RuntimeError, ValueError, OSError):
        expanded = path
    return os.path.normcase(os.path.normpath(str(expanded.absolute())))


def _guard_path_keys() -> set[str]:
    """Absolute paths of the state file, its marker, and the armed record.

    The content-root State directory is not one of these. Files inside it are
    ordinary instance files. Removing or moving that directory itself is a
    separate check.
    """
    return {
        _path_key(state_path()),
        _path_key(_armed_path(state_path())),
        _path_key(armed_record_path()),
        _path_key(Path.home() / ".bprotective"),
        _path_key(Path.home() / ".bprotective" / "armed.json"),
    }


def _state_directory_keys() -> set[str]:
    content = content_root()
    if content is None:
        return set()
    return {_path_key(content / "State")}


def _command_tokens(surface: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    for ch in surface:
        if ch in " \t\r\n;&|<>":
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _token_is_guard(token: str, keys: set[str]) -> bool:
    """True when this one path is a real guard path, not any folder named state."""
    raw = token.strip().strip("'\"")
    if not raw or raw in {".", ".."}:
        return False
    slash = raw.replace("\\", "/")
    lower = slash.lower()
    if (
        lower == ".bprotective"
        or lower.startswith(".bprotective/")
        or lower.startswith("~/.bprotective")
        or "/.bprotective" in "/" + lower
    ):
        return True
    base = lower.rstrip("/").rsplit("/", 1)[-1]
    if base in _STATE_FILE_NAMES:
        return True
    try:
        candidate = _path_key(Path(raw))
    except OSError:
        return False
    return candidate in keys


def _might_name_guard(surface: str) -> bool:
    """Cheap reject for commands that cannot name a guard path."""
    if "bprotective.json" in surface.lower() or ".bprotective" in surface.lower():
        return True
    if "bSmart/State" in surface or "bSmart\\State" in surface or "State" in surface:
        return True
    return "/" in surface or "\\" in surface


def _mentions_guard_path(surface: str, keys: set[str]) -> bool:
    return any(_token_is_guard(token, keys) for token in _command_tokens(surface))


def _bare_token(token: str) -> str:
    return token.strip().strip("'\"")


def _is_state_directory_operand(token: str, keys: set[str]) -> bool:
    """True for the State directory itself, not for a file inside it.

    Relative names are case-sensitive, so ``src/state`` is a different path.
    An absolute path matches only the content-root State directory.
    """
    raw = _bare_token(token)
    if not raw or raw in {".", ".."}:
        return False
    normalized = os.path.normpath(raw.replace("\\", "/")).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in {"State", "bSmart/State"}:
        return True
    try:
        candidate = _path_key(Path(raw))
    except OSError:
        return False
    return candidate in keys


def _rm_targets_state_dir(argv: list[str], keys: set[str]) -> bool:
    if not argv or argv[0] != "rm":
        return False
    recursive = False
    operands: list[str] = []
    ended = False
    for arg in argv[1:]:
        bare = _bare_token(arg)
        if ended:
            operands.append(bare)
            continue
        if bare == "--":
            ended = True
            continue
        if bare in {"--recursive", "--force"} or bare.startswith("--recursive=") or bare.startswith("--force="):
            if bare.startswith("--recursive"):
                recursive = True
            continue
        if bare.startswith("--"):
            continue
        if bare.startswith("-") and len(bare) > 1:
            if "r" in bare[1:].lower():
                recursive = True
            continue
        operands.append(bare)
    if not recursive:
        return False
    return any(_is_state_directory_operand(item, keys) for item in operands)


def _move_targets_state_dir(argv: list[str], keys: set[str]) -> bool:
    if not argv or argv[0] not in {"mv", "move", "move-item"}:
        return False
    sources: list[str] = []
    used_target = False
    index = 1
    while index < len(argv):
        arg = argv[index]
        bare = _bare_token(arg)
        key = bare.lower().split("=", 1)[0]
        if bare == "--":
            index += 1
            continue
        if key in {"-t", "--target-directory"}:
            used_target = True
            if "=" not in bare:
                index += 1
            index += 1
            continue
        if key in {"-destination", "-newname"}:
            if "=" not in bare:
                index += 1
            index += 1
            continue
        if key in {"-path", "-literalpath"}:
            if "=" in bare:
                sources.append(_bare_token(bare.split("=", 1)[1]))
            elif index + 1 < len(argv):
                sources.append(_bare_token(argv[index + 1]))
                index += 1
            index += 1
            continue
        if bare.startswith("-"):
            index += 1
            continue
        sources.append(bare)
        index += 1
    if not used_target and len(sources) > 1:
        sources = sources[:-1]
    return any(_is_state_directory_operand(item, keys) for item in sources)


def _remove_item_targets_state_dir(argv: list[str], keys: set[str]) -> bool:
    if not argv or argv[0] not in {"remove-item", "rmdir", "rd"}:
        return False
    if argv[0] == "remove-item":
        recursive = False
        for arg in argv[1:]:
            if _bare_token(arg).lower().split("=", 1)[0] in {"-recurse", "-r"}:
                recursive = True
        if not recursive:
            return False
    operands: list[str] = []
    index = 1
    while index < len(argv):
        bare = _bare_token(argv[index])
        key = bare.lower().split("=", 1)[0]
        if key in {"-path", "-literalpath"}:
            if "=" in bare:
                operands.append(_bare_token(bare.split("=", 1)[1]))
            elif index + 1 < len(argv):
                operands.append(_bare_token(argv[index + 1]))
                index += 1
            index += 1
            continue
        if bare.startswith("-") or bare.startswith("/"):
            index += 1
            continue
        operands.append(bare)
        index += 1
    return any(_is_state_directory_operand(item, keys) for item in operands)


def _removes_or_moves_state_dir(command: str) -> bool:
    """True when a command recursively removes or moves the State directory itself."""
    keys = _state_directory_keys()
    for statement in _split_statements(command):
        words = _unwrap_sudo(statement.split())
        if not words:
            continue
        if words[0] == "git" and len(words) > 1 and words[1] == "mv":
            words = ["mv", *words[2:]]
        if (
            _rm_targets_state_dir(words, keys)
            or _move_targets_state_dir(words, keys)
            or _remove_item_targets_state_dir(words, keys)
        ):
            return True
    return False


def _channel_block(command: str) -> Decision | None:
    """Block shell control of the guard and writes that name its real files.

    Groups, subshells, ``$(...)``, and backticks are statement boundaries, so
    each piece is checked on its own. Quoted text is removed before the
    general path check, so a commit message that says "state" is not a path.
    The file match is the state file, its ``.armed`` marker, and
    ``~/.bprotective``. A file inside the content-root State directory is not
    a match. Recursive removal or a move of that directory itself is blocked,
    for the relative name and the absolute path. This is a heuristic for
    accidental commands. The armed record outside State is what fails closed
    after a tamper the heuristic missed.
    """
    # Control can span statements: `B=scripts/bprotective; python3 $B off`.
    # Keep the raw text so `$(...)` inside double quotes is still visible.
    # Groups are already boundaries inside that check.
    if _is_control_command(command):
        return Decision("block", "guard-control", "changing bProtective from a shell command")
    if _removes_or_moves_state_dir(command):
        return Decision("block", "state-dir", "recursive removal or move of the State directory")
    for statement in _split_statements(command):
        if not statement.strip():
            continue
        decision = _channel_statement(statement)
        if decision is not None:
            return decision
    return None


def _channel_statement(command: str) -> Decision | None:
    surface = _strip_quotes(command).strip()
    if not surface:
        return None
    names_file = "bprotective.json" in command.lower()
    if not names_file and not _might_name_guard(surface):
        return None
    if not (
        _WRITE_TOOL_RE.search(surface)
        or _STATE_MUTATE_RE.search(surface)
        or _GUARD_REDIRECT_RE.search(surface)
    ):
        return None
    if names_file or _mentions_guard_path(surface, _guard_path_keys()):
        return Decision("block", "state-file", "write, delete, or move of the bProtective state file")
    return None


def _dd_block(argv: list[str]) -> Decision | None:
    """Block ``dd of=/dev/...`` including ``of="/dev/sda"``. Quote stripping would hide that."""
    if not argv or _basename(argv[0]) != "dd":
        return None
    for index, arg in enumerate(argv):
        compact = arg.replace('"', "").replace("'", "").lower()
        if "of=/dev" in compact:
            return Decision("block", "device-format", "disk formatting or raw-device overwrite")
        if compact != "of":
            continue
        if index + 1 >= len(argv):
            continue
        nxt = argv[index + 1].replace('"', "").replace("'", "")
        if nxt == "=" and index + 2 < len(argv):
            device = argv[index + 2].replace('"', "").replace("'", "").lower()
        else:
            device = nxt[1:].lower() if nxt.startswith("=") else nxt.lower()
        if device.startswith("/dev"):
            return Decision("block", "device-format", "disk formatting or raw-device overwrite")
    return None


def _interpreter_exec_block(argv: list[str]) -> Decision | None:
    """Block ``perl -e 'system("rm -rf /")'`` and the same shape in other interpreters."""
    if not argv or argv[0] not in {"perl", "ruby", "node", "php", "python", "python3", "py"}:
        return None
    body: str | None = None
    for index, arg in enumerate(argv):
        if arg in {"-e", "-c"} and index + 1 < len(argv):
            body = argv[index + 1]
            break
    if not body:
        return None
    lowered = body.lower()
    marker = "rm -rf "
    start = 0
    while True:
        index = lowered.find(marker, start)
        if index < 0:
            return None
        rest = body[index + len(marker) :].lstrip()
        operand: list[str] = []
        for ch in rest:
            if ch in " \t\r\n\"');|&":
                break
            operand.append(ch)
        if _posix_root_operand("".join(operand), None):
            return Decision("block", "root-recursive-delete", "recursive deletion of a protected root or home path")
        start = index + len(marker)


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
        if any(_posix_root_operand(token, cwd) for token in tokens if token not in _STATEMENT_SEPARATORS):
            return Decision("block", "root-recursive-delete", "recursive deletion of a protected root or home path")
    return None


def _structured_decision(command: str, tokens: list[str], *, _skip_channel: bool = False) -> Decision | None:
    if not _skip_channel:
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
            _interpreter_exec_block(argv),
            _dd_block(argv),
        )
        for decision in checks:
            if decision is None:
                continue
            if decision.action == "block":
                return decision
            if escalation is None:
                escalation = decision
    return escalation


def _fork_bomb_at(text: str) -> bool:
    """True when ``text`` starts with a fork bomb. The window is bounded."""
    if not text.startswith(":()"):
        return False
    j = 3
    n = len(text)
    for ch in "{:|:&};:":
        while j < n and text[j] in " \t\r":
            j += 1
        if j >= n or text[j] != ch:
            return False
        j += 1
    return True


def _linear_fork_bomb(lowered: str) -> bool:
    start = 0
    while True:
        index = lowered.find(":()", start)
        if index < 0:
            return False
        if _fork_bomb_at(lowered[index : index + 48]):
            return True
        start = index + 3


def _named_fork_bomb(text: str) -> bool:
    """True for ``name(){ name|name& };name``. One forward scan, bounded window."""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if not (ch.isalpha() or ch == "_"):
            i += 1
            continue
        start = i
        i += 1
        while i < n and (text[i].isalnum() or text[i] == "_"):
            i += 1
        name = text[start:i]
        j = i
        while j < n and text[j] in " \t":
            j += 1
        if j + 1 >= n or text[j] != "(" or text[j + 1] != ")":
            continue
        j += 2
        while j < n and text[j] in " \t\r\n":
            j += 1
        if j >= n or text[j] != "{":
            continue
        if _fork_body_calls_itself(text[j + 1 : j + 1 + 64 + 2 * len(name)], name):
            return True
    return False


def _fork_body_calls_itself(window: str, name: str) -> bool:
    k = 0
    m = len(window)

    def skip_space() -> None:
        nonlocal k
        while k < m and window[k] in " \t\r\n":
            k += 1

    skip_space()
    if not window.startswith(name, k):
        return False
    k += len(name)
    skip_space()
    if k >= m or window[k] != "|":
        return False
    k += 1
    skip_space()
    if not window.startswith(name, k):
        return False
    k += len(name)
    skip_space()
    if k >= m or window[k] != "&":
        return False
    k += 1
    skip_space()
    if k >= m or window[k] != "}":
        return False
    k += 1
    skip_space()
    if k >= m or window[k] != ";":
        return False
    k += 1
    skip_space()
    return window.startswith(name, k)


def _command_statements(text: str) -> list[list[str]]:
    """Split on statement separators, groups, and substitutions. One pass.

    ``${name}`` stays one word. ``$(`` and backticks are boundaries even when
    a double quote is sitting on them, so ``bash -c "rm -rf /"`` still splits
    into words the operand check can see.
    """
    statements: list[list[str]] = []
    current: list[str] = []
    buf: list[str] = []
    param = 0

    def flush_word() -> None:
        if buf:
            current.append("".join(buf))
            buf.clear()

    def flush_statement() -> None:
        flush_word()
        if current:
            statements.append(list(current))
            current.clear()

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if param:
            buf.append(ch)
            if ch == "{":
                param += 1
            elif ch == "}":
                param -= 1
            i += 1
            continue
        if ch in " \t\r":
            flush_word()
            i += 1
            continue
        if text.startswith("&&", i) or text.startswith("||", i) or text.startswith("$(", i):
            flush_statement()
            i += 2
            continue
        if ch == "{" and buf and buf[-1] == "$":
            buf.append(ch)
            param = 1
            i += 1
            continue
        if ch in ";&|\n(){}`":
            flush_statement()
            i += 1
            continue
        buf.append(ch)
        i += 1
    flush_statement()
    return statements


def _bare_word(word: str) -> str:
    return word.strip().strip("'\"")


def _is_recursive_rm_flag(arg: str) -> bool:
    bare = _bare_word(arg).lower()
    if bare in {"--recursive", "-recurse", "/s"} or bare.startswith("--recursive="):
        return True
    if bare.startswith("-") and not bare.startswith("--"):
        letters = bare[1:]
        # rm clusters are short (-rf). Do not treat -Force as recursive.
        return letters.isalpha() and "r" in letters and len(letters) <= 4
    return False


def _is_windows_root_operand(bare: str) -> bool:
    """True for a drive root, ``C:\\*.*``, or ``C:\\Users`` and one user under it."""
    text = bare.replace("/", "\\")
    if len(text) < 2 or not text[0].isalpha() or text[1] != ":":
        return False
    rest = text[2:].lower()
    if rest in {
        "",
        "\\",
        "\\*",
        "\\*.*",
        "\\windows",
        "\\users",
        "\\program files",
        "\\program files (x86)",
    }:
        return True
    prefix = "\\users\\"
    if rest.startswith(prefix):
        tail = rest[len(prefix) :].rstrip("\\")
        if tail.endswith("\\*"):
            tail = tail[:-2]
        return bool(tail) and "\\" not in tail and tail not in {".", ".."}
    return False


def _is_root_delete_operand(arg: str) -> bool:
    """True for ``/``, ``~``, ``$HOME``, ``/usr``, or a drive root. Not ``C:\\Windows\\Temp``."""
    bare = _bare_word(arg)
    if not bare:
        return False
    if _posix_root_operand(bare, None):
        return True
    return _is_windows_root_operand(bare)


def _past_deadline(deadline: float | None) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def _scan_words(words: list[str], deadline: float | None) -> Decision | None:
    """Every hard-block check for one statement, in one forward pass."""
    seen_rm = False
    seen_windows = False
    recursive = False
    root = False
    mkfs = False
    dd = False
    of_dev = False
    pending_of = False
    pending_eq = False
    format_verb = False
    format_volume = False
    diskpart = False
    seen_find = False
    seen_delete = False
    find_root = False
    for index, word in enumerate(words):
        if index % 256 == 0 and _past_deadline(deadline):
            return _scan_limit("command scan exceeded the time limit")
        bare = _bare_word(word)
        name = _basename(bare)
        lower = bare.replace('"', "").replace("'", "").lower()
        if name == "rm":
            seen_rm = True
        elif name in {"remove-item", "ri", "del", "erase", "rd", "rmdir"}:
            seen_windows = True
        elif name == "mkfs" or name.startswith("mkfs."):
            mkfs = True
        elif name == "dd":
            dd = True
        elif name == "format-volume":
            format_volume = True
        elif name in {"format", "format.com"}:
            format_verb = True
        elif name == "diskpart":
            diskpart = True
        elif name == "find":
            seen_find = True
        if bare == "-delete":
            seen_delete = True
        if "of=/dev" in lower:
            of_dev = True
        if pending_eq and lower.startswith("/dev"):
            of_dev = True
        pending_eq = pending_of and bare == "="
        pending_of = lower == "of" and bare != "="
        if (seen_rm or seen_windows) and name not in {"rm", "remove-item", "ri", "del", "erase", "rd", "rmdir"}:
            if _is_recursive_rm_flag(word):
                recursive = True
            elif _is_root_delete_operand(word):
                root = True
        if _is_root_delete_operand(word):
            find_root = True
        if recursive and root and (seen_rm or seen_windows):
            if seen_rm:
                return Decision(
                    "block",
                    "root-recursive-delete",
                    "recursive deletion of a protected root or home path",
                )
            return Decision(
                "block",
                "windows-root-recursive-delete",
                "recursive deletion of a Windows root, system, or home path",
            )
        if mkfs or (dd and of_dev):
            return Decision("block", "device-format", "disk formatting or raw-device overwrite")
        if format_volume or (format_verb and _is_root_delete_operand(word) and name not in {"format", "format.com"}):
            return Decision("block", "windows-format", "disk formatting")
        if diskpart:
            return Decision("block", "diskpart", "diskpart can erase or repartition disks")
        if seen_find and seen_delete and find_root:
            return Decision("block", "find-delete", "find -delete of a protected root")
    return None


def _oversized_hard_block(command: str, deadline: float | None = None) -> Decision | None:
    """Block catastrophic commands in text past the tokenizer cap.

    One forward scan. It does not run the full tokenizer. A match blocks.
    Past the time limit the caller asks instead of scanning until the harness
    gives up. No match lets the caller ask.
    """
    if deadline is None:
        deadline = time.monotonic() + _MAX_SCAN_SECONDS
    if _past_deadline(deadline):
        return _scan_limit("command scan exceeded the time limit")
    lowered = command.lower()
    if _linear_fork_bomb(lowered) or _named_fork_bomb(command):
        return Decision("block", "fork-bomb", "fork bomb")
    if _past_deadline(deadline):
        return _scan_limit("command scan exceeded the time limit")
    if not any(
        token in lowered
        for token in ("mkfs", "dd", "format", "diskpart", "rm", "remove-item", "rmdir", "del", "rd", "ri", "erase", "find")
    ):
        return None
    for words in _command_statements(command):
        if _past_deadline(deadline):
            return _scan_limit("command scan exceeded the time limit")
        decision = _scan_words(words, deadline)
        if decision is not None:
            return decision
    return None


def policy_decision(
    command: str,
    config: Config | None = None,
    _depth: int = 0,
    _deadline: float | None = None,
    _skip_channel: bool = False,
) -> Decision:
    """Return allow, escalate, or block from the command text. Ignores on/off state."""
    if _depth > 3:
        return Decision("block", "nested-shell", "nested shell command was not expanded")
    if len(command) > _MAX_COMMAND_CHARS:
        deadline = _deadline if _deadline is not None else time.monotonic() + _MAX_SCAN_SECONDS
        if not _skip_channel:
            channel = _channel_block(command)
            if channel is not None:
                return channel
        hard = _oversized_hard_block(command, deadline)
        if hard is not None:
            return hard
        return _scan_limit("command exceeds the scan size limit")
    deadline = _deadline if _deadline is not None else time.monotonic() + _MAX_SCAN_SECONDS
    if time.monotonic() >= deadline:
        return _scan_limit("command scan exceeded the time limit")
    try:
        tokens = _tokenize(command, deadline)
    except ScanLimit as exc:
        return _scan_limit(str(exc))
    active = config or EMPTY_CONFIG
    structured = _structured_decision(command, tokens, _skip_channel=_skip_channel)
    if structured is not None and structured.action == "block":
        return structured
    surface = _strip_quotes(command)
    if _named_fork_bomb(command):
        return Decision("block", "fork-bomb", "fork bomb")
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
    state = read_state()
    if state.get("error"):
        return Decision("block", "state-invalid", str(state["error"]))
    enabled = bool(state.get("enabled"))
    # Past the tokenizer cap, still run the linear channel check and a linear
    # hard-block scan over the whole text. Ask only when neither matches.
    # On and off follow the same rules as a command under the cap.
    if len(command) > _MAX_COMMAND_CHARS:
        deadline = time.monotonic() + _MAX_SCAN_SECONDS
        if via_hook or enabled:
            channel = _channel_block(command)
            if channel is not None:
                return channel
        if enabled:
            hard = _oversized_hard_block(command, deadline)
            if hard is not None and hard.action == "block":
                return hard
            decision = hard if hard is not None else _scan_limit("command exceeds the scan size limit")
            allowed = state.get("allow_once")
            if isinstance(allowed, str) and allowed == command.strip():
                state["allow_once"] = None
                write_state(state)
                return Decision("allow", "allow-once", "operator approved this command once")
            return decision
        return Decision("allow", "disabled", "bProtective is off")
    # One channel check per call. via_hook still blocks guard control while off.
    # A direct check while off does not, so `bprotective check` stays quiet.
    if via_hook or enabled:
        channel = _channel_block(command)
        if channel is not None:
            return channel
    if not enabled:
        return Decision("allow", "disabled", "bProtective is off")
    config, error = load_config()
    if error:
        return Decision("block", "config-invalid", error)
    decision = policy_decision(command, config, _skip_channel=True)
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
            [a-z]:\\\*\.\*
            | [a-z]:\\users\\[^\\\s"'`]+\\?\*?
            | [a-z]:(?:\\(?:\*|windows|users|program\ files(?:\ \(x86\))?)?)?
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
