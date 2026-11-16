"""Loader guardrail tests (no network: abort path never connects)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import load_snowflake  # noqa: E402


def test_confirm_mismatch_aborts_before_connect(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HR_ENV_FILE", str(tmp_path / "nope.env"))
    monkeypatch.setenv("HR_BACKEND", "sqlite")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "TEST_SABINA_MALER")
    monkeypatch.setattr(sys, "argv", ["load_snowflake.py", "--confirm", "WRONG_DB"])
    assert load_snowflake.main() == 2
    assert "ABORTED" in capsys.readouterr().out


def test_confirm_match_passes_gate(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("HR_ENV_FILE", str(tmp_path / "nope.env"))
    monkeypatch.setenv("HR_BACKEND", "sqlite")
    monkeypatch.setenv("HR_DB", str(tmp_path / "gate.db"))
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "TEST_SANDBOX")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "ASSIGNMENT_SABINA")
    monkeypatch.setattr(sys, "argv", ["load_snowflake.py", "--confirm",
                                      "TEST_SANDBOX.ASSIGNMENT_SABINA"])
    with pytest.raises(sqlite3.OperationalError):
        load_snowflake.main()  # gate passed; sqlite fails later at USE DATABASE


def test_target_counts_guard(tmp_path):
    from hr_demo_env import db

    conn = db.get_connection(sqlite_path=str(tmp_path / "guard.db"))
    conn.execute("CREATE TABLE departments (id INTEGER)")
    for t in ("roles", "employees", "attendance", "leaves", "lifecycle_events"):
        conn.execute(f"CREATE TABLE {t} (id INTEGER)")
    assert load_snowflake._target_counts(conn) == {t: 0 for t in load_snowflake.ORDER}
    conn.execute("INSERT INTO employees VALUES (1)")
    assert load_snowflake._target_counts(conn)["employees"] == 1
    conn.close()


def test_ddl_statements_skip_comments():
    ddl = "-- a comment\n\nCREATE TABLE a (x INT);\n-- trailing\nCREATE TABLE b (y INT);"
    assert load_snowflake._ddl_statements(ddl) == ["CREATE TABLE a (x INT)", "CREATE TABLE b (y INT)"]


def test_ddl_statements_on_real_file():
    ddl = open(os.path.join(os.path.dirname(__file__), "..", "sql", "snowflake_ddl.sql")).read()
    stmts = load_snowflake._ddl_statements(ddl)
    assert len(stmts) == 7 and all(s.upper().startswith("CREATE") for s in stmts)
