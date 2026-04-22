# Dashboard Spec Writer — Examples

## Example 1: IMM-05 Document Compliance Dashboard

**Input:** `IMM-05 document compliance dashboard`

KPI Cards:

| KPI | Label | Formula | Alert Threshold |
| --- | --- | --- | --- |
| total_active | Tài liệu Active | COUNT(workflow_state='Active') | — |
| expiring_90d | Sắp hết hạn | COUNT(expiry_date ≤ today+90) | > 0 → yellow |
| expired | Đã hết hạn | COUNT(workflow_state='Expired') | > 0 → red |
| missing_docs | Thiết bị thiếu hồ sơ | COUNT(doc_completeness_pct < 100) | > 0 → red |

Charts:

```text
Chart: Expiry Timeline
Type: Bar
X-axis: Month (next 12 months)
Y-axis: COUNT(documents expiring that month)
Drilldown: Click month → filtered document list
```

```text
Chart: Compliance by Department
Type: Donut
Segments: Compliant / Expiring_Soon / Non-Compliant / Exempt
Drilldown: Click segment → asset list filtered by status
```

---

## Example 2: Fleet Maintenance Compliance Cockpit

**Input:** `Cross-module compliance overview for CMMS Admin`

KPI Cards:

| KPI | Label | Formula |
| --- | --- | --- |
| assets_active | Thiết bị đang vận hành | COUNT(Asset, docstatus=1) |
| pm_overdue | PM quá hạn | COUNT(MaintenancePlan, next_due_date < today) |
| calibration_due | Hiệu chuẩn sắp hết hạn | COUNT(calibration_expiry ≤ today+30) |
| open_incidents | Sự cố đang mở | COUNT(IncidentReport, workflow_state='Under Investigation') |

Alert Rules:

```text
Alert: Critical equipment without active PM plan
Condition: Asset.asset_criticality = 'Critical' AND no linked MaintenancePlan
Severity: Critical
Action: Link to /maintenance/create?asset=<name>
```

---

## Example 3: IMM-08 PM Performance Dashboard

Charts:

```text
Chart: PM Compliance Rate (12 months)
Type: Line
X-axis: Month
Y-axis: (completed_on_time / scheduled) × 100
Target line: 95%
```

KPIs: PM On-Time Rate, Average Days Overdue, Technician Utilization %, Assets Never PM'd
