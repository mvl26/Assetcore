# IMM-02 — API Interface

| Base URL | `/api/method/assetcore.api.imm02` |
|---|---|

## Endpoints

### POST create_procurement_plan
```json
{"plan_year": 2027, "approved_budget": 5000000000}
```
Response: `{"success": true, "data": {"name": "PP-27-00001", "status": "Draft"}}`

### POST add_item
```json
{
  "plan_name": "PP-27-00001",
  "needs_assessment": "NA-26-04-00001",
  "device_model": "DM-00001",
  "quantity": 2,
  "estimated_unit_cost": 500000000,
  "priority": "High",
  "planned_quarter": "Q2"
}
```

### GET get_procurement_plan
`?name=PP-27-00001` → Full document

### GET list_procurement_plans
`?year=2027&status=Approved`

### POST approve_plan
```json
{"name": "PP-27-00001", "notes": "Phê duyệt theo nghị quyết BGĐ số 05/2027"}
```

### POST lock_budget
```json
{"name": "PP-27-00001"}
```

### GET get_dashboard_stats
`?year=2027`
```json
{
  "success": true,
  "data": {
    "total_items": 12,
    "approved_budget": 5000000000,
    "allocated_budget": 4200000000,
    "budget_utilization": 84.0,
    "items_by_status": {"Pending": 8, "PO Raised": 3, "Delivered": 1},
    "items_by_priority": {"Critical": 2, "High": 5, "Medium": 4, "Low": 1}
  }
}
```
