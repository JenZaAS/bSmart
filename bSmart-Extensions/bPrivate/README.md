# bPrivate prototype

A stdlib-only, locally testable privacy runtime and HTTP gateway. The gateway is **chat-completions-compatible** for non-streaming OpenAI-style JSON POST requests, and is **not yet Hermes-integrated** (and is not a Hermes provider adapter).

## CLI

Run from this directory:

```sh
python3 bprivacy.py on
python3 bprivacy.py off
python3 bprivacy.py status
python3 bprivacy.py help
python3 bprivacy.py info
python3 bprivacy.py --mode on --values '["Alice"]' encode 'Hello Alice'
python3 bprivacy.py serve --listen 127.0.0.1:8765 --upstream http://127.0.0.1:9000/v1/chat/completions --mode on --values '["Alice"]' --protected-path /srv/bprivate/source
```

`serve` forwards POST requests to the configured upstream. In mode `on`, every JSON string is recursively encoded before forwarding and recursively decoded in the JSON response, including message content and tool-call arguments. The session mapping remains in memory for the lifetime of the gateway process and is never sent upstream. Protected paths found in tool arguments are rejected. Upstream failures, malformed JSON, unknown placeholders, raw outbound values, and mapping-shaped outbound payloads fail closed. Streaming requests are explicitly rejected with HTTP 400.

Mode `off` forwards the original request bytes and returns the original upstream response bytes (apart from HTTP transport framing), while still rejecting streaming requests because streaming is not implemented. The gateway never logs request or response content.

`encode`, `decode`, `validate`, and `stage-text` are local JSON-returning commands. `stage-text` accepts UTF-8 text only and rejects binary/image files.

## Tests and smoke test

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The integration tests run an in-process mock upstream and exercise normal responses, tool calls, mode-off passthrough, outbound protection, path policy, streaming rejection, and upstream failures. No deployment or external service is required.

## Limitations

- In-memory session state only; no persistence across gateway processes, encryption, key management, or concurrency protocol.
- Exact string replacement, not entity/format-aware redaction.
- Non-streaming JSON only; no image/PDF parsing, provider adapters, or Hermes core changes.
