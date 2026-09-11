#!/usr/bin/env python3
"""File-backed bQAbuild question-and-answer runtime.

The handler stores only explicit questions, answers, and generated briefs. It
never edits project source or performs Git/deployment operations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path("/workspace/bSmart/QABuild")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-._")
    if not slug:
        raise ValueError("Session ID must contain letters or numbers")
    return slug[:80]


def root_path(root: str | Path | None) -> Path:
    return Path(root) if root is not None else DEFAULT_ROOT


def session_path(root: str | Path | None, session_id: str) -> Path:
    return root_path(root) / "sessions" / f"{slugify(session_id)}.json"


def load_session(root: str | Path | None, session_id: str) -> dict[str, Any]:
    path = session_path(root, session_id)
    if not path.exists():
        raise ValueError(f"Session not found: {session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(root: str | Path | None, session: dict[str, Any]) -> Path:
    path = session_path(root, session["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def start_session(title: str, root: str | Path | None = None, session_id: str | None = None) -> dict[str, Any]:
    if not title.strip():
        raise ValueError("Title must not be empty")
    identifier = slugify(session_id or title)
    path = session_path(root, identifier)
    if path.exists():
        raise ValueError(f"Session already exists: {identifier}")
    session = {
        "id": identifier,
        "title": title.strip(),
        "created_at_utc": now_utc(),
        "updated_at_utc": now_utc(),
        "status": "draft",
        "current_question": 0,
        "questions": [],
        "answers": [],
        "brief_path": None,
    }
    save_session(root, session)
    return session


def validate_questions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("Questions must be a non-empty JSON list")
    result = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each question must be a JSON object")
        required = ["id", "title", "options", "recommendation"]
        missing = [key for key in required if not str(item.get(key, "")).strip()]
        if missing:
            raise ValueError(f"Question missing: {', '.join(missing)}")
        identifier = slugify(str(item["id"]))
        if identifier in seen:
            raise ValueError(f"Duplicate question ID: {identifier}")
        seen.add(identifier)
        options = item["options"]
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError(f"Question {identifier} must have 2–4 options")
        if any(not str(option).strip() for option in options):
            raise ValueError(f"Question {identifier} has an empty option")
        result.append({
            "id": identifier,
            "title": str(item["title"]).strip(),
            "context": str(item.get("context", "")).strip(),
            "options": [str(option).strip() for option in options],
            "recommendation": str(item["recommendation"]).strip(),
        })
    return result


def set_questions(session_id: str, questions_file: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    session = load_session(root, session_id)
    questions = validate_questions(json.loads(Path(questions_file).read_text(encoding="utf-8")))
    session["questions"] = questions
    session["current_question"] = 0
    session["answers"] = []
    session["status"] = "questioning"
    session["updated_at_utc"] = now_utc()
    save_session(root, session)
    return session


def next_question(session_id: str, root: str | Path | None = None) -> dict[str, Any] | None:
    session = load_session(root, session_id)
    index = session["current_question"]
    if index >= len(session["questions"]):
        return None
    return session["questions"][index]


def answer_question(session_id: str, answer: str, root: str | Path | None = None) -> dict[str, Any]:
    if not answer.strip():
        raise ValueError("Answer must not be empty")
    session = load_session(root, session_id)
    index = session["current_question"]
    if index >= len(session["questions"]):
        raise ValueError("All configured questions already have answers")
    question = session["questions"][index]
    session["answers"].append({
        "question_id": question["id"],
        "question": question["title"],
        "answer": answer.strip(),
        "recorded_at_utc": now_utc(),
    })
    session["current_question"] = index + 1
    session["status"] = "ready" if session["current_question"] == len(session["questions"]) else "questioning"
    session["updated_at_utc"] = now_utc()
    save_session(root, session)
    return session


def revise_answer(session_id: str, question_id: str, answer: str, root: str | Path | None = None) -> dict[str, Any]:
    if not answer.strip():
        raise ValueError("Answer must not be empty")
    session = load_session(root, session_id)
    identifier = slugify(question_id)
    question = next((item for item in session["questions"] if item["id"] == identifier), None)
    if question is None:
        raise ValueError(f"Question not found: {question_id}")
    previous = next((item for item in reversed(session["answers"]) if item["question_id"] == identifier), None)
    record = {
        "question_id": identifier,
        "question": question["title"],
        "answer": answer.strip(),
        "recorded_at_utc": now_utc(),
    }
    if previous is not None:
        record["supersedes_recorded_at_utc"] = previous["recorded_at_utc"]
    session["answers"].append(record)
    session["updated_at_utc"] = now_utc()
    save_session(root, session)
    return session


def _lines(items: list[str], fallback: str) -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {fallback}"


def build_brief(
    session_id: str,
    read_first: list[str] | None = None,
    steps: list[str] | None = None,
    validations: list[str] | None = None,
    rules: list[str] | None = None,
    root: str | Path | None = None,
) -> Path:
    session = load_session(root, session_id)
    if not session["questions"] or session["current_question"] < len(session["questions"]):
        raise ValueError("Answer every configured question before building the brief")
    read_first = read_first or []
    steps = steps or []
    validations = validations or []
    rules = rules or []
    decision_lines = []
    for answer in session["answers"]:
        decision_lines.append(f"- **{answer['question']}** — {answer['answer']}")
    content = f"""# bQAbuild brief: {session['title']}

## Read first

{_lines(read_first, 'The active project instructions and authoritative requirements.')}

## Requested change

Implement the requested change: **{session['title']}**.

## Recorded decisions

{_lines(decision_lines, 'No decisions recorded.')}

## Implementation steps

{_lines(steps, 'Define the smallest safe implementation from the recorded decisions.')}

## Validation

{_lines(validations, 'Run the relevant automated tests and one realistic manual check.')}

## Rules

{_lines(rules, 'Do not commit, publish, deploy, or make destructive changes unless separately instructed.')}

This brief is a scoped handoff, not authorization to edit, commit, publish, or deploy.
"""
    path = root_path(root) / "briefs" / f"{session['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    session["status"] = "built"
    session["brief_path"] = str(path)
    session["updated_at_utc"] = now_utc()
    save_session(root, session)
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="bQAbuild question-and-answer runtime")
    parser.add_argument("--root", default=None, help="Instance-local state root")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("title")
    start.add_argument("--session-id")
    questions = sub.add_parser("set-questions")
    questions.add_argument("session")
    questions.add_argument("questions_file")
    for name in ["next", "status"]:
        item = sub.add_parser(name)
        item.add_argument("session")
    answer = sub.add_parser("answer")
    answer.add_argument("session")
    answer.add_argument("answer")
    revise = sub.add_parser("revise")
    revise.add_argument("session")
    revise.add_argument("question_id")
    revise.add_argument("answer")
    build = sub.add_parser("build")
    build.add_argument("session")
    build.add_argument("--read-first", action="append", default=[])
    build.add_argument("--step", dest="steps", action="append", default=[])
    build.add_argument("--validate", dest="validations", action="append", default=[])
    build.add_argument("--rule", dest="rules", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "start":
            result = start_session(args.title, args.root, args.session_id)
            print(json.dumps({"id": result["id"], "status": result["status"]}))
        elif args.command == "set-questions":
            result = set_questions(args.session, args.questions_file, args.root)
            print(json.dumps({"id": result["id"], "status": result["status"], "questions": len(result["questions"])}))
        elif args.command == "next":
            print(json.dumps(next_question(args.session, args.root), ensure_ascii=False))
        elif args.command == "answer":
            result = answer_question(args.session, args.answer, args.root)
            print(json.dumps({"id": result["id"], "status": result["status"], "answered": len(result["answers"])}))
        elif args.command == "revise":
            result = revise_answer(args.session, args.question_id, args.answer, args.root)
            print(json.dumps({"id": result["id"], "status": result["status"], "answers": len(result["answers"])}))
        elif args.command == "status":
            result = load_session(args.root, args.session)
            print(json.dumps({key: result[key] for key in ["id", "title", "status", "current_question", "questions", "answers", "brief_path"]}, ensure_ascii=False))
        elif args.command == "build":
            print(str(build_brief(args.session, args.read_first, args.steps, args.validations, args.rules, args.root)))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"bQAbuild error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
