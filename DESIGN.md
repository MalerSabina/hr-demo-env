# DESIGN.md — hr-demo-env

## Data models

Mirrors DATABASE.md schema. Key types: dates as `YYYY-MM-DD` text (SQLite) /
`DATE` (Snowflake); `term_date NULL` = active; `kind` columns are checked
against fixed sets (`vacation|sick|unpaid`, `promotion|raise|transfer`).

## Key functions/classes

```python
# generator.py
generate(seed: int, out_dir: str, db_path: str, scale: str = "demo") -> dict[str, int]
# metrics.py
get_headcount(conn, as_of: str) -> int
turnover_by_dept(conn, start: str, end: str) -> list[dict]   # {dept, started, left, rate}
attendance_anomalies(conn, start: str, end: str) -> list[dict]  # {emp_id, day, type, detail}
# agent.py
answer_question(question: str, conn, llm_client=None) -> dict  # {answer, sources[], refused: bool}
# mcp/server.py
TOOLS: dict[str, callable]   # manifest name -> metrics function; must match tools.json
```

## Error handling

- Metric functions validate date ranges (`start <= end`, else `ValueError`).
- Agent: no metric match → `refused: True` + safe completion (R6); LLM errors
  propagate with the metric sources gathered so far.
- Generator: fails fast on unwritable `out_dir`; seed logged in EVIDENCE.md.
- Secrets: `SNOWFLAKE_*` read from env at runtime; missing → actionable error naming the var.
