"""Small, local-only bPrivate runtime and stdlib HTTP gateway prototype."""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable


class PrivacyError(Exception): pass
class PathPolicyError(PrivacyError): pass
class OutboundLeakError(PrivacyError): pass
class UnknownPlaceholderError(PrivacyError): pass
class UnsupportedFileError(PrivacyError): pass

_PLACEHOLDER = re.compile(r"\{\{BPV_(\d{4})\}\}")
_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf", ".zip", ".gz", ".mp3", ".mp4"}


class PrivacyRuntime:
    """Encode configured values locally and decode known placeholders locally."""
    def __init__(self, mode: str = "off", protected_values: Iterable[str] = (), protected_paths: Iterable[str] = ()):
        if mode not in {"off", "on"}: raise ValueError("mode must be 'off' or 'on'")
        self.mode = mode
        self.protected_values = tuple(dict.fromkeys(str(v) for v in protected_values if str(v)))
        self.protected_paths = tuple(str(Path(p).resolve()) for p in protected_paths)
        self._value_to_placeholder: dict[str, str] = {}
        self._placeholder_to_value: dict[str, str] = {}

    @property
    def mapping(self) -> dict[str, str]: return dict(self._value_to_placeholder)
    def status(self) -> dict[str, Any]:
        return {"mode": self.mode, "mapping_entries": len(self._value_to_placeholder), "configured_values": len(self.protected_values), "protected_paths": list(self.protected_paths), "local_decode_only": True}
    def check_input_path(self, path: str | Path) -> None:
        candidate = Path(path).resolve()
        for protected in self.protected_paths:
            root = Path(protected)
            if candidate == root or root in candidate.parents: raise PathPolicyError(f"protected path cannot be online-model input: {candidate}")
    def _placeholder_for(self, value: str) -> str:
        if value in self._value_to_placeholder: return self._value_to_placeholder[value]
        placeholder = f"{{{{BPV_{len(self._value_to_placeholder) + 1:04d}}}}}"
        self._value_to_placeholder[value] = placeholder; self._placeholder_to_value[placeholder] = value
        return placeholder
    def encode(self, text: str) -> str:
        if self.mode == "off": return text
        result = text
        for value in sorted(self.protected_values, key=len, reverse=True): result = result.replace(value, self._placeholder_for(value))
        return result
    def decode(self, text: str) -> str:
        if self.mode == "off": return text
        unknown = [m.group(0) for m in _PLACEHOLDER.finditer(text) if m.group(0) not in self._placeholder_to_value]
        if unknown: raise UnknownPlaceholderError(f"unknown placeholder: {unknown[0]}")
        return _PLACEHOLDER.sub(lambda m: self._placeholder_to_value[m.group(0)], text)
    def validate_outbound(self, payload: Any) -> bool:
        if self.mode == "off": return True
        def has_mapping_content(value: Any) -> bool:
            if isinstance(value, dict):
                return any(key in {"mapping", "session_mapping", "_value_to_placeholder"} for key in value) or any(has_mapping_content(item) for item in value.values())
            if isinstance(value, list): return any(has_mapping_content(item) for item in value)
            return False
        if has_mapping_content(payload): raise OutboundLeakError("mapping content cannot be sent outbound")
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True) if not isinstance(payload, str) else payload
        if any(value in serialized for value in self._value_to_placeholder): raise OutboundLeakError("raw protected value cannot be sent outbound")
        return True
    def stage_text(self, path: str | Path) -> str:
        p = Path(path)
        if p.suffix.lower() in _BINARY_SUFFIXES: raise UnsupportedFileError("binary/image staging is not supported")
        data = p.read_bytes()
        if b"\x00" in data: raise UnsupportedFileError("binary content is not supported")
        try: return data.decode("utf-8")
        except UnicodeDecodeError as exc: raise UnsupportedFileError("only UTF-8 text is supported") from exc


def _map_json(value: Any, transform) -> Any:
    if isinstance(value, str): return transform(value)
    if isinstance(value, list): return [_map_json(item, transform) for item in value]
    if isinstance(value, dict): return {key: _map_json(item, transform) for key, item in value.items()}
    return value


class PrivacyGateway:
    """Non-streaming OpenAI chat-completions-compatible local gateway."""
    def __init__(self, upstream_url: str, mode: str = "off", protected_values: Iterable[str] = (), protected_paths: Iterable[str] = ()):
        self.upstream_url = upstream_url
        self.runtime = PrivacyRuntime(mode, protected_values, protected_paths)

    def _check_tool_paths(self, value: Any, in_tool_args: bool = False) -> None:
        if isinstance(value, str):
            if in_tool_args and (value.startswith("/") or "/" in value): self.runtime.check_input_path(value)
        elif isinstance(value, list):
            for item in value: self._check_tool_paths(item, in_tool_args)
        elif isinstance(value, dict):
            for key, item in value.items(): self._check_tool_paths(item, in_tool_args or key in {"arguments", "parameters", "tool_calls", "tools"})

    def handle(self, raw: bytes) -> tuple[int, bytes, str]:
        if self.runtime.mode == "off":
            try: payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError): payload = None
            if isinstance(payload, dict) and payload.get("stream") is True: return 400, b'{"error":"streaming requests are not supported"}', "application/json"
            return self._forward(raw, passthrough=True)
        try: payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError): return 400, b'{"error":"invalid JSON request"}', "application/json"
        if not isinstance(payload, dict): return 400, b'{"error":"request must be a JSON object"}', "application/json"
        if payload.get("stream") is True: return 400, b'{"error":"streaming requests are not supported (fail-closed)"}', "application/json"
        try:
            self._check_tool_paths(payload)
            encoded = _map_json(payload, self.runtime.encode)
            self.runtime.validate_outbound(encoded)
            return self._forward(json.dumps(encoded, ensure_ascii=False, separators=(",", ":")).encode(), passthrough=False)
        except PrivacyError as exc:
            return 400, json.dumps({"error": str(exc)}).encode(), "application/json"

    def _forward(self, body: bytes, passthrough: bool) -> tuple[int, bytes, str]:
        request = urllib.request.Request(self.upstream_url, data=body, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, result = response.status, response.read()
                content_type = response.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as exc: return exc.code, exc.read(), "application/json"
        except (urllib.error.URLError, TimeoutError, OSError): return 502, b'{"error":"upstream request failed"}', "application/json"
        if passthrough: return status, result, content_type
        try: decoded = _map_json(json.loads(result), self.runtime.decode)
        except (ValueError, UnicodeDecodeError): return 502, b'{"error":"upstream returned invalid JSON"}', "application/json"
        except PrivacyError as exc: return 502, json.dumps({"error": str(exc)}).encode(), "application/json"
        return status, json.dumps(decoded, ensure_ascii=False, separators=(",", ":")).encode(), content_type

    def server(self, address: tuple[str, int]) -> ThreadingHTTPServer:
        gateway = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                status, body, content_type = gateway.handle(self.rfile.read(length))
                self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, format, *args): pass
        return ThreadingHTTPServer(address, Handler)


def _json_arg(value: str | None) -> list[str]:
    if not value: return []
    parsed = json.loads(value)
    if not isinstance(parsed, list): raise ValueError("expected a JSON array")
    return [str(item) for item in parsed]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="bPrivate local runtime prototype")
    parser.add_argument("--mode", choices=("off", "on"), default="off"); parser.add_argument("--values"); parser.add_argument("--protected-paths")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("on"); sub.add_parser("off"); sub.add_parser("status"); sub.add_parser("help"); sub.add_parser("info"); enc = sub.add_parser("encode"); enc.add_argument("text"); dec = sub.add_parser("decode"); dec.add_argument("text"); val = sub.add_parser("validate"); val.add_argument("payload"); stage = sub.add_parser("stage-text"); stage.add_argument("path")
    serve = sub.add_parser("serve"); serve.add_argument("--listen", default="127.0.0.1:8765"); serve.add_argument("--upstream", required=True); serve.add_argument("--mode", dest="serve_mode", choices=("off", "on"), default=None); serve.add_argument("--values", dest="serve_values", default=None); serve.add_argument("--protected-path", action="append", dest="serve_paths", default=[])
    args = parser.parse_args(argv)
    try:
        values = _json_arg(args.values)
        paths = _json_arg(args.protected_paths)
        if args.command == "serve":
            values = _json_arg(args.serve_values) if args.serve_values is not None else values
            paths = args.serve_paths or paths
            host, port = args.listen.rsplit(":", 1); gateway = PrivacyGateway(args.upstream, args.serve_mode or args.mode, values, paths)
            print(json.dumps({"ok": True, "listening": args.listen, "upstream": args.upstream}, sort_keys=True), flush=True)
            gateway.server((host, int(port))).serve_forever(); return 0
        runtime = PrivacyRuntime(args.mode, values, paths)
        if args.command in {"on", "off"}: result = {"mode": args.command, "message": f"bPrivate {args.command}"}
        elif args.command in {"help", "info"}: result = {"commands": ["on", "off", "status", "help", "info"], "description": "Optional local encode/decode gateway for online-model traffic."}
        elif args.command == "status": result = runtime.status()
        elif args.command == "encode": result = {"encoded": runtime.encode(args.text), "status": runtime.status()}
        elif args.command == "decode": result = {"decoded": runtime.decode(args.text), "status": runtime.status()}
        elif args.command == "validate": result = {"valid": runtime.validate_outbound(args.payload)}
        else: result = {"text": runtime.stage_text(args.path)}
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True)); return 0
    except (PrivacyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}, sort_keys=True)); return 2


if __name__ == "__main__": raise SystemExit(main())
