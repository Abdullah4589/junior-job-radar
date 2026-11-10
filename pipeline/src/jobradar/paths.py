"""Locate the repository root when the package is installed editable."""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    override = os.environ.get("JOBRADAR_ROOT")
    if override:
        root = Path(override).resolve()
        if not (root / "README.md").is_file():
            raise FileNotFoundError(f"JOBRADAR_ROOT={root} has no README.md")
        return root

    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "pipeline" / "pyproject.toml").is_file() and (
            candidate / "README.md"
        ).is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate the Junior Job Radar repo root. Set JOBRADAR_ROOT."
    )
