# Contributing

Thank you for helping improve Hermes Devin ACP.

## Development

Fork the repository, create a focused branch, and run the test suite before
opening a pull request:

```bash
python -m pip install pytest
pytest -q
bash -n install.sh uninstall.sh
```

Keep changes small, add tests for behavior changes, and update the README when
the user experience changes. Pull requests must not include credentials, Devin
session data, proprietary code, or generated dependency directories.

## Reporting bugs

Include your operating system, Hermes version or commit, Devin CLI version,
installation method, expected behavior, and sanitized error output. Use the
private process in [SECURITY.md](SECURITY.md) for vulnerabilities.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
