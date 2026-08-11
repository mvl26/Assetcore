---
name: assetcore-import
description: >
  Phát triển tính năng import dữ liệu hàng loạt cho AssetCore — bao gồm
  BE validation layer (pre-validation + post-processing), API endpoints import,
  và FE Import Wizard (Vue 3, 4-bước). Dùng khi user nói "import dữ liệu",
  "bulk import", "upload excel", "import tài sản", "import NCC", "import model",
  "import user", "import phụ tùng", "import kho", "wizard import",
  "template import", "validation import", "pre-validate", "post-process import",
  "ImportWizardView", "useImport", "import_validators", "import_postprocess",
  "api/import_data", "tính năng import", "nhập dữ liệu hàng loạt".
  LUÔN dùng skill này khi task liên quan đến bất kỳ phần nào của import pipeline.
---

# AssetCore Import Feature — Development Guide

## Overview

Skill này là rulebook khi implement tính năng import hàng loạt: **BE validation + API endpoints** + **FE Import Wizard** (Vue 3, 4-bước). Nguyên tắc cốt lõi: **pre-validate TRƯỚC khi insert, post-process SAU khi insert; mỗi layer làm đúng một việc** (API mỏng → validator chỉ đọc → resolver display→code → insert) và Skip-Invalid mode luôn opt-in để user không mất data âm thầm.

> Chiến lược đầy đủ tại `docs/res/guides/import-strategy.md`.
> Skill này là rulebook khi implement — đọc strategy doc trước, áp dụng rules ở đây.

## When to Use

- Viết/sửa BE import: `api/import_data.py`, `import_validators.py`, `import_postprocess.py`, `import_helpers.py`.
- Viết/sửa FE Import Wizard: `importData.ts`, `ReferenceDataView.vue` / `ImportWizardView.vue`, `types/import.ts`.
- Thêm DocType mới vào import (template map + validator + resolvable Link fields).
- Pre-validation, post-processing, Skip-Invalid mode, Tree DocType cascade, template download/export.
- **KHÔNG dùng khi**: viết BE/DocType/workflow thường (→ `assetcore-be`), FE view khác import (→ `assetcore-fe`), chỉ viết/chạy test (→ `assetcore-test`), hoặc còn ở mức ý tưởng (→ `assetcore-plan`).

---

## Process — implement import pipeline (slice + boundary-validated)

Quy trình từng bước (spine — chi tiết ở mục dưới):
1. **Kiến trúc tổng quan** — nắm pipeline FE Wizard → API thin wrapper → validator/helpers/post-processor; phân chia trách nhiệm CỨNG → §Kiến trúc tổng quan
2. **Thin vertical slice 1 entity** — build 1 DocType xuyên stack rồi test, theo dependency order Wave 1→4 → §Named principle (incremental-implementation) — slice + boundary validation
3. **Backend** — pre-validator (trả `list[ImportError]`, không raise) + resolvable Link + post-process side-effect; boundary validation trước insert → §Backend (BE)
4. **Frontend** — Import Wizard 4 bước (Chọn → Upload → Preview → Kết quả), Skip-Invalid opt-in → §Frontend (FE)
5. **Template mapping / Reload / Dependency order** — `_TEMPLATE_MAP`, reload gunicorn `--preload`, thứ tự phụ thuộc → §Template mapping · Reload · Dependency order
6. **Verification** — checklist BE+FE bằng chứng (endpoint·validator·resolver·wizard) trước khi xong → §Verification

---

## Kiến trúc tổng quan

```
┌──────────────────────────────────────────────────────────────┐
│  ReferenceDataView.vue / ImportWizardView.vue  (FE — Vue 3)  │
│  Bước 1: Chọn loại → 2: Upload → 3: Preview → 4: Kết quả    │
└────────────────────┬─────────────────────────────────────────┘
                     │ POST /api/method/assetcore.api.import_data.*
┌────────────────────▼─────────────────────────────────────────┐
│  assetcore/api/import_data.py  (Tier 1 — thin wrapper)       │
│  init_import_folders / preview_ref_data / import_ref_data    │
│  export_ref_data / download_template / build_error_report    │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┴──────────────┐
        ▼                           ▼
┌───────────────────┐    ┌──────────────────────────┐
│ import_validators │    │   import_helpers.py       │
│ (pre-validation)  │    │   parse / build_report    │
│ Tier 2 — service  │    │   folder management       │
└───────────────────┘    └──────────────────────────┘
```

### Hai luồng import

**Luồng A — Direct insert** (hiện tại, dùng cho ref-data):
- `AC Asset Category`, `AC Department`, `AC Location`
- Không có side-effects → `frappe.new_doc().insert()` trực tiếp trong loop
- Không qua Frappe Data Import engine

**Luồng B — Frappe Data Import engine** (dành cho AC Asset, tương lai):
- `AC Asset` có PM schedule, audit trail, workflow → cần engine + post-processor
- Engine xử lý Link validation, row logging, progress tracking

**Phân chia trách nhiệm — CỨNG:**

| Layer | Làm gì | KHÔNG làm gì |
|---|---|---|
| API (`import_data.py`) | Parse params, gọi service, trả JSON | Logic validation, DB access |
| Pre-validator | Kiểm tra domain rules TRƯỚC khi insert | Không insert, không gọi Frappe engine |
| `import_helpers.py` | Parse file, build error report, folder mgmt | Không validate domain |
| Post-processor | Sinh side-effects SAU khi insert xong | Không re-validate, không reinsert |
| FE Wizard | Hiển thị wizard, gọi API | Không tự validate domain logic |

---

## Named principle (incremental-implementation) — slice + boundary validation

> Hút từ agent-skills generic → tailor pipeline import. Build từng lát mỏng, validate ở ranh giới.

- **Thin vertical slice** — KHÔNG implement cả pipeline mọi DocType một lượt. Mỗi lát = **1 entity đi xuyên stack rồi test**: thêm template map + validator (`import_validators`) → post-process (nếu có side-effect) → 1 bước wizard FE (`ReferenceDataView`/`ImportWizardView`) → test, rồi mới sang entity kế. Ví dụ: làm xong `AC Asset Category` (validator → resolvable Link → preview → import → test pass) MỚI sang `AC Department`/`AC Location`. Mỗi lát để hệ thống ở trạng thái chạy được, dễ revert (additive). Theo đúng dependency order Wave 1→4 (xem `references/import-misc.md`).
- **Boundary validation** — validate ở **RANH GIỚI trước khi ghi DB**, không để Frappe engine/`insert()` ném lỗi giữa chừng. Pre-validator chạy ở biên API→DB: kiểm domain rule + resolve Link (display→code qua `_link_lookup_set`) + cascade tree TRƯỚC insert, trả `list[ImportError]` (KHÔNG raise) để user thấy đủ lỗi ở Preview. Insert chỉ chạy khi đã qua biên sạch; post-process side-effect chạy SAU, không re-validate. Đây là lý do "pre-validate TRƯỚC insert, post-process SAU" ở Overview.

---

## Backend (BE)

> Heavy reference: see [references/backend-import.md](references/backend-import.md) — file structure, ErrorCode (`.VALIDATION`/`.INTERNAL`), 6 API endpoints + response schema, pre-validation registry + **LL-IMP-1** `_link_lookup_set`, helper utilities (`parse_upload_file`, `save_file`, template map), Frappe folder management (`ensure_import_folder` + commit), direct insert + **resolvable Link fields (LL-BE-26)**, Skip-Invalid Mode (`_do_import` contract, `_cascade_skip_for_tree`, preview `cascade_count`), Frappe Data Import engine, BE anti-patterns chi tiết (1-9, 15-22), cross-skill BE rules (LL-BE-7/8/26, LL-IMP-1).

## Frontend (FE)

> Heavy reference: see [references/frontend-import.md](references/frontend-import.md) — file structure, types (`RefDataDoctype`, `ImportMode`, `ImportResult`…), API client (`BASE = '/api/method/...'`), file upload (override `Content-Type`), `openImport()` sequence, Skip-Invalid Mode UX (radio strict/skip, cascade warning, 30%/100% guards), template download (URL trực tiếp), FE anti-patterns chi tiết (10-14).

## Template mapping · Reload · Dependency order

> Heavy reference: see [references/import-misc.md](references/import-misc.md) — `_TEMPLATE_MAP` (Phần 4, 11 DocType + generator), reload gunicorn `--preload` qua `kill -HUP` (Phần 5), dependency order Wave 1→4 (Phần 6).

---

## Common Rationalizations

Tổng hợp từ "Phần 3 — Anti-patterns". Chi tiết đầy đủ giữ trong references/ (BE anti-patterns 1-9/15-22, FE anti-patterns 10-14).

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Dùng `ErrorCode.VALIDATION_ERROR`/`INTERNAL_ERROR` cho rõ nghĩa" | Attribute KHÔNG tồn tại → `AttributeError` runtime (anti-pattern #1). Dùng `.VALIDATION`/`.INTERNAL`. |
| "Lưu file bằng `frappe.get_doc('File', content=...)` cho nhanh" | Trigger mandatory validation → *"Fields `file_name` or `file_url` must be set"* (#2). Dùng `save_file()`. |
| "Tạo folder bằng `frappe.new_doc('File', is_folder=1)`" | Không có `ignore_if_duplicate` → crash khi folder đã có (#3). Dùng `create_new_folder()`. |
| "Tạo folder xong khỏi commit, request sau tự thấy" | DB transaction chưa visible → upload kế tiếp fail (#4). `frappe.db.commit()` bắt buộc trong `ensure_import_folder`. |
| "Validator báo lỗi thì cứ `raise` cho gọn" | Raise crash preview, user thấy 500 thay vì danh sách lỗi (#6). Trả `list[ImportError]`, không raise. |
| "Validator check Link chỉ cần collect `r.name`" | Reject mọi display name user nhập (LL-IMP-1 / #21). Dùng `_link_lookup_set(doctype, display_field)` — accept cả code + display. |
| "Tree DocType không cần resolve `parent_location`" | Frappe `nested_set.validate_parent_field` crash *"Could not find Parent"* (LL-BE-26 / #15). Thêm vào `_RESOLVABLE_LINKS_BY_DOCTYPE`. |
| "Skip mode cứ insert child, parent skip kệ nó" | Orphan tree node, gãy `lft/rgt` (#16). PHẢI `_cascade_skip_for_tree` propagate skip mọi cấp. |
| "Default `skip_invalid=True` cho tiện user" | User import thiếu data mà không biết (#17). Skip PHẢI opt-in qua radio FE; BE default `False`. |
| "Upload thẳng `api.post(upload_file, fd)` luôn" | Axios gửi `application/json` phá multipart boundary (#10). Pass `{ headers: { 'Content-Type': undefined } }`. |
| "Gọi API import không cần `/api/method/`" | 404 "Không tìm thấy tài nguyên" (#12). Dùng `BASE = '/api/method/assetcore.api.import_data'`. |
| "Upload trước, tạo folder sau cũng được" | Frappe reject *"Could not find Folder"* (#11). `initImportFolders()` PHẢI gọi trước upload. |
| "Export cứ dump thẳng `frappe.get_all`, cột Link ra sao kệ" | Cột Link ra MÃ hệ thống (`AC-DEPT-0007`) — file xuất ra không đọc được, nhập lại phải tra mã (LL-IMP-2). Chạy `resolve_links_to_display` trước khi ghi sheet. |
| "Báo lỗi 'Dòng 3' là đủ rồi" | Parser bỏ dòng trống ⇒ "dòng 3" có thể là hàng 9 của Excel. Trả `source_row` + `label` VI qua `enrich_issues` (LL-IMP-3). |
| "Doctype này logic riêng, chưa cho skip cũng được" | 1 email sai = bắt sửa file nhập lại từ đầu (LL-IMP-4). Đường upsert riêng vẫn phải nhận `invalid_idx`/`skipped_rows`. |
| "DocType có bảng con thì cho user 2 sheet cha/con cho đúng cấu trúc" | Người nhập liệu bệnh viện điền 1 sheet phẳng (mỗi hàng = 1 dòng con), BE gộp theo khoá (LL-IMP-6). 2 sheet = phải tự khớp khoá tay, sai ngay. |
| "Gộp nhóm theo các hàng liền nhau cho nhanh" | File thật rải rác các hàng cùng mẫu. Gộp theo KHOÁ đã chuẩn hoá tên→mã + nhãn→enum (LL-IMP-6a/b). |
| "Việt hoá enum cho mẫu đang sửa thôi, mẫu khác tính sau" | Nửa Việt nửa Anh khó dùng hơn thuần Anh (LL-IMP-8). Quét cả `_REF_DATA_CONFIG` + `_TEMPLATE_MAP` một lượt, guard `test_import_enum_labels.py` phải xanh. |
| "Hai field cùng ý nghĩa thì dùng chung 1 map nhãn" | `supplier_group` kết thúc 'Service Provider', `vendor_type' kết thúc 'Service' — gộp = khoá rác + nhãn trùng ⇒ đổi ngược không xác định (LL-IMP-7). Đọc `options` TỪNG field. |
| "Danh sách dropdown trong file mẫu chép từ tài liệu là được" | Sheet SLA từng chào `P1 Critical` trong khi DocType chỉ có `P1..P4` ⇒ user làm đúng hướng dẫn vẫn bị từ chối. Đối chiếu `options` thật (LL-IMP-7). |
| "Cột Select cứ để user gõ đúng enum tiếng Anh" | "Semi-Annual"/"Pass/Fail" không phải tiếng người dùng. Template + export in nhãn VI, import nhận cả hai (LL-IMP-7). |
| "Banner ghi hàng 5 hay hàng 6 thì có gì khác" | Parser đọc từ hàng 6; banner sai ⇒ người dùng ghi đè hàng ví dụ, dòng đầu bị nuốt IM LẶNG (LL-IMP-5). |
| "Làm 1 phát cả 11 DocType cho xong pipeline" | Vi phạm thin vertical slice — build 1 entity xuyên stack + test rồi mới sang entity kế (theo dependency order). Cả-một-lượt = lỗi compound, khó revert (Named principle). |
| "Cứ insert rồi engine Frappe tự báo lỗi" | Vi phạm boundary validation — validate ở biên TRƯỚC insert, trả `list[ImportError]` để user thấy đủ lỗi ở Preview; insert chỉ sau khi qua biên sạch (Named principle). |

## Red Flags — STOP

- `ErrorCode.VALIDATION_ERROR` / `INTERNAL_ERROR` xuất hiện trong code (attribute không tồn tại).
- `frappe.get_doc({"doctype": "File", ...}).insert()` để lưu file/tạo folder (dùng `save_file` / `create_new_folder`).
- `ensure_import_folder` thiếu `frappe.db.commit()`; FE upload trước khi gọi `initImportFolders()`.
- Validator `raise` Exception thay vì trả `list[ImportError]`; validator insert/update DB.
- Validator check Link field bằng `{r.name for r in frappe.get_all(...)}` hoặc `frappe.db.exists(...)` không union display field (LL-IMP-1).
- Tree DocType thiếu entry `nsm_parent_field` trong `_RESOLVABLE_LINKS_BY_DOCTYPE`; skip mode không chạy `_cascade_skip_for_tree`.
- `skip_invalid` default `True` ở BE hoặc auto-select skip ở FE radio.
- `api.post('/api/method/upload_file', fd)` thiếu `{ headers: { 'Content-Type': undefined } }`; FormData thiếu `is_private: '1'`.
- FE gọi API import thiếu prefix `/api/method/`; template download gọi `frappeGet` thay vì `window.open(url)`.
- `submit_after_import = True` khi dùng Frappe engine cho AC Asset.
- DocType cha+bảng con dựng bản ghi bằng `new_doc().insert()` trần thay vì service layer của module; gộp nhóm theo vị trí liền kề; khoá nhóm chưa chuẩn hoá tên→mã / nhãn→enum.
- Template hoặc export in enum tiếng Anh cho cột Select đã có nhãn VI ở FE.
- Validator còn tập `_VALID_*` hardcode tiếng Anh; dropdown gõ tay lần hai thay vì sinh từ `ENUM_DISPLAY_BY_DOCTYPE`; nhãn enum khai trong `.vue` thay vì `constants/labels.ts`.
- Khai Link display→code ở `api/import_data.py` thay vì SSoT `utils/import_helpers.LINK_DISPLAY_BY_DOCTYPE` (alias phải `assertIs`, KHÔNG fork bản sao).
- `export_ref_data` ghi thẳng giá trị Link (ra mã hệ thống) — thiếu `resolve_links_to_display`.
- Lỗi trả FE thiếu `source_row`/`label`; hoặc khoá parser `__*` lọt vào `doc.update()`.
- `raise` chặn skip_invalid theo doctype; template `desc` cột Link không có chữ "TÊN"; banner template ghi sai hàng dữ liệu đầu tiên.
- Template `example` dùng system code thay vì display name (user copy sẽ điền code lệch master).

## Verification

Tổng hợp từ "Phần 7 — Checklist trước khi xong". Trước khi khai báo import "xong":

**BE**
- [ ] `api/import_data.py`: 6 endpoints, mỗi cái dùng `_handle` pattern; mọi `ErrorCode` là `.VALIDATION`/`.INTERNAL` (không `*_ERROR`).
- [ ] `ensure_import_folder()` gọi `frappe.db.commit()` sau khi tạo; dùng `save_file()` (không `frappe.get_doc("File")`) cho error report.
- [ ] `_TEMPLATE_MAP`: 3 file riêng cho Category/Department/Location; template files tồn tại trong `assetcore/public/import_templates/`.
- [ ] `VALIDATOR_REGISTRY` đủ DocType; validator không raise, trả `list[ImportError]`; `parse_upload_file` bỏ đúng 5 header rows, trả `tuple[list[str], list[dict]]`.
- [ ] `download_template` set Content-Disposition attachment đúng.
- [ ] `_RESOLVABLE_LINKS_BY_DOCTYPE`: mỗi DocType có Link display name → có entry (đặc biệt Tree DocType với `nsm_parent_field`) (LL-BE-26).
- [ ] (LL-IMP-1) Mọi validator check Link dùng `_link_lookup_set(doctype, display_field)`. Audit grep KHÔNG match khi context build valid Link set: `grep -nE 'for r in frappe\.get_all\([^,]+, fields=\["name"\]\)' assetcore/services/import_validators.py`.
- [ ] Template example dùng display name (tiếng Việt) khớp resolver, không system code.
- [ ] (LL-IMP-2) `LINK_DISPLAY_BY_DOCTYPE` ở `utils/import_helpers.py` là SSoT; `_RESOLVABLE_LINKS_BY_DOCTYPE` chỉ alias; `export_ref_data` gọi `resolve_links_to_display` ⇒ export in TÊN.
- [ ] (LL-IMP-3) mọi lỗi trả ra (preview · import errors · skipped_rows · error report) đi qua `enrich_issues` ⇒ có `source_row` (hàng thật) + `label` (nhãn VI); `_normalise_row` bỏ khoá `__*`.
- [ ] (LL-IMP-4) skip_invalid chạy được cho MỌI doctype hỗ trợ, kể cả đường upsert riêng.
- [ ] (LL-IMP-5) banner template + vùng dropdown + `FIRST_DATA_ROW` cùng chỉ hàng 6.
- [ ] (LL-IMP-6) DocType cha+bảng con: khai đủ `child_table`/`group_key_fields`/`parent_fields`/`child_fields`; khoá nhóm chuẩn hoá TRƯỚC khi gộp; tạo bản ghi qua service layer; trả `groups_created`; export trải phẳng cùng bố cục.
- [ ] (LL-IMP-7) cột Select khai ở `ENUM_DISPLAY_BY_DOCTYPE`, nhãn khớp SSoT FE; template/export in nhãn VI, import nhận cả nhãn VI lẫn giá trị gốc.
- [ ] (LL-IMP-7) `bench --site <site> run-tests --app assetcore --module assetcore.tests.test_import_enum_labels` **XANH** — 4 tầng: phủ-kín · không-khoá-rác · parity FE · dropdown trong `.xlsx` thật.
- [ ] (LL-IMP-8) validator KHÔNG còn tập `_VALID_*` hardcode tiếng Anh cho cột Select (dùng `_check_enum`); đường insert phẳng có `_restore_enum_values`; đã sinh lại TOÀN BỘ template.
- [ ] `import_ref_data()`: param `skip_invalid: bool = False`, default `False`; `_cascade_skip_for_tree()` walk-pass cho cascade nhiều cấp.
- [ ] Response include `skipped` (int) + `skipped_rows` (list[{row, reason, field, message}]); `preview_ref_data` include `cascade_count` cho Tree DocType; edge 100% invalid raise ServiceError, không commit rỗng.

**FE**
- [ ] `BASE = '/api/method/assetcore.api.import_data'` — không thiếu `/api/method/`.
- [ ] `initImportFolders()` gọi TRƯỚC khi show file upload; `api.post upload_file` có `{ headers: { 'Content-Type': undefined } }`; `is_private: '1'` trong FormData.
- [ ] `getTemplateUrl(currentDoctype())` đúng doctype tab active; error report + export dùng `window.open(url)` không `frappeGet`.
- [ ] `ImportMode` radio default `"strict"`, không auto-select skip; bước 3 hiển thị `totalSkip = errors.length + cascadeCount` TRƯỚC confirm.
- [ ] Bước 4 hiển thị `skippedRows` với badge "phụ thuộc" cho cascade; warning đỏ khi `totalSkip/totalRows > 30%`; disable Import khi 100% invalid.
- [ ] `importRefData(doctype, fileUrl, mode)` map snake_case `skipped_rows` → camelCase `skippedRows`.
- [ ] Wizard hiển thị **"Hàng {sourceRow}"** (số hàng thật trong file) + nhãn cột tiếng Việt (`label` / `fieldLabels`) — KHÔNG hiện `row` thô hay fieldname tiếng Anh.

---

## Tham chiếu

- Chiến lược đầy đủ: `docs/res/guides/import-strategy.md`
- Template files: `assetcore/public/import_templates/`
- Template generator: `docs/res/imports/generate_templates.py`
- Frappe file_manager: `frappe.utils.file_manager.save_file`
- Frappe folder API: `frappe.core.api.file.create_new_folder`
- BE conventions: `.claude/skills/assetcore-be/SKILL.md`
- FE conventions: `.claude/skills/assetcore-fe/SKILL.md`
- BE deep-dive: [references/backend-import.md](references/backend-import.md) · FE deep-dive: [references/frontend-import.md](references/frontend-import.md) · Misc: [references/import-misc.md](references/import-misc.md)

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
