# Hermes Devin ACP

Use the models included with an authenticated Devin CLI account as a model
provider in Hermes Agent. The provider appears as **Devin Subscription** in
the Hermes `/model` picker and discovers the account's current model catalog
with `devin models list`.

## Requirements

- Hermes Agent with the generic external ACP `ProviderProfile` contract
- Devin CLI available in `PATH`
- An authenticated Devin account (`devin auth status`)

This integration uses the local Devin CLI login. Usage and any on-demand
charges remain governed by the user's Devin plan and account settings.

## Install

```bash
git clone https://github.com/YOUR_ORG/hermes-devin-acp.git
cd hermes-devin-acp
./install.sh
```

Restart Hermes, then run `/model` and select **Devin Subscription**. A model
can also be selected directly:

```text
/model gpt-5-6-terra-medium --provider devin-acp
```

The installer stops with an explicit error when Hermes is too old to load
external ACP plugins. Until the generic ACP change is available in a Hermes
release, install the corresponding Hermes branch or patch first.

## Configuration

The plugin normally finds `devin` in `PATH`. Override the executable or ACP
arguments when needed:

```bash
export HERMES_DEVIN_ACP_COMMAND=/absolute/path/to/devin
export HERMES_DEVIN_ACP_ARGS='acp'
```

## Update

Pull the repository and run `./install.sh` again. The installer replaces only
the `devin-acp` plugin directory.

## Uninstall

```bash
./uninstall.sh
```

## Architecture

Hermes starts `devin acp` over stdio and adapts the ACP conversation to its
normal chat transport. Authentication stays inside Devin CLI; the plugin does
not read, copy, or publish Devin credentials.

## Security

ACP agents can execute tools. Review Hermes and Devin permission settings
before using the provider in repositories containing sensitive data.
