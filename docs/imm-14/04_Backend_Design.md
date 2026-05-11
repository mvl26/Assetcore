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

*Hết file 04. Field detail + service code mẫu sẽ bổ sung trong sprint W3-1 sau khi BE scaffold.*
