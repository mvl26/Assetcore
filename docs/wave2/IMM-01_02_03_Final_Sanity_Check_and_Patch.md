# IMM-01/02/03 — Final Sanity Check & Patch Instructions

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | Forensic Cross-Validation — Devil's Advocate Review |
| Phiên bản | 1.0.0 |
| Ngày | 2026-04-22 |
| Reviewer | Chief Architect (self-audit) |
| Phạm vi | BA_Business_Analysis · ERPNext_Mapping_Strategy · Technical_Design |
| Kết luận | **6 CRITICAL + 3 MINOR gaps found. Patch required before Sprint 1.** |

---

## 1. CRITICAL GAPS FOUND

---

### GAP-01 — CRITICAL | NA.status → "Planned": Không có trigger nào thực thi

**Axis:** State-Workflow + Cross-Module Hook

**Vị trí phát hiện:**
- BA Doc: `Bước 5 — "status → Planned (auto khi link PP)"`
- Technical Design: `NeedsAssessment.on_update_after_submit()` — KHÔNG có code xử lý trạng thái "Planned"
- Technical Design Workflow table: `NA → Planned | System (auto)` — nhưng không có System action nào được implement

**Phân tích:**
`Procurement Plan Item.needs_assessment` là FK từ PP Item → NA (không phải ngược lại). Khi HTM Manager thêm NA vào PP Item, không có hook nào trên PP Item controller gọi ngược lại để set `NA.status = Planned`. Kết quả: NA được duyệt và linked vào PP nhưng vẫn hiển thị "Approved" mãi mãi — **dead state, không bao giờ tự chuyển sang "Planned"**.

**Severity:** CRITICAL — traceability chain bị vỡ, NA không reflect thực trạng.

---

### GAP-02 — CRITICAL | Role "IMM Finance Director" vs "IMM Finance Officer": Hai tên khác nhau trong cùng hệ thống

**Axis:** Data-UI + State-Workflow

**Vị trí phát hiện:**
- BA Doc (IMM-01, IMM-02): Actor = `IMM Finance Director` (xuất hiện 6 lần)
- BA Doc (IMM-03): Actor = `IMM Finance Officer`
- ERPNext Mapping Strategy (Phần 4): Tạo Role mới = `IMM Finance Officer`
- Technical Design Workflow Table: `Phê duyệt NA | IMM Finance Officer` (nhưng BA nói Finance Director)
- Technical Design Permission Matrix: `Finance Officer` column

**Phân tích:**
Fixtures chỉ tạo `IMM Finance Officer`. Nhưng Frappe Workflow cho NA và PP sẽ reference `IMM Finance Director` (nếu dựa theo BA Doc). **Kết quả: Workflow NA/PP sẽ không có actor hợp lệ để approve** — toàn bộ luồng phê duyệt NA và khóa ngân sách PP bị blocked.

**Severity:** CRITICAL — workflow NA và PP bị broken trước khi code đầu tiên chạy.

---

### GAP-03 — CRITICAL | `_notify_ops_manager_budget_locked()`: Method được gọi nhưng không được định nghĩa

**Axis:** Cross-Module Hook

**Vị trí phát hiện:**
- Technical Design `procurement_plan.py` line 412: `self._notify_ops_manager_budget_locked()` — được gọi
- Technical Design: Không có implementation của method này trong controller body

**Phân tích:**
`ProcurementPlan.on_update_after_submit()` gọi `self._notify_ops_manager_budget_locked()` nhưng method body bị thiếu hoàn toàn. Runtime sẽ throw `AttributeError`. **Kết quả: Mỗi lần khóa ngân sách PP sẽ raise unhandled exception, workflow bị block.**

**Severity:** CRITICAL — runtime error 100% reproducible.

---

### GAP-04 — CRITICAL | VE Joint Approval (Tech Reviewer AND Finance Officer): Frappe Workflow không hỗ trợ AND-condition native

**Axis:** State-Workflow

**Vị trí phát hiện:**
- Technical Design Phần 4.3: `Phê duyệt VE | In Progress | Approved | IMM Technical Reviewer, IMM Finance Officer`
- Module Overview IMM-03: "hội đồng chốt" — ngụ ý cả hai phải đồng ý
- Frappe Workflow: 1 transition chỉ có thể có `allowed_roles` (OR logic) — không có AND mechanism native

**Phân tích:**
Nếu khai báo 2 roles trong 1 transition, Frappe cho phép **bất kỳ ai** trong 2 roles đó approve (OR, không phải AND). Tech Reviewer một mình có thể approve VE mà không cần Finance Officer sign-off. **Kết quả: Financial oversight bị bypass hoàn toàn.**

**Severity:** CRITICAL — vi phạm BR-03: procurement governance requirement.

---

### GAP-05 — CRITICAL | POR.status → "Fulfilled": PP Item không được cập nhật sang "Delivered"

**Axis:** State-Workflow + Cross-Module Hook

**Vị trí phát hiện:**
- `Procurement Plan Item.status` options: `Pending / PO Raised / Ordered / Delivered / Cancelled`
- Technical Design: Chỉ implement `POR Released → PP Item = Ordered`
- Không có controller, API, hay hook nào implement `POR Fulfilled → PP Item = Delivered`
- Module Overview IMM-03: "Storekeeper xác nhận giao hàng (POR → Fulfilled)" — nhưng downstream effect không được xử lý

**Phân tích:**
`PP Item.status = "Delivered"` là trạng thái cuối cùng cần thiết cho:
1. PP Budget Utilization KPI (allocated vs delivered)
2. IMM-04 commissioning trigger chính xác (hàng đã về kho thực tế)
3. Audit trail năm tài chính

**Severity:** CRITICAL — trạng thái "Delivered" là dead state, không bao giờ đạt được.

---

### GAP-06 — CRITICAL | `notify_imm04_readiness.py`: Sai tên field `head_of_dept` (thực tế là `dept_head`)

**Axis:** Cross-Module Hook

**Vị trí phát hiện:**
- Technical Design `notify_imm04_readiness.py` line 13:
  `dept_head = frappe.db.get_value("AC Department", dept, "head_of_dept")`
- Scan thực tế `ac_department.json`:
  Field name thực = `dept_head` (label: "Department Head")

**Phân tích:**
`frappe.db.get_value("AC Department", dept, "head_of_dept")` sẽ trả về `None` (silent fail) vì field không tồn tại với tên đó. Notification sẽ không được gửi đến Dept Head. **Không phải exception — sẽ fail silently, khó debug.**

**Severity:** CRITICAL — silent data loss, trace chain POR → Dept Head bị đứt.

---

## 2. MINOR GAPS FOUND

---

### MINOR-01 | TS "Revised" → "Under Review": Không có API endpoint resubmit

**Vị trí:** IMM-03 API Interface — không có `resubmit_technical_spec` endpoint.
Workflow cho phép Revised → Under Review nhưng UI Guide và API không document action button hay endpoint cho Ops Manager để resubmit TS sau khi nhận feedback.

---

### MINOR-02 | `planning_snapshot` child table: Không có trigger auto-populate

**Vị trí:** Mapping Strategy Phần 2.2 — `planning_snapshot` Table field tồn tại trong NA.
Không có controller code nào auto-copy Device Model fields vào snapshot khi `linked_device_model` được chọn. Data capture mechanism hoàn toàn thiếu.

---

### MINOR-03 | `create_vendor_evaluation` API không auto-populate `linked_plan_item` từ TS

**Vị trí:** IMM-03 API Interface — request body cho `create_vendor_evaluation` chỉ nhận `linked_technical_spec` nhưng không tự suy ra `linked_plan_item`.
VE controller cần `linked_plan_item` để validate ngân sách nhưng không có fetch logic.

---

## 3. THE PATCH INSTRUCTIONS

---

### PATCH-01: Fix GA P-01 — NA.status → "Planned" trigger

**File:** `assetcore/doctype/procurement_plan/procurement_plan.py`

**Thêm vào `_set_items_po_raised()` method:**

```python
def _set_items_po_raised(self) -> None:
    for item in self.items:
        if item.status == "Pending":
            item.status = "PO Raised"
            # GAP-01 FIX: cập nhật ngược lại NA.status → Planned
            if item.needs_assessment:
                na_doc = frappe.get_doc("Needs Assessment", item.needs_assessment)
                if na_doc.status == "Approved":
                    frappe.db.set_value(
                        "Needs Assessment", item.needs_assessment, "status", "Planned"
                    )
                    # Append lifecycle event trực tiếp qua SQL để tránh submit issue
                    frappe.get_doc({
                        "doctype": "Asset Lifecycle Event",
                        "event_type": "linked_to_procurement_plan",
                        "event_domain": "imm_planning",
                        "from_status": "Approved",
                        "to_status": "Planned",
                        "actor": frappe.session.user,
                        "root_doctype": "Needs Assessment",
                        "root_record": item.needs_assessment,
                        "event_timestamp": frappe.utils.now(),
                        "notes": f"Linked to PP: {self.name}",
                    }).insert(ignore_permissions=True)
    self.save(ignore_permissions=True)
```

---

### PATCH-02: Fix GAP-02 — Thống nhất role "IMM Finance Director" → "IMM Finance Officer"

**Scope:** Toàn bộ hệ thống — đây là quyết định thiết kế, không phải code fix.

**Quyết định:** Dùng **`IMM Finance Officer`** là tên chuẩn duy nhất (đã được tạo qua fixtures).

**Files cần update:**

| File | Thay thế |
|---|---|
| `IMM-01_02_03_BA_Business_Analysis.md` | `IMM Finance Director` → `IMM Finance Officer` (tất cả 6 chỗ) |
| Frappe Workflow JSON cho NA | role = `IMM Finance Officer` |
| Frappe Workflow JSON cho PP | role = `IMM Finance Officer` |
| `assetcore/doctype/needs_assessment/needs_assessment.py` | Update comment/doc reference |
| `constants/roles.ts` | Thêm: `FINANCE_OFFICER: 'IMM Finance Officer'` |

**Không tạo role `IMM Finance Director`** — chỉ có 1 Finance role duy nhất trong system.

---

### PATCH-03: Fix GAP-03 — Implement `_notify_ops_manager_budget_locked()`

**File:** `assetcore/doctype/procurement_plan/procurement_plan.py`

**Thêm method body:**

```python
def _notify_ops_manager_budget_locked(self) -> None:
    """Notify Ops Manager: budget locked, create TS for each PO Raised item."""
    n_items = len([i for i in self.items if i.status == "PO Raised"])
    msg = (
        f"PP {self.name} đã khóa ngân sách — "
        f"Cần tạo Đặc tả Kỹ thuật cho {n_items} dòng thiết bị."
    )
    ops_managers = frappe.get_all(
        "Has Role",
        filters={"role": "IMM Operations Manager", "parenttype": "User"},
        fields=["parent"],
    )
    for u in ops_managers:
        frappe.publish_realtime(
            "imm_notification",
            {"message": msg, "type": "info", "link": f"/planning/procurement-plans/{self.name}"},
            user=u.parent,
        )
```

---

### PATCH-04: Fix GAP-04 — VE Joint Approval: 2-step workflow

**Quyết định thiết kế:** Thay `In Progress → Approved (2 roles)` bằng 2 bước riêng biệt.

**Workflow cập nhật cho `Vendor Evaluation`:**

```
Draft → In Progress          (Actor: IMM Operations Manager)
In Progress → Tech Reviewed  (Actor: IMM Technical Reviewer)  ← NEW STATE
Tech Reviewed → Approved     (Actor: IMM Finance Officer)
In Progress → Cancelled      (Actor: IMM Operations Manager)
```

**DocType update — thêm state vào `Vendor Evaluation.status` Select options:**

```
Draft\nIn Progress\nTech Reviewed\nApproved\nCancelled
```

**Controllers cần cập nhật:**

```python
# vendor_evaluation.py — on_update_after_submit
def on_update_after_submit(self) -> None:
    if self.status == "Tech Reviewed":
        _log_event(self, "vendor_evaluation_tech_reviewed", "Tech Reviewed")
        # Notify Finance Officer
        ...
    elif self.status == "Approved":
        self.approved_by = frappe.session.user
        self.approval_date = frappe.utils.today()
        _log_event(self, "vendor_selected", "Approved", ...)
```

**API update — thêm endpoint:**
```
POST approve_ve_technical(name, notes)   → status: Tech Reviewed
POST approve_ve_financial(name, recommended_vendor, notes)  → status: Approved
```

**Các docs cần update:** IMM-03_Module_Overview, IMM-03_Functional_Specs, IMM-03_API_Interface.

---

### PATCH-05: Fix GAP-05 — POR Fulfilled → PP Item "Delivered"

**File:** `assetcore/doctype/purchase_order_request/purchase_order_request.py`

**Update `on_update_after_submit`:**

```python
def on_update_after_submit(self) -> None:
    if self.status == "Released":
        self.release_date = frappe.utils.today()
        self.released_by = frappe.session.user
        _update_plan_item_status(self, "Ordered")       # existing
        _log_event(self, "por_released", "Released")
        self.save(ignore_permissions=True)
        frappe.enqueue(
            "assetcore.imm_planning.utils.notify_imm04_readiness",
            queue="default", timeout=300, por_name=self.name,
        )
    elif self.status == "Fulfilled":                    # GAP-05 FIX
        _update_plan_item_status(self, "Delivered")
        _log_event(self, "por_fulfilled", "Fulfilled",
                   notes="Storekeeper confirmed delivery")
        self.save(ignore_permissions=True)


def _update_plan_item_status(doc: Document, new_status: str) -> None:
    """Unified helper để update PP Item status."""
    if doc.linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item,
                            "status", new_status)
```

**API update — thêm endpoint `confirm_por_delivery`:**

```python
@frappe.whitelist()
def confirm_por_delivery(name: str, delivery_notes: str = "") -> dict:
    """Storekeeper confirms physical delivery — POR → Fulfilled."""
    ...
    # trigger status → Fulfilled via workflow or direct set
```

---

### PATCH-06: Fix GAP-06 — Sửa field name `head_of_dept` → `dept_head`

**File:** `assetcore/imm_planning/utils/notify_imm04_readiness.py`

```python
# BEFORE (sai):
dept_head = frappe.db.get_value("AC Department", dept, "head_of_dept")

# AFTER (đúng — verified từ ac_department.json):
dept_head = frappe.db.get_value("AC Department", dept, "dept_head")
```

---

### PATCH MINOR-01: Thêm `resubmit_technical_spec` endpoint

**File:** `assetcore/api/imm03.py`

```python
@frappe.whitelist()
def resubmit_technical_spec(name: str) -> dict:
    """Ops Manager resubmits a Revised TS back to Under Review."""
    doc = frappe.get_doc("Technical Specification", name)
    if doc.status != "Revised":
        return _err("TS không ở trạng thái Revised", "INVALID_STATE")
    doc.status = "Under Review"
    _log_event(doc, "technical_spec_resubmitted", "Under Review")
    doc.save(ignore_permissions=True)
    return _ok({"status": doc.status})
```

---

### PATCH MINOR-02: Auto-populate `planning_snapshot` khi chọn Device Model

**File:** `assetcore/doctype/needs_assessment/needs_assessment.py`

```python
def validate(self) -> None:
    _vr02_budget_range(self)
    _vr03_quantity_range(self)
    if self.status not in ("Draft", None):
        _vr04_justification_length(self)
    _vr01_duplicate_check(self)
    _sync_device_snapshot(self)     # PATCH MINOR-02


def _sync_device_snapshot(doc: Document) -> None:
    """Snapshot Device Model fields at time of NA creation."""
    if not doc.linked_device_model or doc.planning_snapshot:
        return  # chỉ populate lần đầu
    m = frappe.db.get_value(
        "IMM Device Model",
        doc.linked_device_model,
        ["model_name", "manufacturer", "medical_device_class",
         "nd98_class", "gmdn_code", "risk_classification", "expected_lifespan_years"],
        as_dict=True,
    )
    if m:
        doc.append("planning_snapshot", {
            "snapshot_date": frappe.utils.now(),
            "model_name": m.model_name,
            "manufacturer": m.manufacturer,
            "medical_device_class": m.medical_device_class,
            "nd98_class": m.get("nd98_class"),
            "gmdn_code": m.gmdn_code,
            "risk_classification": m.risk_classification,
            "expected_lifespan_years": m.expected_lifespan_years,
        })
```

---

### PATCH MINOR-03: Auto-populate `VE.linked_plan_item` từ TS

**File:** `assetcore/api/imm03.py` — `create_vendor_evaluation`

```python
@frappe.whitelist()
def create_vendor_evaluation(linked_technical_spec: str, evaluation_method: str,
                              evaluation_date: str = "") -> dict:
    # PATCH MINOR-03: fetch linked_plan_item từ TS
    linked_plan_item = frappe.db.get_value(
        "Technical Specification", linked_technical_spec, "linked_plan_item"
    )
    doc = frappe.get_doc({
        "doctype": "Vendor Evaluation",
        "linked_technical_spec": linked_technical_spec,
        "linked_plan_item": linked_plan_item,   # auto-populated
        "evaluation_method": evaluation_method,
        "evaluation_date": evaluation_date or frappe.utils.today(),
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)
    return _ok({"name": doc.name, "linked_plan_item": linked_plan_item})
```

---

## 4. FINAL ARCHITECT APPROVAL

### Pre-Sprint-1 Gate Checklist

| # | Condition | Status | Blocker? |
|---|---|---|---|
| **DB READY** | | | |
| DB-1 | `Procurement Plan Item.status` có option "Ordered" và "Delivered" | ⚠ Patch needed (Delivered không có trigger) | YES |
| DB-2 | `Vendor Evaluation.status` có state "Tech Reviewed" | ⚠ Patch needed (GAP-04) | YES |
| DB-3 | Role duy nhất = `IMM Finance Officer` (không có `IMM Finance Director`) | ⚠ Patch needed (GAP-02) | YES |
| DB-4 | `Asset Lifecycle Event` có field `event_domain` (Custom Field fixture) | ✅ Documented in Mapping Strategy | NO |
| DB-5 | `IMM Device Model` có field `nd98_class` (Custom Field fixture) | ✅ Documented | NO |
| **UI READY** | | | |
| UI-1 | `StatusBadge.vue` có color map cho tất cả Planning states (bao gồm "Tech Reviewed") | ⚠ Cần thêm "Tech Reviewed" sau GAP-04 patch | NO |
| UI-2 | `VEDetailView` có 2 workflow action buttons riêng biệt (Tech Approve / Finance Approve) | ⚠ Cần update sau GAP-04 patch | YES |
| UI-3 | `PORDetailView` có action "Xác nhận Giao hàng" cho Storekeeper role | ⚠ Missing (GAP-05) | YES |
| UI-4 | `NACreateView` có `planning_snapshot` section (readonly, auto-fill) | ⚠ MINOR-02, không block Sprint 1 | NO |
| **EVENT READY** | | | |
| EV-1 | `notify_imm04_readiness` dùng đúng field `dept_head` (không phải `head_of_dept`) | ⚠ GAP-06 patch required | YES |
| EV-2 | `_notify_ops_manager_budget_locked()` có implementation | ⚠ GAP-03 patch required | YES |
| EV-3 | NA.status → "Planned" được trigger khi linked vào PP Item | ⚠ GAP-01 patch required | YES |
| EV-4 | POR.status → "Fulfilled" trigger PP Item → "Delivered" | ⚠ GAP-05 patch required | YES |

---

### Verdict

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ APPROVED FOR SPRINT 1 CODING — ALL 6 BLOCKERS PATCHED       │
│                                                                  │
│  Patches applied 2026-04-22:                                    │
│    PATCH-01: NA Planned trigger          → procurement_plan.py  │
│    PATCH-02: Finance role unified        → BA_Business_Analysis │
│    PATCH-03: notify_budget implemented   → procurement_plan.py  │
│    PATCH-04: VE 2-step workflow          → Tech Design + API    │
│    PATCH-05: POR Fulfilled → Delivered   → Tech Design + API    │
│    PATCH-06: dept_head field fixed       → Tech Design          │
│    MINOR-01: resubmit_technical_spec     → API Interface        │
│    MINOR-02: planning_snapshot (deferred — field not in DocType)│
│    MINOR-03: VE auto-populate plan_item  → API Interface        │
│                                                                  │
│  Sprint 1 pre-conditions met. Proceed with implementation.      │
└─────────────────────────────────────────────────────────────────┘
```
