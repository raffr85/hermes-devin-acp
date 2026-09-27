#!/usr/bin/env python3
"""Stand-in for the Devin CLI used by the tests.

Mirrors the observed behavior of ``devin`` 3000.x: ``auth status`` and ``models list`` exit 0
even when logged out (the verdict is in the text), and ``acp`` speaks ACP JSON-RPC over stdio,
advertising the model as a ``configOptions`` entry on ``session/new``.
"""

from __future__ import annotations

import json
import os
import sys

MODELS = {
    "families": [
        {
            "id": "claude-opus",
            "display_name": "Claude Opus",
            "aliases": ["opus"],
            "models": [
                {"id": "claude-opus-high", "display_name": "Claude Opus High"},
                {"id": "claude-opus-medium", "display_name": "Claude Opus Medium"},
            ],
        },
        {
            "id": "swe",
            "display_name": "SWE",
            "models": [{"id": "swe-1-6-fast", "display_name": "SWE 1.6 Fast", "aliases": ["fast"]}],
        },
    ]
}
MODEL_IDS = [m["id"] for family in MODELS["families"] for m in family["models"]]
LOGGED_OUT_TEXT = (
    "Not logged in.\n  Credentials path: /tmp/fake/credentials.toml\n"
    "Run `devin auth login` to authenticate.\n"
)


def _logged_in() -> bool:
    return os.environ.get("FAKE_DEVIN_LOGGED_IN") == "1"


def _log(entry: dict) -> None:
    path = os.environ.get("FAKE_DEVIN_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


def _send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def _acp(argv: list[str]) -> int:
    model = argv[argv.index("--model") + 1] if "--model" in argv else "swe-1-6-fast"
    _log({"argv": argv, "model": model})
    session_id = "fake-session"
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, request_id, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": 1, "agentCapabilities": {}}})
        elif method == "session/new":
            option = {
                "id": "model",
                "name": "Model",
                "category": "model",
                "type": "select",
                "currentValue": model,
                "options": [{"value": m, "name": m} for m in MODEL_IDS],
            }
            _send({"jsonrpc": "2.0", "id": request_id, "result": {"sessionId": session_id, "configOptions": [option]}})
        elif method == "session/set_config_option":
            model = str(params.get("value") or model)
            _log({"set_config_option": params})
            _send({"jsonrpc": "2.0", "id": request_id, "result": {}})
        elif method == "session/prompt":
            if not _logged_in():
                _send({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": "Please log in to use Devin."}})
                continue
            prompt_text = " ".join(str(p.get("text") or "") for p in params.get("prompt") or [] if isinstance(p, dict))
            _log({"prompt": prompt_text, "model": model})
            _send({
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": f"pong from {model}"}},
                },
            })
            _send({"jsonrpc": "2.0", "id": request_id, "result": {"stopReason": "end_turn"}})
        elif request_id is not None:
            _send({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"unknown method {method}"}})
    return 0


def main(argv: list[str]) -> int:
    if argv[:2] == ["auth", "status"]:
        sys.stdout.write("Logged in as tester@example.com\n  Credentials path: /tmp/fake/credentials.toml\n" if _logged_in() else LOGGED_OUT_TEXT)
        return 0
    if argv[:2] == ["models", "list"]:
        if not _logged_in():
            sys.stdout.write("Error: Not logged in. Run `devin auth login` to authenticate.\n")
            return 0
        if "json" in argv:
            sys.stdout.write(json.dumps(MODELS) + "\n")
        else:
            sys.stdout.write("Available models\n\n")
            for family in MODELS["families"]:
                sys.stdout.write(f"{family['display_name']} ({family['id']})\n")
                for m in family["models"]:
                    sys.stdout.write(f"  {m['id']:<36} {m['display_name']}\n")
        return 0
    if argv[:1] == ["acp"]:
        return _acp(argv)
    sys.stderr.write(f"fake devin: unsupported arguments {argv!r}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
