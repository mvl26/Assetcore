# IMM-02 — Technical Design

## 1. DocType Schema

### Procurement Plan
```
autoname: PP-.YY.-.#####
module: Assetcore
is_submittable: 1
track_changes: 1

Fields:
- plan_year (Int, reqd)
- approved_budget (Currency, reqd)
- allocated_budget (Currency, read_only — computed)
- remaining_budget (Currency, read_only — computed)
- status (Select: Draft/Under Review/Approved/Budget Locked)
- approved_by (Link → User)
- approval_date (Date)
- approval_notes (Text)
- items (Table → Procurement Plan Item)
- lifecycle_events (Table → Asset Lifecycle Event)
```

### Procurement Plan Item (child)
```
Fields:
- needs_assessment (Link → Needs Assessment)
- device_model (Link → IMM Device Model)
- equipment_description (Data, reqd)
- quantity (Int, reqd, default 1)
- estimated_unit_cost (Currency, reqd)
- total_cost (Currency, read_only — = qty × unit_cost)
- priority (Select: Critical/High/Medium/Low, reqd)
- planned_quarter (Select: Q1/Q2/Q3/Q4)
- vendor_shortlist (Text)
- status (Select: Pending/PO Raised/Delivered/Cancelled, default Pending)
- por_reference (Link → Purchase Order Request)
```

---

## 2. Service Logic

```python
def validate_procurement_plan(doc):
    # Recalculate allocated_budget = SUM(items.total_cost)
    # Recalculate remaining_budget = approved - allocated
    # VR-02-01: allocated ≤ approved
    # VR-02-03: linked NAs must be Approved status

def calculate_totals(doc):
    # For each item: item.total_cost = item.quantity × item.estimated_unit_cost
    # doc.allocated_budget = SUM(item.total_cost)
    # doc.remaining_budget = doc.approved_budget - doc.allocated_budget
```

---

## 3. Workflow Transitions

| From | To | Action | Guard |
|---|---|---|---|
| Draft | Under Review | submit_for_review | len(items) > 0 |
| Under Review | Approved | approve_plan | VR-02-01 |
| Approved | Budget Locked | lock_budget | Finance Director role |
