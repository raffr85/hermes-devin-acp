"""Load the plugin through a real Hermes Agent checkout (``HERMES_AGENT_ROOT``).

Covers the full path a user hits: plugin discovery from ``HERMES_HOME``, the
``external_process`` credential/status resolvers, model discovery, and a complete
ACP round trip through Hermes' own client against ``tests/fake_devin.py``.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import shutil
import sys

import pytest

from tests.conftest import HERMES_PROFILE_FIELDS, PLUGIN_DIR
from tests.fake_devin import MODEL_IDS

pytestmark = pytest.mark.usefixtures("hermes_root")


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    shutil.copytree(PLUGIN_DIR, home / "plugins" / "model-providers" / "devin-acp")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_PROFILE", raising=False)
    for name in [m for m in sys.modules if m == "providers" or m.startswith("providers.")]:
        monkeypatch.delitem(sys.modules, name)
    return home


@pytest.fixture
def providers(hermes_home):
    return importlib.import_module("providers")


def test_strict_stub_matches_real_provider_profile_fields():
    from providers.base import ProviderProfile

    real_fields = {field.name for field in dataclasses.fields(ProviderProfile)}
    assert set(HERMES_PROFILE_FIELDS) <= real_fields
    for hook in ("create_client", "setup_status", "discover_models", "fetch_models"):
        assert callable(getattr(ProviderProfile, hook))


def test_plugin_is_discovered_and_registered(providers):
    profile = providers.get_provider_profile("devin-acp")
    assert type(profile).__name__ == "DevinACPProfile"
    assert profile.auth_type == "external_process"
    assert providers.get_provider_profile("devin").name == "devin-acp"
    assert "devin-acp" in {p.name for p in providers.list_providers()}
    assert profile.process_command == "devin"
    assert profile.process_args == ("acp",)


def test_external_process_resolvers_see_the_plugin(providers, fake_devin):
    from hermes_cli.auth import (
        get_external_process_provider_status,
        resolve_external_process_provider_credentials,
    )

    status = get_external_process_provider_status("devin-acp")
    assert status["configured"] is True
    assert status["resolved_command"] == str(fake_devin.path)
    assert status["args"] == ["acp"]

    creds = resolve_external_process_provider_credentials("devin-acp")
    assert creds["command"] == str(fake_devin.path)
    assert creds["base_url"] == "acp://devin"


def test_setup_status_and_catalog_against_cli(providers, fake_devin, monkeypatch):
    profile = providers.get_provider_profile("devin-acp")

    monkeypatch.setenv("FAKE_DEVIN_LOGGED_IN", "0")
    status = profile.setup_status()
    assert status["available"] is True
    assert status["logged_in"] is False
    assert status["login_command"] == [str(fake_devin.path), "auth", "login"]
    assert profile.discover_models() is None

    monkeypatch.setenv("FAKE_DEVIN_LOGGED_IN", "1")
    assert profile.setup_status()["logged_in"] is True
    rows = profile.discover_models()
    assert [row["id"] for row in rows] == MODEL_IDS
    assert profile.fetch_models() == MODEL_IDS


def test_acp_round_trip_binds_selected_model(providers, fake_devin, tmp_path):
    from hermes_cli.auth import resolve_external_process_provider_credentials

    profile = providers.get_provider_profile("devin-acp")
    creds = resolve_external_process_provider_credentials("devin-acp")
    client = profile.create_client(
        api_key=creds["api_key"], base_url=creds["base_url"], command=creds["command"],
        args=creds["args"], acp_cwd=str(tmp_path),
    )
    assert client.HERMES_SKIP_TRANSPORT_WRAP is True

    response = client.chat.completions.create(
        model="claude-opus-medium", messages=[{"role": "user", "content": "ping"}], timeout=60,
    )
    assert response.choices[0].message.content == "pong from claude-opus-medium"

    events = [json.loads(line) for line in fake_devin.log.read_text().splitlines()]
    spawn = next(event for event in events if "argv" in event)
    assert spawn["argv"] == ["acp", "--model", "claude-opus-medium"]
    prompt = next(event for event in events if "prompt" in event)
    assert prompt["model"] == "claude-opus-medium"
    assert "ping" in prompt["prompt"]
    assert client._acp_args == [*creds["args"]]  # per-request binding leaves the client clean
