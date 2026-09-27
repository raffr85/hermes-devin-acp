# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-27

Requires Hermes Agent >= v2026.9.24. Earlier plugin releases targeted a provider
contract that never shipped in Hermes and fail to load on every published version.

### Changed

- Port the provider to the upstream `external_process` contract (`process_command`,
  `process_args`, `process_command_env_vars`, `process_args_env_var`) with the
  `create_client`, `setup_status`, `discover_models`, and `fetch_models` hooks.
- Reuse Hermes' own stdio ACP client instead of shipping a transport; the plugin
  only binds `--model` per request through thread-local state.
- Read the model catalog from `devin models list --format json`, keeping the
  plain-text listing and the built-in list as fallbacks.
- Extend CI to Python 3.10–3.13 and add an integration job that loads
  the plugin through a real Hermes checkout, pinned to the supported release.

### Fixed

- Treat `devin auth status` output as the login verdict; the command exits 0
  when logged out, so the previous check never failed.
- Stop the installer from rejecting compatible Hermes versions; it now checks the
  real contract and the Hermes package version, and warns instead of failing when
  the CLI is installed but not logged in.
- Replace the permissive `ProviderProfile` test stub that hid the contract break.

### Removed

- `install_compat.py` and all in-place patching of Hermes core.

## [0.1.5] - 2026-08-03

- Make the installer detect and repair affected Hermes provider resolvers.
- Keep installation idempotent and avoid requiring manual `config.yaml` edits.
- Validate exact external ACP provider selection through regression tests.

## [0.1.4] - 2026-08-02

### Fixed

- Bind the model selected in Hermes to each Devin ACP process with
  `devin acp --model <selected-model>`.
- Use the provider-neutral external ACP client contract so Hermes can identify
  the integration as Devin instead of Copilot.

## [0.1.3] - 2026-08-02

### Changed

- Pin the documented remote install and uninstall commands to an immutable
  release tag.
- Make the remote installer's default source the current tagged release.
- Document every local validation command used by CI.

## [0.1.2] - 2026-08-02

### Fixed

- Isolate the Hermes provider contract in tests so the full CI matrix can run
  independently of a Hermes installation.

## [0.1.1] - 2026-08-02

### Fixed

- Make formatting and shell checks portable across local and CI environments.

## [0.1.0] - 2026-08-02

### Added

- Initial public release of the Devin ACP model provider for Hermes Agent.
- Installer, uninstaller, tests, CI, release automation, and OSS community
  documentation.

[0.2.0]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.5...v0.2.0
[0.1.5]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/raffr85/hermes-devin-acp/releases/tag/v0.1.0
