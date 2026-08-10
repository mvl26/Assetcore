# ADR-001 — QR cấp tài sản (Asset-level QR)

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** (chốt vòng 1 — factory QR) |
| Ngày | 2026-06-04 |
| Phạm vi | IMM-00 (registry — `AC Asset`) + IMM-04 (commissioning — tương thích ngược) |
| Owner | BA Lead + System Architect |
| Liên quan | Roadmap A1→A6 + B (xem §8) |
| Supersedes | Cơ chế QR cũ ở cấp commissioning (`internal_tag_qr`) — **không thay thế**, chỉ bổ sung (xem D6) |

> ADR này là **quyết định cuối** cho 6 vấn đề kiến trúc QR cấp tài sản. Mọi spec ở `docs/imm-00/04_Backend_Design.md` §II.1.8 và `docs/imm-04/04_Backend_Design.md` §8.1 phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.

---

## Bối cảnh (vì sao cần)

Yêu cầu nghiệp vụ: mỗi **tài sản** (thiết bị y tế) có mã QR → in từ hệ thống → dán lên thiết bị → người dùng quét QR (camera điện thoại) → xem thông tin thiết bị.

**As-Is (verify code 2026-06-04):**
- QR hiện CÓ nhưng gắn vào IMM-04 Commissioning: field `internal_tag_qr` format `BV-{DEPT}-{YYYY}-{SEQ}` (`services/imm04.py:575`, `generate_qr_label` @996).
- `AC Asset` doctype có **0 field QR** → asset import/legacy không có QR; QR không sống ở cấp tài sản (verify: `ac_asset.json`).
- QR encode **chuỗi tag** (không phải URL) → camera điện thoại quét ra text vô dụng, không mở app (`QRLabel.vue` encode tag string).
- Chưa có quét bằng **camera** (`QRScanView.vue` = scanner-wedge gõ tay/đầu đọc).
- Chưa có in label **hàng loạt** theo asset.
- Route "deep-link" chỉ **redirect** `/documents/asset/:assetId → /documents?asset=` (`router/index.ts:233`), không phải màn xem thông tin thiết bị mobile.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting (định danh tài sản — IMM-00) + Installation & Commissioning (IMM-04 in nhãn lúc nghiệm thu).
2. **NĐ98:** Truy xuất nguồn gốc (UDI/Serial) + hồ sơ thiết bị → QR là cổng vào hồ sơ → **KHÔNG được public-anonymous** (rò rỉ thông tin thiết bị y tế + vị trí lâm sàng).
3. **Stakeholder:** Kỹ thuật viên TBYT (quét tra cứu tại giường), Workshop (in nhãn), Quản trị tài sản (sinh token, backfill).
4. **Lifecycle event:** `qr_generated` (sinh token), `label_printed` (in nhãn).
5. **Hậu quả nếu data sai:** token đoán được → liệt kê toàn bộ thiết bị (enumeration) → lộ vị trí/cấu hình thiết bị lâm sàng; token đổi → nhãn đã dán hỏng (phải bền/idempotent).

---

## Quyết định (6 quyết định — KHÔNG mơ hồ)

### D1 — Payload QR = field MỚI `qr_token` trên `AC Asset`

```python
import secrets
qr_token = secrets.token_urlsafe(16)   # ~22 ký tự URL-safe [A-Za-z0-9_-]
```

| Thuộc tính | Giá trị |
|---|---|
| Field | `qr_token` (Data, length 32) trên `AC Asset` |
| Sinh giá trị | `secrets.token_urlsafe(16)` → ~22 ký tự URL-safe |
| Tính chất | **enumeration-safe** (không tuần tự, không đoán được), **idempotent** (sinh đúng 1 lần, không đổi khi update), **unique** (DB UNIQUE), **read_only** trên form |
| Thời điểm sinh | `before_insert` (mọi asset mới); backfill cho asset cũ (D5) |

**Lý do loại bỏ các phương án khác:**

| Phương án | Vì sao loại |
|---|---|
| Dùng `name` (`AC-ASSET-.YYYY.-.#####`) | **Tuần tự → đoán được.** `AC-ASSET-2026-00001` → kẻ tấn công liệt kê toàn bộ asset bằng cách tăng số. Vi phạm enumeration-safe (D4/NĐ98). |
| Dùng `internal_tag_qr` (`BV-{DEPT}-{YYYY}-{SEQ}`) | **Đoán được** (DEPT + YYYY + SEQ tuần tự) + **doc-bound** (sống ở commissioning, không phải mọi asset có) + đã là **chuỗi tag không phải URL**. Giữ cho tương thích ngược (D6) nhưng KHÔNG dùng làm payload deep-link. |
| `manufacturer_sn` / `udi_code` | Có thể trống, do NSX cấp (không kiểm soát unique nội bộ), in trên nhãn NSX → lộ ra ngoài. |

**Hệ quả:** `qr_token` ≠ định danh nghiệp vụ — chỉ là **khóa tra cứu mờ** (opaque lookup key). Định danh nghiệp vụ vẫn là `name`/`asset_code`/`manufacturer_sn`.

---

#### D1.1 — SSoT sinh token collision-safe (Self-Correction Vòng 17 B — BR-00-31)

> **Lỗi thiết kế gốc:** D1 chốt `qr_token` UNIQUE + "collision-safe" nhưng KHÔNG đặc tả **1 SSoT** sinh token → collision-safety rải rác 3 kiểu KHÔNG nhất quán: (a) `_ensure_qr_token` (before_insert) + `ensure_asset_qr_token` gọi `generate_qr_token()` **TRẦN** (0 guard → đụng UNIQUE → `IntegrityError` 500, abort INSERT); (b) `regenerate_asset_qr_token` vòng `while new==old` chỉ guard token CŨ (hở token asset khác); (c) patch backfill 008 tự loop write-then-catch Duplicate (bản logic thứ 2). 1 đường HỞ hoàn toàn + 2 bản logic song song.

**Quyết định:** gom về **1 helper SSoT** `services/imm00.py::generate_unique_qr_token(exclude: str | None = None) -> str`:

| Thuộc tính | Giá trị |
|---|---|
| Cơ chế | loop `generate_qr_token()` tới khi `not frappe.db.exists("AC Asset", {"qr_token": token})` (pre-write check, UNIQUE IDX O(log n)) VÀ `token != exclude` |
| Bounded retry | hằng `_MAX_QR_TOKEN_RETRY = 5`; cạn → `frappe.throw(<VI sạch>)` (= `frappe.ValidationError`, message VI qua envelope; KHÔNG `IntegrityError` thô 500). Test contract bám `assertRaises(frappe.ValidationError)`. ⚠️ loop dùng `_attempt` KHÔNG `_` (shadow gettext `_`). |
| Bản chất | **thuần token-gen — KHÔNG ghi DB** (chỉ `frappe.db.exists` read) |
| `exclude` | chặn token cũ khi rotate (`regenerate(exclude=old)` → guard CẢ cũ CẢ asset khác trong 1 vòng) |
| Delegate | `_ensure_qr_token` (before_insert) + `ensure_asset_qr_token` + `regenerate_asset_qr_token` + patch 008 `_set_token_collision_safe` — KHÔNG còn `generate_qr_token()` trần ở đường ghi, KHÔNG còn loop+catch Duplicate riêng |
| Schema-delta | **KHÔNG** (thuần helper + delegate + test; KHÔNG cap/field/DocType/enum/patch mới — chỉ sửa patch 008 sẵn có). `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE KHÔNG đổi. |

Spec ràng buộc đầy đủ: IMM-00 [`02 BR-00-31` + `FR-00-76..79`](../imm-00/02_Analysis_Design.md), [`04 §II.1.8-COLL`](../imm-00/04_Backend_Design.md), [`07 §III.6.e`](../imm-00/07_Testing_QA.md).

---

### D2 — Deep-link schema = `/a/<token>`

```
<qr-base>/a/<qr_token>
ví dụ: https://htm.benhvien.vn/a/Xk7p2Qm9_aZ4Lr8sT0wVcQ
```

| Thuộc tính | Giá trị |
|---|---|
| Route FE | `/a/:token` (URL ngắn — camera điện thoại quét ra link mở thẳng màn info) |
| Build URL tuyệt đối | BE dùng helper SSoT `services.imm00._build_qr_url(qr_token)`. **Host = base-URL CÔNG KHAI cấu hình được** (site_config key `assetcore_qr_base_url`, vd `https://htm.benhvien.vn`); KHÔNG cấu hình → fallback `frappe.utils.get_url(f"/a/{qr_token}")`. Xem **D2.1**. |
| Resolve | FE `/a/:token` gọi `resolve_qr_token(token)` → lấy `name` → `router.replace({name:'AssetScanInfo'})` (**A6: màn info mobile-first MỚI `/assets/:id/info`**, KHÔNG redirect sang `AssetDetail` admin). Màn info gọi `get_asset_scan_info` lấy payload cốt lõi. |
| Bỏ | Route cũ `/documents/asset/:assetId → redirect /documents?asset=` KHÔNG còn là deep-link QR (giữ route cho link cũ, nhưng QR mới trỏ `/a/<token>`). |

**Lý do `/a/<token>` thay vì `/assets/:id?...`:** URL **ngắn nhất** (QR ít module hơn → in nhỏ/quét xa hơn), **không lộ** `name` tuần tự trong URL (enumeration), **token-only** → resolve qua 1 endpoint RBAC-gated thay vì lộ route nội bộ.

#### D2.1 — Host công khai cấu hình được (Self-Correction Vòng 14 B — BR-00-30)

> **Self-Correction (root-cause).** Phiên bản trước của D2 đặc tả `frappe.utils.get_url(f"/a/{qr_token}")` là hành vi **CUỐI** ("host từ site config, dùng được ngoài LAN"). **Sai trên thực địa:** `get_url` trả `host_name`/`request host` của Frappe — trên site nội bộ là `http://miyano/a/<token>` (host LAN, không có DNS công cộng) → camera điện thoại quét tem **KHÔNG mở được**. P2 blocker tái diễn ở eval Vòng 4/9/10. → D2 KHÔNG còn coi `get_url` là final; base-URL deep-link giờ là **host công khai cấu hình được**, `get_url` chỉ là fallback dev/test.

| Quy tắc | Chi tiết |
|---|---|
| **Nguồn base** | site_config key MỚI `assetcore_qr_base_url` (vd `https://htm.benhvien.vn`) đọc qua `frappe.conf.get(...)`. KHÔNG hardcode. |
| **Có giá trị hợp lệ** | `_build_qr_url('TOK') == '<base-đã-strip-/>/a/TOK'` — strip MỌI `/` thừa cuối base, nối đúng **1** `/` (KHÔNG `//`). |
| **Vắng/rỗng** | Fallback `frappe.utils.get_url(f"/a/{token}")` (hành vi cũ — dev/test/site chưa cấu hình KHÔNG vỡ). |
| **Hợp lệ hoá (1 chỗ)** | `_qr_base_url()` (đọc + validate): CHỉ scheme `http`/`https`; reject (→ trả `None` ⇒ fallback `get_url` + log cảnh báo **1 lần**, KHÔNG throw) khi thiếu scheme / scheme lạ / có path (ngoài `/` cuối — bị strip) / có query / fragment / khoảng trắng / chứa `/a/` lồng nhau. |
| **Token nguyên vẹn** | token urlsafe (`[A-Za-z0-9_-]`) nối THẲNG sau `/a/` (KHÔNG encode) → URL chứa token y nguyên. |
| **1 SSoT** | MỌI consumer deep-link (`build_asset_label_data` + batch, `regenerate_asset_qr_token` payload, `imm04.generate_qr_label` qua D6.1) dùng CHUNG `_build_qr_url`. `grep '/a/' services/` chỉ còn 1 điểm sinh URL. |

Spec đầy đủ + acceptance: [`../imm-00/02_Analysis_Design.md`](../imm-00/02_Analysis_Design.md) **BR-00-30** + [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8-QRBASE. Cấu hình deploy: [`../imm-00/08_Deployment.md`](../imm-00/08_Deployment.md) §II.2.

---

### D3 — Lifecycle event MỚI: `qr_generated`, `label_printed`

Thêm **2 option** vào `Asset Lifecycle Event.event_type` (verify: options hiện tại KHÔNG có 2 giá trị này):

| event_type | Khi nào emit | Emit bởi (CHỐT A3) | root_doctype / root_record | Vòng |
|---|---|---|---|---|
| `qr_generated` | Lần đầu sinh `qr_token` (before_insert / backfill / token-less on-demand) | `emit_qr_generated` qua `ensure_asset_qr_token` (best-effort) | `AC Asset` / `<asset name>` | A1 ✅ |
| `label_printed` | Khi in nhãn (1 hoặc batch) — 1 event / asset / lần in | `emit_label_printed` qua `mark_label_printed` POST (KHÔNG nuốt lỗi) | `AC Asset` / `<asset name>` | **A3** |
| `qr_regenerated` | Khi **rotate** (sinh-lại) `qr_token` — vô hiệu hoá token cũ + cấp token mới | `emit_qr_regenerated` qua `regenerate_asset_qr_token` POST (**KHÔNG nuốt lỗi** — sự kiện bảo mật phải ghi được, all-or-nothing) | `AC Asset` / `<asset name>` | **B (item 2)** |

> **CHỐT B item 2 — `qr_regenerated` là OPTION MỚI (option thứ 3 của QR).** Verify enum live (`asset_lifecycle_event.json`, 2026-06-04): hiện CÓ `qr_generated`+`label_printed` (A1/A3) nhưng **KHÔNG có `qr_regenerated`** → đây là schema-delta DUY NHẤT của B item 2 (xem §II.6 / handover row). `emit_qr_regenerated` ghi 1 ALE `qr_regenerated` + 1 IMM Audit Trail `event_type='System'` với `change_summary` nêu **rotate/vô-hiệu-hoá** — **TUYỆT ĐỐI KHÔNG log token thô (cũ hay mới)** vào notes/change_summary (token là khoá tra cứu mờ; lộ token = lộ deep-link asset). Không nuốt lỗi (≠ `emit_qr_generated` best-effort): rotate là chủ động ứng phó lộ token → audit BẮT BUỘC ghi được, lỗi ghi event → raise → 422/500 (asset KHÔNG bị set token mới nửa chừng mà thiếu audit).

**A3 — CHỐT đầy đủ (V4):** endpoint dữ liệu + sự kiện in đặt ở **IMM-00 registry** (`api/imm00.py`+`services/imm00.py`), KHÔNG IMM-04:
- `get_asset_label_data(asset)` / `get_asset_label_data_batch(assets)` (GET): payload nhãn `{name, asset_code, device_model_name, location_name, lifecycle_status, qr_url}`; `qr_url = get_url(f"/a/{token}")`; token-less → `ensure_asset_qr_token` trước (KHÔNG rỗng); **READ-ONLY về print event** (KHÔNG emit `label_printed`/audit). Batch: 1 query gộp + IN-clause (KHÔNG N+1), thứ tự = input, missing → `{name, error:"AC-E001"}`.
- `mark_label_printed(assets)` (POST): 1 ALE `label_printed` + 1 audit / asset / lần in (N lần = N event); all-or-nothing; gate `asset.write` (**vòng B — SIẾT, xem D4**; A3 tạm dùng `asset.read`).
- IDOR: cả 3 tái dùng `assert_vendor_can_access("AC Asset", name)`; vendor ngoài scope → 403 (batch/POST → 403 toàn call). Asset không tồn tại → 404 leak-safe.

Helper dùng sẵn: `assetcore.utils.lifecycle.create_lifecycle_event(asset, event_type, actor, from_status, to_status, root_doctype, root_record, notes)` (verify signature `lifecycle.py:72`). Audit: `log_audit_event(...)` (SHA-256 chain).

**Schema-delta:** chỉ mở rộng enum `event_type` (đã làm ở A1 — `asset_lifecycle_event.json` line 54 đã chứa cả 2) — KHÔNG đổi field nào của `Asset Lifecycle Event`.

---

### D4 — RBAC (A2 — resolve contract CHỐT)

| Hành động | Cổng | Auth | Vòng |
|---|---|---|---|
| Resolve token (`resolve_qr_token`) | capability `asset.read` (gate qua `require("asset.read")`) | **AUTH-REQUIRED** (NĐ98 — KHÔNG anonymous-public) | A2 |
| Màn info thiết bị (`/assets/:id/info` — `AssetScanInfo`) | capability `asset.read` (**A6: màn info mobile-first MỚI** qua `get_asset_scan_info`, KHÔNG phải `AssetDetail` admin) | AUTH-REQUIRED | A2 (redirect) / A6 (màn info) |
| In nhãn / sinh-lại nhãn (GET label data + POST mark printed) | capability **`asset.write`** (gate `require("asset.write")`) — **CHỐT vòng B** | AUTH-REQUIRED | **B** |
| **Sinh-lại / rotate (regenerate) `qr_token`** (`regenerate_asset_qr_token` POST) | capability **`asset.write`** (cùng cổng ghi — rotate là GHI: overwrite token + emit event/audit; KHÔNG cap riêng) | AUTH-REQUIRED | **B (item 2)** |

> **D4-regenerate — Contract CHỐT B item 2 (rotate token cấp asset):**
> Endpoint MỚI `assetcore.api.imm00.regenerate_asset_qr_token(asset)` — `@frappe.whitelist(methods=["POST"])`. Mục đích: **vô hiệu hoá QR bị lộ** (in nhầm/chụp/rò rỉ) + cấp token MỚI. Khác `ensure_asset_qr_token` (idempotent if-empty — KHÔNG overwrite token đang có).
>
> | # | Quy tắc | Chi tiết |
> |---|---|---|
> | 1 | **Gate `asset.write` ĐẦU HÀM** | `rbac.require("asset.write")` chạy TRƯỚC mọi DB read/write. User chỉ-đọc (`asset.read` NHƯNG KHÔNG `asset.write`) / Guest / điều dưỡng → **403** (`PermissionError`). User `asset.write` → tiếp tục. **KHÔNG cap mới** — `asset.write` đã có từ A2 (`CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`, KHÔNG churn version). |
> | 2 | **Sinh token MỚI enumeration-safe, KHÁC token cũ** | `new = generate_qr_token()` (`secrets.token_urlsafe(16)`). Loop-guard: nếu `new == old` (xác suất ~0) → sinh lại đến khi khác. **GHI ĐÈ** `qr_token` hiện có: `frappe.db.set_value("AC Asset", name, "qr_token", new, update_modified=False)` (KHÔNG bump `modified` — token là metadata kỹ thuật, không phải sửa nghiệp vụ). Collision-safe với UNIQUE index (catch → sinh lại). |
> | 3 | **Token CŨ KHÔNG còn resolve được** | Sau rotate: `resolve_qr_token(old)` → `None` → endpoint 404; `resolve_qr_token(new)` → asset đúng. Vì lookup qua field `qr_token` (UNIQUE) đã đổi → mọi nhãn/deep-link đã in với token cũ **chết** (đúng mục tiêu: vô hiệu hoá QR lộ). |
> | 4 | **Audit/lifecycle BẮT BUỘC (NĐ98 / CLAUDE.md §5)** | 1 ALE `event_type='qr_regenerated'` + 1 IMM Audit Trail (`event_type='System'`) qua `emit_qr_regenerated`. `change_summary` nêu hành động **rotate / vô hiệu hoá nhãn QR cũ** — **KHÔNG log token thô** (cũ/mới). KHÔNG nuốt lỗi (sự kiện bảo mật). |
> | 5 | **IDOR-safe** | `assert_vendor_can_access("AC Asset", asset)` TRƯỚC khi rotate → vendor KHÔNG rotate được asset ngoài scope → **403**. Đồng nhất leak-safe với `resolve_qr_token` (KHÔNG nới IDOR khi siết RBAC). |
> | 6 | **Asset không tồn tại → 404 leak-safe** | `frappe.db.exists("AC Asset", asset)` False → 404 (`AC-E001`), KHÔNG 500, KHÔNG đoán id. |
> | 7 | **Thứ tự gate (BẮT BUỘC)** | `require("asset.write")` (403) → tồn-tại (404) → `assert_vendor_can_access` (403 IDOR) → rotate + emit + `frappe.db.commit()`. Gate WRITE ĐẦU TIÊN → user chỉ-đọc KHÔNG dò được asset nào tồn tại. |
> | 8 | **Nhãn phản ánh token MỚI** | Sau rotate, `get_asset_label_data(asset)` / `build_asset_label_data` trả `qr_url = get_url("/a/{new}")` — preview/print dùng deep-link mới. (Tự nhiên đúng vì `qr_token` field đã đổi; KHÔNG cần đụng A3.) |
> | 9 | **Response** | `{success:true, data:{name, qr_url}}` — `qr_url` là deep-link MỚI (FE refetch để cập nhật preview/nhãn). KHÔNG trả token thô trong envelope (FE chỉ cần `qr_url`). |

**Quy tắc:**

> **Self-Correction vòng B (2026-06-04) — đổi cổng in nhãn từ `asset.print_label` → `asset.write`:**
> Thiết kế A3/D4 gốc dự kiến **cap MỚI** `asset.print_label` (+ `asset.regenerate_qr`) cho hành-động-ghi. **Bỏ phương án đó**, dùng cap đã có **`asset.write`** vì:
> 1. **KHÔNG churn cap-set version.** `asset.write` đã auto-sinh từ `_DOMAIN_PRIMARY["Asset"]="AC Asset"` (A2). Thêm cap `print_label` mới → đổi `sorted(CAPABILITY_MAP)` → `CAP_SET_VERSION` đổi (v95→v96) → buộc bump FE `auth.ts::CAP_SET_VERSION` + bust toàn bộ `ac_caps::*` lần nữa (lesson IMM-14). Dùng `asset.write` → version GIỮ **`v95.3388ee5629c1`**, FE KHÔNG đổi hằng số.
> 2. **Đúng ngữ nghĩa least-privilege.** In nhãn = ghi `label_printed` event + audit (side-effect bền vững) ⇒ đây là **write** trên registry `AC Asset` theo DocPerm. `asset.read` (chỉ đọc/resolve QR) KHÔNG đủ. `asset.write` resolve qua `frappe.has_permission("AC Asset","write")` — KHÔNG hardcode role-name (chống RBAC dead-gate).
> 3. **Tách read/write rõ ràng:** đọc-only (`resolve_qr_token`, `get_asset_scan_info`, `get_asset`) giữ `asset.read`; ghi/side-effect (`get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed`) siết `asset.write`. (Lưu ý: `get_asset_label_data[_batch]` GET nhưng có side-effect token-backfill `ensure_asset_qr_token` + là tiền-đề thao-tác-in ⇒ xếp nhóm WRITE — xem 05 §Permission Matrix.)
> 4. **`asset.print_label`/`asset.regenerate_qr` REMOVED khỏi roadmap** — KHÔNG còn cap riêng cho in/regenerate.
- **KHÔNG public-anonymous.** Quét QR → nếu chưa đăng nhập → FE redirect login rồi quay lại `/a/<token>` (deep-link giữ nguyên sau auth qua `query.redirect=to.fullPath`).
- **KHÔNG RBAC dead-gate** (lesson r1-25). **[BE verify 2026-06-04 — GROUND TRUTH, RE-VERIFY A2]:** capability `asset.read` **CHƯA tồn tại** trong `CAPABILITY_MAP` (`services/shared/rbac.py`). `AC Asset` đang ở bucket `_shared` (rbac.py:55 — chỉ phục vụ `DOCTYPE_DOMAIN` grouping, KHÔNG sinh prefix cap); `_DOMAIN_PRIMARY` (rbac.py:66-74) KHÔNG có khóa `"Asset"` → 0 cap nào bind `("AC Asset", <ptype>)`. Hiện 89 cap, `CAP_SET_VERSION="v89.2df4c16c2bbd"`. → **A2 BẮT BUỘC thêm trước khi gate**, KHÔNG được giả định có sẵn.
  - **Cách thêm (Frappe-first, nhất quán pattern hiện hành):** thêm khóa `"Asset": "AC Asset"` vào `_DOMAIN_PRIMARY` → vòng lặp `for _dom, _dt in _DOMAIN_PRIMARY.items()` (rbac.py:79) tự sinh `asset.read/write/create/delete/submit/cancel` bind `("AC Asset", <ptype>)`. Quyền đọc QR-resolve = `can("asset.read")` → `frappe.has_permission("AC Asset", "read")` theo DocPerm thật (KHÔNG hardcode role-name).
  - **KHÔNG đụng bucket `_shared`:** giữ `"AC Asset"` trong `_DOMAIN_DOCTYPES["_shared"]` (line 55) — đó là 2 vai trò ĐỘC LẬP: `_DOMAIN_DOCTYPES` map DocType→domain-word (cho `DOCTYPE_DOMAIN`), còn `_DOMAIN_PRIMARY` chọn 1 DocType đại diện để auto-sinh cap. Thêm vào `_DOMAIN_PRIMARY` KHÔNG xung đột với `_shared`; chỉ thêm 6 cap mới.
  - **Verify cap tồn tại (chống dead-gate):** `from assetcore.services.shared.rbac import CAPABILITY_MAP; assert "asset.read" in CAPABILITY_MAP` — BẮT BUỘC xanh sau khi thêm domain (acceptance A2).
  - **Hệ quả cache (lesson IMM-14):** thêm 6 cap đổi `sorted(CAPABILITY_MAP)` (89→95 key) → `_compute_cap_set_version()` đổi hash → `CAP_SET_VERSION` mới (vd `v95.<sha>`). `after_migrate` (`assetcore.setup.install.after_migrate`, hooks.py:3 → install.py:132) PHẢI gọi `rbac.invalidate_capabilities()` bust `ac_caps::*` (đã wired install.py:156). FE `auth.ts::CAP_SET_VERSION` hằng số PHẢI bump khớp giá trị BE mới → `isCapCacheStale()` tự bỏ persisted-caps cũ (rỗng `asset.*`) → KHÔNG cần xóa localStorage tay. Nếu KHÔNG bump FE / KHÔNG bust BE → user cũ giữ cap-set rỗng `asset.*` → gate chết âm thầm.
- **IDOR / vendor isolation (A2):** resolve PHẢI tái dùng `assert_vendor_can_access("AC Asset", asset_name)` (`services/shared/scope.py:160`) — KHÔNG re-implement. Vendor Engineer resolve token của asset NGOÀI scope (không được giao PM/CM Work Order) → `ServiceError(FORBIDDEN)` → 403, KHÔNG trả data asset ngoài scope.
- **Enumeration / leak-safe (A2):** token KHÔNG tồn tại → **404** (`AC-E001`), KHÔNG 500, KHÔNG phân biệt "token sai định dạng" vs "không có asset" qua message khác nhau (cùng 404 generic). Tránh leak có/không qua timing rõ rệt (lookup 1 query `frappe.db.get_value`/`exists` — KHÔNG nhánh sớm tốn kém khác biệt). Rate-limit chốt ngưỡng ở vòng B.
- **Audit read-only (A2 — CHỐT):** resolve QR là **read-only lookup** → **KHÔNG ghi audit/lifecycle mỗi lần quét** (tránh spam audit chain — mỗi KTV quét tra cứu tại giường nhiều lần/ngày). Lifecycle event `qr_generated` ghi ở A1 (sinh token), `label_printed` ở A4 (in nhãn) — đó là các sự kiện THAY ĐỔI trạng thái nhãn, ĐÁNG ghi. Resolve KHÔNG đổi gì → KHÔNG audit. (Quyết định self-correction: acceptance A2 nêu "best-effort audit HOẶC ghi nhận quyết định KHÔNG audit" — chọn KHÔNG audit, chốt tại đây.)

---

### D4.1 — No-raw-token parity trên MỌI đường ĐỌC AC Asset (rule 9 mở rộng) — **NEW (Vòng 24 B)**

> **Self-Correction — lỗi thiết kế gốc (root-cause).** D4 rule 9 chốt "KHÔNG trả token thô trong envelope" CHỈ cho `regenerate_asset_qr_token` (đường GHI). D1/D4 lại đặc tả `qr_token` là **khóa tra cứu MỜ** (opaque lookup key) — KHÔNG phải định danh nghiệp vụ, và **enumeration-safe** chỉ có giá trị nếu token KHÔNG rời BE qua bất kỳ đường nào. **BA chưa đặc tả no-raw-token cho đường ĐỌC asset đầy đủ.** Hệ quả thực tế: `get_asset(name)` build payload bằng `frappe.get_doc("AC Asset", name).as_dict()` → trả **NGUYÊN** dict gồm field `qr_token` thô. Bất kỳ user có `asset.read` (gồm vendor trong scope) gọi `get_asset` → đọc token thô của asset → có thể dựng deep-link `/a/<token>` ngoài luồng quét hợp lệ, hoặc lưu/chia sẻ token (lộ ngoài tầm rotate). Vi phạm mục tiêu opaque-key/enumeration-safe của ADR (D1/D2/D4).

**Quyết định (CHỐT B-24):** mọi endpoint ĐỌC AC Asset áp **no-raw-token parity** — token thô KHÔNG BAO GIỜ rời BE qua đường đọc. Deep-link chỉ đi ra dưới dạng `qr_url` **dựng server-side** (qua `build_asset_label_data` / `_build_qr_url` — D2/D2.1), KHÔNG bao giờ là `qr_token` trần.

| # | Endpoint đọc AC Asset | Cơ chế hiện tại | Quy tắc B-24 |
|---|---|---|---|
| 1 | `get_asset(name)` | `frappe.get_doc(...).as_dict()` → **CÓ** `qr_token` thô | **STRIP** `qr_token` khỏi dict sau `as_dict()`, TRƯỚC khi enrich/`_ok`. `data.pop("qr_token", None)`. Mọi field khác GIỮ NGUYÊN (`asset_code`, `lifecycle_status`, `device_model_name`, `location_name`, `category_name`, `supplier_name`, `responsible_technician_name`, HTM fields…). |
| 2 | `get_asset_timeline(name)` | `frappe.get_list("Asset Lifecycle Event", …)` — KHÔNG đọc `AC Asset` | **PARITY tự nhiên** — payload là list event field tường minh, KHÔNG có `qr_token`. KHÔNG đụng code; test khẳng định parity. |
| 3 | `get_asset_kpi(name)` | Build dict KPI tường minh (whitelist field) | **PARITY tự nhiên** — `frappe.get_doc` chỉ để đọc field KPI, payload KHÔNG `as_dict()` → KHÔNG có `qr_token`. KHÔNG đụng code; test khẳng định parity. |
| 4 | `resolve_qr_token`, `get_asset_scan_info`, `get_asset_label_data[_batch]` | Đã build payload whitelist tường minh (A2/A6/A3) | **ĐÃ parity** (rule 9 / A6 "KHÔNG `as_dict()` rồi pop"). KHÔNG đụng. |

**Quy tắc thực thi:**

| # | Quy tắc | Chi tiết |
|---|---|---|
| 1 | **STRIP, KHÔNG re-whitelist** | `get_asset` GIỮ hành vi "trả đầy đủ HTM fields" (FE `AssetDetailView` cần đủ data) — chỉ `pop("qr_token", None)` SAU `as_dict()`. KHÔNG đổi sang whitelist tường minh (tránh rủi ro rớt field khác → FE thiếu data). |
| 2 | **qr_url KHÔNG thay token** | `get_asset` (màn admin `AssetDetail`) **KHÔNG cần** trả `qr_url` — deep-link/in nhãn đã có endpoint riêng `get_asset_label_data` (nút "In nhãn") + `regenerate_asset_qr_token` (nút "Sinh lại QR"). `get_asset` chỉ là chi tiết asset, KHÔNG phải nguồn deep-link. (Nếu vòng sau cần `qr_url` ở `AssetDetail` → dựng qua `_build_qr_url`, KHÔNG lộ token.) |
| 3 | **FE KHÔNG vỡ** | Grep FE `frontend/src/` xác nhận 0 consumer đọc `data.qr_token` từ `get_asset`/timeline/kpi (FE chỉ dùng `qr_url` từ label/regenerate). Strip token → KHÔNG breaking-change FE. |
| 4 | **Guard chống tái phát (Grep/AST)** | Test guard: 0 endpoint trong `assetcore/api/imm00.py` (và mọi `api/*.py`) trả `frappe.get_doc(_DT_ASSET, …).as_dict()` mà KHÔNG `pop("qr_token")`/strip trước khi `_ok`. Phát hiện qua AST (`ast.walk` tìm `.as_dict()` trên `get_doc("AC Asset")` thiếu strip) HOẶC grep-pattern. Chống regress khi thêm endpoint asset-read MỚI. |
| 5 | **RBAC/IDOR/404 GIỮ NGUYÊN** | B-24 CHỈ strip token — KHÔNG đụng gate: `get_asset` giữ `frappe.db.exists` 404 + `assert_vendor_can_access` 403 IDOR. KHÔNG nới/siết quyền. |
| 6 | **KHÔNG schema-delta** | Thuần strip + guard test. KHÔNG cap/field/DocType/enum/patch mới. `CAP_SET_VERSION` GIỮ **`v95.3388ee5629c1`**. `bench migrate` sạch. FE KHÔNG đổi (BE-only). |

**Vì sao token thô KHÔNG cần ở client (kể cả admin):** client cần (a) **hiển thị** asset → field nghiệp vụ (đã có, không gồm token); (b) **deep-link/in nhãn** → `qr_url` dựng server-side. Token thô chỉ là khóa tra cứu nội bộ BE (lookup `frappe.db.get_value("AC Asset", {"qr_token": …})`). Lộ ra client = mở rộng bề mặt tấn công (lưu/chia sẻ/dò token) mà KHÔNG thêm năng lực hợp lệ nào.

---

### D5 — Backfill (migration)

Patch sinh `qr_token` cho **MỌI** asset cũ/import/legacy chưa có token:

| Thuộc tính | Giá trị |
|---|---|
| Patch | `assetcore.patches.v3_2.008_backfill_asset_qr_token` (đăng ký trong `patches.txt`) |
| Logic | `frappe.get_all("AC Asset", {"qr_token": ["in", ["", None]]})` → mỗi asset: `frappe.db.set_value("AC Asset", name, "qr_token", secrets.token_urlsafe(16))` |
| Idempotent | Chạy lại = no-op (chỉ chạm asset `qr_token` rỗng). Re-run an toàn. |
| Collision-safe | Catch UNIQUE violation → sinh lại token (xác suất ~0 nhưng phải guard). |
| Lifecycle | Backfill emit `qr_generated` event/asset (best-effort, KHÔNG vỡ patch nếu audit lỗi). |

---

### D6 — Tương thích ngược (`internal_tag_qr`)

| Quyết định | Chi tiết |
|---|---|
| **GIỮ** field `internal_tag_qr` ở commissioning | Field `Asset Commissioning.internal_tag_qr` KHÔNG bị xoá/đổi. `assign_identification` / `generate_internal_qr` / `get_barcode_lookup` (`services/imm04.py:575,1406,977`) hoạt động NGUYÊN VẸN — KHÔNG breaking change. Field vẫn hiển thị read-only + dùng cho scanner-wedge lookup (`get_barcode_lookup` filter theo `internal_tag_qr`). |
| QR mới (asset-level) **song song** | `qr_token` là cơ chế mới, không thay `internal_tag_qr`. Một asset có thể có cả hai trong giai đoạn chuyển tiếp. |
| **Dedup → 1 deep-link (CHỐT vòng 13/B-3 — D6)** | Xem **§D6.1** dưới — hợp nhất ẢNH QR + contract nhãn của `generate_qr_label` về **deep-link asset `/a/<token>`** (tái dùng `ensure_asset_qr_token` + `_build_qr_url` của IMM-00). Vòng A KHÔNG đụng IMM-04 logic; **vòng 13 đụng DUY NHẤT `generate_qr_label`** (chỉ contract nhãn — KHÔNG đụng field/cap/DocType). |
| Scanner-wedge cũ | `QRScanView.vue` (gõ tay/đầu đọc) GIỮ; A5 thêm camera-scan **song song** (URL `/a/<token>` vs mã thô đều xử lý được). |

#### D6.1 — Dedup `generate_qr_label` → deep-link asset (CHỐT vòng 13 / B-3)

**Vấn đề (RC dedup):** trước vòng 13 tồn tại **2 đường QR quét-được** trên cùng 1 thiết bị:
1. QR cấp commissioning — `generate_qr_label` mã hoá chuỗi tag `internal_tag_qr` (`BV-DEPT-YYYY-SEQ`) + `scan_url = /app/asset-commissioning/<name>` (desk-login ERPNext).
2. QR cấp asset — `/a/<token>` deep-link enumeration-safe (A2/A6).

→ Đường (1) **đoán được** (tag tuần tự) + **trỏ ERPNext desk** (lộ name phiếu tuần tự + yêu cầu desk login, không phải màn info mobile). Vi phạm mục tiêu enumeration-safe của ADR (D1/D2/D4).

**Quyết định:** sau vòng 13, **CHỈ còn 1 đường QR quét-được = deep-link asset `/a/<token>`**. `generate_qr_label` ngừng mã hoá chuỗi tag tuần tự vào ẢNH QR và ngừng phát `scan_url` desk.

| # | Quy tắc | Chi tiết |
|---|---|---|
| 1 | **Thêm field `qr_url` vào response** | Khi phiếu đã có `final_asset` (đã Clinical Release / đã mint asset): `qr_url` = chuỗi tuyệt đối `/a/<token>`, dựng qua **tái dùng** helper IMM-00 — **KHÔNG copy-paste** logic sinh token/URL (1 helper duy nhất — dedup THẬT, không tái hiện CSPRNG/`get_url` trong imm04). **2 cách tái dùng, chọn 1:** (a) `services.imm00.ensure_asset_qr_token(final_asset)` → `services.imm00._build_qr_url(token)` (đúng 2 helper ADR nêu); HOẶC (b) **ưu tiên** gọi 1 entry point public `services.imm00.build_asset_label_data(final_asset)["qr_url"]` (hàm này nội bộ đã gọi `ensure_asset_qr_token`+`_build_qr_url` — tránh import symbol private `_build_qr_url` cross-module). Cả 2 cho cùng kết quả; (b) gọn hơn + 1 SSoT public. |
| 2 | **Edge: phiếu CHƯA có `final_asset`** | `generate_qr_label` trả `qr_url = null` (None). **KHÔNG** gọi `ensure_asset_qr_token` (không có asset để sinh token), **KHÔNG throw**. Nhãn fallback dùng `commissioning_id` như cũ. Không sinh "asset-less QR rác". |
| 3 | **Thay `scan_url` desk** | Field `scan_url = /app/asset-commissioning/<name>` (desk-login) **ĐƯỢC THAY bằng `qr_url`** (deep-link). **Chốt [BA]: BỎ HẲN field `scan_url`** khỏi contract nhãn — không còn URL desk-login trong response. (FE đọc `qr_url`; mọi nơi đọc `scan_url` đổi sang `qr_url`.) |
| 4 | **`docs_url` GIỮ NGUYÊN** | `docs_url = /documents/asset/<final_asset>` không trong scope vòng này — KHÔNG đụng. |
| 5 | **RBAC GIỮ NGUYÊN** | `generate_qr_label` vẫn gate `frappe.has_permission("Asset Commissioning", "read")` (FORBIDDEN nếu thiếu). `ensure_asset_qr_token` CHỈ set token (idempotent), **KHÔNG nâng quyền** (không gate asset.write — chỉ đọc commissioning + backfill token kỹ thuật). |
| 6 | **Lifecycle: KHÔNG double-emit** | `ensure_asset_qr_token` idempotent: asset đã có token (đã emit `qr_generated` ở A1/backfill) → NO-OP, KHÔNG emit lần 2. Asset token-less hiếm (mọi asset mint ở `create_ac_asset` có token qua `before_insert`/backfill) → nếu rỗng, ensure sinh + emit `qr_generated` 1 lần (đúng nghiệp vụ — token đầu tiên). `generate_qr_label` **KHÔNG tự emit event mới** (không `label_printed` — đó là `mark_label_printed` POST; `generate_qr_label` là GET preview). |
| 7 | **ẢNH QR mã hoá `qr_url`, KHÔNG tag** | Sau vòng 13, ảnh QR trên nhãn commissioning (FE) mã hoá `res.qr_url` (deep-link) khi có; fallback `res.qr_value` (tag cũ) CHỈ khi `qr_url` rỗng (phiếu chưa có asset). Quét điện thoại trên phiếu đã release → mở thẳng `AssetScanInfo` (A6), KHÔNG ra chuỗi text thô. |

**Cap-set:** GIỮ `v95.3388ee5629c1` — KHÔNG cap mới, KHÔNG field DocType mới, KHÔNG patch mới, KHÔNG enum option mới. `bench migrate` sạch (không schema-delta).

---

## §8 — Roadmap A1→A6 + B (mỗi vòng đúng 1 đề mục đóng kín)

| Vòng | Mã | Đề mục | Phạm vi chốt |
|---|---|---|---|
| V2 | **A1** | BE: field `qr_token` + sinh idempotent (3-tier) + `before_insert` + migration backfill | IMM-00 schema-delta + patch (D1, D5) |
| V3 | **A2** | BE+FE: route `/a/<token>` + endpoint `resolve_qr_token` (RBAC `asset.read`, rate-limit) | D2, D4 (resolve) |
| V4 | **A3** | BE: `get_asset_label_data`(1+batch) READ-ONLY + `mark_label_printed` POST emit `label_printed`+audit (IMM-00) | D3 (spec chốt — chờ scaffold/test) |
| V5 | **A4** | FE: in label theo asset (1 + HÀNG LOẠT, print CSS A4/khổ tem), `QRLabel` encode URL `/a/<token>`, preview+print | D2, D3 (`label_printed`) |
| V6 | **A5** | FE: camera scan (getUserMedia) + xử lý URL vs mã thô + fallback nhập tay. **A5+(B) (✅):** thêm decode-fallback **jsQR** (lazy dynamic import) trong `useQrCameraScanner` khi trình duyệt thiếu `BarcodeDetector` (iOS Safari / Firefox) → `isSupported()` true khi có camera API; nhánh fallback grab frame qua `<canvas>` ẩn + throttle ~250ms (KHÔNG rAF mỗi frame); native BarcodeDetector GIỮ NGUYÊN (KHÔNG load jsQR); stop-on-first-hit + no camera-leak ở cả 2 nhánh; KHÔNG cap/field/DocType mới, `CAP_SET_VERSION` GIỮ nguyên. | D6 (song song scanner-wedge) |
| V7 | **A6** | BE: endpoint `get_asset_scan_info(token\|name)` (payload mobile cốt lõi + bảo trì gần nhất + nhãn VI SSoT, no-audit, no-N+1) + SSoT `services/shared/labels.py`. FE: route+view `AssetScanInfo` (`/assets/:id/info`) mobile-first read-only; `QrResolveView` đổi đích redirect (Self-Correction A2). Tái dùng `asset.read` — KHÔNG cap/field/DocType mới | D2, D4 (màn info) |
| V8+ | **B** | Hardening (nhiều item, mỗi vòng 1 đề mục) — xem bảng con dưới | D4, D6 |

**B — bảng con (mỗi vòng đúng 1 item, TDD, KHÔNG cap mới trừ khi nêu rõ):**

| Item | Đề mục | Phạm vi chốt | Trạng thái |
|---|---|---|---|
| B-1 | **RBAC siết in nhãn `asset.read`→`asset.write`** (least-privilege, KHÔNG cap mới, KHÔNG đổi `CAP_SET_VERSION`) | D4 | ✅ DONE (Vòng 9) |
| **B-2** | **Regenerate (rotate) `qr_token`** — endpoint `regenerate_asset_qr_token` POST gate `asset.write` + IDOR + token mới enumeration-safe overwrite + token cũ chết + ALE `qr_regenerated` + audit (no raw token) + FE nút "Sinh lại mã QR" (BaseModal cảnh báo, KHÔNG `window.confirm`) | D1 (rotate≠ensure), D3 (`qr_regenerated`), D4 (regenerate contract) | **▶️ vòng này (BA doc CHỐT)** |
| **B-3** | **Dedup QR commissioning↔asset → 1 deep-link** (`generate_qr_label` trả `qr_url=/a/<token>` tái dùng `ensure_asset_qr_token`+`_build_qr_url`; bỏ `scan_url` desk + bỏ mã-hoá tag tuần tự vào ảnh QR; edge token-less→`qr_url=null`; FE encode `qr_url` fallback `qr_value`; GIỮ field `internal_tag_qr` + scanner-wedge) | D6 (§D6.1) | **▶️ vòng 13 (BA doc CHỐT)** |
| **B-5** | **Print fidelity (label-stock format)** — FE selector khổ tem (A4 nhiều-nhãn / Tem 50×30 / Tem 70×40mm) ở CẢ 2 đường in (AssetLabelPrintView batch + modal in-1-tem AssetDetailView); SSoT `frontend/src/constants/label.ts::LABEL_FORMATS`; tem vật lý → `@page { size: <mm> }` inject + 1 nhãn/trang khít khổ + QR mm-aware (bỏ 120px cố định để camera quét); A4 = mặc định giữ nguyên lưới 2 cột (regression). **FE-only, KHÔNG cap/field/DocType/route/BE, `CAP_SET_VERSION` GIỮ v95.** | D3 (in nhãn) | **▶️ vòng này (BA doc CHỐT)** |
| **B-6** | **Batch-size cap nhãn QR (payload-DoS)** — hằng SSoT `services/imm00.py::_MAX_LABEL_BATCH=200`; CẢ `get_asset_label_data_batch` + `mark_label_printed` → **413** `_err(<MSG_VI>,413)` khi `len(names)>cap` (SAU `rbac.require("asset.write")`, TRƯỚC `exists`/IDOR; bucket 413 RIÊNG; no-leak asset name). FE guard song song `AssetListView`(selectAll)+`AssetLabelPrintView`(query.names CSV) chặn gửi request chắc-413; URL paste lọt → màn print map 413→bucket VI. KHÁC rate-limit B-1/V12 (req/phút). **KHÔNG cap/field/DocType/patch mới, `CAP_SET_VERSION` GIỮ v95.** | D3 (in nhãn) / D4 (gate order) | **▶️ vòng 22 (BA doc CHỐT)** |
| **B-7** | **Rate-limit endpoint GHI rotate `regenerate_asset_qr_token`** (đóng bất đối xứng read-throttled/write-rotate-unthrottled) — `@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)`, hằng RIÊNG `AC_QR_REGEN_RATE_LIMIT=10` (THẤP hơn resolve=30; rotate hiếm hơn) + bucket RIÊNG (cmd). 429 NGOÀI/TRƯỚC `rbac.require("asset.write")` → 0 side-effect (KHÔNG token mới/ALE/audit), no-leak; thứ tự gate giữ ĐÚNG precedent V12 (429→403→404→IDOR). Happy-path ≤10/60s rotate vẫn 200 `{name,qr_url}` no-raw-token. **Self-Correction:** BR-00-29 mục 6 (V12) miễn rate-limit toàn nhóm GHI gồm rotate → carve-out rotate (3 endpoint in-nhãn GIỮ unthrottled). FE cặp: `httpStatusToCode(429)→RATE_LIMITED` + message VI 'Bạn thao tác quá nhanh…' (modal Sinh-lại GIỮ MỞ). **KHÔNG cap/field/DocType/enum/patch mới, `CAP_SET_VERSION` GIỮ v95.3388ee5629c1.** Spec: IMM-00 02 BR-00-38 + FR-00-87/88, 04 §II.1.8d, 05 §III.1 + §I.7b, 06 §II.3e-RATELIMIT, 07 §III.6.d-ROTATERL/FE429. | D4 (rotate contract) / KHÔNG mâu thuẫn D1–D6 | **▶️ vòng 27 (BA doc CHỐT)** |
| B-4+ | enumeration-safe verify, rate-limit ngưỡng, i18n VI SSoT sweep, a11y, empty/error/loading, N+1 batch | D4 | backlog (N+1 batch ✅ A3, cap ✅ B-6, rotate-RL ✅ B-7) |

**Nguyên tắc:** mỗi vòng TDD (RED trước), KHÔNG lặp đề mục, KHÔNG commit (user review). Vòng A KHÔNG đụng logic IMM-04 commissioning.

---

## Bàn giao [BA] → BE/FE: DocType/field/event/endpoint/route sẽ đụng

| Loại | Tên | Module doc | Thay đổi |
|---|---|---|---|
| Field MỚI | `AC Asset.qr_token` (Data 32, read_only, unique) | IMM-00 §II.1.8 | A1 |
| Enum +2 | `Asset Lifecycle Event.event_type += qr_generated, label_printed` | IMM-00 §II.6 | A1/A3/A4 |
| Enum +1 (**B-2**) | `Asset Lifecycle Event.event_type += qr_regenerated` (schema-delta DUY NHẤT của B-2 — `bench migrate` Select-option add, KHÔNG đổi cột DB, KHÔNG destructive) | IMM-00 §II.6 / §II.1d | **B-2** |
| Endpoint MỚI (**B-2**) | `regenerate_asset_qr_token(asset)` POST → `{name, qr_url}` (rotate `qr_token`: token mới enumeration-safe GHI ĐÈ `update_modified=False`, token cũ→404; gate `require("asset.write")`→403; IDOR `assert_vendor_can_access`→403; 404 token-less asset; emit `qr_regenerated`+audit no-raw-token; `frappe.db.commit()`). **KHÁC `ensure_asset_qr_token`** (idempotent if-empty — KHÔNG overwrite). | IMM-00 §II.1.8d / §05 III.1 | **B-2** |
| Service MỚI (**B-2**) | `regenerate_asset_qr_token(asset_name, actor=None) -> dict` + `emit_qr_regenerated(asset_name, actor=None)` (`services/imm00.py`, cạnh `emit_label_printed`) + hằng `QR_REGENERATED_EVENT = "qr_regenerated"` (cạnh `LABEL_PRINTED_EVENT`) | IMM-00 §II.1.8d | **B-2** |
| Nút FE MỚI (**B-2**) | "Sinh lại mã QR" (`AssetDetailView`) — `v-if="can('asset.write')"`; click → `BaseModal` cảnh báo "thao tác này vô hiệu hoá mọi nhãn QR đã in" (**KHÔNG `window.confirm`**); xác nhận → `regenerateAssetQrToken(id)` → refetch asset + toast VI; huỷ → no-op | IMM-00 §06 II.3e | **B-2** |
| Endpoint MỚI | `resolve_qr_token(token)` → `{name, asset_code, lifecycle_status, device_model_name, location_name}` (RBAC `require("asset.read")` + IDOR `assert_vendor_can_access`; 404 nếu token sai; KHÔNG audit) | IMM-00 §05 III.1 | A2 |
| Endpoint MỚI | `get_asset_label_data(asset)` / `get_asset_label_data_batch(assets)` (GET, READ-ONLY về print event, KHÔNG emit) + `mark_label_printed(assets)` (POST, emit `label_printed`+audit) — **đặt ở IMM-00** `api/imm00.py` | IMM-00 §II.1.8b / §05 III.1 | A3 |
| RBAC SIẾT (vòng B) | 3 endpoint trên đổi gate `require("asset.read")` → **`require("asset.write")`** (least-privilege; read-only `resolve_qr_token`/`get_asset_scan_info`/`get_asset` GIỮ `asset.read`; IDOR `assert_vendor_can_access` GIỮ NGUYÊN — siết RBAC KHÔNG nới IDOR) | IMM-00 §05 III.1 / §Permission Matrix | **B** |
| Endpoint MỚI | `get_asset_scan_info(token\|name)` → payload mobile cốt lõi (`name, asset_code, asset_name, device_model_name, location_name, lifecycle_status, lifecycle_status_label, last_maintenance{event_type,event_type_label,date}, next_pm_date`); RBAC `require("asset.read")` + IDOR `assert_vendor_can_access`; 404 leak-safe; **NO-AUDIT**, **NO-N+1** (ALE `ORDER BY timestamp DESC LIMIT 1` + `next_pm_date` denorm); KHÔNG trả field nhạy cảm | IMM-00 §II.1.8c / §05 III.1 | **A6** |
| File MỚI | `services/shared/labels.py` — SSoT nhãn VI (`LIFECYCLE_STATUS_LABEL_VI`, `LIFECYCLE_EVENT_LABEL_VI` + getter), chống leak mã EN | IMM-00 §III.1c-6 | **A6** |
| Route FE MỚI | `/a/:token` (deep-link resolve) | IMM-00/IMM-04 §06 | A2 |
| Route FE MỚI | `/assets/:id/info` name `AssetScanInfo` (`AssetScanInfoView.vue` mobile-first read-only, gate `asset.read`) | IMM-00 §06 II.3c | **A6** |
| Đổi FE (Self-Correction) | `QrResolveView.vue` redirect `AssetDetail` → `AssetScanInfo` (regression test chứng minh KHÔNG còn landing `AssetDetail`) | IMM-00 §06 II.3b | **A6** |
| Patch MỚI | `v3_2.008_backfill_asset_qr_token` | IMM-00 §Migration | A1 |
| Capability | `asset.{read,write,create,delete,submit,cancel}` (**A2: thêm `"Asset":"AC Asset"` vào `_DOMAIN_PRIMARY` → auto-sinh 6 cap; 89→95 key → `CAP_SET_VERSION="v95.3388ee5629c1"` → bump FE `auth.ts` hằng số + `after_migrate` bust `ac_caps::*`**). **Vòng B: dùng `asset.write` (đã có) cho in nhãn — KHÔNG thêm cap mới, version GIỮ v95. `asset.print_label`/`asset.regenerate_qr` ĐÃ BỎ khỏi roadmap.** | IMM-00 §III.1c RBAC | A2/B |
| Route FE gate | `/a/:token` + `/assets/:id` `meta.requiredCapabilities:['asset.read']` (read-only, giữ); **`AssetLabelPrint` (`/assets/labels/print`) đổi `['asset.read']` → `['asset.write']` (vòng B)** | IMM-00 §06 II.3/II.4 | A2/B |
| Nút FE gate (vòng B) | "In nhãn QR" (`AssetDetailView`) đổi `can('asset.read')` → `can('asset.write')`; "In nhãn hàng loạt" (`AssetListView`) **thêm** `v-if="can('asset.write')"` (hiện chưa gate cap) | IMM-00 §06 | **B** |
| **Đổi BE (vòng 13 / B-3)** | `services.imm04.generate_qr_label` — **+field `qr_url`** (deep-link `/a/<token>` khi có `final_asset`, else `null`) tái dùng `imm00.ensure_asset_qr_token`+`_build_qr_url`; **BỎ field `scan_url`** (desk-login); ảnh QR FE encode `qr_url`. Field `internal_tag_qr` + `assign_identification`/`generate_internal_qr`/`get_barcode_lookup` (scanner-wedge) GIỮ NGUYÊN. KHÔNG emit event mới (ensure idempotent). | IMM-04 §05 §13 / §8.1 D6.1 | **B-3** |
| Đổi FE (vòng 13 / B-3) | `QRLabel.vue` (commissioning) encode QR từ `res.qr_url` khi có; fallback `res.qr_value` (tag) chỉ khi `qr_url` rỗng. Type `QrLabelData`: `+qr_url?: string\|null`, `−scan_url`. | IMM-04 §06 | **B-3** |
| Helper sẵn có (tái dùng — KHÔNG copy) | `services.imm00.ensure_asset_qr_token(asset)` (idempotent set token + emit `qr_generated` lần đầu), `services.imm00._build_qr_url(token)` (`get_url("/a/{token}")`) | IMM-00 §II.1.8 | B-3 |
| Helper sẵn có | `create_lifecycle_event`, `log_audit_event`, `frappe.utils.get_url` | — | dùng trực tiếp |

---

## Tham chiếu

- IMM-00 schema: [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8, §II.6
- IMM-04 backend: [`./04_Backend_Design.md`](./04_Backend_Design.md) §8.1
- Lifecycle helper: `assetcore/utils/lifecycle.py:72` (`create_lifecycle_event`)
- RBAC: `assetcore/services/shared/rbac.py` (`CAPABILITY_MAP`)
- Compat: `assetcore/services/imm04.py:575,1052` (`internal_tag_qr`)
