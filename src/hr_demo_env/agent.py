"""Grounded HR chat agent (R6). Routes NL questions to metric functions.

An optional llm_client with .generate(prompt: str) -> str polishes wording;
without one, answers render from templates. Either way every answer cites its
source metric (SYSTEM_PROMPT.md contract). Out-of-scope -> refused: True.
"""

from __future__ import annotations

import datetime as dt

from . import db as dbmod
from . import metrics


def _quarter_range():
    today = dt.date.today()
    q = (today.month - 1) // 3
    start = dt.date(today.year, 3 * q + 1, 1)
    return start.isoformat(), today.isoformat()


def answer_question(question: str, conn, llm_client=None) -> dict:
    q = question.lower()
    start, end = _quarter_range()

    if any(p in q for p in ("list databases", "show databases", "what databases",
                            "which databases", "warehouses", "what warehouse")):
        try:
            dbs = dbmod.show_databases(conn)
            body = "Visible databases: " + ", ".join(dbs) + "."
        except Exception as exc:
            body = f"Database listing needs HR_BACKEND=snowflake ({type(exc).__name__})."
        return {"answer": body, "sources": ["SHOW DATABASES"], "refused": False}

    if any(k in q for k in ("turnover", "attrition", "resign", "quit", "leaving")):
        rows = metrics.turnover_by_dept(conn, start, end)
        worst = max(rows, key=lambda r: r["rate"]) if rows else None
        body = ("Turnover by department:\n" + "\n".join(
            f"- {r['dept']}: {r['started']} started, {r['left']} exits "
            f"(rate {r['rate']})" for r in rows))
        if worst:
            body += f"\nHighest: {worst['dept']} at {worst['rate']}."
        sources = ["turnover_by_dept", "Retention & Turnover Risk dashboard"]
    elif any(k in q for k in ("headcount", "how many employees", "staff count", "hc")):
        n = metrics.get_headcount(conn, end)
        body, sources = f"Headcount as of {end}: {n} active employees.", ["get_headcount"]
    elif any(k in q for k in ("anomal", "late", "overtime", "missing", "attendance", "clock")):
        rows = metrics.attendance_anomalies(conn, start, end)
        body = f"{len(rows)} attendance anomalies since {start} " \
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
