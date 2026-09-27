"""Unit tests for the provider module against a strict stand-in of the upstream contract."""

from __future__ import annotations

import json
import subprocess
import sys
import types
from typing import ClassVar

import pytest

from tests.fake_devin import LOGGED_OUT_TEXT, MODEL_IDS, MODELS

# --- parsers -----------------------------------------------------------------------------


def test_parse_models_json_accepts_bare_id_list(plugin_module):
    assert plugin_module.parse_models_json(json.dumps(["opus", "sonnet", "opus"])) == [
        {"id": "opus", "label": "opus", "note": ""},
        {"id": "sonnet", "label": "sonnet", "note": ""},
    ]


def test_parse_models_json_accepts_object_list(plugin_module):
    payload = [
        {"id": "claude-opus-high", "display_name": "Claude Opus High", "description": "Best quality"},
        {"slug": "swe-1-6-fast", "name": "SWE 1.6 Fast"},
    ]
    assert plugin_module.parse_models_json(json.dumps(payload)) == [
        {"id": "claude-opus-high", "label": "Claude Opus High", "note": "Best quality"},
        {"id": "swe-1-6-fast", "label": "SWE 1.6 Fast", "note": ""},
    ]


def test_parse_models_json_flattens_families_and_ignores_alias_lists(plugin_module):
    rows = plugin_module.parse_models_json(json.dumps(MODELS))
    assert [row["id"] for row in rows] == MODEL_IDS
    assert rows[-1] == {"id": "swe-1-6-fast", "label": "SWE 1.6 Fast", "note": "aliases: fast"}


def test_parse_models_json_accepts_models_envelope(plugin_module):
    rows = plugin_module.parse_models_json(json.dumps({"models": [{"id": "opus"}, {"id": "opus"}]}))
    assert rows == [{"id": "opus", "label": "opus", "note": ""}]


@pytest.mark.parametrize("output", ["", "Not logged in.", "{", json.dumps({"error": "boom"}), json.dumps(42)])
def test_parse_models_json_rejects_non_catalog_output(plugin_module, output):
    assert plugin_module.parse_models_json(output) == []


def test_parse_models_text_reads_indented_rows_only(plugin_module):
    output = (
        "Available models\n\nClaude Opus (claude-opus)\n"
        "  claude-opus-high                     Claude Opus High\n"
        "  aliases: opus\n"
        "  swe-1-6-fast\n"
        "  claude-opus-high                     duplicate\n"
    )
    assert plugin_module.parse_models_text(output) == [
        {"id": "claude-opus-high", "label": "Claude Opus High", "note": ""},
        {"id": "swe-1-6-fast", "label": "swe-1-6-fast", "note": ""},
    ]


@pytest.mark.parametrize(
    ("output", "returncode", "expected"),
    [
        (LOGGED_OUT_TEXT, 0, False),
        ("Logged in as tester@example.com\n", 0, True),
        ("Logged in as tester@example.com\n", 1, False),
        ("", 0, False),
        ("Error: Not logged in. Run `devin auth login`.", 0, False),
        ("Not authenticated", 0, False),
    ],
)
def test_parse_auth_status_uses_output_not_exit_code(plugin_module, output, returncode, expected):
    assert plugin_module.parse_auth_status(output, returncode) is expected


@pytest.mark.parametrize(
    ("args", "model", "expected"),
    [
        (["acp"], "opus", ["acp", "--model", "opus"]),
        (["acp"], "", ["acp"]),
        (["acp"], "devin-acp", ["acp"]),
        (["acp", "--model", "gpt"], "opus", ["acp", "--model", "gpt"]),
        (["acp", "--cloud"], "opus", ["acp", "--cloud"]),
    ],
)
def test_with_model_flag(plugin_module, args, model, expected):
    assert plugin_module.with_model_flag(args, model) == expected


# --- command resolution -------------------------------------------------------------------


def test_resolve_command_and_args_honor_env(plugin_module, monkeypatch):
    assert plugin_module.resolve_command() == "devin"
    assert plugin_module.resolve_args() == ["acp"]
    monkeypatch.setenv("DEVIN_CLI_PATH", "/opt/devin/bin/devin")
    assert plugin_module.resolve_command() == "/opt/devin/bin/devin"
    monkeypatch.setenv("HERMES_DEVIN_ACP_COMMAND", "/custom/devin")
    assert plugin_module.resolve_command() == "/custom/devin"
    monkeypatch.setenv("HERMES_DEVIN_ACP_ARGS", "acp --agent-type 'my agent'")
    assert plugin_module.resolve_args() == ["acp", "--agent-type", "my agent"]


# --- profile -----------------------------------------------------------------------------


def test_profile_matches_upstream_external_process_contract(plugin_module):
    profile = plugin_module.devin_acp
    assert plugin_module.registered_profiles == [profile]
    assert profile.name == "devin-acp"
    assert "devin" in profile.aliases
    assert profile.auth_type == "external_process"
    assert profile.api_mode == "chat_completions"
    assert profile.env_vars == ()
    assert profile.base_url == "acp://devin"
    assert profile.supports_health_check is False
    assert profile.process_command == "devin"
    assert profile.process_args == ("acp",)
    assert profile.process_command_env_vars == ("HERMES_DEVIN_ACP_COMMAND", "DEVIN_CLI_PATH")
    assert profile.process_args_env_var == "HERMES_DEVIN_ACP_ARGS"
    assert profile.fallback_models and all(isinstance(m, str) for m in profile.fallback_models)


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["devin"], returncode, stdout=stdout, stderr="")


def test_setup_status_reports_missing_cli(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: None)
    status = plugin_module.devin_acp.setup_status()
    assert status["available"] is False
    assert status["logged_in"] is False
    assert "cli.devin.ai" in status["detail"]


def test_setup_status_detects_logged_out_despite_zero_exit(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", lambda *a, **k: _completed(LOGGED_OUT_TEXT))
    status = plugin_module.devin_acp.setup_status()
    assert status["available"] is True
    assert status["logged_in"] is False
    assert status["login_command"] == ["/usr/bin/devin", "auth", "login"]
    assert "devin auth login" in status["detail"]


def test_setup_status_detects_logged_in(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", lambda *a, **k: _completed("Logged in as tester\n"))
    status = plugin_module.devin_acp.setup_status()
    assert status["available"] is True
    assert status["logged_in"] is True
    assert status["plan"] == "Devin subscription"


def test_setup_status_reports_timeout_as_unavailable(plugin_module, monkeypatch):
    def timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="devin", timeout=1)

    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", timeout)
    status = plugin_module.devin_acp.setup_status()
    assert status["available"] is False
    assert status["logged_in"] is False
    assert "did not respond" in status["detail"]


def test_discover_models_prefers_json_output(plugin_module, monkeypatch):
    calls = []

    def run(cmd, **_k):
        calls.append(cmd)
        return _completed(json.dumps(MODELS))

    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", run)
    rows = plugin_module.devin_acp.discover_models()
    assert [row["id"] for row in rows] == MODEL_IDS
    assert calls == [["/usr/bin/devin", "models", "list", "--format", "json"]]
    assert plugin_module.devin_acp.fetch_models() == MODEL_IDS


def test_discover_models_falls_back_to_text_listing(plugin_module, monkeypatch):
    outputs = iter(["error: unexpected argument '--format'", "Models:\n  opus  Claude Opus\n  swe-1-6-fast  SWE\n"])
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", lambda cmd, **_k: _completed(next(outputs)))
    assert plugin_module.devin_acp.discover_models() == [
        {"id": "opus", "label": "Claude Opus", "note": ""},
        {"id": "swe-1-6-fast", "label": "SWE", "note": ""},
    ]


@pytest.mark.parametrize("stdout, code", [("Error: Not logged in.", 0), ("", 1), ("{not json", 0)])
def test_discover_models_returns_none_without_a_catalog(plugin_module, monkeypatch, stdout, code):
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: "/usr/bin/devin")
    monkeypatch.setattr(plugin_module.subprocess, "run", lambda cmd, **_k: _completed(stdout, code))
    assert plugin_module.devin_acp.discover_models() is None
    assert plugin_module.devin_acp.fetch_models() is None


def test_discover_models_returns_none_when_cli_missing(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module.shutil, "which", lambda _cmd: None)
    assert plugin_module.devin_acp.discover_models() is None
    assert plugin_module.devin_acp.fetch_models() is None


class _FakeCopilotACPClient:
    """Constructor/attribute surface of ``agent.copilot_acp_client.CopilotACPClient``."""

    HERMES_SKIP_TRANSPORT_WRAP = True
    HERMES_SKIP_ASYNC_WRAP = True
    seen_args: ClassVar[list[list[str]]] = []

    def __init__(self, *, api_key=None, base_url=None, acp_command=None, acp_args=None, **_):
        self.api_key = api_key or "copilot-acp"
        self.base_url = base_url or "acp://copilot"
        self._acp_command = acp_command
        self._acp_args = list(acp_args or [])

    def _run_prompt(self, prompt_text, *, timeout_seconds, model=None):
        type(self).seen_args.append(list(self._acp_args))
        return f"echo:{prompt_text}", ""


@pytest.fixture
def fake_hermes_acp(monkeypatch):
    agent = types.ModuleType("agent")
    shim = types.ModuleType("agent.copilot_acp_client")
    shim.CopilotACPClient = _FakeCopilotACPClient
    monkeypatch.setitem(sys.modules, "agent", agent)
    monkeypatch.setitem(sys.modules, "agent.copilot_acp_client", shim)
    _FakeCopilotACPClient.seen_args = []
    return _FakeCopilotACPClient


def test_create_client_wraps_hermes_acp_shim_and_binds_model_per_request(plugin_module, fake_hermes_acp):
    client = plugin_module.devin_acp.create_client(
        api_key="devin-acp", base_url="acp://devin", command="/opt/devin", args=["acp", "--agent-type", "x"]
    )
    assert isinstance(client, fake_hermes_acp)
    assert client._acp_command == "/opt/devin"
    assert client._acp_args == ["acp", "--agent-type", "x"]
    assert client.HERMES_SKIP_TRANSPORT_WRAP is True

    assert client._run_prompt("hi", timeout_seconds=1, model="opus") == ("echo:hi", "")
    client._run_prompt("hi", timeout_seconds=1, model=None)
    client._run_prompt("hi", timeout_seconds=1, model="devin-acp")
    assert fake_hermes_acp.seen_args == [
        ["acp", "--agent-type", "x", "--model", "opus"],
        ["acp", "--agent-type", "x"],
        ["acp", "--agent-type", "x"],
    ]
    assert client._acp_args == ["acp", "--agent-type", "x"]


def test_create_client_defaults_to_resolved_command(plugin_module, fake_hermes_acp, monkeypatch):
    monkeypatch.setenv("HERMES_DEVIN_ACP_COMMAND", "/custom/devin")
    monkeypatch.setenv("HERMES_DEVIN_ACP_ARGS", "acp --cloud")
    client = plugin_module.devin_acp.create_client(api_key="devin-acp", base_url="acp://devin")
    assert client._acp_command == "/custom/devin"
    assert client._acp_args == ["acp", "--cloud"]
    client._run_prompt("hi", timeout_seconds=1, model="opus")
    assert fake_hermes_acp.seen_args == [["acp", "--cloud"]]
