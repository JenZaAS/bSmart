#!/usr/bin/env python3
"""bSelective MATLAB v1: one list command and one get command."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import argparse
import json
import re
import sys

SECTION_RE = re.compile(r"^\s*(classdef|properties|methods|function|if|for|parfor|while|switch|try|spmd|arguments|end)\b(.*)$", re.IGNORECASE)
BLOCK_START_KEYWORDS = {"classdef", "properties", "methods", "function", "if", "for", "parfor", "while", "switch", "try", "spmd", "arguments"}
CLASSDEF_RE = re.compile(r"^\s*classdef\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z]\w*)", re.IGNORECASE)
FUNCTION_RE = re.compile(
    r"^\s*function\s+(?:(?P<outputs>\[[^\]]+\]|[A-Za-z]\w*)\s*=\s*)?(?P<name>[A-Za-z]\w*(?:\.[A-Za-z]\w*)?)\s*(?P<args>\([^)]*\))?",
    re.IGNORECASE,
)
PROPERTY_LINE_RE = re.compile(r"^\s*(?P<name>[A-Za-z]\w*)\s*(?:[=;{(].*)?$")


@dataclass
class Block:
    kind: str
    name: str | None
    start_line: int
    end_line: int
    header: str
    attributes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_lines(file: str | Path) -> list[str]:
    return Path(file).read_text(encoding="utf-8").splitlines()


def _first_help_block(lines: list[str]) -> list[str]:
    help_lines: list[str] = []
    seen_declaration = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if help_lines:
                help_lines.append("")
            continue
        if stripped.startswith("%"):
            if seen_declaration or not help_lines:
                help_lines.append(stripped.lstrip("%").strip())
                continue
        if stripped.lower().startswith(("classdef", "function")):
            seen_declaration = True
            continue
        if seen_declaration or help_lines:
            break
    while help_lines and help_lines[-1] == "":
        help_lines.pop()
    return help_lines


def _find_matching_end(lines: list[str], start_index: int) -> int:
    depth = 0
    started = False
    for idx in range(start_index, len(lines)):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("%"):
            continue
        match = SECTION_RE.match(lines[idx])
        if not match:
            continue
        keyword = match.group(1).lower()
        if keyword in BLOCK_START_KEYWORDS:
            depth += 1
            started = True
        elif keyword == "end" and started:
            depth -= 1
            if depth <= 0:
                return idx + 1
    return len(lines)


def _discover_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        class_match = CLASSDEF_RE.match(line)
        if class_match:
            blocks.append(Block("class", class_match.group("name"), idx + 1, _find_matching_end(lines, idx), stripped))
            continue
        if re.match(r"^\s*properties\b", line, re.IGNORECASE):
            attrs = stripped[len("properties"):].strip()
            blocks.append(Block("properties", None, idx + 1, _find_matching_end(lines, idx), stripped, attrs))
            continue
        if re.match(r"^\s*methods\b", line, re.IGNORECASE):
            attrs = stripped[len("methods"):].strip()
            blocks.append(Block("methods", None, idx + 1, _find_matching_end(lines, idx), stripped, attrs))
            continue
        func_match = FUNCTION_RE.match(line)
        if func_match:
            blocks.append(Block("function", func_match.group("name"), idx + 1, _find_matching_end(lines, idx), stripped))
    return blocks


def _class_name(lines: list[str]) -> str | None:
    for line in lines:
        match = CLASSDEF_RE.match(line)
        if match:
            return match.group("name")
    return None


def _signature(block: Block) -> dict[str, Any]:
    match = FUNCTION_RE.match(block.header)
    if not match:
        return block.to_dict()
    return {
        **block.to_dict(),
        "name": match.group("name"),
        "signature": block.header.strip(),
        "outputs": (match.group("outputs") or "").strip(),
        "args": (match.group("args") or "()").strip(),
    }


def _properties(lines: list[str], names: list[str] | None = None, constants_only: bool = False) -> list[dict[str, Any]]:
    wanted = {name.lower() for name in names} if names else None
    out = []
    for block in _discover_blocks(lines):
        if block.kind != "properties":
            continue
        is_constant = "constant" in block.attributes.lower()
        if constants_only and not is_constant:
            continue
        for line_no in range(block.start_line + 1, block.end_line):
            stripped = lines[line_no - 1].strip()
            if not stripped or stripped.startswith("%") or stripped.lower() == "end":
                continue
            match = PROPERTY_LINE_RE.match(lines[line_no - 1])
            if not match:
                continue
            name = match.group("name")
            if wanted and name.lower() not in wanted:
                continue
            out.append({"name": name, "line": line_no, "source": stripped, "attributes": block.attributes, "constant": is_constant})
    return out


def _functions(lines: list[str], names: list[str] | None = None) -> list[dict[str, Any]]:
    wanted = {name.lower() for name in names} if names else None
    out = []
    for block in _discover_blocks(lines):
        if block.kind != "function" or not block.name:
            continue
        if wanted and block.name.lower() not in wanted:
            continue
        out.append(_signature(block))
    return out


def _function_source(lines: list[str], name: str) -> dict[str, Any]:
    for block in _discover_blocks(lines):
        if block.kind == "function" and block.name and block.name.lower() == name.lower():
            return {**_signature(block), "source": "\n".join(lines[block.start_line - 1 : block.end_line]) + "\n"}
    raise KeyError(f"Function/method not found: {name}")


def _function_help(lines: list[str], name: str) -> dict[str, Any]:
    source = _function_source(lines, name)
    idx = source["start_line"]
    help_lines = []
    while idx < len(lines):
        stripped = lines[idx].strip()
        if stripped.startswith("%"):
            help_lines.append(stripped.lstrip("%").strip())
            idx += 1
            continue
        if not stripped and help_lines:
            help_lines.append("")
            idx += 1
            continue
        break
    while help_lines and help_lines[-1] == "":
        help_lines.pop()
    return {"name": name, "start_line": source["start_line"], "help": help_lines}


def _refs(symbol: str, scope: str | Path) -> list[dict[str, Any]]:
    root = Path(scope)
    files = [root] if root.is_file() else sorted(root.rglob("*.m"))
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    matches = []
    for file in files:
        for idx, line in enumerate(_read_lines(file), start=1):
            stripped = line.strip()
            if pattern.search(stripped):
                matches.append({"file": str(file), "line": idx, "text": stripped})
    return matches


def _line_context(lines: list[str], target: str, default_radius: int = 5) -> dict[str, Any]:
    parts = target.split(":", 1)
    line_no = int(parts[0])
    radius = int(parts[1]) if len(parts) == 2 and parts[1] else default_radius
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    return {
        "start_line": start,
        "end_line": end,
        "lines": [{"line": idx, "text": lines[idx - 1]} for idx in range(start, end + 1)],
    }


def list_items(file: str | Path, kind: str = "all", target: str | None = None) -> dict[str, Any]:
    """List available MATLAB source parts. `list all` is the preferred first peek."""
    lines = _read_lines(file)
    kind = kind.lower().replace("-", "_")
    funcs = _functions(lines)
    props = _properties(lines)
    data = {"file": str(file), "kind": kind}
    if kind in {"all", "outline"}:
        data.update({
            "class": _class_name(lines),
            "header_lines": len(_first_help_block(lines)),
            "constants": [p for p in props if p["constant"]],
            "properties": props,
            "functions": funcs,
            "getters": [f for f in funcs if f["name"].lower().startswith("get.")],
            "setters": [f for f in funcs if f["name"].lower().startswith("set.")],
        })
    elif kind in {"header", "help"}:
        data["header_available"] = bool(_first_help_block(lines))
    elif kind in {"constant", "constants", "constant_property", "constant_properties"}:
        data["constants"] = [p for p in props if p["constant"]]
    elif kind in {"property", "properties"}:
        data["properties"] = props
    elif kind in {"function", "functions", "method", "methods"}:
        data["functions"] = funcs
    elif kind in {"getter", "getters"}:
        data["getters"] = [f for f in funcs if f["name"].lower().startswith("get.")]
    elif kind in {"setter", "setters"}:
        data["setters"] = [f for f in funcs if f["name"].lower().startswith("set.")]
    elif kind in {"ref", "refs", "reference", "references"}:
        if not target:
            raise ValueError("list refs requires TARGET symbol")
        data["references"] = _refs(target, file)
    else:
        raise ValueError(f"Unknown list kind: {kind}")
    return data


def get_item(file: str | Path, kind: str, target: str | None = None) -> dict[str, Any] | str:
    """Get one selected MATLAB source part; `get all` returns the full file."""
    lines = _read_lines(file)
    kind = kind.lower().replace("-", "_")
    if kind == "all":
        return "\n".join(lines) + "\n"
    if kind in {"header", "help"} and target is None:
        return {"file": str(file), "kind": "header", "help": _first_help_block(lines)}
    if kind in {"help", "function_help", "method_help"} and target:
        return {"file": str(file), "kind": kind, **_function_help(lines, target)}
    if kind in {"outline", "list"}:
        return list_items(file, "all")
    if kind in {"constant", "constant_property"}:
        if not target:
            return {"file": str(file), "kind": kind, "constants": _properties(lines, constants_only=True)}
        matches = _properties(lines, [target], constants_only=True)
        if not matches:
            raise KeyError(f"Constant property not found: {target}")
        return {"file": str(file), "kind": kind, "constant": matches[0]}
    if kind == "constants":
        return {"file": str(file), "kind": kind, "constants": _properties(lines, constants_only=True)}
    if kind in {"property", "properties"}:
        matches = _properties(lines, [target] if target else None)
        if target and not matches:
            raise KeyError(f"Property not found: {target}")
        return {"file": str(file), "kind": kind, "properties": matches}
    if kind in {"function", "method", "source", "getter", "setter"}:
        if not target:
            raise ValueError(f"get {kind} requires TARGET")
        return {"file": str(file), "kind": kind, **_function_source(lines, target)}
    if kind in {"functions", "methods"}:
        return {"file": str(file), "kind": kind, "functions": _functions(lines)}
    if kind in {"line", "context"}:
        if not target:
            raise ValueError("get line requires TARGET line number, optionally LINE:RADIUS")
        return {"file": str(file), "kind": kind, **_line_context(lines, target)}
    if kind in {"ref", "refs", "reference", "references"}:
        if not target:
            raise ValueError("get refs requires TARGET symbol")
        return {"file": str(file), "kind": kind, "references": _refs(target, file)}
    raise ValueError(f"Unknown get kind: {kind}")


# Backward-compatible Python aliases for early prototype callers.
def get_file_summary(file: str | Path) -> dict[str, Any]:
    return list_items(file, "all")


def get_class_outline(file: str | Path) -> dict[str, Any]:
    return list_items(file, "all")


def get_method_signatures(file: str | Path) -> list[dict[str, Any]]:
    return _functions(_read_lines(file))


def get_function_help(file: str | Path, name: str | None = None) -> dict[str, Any]:
    result = get_item(file, "help", name)
    assert isinstance(result, dict)
    return result


def get_method_source(file: str | Path, name: str) -> dict[str, Any]:
    result = get_item(file, "function", name)
    assert isinstance(result, dict)
    return result


def get_property_definitions(file: str | Path, names: list[str] | None = None) -> dict[str, Any]:
    return {"file": str(file), "properties": _properties(_read_lines(file), names)}


def get_local_functions(file: str | Path) -> list[dict[str, Any]]:
    funcs = _functions(_read_lines(file))
    return funcs[1:] if len(funcs) > 1 else []


def find_symbol_references(symbol: str, scope: str | Path) -> list[dict[str, Any]]:
    return _refs(symbol, scope)



def _compact_name(signature: dict[str, Any]) -> str:
    name = signature.get("name") or "<unknown>"
    args = signature.get("args") or "(...)"
    if args == "()":
        return f"{name}()"
    if len(args) > 32:
        args = "(...)"
    return f"{name}{args}"


def _function_range(signature: dict[str, Any]) -> str:
    return f"{signature.get('start_line', '?')}-{signature.get('end_line', '?')}"


def format_list_text(data: dict[str, Any], compact: bool = True) -> str:
    """Format list output for token-conscious agent use."""
    lines: list[str] = []
    file = Path(data.get("file", ""))
    try:
        line_count = len(_read_lines(file)) if file else 0
    except Exception:
        line_count = 0
    funcs = data.get("functions", []) or []
    props = data.get("properties", []) or []
    constants = data.get("constants", []) or []
    getters = data.get("getters", []) or []
    setters = data.get("setters", []) or []

    if data.get("class"):
        lines.append(f"class: {data['class']}")
    if line_count:
        lines.append(f"lines: {line_count}")
    if "header_lines" in data:
        lines.append(f"header_lines: {data.get('header_lines', 0)}")

    if props or constants:
        private = [p for p in props if "private" in str(p.get("attributes", "")).lower()]
        public = [p for p in props if "private" not in str(p.get("attributes", "")).lower() and not p.get("constant")]
        constant_count = len(constants) if constants else len([p for p in props if p.get("constant")])
        lines.append("")
        lines.append("properties:")
        lines.append(f"  total: {len(props)}")
        lines.append(f"  constants: {constant_count}")
        if private:
            lines.append(f"  private: {len(private)}")
        if public:
            lines.append(f"  public: {len(public)}")

    if funcs:
        normal_funcs = [f for f in funcs if not str(f.get("name", "")).lower().startswith(("get.", "set."))]
        accessor_count = len(funcs) - len(normal_funcs)
        display_funcs = normal_funcs if compact else funcs
        lines.append("")
        lines.append("functions:")
        for f in display_funcs:
            lines.append(f"  {_function_range(f)} {_compact_name(f)}")
        if compact and accessor_count:
            lines.append("")
            lines.append("accessors:")
            lines.append(f"  getters/setters: {accessor_count} collapsed")
    elif getters or setters:
        lines.append("")
        lines.append("accessors:")
        lines.append(f"  getters/setters: {len(getters) + len(setters)}")

    if "references" in data:
        refs = data.get("references", []) or []
        lines.append("")
        lines.append(f"references: {len(refs)}")
        for ref in refs if not compact else refs[:20]:
            lines.append(f"  {ref.get('file')}:{ref.get('line')} {ref.get('text')}")
        if compact and len(refs) > 20:
            lines.append(f"  ... {len(refs) - 20} more")

    return "\n".join(lines).rstrip() + "\n"

def _print(value: Any, *, output_format: str = "json", compact: bool = False, list_output: bool = False) -> None:
    if isinstance(value, str):
        print(value, end="")
    elif output_format == "text" and list_output:
        print(format_list_text(value, compact=compact), end="")
    else:
        indent = None if compact else 2
        print(json.dumps(value, indent=indent, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="bSelective MATLAB: list/get selected .m context")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List extractable MATLAB parts")
    list_parser.add_argument("file")
    list_parser.add_argument("kind", nargs="?", default="all")
    list_parser.add_argument("target", nargs="?")
    list_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format; text is compact for agent use")
    list_parser.add_argument("--compact", action="store_true", help="Collapse verbose details; implied for text list output")

    get_parser = subparsers.add_parser("get", help="Get selected MATLAB context")
    get_parser.add_argument("file")
    get_parser.add_argument("kind")
    get_parser.add_argument("target", nargs="?")
    get_parser.add_argument("--format", choices=["json"], default="json", help="Get output is JSON unless selected source is plain text")
    get_parser.add_argument("--compact", action="store_true", help="Use compact JSON without pretty indentation")

    args = parser.parse_args(argv)
    if args.command == "list":
        _print(list_items(args.file, args.kind, args.target), output_format=args.format, compact=args.compact or args.format == "text", list_output=True)
    elif args.command == "get":
        _print(get_item(args.file, args.kind, args.target), output_format=args.format, compact=args.compact)
    else:  # pragma: no cover
        parser.error(f"Unknown command {args.command!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
