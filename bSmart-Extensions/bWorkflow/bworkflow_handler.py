#!/usr/bin/env python3
"""bWorkflow Markdown runtime helpers.

Authoritative workflow data is Markdown under /workspace/bSmart/Workflows.
This module deliberately uses only the Python standard library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import json
import sys

DEFAULT_WORKFLOW_ROOT = Path("/workspace/bSmart/Workflows")


def _as_root(root: str | Path | None) -> Path:
    return Path(root) if root is not None else DEFAULT_WORKFLOW_ROOT


def _parse_list_blocks(text: str) -> list[dict[str, Any]]:
    """Parse simple catalogue list blocks using `- Key: value` + indented fields."""
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ID:"):
            if current:
                items.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue
        if current is not None and raw_line.startswith("  ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            normalized_key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if normalized_key == "keywords":
                current[normalized_key] = [part.strip() for part in value.split(",") if part.strip()]
            else:
                current[normalized_key] = value

    if current:
        items.append(current)
    return items


def _parse_workflow_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    parts = text.split("\n## WORKFLOW ")
    for part in parts[1:]:
        block = "## WORKFLOW " + part
        header_line = block.splitlines()[0]
        workflow_id = header_line.replace("## WORKFLOW", "", 1).strip()
        metadata_text = block.split("\n### ", 1)[0]
        entry: dict[str, Any] = {"id": workflow_id, "type": "workflow"}
        lines = metadata_text.splitlines()[1:]
        index = 0
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                index += 1
                continue
            if line.startswith("Associated files:"):
                files: list[str] = []
                index += 1
                while index < len(lines) and lines[index].startswith("  - "):
                    files.append(lines[index].split("- ", 1)[1].strip())
                    index += 1
                entry["associated_files"] = files
                continue
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                normalized_key = key.strip().lower().replace(" ", "_")
                if normalized_key != "id":
                    entry[normalized_key] = value.strip()
            index += 1
        entry.setdefault("associated_files", [])
        entries.append(entry)
    return entries


def _topic_file_for_scope(root_path: Path, scope: str) -> Path:
    parts = scope.split(".")
    if len(parts) != 2:
        raise ValueError(f"Expected topic scope '<domain>.<topic>', got {scope!r}")
    domain, topic = parts
    return root_path / domain / f"{topic}.md"


def list_workflows(scope: str | None = None, filter: str | None = None, root: str | Path | None = None) -> list[dict[str, Any]]:
    """List workflow catalogue entries at the requested hierarchy level."""
    root_path = _as_root(root)
    if scope is None:
        index_path = root_path / "index.md"
        text = index_path.read_text(encoding="utf-8")
        entries = _parse_list_blocks(text)
        entry_type = "domain"
    elif "." not in scope:
        index_path = root_path / scope / "index.md"
        text = index_path.read_text(encoding="utf-8")
        entries = _parse_list_blocks(text)
        entry_type = "topic"
    else:
        topic_path = _topic_file_for_scope(root_path, scope)
        text = topic_path.read_text(encoding="utf-8")
        return _parse_workflow_entries(text)

    for entry in entries:
        entry.setdefault("keywords", [])
        entry["type"] = entry_type
    if filter is not None:
        narrowed = []
        for entry in entries:
            blob = " ".join(str(entry.get(key, "")) for key in ["id", "title", "summary", "status"])
            blob += " " + " ".join(entry.get("keywords", []))
            blob += " " + " ".join(entry.get("associated_files", []))
            if filter.lower() in blob.lower():
                narrowed.append(entry)
        entries = narrowed
    return entries


def _split_entry_blocks(text: str) -> tuple[str, list[str]]:
    marker = "\n## WORKFLOW "
    first = text.find(marker)
    if first == -1:
        return text, []
    prefix = text[: first + 1]
    raw_blocks = text[first + 1 :].split(marker.strip())
    blocks = [(marker.strip() + raw).rstrip() + "\n" for raw in raw_blocks if raw]
    return prefix, blocks


def _entry_id_from_block(block: str) -> str:
    return block.splitlines()[0].replace("## WORKFLOW", "", 1).strip()


def _domain_topic_from_id(workflow_id: str) -> tuple[str, str]:
    parts = workflow_id.split(".")
    if len(parts) < 2:
        raise ValueError(f"Expected workflow id with at least domain.topic, got {workflow_id!r}")
    return parts[0], parts[1]


def _read_topic_text(workflow_id: str, root: str | Path | None = None) -> tuple[Path, str]:
    root_path = _as_root(root)
    topic_path = _topic_file_for_scope(root_path, ".".join(_domain_topic_from_id(workflow_id)))
    return topic_path, topic_path.read_text(encoding="utf-8")


def _get_entry_block(workflow_id: str, root: str | Path | None = None) -> str:
    _topic_path, text = _read_topic_text(workflow_id, root=root)
    _prefix, blocks = _split_entry_blocks(text)
    for block in blocks:
        if _entry_id_from_block(block) == workflow_id:
            return block.rstrip() + "\n"
    raise KeyError(f"Workflow not found: {workflow_id}")


def _write_replaced_entry(workflow_id: str, new_block: str, root: str | Path | None = None) -> None:
    topic_path, text = _read_topic_text(workflow_id, root=root)
    prefix, blocks = _split_entry_blocks(text)
    output_blocks = []
    replaced = False
    for block in blocks:
        if _entry_id_from_block(block) == workflow_id:
            output_blocks.append(new_block.rstrip() + "\n")
            replaced = True
        else:
            output_blocks.append(block.rstrip() + "\n")
    if not replaced:
        raise KeyError(f"Workflow not found: {workflow_id}")
    topic_path.write_text(prefix.rstrip() + "\n\n" + "\n".join(output_blocks).rstrip() + "\n", encoding="utf-8")


def get_workflow(workflow_id: str, root: str | Path | None = None) -> str:
    """Return a topic file for domain.topic ids, or one exact workflow entry."""
    if len(workflow_id.split(".")) == 2:
        topic_path = _topic_file_for_scope(_as_root(root), workflow_id)
        return topic_path.read_text(encoding="utf-8")
    return _get_entry_block(workflow_id, root=root)


def get_workflow_section(workflow_id: str, section: str, root: str | Path | None = None) -> str:
    """Return only one ### section body from a workflow entry."""
    block = _get_entry_block(workflow_id, root=root)
    wanted = section.strip().lower()
    parts = block.split("\n### ")
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        if heading.strip().lower() == wanted:
            return body.split("\n### ", 1)[0].rstrip() + "\n"
    raise KeyError(f"Section not found: {section}")


def _all_topics(root_path: Path) -> list[dict[str, Any]]:
    topics = []
    for domain in list_workflows(root=root_path):
        try:
            topics.extend(list_workflows(domain["id"], root=root_path))
        except FileNotFoundError:
            continue
    return topics


def _matches_text(haystack: str, needle: str | None) -> bool:
    return needle is None or needle.lower() in haystack.lower()


def search_workflows(
    query: str | None = None,
    scope: str | list[str] | None = None,
    root: str | Path | None = None,
    keyword: str | None = None,
    title: str | None = None,
    associated_file: str | None = None,
    workflow_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search catalogue metadata and workflow entry metadata directly from Markdown."""
    root_path = _as_root(root)
    scopes = [scope] if isinstance(scope, str) else scope
    results = []
    topics = _all_topics(root_path)
    if scopes:
        topics = [topic for topic in topics if any(topic["id"].startswith(item) for item in scopes)]

    for topic in topics:
        topic_blob = " ".join(str(topic.get(key, "")) for key in ["id", "title", "summary"])
        topic_blob += " " + " ".join(topic.get("keywords", []))
        if associated_file is None and workflow_id is None and _matches_text(topic_blob, query) and _matches_text(topic_blob, keyword) and _matches_text(topic.get("title", ""), title):
            results.append(topic)

        for entry in list_workflows(topic["id"], root=root_path):
            if workflow_id and workflow_id not in entry["id"]:
                continue
            if associated_file and not any(associated_file.lower() in item.lower() for item in entry.get("associated_files", [])):
                continue
            entry_blob = " ".join(str(entry.get(key, "")) for key in ["id", "title", "status"])
            entry_blob += " " + " ".join(entry.get("associated_files", []))
            if not _matches_text(entry_blob, query):
                continue
            if not _matches_text(entry.get("title", ""), title):
                continue
            if not _matches_text(entry_blob, keyword):
                continue
            if associated_file or workflow_id or query or title or keyword:
                results.append(entry)
    return results


def _replace_metadata_line(block: str, label: str, value: str) -> str:
    lines = block.splitlines()
    prefix = f"{label}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{label}: {value}"
            return "\n".join(lines) + "\n"
    lines.insert(1, f"{label}: {value}")
    return "\n".join(lines) + "\n"


def _metadata_dict(block: str) -> dict[str, Any]:
    return _parse_workflow_entries("\n" + block)[0]


def log_workflow_run(
    workflow_id: str,
    result: str,
    root: str | Path | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Update compact success/failure counters for one workflow run."""
    if result not in {"success", "failure"}:
        raise ValueError("result must be 'success' or 'failure'")
    date = date or "unknown"
    block = _get_entry_block(workflow_id, root=root)
    meta = _metadata_dict(block)
    successful = int(meta.get("successful_runs", "0"))
    failed = int(meta.get("failed_runs", "0"))
    if result == "success":
        successful += 1
        block = _replace_metadata_line(block, "Last successful use", date)
    else:
        failed += 1
        block = _replace_metadata_line(block, "Last failed use", date)
    total = successful + failed
    block = _replace_metadata_line(block, "Successful runs", str(successful))
    block = _replace_metadata_line(block, "Failed runs", str(failed))
    block = _replace_metadata_line(block, "Total runs", str(total))
    _write_replaced_entry(workflow_id, block, root=root)
    return _metadata_dict(block)


def reset_workflow_counters(
    workflow_id: str,
    reason: str,
    root: str | Path | None = None,
    date: str | None = None,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Reset current status-period counters and append lifecycle history."""
    date = date or "unknown"
    git_commit = git_commit or "unknown"
    block = _get_entry_block(workflow_id, root=root)
    for label, value in [
        ("Successful runs", "0"),
        ("Failed runs", "0"),
        ("Total runs", "0"),
        ("Last successful use", "None"),
        ("Last failed use", "None"),
    ]:
        block = _replace_metadata_line(block, label, value)
    history = (
        f"\n- {date} — counters reset\n"
        f"  - Reason: {reason}\n"
        f"  - Git commit: {git_commit}\n"
    )
    if "\n### Lifecycle history\n" in block:
        block = block.rstrip() + history
    else:
        block = block.rstrip() + "\n\n### Lifecycle history\n" + history
    _write_replaced_entry(workflow_id, block, root=root)
    return _metadata_dict(block)


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="bWorkflow Markdown runtime")
    parser.add_argument("--root", default=str(DEFAULT_WORKFLOW_ROOT), help="Workflow content root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List domains, topics, or workflow entries")
    list_parser.add_argument("scope", nargs="?")
    list_parser.add_argument("--filter")

    search_parser = subparsers.add_parser("search", help="Search workflow metadata")
    search_parser.add_argument("query", nargs="?")
    search_parser.add_argument("--scope", action="append")
    search_parser.add_argument("--keyword")
    search_parser.add_argument("--title")
    search_parser.add_argument("--associated-file")
    search_parser.add_argument("--workflow-id")

    get_parser = subparsers.add_parser("get", help="Get a topic file or workflow entry")
    get_parser.add_argument("workflow_id")

    section_parser = subparsers.add_parser("section", help="Get one workflow entry section")
    section_parser.add_argument("workflow_id")
    section_parser.add_argument("section")

    log_parser = subparsers.add_parser("log-run", help="Update workflow run counters")
    log_parser.add_argument("workflow_id")
    log_parser.add_argument("result", choices=["success", "failure"])
    log_parser.add_argument("--date")

    reset_parser = subparsers.add_parser("reset-counters", help="Reset workflow run counters")
    reset_parser.add_argument("workflow_id")
    reset_parser.add_argument("--reason", required=True)
    reset_parser.add_argument("--date")
    reset_parser.add_argument("--git-commit")

    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "list":
        _print_json(list_workflows(args.scope, filter=args.filter, root=root))
    elif args.command == "search":
        _print_json(
            search_workflows(
                args.query,
                scope=args.scope,
                root=root,
                keyword=args.keyword,
                title=args.title,
                associated_file=args.associated_file,
                workflow_id=args.workflow_id,
            )
        )
    elif args.command == "get":
        print(get_workflow(args.workflow_id, root=root), end="")
    elif args.command == "section":
        print(get_workflow_section(args.workflow_id, args.section, root=root), end="")
    elif args.command == "log-run":
        _print_json(log_workflow_run(args.workflow_id, args.result, root=root, date=args.date))
    elif args.command == "reset-counters":
        _print_json(
            reset_workflow_counters(
                args.workflow_id,
                reason=args.reason,
                root=root,
                date=args.date,
                git_commit=args.git_commit,
            )
        )
    else:  # pragma: no cover - argparse prevents this
        parser.error(f"Unknown command {args.command!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
