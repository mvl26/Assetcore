# ADR-IMM00-ASSETCODE — Semantic & auto-gen Mã tài sản (`asset_code`=PK) vs Số serial NSX (`manufacturer_sn`)

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([V1-GATE] — factory asset-code run10, Vòng 1 PHÂN TÍCH) |
| Ngày | 2026-06-08 |
| Phạm vi | IMM-00 (registry — `AC Asset`) — định danh tài sản; chạm IMM-04/05 (commissioning/registration) + import |
| Owner | BA Lead + System Architect |
| Liên quan | `ADR-IMM00-... ` + `docs/imm-04/ADR-001-asset-qr.md` (QR token là field định danh phụ, KHÔNG phải PK) |
| Supersedes | Không — chốt lại DỨT KHOÁT semantic đã hiện hữu trong code (xác nhận hành vi BE, KHÔNG đổi autoname) |

> ADR này là **quyết định cuối** cho semantic định danh tài sản. Mọi spec ở `docs/imm-00/04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md` và task BE/FE/QA Vòng 2–10 phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** đây là gate PHÂN TÍCH — Vòng 1 KHÔNG đụng code (`.py`/`.vue`/`.ts`). Chỉ chốt semantic + nhãn UX để Vòng 2–10 thực thi mà KHÔNG phải hỏi lại. Mỗi task xuống dòng map được tới đúng 1 quyết định D1–D5.

---

## Bối cảnh (vì sao cần GATE này)

**Yêu cầu user (raw, phiên 2026-06-08 11:11):** form tạo tài sản (`/assets/new` → `AssetCreateView.vue`) "không thấy chỗ nhập mã tài sản". Mã tài sản phải hoạt động: **(1)** để trống → tự sinh; **(2)** có nhập → dùng mã đó làm định danh "thay số serial". User gọi nguồn auto-gen là **"serinumber"** — cần làm rõ đây KHÔNG phải số serial NSX.

Nguy cơ nếu KHÔNG chốt: dev/FE/QA có thể (a) hiểu nhầm `asset_code` = `manufacturer_sn` → trộn 2 khái niệm, (b) "tự sinh theo serinumber" → default `asset_code` theo serial (làm serial thành PK), (c) thêm ô nhập sai nhãn/sai helper → user nhập serial vào ô mã. Tất cả phá vỡ invariant `asset_code == name` (PK) và truy xuất nguồn gốc NĐ98.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting — định danh tài sản (IMM-00 foundation/master data). In nhãn/định danh lúc Installation & Commissioning (IMM-04/05).
2. **NĐ98:** Truy xuất nguồn gốc (UDI/Serial) + hồ sơ thiết bị. `asset_code` = định danh nội bộ BV (PK truy hồ sơ); `manufacturer_sn` = số serial NSX phục vụ truy xuất nguồn gốc/UDI. Hai khái niệm ĐỘC LẬP — không được trộn (serial do NSX kiểm soát, có thể trùng chéo-vendor / rỗng / không hợp pattern PK).
3. **Stakeholder:** Quản trị tài sản (cấp/quản mã), Kỹ thuật viên TBYT (tra cứu theo mã), người import dữ liệu legacy.
4. **Lifecycle event:** không phát sinh event mới — `asset_code` cố định lúc `after_insert`; immutable sau đó. (QR `qr_generated` là cơ chế riêng, không liên quan PK.)
5. **Hậu quả nếu data sai:** serial làm PK → 2 tài sản khác NSX trùng serial → INSERT đụng UNIQUE / ghi đè hồ sơ → mất audit trail. PK đổi được sau tạo → mọi link (Work Order/Incident/Audit) trỏ sai → vỡ truy xuất nguồn gốc.

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| F1 | `autoname()`: nếu `asset_code` nhập (sau strip) → validate pattern `^[A-Za-z0-9._\-/]+$`, `name = asset_code = code`. | `ac_asset.py:34-43` |
| F2 | `autoname()`: nếu `asset_code` TRỐNG → `name = make_autoname(series)`, `series` mặc định `AC-ASSET-.YYYY.-.#####`, rồi `asset_code = name`. KHÔNG default theo serial. | `ac_asset.py:13,45-48` |
| F3 | `asset_code` UNIQUE ở **DB-level**: `ac_asset.json` field `asset_code` `unique=1`. | `ac_asset.json` (field `asset_code`) |
| F4 | `manufacturer_sn` KHÔNG có DB-unique: `ac_asset.json` field `manufacturer_sn` `unique=null`. Uniqueness CHỈ ở **app-level** qua validator. | `ac_asset.json` (field `manufacturer_sn`); `ac_asset.py:211-221` |
| F5 | `_validate_unique_asset_code()`: chặn trùng `asset_code` (app guard, song song DB-unique) + **immutable**: nếu `not is_new()` và `old != asset_code` → throw "Mã tài sản không thể thay đổi sau khi tạo". | `ac_asset.py:193-209` |
| F6 | `_validate_unique_manufacturer_sn()`: throw nếu trùng `manufacturer_sn` (app-level, `frappe.db.exists`). KHÔNG immutable. | `ac_asset.py:211-221` |
| F7 | `naming_series`: Select `reqd=1`, options chỉ `AC-ASSET-.YYYY.-.#####`. `doctype.autoname == "autoname"` (dùng controller `autoname()`, KHÔNG dùng naming_rule). | `ac_asset.json` (fields + `autoname`) |
| F8 | **FE `AssetCreateView.vue` THIẾU ô `asset_code`** — chỉ có "Serial Number" bind `form.manufacturer_sn` (dòng 171-172). `AssetEditView.vue` cũng KHÔNG có ô `asset_code`. | `AssetCreateView.vue:171-172`; grep `asset_code` trong 2 view = 0 |
| F9 | API `create_asset` đã NHẬN `asset_code` từ payload: `doc.update({k:v ...})` truyền thẳng mọi field form_dict (trừ cmd/doctype) → `asset_code` đi vào `autoname()`. `createAsset(data: Partial<AcAsset>)` và type `AcAsset.asset_code` đã tồn tại ở FE. | `api/imm00.py:545-550`; `frontend/src/api/imm00.ts:28,57` |
| F10 | Import validator asset: dedup `asset_code` theo cả `name` lẫn cột `asset_code` (existing) + trong batch (`seen_codes`); thông báo VI "đã tồn tại trong hệ thống" / "bị trùng lặp trong file". | `services/import_validators.py:635-682` |
| F11 | **Reserved-prefix data-hygiene THỰC TẾ = `_` (underscore) và `SI-`** (loại asset rác test/security-audit khỏi list/donut) — KHÔNG phải `TS-`/`CAT-`. `TS-…` là `asset_code`/`name` user-nhập/legacy (vd `TS-2025-USG-001`); `CAT-.####` là autoname của **AC Asset Category** (doctype KHÁC), KHÔNG phải asset. | `services/imm00.py:1534-1538`; `ac_asset_category.py:32` |
| F12 | AC Asset Category đã có description chuẩn cho mã: "Nếu nhập tay → dùng làm mã định danh. Nếu để trống → hệ thống tự sinh CAT-.####. Sau khi tạo không thể thay đổi." → mẫu helper text để D4 mirror cho `asset_code`. | `ac_asset_category.json:47` (field `category_code`) |
| F13 | **Test gap:** KHÔNG có test dành riêng cho `autoname` (trống vs nhập), uniqueness/immutability `asset_code`, hay app-unique `manufacturer_sn` trong `test_imm00.py`. (Có test QR token uniqueness + reserved-prefix data-hygiene — khác semantic này.) | grep `def test_*autoname/asset_code uniq/immutab/serial uniq` = 0 |

---

## Quyết định (5 quyết định — DỨT KHOÁT, mỗi quyết định 1 dòng + lý do)

### D1 — Semantic: `asset_code` = Mã tài sản = `name`/PK; `manufacturer_sn` = Số serial NSX = field nghiệp vụ riêng

**Quyết định (1 dòng):** `asset_code` (Mã tài sản) **LÀ** `name` (PK định danh nội bộ); `manufacturer_sn` (Số serial NSX) là field nghiệp vụ ĐỘC LẬP — **KHÔNG BAO GIỜ** trộn/đồng nhất 2 khái niệm.

**Lý do:** PK phải do BV kiểm soát, ổn định, hợp pattern (F1–F3); serial do NSX kiểm soát, có thể rỗng/trùng-chéo-vendor/không hợp pattern (F4, F6). Trộn 2 khái niệm phá truy xuất nguồn gốc NĐ98 + vỡ link audit. Code đã tách đúng (F1, F5, F6) → ADR chỉ **chốt thành luật**.

---

### D2 — Auto-gen khi `asset_code` TRỐNG: series counter `make_autoname('AC-ASSET-.YYYY.-.#####')` — KHÔNG default-theo-serial

**Quyết định (1 dòng):** `asset_code` trống → tự sinh bằng **series counter** `make_autoname("AC-ASSET-.YYYY.-.#####")` (giữ nguyên hành vi BE F2), **KHÔNG** default `asset_code = manufacturer_sn`.

**Làm rõ "serinumber":** "serinumber" user nói = `manufacturer_sn` (Số serial NSX) — đây là **field nghiệp vụ riêng**, **KHÔNG phải nguồn auto-gen** mã. "Tự sinh" = series counter của hệ thống, độc lập serial.

**Lý do bác phương án serial-as-code:**
- Serial có thể **rỗng** → không có gì để làm PK (F4: không reqd).
- Serial có thể **trùng chéo-vendor** (2 NSX khác nhau cùng chuỗi serial) → đụng UNIQUE PK / ghi đè hồ sơ.
- Serial có thể **không hợp pattern PK** `^[A-Za-z0-9._\-/]+$` (chứa space/ký tự lạ) → `autoname()` throw (F1).
- Serial do **NSX kiểm soát**, không phải BV → không an toàn làm khóa định danh nội bộ ổn định.

**Self-correction:** KHÔNG đổi autoname hiện có. Hành vi BE F2 đã đúng yêu cầu user "(1) trống → tự sinh; (2) nhập → dùng làm định danh". Khoảng cách DUY NHẤT là **FE thiếu ô nhập** (F8) — sửa ở Vòng 2–10, KHÔNG đổi BE autoname.

---

### D3 — Pattern / uniqueness / immutability: chốt thành luật + DB-unique vs app-unique

**Quyết định (1 dòng):**
- `asset_code`: khớp `^[A-Za-z0-9._\-/]+$` · **UNIQUE ở DB-level** (`unique=1`) · **IMMUTABLE** sau khi tạo.
- `manufacturer_sn`: **UNIQUE ở app-level** (validator `_validate_unique_manufacturer_sn`, `unique=null` ở DB) · **mutable** (sửa được sau tạo).

**Khác biệt DB-unique vs app-unique (chốt rõ):**
- **DB-unique** (`asset_code`): MariaDB enforce constraint → mọi đường ghi (UI/REST/import/`bench execute`/race-condition) đều bị chặn ở tầng DB, không phụ thuộc validator có chạy hay không.
- **App-unique** (`manufacturer_sn`): chỉ validator Python `frappe.db.exists` kiểm tra (F6). Có **lỗ race-condition** (2 insert đồng thời cùng serial qua check trước commit) và bypass nếu ai đó ghi thẳng DB bỏ validate.

**Có nâng `manufacturer_sn` lên DB-unique không? → CHỐT: KHÔNG nâng (giữ app-unique).**
- **Lý do:** serial NSX **có thể trùng hợp pháp** giữa các tài sản trong thực tế (tái sử dụng serial sau RMA, NSX khác nhau, dữ liệu legacy thiếu chuẩn). DB-unique cứng sẽ chặn import legacy + chặn nghiệp vụ hợp lệ; app-unique cho phép xử lý mềm (cảnh báo, override có kiểm soát ở roadmap). Nếu tương lai cần siết → mở ADR riêng + migration (phải làm sạch trùng trước khi thêm constraint). *(Cần khảo sát baseline)* tỉ lệ trùng serial trong data hiện hữu trước khi cân nhắc siết.

---

### D4 — UX/i18n VI: nhãn chuẩn + helper text để user KHÔNG nhầm 2 ô

**Quyết định (1 dòng):** dùng **nguyên văn** dưới đây cho FE create/edit/import (đồng nhất mẫu đã có ở AC Asset Category, F12).

| Field | Label VI (chuẩn) | Helper text VI (nguyên văn — dùng y hệt) |
|---|---|---|
| `asset_code` | **Mã tài sản** | `Để trống = hệ thống tự sinh; nhập = dùng làm mã định danh, không sửa được sau khi tạo` |
| `manufacturer_sn` | **Số serial NSX** | `Số serial của nhà sản xuất (NSX). Field nghiệp vụ — KHÔNG phải mã định danh tài sản.` |

**Ràng buộc FE:**
- Ô "Serial Number" hiện tại (`AssetCreateView.vue:172`, bind `form.manufacturer_sn`) phải đổi label EN→VI thành **"Số serial NSX"** (diệt leak EN).
- **THÊM ô "Mã tài sản"** (`asset_code`) đứng TRÊN/RIÊNG ô serial, với helper text nguyên văn ở trên — để user không gõ serial vào ô mã và ngược lại.
- `AssetEditView.vue`: ô `asset_code` (nếu hiển thị) phải **read-only/disabled** (immutable D3) + helper "không sửa được sau khi tạo".

**Lý do:** F8 cho thấy FE thiếu ô mã + chỉ có ô serial nhãn EN → user buộc gọi serial là "serinumber" để tự sinh. Helper text tách bạch 2 ô là biện pháp UX trực tiếp chống nhầm (đã chứng minh hiệu quả ở Category, F12).

---

### D5 — Quy tắc dữ liệu hiện hữu + reserved-prefix + invariant `asset_code == name`

**Quyết định (1 dòng):** `asset_code == name` là **INVARIANT** (đã unify, F1–F2) — chỉ **assert** invariant, **KHÔNG backfill/migration** nếu data đã thoả; collision + reserved-prefix phải báo lỗi rõ.

**Chốt từng phần:**
- **Invariant:** mọi `AC Asset` phải có `asset_code == name`. Trống → autoname đồng bộ (F2); nhập → cả 2 = code (F1). Vòng 2–10: thêm **assert/guard test** invariant (D5↔F13 test gap), KHÔNG sửa data.
- **Reserved-prefix (đính chính F11):** prefix data-hygiene THỰC SỰ loại asset rác = **`_`** (test fixtures) và **`SI-`** (security-injection audit), KHÔNG phải `TS-`/`CAT-`. `TS-…` là `asset_code`/`name` hợp lệ (user/legacy nhập); `CAT-.####` thuộc **AC Asset Category** (doctype khác). → KHÔNG cấm user nhập `asset_code` bắt đầu bằng `TS-`/`CAT-`; CHỈ tránh đụng `_`/`SI-` (vốn không phải pattern người dùng gõ).
- **Collision `asset_code == series-PK-trùng`:** nếu user nhập `asset_code` trùng một `name` đã do series sinh (vd nhập tay "AC-ASSET-2026-00001") → app guard (F5) + DB-unique (F3) + import dedup (F10) đều báo lỗi rõ VI ("Mã tài sản … đã tồn tại"). Giữ nguyên — KHÔNG nới.
- **Backfill/migration:** **KHÔNG cần** — code đã unify `asset_code=name` cho mọi đường ghi (F1, F2). Chỉ thêm **invariant-assert test** để chứng minh data hiện hữu thoả (nếu test phát hiện vi phạm cũ → MỞ ticket riêng, KHÔNG ôm vào gate này). *(Cần khảo sát)* nếu QA muốn 1 lệnh `bench execute` đếm `COUNT(*) WHERE asset_code != name` để xác nhận 0 trước khi đóng gate.

---

## Bàn giao Core Doc — task Vòng 2–10 map tới đúng 1 quyết định

> Gate code: ADR chốt → Vòng 2–10 thực thi. KHÔNG đụng `.py/.vue/.ts` ở Vòng 1.

| Task (BE/FE/QA) | Map | Mô tả delta |
|---|---|---|
| **BE-1** | D2/D5 | Giữ nguyên `autoname()` (F1–F2) — **no-op**, chỉ xác nhận & viết docstring/comment chốt "KHÔNG default-theo-serial". |
| **BE-2** | D3 | Giữ `asset_code` `unique=1` (DB) + `manufacturer_sn` `unique=null` (app-only). Quyết định D3: KHÔNG nâng serial lên DB-unique. |
| **FE-1** | D4 | `AssetCreateView.vue`: THÊM ô "Mã tài sản" (`form.asset_code`) + helper text nguyên văn D4; đổi label "Serial Number"→"Số serial NSX". |
| **FE-2** | D4/D3 | `AssetEditView.vue`: hiển thị `asset_code` **read-only** (immutable) + helper "không sửa được sau khi tạo". |
| **FE-3** | D1/D4 | Import wizard/template: cột "Mã tài sản"(`asset_code`) tách cột "Số serial NSX"(`manufacturer_sn`), helper/nhãn chuẩn D4. |
| **QA-1** | D2 | Test `autoname` RED→GREEN: trống → `name` khớp `^AC-ASSET-\d{4}-\d{5}$` & `asset_code==name`; nhập → `name==asset_code`. |
| **QA-2** | D3 | Test uniqueness `asset_code` (DB-unique, trùng→throw) + immutability (`not is_new()` đổi code→throw). |
| **QA-3** | D3 | Test `manufacturer_sn` app-unique (trùng→throw validator) + **mutable** (sửa serial sau tạo → OK). |
| **QA-4** | D2/D1 | Test KHÔNG default-theo-serial: tạo asset có `manufacturer_sn` + `asset_code` trống → `asset_code` là `AC-ASSET-…` (KHÔNG bằng serial). |
| **QA-5** | D5 | Invariant-assert: mọi asset `asset_code == name` (đóng test gap F13). *(Cần khảo sát)* count `asset_code != name` = 0 trên data hiện hữu. |
| **FE-4** | D4 | i18n VI sweep: ô serial KHÔNG leak label EN; helper tách bạch 2 ô. |

---

## Tham chiếu chéo

- DocType controller: `assetcore/assetcore/doctype/ac_asset/ac_asset.py` (autoname/validators)
- DocType schema: `assetcore/assetcore/doctype/ac_asset/ac_asset.json` (field defs)
- API: `assetcore/api/imm00.py::create_asset` / `update_asset`
- Import: `assetcore/services/import_validators.py` (asset dedup)
- Reserved-prefix SSoT: `assetcore/services/imm00.py:1534-1538`
- FE: `frontend/src/views/asset/AssetCreateView.vue`, `AssetEditView.vue`, `frontend/src/api/imm00.ts`, `frontend/src/types/imm00.ts`
- Mẫu UX tham chiếu: `assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.json:47` (description mã danh mục)
- Core Doc: `docs/imm-00/04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`
- Test gap (đóng ở Vòng 2–10): `assetcore/tests/test_imm00.py`
