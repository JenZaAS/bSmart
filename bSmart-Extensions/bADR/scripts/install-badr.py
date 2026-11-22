#!/usr/bin/env python3
"""Create the standard bADR project files without overwriting existing files."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
# (file in the project's ADR folder, template it is copied from)
FILES = (
    ("README.md", "README.template.md"),
    ("template.md", "template.md"),
    ("template-short.md", "template-short.md"),
)


DEFAULT_ADR_PATH = "docs/adr"


def install(project_root: Path, force: bool = False, adr_path: str = DEFAULT_ADR_PATH) -> list[Path]:
    target = project_root.resolve() / Path(adr_path)
    target.mkdir(parents=True, exist_ok=True)
    created = []
    for name, source in FILES:
        dst = target / name
        if force or not dst.exists():
            text = (TEMPLATES / source).read_text(encoding="utf-8")
            dst.write_text(text, encoding="utf-8", newline="\n")
            created.append(dst)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--force", action="store_true", help="overwrite bADR-managed files")
    parser.add_argument("--adr-path", default=DEFAULT_ADR_PATH,
                        help="ADR folder relative to the project (match adr_path in project.md); default docs/adr")
    args = parser.parse_args()
    if Path(args.adr_path).is_absolute() or ".." in Path(args.adr_path).parts:
        parser.error("--adr-path must be a relative path inside the project")
    created = install(Path(args.project_root), args.force, args.adr_path)
    for path in created:
        print(f"created {path}")
    if not created:
        print("bADR files already present; no changes made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
