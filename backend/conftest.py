"""
Root conftest — mock heavy dependencies so lightweight utility modules
can be tested without the full dependency tree installed.

Also provides enough mocking for open_webui.models.* imports to work,
allowing Pydantic/SQLAlchemy model tests without the full app env.
"""
import os
import sys
import types
from contextlib import contextmanager
from unittest.mock import MagicMock

# ── Tier 1: mock modules that __init__.py needs ──
for mod_name in ("typer", "uvicorn"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# ── Tier 2: set env vars that open_webui.env reads at import time ──
_env_defaults = {
    "DATABASE_URL": "sqlite:///test.db",
    "WEBUI_SECRET_KEY": "test-secret-key",
    "WEBUI_AUTH": "true",
}
for k, v in _env_defaults.items():
    os.environ.setdefault(k, v)

# ── Tier 3: mock the entire open_webui.internal.* chain ──
# Instead of mocking each leaf dependency (peewee, playhouse, cryptography,
# markdown, bs4, ...) we mock the internal modules themselves and provide
# the concrete objects that model files actually use (Base, get_db_context).

_heavy_mods = [
    "peewee",
    "peewee_migrate",
    "playhouse",
    "playhouse.db_url",
    "playhouse.shortcuts",
    "cryptography",
    "cryptography.hazmat",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.serialization",
    "markdown",
    "bs4",
]
for mod_name in _heavy_mods:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Mock wrappers before db.py tries to import it
if "open_webui.internal.wrappers" not in sys.modules:
    sys.modules["open_webui.internal.wrappers"] = MagicMock()

# Build a real-enough open_webui.internal.db module with Base + get_db_context
if "open_webui.internal.db" not in sys.modules:
    from sqlalchemy import MetaData
    from sqlalchemy.orm import Session, declarative_base

    _db_mod = types.ModuleType("open_webui.internal.db")
    _db_mod.Base = declarative_base()
    _db_mod.JSONField = MagicMock()
    _db_mod.get_db = MagicMock()

    @contextmanager
    def _get_db_context(db=None):
        yield db or MagicMock(spec=Session)

    _db_mod.get_db_context = _get_db_context
    _db_mod.get_session = MagicMock()
    sys.modules["open_webui.internal.db"] = _db_mod

# Mock the env module to avoid importing its heavy deps
if "open_webui.env" not in sys.modules:
    _env_mod = types.ModuleType("open_webui.env")
    # Provide commonly accessed attributes with sane defaults
    _env_attrs = {
        "DATABASE_URL": "sqlite:///test.db",
        "DATABASE_SCHEMA": None,
        "DATABASE_POOL_SIZE": 0,
        "DATABASE_POOL_MAX_OVERFLOW": 0,
        "DATABASE_POOL_RECYCLE": 3600,
        "DATABASE_POOL_TIMEOUT": 30,
        "DATABASE_ENABLE_SQLITE_WAL": False,
        "DATABASE_ENABLE_SESSION_SHARING": False,
        "ENABLE_DB_MIGRATIONS": False,
        "OPEN_WEBUI_DIR": os.path.dirname(os.path.abspath(__file__)),
        "VERSION": "0.0.0-test",
        "WEBUI_SECRET_KEY": "test-secret-key",
        "WEBUI_AUTH": True,
        "UVICORN_WORKERS": 1,
        "STATIC_DIR": "/tmp",
        "FRONTEND_BUILD_DIR": "/tmp",
    }
    for attr, val in _env_attrs.items():
        setattr(_env_mod, attr, val)
    sys.modules["open_webui.env"] = _env_mod

# Mock constants module
if "open_webui.constants" not in sys.modules:
    _const_mod = types.ModuleType("open_webui.constants")

    class _ErrorMessages:
        DEFAULT = staticmethod(lambda msg="": msg or "An error occurred")
        NOT_FOUND = staticmethod(lambda: "Not found")
        UNAUTHORIZED = staticmethod(lambda: "Unauthorized")

    _const_mod.ERROR_MESSAGES = _ErrorMessages
    sys.modules["open_webui.constants"] = _const_mod

# Mock the auth module (deep dependency chain: jwt, passlib, etc.)
if "open_webui.utils.auth" not in sys.modules:
    _auth_mod = types.ModuleType("open_webui.utils.auth")
    _auth_mod.get_verified_user = MagicMock()
    _auth_mod.get_admin_user = MagicMock()
    sys.modules["open_webui.utils.auth"] = _auth_mod
