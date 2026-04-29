# Wave 2 Alignment — IMM-01 / IMM-02 / IMM-03

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | LIVE — phải đọc trước khi triển khai Wave 2 |
| Phạm vi | Hiệu chỉnh các tài liệu IMM-01, IMM-02, IMM-03 cho khớp **Wave 1 thực tế** trên codebase |

---

## Mục đích

Bộ tài liệu IMM-01 / 02 / 03 ban đầu (v0.1.0) viết theo bootstrap plan và ở mức ý niệm. Khi đối chiếu codebase Wave 1 đã chạy LIVE (IMM-00, IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12) phát hiện một số chỗ **không khớp convention thực tế**.

Tài liệu này là **bản ghi đè bắt buộc** — khi triển khai Wave 2, mọi điểm sau đây trong file IMM-0x_*.md phải được thay theo bảng dưới (không cần chỉnh thủ công ở tất cả vị trí; coi tài liệu này là source of truth cuối).

---

## 1. Module Frappe & cấu trúc thư mục

| Trong docs IMM-01/02/03 ban đầu | Wave 1 thực tế |
|---|---|
| `module imm_planning`, `imm_master`, `imm_eol` | **Chỉ một module** Frappe: `AssetCore` (xem `assetcore/modules.txt`) |
| Folder `assetcore/imm_planning/doctype/...` | Tất cả DocType ở `assetcore/assetcore/doctype/<doctype_name>/` (snake_case) |
| Service `assetcore/services/imm01.py` | ✅ Khớp — Wave 1 đã có `services/imm04.py`, `services/imm05.py`, ... → IMM-01/02/03 thêm `services/imm01.py`, `services/imm02.py`, `services/imm03.py` |
| API `assetcore/api/imm01.py` | ✅ Khớp — Wave 1 đã có `api/imm04.py`, `api/imm05.py`, ... |
| Workflow `assetcore/assetcore/workflow/imm_0x_*.json` | ✅ Khớp |

**→ Thay khi đọc:** mỗi chỗ docs ghi `module imm_planning` đọc thành `module AssetCore`.

---

## 2. Naming series (transactions IMM-01/02/03)

Wave 1 chuẩn: `IMM04-.YY.-.MM.-.#####`, `IMM05-.YY.-.MM.-.#####`, `AC-PUR-.YYYY.-.#####`.

| DocType (mới) | Naming series chuẩn Wave 2 |
|---|---|
| IMM Needs Request | `IMM01-NR-.YY.-.MM.-.#####` (thay `NR-…` trong docs) |
| IMM Procurement Plan | `IMM01-PP-.YY.-.#####` |
| IMM Demand Forecast | `IMM01-DF-.YYYY.-.#####` |
| IMM Tech Spec | `IMM02-TS-.YY.-.#####` |
| IMM Market Benchmark | `IMM02-MB-.YY.-.#####` |
| IMM Lock-in Risk Assessment | `IMM02-LR-.YY.-.#####` |
| IMM Vendor Evaluation | `IMM03-VE-.YY.-.#####` |
| IMM Procurement Decision | `IMM03-PD-.YY.-.#####` |
| IMM AVL Entry | `IMM03-AVL-.YYYY.-.#####` |
| IMM Vendor Scorecard | `IMM03-VS-.YYYY.-.QN-{Vendor}` |
| IMM Supplier Audit | `IMM03-SA-.YY.-.#####` |

**→ Thay khi đọc:** tiền tố naming series ở Module Overview §3 và Technical Design §2 các module 01/02/03.

---

## 3. DocType ngoại vi đã tồn tại Wave 1 (KHÔNG được tạo mới hoặc extend ERPNext core)

Bộ docs ban đầu nói "extend Supplier ERPNext", "mint Purchase Order ERPNext", "Asset (ERPNext core)" — **SAI**. Wave 1 đã tự xây bộ DocType core riêng.

| Khi docs ghi | Đọc thành (Wave 1 thực tế) |
|---|---|
| ERPNext `Supplier` | `AC Supplier` |
| ERPNext `Purchase Order` | `AC Purchase` (đã có; dùng child `AC Purchase Device Item` cho thiết bị, `AC Purchase Item` cho phụ tùng) |
| ERPNext `Asset` | `AC Asset` |
| ERPNext `Asset Category` | `AC Asset Category` |
| ERPNext `Department` | `AC Department` |
| ERPNext `Location` | `AC Location` |
| `IMM Device Model` | ✅ giữ nguyên — đã có Wave 1 |
| Asset Commissioning, Asset Document, Asset Lifecycle Event, IMM Audit Trail, IMM CAPA Record | ✅ đã có Wave 1 — reuse |

### Hệ quả cho IMM-03:

- **Vendor Profile** không phải link `Supplier`; là field bổ sung trên `AC Supplier` (custom field) **HOẶC** một DocType mới `IMM Vendor Profile` link 1:1 về `AC Supplier`. Khuyến nghị: dùng custom field trên `AC Supplier` cho mức cơ bản (avl_status, avl_categories, last_audit_date, next_audit_date, overall_score, certifications) — chỉ tách `IMM Vendor Profile` nếu cần workflow riêng. Quyết định cuối: theo brainstorm khi mở sprint.
- **Procurement Decision → mint PO**: thay "tạo ERPNext Purchase Order" thành "tạo `AC Purchase` với `naming_series=AC-PUR-.YYYY.-.#####`, link `supplier`→`AC Supplier`, child `devices`→`AC Purchase Device Item`". Custom field bổ sung trên `AC Purchase`: `imm_procurement_decision`, `imm_tech_spec`, `imm_funding_source`.
- **PO direct-create gating** (BR-03-08): hook validate trên `AC Purchase` thay vì ERPNext `Purchase Order`.

---

## 4. Lifecycle event & audit trail — REUSE

Wave 1 đã có 2 cơ chế audit:

| DocType | Vai trò | Khi dùng |
|---|---|---|
| `Asset Lifecycle Event` | Sự kiện gắn 1 `AC Asset` (event_type, from_status, to_status, actor, timestamp, root_record) | Khi đã có Asset (post IMM-04 commissioning) |
| `IMM Audit Trail` | Audit cross-cutting (mọi DocType, không cần asset) | Pre-asset (IMM-01/02/03) hoặc các action không gắn 1 asset cụ thể |

**→ Thay khi đọc:** docs IMM-01/02/03 nói "child table `Needs/Spec/Decision Lifecycle Event`" → **bỏ** child table riêng; ghi audit qua `IMM Audit Trail` (1 row per state change, link `root_doctype=IMM Needs Request`, `root_record=name`). VR-06 (immutable) áp dụng cấp `IMM Audit Trail`, không lặp lại trên từng module.

Workflow transitions vẫn lưu ở `workflow_state` field; chi tiết transition được derive từ `IMM Audit Trail` query.

---

## 5. API response envelope & error codes

### Envelope đã sai trong docs

Docs viết:
```json
{ "message": { "ok": true, "data": ... } }
```

**Wave 1 thực tế** (assetcore/utils/helpers.py + utils/response.py):
```json
// success
{ "success": true, "data": ... }

// error
{ "success": false, "error": "<human msg>", "code": "<MACHINE_CODE>" }
```

→ Mọi mục §1 "Conventions" và §3 ví dụ response trong `IMM-0x_API_Interface.md` cần đọc thành envelope này. Helper bắt buộc dùng:

```python
from assetcore.utils.helpers import _ok, _err
from assetcore.services.shared import ErrorCode, ServiceError
```

### Error codes — bộ chuẩn duy nhất

Wave 1 dùng enum trong `assetcore/services/shared/constants.py`:

| Code | HTTP gợi ý | Khi nào |
|---|---|---|
| `VALIDATION` | 400 | Field-level validation |
| `INVALID_PARAMS` | 400 | Tham số API sai dạng |
| `BUSINESS_RULE` | 422 | Vi phạm BR/Gate/VR nghiệp vụ |
| `BAD_STATE` | 409 | Workflow transition không hợp lệ |
| `CONFLICT` | 409 | Trùng lặp / xung đột |
| `DUPLICATE` | 409 | Vi phạm unique |
| `NOT_FOUND` | 404 | Resource không tồn tại |
| `FORBIDDEN` | 403 | Thiếu quyền |
| `UNAUTHORIZED` | 401 | Chưa đăng nhập |
| `RATE_LIMITED` | 429 | Throttle |
| `INTERNAL` | 500 | Lỗi không xác định |

**→ Thay trong docs:** mọi `VR-01-02`, `G01`, `WORKFLOW-INVALID`, `PERM-DENY`, `PO-MINT-FAIL` đọc theo bảng:

| Docs ghi | Code chuẩn Wave 1 |
|---|---|
| `VR-0x-yy` (validation) | `VALIDATION` (kèm `fields[<field>] = <msg>` cho field-level) |
| `G0x` (gate) | `BUSINESS_RULE` (kèm `error="G0x: <message>"`) |
| `WORKFLOW-INVALID` | `BAD_STATE` |
| `PERM-DENY` | `FORBIDDEN` |
| `NOT-FOUND` | `NOT_FOUND` |
| `PO-MINT-FAIL` | `INTERNAL` (rollback decision) |

VR-id và Gate-id (`VR-01-02`, `G01`) **vẫn được giữ** ở các bảng Business Rules / Validation Rules trong Functional Specs và Technical Design (để traceability), nhưng client **không bao giờ thấy chuỗi đó là `code` — chỉ thấy ErrorCode chuẩn**. Mã VR/Gate chỉ xuất hiện ở `error` message và log.

---

## 6. Frappe Role names (ánh xạ tổ chức → Role)

Docs gắn nhãn theo vai trò tổ chức (ĐT-HĐ-NCC, KH-TC, TCKT, PTP Khối 1, VP Block1, ...). Trong Frappe Role chỉ có những role thực tế Wave 1 đã tạo. Wave 2 cần **bổ sung 6 role mới** + tận dụng role hiện có.

### Role đã có Wave 1 (reuse)

| Role | Module trước đây dùng |
|---|---|
| IMM System Admin | IMM-00, IMM-04 |
| IMM Operations Manager | IMM-04, IMM-08, IMM-09 |
| IMM QA Officer | IMM-04, IMM-05, IMM-10 |
| IMM Auditor | IMM-00, IMM-05 |
| IMM Department Head | IMM-04 |
| IMM Deputy Department Head | IMM-04 |
| IMM Workshop Lead | IMM-04, IMM-08, IMM-09 |
| IMM Biomed Technician | IMM-04 |
| IMM Technician | IMM-08, IMM-09 |
| IMM Storekeeper | IMM-09 |
| IMM Document Officer | IMM-05 |
| IMM Clinical User | IMM-04 (clinical justification) |

### Role mới cần thêm cho Wave 2 (qua fixture)

| Role mới | Tổ chức tương ứng | Dùng cho |
|---|---|---|
| `IMM Planning Officer` | KH-TC Officer (Khối 1) | IMM-01 scoring, IMM-02 benchmark, IMM-03 commercial scoring |
| `IMM Finance Officer` | TCKT Officer | IMM-01 budget estimate, IMM-03 financial scoring + Contract Signed |
| `IMM HTM Engineer` | Nhóm HTM | IMM-02 Tech Spec drafting, IMM-03 technical scoring |
| `IMM Procurement Officer` | ĐT-HĐ-NCC Officer | IMM-03 vendor profile / evaluation / decision |
| `IMM Risk Officer` | QA Risk Team (mở rộng) | IMM-02 lock-in risk + infra compat, IMM-03 supplier audit |
| `IMM Board Approver` | VP Block1 / BGĐ | IMM-01 final approve, IMM-02 lock spec, IMM-03 award decision |

(`IMM Department Head` đã có thể đóng vai trò "PTP Khối 1" cho điều phối / submit step — không cần thêm role.)

**→ Thay khi đọc Module Overview §7 và Functional Specs §2:** mọi nhãn tổ chức dịch sang `IMM <Role>` theo bảng trên. Permission JSON DocType sẽ dùng tên Frappe Role chuẩn.

---

## 7. AVL — không có DocType riêng ở Wave 1

Phương án thực thi:

- **Custom fields bổ sung trên `AC Supplier`** (Wave 2 patch):
  - `imm_avl_status` (Select: Approved / Conditional / Suspended / Expired / Not Applicable)
  - `imm_avl_categories` (Small Text — comma list)
  - `imm_overall_score` (Float)
  - `imm_last_audit_date`, `imm_next_audit_date` (Date)
- **DocType mới `IMM AVL Entry`** giữ phiếu cấp/gia hạn AVL với workflow 4 state — khi submit thì cập nhật custom field tương ứng trên `AC Supplier`.
- **`IMM Vendor Profile`** — KHÔNG tạo DocType riêng nữa; thay bằng:
  - Custom fields bổ sung trên `AC Supplier`: `legal_name`, `vat_code`, `country`, `rep_name`, `rep_phone`, `rep_email`, `bank_name`, `bank_account`, `device_categories`, `scope_of_supply`, `financial_health` (đã có sẵn một phần — kiểm tra `ac_supplier.json` rồi thêm phần còn thiếu).
  - Child table `Vendor Cert` (DocType mới) gắn vào `AC Supplier` qua field `certifications`.

**→ Thay trong IMM-03 Module Overview §3 và Technical Design §2:** "IMM Vendor Profile" → "Custom fields trên AC Supplier + child table Vendor Cert".

---

## 8. Reference data dictionary — fields đã tồn tại

Trong `docs/assetcore-bootstrap/data-dictionary.md` đã có các custom field standard:

- `AC Asset.imm_device_model`, `imm_medical_device_class`, `imm_registration_number`, `imm_lifecycle_status`, `imm_risk_class`, `imm_department`.
- IMM Device Model fields chuẩn (model_name, manufacturer, country_of_origin, device_category, medical_device_class, gmdn_code, hsn_code, risk_classification, recommended_pm_frequency, ...).

→ IMM-01/02/03 phải reuse các field này khi link sang AC Asset / IMM Device Model thay vì tự định nghĩa lại.

---

## 9. Workflow JSON path & convention

Wave 1 đặt workflow JSON tại `assetcore/assetcore/workflow/imm_NN_<purpose>_workflow.json`. Wave 2 dự kiến:

| Module | File workflow |
|---|---|
| IMM-01 | `imm_01_needs_workflow.json` (8 state) |
| IMM-01 | `imm_01_plan_workflow.json` (4 state cho Procurement Plan: Draft/Approved/Active/Closed) |
| IMM-02 | `imm_02_spec_workflow.json` (7 state) |
| IMM-03 | `imm_03_vendor_eval_workflow.json` (5 state) |
| IMM-03 | `imm_03_decision_workflow.json` (9 state) |
| IMM-03 | `imm_03_avl_workflow.json` (4 state) |

Tất cả workflow phải có:
- `workflow_state_field = workflow_state` (default Wave 1)
- Action label tiếng Việt
- Allowed Roles theo §6 trên

---

## 10. Hooks & Scheduler — append vào hooks.py hiện hữu

Wave 1 `hooks.py` đã có các scheduler entry IMM-00/04/05/08/09/11/12. Wave 2 chỉ **append** thêm — KHÔNG ghi đè:

```python
scheduler_events = {
    "daily": [
        # ... Wave 1 entries ...
        # Wave 2 IMM-01
        "assetcore.services.imm01.check_pending_request_overdue",
        # Wave 2 IMM-02
        "assetcore.services.imm02.check_overdue_drafts",
        # Wave 2 IMM-03
        "assetcore.services.imm03.check_avl_expiry",
        "assetcore.services.imm03.check_audit_due",
        "assetcore.services.imm03.check_decision_overdue",
    ],
    "weekly": [
        # ... Wave 1 entries ...
        "assetcore.services.imm01.budget_envelope_alert",
        "assetcore.services.imm02.benchmark_freshness_alert",
    ],
    "monthly": [
        "assetcore.services.imm01.generate_demand_forecast",
    ],
    "quarterly": [
        "assetcore.services.imm02.compatibility_recheck",
        "assetcore.services.imm03.update_vendor_scorecard",
    ],
}
```

Lưu ý Frappe v15 chỉ hỗ trợ keys: `all`, `hourly`, `daily`, `weekly`, `monthly`, `cron`. **Không có `quarterly`** — phải dùng `cron` với expression `0 2 1 1,4,7,10 *` cho job quarterly. **→ Sửa trong docs:** mọi chỗ ghi "scheduler quarterly" đọc thành "scheduler cron quarterly (1/4/7/10 hàng năm)".

---

## 11. Patches & migration

Wave 1 patches ở `assetcore/patches/`. Wave 2 patches phải đăng ký trong `assetcore/patches.txt`. Convention version path: `assetcore.patches.v15_NN.<patch_name>`.

| Patch | Mục đích |
|---|---|
| `v15_05.create_imm01_doctypes` | Bootstrap IMM Needs Request, Procurement Plan, Demand Forecast + child tables |
| `v15_05.install_imm01_workflows` | Load 2 workflow JSON IMM-01 |
| `v15_05.seed_priority_weights` | Seed default scoring weights |
| `v15_06.create_imm02_doctypes` | IMM Tech Spec + Market Benchmark + Lock-in Risk |
| `v15_06.install_imm02_workflow` | Workflow IMM-02 |
| `v15_06.seed_lock_in_weights` | Default lock-in dimension weights |
| `v15_07.create_imm03_doctypes` | IMM Vendor Evaluation + Procurement Decision + AVL Entry + Scorecard + Supplier Audit |
| `v15_07.add_supplier_imm_fields` | Custom fields lên AC Supplier (avl_status, avl_categories, ...) |
| `v15_07.add_purchase_imm_fields` | Custom fields lên AC Purchase (imm_procurement_decision, imm_tech_spec, imm_funding_source) |
| `v15_07.install_imm03_workflows` | 3 workflow JSON IMM-03 |
| `v15_07.seed_eval_criteria_default` | Default criteria 5 nhóm |
| `v15_07.seed_procurement_method_config` | Master ngưỡng theo NĐ + Luật Đấu thầu 22/2023 |
| `v15_07.add_imm_planning_roles` | Tạo 6 IMM Role mới (§6) |

---

## 12. Definition of Done bổ sung cho Wave 2

Mỗi module IMM-01 / 02 / 03 ngoài DoD trong Functional Specs còn phải:

- [ ] Reuse `AC Supplier` / `AC Purchase` / `AC Asset` / `AC Department` / `IMM Device Model` / `IMM Audit Trail` / `IMM CAPA Record` (không tạo trùng).
- [ ] Tất cả endpoint dùng envelope `{success, data|error, code}` qua `_ok` / `_err`.
- [ ] Error code thuộc `assetcore.services.shared.ErrorCode` enum.
- [ ] Permission JSON dùng đúng tên Frappe Role (Wave 1 reuse + 6 role Wave 2 thêm).
- [ ] Naming series tiền tố `IMM01-…` / `IMM02-…` / `IMM03-…` (hoặc `AC-PUR-…` cho PO).
- [ ] Audit trail ghi qua `IMM Audit Trail`, KHÔNG tạo lifecycle event DocType riêng.
- [ ] Hook + scheduler append (không ghi đè) vào `hooks.py`.
- [ ] Workflow JSON theo path `assetcore/assetcore/workflow/imm_0x_*.json`.
- [ ] Patches đăng ký đúng `patches.txt`, version `v15_05` / `v15_06` / `v15_07`.
- [ ] Toàn bộ message lỗi tiếng Việt; field label tiếng Việt.

---

## 13. Quy trình đọc tài liệu Wave 2

Khi triển khai một module IMM-01 / 02 / 03:

1. **Bắt đầu** đọc file này (`WAVE2_ALIGNMENT.md`) — coi là source of truth.
2. Đọc `IMM-0x_Module_Overview.md` để nắm phạm vi + workflow + dependency.
3. Đọc `IMM-0x_Functional_Specs.md` để nắm user story + acceptance.
4. Đọc `IMM-0x_Technical_Design.md` để biết schema và logic.
   → **Áp dụng các sửa đổi §1–§12 ở trên** mỗi khi bắt gặp ký hiệu lệch.
5. `IMM-0x_API_Interface.md` — đặc biệt §1 envelope và §5 error codes phải đọc theo §5 file này.
6. `IMM-0x_UI_UX_Guide.md` + `IMM-0x_UAT_Script.md` — không bị ảnh hưởng nhiều, đọc bình thường.

Khi viết code, ưu tiên Wave 1 convention (services/imm04.py, api/imm04.py) làm template.

---

## 14. Changelog

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-04-29 | Phát hành alignment đầu tiên — đối chiếu IMM-01/02/03 v0.1.0 với Wave 1 LIVE |

---

*End of Wave 2 Alignment v1.0.0*
