"""Shared fixtures.

Two ways to load the plugin:

* ``plugin_module`` — against a strict stand-in for Hermes' ``ProviderProfile`` that only
  accepts the upstream field names in ``HERMES_PROFILE_FIELDS``. Unknown keywords raise
  ``TypeError`` exactly like the real dataclass, so a contract drift fails here too.
* ``hermes_root`` — a real Hermes Agent checkout (``HERMES_AGENT_ROOT`` or the default
  install path). Tests using it verify ``HERMES_PROFILE_FIELDS`` against the real
  dataclass and load the plugin through Hermes' own discovery.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "hermes_plugin" / "devin-acp"
FAKE_DEVIN = Path(__file__).resolve().parent / "fake_devin.py"

# ProviderProfile dataclass fields the plugin relies on (providers/base.py upstream).
HERMES_PROFILE_FIELDS = (
    "name",
    "api_mode",
    "aliases",
    "display_name",
    "description",
    "signup_url",
    "env_vars",
    "base_url",
    "auth_type",
    "supports_health_check",
    "process_command",
    "process_args",
    "process_command_env_vars",
    "process_args_env_var",
    "fallback_models",
)

_PROFILE_DEFAULTS = {
    "api_mode": "chat_completions",
    "aliases": (),
    "display_name": "",
    "description": "",
    "signup_url": "",
    "env_vars": (),
    "base_url": "",
    "auth_type": "api_key",
    "supports_health_check": True,
    "process_command": "",
    "process_args": (),
    "process_command_env_vars": (),
    "process_args_env_var": "",
    "fallback_models": (),
}


class StrictProviderProfile:
    """Keyword-only constructor mirroring the upstream dataclass field set."""

    def __init__(self, **settings):
        unknown = set(settings) - set(HERMES_PROFILE_FIELDS)
        if unknown:
            raise TypeError(
                f"ProviderProfile.__init__() got an unexpected keyword argument {min(unknown)!r}"
            )
        if "name" not in settings:
            raise TypeError("ProviderProfile.__init__() missing 1 required argument: 'name'")
        self.__dict__.update({**_PROFILE_DEFAULTS, **settings})

    def create_client(self, **client_kwargs):
        return None

    def setup_status(self, **kwargs):
        return None

    def discover_models(self, **kwargs):
        return None

    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        return None


def load_plugin(module_name: str = "devin_acp_under_test"):
    spec = importlib.util.spec_from_file_location(
        module_name, PLUGIN_DIR / "__init__.py", submodule_search_locations=[str(PLUGIN_DIR)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_module(monkeypatch):
    registered = []
    providers = types.ModuleType("providers")
    providers.register_provider = registered.append
    providers_base = types.ModuleType("providers.base")
    providers_base.ProviderProfile = StrictProviderProfile
    monkeypatch.setitem(sys.modules, "providers", providers)
    monkeypatch.setitem(sys.modules, "providers.base", providers_base)
    for var in ("HERMES_DEVIN_ACP_COMMAND", "DEVIN_CLI_PATH", "HERMES_DEVIN_ACP_ARGS"):
        monkeypatch.delenv(var, raising=False)
    module = load_plugin()
    module.registered_profiles = registered
    yield module
    sys.modules.pop("devin_acp_under_test", None)


def find_hermes_root() -> Path | None:
    candidates = [os.environ.get("HERMES_AGENT_ROOT", "")]
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    candidates.append(os.path.join(hermes_home, "hermes-agent"))
    for candidate in candidates:
        if candidate and (Path(candidate) / "providers" / "base.py").is_file():
            return Path(candidate).resolve()
    return None


@pytest.fixture(scope="session")
def hermes_root() -> Path:
    root = find_hermes_root()
    if root is None:
        message = "Hermes Agent checkout not found; set HERMES_AGENT_ROOT to run integration tests"
        if os.environ.get("HERMES_DEVIN_ACP_REQUIRE_HERMES") == "1":
            pytest.fail(message)
        pytest.skip(message)
    if sys.version_info < (3, 11):
        pytest.skip("Hermes Agent requires Python 3.11 or newer")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


@pytest.fixture
def fake_devin(tmp_path, monkeypatch):
    """A ``devin`` stand-in on PATH speaking the CLI subset the plugin uses, incl. ACP."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "fake-devin.log"
    script = bin_dir / "devin"
    script.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "{FAKE_DEVIN}" "$@"\n')
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_DEVIN_LOG", str(log))
    monkeypatch.setenv("FAKE_DEVIN_LOGGED_IN", "1")
    for var in ("HERMES_DEVIN_ACP_COMMAND", "DEVIN_CLI_PATH", "HERMES_DEVIN_ACP_ARGS"):
        monkeypatch.delenv(var, raising=False)
    return types.SimpleNamespace(path=script, log=log)
