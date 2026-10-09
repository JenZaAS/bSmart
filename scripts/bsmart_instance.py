"""Instance paths shared by the checkout scripts in this directory.

Those scripts import this module by name after putting this directory on
sys.path. A normal launch already does that; the scripts also insert it so
runpy and other loaders can import the helper. bStart.py and the client
adapters load this file by path, because the workspace-root bStart.py copy
does not live next to it.
"""

from __future__ import annotations

import os
from pathlib import Path

CONTAINER_WORKSPACE = Path("/workspace")


def default_content_root(system_root: Path) -> Path:
    """Sibling bSmart next to this checkout.

    /workspace/bSmart is only the fallback for the container checkout itself.
    Another instance must not inherit that directory just because it exists.
    The system path is the one used to launch the script, not a symlink target.
    """
    sibling = system_root.parent / "bSmart"
    container = CONTAINER_WORKSPACE / "bSmart"
    if sibling.is_dir():
        return sibling
    if os.path.normpath(str(system_root.parent.absolute())) == os.path.normpath(str(CONTAINER_WORKSPACE)) and container.is_dir():
        return container
    return sibling


def workspace_for_system(system: Path, container: Path = CONTAINER_WORKSPACE) -> Path:
    """Parent of this checkout when that parent owns this bSmart-System.

    Falls back to the container workspace otherwise. absolute() keeps a
    symlinked checkout on the instance that launched it.
    """
    system_abs = Path(os.path.normpath(str(system.absolute())))
    parent = system_abs.parent
    own = parent / "bSmart-System"
    if own.exists() and os.path.normpath(str(own.absolute())) == os.path.normpath(str(system_abs)):
        return parent
    return container


def spec_block_value(text: str, block: str, key: str) -> str | None:
    """Read one scalar from a top-level yamlish block."""
    in_block = False
    for line in text.splitlines():
        if not line.startswith((" ", "\t")):
            in_block = line.strip() == f"{block}:"
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped.startswith(f"{key}:"):
            continue
        value = stripped.split(":", 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if value:
            return value
    return None


def resolve_recorded_path(workspace: Path, raw: str | None) -> Path | None:
    """Resolve a spec path against the workspace unless it is already absolute."""
    if raw is None:
        return None
    value = raw.strip()
    if not value or value.startswith("TODO") or value.startswith("<"):
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.absolute()
    return (workspace / path).absolute()


def default_storage_spec(workspace: Path) -> Path:
    return workspace / "bSmart" / "State" / "container-storage.yaml"


def readable_dir(path: Path) -> bool:
    try:
        return path.is_dir() and os.access(path, os.R_OK)
    except OSError:
        return False


def select_instance_project_root(
    workspace: Path,
    environ: dict[str, str] | None = None,
    spec_path: Path | None = None,
    mounted: Path = Path("/projects"),
) -> Path | None:
    """Project root for this instance.

    Environment override wins. A recorded storage spec wins over a mounted
    /projects directory and over ./projects, so a stale mount does not hide
    internal storage. Absolute spec paths are used as written.
    """
    env = os.environ if environ is None else environ
    override = env.get("BSMART_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser()
        return candidate.resolve() if readable_dir(candidate) else None
    spec = spec_path if spec_path is not None else default_storage_spec(workspace)
    if spec.is_file():
        try:
            text = spec.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        recorded = resolve_recorded_path(workspace, spec_block_value(text, "project_storage", "project_root"))
        if recorded is not None and readable_dir(recorded):
            return recorded.resolve()
    for candidate in (mounted, workspace / "projects"):
        if readable_dir(candidate):
            return candidate.resolve()
    return None


def git_safe_directory(repo: Path) -> str:
    """Path Git can compare on Windows.

    safe.directory is matched literally. A backslash is easy for Git to treat
    as an escape, so the value uses forward slashes.
    """
    return os.path.normpath(str(repo)).replace("\\", "/")
