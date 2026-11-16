"""Grounded HR chat agent (R6). Routes NL questions to metric functions.

An optional llm_client with .generate(prompt: str) -> str polishes wording;
without one, answers render from templates. Either way every answer cites its
source metric (SYSTEM_PROMPT.md contract). Out-of-scope -> refused: True.
"""

from __future__ import annotations

import datetime as dt
import re

from . import db as dbmod
from . import metrics


def _resolve_range(question: str, today=None):
    """Map NL date hints to (start, end, label); default is quarter-to-date."""
    today = today or dt.date.today()
    q = question.lower()
    if "last year" in q:
        y = today.year - 1
        return f"{y}-01-01", f"{y}-12-31", str(y)
    if "last quarter" in q:
        qi = (today.month - 1) // 3 - 1
        year = today.year
        if qi < 0:
            qi, year = 3, year - 1
        start = dt.date(year, 3 * qi + 1, 1)
        end_month = 3 * qi + 3
        if end_month < 12:
            end = dt.date(year, end_month + 1, 1) - dt.timedelta(days=1)
        else:
            end = dt.date(year, 12, 31)
        return start.isoformat(), end.isoformat(), f"Q{qi + 1} {year}"
    if "this year" in q or "year to date" in q:
        return f"{today.year}-01-01", today.isoformat(), f"{today.year} to date"
    qi = (today.month - 1) // 3
    start = dt.date(today.year, 3 * qi + 1, 1)
    return start.isoformat(), today.isoformat(), f"Q{qi + 1} {today.year} to date"


def _known_depts(conn):
    try:
        return [r[0] for r in
                conn.execute("SELECT name FROM departments ORDER BY name").fetchall()]
    except Exception:
        return ["Data", "Engineering", "Finance", "HR",
                "Marketing", "Operations", "Sales", "Support"]


def _mentioned(q: str, names: list) -> list:
    return [n for n in names
            if re.search(r"\b" + re.escape(n) + r"\b", q, re.IGNORECASE)]


def answer_question(question: str, conn, llm_client=None) -> dict:
    q = question.lower()
    start, end, span = _resolve_range(question)

    if any(p in q for p in ("list databases", "show databases", "what databases",
                            "which databases", "warehouses", "what warehouse")):
        try:
            dbs = dbmod.show_databases(conn)
            body = "Visible databases: " + ", ".join(dbs) + "."
        except Exception as exc:
            body = f"Database listing needs HR_BACKEND=snowflake ({type(exc).__name__})."
        return {"answer": body, "sources": ["SHOW DATABASES"], "refused": False}

    if any(k in q for k in ("turnover", "attrition", "resign", "quit", "leaving",
                            "left", "exit", "departed", "churn")):
        rows = metrics.turnover_by_dept(conn, start, end)
        want = _mentioned(q, _known_depts(conn))
        show = [r for r in rows if r["dept"] in want] if want else rows
        body = (f"Turnover by department ({span}):\n" + "\n".join(
            f"- {r['dept']}: {r['started']} started, {r['left']} exits "
            f"(rate {r['rate']})" for r in show))
        if len(show) > 1:
            worst = max(show, key=lambda r: r["rate"])
            body += f"\nHighest: {worst['dept']} at {worst['rate']}."
            if want:
                best = min(show, key=lambda r: r["rate"])
                body += f" Lowest: {best['dept']} at {best['rate']}."
        sources = ["turnover_by_dept", "Retention & Turnover Risk dashboard"]
    elif any(k in q for k in ("headcount", "how many employees", "how many staff",
                              "how many people work", "staff count", "hc")):
        n = metrics.get_headcount(conn, end)
        body, sources = f"Headcount as of {end}: {n} active employees.", ["get_headcount"]
    elif any(k in q for k in ("anomal", "late", "overtime", "missing", "attendance", "clock")):
        rows = metrics.attendance_anomalies(conn, start, end, limit=5000)
        if "overtime" in q and "late" not in q and "missing" not in q:
            focus = "overtime"
        elif "late" in q and "overtime" not in q:
            focus = "late"
        elif "missing" in q:
            focus = "missing_punch"
        else:
            focus = None
        sel = [r for r in rows if r["type"] == focus] if focus else rows
        if "by department" in q or "which department" in q or "per department" in q:
            by_dept: dict = {}
            for r in sel:
                by_dept[r.get("dept", "?")] = by_dept.get(r.get("dept", "?"), 0) + 1
            ranked = sorted(by_dept.items(), key=lambda kv: kv[1], reverse=True)
            kind = focus or "anomalies"
            body = (f"{kind.capitalize()} by department ({span}):\n" + "\n".join(
                f"- {d}: {c} {kind}" for d, c in ranked))
            if ranked:
                body += f"\nMost: {ranked[0][0]} ({ranked[0][1]})."
        elif not sel:
            body = f"No {focus} rows in {span}."
        else:
            body = f"{len(sel)} {focus + ' ' if focus else ''}anomalies in {span} " \
                   f"({sum(1 for r in rows if r['type'] == 'late')} late, " \
                   f"{sum(1 for r in rows if r['type'] == 'missing_punch')} missing punches, " \
                   f"{sum(1 for r in rows if r['type'] == 'overtime')} overtime)."
        sources = ["attendance_anomalies", "Attendance Anomaly dashboard"]
    elif any(k in q for k in ("leave", "vacation", "sick", "time off")):
        n = conn.execute("SELECT COUNT(*) FROM leaves").fetchone()[0]
        body, sources = (f"{n} leave records in the dataset "
                         "(break down by kind via turnover_by_dept companion query).",
                         ["leaves table"])
    else:
        return {"answer": ("Out of scope — I answer headcount, turnover, attendance "
                           "anomalies, and leave questions from the HR dashboards. "
                           "Try: 'turnover by department last quarter?'"),
                "sources": [], "refused": True}

    if llm_client is not None:
        try:
            body = llm_client.generate(
                f"User asked: {question}\nMetric results: {body}\n"
                f"Answer concisely and cite: {', '.join(sources)}.")
        except Exception as exc:  # LLM failure degrades, never hides metrics
            body = f"{body}\n(note: language model unavailable: {exc})"
    return {"answer": body, "sources": sources, "refused": False}


def main() -> None:
    import argparse

    from . import db as dbmod

    ap = argparse.ArgumentParser(description="Ask the HR demo data a question.")
    ap.add_argument("question")
    ap.add_argument("--db", default=None)
    ap.add_argument("--backend", default=None)
    ap.add_argument("--warehouse", default=None)
    ap.add_argument("--database", default=None)
    a = ap.parse_args()
    conn = dbmod.get_connection(backend=a.backend, sqlite_path=a.db,
                                warehouse=a.warehouse, database=a.database)
    try:
        res = answer_question(a.question, conn)
    finally:
        conn.close()
    print(res["answer"])
    print("sources: " + ", ".join(res["sources"]))


if __name__ == "__main__":
    main()
