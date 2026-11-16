"""Smoke tests for hr-demo-env (FLOWS.md main flow). Seeded, hermetic, stdlib-only."""

import json
import sqlite3
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hr_demo_env import generator, metrics, agent  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "dev.db")
    generator.generate(seed=7, out_dir=str(tmp_path / "data"), db_path=path, n_employees=60)
    conn = sqlite3.connect(path)
    yield conn
    conn.close()


def test_generator_deterministic(tmp_path):
    a = generator.generate(seed=7, out_dir=str(tmp_path / "a"), db_path=str(tmp_path / "a.db"), n_employees=60)
    b = generator.generate(seed=7, out_dir=str(tmp_path / "b"), db_path=str(tmp_path / "b.db"), n_employees=60)
    assert a == b
    assert a["employees"] == 60 and a["attendance"] > 1000


def test_headcount_positive(db):
    assert metrics.get_headcount(db, "2026-06-01") > 0


def test_turnover_structure(db):
    rows = metrics.turnover_by_dept(db, "2024-01-01", "2026-12-31")
    assert rows and all(set(r) == {"dept", "started", "left", "rate"} for r in rows)


def test_anomalies_detected(db):
    rows = metrics.attendance_anomalies(db, "2024-01-01", "2026-12-31")
    assert rows and all(r["type"] in ("late", "missing_punch", "overtime") for r in rows)


def test_bad_range_rejected(db):
    with pytest.raises(ValueError):
        metrics.turnover_by_dept(db, "2026-01-01", "2025-01-01")


def test_mcp_manifest_matches_registry():
    root = os.path.join(os.path.dirname(__file__), "..")
    manifest = json.load(open(os.path.join(root, "mcp", "tools.json")))
    sys.path.insert(0, os.path.join(root, "mcp"))
    import server
    assert {t["name"] for t in manifest["tools"]} == set(server.TOOLS)


def test_agent_answers_and_refuses(db):
    ok = agent.answer_question("What is turnover by department last quarter?", db)
    assert not ok["refused"] and ok["sources"]
    no = agent.answer_question("What is Alice's salary?", db)
    assert no["refused"] is True
