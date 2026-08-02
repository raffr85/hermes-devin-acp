#!/usr/bin/env bash
set -euo pipefail

plugin_source="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hermes_plugin/devin-acp"
hermes_root="${HERMES_HOME:-$HOME/.hermes}"
plugin_target="$hermes_root/plugins/model-providers/devin-acp"
profile_contract="$hermes_root/hermes-agent/providers/base.py"

if [[ ! -f "$profile_contract" ]] || ! grep -q "external_command:" "$profile_contract"; then
  echo "This Hermes installation does not yet support generic external ACP providers." >&2
  echo "Install a Hermes version containing the external ACP ProviderProfile contract first." >&2
  exit 1
fi

if ! command -v devin >/dev/null 2>&1; then
  echo "Devin CLI was not found in PATH." >&2
  exit 1
fi

if ! devin auth status >/dev/null 2>&1; then
  echo "Devin CLI is not authenticated. Run: devin auth login" >&2
  exit 1
fi

mkdir -p "$(dirname "$plugin_target")"
mkdir -p "$plugin_target"
cp -R "$plugin_source/." "$plugin_target/"

echo "Installed Devin Subscription provider at $plugin_target"
echo "Restart Hermes and run /model."
