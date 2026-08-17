# 04 — Backend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Cập nhật | 2026-05-14 |
| Trạng thái | ✅ Live — `services/imm12.py` và `api/imm12.py` đã implement |

---

## 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────┐
│  api/imm12.py   ← @frappe.whitelist() — thin wrapper     │
│  api/imm00.py   ← CAPA endpoints (✅ LIVE)                │
└──────────────────────┬───────────────────────────────────┘
                       │ no logic — delegate only
                       ▼
┌──────────────────────────────────────────────────────────┐
│  services/imm12.py  ← orchestration + IMM-12 logic       │
│  services/imm00.py  ← CAPA / audit / lifecycle (✅ LIVE)  │
└──────────────────────┬───────────────────────────────────┘
                       │ frappe.get_doc / frappe.db
                       ▼
┌──────────────────────────────────────────────────────────┐
│  DocType Controllers                                      │
│  Incident Report (`incident_report`) ✅ LIVE              │
│  IMM RCA Record (`imm_rca_record`) ✅ LIVE                │
│  IMM CAPA Record (`imm_capa_record`) ✅ LIVE              │
└──────────────────────────────────────────────────────────┘
```

**Conventions:**
- Type hints + docstring cho mọi function
- API layer: parse params → call service → `_ok()` / `_err()`
- ServiceError: `raise frappe.ValidationError("...")` — caught by `_handle()`
- Naming: `snake_case` Python, `PascalCase` DocType

---

## 2. DocTypes

### 2.1 Incident Report ✅ DocType: `incident_report`

> DocType name: `Incident Report`. DocType folder: `assetcore/assetcore/doctype/incident_report/`. Fields below reflect actual schema.

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `severity` | Select (Minor/Major/Critical) | Yes | — |
| `fault_code` | Data | No | Lookup catalog |
| `clinical_impact` | Text | Conditional | Required if Critical (BR-12-01) |
| `acknowledged_by` | Link User | No | Set on Acknowledge |
| `acknowledged_at` | Datetime | No | Auto |
| `resolved_by` | Link User | No | Set on Resolve |
| `resolved_at` | Datetime | No | Auto |
| `closed_by` | Link User | No | Set on Close |
| `closed_at` | Datetime | No | Auto |
| `linked_repair_wo` | Link / Data | No | IMM-09 (actual field name: `linked_repair_wo`) |
| `rca_record` | Link RCA Record | No | Auto when trigger |
| `requires_rca` | Check | No | `default:0`, **user-editable manual additive-override** ("Tự động bật nếu severity=High/Critical; có thể bật thủ công cho case khác"). Là input của điều kiện workflow JSON `doc.severity in ('High','Critical') or doc.requires_rca==1`. Gate close đọc field NÀY (LIVE) như phần OR của predicate RCA-obligation — xem BR-12-02 / ADR-IMM12-RCA-LIVE-SSoT |
| `rca_required` | Check | No | **`read_only:1` — DERIVED MIRROR của `_needs_rca(severity)`** (KHÔNG phải input của gate). `validate_incident_close_gate` recompute `= 1 if _needs_rca(severity) else 0` MỖI lần save ⇒ escalation Medium→Critical + `doc.save()` → `1` LIVE (KHÔNG stale set-once). Nuôi KPI `rca_pending` + list column; gate close **KHÔNG** đọc cờ này (BR-12-02) |
| `linked_capa` | Link IMM CAPA Record | No | Set after RCA Submit |
| `chronic_failure_flag` | Check | No | Set by scheduler |
| `assigned_to` | Link User | No | KTV phụ trách |
| `client_request_id` | Data | No | **CR-24 (Round 32)** — idempotency key mobile write-outbox. `search_index:1` (sinh DB index → dedupe index-seek O(1)); `hidden:1` + `read_only:1` + `no_copy:1` (field kỹ thuật, KHÔNG copy sang amendment — chống crid propagate làm false dedupe-hit). Rỗng (`""`) cho call-path cũ web/desk → backward-compat. Xem §2.1a |

**Permission Query (DocType level):**
```python
def get_permission_query_conditions(user):
    """Reporting User chỉ thấy IR của department mình."""
    if "IMM Workshop Lead" in frappe.get_roles(user):
        return ""  # see all
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    return f'`tabIncident Report`.`department` = "{dept}"'
```

**Indexes:**
```sql
CREATE INDEX idx_ir_asset_fault_date
  ON `tabIncident Report` (asset, fault_code, reported_at);
CREATE INDEX idx_ir_severity_status
  ON `tabIncident Report` (severity, status);
-- CR-24 (Round 32): sinh TỰ ĐỘNG bởi `client_request_id` field-prop `search_index:1`
-- (KHÔNG viết SQL thủ công — Frappe `bench migrate` tạo index). Đáp ứng acceptance
-- "dedupe lookup KHÔNG quét full-table (O(1)/index-seek)". NON-UNIQUE (xem ADR-IMM12-09
-- — UNIQUE loại vì nhiều dòng `client_request_id=""` của call-path cũ).
CREATE INDEX client_request_id
  ON `tabIncident Report` (client_request_id);
```

### 2.1a Idempotency `client_request_id` — mobile write-outbox re-drain (CR-24, Round 32) 🆕 SPEC

> ⚠️ **[LANDED-DELTA 2026-07-14 — hiện thực KHÁC spec dưới, đã VERIFY @source]:** bản land (ADR-MOBILE-047, Accepted) chốt (1) **`unique:1`** thay `search_index:1` — NULL-store: `doc.client_request_id = key` CHỈ khi truthy (`services/imm12.py:544-545`) → phiếu không-khoá lưu **NULL**, MariaDB unique cho phép nhiều NULL ⇒ backward-compat GIỮ (lo ngại "`""` collide" của ADR-IMM12-09 không xảy ra); (2) scope **GLOBAL theo key** — `_dedupe_lookup` (@:450) KHÔNG lọc `reported_by`; (3) thêm **lớp-2 race-handler** `except frappe.UniqueValidationError → clear_last_message → re-read winner` (@:549-560). Field props thật: `incident_report.json` = `unique:1, read_only, no_copy, set_only_once` (KHÔNG `search_index`, KHÔNG `hidden`). Spec dưới GIỮ nguyên làm sử liệu; ADR-IMM12-09 → **Superseded**. Spec photo-dedupe (§2.1b) bám pattern ĐÃ LAND.

> **Bối cảnh (WHY).** App mobile ghi offline qua **write-outbox**: khi mất mạng, action `report_incident` xếp hàng trong outbox local; khi có mạng lại, outbox **re-drain** (gửi lại). Nếu response của lần gửi đầu bị mất (timeout/mạng rớt SAU khi server đã tạo phiếu), client tưởng thất bại → giữ trong outbox → **re-drain gửi LẠI** → tạo **phiếu sự cố TRÙNG**. NĐ98 yêu cầu vết sự cố / audit trail toàn vẹn — phiếu trùng + lifecycle event trùng + audit trail trùng = **làm bẩn vết audit**. `client_request_id` (UUID sinh client-side, ổn định qua mọi lần re-drain của CÙNG một action outbox) đóng cửa sổ này.

**Field schema (DocType `Incident Report`):**

| Prop | Giá trị | Lý do |
|---|---|---|
| `fieldname` | `client_request_id` | — |
| `fieldtype` | `Data` | UUID string (mirror `fault_code` Data — precedent field có `search_index`) |
| `search_index` | `1` | Sinh **DB index non-unique** trên cột → dedupe lookup = index-seek (acceptance O(1)) |
| `unique` | `0` (KHÔNG set) | UNIQUE loại — xem ADR-IMM12-09 (nhiều dòng `""` của call-path cũ sẽ collide) |
| `hidden` | `1` | Field kỹ thuật — KHÔNG hiện form web/desk |
| `read_only` | `1` | Set 1 lần lúc insert, KHÔNG sửa sau |
| `no_copy` | `1` | Incident Report submittable (`amended_from`) — chống crid copy sang amendment → false dedupe-hit |
| `reqd` | `0` | OPTIONAL — call-path cũ (web/desk) KHÔNG gửi ⇒ backward-compat 100% |

**Dedupe algorithm (service `report_incident`, đặt ở ĐẦU hàm — TRƯỚC validate/insert/log/event):**

```python
def report_incident(asset, incident_type, severity, description, *,
                    ..., client_request_id: str = "") -> dict:
    actor = reported_by or frappe.session.user
    # CR-24: idempotency guard — re-drain outbox KHÔNG tạo phiếu trùng (BR-12-25).
    # Scope (client_request_id, reported_by): cùng key + cùng người báo → CÙNG action.
    # Bỏ qua khi rỗng → call-path cũ NGUYÊN VẸN (mỗi call = 1 phiếu).
    if client_request_id:
        existing = frappe.db.get_value(
            _DT_INCIDENT,
            {"client_request_id": client_request_id, "reported_by": actor},
            ["name", "status", "severity"], as_dict=True,
        )
        if existing:
            # Trả phiếu ĐÃ tạo — KHÔNG insert, KHÔNG _log, KHÔNG emit lifecycle event.
            return {"name": existing.name, "status": existing.status,
                    "severity": existing.severity}
    # ... validate (BR-12-01 clinical_impact / asset exists) + tạo doc như cũ ...
    doc.client_request_id = client_request_id   # persist (rỗng cho call cũ)
    doc.insert()
    # ... _log() + _emit_incident_reported_event() như cũ ...
    return {"name": doc.name, "status": doc.status, "severity": severity}
```

**Invariant (INV-IDEMP-12):**
- `client_request_id` non-empty, gọi 2× → **CHỈ 1 dòng** `tabIncident Report`; call thứ 2 return `name` phiếu đã có.
- Sau call trùng thứ 2: `count(Asset Lifecycle Event, event_type='incident_reported', root_record=<IR>) == 1` **VÀ** `count(IMM Audit Trail cho <IR>) == 1` (early-return TRƯỚC `_log`/emit ⇒ không double).
- `client_request_id` rỗng/thiếu → mỗi call = 1 phiếu (guard skip).
- 2 `client_request_id` KHÁC nhau → 2 phiếu riêng.
- Return shape của dedupe-hit **BẰNG** shape create thường: `{name, status, severity}` (3-key).

### ADR-IMM12-09: Idempotency `client_request_id` = app-level dedupe (SELECT-before-insert) + index NON-UNIQUE, KHÔNG DB UNIQUE constraint
- **Status**: **Superseded by ADR-MOBILE-047** (bản land 2026-07-14: `unique:1` NULL-store + GLOBAL-key + race-handler `UniqueValidationError` — chính là phương án "UNIQUE + lưu NULL khi rỗng" mà ADR này để dành hardening; NULL-store qua persist-if-truthy KHÔNG cần override write-path như lo ngại ở Alternatives)
- **Date**: 2026-07-14
- **Context**: Mobile write-outbox re-drain tạo phiếu sự cố trùng (NĐ98 audit-integrity). Cần idempotency key ổn định. Ràng buộc: (a) backward-compat 100% — call-path cũ web/desk KHÔNG gửi key ⇒ field mặc định `""`, nhiều phiếu cùng `""` phải cùng tồn tại; (b) không double lifecycle event / audit; (c) lookup index-seek KHÔNG full-scan.
- **Decision**: Dedupe ở **application-layer** — `frappe.db.get_value(_DT_INCIDENT, {client_request_id, reported_by})` SELECT-before-insert ở đầu service; trúng → early-return phiếu cũ (bỏ qua insert/log/event). Index = **`search_index:1` NON-UNIQUE** trên cột `client_request_id`. Scope dedupe = `(client_request_id, reported_by)` (cùng "reporter" theo acceptance).
- **Alternatives (loại + lý do)**:
  - **DB UNIQUE index trên `client_request_id`**: LOẠI. Frappe Data field mặc định lưu `""` (KHÔNG NULL); UNIQUE trên `""` → call-path cũ thứ 2 (không key) bị **DuplicateEntryError** ⇒ phá backward-compat (acceptance "mỗi call = 1 phiếu").
  - **UNIQUE + lưu NULL khi rỗng** (MariaDB cho phép nhiều NULL, chặn trùng non-NULL): LOẠI ở round này. Frappe app-level `validate_duplicate` bỏ qua giá trị rỗng NHƯNG vẫn ép `""` xuống cột (không tự NULL-hoá) ⇒ phải override write-path để set None — tăng bề mặt rủi ro; và app-guard đã đáp ứng ĐỦ acceptance (test tuần tự). Ghi nhận là **hardening tương lai** nếu cần chống race.
  - **Client gửi `name` cố định (idempotent-PUT)**: LOẠI. Va chạm naming_series (`INC-.YYYY.-`) + lộ cấu trúc name ra client.
- **Consequences**:
  - ➕ Backward-compat trọn vẹn; migration nhẹ (1 field + 1 index, `bench migrate`).
  - ➕ Return-early trước `_log`/emit ⇒ 0 double audit / 0 double lifecycle event.
  - ➖ **Residual race** (đã biết, chấp nhận): 2 re-drain ĐỒNG THỜI cùng key có thể cùng miss SELECT rồi cùng insert → 2 phiếu. Chấp nhận vì: outbox drain **tuần tự per-device** (1 hàng đợi/thiết bị), `client_request_id` là UUID; acceptance test tuần tự. Hardening (UNIQUE-via-NULL) để dành round sau nếu quan sát thấy trùng thực tế.
  - ➖ Thêm 1 SELECT/req khi có key — chi phí index-seek, không đáng kể.

### 2.1b Idempotency ảnh hiện trường `client_request_id` — `attach_incident_photo` (CR-24 phần dư · B-rel-3, vòng 3) 🆕 SPEC

> **Bối cảnh (WHY).** Mobile drain PHA-2 đính ảnh theo `photoCursor`: response `attach_incident_photo` rớt mạng SAU khi server đã tạo File → cursor không advance → re-drain re-POST cùng ảnh → **File TRÙNG + event `incident_photo_attached` TRÙNG** (bẩn evidence-trail NĐ98). Frappe không tự đóng: `File.validate_duplicate_entry` (`frappe/core/doctype/file/file.py:413-441`) trùng content_hash CHỈ reuse `file_url` — vẫn insert ROW mới + service vẫn emit event lần 2. Spec API-mặt-ngoài: `05 §15a`.

**Dedupe anchor — Custom Field trên `File` (core → extend qua fixture, KHÔNG sửa core):**

| Prop | Giá trị | Lý do |
|---|---|---|
| `dt` | `File` | Record sinh ra của flow = File — key sống cùng record (no-TTL, ADR-IMM12-10 (c)) |
| `fieldname` | `ac_client_request_id` | Prefix `ac_` = app-scoped trên doctype core dùng chung site (tránh va app khác — bài học orphan custom-field mvl) |
| `fieldtype` | `Data` | Composite scoped key, ≤140 ký tự |
| **Giá trị lưu** | **`f"{incident_name}::{client_request_id}"`** (composite SCOPED) | 1 cột unique mã hoá scope `(incident, key)`: cùng key+cùng incident → cùng value → unique chặn race (AC2); cùng key+KHÁC incident → value KHÁC → 2 File hợp lệ (AC4). ~52 ký tự (INC-name 14 + `::` + UUID 36) < 140 |
| `unique` | `1` | Lớp-2 race (NULL-store: chỉ set khi key truthy → File thường = NULL, multi-NULL hợp lệ — pattern ADR-MOBILE-047) |
| `hidden` / `read_only` / `no_copy` | `1` / `1` / `1` | Field kỹ thuật, set 1 lần lúc insert, không copy |
| `insert_after` | `attached_to_name` | Anchor field có thật trên File |
| Fixture | `assetcore/fixtures/file_custom_fields.json` + entry `hooks.py fixtures` (module-tag AssetCore) | Precedent `imm15_custom_fields.json`/`imm16_*`; sync qua `bench migrate`/`import-fixtures` |

**Thuật toán (service `attach_incident_photo` — dedupe SAU permission, TRƯỚC validation; vì sao: `05 §15a`):**

```python
def attach_incident_photo(incident_name, filedata=None, filename="",
                          content_type="", client_request_id: str = "") -> dict:
    incident = _get_incident(incident_name)          # NOT_FOUND
    _assert_can_attach_photo(incident)               # FORBIDDEN (TRƯỚC dedupe — chống probe key leak file_url)
    # CR-24 phần dư: dedupe pre-check (lớp-1) — replay trả File ĐÃ đính, 0 insert / 0 event.
    scoped_key = f"{incident_name}::{client_request_id}" if client_request_id else ""
    if scoped_key:
        existing = frappe.db.get_value(_DT_FILE, {"ac_client_request_id": scoped_key},
                                       ["file_url", "file_name"], as_dict=True)
        if existing:
            return {"file_url": existing.file_url, "file_name": existing.file_name}
    # ... validation ladder CŨ nguyên vẹn: file present → content-type → size → max-count ...
    try:
        file_doc = frappe.get_doc({..., "ac_client_request_id": scoped_key or None}).insert(...)
    except (UnidentifiedImageError, OSError) as exc:
        ...  # nhánh corrupt CŨ giữ nguyên
    except frappe.UniqueValidationError:
        # Lớp-2 race: request concurrent cùng scoped_key đã insert giữa pre-check và insert này.
        # Kẻ thua raise TRƯỚC create_lifecycle_event ⇒ 0 event trùng. Re-read winner → idempotent.
        frappe.clear_last_message()
        winner = frappe.db.get_value(_DT_FILE, {"ac_client_request_id": scoped_key},
                                     ["file_url", "file_name"], as_dict=True)
        if winner:
            return {"file_url": winner.file_url, "file_name": winner.file_name}
        raise
    # ... create_lifecycle_event(incident_photo_attached) + commit CŨ nguyên vẹn ...
```

**Invariant (INV-IDEMP-12-PHOTO):**
- Cùng `(incident, key)` POST 2× → **1 ROW File** ∧ `count(Asset Lifecycle Event, event_type='incident_photo_attached', root_record=IR) == 1`; call#2 return `{file_url, file_name}` **==** call#1 (shape EXACT 2-key KHÔNG đổi — OAS guard (e) GIỮ).
- Key rỗng → mỗi call = 1 File mới (at-least-once cũ; `ac_client_request_id` = NULL).
- Cùng key + KHÁC incident → 2 File (composite KHÁC — không dedupe chéo).
- Dedupe-hit thắng max-count: incident đủ 5 ảnh, replay key của ảnh đã đính → success (KHÔNG `VALIDATION "Tối đa 5 ảnh"`).
- Permission-before-dedupe: user không-reporter/không-write replay key hợp lệ → FORBIDDEN (không leak `file_url`).

### ADR-IMM12-10: Idempotency ảnh = composite scoped key `{incident}::{key}` trên Custom Field `File.ac_client_request_id` (unique NULL-store, 2 lớp, KHÔNG TTL)
- **Status**: Accepted
- **Date**: 2026-07-16
- **Context**: Đóng attachment-dup re-drain (CR-24 phần dư, B-rel-3). KHÁC `report_incident`: record đích là **`File` — doctype CORE** (không sửa core → chỉ extend); acceptance đòi scope **per-incident** (AC4: cùng key khác incident = 2 File); response phải GIỮ EXACT 2-key `{file_url,file_name}` (OAS closed). **Backend-confirm:** (a) Frappe KHÔNG có idempotency request-level sẵn — `File.validate_duplicate_entry` chỉ reuse `file_url` khi trùng content_hash, vẫn insert ROW + service vẫn emit event (`file.py:413-441`) ⇒ tự dedupe; (b) khoá = **body field `client_request_id`** (multipart part) parity `report_incident`, KHÔNG header; (c) **KHÔNG TTL** — key sống cùng File record.
- **Decision**: Custom Field `ac_client_request_id` trên `File` (fixture, module-tag) lưu **composite scoped** `f"{incident_name}::{client_request_id}"`, `unique:1` NULL-store (chỉ set khi key truthy). Dedupe 2 lớp parity ADR-MOBILE-047: lớp-1 pre-check SAU permission/TRƯỚC validation (early-return `{file_url,file_name}` File cũ, 0 event lần 2); lớp-2 `except UniqueValidationError → clear_last_message → re-read winner` (kẻ thua raise TRƯỚC emit ⇒ 0 event trùng).
- **Alternatives (loại + lý do)**:
  - **(A) Header `Idempotency-Key`**: LOẠI — Frappe RPC không route header sạch; body-field nhất quán `report_incident` (ADR-MOBILE-047 Alt-A).
  - **(B) Raw key + `unique:1` (không composite)**: LOẠI — VỠ AC4: cùng key KHÁC incident → unique violation → File #2 hợp lệ bị chặn/raise thay vì tạo.
  - **(C) Index non-unique + pre-check only (lookup filter `attached_to_name`+key)**: LOẠI — hở race concurrent re-drain (2 in-flight cùng qua pre-check → 2 File + 2 event); ADR-MOBILE-047 Alt-E đã loại pattern này.
  - **(D) Registry doctype riêng `AC Idempotency Key` (key, scope, result_json)**: LOẠI round này — over-engineer cho 1 endpoint; +1 DocType + result-snapshot có thể stale vs File thật. **Ghi chú:** cân nhắc LẠI khi generalize backlog imm08/imm09 photo-dedupe (3+ endpoint cùng pattern thì registry bắt đầu trả vốn).
  - **(E) Dựa `content_hash` dedupe sẵn của File**: LOẠI — chỉ reuse `file_url` (vẫn ROW + event trùng); và dedupe-by-content phá at-least-once chủ đích (user đính CÙNG ảnh 2 lần không key phải được 2 File — AC3).
  - **(F) TTL/expiry cho key**: LOẠI — parity ADR-MOBILE-047 Alt-D (over-engineer; client UUID collision-free; exact-match toàn-thời-gian đơn giản + đúng).
- **Consequences**:
  - ➕ AC2 (1 File + 1 event, replay trả kết quả cũ) + AC3 (rỗng → at-least-once cũ, NULL) + AC4 (composite → không dedupe chéo) + race-safe; response shape KHÔNG đổi → OAS response/envelope guard GIỮ.
  - ➕ KHÔNG sửa core: Custom Field fixture (precedent imm15/16), cột NULL cho mọi File ngoài flow này (site dùng chung an toàn).
  - ➖ Cần `bench migrate`/`import-fixtures` (tạo cột + unique index trên `tabFile` — bảng lớn, DDL 1 lần) + gunicorn reload cho HTTP live (HARD-STOP USER — chỉ ghi chú).
  - ➖ File bị xoá → key biến mất → replay sau xoá tạo File mới (chấp nhận — record không còn thì "kết quả đã ghi" không còn; hệ quả trực tiếp của no-TTL/key-sống-cùng-record).
  - ➖ Key rất dài (>~100 ký tự) → composite vượt 140 → insert lỗi DataError; contract client = UUID (~36) ⇒ ngoài contract, không thêm validation (parity report-level không check độ dài). Ghi Boundaries Never.
  - ➖ Composite lộ `incident_name` trong giá trị cột (nội bộ DB, field hidden — chấp nhận).


DocType name: `IMM RCA Record`. Child tables: `IMM RCA Five Why Step` (`imm_rca_five_why_step`) for 5-Why, `IMM RCA Related Incident` (`imm_rca_related_incident`) for chronic grouping.

Naming: `RCA-.YYYY.-.#####` · Submittable

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `asset` | Link AC Asset | Yes | — |
| `incident_report` | Link Incident Report | Yes | Primary source |
| `related_incidents` | Table (RCA Related Incident) | No | Chronic group |
| `fault_code` | Data | No | — |
| `trigger_type` | Select | Yes | Major Incident / Critical Incident / Chronic Failure / Manual |
| `incident_count` | Int | No | Chronic: COUNT in 90 days |
| `rca_method` | Select | Required before Submit | 5Why / Fishbone / Other |
| `root_cause` | Text | Required before Submit | BR-12-07 |
| `contributing_factors` | Text | No | — |
| `five_why_steps` | Table (RCA Five Why Step) | No | When method=5Why |
| `corrective_action_summary` | Text | No | Set on submit_rca (actual field: `corrective_action_summary`) |
| `preventive_action_summary` | Text | No | Set on submit_rca (actual field: `preventive_action_summary`) |
| `due_date` | Date | Yes | +7d or +14d |
| `status` | Select | Yes | RCA Required / RCA In Progress / Completed / Cancelled |
| `assigned_to` | Link User | Yes | — |
| `completed_by` | Link User | No | Set on Submit |
| `completed_date` | Date | No | Auto |
| `linked_capa` | Link IMM CAPA Record | No | Auto after Submit (BR-12-06) |

**IMM RCA Record Controller:** `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py` ✅ EXISTS

---

## 3. Workflow — Incident Report ✅ LIVE

### States (actual — constants `services/imm12.py:37-47` + `imm_12_incident_workflow.json`)

| State | docstatus | Mô tả |
|---|---|---|
| Open | 0 | IR mới tạo |
| Acknowledged | 0 | Workshop Lead/Technician đã tiếp nhận |
| In Progress | 0 | Đang xử lý |
| Resolved | 0 | Đã giải quyết |
| RCA Required | 0 | High/Critical hoặc chronic — chờ RCA Completed trước Close |
| Closed | 0 | Final — IR đóng |
| Cancelled | 0 | False alarm |

> Internal docstring trong `services/imm12.py` đôi chỗ ghi "Under Investigation" — đây là alias lịch sử cho `In Progress`. Tên state thực tế trong code & DocType là `In Progress`.

### Transitions — SSoT `_VALID_TRANSITIONS` (incident) ⇄ `imm_12_incident_workflow.json` (CR-WF-12, Round 12) ✅ SPEC

**`_VALID_TRANSITIONS` là SSoT sinh `allowed_transitions`** — `get_incident_detail()` (`services/imm12.py:1084`) trả `allowed_transitions = _VALID_TRANSITIONS.get(doc.status, [])` → điều khiển render CTA FE (`IncidentDetailView.vue` gate `status===X && allowed_transitions.includes(Y)`). Vì thế map này PHẢI đối soát **edge-by-edge** với workflow JSON, nếu không nút CTA sẽ *dead* (map thừa cạnh workflow từ chối) hoặc *ẩn câm* (workflow cho phép nhưng map thiếu → FE không render).

```python
# services/imm12.py:228 — SSoT DUY NHẤT cho allowed_transitions Incident (drives FE CTA)
_VALID_TRANSITIONS: dict[str, list[str]] = {
    _STATUS_OPEN:          [_STATUS_ACKNOWLEDGED, _STATUS_CANCELLED],
    _STATUS_ACKNOWLEDGED:  [_STATUS_INVESTIGATING, _STATUS_CANCELLED],
    _STATUS_INVESTIGATING: [_STATUS_RESOLVED, _STATUS_CANCELLED],                    # ⬅ Round 12: BỎ 'RCA Required' (drift b — workflow KHÔNG có cạnh In Progress→RCA Required)
    _STATUS_RESOLVED:      [_STATUS_CLOSED, _RCA_REQUIRED, _STATUS_INVESTIGATING],   # ⬅ Round 12: THÊM 'In Progress' = "Mở lại điều tra" (drift a — surface CTA reopen)
}
```

| From | To | Trigger (service / workflow action) | Cap gate | Validation |
|---|---|---|---|---|
| Open | Acknowledged | `acknowledge_incident()` / "Tiếp nhận sự cố" | `incident.acknowledge` | — |
| Open | Cancelled | `cancel_incident()` / "Hủy sự cố" | `incident.acknowledge` | reason required |
| Acknowledged | In Progress | `start_work()` / "Bắt đầu xử lý" | `incident.acknowledge` | — |
| Acknowledged | Cancelled | `cancel_incident()` / "Hủy sự cố" | `incident.acknowledge` | reason required |
| In Progress | Resolved | `resolve_incident()` / "Đánh dấu đã giải quyết" | `incident.acknowledge` | resolution_notes required |
| In Progress | Cancelled | `cancel_incident()` / "Hủy sự cố" | `incident.acknowledge` | reason required |
| Resolved | Closed | `close_incident()` / "Đóng sự cố" | `incident.close` | BR-12-02: High/Critical → RCA `Completed` required |
| Resolved | RCA Required | **`request_rca(name, rca_reason)` / "Yêu cầu RCA" (BR-12-24, Round 38)** — qua `apply_workflow("Yêu cầu RCA")` (KHÔNG `db.set_value`) + sync `status` Select | `compliance.submit` | `rca_reason` required · idempotent RCA reuse · audit `_log` (Resolved→RCA Required) |
| Resolved | In Progress | **`reopen_incident(name, reason)` / "Mở lại điều tra" (BR-12-23, Round 12)** | `incident.close` | reason required · audit `_log` (Resolved→In Progress) |

> **⚠️ Self-Correction (Round 12):** bảng cũ có 3 dòng SAI đã gỡ — (1) `Open → In Progress (skip Acknowledged)`: KHÔNG tồn tại; `_assert_transition` chặn (Open chỉ đi Acknowledged/Cancelled, D3). (2) `In Progress → RCA Required` gán cho `resolve_incident()`: SAI — `resolve_incident()` set status=`Resolved` rồi *auto-tạo RCA Record* (DocType khác), KHÔNG set Incident status; và workflow KHÔNG có cạnh này ⇒ đã gỡ khỏi `_VALID_TRANSITIONS[In Progress]`. (3) `RCA Required → Closed` gán cho `close_incident()`: SAI — đóng qua auto-advance (xem EXCEPTION_EDGES).

**EXCEPTION_EDGES — cạnh workflow CỐ Ý không đưa vào `_VALID_TRANSITIONS`** (không phải CTA-FE, có cơ chế thực thi khác):

| Edge | Cơ chế thực thi | Rationale (vì sao KHÔNG là CTA) |
|---|---|---|
| `RCA Required → Closed` | `_advance_incident_after_rca()` (`services/imm12.py:1475`) auto `apply_workflow(_ACTION_RCA_DONE_CLOSE)` khi RCA Record → `Completed` (test RC-04) | Hệ thống TỰ đẩy sau khi RCA hoàn tất — không có nút bấm. RCA có map CTA riêng `_RCA_VALID_TRANSITIONS` trên `IMM RCA Record`. Nếu đưa vào `_VALID_TRANSITIONS` sẽ tạo CTA "đóng tay" ở trạng thái RCA Required, lách BR-12-02 (đóng khi RCA chưa Completed). |

> **Ghi chú "RCA Required" (Incident status) — grounded (cập nhật Round 38):** Trước Round 38, KHÔNG service nào set `Incident.doc.status = "RCA Required"` (các dòng `rca.status=_RCA_REQUIRED` là **RCA Record**, khác DocType) — Incident vào `RCA Required` CHỈ qua desk workflow. `Resolved → RCA Required` GIỮ trong map vì là cạnh THẬT của workflow (INV-1 pass). **Round 38 (BR-12-24, ADR-IMM12-RCA-ENTRY) ĐÓNG backlog này:** endpoint `request_rca(name, rca_reason)` surface cạnh thành CTA-FE server-driven — Incident vào `RCA Required` qua **`apply_workflow("Yêu cầu RCA")`** (mirror `_advance_incident_after_rca`, KHÔNG `db.set_value` trực tiếp) + sync `status` Select. **KHÔNG đổi `_VALID_TRANSITIONS` NÀO** (state edge đã đúng từ Round 12 — chỉ bổ ENTRY endpoint+CTA) ⇒ INVARIANT `TestIncidentAllowedTransitions` + workflow JSON bất biến ⇒ admin-override 22/22 GREEN. Cap-gate `compliance.submit` (⊆ workflow allowed → KHÔNG false-clickable). `request_rca` ↔ `_advance_incident_after_rca` là ENTRY↔EXIT của nhánh RCA Required (loop đóng kín).

#### 3.0.0 INVARIANT (CR-WF-12) — chống drift câm ✅ SPEC

Đặt `WF = {(state, next_state)}` gom-vai (dedupe theo cặp, bỏ chiều role) từ `imm_12_incident_workflow.json.transitions[]`; `SVC = {(f, t) | t ∈ _VALID_TRANSITIONS[f]}`; `EXCEPTION_EDGES = {("RCA Required","Closed")}`.

- **INV-1 (service ⊆ workflow):** `SVC ⊆ WF` — mọi cạnh trong `_VALID_TRANSITIONS` PHẢI là cạnh THẬT của workflow (chặn nút *dead/bypass*). *Bắt drift (b): trước fix `("In Progress","RCA Required") ∈ SVC \ WF` → RED.*
- **INV-2 (workflow ⊆ service ∪ exception):** `WF ⊆ SVC ∪ EXCEPTION_EDGES` — mọi cạnh workflow HOẶC là CTA (∈ SVC) HOẶC là exception có rationale. *Bắt drift (a): trước fix `("Resolved","In Progress") ∈ WF \ (SVC ∪ EXCEPTION)` → RED.*
- **Codomain:** mọi state trong SVC ⊆ 7 state chuẩn `{Open, Acknowledged, In Progress, Resolved, RCA Required, Closed, Cancelled}`.

Guard: `test_imm12.TestIncidentAllowedTransitions` (mirror `TestRCAAllowedTransitions:2739`) — **RED trước fix, GREEN sau fix**. Fix chỉ đụng SERVICE map + thêm `reopen_incident` handler; **KHÔNG đụng workflow JSON** ⇒ `test_workflow_admin_override` GIỮ GREEN (Super Admin vẫn phủ mọi transition-group — không thêm/bớt cạnh workflow nào).

**RCA States:** `RCA Required` → `RCA In Progress` → `Completed` / `Cancelled`

#### 3.0.1 RCA State Machine — server-driven CTA SSoT (BR-12-19..22, Round 9) ✅ SPEC

RCA có **dual-track** giống Incident/Repair: `status` (domain SSoT, field trên `IMM RCA Record`) song song `workflow_state` (Frappe-native workflow "IMM-12 RCA Workflow"). **Endpoint thao tác trên `status`** (set trực tiếp + `_ok` Decision-B), KHÔNG gọi `apply_workflow` native → `status` là SoT hành động, `workflow_state` là mirror cho desk. (ADR-IMM12-RCA-CTA D1 — §02.)

**SSoT chuyển trạng thái** — thêm map `_RCA_VALID_TRANSITIONS` trong `services/imm12.py` (mirror `_REPAIR_VALID_TRANSITIONS` imm09.py:91, keyed BẰNG hằng `_RCA_REQUIRED/_RCA_IN_PROGRESS/_RCA_COMPLETED/_RCA_CANCELLED`, KHÔNG literal):

```python
# services/imm12.py — SSoT DUY NHẤT cho allowed_transitions RCA (đóng ASYMMETRY:
# imm12 báo-hỏng + imm09 repair đã có allowed_transitions[]; RCA là thành viên kế).
_RCA_VALID_TRANSITIONS: dict[str, list[str]] = {
    _RCA_REQUIRED:    [_RCA_IN_PROGRESS, _RCA_CANCELLED],   # 'RCA Required'
    _RCA_IN_PROGRESS: [_RCA_COMPLETED, _RCA_CANCELLED],     # 'RCA In Progress'
    _RCA_COMPLETED:   [],                                    # terminal
    _RCA_CANCELLED:   [],                                    # terminal
}
```

- **Codomain ⊆** `{RCA Required, RCA In Progress, Completed, Cancelled}` (options field `status`, verified 04 §2.2:107). Terminal `Completed`/`Cancelled` → `[]` (0 outgoing) ⇒ FE KHÔNG render nút.
- **Grounded edge-by-edge** `fixtures/workflow.json` "IMM-12 RCA Workflow" transitions[] (start/complete/cancel). Guard test (`test_imm12.TestRCAAllowedTransitions`) chốt map ↔ enum `status` + payload `get_rca`.
  > **⚠️ Self-Correction (Round 30, CR-WF-12-RCA):** guard cũ chỉ chốt *state-machine* (map codomain ↔ enum `status`) — **KHÔNG** parse workflow-JSON và **KHÔNG** kiểm *role-parity*. Vì thế asymmetry role desk↔endpoint (Corrective Manager thiếu ở "Bắt đầu/Hoàn thành") tồn tại câm dù D2 của ADR-IMM12-RCA-CTA đã tuyên bố `native-allowed == endpoint-allowed`. Fix + 3 invariant `INV-RCA-PARITY-A/B/C` ở §3.0.2 làm luật hoá; xem ADR-IMM12-RCA-PARITY (02 §IV.3).

**Capability gate (root-cause axis-A — chống RBAC dead-gate).** 3 endpoint transition (`start_rca`/`submit_rca`/`cancel_rca`) gate theo **capability `corrective.write`** (SSoT binding `rbac.CAPABILITY_MAP["corrective.write"] = ("Incident Report", "write")` — domain `Corrective` primary DocType = Incident Report, rbac.py:71). Resolve TRUE cho role có DocPerm `write` trên Incident Report: **AssetCore Super Admin, Corrective Manager, Corrective User** (verified incident_report.json perms) — FALSE cho base `AssetCore System User` / Auditor / Commissioning Manager.
- `get_rca` trả cờ `can_manage_rca` (int 0/1) = `1 if rbac.can("corrective.write") else 0` — mirror `allowed_transitions` của `get_work_order` (imm09.py:917). FE dùng `can_manage_rca && đích ∈ allowed_transitions` để render CTA (KHÔNG hardcode role-name, KHÔNG hardcode `status===`).
- **KHÔNG** gate bằng role-name literal (anti-pattern dead-gate) và **KHÔNG** dựa `docstatus`/`_can_close` (submit-level) cho start/cancel — cả 3 là thao tác GHI nội-dung-RCA ⇒ cùng bind `write`.

#### 3.0.2 RCA desk↔endpoint role parity — CR-WF-12-RCA (Trục A) ✅ SPEC

**Vấn đề (grounded @source 2026-07-13).** `corrective.write` (gate 3 endpoint RCA) resolve TRUE cho **{AssetCore Super Admin, Corrective Manager, Corrective User}** (DocPerm `write=1` trên Incident Report). Nhưng workflow desk **`imm_12_rca_workflow.json`** cấp role hẹp hơn ở 2/3 action quản-RCA:

| Action (transition) | Cạnh state | Role-set HIỆN TẠI (source == fixture) | Thiếu | Sau fix |
|---|---|---|---|---|
| **Bắt đầu phân tích RCA** | `RCA Required → RCA In Progress` | {AssetCore Super Admin, Corrective User, System Manager} | **Corrective Manager** | +Corrective Manager → 4 role |
| **Hoàn thành RCA** | `RCA In Progress → Completed` | {AssetCore Super Admin, Corrective User, System Manager} | **Corrective Manager** | +Corrective Manager → 4 role |
| **Hủy RCA** | `RCA Required → Cancelled` · `RCA In Progress → Cancelled` | {AssetCore Super Admin, Corrective Manager, Corrective User, System Manager} | — (đủ) | GIỮ NGUYÊN (4 role) |

⇒ **Corrective Manager gọi được `start_rca`/`submit_rca` (có `corrective.write`) nhưng mở phiếu RCA ở desk KHÔNG THẤY / KHÔNG BẤM được nút "Bắt đầu/Hoàn thành"** (Frappe native enforce quyền theo TỪNG transition-group). Đây là root-cause "user đủ quyền AssetCore nhưng luồng RCA không duyệt được".

**Delta (fix dữ-liệu-role thuần — KHÔNG code Python, KHÔNG đổi `_RCA_VALID_TRANSITIONS`):**

1. `assetcore/assetcore/workflow/imm_12_rca_workflow.json` — THÊM 2 row transition:
   ```json
   { "action": "Bắt đầu phân tích RCA", "allowed": "Corrective Manager", "next_state": "RCA In Progress", "state": "RCA Required",    "allow_self_approval": 1 }
   { "action": "Hoàn thành RCA",        "allowed": "Corrective Manager", "next_state": "Completed",       "state": "RCA In Progress", "allow_self_approval": 1 }
   ```
   (đối xứng đúng `allow_self_approval:1` như các row cùng transition-group; KHÔNG đổi row nào khác.)
2. `assetcore/fixtures/workflow.json` "IMM-12 RCA Workflow" — THÊM **cùng 2 row** (giữ `source == fixture`, INV-C).

Sau fix: role-set mỗi action quản-RCA = **{Corrective User, Corrective Manager, System Manager, AssetCore Super Admin}** (khớp "Hủy RCA" đã có). Tuple-set mọi row khác **bất biến**.

**INVARIANT (làm luật — chống tái-drift câm; mirror `TestIncidentAllowedTransitions` incident):**

- **INV-RCA-PARITY-A (SSoT⇄workflow):** codomain(state→{next_state}) parse từ `imm_12_rca_workflow.json` **== `_RCA_VALID_TRANSITIONS` codomain EXACT** theo set: `RCA Required→{RCA In Progress, Cancelled}`; `RCA In Progress→{Completed, Cancelled}`; `Completed→∅`; `Cancelled→∅`. (Bổ khuyết `TestRCAAllowedTransitions` — vốn KHÔNG parse workflow-JSON.)
- **INV-RCA-PARITY-B (desk == endpoint):** ∀ action ∈ {Bắt đầu phân tích RCA, Hoàn thành RCA, Hủy RCA}: `workflow.allowed_role_set(action) ⊇ roles(corrective.write) ∪ {AssetCore Super Admin, System Manager}`. `roles(corrective.write)` tính **ĐỘNG** qua `rbac.CAPABILITY_MAP["corrective.write"] = ("Incident Report","write")` → DocPerm write=1 (KHÔNG hardcode role-name). Dùng **⊇** (không `==`): workflow được PHÉP rộng hơn cap-gate (admin-override), KHÔNG được hẹp hơn. **RED trước fix** (Start/Complete thiếu Corrective Manager) → **GREEN sau**.
- **INV-RCA-PARITY-C (fresh-install seed):** `fixtures/workflow.json` "IMM-12 RCA Workflow" transition tuple-set (state, action, next_state, allowed) **== source** `imm_12_rca_workflow.json` — site cài mới seed đúng như dev.

**Live-sync (KHÔNG `bench migrate` — HARD-STOP USER).** Đồng bộ Workflow doc "IMM-12 RCA Workflow" trên site đang chạy qua `setup.backfill_workflow_admin.run` (append admin-role) **HOẶC** re-import fixture / chỉnh live Workflow doc. **Lưu ý:** `backfill_workflow_admin` chỉ APPEND `{AssetCore Super Admin, System Manager}` — **KHÔNG tự thêm `Corrective Manager`**; role này vào live qua fixture re-import hoặc chỉnh Workflow doc trực tiếp (xem 08 §RCA-parity). Sau sync: user role `Corrective Manager` mở phiếu RCA ở desk THẤY + BẤM được nút "Bắt đầu/Hoàn thành phân tích". `_RCA_VALID_TRANSITIONS` (runtime service) **KHÔNG đổi** ⇒ FE `allowed_transitions`/`can_manage_rca` bất biến (Corrective Manager vốn đã có `can_manage_rca=1` trên SPA; fix này vá đường DESK/native-workflow).

**BR-12-04:** Critical → auto asset Out of Service on `report_incident()`. High → auto asset Out of Service on `acknowledge_incident()`.
**BR-12-02:** High/Critical Incident cannot close until linked RCA status = `Completed`.
**Asset restore:** `close_incident()` checks if asset is `Out of Service` and transitions back to `Active`.

#### 3.0.3 RCA-gate close_incident — DERIVE-LIVE `severity` SSoT (BR-12-02 / ADR-IMM12-RCA-LIVE-SSoT) ✅ SPEC (Round 4)

**Vấn đề (đóng-giả escalation):** cả 2 gate BR-12-02 CŨ quyết định trên cờ STORED `rca_required` (set-once lúc `report_incident:@541`), KHÔNG re-derive khi `severity` đổi ⇒ phiếu tạo Medium (`rca_required=0`) rồi escalate Critical **lọt CẢ 2 gate**:
- gate-1 `close_incident:@711` cũ: `if _needs_rca(doc.severity) and doc.rca_required:` → `True and 0` = **False** → skip.
- gate-2 `validate_incident_close_gate:@1750-1752` cũ: `if severity not in _HIGH_SEVERITY: return` rồi `if not requires_rca and not rca_required: return` → escaped bởi cờ stale.

**SSoT (LIVE) — predicate nghĩa-vụ-RCA** dùng CHUNG bởi 2 gate + workflow JSON:

```
requires_rca_obligation(doc) := _needs_rca(doc.severity)  OR  doc.requires_rca == 1
                             := (severity ∈ {High, Critical}) OR (manual override)
```

MIRROR ĐÚNG `imm_12_incident_workflow.json:103/196/204` `doc.severity in ('High','Critical') or doc.requires_rca == 1` ⇒ **triple-parity workflow-JSON ⇔ gate-1 ⇔ gate-2**.

| Gate | File:line | Điều kiện MỚI | Reject |
|---|---|---|---|
| gate-1 service | `close_incident:711` | `if _needs_rca(doc.severity) or doc.requires_rca:` (bỏ `and doc.rca_required`) | thiếu `rca_record` → `nthrow(IMM12_CLOSE_RCA_REQUIRED)`; RCA `status!=Completed` → `nthrow(IMM12_CLOSE_RCA_INCOMPLETE)` |
| gate-2 hook | `validate_incident_close_gate:1750` | `if severity not in _HIGH_SEVERITY and not doc.get("requires_rca"): return` (bỏ escape đọc `rca_required`) | `nthrow_in_hook(...)` (in-handler HTTP-200 Error envelope) |

**Mirror sync (derive-live):** đầu `validate_incident_close_gate` (chạy trên mọi insert+update) recompute `doc.rca_required = 1 if _needs_rca(doc.severity) else 0` ⇒ escalation + `doc.save()` → `rca_required==1` LIVE; downgrade → `0`. Field GIỮ (KPI/list) nhưng gate **KHÔNG đọc**. Acceptance đầy đủ: `02 §IV.2c` (INV-RCA-LIVE-1..8). **KHÔNG thêm `@frappe.whitelist` / DocType / field ⇒ `oas_baseline` bất biến; `imm_12_incident_workflow.json` bất biến.**

#### 3.0.4 `_build_incident_actions` — server-driven CTA `available_actions[]` (CR-39) 🟡 SPEC (BE Bước-4)

**Vấn đề:** màn Chi tiết sự cố gate 6 CTA bằng **predicate-mirror ở FE** (hardcode `status===`, `can(cap)`, tự suy BR-12-02) ⇒ advertise≠enforce → nút hiện nhưng bấm ra **403/422 sau khi bấm** + drift khi BE đổi cap/transition. Fix: BE trả 1 mảng CTA có sẵn `enabled`+`reason` (parity `_build_available_actions` imm00 + `allowed_transitions`/`can_manage_rca` RCA). Đầy đủ API-shape + invariant: `05 §18`; quyết định `source_states`: **ADR-IMM12-09**.

**SSoT tuple `_INCIDENT_ACTION_SPECS`** (tuple bất biến, thứ tự = thứ tự render FE — LUÔN đủ 6):

| key | label VI | `target_status` | `source_states` | cap (predicate SSoT) |
|---|---|---|---|---|
| `acknowledge` | Tiếp nhận | `Acknowledged` | `{Open}` | `incident.acknowledge` (`_CAP_INVESTIGATE`) |
| `start_work` | Bắt đầu xử lý | `In Progress` | `{Acknowledged}` | `incident.acknowledge` |
| `resolve` | Đánh dấu đã giải quyết | `Resolved` | `{In Progress}` | `incident.acknowledge` |
| `close` | Đóng sự cố | `Closed` | `{Resolved}` | `incident.close` (`_CAP_CLOSE`) |
| `reopen` | Mở lại điều tra | `In Progress` | `{Resolved}` | `incident.close` |
| `cancel` | Hủy sự cố | `Cancelled` | `{Open, Acknowledged, In Progress}` | `incident.acknowledge` |

> **⚠️ `start_work` & `reopen` cùng đích `In Progress`** ⇒ `target ∈ _VALID_TRANSITIONS[status]` KHÔNG đủ (bật sai chéo state). `source_states` khử va chạm — xem **ADR-IMM12-09** (05).

**Thuật toán `_build_incident_actions(doc) -> list[dict]`** (READ-ONLY, mirror `_build_available_actions` imm00.py:762):
```python
def _build_incident_actions(doc):
    actions = []
    for spec in _INCIDENT_ACTION_SPECS:            # 6 spec, thứ tự cố định
        transition_ok = (spec.target in _VALID_TRANSITIONS.get(doc.status, [])
                         and doc.status in spec.source_states)     # ADR-IMM12-09
        has_cap = rbac.can(spec.cap)               # cap-hằng ENDPOINT (KHÔNG re-literal)
        business_ok = _close_rca_satisfied(doc) if spec.key == "close" else True
        enabled = bool(transition_ok and has_cap and business_ok)
        if enabled:
            reason = ""
        else:                                       # INV-CTA-2: transition > cap > business > unknown
            reason = (
                (spec.blocked_reason if not transition_ok else "")
                or ("" if has_cap else _CAP_REASON_VI)
                or (_CLOSE_RCA_REASON_VI if (spec.key == "close" and not business_ok) else "")
                or _UNKNOWN_REASON_VI                # bịt nhánh status '' / mã lạ + đủ transition+cap
            )
        actions.append({"key": spec.key, "label": spec.label, "route": "",
                        "enabled": enabled, "reason": reason})
    return actions
```
- **`has_cap`**: DÙNG ĐÚNG cap-string endpoint ghi (`_CAP_INVESTIGATE='incident.acknowledge'`, `_CAP_CLOSE='incident.close'`, `api/imm12.py:52-53`). **TUYỆT ĐỐI KHÔNG hardcode cap khác** (drift = gate nói dối). **Khuyến nghị**: hoist 2 hằng cap về `services/imm12.py` (hoặc shared constants) rồi `api/imm12.py` import — advertise (`_build_incident_actions`) & enforce (endpoint gate) đọc **1 SSoT**.
- **`business_gate` = `_close_rca_satisfied(doc)`** (SHARED predicate — extract từ logic hiện có của `close_incident:711`):
  ```python
  def _close_rca_satisfied(doc) -> bool:      # BR-12-02 boolean SSoT, READ-ONLY
      if not _needs_rca(doc.severity):
          return True
      if not doc.rca_record:
          return False
      return frappe.db.get_value(_DT_RCA, doc.rca_record, "status") == _RCA_COMPLETED
  ```
  `close_incident()` refactor gọi `if not _close_rca_satisfied(doc): <branch chọn IMM12_CLOSE_RCA_REQUIRED vs INCOMPLETE>` ⇒ **advertise==enforce** (INV-CTA-4). Giữ nguyên 2 message cụ thể của `close_incident` (predicate chỉ trả bool).
- **`get_incident_detail`**: thêm `data["available_actions"] = _build_incident_actions(doc)` (cạnh `allowed_transitions`). **KHÔNG** ghi audit/lifecycle/modify (INV-CTA-5 — `_build_incident_actions` chỉ `rbac.can` + đọc field + 1 `db.get_value` RCA status).
- **Hằng VI** (BE no-EN-leak): `_CAP_REASON_VI="Bạn không có quyền thực hiện thao tác này"`; `_CLOSE_RCA_REASON_VI="Cần hoàn tất phân tích nguyên nhân gốc (RCA) trước khi đóng sự cố"`; `_UNKNOWN_REASON_VI="Không thể thực hiện thao tác này ở trạng thái hiện tại"`; `blocked_reason` per-CTA (precondition VI, xem `05 §18` mẫu JSON).
- **KHÔNG** thêm `@frappe.whitelist`/DocType/field ⇒ `oas_baseline` bất biến; `imm_12_incident_workflow.json` bất biến. Mobile OAS mirror (`IncidentDetail += available_actions`) đã curate ở BA slice (`05 §18` note ✅).
- **Test (Bước-4, `tests/test_imm12.py`):** INV-CTA-1 (mọi status kể cả `''`/mã lạ: disabled⟹reason≠""; enabled⟹reason==""); INV-CTA-3 (đủ 6, thứ tự); INV-CTA-4 (advertise==enforce: `close.enabled` ⟺ `close_incident` không raise BR-12-02; `start_work.enabled==False` ở Resolved & `reopen.enabled==False` ở Acknowledged — chốt ADR-IMM12-09); INV-CTA-5 (count-before==count-after IMM Audit Trail + Asset Lifecycle Event).

#### 3.0.5 `get_incident_detail` — enrich 3 field rẻ (`reporter_name`/`assigned_to_name`/`asset_lifecycle_status`) (CR-40) 🟡 SPEC (BE Bước-4)

**Vấn đề:** màn Chi tiết sự cố (a) rò `reported_by`/`assigned_to` = **email thô** thay họ tên (U7) — vì `get_incident_detail` (`services/imm12.py:1414-1446`) là code-path RIÊNG KHÔNG gọi `_enrich_asset_names` (helper mà `list_incidents` DÙNG để có `reporter_name`/`assigned_to_name`, `imm12.py:444-461`); (b) KTV rút máy khỏi vận hành KHÔNG thấy trạng thái máy — acknowledge High/Critical đẩy asset `Out of Service` (BR-12-04) nhưng detail không phơi `AC Asset.lifecycle_status` (U1). Fix: bồi 3 field **REUSE** predicate cũ + 1 field lifecycle LIVE. Đầy đủ API-shape + invariant + ADR: `05 §19` + **ADR-IMM12-12**.

**Delta code (READ-ONLY, additive — 0 DocType/field/whitelist/migrate):**
```python
# services/imm12.py::get_incident_detail — thay block imm12.py:1416-1417
if doc.asset:
    data["asset_name"], data["asset_lifecycle_status"] = frappe.db.get_value(
        _DT_ASSET, doc.asset, ["asset_name", "lifecycle_status"])   # 1 query, song song asset_name (INV-ENR-3)
# … (giữ allowed_transitions / _enrich_sla_breach / rca / available_actions / scene_photos như cũ)
_enrich_asset_names([data])          # REUSE helper: bồi reporter_name/assigned_to_name (imm12.py:452-460);
                                     # set lại asset_name cùng giá trị — vô hại. KHÔNG re-implement predicate.
```
- **`reporter_name`/`assigned_to_name`**: DÙNG NGUYÊN `_enrich_asset_names([data])` — 1 SSoT với `list_incidents` (cùng `User.full_name`, cùng fallback raw-id khi full_name rỗng). Parity list↔detail (INV-ENR-1). **TUYỆT ĐỐI KHÔNG** viết lại vòng lặp enrich cục bộ (drift = list đổi map → detail lệch).
- **`asset_lifecycle_status`**: gộp vào `db.get_value` `asset_name` sẵn có (`:1417`) → **KHÔNG N+1**; LIVE từ `AC Asset.lifecycle_status` (server SSoT — nguyên tắc `overdue_server_flag_ssot`, KHÔNG denormalize lên Incident doc). `doc.asset` rỗng ⟹ nhánh `if doc.asset` bỏ qua ⟹ key absent/`''` — endpoint KHÔNG crash (INV-ENR-4).
- **Scope đóng kín:** `asset_lifecycle_status` GIỮ trong `get_incident_detail` — **KHÔNG** đẩy vào `_enrich_asset_names` chung (sẽ lan sang `list_incidents` = nở scope). CR-56 (`get_rca` thiếu `assigned_to_name`) + CR-50 (`repair_checklist` seed) = **OUT-OF-SCOPE** vòng này.
- **KHÔNG** ghi audit/lifecycle/modify doc (READ-ONLY) ⇒ `oas_baseline` bất biến; Mobile OAS mirror (`IncidentDetail += 3 field`) đã curate ở BA slice (`05 §19` note ✅, `test_mobile_oas` +5 TC GREEN).
- **Test (Bước-4, `tests/test_imm12.py`):** INV-ENR-1 (parity `reporter_name` list==detail cùng `name`); INV-ENR-2 (no-raw-email: `full_name` tồn tại ⟹ `reporter_name`==full_name ≠ email); INV-ENR-3 (`asset_lifecycle_status`==`AC Asset.lifecycle_status`; sau acknowledge Critical ⟹ `Out of Service`); INV-ENR-4 (no-asset ⟹ không raise); INV-ENR-5 (3 field ∉ required, additive). **DoD** (chạm `services/imm12.py` production dưới gunicorn `--preload`) = `bench --site miyano run-tests` module-isolated `test_imm12` (+ `test_mobile_oas`) XANH THẬT — **KHÔNG curl live** (worker preload stale tới khi USER reload).

### 3.1 SoT "incident đang mở" — Single Source of Truth (BR-12-11) ✅ LIVE

Định nghĩa DUY NHẤT cho khái niệm "incident đang mở" — mọi consumer (dashboard KPI card / donut / persona, SLA breach engine, list drill-down) PHẢI dùng chung helper này → **invariant: card count == số dòng list sau drill** (không drift).

```python
# services/imm12.py:59-74 (đã có từ round-18 — KHÔNG sửa)
INCIDENT_OPEN_STATES = (Open, Acknowledged, In Progress, RCA Required)   # POSITIVE list

def open_incident_filter(extra: dict | None = None) -> dict:
    """Trả {"status": ["in", INCIDENT_OPEN_STATES], **extra}."""
```

| State | Trong open-set? | Lý do |
|---|---|---|
| Open | ✅ | mới tạo, chưa xử lý |
| Acknowledged | ✅ | đã tiếp nhận, còn đang xử lý — **KHÔNG được bỏ sót** |
| In Progress | ✅ | đang xử lý |
| RCA Required | ✅ | chờ RCA Completed trước Close — **KHÔNG được bỏ sót** |
| Resolved | ❌ | đã rời open-set (terminal-ish) |
| Closed | ❌ | terminal |
| Cancelled | ❌ | terminal (false alarm) — dùng POSITIVE list để KHỎI vô tình đếm Cancelled là mở |

**BR-12-11 (delta vòng 21) — gắn 2 consumer còn sót vào SoT:**

1. **`get_incident_stats()` THÊM key `open_total`** = `_count(open_incident_filter())` = số incident ở MỌI state mở của SoT — KHÔNG chỉ `status == "Open"`. Trên live DB hiện tại (3 Open + 1 Acknowledged = 4 mở, 1 Closed) ⇒ `open_total == 4`, KHÔNG còn `== 3`.
2. **`get_dashboard().active_incidents`** đổi filter từ tuple cục bộ `[_STATUS_OPEN, _STATUS_INVESTIGATING]` → `open_incident_filter()` ⇒ bao trùm Acknowledged + RCA Required; số dòng (trước cắt `limit_page_length=10`) khớp `open_total`.
3. **Grep guard:** trong `get_incident_stats()` + `get_dashboard()` KHÔNG còn literal/tuple status cục bộ cho ngữ nghĩa open-set (vd inline `[_STATUS_OPEN, _STATUS_INVESTIGATING]`). Định nghĩa open-set CHỈ tồn tại ở `INCIDENT_OPEN_STATES` / `open_incident_filter()`.

**Backward-compat (BẮT BUỘC):** giữ nguyên key `open` (= count `status==Open`) và `investigating` (= count `status==In Progress`) trong `get_incident_stats()` — consumer khác đọc breakdown từng-state vẫn chạy. Vòng 21 chỉ **THÊM** `open_total`, KHÔNG xoá/đổi nghĩa key cũ.

**BR-12-11b (delta vòng 29) — KPI strip severity = open-set (gắn tile "nghiêm trọng/mức cao" vào SoT):**

Vấn đề thiết kế gốc (Self-Correction): KPI strip `IncidentListView.vue` tile *"Sự cố nghiêm trọng"* / *"Sự cố mức cao"* hiện bind `stats.critical` / `stats.high` — đây là **count GLOBAL mọi-status** (gồm Closed/Cancelled/Resolved). Khi user drill `?open=1` (hoặc `?severity=High`), bảng chỉ hiển thị dòng open-set ⇒ **mâu thuẫn thị giác strip-vs-table**: strip báo số global (vd 4 High kể cả đã đóng) trong khi bảng chỉ 2 dòng High đang mở. Strip severity phải đếm theo **cùng SoT** `open_incident_filter()` như mọi consumer khác.

1. **`get_incident_stats()` THÊM 2 key `critical_open` + `high_open`** = `_count(open_incident_filter({"severity": …}))` — DÙNG LẠI SoT `open_incident_filter()` (round-18), **KHÔNG** inline negative-list / tuple status mới. Closed/Cancelled/Resolved **bị loại** vì không nằm trong `INCIDENT_OPEN_STATES`.

```python
# services/imm12.py::get_incident_stats() — THÊM (KHÔNG xoá critical/high global)
"critical_open": _count(open_incident_filter({"severity": _SEV_CRITICAL})),
"high_open":     _count(open_incident_filter({"severity": _SEV_HIGH})),
```

> `open_incident_filter(extra)` đã hỗ trợ merge `extra` (xem `:64`): `open_incident_filter({"severity": _SEV_CRITICAL})` → `{"status": ["in", INCIDENT_OPEN_STATES], "severity": "Critical"}`. KHÔNG cần helper mới.

2. **Backward-compat (BẮT BUỘC):** GIỮ NGUYÊN `critical` (= count `severity==Critical`, mọi-status) và `high` (global) cho donut/severity_breakdown + consumer cũ. Vòng 29 chỉ **THÊM** `critical_open`/`high_open`.

3. **Grep guard:** open-set severity count CHỈ sinh qua `open_incident_filter()` (1 SoT). KHÔNG literal/tuple status open-set cục bộ trong `get_incident_stats()` cho 2 key mới.

**Invariant đo được (data live: 5 incident = 3 Open + 1 Acknowledged + 1 Closed + 0 Cancelled; trong open-set: 1 Critical + 2 High):**

| Key | Giá trị | Predicate |
|---|---|---|
| `critical_open` | `== 1` | `open_incident_filter() ∧ severity==Critical` (Closed/Cancelled loại) |
| `high_open` | `== 2` | `open_incident_filter() ∧ severity==High` |
| `critical` (global, giữ) | == tổng-mọi-status | `severity==Critical` |
| `high` (global, giữ) | == tổng-mọi-status | `severity==High` |
| **bất biến** | `critical_open <= critical` ∧ `high_open <= high` | luôn đúng (open-set ⊆ all-status) |

**Hồi quy (KHÔNG đổi):** `open_total` (round-21), `closed`, `severity_breakdown` donut (ngoài scope), invariant card==drill (round-18/21). ⚠️ `chronic` ĐỔI nghĩa ở BR-12-12 vòng này (xem dưới) — không còn "đếm cờ".

---

**BR-12-12 (delta vòng 3/50) — KPI "Lặp lại (Chronic)" = nhóm LIVE rolling-window, kill tile-vs-panel divergence:**

Vấn đề thiết kế gốc (Self-Correction): `get_incident_stats()` đặt `"chronic": _count({"chronic_failure_flag": 1})` (`services/imm12.py:670`) — đếm **cờ bền vững** `chronic_failure_flag`. Cờ này do scheduler `_process_chronic_group()` (`:858-873`) set `=1` trên TỪNG incident-row thuộc cụm chronic, và **KHÔNG BAO GIỜ reset** khi cụm hết hạn 90 ngày (cờ là dấu lịch sử BR-12-03). Hậu quả:

- **Tile monotone-stale**: tile `chronic` chỉ tăng, không giảm — khi 3+ incident cũ aged-out > 90 ngày, không còn nhóm `(asset, fault_code)` nào ≥ 3 trong 90d, nhưng tile VẪN > 0 vì cờ còn nguyên trên các incident cũ.
- **Lệch đơn vị**: tile đếm **số incident-rows-có-cờ** (vd 6 row) trong khi panel ngay dưới (`get_dashboard().chronic_failures` = `get_chronic_failures()`) đếm **số nhóm `(asset, fault_code)` live** (vd 1 nhóm). 2 con số mâu thuẫn trên CÙNG 1 màn hình (`IMM12DashboardView.vue:106` tile vs `:221-234` panel).
- **Định nghĩa doc lệch**: 02 §I.5:94 (cũ "Assets có cờ = True") vs §II.7 BR-12-03:189 / get_chronic_failures (live rolling). **BA CHỐT: SoT = LIVE** (định nghĩa rolling-window là cái user/QA Officer hành động theo); cờ giữ riêng cho badge per-row + RCA grouping.

**Quyết định Core Doc:**

1. **Thêm 1 SoT count helper dùng chung** `chronic_failure_count() -> int` — phái sinh từ CHÍNH `get_chronic_failures()` (anti-drift, KHÔNG re-implement SQL):

```python
# services/imm12.py — SoT DUY NHẤT cho KPI chronic (BR-12-12)
def chronic_failure_count() -> int:
    """Số nhóm (asset, fault_code) đang chronic theo cửa sổ trượt 90 ngày live.
    CÙNG predicate get_chronic_failures() (GROUP BY HAVING >= 3) → 1 SoT, no drift."""
    return len(get_chronic_failures())
```

2. **`get_incident_stats()` đổi `chronic` sang SoT helper** — XOÁ `_count({"chronic_failure_flag": 1})`:

```python
# services/imm12.py::get_incident_stats() — THAY (KHÔNG còn đếm cờ)
"chronic": chronic_failure_count(),   # BR-12-12 LIVE — was _count({"chronic_failure_flag": 1})
```

3. **Grep guard**: trong `get_incident_stats()` KHÔNG còn `chronic_failure_flag` cho ngữ nghĩa KPI tile. Đếm chronic CHỈ sinh qua `chronic_failure_count()`/`get_chronic_failures()` (1 SoT). (Cờ `chronic_failure_flag` còn xuất hiện ở `_process_chronic_group` setter + list field cho badge per-row — đó là lifecycle riêng, KHÔNG đụng.)

4. **Invariant tile == panel (BR-12-12, đo trên 1 payload `get_dashboard()`):** `stats.chronic == len(chronic_failures)`. ⚠️ **Lưu ý cắt top-5**: `get_dashboard().chronic_failures = get_chronic_failures()[:5]` (hiển thị top-5 panel). Để invariant ĐÚNG cả khi > 5 nhóm, Core Doc CHỐT 1 trong 2 (BE chọn, ghi rõ trong test):
   - **(a) khuyến nghị:** invariant test giữ data ≤ 5 nhóm (thực tế live ~1 nhóm) ⇒ `[:5]` không cắt ⇒ `stats.chronic == len(dashboard["chronic_failures"])` đúng tự nhiên. Test assert trực tiếp trên payload.
   - **(b) nếu BE muốn invariant bền > 5 nhóm:** so `stats.chronic` với `len(get_chronic_failures())` (FULL, không cắt) trong test — vì cả `stats.chronic` lẫn panel-source cùng phái sinh từ `get_chronic_failures()`, `[:5]` chỉ là view-limit hiển thị, KHÔNG phải nguồn đếm. KHÔNG bỏ `[:5]` ở payload (giữ UX top-5 panel).

   → BE document lựa chọn trong docstring test `TestChronicSoT`.

5. **RED-prove lifecycle (BẮT BUỘC, ≥1 test):** dựng 3+ incident cùng `(asset, fault_code)` với `reported_at` aged-out > 90 ngày (cờ `chronic_failure_flag=1` set trên chúng để mô phỏng cụm cũ đã từng chronic), KHÔNG có nhóm nào ≥ 3 trong 90d hiện tại ⇒ assert `get_incident_stats()["chronic"] == 0`. Revert SoT về `_count({"chronic_failure_flag": 1})` ⇒ test FAIL (tile = 3 ≠ 0, chứng minh test bắt được stale). Restore ⇒ GREEN.

6. **Badge per-row GIỮ NGUYÊN (KHÔNG regression):** `chronic_failure_flag` tiếp tục phục vụ badge *"Lặp lại"* per-row (`IncidentListView.vue:271/:317`) — đánh dấu incident *từng thuộc* cụm chronic (lifecycle BR-12-03, audit/RCA grouping). KHÔNG xoá field, KHÔNG reset cờ, KHÔNG đổi `_process_chronic_group`. Test no-regression: badge vẫn render cho incident có cờ kể cả khi tile chronic = 0.

**Invariant đo được (BR-12-12):**

| Đối tượng | Giá trị | Nguồn |
|---|---|---|
| `stats.chronic` | == số nhóm `(asset, fault_code)` live (≥3/90d) | `chronic_failure_count()` = `len(get_chronic_failures())` |
| `len(dashboard.chronic_failures)` | == `stats.chronic` (data ≤5 nhóm) hoặc == với FULL list (data >5) | `get_chronic_failures()[:5]` / FULL |
| tile sau aged-out >90d (cờ còn =1) | `== 0` (RED-prove) | nhóm live = 0 |
| badge per-row "Lặp lại" | render nếu `ir.chronic_failure_flag==1` | cờ bền vững — KHÔNG đổi |

**Hồi quy (KHÔNG đổi):** `open_total`, `critical_open`/`high_open`, `closed`, donut. Endpoint `api/imm12.py::get_incident_stats()` đã delegate service-layer (round-29) ⇒ `chronic` mới tự lộ qua endpoint, **KHÔNG đụng `api/imm12.py`**.

---

### 3.2 SoT SLA-breach LIVE predicate (BR-12-13) — kill undercount cửa-sổ-trễ-scheduler

Vấn đề thiết kế gốc (Self-Correction): `get_incident_stats()` đặt `"sla_response_breached": _count({"response_breached": 1})` + `"sla_resolution_breached": _count({"resolution_breached": 1})` (`services/imm12.py:677-678`) — đếm **cờ bền vững** `response_breached`/`resolution_breached`. 2 cờ này CHỈ do scheduler `check_incident_sla_breach()` (hourly, `:774`) hoặc write-path `acknowledge_incident`/`resolve_incident` (BR-12-08) stamp `=1`. Hậu quả **undercount cửa-sổ-trễ-scheduler**:

- Incident OPEN vừa quá `resolution_due_at` 1–59 phút, scheduler chưa tới lượt quét hourly ⇒ cờ còn `0` ⇒ tile `sla_resolution_breached` đếm thiếu incident này (vẫn đang breach THẬT). QA Officer nhìn tile thấy 0 trong khi DB có incident quá hạn chưa đóng.
- Cùng lỗi với badge per-row: `list_incidents`/`active_incidents` trả cờ thô `response_breached`/`resolution_breached` ⇒ FE badge chỉ hiện sau khi scheduler stamp, KHÔNG hiện ngay khi quá hạn.
- **Định nghĩa BA CHỐT: SoT = LIVE** — "đang vi phạm SLA" là trạng thái user/QA hành động theo NGAY (NĐ98 Điều 67 cửa sổ luật định), KHÔNG đợi scheduler. Cờ giữ riêng cho escalation idempotent-key (BR-12-09) + audit lịch sử (BR-12-08).

**Quyết định Core Doc:**

1. **Predicate SoT `sla_breach_filter(kind)`** — định nghĩa DUY NHẤT nhánh **live-overdue** (dùng lại `open_incident_filter()` → terminal Cancelled/Closed/Resolved KHÔNG vào nhánh này):

```python
# services/imm12.py — SoT predicate cho nhánh live-overdue (BR-12-13)
def sla_breach_filter(kind: str) -> dict:
    """Filter dict cho nhánh LIVE-OVERDUE của breach (kind ∈ {"response","resolution"}).

    `open_incident_filter()` ∧ `<kind>_due_at < now()` (+ kind==response: acknowledged_at unset).
    KHÔNG gồm nhánh cờ=1 (đếm tách trong sla_breach_count để né OR trong frappe.db.count).
    Terminal Cancelled/Closed/Resolved bị loại tự nhiên (không thuộc INCIDENT_OPEN_STATES) → INV-SLA-6.
    """
    now = now_datetime()
    if kind == "response":
        return open_incident_filter({
            "response_due_at": ["<", now],
            "acknowledged_at": ["is", "not set"],
        })
    return open_incident_filter({
        "resolution_due_at": ["<", now],
    })
```

2. **SoT count helper `sla_breach_count(kind)`** — phái sinh từ `sla_breach_filter`, cộng 2 nhánh mutually-exclusive (cờ=1 vs cờ=0∧live) → KHÔNG double-count:

```python
# services/imm12.py — SoT count cho KPI (BR-12-13). = (cờ=1) OR (đang-mở ∧ quá-hạn-live)
def sla_breach_count(kind: str) -> int:
    flag = "response_breached" if kind == "response" else "resolution_breached"
    flagged = frappe.db.count(_DT_INCIDENT, {flag: 1})
    live_filter = dict(sla_breach_filter(kind))
    live_filter[flag] = 0            # nhánh live CHỈ đếm cờ chưa stamp → exclusive với flagged
    live_unflagged = frappe.db.count(_DT_INCIDENT, live_filter)
    return flagged + live_unflagged
```

> **Vì sao tách 2 `count` thay vì 1 OR**: `frappe.db.count` không hỗ trợ OR ở top-level. 2 nhánh `(cờ=1)` và `(cờ=0 ∧ open ∧ overdue)` **không giao nhau** (phân biệt theo giá trị cờ) ⇒ tổng = đúng predicate `(cờ=1) OR (đang-mở ∧ quá-hạn)`. Đây là lý do `sla_breach_filter` KHÔNG nhúng nhánh cờ — giữ filter "live-overdue" thuần để `sla_breach_count` ghép `flag=0`, đồng thời per-row enrich tái dùng cùng predicate.

3. **`get_incident_stats()` đổi 2 KPI sang SoT helper** — XOÁ `_count({"response_breached":1})`/`_count({"resolution_breached":1})`:

```python
# services/imm12.py::get_incident_stats() — THAY (KHÔNG còn đếm cờ đơn lẻ)
"sla_response_breached":   sla_breach_count("response"),     # BR-12-13 LIVE
"sla_resolution_breached": sla_breach_count("resolution"),
```

4. **Per-row enrich LIVE** — `list_incidents()` + `get_dashboard().active_incidents` thêm `is_response_breached`/`is_resolution_breached` (0|1) derive từ CÙNG predicate trên từng row đã fetch (in-Python, KHÔNG query thêm per-row — đã có `response_due_at`/`resolution_due_at`/`acknowledged_at`/`status`/cờ trong field list). Helper per-row:

```python
# services/imm12.py — derive live breach 1 row (CÙNG predicate sla_breach_filter, in-Python)
def _row_is_breached(row: dict, kind: str, now) -> int:
    flag = row.get("response_breached" if kind == "response" else "resolution_breached")
    if flag:                                   # nhánh cờ=1 (lịch sử / đã stamp)
        return 1
    if row.get("status") not in INCIDENT_OPEN_STATES:   # terminal → KHÔNG live-overdue (INV-SLA-6)
        return 0
    due = row.get("response_due_at" if kind == "response" else "resolution_due_at")
    if not due or get_datetime(due) >= now:
        return 0
    if kind == "response" and row.get("acknowledged_at"):   # đã tiếp nhận → hết live response-breach
        return 0
    return 1
```

   - `list_incidents()` field list THÊM `response_due_at`, `resolution_due_at` (đã có `acknowledged_at`, cờ, status) → sau khi fetch rows, gán `row["is_response_breached"] = _row_is_breached(row, "response", now)` + `is_resolution_breached`.
   - `get_dashboard().active_incidents` field list THÊM `response_due_at`, `resolution_due_at`, `acknowledged_at` (hiện chỉ có cờ) → enrich tương tự.
   - Cờ thô `response_breached`/`resolution_breached` GIỮ trong payload (backward-compat) nhưng FE chuyển sang đọc `is_*_breached` (xem 06).

5. **Grep guard (anti-drift, 1 SoT):** trong `get_incident_stats()` KHÔNG còn `_count({"response_breached":1})` / `_count({"resolution_breached":1})` đơn lẻ cho 2 KPI. Đếm SLA-breach CHỈ sinh qua `sla_breach_count()` → `sla_breach_filter()`. Per-row live CHỈ sinh qua `_row_is_breached()` (cùng predicate). (Cờ thô còn ở write-path `acknowledge_incident`/`resolve_incident`/`check_incident_sla_breach` setter + escalation idempotent-key — lifecycle riêng BR-12-08/09, KHÔNG đụng.)

6. **Idempotent (INV-SLA-4, no double-path drift):** sau `check_incident_sla_breach()` stamp cờ, incident vừa-đếm-vì-live nay rơi vào nhánh `(cờ=1)` ⇒ `sla_breach_count` cho cùng con số (cờ=1 đếm 1, live-unflagged loại nó vì `flag=0` không match). RED-prove: gọi stats → chạy scheduler → gọi lại stats ⇒ `sla_resolution_breached` BẰNG nhau.

7. **RED-prove (BẮT BUỘC):** OPEN incident `resolution_due_at = now()−2h`, `resolution_breached=0`, scheduler chưa chạy ⇒ assert `get_incident_stats()["sla_resolution_breached"] == 1`. Revert 2 KPI về `_count({"...breached":1})` ⇒ test FAIL (0 ≠ 1, chứng minh bắt được undercount). Restore ⇒ GREEN.

**Invariant đo được (BR-12-13):**

| Đối tượng | Giá trị | Nguồn |
|---|---|---|
| `stats.sla_resolution_breached` (OPEN overdue cờ=0) | `== 1` (INV-SLA-1) | `sla_breach_count("resolution")` nhánh live |
| `stats.sla_response_breached` (OPEN unack overdue cờ=0) | `== 1` (INV-SLA-2) | `sla_breach_count("response")` nhánh live |
| `stats.sla_*_breached` (Closed/Resolved cờ=1 lịch sử) | đếm qua nhánh `cờ=1` (INV-SLA-3) | `count(<flag>=1)` |
| `stats.sla_*_breached` trước == sau scheduler | bằng nhau (INV-SLA-4) | idempotent 2-nhánh exclusive |
| `row.is_*_breached` (per-row live) | == tile (INV-SLA-5) | `_row_is_breached()` cùng predicate |
| terminal đóng-đúng-hạn cờ=0 | KHÔNG live-overdue (INV-SLA-6) | `status ∉ INCIDENT_OPEN_STATES` |

**Hồi quy (KHÔNG đổi):** `open_total`, `critical_open`/`high_open`, `chronic`, `closed`, donut. Cờ `response_breached`/`resolution_breached` write-path + escalation BR-12-08/09 KHÔNG đụng. Endpoint `api/imm12.py` delegate service-layer ⇒ 2 KPI + field enrich mới tự lộ qua endpoint, **KHÔNG đụng `api/imm12.py`** (verify delegate verbatim).

---

## 4. Service Layer — `services/imm12.py` ✅ LIVE

### 4.1 Public functions (actual signatures)

| Function | Returns | Logic Owner | Notes |
|---|---|---|---|
| `report_incident(asset, incident_type, severity, description, *, fault_code, ..., source="manual", client_request_id="")` | `dict {name, status, severity}` | IMM-12 | BR-12-01 Critical→clinical_impact; BR-12-04 Critical→OOS; **BR-12-16** emit `incident_reported` lifecycle + provenance `source` (V4 D2); **BR-12-25 (CR-24)** idempotency guard `client_request_id` — trúng key (scope `+reported_by`) → early-return phiếu cũ TRƯỚC insert/log/event (§2.1a, ADR-IMM12-09) |
| `acknowledge_incident(name, notes, assigned_to)` | `dict {name, status}` | IMM-12 | Open→Acknowledged (D3); High→OOS |
| `resolve_incident(name, resolution_notes, root_cause)` | `dict {name, status, rca_created}` | IMM-12 | auto-create RCA for High/Critical |
| `close_incident(name, verification_notes)` | `dict {name, status, closed_date}` | IMM-12 | **BR-12-02 / ADR-IMM12-RCA-LIVE-SSoT (Round 4)** — gate DERIVE-LIVE: `if _needs_rca(doc.severity) or doc.requires_rca:` (bỏ `and doc.rca_required` stored → chặn đóng-giả escalation Medium→Critical). Thiếu `rca_record` → `nthrow(IMM12_CLOSE_RCA_REQUIRED)`; RCA `status!=Completed` → `nthrow(IMM12_CLOSE_RCA_INCOMPLETE)`. Restore asset Out of Service → Active. Xem §3.0.3 |
| `validate_incident_close_gate(doc, method)` | `None` (hook `Incident Report.validate`, `hooks.py:270`) | IMM-12 | **BR-12-02 / ADR-IMM12-RCA-LIVE-SSoT** — (1) recompute mirror `doc.rca_required = 1 if _needs_rca(doc.severity) else 0` (derive-live mỗi save); (2) khi target→Closed, gate CÙNG predicate gate-1: `if severity not in _HIGH_SEVERITY and not doc.get("requires_rca"): return` (bỏ escape đọc `rca_required` stored) → thiếu/incomplete RCA → `nthrow_in_hook(...)`. Chặn desk/`doc.save` parity API. Xem §3.0.3 |
| `reopen_incident(name, reason)` | `dict {name, status}` | IMM-12 | **BR-12-23 (Round 12)** — Resolved → In Progress ("Mở lại điều tra"); `_assert_transition` (map đã có 'In Progress' ∈ `_VALID_TRANSITIONS[Resolved]`); `reason` required (`IMM12_REOPEN_REASON_REQUIRED`); cap `incident.close` (parity Close — cùng role-set workflow {System Manager, Super Admin}); audit `_log(name, asset, "Mở lại điều tra — {reason}", "Resolved", "In Progress")` (IMM Audit Trail, BR-12-05). **KHÔNG** đổi asset `lifecycle_status` (Resolved chưa restore asset — chỉ Close mới restore; nếu Critical/OOS thì asset vẫn OOS, đúng) ⇒ **KHÔNG** cần Asset Lifecycle Event mới (xem ADR-IMM12-INCIDENT-CTA §Consequences) |
| `cancel_incident(name, reason)` | `dict {name, status}` | IMM-12 | reason required |
| `request_rca(name, rca_reason)` | `dict {name, status, rca_record}` | IMM-12 | **BR-12-24 / ADR-IMM12-RCA-ENTRY (Round 38)** — Resolved → RCA Required ("Yêu cầu RCA"). **Gate precondition đọc `doc.status` (domain SSoT, KHÔNG `workflow_state`)**: `status ≠ Resolved` → `nthrow(MSG.IMM12_REQUEST_RCA_BAD_STATE)` (422, MSG MỚI — KHÔNG dùng `_assert_transition`/`IMM12_BAD_STATE`=409), KHÔNG đổi status; `rca_reason` blank → `nthrow(MSG.IMM12_RCA_REASON_REQUIRED)` (422). Transition **qua `apply_workflow(inc, "Yêu cầu RCA")`** (mirror `_advance_incident_after_rca`, KHÔNG `db.set_value` trực tiếp) → flip `workflow_state`, rồi `frappe.db.set_value(status="RCA Required")` sync Select (dual-track); wrap try/except + fallback `db.set_value({workflow_state, status})` khi desync. **RCA idempotent reuse (loại-Cancelled, BR-12-27/ADR-IMM12-11)**: `if not _has_live_rca(doc): create_rca(name)` (GUARD trước — reuse CHỈ khi RCA CÒN SỐNG; rca_record trỏ RCA `Cancelled` ⇒ `_has_live_rca`=False ⇒ tạo RCA MỚI, KHÔNG tái dùng hồ sơ huỷ; RCA sống ⇒ reuse, `create_rca` raise 409 nếu đã có ⇒ KHÔNG tạo trùng). Audit `_log(name, asset, "Yêu cầu RCA — {rca_reason}", "Resolved", "RCA Required")` (IMM Audit Trail, BR-12-05) — **KHÔNG** thêm option Select `event_type`. Cap-gate `compliance.submit` ở API tier (rbac.can + `_MSG_FORBIDDEN`). ENTRY của nhánh RCA Required; EXIT = `_advance_incident_after_rca` (auto-close sau RCA Completed) |
| `create_rca(incident_name, rca_method)` | `dict {name, status, due_date}` | IMM-12 | Idempotent: 409 `IMM12_RCA_ALREADY_EXISTS` khi RCA **CÒN SỐNG** (`_has_live_rca`=True, status ∈ {Required, In Progress, Completed}). **BR-12-27 / ADR-IMM12-11 (CR-55)**: rca_record trỏ RCA `Cancelled` ⇒ `_has_live_rca`=False ⇒ TẠO RCA MỚI + `set_value(rca_record=<mới>)` re-point Incident; RCA Cancelled cũ GIỮ NGUYÊN (audit NĐ98). Guard đổi `if doc.rca_record and exists` → `if _has_live_rca(doc)` |
| `get_rca(name)` | `dict` | IMM-12 | includes `incident_severity` **+ `allowed_transitions: list[str]` = `_RCA_VALID_TRANSITIONS.get(status, [])` + `can_manage_rca: int(0/1)` = `rbac.can("corrective.write")` (BR-12-19, server-driven CTA — parity `get_work_order` imm09.py:917)** |
| `start_rca(name)` | `dict {name, status}` | IMM-12 | **BR-12-20** — `RCA Required → RCA In Progress`; status ≠ `RCA Required` → `nthrow(MSG.IMM12_RCA_START_INVALID_STATE)` (VN inline, 409). Audit `_log(...)` change_summary token **`rca_started`**. Gate cap `corrective.write` ở API tier |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | `dict {name, status, linked_capa}` | IMM-12 | **AC-CR-83 / BR-12-28** — PRE-CHECK 3 ràng buộc hồ sơ RCA **TRƯỚC MỌI PHÉP GÁN** (thứ tự: `validate_rca_assignment` → `validate_rca_completion(allow_capa_substitute=False)` → `validate_five_why_payload(rca.rca_method, five_why_steps or <bước đang có>)`) ⇒ hết `frappe.throw` trần thoát ra HTTP-417; hồ sơ bị từ chối GIỮ NGUYÊN status/root_cause/corrective_action_summary/completed_by/completed_date (INV-RCA-5). 2 nhánh có sẵn `root_cause`/`corrective_action` bồi thêm `fields` (message_code CŨ giữ nguyên — INV-RCA-6). BR-12-06: auto `create_capa()` via IMM-00. **BR-12-21** — CHỈ thành công từ `RCA In Progress`; status == `RCA Required` → `nthrow(MSG.IMM12_RCA_SUBMIT_INVALID_STATE)` (chặn nhảy-cóc bỏ `RCA In Progress` — hành vi cũ = BUG). Audit token **`rca_completed`** |
| `validate_five_why_payload(method, steps)` | `dict \| None` | IMM-12 | **AC-CR-83 / BR-12-28 — SSoT #1.** Hàm THUẦN (0 DB, 0 session). `"why" not in method.lower()` ⇒ `None`. `<5` bước ⇒ `{"message_code": MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE, "fields": {"five_why_steps": …}, "context": {"count": n}}` (dừng, KHÔNG xét từng bước). Ngược lại gom MỌI bước thiếu `why_question`/`why_answer` ⇒ 1 khoá `five_why_steps.<why_number>` cho MỖI bước khuyết. **KHÔNG nhận `status`** — cổng trạng thái ở call-site. Xem `05 §22.3` |
| `validate_rca_assignment(status, assigned_to)` | `dict \| None` | IMM-12 | **AC-CR-83 / BR-12-28 — SSoT #2.** `status ∈ {RCA In Progress, Completed} ∧ not assigned_to` ⇒ `MSG.IMM12_RCA_ASSIGNEE_REQUIRED` + `fields.assigned_to`. Bắt buộc gọi ở `submit_rca` vì `start_rca` cố tình bypass `validate` (D-RCA-4) |
| `validate_rca_completion(status, root_cause, corrective_action, linked_capa="", *, allow_capa_substitute=True)` | `dict \| None` | IMM-12 | **AC-CR-83 / BR-12-28 — SSoT #3.** Chỉ áp khi `status == Completed`. `not root_cause` ⇒ `MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED` + `fields.root_cause`; `not corrective_action ∧ (not allow_capa_substitute ∨ not linked_capa)` ⇒ `MSG.IMM12_RCA_CORRECTIVE_REQUIRED` + `fields.corrective_action` (**tên tham số GHI**, ADR-IMM12-14). Service gọi với `allow_capa_substitute=False` (D-RCA-2); hook gọi mặc định `True` |
| `_nthrow_violation(v)` / `_nthrow_violation_in_hook(v)` | `NoReturn` | IMM-12 | **AC-CR-83** — 2 adapter mỏng đưa CÙNG 1 vi phạm ra 2 kênh: service → `nthrow(code, fields=…, **ctx)` (envelope Decision-B CÓ `fields`); hook → `nthrow_in_hook(code, **ctx)` (ValidationError CÓ `message_code`, KHÔNG `fields` — giới hạn kênh hook) |
| `cancel_rca(name, reason)` | `dict {name, status}` | IMM-12 | **BR-12-22** — `{RCA Required, RCA In Progress} → Cancelled`; status ∈ `{Completed, Cancelled}` → `nthrow(MSG.IMM12_RCA_CANCEL_INVALID_STATE)` (VN inline, 409). `reason` required. Audit token **`rca_cancelled`**. Gate cap `corrective.write` ở API tier |
| `list_incidents(status, severity, asset, page, page_size)` | `dict {pagination, items}` | IMM-12 | — |
| `get_incident_detail(name)` | `dict` | IMM-12 | includes `allowed_transitions` + nested `rca` + `is_response_breached`/`is_resolution_breached` (BR-12-13 LIVE) + `scene_photos: [{file_url, file_name}]` (BR-12-18 parity mobile+web; `[]` khi chưa có; derive `_scene_photos(name)`) **+ `available_actions: [6×AvailableAction]`** (CR-39 server-driven CTA; derive `_build_incident_actions(doc)`, READ-ONLY; §3.0.4 + `05 §18`) **+ `reporter_name`/`assigned_to_name`** (CR-40 REUSE `_enrich_asset_names`, `User.full_name` fallback raw-id) **+ `asset_lifecycle_status`** (CR-40 `AC Asset.lifecycle_status` LIVE song song `asset_name`; §3.0.5 + `05 §19`) |
| `_build_incident_actions(doc)` | `list[dict]` (6× `{key,label,route,enabled,reason}`) | IMM-12 | **CR-39** — SSoT 6 CTA server-driven; `enabled = transition_allowed ∩ has_cap ∩ business_gate`; `route=""`; READ-ONLY. Xem §3.0.4 + ADR-IMM12-09 (`05`) |
| `_close_rca_satisfied(doc)` | `bool` | IMM-12 | **CR-39** — BR-12-02 boolean SSoT (`not _needs_rca` OR `rca.status=='Completed'`); DÙNG CHUNG `close_incident` (enforce) + `_build_incident_actions.close.business_gate` (advertise) ⇒ advertise==enforce. READ-ONLY |
| `attach_incident_photo(incident_name, *, file_bytes, file_name, content_type)` | `dict {file_url, file_name}` | IMM-12 | **BR-12-17** — validate content-type(jpg/png)+size(`MAX_INCIDENT_PHOTO_BYTES`)+max(`MAX_INCIDENT_PHOTOS=5`, đếm `_scene_photos`) TRƯỚC khi tạo File private (`is_private=1`, `attached_to_doctype="Incident Report"`, `attached_to_name=<incident>`); **BR-12-18** emit ĐÚNG 1 `Asset Lifecycle Event` `incident_photo_attached` (hard, KHÔNG swallow) + commit cùng File. Nhánh reject → `nthrow`/`ServiceError(VALIDATION\|FORBIDDEN)` **KHÔNG** tạo File. API tier wrap `handle()` → Decision-B HTTP-200. **BR-12-26 (CR-24 phần dư, vòng 3):** +kwarg `client_request_id=""` — dedupe 2 lớp SAU permission/TRƯỚC validation, replay trả File ĐÃ đính (§2.1b + ADR-IMM12-10) |
| `_scene_photos(incident_name)` | `list[{file_url, file_name}]` | IMM-12 | **SoT DUY NHẤT** cho scene photos — `frappe.get_all("File", filters={attached_to_doctype:"Incident Report", attached_to_name, is_private:1}, fields=[file_url,file_name])` lọc ảnh (`.jpg/.jpeg/.png`). Dùng CHUNG cho `get_incident_detail.scene_photos` LẪN max-count `attach_incident_photo` ⇒ **count==rows** (chống drift) |
| `get_incident_stats()` | `dict` | IMM-12 | counts per status + severity **+ `open_total` = count(`open_incident_filter()`) (BR-12-11 SoT card-count) + `critical_open`/`high_open` = count(`open_incident_filter()∧severity`) (BR-12-11b KPI-strip open-set) + `chronic` = `chronic_failure_count()` (BR-12-12 LIVE rolling-window nhóm, KHÔNG cờ stale) + `sla_response_breached` = `sla_breach_count("response")` + `sla_resolution_breached` = `sla_breach_count("resolution")`** (BR-12-13 LIVE predicate — KHÔNG còn `_count(response_breached=1)`/`_count(resolution_breached=1)` đơn lẻ) |
| `get_asset_incident_history(asset, limit)` | `dict {asset, items}` | IMM-12 | — |
| `chronic_failure_count()` | `int` | IMM-12 | **BR-12-12 SoT helper** — `len(get_chronic_failures())` (CÙNG predicate: GROUP BY (asset, fault_code) HAVING ≥ 3 trong 90d, `status != Cancelled`). Nguồn DUY NHẤT cho `stats.chronic`. Implement = `return len(get_chronic_failures())` (KHÔNG re-implement SQL — 1 SoT predicate) |
| `get_chronic_failures()` | `list` | IMM-12 | SQL GROUP BY (asset, fault_code), HAVING ≥ 3 |
| `sla_breach_filter(kind)` | `dict` (filter) | IMM-12 | **BR-12-13 SoT predicate** — `kind ∈ {"response","resolution"}`. Trả filter dict cho nhánh **live-overdue** (`open_incident_filter()` ∧ `<kind>_due_at < now()` ∧ — chỉ response — `acknowledged_at` is not set). KHÔNG bao gồm nhánh cờ=1 (đếm tách qua `sla_breach_count` để tránh OR trong `frappe.db.count`). Nguồn DUY NHẤT định nghĩa "live-overdue" cho cả count lẫn per-row enrich |
| `sla_breach_count(kind)` | `int` | IMM-12 | **BR-12-13 SoT count** — `count(<kind>_breached=1)` + `count(sla_breach_filter(kind) ∧ <kind>_breached=0)`. 2 nhánh mutually-exclusive (cờ=1 vs cờ=0) ⇒ cộng KHÔNG double-count. = predicate `(cờ=1) OR (đang-mở ∧ quá-hạn-live)`. Nguồn DUY NHẤT cho `stats.sla_response_breached`/`sla_resolution_breached` |
| `get_dashboard()` | `dict {stats, active_incidents, open_rcas, chronic_failures}` | IMM-12 | **`active_incidents` filter = `open_incident_filter()` (BR-12-11) — KHÔNG tuple cục bộ `[Open, In Progress]`; bao trùm Acknowledged + RCA Required; số dòng (trước cắt limit 10) == `stats.open_total`. INVARIANT (BR-12-12): `stats.chronic == len(chronic_failures)` trên cùng payload (cả hai phái sinh từ `get_chronic_failures()`) — tile == panel, KHÔNG drift. ⚠️ `chronic_failures` field giữ `[:5]` để hiển thị top-5, nhưng `stats.chronic` đếm FULL `len(get_chronic_failures())`; nếu > 5 nhóm thì invariant test so `stats.chronic` với FULL list KHÔNG bị cắt — xem §test note `04` dưới.** |
| `detect_chronic_failures()` | `dict {flagged, rca_created, groups}` | Scheduler | BR-12-03: flag + auto RCA Chronic |

**Note:** Function `submit_rca_and_create_capa` does **not** exist — actual name is `submit_rca`. Field `fault_description` does **not** exist — actual field is `description`.

### 4.2 Key implementation notes

- `report_incident` signature: `(asset, incident_type, severity, description, *, fault_code, workaround_applied, clinical_impact, patient_affected, patient_impact_description, immediate_action, linked_repair_wo, reported_by, source="manual")` — returns `dict`, NOT `str`. **V4 D2:** `source` enum `{"manual","qr-scan"}` (default manual) → provenance trong lifecycle `incident_reported` + audit `change_summary`.
- DocType name used: `"Incident Report"` (constant `_DT_INCIDENT`).
- RCA DocType name: `"IMM RCA Record"` (constant `_DT_RCA`). **NOT** `"RCA Record"`.
- CAPA DocType name: `"IMM CAPA Record"` (constant `_DT_CAPA`).
- Chronic detection: `_CHRONIC_WINDOW_DAYS=90`, `_CHRONIC_MIN_COUNT=3`, `_RCA_DUE_MAJOR=7`, `_RCA_DUE_CHRONIC=14`.
- `submit_rca` writes fields: `root_cause`, `corrective_action_summary`, `preventive_action_summary`, `rca_notes`, `completed_by`, `completed_date`, `linked_capa`.
- Auto-CAPA on `submit_rca` via `svc00.create_capa()` — sets `linked_capa` on both RCA and Incident.
- `_auto_create_capa()` is a fallback on `resolve_incident()` for High/Critical without RCA flow.
- **Audit trail 3 transition (Round 9):** ghi qua `_log(name, rca.asset, summary, from_status, to_status)` → `svc00.log_audit_event` (`IMM Audit Trail`), `summary` mang token semantic **`rca_started` / `rca_completed` / `rca_cancelled`** ở đầu chuỗi (test AC7 assert token trong `change_summary` + cặp `from_status→to_status`). Side-effect audit → wrap try/except, KHÔNG fail transition. (Không thêm value mới vào `Asset Lifecycle Event.event_type` enum — token nằm ở audit `change_summary`, giữ enum 26 giá trị canonical.)
- **fixtures/workflow.json "IMM-12 RCA Workflow" — align với capability gate (ADR-IMM12-RCA-CTA D2):** hai transition "Hủy RCA" hiện chỉ `allowed` cho `System Manager` + `AssetCore Super Admin`. Vì endpoint `cancel_rca` gate `corrective.write` (Corrective User/Manager có write=1) → thêm `Corrective User` + `Corrective Manager` vào cả 2 transition "Hủy RCA" để **native-workflow-allowed == endpoint-capability-allowed** (đóng drift "cancel qua API được nhưng desk-workflow chặn"). Sau sửa fixture: `bench --site <site> reload-doctype "Workflow"`/`migrate` + `execute assetcore.setup.backfill_workflow_admin.run` (KHÔNG data-migration). Guard invariant: `test_workflow_admin_override` + guard test map↔JSON.

---

## 5. API Layer — `api/imm12.py` ✅ LIVE

Imports from `assetcore.utils.response` (`_ok`, `_err`). Role check via `_has_role(*roles)`.

**Roles constants:**
- `_ROLES_INVESTIGATE = {"IMM Workshop Lead", "IMM Technician", "IMM QA Officer", "System Manager"}`
- `_ROLES_CLOSE = {"IMM Workshop Lead", "IMM QA Officer", "System Manager"}`

**Actual @frappe.whitelist endpoints:**

| Function | Method | Role guard |
|---|---|---|
| `report_incident(asset, incident_type, severity, description, fault_code, ..., source, client_request_id="")` | POST | **`rbac.can("corrective.create")`** (V4-GATE D1 — KHÔNG còn chỉ Guest-401); **CR-24** handler THÊM param `client_request_id` (default `""`) truyền xuống svc — bắt buộc để yaml-prop ⊆ live-handler-params (test_mobile_oas 13e handler-parity, §05) |
| `cancel_incident(name, reason)` | POST | ROLES_INVESTIGATE |
| `create_rca(incident_name, rca_method)` | POST | ROLES_INVESTIGATE |
| `get_rca(name)` | GET | authenticated |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | POST | ROLES_INVESTIGATE |
| `get_asset_incident_history(asset, limit)` | GET | authenticated |
| `get_chronic_failures()` | GET | authenticated |
| `get_dashboard()` | GET | authenticated |
| `list_incidents(status, severity, asset, open, page, page_size)` | GET | authenticated | `open=1` áp SoT `open_incident_filter()` cho drill (status đơn lẻ ưu tiên hơn open) |
| `get_incident(name)` | GET | authenticated |
| `acknowledge_incident(name, notes, assigned_to)` | POST | ROLES_INVESTIGATE |
| `resolve_incident(name, resolution_notes, root_cause)` | POST | ROLES_INVESTIGATE |
| `close_incident(name, verification_notes)` | POST | ROLES_CLOSE |
| `get_incident_stats()` | GET | authenticated | trả service-layer shape (gồm `open_total`) — xem Self-Correction dưới |
| `attach_incident_photo(incident_name)` | POST (multipart) | **reporter OR `incident.write`** (BR-12-17) | `file` từ `frappe.request.files["file"]`; Guest→dispatcher-403; not-reporter∧not-write→in-handler cap-403 (Decision-B `FORBIDDEN`); validation→`VALIDATION` `fields.file`. Xem `05 §2 #15` |

> **⚠️ SELF-CORRECTION (BR-12-11) — api-layer `get_incident_stats` divergence:** endpoint `api/imm12.py::get_incident_stats()` hiện re-implement cục bộ với alias chết `"Under Investigation"` + inline open-set tuple `["Open","Under Investigation"]` (đếm 0 trên data thật, vi phạm SoT + CLAUDE.md §15). Core Doc CHỐT: endpoint PHẢI `return handle(svc_stats)` (delegate `services/imm12.py::get_incident_stats`) ⇒ trả CÙNG shape với `get_dashboard().stats` (gồm `open_total`, `total`, severity, `sla_*`). Chi tiết: `05_API §11.6`.

### 5.1 V4-GATE — Cap-gate `report_incident` (BR-12-15) — đóng lỗ leo quyền P1 ✅ CHỐT

> **ADR:** `ADR-IMM12-REPORT-FAILURE.md` D1. **Gap (verify tại source):** route-guard FE (`router/index.ts:450`) + scan-action SSoT (`services/imm00.py:419-420`) ĐỀU gate `corrective.create`, NHƯNG API+svc `report_incident` CHỈ chặn Guest-401 → user `corrective.read`-không-`create` bypass qua curl/REST.

**CHỐT (1 nơi chịu trách nhiệm HTTP = API tier):**
```python
# api/imm12.py — đầu report_incident, sau Guest-401, TRƯỚC handle()
_CAP_REPORT = "corrective.create"   # auto-gen ("Incident Report","create") — SSoT rbac.py
if not rbac.can(_CAP_REPORT):
    return _err(_(_MSG_FORBIDDEN), 403)   # "Không có quyền thực hiện hành động này"
```
- **KHÔNG dùng `rbac.require(_CAP_REPORT)`** — `require` throw `"Khong du quyen: corrective.create"` ⇒ LEAK raw cap (vi phạm AC1). Dùng `rbac.can` + `_err(_MSG_FORBIDDEN, 403)` (VI sạch).
- **Parity 3-tier** (cùng cap `corrective.create`): tier-1 route-guard · tier-2 scan-action `report_failure.capability` · tier-3 API gate (THÊM). QA test tương đẳng 3 binding.

| Tier | Vị trí | Cap | Khi thiếu cap |
|---|---|---|---|
| 1 Route-guard | `router/index.ts:450` `IncidentCreate` | `corrective.create` | redirect /unauthorized |
| 2 Scan-action SSoT | `services/imm00.py:419-420` `report_failure` | `corrective.create` | nút "Báo hỏng" disabled + tooltip |
| 3 API tier (THÊM) | `api/imm12.py::report_incident` | `corrective.create` | **403** VI sạch (chặn curl/REST) |

---

## 6. Audit Trail

| Event | Trigger | `event_type` | Actor |
|---|---|---|---|
| IR created (Minor) | `report_incident()` | `incident_reported` | session.user |
| IR created (Critical) | `report_incident()` + asset transition | `incident_reported_critical` | session.user |
| IR Acknowledged | `acknowledge_incident()` | `incident_acknowledged` | Workshop Lead |
| IR Resolved | `resolve_incident()` | `incident_resolved` | Workshop Lead / KTV |
| IR Closed | `close_incident()` | `incident_closed` | Workshop Lead |
| RCA Completed + CAPA created | `submit_rca()` | `rca_completed` | QA Officer |
| Chronic failure detected | `detect_chronic_failures()` | `chronic_failure_detected` | Administrator (scheduler) |
| SLA breach detected | `check_incident_sla_breach()` | `Incident` (`change_summary="SLA breach (...) phát hiện bởi scheduler"`) | Administrator (scheduler) |
| SLA breach escalated | `check_incident_sla_breach()` | `Incident` (`change_summary="SLA breach escalated → <recipients>"`) | Administrator (scheduler) |

> **2 audit entry tách bạch (BR-12-05 + BR-12-09):** entry *phát hiện* (set cờ) đã có từ trước; khi escalate bắn notification thì GHI THÊM entry *escalated* — KHÔNG thay thế entry phát hiện. Nếu incident không có recipient nào → chỉ ghi entry phát hiện (không ghi entry escalated, không bắn rỗng).

Tất cả gọi `imm00.log_audit_event()` → SHA-256 hash chain (NĐ98/ISO 13485).

### 6.1 V4-GATE — Canonical lifecycle event `incident_reported` + provenance `source` (BR-12-16) ✅ CHỐT

> **ADR:** `ADR-IMM12-REPORT-FAILURE.md` D2. **Gap (verify tại source):** `_log` (`services/imm12.py:208-221`, `:212`) hiện ghi `event_type="Incident"` **generic** vào `IMM Audit Trail` — KHÔNG phải canonical `incident_reported` mà bảng §6 ở trên ĐÃ ghi (doc↔code drift), và KHÔNG ghi `Asset Lifecycle Event` (vi phạm CLAUDE.md §10).

**Self-correction tên event:** PM gọi AC là `failure_reported`, NHƯNG canonical option của `Asset Lifecycle Event.event_type` (Select) là **`incident_reported`** — `failure_reported` KHÔNG có trong Select (ghi sẽ throw / phải đổi schema). ⇒ **CHỐT dùng `incident_reported`** (đóng đúng intent "không còn chỉ generic 'Incident'" mà KHÔNG đổi schema).

**CHỐT 2 record (KHÔNG trộn 2 cơ chế):**

1. **Lifecycle event (trục §10)** — `report_incident` thành công ⇒ `create_lifecycle_event(event_type="incident_reported", actor, from_status, to_status, root_doctype=_DT_INCIDENT, root_record=doc.name, notes="Báo hỏng ({source_label}) — {severity} — {incident_type}")`.
   - `root_doctype` BẮT BUỘC kèm `root_record` (nếu không Frappe throw "Root DocType must be set first" → event bị nuốt — pattern IMM-09 `services/imm09.py:493-514`).
   - `_source_label(source)`: `"qr-scan"`→`"qr-scan"`, else→`"manual"` (SSoT 1 hàm, KHÔNG inline literal).
2. **Audit trail (hash-chain, GIỮ)** — `_log` VẪN ghi `IMM Audit Trail`; `change_summary` THÊM provenance: `f"Incident reported ({source_label}) — {severity} — {incident_type}"`. GIỮ chain hợp lệ (chỉ đổi text row MỚI, không sửa row cũ). *(Tuỳ BE)* nâng `event_type` audit-row báo hỏng "Incident"→"incident_reported" cho khớp bảng §6.

**`source` (provenance):** enum `{"manual","qr-scan"}`, **default `"manual"`** (mọi đường cũ không truyền → manual, NO regression). source ∉ enum → coi `"manual"` (KHÔNG throw — provenance không phải security gate).

**AC2 PASS khi:** (a) ≥1 `Asset Lifecycle Event` `event_type='incident_reported'` cho asset; (b) `notes` chứa "qr-scan" khi source=qr-scan / "manual" khi mặc định; (c) `verify_audit_chain(asset)['valid']==True` (lifecycle KHÔNG nằm trong chain — `utils/lifecycle.py:97-114`; audit-row mới có hash hợp lệ).

### 6.2 Canonical lifecycle event `incident_photo_attached` — bằng chứng hiện trường NĐ98 (BR-12-18) 🟡 SPEC

> **ADR:** `05 §2 ADR-IMM12-07`. **Gap:** đính ảnh vào phiếu là thao tác trên hồ sơ sự cố TTBYT → NĐ98 đòi evidence trail; KHÔNG được đính im lặng.

**Schema change (BẮT BUỘC — deploy `bench reload-doctype "Asset Lifecycle Event"`):** THÊM option `incident_photo_attached` vào Select `event_type` của `asset_lifecycle_event.json` (hiện enum kết ở `qr_regenerated` — xem `04 §6.1` self-correction: giá trị ngoài Select bị throw/nuốt). Đối xứng tên `incident_reported`.

**CHỐT (success-path `attach_incident_photo`, sau `File.insert`):**
```python
# services/imm12.py — hard-requirement, KHÔNG try/except-swallow (KHÁC incident_reported best-effort)
svc00.create_lifecycle_event(
    asset=incident.asset,
    event_type="incident_photo_attached",
    actor=frappe.session.user,                 # AC: actor = người đính
    root_doctype="Incident Report",            # BẮT BUỘC kèm root_record (thiếu → event bị nuốt)
    root_record=incident_name,
    notes=f"Đính ảnh bằng chứng: {file_name}",
)
frappe.db.commit()                             # File + event commit CÙNG transaction
```
- **Đúng 1 event/lần success** (test khẳng định `count(event_type='incident_photo_attached', root_record=<IR>) == số lần attach thành công`).
- **Atomicity:** nếu `create_lifecycle_event` throw → chưa `commit` ⇒ File.insert rollback ⇒ **không orphan, không silent** (khác `incident_reported` swallow — bằng chứng không được mất).
- **Nhánh reject** (FORBIDDEN/VALIDATION) return-sớm TRƯỚC `File.insert` ⇒ KHÔNG File, KHÔNG event.

**AC PASS khi:** (a) success → đúng 1 `File` private + đúng 1 lifecycle `incident_photo_attached` (`actor=session.user`, `root_record=<IR>`); (b) mọi nhánh reject → 0 File + 0 event; (c) `event_type` tồn tại trong Select sau reload-doctype (KHÔNG throw).

---

## 7. Scheduler ✅ LIVE

| Job | Cron | Function | Logic |
|---|---|---|---|
| Chronic failure detection | Daily | `imm12.detect_chronic_failures` | BR-12-03: ≥3 same (asset, fault_code) in 90d — returns `{flagged, rca_created, groups}` |
| CAPA overdue check | Daily | `imm00.check_capa_overdue` | ✅ LIVE — BR-00-09 |
| Incident SLA breach + escalation | Hourly | `imm12.check_incident_sla_breach` | BR-12-08 (set cờ) **+ BR-12-09 escalation** (bắn notification 0→1) **+ BR-12-10** (NĐ98 gate Critical/High) — returns `{response_breached, resolution_breached, escalated}` |

**Registration thực tế trong `assetcore/hooks.py`:**
```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm00.check_capa_overdue",
        # ...
        "assetcore.services.imm12.detect_chronic_failures",
        # ...
    ],
}
```

**Vòng 3 — Notification E3 (Incident created):** `hooks.py::doc_events["Incident Report"]["after_insert"] = "assetcore.services.notifications.notify_incident_created"` — khi Incident vừa tạo → báo người phụ trách (`assigned_to`, fallback `reported_by`) qua Notification Log + email (per-user toggle). Audit = Notification Log (core). Spec đầy đủ: `docs/imm-00/04_Backend_Design.md §III.1b-2`.

### 7.1 SLA breach escalation engine (BR-12-09 / BR-12-10) — design SAU fix

> **ROOT CAUSE (Self-Correction):** `check_incident_sla_breach` (hourly, `imm12.py`) hiện set `response_breached`/`resolution_breached=1` + `_log()` audit nhưng **KHÔNG bắn notification nào** — incident quá hạn chìm vào log câm. Reference impl đã có ở IMM-09: `notifications.run_sla_breach_scan()` (state-change 0→1 + `_dispatch`). IMM-12 phải áp cùng pattern, KHÔNG đổi hành vi IMM-09.

**Recipient resolution (SSoT, không hardcode role) — hàm mới `_incident_sla_recipients(incident: dict, severity: str) -> list[str]`:**

Recipient = union (dedupe, loại `Administrator` + empty) của:

| Nguồn | Field / SSoT | Ghi chú |
|---|---|---|
| Người phụ trách incident | `incident["assigned_to"]` | primary; nếu trống → fallback `incident["reported_by"]` (Incident Report KHÔNG có field `supervisor` — khác WO; xác minh trên `incident_report.json`) |
| Escalation L1 từ policy | `policy["escalation_l1_user"]` | `get_sla_policy(_severity_to_sla_priority(severity))` đã trả field này (imm00.py:251) — TRƯỚC fix imm12 CHƯA dùng |
| Escalation L2 từ policy | `policy["escalation_l2_user"]` | như trên |
| **NĐ98 gate (BR-12-10)** | `notify_roles.QA_OFFICER` + `notify_roles.OPS_MANAGER` → `get_users_with_role(...)` | CHỈ khi `severity ∈ {Critical, High}`; thêm KỂ CẢ khi policy không set escalation_l*_user |

- Role-name lấy từ **`services/shared/notify_roles.py`** (anti RBAC-dead-gate) — KHÔNG literal trong imm12. Cần **bổ sung block escalation incident** vào notify_roles (xem dưới).
- `_incident_sla_recipients` trả `[]` ⇒ caller set cờ + ghi entry phát hiện như cũ, **KHÔNG** bắn, KHÔNG ghi entry escalated, KHÔNG crash.

**notify_roles SSoT — bổ sung (delta cho `services/shared/notify_roles.py`):**
```python
# Người nhận escalation SLA của Incident (IMM-12) — NĐ98 gate cho Critical/High.
INCIDENT_ESCALATION_QA: list[str] = QA_OFFICER      # ["Compliance Manager"]
INCIDENT_ESCALATION_OPS: list[str] = OPS_MANAGER    # ["Maintenance Manager"]
# → thêm cả 2 vào ALL_NOTIFY_ROLES (guard test test_notify_roles_exist phủ tự động).
```
> Tái dùng role THẬT đã khai báo (`QA_OFFICER`/`OPS_MANAGER`) — không sinh role-name mới. ALL_NOTIFY_ROLES đã chứa các role này nên guard `test_tc_r21_01` vẫn xanh; alias khai báo riêng để escalation incident có điểm cấu hình độc lập (đúng pattern `CAPA_ESCALATION_MANAGER`).

**Content (tiếng Việt, phân biệt 2 loại breach) — dựng trong `check_incident_sla_breach`:**

| Loại | Trigger | Subject | Message (HTML) |
|---|---|---|---|
| response-breach | `response_breached 0→1` | `VI PHẠM SLA (tiếp nhận): Sự cố <name>` | `Sự cố <b><name></b> trên thiết bị <b><asset_name></b> CHƯA được tiếp nhận và đã quá hạn <b><N> giờ</b> (hạn tiếp nhận: <response_due_at>). Mức độ: <severity VI>. Vui lòng tiếp nhận khẩn.` |
| resolution-breach | `resolution_breached 0→1` | `VI PHẠM SLA (xử lý): Sự cố <name>` | `Sự cố <b><name></b> trên thiết bị <b><asset_name></b> CHƯA được đóng và đã quá hạn xử lý <b><N> giờ</b> (hạn xử lý: <resolution_due_at>). Mức độ: <severity VI>. Vui lòng xử lý khẩn.` |

- `<N>` = số giờ quá hạn = `round((now - due_at).total_seconds()/3600, 1)`.
- `<asset_name>` enrich qua `_enrich_asset_names` / `frappe.db.get_value("AC Asset", asset, "asset_name")`; `<severity VI>` qua map VI đã có (vd `_SEVERITY_VI`).
- Bắn qua `notifications._dispatch(recipients, subject, message, doc_like)` với `doc_like = frappe._dict(doctype=_DT_INCIDENT, name=incident["name"])` → in-app (Notification Log) + email per-user toggle + deep-link. **1 notification / 1 loại breach** (nếu cả 2 cờ cùng 0→1 trong 1 lần quét ⇒ 2 notification, mỗi loại 1).

**Idempotency (anti-spam — chính cờ làm khoá):**
- Khoá = `response_breached` / `resolution_breached` (Check trên `Incident Report`, bền vững DB).
- Trong vòng quét, mỗi loại CHỈ bắn khi cờ tương ứng đang `0` VÀ điều kiện quá hạn đúng ⇒ set `1` + bắn ĐÚNG 1 lần (set cờ và bắn trong cùng nhánh).
- Lần quét kế: cờ đã `=1` ⇒ nhánh không vào ⇒ KHÔNG bắn lại. **Sweep 2 lần liên tiếp ⇒ tổng số notification không đổi** (TC bắt buộc).
- KHÔNG dùng Notification Log dedupe cho breach (cờ DB rẻ & chắc hơn) — khớp pattern IMM-09 §III.1b-6.

**Audit (BR-12-05, KHÔNG thay thế):**
- Giữ nguyên `_log(... "SLA breach (<kinds>) phát hiện bởi scheduler" ...)` (entry phát hiện hiện có).
- Sau khi `_dispatch` thành công cho ≥1 recipient → ghi THÊM `_log(... f"SLA breach escalated → {', '.join(recipients)}" ...)`.

**Per-incident an toàn (batch resilience):**
- Vòng `for row in candidates` bọc `try/except` mỗi incident: lỗi (thiếu policy / recipient resolve fail) → `frappe.log_error` + `continue`, KHÔNG dừng batch, KHÔNG rollback các incident đã xử lý.
- `frappe.db.commit()` 1 lần cuối batch nếu có thay đổi (giữ như hiện tại).

**Return value (mở rộng, không breaking):** `{"response_breached": int, "resolution_breached": int, "escalated": int}` — `escalated` = số incident đã bắn ≥1 notification.

**Regression guard:** KHÔNG đụng `notifications.run_sla_breach_scan()` (Asset Repair / IMM-09). Tái dùng `_dispatch` + `get_users_with_role` từ `notifications.py` qua import (lazy import trong imm12 để tránh circular).

> `check_capa_overdue` và `detect_chronic_failures` đăng ký trong `scheduler_events.daily` (không phải cron riêng) — Frappe sẽ chạy 1 lần/ngày tại khung scheduler tick mặc định.

---

## 8. Integration Points

| System | Direction | Method | Notes |
|---|---|---|---|
| IMM-00 Foundation | Outbound (call) | Python import | CAPA, Audit, Lifecycle |
| IMM-09 Repair | Link | DocType Link field | `repair_wo` on Incident Report |
| IMM-13 Risk Register | Event | Webhook (Sprint 12.5) | `chronic.detected` event |
| Email (Frappe) | Outbound | `frappe.sendmail()` | Critical alert + CAPA overdue |
| IMM-15 Vigilance | Event | Webhook (Sprint 12.5) | `incident.created` event |

---

## 9. Non-Functional

| Category | Requirement | Implementation |
|---|---|---|
| Idempotency | `acknowledge/resolve/close`: repeat call → return current state | Check status before transition |
| Concurrency | No double-acknowledge | DB-level status check + ValidationError |
| Chronic detection | Idempotent | Guard: `frappe.db.exists("IMM RCA Record", {status in ["RCA Required", "RCA In Progress"]})` |
| Logging | All errors logged to Frappe error log | `frappe.log_error()` in `_handle()` |
| Performance | List query < 500ms p95 | Index on `(asset, fault_code, reported_at)` + `(severity, status)` |

---

## 4.3 AC-CR-83 — code-shape: controller `IMM RCA Record` hết `frappe.throw` trần 🟢 **ĐÃ LAND (BE Bước-4, 2026-07-27)**

> **Trạng thái thực tế trên đĩa (verify `@source` 2026-07-27):** controller **0** `frappe.throw(`; 3 validator lazy-import và gọi CHÍNH 3 predicate SSoT của `services/imm12.py`; `on_submit` dùng `nthrow_in_hook(MSG.IMM12_RCA_SUBMIT_NOT_COMPLETED, status=…)`.
> Vị trí THẬT sau khi land: `validate_five_why_payload` `services/imm12.py:974-1025` · `validate_rca_assignment` `:1028-1040` · `validate_rca_completion` `:1043-1071` · `_nthrow_violation` `:1074-1077` · `_nthrow_violation_in_hook` `:1080-1086` · PRE-CHECK trong `submit_rca` `:1236-1250` (NGAY SAU guard trạng thái `:1230`, TRƯỚC phép gán đầu tiên `:1253`).
> Guard đang xanh: `test_imm12::TestRcaSubmitEnvelope` (11 TC) + `TestRcaValidatorSsot` (3 TC) — `bench --site miyano run-tests --module assetcore.tests.imm12.test_imm12` ⇒ **Ran 198 OK**.


**File:** `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py` — **6 → 0** lời gọi `frappe.throw(`.

```python
# ── validations (SAU AC-CR-83) ────────────────────────────────────────────────
def _validate_assignment(self) -> None:
    from assetcore.services.imm12 import (          # lazy — chống circular ImportError
        _nthrow_violation_in_hook, validate_rca_assignment,
    )
    v = validate_rca_assignment(self.status, self.assigned_to)
    if v:
        _nthrow_violation_in_hook(v)

def _validate_five_why_when_method_5why(self) -> None:
    if self.status not in ("RCA In Progress", "Completed"):
        return                                       # cổng trạng thái Ở CALL-SITE
    from assetcore.services.imm12 import (
        _nthrow_violation_in_hook, validate_five_why_payload,
    )
    v = validate_five_why_payload(self.rca_method, self.get("five_why_steps"))
    if v:
        _nthrow_violation_in_hook(v)                 # KHÔNG còn vòng lặp kiểm tra riêng

def _validate_completion_requirements(self) -> None:
    from assetcore.services.imm12 import (
        _nthrow_violation_in_hook, validate_rca_completion,
    )
    v = validate_rca_completion(self.status, self.root_cause,
                                self.corrective_action_summary, self.linked_capa)
    if v:
        _nthrow_violation_in_hook(v)
```

`on_submit` (`imm_rca_record.py:29-32`) đổi sang `nthrow_in_hook(MSG.IMM12_RCA_SUBMIT_NOT_COMPLETED, status=self.status)`.

**3 điều KHÔNG được làm khi land:**

1. ❌ **Top-level import** `from assetcore.services.imm12 import …` ở đầu controller — circular `ImportError` lúc `bench start` (tiền lệ đang chạy: `imm_rca_record.py:41` đã lazy-import `on_rca_completed`).
2. ❌ Giữ lại **bản kiểm tra thứ hai** trong controller (vòng lặp/điều kiện riêng) — chính là class-of-bug "luật thứ hai" mà INV-RCA-2 cấm; guard `TestRcaValidatorSsot` sẽ đỏ.
3. ❌ Đổi predicate `"why" in method.lower()` để bắt thêm `"Both"` — đó là **AC-CR-83b**, cần ratify (D-RCA-3, `05 §22.8`); mở rộng ở vòng này làm hồ sơ đang hợp lệ hoá không hợp lệ (vi phạm AC-6).

**Thay đổi kèm theo (ngoài `services/imm12.py`):**

| File | Delta |
|---|---|
| `assetcore/utils/notify.py` | `nthrow(message_code, *, error_code=None, **fields=None**, **context)` → chuyển thẳng vào `ServiceError(..., fields=fields)`. Backward-compatible; `fields` thành **tên dành riêng** (0 entry registry đang dùng biến template `{fields}`) |
| `assetcore/utils/messages.py` | +3 hằng & entry: `IMM12_RCA_FIVE_WHY_INCOMPLETE` (422) · `IMM12_RCA_ASSIGNEE_REQUIRED` (422) · `IMM12_RCA_SUBMIT_NOT_COMPLETED` (409) — bảng đầy đủ ở `05 §22.4`. **KHÔNG** đụng 2 entry cũ (INV-RCA-6) |
| `docs/mobile/openapi/…yaml` | ✅ cite `services/imm12.py:*` **ĐÃ refresh** theo dòng THẬT sau khi predicate + pre-check land (`963→1116 create_rca` · `1070→1230` · `1075/1077→1240` · `1081→1253` · `1083→1255` · `1084→1256` · `1085→1257` · `1088→1260` · `1091→1265` · `1099→1272` · `1109→1282` · `1118→1290` · `1120→1292`; kèm 2 cite lân cận cùng module `get_incident_detail`→`1579-1663`, `get_asset_incident_history`→`1709-1763`) ⇒ `cr83_e` XANH |

> 📌 **Nguồn hợp đồng đầy đủ** (envelope · 5 `message_code` · khoá `fields` · 9 invariant · 4 divergence · 3 ADR · handoff): [`05_API_Specification.md §22`](./05_API_Specification.md).

---

## DoD — File 04 hoàn chỉnh

- [x] Architecture overview (3-tier với LIVE/Pending rõ)
- [x] DocType: Incident Report custom fields + indexes + permission query
- [x] DocType: RCA Record full field table
- [x] Workflow states + transitions table
- [x] Service layer: function signatures + `report_incident` full code
- [x] Service layer: `detect_chronic_failures` full code (SQL + idempotency)
- [x] API layer: `_handle` pattern + 5 endpoints
- [x] Audit trail table (7 events)
- [x] Scheduler table + hooks.py registration
- [x] Integration points table
- [x] Non-functional (idempotency, concurrency, logging)
- [x] ✅ `services/imm12.py` — fully implemented
- [x] ✅ `api/imm12.py` — 14 endpoints live
- [x] ✅ DocType JSONs: incident_report, imm_rca_record, imm_capa_record, imm_rca_five_why_step, imm_rca_related_incident
- [ ] Reviewed bởi BE Lead
