# ADR-MOBILE-035 — `getAssetScanInfo` `department_name` scan-schema-parity (**CR-19 · scan-schema-parity** — bồi property `department_name` (Khoa/Phòng) vào schema `AssetScanInfo` NGAY CẠNH `location_name` để đóng field-parity gap màn quét QR F1; **SCHEMA-FIELD ADD** — 0 path/opId/schema-component mới, `additionalProperties:false` GIỮ; ∈ `required[]` mirror `location_name` — BE emit vô-điều-kiện `''` fallback KHÔNG null)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-035 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, closed-schema `additionalProperties:false` — 200-shape `AssetScanInfo` KHÔNG đổi) · **C-ASCAN-PARITY** (đóng drift 4 field BE-emit `manufacturer_sn`/`risk_classification`/`warranty_expiry_date`/`warranty_expired` — CÙNG nguyên tắc: field builder emit thật PHẢI khai schema closed) · precedent field-parity: `location_name` (Vòng 46 — denorm `AC Location` Link → `*_name`, non-null, ∈ `required`) + `getAsset` `AssetDetail.department_name` (`imm00.py:302` — đã có) · Core Doc IMM-00 narrative [`04-api-contract.md`](./04-api-contract.md) §5c (bảng read-path `getAssetScanInfo` + bullet `department_name`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13): builder `assetcore/services/imm00.py` `build_asset_scan_info` return dict — key `department_name` emit **vô-điều-kiện** @**825-828**: `"department_name": _str_or_blank(frappe.db.get_value("AC Department", row["department"], "department_name") if row.get("department") else "")`. `_str_or_blank` LUÔN trả `str` (`''` khi rỗng/None/whitespace-only, KHÔNG `None`) — parity `location_name` @814-817 (Vòng 46). Điều kiện `if row.get("department")` CHỈ skip N+1 query khi asset chưa gán khoa (`_str_or_blank("") → ""`), KHÔNG làm key vắng. `git diff services/imm00.py` vùng `build_asset_scan_info` = TRỐNG round NÀY ⇒ backend ĐÃ LIVE (source-verified), thay đổi CHỈ ở OAS mirror. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (`AssetScanInfo.properties.department_name` + `AssetScanInfo.required[]`). Nguồn yêu cầu: [`assetcore-mobile/docs/api/CONTRACT-REQUESTS.md`](../../../../../assetcore-mobile/docs/api/CONTRACT-REQUESTS.md) CR-19.

---

## Context

Màn **quét QR F1** (mobile-first, sau khi camera đọc mã) render `AssetScanInfo` — tóm tắt định danh + trạng thái thiết bị để KTV hiện trường đối chiếu ĐÚNG thiết bị vật lý trước khi báo sự cố / mở WO. Schema đã có `location_name` (**vị trí lắp đặt**) nhưng THIẾU `department_name` (**Khoa/Phòng** sở hữu thiết bị).

Hệ quả contract-gap (CR-19, phát hiện live khi so màn quét vs màn Chi tiết thiết bị):
- Builder `build_asset_scan_info` (@`imm00.py:825`) **ĐÃ emit `department_name`** (denorm `AC Asset.department` Link → `AC Department.department_name`) — nhưng schema `AssetScanInfo` là **closed-schema** (`additionalProperties:false`) và CHƯA khai property này ⇒ strict codegen client (Dart/Kotlin/typescript-axios strict) **drop field wire-thật hoặc crash deser** (đối xứng đúng drift đã đóng ở **C-ASCAN-PARITY** cho 4 field khác).
- Màn **Chi tiết thiết bị** (`getAsset` → `AssetDetail.department_name` @`imm00.py:302`) đã hiển thị "Khoa/Phòng"; CHỈ màn quét scan-info còn thiếu → lệch trải nghiệm giữa 2 màn cùng thiết bị.
- KTV hiện trường cần biết thiết bị thuộc **khoa nào** (KHÔNG chỉ vị trí lắp đặt) ngay khi quét — DoD F1 "đủ trường tóm tắt".

Ràng buộc quyết định:
1. **BE emit vô-điều-kiện, non-null** (`imm00.py:825` + `_str_or_blank` → LUÔN `str`, `''` khi trống) ⇒ `department_name` PHẢI **∈ `required[]`** và **KHÔNG `nullable`** — mirror `location_name` (đã required), KHÁC `warranty_expiry_date` (nullable, NGOÀI required).
2. **CONTRACT-ONLY**: builder ĐÃ LIVE @source — thay đổi CHỈ ở OAS mirror (documentation/contract), **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
3. **KHÔNG drift closed-schema**: `AssetScanInfo` giữ `additionalProperties:false`; path/opId 65 GIỮ + c5 54 GIỮ (schema-FIELD add ≠ path/schema-component mới).

## Decision

Bồi 1 property `department_name` vào schema `AssetScanInfo`, NGAY CẠNH `location_name`, và THÊM vào `required[]` (SAU `- location_name`):

### `AssetScanInfo.properties.department_name`
- **`type: string`** (AC Department.department_name = `Data` + `_str_or_blank` → LUÔN string). **KHÔNG `nullable`** (`_str_or_blank` trả `''` khi rỗng, KHÔNG `None`).
- **`description` verbatim**: *"Tên khoa/phòng; denorm AC Asset.department -> AC Department.department_name; '' khi không gán; imm00.py:825."*

### `AssetScanInfo.required[]`
- THÊM `- department_name` NGAY SAU `- location_name` — BE emit vô-điều-kiện (`''` fallback, non-null) ⇒ parity `location_name` (đã required). KHÔNG nullable ⇒ KHÔNG optional.

### Invariant contract (guard `TestMobileScanInfoDepartmentNameParity` a..d, `test_mobile_oas`)
- **TC-a** `AssetScanInfo.properties` CÓ `department_name` (drift-closed; RED trước bồi → GREEN sau).
- **TC-b** `department_name` = `type:string` + KHÔNG `nullable:true` (parity `location_name`).
- **TC-c** `department_name` ∈ `AssetScanInfo.required[]` (LUÔN emit, non-null).
- **TC-d** `additionalProperties:false` GIỮ NGUYÊN (closed-schema sweep unbroken khi bồi field).
- **+ `TestMobileAssetScanInfoFieldParity` TC-h** (forward parity-sweep): `service_keys` +`department_name` — sweep phản ánh live-builder (KHÔNG đổi count, giữ invariant service-keys ⊆ schema-props).
- **RED-before/GREEN-after** chứng minh trên TC-a/TC-c: property/required vắng → RED; có → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ nguyên (không bồi property)** | Không đóng CR-19 — builder emit `department_name` nhưng schema closed KHÔNG khai ⇒ strict codegen drop/crash field wire-thật; màn quét lệch màn Chi tiết. |
| **B. Bồi property nhưng `nullable:true` + NGOÀI `required`** | LỆCH BE-behavior: `_str_or_blank` LUÔN trả `str` (`''` KHÔNG `None`) — client sinh field optional/nullable SAI, phải null-check thừa. Parity `location_name` (required, non-null) mới đúng. |
| **C. Nới `additionalProperties:true`** cho `AssetScanInfo` | Phá closed-schema sweep (ADR-001) — mọi field emit PHẢI khai tường minh; nới = mất anti-drift guard cho toàn schema. |
| **D. Kéo thêm `department` raw Link id (`AC-DEPT-xxxx`)** | Rò mã Link nội bộ ra UI (no-raw parity `location`/`device_model` KHÔNG emit raw); màn quét chỉ cần **nhãn** khoa. Builder cố ý CHỈ emit `*_name`. |

## Consequences

- **(+)** Codegen client phơi `department_name: string` ⇒ màn quét QR F1 hiển thị **Khoa/Phòng**, parity màn Chi tiết thiết bị; đóng DoD F1 "đủ trường tóm tắt".
- **(+)** Property + `required` khai == BE emit vô-điều-kiện non-null (TC-a/b/c introspect-vs-schema) ⇒ contract trung thực @source, chống drift.
- **(+)** SCHEMA-FIELD ADD: path-count **65 GIỮ**, opId **65 GIỮ**, c5 **54 GIỮ**, `additionalProperties:false` GIỮ NGUYÊN ⇒ baseline closed-schema sweep + path-count guard + d12/d15/d17 KHÔNG đỏ.
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate. Test: `test_mobile_oas` 606→**610** (+4 TC `TestMobileScanInfoDepartmentNameParity` a..d) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 606→610 / `_GUARD_SUITE_SUM` 749→**753** / `_MOBILE_OAS_TOTAL` 775→**779**.

### Naming guard (∅)
Không thêm schema/component mới ⇒ 0 va chạm tên. Property `department_name` là field NỘI-BỘ của `AssetScanInfo` (đối xứng `location_name`/`device_model_name`) — không đăng ký `components/schemas` mới, không đụng `DepartmentListItem.department_name` (list ref-data CR-10a) / `MyProfile.department_name` (CR-20) / `AssetDetail.department_name` (getAsset).

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau khi regenerate client từ OAS mirror: model `asset-scan-info.ts` (hoặc tương đương) có `department_name: string` (required, non-null). Màn quét QR F1 render "Khoa/Phòng" từ `info.department_name` NGAY CẠNH "Vị trí" (`location_name`) — hiển thị `''` như trạng thái "chưa gán" (KHÔNG null-check thừa). CR-19 → RESOLVED (contract-parity, backend đã ship).
