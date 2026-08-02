import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def hermes_provider_contract(monkeypatch):
    """Provide the minimal Hermes contract used when loading the plugin."""

    class ProviderProfile:
        def __init__(self, **settings):
            self.__dict__.update(settings)

    providers = types.ModuleType("providers")
    providers.register_provider = lambda profile: None
    providers_base = types.ModuleType("providers.base")
    providers_base.ProviderProfile = ProviderProfile
    monkeypatch.setitem(sys.modules, "providers", providers)
    monkeypatch.setitem(sys.modules, "providers.base", providers_base)


def test_plugin_registers_and_parses_catalog(monkeypatch):
    plugin = Path(__file__).parents[1] / "hermes_plugin" / "devin-acp" / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_devin_acp_plugin", plugin)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class Result:
        returncode = 0
        stdout = """Available models\n\nClaude Sonnet (claude-sonnet)\n  aliases: sonnet\n  claude-sonnet-high                   Claude Sonnet High\n  gpt-5-6-terra-medium                 GPT Terra Medium\n"""

    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/devin")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: Result())

    assert module.devin_acp.fetch_models() == [
        "claude-sonnet-high",
        "gpt-5-6-terra-medium",
    ]
    assert module.devin_acp.display_name == "Devin Subscription"
    assert module.devin_acp.external_model_arg == "--model"


@pytest.mark.parametrize(
    ("which_result", "run_result"),
    [
        (None, None),
        ("/usr/bin/devin", subprocess.TimeoutExpired("devin", 8)),
    ],
)
def test_catalog_failure_returns_none(monkeypatch, which_result, run_result):
    plugin = Path(__file__).parents[1] / "hermes_plugin" / "devin-acp" / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_devin_acp_failures", plugin)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    monkeypatch.setattr(module.shutil, "which", lambda _: which_result)
    if isinstance(run_result, Exception):
        monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(run_result))

    assert module.devin_acp.fetch_models() is None
