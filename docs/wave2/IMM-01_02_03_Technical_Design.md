# IMM-01 / IMM-02 / IMM-03 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | Technical Design — Frontend, Routing, Event Hooks, Permission |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |
| Nguồn context | Sync_State_Step1/2.md · F1–F5 Decisions · Wave 1 codebase scan |
| Nguyên tắc cốt lõi | **Reuse Wave 1 maximum — tạo mới chỉ khi không có analog** |

---

## PHẦN 1 — UI/UX COMPONENT ASSEMBLY

### 1.1 Inventory Component Wave 1 (đã xác nhận qua scan)

| Component | File | Loại | Mô tả |
|---|---|---|---|
| `StatusBadge` | `components/common/StatusBadge.vue` | Common | Badge màu theo trạng thái |
| `BaseModal` | `components/common/BaseModal.vue` | Common | Modal confirm/form overlay |
| `BasePagination` | `components/common/BasePagination.vue` | Common | Phân trang list |
| `SmartSelect` | `components/common/SmartSelect.vue` | Common | Dropdown có search |
| `LinkSearch` | `components/common/LinkSearch.vue` | Common | Link field search (DocType lookup) |
| `LoadingSpinner` | `components/common/LoadingSpinner.vue` | Common | Loading state |
| `SkeletonLoader` | `components/common/SkeletonLoader.vue` | Common | Skeleton cho list/card |
| `LinkInfoCard` | `components/common/LinkInfoCard.vue` | Common | Card hiển thị linked record info |
| `WorkflowActions` | `components/imm04/WorkflowActions.vue` | IMM-04 | Workflow transition buttons + confirm |
| `DocumentChecklist` | `components/imm04/DocumentChecklist.vue` | IMM-04 | Editable checklist table (grid rows) |
| `BaselineTestTable` | `components/imm04/BaselineTestTable.vue` | IMM-04 | Editable test grid với pass/fail |
| `CommissioningForm` | `components/imm04/CommissioningForm.vue` | IMM-04 | Multi-section form pattern |

**View Patterns tái sử dụng:**

| Pattern | File nguồn | Dùng cho |
|---|---|---|
| ListView (header + filter + table + pagination) | `CMWorkOrderListView.vue` | NA, PP, TS, VE, POR list |
| DetailView (info + actions + timeline) | `CommissioningDetailView.vue` | NA, PP, TS, VE, POR detail |
| CreateView (multi-section form) | `CommissioningCreateView.vue` | NA create, TS create |
| Dashboard (KPI cards + charts) | `CMDashboardView.vue` | Planning Dashboard |

---

### 1.2 Bảng ánh xạ Component → View Wave 2

#### IMM-01: Needs Assessment

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `NAListView.vue` | `StatusBadge`, `BasePagination`, `SkeletonLoader`, `SmartSelect` (dept filter) | — |
| `NACreateView.vue` | `SmartSelect` (dept, model), `BaseModal` (duplicate warn VR-01-01) | — |
| `NADetailView.vue` | `StatusBadge`, `WorkflowActions`, `LinkInfoCard` (linked model) | `LifecycleEventTimeline` (xem inline events) |
| `NAReviewModal.vue` | `BaseModal` | — |

> `WorkflowActions.vue` — tái dụng nguyên xi: chỉ cần thay `actions[]` prop với transitions của NA Workflow.

#### IMM-02: Procurement Plan

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `PPListView.vue` | `StatusBadge`, `BasePagination`, `SkeletonLoader` | — |
| `PPDetailView.vue` | `StatusBadge`, `WorkflowActions`, `DocumentChecklist` (items table — pattern) | `BudgetProgressBar.vue` |
| `PPItemRow.vue` (component) | `SmartSelect` (NA lookup, model lookup), `StatusBadge` | — |

> `DocumentChecklist.vue` (IMM-04) — grid rows với inline edit: **tái dụng pattern, không import trực tiếp** vì data schema khác. Tạo `PPItemsTable.vue` theo cùng layout/styling.

#### IMM-03: Technical Specification

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `TSListView.vue` | `StatusBadge`, `BasePagination`, `SkeletonLoader` | — |
| `TSCreateView.vue` | `SmartSelect` (plan item, model), `CommissioningForm` (multi-section pattern) | — |
| `TSDetailView.vue` | `StatusBadge`, `WorkflowActions`, `LinkInfoCard` | — |

#### IMM-03: Vendor Evaluation

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `VEListView.vue` | `StatusBadge`, `BasePagination`, `SkeletonLoader` | — |
| `VEDetailView.vue` | `StatusBadge`, `WorkflowActions`, `LinkInfoCard` | `VendorScoringTable.vue` |

> `BaselineTestTable.vue` (IMM-04) — editable grid với numeric inputs + computed result: **tái dụng pattern** cho `VendorScoringTable.vue`. Cùng layout, thay `is_pass` check bằng `total_score` + `score_band`.

#### IMM-03: Purchase Order Request

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `PORListView.vue` | `StatusBadge`, `BasePagination`, `SkeletonLoader` | — |
| `PORCreateView.vue` | `SmartSelect`, `LinkInfoCard` (linked VE + TS) | `PORApprovalBadge.vue` |
| `PORDetailView.vue` | `StatusBadge`, `WorkflowActions`, `LinkInfoCard` | `PORApprovalBadge.vue` |

#### Planning Dashboard

| View | Wave 1 Components tái dụng | Wave 2 mới |
|---|---|---|
| `PlanningDashboard.vue` | `CMDashboardView` pattern (KPI cards + chart structure) | `BudgetProgressBar.vue` |

---

### 1.3 New Components cần tạo (Wave 2 — chỉ 3)

#### `BudgetProgressBar.vue`
```
Props: { approved: number, allocated: number, label?: string }
Logic: remaining = approved - allocated; pct = allocated/approved×100
Style: progress bar xanh → vàng → đỏ theo % (≤80% / 80–99% / ≥100%)
Dùng: PPDetailView (header), PlanningDashboard (summary card)
```

#### `VendorScoringTable.vue`
```
Props: { vendors: VendorEvaluationItem[], readonly?: boolean }
Events: emit('update:vendors', newList)
Logic: tính total_score và score_band realtime khi user nhập score
Style: Grid table, cuối mỗi row hiện tổng điểm + badge A/B/C/D
Inspired by: BaselineTestTable.vue pattern (IMM-04)
```

#### `PORApprovalBadge.vue`
```
Props: { totalAmount: number, threshold?: number = 500_000_000 }
Render: nếu totalAmount > threshold → hiện badge "⚠ Cần Giám đốc ký"
Dùng: PORCreateView (form header), PORDetailView (workflow section)
```

---

## PHẦN 2 — FRONTEND ROUTING

### 2.1 Routes mới — append vào `router/index.ts`

> **Section 13: IMM-01/02/03 — Planning & Procurement** (thêm sau Section 12)

```typescript
// ─── 13. IMM-01/02/03 — Planning & Procurement ────────────────────────────

// IMM-01 — Needs Assessment
{ path: '/planning', redirect: '/planning/dashboard' },
{
  path: '/planning/dashboard',
  name: 'PlanningDashboard',
  component: () => import('@/views/PlanningDashboardView.vue'),
  meta: { requiresAuth: true, title: 'Tổng quan Kế hoạch — IMM-01/02/03' },
},
{
  path: '/planning/needs-assessments',
  name: 'NAList',
  component: () => import('@/views/NAListView.vue'),
  meta: { requiresAuth: true, title: 'Danh sách Đánh giá Nhu cầu — IMM-01' },
},
{
  path: '/planning/needs-assessments/new',
  name: 'NACreate',
  component: () => import('@/views/NACreateView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Tạo Phiếu Đánh giá Nhu cầu — IMM-01',
    requiredRoles: ROLES_PLANNING_CREATE,
  },
},
{
  path: '/planning/needs-assessments/:id',
  name: 'NADetail',
  component: () => import('@/views/NADetailView.vue'),
  props: true,
  meta: { requiresAuth: true, title: 'Chi tiết Đánh giá Nhu cầu — IMM-01' },
},

// IMM-02 — Procurement Plan
{
  path: '/planning/procurement-plans',
  name: 'PPList',
  component: () => import('@/views/PPListView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Danh sách Kế hoạch Mua sắm — IMM-02',
    requiredRoles: ROLES_PLANNING_VIEW,
  },
},
{
  path: '/planning/procurement-plans/new',
  name: 'PPCreate',
  component: () => import('@/views/PPCreateView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Tạo Kế hoạch Mua sắm — IMM-02',
    requiredRoles: ROLES_PLANNING_MANAGE,
  },
},
{
  path: '/planning/procurement-plans/:id',
  name: 'PPDetail',
  component: () => import('@/views/PPDetailView.vue'),
  props: true,
  meta: { requiresAuth: true, title: 'Chi tiết Kế hoạch Mua sắm — IMM-02' },
},

// IMM-03 — Technical Specification
{
  path: '/planning/technical-specs',
  name: 'TSList',
  component: () => import('@/views/TSListView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Danh sách Đặc tả Kỹ thuật — IMM-03',
    requiredRoles: ROLES_PLANNING_VIEW,
  },
},
{
  path: '/planning/technical-specs/new',
  name: 'TSCreate',
  component: () => import('@/views/TSCreateView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Tạo Đặc tả Kỹ thuật — IMM-03',
    requiredRoles: ROLES_PLANNING_MANAGE,
  },
},
{
  path: '/planning/technical-specs/:id',
  name: 'TSDetail',
  component: () => import('@/views/TSDetailView.vue'),
  props: true,
  meta: { requiresAuth: true, title: 'Chi tiết Đặc tả Kỹ thuật — IMM-03' },
},

// IMM-03 — Vendor Evaluation
{
  path: '/planning/vendor-evaluations',
  name: 'VEList',
  component: () => import('@/views/VEListView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Danh sách Đánh giá Nhà cung cấp — IMM-03',
    requiredRoles: ROLES_PLANNING_VIEW,
  },
},
{
  path: '/planning/vendor-evaluations/:id',
  name: 'VEDetail',
  component: () => import('@/views/VEDetailView.vue'),
  props: true,
  meta: {
    requiresAuth: true,
    title: 'Đánh giá Nhà cung cấp — IMM-03',
    requiredRoles: ROLES_PLANNING_VIEW,
  },
},

// IMM-03 — Purchase Order Request
{
  path: '/planning/purchase-order-requests',
  name: 'PORList',
  component: () => import('@/views/PORListView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Danh sách Yêu cầu Mua sắm — IMM-03',
    requiredRoles: ROLES_PLANNING_VIEW,
  },
},
{
  path: '/planning/purchase-order-requests/new',
  name: 'PORCreate',
  component: () => import('@/views/PORCreateView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Tạo Yêu cầu Mua sắm — IMM-03',
    requiredRoles: ROLES_PLANNING_MANAGE,
  },
},
{
  path: '/planning/purchase-order-requests/:id',
  name: 'PORDetail',
  component: () => import('@/views/PORDetailView.vue'),
  props: true,
  meta: { requiresAuth: true, title: 'Chi tiết Yêu cầu Mua sắm — IMM-03' },
},
```

### 2.2 Role Groups mới — append vào `constants/roles.ts`

```typescript
// Wave 2 — Planning roles
export const ROLES_PLANNING_CREATE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DEPT_HEAD, Roles.OPS_MANAGER, Roles.CLINICAL,
] as const

export const ROLES_PLANNING_MANAGE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
] as const

export const ROLES_PLANNING_VIEW: readonly RoleName[] = [
  ...ALL_IMM_ROLES,         // tất cả roles được xem
] as const

export const ROLES_PLANNING_APPROVE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
] as const

// Wave 2 new roles (sau khi fixtures tạo xong)
// Thêm vào Roles const:
// TECH_REVIEWER: 'IMM Technical Reviewer'
// FINANCE_OFFICER: 'IMM Finance Officer'
```

### 2.3 Sidebar Group mới — append vào `AppSidebar.vue` navGroups

```typescript
// Thêm vào navGroups array — sau group 'IMM-00 Nền tảng', trước 'IMM-04 Lắp đặt'
{
  title: 'Kế hoạch Mua sắm',
  items: [
    { label: 'Tổng quan KH', path: '/planning/dashboard', icon: 'chart' },
    { label: 'Đánh giá nhu cầu', path: '/planning/needs-assessments', icon: 'list' },
    { label: 'Kế hoạch mua sắm', path: '/planning/procurement-plans', icon: 'folder' },
    { label: 'Đặc tả kỹ thuật', path: '/planning/technical-specs', icon: 'list' },
    { label: 'Đánh giá NCC', path: '/planning/vendor-evaluations', icon: 'list' },
    { label: 'Yêu cầu mua sắm', path: '/planning/purchase-order-requests', icon: 'list' },
  ],
},
```

> **F1 Resolution:** Chỉ thêm 1 `NavGroup` object vào array — không sửa layout, không tạo component mới.

---

## PHẦN 3 — CROSS-MODULE EVENT HOOKS

### 3.1 Sơ đồ luồng Event tổng thể

```
IMM-01 on_submit(Approved)
  │
  ├─▶ [Frappe Notification] → Ops Manager: "NA {name} cần đưa vào kế hoạch"
  └─▶ [Asset Lifecycle Event] event_type=needs_assessment_approved, domain=imm_planning

IMM-02 on_update(status → Budget Locked)
  │
  ├─▶ [Loop PP Items] status=Pending → status=PO Raised
  ├─▶ [Asset Lifecycle Event] event_type=budget_locked, domain=imm_planning
  └─▶ [Frappe Notification] → Ops Manager: "Ngân sách đã khóa — Tạo TS cho {n} items"

IMM-03/TS on_submit(Approved)
  │
  └─▶ [Frappe Notification] → Technical Reviewer: "TS {name} sẵn sàng cho VE"

IMM-03/VE on_submit(Approved)
  │
  ├─▶ [Asset Lifecycle Event] event_type=vendor_selected, domain=imm_planning
  └─▶ [Frappe Notification] → Ops Manager: "VE {name} đã chọn vendor — Tạo POR"

IMM-03/POR on_submit(Released)
  │
  ├─▶ [Asset Lifecycle Event] event_type=por_released, domain=imm_planning
  ├─▶ [Update] PP Item.status = Ordered (synchronous)
  └─▶ [frappe.enqueue] notify_imm04_readiness(por_name) ← async, queue=default
        │
        └─▶ Tạo Frappe Notification cho:
              - Kho (Storekeeper): "POR {name} released — chuẩn bị tiếp nhận"
              - Ops Manager: "Khởi động IMM-04 cho {equipment}"
              - Dept Head của khoa yêu cầu ban đầu (trace: POR → PP Item → NA → dept)
```

### 3.2 Controller Hooks chi tiết

#### `needs_assessment.py`

```python
class NeedsAssessment(Document):

    def validate(self) -> None:
        self._vr_01_02_budget()
        self._vr_01_03_quantity()
        self._vr_01_01_duplicate_warn()

    def before_submit(self) -> None:
        self._vr_01_04_justification_length()

    def on_update_after_submit(self) -> None:
        """Workflow state changes đi qua đây (không phải on_submit)."""
        if self.status == "Approved":
            self._log_lifecycle("needs_assessment_approved", "Approved")
            self._notify_ops_manager_for_planning()
        elif self.status == "Rejected":
            self._log_lifecycle("needs_assessment_rejected", "Rejected",
                                notes=self.reject_reason)
            self._notify_dept_head_rejection()

    def _notify_ops_manager_for_planning(self) -> None:
        frappe.publish_realtime(
            "imm_notification",
            {"message": f"Phiếu {self.name} đã duyệt — cần đưa vào kế hoạch mua sắm",
             "type": "success"},
            user=self._get_ops_manager(),
        )
```

#### `procurement_plan.py`

```python
class ProcurementPlan(Document):

    def validate(self) -> None:
        self._vr_02_01_budget_cap()
        self._vr_02_02_has_items()
        self._br_02_01_unique_locked_plan()
        self._calc_remaining_budget()

    def on_update_after_submit(self) -> None:
        if self.status == "Budget Locked":
            self._set_items_po_raised()
            self._log_lifecycle("budget_locked", "Budget Locked")
            self._notify_ops_manager_budget_locked()

    def _calc_remaining_budget(self) -> None:
        self.allocated_budget = sum(
            (item.total_cost or 0) for item in self.items
        )
        self.remaining_budget = (self.approved_budget or 0) - self.allocated_budget

    def _set_items_po_raised(self) -> None:
        for item in self.items:
            if item.status == "Pending":
                item.status = "PO Raised"
        self.save(ignore_permissions=True)
```

#### `vendor_evaluation.py`

```python
class VendorEvaluation(Document):

    def validate(self) -> None:
        self._vr_03_04_min_vendors()
        self._calculate_scores()
        self._vr_03_05_recommend_justification()

    def _calculate_scores(self) -> None:
        for item in self.items:
            item.total_score = round(
                (item.technical_score or 0) * 0.40
                + (item.financial_score or 0) * 0.30
                + (item.profile_score or 0) * 0.20
                + (item.risk_score or 0) * 0.10,
                2,
            )
            s = item.total_score
            item.score_band = (
                "A (≥8)" if s >= 8 else
                "B (6–7.9)" if s >= 6 else
                "C (4–5.9)" if s >= 4 else "D (<4)"
            )
```

#### `purchase_order_request.py`

```python
class PurchaseOrderRequest(Document):

    def validate(self) -> None:
        self._calc_total()
        self._vr_03_06_budget_variance()
        self._vr_03_07_vendor_match()
        self._br_03_01_set_director_flag()

    def on_update_after_submit(self) -> None:
        if self.status == "Released":
            self._update_plan_item_ordered()
            self._log_lifecycle("por_released", "Released")
            frappe.enqueue(
                "assetcore.imm_planning.utils.notify_imm04_readiness",
                queue="default",
                timeout=300,
                por_name=self.name,
            )

    def _br_03_01_set_director_flag(self) -> None:
        self.requires_director_approval = (
            1 if (self.total_amount or 0) > 500_000_000 else 0
        )

    def _update_plan_item_ordered(self) -> None:
        if self.linked_plan_item:
            frappe.db.set_value(
                "Procurement Plan Item",
                self.linked_plan_item,
                "status", "Ordered",
            )
```

#### `utils/notify_imm04_readiness.py` (Background Job — D6)

```python
import frappe

def notify_imm04_readiness(por_name: str) -> None:
    """
    Async job: notify IMM-04 stakeholders khi POR Released.
    Không tạo Commissioning Record — chỉ notify (D7).
    """
    por = frappe.get_doc("Purchase Order Request", por_name)
    pp_item = frappe.get_doc("Procurement Plan Item", por.linked_plan_item)
    na = frappe.get_doc("Needs Assessment", pp_item.needs_assessment) \
         if pp_item.needs_assessment else None

    msg = (
        f"POR {por_name} đã phát hành — "
        f"Chuẩn bị tiếp nhận: {por.equipment_description} "
        f"(SL: {por.quantity}) từ {por.vendor_name}. "
        f"Dự kiến giao: {por.expected_delivery_date or 'TBD'}"
    )

    # Notify Storekeeper
    for user in frappe.get_all("User", filters={"role_profile_name": "IMM Storekeeper"},
                                fields=["name"]):
        frappe.publish_realtime("imm_notification",
                                {"message": msg, "type": "info"}, user=user.name)

    # Notify Ops Manager
    frappe.publish_realtime("imm_notification",
                            {"message": f"Khởi động IMM-04 cho {por.equipment_description}",
                             "type": "success"},
                            user=por.approved_by or frappe.session.user)

    # Notify requesting dept head (trace chain)
    if na:
        dept_head = frappe.db.get_value("AC Department", na.requesting_dept, "head_of_dept")
        if dept_head:
            frappe.publish_realtime("imm_notification",
                                    {"message": f"Thiết bị đã được đặt hàng cho khoa: "
                                                f"{por.equipment_description}",
                                     "type": "success"}, user=dept_head)

    frappe.logger().info(f"[IMM-03→IMM-04] notify_imm04_readiness complete: {por_name}")
```

---

## PHẦN 4 — PERMISSION MATRIX EXTENSION

### 4.1 Ma trận CRUD đầy đủ Wave 2

| DocType | Clinical User | Dept Head | Ops Manager | Tech Reviewer | Finance Officer | Sys Admin |
|---|---|---|---|---|---|---|
| `Needs Assessment` | **CR** (own dept*) | **CRWS** | **CRWS** | **R** | **R** | All |
| `Procurement Plan` | — | **R** | **CRWS** | **R** | **RS** (lock) | All |
| `Procurement Plan Item` | — | **R** | **CRW** (in PP) | **R** | **R** | All |
| `Technical Specification` | — | **R** | **CRWS** | **CRWS** | **R** | All |
| `Vendor Evaluation` | — | **R** | **CRW** | **CRWS** | **CRWS** | All |
| `Vendor Evaluation Item` | — | **R** | **CRW** | **CRW** | **CRW** | All |
| `Purchase Order Request` | — | **Approve** (>500M) | **CRWS** (≤500M) | **R** | **CRWS** | All |

> `*` = filtered by User Permission trên `requesting_dept`

### 4.2 User Permission Setup (F4 Resolution)

```
DocType    : User Permission
Allow      : AC Department
For Role   : IMM Clinical User
             IMM Department Head

Effect     : Clinical User và Dept Head chỉ thấy NA thuộc departments
             được liệt kê trong User Permission của họ.

Frappe config (fixtures/user_permissions.json pattern):
  - Field: requesting_dept (trong Needs Assessment)
  - Apply on: Needs Assessment
  - Permission type: User Permission per User hoặc per Role
```

### 4.3 Phân quyền Workflow Transition (Frappe Workflow Role)

| Transition | From State | To State | Role |
|---|---|---|---|
| Nộp phiếu | Draft | Submitted | IMM Department Head |
| Bắt đầu xem xét | Submitted | Under Review | IMM Operations Manager |
| Phê duyệt NA | Under Review | Approved | IMM Operations Manager, IMM Finance Officer |
| Từ chối NA | Under Review | Rejected | IMM Operations Manager |
| NA → Planned | Approved | Planned | System (auto) |
| Gửi KH xem xét | Draft | Under Review | IMM Operations Manager |
| Phê duyệt KH | Under Review | Approved | IMM Department Head |
| Khóa ngân sách | Approved | Budget Locked | IMM Finance Officer |
| Phê duyệt TS | Under Review | Approved | IMM Technical Reviewer |
| Phê duyệt VE | In Progress | Approved | IMM Technical Reviewer, IMM Finance Officer |
| Phê duyệt POR (≤500M) | Under Review | Approved | IMM Operations Manager, IMM Finance Officer |
| Phê duyệt POR (>500M) | Under Review | Approved | IMM Department Head |
| Phát hành POR | Approved | Released | IMM Operations Manager |

---

## PHẦN 5 — FRAPPE MODULE REGISTRATION (F5)

### 5.1 Sửa `assetcore/modules.txt`

```
# Thêm 1 dòng — không sửa các dòng Wave 1 hiện có:
imm_planning
```

### 5.2 Đăng ký fixtures trong `hooks.py`

```python
# hooks.py — fixtures section (append, không override)
fixtures = [
    # Wave 1 fixtures (giữ nguyên)
    ...
    # Wave 2 — Planning
    {"dt": "Custom Field", "filters": [["dt", "in", [
        "Asset Lifecycle Event", "IMM Device Model"
    ]]]},
    {"dt": "Role", "filters": [["name", "in", [
        "IMM Technical Reviewer", "IMM Finance Officer"
    ]]]},
    {"dt": "Workflow", "filters": [["name", "in", [
        "Needs Assessment Workflow",
        "Procurement Plan Workflow",
        "Technical Specification Workflow",
        "Vendor Evaluation Workflow",
        "Purchase Order Request Workflow",
    ]]]},
]
```

### 5.3 Đăng ký background job trong `hooks.py`

```python
# hooks.py — scheduler (thêm vào existing dict, không replace)
scheduler_events["daily"].append(
    "assetcore.imm_planning.scheduler.check_planning_sla",
)
# Hàm check: flag NA > 14 ngày chưa xử lý, PP > 30 ngày chưa lock
```

---

## PHẦN 6 — TRÌNH TỰ TRIỂN KHAI ĐỀ XUẤT

> Thứ tự này tránh dependency conflict khi `bench migrate`.

```
Sprint 1 — Foundation (tuần 1-2)
  ├── [BE] Thêm imm_planning vào modules.txt
  ├── [BE] Tạo fixtures: 2 Roles mới, 3 Custom Fields (Wave 1 inject)
  ├── [BE] Patch Procurement Plan Item: thêm status "Ordered"
  ├── [BE] Hoàn thiện POR DocType (JSON + .py + .js + test)
  ├── [BE] bench migrate → verify
  └── [FE] Thêm sidebar group + 12 routes vào router/index.ts + roles.ts

Sprint 2 — IMM-01 Complete (tuần 2-3)
  ├── [BE] Kiểm tra/hoàn thiện imm01.py (thêm begin_technical_review nếu thiếu)
  ├── [BE] Tạo Needs Assessment Workflow JSON
  ├── [BE] Setup User Permission fixtures (F4)
  ├── [FE] NAListView, NACreateView, NADetailView
  └── [FE] NAReviewModal (reuse BaseModal)

Sprint 3 — IMM-02 Complete (tuần 3-4)
  ├── [BE] Tạo imm02.py API
  ├── [BE] Tạo Procurement Plan Workflow JSON
  ├── [FE] PPListView, PPCreateView, PPDetailView
  ├── [FE] PPItemsTable component
  └── [FE] BudgetProgressBar component (mới)

Sprint 4 — IMM-03 Complete (tuần 4-6)
  ├── [BE] Tạo TS DocType + imm03.py (phần TS)
  ├── [BE] Tạo VE DocType + VE Item DocType
  ├── [BE] Hoàn thiện POR .py controller với enqueue
  ├── [BE] notify_imm04_readiness.py background job
  ├── [FE] TSListView, TSCreateView, TSDetailView
  ├── [FE] VEListView, VEDetailView + VendorScoringTable component (mới)
  ├── [FE] PORListView, PORCreateView, PORDetailView + PORApprovalBadge (mới)
  └── [FE] PlanningDashboardView

Sprint 5 — Integration & UAT (tuần 7-8)
  ├── End-to-end test: NA → PP → TS → VE → POR → IMM-04 notify
  ├── User Permission test: Clinical User isolation
  ├── Director threshold test: POR >500M
  └── Audit trail completeness check
```

---

*Tài liệu này là đầu vào cho:*
*`Sync_State_Final_Wave2_Phase1.md` (Master Index)*
