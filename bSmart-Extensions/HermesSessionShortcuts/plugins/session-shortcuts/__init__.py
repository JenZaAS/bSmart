"""SschwAdmin session-history slash shortcuts for Hermes.

Commands:
- /hist [telegram|cli|discord|all] [limit] [search terms]
- /hresume <number-or-session-id>
- /teleresume [search]

Safety default: /hist lists Telegram sessions only. Use /hist all explicitly
when you really want cross-source CLI/Telegram/Discord results.
"""

from __future__ import annotations

import json
import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SOURCES = ["telegram"]
EXCLUDED_DEFAULT: list[str] | None = None
CACHE_DIR_NAME = "session-shortcuts"
CACHE_FILE_NAME = "last-hist.json"
RECAP_USER_MESSAGES = 6
RECAP_ASSISTANT_MESSAGES = 4
RECAP_MAX_CHARS = 2600


def _home() -> Path:
    try:
        from hermes_constants import get_hermes_home
        return get_hermes_home()
    except Exception:
        import os
        return Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()


def _cache_file() -> Path:
    path = _home() / CACHE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path / CACHE_FILE_NAME


def _session_db():
    from hermes_state import SessionDB
    return SessionDB(read_only=True)


def _relative_time(ts: Any) -> str:
    if not ts:
        return "?"
    try:
        seconds = float(ts)
    except Exception:
        return "?"
    now = datetime.now().timestamp()
    delta = max(0, now - seconds)
    if delta < 60:
        return "now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    if delta < 7 * 86400:
        return f"{int(delta // 86400)}d ago"
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d")


def _trim(text: Any, width: int) -> str:
    s = str(text or "").replace("\n", " ").strip()
    if len(s) <= width:
        return s
    return s[: max(0, width - 1)] + "…"


def _parse_hist_args(raw_args: str) -> tuple[list[str] | None, list[str] | None, int, str | None, str]:
    """Return (sources, exclude_sources, limit, search, label)."""
    parts = shlex.split(raw_args or "")
    limit = 15
    sources: list[str] | None = list(DEFAULT_SOURCES)
    exclude: list[str] | None = EXCLUDED_DEFAULT
    label = "Telegram sessions"
    search_parts: list[str] = []

    for part in parts:
        low = part.lower().strip()
        if low in {"telegram", "tele", "tg"}:
            sources = ["telegram"]
            exclude = None
            label = "Telegram sessions"
        elif low in {"discord", "dc"}:
            sources = ["discord"]
            exclude = None
            label = "Discord sessions"
        elif low in {"cli", "local"}:
            sources = ["cli"]
            exclude = None
            label = "CLI sessions"
        elif low in {"all", "--all"}:
            sources = None
            exclude = None
            label = "all sessions"
        elif low in {"full", "--full"}:
            # accepted for muscle memory; list_sessions_rich already includes named sessions
            pass
        elif re.fullmatch(r"\d+", low):
            limit = max(1, min(50, int(low)))
        else:
            search_parts.append(part)

    search = " ".join(search_parts).strip() or None
    if search:
        label += f" matching '{search}'"
    return sources, exclude, limit, search, label


def _list_sessions(*, sources: list[str] | None, exclude_sources: list[str] | None, limit: int, search: str | None):
    db = _session_db()
    try:
        return db.list_sessions_rich(
            sources=sources,
            exclude_sources=exclude_sources,
            limit=limit,
            search_query=search,
            order_by_last_active=True,
            compact_rows=True,
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


def _write_cache(rows: list[dict[str, Any]], label: str) -> None:
    payload = {
        "created_at": datetime.now().timestamp(),
        "label": label,
        "rows": [
            {
                "index": i,
                "id": row.get("id"),
                "title": row.get("title"),
                "source": row.get("source"),
                "last_active": row.get("last_active"),
            }
            for i, row in enumerate(rows, 1)
        ],
    }
    _cache_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_cache() -> dict[str, Any]:
    path = _cache_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _format_rows(rows: list[dict[str, Any]], label: str) -> str:
    if not rows:
        return f"No {label} found."
    _write_cache(rows, label)
    lines = [f"Recent {label}:", "", f"{'#':>2}  {'src':<8} {'last':<10} {'title':<32}  ID"]
    lines.append(f"{'--':>2}  {'-'*8} {'-'*10} {'-'*32}  {'-'*24}")
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i:>2}  {_trim(row.get('source'), 8):<8} "
            f"{_relative_time(row.get('last_active')):<10} "
            f"{_trim(row.get('title') or '—', 32):<32}  "
            f"{row.get('id') or ''}"
        )
        preview = _trim(row.get("preview"), 72)
        if preview:
            lines.append(f"    {preview}")
    lines.extend([
        "",
        "Continue: /hresume <number>  (from this list)",
        "Latest Telegram: /teleresume",
        "Filters: /hist telegram | /hist cli | /hist discord | /hist all | /hist <search>",
        "Privacy: /hist defaults to Telegram only; /hist all is explicit.",
    ])
    return "\n".join(lines)


def _resume_in_cli(ctx: Any, session_id: str) -> bool:
    cli = getattr(getattr(ctx, "_manager", None), "_cli_ref", None)
    if cli is None:
        return False
    handler = getattr(cli, "_handle_resume_command", None)
    if handler is None:
        return False
    handler(f"/resume {session_id}")
    return True


def _resolve_target(target: str) -> str | None:
    target = (target or "").strip()
    if not target:
        return None
    if re.fullmatch(r"\d+", target):
        cache = _read_cache()
        rows = cache.get("rows") or []
        idx = int(target)
        for row in rows:
            if int(row.get("index") or -1) == idx:
                return row.get("id")
        return None
    return target


def _get_session_row(session_id: str) -> dict[str, Any]:
    db = _session_db()
    try:
        row = db.get_session(session_id) or {}
        try:
            resolved = db.resolve_resume_session_id(session_id)
            if resolved and resolved != session_id:
                row = db.get_session(resolved) or row
                row = dict(row)
                row["resolved_id"] = resolved
        except Exception:
            pass
        return row
    finally:
        try:
            db.close()
        except Exception:
            pass


def _load_messages(session_id: str, limit: int = 80) -> list[dict[str, Any]]:
    db = _session_db()
    try:
        try:
            resolved = db.resolve_resume_session_id(session_id) or session_id
        except Exception:
            resolved = session_id
        # SessionDB implementations have varied; try common APIs before falling back.
        for method_name in ("get_messages", "load_messages", "get_session_messages"):
            method = getattr(db, method_name, None)
            if callable(method):
                try:
                    messages = method(resolved)
                    if messages:
                        return list(messages)[-limit:]
                except TypeError:
                    try:
                        messages = method(resolved, limit=limit)
                        if messages:
                            return list(messages)[-limit:]
                    except Exception:
                        pass
                except Exception:
                    pass
        raw_db = getattr(db, "_db", None)
        if raw_db is not None:
            try:
                cur = raw_db.execute(
                    "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                    (resolved, limit),
                )
                rows = cur.fetchall()
                return [
                    {"role": r[0], "content": r[1]}
                    for r in reversed(rows)
                ]
            except Exception:
                pass
        return []
    finally:
        try:
            db.close()
        except Exception:
            pass


def _message_text(msg: dict[str, Any]) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


def _build_recap(session_id: str) -> str:
    row = _get_session_row(session_id)
    resolved_id = row.get("resolved_id") or row.get("id") or session_id
    title = row.get("title") or "—"
    source = row.get("source") or "?"
    messages = _load_messages(str(resolved_id))
    user_seen = 0
    assistant_seen = 0
    picked: list[str] = []
    for msg in reversed(messages):
        role = str(msg.get("role") or "").lower()
        text = _message_text(msg).strip()
        if not text:
            continue
        if role == "user":
            if user_seen >= RECAP_USER_MESSAGES:
                continue
            user_seen += 1
            picked.append(f"User: {_trim(text, 420)}")
        elif role == "assistant":
            if assistant_seen >= RECAP_ASSISTANT_MESSAGES:
                continue
            assistant_seen += 1
            picked.append(f"Assistant: {_trim(text, 520)}")
    picked.reverse()
    if not picked:
        body = "No transcript messages could be loaded for this session."
    else:
        body = "\n".join(f"- {line}" for line in picked)
    text = (
        f"Selected session: {title}\n"
        f"Source: {source}\n"
        f"Session ID: {resolved_id}\n\n"
        "Compact recap from the selected session:\n"
        f"{body}"
    )
    if len(text) > RECAP_MAX_CHARS:
        text = text[: RECAP_MAX_CHARS - 1] + "…"
    return text


def _queue_review_prompt(session_id: str) -> str:
    return (
        "/queue Make a compact review of the selected session recap above. "
        "Extract the user goal, key decisions, current state, open questions, "
        "and the next safe action. Then continue from that context. "
        f"Selected session ID: {session_id}"
    )


def _gateway_resume_message(session_id: str, prefix: str = "") -> str:
    recap = _build_recap(session_id)
    queue_prompt = _queue_review_prompt(session_id)
    return (
        f"{prefix}{recap}\n\n"
        "To truly switch this Telegram chat to that saved session, run:\n"
        f"/resume {session_id}\n\n"
        "Then, to have the active chat read the recap into working context, copy/paste:\n"
        f"{queue_prompt}\n\n"
        "Note: Hermes plugin slash commands cannot currently dispatch the built-in "
        "gateway /queue handler themselves, so this is a prepared one-line command "
        "rather than an automatic queue."
    )


def _handle_hist(raw_args: str) -> str:
    sources, exclude, limit, search, label = _parse_hist_args(raw_args)
    rows = _list_sessions(sources=sources, exclude_sources=exclude, limit=limit, search=search)
    return _format_rows(rows, label)



def _make_hresume(ctx: Any):
    def _handle_hresume(raw_args: str) -> str | None:
        target = (raw_args or "").strip()
        if not target:
            return "Usage: /hresume <number-from-/hist-or-session-id>"
        session_id = _resolve_target(target)
        if not session_id:
            return f"No cached /hist entry for {target}. Run /hist first."
        if _resume_in_cli(ctx, session_id):
            return None
        return _gateway_resume_message(session_id)
    return _handle_hresume


def _make_teleresume(ctx: Any):
    def _handle_teleresume(raw_args: str) -> str | None:
        # Optional search text is allowed: /teleresume foundry
        search = (raw_args or "").strip() or None
        rows = _list_sessions(sources=["telegram"], exclude_sources=None, limit=1, search=search)
        if not rows:
            return "No Telegram sessions found." if not search else f"No Telegram session matching '{search}' found."
        session_id = rows[0].get("id")
        if not session_id:
            return "Latest Telegram session had no session ID."
        if _resume_in_cli(ctx, session_id):
            return None
        title = rows[0].get("title") or "—"
        return _gateway_resume_message(session_id, prefix=f"Latest Telegram session: {title}\n\n")
    return _handle_teleresume


def register(ctx) -> None:
    ctx.register_command(
        "hist",
        handler=_handle_hist,
        description="List resumable Telegram sessions; use '/hist all' for all sources.",
        args_hint="[telegram|cli|discord|all] [limit|search]",
    )
    ctx.register_command(
        "hresume",
        handler=_make_hresume(ctx),
        description="Resume/list recap for a numbered session from /hist, or exact session ID.",
        args_hint="<number-or-session-id>",
    )
    ctx.register_command(
        "teleresume",
        handler=_make_teleresume(ctx),
        description="Resume/list recap for the latest Telegram session (optionally matching text).",
        args_hint="[search]",
    )
