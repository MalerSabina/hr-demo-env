# DATABASE.md — hr-demo-env

## Data profile

- Entities: departments (~8), roles (~25), employees (~300), attendance logs (~150k rows / 2y), leaves (~1.5k), lifecycle events (~600).
- Access: write-once seed, then read-heavy analytics (aggregations by dept/month/tenure).
- Consistency/durability: prod = Snowflake (time travel, R1/R3); local dev = SQLite file (R7). No concurrent writers; single-threaded generator.

## Candidates

| Option | Fits | Gaps | Verdict |
|--------|------|------|---------|
| Snowflake (mandated target) | R1, R3, R4 — brief requires it; elastic analytics; shares/clones for demo | Costs money; needs credentials; can't run in CI | **Target DWH** |
| SQLite local file | R7 dev parity; zero-ops; same relational model; runs in tests | Not a prod DWH; no warehouse features | **Dev stand-in** |
| Postgres container | Relational parity like SQLite | Extra ops/container for zero gain at this scale; no mandate | Rejected — no benefit over SQLite for R7 |

## Decision

**Snowflake as target (R1, R3, R4 — mandated), SQLite file as local dev mirror (R7).**
One logical model, two physical backends: `sql/snowflake_ddl.sql` is canonical;
`src/hr_demo_env/generator.py` materializes the identical tables in SQLite.

## Schema outline

- `departments(dept_id PK, name, budget)`; `roles(role_id PK, dept_id FK, title, level, base_salary)`.
- `employees(emp_id PK, first, last, email, dept_id FK, role_id FK, manager_id FK→employees, hire_date, term_date NULL, salary)`. Index on `(dept_id, hire_date)`.
- `attendance(att_id PK, emp_id FK, day, clock_in, clock_out, overtime_min)`. Index on `(day, emp_id)`.
- `leaves(leave_id PK, emp_id FK, start_day, end_day, kind [vacation|sick|unpaid])`.
- `lifecycle_events(ev_id PK, emp_id FK, ev_day, kind [promotion|raise|transfer], details_json)`. Index on `(emp_id, ev_day)`.

## Ops notes

- Migrations: versioned files in `sql/` (`V1__...`); SQLite rebuilt from generator, never migrated.
- Backup: Snowflake time travel (prod); SQLite = copy `dev.db` (local).
- Local-vs-Docker: SQLite file volume-mounted at `./data/`; Snowflake reached only via env creds.
