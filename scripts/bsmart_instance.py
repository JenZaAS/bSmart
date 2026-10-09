"""Instance paths shared by the checkout scripts in this directory.

Those scripts import this module by name after putting this directory on
sys.path. A normal launch already does that; the scripts also insert it so
runpy and other loaders can import the helper. The workspace-root bStart.py
copy does not import this module: that file is installed on its own and keeps
its own copy of the content-root rule.
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


def git_safe_directory(repo: Path) -> str:
    """Path Git can compare on Windows.

    safe.directory is matched literally. A backslash is easy for Git to treat
    as an escape, so the value uses forward slashes.
    """
    return os.path.normpath(str(repo)).replace("\\", "/")
