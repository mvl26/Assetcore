# ADR-MOBILE-051 — `listInternalAudits` (`imm16.list_internal_audits`) curate vào OAS mirror (**CR-27a · MỞ NHÁNH IMM-16 F7 "Audit nội bộ (checklist hiện trường)"** — bồi ĐÚNG 1 GET-list path trả danh sách phiên audit nội bộ (IMM Internal Audit) phục vụ Compliance/QMS, permission-aware, phân trang; LIST-ENTRY của màn F7; ⚠️ rows-key `data.data[]` **DOUBLE-DATA** (mirror PM/calib) — KHÁC `listCommissioning` `data.items[]`; 200 = oneOf `[Envelope, Error]` Decision-B; list-item MIỄN Check int-0/1)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-051 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-15 |
| Tác giả | BA (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; closed-schema oneOf, KHÔNG discriminator) · **template LIST trực-tiếp**: **ADR-MOBILE-049** (`listAllocations`) CÙNG shape paginated list-read qua response-component `oneOf [<ListEnvelope>, Error]` CÙNG rows-key `data.data[]` DOUBLE-DATA · **precedent double-data**: `PmWorkOrderListEnvelope`/`CalibrationListEnvelope`/`AllocationListEnvelope` (rows-key `data.data[]`) · **contrast**: `listCommissioning` (ADR-048) rows-key `data.items[]` (bẫy copy-nhầm) · Core Doc IMM-16 [`docs/imm-16/05_API_Specification.md §3.6`](../imm-16/05_API_Specification.md) + [`04-api-contract.md §6`](./04-api-contract.md) |

---

## 1. Bối cảnh

Màn **F7 "Audit nội bộ (checklist hiện trường)"** là LIST-ENTRY tiêu thụ `imm16.list_internal_audits` để
hiển thị danh sách các phiên audit nội bộ (IMM Internal Audit) — mã audit, loại, kỳ hạn (từ/đến), trưởng
đoàn, trạng thái, số phát hiện — phục vụ Compliance/QMS (ISO 13485 §8.2.4 internal audit; NĐ98 hồ sơ tuân
thủ). **IMM-16 CHƯA có endpoint nào curate** vào contract mirror (`assetcore-mobile.openapi.yaml`) → mobile
đang gọi raw `apiClient` (0 generated typed-client). Đây là op **MỞ NHÁNH IMM-16** (đầu tiên, 0/4 endpoint
curated). Endpoint **ĐÃ LIVE** ở web-BE. ADR này curate **contract-only** (0 `.py` runtime change / 0 reload
/ 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `list_internal_audits` @`api/imm16.py:80` — `@frappe.whitelist()` **bare** (no `allow_guest`) →
  GET nhận; guest → dispatcher-403. Chữ ký `list_internal_audits(filters: str = "{}", page: int = 1,
  page_size: int = 20)` = **3 param**. Thân: `_parse_json(filters)` trong `try/except ServiceError → _err`
  (malformed → INVALID_PARAMS TRÊN HTTP-200 @`api/imm16.py:82-85`); rồi `_handle(svc.list_internal_audits,
  f, page=int(page), page_size=int(page_size))`. **KHÔNG** param discrete override (KHÁC `listAllocations`
  7-param — audit chỉ 3-param JSON-passthrough thuần, gần `listCommissioning`).
- Service `list_internal_audits` @`services/imm16.py:360` — `InternalAuditRepo.list(filters=
  normalize_filters(filters), fields=[...8 field...], order_by="planned_start desc", page, page_size)` →
  enrich loop `lead_auditor_name` → **`return {"data": rows, "pagination": pg}`** @`services/imm16.py:375`
  → `_ok` ⇒ **rows-key `data.data[]` (DOUBLE-DATA**, mirror PM/calib/allocation, KHÁC Commissioning/Asset/
  Incident `data.items[]`).
- 8 field `InternalAuditRepo.list` @`services/imm16.py:365-366` (VERBATIM, đọc thẳng list `fields=[...]`):
  `name · audit_code · audit_type · planned_start · planned_end · lead_auditor · status · findings_count`.
- 1 enrich `lead_auditor_name` @`services/imm16.py:371-374` — **CHỈ set khi `lead_auditor` truthy**
  (`if row.get("lead_auditor"): row["lead_auditor_name"] = frappe.db.get_value("User", …, "full_name") or
  row["lead_auditor"]`) ⇒ **OPTIONAL** (∉ `required[]` — có row KHÔNG có key này khi lead_auditor rỗng).
- DocType `imm_internal_audit.json` — field-type grounding (bảng §3): `autoname = AUD-INT-.YYYY.-.#####`.

---

## 2. Quyết định

### (a) 200 = oneOf `[InternalAuditListEnvelope, Error]` — **Decision-B**

`list_internal_audits` chạy QUA `_handle(...)` VÀ handler có nhánh `_err` cho malformed `filters`
(@`api/imm16.py:82-85` → INVALID_PARAMS). Lỗi đến TRÊN HTTP-200 với body `Error` ⇒ 200 = **oneOf**
`[InternalAuditListEnvelope | Error]`. **KHÔNG raise HTTP-4xx** (mọi lỗi nghiệp-vụ = in-handler HTTP-200 +
Error envelope). Wire qua **response-component** `InternalAuditList` (KHÔNG inline) — đối xứng
`AllocationList`/`CommissioningList`/`PmWorkOrderList`. `Error.http_status` thực-tế ⊇ `{400 (malformed
filters)}`.

### (b) ⚠️ rows-key `data.data[]` (DOUBLE-DATA) — điểm phân-biệt CỐT-LÕI

Service `return {"data": rows, "pagination": pg}` @`services/imm16.py:375` → `_ok` bọc thêm 1 lớp `data` ⇒
envelope `{success:true, data:{data:[…], pagination:{…}}}` — **DOUBLE-DATA**. Mirror `PmWorkOrderListEnvelope`/
`CalibrationListEnvelope`/`AllocationListEnvelope` (di-sản service layer PM/calib/allocation). **KHÁC**
`CommissioningListPage`/`AssetListEnvelope` rows-key `data.items[]`. Bẫy copy-nhầm `mapCommissioningList`
(CR-25) → guard TC c chốt: `InternalAuditListPage` set-keys == `{data, pagination}` CHÍNH XÁC, assert
`'items' ∉ keys`.

Envelope `InternalAuditListEnvelope = {success:[true], data: $ref InternalAuditListPage}`;
`InternalAuditListPage = {data: array<InternalAuditListItem>, pagination: $ref Pagination}`. REUSE component
`Pagination` — KHÔNG tạo mới.

### (c) `InternalAuditListItem` = **EXACT 9 property**, closed, `required:[name]`

8 field `InternalAuditRepo.list` VERBATIM @`:365-366` + 1 enrich (`lead_auditor_name`).
`additionalProperties:false`. Chỉ `name` REQUIRED (PK naming-series `AUD-INT-.YYYY.-.#####`); mọi field khác
optional (Option A closed-schema). `lead_auditor_name` **OPTIONAL** (∉ `required[]`) vì service CHỈ gán khi
`lead_auditor` truthy @`:371-374` → có row THIẾU key này.

### (c.1) **⚠️ SELF-CORRECTION — `audit_type`/`status` = `type:string` (KHÔNG hard `enum:`)**

Đề mục ghi `audit_type=enum[Internal,Self-assessment]` · `status=enum[Planned,In Progress,Reporting,
Closed]`. Nhưng ground-truth DocType: cả 2 Select có **leading-blank** (`options='\nInternal\n…'` ·
`'\nPlanned\n…'`) ⇒ **empty-string `""` là value HỢP-LỆ đã-persist** (`audit_type` `reqd=None` → record cũ/
import CÓ THỂ rỗng; `status` default `'Planned'` nhưng "" vẫn ∈ options). Khai `enum:[Internal,Self-
assessment]` cứng ⇒ contract SAI-lệch: reject row `audit_type=""` → strict-codegen native (Dart/Kotlin)
deser CRASH. ⇒ **spec `type: string` + liệt-kê value ở `description`** (KHÔNG hard `enum:`), đúng **precedent
list-item** `AllocationListItem.allocation_status`/`urgency` (type:string) và `CommissioningListItem`. Giá-
trị enum là **domain-documentation** ở description, KHÔNG là JSON-Schema constraint. (Tương phản: DETAIL
schema như `SpareAllocationDetail.allocation_status` DÙNG hard enum vì single-record precise; LIST-item KHÔNG
— forward-compat + leading-blank.) Guard TC b: assert `audit_type.type=='string'` ∧ `'enum' ∉ audit_type`.

### (d) **List-item MIỄN Check int-0/1 (CR-01)**

`InternalAuditRepo.list.fields` = 8 field ∅ `Check` (0 property `type: boolean`); `findings_count` = `Int`
(count thật, `type: integer` non-null default-0) — KHÔNG phải Check 0/1. ⇒ `InternalAuditListItem` MIỄN
coercion `Number(x)===1` (CR-01 family). Guard TC b: `0 prop type:boolean`.

### (e) tag mới `compliance`

Op-level `tags: [compliance]` (module-tag IMM-16 "Compliance/QMS/Internal Audit" — parity, KHÔNG có top-
level `tags:` block trong mirror; đối xứng `[inventory]`/`[commissioning]`). Đây là op **ĐẦU TIÊN** mang tag
`compliance` (dành forward-reserve các endpoint IMM-16 kế: `getInternalAudit`/`listComplianceFindings`/
`getManagementReview`).

### (f) 3 param typed **1:1 argspec** — 1 inline + 2 `$ref`

Params path = ĐÚNG 3, đúng thứ-tự argspec: `filters` (inline `type:string` `default:'{}'` JSON-passthrough,
optional) · `$ref Page` (page int default 1) · `$ref PageSize` (page_size int default 20). REUSE `Page`/
`PageSize` component. **KHÔNG** param discrete (KHÁC `listAllocations` 4-override) — audit là JSON-passthrough
thuần (mirror `listCommissioning` 3-param, NHƯNG `filters` inline KHÔNG dedicated component vì audit KHÔNG
có allow-key enumeration cần document). `filters.default:'{}'` khai tường-minh (khớp acceptance).

### (g) No-collision / naming-guard

Namespace `InternalAudit*` (schema `InternalAuditListItem`/`InternalAuditListPage`/`InternalAuditListEnvelope`,
response-component `InternalAuditList`, opId `listInternalAudits`) DISJOINT với `Allocation*`/`Commissioning*`/
`DueCalibration*`/`Incident*` (khác endpoint, khác NGUỒN). Guard TC g: `InternalAudit*` schema-family == ĐÚNG
3; `listInternalAudits`/`listAllocations`/`listCommissioning` tồn tại song song; codify tương-phản rows-key
(`InternalAuditListPage.data` DOUBLE-DATA vs `CommissioningListPage.items`).

### (h) CONTRACT-ONLY

Backend `imm16.list_internal_audits` ĐÃ LIVE (`api/imm16.py:80` · `services/imm16.py:360`) → **0 `.py`
runtime change · 0 reload · 0 migrate**. Chỉ chạm YAML mirror + test guard + docs (ADR này). Guard TC f
khẳng-định live-signature parity: `inspect.signature(imm16.list_internal_audits)` == ĐÚNG 3 param
`{filters, page, page_size}` (yaml KHÔNG bịa/sót).

---

## 3. `InternalAuditListItem` — type ĐÚNG từng field (GROUNDED `imm_internal_audit.json`)

| # | property | nguồn | fieldtype | OpenAPI type | ghi chú |
|---|---|---|---|---|---|
| 1 | `name` | `InternalAuditRepo.list` `:365` | (autoname `AUD-INT-.YYYY.-.#####`) | `string` | PK — **required** |
| 2 | `audit_code` | list `:365` | Data (`reqd`) | `string` | mã audit |
| 3 | `audit_type` | list `:365` | Select (Internal/Self-assessment · **leading-blank**) | `string` (**KHÔNG enum** §2.c.1) | loại audit — value ∈ `{Internal, Self-assessment, ""}` documented ở description |
| 4 | `planned_start` | list `:365` | Date (`reqd`) | `string` `format:date` nullable | kỳ hạn bắt đầu — **order_by** `planned_start desc` @`:368` |
| 5 | `planned_end` | list `:366` | Date (`reqd`) | `string` `format:date` nullable | kỳ hạn kết thúc |
| 6 | `lead_auditor` | list `:366` | Link (User) | `string` nullable | trưởng đoàn (Link `User`; `.get(...) or ""` khi dangling) |
| 7 | `status` | list `:366` | Select (Planned/In Progress/Reporting/Closed · **leading-blank** · default `Planned`) | `string` (**KHÔNG enum** §2.c.1) | trạng thái phiên audit — value documented ở description |
| 8 | `findings_count` | list `:366` | Int | `integer` | số phát hiện (non-null, default 0) — KHÔNG Check int-0/1 |
| 9 | `lead_auditor_name` | enrich `:371-374` | (denorm `User.full_name`) | `string` | tên trưởng đoàn — **OPTIONAL ∉ required[]** (CHỈ set khi `lead_auditor` truthy) |

**KHÔNG có** field `Check` int-0/1 → 0 property `type: boolean` (§2.d). `findings_count` = `integer` (Int
count). `*_date`/`Link` nullable = `string` (`.get(...) or ""` coalesce khi FK dangling / date rỗng).
`audit_type`/`status` = `string` KHÔNG hard-enum (§2.c.1 leading-blank + list-item precedent).

---

## 4. Guard test (test_mobile_oas `TestMobileListInternalAuditContract` a..g)

- **a** — path `.../imm16.list_internal_audits` method GET-only + `operationId: listInternalAudits` + `tags:
  [compliance]`; ∈ `_MVP_BUSINESS_PATHS`; path/opId count == 82 unique camelCase (RED-before).
- **b** — `InternalAuditListItem` closed + `set(properties)` == EXACT 9 (8 list VERBATIM + `lead_auditor_name`
  enrich); `required:[name]` (assert `lead_auditor_name ∉ required` §2.c); `lead_auditor_name` hiện diện;
  **0 property `type: boolean`** (MIỄN CR-01); **`audit_type.type=='string'` ∧ `status.type=='string'` ∧
  `'enum' ∉ audit_type` ∧ `'enum' ∉ status`** (§2.c.1 self-correction hard-enum).
- **c** — **anti-copy-listCommissioning (double-data)**: `InternalAuditListPage` closed, set-keys ==
  `{data, pagination}` CHÍNH XÁC, assert `'items' ∉ keys`; `data.items.$ref` → `/InternalAuditListItem`;
  `pagination.$ref` → `/Pagination`.
- **d** — parameters ĐÚNG 3 (1:1 argspec): 2 `$ref [Page, PageSize]` + 1 inline `filters` (query/string/
  optional/`default:'{}'`); KHÔNG `mine`/`workflow_state`/discrete-override/`WorkOrderFilters`/
  `CommissioningFilters`.
- **e** — 200 = response-component `InternalAuditList` `oneOf [InternalAuditListEnvelope, Error]` 0-discr;
  `Envelope.data.$ref` → `/InternalAuditListPage` (rows-key `data.data[]`); success enum `[true]`/`[false]`;
  401 `Unauthorized401`, 403 `Forbidden`; status set `[200,401,403]`; KHÔNG requestBody.
- **f** — 3 schema closed; ∈ `_MVP_LIST_ENVELOPE` (len==12) trỏ `InternalAuditListEnvelope`; self-consistent
  (path ∈ `_MVP_BUSINESS_PATHS ∩ _MVP_LIST_ENVELOPE`); live-signature parity == ĐÚNG 3 param
  `{filters, page, page_size}`.
- **g** — naming-guard: `InternalAudit*` == ĐÚNG 3 schema, disjoint `Allocation*`/`Commissioning*`/
  `DueCalibration*`; rows-key tương-phản codified (`InternalAuditListPage.data` vs `CommissioningListPage.items`).

**Bulk-bump guard** (BE Bước-4 áp dụng; xác-nhận LIVE trước khi sửa — memory *concurrent-session numbering
drift*): path/opId count **+1 (81→82)** · `_MVP_LIST_ENVELOPE` **11→12** (thêm key path → `InternalAuditList
Envelope`) · c5 **70→71** · `_PARITY_BUSINESS_PATHS` **70→71** · `_EXPECTED_TEST_COUNT` **+7 (743→750)** ·
docset 3 counter (`_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` **743→750** · `_GUARD_SUITE_SUM` **886→893** ·
`_MOBILE_OAS_TOTAL` **912→919**) · delta var `list_internal_audits_delta=7` · transition-baseline doc_09 giữ
`pre_fc3_six==191`. `test_mobile_docset` (path-count/schema-count) + `test_mobile_preflight` VẪN xanh sau khi
đồng-bộ counter.

---

## 5. Hệ quả

- **+**: mobile FE codegen được typed-client cho màn F7 "Audit nội bộ" (thay raw `apiClient`); **mở nhánh
  IMM-16** (tag `compliance` sẵn cho `getInternalAudit`/`listComplianceFindings`/`getManagementReview` kế).
  Double-data trap được test khóa (chống deser rỗng rows). Self-correction hard-enum → tránh CRASH deser row
  `audit_type=""`.
- **−**: thêm 3 schema + 1 response-component + 1 path vào mirror (đã cân bằng qua bookkeeping §4). Rows-key
  `data.data[]` là di-sản service layer (KNOWN-GAP normalize về 1 key chung = Phase-E, đụng service `.py` —
  NGOÀI phạm-vi round contract-only này).
- **Đánh đổi**: (1) giữ nguyên rows-key `data.data[]` (KHÔNG hợp-nhất về `items`) = nói ĐÚNG sự-thật wire-
  shape cho codegen native (nếu khai `items` → model deser sai key → rows rỗng). (2) `audit_type`/`status` =
  `type:string` (KHÔNG enum) = mất strict-validate 2 field NHƯNG đúng ground-truth leading-blank (đánh đổi
  hợp-lý — reject-valid-row nguy-hiểm hơn).

**Alternatives loại:** raw-apiClient mãi (mất typed) / `data.items[]` (service trả `data` → deser rỗng rows,
bẫy copy `mapCommissioningList` CR-25) / SINGLE-shape (giấu `_err` 400 malformed → parse crash) / hard
`enum:` cho `audit_type`/`status` (leading-blank "" hợp-lệ → reject-valid-row → codegen deser CRASH) /
`lead_auditor_name` ∈ `required[]` (service CHỈ gán khi truthy → row thiếu key → deser fail) / discrete
override param (handler chỉ 3-param JSON-passthrough) / dedicated `AuditFilters` component (audit KHÔNG có
allow-key enumeration cần document — inline đủ) / hợp-nhất rows-key về `items` (đụng service `.py` = Phase-E).
**Accepted.**
