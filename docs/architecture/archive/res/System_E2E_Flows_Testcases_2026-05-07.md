# AssetCore — Luồng Hệ thống & Testcase E2E (FE → BE)

**Ngày phát hành:** 2026-05-07
**Phạm vi:** Toàn bộ chức năng đã build tới Wave 2 (sprint hiện hành)
**Mục đích:**
1. Chốt **milestone** các luồng nghiệp vụ đã có trong hệ thống (snapshot để truy ngược).
2. Cung cấp **bộ testcase thực tế** kiểm thử từ Frontend (Vue) → API (Frappe whitelist) → Database (DocType) → Audit Trail.
3. Là input cho UAT, regression test và CI smoke check.

**Tham chiếu:**
- `docs/res/Frontend_Router_Navigation_Map.md`
- `docs/res/Module_Business_Flows_2026-04-19.md`
- `docs/imm-XX/IMM-XX_UAT_Script.md` (chi tiết từng module)
- `assetcore/api/*.py` (BE endpoints) · `frontend/src/router/index.ts` (FE routes)

---

## 0. Quy ước viết testcase

Mỗi testcase tuân thủ format:

```
TC-<MODULE>-<STT>: <Tên ngắn>
  Actor:    <vai trò Frappe role>
  Pre:      <dữ liệu cần có trước khi chạy>
  FE Step:  <thao tác trên UI>  → route: <path>
  API Call: <method> <endpoint>  body=<payload>
  BE Check: <DocType field, status, side-effect>
  DB:       <bảng + dòng phải tồn tại / state>
  Audit:    <Lifecycle Event / Audit Trail row sinh ra>
  Expect:   <kết quả UI sau action>
```

**Nguyên tắc:**
- Mỗi action **phải sinh** Lifecycle Event hoặc Audit Trail (ISO 13485) — kiểm tra ở bước `Audit:`.
- Response API phải dạng `_ok(data)` / `_err(msg, code)` (xem `assetcore/api/*.py`).
- Validation lỗi UI phải hiển thị bằng tiếng Việt (`frappe.throw(_("..."))`).
- Role check: System Manager / Administrator bypass IMM role guard (xem `router/index.ts` L817).

---

## 1. Milestone — Chức năng đã build (snapshot 2026-05-07)

### 1.1 Khối chung

| Khối | Module | Trạng thái BE | Trạng thái FE | Ghi chú |
|---|---|---|---|---|
| Auth | Login / Register / Profile / Change Password | ✅ | ✅ | `api/auth.py`, `views/auth/` |
| Layout | Notification, Session ping, Logout | ✅ | ✅ | `api/layout.py` |
| Dashboard | Overview KPI | ✅ | ✅ | `api/dashboard.py` → `/dashboard` |
| Launcher | Hub IMM (chọn module) | — | ✅ | `views/modules/LauncherView.vue` |
| Admin | User Profile + Role Profile | ✅ | ✅ | `api/user.py` |

### 1.2 Khối 1 — Hoạch định & Mua sắm (Wave 2)

| Module | Tên | API file | FE views | UAT Script |
|---|---|---|---|---|
| IMM-01 | Đề xuất nhu cầu + Kế hoạch mua sắm | `api/imm01.py` | `views/imm01/` | `docs/imm-01/IMM-01_UAT_Script.md` |
| IMM-02 | Hồ sơ kỹ thuật (Tech Spec) | `api/imm02.py` | `views/imm02/` | `docs/imm-02/IMM-02_UAT_Script.md` |
| IMM-03 | Đánh giá NCC, AVL, Quyết định mua sắm | `api/imm03.py` | `views/imm03/` | `docs/imm-03/IMM-03_UAT_Script.md` |
| IMM-03b | Purchase Order | `api/purchase.py` | `views/purchase/` | — |

### 1.3 Khối 2 — Triển khai & Lắp đặt (Wave 1)

| Module | Tên | API | FE | UAT |
|---|---|---|---|---|
| IMM-04 | Commissioning (nghiệm thu) | `api/imm04.py` | `views/commissioning/` | `imm-04/IMM-04_UAT_Script_v2.md` |
| IMM-05 | Document Repository | `api/imm05.py` | `views/document/` | `imm-05/IMM-05_UAT_Script.md` |
| IMM-06 | Asset Registration | (kế thừa từ IMM-04 onSubmit) | (auto) | `imm-06/IMM-06_UAT_Script.md` |

### 1.4 Khối 3 — Vận hành & Bảo trì (Wave 1)

| Module | Tên | API | FE | UAT |
|---|---|---|---|---|
| IMM-08 | Preventive Maintenance | `api/imm08.py` | `views/pm/` | `imm-08/IMM-08_UAT_Script.md` |
| IMM-09 | Corrective Maintenance | `api/imm09.py` | `views/cm/` | `imm-09/IMM-09_UAT_Script.md` |
| IMM-11 | Calibration | `api/imm11.py` | `views/calibration/` | `imm-11/IMM-11_UAT_Script.md` |
| IMM-12 | Incident + RCA + CAPA | `api/imm12.py` | `views/incident/` | `imm-12/IMM-12_UAT_Script.md` |
| IMM-15 | Inventory + Spare Parts + Stock | `api/inventory.py` | `views/inventory/` | `imm-15/IMM-15_UAT_Script.md` |
| IMM-16 | Audit Trail | (read-only `imm_audit_trail`) | `views/audit/` | `imm-16/IMM-16_UAT_Script.md` |

### 1.5 Khối 4 — Vận hành đời / Kết thúc (Foundation)

| Module | Tên | API | FE |
|---|---|---|---|
| Asset Master | AC Asset 360° | `api/imm00.py` | `views/asset/` |
| Asset Transfer | Điều chuyển | (trong `imm00.py` services) | `views/asset/AssetTransfer*.vue` |
| Service Contract | HĐ dịch vụ | `imm00.py` | `views/purchase/ServiceContract*.vue` |
| Depreciation | Khấu hao | `api/depreciation.py` | `views/asset/DepreciationView.vue` |

---

## 2. Sơ đồ luồng tổng — End-to-End

```
[IMM-01 Needs] → [IMM-01 Plan] → [IMM-02 Tech Spec] → [IMM-03 Vendor Eval]
       │              │                   │                     │
       │              │                   │                     ▼
       │              │                   │            [IMM-03 Decision]
       │              │                   │                     │
       │              ▼                   │                     ▼
       │         (Budget OK)              │              [Purchase Order]
       │                                  │                     │
       │                                  │                     ▼
       └──────────────►[IMM-04 Commission]◄─────────[Goods Receipt: hardware tới]
                              │
                              ▼
                      [IMM-06 Register Asset] ──► [AC Asset = ACTIVE]
                              │
        ┌─────────────────────┼──────────────────────────┐
        ▼                     ▼                          ▼
   [IMM-08 PM]           [IMM-11 Cal]              [IMM-09 CM]
        │                     │                          ▲
        ▼                     ▼                          │
   PM Result        Cal Result (pass/fail)          (incident)
        │                     │                          │
        └──── Major fail ─────┴── failure ──► [IMM-12 Incident]
                                                  │
                                                  ▼
                                          [RCA → CAPA]
                                                  │
        ┌─────────────────────────────────────────┘
        ▼
   [Audit Trail (IMM-16)] — bắt buộc trong mọi node
```

---

## 3. Luồng nghiệp vụ chi tiết + Testcase

### 3.A. AUTH & ONBOARDING

#### A.1 Luồng đăng ký + đăng nhập

```
Register → (admin approve) → Login → fetchSession → Profile
```

**TC-AUTH-01: Đăng ký tài khoản mới**
- Actor: Guest
- FE Step: `/register` → nhập email/full_name/password → "Đăng ký"
- API Call: `POST /api/method/assetcore.api.auth.register_user`
- BE Check: User tạo `enabled=0`, role mặc định `IMM Operator`
- DB: `tabUser` mới, `tabHas Role` link
- Audit: tạo notification cho `IMM System Admin`
- Expect: UI hiện "Chờ admin duyệt"

**TC-AUTH-02: Admin duyệt user**
- Actor: System Manager
- Pre: TC-AUTH-01 đã chạy
- FE Step: `/user-profiles` → chọn user → "Duyệt"
- API Call: `POST /api/method/assetcore.api.user.approve_registration`
- BE Check: `User.enabled=1`, gửi welcome email
- DB: `tabUser.enabled=1`
- Expect: User đăng nhập được

**TC-AUTH-03: Đăng nhập thành công**
- Actor: User đã được duyệt
- FE Step: `/login` → email + password
- API Call: `POST /api/method/login` → sau đó FE gọi `auth.fetchSession()` → `api.layout.get_user_context`
- BE Check: trả `{user, roles, full_name, ...}`
- Expect: redirect `/launcher`, sidebar hiển thị các module theo role

**TC-AUTH-04: Đăng nhập sai mật khẩu**
- FE Step: `/login` → password sai
- Expect: hiển thị "Email hoặc mật khẩu không đúng" (tiếng Việt)

**TC-AUTH-05: Đổi mật khẩu**
- Actor: User logged-in
- FE Step: `/account/change-password`
- API: `POST assetcore.api.auth.change_password` (old_password, new_password)
- BE Check: Frappe Auth verify old, update new
- Expect: logout + redirect login

**TC-AUTH-06: Route guard — không có role**
- Actor: User không có `ROLES_PM_MANAGE`
- FE Step: gõ trực tiếp `/pm/work-orders/new`
- Expect: redirect `/unauthorized?forbidden=/pm/work-orders/new`

---

### 3.B. IMM-01 — ĐỀ XUẤT NHU CẦU & KẾ HOẠCH MUA SẮM

```
[Draft Needs] → [Submit] → [Score] → [Budget Estimate] → [Board Approve]
                                                              │
                                                              ▼
                                                   [Roll into Procurement Plan]
```

**Workflow trạng thái** (xem `IMM Needs Request`):
`Draft → Submitted → Scored → Budgeted → Approved | Rejected`

**TC-IMM01-01: Tạo đề xuất nhu cầu mới**
- Actor: IMM Operator
- FE Step: `/needs-requests/new` → fill form (loại thiết bị, số lượng, lý do, urgency)
- API Call: `POST assetcore.api.imm01.create_needs_request` body=`{payload: {...}}`
- BE Check: tạo `IMM Needs Request` status=`Draft`, naming `NR-YYYY-#####`
- DB: `tabIMM Needs Request` mới
- Audit: Audit Trail `action=create, doctype=IMM Needs Request`
- Expect: redirect `/needs-requests/:id`

**TC-IMM01-02: Submit đề xuất**
- Pre: TC-IMM01-01
- FE Step: trang detail → "Gửi duyệt"
- API: `POST assetcore.api.imm01.submit_needs_request name=NR-...`
- BE Check: status=`Submitted`, populate `submitted_by`, `submitted_on`
- Audit: Lifecycle Event `submitted`
- Expect: action button đổi thành "Score"

**TC-IMM01-03: Chấm điểm ưu tiên**
- Actor: IMM Manager
- FE Step: detail → tab "Scoring" → nhập rows
- API: `POST assetcore.api.imm01.score_needs_request name=..., scoring_rows=[...]`
- BE Check: ghi vào child table `Needs Priority Scoring`, status → `Scored`, tính `priority_score`
- DB: `tabNeeds Priority Scoring` rows mới
- Expect: `priority_score` hiển thị trên detail

**TC-IMM01-04: Lập budget estimate**
- Actor: IMM Finance / Manager
- FE: detail → tab "Budget" → thêm line items
- API: `POST assetcore.api.imm01.submit_budget_estimate name=..., budget_lines=[{item, qty, unit_price}]`
- BE: ghi vào `Budget Estimate Line`, tính `total_budget`, status=`Budgeted`
- DB: `tabBudget Estimate Line`
- Expect: tổng tiền hiển thị

**TC-IMM01-05: Board approve**
- Actor: IMM Board Approver
- FE: detail → "Duyệt" (chỉ hiện khi status=Budgeted + role match)
- API: `POST assetcore.api.imm01.approve_needs_request board_approver=..., remarks=...`
- BE: status=`Approved`, populate `approved_by`, `approved_on`
- Audit: Lifecycle Event `approved`
- Expect: button "Roll into Plan" xuất hiện

**TC-IMM01-06: Reject đề xuất**
- API: `POST assetcore.api.imm01.reject_needs_request name=..., rejection_reason=...`
- BE Check: lỗi nếu `rejection_reason` rỗng → `frappe.throw(_("Lý do từ chối là bắt buộc"))`
- Expect: status=`Rejected`, không cho transition tiếp

**TC-IMM01-07: Roll multiple needs vào kế hoạch năm**
- Actor: IMM Manager
- FE: `/procurement-plans` → "Tạo kế hoạch từ đề xuất đã duyệt"
- API: `POST assetcore.api.imm01.roll_into_plan plan_year=2026, plan_period="Annual", needs=[...]`
- BE: tạo `IMM Procurement Plan` + `Procurement Plan Line` cho mỗi need
- DB: `tabIMM Procurement Plan`, `tabProcurement Plan Line`
- Expect: list `/procurement-plans` hiện plan mới

**TC-IMM01-08: Demand forecast**
- API: `GET assetcore.api.imm01.get_demand_forecast forecast_year=2026, device_category=Diagnostic`
- BE: tổng hợp từ history + driver
- Expect: trả `{forecast: [{period, qty, confidence}]}`

**TC-IMM01-09: KPI dashboard**
- API: `GET assetcore.api.imm01.dashboard_kpis period=2026-Q2`
- Expect: `{total_requests, approved_count, avg_approval_days, top_categories}`

---

### 3.C. IMM-02 — HỒ SƠ KỸ THUẬT (TECH SPEC)

```
[Draft] → [Benchmark] → [Lock-in Risk] → [Lock] → [Reissue (nếu cần)]
```

**TC-IMM02-01: Tạo Tech Spec từ Procurement Plan**
- Actor: IMM Tech Officer
- FE: `/tech-specs/new` → chọn plan + plan_lines
- API: `POST assetcore.api.imm02.draft_from_plan plan=PP-..., plan_lines=[...]`
- BE: tạo `IMM Tech Spec` status=`Draft`, copy fields từ plan, sinh `Tech Spec Requirement` rows
- DB: `tabIMM Tech Spec`, `tabTech Spec Requirement`
- Expect: redirect `/tech-specs/:id`

**TC-IMM02-02: Submit benchmark thị trường**
- API: `POST assetcore.api.imm02.submit_benchmark spec_ref=..., candidates=[{vendor, model, price}]`
- BE: tạo `IMM Market Benchmark` + `Benchmark Candidate` rows
- Expect: ít nhất 3 candidate mới hiện được tab "So sánh"

**TC-IMM02-03: Lock-in risk assessment**
- API: `POST assetcore.api.imm02.submit_lock_in_assessment spec_ref=..., items=[...]`
- BE: tạo `IMM Lock-in Risk Assessment`, `Lock-in Risk Item`
- Expect: cảnh báo đỏ nếu `lock_in_score >= 70`

**TC-IMM02-04: Lock spec**
- FE: detail → "Khóa hồ sơ" (yêu cầu approver)
- API: `POST assetcore.api.imm02.lock_spec name=..., approver=user@..., remarks=...`
- BE: status=`Locked`, mọi field readonly trừ thông qua reissue
- Audit: Lifecycle Event `spec_locked`
- Expect: form chuyển read-only

**TC-IMM02-05: Reissue spec sau khi đã lock**
- API: `POST assetcore.api.imm02.reissue_spec from_spec=TS-...`
- BE: tạo bản mới version `v2`, link `parent_spec`
- Expect: spec cũ status `Superseded`, spec mới `Draft`

**TC-IMM02-06: Withdraw spec**
- API: `POST assetcore.api.imm02.withdraw_spec name=..., withdrawal_reason="..."`
- BE: status=`Withdrawn`, không cho dùng cho IMM-03
- Expect: error UI "Không thể đánh giá NCC trên spec đã thu hồi"

---

### 3.D. IMM-03 — ĐÁNH GIÁ NCC + AVL + QUYẾT ĐỊNH MUA SẮM

```
[Create Eval] → [Add Candidates] → [Submit Quotations] → [Score] → [Decision]
                       │
                       └── (NCC chưa AVL) → [AVL Sign-off] → [Approve AVL]
```

**TC-IMM03-01: Tạo đánh giá từ Tech Spec đã lock**
- Actor: IMM Procurement Officer
- FE: `/vendor-evaluations` → "Đánh giá mới" → chọn spec
- API: `POST assetcore.api.imm03.create_evaluation spec_ref=TS-..., weighting_scheme={tech: 60, price: 40}`
- BE: spec phải `Locked`; nếu không → `frappe.throw(_("Hồ sơ kỹ thuật chưa được khóa"))`
- DB: `tabIMM Vendor Evaluation`
- Expect: redirect detail page

**TC-IMM03-02: Thêm NCC ứng viên (đã AVL)**
- API: `POST assetcore.api.imm03.add_candidate name=VE-..., supplier=SUP-001`
- BE: kiểm `IMM AVL Entry` cho `device_category` của spec — nếu có → OK
- DB: `tabVendor Eval Candidate`
- Expect: candidate hiện trong table

**TC-IMM03-03: Thêm NCC chưa AVL (yêu cầu sign-off)**
- API: `POST ... add_candidate supplier=SUP-NEW, sign_off_non_avl="GĐ duyệt 2026-05-06"`
- BE: nếu không có sign_off → `frappe.throw(_("NCC này chưa thuộc AVL — cần sign-off"))`
- Audit: ghi `sign_off_non_avl` vào audit trail

**TC-IMM03-04: Nhập báo giá**
- API: `POST ... submit_quotations name=VE-..., quotations=[{supplier, total_price, currency, validity_days}]`
- BE: ghi `Vendor Quotation Line`
- Expect: tab "Báo giá" hiện đủ rows

**TC-IMM03-05: Chấm điểm đa-vai trò**
- API: `POST ... score_evaluation name=..., scorer_role="Tech", scores_by_supplier={SUP-001: {tech_quality: 8, ...}}`
- BE: ghi `IMM Vendor Scorecard` + `Scorecard KPI Row`, blend với weighting → `final_score`
- Expect: ranking table tự động sắp xếp

**TC-IMM03-06: Tạo quyết định mua sắm**
- API: `POST assetcore.api.imm03.transition_eval_workflow name=VE-..., action="Decide"`
- BE: tạo `IMM Procurement Decision` link tới winner
- Expect: redirect `/procurement-decisions/:id`

**TC-IMM03-07: AVL — đăng ký NCC mới**
- API: `POST ... create_avl_entry supplier=SUP-002, device_category="MRI"`
- BE: status=`Pending`
- DB: `tabIMM AVL Entry`

**TC-IMM03-08: AVL approve**
- API: `POST ... approve_avl name=AVL-..., approver=GD@..., approval_doc="QC-AVL-2026"`
- BE: status=`Approved`, `valid_until` = +2 năm
- Expect: NCC dùng được cho evaluation mới

**TC-IMM03-09: AVL suspend**
- API: `POST ... suspend_avl name=AVL-..., suspension_reason="..."`
- BE: status=`Suspended`, evaluation mới block sử dụng

---

### 3.E. PURCHASE ORDER (sau Decision)

**TC-PO-01: Tạo đơn mua từ Decision**
- FE: `/purchases/new` (pre-filled từ decision)
- API: `POST assetcore.api.purchase.create_purchase payload={supplier, items, total}`
- BE: tạo `AC Purchase` status=`Draft` + `AC Purchase Item` + `AC Purchase Device Item`
- Expect: status badge "Draft"

**TC-PO-02: Submit đơn**
- API: `POST assetcore.api.purchase.submit_purchase name=PO-...`
- BE: status=`Submitted`, frozen
- Audit: Lifecycle Event `po_submitted`

**TC-PO-03: Mark received (hàng tới)**
- API: `POST ... mark_received name=PO-...`
- BE: status=`Received`, trigger sang IMM-04 commissioning
- Expect: notification cho IMM Logistics

**TC-PO-04: Tạo phiếu nhập kho từ PO**
- API: `POST ... create_receipt_movement name=PO-..., to_warehouse=WH-..., items=[...]`
- BE: tạo `AC Stock Movement` type=`Receipt` linked với PO
- DB: `tabAC Stock Movement`
- Expect: tồn kho cập nhật

---

### 3.F. IMM-04 — COMMISSIONING (NGHIỆM THU)

**Workflow** (`asset_commissioning`):
`Draft → Submitted → Acceptance → Handover → Completed | NC`

**TC-IMM04-01: Tạo phiếu nghiệm thu từ PO**
- Actor: IMM Acceptance Officer
- FE: `/commissioning/new`
- API: `POST assetcore.api.imm04.create_commissioning data={purchase: PO-..., scheduled_date}`
- BE: tạo `Asset Commissioning` naming `ACC-YYYY-#####` status=`Draft`
- DB: `tabAsset Commissioning`
- Expect: redirect detail

**TC-IMM04-02: Lưu nháp**
- API: `POST ... save_commissioning name=ACC-..., fields={...}`
- Expect: badge "Đã lưu lúc HH:mm"

**TC-IMM04-03: Quét barcode tra cứu**
- FE: nút quét QR
- API: `GET ... get_barcode_lookup barcode=...`
- BE: lookup PO + device model
- Expect: form auto-fill

**TC-IMM04-04: Check serial number duplicate**
- API: `GET ... check_sn_unique vendor_sn=SN-001, exclude_name=ACC-...`
- BE: query `AC Asset` + `Asset Commissioning`
- Expect: error red "Serial đã tồn tại trên asset XYZ"

**TC-IMM04-05: Submit phiếu (full flow)**
- Pre: form đủ field, có bảng kiểm `Commissioning Checklist`
- API: `POST ... submit_commissioning name=ACC-...`
- BE:
  - validate đầy đủ checklist
  - tạo `AC Asset` (IMM-06 trigger) status=`Active`
  - tạo `Asset Lifecycle Event` (`installed`, `commissioned`)
  - tạo audit trail
- DB: `tabAsset Commissioning.workflow_state=Completed`, `tabAC Asset` mới
- Expect: redirect `/assets/:id` mới

**TC-IMM04-06: Báo cáo Non-Conformance**
- API: `POST ... report_nonconformance commissioning_name=ACC-..., nc_data={severity, description}`
- BE: tạo `Asset QA Non Conformance`, blocks completion
- DB: `tabAsset QA Non Conformance`
- Expect: tab "NC" hiện row mới, status phiếu = `NC`

**TC-IMM04-07: In handover PDF**
- API: `GET ... generate_handover_pdf name=ACC-...`
- Expect: download PDF biên bản bàn giao (BM-04-01)

**TC-IMM04-08: In QR label cho asset**
- API: `GET ... generate_qr_label name=ACC-...`
- Expect: PDF QR có serial + asset code

**TC-IMM04-09: Timeline phiếu**
- FE: `/commissioning/:id/timeline`
- API: `GET ... get_asset_timeline` (xem IMM-00)
- Expect: hiển thị tất cả lifecycle event của asset

---

### 3.G. IMM-05 — DOCUMENT REPOSITORY

**TC-IMM05-01: Upload tài liệu**
- Actor: IMM Document Officer
- FE: `/documents/new` → chọn asset + loại + file
- API: `POST assetcore.api.imm05.create_document doc_data={asset, doc_type, file, expiry_date}`
- BE: tạo `Asset Document` status=`Pending Approval`
- DB: `tabAsset Document`, file vào `private/files/`
- Expect: redirect detail

**TC-IMM05-02: Approve tài liệu**
- Actor: Manager
- API: `POST ... approve_document name=AD-...`
- BE: status=`Approved`, sinh `Lifecycle Event` `doc_approved`
- Expect: badge xanh "Đã duyệt"

**TC-IMM05-03: Reject với lý do**
- API: `POST ... reject_document name=..., rejection_reason="..."`
- BE: bắt buộc reason, status=`Rejected`

**TC-IMM05-04: Document Request**
- API: `POST ... create_document_request asset=..., doc_type_detail=..., due_date=...`
- BE: tạo `Document Request`, gửi notification owner
- Expect: list `/documents/requests` có row pending

**TC-IMM05-05: Mark exempt (miễn yêu cầu)**
- API: `POST ... mark_exempt asset_ref=..., doc_type_detail=..., reason=...`
- BE: tạo `Document Request` status=`Exempted` (audit lý do)

**TC-IMM05-06: Sắp hết hạn — alert**
- API: `GET ... get_expiring_documents days=90`
- BE: query `Asset Document.expiry_date <= today + 90`
- Expect: dashboard `/documents` hiển thị widget "90 ngày tới"

**TC-IMM05-07: Compliance theo phòng ban**
- API: `GET ... get_compliance_by_dept`
- Expect: bar chart % phòng ban đủ hồ sơ

---

### 3.H. IMM-08 — PREVENTIVE MAINTENANCE (PM)

**Workflow** (`pm_work_order`):
`Scheduled → Assigned → In Progress → Completed | Major Failure → escalate IMM-12`

**TC-IMM08-01: Tạo PM Schedule định kỳ**
- Actor: IMM PM Manager
- FE: `/pm/schedules` → "Tạo lịch"
- API: `POST assetcore.api.imm08.create_pm_schedule asset_ref=..., interval_days=180, template=PMT-...`
- BE: tạo `PM Schedule`, scheduler tự sinh `PM Work Order` mỗi `interval_days`
- DB: `tabPM Schedule`

**TC-IMM08-02: Tạo PM Work Order ad-hoc**
- API: `POST ... create_pm_work_order` body={asset, scheduled_date, template}
- BE: tạo `PM Work Order` status=`Scheduled`, naming `WO-PM-...`
- Expect: hiện trên `/pm/calendar`

**TC-IMM08-03: Gán kỹ thuật viên**
- API: `POST ... assign_technician name=WO-..., technician=user@..., scheduled_date=...`
- BE: kiểm `AC Authorized Technician` cho asset_category
- Expect: status=`Assigned`, notification kỹ thuật viên

**TC-IMM08-04: Submit kết quả PM**
- API: `POST ... submit_pm_result name=WO-..., checklist_results=[{item, pass, note}], signoff=...`
- BE: validate đủ checklist, status=`Completed`, tạo `PM Task Log` + Lifecycle Event `pm_completed`
- DB: `tabPM Task Log`, `tabPM Checklist Result`
- Audit: rollup KPI `last_pm_date`, `next_pm_due_date` trên asset

**TC-IMM08-05: Báo lỗi nghiêm trọng từ PM**
- API: `POST ... report_major_failure pm_wo_name=..., failure_description=..., severity="Critical"`
- BE:
  - PM WO status=`Major Failure`
  - tạo `Incident Report` (chuyển sang IMM-12) link PM WO
  - nếu `Critical` → auto-tạo CAPA (BR-00-08)
- DB: `tabIncident Report` mới + `tabIMM CAPA Record`
- Expect: redirect `/incidents/:id`

**TC-IMM08-06: Reschedule PM**
- API: `POST ... reschedule_pm name=WO-..., new_date=..., reason=...`
- BE: kiểm `new_date >= today`, ghi audit lý do
- Expect: calendar update

**TC-IMM08-07: Calendar view (tháng)**
- API: `GET ... get_pm_calendar year=2026, month=5, asset_ref=...`
- Expect: trả `[{date, work_orders: [...]}]` để FE render lịch

**TC-IMM08-08: KPI dashboard**
- API: `GET ... get_pm_dashboard_stats year=2026, month=5`
- Expect: `{compliance_rate, overdue, completed_on_time, by_category}`

---

### 3.I. IMM-09 — CORRECTIVE MAINTENANCE (CM)

**Workflow** (`asset_repair`):
`Reported → Assigned → Diagnosing → Repairing → Closed`

**TC-IMM09-01: Tạo phiếu sửa chữa**
- Actor: IMM CM Officer / Operator báo cáo
- FE: `/cm/create`
- API: `POST assetcore.api.imm09.create_repair_work_order asset_ref=..., repair_type="Breakdown", priority="High", failure_description=...`
- BE: tạo `Asset Repair`, asset.status → `Under Repair`, lifecycle event `failure_reported`
- DB: `tabAsset Repair`

**TC-IMM09-02: Gán kỹ thuật viên**
- API: `POST ... assign_technician name=RP-..., technician=..., priority="High"`
- BE: SLA timer khởi động dựa trên `IMM SLA Policy`
- Expect: countdown SLA hiển thị

**TC-IMM09-03: Submit chẩn đoán**
- API: `POST ... submit_diagnosis name=..., diagnosis_notes="...", needs_parts=1`
- BE: status=`Diagnosing → Awaiting Parts` nếu needs_parts
- Expect: nếu `needs_parts` thì button "Yêu cầu phụ tùng" enable

**TC-IMM09-04: Yêu cầu phụ tùng**
- API: `POST ... request_spare_parts name=..., parts=[{spare_part, qty}]`
- BE: tạo `Spare Parts Used` rows + tạo `AC Stock Movement` type=`Issue` (nếu có sẵn)
- DB: `tabSpare Parts Used`, `tabAC Stock Movement`

**TC-IMM09-05: Bắt đầu sửa**
- API: `POST ... start_repair name=...`
- BE: status=`Repairing`, ghi `repair_started_at`

**TC-IMM09-06: Đóng phiếu**
- API: `POST ... close_work_order name=..., repair_summary=..., root_cause_category="Wear", verification_passed=1`
- BE:
  - validate `verification_passed`
  - status=`Closed`, asset.status → `Active`
  - tính MTTR (`closed_at - reported_at`)
  - lifecycle event `repaired`
- DB: `tabAsset Repair.workflow_state=Closed`, asset state restored
- Audit: `repaired` event với MTTR

**TC-IMM09-07: Firmware Change Request**
- FE: `/cm/firmware/:id`
- BE: `Firmware Change Request` workflow (Approve → Apply)

**TC-IMM09-08: MTTR report**
- API: `GET ... get_mttr_report year=2026, month=5`
- Expect: `{avg_mttr_hours, by_category, top_problematic_assets}`

---

### 3.J. IMM-11 — CALIBRATION

**Workflow** (`imm_asset_calibration`):
`Scheduled → In Progress → Sent To Lab → Result Pending → Pass | Fail`

**TC-IMM11-01: Tạo lịch hiệu chuẩn**
- API: `POST assetcore.api.imm11.create_calibration_schedule asset=..., calibration_type="Periodic", interval_days=365`
- BE: tạo `IMM Calibration Schedule`, scheduler tạo `IMM Asset Calibration` đến hạn

**TC-IMM11-02: Tạo phiếu hiệu chuẩn**
- API: `POST ... create_calibration asset=..., calibration_type=..., scheduled_date=...`
- BE: tạo `IMM Asset Calibration` status=`Scheduled`

**TC-IMM11-03: Gửi đi lab ngoài**
- API: `POST ... send_to_lab name=CAL-..., sent_date=..., lab_supplier=SUP-LAB-...`
- BE: status=`Sent To Lab`, asset marked `Out of Service`
- Expect: lifecycle event `cal_sent_to_lab`

**TC-IMM11-04: Nhập kết quả đo (parameters)**
- API: `POST ... add_measurement name=..., parameter_name="Voltage", unit="V", nominal_value=220, measured_value=219.5`
- BE: tạo `IMM Calibration Measurement`, tự tính `pass/fail` theo tolerance
- DB: `tabIMM Calibration Measurement`

**TC-IMM11-05: Submit pass**
- API: `POST ... submit_calibration name=...` (sau khi điền đủ measurements)
- BE: nếu mọi measurement pass → status=`Pass`, asset.status → `Active`
- Audit: lifecycle event `calibration_passed`, sinh certificate field

**TC-IMM11-06: Submit fail → escalate**
- BE: nếu có measurement out-of-tolerance → status=`Fail`, asset.status → `Quarantine`, auto-tạo Incident
- Expect: redirect `/incidents/:id`

**TC-IMM11-07: Cal certificate trong document repo**
- BE: file cert tự attach vào `Asset Document` type=`Calibration Certificate`
- Expect: hiện trên `/documents?asset=...`

---

### 3.K. IMM-12 — INCIDENT + RCA + CAPA

**Workflow** (`incident_report`):
`Reported → Acknowledged → Investigating (RCA) → Resolved → Closed`

**TC-IMM12-01: Báo cáo sự cố**
- Actor: IMM Operator / IMM Reporter
- FE: `/incidents/new`
- API: `POST assetcore.api.imm12.report_incident asset=..., severity="Critical", description=..., occurred_at=...`
- BE: tạo `Incident Report` status=`Reported`, asset.status → `Under Investigation` nếu Critical, naming `IR-...`
- DB: `tabIncident Report`
- Audit: lifecycle event `failure_reported`

**TC-IMM12-02: Acknowledge**
- API: `POST ... acknowledge_incident name=IR-..., notes=..., assigned_to=user@...`
- BE: status=`Acknowledged`, SLA timer cho RCA

**TC-IMM12-03: Tạo RCA**
- API: `POST ... create_rca incident_name=IR-..., rca_method="5-Why"`
- BE: tạo `IMM RCA Record`, tạo 5 row `IMM RCA Five Why Step` rỗng
- DB: `tabIMM RCA Record`

**TC-IMM12-04: Submit RCA + tạo CAPA**
- API: `POST ... submit_rca rca_name=..., five_why_steps=[...], related_incidents=[...], proposed_capa=[{action, owner, due_date}]`
- BE: ghi steps, tự tạo `IMM CAPA Record` cho mỗi proposed action
- DB: `tabIMM CAPA Record` mới
- Expect: list `/capas` có rows mới

**TC-IMM12-05: Resolve incident**
- API: `POST ... resolve_incident name=..., resolution_notes=..., root_cause=...`
- BE: status=`Resolved`, asset.status restore
- Audit: `incident_resolved`

**TC-IMM12-06: Close incident (verification)**
- API: `POST ... close_incident name=..., verification_notes=...`
- BE: yêu cầu CAPA liên quan ở status `Verified` mới close được, không thì `frappe.throw`

**TC-IMM12-07: Cancel incident (sai báo)**
- API: `POST ... cancel_incident name=..., reason=...`
- BE: status=`Cancelled`, ghi audit lý do

**TC-IMM12-08: Chronic failure detection**
- API: `GET ... get_chronic_failures`
- BE: lọc asset có ≥3 incident/năm → flag chronic
- Expect: dashboard `/incidents/dashboard` hiển thị "Top 10 thiết bị hay hỏng"

**TC-IMM12-09: Asset incident history**
- API: `GET ... get_asset_incident_history asset=..., limit=10`
- Expect: trả timeline kèm severity

**TC-IMM12-10: CAPA close**
- FE: `/capas/:id`
- BE: `IMM CAPA Record` workflow Open → In Progress → Implemented → Verified → Closed

---

### 3.L. IMM-15 — INVENTORY (KHO + PHỤ TÙNG)

**TC-IMM15-01: Tạo warehouse**
- API: `POST assetcore.api.inventory.create_warehouse payload={code, name, location}`
- DB: `tabAC Warehouse`

**TC-IMM15-02: Tạo spare part master**
- API: `POST ... create_spare_part payload={code, name, stock_uom, default_warehouse}`
- BE: validate UOM tồn tại
- DB: `tabAC Spare Part`

**TC-IMM15-03: Tạo phiếu nhập kho (Receipt)**
- API: `POST ... create_stock_movement payload={type: "Receipt", from: null, to: WH-..., items: [{part, qty, uom}]}`
- BE: tạo `AC Stock Movement` Draft
- DB: `tabAC Stock Movement`, `tabAC Stock Movement Item`

**TC-IMM15-04: Submit movement**
- API: `POST ... submit_stock_movement name=SM-...`
- BE:
  - validate qty > 0
  - cập nhật `AC Spare Part Stock` warehouse balance
  - lifecycle event `stock_in`
- DB: `tabAC Spare Part Stock` updated
- Audit: ghi audit trail

**TC-IMM15-05: Phiếu xuất (Issue) cho CM Work Order**
- API: `POST ... create_stock_movement payload={type: "Issue", from: WH-..., reference_type: "Asset Repair", reference_name: RP-...}`
- BE: kiểm tồn kho ≥ qty xuất, nếu không → `frappe.throw(_("Tồn kho không đủ"))`
- Expect: link tới CM WO hiển thị

**TC-IMM15-06: Cancel movement**
- API: `POST ... cancel_stock_movement name=SM-...`
- BE: rollback stock, status=`Cancelled`
- DB: `tabAC Spare Part Stock` revert

**TC-IMM15-07: Stock level dashboard**
- API: `GET ... get_stock_overview`
- Expect: `{total_value, low_stock_alerts, by_warehouse}`

**TC-IMM15-08: UOM conversion**
- API: `GET ... convert_qty spare_part=..., qty=10, from_uom="Hộp", to_uom="Cái"`
- BE: lookup `AC UOM Conversion`
- Expect: trả qty đã convert

**TC-IMM15-09: Search part autocomplete**
- API: `GET ... search_parts_autocomplete q="filter", limit=10`
- Expect: đề xuất top 10 dùng cho FE typeahead

---

### 3.M. IMM-16 — AUDIT TRAIL

**TC-IMM16-01: Mọi action sinh audit row**
- Pre: chạy bất kỳ TC tạo/sửa/transition ở trên
- API: `GET /api/method/frappe.client.get_list doctype=IMM Audit Trail filters=...`
- DB: `tabIMM Audit Trail` có row mới sau mỗi action
- Field bắt buộc: `actor`, `action`, `doctype_ref`, `name_ref`, `before`, `after`, `timestamp`, `ip`

**TC-IMM16-02: Audit trail UI list**
- FE: `/audit-trail`
- Expect: filter theo doctype + action + date range, export CSV

**TC-IMM16-03: Audit trail không bị xóa**
- DB: `IMM Audit Trail` permission `delete=0` cho mọi role trừ Administrator
- Expect: API delete trả 403

---

### 3.N. ASSET MASTER (IMM-00) — CROSS-CUTTING

**TC-IMM00-01: List assets có filter**
- API: `GET assetcore.api.imm00.list_assets filters=..., page=1, page_size=20`
- FE: `/assets` filter (department/category/status)

**TC-IMM00-02: Asset 360° view**
- FE: `/assets/:id`
- API: `GET ... get_asset name=...` + `get_asset_timeline` + `get_asset_kpi`
- Expect: tabs Info / Timeline / Documents / PM / CM / Calibration / Incidents

**TC-IMM00-03: Transition asset status**
- API: `POST ... transition_status name=..., to_status="Retired", reason="..."`
- BE: validate valid transition (state machine), tạo `Asset Lifecycle Event`
- DB: `tabAC Asset.status` + `tabAsset Lifecycle Event` mới

**TC-IMM00-04: GMDN status (QR scan)**
- FE: `/qr-scan` → quét QR
- API: `POST ... toggle_gmdn_status name=...`
- Expect: hiện status hiện tại + lịch PM/CAL gần nhất

**TC-IMM00-05: Validate asset for operations**
- API: `GET ... validate_for_operations name=...`
- BE: kiểm `Active` status + chứng chỉ calibration valid + bảo hiểm
- Expect: trả `{ok: bool, blockers: [...]}` — IMM-08/09 dùng để gate

**TC-IMM00-06: Asset Transfer**
- FE: `/asset-transfers/new`
- API: tạo `Asset Transfer`, submit → cập nhật `AC Asset.location`
- DB: `tabAsset Transfer` + lifecycle event `transferred`

**TC-IMM00-07: Service Contract**
- FE: `/service-contracts/new` → link nhiều assets
- DB: `tabService Contract` + `tabService Contract Asset`
- Scheduler: `check_service_contract_expiry` cảnh báo trước 30 ngày

**TC-IMM00-08: Depreciation**
- API: `GET ... get_depreciation_stats` + `compute_one_depreciation name=...`
- BE: tính straight-line theo `acquisition_cost`, `useful_life_years`
- DB: `tabAC Asset Depreciation Schedule`

---

### 3.O. DASHBOARD & NAVIGATION

**TC-DASH-01: Dashboard tổng**
- FE: `/dashboard`
- API: `GET assetcore.api.dashboard.get_overview`
- Expect: total assets, PM compliance, open incidents, expiring docs, low stock

**TC-NAV-01: Sidebar đổi theo module**
- FE: vào `/pm/...` → sidebar hiện nav IMM-08; vào `/incidents/...` → sidebar IMM-12
- Cơ chế: `meta.moduleId` từ `MODULE_RULES` (xem `router/index.ts` L730-770)

**TC-NAV-02: 404 catch-all**
- FE: gõ `/khong-ton-tai`
- Expect: render `NotFoundView.vue`

**TC-NAV-03: Pending approvals**
- FE: `/approvals/pending`
- BE: tổng hợp các phiếu đang chờ user duyệt theo role

---

## 4. Bộ Smoke Test (chạy trước mỗi release)

Tối thiểu phải pass các luồng dưới đây mới được merge `master`:

| # | Test | Chú thích |
|---|---|---|
| 1 | TC-AUTH-01 → 03 | Đăng ký + duyệt + login |
| 2 | TC-IMM01-01 → 05 | Needs Request full happy path |
| 3 | TC-IMM02-01,04 | Tech Spec → Lock |
| 4 | TC-IMM03-01,02,06 | Vendor eval → Decision |
| 5 | TC-PO-01,02,03 | PO submit + receive |
| 6 | TC-IMM04-01,05 | Commissioning submit → tạo Asset |
| 7 | TC-IMM05-01,02 | Document upload + approve |
| 8 | TC-IMM08-02,03,04 | PM WO → assign → submit |
| 9 | TC-IMM09-01,02,06 | Repair tạo → assign → close |
| 10 | TC-IMM11-02,04,05 | Calibration full pass |
| 11 | TC-IMM12-01,03,04 | Incident → RCA → CAPA |
| 12 | TC-IMM15-03,04 | Stock receipt + submit |
| 13 | TC-IMM16-01 | Audit trail có data sau các TC trên |

**Cách chạy:**
- Backend: `bench --site assetcore.localhost run-tests --app assetcore` (xem `assetcore/tests/`)
- Frontend: chạy thủ công theo flow + `frontend/tests/` (Vitest) khi đã có
- E2E: viết kịch bản Playwright theo `Frontend_Test_Report_2026-04-26.md`

---

## 5. Edge Cases bắt buộc test

| Edge case | Module | Expect |
|---|---|---|
| Submit khi field bắt buộc rỗng | All | `frappe.throw(_("..."))` tiếng Việt, FE hiện toast đỏ |
| Concurrent edit (2 user) | IMM-04, 09 | optimistic lock — báo "Bản ghi đã thay đổi, refresh" |
| Role không đủ truy cập | All | redirect `/unauthorized` |
| API trả 500 | All | FE hiện toast "Lỗi hệ thống, thử lại" + log Sentry |
| Network offline | FE | retry exponential 3 lần, sau đó queue offline |
| File upload > 10MB | IMM-05 | reject với message "File quá lớn (max 10MB)" |
| Stock xuất quá tồn | IMM-15 | block submit |
| PM scheduled date < today | IMM-08 | warning, vẫn cho tạo (backdated) nhưng audit lý do |
| Calibration overdue > 90 ngày | IMM-11 | asset.status auto → `Quarantine` |
| Incident severity Critical | IMM-12 | auto-tạo CAPA + notification ban giám đốc |
| Asset đã `Retired` | IMM-08/09/11 | block tạo WO mới |
| AVL hết hạn | IMM-03 | block evaluation |
| Tech Spec đã `Withdrawn` | IMM-03 | block create_evaluation |

---

## 6. Audit & Compliance Checklist

Mỗi testcase ở trên **phải verify** thêm các điểm ISO 13485 / NĐ98:

- [ ] Mọi state change → `Asset Lifecycle Event` row
- [ ] Mọi insert/update/delete → `IMM Audit Trail` row (with before/after JSON)
- [ ] User-facing errors là tiếng Việt
- [ ] File attachments ở `private/files/` (không public)
- [ ] Permission deny không leak data (chỉ ID + 403)
- [ ] Critical incident → CAPA tự sinh trong < 1 giây
- [ ] PDF biên bản (handover, cal cert) ký số / có metadata user

---

## 7. Lộ trình mở rộng testcase (Wave 3+)

Các module **chưa build** trong snapshot này:

| Module | Tên | Dự kiến |
|---|---|---|
| IMM-07 | Asset Performance Monitoring | Wave 3 |
| IMM-10 | Vendor Performance Tracking | Wave 3 |
| IMM-13 | Decommissioning | Wave 3 |
| IMM-14 | Disposal | Wave 3 |
| IMM-17 | Compliance Reporting (NĐ98 export) | Wave 3 |

Khi build module mới → thêm section `3.X` + cập nhật smoke test #14, 15...

---

## 8. Phụ lục — API endpoint reference

Liệt kê đầy đủ endpoint hiện có (snapshot 2026-05-07):

```
auth.py        : register_user, get_user_profile, update_my_profile, change_password
layout.py      : get_user_context, ping_session, logout_user, list_notifications, mark_*
user.py        : list_users, get_user_info, update_user_info, update_user_roles,
                 approve_registration, create_system_user, reset_user_password,
                 list_role_profiles, assign_role_profile
dashboard.py   : get_overview, get_dashboard_data
imm00.py       : list_assets, get_asset, create_asset, update_asset, transition_status,
                 update_gmdn_status, toggle_gmdn_status, get_asset_timeline,
                 validate_for_operations, get_asset_kpi,
                 list_suppliers, get/create/update_supplier, list_locations
imm01.py       : list/get/create/update_needs_request, transition_workflow,
                 submit_needs_request, score_needs_request, submit_budget_estimate,
                 approve/reject_needs_request, list_procurement_plans, roll_into_plan,
                 get_demand_forecast, dashboard_kpis
imm02.py       : list/get/create/update_tech_spec, draft_from_plan, transition_workflow,
                 get_market_benchmark, get_lock_in_assessment, lock_spec, withdraw_spec,
                 reissue_spec, submit_benchmark, submit_lock_in_assessment, dashboard_kpis
imm03.py       : list/create_evaluation, add_candidate, submit_quotations, score_evaluation,
                 list_avl, create_avl_entry, approve_avl, suspend_avl,
                 get_evaluation/decision/avl, list_decisions,
                 transition_eval/decision_workflow
imm04.py       : list_commissioning, get_form_context, get_barcode_lookup,
                 get_dashboard_stats, generate_qr_label, get_po_details, search_link,
                 check_sn_unique, list_non_conformances, generate_handover_pdf,
                 transition_state, submit_commissioning, save_commissioning,
                 create_commissioning, report_nonconformance
imm05.py       : list/get/create/update_document, approve/reject_document,
                 get_asset_documents, get_dashboard_stats, get_expiring_documents,
                 get_compliance_by_dept, get_document_history,
                 create_document_request, get_document_requests, mark_exempt
imm08.py       : list/get_pm_work_orders, assign_technician, submit_pm_result,
                 report_major_failure, reschedule_pm, create_pm_work_order,
                 get_pm_calendar, get_pm_dashboard_stats, get_asset_pm_history,
                 list/get/create/update_pm_schedule, set_pm_schedule_status
imm09.py       : list/get_repair_work_orders, create_repair_work_order, assign_technician,
                 submit_diagnosis, start_repair, request_spare_parts, close_work_order,
                 get_repair_kpis, get_asset_repair_history, search_spare_parts,
                 get_mttr_report
imm11.py       : list/get/create/update/delete_calibration_schedule,
                 list/get/create/update_calibration, submit_calibration,
                 add_measurement, get_calibration_kpis, get_calibration_dashboard,
                 get_asset_calibration_history, send_to_lab
imm12.py       : report_incident, cancel_incident, create_rca, get_rca, submit_rca,
                 get_asset_incident_history, get_chronic_failures, get_dashboard,
                 list/get_incidents, acknowledge_incident, resolve_incident,
                 close_incident, get_incident_stats
inventory.py   : warehouses CRUD, spare_parts CRUD, stock_movements CRUD/submit/cancel,
                 stock_overview/levels, search_parts_autocomplete, UOM CRUD + conversion
purchase.py    : list/get/create/update_purchase, submit/cancel/delete_purchase,
                 mark_received, get_purchase_movements, create_receipt_movement,
                 get_part_purchases, get_purchase_commissionings, search_purchases
depreciation.py: list_assets_depreciation, get_depreciation_stats,
                 compute_one_depreciation, compute_all_depreciation,
                 get_depreciation_schedule
```

---

**Hết tài liệu — phiên bản 2026-05-07.**
Mọi thay đổi luồng / API mới → cập nhật file này hoặc tạo bản `System_E2E_Flows_Testcases_<date>.md` mới và link từ `Module_Business_Flows_*.md`.
