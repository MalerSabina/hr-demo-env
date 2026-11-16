"""Backend-switch tests (no credentials needed)."""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hr_demo_env import db  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_dotenv(tmp_path, monkeypatch):
    # Never let the real project .env leak into backend tests.
    monkeypatch.setenv("HR_ENV_FILE", str(tmp_path / "test.env"))


def test_sqlite_default(tmp_path, monkeypatch):
    monkeypatch.delenv("HR_BACKEND", raising=False)
    p = str(tmp_path / "t.db")
    sqlite3.connect(p).execute("CREATE TABLE t(a)").close()
    conn = db.get_connection(sqlite_path=p)
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    conn.close()


def test_snowflake_missing_env_is_actionable(monkeypatch):
    monkeypatch.setenv("HR_BACKEND", "snowflake")
    for v in db.SNOWFLAKE_VARS + ["SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ROLE"]:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="missing env"):
        db.get_connection()


def test_unknown_backend_rejected():
    with pytest.raises(ValueError, match="unknown HR_BACKEND"):
        db.get_connection(backend="oracle")


def test_pat_auth_wiring(monkeypatch):
    import snowflake.connector
    monkeypatch.setenv("HR_BACKEND", "snowflake")
    for v in db.SNOWFLAKE_VARS:
        monkeypatch.setenv(v, "x")
    monkeypatch.setenv("SNOWFLAKE_PAT", "test-pat-value")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSES", "WH_A,WH_B")
    for v in ("SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    captured = {}
    monkeypatch.setattr(snowflake.connector, "connect",
                        lambda **kw: captured.update(kw) or "SENTINEL")
    assert db.get_connection()._raw == "SENTINEL"
    assert captured["authenticator"] == "PROGRAMMATIC_ACCESS_TOKEN"
    assert captured["token"] == "test-pat-value"
    assert "password" not in captured and "private_key" not in captured


def test_snowflake_no_auth_method_is_actionable(monkeypatch):
    monkeypatch.setenv("HR_BACKEND", "snowflake")
    for v in db.SNOWFLAKE_VARS:
        monkeypatch.setenv(v, "x")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSES", "WH_A")
    for v in ("SNOWFLAKE_PAT", "SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="SNOWFLAKE_PAT"):
        db.get_connection()


def test_warehouses_list_and_limit(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSES", "WH_A, WH_B,WH_C")
    monkeypatch.delenv("SNOWFLAKE_WAREHOUSE", raising=False)
    assert db.allowed_warehouses() == ["WH_A", "WH_B", "WH_C"]
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSES", "A,B,C,D")
    with pytest.raises(RuntimeError, match="max is 3"):
        db.allowed_warehouses()


def test_warehouse_override_validated(monkeypatch):
    import snowflake.connector
    monkeypatch.setenv("HR_BACKEND", "snowflake")
    for v in db.SNOWFLAKE_VARS:
        monkeypatch.setenv(v, "x")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSES", "WH_A,WH_B")
    monkeypatch.setenv("SNOWFLAKE_PAT", "p")
    with pytest.raises(RuntimeError, match="allowed: WH_A, WH_B"):
        db.get_connection(warehouse="WH_NOPE")
    captured = {}
    monkeypatch.setattr(snowflake.connector, "connect", lambda **kw: captured.update(kw))
    db.get_connection(warehouse="WH_B", database="OTHER_DB")
    assert captured["warehouse"] == "WH_B" and captured["database"] == "OTHER_DB"


def test_sqlite_rejects_overrides(tmp_path):
    with pytest.raises(RuntimeError, match="need HR_BACKEND=snowflake"):
        db.get_connection(backend="sqlite", sqlite_path=str(tmp_path / "x.db"), warehouse="WH_A")


def test_dotenv_loads_missing_only(tmp_path, monkeypatch):
    envf = tmp_path / ".env"
    envf.write_text("HR_DB=fromfile.db\nSNOWFLAKE_PAT=file-pat\n# comment\nNOT_A_PAIR\n")
    monkeypatch.setenv("HR_ENV_FILE", str(envf))
    monkeypatch.setenv("SNOWFLAKE_PAT", "real-env-wins")
    monkeypatch.delenv("HR_DB", raising=False)
    db._load_dotenv()
    assert os.environ["HR_DB"] == "fromfile.db"
    assert os.environ["SNOWFLAKE_PAT"] == "real-env-wins"


def test_dotenv_missing_file_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("HR_ENV_FILE", str(tmp_path / "nope.env"))
    db._load_dotenv()  # must not raise
