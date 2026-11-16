"""Load the HR demo dataset into Snowflake (Phase 1, guided [HITL] B.2).

Reads credentials from env/.env only (never prints values).
Creates DATABASE (IF NOT EXISTS) + HR_DEMO schema, runs sql/snowflake_ddl.sql,
clears tables child-first, bulk-loads data/*.csv. Idempotent: safe to re-run.

Usage: HR_BACKEND=snowflake .venv/bin/python scripts/load_snowflake.py
Target DB comes from SNOWFLAKE_DATABASE (TEST_SABINA_MALER).
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hr_demo_env import db  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
ORDER = ["departments", "roles", "employees", "attendance", "leaves", "lifecycle_events"]


def _target_counts(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ORDER}


def _ddl_statements(text):
    code = "\n".join(l for l in text.splitlines()
                      if l.strip() and not l.strip().startswith("--"))
    return [c for c in (s.strip() for s in code.split(";")) if c]


def _csv_rows(name):
    with open(os.path.join(ROOT, "data", f"{name}.csv"), newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Load HR demo dataset into Snowflake.")
    ap.add_argument("--confirm", required=True,
                    help="Type DATABASE.SCHEMA to prove write intent, e.g. --confirm \"TEST_SANDBOX.ASSIGNMENT_SABINA\"")
    ap.add_argument("--allow-overwrite", action="store_true",
                    help="Clear the 6 HR tables first. Without it, existing data aborts the load.")
    args = ap.parse_args()
    database = os.environ.get("SNOWFLAKE_DATABASE", "TEST_SANDBOX")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "ASSIGNMENT_SABINA")
    if args.confirm != f"{database}.{schema}":
        print(f"ABORTED: --confirm must exactly match SNOWFLAKE_DATABASE.SNOWFLAKE_SCHEMA={database}.{schema}")
        return 2
    conn = db.get_connection()
    try:
        conn.execute(f"USE DATABASE {database}")
        if not conn.execute(f"SHOW SCHEMAS LIKE '{schema}' IN DATABASE {database}").fetchall():
            conn.execute(f"CREATE SCHEMA {database}.{schema}")
        ddl = open(os.path.join(ROOT, "sql", "snowflake_ddl.sql")).read().replace("HR_DEMO", schema)
        for stmt in _ddl_statements(ddl):
            if stmt.strip().upper().startswith("CREATE SCHEMA"):
                continue  # schema ensured above; role has CREATE TABLE inside it, not CREATE SCHEMA on DB
            conn.execute(stmt)
        conn.execute(f"USE SCHEMA {database}.{schema}")
        counts = _target_counts(conn)
        if any(counts.values()) and not args.allow_overwrite:
            print(f"ABORTED: target tables already hold data {counts}; re-run with --allow-overwrite to clear first")
            return 2
        if any(counts.values()):
            for name in reversed(ORDER):  # child-first clear, only with --allow-overwrite
                conn.execute(f"DELETE FROM {name}")
        total = 0
        for name in ORDER:
            rows = _csv_rows(name)
            cols = list(rows[0].keys())
            vals = [[r[c] if r[c] not in ("", "None") else None for c in cols] for r in rows]
            if name == "lifecycle_events":  # VARIANT col: PARSE_JSON illegal in VALUES + driver needs VALUES for executemany, so row-by-row SELECT form (460 rows)
                for v in vals:
                    conn.execute(
                        f"INSERT INTO {name} ({', '.join(cols)}) SELECT {', '.join(['PARSE_JSON(?)' if c == 'details' else '?' for c in cols])}",
                        v)
            else:
                conn.executemany(
                    f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                    vals)
            total += len(vals)
            print(f"loaded {name}: {len(vals)} rows")
        conn.commit()
        print(f"DONE database={database} schema={schema} total_rows={total}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
