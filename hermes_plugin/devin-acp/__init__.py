"""Devin subscription provider for Hermes Agent via ACP."""

from __future__ import annotations

import re
import shutil
import subprocess

from providers import register_provider
from providers.base import ProviderProfile

_MODEL_LINE = re.compile(r"^\s{2}([^\s]+)\s{2,}\S")


class DevinACPProfile(ProviderProfile):
    """Discover the models exposed by the authenticated Devin CLI."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        command = shutil.which(self.external_command)
        if not command:
            return None
        try:
            completed = subprocess.run(
                [command, "models", "list"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None

        models: list[str] = []
        for line in completed.stdout.splitlines():
            match = _MODEL_LINE.match(line)
            if match:
                models.append(match.group(1))
        return list(dict.fromkeys(models)) or None


devin_acp = DevinACPProfile(
    name="devin-acp",
    aliases=("devin", "devin-subscription"),
    display_name="Devin Subscription",
    description="Devin CLI models using your authenticated subscription",
    signup_url="https://app.devin.ai/",
    api_mode="chat_completions",
    auth_type="external_process",
    base_url="acp://devin",
    supports_health_check=False,
    external_command="devin",
    external_args=("acp",),
    external_command_env="HERMES_DEVIN_ACP_COMMAND",
    external_args_env="HERMES_DEVIN_ACP_ARGS",
    external_auth_args=("auth", "status"),
    external_model_arg="--model",
    fallback_models=("sonnet", "opus", "gpt", "gemini", "swe"),
)

register_provider(devin_acp)
