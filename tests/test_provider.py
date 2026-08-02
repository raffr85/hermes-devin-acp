import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


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
