# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

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

[0.1.4]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/raffr85/hermes-devin-acp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/raffr85/hermes-devin-acp/releases/tag/v0.1.0
