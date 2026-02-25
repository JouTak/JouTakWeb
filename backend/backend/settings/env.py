from __future__ import annotations

import os
from pathlib import Path


def _read_secret_file(path: str, *, env_name: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(
            f"{env_name} points to unreadable file: {path}"
        ) from exc


def apply_env_file_overrides(keys: tuple[str, ...]) -> None:
    """Load `FOO` from `FOO_FILE` when provided.

    Docker Swarm/Kubernetes often expose secrets as files; this helper keeps
    plain envs backward-compatible while enabling file-based secret injection.
    """
    for key in keys:
        file_key = f"{key}_FILE"
        file_path = os.environ.get(file_key)
        if not file_path:
            continue
        os.environ[key] = _read_secret_file(file_path, env_name=file_key)
