# Attendance Anomaly Dashboard — Visual & Metric Breakdown

**Date:** 2026-11-15  
**Environment:** Tableau Cloud Web Authoring (`malersabina25-37fd130b43`)  
**Data Source:** Snowflake (`TEST_SANDBOX.ASSIGNMENT_SABINA`) via Stored Extract  
**Dashboard Name:** `Attendance Anomaly Dashboard`

---

## Executive Overview
The Attendance Anomaly Dashboard provides operational visibility into employee time-tracking irregularities across departments. It allows HR business partners and department heads to monitor overtime exposure, identify systemic late-arrival patterns, and audit attendance logging compliance over a 2-year historical horizon (~83,000 attendance records across 300 employees).

---

## Detailed Chart-by-Chart Explanation

### Chart 1: Overtime by Department (`Overtime by Dept`)
- **Visual Form:** Horizontal Bar Chart
- **Shelves & Fields:**
  - **Rows (Y-axis):** `DEPARTMENTS.NAME` (e.g., Engineering, Operations, Sales, Marketing, HR, Finance, Data, Support)
  - **Columns (X-axis):** `SUM(ATTENDANCE.OVERTIME_MIN)`
- **What this chart shows:**
  - Aggregates total recorded overtime minutes logged by all employees within each department.
  - Highlights operational strain and workload imbalance. In typical organizations, Operations and Support accumulate higher overtime volumes due to coverage shifts, while Engineering may spike during release cycles.
- **Key Insights for HR Analysts:**
  - Identifies which departments carry excessive overtime liability and potential burnout risk.
  - Serves as an input for workforce planning, headcount justification, and labor-law compliance monitoring (excessive continuous overtime).

---

### Chart 2: Monthly Attendance Trend (`Monthly Attendance Trend`)
- **Visual Form:** Time-Series Line Chart
- **Shelves & Fields:**
  - **Columns (X-axis):** `ATTENDANCE.DAY` (Truncated to Month, continuous time series spanning 24+ months)
  - **Rows (Y-axis):** `COUNT(ATTENDANCE.ATT_ID)` (Total attendance records logged per month)
- **What this chart shows:**
  - The longitudinal volume of employee clock-in/out events over time.
  - Depicts headcount growth trends alongside seasonality in punch-clock activity (dips during major holiday months like December/August, growth as hiring expands the active workforce from initial cohorts to ~183 active employees).
- **Key Insights for HR Analysts:**
  - Baseline health check of attendance tracking compliance.
  - Sudden dips or missing volume in a specific month indicate data pipeline interruptions, missing punch compliance issues, or collective office closures.

---

### Chart 3: Late Clock-Ins by Department (`Late Clock-Ins`)
- **Visual Form:** Departmental Breakdown Bar Chart
- **Shelves & Fields:**
  - **Rows (Y-axis):** `DEPARTMENTS.NAME`
  - **Columns (X-axis):** `COUNT(ATTENDANCE.CLOCK_IN)` (filtered / scoped for clock-ins past the standard 09:30 AM core threshold)
- **What this chart shows:**
  - The frequency and concentration of irregular morning arrival times by business unit.
  - Separates flexible-schedule teams (e.g., Engineering or Creative roles) from strict coverage teams (e.g., Support and Operations) where late clock-ins disrupt shift handovers and customer SLAs.
- **Key Insights for HR Analysts:**
  - Differentiates cultural flexibility from chronic punctuality anomalies.
  - Gives team managers factual data during quarterly performance and attendance reviews rather than relying on subjective observation.

---

## Dashboard Interactivity & Usage Flow
1. **Department Filtering:** Selecting a department bar in Chart 1 highlights that department's specific trajectory on the Monthly Trend (Chart 2) and filters the Late Clock-In breakdown (Chart 3).
2. **Time Slicing:** Hovering or lassoing a specific quarter in Chart 2 isolates overtime and punctuality anomalies specifically for that period.
3. **Single Source of Truth:** Backed by the extracted Snowflake model, ensuring uniform metrics between Tableau reporting and the Claude AI chat agent (`mcp/server.py`).
