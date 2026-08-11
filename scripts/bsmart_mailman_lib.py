#!/usr/bin/env python3
"""Deterministic bSmart mail relay core (bMail / bsmart-mailman).

Stdlib-only. No AI/model calls. Designed for restrictive agent runtimes where
agents may only write to their own mail/outbox/pending and a non-agent relay
moves validated messages to recipient inboxes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

MAILBOX_DIRS = [
    "inbox/new",
    "inbox/processing",
    "inbox/read",
    "inbox/archived",
    "outbox/pending",
    "outbox/sent",
    "outbox/failed",
    "wake/pending",
    "wake/sent",
    "wake/suppressed",
    "log",
]
REQUIRED_MESSAGE_FIELDS = ["id", "from", "to", "subject", "body", "created_at"]
SUPPORTED_WAKE_TYPES = {None, "none", "file"}
SEND_POLICY_MODES = {"disabled", "restricted", "open"}


class MailmanError(Exception):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MailmanError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".json"
    for n in range(1, 10000):
        candidate = directory / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise MailmanError(f"could not allocate unique path in {directory} for {filename}")


def safe_message_filename(message_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in message_id)
    return f"{safe}.json"


def init_mailbox(mailbox: Path) -> None:
    for rel in MAILBOX_DIRS:
        (mailbox / rel).mkdir(parents=True, exist_ok=True)


def _validate_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise MailmanError(f"{field} must be a list of agent ids")
    return value


def normalize_send_policy(agent_id: str, agent: dict[str, Any]) -> dict[str, Any]:
    """Return canonical v1 send policy while accepting v0 allowed_to."""
    policy = agent.get("send_policy")
    legacy_allowed = agent.get("allowed_to")
    legacy_denied = agent.get("denied_to")
    if policy is None:
        # v0 compatibility: allowed_to meant restricted allow-list.
        policy = {
            "mode": "restricted",
            "allow_to": _validate_string_list(legacy_allowed, f"agents.{agent_id}.allowed_to"),
            "deny_to": _validate_string_list(legacy_denied, f"agents.{agent_id}.denied_to"),
        }
    elif isinstance(policy, dict):
        mode = policy.get("mode", "restricted")
        if mode not in SEND_POLICY_MODES:
            raise MailmanError(f"agents.{agent_id}.send_policy.mode must be one of {sorted(SEND_POLICY_MODES)}")
        policy = {
            "mode": mode,
            "allow_to": _validate_string_list(policy.get("allow_to", legacy_allowed or []), f"agents.{agent_id}.send_policy.allow_to"),
            "deny_to": _validate_string_list(policy.get("deny_to", legacy_denied or []), f"agents.{agent_id}.send_policy.deny_to"),
        }
    else:
        raise MailmanError(f"agents.{agent_id}.send_policy must be an object when present")
    agent["send_policy"] = policy
    agent.setdefault("allowed_to", policy["allow_to"])
    return policy


def normalize_registry(path: Path) -> dict[str, Any]:
    registry = load_json(path)
    if not isinstance(registry, dict):
        raise MailmanError("registry must be a JSON object")
    agents = registry.get("agents")
    if not isinstance(agents, dict):
        raise MailmanError("registry requires object field agents")
    routes = registry.setdefault("routes", {})
    if not isinstance(routes, dict):
        raise MailmanError("registry routes must be an object")
    routes.setdefault("default_policy", "deny")
    if routes["default_policy"] != "deny":
        raise MailmanError("mailman supports only routes.default_policy = deny")
    for agent_id, agent in agents.items():
        if not isinstance(agent, dict):
            raise MailmanError(f"agents.{agent_id} must be an object")
        if not agent.get("mailbox"):
            raise MailmanError(f"agents.{agent_id}.mailbox is required")
        for optional_text in ("display_name", "role", "description"):
            if optional_text in agent and not isinstance(agent[optional_text], str):
                raise MailmanError(f"agents.{agent_id}.{optional_text} must be a string when present")
        normalize_send_policy(agent_id, agent)
        wake = agent.get("wake", {})
        if wake is None:
            wake_type = None
        elif isinstance(wake, dict):
            wake_type = wake.get("type")
        else:
            raise MailmanError(f"agents.{agent_id}.wake must be an object when present")
        if wake_type not in SUPPORTED_WAKE_TYPES:
            raise MailmanError(f"agents.{agent_id}.wake.type={wake_type!r} is not supported")
    return registry


def agent_mailbox(registry: dict[str, Any], agent_id: str) -> Path:
    try:
        return Path(registry["agents"][agent_id]["mailbox"]).expanduser()
    except KeyError as exc:
        raise MailmanError(f"unknown agent: {agent_id}") from exc


def validate_message(message: dict[str, Any], source_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_MESSAGE_FIELDS:
        if field not in message or message[field] in (None, ""):
            errors.append(f"missing required field: {field}")
    for field in ["id", "from", "to", "subject", "body", "created_at"]:
        if field in message and not isinstance(message[field], str):
            errors.append(f"field must be string: {field}")
    if source_path and "id" in message and source_path.name != safe_message_filename(str(message["id"])):
        # Advisory only would hide accidental mismatches; fail closed for v0.
        errors.append("message id does not match pending filename")
    return errors


def is_allowed(registry: dict[str, Any], sender: str, recipient: str) -> bool:
    """Evaluate v1 send_policy. disabled > deny_to > restricted allow_to > open."""
    agent = registry["agents"].get(sender, {})
    policy = agent.get("send_policy") or normalize_send_policy(sender, agent)
    mode = policy.get("mode", "restricted")
    allow_to = policy.get("allow_to", [])
    deny_to = policy.get("deny_to", [])
    if mode == "disabled":
        return False
    if "*" in deny_to or recipient in deny_to:
        return False
    if mode == "restricted":
        return "*" in allow_to or recipient in allow_to
    if mode == "open":
        return True
    return False


def route_denial_reason(registry: dict[str, Any], sender: str, recipient: str) -> str:
    policy = registry["agents"].get(sender, {}).get("send_policy", {})
    mode = policy.get("mode", "restricted")
    if mode == "disabled":
        return f"route denied by send_policy disabled: {sender} -> {recipient}"
    if "*" in policy.get("deny_to", []) or recipient in policy.get("deny_to", []):
        return f"route denied by send_policy deny_to: {sender} -> {recipient}"
    return f"route denied by send_policy restricted allow_to: {sender} -> {recipient}"


def write_wake_marker(recipient_box: Path, message: dict[str, Any], delivered_path: Path, sender_box: Path, registry: dict[str, Any]) -> Path | None:
    recipient = str(message.get("to", ""))
    wake = registry.get("agents", {}).get(recipient, {}).get("wake", {})
    wake_type = wake.get("type") if isinstance(wake, dict) else None
    if wake_type != "file":
        return None
    marker = {
        "id": f"wake-{message.get('id')}",
        "type": "mail_arrived",
        "message_id": message.get("id"),
        "from": message.get("from"),
        "to": message.get("to"),
        "subject": message.get("subject"),
        "created_at": utc_now(),
        "delivered_path": str(delivered_path),
        "handling_hint": wake.get("handling_hint", "triage_then_delegate"),
    }
    path = unique_path(recipient_box / "wake" / "pending", safe_message_filename(str(marker["id"])))
    write_json(path, marker)
    entry = delivery_log_entry("wake_queued", message, delivered_path, "wake marker queued", path)
    log_for_mailbox(recipient_box, entry)
    log_for_mailbox(sender_box, entry)
    return path


def delivery_log_entry(status: str, message: dict[str, Any], pending_path: Path, detail: str, delivered_path: Path | None = None) -> dict[str, Any]:
    entry = {
        "timestamp": utc_now(),
        "status": status,
        "id": message.get("id"),
        "from": message.get("from"),
        "to": message.get("to"),
        "subject": message.get("subject"),
        "pending_path": str(pending_path),
        "detail": detail,
    }
    if delivered_path:
        entry["delivered_path"] = str(delivered_path)
    return entry


def move_with_annotation(src: Path, dest_dir: Path, message: dict[str, Any] | None = None, reason: str | None = None) -> Path:
    dest = unique_path(dest_dir, src.name)
    if message is not None:
        annotated = dict(message)
        if reason:
            annotated["delivery_error"] = reason
        write_json(dest, annotated)
        src.unlink()
    else:
        shutil.move(str(src), str(dest))
    return dest


def log_for_mailbox(mailbox: Path, entry: dict[str, Any]) -> None:
    append_jsonl(mailbox / "log" / "deliveries.jsonl", entry)


def fail_pending(registry: dict[str, Any], pending_path: Path, message: dict[str, Any], reason: str) -> Path:
    sender_value = message.get("from") if isinstance(message, dict) else None
    sender = sender_value if isinstance(sender_value, str) else None
    if sender is not None and sender in registry.get("agents", {}):
        sender_box = agent_mailbox(registry, sender)
        failed_path = move_with_annotation(pending_path, sender_box / "outbox" / "failed", message, reason)
        entry = delivery_log_entry("failed", message, pending_path, reason)
        entry["failed_path"] = str(failed_path)
        log_for_mailbox(sender_box, entry)
        return failed_path
    # If sender is not known, keep failure next to the source mailbox owner based on path.
    failed_path = move_with_annotation(pending_path, pending_path.parents[1] / "failed", message, reason)
    return failed_path


def deliver_one(registry: dict[str, Any], sender_id: str, pending_path: Path) -> tuple[str, str]:
    try:
        message = load_json(pending_path)
    except MailmanError as exc:
        bad = {"id": pending_path.stem, "from": sender_id, "to": "", "subject": "", "body": "", "created_at": utc_now()}
        fail_pending(registry, pending_path, bad, str(exc))
        return "failed", str(exc)
    if not isinstance(message, dict):
        reason = "message must be a JSON object"
        fail_pending(registry, pending_path, {"id": pending_path.stem, "from": sender_id, "to": "", "subject": "", "body": "", "created_at": utc_now()}, reason)
        return "failed", reason

    errors = validate_message(message, pending_path)
    if message.get("from") != sender_id:
        errors.append(f"message from={message.get('from')!r} does not match sender mailbox {sender_id!r}")
    recipient_value = message.get("to")
    recipient = recipient_value if isinstance(recipient_value, str) else None
    if recipient not in registry.get("agents", {}):
        errors.append(f"unknown recipient: {recipient}")
    if errors:
        reason = "; ".join(errors)
        fail_pending(registry, pending_path, message, reason)
        return "failed", reason
    assert recipient is not None
    if not is_allowed(registry, sender_id, recipient):
        reason = route_denial_reason(registry, sender_id, recipient)
        fail_pending(registry, pending_path, message, reason)
        return "failed", reason

    sender_box = agent_mailbox(registry, sender_id)
    recipient_box = agent_mailbox(registry, recipient)
    init_mailbox(recipient_box)
    delivered_path = unique_path(recipient_box / "inbox" / "new", pending_path.name)
    shutil.copy2(pending_path, delivered_path)
    sent_path = move_with_annotation(pending_path, sender_box / "outbox" / "sent")
    entry = delivery_log_entry("delivered", message, pending_path, "delivered", delivered_path)
    entry["sent_path"] = str(sent_path)
    log_for_mailbox(sender_box, entry)
    log_for_mailbox(recipient_box, entry)
    wake_path = write_wake_marker(recipient_box, message, delivered_path, sender_box, registry)
    if wake_path:
        entry["wake_path"] = str(wake_path)
    return "delivered", str(delivered_path)


def deliver(registry_path: Path) -> dict[str, int]:
    registry = normalize_registry(registry_path)
    counts = {"delivered": 0, "failed": 0, "pending": 0}
    for sender_id in sorted(registry["agents"]):
        mailbox = agent_mailbox(registry, sender_id)
        init_mailbox(mailbox)
        pending_dir = mailbox / "outbox" / "pending"
        for pending_path in sorted(pending_dir.glob("*.json")):
            counts["pending"] += 1
            status, detail = deliver_one(registry, sender_id, pending_path)
            counts[status] += 1
            print(f"{status}: {sender_id}: {pending_path.name}: {detail}")
    print(json.dumps(counts, sort_keys=True))
    return counts


def build_message(sender: str, recipient: str, subject: str, body: str, intent: str | None = None, goal: str | None = None, handled_by: str | None = None) -> dict[str, str]:
    created = utc_now()
    msg_id = f"{created.replace(':', '').replace('-', '').replace('Z', 'Z')}-{sender}-to-{recipient}-{uuid.uuid4().hex[:12]}"
    message = {"id": msg_id, "from": sender, "to": recipient, "subject": subject, "body": body, "created_at": created}
    if intent:
        message["intent"] = intent
    if goal:
        message["goal"] = goal
    if handled_by:
        message["handled_by"] = handled_by
    return message


def send_message(registry_path: Path, sender: str, recipient: str, subject: str, body: str, intent: str | None = None, goal: str | None = None, handled_by: str | None = None) -> Path:
    registry = normalize_registry(registry_path)
    mailbox = agent_mailbox(registry, sender)
    init_mailbox(mailbox)
    # Recipient is checked at send time for operator feedback, but delivery still enforces policy.
    if recipient not in registry.get("agents", {}):
        raise MailmanError(f"unknown recipient: {recipient}")
    message = build_message(sender, recipient, subject, body, intent=intent, goal=goal, handled_by=handled_by)
    path = unique_path(mailbox / "outbox" / "pending", safe_message_filename(message["id"]))
    write_json(path, message)
    return path


def inbox(mailbox: Path) -> list[dict[str, str]]:
    init_mailbox(mailbox)
    rows = []
    for path in sorted((mailbox / "inbox" / "new").glob("*.json")):
        try:
            msg = load_json(path)
            rows.append({
                "id": str(msg.get("id", path.stem)),
                "from": str(msg.get("from", "")),
                "subject": str(msg.get("subject", "")),
                "created_at": str(msg.get("created_at", "")),
                "path": str(path),
            })
        except MailmanError:
            rows.append({"id": path.stem, "from": "", "subject": "<invalid JSON>", "created_at": "", "path": str(path)})
    return rows


def wake_pending(mailbox: Path) -> list[dict[str, str]]:
    init_mailbox(mailbox)
    rows = []
    for path in sorted((mailbox / "wake" / "pending").glob("*.json")):
        try:
            marker = load_json(path)
            rows.append({
                "id": str(marker.get("id", path.stem)),
                "type": str(marker.get("type", "")),
                "message_id": str(marker.get("message_id", "")),
                "from": str(marker.get("from", "")),
                "subject": str(marker.get("subject", "")),
                "created_at": str(marker.get("created_at", "")),
                "path": str(path),
            })
        except MailmanError:
            rows.append({"id": path.stem, "type": "<invalid JSON>", "message_id": "", "from": "", "subject": "", "created_at": "", "path": str(path)})
    return rows


def check_mailbox(mailbox: Path) -> dict[str, Any]:
    """Fast recipient-side check for natural prompts like 'check your mail'."""
    init_mailbox(mailbox)
    new_messages = inbox(mailbox)
    wake_markers = wake_pending(mailbox)
    return {
        "mailbox": str(mailbox),
        "new": len(new_messages),
        "wake_pending": len(wake_markers),
        "messages": new_messages,
        "wake": wake_markers,
        "hint": "Use `bMail read --mailbox MAILBOX --id MESSAGE_ID` to read a message.",
    }


def read_message(mailbox: Path, message_id: str) -> dict[str, Any]:
    init_mailbox(mailbox)
    filename = safe_message_filename(message_id)
    candidates = [mailbox / "inbox" / "new" / filename, mailbox / "inbox" / "read" / filename, mailbox / "inbox" / "archived" / filename]
    for path in candidates:
        if path.exists():
            message = load_json(path)
            if path.parent.name == "new":
                dest = unique_path(mailbox / "inbox" / "read", path.name)
                shutil.move(str(path), str(dest))
                message["read_path"] = str(dest)
            else:
                message["read_path"] = str(path)
            return message
    raise MailmanError(f"message not found in mailbox inbox: {message_id}")


def move_wake_marker(mailbox: Path, wake_id: str, dest_name: str) -> Path:
    init_mailbox(mailbox)
    filename = safe_message_filename(wake_id)
    source = mailbox / "wake" / "pending" / filename
    if not source.exists():
        raise MailmanError(f"wake marker not found: {wake_id}")
    dest = unique_path(mailbox / "wake" / dest_name, filename)
    shutil.move(str(source), str(dest))
    return dest


def tickle_summary(mailbox: Path) -> dict[str, Any]:
    """Stable machine-readable summary for cron monitor-mode.

    Intentionally omits current timestamps so unchanged pending wake markers
    hash to the same output and Hermes monitor jobs stay silent.
    """
    init_mailbox(mailbox)
    wake = wake_pending(mailbox)
    messages = inbox(mailbox)
    by_id = {row["id"]: row for row in messages}
    items = []
    for marker in wake:
        message_id = marker.get("message_id", "")
        message_row = by_id.get(message_id)
        if not message_row:
            # A pending wake whose message is no longer in inbox/new is stale
            # for wake purposes. `bMail check` still exposes it for cleanup,
            # but the cron tickle should not re-wake the agent forever.
            continue
        item = {
            "wake_id": marker.get("id", ""),
            "message_id": message_id,
            "from": marker.get("from", ""),
            "subject": marker.get("subject", ""),
            "message_path": message_row.get("path", ""),
            "wake_path": marker.get("path", ""),
        }
        items.append(item)
    return {
        "mailbox": str(mailbox),
        "pending_wake": len(items),
        "new_messages": len(messages),
        "items": items,
        "command_hint": "python3 /workspace/bSmart-System/scripts/bMail read --mailbox /mail --id <message_id>",
    }


def cmd_mailman(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bsmart-mailman", description="bSmart deterministic non-agent mail relay")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init-agent", help="create mailbox folder layout")
    p_init.add_argument("--mailbox", required=True)
    p_deliver = sub.add_parser("deliver", help="deliver pending messages once")
    p_deliver.add_argument("--registry", required=True)
    p_watch = sub.add_parser("watch", help="deliver pending messages repeatedly")
    p_watch.add_argument("--registry", required=True)
    p_watch.add_argument("--interval", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "init-agent":
            init_mailbox(Path(args.mailbox).expanduser())
            print(f"initialized: {Path(args.mailbox).expanduser()}")
            return 0
        if args.command == "deliver":
            counts = deliver(Path(args.registry).expanduser())
            return 1 if counts["failed"] else 0
        if args.command == "watch":
            while True:
                deliver(Path(args.registry).expanduser())
                time.sleep(args.interval)
    except KeyboardInterrupt:
        return 130
    except MailmanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_bmail(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bMail", description="bSmart mailbox CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    p_send = sub.add_parser("send", help="write an outgoing message to sender outbox/pending")
    p_send.add_argument("--registry", required=True)
    p_send.add_argument("--from", dest="sender", required=True)
    p_send.add_argument("--to", dest="recipient", required=True)
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--intent", help="explicit sender intent for receiver/subagent triage")
    p_send.add_argument("--goal", help="explicit completion goal for receiver/subagent triage")
    p_send.add_argument("--handled-by", help="trace subagent/worker id when parent agent sends a delegated result")
    body = p_send.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    p_inbox = sub.add_parser("inbox", help="list inbox/new messages")
    p_inbox.add_argument("--mailbox", required=True)
    p_check = sub.add_parser("check", help="quickly summarize inbox/new and wake/pending for prompts like 'check your mail'")
    p_check.add_argument("--mailbox", default=os.environ.get("BSMART_MAIL_ROOT", "/mail"))
    p_tickle = sub.add_parser("tickle", help="stable wake-marker summary for Hermes cron monitor-mode; silent when no pending wake markers")
    p_tickle.add_argument("--mailbox", default=os.environ.get("BSMART_MAIL_ROOT", "/mail"))
    p_ack_wake = sub.add_parser("ack-wake", help="move one wake marker from wake/pending to wake/sent after the related mail is handled")
    p_ack_wake.add_argument("--mailbox", default=os.environ.get("BSMART_MAIL_ROOT", "/mail"))
    p_ack_wake.add_argument("--id", required=True, help="wake marker id, e.g. wake-<message-id>")
    p_read = sub.add_parser("read", help="show a message and move it from inbox/new to inbox/read")
    p_read.add_argument("--mailbox", required=True)
    p_read.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "send":
            if args.body_file:
                body_text = Path(args.body_file).expanduser().read_text(encoding="utf-8")
            else:
                body_text = args.body
            path = send_message(Path(args.registry).expanduser(), args.sender, args.recipient, args.subject, body_text, intent=args.intent, goal=args.goal, handled_by=args.handled_by)
            print(f"queued: {path}")
            return 0
        if args.command == "inbox":
            rows = inbox(Path(args.mailbox).expanduser())
            for row in rows:
                print(json.dumps(row, ensure_ascii=False, sort_keys=True))
            print(json.dumps({"new": len(rows)}, sort_keys=True))
            return 0
        if args.command == "check":
            summary = check_mailbox(Path(args.mailbox).expanduser())
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            return 1 if summary["new"] or summary["wake_pending"] else 0
        if args.command == "tickle":
            summary = tickle_summary(Path(args.mailbox).expanduser())
            if summary["pending_wake"]:
                print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
                return 1
            return 0
        if args.command == "ack-wake":
            dest = move_wake_marker(Path(args.mailbox).expanduser(), args.id, "sent")
            print(f"acknowledged: {dest}")
            return 0
        if args.command == "read":
            message = read_message(Path(args.mailbox).expanduser(), args.id)
            print(json.dumps(message, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
    except MailmanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
