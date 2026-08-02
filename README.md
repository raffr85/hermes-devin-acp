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

You need a recent Hermes Agent installation with external ACP provider support.
Then install the official Devin CLI, authenticate, and install this provider:

```bash
curl -fsSL https://cli.devin.ai/install.sh | bash
devin auth login
curl -fsSL https://raw.githubusercontent.com/raffr85/hermes-devin-acp/v0.1.3/install.sh | bash
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
- Hermes Agent with the external ACP `ProviderProfile` contract
- the official `devin` CLI in `PATH`
- an authenticated Devin account (`devin auth status`)

The installer fails with an actionable message when a requirement is missing.
It writes only to `${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers/devin-acp`.

## Usage

Select any model reported by your account through `/model`, or choose one
directly:

```text
/model gpt-5-6-terra-medium --provider devin-acp
```

The catalog is discovered dynamically with `devin models list`, so available
models can vary by account and over time.

## Configuration

The defaults work for standard installations. These optional variables override
them:

```bash
export HERMES_DEVIN_ACP_COMMAND=/absolute/path/to/devin
export HERMES_DEVIN_ACP_ARGS='acp'
```

Set `HERMES_HOME` if Hermes uses a non-default data directory. To install a
specific provider release through the remote installer, set
`HERMES_DEVIN_ACP_VERSION`, for example `v0.1.3`.

## Update and uninstall

Run the install command again to update. Remove only this provider with:

```bash
curl -fsSL https://raw.githubusercontent.com/raffr85/hermes-devin-acp/v0.1.3/uninstall.sh | bash
```

## Troubleshooting

**`Devin CLI was not found`** — install it and open a new shell so `devin` is in
`PATH`.

**`Devin CLI is not authenticated`** — run `devin auth login`, then retry.

**`Hermes does not support external ACP providers`** — update Hermes Agent to a
version whose `providers/base.py` includes the `external_command` profile field.

**The provider is absent from `/model`** — restart Hermes after installation and
verify that `HERMES_HOME` points to the same Hermes installation you run.

## How it works

Hermes starts `devin acp` over stdio and adapts the ACP conversation to its
normal chat transport. The plugin asks `devin models list` for the current model
catalog. Authentication remains inside the official Devin CLI; this plugin does
not read, copy, log, or publish Devin credentials.

## Security and billing

ACP agents can execute tools. Review Hermes and Devin permission settings before
using the provider in repositories containing sensitive data. Devin usage may
consume included quota or on-demand credits. See [SECURITY.md](SECURITY.md) for
private vulnerability reporting.

## Contributing

Bug reports and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md)
before submitting a change. This independent community project is not affiliated
with or endorsed by Cognition AI or Nous Research.

Released under the [MIT License](LICENSE).
