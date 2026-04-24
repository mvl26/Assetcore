# IMM-02 — Kế Hoạch Mua Sắm (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Kế Hoạch Mua Sắm |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-21 |
| Trạng thái | Wave 2 — In Development |

---

## 1. Mục đích

IMM-02 tổng hợp các nhu cầu đã phê duyệt (IMM-01) thành **kế hoạch mua sắm hàng năm** với ngân sách được phân bổ và ưu tiên hóa. Là cầu nối giữa planning (IMM-01) và procurement execution (IMM-03).

---

## 2. Vị trí trong kiến trúc

```
IMM-01 Approved NAs  ──────▶  IMM-02 Procurement Plan  ──────▶  IMM-03 PO Request
                              (annual budget lock)
```

---

## 3. DocTypes

| DocType | Naming | Submittable |
|---|---|---|
| `Procurement Plan` | `PP-.YY.-.#####` | Yes |
| `Procurement Plan Item` | (child) | No |

### Fields — Procurement Plan

| Field | Type | Mô tả |
|---|---|---|
| plan_year | Int | Năm kế hoạch |
| approved_budget | Currency | Tổng ngân sách được phê duyệt |
| allocated_budget | Currency | Tổng đã phân bổ (tổng từ items) |
| remaining_budget | Currency | = approved_budget - allocated_budget |
| status | Select | Draft/Under Review/Approved/Budget Locked |
| approved_by | Link → User | |
| items | Table → Procurement Plan Item | Danh sách thiết bị cần mua |

### Fields — Procurement Plan Item (child)

| Field | Type | Mô tả |
|---|---|---|
| needs_assessment | Link → Needs Assessment | Phiếu NA nguồn gốc |
| device_model | Link → IMM Device Model | |
| equipment_description | Data | |
| quantity | Int | |
| estimated_unit_cost | Currency | |
| total_cost | Currency | = qty × unit_cost |
| priority | Select | Critical/High/Medium/Low |
| planned_quarter | Select | Q1/Q2/Q3/Q4 |
| vendor_shortlist | Text | Nhà cung cấp đề xuất |
| status | Select | Pending/PO Raised/Delivered/Cancelled |

---

## 4. Workflow

| Từ | Hành động | Đến | Actor |
|---|---|---|---|
| Draft | Gửi xem xét | Under Review | HTM Manager |
| Under Review | Phê duyệt kế hoạch | Approved | VP Block2 |
| Approved | Khóa ngân sách | Budget Locked | Finance Director |
| Budget Locked | Tạo PO | (trigger IMM-03) | HTM Manager |

---

## 5. KPIs

| KPI | Mô tả |
|---|---|
| Budget utilization | allocated_budget / approved_budget × 100 |
| Items by priority | Count Critical/High/Medium/Low |
| Items by status | Count by status |
| Quarterly distribution | Sum cost per quarter |
