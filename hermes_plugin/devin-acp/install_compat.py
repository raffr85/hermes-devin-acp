#!/usr/bin/env python3
"""Install the minimal Hermes resolver compatibility fix when required."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

MARKER = "# hermes-devin-acp: external provider resolver compatibility"
ANCHOR = "    # 0.5 Exact Hermes provider IDs must win over LOSSY alias collapsing.\n"
PATCH = f'''    {MARKER}
    # Provider plugins extend the auth registry but may be absent from
    # models.dev and the static Hermes overlays. Preserve exact external ACP
    # identities selected by the model picker.
    try:
        from hermes_cli.auth import PROVIDER_REGISTRY as _AUTH_PROVIDER_REGISTRY

        _plugin_config = _AUTH_PROVIDER_REGISTRY.get(raw)
        if _plugin_config is not None and _plugin_config.auth_type == "external_process":
            return ProviderDef(
                id=_plugin_config.id,
                name=_plugin_config.name,
                transport="openai_chat",
                api_key_env_vars=tuple(_plugin_config.api_key_env_vars or ()),
                base_url=_plugin_config.inference_base_url or "",
                auth_type="external_process",
                source="hermes-auth-registry",
            )
    except Exception:
        pass

'''


def patch_source(source: str) -> tuple[str, bool]:
    """Return compatible source and whether a change was necessary."""
    if MARKER in source:
        return source, False
    if (
        "_AUTH_PROVIDER_REGISTRY.get(raw)" in source
        and 'auth_type="external_process"' in source
        and "def resolve_provider_full(" in source
    ):
        return source, False
    if ANCHOR not in source:
        raise RuntimeError(
            "unsupported Hermes provider resolver; update Hermes Agent and retry"
        )
    return source.replace(ANCHOR, PATCH + ANCHOR, 1), True


def install(hermes_root: Path) -> bool:
    target = hermes_root / "hermes-agent" / "hermes_cli" / "providers.py"
    if not target.is_file():
        raise RuntimeError(f"Hermes provider resolver was not found: {target}")
    original = target.read_text(encoding="utf-8")
    updated, changed = patch_source(original)
    if not changed:
        return False
    mode = stat.S_IMODE(target.stat().st_mode)
    fd, temporary = tempfile.mkstemp(prefix=".providers.py.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: install_compat.py HERMES_HOME", file=sys.stderr)
        return 2
    try:
        changed = install(Path(sys.argv[1]).expanduser().resolve())
    except (OSError, RuntimeError) as exc:
        print(f"hermes-devin-acp: {exc}", file=sys.stderr)
        return 1
    if changed:
        print("Applied Hermes external-provider resolver compatibility fix")
    else:
        print("Hermes external-provider resolver is compatible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
