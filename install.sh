#!/usr/bin/env bash
set -euo pipefail

repository="raffr85/hermes-devin-acp"
version="${HERMES_DEVIN_ACP_VERSION:-v0.2.0}"
hermes_root="${HERMES_HOME:-$HOME/.hermes}"
hermes_agent="${HERMES_AGENT_ROOT:-$hermes_root/hermes-agent}"
plugin_parent="$hermes_root/plugins/model-providers"
plugin_target="$plugin_parent/devin-acp"
devin_cmd="${HERMES_DEVIN_ACP_COMMAND:-${DEVIN_CLI_PATH:-devin}}"
plugin_files=(__init__.py plugin.yaml)
script_dir=""
if script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd)"; then
  :
fi
local_source="$script_dir/hermes_plugin/devin-acp"
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

warn() {
  printf 'hermes-devin-acp: warning: %s\n' "$1" >&2
}

# Hermes release v2026.9.24 (package 0.21.5) is the first that resolves plugin external_process
# providers from $HERMES_HOME/plugins; dev checkouts report 0.0.0 and are assumed current.
min_hermes_release="v2026.9.24"
min_hermes_package="0.21.5"

version_lt() {
  local IFS=. i
  local -a a b
  read -r -a a <<<"$1"
  read -r -a b <<<"$2"
  for i in 0 1 2; do
    if ((10#${a[i]:-0} < 10#${b[i]:-0})); then return 0; fi
    if ((10#${a[i]:-0} > 10#${b[i]:-0})); then return 1; fi
  done
  return 1
}

if [[ -d "$hermes_agent" ]]; then
  profile_contract="$hermes_agent/providers/base.py"
  acp_client="$hermes_agent/agent/copilot_acp_client.py"
  if [[ ! -f "$profile_contract" ]] || ! grep -q "process_command:" "$profile_contract" \
    || ! grep -q "def create_client" "$profile_contract" || [[ ! -f "$acp_client" ]]; then
    fail "Hermes Agent at $hermes_agent predates the external_process provider contract ($min_hermes_release). Run: hermes update"
  fi
  hermes_package="$(sed -n 's/^version = "\([0-9.]*\)".*/\1/p' "$hermes_agent/pyproject.toml" 2>/dev/null | head -n 1)"
  if [[ -n "$hermes_package" && "$hermes_package" != "0.0.0" ]] && version_lt "$hermes_package" "$min_hermes_package"; then
    fail "Hermes Agent $hermes_package at $hermes_agent is older than $min_hermes_release ($min_hermes_package). Run: hermes update"
  fi
else
  warn "Hermes Agent checkout not found at $hermes_agent; skipping contract check (requires Hermes >= $min_hermes_release)."
fi

command -v "$devin_cmd" >/dev/null 2>&1 || fail "Devin CLI '$devin_cmd' was not found. Install it from https://cli.devin.ai/install.sh"

# `devin auth status` exits 0 when logged out; the verdict is in its output.
auth_output="$("$devin_cmd" auth status 2>&1 || true)"
if [[ -z "$auth_output" ]] || printf '%s' "$auth_output" | grep -qiE 'not logged in|not authenticated|auth login'; then
  warn "Devin CLI is not authenticated. Run: $devin_cmd auth login"
fi

mkdir -p "$plugin_parent"
staging="$(mktemp -d "$plugin_parent/.devin-acp.XXXXXX")"

local_complete=1
for file in "${plugin_files[@]}"; do
  [[ -f "$local_source/$file" ]] || local_complete=0
done

if [[ "$local_complete" == 1 ]]; then
  for file in "${plugin_files[@]}"; do
    cp "$local_source/$file" "$staging/"
  done
else
  command -v curl >/dev/null 2>&1 || fail "curl is required for remote installation"
  base_url="https://raw.githubusercontent.com/$repository/$version/hermes_plugin/devin-acp"
  for file in "${plugin_files[@]}"; do
    curl --fail --silent --show-error --location "$base_url/$file" --output "$staging/$file"
  done
fi

for file in "${plugin_files[@]}"; do
  [[ -s "$staging/$file" ]] || fail "Plugin file $file is missing or empty"
done
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$staging/__init__.py" \
    || fail "Plugin module does not parse with $(command -v python3)"
fi

rm -rf -- "$plugin_target"
mv "$staging" "$plugin_target"
staging=""

printf 'Installed Devin Subscription provider at %s\n' "$plugin_target"
printf 'Restart Hermes and run /model, then pick "Devin Subscription".\n'
