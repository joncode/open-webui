"""
Root conftest — mock heavy dependencies so lightweight utility modules
can be tested without the full dependency tree installed.
"""
import sys
from unittest.mock import MagicMock

for mod_name in ("typer", "uvicorn"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
