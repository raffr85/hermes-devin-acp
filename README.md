# Hermes Devin ACP

Use the models available to your Devin account directly from
[Hermes Agent](https://github.com/NousResearch/hermes-agent). The provider runs
the official Devin CLI over ACP, keeps authentication in the CLI, and appears as
**Devin Subscription** in Hermes' `/model` picker.

> [!IMPORTANT]
> This project does not share a Devin subscription. Every user must authenticate
> with an account they are authorized to use. Usage and charges are controlled by
> that account's Devin plan.

## Quick start

You need Hermes Agent v2026.9.24 or newer (`hermes update`). Then install the
official Devin CLI, authenticate, and install this provider:

```bash
curl -fsSL https://cli.devin.ai/install.sh | bash
devin auth login
curl -fsSL https://raw.githubusercontent.com/raffr85/hermes-devin-acp/v0.2.0/install.sh | bash
```

Restart Hermes, run `/model`, and select **Devin Subscription**.

To inspect the installer before running it:

```bash
git clone https://github.com/raffr85/hermes-devin-acp.git
cd hermes-devin-acp
./install.sh
```

## Requirements

- macOS or Linux
- `bash` and, for the one-line install, `curl`
- Hermes Agent >= v2026.9.24 (the first release that loads `external_process`
  provider plugins from `$HERMES_HOME/plugins`)
- the official `devin` CLI in `PATH`
- an authenticated Devin account (`devin auth login`)

The installer copies two files to
`${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers/devin-acp` and never
modifies Hermes itself. It fails with an actionable message when the Devin CLI
is missing or the Hermes checkout at `${HERMES_AGENT_ROOT:-$HERMES_HOME/hermes-agent}`
predates the provider contract, and only warns when the CLI is installed but
not logged in (`devin auth status` exits 0 either way; the installer reads its
output). Re-running it updates the plugin in place.

## Usage

Select any model reported by your account through `/model`, or choose one
directly:

```text
/model gpt-5-6-terra-medium --provider devin-acp
```

The catalog comes from `devin models list --format json` (falling back to the
plain-text listing, then to a small built-in list), so available models vary by
account and over time. Hermes starts `devin acp --model <selected-model>`,
binding the ACP session to the model selected in Hermes rather than passing it
as a prompt hint. Selecting the bare `devin-acp` entry lets the CLI pick its
default model.

## Configuration

The defaults work for standard installations. These optional variables override
them:

```bash
export HERMES_DEVIN_ACP_COMMAND=/absolute/path/to/devin   # or DEVIN_CLI_PATH
export HERMES_DEVIN_ACP_ARGS='acp --cloud'                 # shell-split; default: acp
```

`--model` is only appended when the arguments do not already carry `--model`
or `--cloud`. Set `HERMES_HOME` if Hermes uses a non-default data directory and
`HERMES_AGENT_ROOT` if the Hermes checkout is not at `$HERMES_HOME/hermes-agent`.
To install a specific provider release through the remote installer, set
`HERMES_DEVIN_ACP_VERSION`, for example `v0.2.0`.

## Update and uninstall

Run the install command again to update. Remove only this provider with:

```bash
curl -fsSL https://raw.githubusercontent.com/raffr85/hermes-devin-acp/v0.2.0/uninstall.sh | bash
```

## Troubleshooting

**`Devin CLI was not found`** — install it and open a new shell so `devin` is in
`PATH`.

**`Devin CLI is not authenticated`** — run `devin auth login`, then retry.
Hermes' provider setup reports the same login state from `devin auth status`.

**`predates the external_process provider contract` / `is older than v2026.9.24`**
— run `hermes update`. If Hermes lives outside `$HERMES_HOME/hermes-agent`, set
`HERMES_AGENT_ROOT` before installing.

**`Please log in to use Devin` in a response** — the CLI session expired; run
`devin auth login` again.

**The provider is absent from `/model`** — restart Hermes after installation and
verify that `HERMES_HOME` points to the same Hermes installation you run.

## How it works

The plugin registers an `external_process` `ProviderProfile` named `devin-acp`
(aliases `devin`, `devin-subscription`). Hermes' own stdio ACP client
(`agent/copilot_acp_client.py`) starts `devin acp` over stdio and adapts the
ACP conversation to its normal chat-completions transport; the plugin only adds
the `--model` flag, `devin auth status` parsing for the setup screen, and the
JSON model catalog. Authentication remains inside the official Devin CLI; this
plugin does not read, copy, log, or publish Devin credentials.

## Security and billing

ACP agents can execute tools: `devin acp` runs locally with your user's
permissions and can read and modify files or run commands in the working
directory Hermes hands it. Review Hermes and Devin permission settings before
using the provider in repositories containing sensitive data. Devin usage may
consume included quota or on-demand credits. See [SECURITY.md](SECURITY.md) for
private vulnerability reporting.

## Contributing

Bug reports and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md)
before submitting a change. This independent community project is not affiliated
with or endorsed by Cognition AI or Nous Research.

Released under the [MIT License](LICENSE).
