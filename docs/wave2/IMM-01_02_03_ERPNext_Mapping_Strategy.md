# IMM-01 / IMM-02 / IMM-03 — ERPNext Mapping Strategy

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | ERPNext Extension & DocType Mapping — Wave 2 Planning Block |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |
| Nguồn context | IMM-01_02_03_BA_Business_Analysis.md · Sync_State_Step1.md · D1–D7 Decisions |
| Frappe Module | `imm_planning` (mới) |
| Constraint | Extend only — KHÔNG modify Wave 1 core |

---

## PHẦN 0 — AUDIT THỰC TRẠNG CODEBASE

### Kết quả scan (2026-04-22)

| DocType | Path | Trạng thái | Ghi chú |
|---|---|---|---|
| `Needs Assessment` | `assetcore/doctype/needs_assessment/` | **EXISTS** — JSON + .py | Đủ fields BA, có lifecycle_events embedded |
| `Procurement Plan` | `assetcore/doctype/procurement_plan/` | **EXISTS** — JSON | Đủ fields BA |
| `Procurement Plan Item` | `assetcore/doctype/procurement_plan_item/` | **EXISTS** — JSON | Có `por_reference` Link, thiếu status "Ordered" |
| `Purchase Order Request` | `assetcore/doctype/purchase_order_request/` | **STUB** — dir trống | Cần tạo JSON + .py |
| `Technical Specification` | — | **MISSING** | Tạo mới |
| `Vendor Evaluation` | — | **MISSING** | Tạo mới |
| `Vendor Evaluation Item` | — | **MISSING** | Tạo mới (child table) |
| `Asset Lifecycle Event` | `assetcore/assetcore/doctype/asset_lifecycle_event/` | **EXISTS** | Thiếu: `event_domain`, planning event_types |
| `IMM Device Model` | `assetcore/assetcore/doctype/imm_device_model/` | **EXISTS** | Thiếu: `nd98_class` field (D5) |

**Kết luận:** 3 DocTypes cần tạo mới, 1 DocType cần hoàn thiện, 2 DocType Wave 1 cần Custom Field injection.

---

## PHẦN 1 — MAPPING ERPNext CORE ↔ CUSTOM

### 1.1 Phán quyết thiết kế

| Nghiệp vụ | ERPNext Core | Quyết định | Lý do |
|---|---|---|---|
| Nhu cầu thiết bị | — | **Custom DocType** `Needs Assessment` | Không có analog trong core ERPNext |
| Kế hoạch ngân sách | `Budget` module (ERPNext) | **Custom DocType** `Procurement Plan` | ERPNext Budget quá tài chính, không đủ HTM governance |
| Nhà cung cấp | `Supplier` (ERPNext core) | **Link tới core** — không tạo lại | Tránh duplicate master data |
| Đặc tả kỹ thuật | `Item` (ERPNext) | **Custom DocType** `Technical Specification` | Item chỉ lưu catalog, không lưu evaluation criteria |
| Đánh giá vendor | `Supplier Scorecard` (ERPNext) | **Custom DocType** `Vendor Evaluation` | Supplier Scorecard thiếu: regulatory_class, NĐ98, weighted scoring |
| Yêu cầu mua sắm | `Purchase Order` (ERPNext) | **Custom DocType** `Purchase Order Request` | PO trong ERPNext là sau khi đã quyết định; POR là trước — cần approval gate riêng |
| Audit trail | `Asset Lifecycle Event` (Wave 1) | **Extend via Custom Field** | Thêm `event_domain` — không tạo DocType mới (D2) |
| Device catalog | `IMM Device Model` (Wave 1) | **Extend via Custom Field** | Thêm `nd98_class` — không sửa core JSON (D5) |

### 1.2 Quan hệ với ERPNext Core DocTypes

```
Needs Assessment ──────────────────▶ AC Department (Link)
Needs Assessment ──────────────────▶ IMM Device Model (Link, optional)
Needs Assessment ──────────────────▶ User (Link: requested_by)
Procurement Plan Item ─────────────▶ Needs Assessment (Link)
Procurement Plan Item ─────────────▶ IMM Device Model (Link, optional)
Procurement Plan Item ─────────────▶ Purchase Order Request (Link: por_reference)
Technical Specification ───────────▶ Procurement Plan Item (Link)
Technical Specification ───────────▶ IMM Device Model (Link, optional)
Vendor Evaluation ─────────────────▶ Technical Specification (Link)
Vendor Evaluation Item ────────────▶ Supplier / AC Supplier (Link: vendor)
Purchase Order Request ────────────▶ Procurement Plan Item (Link)
Purchase Order Request ────────────▶ Vendor Evaluation (Link)
Purchase Order Request ────────────▶ Technical Specification (Link)
Purchase Order Request ────────────▶ AC Supplier (Link: vendor)
Purchase Order Request ────────────▶ User (Link: approved_by)
Tất cả Document DocTypes ──────────▶ Asset Lifecycle Event (inline child table)
```

---

## PHẦN 2 — FIELD MAPPING TABLES

> Format: `field_name | Fieldtype | Options/Linked DocType | Required(Y/N)`
> `[CALC]` = calculated field (set in controller, not user input)
> `[AUTO]` = set automatically (frappe.session.user, today(), etc.)
> `[WF]` = managed by Frappe Workflow engine

---

### 2.1 DocType: `Needs Assessment`
**Type:** Document | **Submittable:** Yes | **Naming:** `NA-.YY.-.MM.-.#####`
**Module:** imm_planning | **Status:** EXISTS — verify fields below

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `naming_series` | Select | `NA-.YY.-.MM.-.#####` | Y |
| `requesting_dept` | Link | AC Department | Y |
| `request_date` | Date | — | Y `[AUTO]` |
| `requested_by` | Link | User | Y `[AUTO]` |
| `equipment_type` | Data | — | Y |
| `linked_device_model` | Link | IMM Device Model | N |
| `quantity` | Int | — | Y |
| `priority` | Select | Critical\nHigh\nMedium\nLow | Y |
| `estimated_budget` | Currency | — | Y |
| `current_equipment_age` | Int | — | N |
| `failure_frequency` | Select | Never\nRarely\nMonthly\nWeekly\nDaily | N |
| `clinical_justification` | Text Editor | — | Y |
| `status` | Select | Draft\nSubmitted\nUnder Review\nApproved\nRejected\nPlanned | N `[WF]` |
| `htmreview_notes` | Text | — | N |
| `finance_notes` | Text | — | N |
| `approved_budget` | Currency | — | N |
| `reject_reason` | Text | — | N |
| `lifecycle_events` | Table | Asset Lifecycle Event | N |
| **[THÊM MỚI]** `planning_snapshot` | Table | IMM Planning Device Snapshot | N |

> **D1 Resolution:** `IMM Planning Device Snapshot` child table lưu copy thông tin Device Model tại thời điểm tạo NA — tránh mất data nếu Model thay đổi sau này.

---

### 2.2 DocType: `IMM Planning Device Snapshot` *(Child Table mới)*
**Type:** Child Table | **Module:** imm_planning

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `snapshot_date` | Datetime | — | Y `[AUTO]` |
| `model_name` | Data | — | Y |
| `manufacturer` | Data | — | N |
| `medical_device_class` | Data | — | N |
| `nd98_class` | Data | — | N |
| `gmdn_code` | Data | — | N |
| `risk_classification` | Data | — | N |
| `expected_lifespan_years` | Int | — | N |

---

### 2.3 DocType: `Procurement Plan`
**Type:** Document | **Submittable:** Yes | **Naming:** `PP-.YY.-.#####`
**Module:** imm_planning | **Status:** EXISTS — verify fields below

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `naming_series` | Select | `PP-.YY.-.#####` | Y |
| `plan_year` | Int | — | Y |
| `approved_budget` | Currency | — | Y |
| `allocated_budget` | Currency | — | N `[CALC]` |
| `remaining_budget` | Currency | — | N `[CALC]` |
| `status` | Select | Draft\nUnder Review\nApproved\nBudget Locked | N `[WF]` |
| `approved_by` | Link | User | N |
| `approval_date` | Date | — | N |
| `approval_notes` | Text | — | N |
| `items` | Table | Procurement Plan Item | N |
| `lifecycle_events` | Table | Asset Lifecycle Event | N |

> **Constraint BR-02-01:** Unique index trên `plan_year` khi status IN ('Approved','Budget Locked') — enforce trong `validate()` controller.

---

### 2.4 DocType: `Procurement Plan Item` *(Child Table)*
**Type:** Child Table | **Module:** imm_planning | **Status:** EXISTS — cần patch `status` options

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `needs_assessment` | Link | Needs Assessment | N |
| `device_model` | Link | IMM Device Model | N |
| `equipment_description` | Data | — | Y |
| `quantity` | Int | — | Y |
| `estimated_unit_cost` | Currency | — | Y |
| `total_cost` | Currency | — | N `[CALC]` |
| `priority` | Select | Critical\nHigh\nMedium\nLow | Y |
| `planned_quarter` | Select | Q1\nQ2\nQ3\nQ4 | N |
| `vendor_shortlist` | Text | — | N |
| `status` | Select | **Pending\nPO Raised\nOrdered\nDelivered\nCancelled** | N |
| `por_reference` | Link | Purchase Order Request | N |

> **Patch cần thiết:** Thêm status option `"Ordered"` vào Select field — hiện tại thiếu so với BA spec.

---

### 2.5 DocType: `Technical Specification` *(Tạo mới)*
**Type:** Document | **Submittable:** Yes | **Naming:** `TS-.YY.-.#####`
**Module:** imm_planning | **Status:** MISSING — tạo mới

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `naming_series` | Select | `TS-.YY.-.#####` | Y |
| `linked_plan_item` | Link | Procurement Plan Item | Y |
| `procurement_plan` | Link | Procurement Plan | Y |
| `device_model` | Link | IMM Device Model | N |
| `equipment_description` | Data | — | Y |
| `performance_requirements` | Text Editor | — | Y |
| `safety_standards` | Text | — | Y |
| `regulatory_class` | Select | **Class A\nClass B\nClass C\nClass D** | Y |
| `mdd_class` | Select | Class I\nClass II\nClass III | N |
| `accessories_included` | Text | — | N |
| `warranty_terms` | Data | — | N |
| `expected_delivery_weeks` | Int | — | N |
| `installation_requirements` | Text | — | N |
| `training_requirements` | Text | — | N |
| `reference_standard` | Data | — | N |
| `status` | Select | Draft\nUnder Review\nApproved\nRevised | N `[WF]` |
| `reviewed_by` | Link | User | N |
| `review_date` | Date | — | N |
| `review_notes` | Text | — | N |
| `lifecycle_events` | Table | Asset Lifecycle Event | N |

> **D5 Resolution:** `regulatory_class` dùng NĐ98/2021 Phụ lục II (A/B/C/D). `mdd_class` optional cho tương thích quốc tế.

---

### 2.6 DocType: `Vendor Evaluation` *(Tạo mới)*
**Type:** Document | **Submittable:** Yes | **Naming:** `VE-.YY.-.#####`
**Module:** imm_planning | **Status:** MISSING — tạo mới

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `naming_series` | Select | `VE-.YY.-.#####` | Y |
| `linked_technical_spec` | Link | Technical Specification | Y |
| `linked_plan_item` | Link | Procurement Plan Item | Y `[AUTO from TS]` |
| `evaluation_date` | Date | — | Y |
| `evaluation_method` | Select | RFQ\nTender\nDirect | Y |
| `items` | Table | Vendor Evaluation Item | Y |
| `recommended_vendor` | Link | AC Supplier | N |
| `selection_justification` | Text | — | N |
| `committee_members` | Text | — | N |
| `status` | Select | Draft\nIn Progress\nApproved\nCancelled | N `[WF]` |
| `approved_by` | Link | User | N |
| `approval_date` | Date | — | N |
| `lifecycle_events` | Table | Asset Lifecycle Event | N |

---

### 2.7 DocType: `Vendor Evaluation Item` *(Child Table mới)*
**Type:** Child Table | **Module:** imm_planning

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `vendor` | Link | AC Supplier | Y |
| `vendor_name` | Data | — | N `[AUTO fetch]` |
| `quoted_price` | Currency | — | N |
| `technical_score` | Float | — | Y |
| `financial_score` | Float | — | Y |
| `profile_score` | Float | — | Y |
| `risk_score` | Float | — | Y |
| `total_score` | Float | — | N `[CALC: tech×0.4+fin×0.3+profile×0.2+risk×0.1]` |
| `score_band` | Select | A (≥8)\nB (6–7.9)\nC (4–5.9)\nD (<4) | N `[CALC]` |
| `compliant_with_ts` | Check | — | Y |
| `has_nd98_registration` | Check | — | Y |
| `notes` | Text | — | N |
| `is_recommended` | Check | — | N |

> **D4 Resolution:** Float 0–10 per criterion + weighted `total_score` + derived `score_band` — cả hai được tính trong controller Python. Band thêm vào để UI filter dễ.

---

### 2.8 DocType: `Purchase Order Request` *(Hoàn thiện stub)*
**Type:** Document | **Submittable:** Yes | **Naming:** `POR-.YY.-.#####`
**Module:** imm_planning | **Status:** STUB (dir trống) — tạo JSON + .py

| field_name | Fieldtype | Options / Linked DocType | Required |
|---|---|---|---|
| `naming_series` | Select | `POR-.YY.-.#####` | Y |
| `linked_plan_item` | Link | Procurement Plan Item | Y |
| `linked_evaluation` | Link | Vendor Evaluation | Y |
| `linked_technical_spec` | Link | Technical Specification | Y |
| `procurement_plan` | Link | Procurement Plan | Y `[AUTO from PP Item]` |
| `vendor` | Link | AC Supplier | Y |
| `vendor_name` | Data | — | N `[AUTO fetch]` |
| `equipment_description` | Data | — | Y |
| `quantity` | Int | — | Y |
| `unit_price` | Currency | — | Y |
| `total_amount` | Currency | — | N `[CALC: qty × unit_price]` |
| `currency` | Link | Currency | N |
| `delivery_terms` | Data | — | N |
| `payment_terms` | Data | — | N |
| `expected_delivery_date` | Date | — | N |
| `warranty_period_months` | Int | — | N |
| `requires_director_approval` | Check | — | N `[CALC: total>500M]` |
| `status` | Select | Draft\nUnder Review\nApproved\nReleased\nFulfilled\nCancelled | N `[WF]` |
| `approved_by` | Link | User | N |
| `approval_date` | Date | — | N |
| `release_date` | Date | — | N |
| `released_by` | Link | User | N |
| `cancellation_reason` | Text | — | N |
| `lifecycle_events` | Table | Asset Lifecycle Event | N |

> **D7 Resolution:** Khi `status → Released`, controller chỉ ghi `Asset Lifecycle Event` với event_domain=`imm_planning`, event_type=`por_released` + gọi `frappe.enqueue()` để async notify — KHÔNG tạo Commissioning Record.

---

## PHẦN 3 — CUSTOM FIELDS INJECTION VÀO WAVE 1

> Tất cả Custom Fields dưới đây được khai báo trong `fixtures/custom_fields.json`
> của module `imm_planning`. KHÔNG sửa trực tiếp Wave 1 DocType JSON files.

### 3.1 Custom Fields → `Asset Lifecycle Event`

| Tên field | Fieldtype | Options | Required | Lý do (Decision) |
|---|---|---|---|---|
| `event_domain` | Select | `imm_master`\n`imm_deployment`\n`imm_operations`\n`imm_planning`\n`imm_eol` | N | **D2** — phân biệt nguồn gốc event, tránh trộn lẫn Planning vs Operations |

> **Cách thêm options cho `event_type`:** Tạo Custom Field override `event_type` với đủ options Planning:
> `needs_assessment_created`, `submitted_for_review`, `technical_review_started`,
> `needs_assessment_approved`, `needs_assessment_rejected`, `linked_to_procurement_plan`,
> `procurement_plan_created`, `item_added_to_plan`, `plan_submitted_for_review`,
> `plan_approved`, `budget_locked`, `po_request_raised`,
> `technical_spec_created`, `technical_spec_approved`,
> `vendor_evaluation_started`, `vendor_selected`,
> `purchase_order_request_created`, `por_approved`, `por_released`

### 3.2 Custom Fields → `IMM Device Model`

| Tên field | Fieldtype | Options | Required | Lý do (Decision) |
|---|---|---|---|---|
| `nd98_class` | Select | `\nClass A\nClass B\nClass C\nClass D` | N | **D5** — NĐ98/2021 Phụ lục II classification, bổ sung bên cạnh `medical_device_class` (MDD) đã có |
| `vn_registration_number` | Data | — | N | Số đăng ký Bộ Y Tế Việt Nam — cần cho VR-03-02 |

### 3.3 Custom Fields tổng hợp (fixtures file)

```python
# assetcore/imm_planning/fixtures/custom_fields.json (mẫu cấu trúc)
[
  {
    "doctype": "Custom Field",
    "dt": "Asset Lifecycle Event",
    "fieldname": "event_domain",
    "fieldtype": "Select",
    "options": "imm_master\nimm_deployment\nimm_operations\nimm_planning\nimm_eol",
    "label": "Event Domain",
    "insert_after": "event_type"
  },
  {
    "doctype": "Custom Field",
    "dt": "IMM Device Model",
    "fieldname": "nd98_class",
    "fieldtype": "Select",
    "options": "\nClass A\nClass B\nClass C\nClass D",
    "label": "Phân loại NĐ98 (A/B/C/D)",
    "insert_after": "medical_device_class"
  },
  {
    "doctype": "Custom Field",
    "dt": "IMM Device Model",
    "fieldname": "vn_registration_number",
    "label": "Số đăng ký BYT",
    "fieldtype": "Data",
    "insert_after": "nd98_class"
  }
]
```

---

## PHẦN 4 — ROLES MỚI CẦN TẠO

> Tạo trong `assetcore/imm_planning/fixtures/roles.json` — KHÔNG sửa Wave 1 roles.

| Role Name | Mô tả | Quyền chính |
|---|---|---|
| `IMM Technical Reviewer` | Thành viên Hội đồng Kỹ thuật — đánh giá TS, VE | Read/Review: TS, VE; Submit: VE |
| `IMM Finance Officer` | Cán bộ Tài chính — xem xét giá thầu, POR | Read: PP, VE; Submit: POR (≤500M) |

---

## PHẦN 5 — PERMISSION MATRIX CHO WAVE 2 DocTypes

| DocType | Clinical User | Dept Head | Ops Manager | Tech Reviewer | Finance Officer | Sys Admin |
|---|---|---|---|---|---|---|
| `Needs Assessment` | CR | CRW**S** | CRWS | R | R | All |
| `Procurement Plan` | — | R | CRW**S** | R | R | All |
| `Procurement Plan Item` | — | R | CRW | R | R | All |
| `Technical Specification` | — | R | CRW**S** | CRW**S** | R | All |
| `Vendor Evaluation` | — | R | CRW | CRW**S** | CRWS | All |
| `Purchase Order Request` | — | **Approve (>500M)** | CRWS | R | CRW**S** (≤500M) | All |

> **S** = Submit quyền (bao gồm trigger workflow transition)

---

## PHẦN 6 — CONTROLLER PATTERN (Python)

### 6.1 Pattern chuẩn cho mọi DocType Wave 2

```python
# assetcore/imm_planning/doctype/[name]/[name].py
import frappe
from frappe import _
from frappe.model.document import Document

class [DocTypeName](Document):

    def validate(self) -> None:
        """Chạy mọi Validation Rule trước khi save."""
        self._validate_[rule_1]()
        self._validate_[rule_2]()

    def before_submit(self) -> None:
        """Gate check cuối trước khi submit."""
        self._validate_submit_requirements()

    def on_submit(self) -> None:
        """Post-submit: audit trail + downstream triggers."""
        self._log_lifecycle_event("document_submitted", self.status)
        self._trigger_downstream()

    def _log_lifecycle_event(
        self, event_type: str, to_status: str, notes: str = ""
    ) -> None:
        event = frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "event_type": event_type,
            "event_domain": "imm_planning",   # D2
            "timestamp": frappe.utils.now(),
            "actor": frappe.session.user,
            "from_status": self.status,
            "to_status": to_status,
            "root_doctype": self.doctype,
            "root_record": self.name,
            "notes": notes,
        })
        self.append("lifecycle_events", event.as_dict())
```

### 6.2 Controller đặc thù: `Vendor Evaluation`

```python
def _calculate_scores(self) -> None:
    """D4: weighted scoring 40/30/20/10."""
    for item in self.items:
        item.total_score = (
            (item.technical_score or 0) * 0.40
            + (item.financial_score or 0) * 0.30
            + (item.profile_score or 0) * 0.20
            + (item.risk_score or 0) * 0.10
        )
        score = item.total_score
        item.score_band = (
            "A (≥8)" if score >= 8 else
            "B (6–7.9)" if score >= 6 else
            "C (4–5.9)" if score >= 4 else
            "D (<4)"
        )
```

### 6.3 Controller đặc thù: `Purchase Order Request`

```python
def validate(self) -> None:
    self._calc_total_amount()
    self._check_budget_variance()        # VR-03-06
    self._check_director_threshold()     # BR-03-01

def _check_director_threshold(self) -> None:
    """D6: tự set cờ requires_director_approval."""
    self.requires_director_approval = (
        1 if (self.total_amount or 0) > 500_000_000 else 0
    )

def on_submit(self) -> None:
    self._log_lifecycle_event("por_released", "Released")
    self._update_plan_item_status()      # PP Item → Ordered
    frappe.enqueue(                      # D6: async notify
        "assetcore.imm_planning.utils.notify_imm04_readiness",
        queue="default",
        por_name=self.name,
    )
```

---

## PHẦN 7 — NAMING SERIES MỚI

```python
# Bổ sung vào hooks.py scheduler_events section (không override)
# Đây là naming series cho 5 DocType Wave 2:

NA-.YY.-.MM.-.#####     → Needs Assessment       (đã có)
PP-.YY.-.#####          → Procurement Plan        (đã có)
TS-.YY.-.#####          → Technical Specification (mới)
VE-.YY.-.#####          → Vendor Evaluation       (mới)
POR-.YY.-.#####         → Purchase Order Request  (mới)
```

---

## PHẦN 8 — FILE STRUCTURE CẦN TẠO

```
assetcore/
├── imm_planning/                            ← Frappe module mới
│   ├── __init__.py
│   ├── doctype/
│   │   ├── technical_specification/
│   │   │   ├── technical_specification.json
│   │   │   ├── technical_specification.py
│   │   │   ├── technical_specification.js
│   │   │   └── test_technical_specification.py
│   │   ├── vendor_evaluation/
│   │   │   ├── vendor_evaluation.json
│   │   │   ├── vendor_evaluation.py
│   │   │   ├── vendor_evaluation.js
│   │   │   └── test_vendor_evaluation.py
│   │   ├── vendor_evaluation_item/
│   │   │   └── vendor_evaluation_item.json  ← child table only
│   │   └── imm_planning_device_snapshot/
│   │       └── imm_planning_device_snapshot.json ← child table (D1)
│   ├── fixtures/
│   │   ├── custom_fields.json               ← inject vào Wave 1
│   │   └── roles.json                       ← 2 roles mới
│   └── utils/
│       └── notify_imm04_readiness.py        ← D6 async handler
│
└── doctype/                                 ← path hiện tại
    └── purchase_order_request/
        ├── purchase_order_request.json      ← hoàn thiện stub
        ├── purchase_order_request.py
        ├── purchase_order_request.js
        └── test_purchase_order_request.py
```

> **Lưu ý path duality:** `needs_assessment`, `procurement_plan`, `procurement_plan_item`
> đang nằm tại `assetcore/doctype/` (không phải `imm_planning/doctype/`).
> Wave 2 sẽ đặt DocType mới vào `imm_planning/` để consistent với module naming.
> POR là ngoại lệ: hoàn thiện tại `assetcore/doctype/` vì stub đã tồn tại đó.

---

## PHẦN 9 — WORKFLOW DEFINITIONS (tóm tắt)

| Workflow | DocType | States | Transition Roles |
|---|---|---|---|
| `Needs Assessment Workflow` | Needs Assessment | Draft→Submitted→Under Review→Approved/Rejected→Planned | Dept Head\|Ops Manager\|Finance Officer |
| `Procurement Plan Workflow` | Procurement Plan | Draft→Under Review→Approved→Budget Locked | Ops Manager\|Dept Head\|Finance Officer |
| `Technical Spec Workflow` | Technical Specification | Draft→Under Review→Approved | Ops Manager\|Tech Reviewer |
| `Vendor Evaluation Workflow` | Vendor Evaluation | Draft→In Progress→Approved→Cancelled | Ops Manager\|Tech Reviewer\|Finance Officer |
| `POR Workflow` | Purchase Order Request | Draft→Under Review→Approved→Released→Fulfilled/Cancelled | Finance Officer\|Ops Manager\|Dept Head (>500M) |

---

*Tài liệu này là đầu vào cho:*
*`IMM-01_02_03_Technical_Design.md` (Step 3)*
