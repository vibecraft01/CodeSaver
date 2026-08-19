"""Runtime compatibility checks."""

from __future__ import annotations

import sys
from typing import Optional, Tuple

MIN_PYTHON: Tuple[int, int] = (3, 9)


def check_python_version(version_info: Optional[Tuple[int, int]] = None) -> bool:
    """Return whether the current (or supplied) interpreter is supported."""
    current = version_info or (sys.version_info.major, sys.version_info.minor)
    return current >= MIN_PYTHON


def python_version_text(version_info: Optional[Tuple[int, int]] = None) -> str:
    current = version_info or (sys.version_info.major, sys.version_info.minor)
    return f"{current[0]}.{current[1]}"
