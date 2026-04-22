---
name: dashboard-spec-writer
description: Write complete dashboard specifications for AssetCore IMM modules — KPIs, charts, alerts, backend APIs, frontend component structure
type: skill
---

# Dashboard Spec Writer — AssetCore

## What This Skill Does

Given an IMM module or domain area, produce a **complete, implementation-ready dashboard specification** covering KPIs, chart types, data sources, backend endpoints, and frontend component layout.

## Input

User provides one of:

- Module name: `"IMM-05 Document Repository dashboard"`
- Domain area: `"Fleet compliance cockpit"`
- Goal: `"Show PM compliance across all assets"`

## Output Format

### 1. Dashboard Overview

```text
Dashboard: <name>
Module: IMM-XX
Primary Actor: <role who views this>
Refresh: real-time / on-demand / scheduled (cron)
Access: Public / Internal Only
```

### 2. KPI Cards

For each KPI card:

| KPI | Label (VI) | Formula | Source DocType | Filter | Alert Threshold | Color |
|-----|------------|---------|----------------|--------|-----------------|-------|

Color guide: green = good, yellow = warning, red = critical.

### 3. Charts

For each chart:

```text
Chart: <name>
Type: Bar / Line / Pie / Donut / Heatmap
X-axis: <field or time dimension>
Y-axis: <metric>
Group by: <optional>
Filter: <default filter>
Drilldown: <what clicking a bar/slice does>
Backend query: SELECT ... FROM ... WHERE ...
```

### 4. Alert Rules

```text
Alert: <name>
Condition: <formula or threshold>
Severity: Info / Warning / Critical
Display: Banner / Badge / Toast
Action: Link to list / Detail view
```

### 5. Backend APIs Required

For each new endpoint needed:

```python
@frappe.whitelist()
def <function_name>(<params>) -> dict:
    """
    GET /api/method/assetcore.api.<module>.<function_name>
    Returns: {success, data: {...}}
    """
    # describe what the query returns
```

### 6. Frontend Component Structure

```text
<DashboardView>
  ├── <KpiGrid> — 4 KPI cards
  ├── <ChartRow>
  │   ├── <BarChart title="..." />
  │   └── <DonutChart title="..." />
  ├── <AlertBanner v-if="criticalCount > 0" />
  └── <DocumentTable> — paginated list with row actions
```

### 7. State Management (Pinia Store)

```typescript
// store/<module>.ts
interface <Module>State {
  kpis: <KpiType> | null
  chartData: <ChartData>[]
  alerts: Alert[]
  loading: boolean
  error: string | null
}
```

### 8. Performance Notes

- Which queries need indexes?
- Which data can be cached (and for how long)?
- Any heavy aggregation that should run as a scheduled task instead of on-demand?

## Design Principles

- Every KPI must link back to source data (drill-down)
- Red/amber/green status must match workflow states
- Dashboards display, they do not perform actions — actions go through Work Orders
- Mobile-friendly: KPI cards stack on small screens
- Always show "last updated" timestamp

## Step-by-Step Execution

1. Identify primary actor and decision they need to make
2. List 3–6 KPI cards (most important metrics first)
3. Design 1–3 charts that show trends or distributions
4. Define alert rules for actionable conditions
5. Map each KPI/chart to its backend query
6. Design backend API endpoints
7. Sketch frontend component tree
8. Note performance considerations
9. Output all sections in order
