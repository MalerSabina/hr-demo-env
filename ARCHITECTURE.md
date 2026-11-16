# ARCHITECTURE.md — hr-demo-env

## Components

| Component | Responsibility |
|-----------|----------------|
| `generator.py` | Seeded fictitious HR data → CSVs + SQLite `dev.db` (R2, R7) |
| Snowflake DWH | Canonical prod schema + seeded tables (R1, R3) |
| Tableau | Extract + 2 dashboards (Attendance Anomaly, Retention & Turnover Risk) (R4) |
| `metrics.py` | Metric functions over either backend (headcount, turnover, anomalies) (R5) |
| `mcp/server.py` | MCP tool server exposing metrics per `tools.json` (R5) |
| `agent.py` | NL → metric calls → grounded answer via Claude (R6) |

## Diagram

```
[generator.py] --seed--> [CSVs + SQLite dev.db]   (local, R7)
      |  (same model)
      v
[Snowflake DWH] --extract--> [Tableau: 2 dashboards]   (R4)
      ^
[metrics.py] <--SQL--> (either backend)
      ^
[mcp/server.py] --tools--> [agent.py] --Claude API--> user   (R5, R6)
```

## Trade-off

One logical model on two backends (Snowflake prod / SQLite dev) costs a small
translation burden (DDL dialects) but buys credential-free local dev and CI —
worth it since R7 explicitly requires it.
