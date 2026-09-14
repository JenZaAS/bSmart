#!/usr/bin/env python3
"""Create the standard bADR project files without overwriting existing files."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def install(project_root: Path, force: bool = False) -> list[Path]:
    target = project_root.resolve() / "docs" / "adr"
    target.mkdir(parents=True, exist_ok=True)
    created = []
    for name in ("README.md", "template.md"):
        dst = target / name
        if force or not dst.exists():
            dst.write_text((TEMPLATES / ("README.template.md" if name == "README.md" else name)).read_text(encoding="utf-8"), encoding="utf-8")
            created.append(dst)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--force", action="store_true", help="overwrite bADR-managed files")
    args = parser.parse_args()
    created = install(Path(args.project_root), args.force)
    for path in created:
        print(f"created {path}")
    if not created:
        print("bADR files already present; no changes made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
