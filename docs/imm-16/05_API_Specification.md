# 05 — API Specification — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản tài liệu | 1.3 (sync app v0.0.2) |
| Ngày cập nhật | 2026-05-27 |
| Trạng thái | IMPLEMENTED — Wave 2 (feature/hieuc/wave-2) |
| Base path | `assetcore.api.imm16` |
| URL pattern | `/api/method/assetcore.api.imm16.<function>` |

> ✅ Implemented — Wave 2. `assetcore/api/imm16.py` có **52 whitelist functions** (verified `grep -c "^@frappe.whitelist" assetcore/api/imm16.py` = 52, 2026-05-27; **round 14 sẽ +`start_review` ⇒ 53 sau khi BE code Bước-4** — LIVE hiện vẫn 52): 31 canonical endpoints trong §3.x catalog + 12 legacy aliases (§1.4 cuối) + 9 helpers/scheduler triggers chưa enumerate trong §3.x (cụ thể: `run_compliance_evaluation`, `generate_scorecard`, `submit_audit_findings`, `close_finding`, `close_internal_audit`, `create_finding`, `create_compliance_rule`, `create_internal_audit`, `check_asset_compliance` — đều có whitelist nhưng là wrapper/POST-trigger không phải REST CRUD chính). FE consume qua `frontend/src/api/imm16.ts` + `frontend/src/stores/imm16.ts`. §1.4 dưới đây là danh sách canonical + alias.

---

## §1 Tổng quan

### §1.1 Response Envelope (AssetCore Standard)

**Mọi endpoint dùng envelope AssetCore — KHÔNG dùng Frappe wrapper `{"message": ...}`.**

**Thành công (HTTP 200):**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi (HTTP 200 với success=false):**

```json
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "FIN-XXX"
}
```

Helpers tại `assetcore/utils/helpers.py`:

```python
def _ok(data: dict) -> dict:
    return {"success": True, "data": data}

def _err(msg: str, code: str = "ERROR") -> dict:
    return {"success": False, "error": msg, "code": code}
```

> **LƯU Ý QUAN TRỌNG:** Frappe framework wrap mọi response trong outer `{"message": ...}`.  
> FE parse: `response.json().message` → `{"success": true, "data": {...}}`.  
> HTTP status luôn là 200. Logic lỗi nằm trong `success` field.

### §1.2 Phân trang

```json
{
  "items": [ /* array */ ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

`page` 1-based, `page_size` mặc định 20.

### §1.3 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → `{"success": false, "error": "...", "code": "FORBIDDEN"}`.

### §1.4 API Catalog

**Canonical endpoints** (31):

| # | Function | Method | Roles | Mô tả |
|---|---|---|---|---|
| 3.1.1 | `list_rules` | GET | All authenticated | Danh sách Compliance Rule |
| 3.1.2 | `get_rule` | GET | All authenticated | Chi tiết Rule |
| 3.1.3 | `create_rule` | POST | Tổ HC-QLCL, CMMS Admin | Tạo Rule mới |
| 3.1.4 | `update_rule` | POST | Tổ HC-QLCL, CMMS Admin | Cập nhật Rule (versioned) |
| 3.1.5 | `deactivate_rule` | POST | Tổ HC-QLCL, CMMS Admin | Deactivate Rule |
| 3.1.6 | `reactivate_rule` | POST | Tổ HC-QLCL, CMMS Admin | Reactivate Rule (BUG-16-02) |
| 3.1.7 | `get_record_history` | GET | All authenticated | Audit trail history cho Finding/CAPA/MR/Rule |
| 3.2.1 | `list_findings` | GET | All authenticated | Danh sách Finding |
| 3.2.2 | `get_finding` | GET | All authenticated | Chi tiết Finding (enrich asset_name, dept_name, rule_name) |
| 3.2.2b | `start_review` | POST | Tổ HC-QLCL, Internal Auditor, CMMS Admin | **(round 14)** Open → Under Review (surface phantom, ADR-IMM-16-06) |
| 3.2.3 | `confirm_finding` | POST | Tổ HC-QLCL, Internal Auditor, CMMS Admin | Confirm NC |
| 3.2.4 | `mark_false_positive` | POST | Tổ HC-QLCL, Internal Auditor, CMMS Admin | Mark False Positive |
| 3.2.5 | `waive_finding` | POST | VP Block2, CMMS Admin | Waive Finding (BR-16-06) |
| 3.2.6 | `link_to_capa` | POST | Tổ HC-QLCL, Workshop Head, CMMS Admin | Link Finding → CAPA |
| 3.3.1 | `list_audits` | GET | All authenticated | Danh sách Internal Audit |
| 3.3.2 | `get_audit` | GET | All authenticated | Chi tiết Internal Audit |
| 3.3.3 | `create_audit` | POST | Tổ HC-QLCL, CMMS Admin | Tạo Audit |
| 3.3.4 | `start_audit` | POST | Tổ HC-QLCL, CMMS Admin | Bắt đầu Audit (Planned → In Progress) |
| 3.3.5 | `complete_audit_checklist` | POST | Tổ HC-QLCL, CMMS Admin | Hoàn thành checklist + auto-Finding |
| 3.3.6 | `close_audit` | POST | Tổ HC-QLCL, VP Block2, CMMS Admin | Đóng Audit (VR-08) |
| 3.4.1 | `create_capa_from_finding` | POST | Tổ HC-QLCL, CMMS Admin | Tạo CAPA từ Finding |
| 3.4.2 | `get_capa` | GET | All authenticated | Chi tiết CAPA (enrich + finding link) |
| 3.4.3 | `update_capa_fields` | POST | Tổ HC-QLCL, CMMS Admin | Cập nhật nội dung CAPA (narrative fields) |
| 3.4.4 | `advance_capa_state` | POST | Tổ HC-QLCL, CMMS Admin | Advance CAPA state machine |
| 3.4.5 | `perform_effectiveness_check` | POST | Tổ HC-QLCL, CMMS Admin | Effectiveness check |
| 3.4.6 | `reopen_capa` | POST | Tổ HC-QLCL, CMMS Admin | Force reopen CAPA |
| 3.5.1 | `list_scorecards` | GET | All authenticated | Danh sách Scorecard |
| 3.5.2 | `get_current_scorecard` | GET | All authenticated | Scorecard tháng hiện tại |
| 3.5.3 | `get_scorecard_by_period` | GET | All authenticated | Scorecard theo year+month+scope |
| 3.5.4 | `publish_scorecard` | POST | Tổ HC-QLCL, VP Block2, CMMS Admin | Publish Scorecard |
| 3.6.1 | `list_management_reviews` | GET | All authenticated | Danh sách MR |
| 3.6.2 | `get_management_review` | GET | All authenticated | Chi tiết MR **+ server-driven CTA** (`allowed_transitions` + `can_advance` + `can_close` — §3.6.2b) |
| 3.6.3 | `create_management_review` | POST | VP Block2, CMMS Admin | Tạo Management Review |
| 3.6.4 | `update_management_review` | POST | VP Block2, CMMS Admin | Cập nhật MR (attendees + output_actions) |
| 3.6.5 | `advance_mr_state` | POST | VP Block2, CMMS Admin | Advance MR state (Draft→Held→Minutes Approved) |
| 3.6.6 | `finalize_management_review` | POST | VP Block2, CMMS Admin | Finalize MR → Closed |
| 3.7.1 | `get_dashboard_stats` | GET | All authenticated | KPI dashboard |
| 3.7.2 | `get_compliance_heatmap` | GET | All authenticated | Heatmap module×dept |
| 3.7.3 | `get_capa_aging` | GET | All authenticated | CAPA aging buckets |
| 3.7.4 | `get_overdue_actions` | GET | All authenticated | Overdue actions |
| 3.8.1 | `check_asset_compliance_status` | GET | All authenticated | Cross-module gate BR-16-09 |

**Legacy/alias endpoints** (11 — backward compat):

| Function | Alias của |
|---|---|
| `list_compliance_rules` | `list_rules` |
| `create_compliance_rule` | `create_rule` |
| `list_compliance_findings` | `list_findings` |
| `create_finding` | standalone (không có canonical wrapper riêng) |
| `close_finding` | standalone |
| `list_internal_audits` | `list_audits` |
| `create_internal_audit` | `create_audit` |
| `submit_audit_findings` | standalone — **DEPRECATED (dùng `complete_audit_checklist`); R22 guard SIẾT: chỉ từ `In Progress`** (§3.x Audit / ADR-IMM-16-09) |
| `close_internal_audit` | `close_audit` — **DEPRECATED (dùng `close_audit`, có VR-08 gate); R22 guard SIẾT: chỉ đóng từ `Reporting`** (VR-13 parity) |
| `generate_scorecard` | standalone (POST) |
| `check_asset_compliance` | `check_asset_compliance_status` (GET alias mỏng — DEPRECATED; gọi lại hàm canonical, KHÔNG gọi `svc.*` trực tiếp; xem §3.8.1) |
| `run_compliance_evaluation` | standalone (POST trigger) |

---

## §2 Role Constants

```python
# assetcore/api/imm16.py

_DOCTYPE_RULE     = "IMM Compliance Rule"
_DOCTYPE_FINDING  = "IMM Compliance Finding"
_DOCTYPE_AUDIT    = "IMM Internal Audit"
_DOCTYPE_CAPA     = "IMM CAPA Record"          # LIVE — REUSE
_DOCTYPE_SCORECARD = "IMM Compliance Scorecard"
_DOCTYPE_MR       = "IMM Management Review"
_DOCTYPE_RCA      = "IMM RCA Record"           # LIVE — REUSE

_WAIVE_ROLES              = {"Compliance Manager", "AssetCore Super Admin"}
_PUBLISH_SCORECARD_ROLES  = {"Compliance Manager", "AssetCore Super Admin"}
_FINALIZE_MR_ROLES        = {"Compliance Manager", "AssetCore Super Admin"}
_CLOSE_AUDIT_ROLES        = {"Compliance Manager", "AssetCore Super Admin"}
_CREATE_RULE_ROLES        = {"Compliance Manager", "AssetCore Super Admin"}
_AUDIT_LEAD_ROLES         = {"Compliance Manager", "Compliance User", "AssetCore Super Admin"}
```

> Persona cũ (`Tổ HC-QLCL`, `VP Block2`, `Internal Auditor`, `CMMS Admin`) đã được map vào 30-role catalog (post-patch `v3_2.001_module_role_redesign`). Nếu code thực tế còn chứa string persona cũ → cần đồng bộ trong sprint follow-up; tham chiếu `assetcore/fixtures/role.json` cho canonical names.

---

## §3 Endpoint Specifications

### §3.1 Compliance Rule (master)

#### 3.1.3 `create_rule`

**Mô tả:** Tạo Compliance Rule mới — validate VR-01/VR-02, set version="1.0", is_active=1.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.create_rule` |

**Request body:**

```json
{
  "rule_data": {
    "rule_code": "R-IMM08-PM-COMP-90",
    "rule_name": "PM Compliance < 90%",
    "source_module": "IMM-08",
    "category": "PM",
    "severity": "High",
    "threshold_definition": {"metric": "pm_compliance_pct", "op": "<", "value": 90},
    "evaluation_frequency": "Monthly",
    "owner_role": "Workshop Head",
    "qms_doc_ref": "PR-IMMIS-08-01",
    "regulatory_reference": "ISO 13485 §7.5.1",
    "effective_date": "2026-05-01"
  }
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "R-IMM08-PM-COMP-90",
    "version": "1.0",
    "is_active": 1
  }
}
```

**Errors:** `FIN-001` (VR-01), `FIN-002` (VR-02), `FIN-003` (create fail), `FORBIDDEN`

#### 3.1.4 `update_rule`

**Mô tả:** Cập nhật Rule — VR-11 enforce change_summary nếu threshold/severity đổi, bump version.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.update_rule` |

```json
{
  "name": "R-IMM08-PM-COMP-90",
  "rule_data": {"severity": "Critical"},
  "change_summary": "Tăng severity do yêu cầu compliance mới của BYT"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "R-IMM08-PM-COMP-90",
    "version": "1.1",
    "previous_version": "1.0"
  }
}
```

**Errors:** `FIN-011` (VR-11: missing change_summary), `FORBIDDEN`

---

### §3.2 Compliance Finding

#### 3.2.1 `list_findings`

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.list_findings` |

**Query params:** `filters` (JSON: status, severity, responsible_dept, asset, source_module, date_range), `page`, `page_size`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "FND-2026-00001",
        "rule": "R-IMM08-PM-COMP-90",
        "detected_date": "2026-05-01 03:00:00",
        "asset": "AC-ASSET-2026-0001",
        "responsible_dept": "ICU",
        "severity": "High",
        "status": "Under Review",
        "current_value": "78",
        "threshold_value": "90",
        "capa_ref": null
      }
    ],
    "pagination": {"page": 1, "page_size": 20, "total": 42, "total_pages": 3}
  }
}
```

#### 3.2.2 `get_finding`

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.get_finding` |

**Query params:** `name` (Finding name, bắt buộc).

**Response 200:** payload `get_finding` = doc `as_dict()` enrich `asset_name` / `responsible_dept_name` / `rule_name`, **CỘNG 2 field server-driven CTA** (GATE-8 / LL-FE-51 — xem `04_Backend_Design.md §III.B.1`):

```json
{
  "success": true,
  "data": {
    "name": "FND-2026-00001",
    "rule": "R-IMM08-PM-COMP-90",
    "rule_name": "PM completion ≥ 90%",
    "asset": "AC-ASSET-2026-0001",
    "asset_name": "Máy thở ICU-01",
    "responsible_dept": "ICU",
    "responsible_dept_name": "Khoa Hồi sức tích cực",
    "severity": "High",
    "status": "Under Review",
    "capa_ref": null,
    "allowed_transitions": ["Confirmed NC", "False Positive", "Waived"],
    "can_create_capa": false
  }
}
```

- `allowed_transitions: string[]` — trạng thái-đích hợp lệ kế tiếp mà BE cho phép, derive SERVER-SIDE = `_FINDING_VALID_TRANSITIONS.get(status, [])`. Codomain ⊆ `FindingStatus`. Terminal (False Positive / Resolved / Waived / Closed) → `[]`. FE gate nút bằng `capability('compliance.write') && allowed_transitions.includes('<đích>')` — KHÔNG so `status ===` client-side.
- `can_create_capa: boolean` — eligibility cờ cho CTA **Tạo CAPA** + **Liên kết CAPA** = `status == 'Confirmed NC' && !capa_ref`. FE KHÔNG hardcode `'Confirmed NC'`.
- **Fallback forward-compat:** worker cũ chưa enrich → 2 field vắng → FE đọc `?? []` / `?? false` → CTA ẩn, không vỡ.
- **Ánh xạ CTA → target-state / endpoint:**

  | CTA (FindingDetail) | Gate hiển thị | Endpoint gọi khi bấm |
  |---|---|---|
  | Bắt đầu xem xét *(round 14)* | `compliance.write && allowed_transitions.includes('Under Review')` | `start_review` (3.2.2b) |
  | Xác nhận sự không phù hợp | `compliance.write && allowed_transitions.includes('Confirmed NC')` | `confirm_finding` (3.2.3) |
  | Đánh dấu sai | `compliance.write && allowed_transitions.includes('False Positive')` | `mark_false_positive` (3.2.4) |
  | Miễn áp dụng | `compliance.write && allowed_transitions.includes('Waived')` | `waive_finding` (3.2.5) |
  | Tạo CAPA | `compliance.write && can_create_capa` | `create_capa_from_finding` (3.4.1) |
  | Liên kết CAPA | `compliance.write && can_create_capa` | `link_to_capa` (3.2.6) |

- **Guard (defense-in-depth, HTTP-200 Error envelope `BAD_STATE` khi sai state):** `start_review` chỉ từ `{Open}`; `confirm_finding`/`mark_false_positive` chỉ từ `{Open, Under Review}`; `waive_finding` chỉ từ `{Open, Under Review, Confirmed NC}`. `allowed_transitions` là hint hiển thị, KHÔNG thay guard.
- **Lockstep `workflow_state ⇄ status` (round 14, ADR-IMM-16-05):** mọi transition-fn Finding SAU khi đặt `status` cũng đặt `workflow_state = status` (qua `frappe.db.set_value`, bypass validate_workflow) — reload doc ⇒ `workflow_state == status`. Chi tiết cơ chế + INVARIANT: `04_Backend_Design.md §III.B.2`.

#### 3.2.2b `start_review` *(round 14 — CR-WF-16-FIND)*

**Mô tả:** Bắt đầu xem xét Finding — `Open → Under Review`. Surface cạnh workflow `Open→Under Review` vốn 0 service-driver (phantom, ADR-IMM-16-06). Lockstep `workflow_state='Under Review'`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.start_review` |

```json
{ "name": "FND-2026-00001", "reviewer_note": "Bắt đầu xem xét — phân công cán bộ QLCL" }
```

**Guard:**
- Cap `compliance.write` (`_require_qa_or_admin`) → else dispatcher-403 (guest/no-token) hoặc in-handler HTTP-200 `FORBIDDEN` (thiếu cap).
- `status != 'Open'` → HTTP-200 Error envelope `BAD_STATE` (`START_REVIEWABLE = (Open,)`).

**Response 200:**

```json
{ "success": true, "data": {"name": "FND-2026-00001", "status": "Under Review"} }
```
> Sau lockstep: `workflow_state == 'Under Review'` (reload verify).

#### 3.2.5 `waive_finding`

**Mô tả:** Waive Finding — chỉ VP Block2 + VR-04 enforce (BR-16-06).

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.waive_finding` |

```json
{
  "name": "FND-2026-00001",
  "waiver_reason": "Finding này là false alarm do lịch PM đã điều chỉnh kỳ nghỉ Tết...",
  "waiver_evidence": "/files/evidence-waiver-001.pdf",
  "waiver_expiry": "2026-12-31"
}
```

**Validations:**
- Role IN `_WAIVE_ROLES` → else `FIN-006` FORBIDDEN
- `waiver_reason` ≥ 50 chars → else `FIN-004` VR-04
- `waiver_evidence` required → else `FIN-004` VR-04
- `waiver_expiry > today` → else `FIN-004` VR-04

**Response 200:**

```json
{
  "success": true,
  "data": {"name": "FND-2026-00001", "status": "Waived"}
}
```

---

### §3.3 Internal Audit

> **Vòng đời canonical (ADR-IMM-16-02):** `Planned →(start_audit)→ In Progress →(complete_audit_checklist + auto-Finding)→ Reporting →(close_audit, VR-08/VR-13)→ Closed`. CTA màn InternalAuditDetail phát từ `get_audit.allowed_transitions` (action-key) + 2 cờ `can_operate`/`can_close` — KHÔNG so `status ===` client-side (GATE-8/LL-FE-51).

> 📱 **Mobile contract (CR-27a · ADR-MOBILE-051):** endpoint list `imm16.list_internal_audits` (GET, 3 param `filters`/`page`/`page_size`) đã curate vào OAS mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — LIST-ENTRY màn mobile **F7 "Audit nội bộ (checklist hiện trường)"**, opId `listInternalAudits`, tag `compliance` (op ĐẦU TIÊN mở nhánh IMM-16 mobile). ⚠️ **rows-key `data.data[]` DOUBLE-DATA** (envelope bọc 2 lớp — service `return {"data":rows,"pagination":pg}` @`services/imm16.py:375`, KHÁC `data.items[]` của commissioning) — client codegen PHẢI map `data.data[]`. 200 = oneOf `[InternalAuditListEnvelope, Error]` (Decision-B route-by-VALUE `body.success`). `InternalAuditListItem` = 8 field VERBATIM @`:365-366` + `lead_auditor_name` OPTIONAL (enrich CHỈ khi `lead_auditor` truthy @`:371-374`); `audit_type`/`status` khai `type:string` (KHÔNG hard-enum — DocType Select leading-blank ⇒ `""` hợp-lệ, xem ADR-MOBILE-051 §2.c.1). CONTRACT-ONLY — backend LIVE, 0 `.py`/reload/migrate. Chi tiết đầy đủ + guard test: [`../mobile/ADR-MOBILE-051.md`](../mobile/ADR-MOBILE-051.md).

> 📱 **Mobile contract (CR-27b · ADR-MOBILE-052):** endpoint DETAIL `imm16.get_audit` (GET, 1 param `name` typed `in:query, required:true, type:string`) đã curate vào OAS mirror — sibling DETAIL của `listInternalAudits` (đặt liền sau block CR-27a, giữ nhánh IMM-16 liền mạch), opId `getInternalAudit`, tag `compliance`. 200 = **inline** oneOf `[InternalAuditDetailEnvelope | Error]` (Decision-B route-by-VALUE `body.success`; `NOT_FOUND` @`services/imm16.py:1629` đến TRÊN HTTP-200, KHÔNG status-line 404 — parity `getAllocation` R42). Envelope `InternalAuditDetailEnvelope` **CLOSED**; payload `InternalAuditDetail` + child `InternalAuditChecklistItem` (`checklist_items[]`) + `AuditFindingItem` (`findings[]`) **OPEN** — xem Self-Correction ngay dưới. `lead_auditor_name` OPTIONAL (∉ `required`); `audit_type`/`status` (header) + `result`/`category`/`severity`/`capa_status` (child Select) khai `type:string` (KHÔNG hard-enum — Select leading-blank/reqd=None ⇒ `""` hợp-lệ, ADR-MOBILE-051 §2.c.1). CONTRACT-ONLY — backend LIVE @`api/imm16.py:246`, 0 `.py`/reload/migrate. Guard test: `assetcore/tests/test_mobile_oas.py::TestMobileGetInternalAuditDetailContract` (a..g + live).

> ⚠️ **SELF-CORRECTION — ADR-MOBILE-052 (payload OPEN, không CLOSED như acceptance CR-27b phát biểu):** acceptance yêu cầu "cả 4 schema closed (`additionalProperties:false`)", nhưng đây là **mâu thuẫn nội tại** của chính acceptance — nó ĐỒNG THỜI yêu cầu "parity `getAllocation` R42" (mà R42 = detail **OPEN** theo ADR-MOBILE-050). Quyết định cuối = **payload OPEN + chỉ envelope CLOSED**, vì `get_audit` trả `doc.as_dict()` surface (`services/imm16.py:1630`) **Y HỆT** `get_allocation` (`services/imm15.py:224`) → as_dict emit meta Frappe (`name/owner/creation/modified/docstatus/idx`; child `parent/parentfield/parenttype`) VƯỢT danh sách field nghiệp-vụ. Closed-schema trên as_dict surface = **hợp đồng nói dối** → strict Dart/Kotlin codegen deser CRASH trên meta-key (cùng loại rủi ro codegen mà acceptance lo ở cấp enum, nhưng ở cấp object). "closed" trong acceptance là **copy nhầm từ precedent R43 list-item** — `InternalAuditRepo.list` trả CURATED `fields=8` nên closed HỢP-LỆ cho LIST; nhưng DETAIL = as_dict nên PHẢI OPEN. Precedent nhất-quán: cả 6 `*Detail` as_dict-based hiện có (`CalibrationDetail`/`SpareAllocationDetail`…) đều OPEN. False-green được chặn bằng **TC-live subset-guard** (props ⊆ doctype ∪ enrich — chặn field BỊA) + **live-signature parity** (`inspect.signature(get_audit)=={name}`), KHÔNG bằng closed-exact-parity (bất khả thi với as_dict). Xem ADR-MOBILE-052 (Phần dưới, `02_Analysis_Design.md`).

#### 3.3.2 `get_audit` — enrich server-driven CTA (`allowed_transitions` + `can_operate` + `can_close`)

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.get_audit` |

**Query params:** `name` (Audit name, bắt buộc).

**Response 200:** doc `as_dict()` enrich `lead_auditor_name`, **CỘNG 3 field server-driven CTA** (xem `04_Backend_Design.md §III.C.1`):

```json
{
  "success": true,
  "data": {
    "name": "AUD-INT-2026-00001",
    "audit_code": "A-2026-Q2-MAINT",
    "status": "In Progress",
    "lead_auditor": "auditor@hospital.vn",
    "lead_auditor_name": "Trần Thị QLCL",
    "allowed_transitions": ["complete_checklist"],
    "can_operate": true,
    "can_close": false
  }
}
```

- `allowed_transitions: string[]` — **action-key** kế tiếp hợp lệ = `_AUDIT_VALID_TRANSITIONS.get(status, [])`. `{Planned:['start'], In Progress:['complete_checklist'], Reporting:['close'], Closed:[], (rỗng/lạ):[]}`. **Safe-default** — status rỗng/lạ → `[]`, KHÔNG KeyError.
- `can_operate: boolean` = `rbac.can('compliance.write')` — gate CTA **Bắt đầu** + **editor bảng kiểm** (User+).
- `can_close: boolean` = `rbac.can('compliance.submit')` — gate CTA **Đóng** (Manager). Derive SERVER-SIDE.
- **Fallback forward-compat:** worker cũ chưa enrich → 3 field vắng → FE đọc `?? []` / `?? false` → CTA ẩn, không vỡ.
- **Ánh xạ CTA → action-key / endpoint:**

  | CTA (InternalAuditDetail) | Gate hiển thị | Endpoint gọi khi bấm |
  |---|---|---|
  | Bắt đầu | `can_operate && allowed_transitions.includes('start')` | `start_audit` (3.3.4) |
  | Hoàn tất bảng kiểm | `can_operate && allowed_transitions.includes('complete_checklist')` | `complete_audit_checklist` (3.3.5) |
  | Đóng | `can_close && allowed_transitions.includes('close')` | `close_audit` (3.3.6) |

#### 3.3.4 `start_audit`

**Mô tả:** Bắt đầu Audit (Planned → In Progress). Ghi 1 audit-event `audit_started`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.start_audit` |

**Validations:** role `compliance.write` (in-handler cap → `FORBIDDEN`); `status == Planned` → else `BAD_STATE`.

**Response 200:** `{ "success": true, "data": {"name": "...", "status": "In Progress", "actual_start": "2026-05-18"} }`

#### 3.3.5 `complete_audit_checklist`

**Mô tả:** Update checklist items — sinh Finding tự động cho Major/Minor NC; **kết thúc chuyển `status = Reporting`** (khôi phục state chết). Ghi 1 audit-event `audit_checklist_completed`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.complete_audit_checklist` |

```json
{
  "audit_name": "AUD-INT-2026-00001",
  "items": [
    {
      "idx": 1,
      "finding_status": "Major NC",
      "notes": "Tài liệu bảo trì không được cập nhật",
      "clause_ref": "§7.5.1.2"
    },
    {
      "idx": 2,
      "finding_status": "Compliant",
      "notes": "OK"
    }
  ]
}
```

**Validations:** role `compliance.write` (in-handler cap → `FORBIDDEN`); `status == In Progress` → else `BAD_STATE` (bỏ nhánh `Planned` — chặn nhập bảng kiểm khi chưa Bắt đầu).

**Hợp đồng field payload ⇄ child persisted (CR-27b — SỬA silent-verdict-loss):**

> ⚠️ `finding_status` và `clause_ref` trong payload là **DTO transient** — child DocType `IMM Audit Checklist Item` KHÔNG có field tên đó (schema thật: `item_description, category, criteria, result, evidence, notes, finding_ref` — xem 04 §II.6). Verdict được persist QUA field Select **`result`** (đây là field round-trip khi re-fetch `get_audit`). Server PHẢI map `finding_status → result` — KHÔNG được assign thẳng `child.finding_status` (no-op câm: `hasattr(child,"finding_status")==False` ⇒ verdict mất im lặng, bug gốc CR-27b).

| Field payload (DTO) | Persist vào | Ghi chú |
|---|---|---|
| `finding_status` (enum) | **`result`** (map qua bảng dưới) | round-trip qua `get_audit` |
| `notes` | `notes` (field thật) | persist verbatim |
| `clause_ref` | **(không persist)** | child KHÔNG có field — nhận rồi bỏ; KHÔNG assign no-op |
| `idx` | (chỉ để khớp `child.idx`) | không persist |

**Mapping SSoT `finding_status → result`** (DUY NHẤT 1 dict phía service; mọi value ∈ options Select `result` = `{Conforming, Non-Conforming, Not Applicable}`):

| `finding_status` (payload) | `result` (persist) |
|---|---|
| `Compliant` | `Conforming` |
| `Minor NC` | `Non-Conforming` |
| `Major NC` | `Non-Conforming` |
| `N/A` | `Not Applicable` |
| *(unknown / thiếu)* | **giữ nguyên `result` cũ** — KHÔNG set giá trị lạ |

> **Round-trip contract (acceptance CR-27b):** sau `complete_audit_checklist(audit, items=[{idx, finding_status}])` rồi re-fetch `get_audit(audit)` → mỗi `checklist_items[i].result` = giá trị map ở trên, **KHÔNG rỗng**. Trước fix: LUÔN rỗng (2 assign `child.finding_status`/`child.clause_ref` là no-op câm vào field không tồn tại).

**Hành vi cho item finding_status="Major NC"/"Minor NC" (CR-27d — auto-Finding THẬT):**
1. Map `finding_status → child.result` (Major/Minor NC → `Non-Conforming`).
2. **Sinh `IMM Compliance Finding` THẬT** cho mỗi dòng NC: `severity="High"` (Major) / `"Medium"` (Minor); `rule` = canonical `AUDIT-INTERNAL-NC` (get-or-create idempotent); `source_record_doctype="IMM Internal Audit"` + `source_record=<audit>`; `status="Open"`; `detected_date`+`evaluation_date` set (cả hai reqd). `findings_created` = số doc **persist THỰC** (1 Finding/dòng NC — 2 NC ⇒ 2). Chi tiết + field mapping: `04_Backend_Design.md §III.C.1c` / **ADR-IMM-16-11**.
3. Cuối thân: **`status = Reporting`** (In Progress → Reporting) — state `Reporting` không còn chết; ghi ĐÚNG 1 audit-event `audit_checklist_completed`.

> ⚠️ **Fail-loud (CR-27d):** nhánh Finding **KHÔNG** bọc `try/except` nuốt lỗi. Rule/Finding create hỏng vì lý do THẬT → **raise** (in-handler HTTP-200 Error envelope) abort trước commit (all-or-nothing) — KHÔNG âm thầm biến no-op thành success. `findings_created` KHÔNG bao giờ > số persist thật (hết success-giả). **KHÔNG dedup** `find_existing` cho audit-NC (nhiều NC cùng audit/ngày là các vi phạm riêng — dedup sẽ gộp sai).

> 🏷️ **Backlink row→finding — BỎ (CR-27d):** dòng cũ "Set `item.linked_finding = finding.name`" là **no-op câm** (child KHÔNG có `linked_finding`; `finding_ref` là Link → `Audit Finding` ≠ `IMM Compliance Finding` → mismatch doctype). CR-27d LOẠI hẳn assign này; liên kết finding→audit đi qua `source_record` (forward-link SSoT — query Finding theo `source_record=<audit>`). Backlink cấp-dòng = `[ROADMAP]`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "audit_name": "AUD-INT-2026-00001",
    "items_count": 2,
    "findings_created": 1,
    "status": "Reporting"
  }
}
```

#### 3.3.6 `close_audit`

**Mô tả:** Đóng Audit (Reporting → Closed) — VR-13 chặn jump-skip + VR-08 block nếu còn Major NC chưa link CAPA (BR-16-04). Ghi 1 audit-event `audit_closed`.

**Validations:**
- role `compliance.submit` (in-handler cap → `FORBIDDEN`)
- `status == Reporting` → else `BAD_STATE` "Audit phải ở trạng thái Reporting trước khi đóng" (VR-13 — chặn close thẳng từ Planned/In Progress)
- Không còn Major NC (`severity in [High, Critical]`, status ∈ ACTIVE) thiếu `capa_ref` → else `FIN-008` (VR-08)

```json
{
  "name": "AUD-INT-2026-00001",
  "audit_report": "/files/audit-report-q2-2026.pdf"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "AUD-INT-2026-00001",
    "status": "Closed",
    "actual_end": "2026-05-20"
  }
}
```

**Errors:** `BAD_STATE` (VR-13: chưa ở Reporting — jump-skip), `FIN-008` (VR-08: còn Major NC chưa CAPA), `FORBIDDEN`

---

### §3.4 CAPA (operate on IMM CAPA Record LIVE)

#### 3.4.1 `create_capa_from_finding`

**Mô tả:** Tạo CAPA Record từ Finding — gọi `services.imm00.create_capa` + set Custom Fields IMM-16.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.create_capa_from_finding` |

```json
{
  "finding_name": "FND-2026-00001",
  "imm_risk_level": "High",
  "imm_root_cause_method": "5-Why",
  "responsible": "nguyenvana@hospital.vn",
  "due_date": "2026-06-15"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "capa_name": "CAPA-2026-00007",
    "finding_name": "FND-2026-00001",
    "workflow_state": "Open"
  }
}
```

#### 3.4.1b `get_capa` — enrich server-driven CTA (`allowed_transitions` + `can_advance`)

> ⚠️ **Numbering drift (pre-existing, light-touch — báo cáo, không renumber):** bảng tóm tắt §3.4 đánh `get_capa = 3.4.2` nhưng các sub-header chi tiết đã dùng `3.4.2 = advance_capa_state`. Giữ header cũ; subsection get_capa CTA đặt nhãn `3.4.1b` để không renumber (drift ghi ở `_REPORT.md`).

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.get_capa` |

**Params:** `name=CAPA-2026-00007`

**Response 200:** doc `as_dict()` enrich `asset_name` / `responsible_name` / `finding_ref` / `finding_rule` / `incident_ref` / `incident_subject` (BUG-16-08 / B-IMM16-2), **CỘNG 2 field server-driven CTA** (GATE-8 / LL-FE-51 — xem `04_Backend_Design.md §III.D.1` / **ADR-IMM-16-03**):

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "workflow_state": "Implementation",
    "status": "In Progress",
    "asset_name": "Máy thở Hamilton C6 — GB-ICU-01",
    "allowed_transitions": ["Verification"],
    "can_advance": true
  }
}
```

- `allowed_transitions: string[]` — **workflow_state-đích** hợp lệ kế tiếp = `sorted(_CAPA_TRANSITIONS.get(workflow_state, set()))` khi caller có `compliance.write`; **`[]` khi KHÔNG có** (gate quyền dồn vào hint). Codomain ⊆ `CapaWorkflowState`. `sorted()` cho thứ tự xác định. Terminal `Closed` → `[]` (safe-default). FE gate nút bằng `can_advance && allowed_transitions.includes('<đích>')` — KHÔNG so `workflow_state ===` client-side.
- `can_advance: boolean` = `rbac.can('compliance.write')` derive SERVER-SIDE (mirror `can_operate` của Audit). `true` cả ở terminal (phản ánh QUYỀN, không phải còn-thao-tác). FE KHÔNG so role client-side.
- **CTA-hint contract** (đối xứng `get_finding` §3.2.2 / `get_audit` §3.3.2):

  | `workflow_state` | `allowed_transitions` (khi `can_advance`) | CTA hiển thị | Endpoint |
  |---|---|---|---|
  | Open | `['Investigating']` | Bắt đầu điều tra | `advance_capa_state` (3.4.2) |
  | Investigating | `['Action Plan']` | Lập kế hoạch hành động | `advance_capa_state` (3.4.2) |
  | Action Plan | `['Implementation']` | Bắt đầu thực thi | `advance_capa_state` (3.4.2) |
  | Implementation | `['Verification']` | Chuyển sang xác minh | `advance_capa_state` (3.4.2) |
  | Verification | `['Closed', 'Re-opened']` | Đóng CAPA / Mở lại | **`perform_effectiveness_check`** (3.4.3) — gate 2 nút bằng `.includes('Closed')` / `.includes('Re-opened')` |
  | Re-opened | `['Investigating']` | Bắt đầu điều tra (lại) | `advance_capa_state` (3.4.2) |
  | Closed / caller thiếu quyền | `[]` | 0 CTA (hint "không có thao tác / không đủ quyền") | — |

- **Guard (defense-in-depth, KHÔNG thay bằng hint):** `advance_capa_state` giữ nguyên `_require_qa_or_admin()` (FORBIDDEN nếu thiếu `compliance.write`) + `target not in _CAPA_TRANSITIONS[current] → INVALID_STATE` (HTTP-200 Error envelope). `allowed_transitions` là hint hiển thị; dù client bỏ qua, BE vẫn chặn cứng.
- **Bất biến (test khóa):** `allowed_transitions` do get_capa phát dẫn xuất từ CÙNG `_CAPA_TRANSITIONS` mà `advance_capa_state` enforce (KHÔNG nguồn thứ hai) — xem 04 §III.D.1 invariant (a)-(d) + 07 §III.4d.
- **Reconcile-guard map ⇄ workflow (round 19 — CR-WF-16-CAPA):** `_CAPA_TRANSITIONS` khoá parity **2 chiều edge-by-edge** với `imm_16_capa_workflow.json` (INV-16-CAPA-1 MAP⊆WF + INV-16-CAPA-2 WF⊆MAP, `EXCEPTION_EDGES=∅`) ⇒ 0 CTA câm / dead khi map hoặc workflow drift. Codomain ⊆ 7 state hợp lệ; terminal `Closed` ∉ keys → `[]`. Chi tiết `04 §III.D.2` / `ADR-IMM-16-07` / test `07 §III.4d AT-16-CAPA-INV-1..4`.
- **Reconcile-guard map ⇄ workflow qua resolver (round 22 — CR-WF-16-AUDIT):** `_AUDIT_VALID_TRANSITIONS` (codomain = **action-key**, KHÁC Finding/CAPA/MR codomain=state) khoá parity với `imm_16_internal_audit.json` QUA resolver `_AUDIT_ACTION_TO_NEXT_STATE` (action→AuditStatus, SSoT) — INV-AUD-1..5 (`TestAuditWorkflowInvariant`): keys==states[], resolver-keys==3-handler, no-orphan-action, values⊆enum, per-state `{resolver[a] for a in map[state]}`==`{next_state workflow}`. Legacy `submit_audit_findings`/`close_internal_audit` guard SIẾT về linear (guard-detect AA-16-13/14). **ĐÓNG NỐT quartet reconcile IMM-16** (Finding R14 / CAPA R19 / MR R20 + Internal Audit R22). Chi tiết `04 §III.C.2` / `ADR-IMM-16-09` / test `07 AT-16-AUD-INV / AA-16-13/14`.

#### 3.4.2 `advance_capa_state`

**Mô tả:** Advance workflow_state của CAPA Record — server-side VR-05/06/07/12 enforce.

```json
{
  "name": "CAPA-2026-00007",
  "target_state": "Action Plan",
  "payload": {
    "imm_root_cause_method": "5-Why",
    "due_date": "2026-06-15"
  }
}
```

**State-specific validations:**

| target_state | Validation |
|---|---|
| Action Plan | VR-05 `imm_root_cause_method` reqd; VR-12 `due_date > today` |
| Implementation | Tất cả `imm_action_plan` rows có `owner` + `planned_date` |
| Verification | Tất cả `imm_action_plan` rows `status="Done"` |
| Closed | VR-06 `effectiveness_check` reqd; VR-07 phải = "Effective" |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "workflow_state": "Action Plan",
    "status": "In Progress"
  }
}
```

#### 3.4.3 `perform_effectiveness_check`

**Mô tả:** Kết quả effectiveness check — Effective → Close; Not Effective → Re-open + imm_reopen_count++.

```json
{
  "name": "CAPA-2026-00007",
  "result": "Effective",
  "effectiveness_evidence": "/files/evidence-capa-eff-001.pdf"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "new_state": "Closed",
    "imm_reopen_count": 0
  }
}
```

**Khi Not Effective (hoặc Partially Effective):**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "new_state": "Re-opened",
    "imm_reopen_count": 1
  }
}
```

> `new_state` là `"Re-opened"` (không phải `"Investigating"`). Bước tiếp theo FE phải gọi `advance_capa_state` → `"Investigating"` manually.

---

### §3.5 Compliance Scorecard

#### 3.5.3 `get_scorecard_by_period`

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.get_scorecard_by_period` |

**Params:** `year=2026&month=4&scope=Hospital`

> **Semantics rate (BR-16-11):** `score_pct = compliant/(compliant+non_compliant)*100`, mẫu số = chỉ finding ĐÃ adjudicated. `pending_count` (Open + Under Review) báo riêng, KHÔNG vào mẫu số. `score_pct` của Scorecard và `cell.score` của Heatmap dùng CÙNG SoT `compute_compliance_rate()` → CÙNG dataset CÙNG 1 score. `pending_count` là runtime-only (chưa persist field DocType — xem 04 §II.5 row 8a).
>
> **Period-anchor (BR-16-12):** Điều kiện tiên quyết của "CÙNG dataset" — cả Scorecard và Heatmap lọc kỳ theo CÙNG 1 field canonical `evaluation_date` (Date), KHÔNG dùng `detected_date` (Datetime event-timestamp có thể lệch kỳ do lag adjudication). Nếu 2 view lọc 2 field khác nhau, cùng module/kỳ sẽ chọn 2 TẬP finding khác → `score_pct` lệch dù công thức giống. `evaluation_date` là khóa idempotency `(rule, source_record, evaluation_date)` = định nghĩa hệ thống "finding thuộc kỳ nào".

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SCR-2026-04-0001",
    "period_year": 2026,
    "period_month": 4,
    "scope": "Hospital",
    "total_rules_evaluated": 120,
    "compliant_count": 90,
    "non_compliant_count": 18,
    "pending_count": 12,
    "score_pct": 83.33,
    "trend_vs_prev_month": 2.3,
    "score_by_module": [
      {"module": "IMM-08", "score": 91.0},
      {"module": "IMM-11", "score": 72.0}
    ],
    "score_by_department": [
      {"dept": "ICU", "score": 92.0},
      {"dept": "CT", "score": 74.0}
    ],
    "capa_open_count": 18,
    "capa_overdue_count": 5,
    "is_published": 1
  }
}
```

#### 3.5.4 `publish_scorecard`

**Mô tả:** Publish Scorecard — VR-10 gate: quý trước phải có MR Closed (BR-16-08).

```json
{"name": "SCR-2026-04-0001"}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SCR-2026-04-0001",
    "is_published": 1,
    "published_at": "2026-05-05 09:30:00",
    "approved_by_for_review": "vp2@hospital.vn"
  }
}
```

**Errors:** `FIN-010` (VR-10: quý trước thiếu MR), `FIN-009` (VR-09: đã published), `FORBIDDEN`

---

### §3.6 Management Review

> **Vòng đời canonical (ADR-IMM-16-04):** `Draft →(advance_mr_state 'Held')→ Held →(advance_mr_state 'Minutes Approved')→ Minutes Approved →(finalize_management_review)→ Closed`. CTA màn ManagementReviewDetail phát từ `get_management_review.allowed_transitions` (tên status-đích) + 2 cờ `can_advance`/`can_close` — KHÔNG so `status ===` client-side (GATE-8/LL-FE-51). Đây là workflow IMM-16 thứ 4/4 chuyển server-driven.

#### 3.6.2b `get_management_review` — enrich server-driven CTA (`allowed_transitions` + `can_advance` + `can_close`)

**Response 200 (bổ sung 3 khoá, ngoài enrich chair_name/scorecard sẵn có):**

```json
{
  "success": true,
  "data": {
    "name": "MR-2026-00001",
    "quarter": "Q2-2026",
    "status": "Held",
    "workflow_state": "Held",
    "chair_name": "…", "scorecard_score_pct": 92.0,
    "allowed_transitions": ["Minutes Approved"],
    "can_advance": true,
    "can_close": true
  }
}
```

- `allowed_transitions: string[]` — **tên status-đích** hợp lệ kế tiếp = `sorted(_MR_TRANSITIONS.get(status, []))`. `{Draft:['Held'], Held:['Minutes Approved'], Minutes Approved:['Closed'], Closed/rỗng/lạ:[]}`. Phát **vô điều kiện** (không gate bằng cờ — mirror Finding/Audit). **Safe-default** — status rỗng/lạ → `[]`, KHÔNG KeyError. Codomain khớp 1-1 tham số `target_state` của `advance_mr_state`; đích `'Closed'` đi qua `finalize_management_review` (KHÔNG `advance_mr_state`).
- `can_advance: bool` = `rbac.can('compliance.submit')` — gate 2 nút chuyển-cạnh.
- `can_close: bool` = `rbac.can('compliance.submit')` — gate nút Đóng (tách riêng, đối xứng Audit `can_operate`/`can_close`).
- **CTA gate (FE), nhãn khớp EXACT workflow `IMM-16 Management Review Workflow`:**

  | `status` | `allowed_transitions` | CTA hiển thị | Điều kiện | Endpoint |
  |---|---|---|---|---|
  | Draft | `['Held']` | Đánh dấu Đã họp | `can_advance && allowed_transitions.includes('Held')` | `advance_mr_state(name,'Held')` |
  | Held | `['Minutes Approved']` | Phê duyệt Biên bản | `can_advance && allowed_transitions.includes('Minutes Approved')` | `advance_mr_state(name,'Minutes Approved')` |
  | Minutes Approved | `['Closed']` | Đóng và xuất biên bản | `can_close && allowed_transitions.includes('Closed')` | `finalize_management_review(name, minutes_doc, actions)` |
  | Closed / rỗng | `[]` | — | — | — |

- **Guard (defense-in-depth, KHÔNG thay bằng hint):** `advance_mr_state` giữ `rbac.can('compliance.submit')` (FORBIDDEN nếu thiếu) + `target not in _MR_TRANSITIONS[current] → INVALID_STATE` + `target=='Closed' → VALIDATION`. `finalize_management_review` giữ FORBIDDEN + BAD_STATE(đã Closed) + VALIDATION(minutes_doc/≥1 action). `allowed_transitions` là hint hiển thị; dù client bỏ qua, BE vẫn chặn cứng.
- **Bất biến (test khóa):** `allowed_transitions` do get_management_review phát dẫn xuất từ CÙNG `_MR_TRANSITIONS` mà `advance_mr_state`/`finalize` enforce (KHÔNG nguồn thứ hai) — xem 04 §III.F.1 invariant (a)-(d) + 07 §III.4e.
- **Degrade an toàn:** 3 field vắng (worker cũ / lỗi) → FE `?? []` / `?? false` → 0 CTA (KHÔNG dead-control), KHÔNG crash.

#### 3.6.3 `finalize_management_review`

```json
{
  "name": "MR-2026-00001",
  "minutes_doc": "/files/mr-minutes-q2-2026.pdf",
  "output_actions": [
    {
      "action": "Đẩy mạnh PM IMM-08 tại OR",
      "owner": "wshead@hospital.vn",
      "due_date": "2026-09-30"
    }
  ]
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "MR-2026-00001",
    "status": "Closed",
    "quarter": "Q2-2026"
  }
}
```

---

### §3.7 Dashboard / Reports

#### 3.7.1 `get_dashboard_stats`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "kpis": {
      "overall_compliance_pct": 87.5,
      "findings_open": 24,
      "findings_critical": 3,
      "capa_open": 18,
      "capa_overdue": 5,
      "audits_in_progress": 2,
      "mr_quarterly_status": "Pending"
    },
    "trend_12m": [
      {"month": "2025-06", "score_pct": 82.0},
      {"month": "2026-05", "score_pct": 87.5}
    ],
    "top_modules_low": [
      {"module": "IMM-11", "score": 72.0},
      {"module": "IMM-09", "score": 78.0}
    ],
    "recent_findings": []
  }
}
```

#### 3.7.2 `get_compliance_heatmap`

**Params:** `period_year=2026&period_month=4`

> Lọc kỳ theo `evaluation_date` (BR-16-12 period-anchor canonical, CÙNG field với Scorecard — KHÔNG `detected_date`). `cell.score` == `score_pct` của Scorecard cùng module/kỳ trên CÙNG tập finding.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "modules": ["IMM-04","IMM-05","IMM-08","IMM-09","IMM-11","IMM-12","IMM-15"],
    "departments": ["ICU","OR","ER","CT","Internal Med","Pediatric"],
    "matrix": [
      {"module":"IMM-08","dept":"ICU","score":92.0,"findings_count":2},
      {"module":"IMM-08","dept":"OR","score":78.0,"findings_count":5},
      {"module":"IMM-11","dept":"CT","score":65.0,"findings_count":8}
    ]
  }
}
```

---

### §3.8 Cross-module Gate

#### 3.8.1 `check_asset_compliance_status` (CANONICAL)

**Mô tả:** Gọi bởi `gate_wo_submit` (PM Work Order / Asset Repair `.validate`) trước WO Submit; `services/imm04.py` commissioning gate; IMM-13/14 trước decommission; và **FE pre-flight banner** (`PMWorkOrderCreateView.vue` qua client `imm16.ts::checkAssetComplianceStatus`, line 512-513) khi user chọn asset — render BE result, KHÔNG inline-compute membership ở FE.

> **Canonical path (chốt Vòng 16 — collapse duplicate):** đây là endpoint DUY NHẤT delegate trực tiếp tới `svc.check_asset_compliance_status`. Endpoint `check_asset_compliance` (api/imm16.py cũ ~line 124) trở thành **alias mỏng**: gọi lại hàm Python `check_asset_compliance_status(asset)` trong cùng file (KHÔNG gọi thẳng `svc.*`), kèm doc-note `# DEPRECATED alias — dùng check_asset_compliance_status`. Tiêu chí nghiệm thu: `grep -n "svc.check_asset_compliance_status" api/imm16.py` chỉ trả về 1 dòng (trong def canonical). FE client (`imm16.ts:512-513`) trỏ tới canonical path `…imm16.check_asset_compliance_status` — gọi LIVE phải trả 200 (không 403/404 method-not-found).

> **Parity contract (FE pre-flight ⟺ gate_wo_submit):** cả pre-flight banner và `gate_wo_submit` cùng đọc 1 SoT — `result.blocked` mà FE render === `blocked` mà service `check_asset_compliance_status` trả. FE KHÔNG tự tính membership; banner chỉ hiển thị `result.blocked` + `result.reasons[]` verbatim. Khi `blocked===true` → nút "Tạo lệnh" disable (hoặc giữ reactive-throw nhưng banner đã cảnh báo trước). Khi `blocked===false` hoặc asset rỗng → banner ẩn.

`blocked` = có Critical CAPA mở trên asset. "Mở" dùng **SoT `imm00._open_capa_filter()`** (BR-00-15: `status NOT IN ('Closed')`) AND `imm_risk_level='Critical'` — KHÔNG inline `status IN [Open, In Progress, Pending Verification]`. **Invariant dưới cron**: CAPA `'Overdue'` ∈ tập mở → gate giữ `blocked=true` cả trước/sau `check_capa_overdue` flip; `reasons[].status` trả status thật (gồm `'Overdue'`). Non-Critical (High/Medium/Low) KHÔNG block dù Overdue.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.check_asset_compliance_status` |

**Params:** `asset=AC-ASSET-2026-0001`

**Response blocked:**

```json
{
  "success": true,
  "data": {
    "blocked": true,
    "asset": "AC-ASSET-2026-0001",
    "reasons": [
      {
        "type": "CAPA_CRITICAL_OPEN",
        "ref": "CAPA-2026-00007",
        "status": "In Progress",
        "workflow_state": "Implementation",
        "message": "CAPA Critical chưa close"
      }
    ],
    "active_findings_count": 2,
    "active_capas_count": 1
  }
}
```

**Response not blocked:**

```json
{
  "success": true,
  "data": {
    "blocked": false,
    "active_findings_count": 0,
    "active_capas_count": 0
  }
}
```

### §3.9 Scheduler side-effects — CAPA escalation (KHÔNG phải REST endpoint)

`check_capa_due` (cron daily, `hooks.py` scheduler) KHÔNG có request/response client. Hợp đồng side-effect (Vòng 13, RC-CAPA-ESC):

| Khía cạnh | Hợp đồng |
|---|---|
| Tier kích hoạt | **ĐỘC LẬP** theo `effective_risk × overdue_days` (KHÔNG if/elif loại trừ). Critical ≥1d→L1, ≥3d→L1+L2; High ≥3d→L2; Medium/Low→none. |
| Effective-risk SoT | `_capa_escalation_severity(row)` — `imm_risk_level` khi High/Critical, else `severity`-normalized. `severity='Critical'` escalate đúng dù `imm_risk_level` rỗng/Medium. |
| Idempotency | Field `escalation_level` (Int, read-only) = tier cao nhất đã gửi. Chỉ gửi tier `> escalation_level` → cron daily KHÔNG re-send. |
| Audit | Mỗi tier mới = 1 IMM Audit Trail (`event_type="CAPA"`, `change_summary` ghi Level-N). |
| Recipient | L1 = `responsible`; L2 = `responsible` + `notify_roles.CAPA_ESCALATION_MANAGER` (= `Compliance Manager`) qua `_get_role_emails` (SoT R21). |
| Endpoint exposure | `escalation_level` tự lộ trong `get_capa` response (api delegate verbatim — KHÔNG sửa whitelist). |

---

## §4 Error Code Catalog

| Code | HTTP Analog | Business Rule | Mô tả |
|---|---|---|---|
| `FIN-001` | 422 | VR-01 | Threshold JSON không hợp lệ — thiếu metric/op/value |
| `FIN-002` | 422 | VR-02 | evaluation_frequency không hợp lệ |
| `FIN-003` | 500 | — | Không thể tạo Rule |
| `FIN-004` | 422 | VR-04 | Waiver thiếu lý do/evidence/expiry hợp lệ |
| `FIN-005` | 422 | VR-05 | CAPA phải chọn root_cause_method khi advance to Action Plan |
| `FIN-006` | 403 | BR-16-06 | Role không được phép waive (chỉ VP Block2) |
| `FIN-007` | 422 | VR-07 | CAPA không thể Close khi effectiveness chưa Effective |
| `FIN-008` | 422 | VR-08 | Audit có Major NC chưa link CAPA (BR-16-04) |
| `FIN-009` | 422 | VR-09 | Scorecard đã published — không thể sửa |
| `FIN-010` | 422 | VR-10 | Quý trước thiếu Management Review (BR-16-08) |
| `FIN-011` | 422 | VR-11 | Thay đổi Rule threshold/severity thiếu change_summary |
| `FIN-012` | 422 | VR-12 | CAPA due_date phải sau hôm nay (Action Plan) |
| `FIN-013` | 422 | BR-16-09 | Asset bị block do CAPA Critical OPEN |
| `INVALID_STATE` | 422 | — | Workflow transition không hợp lệ |
| `NOT_FOUND` | 404 | — | DocType không tồn tại |
| `FORBIDDEN` | 403 | — | Role không có quyền |
| `VALIDATION_ERROR` | 422 | — | Generic validation fail |
| `CREATE_ERROR` | 500 | — | Insert exception |
| `MR_MISSING_QUARTERLY` | 422 | BR-16-08 | Alias cho FIN-010 |
| `CAPA_LINK_REQUIRED` | 422 | BR-16-04 | Alias cho FIN-008 |

---

## §5 TypeScript Types

> ✅ IMPLEMENTED — Wave 2. Types được định nghĩa **inline** trong `frontend/src/api/imm16.ts` (không có file `frontend/src/types/imm16.ts` riêng — confirmed 2026-05-18). Danh sách interface thực tế: `ComplianceRule`, `ComplianceFinding`, `InternalAudit`, `CapaRecord`, `CapaDetail`, `ComplianceScorecard`, `MRAttendee`, `MROutputActionRow`, `ManagementReview`, `DashboardStats`, `DashboardKpis`, `ComplianceHeatmap`, `HeatmapCell`, `GateReason`, `ComplianceGateResult`, `RecordHistoryEntry`, `ChecklistItemPayload`.

```typescript
// frontend/src/types/imm16.ts

// ── Finding ──────────────────────────────────────────────────────────
export type FindingSeverity = 'Low' | 'Medium' | 'High' | 'Critical'

export type FindingStatus =
  | 'Open'
  | 'Under Review'
  | 'Confirmed NC'
  | 'False Positive'
  | 'Resolved'
  | 'Waived'
  | 'Closed'

export interface ComplianceFinding {
  name: string
  rule: string
  detected_date: string
  asset: string | null
  responsible_dept: string | null
  severity: FindingSeverity
  current_value: string | null
  threshold_value: string | null
  status: FindingStatus
  capa_ref: string | null
  waiver_reason: string | null
  waiver_expiry: string | null
  evaluation_date: string
  workflow_state: string
  /** SSoT server-driven CTA (GATE-8 / LL-FE-51) — trạng thái-đích hợp lệ do
   *  get_finding emit = _FINDING_VALID_TRANSITIONS.get(status, []). Gate nút bằng
   *  `can('compliance.write') && allowed_transitions.includes('<đích>')` — KHÔNG so
   *  status === client-side. Optional (worker cũ chưa enrich → undefined → 0 CTA). */
  allowed_transitions?: string[]
  /** Eligibility CTA Tạo/Liên kết CAPA = (status==='Confirmed NC' && !capa_ref),
   *  derive server-side. FE KHÔNG hardcode 'Confirmed NC'. Optional → fallback false. */
  can_create_capa?: boolean
}

// ── CAPA ─────────────────────────────────────────────────────────────
export type CapaWorkflowState =
  | 'Open'
  | 'Investigating'
  | 'Action Plan'
  | 'Implementation'
  | 'Verification'
  | 'Closed'
  | 'Re-opened'

export type CapaRiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

export interface CapaRecord {
  name: string
  asset: string
  severity: string
  status: string
  workflow_state: CapaWorkflowState
  source_type: string
  source_ref: string | null
  due_date: string | null
  closed_date: string | null
  effectiveness_check: 'Effective' | 'Partially Effective' | 'Not Effective' | null
  imm_root_cause_method: string | null
  imm_risk_level: CapaRiskLevel
  imm_reopen_count: number
  escalation_level?: number   // NEW Vòng 13 — tier escalation cao nhất đã gửi (0/1/2); read-only, tự lộ qua get_capa (api delegate verbatim)
  imm_compliance_finding_ref: string | null
  imm_rca_ref: string | null
  imm_action_plan: CapaActionStep[]
  /** SSoT server-driven CTA (GATE-8 / LL-FE-51, ADR-IMM-16-03) — workflow_state-đích
   *  hợp lệ do get_capa emit = sorted(_CAPA_TRANSITIONS[workflow_state]) khi caller có
   *  compliance.write, [] khi không. Gate nút bằng
   *  `can_advance && allowed_transitions.includes('<đích>')` — KHÔNG so workflow_state ===
   *  client-side. CHỈ get_capa (detail) phát; optional (worker cũ → undefined → 0 CTA). */
  allowed_transitions?: string[]
  /** = rbac.can('compliance.write') derive server-side; cờ tường minh gate CTA advance +
   *  2 nút hiệu quả Đóng/Mở lại. Optional → fallback false. */
  can_advance?: boolean
}

export interface CapaActionStep {
  step_no: number
  action_description: string
  owner: string | null
  planned_date: string | null
  completed_date: string | null
  status: 'Pending' | 'In Progress' | 'Done' | 'Blocked'
}

// ── Scorecard ─────────────────────────────────────────────────────────
export interface ScoreByModule {
  module: string
  score: number
  findings_count: number
}

export interface ScoreByDepartment {
  dept: string
  score: number
  findings_count: number
}

export interface ComplianceScorecard {
  name: string
  period_year: number
  period_month: number
  scope: 'Hospital' | 'Block' | 'Department'
  total_rules_evaluated: number
  compliant_count: number          // adjudicated-compliant (BR-16-11)
  non_compliant_count: number      // Confirmed NC
  pending_count?: number           // Open + Under Review (read-only; runtime-only field)
  score_pct: number                // FE chỉ ĐỌC — KHÔNG inline-compute
  trend_vs_prev_month: number
  score_by_module: ScoreByModule[]
  score_by_department: ScoreByDepartment[]
  capa_open_count: number
  capa_overdue_count: number
  is_published: boolean
  published_at: string | null
  approved_by_for_review: string | null
  restate_of: string | null
}

// ── Dashboard ─────────────────────────────────────────────────────────
export interface DashboardKpis {
  overall_compliance_pct: number
  findings_open: number
  findings_critical: number
  capa_open: number
  capa_overdue: number
  audits_in_progress: number
  mr_quarterly_status: 'Done' | 'Pending' | 'Overdue'
}

export interface DashboardStats {
  kpis: DashboardKpis
  trend_12m: { month: string; score_pct: number }[]
  top_modules_low: { module: string; score: number }[]
  recent_findings: ComplianceFinding[]
}

// ── Heatmap ────────────────────────────────────────────────────────────
export interface HeatmapCell {
  module: string
  dept: string
  score: number
  findings_count: number
}

export interface ComplianceHeatmap {
  modules: string[]
  departments: string[]
  matrix: HeatmapCell[]
}

// ── Gate ────────────────────────────────────────────────────────────────
export interface GateReason {
  type: 'CAPA_CRITICAL_OPEN'
  ref: string
  status: string
  workflow_state: string
  message: string
}

export interface ComplianceGateResult {
  blocked: boolean
  asset?: string
  reasons?: GateReason[]
  active_findings_count: number
  active_capas_count: number
}

// ── API response helpers ───────────────────────────────────────────────
export interface ApiOk<T> {
  success: true
  data: T
}

export interface ApiErr {
  success: false
  error: string
  code: string
}

export type ApiResult<T> = ApiOk<T> | ApiErr
```

---

## §6 Webhook / Realtime Events

| Event | Trigger | Payload |
|---|---|---|
| `imm16:finding_created` | `upsert_finding()` | `{name, severity, asset, dept}` |
| `imm16:finding_status_changed` | confirm / false_positive / waive | `{name, status, reviewer}` |
| `imm16:capa_created` | `create_capa_from_finding` | `{name, risk_level, source_ref}` |
| `imm16:capa_state_changed` | `advance_capa_state` | `{name, new_state, reopen_count}` |
| `imm16:scorecard_published` | `publish_scorecard` | `{name, period, score_pct}` |
| `imm16:audit_closed` | `close_audit` | `{name, findings_count}` |

Phát qua `frappe.publish_realtime(channel, payload)`. FE subscribe trong `stores/imm16Store.ts`.

**Audit-trail (IMM Audit Trail hash chain — `utils.lifecycle.log_audit_event`, KHÔNG realtime) — ĐÚNG 1 record/thao tác:**

| `event_type` | Trigger | Fields |
|---|---|---|
| `audit_started` | `start_audit` | `asset=''`, `ref_doctype='IMM Internal Audit'`, `ref_name`, `from_status=Planned`, `to_status=In Progress` |
| `audit_checklist_completed` | `complete_audit_checklist` | `… from_status=In Progress`, `to_status=Reporting` |
| `audit_closed` | `close_audit` | `… from_status=Reporting`, `to_status=Closed` |

---

## §7 Endpoint ↔ Business Rule Mapping

| Endpoint | Business Rules |
|---|---|
| `create_rule` | VR-01 (threshold JSON), VR-02 (frequency) |
| `update_rule` | VR-11 (change_summary khi threshold/severity đổi), BR-16-05 |
| `waive_finding` | VR-04 (reason/evidence/expiry), BR-16-06 (role VP Block2) |
| `start_audit` | guard Planned→In Progress; BR-16-10 (audit-event `audit_started`) |
| `complete_audit_checklist` | guard In Progress-only → Reporting; BR-16-10 (audit-event `audit_checklist_completed`) |
| `close_audit` | VR-13 (chỉ từ Reporting — chặn jump-skip), VR-08 (Major NC phải có CAPA), BR-16-04, BR-16-10 (audit-event `audit_closed`) |
| `advance_capa_state(Action Plan)` | VR-05 (root_cause_method), VR-12 (due_date) |
| `advance_capa_state(Closed)` | VR-06 (effectiveness_check), VR-07 (phải Effective), BR-16-03 |
| `perform_effectiveness_check` | BR-16-03 (Re-open nếu Not Effective) |
| `publish_scorecard` | VR-09 (immutable), VR-10 (MR quý trước), BR-16-07, BR-16-08 |
| `check_asset_compliance_status` | BR-16-09 (gate IMM-08/09/13/14) |
