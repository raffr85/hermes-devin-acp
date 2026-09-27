"""Devin subscription provider for Hermes Agent via ACP.

Hermes spawns ``devin acp`` over stdio for every turn through the upstream
``external_process`` provider contract (``process_command``/``process_args`` on
``ProviderProfile`` plus ``create_client``/``discover_models``/``setup_status``).
Authentication stays inside the official Devin CLI.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

PROVIDER_ID = "devin-acp"
DEFAULT_COMMAND = "devin"
DEFAULT_ARGS: tuple[str, ...] = ("acp",)
COMMAND_ENV_VARS: tuple[str, ...] = ("HERMES_DEVIN_ACP_COMMAND", "DEVIN_CLI_PATH")
ARGS_ENV_VAR = "HERMES_DEVIN_ACP_ARGS"
LOGIN_ARGS: tuple[str, ...] = ("auth", "login")
CLI_TIMEOUT_SECONDS = 8.0

_TEXT_MODEL_LINE = re.compile(r"^ {2}(\S+)(?: {2,}(.*\S))?\s*$")
_LOGGED_OUT_MARKERS = ("not logged in", "not authenticated", "auth login")
_ID_KEYS = ("id", "slug", "model_id", "model", "name")
_LABEL_KEYS = ("display_name", "displayName", "label", "title", "name")
_NOTE_KEYS = ("note", "description", "aliases")


def resolve_command() -> str:
    """Executable name or path, honoring the override environment variables."""
    for var in COMMAND_ENV_VARS:
        value = os.getenv(var, "").strip()
        if value:
            return value
    return DEFAULT_COMMAND


def resolve_args() -> list[str]:
    raw = os.getenv(ARGS_ENV_VAR, "").strip()
    return shlex.split(raw) if raw else list(DEFAULT_ARGS)


def run_cli(
    args: list[str] | tuple[str, ...],
    *,
    timeout: float = CLI_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str] | None:
    """Run ``devin <args>``; ``None`` when the CLI is missing or does not finish in time."""
    command = shutil.which(resolve_command())
    if not command:
        return None
    try:
        return subprocess.run(
            [command, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def parse_auth_status(output: str, returncode: int) -> bool:
    """``devin auth status`` exits 0 even when logged out, so the verdict comes from its text."""
    text = (output or "").strip()
    if returncode != 0 or not text:
        return False
    lowered = text.lower()
    return not any(marker in lowered for marker in _LOGGED_OUT_MARKERS)


def _first_str(entry: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if key == "aliases" and isinstance(value, list):
            aliases = [str(v).strip() for v in value if str(v).strip()]
            if aliases:
                return "aliases: " + ", ".join(aliases)
    return ""


def _holds_objects(value: Any) -> bool:
    return isinstance(value, dict) or (
        isinstance(value, list) and any(isinstance(item, (dict, list)) for item in value)
    )


def _walk_model_entries(node: Any, rows: list[dict[str, str]]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_model_entries(item, rows)
        return
    if not isinstance(node, dict):
        return
    before = len(rows)
    for child in node.values():
        if _holds_objects(child):
            _walk_model_entries(child, rows)
    if len(rows) > before:
        return  # a family/container: its leaves are the models
    model_id = _first_str(node, _ID_KEYS)
    if model_id:
        label = _first_str(node, _LABEL_KEYS) or model_id
        rows.append({"id": model_id, "label": label, "note": _first_str(node, _NOTE_KEYS)})


def parse_models_json(output: str) -> list[dict[str, str]]:
    """Flatten ``devin models list --format json`` into ``[{id, label, note}]`` rows.

    Accepts a bare list of ids, a list of model objects, a ``{"models": [...]}`` envelope,
    or families nesting their models, so a CLI release that reshapes the envelope keeps
    working. String lists inside an object (``aliases``) are attributes, not models.
    """
    try:
        payload = json.loads(output or "")
    except ValueError:
        return []
    rows: list[dict[str, str]] = []
    if isinstance(payload, list) and payload and all(isinstance(item, str) for item in payload):
        rows = [{"id": item.strip(), "label": item.strip(), "note": ""} for item in payload if item.strip()]
    else:
        _walk_model_entries(payload, rows)
    return _dedupe(rows)


def parse_models_text(output: str) -> list[dict[str, str]]:
    """Fallback for CLIs without ``--format json``: two-space indented ``<id>  <label>`` lines."""
    rows: list[dict[str, str]] = []
    for line in (output or "").splitlines():
        match = _TEXT_MODEL_LINE.match(line)
        if not match:
            continue
        model_id = match.group(1)
        if model_id.endswith(":"):
            continue
        rows.append({"id": model_id, "label": (match.group(2) or model_id).strip(), "note": ""})
    return _dedupe(rows)


def _dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        if row["id"] not in seen:
            seen.add(row["id"])
            unique.append(row)
    return unique


def with_model_flag(args: list[str], model: str) -> list[str]:
    """``devin acp --model <id>`` binds every session the child opens to the selected model."""
    model = (model or "").strip()
    if not model or model == PROVIDER_ID or "--model" in args or "--cloud" in args:
        return list(args)
    return [*args, "--model", model]


class _RequestState(threading.local):
    model: str = ""


_client_class: type | None = None


def client_class() -> type:
    """Lazily build the ACP client on top of Hermes' bundled stdio ACP shim."""
    global _client_class
    if _client_class is not None:
        return _client_class

    from agent.copilot_acp_client import CopilotACPClient

    class DevinACPClient(CopilotACPClient):
        """``CopilotACPClient`` pointed at ``devin acp`` with per-request model binding.

        The upstream shim selects the model after ``session/new`` when the agent
        advertises it as a config option. Devin additionally honors ``--model`` at
        spawn, which also covers fuzzy names (``opus``) that are not option values,
        so the requested model is appended to the spawn arguments per call. Clients
        are shared across threads, hence the thread-local request state.
        """

        def __init__(
            self,
            *,
            acp_command: str | None = None,
            acp_args: list[str] | None = None,
            command: str | None = None,
            args: list[str] | None = None,
            **kwargs: Any,
        ):
            self._request_state = _RequestState()
            super().__init__(
                acp_command=acp_command or command or resolve_command(),
                acp_args=list(acp_args or args or resolve_args()),
                **kwargs,
            )
            self.api_key = kwargs.get("api_key") or PROVIDER_ID
            self.base_url = kwargs.get("base_url") or devin_acp.base_url

        @property
        def _acp_args(self) -> list[str]:
            return with_model_flag(self._base_acp_args, self._request_state.model)

        @_acp_args.setter
        def _acp_args(self, value: list[str]) -> None:
            self._base_acp_args = list(value)

        def _run_prompt(
            self,
            prompt_text: str,
            *,
            timeout_seconds: float,
            model: str | None = None,
        ) -> tuple[str, str]:
            self._request_state.model = str(model or "").strip()
            try:
                return super()._run_prompt(prompt_text, timeout_seconds=timeout_seconds, model=model)
            finally:
                self._request_state.model = ""

    _client_class = DevinACPClient
    return DevinACPClient


def _status(*, available: bool, logged_in: bool, detail: str, login_command: list[str]) -> dict[str, Any]:
    return {
        "available": available,
        "logged_in": logged_in,
        "plan": "Devin subscription" if logged_in else "",
        "detail": detail,
        "login_command": login_command,
    }


class DevinACPProfile(ProviderProfile):
    """Devin CLI as an ``external_process`` provider: catalog and login state come from the CLI."""

    def create_client(self, **client_kwargs: Any) -> Any:
        return client_class()(**client_kwargs)

    def setup_status(self, **kwargs: Any) -> dict[str, Any]:
        """Real login state: ``devin auth status`` exits 0 even when logged out, so read its text."""
        command = resolve_command()
        resolved = shutil.which(command)
        login_command = [resolved or command, *LOGIN_ARGS]
        if not resolved:
            detail = f"Devin CLI '{command}' was not found. Install it from https://cli.devin.ai/install.sh"
            return _status(available=False, logged_in=False, detail=detail, login_command=login_command)
        completed = run_cli(("auth", "status"))
        if completed is None:
            detail = f"`{command} auth status` did not respond within {CLI_TIMEOUT_SECONDS:g}s. Run it manually to inspect the CLI."
            return _status(available=False, logged_in=False, detail=detail, login_command=login_command)
        logged_in = parse_auth_status(f"{completed.stdout}\n{completed.stderr}", completed.returncode)
        detail = "Devin CLI is authenticated." if logged_in else f"Devin CLI is not authenticated. Run: {command} auth login"
        return _status(available=True, logged_in=logged_in, detail=detail, login_command=login_command)

    def discover_models(self, **kwargs: Any) -> list[dict[str, Any]] | None:
        completed = run_cli(("models", "list", "--format", "json"))
        if completed is None or completed.returncode != 0:
            return None
        rows = parse_models_json(completed.stdout)
        if not rows:
            text = run_cli(("models", "list"))
            if text is None or text.returncode != 0:
                return None
            rows = parse_models_text(text.stdout)
        return rows or None

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = CLI_TIMEOUT_SECONDS,
    ) -> list[str] | None:
        rows = self.discover_models()
        return [row["id"] for row in rows] if rows else None


devin_acp = DevinACPProfile(
    name=PROVIDER_ID,
    aliases=("devin", "devin-subscription"),
    display_name="Devin Subscription",
    description="Devin CLI models using your authenticated subscription",
    signup_url="https://app.devin.ai/",
    api_mode="chat_completions",
    env_vars=(),
    auth_type="external_process",
    base_url="acp://devin",
    supports_health_check=False,
    process_command=DEFAULT_COMMAND,
    process_args=DEFAULT_ARGS,
    process_command_env_vars=COMMAND_ENV_VARS,
    process_args_env_var=ARGS_ENV_VAR,
    fallback_models=("sonnet", "opus", "gpt", "gemini", "swe"),
)

register_provider(devin_acp)
