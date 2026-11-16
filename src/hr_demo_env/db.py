"""Backend switch: SQLite (default, local) or Snowflake (env credentials only).

Env contract (names in .env.example; values never in repo/chat/logs):
  HR_BACKEND=sqlite|snowflake, HR_DB (sqlite path),
  SNOWFLAKE_ACCOUNT/USER/WAREHOUSE/DATABASE/SCHEMA, SNOWFLAKE_ROLE (optional),
  SNOWFLAKE_PAT (programmatic access token, verified against connector 5.2.0),
  SNOWFLAKE_PRIVATE_KEY_PATH (key-pair) or SNOWFLAKE_PASSWORD (fallback).
  Warehouses: SNOWFLAKE_WAREHOUSES="WH_A,WH_B,WH_C" (max 3, first = default)
  or legacy single SNOWFLAKE_WAREHOUSE; per-call override validated against list.
  SNOWFLAKE_DATABASE optional: empty = no default DB (see/use all databases).

Metrics use qmark placeholders; this module translates to %s for Snowflake.
"""

from __future__ import annotations

import os
import re
import sqlite3

SNOWFLAKE_VARS = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_SCHEMA"]
MAX_WAREHOUSES = 3


def allowed_warehouses():
    raw = os.environ.get("SNOWFLAKE_WAREHOUSES") or os.environ.get("SNOWFLAKE_WAREHOUSE") or ""
    houses = [w.strip() for w in raw.split(",") if w.strip()]
    if not houses:
        raise RuntimeError("set SNOWFLAKE_WAREHOUSES (comma-separated, max 3) or SNOWFLAKE_WAREHOUSE")
    if len(houses) > MAX_WAREHOUSES:
        raise RuntimeError(f"got {len(houses)} warehouses, max is {MAX_WAREHOUSES}")
    return houses


def show_databases(conn):
    """All visible databases (Snowflake only). Names are identifiers, not secrets."""
    return [r[1] for r in conn.execute("SHOW DATABASES").fetchall()]


def _load_dotenv(path=None):
    """Load KEY=VALUE lines from the project .env (stdlib, no dependency).

    Real environment always wins over .env. `HR_ENV_FILE` overrides the path
    (used by tests). Missing file = silent no-op. Values are never printed.
    """
    if path is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.environ.get("HR_ENV_FILE") or os.path.join(root, ".env")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("\"'")
        if key and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key) and key not in os.environ:
            os.environ[key] = val


class _Conn:
    def __init__(self, raw, to_format: bool):
        self._raw = raw
        self._to_format = to_format

    def execute(self, sql, params=()):
        if self._to_format:
            sql = sql.replace("?", "%s")
        cur = self._raw.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql, seq):
        if self._to_format:
            sql = sql.replace("?", "%s")
        cur = self._raw.cursor()
        cur.executemany(sql, seq)
        return cur

    def commit(self):
        self._raw.commit()

    def close(self):
        self._raw.close()


def get_connection(backend=None, sqlite_path=None, warehouse=None, database=None):
    _load_dotenv()
    backend = backend or os.environ.get("HR_BACKEND", "sqlite")
    if backend == "sqlite":
        if warehouse or database is not None:
            raise RuntimeError("warehouse/database overrides need HR_BACKEND=snowflake")
        path = sqlite_path or os.environ.get("HR_DB", "data/dev.db")
        return _Conn(sqlite3.connect(path), to_format=False)
    if backend == "snowflake":
        missing = [v for v in SNOWFLAKE_VARS if not os.environ.get(v)]
        if missing:
            raise RuntimeError(
                "missing env for Snowflake: " + ", ".join(missing)
                + " (copy .env.example to .env and fill values locally; never commit .env)")
        try:
            import snowflake.connector
        except ImportError as exc:
            raise RuntimeError("pip install -r requirements-snowflake.txt for HR_BACKEND=snowflake") from exc
        houses = allowed_warehouses()
        wh = warehouse or houses[0]
        if warehouse and warehouse not in houses:
            raise RuntimeError(f"unknown warehouse {warehouse!r}; allowed: {', '.join(houses)}")
        dbname = database if database is not None else (os.environ.get("SNOWFLAKE_DATABASE") or None)
        kwargs: dict = {
            "user": os.environ["SNOWFLAKE_USER"],
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "warehouse": wh,
            "schema": os.environ["SNOWFLAKE_SCHEMA"],
        }
        if dbname:
            kwargs["database"] = dbname
        if os.environ.get("SNOWFLAKE_ROLE"):
            kwargs["role"] = os.environ["SNOWFLAKE_ROLE"]
        pat = os.environ.get("SNOWFLAKE_PAT")
        key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
        if pat:
            kwargs["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
            kwargs["token"] = pat
        elif key_path:
            from cryptography.hazmat.primitives import serialization
            raw = open(os.path.expanduser(key_path), "rb").read()
            key = serialization.load_pem_private_key(raw, password=None)
            kwargs["private_key"] = key.private_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.PKCS8,
                serialization.NoEncryption())
        elif os.environ.get("SNOWFLAKE_PASSWORD"):
            kwargs["password"] = os.environ["SNOWFLAKE_PASSWORD"]
        else:
            raise RuntimeError("set SNOWFLAKE_PAT, SNOWFLAKE_PRIVATE_KEY_PATH, or SNOWFLAKE_PASSWORD")
        return _Conn(snowflake.connector.connect(**kwargs), to_format=True)
    raise ValueError(f"unknown HR_BACKEND={backend!r} (want sqlite|snowflake)")
