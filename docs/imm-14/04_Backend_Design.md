# 04 — Backend Design (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | DocType + Workflow + Service 3-tier + Hooks |
| Owner | BE Architect |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |

> **From-scratch — BE chưa scaffold.** File này liệt kê *tên DocType dự kiến + mô tả*, *workflow state*, *service split*. Field detail và endpoint shape chốt khi sprint W3-1 scaffold.

---

## I. DocType dự kiến

| DocType | Loại | Vai trò | Ghi chú |
|---|---|---|---|
| `IMM Asset Closure` | Master (submittable) | Chứng từ duy nhất đóng vòng đời | Naming series `IMM-CL-.YYYY.-.####` (gợi ý) |
| `IMM Reconciliation Line` | Child of `IMM Asset Closure` | Mỗi dòng đối soát kho hoặc kế toán | Field `scope` ∈ {`spare_stock`, `book_value`, `work_order`, `document`} |
| `IMM Sanitization Item` | Child of `IMM Asset Closure` | Checklist sanitization PII/PHI | Mặc định 5–8 item; khoá role `DPO` |
| `IMM Closure Document` | Child of `IMM Asset Closure` | Đính kèm biên bản, ảnh, scan giấy | File attach + meta |

**Các DocType extend (không tạo mới)**:

- `AC Asset` — thêm field `has_patient_data` (Check), `closure_link` (Link → IMM Asset Closure), `decommissioned_on` (Date). *(Field detail chốt sprint W3-1.)*
- `Asset Lifecycle Event` — thêm event_type enum: `decommissioned`, `closure_rolled_back`. *(Sprint W3-1.)*
- `IMM Document` — gate `archived` chỉ được set bởi service IMM-14 (validator).

**Field detail**: *(Thiết kế trong sprint Wave 3-1 — refer skill `assetcore-doctype-designer`.)*

---

## II. Service layer (3-tier)

Theo `CONVENTIONS.md §2`. Module BE đặt tại `assetcore/services/imm14.py` + `assetcore/api/imm14.py` + `assetcore/repositories/closure_repo.py`.

```
assetcore/
├── api/imm14.py             # 1 file API (whitelist endpoints)
├── services/imm14.py        # ClosureService + 2 sub-service
└── repositories/
    ├── closure_repo.py      # ClosureRepo
    ├── asset_repo.py        # extend — set_status, lock
    └── document_repo.py     # extend — archive_for_asset
```

### II.1. ClosureService (orchestrator)

- `create_from_decision(decision_no) -> closure_no` — tạo draft + clone metadata từ Decommission Decision IMM-13.
- `validate_finalize(closure) -> ValidationResult` — kiểm tra BR-14-01, BR-14-02, BR-14-05, BR-14-07, BR-14-08.
- `run_finalize_transaction(closure)` — atomic: cập nhật asset_status, archive IMM-05 docs, sinh lifecycle event, log audit, emit hook.
- `run_rollback(closure, reason)` — đảo lifecycle, unarchive IMM-05 docs.

### II.2. ReconciliationService (sub)

- `load_open_wo(asset)` — query IMM-08 / IMM-09 / IMM-11 work order còn `Open` / `In Progress`.
- `load_spare_stock(asset)` — query IMM-15 stock theo asset.
- `load_book_value(asset)` — đọc `AC Asset.book_value` + `purchase_value`.
- `mark_line_done(line, decision)` — đánh dấu dòng đối soát đã xử lý.

### II.3. SanitizationService (sub)

- `load_template(asset)` — load checklist mặc định theo `gmdn_classification` (asset C/D bắt buộc nhiều item hơn).
- `sign(closure, dpo_user)` — ký xác nhận, ghi `signed_by`, `signed_at`.

### II.4. Repository

Repository **chỉ chứa câu query Frappe ORM**, không có business rule. Tham khảo `assetcore/repositories/repair_repo.py` làm pattern.

---

## III. Workflow `IMM Asset Closure`

| State | Docstatus | Allowed roles | Transition |
|---|---|---|---|
| Draft | 0 | HTM Engineer, PTP Khối 2 | → Reconciling (auto khi tạo lines) |
| Reconciling | 0 | HTM Engineer, Storekeeper, Accountant, DPO | → Pending Approval (khi 7 mục đầy đủ) |
| Pending Approval | 0 | PTP Khối 2 | → Closed (Approve) · → Reconciling (Send back) |
| Closed | 1 | Department Head | → Rollback Requested (Request rollback) |
| Rollback Requested | 1 | Accountant | → Reopened · → Closed (reject) |
| Reopened | 0 | HTM Engineer | → Reconciling (tiếp tục) |
| Cancelled | 2 | Department Head | terminal — chỉ khi closure lỗi nghiêm trọng |

Workflow JSON dự kiến `assetcore/assetcore/workflow/imm_14_closure_workflow.json` *(scaffold sprint W3-1 — refer skill `assetcore-workflow-builder`)*.

**Approval routing**: `Pending Approval → Closed` cần role `IMM-14 Approver` (gán cho Trưởng phòng VT-TBYT). `Rollback Requested → Reopened` cần role `IMM-14 Accountant`.

---

## IV. Hooks (`hooks.py` snippet dự kiến)

```python
# doc_events
"IMM Asset Closure": {
    "validate": "assetcore.services.imm14.on_validate",
    "on_submit": "assetcore.services.imm14.on_submit",   # kích hoạt run_finalize_transaction
    "on_cancel": "assetcore.services.imm14.on_cancel",
},
"AC Asset": {
    "before_save": "assetcore.services.imm14.guard_decommissioned_asset",  # BR-14-06
},

# scheduler_events — cron
"weekly": [
    "assetcore.services.imm14.cron_reconcile_spare_stock",   # đối soát kho định kỳ
    "assetcore.services.imm14.cron_alert_pending_long",       # alert closure quá 5 ngày
],
"monthly": [
    "assetcore.services.imm14.cron_dashboard_refresh",
],
```

*(Sprint W3-1 — chỉ là gợi ý; tên function cuối cùng theo BE scaffold.)*

---

## V. Permission model

| Role | Read | Write | Submit | Approve | Cancel |
|---|---|---|---|---|---|
| HTM Engineer | ✅ | ✅ (Draft, Reconciling) | ❌ | ❌ | ❌ |
| Storekeeper | ✅ | ✅ (only Reconciliation Line scope=spare_stock) | ❌ | ❌ | ❌ |
| Accountant | ✅ | ✅ (only scope=book_value) + rollback confirm | ❌ | ❌ | ❌ |
| DPO | ✅ | ✅ (only Sanitization Item) | ❌ | ❌ | ❌ |
| QLCL Officer | ✅ | ✅ (only Closure Document) | ❌ | ❌ | ❌ |
| Department Head (Approver) | ✅ | ❌ | ✅ (finalize) | ✅ | ✅ (cancelled) |
| Auditor (read-only) | ✅ | ❌ | ❌ | ❌ | ❌ |

Refer `CONVENTIONS.md §5` cho mẫu DocPerm và `assetcore-security` skill cho audit. *(Permission JSON chốt sprint W3-1.)*

---

## VI. Validation chính (theo Business Rules §IV)

| BR | Vị trí kiểm tra | Cơ chế |
|---|---|---|
| BR-14-01 (7 mục) | `validate_finalize` | Aggregate query, raise nếu thiếu |
| BR-14-02 (SoD) | `validate_finalize` | So `created_by` vs current user |
| BR-14-03 (single closure) | `before_insert` | Query active closure cho asset |
| BR-14-04 (rollback window) | `validate_rollback` | `frappe.utils.now() - closed_on ≤ window_days` |
| BR-14-05 (sanitization gate) | `validate_finalize` | Check `asset.has_patient_data` + sanitization signed |
| BR-14-06 (asset lock) | `AC Asset.before_save` hook | Block save nếu asset_status = decommissioned |
| BR-14-07 (archive hồ sơ) | `run_finalize_transaction` | Cùng transaction set IMM-05 docs `archived` |
| BR-14-08 (phụ tùng pending) | `validate_finalize` | Query reconciliation_line scope=spare_stock status=pending |

---

## VII. Error code (placeholder)

Theo `services/shared/constants.py` chuẩn AssetCore. Code dự kiến:

- `IMM14_INCOMPLETE` — closure thiếu mục bắt buộc
- `IMM14_SOD_VIOLATION` — người tạo = người duyệt
- `IMM14_DUPLICATE_CLOSURE` — đã có closure active
- `IMM14_ROLLBACK_EXPIRED` — quá rollback window
- `IMM14_SANITIZATION_REQUIRED` — asset có PHI nhưng chưa sign
- `IMM14_ASSET_LOCKED` — asset đã decommissioned
- `IMM14_DOCS_ARCHIVE_FAIL` — archive IMM-05 fail (transaction roll-back)
- `IMM14_OPEN_WO` — còn WO mở chưa đóng
- `IMM14_PENDING_RECONCILE` — còn dòng đối soát chưa xử lý

*(Code thật do BE scaffold sinh — refer `services/shared/constants.py`.)*

---

## VIII. Integration ngoài

- **IMM-13** input: subscribe `imm13_decision_approved` để gợi ý tạo closure.
- **IMM-15** outbound: emit `imm14_asset_closed` để IMM-15 cron đối soát kho.
- **IMM-16** outbound: emit `imm14_closure_evidence` để IMM-16 audit pack.
- **HIS / Kế toán ERP**: nếu có integration ERP tài chính, push closure → ERP để ghi sổ thanh lý (giai đoạn sau, ngoài Đợt 3 scope core).

---

---

## IX. Wave 2 MVP — Cổng "Hồ sơ giải nhiệm" (Decommission Closure Gate) — CHỐT ĐỂ CODE

> **Self-Correction (2026-06-04):** vòng 2 triển khai **một lát cắt hẹp** của IMM-14, KHÔNG phải toàn bộ thiết kế §I–§VIII (reconciliation 3-chiều, archive IMM-05, rollback 2-step, dashboard). Các phần đó GIỮ NGUYÊN làm `[ROADMAP]` Đợt 3. Hai chỉnh sửa thiết kế gốc:
> 1. **Tên DocType** §I gọi `IMM Asset Closure`. MVP vòng 2 dùng tên **`Asset Decommission`** (đặt theo họ DocType lifecycle hiện có: `Asset Commissioning`, `Asset Repair`, `Asset Transfer`). `IMM Asset Closure` (full reconciliation) là superset Đợt 3 — sẽ extend `Asset Decommission` thêm child tables, KHÔNG tạo DocType thứ 2 trùng vai.
> 2. **Error code** §VII/§05 liệt kê string `IMM14_*`. Codebase KHÔNG dùng string code module-local — dùng **semantic `ErrorCode` bucket** (`utils/response.py:ErrorCode`) + `message_code` (registry `MSG.*`). MVP vòng 2 raise `ServiceError(ErrorCode.BUSINESS_RULE | BAD_STATE | NOT_FOUND, <message VI>)` hoặc `InvalidAssetTransition`. Bảng `IMM14_*` ở §VII/§05 chỉ là *nhãn nghiệp vụ* tham chiếu, KHÔNG phải hằng số code.

### IX.1. Phạm vi vòng 2 (scope-fence)

**In:** DocType `Asset Decommission` (submittable) + gate chặn `lifecycle_status=Decommissioned` nếu chưa có closure approved + side-effect khi Approve + audit + entrypoint FE trên màn asset detail (IMM-00).

**Out (KHÔNG làm vòng này):** IMM-13 stand-down/reassignment/replacement-review; đối soát kho IMM-15 / sổ kế toán / IMM-05 archive; rollback; dashboard end-of-life; donation/sale logistics; print format.

### IX.2. DocType `Asset Decommission` (mới — submittable)

| Thuộc tính | Giá trị |
|---|---|
| Module | AssetCore |
| `is_submittable` | 1 (docstatus 0=Draft, 1=Approved, 2=Cancelled) |
| `autoname` | `naming_series:` → series `DECOM-.YYYY.-.####` |
| `track_changes` | 1 |
| `title_field` | `asset` |

**Fields:**

| fieldname | label (VI) | fieldtype | options / ràng buộc | reqd | ghi chú |
|---|---|---|---|---|---|
| `naming_series` | Số hồ sơ | Select | `DECOM-.YYYY.-.####` | 1 | hidden, default |
| `asset` | Thiết bị | Link | `AC Asset` | 1 | trỏ asset cần giải nhiệm |
| `asset_name_snapshot` | Tên thiết bị | Data | read_only | 0 | fetch_from `asset.asset_name` (snapshot) |
| `risk_classification_snapshot` | Phân loại rủi ro | Data | read_only | 0 | fetch_from `asset.risk_classification` (snapshot, drive gate IX.4-BR3) |
| `disposal_method` | Phương thức xử lý | Select | `Huỷ\nĐiều chuyển/Donation\nBán/Trade-in\nLưu trữ` | 1 | BR-14-W2-02 |
| `decommission_reason` | Lý do giải nhiệm | Small Text | length ≥ 20 ký tự (BR-14-W2-04) | 1 | free-text |
| `patient_data_sanitized` | Đã xử lý dữ liệu bệnh nhân | Check | default 0 | 0* | *BẮT BUỘC=1 khi risk High/Critical (BR-14-W2-03) |
| `sanitization_note` | Ghi chú xử lý dữ liệu | Small Text | — | 0 | mô tả phương thức xoá/huỷ ổ lưu |
| `responsible` | Người chịu trách nhiệm | Link | `User` | 1 | người ký duyệt (BR-14-W2-05) |
| `decommissioned_on` | Ngày giải nhiệm | Datetime | read_only | 0 | set khi Approve thành công |
| `workflow_state` | Trạng thái | Select (workflow) | `Draft\nApproved\nCancelled` | 0 | đồng bộ docstatus |

> `risk_classification` của `AC Asset` ∈ {Low, Medium, High, Critical} ≡ NĐ98 lớp A/B/C/D. "C/D" trong acceptance = **High / Critical**. Snapshot vào record lúc tạo để gate ổn định kể cả khi asset bị sửa sau.

### IX.3. Service & API (3-tier)

```
assetcore/
├── api/imm14.py              # 2 whitelist endpoints (NEW)
├── services/imm14.py         # DecommissionService (NEW)
└── (controller) assetcore/doctype/asset_decommission/asset_decommission.py  # validate/on_submit/on_cancel → delegate service
```

**`services/imm14.py` — hàm chính:**

| Hàm | Chữ ký | Trách nhiệm |
|---|---|---|
| `create_decommission(asset, disposal_method, decommission_reason, patient_data_sanitized, responsible, sanitization_note="")` | → `dict` (closure record meta) | Tạo `Asset Decommission` docstatus=0. Validate field-level + BR-14-W2-06 (terminal) + BR-14-W2-07 (duplicate). KHÔNG đổi asset status. |
| `validate_before_approve(doc)` | → `None` (raise) | Gọi trong controller `validate`/`before_submit`: kiểm BR-14-W2-02..05. Thiếu field → `ServiceError(BUSINESS_RULE, <VI>)`. |
| `on_decommission_submit(doc, method=None)` | → `None` | Hook `on_submit`. **Idempotent.** Gọi `transition_asset_status(asset, AssetStatus.DECOMMISSIONED, actor, root_doctype="Asset Decommission", root_record=doc.name)`. Set `decommissioned_on`. |
| `on_decommission_cancel(doc, method=None)` | → `None` | Hook `on_cancel`. Out-of-scope vòng 2 (rollback) → cho cancel record nhưng KHÔNG đảo asset status (ghi audit "Cancelled, asset status giữ Decommissioned"). |
| `assert_decommission_gate(asset)` | → `None` (raise) | **GATE chính** — gọi từ `AC Asset` controller (xem IX.5). Raise nếu set `lifecycle_status=Decommissioned` mà KHÔNG có `Asset Decommission` docstatus=1 trỏ đúng asset. |

**Quan hệ với `transition_asset_status` (KHÔNG viết lại side-effect):**

`transition_asset_status(to=Decommissioned)` (đã có ở `services/imm00.py:92`) ĐÃ tự:
- (a) chạy state-machine guard + **NEG-09** (chặn nếu asset đang Under Maintenance/Repair/Calibrating) — GIỮ NGUYÊN.
- (b) ghi đúng 1 `Asset Lifecycle Event` `event_type='decommissioned'` (qua `_lifecycle_event_for`) với `root_record` truyền vào = tên closure record.
- (c) ghi 1 `IMM Audit Trail` `event_type='State Change'`, `change_summary` = `lifecycle_status: <from> -> Decommissioned. <reason>`.
- (d) `_cancel_pending_depreciation(asset)` + `_record_depreciation_stopped(...)` — Pending → Cancelled.

⇒ `on_decommission_submit` CHỈ gọi `transition_asset_status` với `reason` chứa `disposal_method` + `patient_data_sanitized` (để (c) `change_summary` chứa 2 trường này theo acceptance). **KHÔNG** tự ghi lifecycle event / audit / cancel depreciation lần nữa (tránh double).

> **Acceptance (c) "audit change_summary chứa disposal_method + patient_data_sanitized":** đạt được bằng cách build `reason = f"Phương thức: {disposal_method}. Đã xử lý dữ liệu bệnh nhân: {'Có' if patient_data_sanitized else 'Không'}. Closure: {doc.name}."` rồi truyền vào `transition_asset_status(..., reason=reason, root_doctype="Asset Decommission", root_record=doc.name)`. `transition_asset_status` nối `reason` vào `change_summary`.

### IX.4. Business rules vòng 2

| BR | Kiểm ở đâu | Cơ chế |
|---|---|---|
| **BR-14-W2-01 (GATE)** | `AC Asset` controller `validate`/`on_update` → `assert_decommission_gate` | KHÔNG cho `lifecycle_status` đổi sang `Decommissioned` nếu không tồn tại `Asset Decommission` docstatus=1, asset=this. Vi phạm → `InvalidAssetTransition`/`ServiceError(BAD_STATE)`, lifecycle_status GIỮ NGUYÊN. |
| BR-14-W2-02 (disposal_method) | `validate_before_approve` | `disposal_method ∈ {Huỷ, Điều chuyển/Donation, Bán/Trade-in, Lưu trữ}`, không rỗng. |
| BR-14-W2-03 (sanitization gate) | `validate_before_approve` | Nếu `risk_classification_snapshot ∈ {High, Critical}` ⇒ `patient_data_sanitized` PHẢI = 1. Thiếu → throw. (Low/Medium: khuyến nghị nhưng không chặn.) |
| BR-14-W2-04 (reason) | `validate_before_approve` | `len(decommission_reason.strip()) ≥ 20`. |
| BR-14-W2-05 (responsible) | `validate_before_approve` | `responsible` không rỗng (người ký). |
| BR-14-W2-06 (terminal/idempotent) | `create_decommission` + `assert_decommission_gate` | Asset đã `Decommissioned` → tạo/Approve closure thứ 2 cho cùng asset bị chặn (`ServiceError(BAD_STATE, "Thiết bị đã giải nhiệm…")`). |
| BR-14-W2-07 (single active) | `create_decommission` | Đã có `Asset Decommission` docstatus∈{0,1} cho asset → chặn tạo mới (`ServiceError(CONFLICT)`). |
| BR-14-W2-08 (no double effect) | `on_decommission_submit` | `transition_asset_status` đã guard `prev==to → return`; nếu asset đã Decommissioned khi submit chạy lại ⇒ no double event/cancel. |
| NEG-09 (reuse) | `transition_asset_status` | Asset đang Under Maintenance/Repair/Calibrating → Approve closure vẫn raise `InvalidAssetTransition`, lifecycle_status GIỮ NGUYÊN. |

### IX.5. GATE wiring (BR-14-W2-01 — chống set-value vòng sau)

Theo Pattern D (`assetcore-doc` Phần 3): **KHÔNG** ai được `frappe.db.set_value("AC Asset", name, "lifecycle_status", "Decommissioned")` trực tiếp. Cổng đặt 2 lớp:

1. **Lớp service (chính):** mọi đường vào Decommissioned PHẢI qua `transition_asset_status`. `transition_asset_status` thêm 1 guard: nếu `to_status == DECOMMISSIONED` và `root_doctype != "Asset Decommission"` (hoặc thiếu closure approved cho asset) → gọi `assert_decommission_gate(asset)` raise. Closure tự nó truyền `root_doctype="Asset Decommission"` nên qua được.
2. **Lớp controller `AC Asset`:** trong `validate`/`before_save`, nếu `lifecycle_status` đổi thành `Decommissioned` bằng đường khác (sửa form tay, import) mà không có closure approved → raise (`assert_decommission_gate`).

> **Same-commit wiring rule:** định nghĩa `on_decommission_submit` + `assert_decommission_gate` → CÙNG commit phải wire vào `hooks.py::doc_events["Asset Decommission"]` (`on_submit`/`on_cancel`) + bổ sung gate vào `AC Asset` controller. Listener bắt buộc chữ ký `def on_decommission_submit(doc, method=None)`.

### IX.6. hooks.py snippet (CHỐT)

```python
doc_events = {
    # ...
    "Asset Decommission": {
        "validate": "assetcore.services.imm14.validate_before_approve",
        "on_submit": "assetcore.services.imm14.on_decommission_submit",
        "on_cancel": "assetcore.services.imm14.on_decommission_cancel",
    },
}
```

---

## X. Vòng 17 — `get_decommission` enrich `can_approve` + `approve_blocked_reason` (server-driven CTA) — CHỐT

> **Delta (2026-07-10).** Không đụng DocType schema, không đổi capability/DocPerm. Chỉ (a) thêm 1 SoT predicate `_evaluate_approvability`; (b) `get_decommission` phát thêm 2 khoá; (c) 3 MSG entry mới. Ref ADR-IMM14-APPROVE-04 (`02 §VIII.5`).

### X.1. `get_decommission` — output delta

`services/imm14.py::get_decommission(name)` (hiện trả `doc.as_dict()` + `asset_name`/`responsible_name`/`lifecycle_status`) thêm 2 khoá:

| Khoá | Kiểu | Nguồn |
|---|---|---|
| `can_approve` | int (0/1) | `_evaluate_approvability(doc)[0]` |
| `approve_blocked_reason` | str (VI, "" khi can=1) | `_evaluate_approvability(doc)[1]` |

Invariant: `approve_blocked_reason != "" ⇔ can_approve == 0` (BR-14-W2-13). Các khoá detail còn lại (asset_name, responsible_name, risk_classification_snapshot, disposal_method, decommission_reason, patient_data_sanitized, sanitization_note, workflow_state, docstatus, decommissioned_on, lifecycle_status) GIỮ NGUYÊN — đủ cho `DecommissionDetailView`.

### X.2. `_evaluate_approvability(doc) -> tuple[int, str]` — SoT DUY NHẤT (BR-14-W2-13)

```python
def _evaluate_approvability(doc) -> tuple[int, str]:
    """SoT cho can_approve + reason. Reuse validate_before_approve (KHÔNG copy field-rule).

    Precedence (first match → blocked): docstatus terminal record → capability →
    asset terminal → field/sanitization validation. Reason resolve qua MSG registry.
    """
    # 1. Record đã ở trạng thái cuối (không phải Draft) → không duyệt lại.
    if doc.docstatus == 2:
        return 0, _reason(MSG.IMM14_APPROVE_BLOCKED_CANCELLED)
    if doc.docstatus == 1:
        return 0, _reason(MSG.IMM14_APPROVE_BLOCKED_ALREADY_APPROVED)
    # 2. Capability (boolean, KHÔNG raise) — Commissioning User read=1/submit=0 → 0.
    if not rbac.can("decommission.approve"):
        return 0, _reason(MSG.IMM14_APPROVE_BLOCKED_NO_PERMISSION)
    # 3. Asset đã Decommissioned bởi record khác (terminal).
    if frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "lifecycle_status") == AssetStatus.DECOMMISSIONED:
        return 0, _reason(MSG.IMM14_ALREADY_DECOMMISSIONED, asset=doc.asset)
    # 4. Field/sanitization gate — REUSE validate_before_approve (SoT field-rule).
    try:
        validate_before_approve(doc)
    except ServiceError as e:   # nthrow → ServiceError mang message VI đã format.
        return 0, e.message     # ⚠️ e.message (VI thuần), KHÔNG str(e).
    return 1, ""
```

- **`_reason(code, **ctx)`** helper: `return format_message(code, ctx)[1]` (`utils/messages.format_message` → phần message đã render VI). KHÔNG hardcode chuỗi VI trong service.
- **⚠️ `e.message` KHÔNG `str(e)`:** `ServiceError.__str__` = `f"[{code}] {message}"` (`services/shared/errors.py:51`) → `str(e)` **rò prefix `[BUSINESS_RULE]`** ra hint. Dùng `e.message` (errors.py:46 = message VI đã render) cho `approve_blocked_reason`.
- **KHÔNG duplicate logic:** field-rule (disposal_method / reason≥20 / responsible / patient_data C-D) CHỈ định nghĩa trong `validate_before_approve` — predicate gọi lại + bắt raise. Terminal/docstatus/capability là atoms `approve_decommission` cũng dùng (guard docstatus, terminal check, `rbac.require` ở API). ⇒ `can_approve` ↔ `approve_decommission` không drift (ADR-IMM14-APPROVE-04).
- **`rbac.can` không raise** (rbac.py:163 — cap thiếu → False). An toàn khi worker cũ / cap stale → degrade thành `can_approve=0` (nút ẩn), KHÔNG 500.
- **Read-only:** `validate_before_approve(doc)` chỉ đọc field in-memory (không `db.set_value`/insert) → gọi trong GET không mutate. `get_decommission` KHÔNG sinh event/audit (BR-14-W2-12 vẫn giữ).

### X.3. MSG registry — 3 entry mới (`utils/messages.py`, cùng commit BE)

| MSG code | template (VI) | severity | http_status |
|---|---|---|---|
| `IMM14_APPROVE_BLOCKED_NO_PERMISSION` | "Bạn không đủ quyền duyệt giải nhiệm." | info | 200 |
| `IMM14_APPROVE_BLOCKED_ALREADY_APPROVED` | "Hồ sơ giải nhiệm đã được duyệt." | info | 200 |
| `IMM14_APPROVE_BLOCKED_CANCELLED` | "Hồ sơ giải nhiệm đã bị huỷ." | info | 200 |

- Các reason còn lại reuse template SẴN CÓ: `IMM14_ALREADY_DECOMMISSIONED` (asset terminal), `IMM14_PATIENT_DATA_REQUIRED` (C/D chưa xử lý PII), `IMM14_REASON_TOO_SHORT`, `IMM14_DISPOSAL_METHOD_REQUIRED`/`_INVALID`, `IMM14_RESPONSIBLE_REQUIRED` (qua raise trong `validate_before_approve`).
- 3 entry mới dùng cho **hint hiển thị** (không phải error envelope) → severity `info`, http_status 200 (chỉ để đủ shape `MessageEntry`; predicate chỉ lấy `[1]` = message).

### X.4. Boundaries (Always / Never)

- **Always:** `can_approve`/`reason` từ 1 SoT `_evaluate_approvability`; reason từ MSG registry; enrich chỉ đọc; `approve_decommission` giữ `rbac.require('decommission.approve')` (BE là SoT — FE ẩn nút chỉ là UX).
- **Never:** KHÔNG reimplement field-rule trong predicate (reuse `validate_before_approve`); KHÔNG hardcode chuỗi VI; KHÔNG mutate trong `get_decommission`; KHÔNG đổi DocType schema / DocPerm / capability map; KHÔNG chạy `doc.submit()` để test-approvability trong GET.

*Hết file 04. Field detail + service code mẫu sẽ bổ sung trong sprint W3-1 sau khi BE scaffold. §IX là CHỐT cho MVP vòng 2; §X là CHỐT cho vòng 17.*
