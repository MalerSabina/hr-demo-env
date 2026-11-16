"""NL-routing tests for improvement 1: date ranges, keywords, dept handling."""

import datetime as dt
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hr_demo_env import agent, metrics  # noqa: E402


@pytest.fixture()
def tiny(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    conn.executescript("""
      CREATE TABLE departments(dept_id INTEGER PRIMARY KEY, name TEXT UNIQUE, budget REAL);
      CREATE TABLE roles(role_id INTEGER PRIMARY KEY, dept_id INTEGER, title TEXT, level TEXT, base_salary REAL);
      CREATE TABLE employees(emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT UNIQUE,
        dept_id INTEGER, role_id INTEGER, manager_id INTEGER, hire_date TEXT, term_date TEXT, salary REAL);
      CREATE TABLE attendance(emp_id INTEGER, day TEXT, clock_in TEXT, clock_out TEXT, overtime_min INTEGER DEFAULT 0);
      CREATE TABLE leaves(leave_id INTEGER PRIMARY KEY, emp_id INTEGER, start_day TEXT, end_day TEXT, kind TEXT);
      CREATE TABLE lifecycle_events(ev_id INTEGER PRIMARY KEY, emp_id INTEGER, ev_day TEXT, kind TEXT, details TEXT);
    """)
    conn.execute("INSERT INTO departments VALUES (1, 'Engineering', 100)")
    conn.execute("INSERT INTO departments VALUES (2, 'Sales', 100)")
    conn.execute("INSERT INTO roles VALUES (1, 1, 'Engineer', 'IC', 10000)")
    conn.execute("INSERT INTO roles VALUES (2, 2, 'Rep', 'IC', 9000)")
    conn.execute("INSERT INTO employees VALUES (1,'A','B','a@x.invalid',1,1,NULL,'2024-01-01',NULL,10000)")
    conn.execute("INSERT INTO employees VALUES (2,'C','D','c@x.invalid',2,2,NULL,'2024-01-01','2025-03-01',9000)")
    conn.execute("INSERT INTO attendance VALUES (1,'2025-06-02','09:45','17:00',0)")
    conn.execute("INSERT INTO attendance VALUES (1,'2025-06-03','09:00','19:00',60)")
    yield conn
    conn.close()


def test_resolve_range_last_year():
    assert agent._resolve_range("turnover last year",
                                today=dt.date(2026, 11, 16)) == ("2025-01-01", "2025-12-31", "2025")


def test_resolve_range_last_quarter():
    assert agent._resolve_range("turnover last quarter",
                                today=dt.date(2026, 11, 16)) == ("2026-07-01", "2026-09-30", "Q3 2026")


def test_resolve_range_default_qtd():
    assert agent._resolve_range("headcount?",
                                today=dt.date(2026, 11, 16)) == ("2026-10-01", "2026-11-16", "Q4 2026 to date")


def test_left_routes_to_turnover(tiny):
    r = agent.answer_question("How many people left last year?", tiny)
    assert r["refused"] is False
    assert "turnover_by_dept" in r["sources"]
    assert "2025" in r["answer"]


def test_overtime_by_dept_names_dept(tiny):
    r = agent.answer_question("Which department had the most overtime last year?", tiny)
    assert r["refused"] is False
    assert "Engineering" in r["answer"]
    assert "Most: Engineering" in r["answer"]


def test_turnover_compare_filters_depts(tiny):
    r = agent.answer_question("Compare turnover in Engineering and Sales last year?", tiny)
    assert r["refused"] is False
    assert "Engineering" in r["answer"] and "Sales" in r["answer"]


def test_anomaly_rows_carry_dept(tiny):
    rows = metrics.attendance_anomalies(tiny, "2025-01-01", "2025-12-31")
    assert rows and all(r["dept"] == "Engineering" for r in rows)


def test_salary_still_refused(tiny):
    assert agent.answer_question("What is the average salary in Engineering?", tiny)["refused"] is True
