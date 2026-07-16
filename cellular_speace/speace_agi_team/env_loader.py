"""Load secrets from a local .env file (without overriding existing env vars).

Usage:
    from speace_agi_team.env_loader import load_env
    load_env()           # looks for .env in CWD, then parent dirs
    load_env("path/.env")

This is intentionally a tiny helper so the project stays free of external
dependencies (no `python-dotenv` required). Lines starting with `#` and empty
lines are ignored. Existing environment variables are NEVER overwritten, so
production deployments keep precedence over local .env files.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Optional

_logger = logging.getLogger(__name__)

_ENV_FILENAME = ".env"


def _find_env_file(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up the directory tree from `start` (default: CWD) looking for .env."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / _ENV_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Returns {} on read/parse errors."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        _logger.warning("env_loader: cannot read %s (%s)", path, e)
        return out

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip optional surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load_env(path: Optional[os.PathLike | str] = None) -> int:
    """Load variables from `path` (or auto-discovered .env) into os.environ.

    Existing environment variables are NOT overwritten. Returns the number of
    new variables that were set.
    """
    env_path = Path(path) if path else _find_env_file()
    if env_path is None:
        _logger.debug("env_loader: no .env file found")
        return 0
    parsed = _parse_env_file(env_path)
    set_count = 0
    for key, value in parsed.items():
        if key not in os.environ:
            os.environ[key] = value
            set_count += 1
    if set_count:
        _logger.info("env_loader: loaded %d var(s) from %s", set_count, env_path)
    return set_count
