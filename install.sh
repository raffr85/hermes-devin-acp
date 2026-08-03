#!/usr/bin/env bash
set -euo pipefail

repository="raffr85/hermes-devin-acp"
version="${HERMES_DEVIN_ACP_VERSION:-v0.1.5}"
hermes_root="${HERMES_HOME:-$HOME/.hermes}"
plugin_parent="$hermes_root/plugins/model-providers"
plugin_target="$plugin_parent/devin-acp"
script_dir=""
if script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd)"; then
  :
fi
local_source="$script_dir/hermes_plugin/devin-acp"
profile_contract="$hermes_root/hermes-agent/providers/base.py"
staging=""

cleanup() {
  if [[ -n "$staging" && -d "$staging" ]]; then
    rm -rf -- "$staging"
  fi
}
trap cleanup EXIT

fail() {
  printf 'hermes-devin-acp: %s\n' "$1" >&2
  exit 1
}

if [[ ! -f "$profile_contract" ]] || ! grep -q "external_command:" "$profile_contract"; then
  fail "Hermes does not support external ACP providers. Update Hermes Agent and retry."
fi

command -v devin >/dev/null 2>&1 || fail "Devin CLI was not found. Install it from https://cli.devin.ai/install.sh"
devin auth status >/dev/null 2>&1 || fail "Devin CLI is not authenticated. Run: devin auth login"

mkdir -p "$plugin_parent"
staging="$(mktemp -d "$plugin_parent/.devin-acp.XXXXXX")"

if [[ -f "$local_source/__init__.py" && -f "$local_source/plugin.yaml" && -f "$local_source/install_compat.py" ]]; then
  cp "$local_source/__init__.py" "$local_source/plugin.yaml" "$local_source/install_compat.py" "$staging/"
else
  command -v curl >/dev/null 2>&1 || fail "curl is required for remote installation"
  base_url="https://raw.githubusercontent.com/$repository/$version/hermes_plugin/devin-acp"
  curl --fail --silent --show-error --location "$base_url/__init__.py" --output "$staging/__init__.py"
  curl --fail --silent --show-error --location "$base_url/plugin.yaml" --output "$staging/plugin.yaml"
  curl --fail --silent --show-error --location "$base_url/install_compat.py" --output "$staging/install_compat.py"
fi

[[ -s "$staging/__init__.py" && -s "$staging/plugin.yaml" && -s "$staging/install_compat.py" ]] || fail "Downloaded plugin files are incomplete"

rm -rf -- "$plugin_target"
mv "$staging" "$plugin_target"
staging=""

python3 "$plugin_target/install_compat.py" "$hermes_root" || fail "Hermes compatibility setup failed"

printf 'Installed Devin Subscription provider at %s\n' "$plugin_target"
printf 'Restart Hermes and run /model.\n'
