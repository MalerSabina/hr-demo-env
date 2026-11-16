"""Metric functions shared by the agent and the MCP server (R5).

Each maps 1:1 to a tool in mcp/tools.json. Work over any sqlite3 connection
so local dev and tests need no credentials.
"""

from __future__ import annotations


def _check_range(start: str, end: str) -> None:
    if start > end:
        raise ValueError(f"expected start <= end as YYYY-MM-DD, got {start} > {end}")


def get_headcount(conn, as_of: str) -> int:
    """Active employees on a date: hired on/before, not terminated before."""
    return conn.execute(
        "SELECT COUNT(*) FROM employees WHERE hire_date <= ? AND (term_date IS NULL OR term_date >= ?)",
        (as_of, as_of)).fetchone()[0]


def turnover_by_dept(conn, start: str, end: str) -> list[dict]:
    """Per-department starts, exits, and exit rate over [start, end]."""
    _check_range(start, end)
    rows = conn.execute(
        """SELECT d.name,
                  SUM(CASE WHEN e.hire_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS started,
                  SUM(CASE WHEN e.term_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS left,
                  COUNT(*) AS total
           FROM employees e JOIN departments d ON d.dept_id = e.dept_id
           GROUP BY d.name ORDER BY d.name""", (start, end, start, end)).fetchall()
    return [{"dept": n, "started": s, "left": l,
             "rate": round(l / total, 3) if total else 0.0}
            for n, s, l, total in rows]


def attendance_anomalies(conn, start: str, end: str, limit: int = 50) -> list[dict]:
    """Late arrivals (>09:30), missing punches, overtime rows in range."""
    _check_range(start, end)
    rows = conn.execute(
        """SELECT a.emp_id, a.day, a.clock_in, a.clock_out, a.overtime_min, d.name
           FROM attendance a
           JOIN employees e ON e.emp_id = a.emp_id
           JOIN departments d ON d.dept_id = e.dept_id
           WHERE a.day BETWEEN ? AND ?
             AND (a.clock_in > '09:30' OR a.clock_out IS NULL OR a.overtime_min > 0)
           ORDER BY a.day LIMIT ?""", (start, end, limit)).fetchall()
    out = []
    for emp_id, day, ci, co, ot, dept in rows:
        if co is None:
            typ, detail = "missing_punch", f"clock_in={ci}, no clock_out"
        elif ot and ot > 0:
            typ, detail = "overtime", f"overtime_min={ot}"
        else:
            typ, detail = "late", f"clock_in={ci}"
        out.append({"emp_id": emp_id, "day": day, "type": typ,
                    "detail": detail, "dept": dept})
    return out
