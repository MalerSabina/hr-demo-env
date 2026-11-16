# TABLEAU_GUIDE.md — hr-demo-env

Step-by-step instructions for building the 2 dashboards in **Tableau Cloud Web Authoring**.
Target site: `https://prod-ch-a.online.tableau.com/#/site/malersabina25-37fd130b43`
Target project: `default`

---

## 1. Snowflake Connection Credentials (copy-paste)

| Field | Value | Notes |
|---|---|---|
| **Server** | `pla72994.east-us-2.azure.snowflakecomputing.com` | standard host |
| **Authentication** | Username and Password | or PAT if web authoring allows token |
| **Username** | `SABINA_MALER` | from prompt |
| **Password** | `<enter locally in Tableau prompt — never commit>` | use PAT if web authoring allows token; rotate any temp password from the brief |
| **Role** | `TEST_ROLE_SABINA` | critical: must set this role |
| **Warehouse** | `TEST_WH` | first warehouse |
| **Database** | `TEST_SANDBOX` | where data was loaded |
| **Schema** | `ASSIGNMENT_SABINA` | 6 tables |

---

## 2. Connect & Build the Stored Extract

1. Open Tableau Cloud site → navigate to **Explore** → project **default**.
2. Click **New** (top-right) → **Workbook**.
3. In the Connect to Data dialog:
   - Search for connector: **Snowflake**.
   - Fill the credentials from the table above.
4. In the Data Source canvas:
   - Select Database: `TEST_SANDBOX`.
   - Select Schema: `ASSIGNMENT_SABINA`.
5. Drag tables onto canvas and join them (all left/inner joins on IDs):
   - `EMPLOYEES` (center table)
   - Join `DEPARTMENTS` on `EMPLOYEES.DEPT_ID = DEPARTMENTS.DEPT_ID`
   - Join `ROLES` on `EMPLOYEES.ROLE_ID = ROLES.ROLE_ID`
   - Join `ATTENDANCE` on `EMPLOYEES.EMP_ID = ATTENDANCE.EMP_ID`
   - Join `LEAVES` on `EMPLOYEES.EMP_ID = LEAVES.EMP_ID` (relationship / left join)
6. Switch **Connection** at top-right from **Live** to **Extract**.
   *(Per brief: "Create an optimized, stored data extract within Tableau to serve as the single source of truth.")*
7. Rename the Data Source: `HR_Analytics_Extract`.

---

## 3. Calculated Fields to Create First

Create these calculated fields in the Data pane (Analysis → Create Calculated Field):

### For Attendance
```
// [Is_Late]
IF [CLOCK_IN] > #09:30:00# THEN 1 ELSE 0 END

// [Is_Missing_Punch]
IF ISNULL([CLOCK_IN]) OR ISNULL([CLOCK_OUT]) THEN 1 ELSE 0 END

// [Overtime_Hours]
ZN([OVERTIME_MIN]) / 60.0

// [Anomaly_Flag]
IF [Is_Late] = 1 OR [Is_Missing_Punch] = 1 OR [OVERTIME_MIN] > 0 THEN 1 ELSE 0 END
```

### For Retention & Turnover
```
// [Is_Active]
IF ISNULL([TERM_DATE]) THEN 1 ELSE 0 END

// [Is_Terminated]
IF NOT ISNULL([TERM_DATE]) THEN 1 ELSE 0 END

// [Tenure_Months]
DATEDIFF('month', [HIRE_DATE], IFNULL([TERM_DATE], TODAY()))

// [Tenure_Band]
IF [Tenure_Months] < 12 THEN '< 1 Year'
ELSEIF [Tenure_Months] <= 36 THEN '1 - 3 Years'
ELSE '3+ Years'
END

// [Annual_Turnover_Rate]
SUM([Is_Terminated]) / COUNTD([EMP_ID])
```

---

## 4. Dashboard 1: "Attendance Anomaly Dashboard"

Target: 4 views arranged in a clean 2x2 grid with top KPI banner.

### Worksheets to build:

#### Sheet 1.1: `KPI_Attendance_Banner` (Stat Tiles)
- **Measures** on Text shelf:
  - `Total Anomalies`: `SUM([Anomaly_Flag])`
  - `Late Arrivals`: `SUM([Is_Late])`
  - `Missing Punches`: `SUM([Is_Missing_Punch])`
  - `Overtime Hours`: `ROUND(SUM([Overtime_Hours]), 0)`
- **Format**: Large bold numbers, recessive labels below.

#### Sheet 1.2: `Trend_Monthly_Anomalies` (Line Chart)
- **Columns**: `DAY` (Continuous Month, e.g. `MONTH(DAY)`)
- **Rows**: `SUM([Anomaly_Flag])`
- **Color**: Anomaly Type (`Measure Names`: Late vs Missing vs Overtime)
- **Marks**: Line (2px width), subtle circle markers.
- **Rule**: Single y-axis, no dual axis.

#### Sheet 1.3: `Anomalies_By_Department` (Horizontal Bar Chart)
- **Rows**: `DEPARTMENTS.NAME` (sorted descending by anomaly count)
- **Columns**: `SUM([Anomaly_Flag])`
- **Color**: Sequential blue ramp (`#1f77b4`), 4px rounded data ends.
- **Tooltip**: Dept name, anomaly count, % of total.

#### Sheet 1.4: `Anomaly_Heatmap_Day_Hour` (Punch Clock Matrix)
- **Columns**: `WEEKDAY(DAY)` (Mon, Tue, Wed, Thu, Fri)
- **Rows**: `HOUR(CLOCK_IN)`
- **Marks**: Square / Heatmap
- **Color**: `COUNT([ATT_ID])` with sequential single-hue ramp.

### Dashboard Layout:
- Canvas: **1366 x 768** fixed (standard enterprise ratio).
- Title: **Attendance Anomaly Monitor** (20pt bold, subtitle with date range).
- Top: KPI Banner (Sheet 1.1).
- Middle left: `Trend_Monthly_Anomalies` (Line).
- Middle right: `Anomalies_By_Department` (Horizontal bars).
- Bottom: `Anomaly_Heatmap_Day_Hour`.
- Top Filter Bar: Date Range (`DAY`), Department dropdown.

---

## 5. Dashboard 2: "Retention & Turnover Risk Dashboard"

Target: Strategic HR executive view.

### Worksheets to build:

#### Sheet 2.1: `KPI_Retention_Banner` (Stat Tiles)
- **Measures** on Text:
  - `Active Headcount`: `SUM([Is_Active])`
  - `Total Exits (All Time)`: `SUM([Is_Terminated])`
  - `Overall Turnover Rate`: `[Annual_Turnover_Rate]` (format as `0.0%`)
  - `Avg Tenure`: `ROUND(AVG([Tenure_Months]), 1)` + " mos"

#### Sheet 2.2: `Turnover_By_Department` (Bar Chart with Reference Line)
- **Rows**: `DEPARTMENTS.NAME` (sorted descending by turnover rate)
- **Columns**: `[Annual_Turnover_Rate]`
- **Color**: Diverging or status threshold (e.g. gray if <10%, warm alert if >10%).
- **Analytics Pane**: Add Average Reference Line across departments.

#### Sheet 2.3: `Hires_vs_Exits_Trend` (Side-by-side or Over-Time Area)
- **Columns**: `MONTH(HIRE_DATE)`
- **Rows**: `COUNTD(EMP_ID)`
- **Color / Split**: Two separate rows or side-by-side:
  - Net additions per month.

#### Sheet 2.4: `Risk_By_Tenure_Band` (Segmented / Stacked Bar)
- **Rows**: `[Tenure_Band]` (`< 1 Year`, `1 - 3 Years`, `3+ Years`)
- **Columns**: `COUNTD(EMP_ID)`
- **Color**: `TERM_DATE` status (Active vs Exited)
- **Insight**: Identifies whether resignation spikes in first year vs mid-career.

### Dashboard Layout:
- Canvas: **1366 x 768** fixed.
- Title: **Retention & Turnover Risk Analysis** (20pt bold).
- Top: KPI Banner (Sheet 2.1).
- Middle left: `Turnover_By_Department` (Bar).
- Middle right: `Risk_By_Tenure_Band`.
- Bottom: `Hires_vs_Exits_Trend`.
- Top Filter Bar: Department, Role Level, Year.

---

## 6. Publish & Verification Steps

1. In Tableau Web Authoring:
   - Click **File** → **Save As**.
   - Name: `HR_Analytics_Demo`.
   - Project: `default`.
   - Embed credentials in data source: **Yes** (so the extract stays self-contained and viewers don't re-enter Snowflake password).
2. Click **Save**.
3. We verify via MCP from here:
   - Run `list-workbooks` → `HR_Analytics_Demo` should appear.
   - Run `list-views` → the 2 dashboards will be enumerated.
   - Run `get-view-image` → Claude captures and verifies the rendered visuals!
