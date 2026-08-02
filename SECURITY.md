# Security Policy

## Supported versions

Security fixes are provided for the latest tagged release.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's **Security → Report a
vulnerability** flow for this repository. Include reproduction steps, impact,
and any suggested mitigation. Do not include real credentials or private source
code.

You can expect an acknowledgment within seven days. Details will remain private
until a fix and coordinated disclosure are ready.

## Trust model

This plugin launches the official `devin` executable and communicates over
stdio. It never needs direct access to Devin credentials. Install from a tagged
release when reproducibility matters, review scripts before execution, and keep
Hermes and Devin CLI updated.
