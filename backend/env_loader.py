"""Small local .env loader for backend scripts and BAML calls.

This intentionally supports only simple KEY=VALUE lines. It avoids adding a
runtime dependency and never prints secret values.
"""

from __future__ import annotations

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def load_local_env(*, override: bool = False) -> None:
    for path in (PROJECT_ROOT / ".env", BACKEND_DIR / ".env"):
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (override or key not in os.environ):
                os.environ[key] = value
