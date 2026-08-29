import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bprivacy import (
    OutboundLeakError, PathPolicyError, PrivacyGateway, PrivacyRuntime,
    UnknownPlaceholderError, UnsupportedFileError,
)


class PrivacyRuntimeTests(unittest.TestCase):
    def test_repeated_values_get_stable_placeholder(self):
        runtime = PrivacyRuntime(mode="on", protected_values=["Alice"])
        self.assertEqual(runtime.encode("Alice met Alice"), "{{BPV_0001}} met {{BPV_0001}}")
        self.assertEqual(runtime.status()["mapping_entries"], 1)

    def test_round_trip_decodes_response(self):
        runtime = PrivacyRuntime(mode="on", protected_values=["Alice", "Acme"])
        encoded = runtime.encode("Contact Alice at Acme")
        self.assertEqual(runtime.decode("Reply about " + encoded), "Reply about Contact Alice at Acme")

    def test_mode_off_preserves_behavior(self):
        runtime = PrivacyRuntime(mode="off", protected_values=["Alice"])
        self.assertEqual(runtime.encode("Alice"), "Alice")
        self.assertEqual(runtime.decode("{{BPV_0001}}"), "{{BPV_0001}}")
        self.assertEqual(runtime.status()["mapping_entries"], 0)

    def test_path_policy_rejects_protected_paths(self):
        runtime = PrivacyRuntime(mode="on", protected_values=["Alice"], protected_paths=["/workspace/bSmart/source"])
        with self.assertRaises(PathPolicyError): runtime.check_input_path("/workspace/bSmart/source/secret.txt")
        runtime.check_input_path("/workspace/bSmart/notes.txt")

    def test_outbound_validator_rejects_raw_value_and_mapping_content(self):
        runtime = PrivacyRuntime(mode="on", protected_values=["Alice"])
        runtime.encode("Alice")
        with self.assertRaises(OutboundLeakError): runtime.validate_outbound("Alice is here")
        with self.assertRaises(OutboundLeakError): runtime.validate_outbound({"mapping": runtime.mapping})
        self.assertTrue(runtime.validate_outbound("{{BPV_0001}} is here"))

    def test_unknown_placeholder_fails_closed(self):
        with self.assertRaises(UnknownPlaceholderError): PrivacyRuntime(mode="on", protected_values=["Alice"]).decode("{{BPV_9999}}")

    def test_text_staging_rejects_binary_and_images(self):
        runtime = PrivacyRuntime(mode="on")
        with tempfile.TemporaryDirectory() as d:
            image = Path(d) / "x.png"; image.write_bytes(b"not text")
            with self.assertRaises(UnsupportedFileError): runtime.stage_text(image)
            binary = Path(d) / "x.txt"; binary.write_bytes(b"a\x00b")
            with self.assertRaises(UnsupportedFileError): runtime.stage_text(binary)


class GatewayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.received = []
        outer = self
        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.received.append(body)
                payload = json.loads(body)
                if payload.get("messages", [{}])[-1].get("content") == "fail":
                    self.send_error(503, "mock upstream failure"); return
                if payload.get("tools"):
                    result = {"choices": [{"message": {"tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "lookup", "arguments": json.dumps({"name": payload["messages"][0]["content"]})}}]}}]}
                else:
                    result = {"choices": [{"message": {"content": "Hello " + payload["messages"][0]["content"]}}]}
                encoded = json.dumps(result).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
            def log_message(self, *_args): pass
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        upstream_url = "http://127.0.0.1:%d/v1/chat/completions" % self.upstream.server_port
        self.gateway = PrivacyGateway(upstream_url, mode="on", protected_values=["Alice"])
        self.server = self.gateway.server(("127.0.0.1", 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/v1/chat/completions" % self.server.server_port

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.upstream.shutdown(); self.upstream.server_close()

    def post(self, payload):
        try:
            with urlopen(Request(self.url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})) as response:
                return response.status, response.read()
        except HTTPError as exc: return exc.code, exc.read()

    def test_normal_and_tool_call_responses_are_decoded(self):
        status, body = self.post({"messages": [{"role": "user", "content": "Alice"}]})
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)["choices"][0]["message"]["content"], "Hello Alice")
        status, body = self.post({"messages": [{"role": "user", "content": "Alice"}], "tools": [{}]})
        self.assertEqual(status, 200); self.assertIn("Alice", json.loads(body)["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])
        self.assertNotIn(b"Alice", self.received[-1])

    def test_mode_off_is_byte_equivalent(self):
        gateway = PrivacyGateway("http://127.0.0.1:%d" % self.upstream.server_port, mode="off", protected_values=["Alice"])
        self.server.shutdown(); self.server.server_close(); self.server = gateway.server(("127.0.0.1", 0)); threading.Thread(target=self.server.serve_forever, daemon=True).start()
        raw = b'{"messages":[{"content":"Alice"}]}'
        with urlopen(Request("http://127.0.0.1:%d" % self.server.server_port, data=raw, headers={"Content-Type": "application/json"})) as response: body = response.read()
        self.assertIn(b"Alice", self.received[-1]); self.assertEqual(json.loads(body)["choices"][0]["message"]["content"], "Hello Alice")

    def test_upstream_failure_and_streaming_are_fail_closed(self):
        self.assertEqual(self.post({"messages": [{"content": "fail"}]})[0], 503)
        status, body = self.post({"messages": [{"content": "Alice"}], "stream": True})
        self.assertEqual(status, 400); self.assertIn(b"stream", body)

    def test_protected_tool_path_is_rejected(self):
        self.gateway.runtime.protected_paths = ("/secret",)
        status, body = self.post({"messages": [{"content": "go"}], "tools": [{"function": {"arguments": {"path": "/secret/file"}}}]})
        self.assertEqual(status, 400); self.assertIn(b"protected path", body)


if __name__ == "__main__": unittest.main()
