"""PyInstaller entry point for CodeSaver release builds."""

import sys
from pathlib import Path

# Keep direct execution and PyInstaller analysis independent of the current
# working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codesaver.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
