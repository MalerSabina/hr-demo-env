"""Seeded fictitious HR data generator (stdlib only).

Writes CSVs + a SQLite dev.db mirroring sql/snowflake_ddl.sql.
Same seed -> identical dataset (R2, N2). No real PII (N1).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import random
import sqlite3

FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Eli", "Nora", "Owen", "Iris",
         "Kai", "Lena", "Milo", "Aria", "Jon", "Sana", "Theo", "Uma", "Vera"]
LAST = ["Cohen", "Levi", "Mizrahi", "Peretz", "Shapira", "Katz", "Baruch",
        "Halevi", "Ohana", "Azulay", "Goldstein", "Dahan", "Weiss", "Klein"]
DEPTS = [("Engineering", 2_400_000), ("Sales", 1_800_000), ("Support", 900_000),
         ("Marketing", 1_100_000), ("Finance", 1_000_000), ("HR", 600_000),
         ("Operations", 1_300_000), ("Data", 1_500_000)]
ROLES = [("Engineer", "IC", 1.0), ("Senior Engineer", "IC", 1.35),
         ("Manager", "M", 1.6), ("Analyst", "IC", 0.9), ("Director", "M", 2.1)]

SCHEMA_SQL = """
CREATE TABLE departments(dept_id INTEGER PRIMARY KEY, name TEXT UNIQUE, budget REAL);
CREATE TABLE roles(role_id INTEGER PRIMARY KEY, dept_id INTEGER, title TEXT, level TEXT, base_salary REAL);
CREATE TABLE employees(emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT UNIQUE,
  dept_id INTEGER, role_id INTEGER, manager_id INTEGER, hire_date TEXT, term_date TEXT, salary REAL);
CREATE TABLE attendance(att_id INTEGER PRIMARY KEY, emp_id INTEGER, day TEXT, clock_in TEXT, clock_out TEXT, overtime_min INTEGER DEFAULT 0);
CREATE TABLE leaves(leave_id INTEGER PRIMARY KEY, emp_id INTEGER, start_day TEXT, end_day TEXT, kind TEXT);
CREATE TABLE lifecycle_events(ev_id INTEGER PRIMARY KEY, emp_id INTEGER, ev_day TEXT, kind TEXT, details TEXT);
CREATE INDEX idx_emp_dept ON employees(dept_id, hire_date);
CREATE INDEX idx_att_day ON attendance(day, emp_id);
CREATE INDEX idx_ev_emp ON lifecycle_events(emp_id, ev_day);
"""


def _workdays(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def generate(seed: int, out_dir: str, db_path: str, n_employees: int = 300) -> dict[str, int]:
    rng = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)
    end = dt.date.today()
    start = end - dt.timedelta(days=730)

    departments = [{"dept_id": i + 1, "name": n, "budget": b} for i, (n, b) in enumerate(DEPTS)]
    roles, rid = [], 1
    for d in departments:
        for title, level, mult in rng.sample(ROLES, 3):
            roles.append({"role_id": rid, "dept_id": d["dept_id"], "title": f"{title} ({d['name']})",
                          "level": level, "base_salary": round(14000 * mult)})
            rid += 1

    employees = []
    for i in range(1, n_employees + 1):
        d = rng.choice(departments)
        droles = [r for r in roles if r["dept_id"] == d["dept_id"]]
        r = rng.choice(droles)
        hire = start + dt.timedelta(days=rng.randint(0, 700))
        term = None
        if rng.random() < 0.12:
            term = hire + dt.timedelta(days=rng.randint(180, 700))
            if term > end:
                term = None
        employees.append({
            "emp_id": i, "first_name": rng.choice(FIRST), "last_name": rng.choice(LAST),
            "email": f"emp{i:04d}@example.invalid", "dept_id": d["dept_id"], "role_id": r["role_id"],
            "manager_id": None, "hire_date": hire.isoformat(),
            "term_date": term.isoformat() if term else None,
            "salary": round(r["base_salary"] * rng.uniform(0.95, 1.2))})
    by_dept: dict[int, list[dict]] = {}
    for e in employees:
        by_dept.setdefault(e["dept_id"], []).append(e)
    for members in by_dept.values():  # earliest hire per dept manages it
        members.sort(key=lambda e: e["hire_date"])
        mgr = members[0]["emp_id"]
        for e in members[1:]:
            e["manager_id"] = mgr

    attendance, leaves, events = [], [], []
    for e in employees:
        hire = dt.date.fromisoformat(e["hire_date"])
        last = dt.date.fromisoformat(e["term_date"]) if e["term_date"] else end
        for day in _workdays(max(hire, start), min(last, end)):
            if rng.random() < 0.02:  # missing punch anomaly
                attendance.append((e["emp_id"], day.isoformat(), "09:00", None, 0))
                continue
            ci = dt.time(8, rng.randint(20, 59)) if rng.random() < 0.9 else dt.time(9, rng.randint(31, 59))
            late = ci >= dt.time(9, 31)
            if rng.random() < 0.08:  # overtime
                co, ot = dt.time(19, rng.randint(0, 59)), rng.randint(30, 150)
            else:
                co, ot = dt.time(17, rng.randint(0, 59)), 0
            row = (e["emp_id"], day.isoformat(), ci.strftime("%H:%M"), co.strftime("%H:%M"), ot)
            attendance.append(row)
            if late:
                pass  # late arrival detectable from clock_in; kept inline, no extra row
        for _ in range(rng.randint(0, 6)):
            s = start + dt.timedelta(days=rng.randint(0, 720))
            leaves.append((e["emp_id"], s.isoformat(),
                           (s + dt.timedelta(days=rng.randint(1, 10))).isoformat(),
                           rng.choice(["vacation", "vacation", "sick", "unpaid"])))
        for _ in range(rng.randint(0, 3)):
            events.append((e["emp_id"],
                           (start + dt.timedelta(days=rng.randint(0, 720))).isoformat(),
                           rng.choice(["promotion", "raise", "transfer"]), "{}"))

    tables = {"departments": departments, "roles": roles, "employees": employees}
    for name, rows in tables.items():
        with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    for name, rows, cols in [
            ("attendance", attendance, ["emp_id", "day", "clock_in", "clock_out", "overtime_min"]),
            ("leaves", leaves, ["emp_id", "start_day", "end_day", "kind"]),
            ("lifecycle_events", events, ["emp_id", "ev_day", "kind", "details"])]:
        with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)

    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    for d in departments:
        conn.execute("INSERT INTO departments VALUES (?,?,?)", (d["dept_id"], d["name"], d["budget"]))
    for r in roles:
        conn.execute("INSERT INTO roles VALUES (?,?,?,?,?)",
                     (r["role_id"], r["dept_id"], r["title"], r["level"], r["base_salary"]))
    for e in employees:
        conn.execute("INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (e["emp_id"], e["first_name"], e["last_name"], e["email"], e["dept_id"],
                      e["role_id"], e["manager_id"], e["hire_date"], e["term_date"], e["salary"]))
    conn.executemany("INSERT INTO attendance(emp_id,day,clock_in,clock_out,overtime_min) VALUES (?,?,?,?,?)", attendance)
    conn.executemany("INSERT INTO leaves(emp_id,start_day,end_day,kind) VALUES (?,?,?,?)", leaves)
    conn.executemany("INSERT INTO lifecycle_events(emp_id,ev_day,kind,details) VALUES (?,?,?,?)", events)
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("departments", "roles", "employees", "attendance", "leaves", "lifecycle_events")}
    conn.close()
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate fictitious HR demo data (seeded).")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    ap.add_argument("--db", default="data/dev.db")
    ap.add_argument("--n", type=int, default=300, help="employees to generate")
    a = ap.parse_args()
    counts = generate(a.seed, a.out, a.db, a.n)
    print(f"seed={a.seed} " + " ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
