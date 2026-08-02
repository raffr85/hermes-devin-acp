#!/usr/bin/env bash
set -euo pipefail

hermes_root="${HERMES_HOME:-$HOME/.hermes}"
plugin_target="$hermes_root/plugins/model-providers/devin-acp"

if [[ -d "$plugin_target" ]]; then
  rm -rf "$plugin_target"
  echo "Removed $plugin_target"
else
  echo "Devin ACP provider is not installed."
fi
