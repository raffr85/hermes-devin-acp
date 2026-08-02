from pathlib import Path
import importlib.util
import sys


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
