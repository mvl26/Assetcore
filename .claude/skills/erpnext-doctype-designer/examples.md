# ERPNext DocType Designer — Examples

## Example 1: Maintenance Plan (IMM-08)

**Input:** `Maintenance Plan for IMM-08 PM scheduling`

```text
DocType: Maintenance Plan
Module: AssetCore
Naming: MP-.YYYY.-.#####
Is Submittable: Yes
```

Field list (excerpt):

| # | fieldname | fieldtype | label | reqd |
| --- | --- | --- | --- | --- |
| 1 | asset_ref | Link→Asset | Thiết bị | Yes |
| 2 | plan_type | Select | Loại PM | Yes |
| 3 | frequency | Select | Chu kỳ | Yes |
| 4 | next_due_date | Date | Ngày PM tiếp theo | Yes |
| 5 | assigned_tech | Link→User | Kỹ thuật viên | No |
| 6 | sla_deadline | Date | Hạn SLA | No |
| 7 | sla_status | Select | Trạng thái SLA | No |
| 8 | tasks | Table→PM Task | Hạng mục kiểm tra | No |

Workflow: `Active → Work Order Created → Completed → Overdue`

---

## Example 2: Asset Commissioning (IMM-04)

**Input:** `Asset Commissioning record for installation`

Key fields: `po_reference→Purchase Order`, `master_item→Item`, `vendor→Supplier`,
`clinical_dept→Department`, `installation_date`, `vendor_serial_no`, `asset_tag`,
`qr_value`, `commissioned_by→User`, `workflow_state`

Naming: `ACC-.YYYY.-.#####`

Workflow: `Draft → Pending Approval → Approved → Commissioned → Cancelled`

---

## Example 3: Incident Report (IMM-12 Corrective)

**Input:** `Incident Report for equipment failure`

Key fields:

- `asset_ref` → Asset
- `incident_type` (Select: Equipment Failure / Software Error / Human Error / Other)
- `reported_by` → User
- `severity` (Select: Low / Medium / High / Critical)
- `description` (Text)
- `root_cause` (Text)
- `corrective_action` (Text)
- `linked_work_order` → Work Order

SLA: Critical = 4h response, High = 24h, Medium = 72h

Workflow: `Reported → Under Investigation → Root Cause Identified → Closed → Cancelled`
