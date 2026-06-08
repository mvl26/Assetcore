# ADR-IMM00-QR-SCAN-ACTION — Affordance model + capability-gate `available_actions` + deep-link contract + QR-gen coverage + label spec + quyền print/rotate

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([R1-GATE] — factory QR-SCAN-ACTION, Vòng 1 PHÂN TÍCH). **D6 = EXECUTED (Vòng 3, 2026-06-08)** — đã thực thi phương án B trong code+test (xem §D6). |
| Ngày | 2026-06-08 |
| Phạm vi | IMM-00 (registry — màn quét QR `AssetScanInfoView`) → chạm IMM-08/09/11/12 (action create) + import + IMM-04/05 (registration) |
| Owner | BA Lead + System Architect |
| Liên quan | `./ADR-IMM00-ASSETCODE.md` (asset_code=PK) + `../imm-04/ADR-001-asset-qr.md` (QR token, deep-link `/a/<token>`, RBAC read/write) |
| Supersedes | Không — **bổ sung** action surface cho màn quét (ADR-001 chốt resolve/scan-info/label read-only; ADR này chốt CTA hành động + gate) |

> ADR này là **quyết định cuối** cho action surface trên màn quét QR + contract `available_actions` BE↔FE + deep-link truyền asset. Mọi spec `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md` và task BE/FE/QA Vòng 2+ phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** đây là gate PHÂN TÍCH — Vòng 1 **KHÔNG đụng code** (`.py`/`.vue`/`.ts`). Chỉ chốt affordance + contract + spec để Vòng 2+ thực thi mà KHÔNG phải hỏi lại. Mỗi quyết định D1–D6 **đo được**; mỗi task xuống dòng map tới đúng 1 quyết định.

---

## Bối cảnh (vì sao cần GATE này)

Màn quét QR `AssetScanInfoView` hiện CHỈ là read-only (định danh + lifecycle + bảo trì gần nhất + next_pm/calibration + cờ overdue server-side). KTV cầm điện thoại quét tem dán trên máy → thấy thông tin nhưng **KHÔNG có lối hành động** (báo hỏng / yêu cầu PM / yêu cầu CM / hiệu chuẩn) ngay tại điểm quét. Đây là use-case lõi của QR tại hiện trường (point-of-care).

**Nguy cơ nếu KHÔNG chốt:**
- (a) FE render nút hành động **literal mỗi action** (hardcode route + điều kiện inline) → drift gate, nút chết, leo quyền.
- (b) Deep-link truyền **raw `qr_token`** sang form action → token (định danh phụ, rotate được) lọt URL action + lịch sử trình duyệt → rò rỉ + form khoá sai field.
- (c) Gate bằng **role-name** (anti-pattern RBAC dead-gate) → nút chết âm thầm khi đổi role.
- (d) Cho tạo WO/Incident trên asset **đã thanh lý** (Decommissioned) → record rác, vỡ lifecycle.
- (e) CM gate ở route (`repair.write`) ≠ gate ở service (`repair.create`) → user thấy nút (FE cap-check 1 nơi) nhưng BE 403 ở nơi khác → trải nghiệm gãy.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting (IMM-00 foundation) — điểm vào action ở **Maintenance** (báo hỏng→Corrective IMM-12, PM IMM-08, CM IMM-09, Calibration IMM-11). Quét tem phát sinh ở Operation/Maintenance.
2. **NĐ98:** Truy xuất nguồn gốc + báo cáo sự cố (Article 67 — incident reporting). Action từ điểm quét phải gắn đúng asset (NAME, không phải token) để audit trail liên tục. Nhãn QR phục vụ định danh tại hiện trường (UDI/serial Article — truy xuất nguồn gốc).
3. **Stakeholder:** KTV TBYT (quét → báo hỏng/yêu cầu WO), QL phòng vật tư (in/cấp tem), người vận hành lâm sàng (báo hỏng). Action gate theo capability của từng persona.
4. **Lifecycle event:** action KHÔNG phát sinh event mới ở IMM-00 — chỉ **điều hướng** sang form tạo WO/Incident của module đích (module đó tự ghi event). Quét = read-only (KHÔNG audit, đồng nhất ADR-001).
5. **Hậu quả nếu data sai:** token lọt URL action → rò rỉ định danh phụ + đứt liên kết khi rotate; cho action trên asset thanh lý → record rác phá lifecycle; gate sai → leo quyền (user không-quyền tạo được WO) hoặc nút chết (user-có-quyền bị chặn).

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| F1 | `build_asset_scan_info()` trả payload read-only: name, asset_code, asset_name, lifecycle_status (mã canonical), device_model_name, location_name, next_pm_date, next_calibration_date, recent_maintenance, **pm_overdue**, **calibration_overdue**. **KHÔNG có `available_actions`.** | `services/imm00.py:407-464` |
| F2 | `get_asset_scan_info(token, name)` gate `rbac.require("asset.read")` + `assert_vendor_can_access` + rate_limit 30/60s; resolve token HOẶC name → 404 no-leak. Read-only (KHÔNG audit). | `api/imm00.py:332-380` |
| F3 | `AssetScanInfoView.vue` hiện **KHÔNG có nút hành động nào** (báo hỏng/PM/CM/calibration) — chỉ card thông tin + "Quét lại" + "Về trang chủ". | `AssetScanInfoView.vue` (grep action routes = 0) |
| F4 | **Capability tồn tại trong `CAPABILITY_MAP`** (sinh từ `_DOMAIN_PRIMARY × _PTYPES`): `corrective.create`→(Incident Report, create); `pm.create`→(PM Work Order, create); `repair.create`→(Asset Repair, create); `calibration.create`→(IMM Asset Calibration, create). Cũng có `.write` cho cả 4. | `rbac.py:66-91` |
| F5 | **Service-tier create gate:** tạo CM (`create_repair`) gate **`repair.create`**; báo hỏng (incident) gate **`corrective.create`**. (PM/calibration create gate `.create` theo cùng pattern domain.) | `api/imm09.py:40` |
| F6 | **Route-guard cap (FE) hiện tại — MISMATCH với svc:** `IncidentCreate` `/incidents/new` → `corrective.create` (KHỚP svc); `PMWorkOrderCreate` `/pm/work-orders/new` → **`pm.write`** (svc `pm.create`); `CMCreate` `/cm/create` → **`repair.write`** (svc `repair.create`); `CalibrationCreate` `/calibration/new` → **`calibration.write`** (svc `calibration.create`). 3/4 route gate `.write`, svc gate `.create`. | `router/index.ts:307-310,341-344,414-417,447-450`; `api/imm09.py:40` |
| F7 | **`available_actions` KHÔNG tồn tại** ở bất kỳ đâu (BE/FE/docs) — contract greenfield. | grep `available_actions` toàn repo = 0 |
| F8 | **Deep-link `?asset=<name>` ĐÃ wire PARTIAL (đính chính — verified at source 2026-06-08 [FE]):** **3/4 create view ĐÃ đọc `route.query.asset` → prefill** (IncidentCreate `form.asset`=`route.query.asset` `IncidentCreateView.vue:13,29-30`; CMCreate `form.asset_ref`=`route.query.asset` `CMCreateView.vue:40,84`; CalibrationCreate `form.asset`=`route.query.asset` `CalibrationCreateView.vue:40`). **CHỈ `PMWorkOrderCreateView` THIẾU** — import `useRouter` (KHÔNG `useRoute`), `form.asset_ref` init `''`, asset chọn qua SmartSelect, KHÔNG đọc query (`PMWorkOrderCreateView.vue:4,36,40,183`). **3 gap PHỤ (cả 4 view):** (a) prefill nhưng **KHÔNG khoá** field asset (vẫn sửa được — không có `:disabled` theo nguồn query); (b) **`source=qr-scan` KHÔNG được đọc ở bất kỳ view nào** (grep `source` = chỉ `source_pm_wo` CM-nội-bộ, KHÔNG phải cờ nguồn qr-scan); (c) tên field nội bộ KHÁC nhau (`asset` ở Incident/Cal vs `asset_ref` ở PM/CM) — query param `asset` map sang field khác nhau. | grep `route.query.asset` 4 view = 3 (PM thiếu); grep `qr-scan` 4 view = 0 |
| F18 | **i18n VI SSoT cho nhãn 4 action = greenfield (FE):** `labels.ts` CHƯA có nhãn `Báo hỏng`/`Yêu cầu bảo trì`/`Yêu cầu sửa chữa`; CHỈ `'Calibration': 'Hiệu chuẩn'` (STATUS map, không phải action-label SSoT). Vòng 2+ FE PHẢI thêm 1 map SSoT `SCAN_ACTION_LABELS` (key→VI) — KHÔNG hardcode nhãn trong .vue. | `labels.ts:428` (chỉ Calibration); grep `Báo hỏng`/`Yêu cầu` labels.ts = 0 |
| F19 | **`AssetScanInfoView` phần info read-only đã đúng** — chỉ 2 nút `Quét lại mã QR` + `Về trang chủ` (comment `:255` "read-only: chỉ Quét lại + Về trang chủ"); KHÔNG card/field nào editable; KHÔNG `available_actions` render. Vòng 2+ thêm action surface PHẢI GIỮ phần info read-only (chỉ thêm cụm nút, không sửa info → editable). | `AssetScanInfoView.vue:153-154,255-258` |
| F9 | **QR-gen ở model layer:** `ac_asset.py::before_insert → _ensure_qr_token` sinh token KHI trống (idempotent — `if self.qr_token: return`, KHÔNG clobber); `after_insert` emit `qr_generated` đúng 1 lần (cờ `qr_token_just_generated`). | `ac_asset.py:50,63,65-94` |
| F10 | **Import dùng Document API:** `import_data.py` `frappe.new_doc(...).update(...).insert()` ⇒ FIRE `before_insert` ⇒ token tự sinh. KHÔNG cần code QR riêng cho import. | `import_data.py:348-350` |
| F11 | **Backfill legacy idempotent đã có:** `ensure_asset_qr_token(asset)` (service) đọc token hiện hữu → no-op nếu có, sinh + emit nếu thiếu. Dùng được làm 1-shot backfill asset legacy thiếu token. | `services/imm00.py:217-247` |
| F12 | **`build_asset_label_data()` trả 6 field:** name, asset_code, device_model_name, location_name, lifecycle_status, qr_url. **THIẾU `manufacturer_sn` + `asset_name`** (theo AC-5 cần 5 field hiển thị: QR + model + serial + tên + mã). | `services/imm00.py:563-594` |
| F13 | **`_build_qr_url` ĐÃ wire `frappe.conf.assetcore_qr_base_url`** (host công khai) → fallback `get_url` — validate scheme/netloc, reject path/query, log-1-lần. (AC-4 mục "(tuỳ)" đã DONE ở BE.) | `services/imm00.py:500-560` |
| F14 | **[EXECUTED Vòng 3 — D6]** In nhãn gate **`asset.print`**: `get_asset_label_data` (:429) + `get_asset_label_data_batch` (:456) + `mark_label_printed` (:493) require `asset.print`. **Rotate** (`regenerate_asset_qr_token` :554) gate **`asset.qr.rotate`** + rate-limit 10/60s. *(Trước Vòng 3 cả 4 đều `asset.write` — nay đã tách.)* | `api/imm00.py:429,456,493,554`; rbac.py CAPABILITY_MAP |
| F15 | **[RESOLVED Vòng 3 — D6]** `asset.write` thực tế chỉ Super Admin có → trước đây KTV/QL vật tư KHÔNG in/rotate được (self-correction P2). **Đã sửa:** in nhãn gate `asset.print` (print=1 sẵn cho mọi role) → persona vận hành **in được**; rotate gate `asset.qr.rotate` (=write, chỉ Super Admin/được-cấp) — least-privilege chính xác. | DocPerm matrix §D6 (verified 2026-06-08) |
| F16 | **Lifecycle status canonical = 7 mã** (Draft + Commissioned + Active + Under Maintenance + Under Repair + Calibrating + Out of Service + Decommissioned). `BLOCKED_FOR_WO = (Out of Service, Decommissioned)` là SSoT cho overdue-exempt + WO-block. `OPERATIONAL = (Commissioned, Active)`. | `constants.py:85-99` |
| F17 | `_strip_qr_token(doc)` xoá `qr_token` khỏi MỌI payload đọc AC Asset (no-raw-token parity) — deep-link dựng server-side qua `_build_qr_url`. | `api/imm00.py:85-97,284` |

---

## Quyết định (6 quyết định — DỨT KHOÁT, mỗi quyết định đo được)

### D1 — AFFORDANCE MODEL: action surface trên màn quét + map 1-1 {label VI, module, route, capability SSoT}

**Quyết định (1 dòng):** màn quét QR phơi **đúng 4 action** (báo hỏng / yêu cầu PM / yêu cầu CM / hiệu chuẩn); mỗi action map **1-1** tới bảng dưới — KHÔNG thêm action ngoài bảng, KHÔNG inline literal route.

| Action (label VI) | IMM module | Route name | Route path | **Capability SSoT (chốt)** | Mismatch ghi nhận |
|---|---|---|---|---|---|
| **Báo hỏng** | IMM-12 Corrective | `IncidentCreate` | `/incidents/new` | **`corrective.create`** | KHỚP route↔svc (F5,F6) |
| **Yêu cầu bảo trì (PM)** | IMM-08 PM | `PMWorkOrderCreate` | `/pm/work-orders/new` | **`pm.create`** | route hiện `pm.write` ≠ svc `pm.create` (F6) → **chốt `pm.create`** |
| **Yêu cầu sửa chữa (CM)** | IMM-09 Repair | `CMCreate` | `/cm/create` | **`repair.create`** | route hiện `repair.write` ≠ svc `repair.create` (F5,F6) → **chốt `repair.create`** |
| **Hiệu chuẩn** | IMM-11 Calibration | `CalibrationCreate` | `/calibration/new` | **`calibration.create`** | route hiện `calibration.write` ≠ svc `calibration.create` (F6) → **chốt `calibration.create`** |

**Chốt 1 capability SSoT cho mỗi action = `<domain>.create`** (lý do: action trên màn quét = **TẠO** WO/Incident, ngữ nghĩa đúng nhất là `.create`; service-tier ĐÃ gate `.create` ở F5; `.create` resolve `frappe.has_permission(DocType, "create")` = đúng quyền tạo record).

**Self-correction (đổi thiết kế gốc — đo được):** route-guard hiện gate `.write` cho 3/4 (PM/CM/Calibration, F6) → **lệch** svc `.create`. Vòng 2+ FE PHẢI đổi `requiredCapabilities` của 3 route này về `<domain>.create` để **route-guard = available_actions = svc** (1 capability/action xuyên 3 tầng). Báo hỏng đã đúng (`corrective.create` cả route lẫn svc) — no-op.

> Đo được: sau Vòng 2+, với mỗi action, 3 giá trị PHẢI bằng nhau: (a) `meta.requiredCapabilities` của route, (b) `key→capability` trong `available_actions` của BE, (c) `rbac.require(...)` ở service create. QA assert tương đẳng.

---

### D2 — CAPABILITY-GATE CONTRACT: shape `available_actions` = capability ∩ lifecycle, derive SERVER-SIDE

**Quyết định (1 dòng):** `get_asset_scan_info` emit field MỚI **`available_actions: list[dict]`**, mỗi phần tử shape **CHÍNH XÁC**:

```
{
  "key":     str,    # định danh action ổn định: 'report_failure' | 'request_pm' | 'request_cm' | 'request_calibration'
  "label":   str,    # nhãn VI (D1): 'Báo hỏng' | 'Yêu cầu bảo trì' | 'Yêu cầu sửa chữa' | 'Hiệu chuẩn'
  "route":   str,    # route NAME (D3): 'IncidentCreate' | 'PMWorkOrderCreate' | 'CMCreate' | 'CalibrationCreate'
  "enabled": bool,   # = (user CÓ capability) ∩ (lifecycle asset cho phép action) — derive SERVER-SIDE
  "reason":  str     # chuỗi VI khi enabled=false; "" khi enabled=true
}
```

**Quy tắc derive `enabled` (SSoT — 1 predicate chung, KHÔNG inline literal mỗi action):**

```
enabled(action) = has_cap(action.capability) AND lifecycle_allows(lifecycle_status, action.key)
```

- `has_cap` = `rbac.can(action.capability)` (capability SSoT D1, KHÔNG hardcode role).
- `lifecycle_allows` = **1 predicate chung** tra **bảng lifecycle×action TƯỜNG MINH** (dưới) — KHÔNG viết `if status == "..."` rải rác mỗi action.

**Bảng lifecycle × action (TƯỜNG MINH — chốt từng ô):**

| lifecycle_status | Báo hỏng (report_failure) | Yêu cầu PM (request_pm) | Yêu cầu CM (request_cm) | Hiệu chuẩn (request_calibration) |
|---|---|---|---|---|
| **Active** | ✅ | ✅ | ✅ | ✅ |
| **Commissioned** | ✅ | ✅ | ✅ | ✅ |
| **Under Maintenance** | ✅ | ✅ | ✅ | ✅ |
| **Under Repair** | ✅ | ✅ | ✅ | ✅ |
| **Calibrating** | ✅ | ✅ | ✅ | ✅ |
| **Out of Service** | ✅ (cho báo hỏng) | ❌ | ✅ (cho CM — sửa để đưa lại vận hành) | ❌ |
| **Decommissioned** | ❌ | ❌ | ❌ | ❌ (KHÔNG cho tạo BẤT KỲ WO/Incident — đã thanh lý) |
| **Draft** | ❌ | ❌ | ❌ | ❌ (chưa commissioned — registry chưa hoàn tất) |

**Lý do từng nhóm:**
- **Decommissioned** = đã thanh lý (vòng đời kết thúc) → cấm TẤT CẢ action tạo record. `reason = "Thiết bị đã thanh lý"`.
- **Out of Service** = ngừng vận hành tạm nhưng còn trong registry → vẫn cho **báo hỏng** (ghi nhận thêm sự cố) + **CM** (sửa để đưa lại vận hành); **KHÔNG cho PM/calibration** (bảo trì định kỳ/hiệu chuẩn vô nghĩa khi máy đang dừng — đồng nhất `BLOCKED_FOR_WO` exempt overdue F16). `reason = "Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa"`.
- **Draft** = chưa commissioned → registry chưa hoàn tất, không vận hành → cấm action. `reason = "Thiết bị chưa đưa vào vận hành"`.
- **Operational + downtime đang-xử-lý** (Active/Commissioned/Under Maintenance/Under Repair/Calibrating) = full 4 action.

**Quy tắc `reason` (chuỗi VI, chỉ khi `enabled=false`):**
- Thiếu capability → `"Bạn không có quyền thực hiện thao tác này"`.
- Lifecycle chặn → message theo nhóm trên (`"Thiết bị đã thanh lý"` / `"Thiết bị đang ngừng hoạt động …"` / `"Thiết bị chưa đưa vào vận hành"`).
- **Ưu tiên hiển thị:** nếu cả thiếu-cap LẪN lifecycle-chặn → ưu tiên reason **lifecycle** (trạng thái asset là sự thật khách quan, hiển thị trước; thiếu-quyền là thứ cấp). Chốt thứ tự: `lifecycle_reason or capability_reason`.

**KHÔNG render nút chết:** FE render **MỌI** phần tử `available_actions` nhưng nút `enabled=false` ở trạng thái **disabled + tooltip = reason** (KHÔNG ẩn hẳn — để KTV biết "vì sao không bấm được", hỗ trợ self-service). Nút `enabled=false` KHÔNG điều hướng khi click. (Khác RBAC dead-gate: nút disabled CÓ lý do hiển thị, KHÔNG phải nút-không-làm-gì-im-lặng.)

**SSoT 1 predicate (chốt vị trí code Vòng 2+):** định nghĩa **1 hàm** `_scan_action_specs()` (bảng 4 action: key/label/route/capability/lifecycle-rule) + **1 predicate** `_lifecycle_allows(status, key)` đọc bảng trên. `build_asset_scan_info` lặp specs → derive `enabled`+`reason`. KHÔNG literal hoá điều kiện ở mỗi action.

> Đo được: QA mock từng `lifecycle_status` × từng capability-set → assert `available_actions` đúng bảng (enabled + reason). Vd Decommissioned + đủ-quyền → 4 phần tử enabled=false reason="Thiết bị đã thanh lý"; Out of Service + đủ-quyền → report_failure/request_cm enabled=true, request_pm/request_calibration enabled=false.

---

### D3 — DEEP-LINK CONTRACT: route truyền `?asset=<name>` — TUYỆT ĐỐI KHÔNG raw `qr_token`

**Quyết định (1 dòng):** mỗi action route = `/<flow>/new?asset=<name>` truyền **asset NAME** (= `asset_code`, vì invariant `asset_code == name` — ADR-ASSETCODE D5); **TUYỆT ĐỐI KHÔNG** truyền `qr_token` thô trong URL hành động.

**Chốt rõ:**
- **Field truyền:** query param **`asset`** = giá trị `name` của AC Asset (đã có trong payload scan-info F1; cũng = `asset_code` do invariant). KHÔNG truyền token (token là định danh phụ, rotate được, đã bị `_strip_qr_token` xoá khỏi mọi payload đọc — F17).
- **Nguồn (audit):** thêm param phụ **`source=qr-scan`** (hằng) để FE đánh dấu nguồn → form create biết "asset đến từ quét QR" để (a) **khoá field asset** (read-only, không cho đổi — tránh tạo nhầm asset khác), (b) ghi nhận nguồn vào audit của record tạo ra (module đích tự xử l. IMM-00 KHÔNG ghi event).
- **URL mẫu:** `/incidents/new?asset=TS-2025-USG-001&source=qr-scan`. Token KHÔNG bao giờ xuất hiện trong URL action (chỉ ở deep-link landing `/a/<token>` → resolve nội bộ → điều hướng `/scan/:token` hoặc `/assets/:id/info`, ADR-001).
- **`available_actions.route`** trả route **NAME** (D2); FE tự dựng URL = `router.resolve({ name, query: { asset, source: 'qr-scan' } })` → KHÔNG để BE ghép query-string (tránh BE biết cấu trúc URL FE).

**Ràng buộc FE (Vòng 2+) — delta CHÍNH XÁC PER-VIEW (đính chính F8 — verified at source [FE] 2026-06-08):**

| Create view | Đọc `?asset`? | Field nội bộ | Delta Vòng 2+ |
|---|---|---|---|
| `IncidentCreateView` | ✅ ĐÃ đọc (`:13,29-30`) → prefill `form.asset` | `asset` | **THÊM khoá** field khi `source==='qr-scan'` + đọc cờ nguồn. (prefill: no-op) |
| `CMCreateView` | ✅ ĐÃ đọc (`:40,84`) → prefill `form.asset_ref` | `asset_ref` | **THÊM khoá** field khi `source==='qr-scan'` + đọc cờ nguồn. (prefill: no-op) |
| `CalibrationCreateView` | ✅ ĐÃ đọc (`:40`) → prefill `form.asset` | `asset` | **THÊM khoá** field khi `source==='qr-scan'` + đọc cờ nguồn. (prefill: no-op) |
| `PMWorkOrderCreateView` | ❌ **THIẾU** (`:4,36,40` — `useRouter` only) | `asset_ref` | **THÊM** `useRoute` + đọc `route.query.asset`→prefill `form.asset_ref` + **khoá** + cờ nguồn. (gap LỚN — wire mới) |

- **Gap chính (FE-gate chốt):** chỉ **`PMWorkOrderCreateView`** chưa đọc `?asset` (3 view kia ĐÃ có). Vòng 2+ FE thêm prefill+khoá cho PM theo mẫu 3 view kia.
- **Gap phụ (cả 4 view):** (a) hiện prefill nhưng **KHÔNG khoá** asset field → Vòng 2+ thêm `:disabled` (hoặc render read-only) khi `source==='qr-scan'` (tránh đổi nhầm asset sau khi từ quét QR vào); (b) **`source=qr-scan` chưa đọc ở bất kỳ view nào** (F8) → thêm `const fromQrScan = route.query.source === 'qr-scan'` làm cờ điều kiện khoá + đánh dấu nguồn audit.
- **Lưu ý map field:** query param `asset` (hằng theo D2/D3) → field nội bộ KHÁC nhau (`asset` ở Incident/Cal, `asset_ref` ở PM/CM). FE đọc cùng `route.query.asset` nhưng gán vào field đúng của từng view. KHÔNG đổi tên query param theo view.

> Đo được: grep `qr_token` trong URL action = 0 (parity no-raw-token giữ); grep `route.query.asset` 4 view = 4 (PM được wire); grep `route.query.source` 4 view ≥ cờ-khoá; Playwright bấm nút từ màn quét → URL chứa `?asset=<name>&source=qr-scan`, KHÔNG chứa token; form đích field asset **disabled** + đúng asset.

---

### D4 — QR-GEN COVERAGE: token sinh ở đâu khi import + backfill legacy

**Quyết định (1 dòng):** token sinh ở **model layer** `ac_asset.py::before_insert → _ensure_qr_token` (idempotent, KHÔNG clobber) → fire ở **MỌI đường tạo** (form-create + import `doc.insert` + registration IMM-04/05) ⇒ **KHÔNG cần code QR riêng cho import**.

**Trả lời câu hỏi user "QR sinh ở đâu khi import":**
- Import (`import_data.py`) dùng `frappe.new_doc("AC Asset").update(...).insert()` (F10) → `insert()` chạy `before_insert` (F9) → `_ensure_qr_token()` sinh token nếu trống. **Cùng 1 đường với form-create + registration** (tất cả qua Document API `.insert()`). Không có đường ghi nào bỏ qua `before_insert` (trừ `frappe.db.sql` thô — KHÔNG dùng cho tạo asset).
- Idempotent: `if self.qr_token: return` (F9) → asset đã có token (vd file import có sẵn cột qr_token) KHÔNG bị ghi đè; `after_insert` emit `qr_generated` đúng 1 lần (cờ).

**Chốt GAP (Vòng 2+ thực thi):**
- **(a) Test verify từng path:** QA viết test khẳng định token sinh sau: (1) form-create `create_asset`, (2) import `doc.insert` (qua `import_data`), (3) registration commissioning (IMM-04/05). Test gap hiện tại — chưa có test phủ "import → token tự sinh".
- **(b) Backfill legacy:** asset legacy (tạo trước khi có `qr_token` field, hoặc import data thiếu token) → chạy 1-shot `ensure_asset_qr_token(asset)` (F11, idempotent — no-op nếu đã có) cho toàn bộ asset thiếu token. (Patch backfill `v3_2.008` đã có ở ADR-001 §IV.3a — xác nhận coverage; nếu còn legacy sót → re-run idempotent.) *(Cần khảo sát baseline)* `COUNT(*) AC Asset WHERE qr_token IS NULL OR qr_token = ''` trước khi đóng gap.
- **(c) [DONE — không phải gap nữa] `_build_qr_url` đọc `frappe.conf.assetcore_qr_base_url`:** đã wire ở BE (F13, `services/imm00.py:500-560`). AC-4 mục "(tuỳ)" → **đóng**. Vận hành chỉ cần set site_config key khi go-live (host công khai).

> Đo được: 3 test path (form/import/registration) GREEN; `COUNT qr_token rỗng = 0` sau backfill; `_build_qr_url` với site_config set → URL host công khai (test đã có ở suite QR).

---

### D5 — LABEL SPEC: nhãn = 5 field (QR + model + serial + tên + mã) + khổ tem + loại máy in

**Quyết định (1 dòng):** nhãn QR in **ĐỦ 5 field hiển thị** = **QR** (encode `qr_url` `/a/<token>`) + **Model** + **Số serial NSX** (`manufacturer_sn`) + **Tên tài sản** (`asset_name`) + **Mã tài sản** (`asset_code`).

**Bảng 5 field + nhãn VI nguyên văn:**

| Field nguồn | Nhãn VI in trên tem (nguyên văn) | Trạng thái payload hiện tại |
|---|---|---|
| `qr_url` (encode QR `/a/<token>`) | *(QR code, không nhãn chữ)* | ✅ có (F12) |
| `device_model_name` | **Model** | ✅ có (F12) |
| `manufacturer_sn` | **Số serial NSX** | ❌ **THIẾU** trong `build_asset_label_data` (F12) |
| `asset_name` | **Tên tài sản** | ❌ **THIẾU** trong `build_asset_label_data` (F12) |
| `asset_code` | **Mã tài sản** | ✅ có (F12) |

**Chốt GAP (Vòng 2+ thực thi):** `build_asset_label_data` (+`_batch`) PHẢI thêm 2 field đọc từ AC Asset: **`manufacturer_sn`** + **`asset_name`** (cả 2 đã là field AC Asset — chỉ thêm vào `get_value` columns + dict return). KHÔNG đổi `qr_url`/token. Nhãn VI "Mã tài sản"/"Số serial NSX" đồng nhất ADR-ASSETCODE D4.

**Khổ tem + loại máy in (chốt 3 preset):**

| Preset | Khổ | Loại máy in | Layout | Dùng khi |
|---|---|---|---|---|
| **Tem nhỏ** | **50×30 mm** | Máy in nhãn barcode (nhiệt) | QR trái + 4 dòng chữ phải (mã/tên/model/serial), font ≥7pt | Dán trực tiếp lên thiết bị nhỏ/tay cầm |
| **Tem vừa** | **70×40 mm** | Máy in nhãn barcode (nhiệt) | QR lớn trái + 4 dòng chữ phải, font ≥9pt | Thiết bị lớn, đọc xa hơn |
| **A4 nhiều tem** | **A4 (grid N×M)** | Máy in laser A4 thường | Lưới nhiều tem/trang, `@page size: A4` | In hàng loạt khi nhập kho/import |

- FE `@page size: …mm` đặt theo preset chọn (print-CSS). QR encode `qr_url` (host công khai nếu site_config set — D4c/F13).
- **Defer code sang Vòng 2+ (FE-only):** chọn preset + print-CSS là FE; BE chỉ đảm bảo payload đủ 5 field (gap trên).

> Đo được: `build_asset_label_data` return chứa `manufacturer_sn`+`asset_name` (test assert keys); preview nhãn hiển thị đủ 5 field + QR quét được; 3 preset render đúng `@page size`.

---

### D6 — QUYỀN PRINT / ROTATE cho persona vận hành (self-correction P2 carry) — ✅ EXECUTED (Vòng 3, 2026-06-08)

> **Trạng thái thực thi:** ADR↔code ĐÃ KHỚP. Phương án B đã code + test (BE 254 OK + 53 rbac OK; FE 941 OK). KHÔNG còn lệch "1 bên Accepted 1 bên đã-BỎ" — note stale cũ ở `api/imm00.py` + `test_imm00.py` đã bị thay bằng gate `asset.print`/`asset.qr.rotate` + version mới.

**Quyết định (1 dòng):** **TÁCH capability riêng** cho print/rotate — KHÔNG gate `asset.write` (quá rộng) cũng KHÔNG `asset.read` (quá lỏng): thêm **`asset.print`**→(AC Asset,"print") (in/re-print nhãn) + **`asset.qr.rotate`**→(AC Asset,"write") (sinh lại token); gate theo DocPerm/capability, KHÔNG hardcode role-name.

**Vấn đề (self-correction nguồn — F14/F15):** hiện in nhãn + rotate gate `asset.write`, mà `asset.write` THỰC TẾ chỉ AssetCore Super Admin có → **KTV/QL vật tư (persona vận hành) KHÔNG in/rotate được** (nút ẩn ĐÚNG gate nhưng persona cần dùng lại không dùng được). 2 phương án:

| Phương án | Print | Rotate | Đánh giá |
|---|---|---|---|
| **A — nới về `asset.read`** | `asset.read` | `asset.read` | ❌ quá lỏng: rotate token = thao tác ghi (đổi định danh phụ, vô hiệu tem cũ) — không thể chỉ-đọc; print cũng có side-effect backfill token. |
| **B — TÁCH cap riêng (CHỐT)** | **`asset.print`** | **`asset.qr.rotate`** | ✅ least-privilege chính xác: persona vận hành được cấp `asset.print`(+`asset.qr.rotate` cho QL vật tư) qua DocPerm/Role mà KHÔNG cần `asset.write` (vốn cho sửa toàn asset). |

**Chốt phương án B — thay đổi RBAC ĐÃ THỰC THI (đo được, EXECUTED Vòng 3):**
- **Thêm 2 capability vào `CAPABILITY_MAP`** (`rbac.py` block `.update(...)`): **`asset.print`→(AC Asset,"print")** + **`asset.qr.rotate`→(AC Asset,"write")`**. **Binding ĐÃ CHỐT = lựa chọn (i)** (KHÔNG tạo ptype custom): `print` là permtype DocPerm chuẩn của Frappe (đã có sẵn trên AC Asset); rotate = thao tác GHI ⇒ nhóm `write`. **Grounding verified at source (2026-06-08, `bench --site miyano console`):** DocPerm AC Asset có **`print=1` cho MỌI role** (AssetCore Auditor/System User + 13 `* User` gồm Calibration/Commissioning/Corrective/Inventory/Repair…) → `asset.print` resolve TRUE NGAY cho mọi persona vận hành, **KHÔNG cần đổi DocPerm cho in**; **`write=1` CHỈ `AssetCore Super Admin`** → `asset.qr.rotate` mặc định chỉ Super Admin (QL vật tư cấp thêm write/grant qua DocPerm khi cần rotate).
- **CAP_SET_VERSION ĐÃ ĐỔI: `v95.3388ee5629c1` → `v97.c30c69b8974d`** (97 cap, hash recompute từ `sorted(CAPABILITY_MAP)`). FE `auth.ts::CAP_SET_VERSION` ĐÃ bump khớp → `isCapCacheStale` tự bỏ persisted-caps cũ; `after_migrate→invalidate_capabilities()` (hook `hooks.py:4`) self-heal cache server. **ADR-001 ghi "GIỮ v95.3388ee5629c1" → ADR NÀY supersede** (thêm cap = version PHẢI đổi; cơ chế self-heal đã có).
- **Đổi gate endpoint (`api/imm00.py`) — ĐÃ THỰC THI:** `get_asset_label_data` (:429) + `get_asset_label_data_batch` (:456) + `mark_label_printed` (:493) đổi `asset.write`→**`asset.print`**; `regenerate_asset_qr_token` (:554) đổi `asset.write`→**`asset.qr.rotate`**. KHÔNG đụng rate-limit rotate (10/60s), no-raw-token parity (`_strip_qr_token`), `_MAX_LABEL_BATCH=200` (413), available_actions/label payload (D5 đã DONE).
- **Đổi gate FE (mirror BE, chống dead-button) — ĐÃ THỰC THI:** route `AssetLabelPrint` (`router/index.ts`) `asset.write`→`asset.print`; `AssetListView.vue::canPrintLabel`→`asset.print`; `AssetDetailView.vue` nút "In nhãn QR"→`asset.print`, nút "Sinh lại mã QR"→`asset.qr.rotate`. Nút "Chỉnh sửa" GIỮ `asset.write` (sửa asset ≠ in/rotate).
- **Cấp quyền persona (DocPerm/Role, KHÔNG hardcode role-name trong code):** KTV TBYT + QL vật tư ĐÃ có `asset.print` (print=1 sẵn — không thao tác gì thêm); QL vật tư cần rotate tem hỏng → admin cấp `write` (hoặc Custom DocPerm permtype write) trên AC Asset cho role tương ứng ở `/app` — KHÔNG deploy code. Admin (Super Admin) giữ cả hai (print=1+write=1).

**DocPerm matrix (verified 2026-06-08 — SSoT cho phân quyền D6):**

| Role | read | write | print | → `asset.print` | → `asset.qr.rotate` | Persona |
|---|---|---|---|---|---|---|
| AssetCore Super Admin | 1 | 1 | 1 | ✅ | ✅ | Admin (in + rotate) |
| Repair User / Calibration User / Corrective User / Inventory User / … (mọi `* User`) | 1 | 0 | 1 | ✅ | ❌ | KTV/QL vận hành (in được, KHÔNG rotate) |
| AssetCore Auditor / System User | 1 | 0 | 1 | ✅ | ❌ | Đọc + in |
| (Guest / role không-print) | 0 | 0 | 0 | ❌ | ❌ | 403 cả in lẫn rotate |

> Đo được (ĐÃ XANH): (1) user có DocPerm print AC Asset NHƯNG KHÔNG write → `get_asset_label_data`/`mark_label_printed` = **200** (test `TestLabelWriteCapability.test_label_data_print_user_200` + `test_mark_printed_print_user_200`); (2) user KHÔNG print (Guest) → **403** VI sạch + 0 side-effect (`test_label_data_no_print_user_403` + `test_mark_printed_no_print_user_403_no_side_effect`); (3) user có `asset.qr.rotate` (write) → rotate **200** (`test_regenerate_write_user_200_new_token`); user chỉ print → rotate **403** (`test_regenerate_print_only_user_403`); (4) `CAP_SET_VERSION` = `v97.c30c69b8974d` (≠ v95…, test `test_cap_set_version_changed_after_split_caps`); (5) `grep -rE 'if.*role ?== ' ` quanh 4 endpoint = 0 (không hardcode role — gate thuần capability); (6) IDOR bất biến (`test_label_idor_unchanged_after_print_gate` + `test_regenerate_vendor_out_of_scope_forbidden_no_leak`).

---

### D7 — FE CONTRACT: `AssetScanInfoView` render BE-driven + deep-link + i18n SSoT (gate [FE] — DOC-ONLY)

**Quyết định (1 dòng):** FE màn quét render nút hành động **HOÀN TOÀN từ `available_actions` BE-driven** — FE **KHÔNG** tự tính quyền/lifecycle (BE là SSoT D2); mỗi nút deep-link `?asset=<name>&source=qr-scan` (D3); disabled+reason VI khi `enabled=false`; **GIỮ phần info read-only** (F19); nhãn action i18n VI qua SSoT (F18).

**Contract FE đo được (FE thực thi Vòng 2+, KHÔNG code Vòng 1):**

- **C1 — render thuần BE-driven (KHÔNG tự tính quyền):** `AssetScanInfoView` lặp `info.available_actions` → 1 nút/phần tử. `enabled` quyết định nút bấm được hay không; FE **KHÔNG** đọc `lifecycle_status` hay capability để tự suy ra enabled (tránh drift FE↔BE + leo quyền client-side). Nếu BE chưa trả `available_actions` (payload cũ) → KHÔNG render cụm nút (defensive absent-vs-empty: `available_actions == null` → ẩn cụm; `== []` → ẩn cụm; có phần tử → render). *Đo:* mock payload thiếu key → KHÔNG vỡ; FE không có nhánh `if lifecycle_status === ...` quanh nút action (grep = 0).
- **C2 — disabled + reason VI (KHÔNG nút chết):** `enabled=false` → nút `disabled` + `:title`/tooltip = `reason` + `aria-disabled="true"`; click KHÔNG điều hướng. reason hiển thị nguyên văn BE (đã VI D2) — FE KHÔNG tự dịch/ghép. a11y: cụm reason có `role="status"`/`aria-live="polite"` để screen-reader đọc lý do. *Đo:* Decommissioned → 4 nút disabled, tooltip "Thiết bị đã thanh lý"; thiếu-cap → tooltip "Bạn không có quyền…".
- **C3 — deep-link KHÔNG raw token:** nút enabled → `router.push({ name: action.route, query: { asset: info.name, source: 'qr-scan' } })`. `info.name` (= asset_code, invariant) — **KHÔNG** dùng `token`/`qr_url`. FE KHÔNG ghép query-string thủ công (dùng router object-form). *Đo:* Playwright URL sau click chứa `?asset=<name>&source=qr-scan`, grep `qr_token`/`/a/` trong URL action = 0.
- **C4 — info GIỮ read-only:** cụm nút action là **THÊM MỚI** dưới các card info; KHÔNG biến card định danh/lifecycle/bảo trì thành editable; 2 nút cũ `Quét lại`/`Về trang chủ` GIỮ (F19). *Đo:* không có `<input>`/`v-model` mới ở phần info; chỉ thêm `<button>` action.
- **C5 — i18n VI SSoT (F18):** nhãn nút ưu tiên `action.label` (BE VI). FE thêm `SCAN_ACTION_LABELS` (`labels.ts`) làm SSoT parity (key→VI) cho guard-test + fallback; KHÔNG hardcode 'Báo hỏng'/'Yêu cầu…' rải rác trong .vue. *Đo:* parity test `SCAN_ACTION_LABELS[key] === BE.label` cho 4 key; grep nhãn action hardcode trong .vue = 0.
- **C6 — deep-link nhận phía create-view (gap chính = PM, F8):** 3 view (Incident/CM/Calibration) ĐÃ prefill `?asset` → CHỈ thêm khoá field + cờ `source`; **PMWorkOrderCreateView** wire MỚI (`useRoute`+`route.query.asset`→`form.asset_ref`+khoá). KHÔNG hardcode token. *Đo:* grep `route.query.asset` 4 view = 4; field asset disabled khi `source==='qr-scan'`.

**Self-correction [FE] so ADR draft trước (đính chính F8 — verified at source):** F8 cũ ghi "4 create view KHÔNG đọc `route.query.asset`" = SAI. Thực tế **3/4 ĐÃ đọc** (Incident/CM/Calibration prefill), **CHỈ PM thiếu**. Gap thực = (a) PM wire mới, (b) cả 4 thêm khoá field + cờ `source=qr-scan` (chưa view nào đọc cờ nguồn). Đã sửa F8 + bảng delta per-view ở D3.

> Đo được tổng (FE-gate): sau Vòng 2+, (1) `AssetScanInfoView` render N nút = `len(available_actions)`; (2) nút disabled hiện reason VI; (3) deep-link `?asset=<name>&source=qr-scan` KHÔNG token; (4) phần info vẫn read-only; (5) nhãn action qua SSoT (parity test xanh); (6) 4 create view nhận `?asset` (PM được wire) + khoá field.

---

## Bàn giao Core Doc — task Vòng 2+ map tới đúng 1 quyết định

> Gate code: ADR chốt → Vòng 2+ thực thi. **KHÔNG đụng `.py/.vue/.ts` ở Vòng 1.**

| Task (BE/FE/QA) | Map | Mô tả delta |
|---|---|---|
| **BE-1** | D1/D2 | `build_asset_scan_info` + emit `available_actions` qua `_scan_action_specs()` + `_lifecycle_allows()` (1 predicate SSoT, bảng lifecycle×action D2). 4 phần tử {key,label,route,enabled,reason}. |
| **BE-2** | D5 | `build_asset_label_data`(+`_batch`) thêm `manufacturer_sn`+`asset_name` vào columns + dict return (5 field hiển thị). KHÔNG đổi qr_url/token. |
| **BE-3** ✅ | D6 | **DONE Vòng 3.** Thêm cap `asset.print`→(AC Asset,print) + `asset.qr.rotate`→(AC Asset,write) vào `CAPABILITY_MAP`; đổi 4 gate (`get_asset_label_data[_batch]`/`mark_label_printed`→`asset.print`, `regenerate_asset_qr_token`→`asset.qr.rotate`); CAP_SET_VERSION v95.3388ee5629c1→v97.c30c69b8974d; `after_migrate→invalidate_capabilities()` self-heal. |
| **BE-4** | D4 | (Nếu backfill sót) re-run `ensure_asset_qr_token` 1-shot cho asset legacy thiếu token (idempotent). *(Cần khảo sát)* count qr_token rỗng trước. |
| **FE-1** | D1/D2/F19 | `AssetScanInfoView.vue`: render `available_actions` (BE-driven, KHÔNG tự tính quyền FE) — nút enabled→điều hướng `router.push({name, query:{asset, source:'qr-scan'}})`, disabled+tooltip=`reason` (KHÔNG render nút chết, KHÔNG ẩn). **GIỮ phần info read-only** (F19 — chỉ THÊM cụm nút, KHÔNG biến info thành editable). Nhãn nút lấy từ `available_actions[].label` (BE đã VI) — KHÔNG hardcode nhãn FE; a11y `aria-disabled` + `role=status`/`aria-live` cho reason. |
| **FE-1b** | F18 | `labels.ts`: thêm SSoT `SCAN_ACTION_LABELS` (`report_failure`→'Báo hỏng', `request_pm`→'Yêu cầu bảo trì', `request_cm`→'Yêu cầu sửa chữa', `request_calibration`→'Hiệu chuẩn') làm fallback/parity nếu FE cần map theo `key`; BE đã emit `label` VI (D2) ⇒ FE ưu tiên `label` BE, dùng SSoT làm guard-test parity. KHÔNG hardcode nhãn rải rác .vue. |
| **FE-2** | D1 | `router/index.ts`: đổi `requiredCapabilities` 3 route (PM/CM/Calibration) `.write`→`.create` để route-guard = available_actions = svc (1 cap/action). |
| **FE-3** | D3/F8 | **PM view (gap chính):** `PMWorkOrderCreateView` thêm `useRoute`+đọc `route.query.asset`→prefill `form.asset_ref`+khoá. **3 view kia (Incident/CM/Calibration) ĐÃ prefill** (F8) → CHỈ thêm **khoá** field asset + đọc `route.query.source==='qr-scan'` cờ nguồn (gap phụ). URL dựng qua `router.push/resolve({name, query})` ở FE-1 (KHÔNG token). |
| **FE-4** | D5 | Print preview: layout 5 field + QR; 3 preset khổ tem (50×30/70×40mm/A4-grid) + `@page size`; nhãn VI nguyên văn. |
| **QA-1** | D2 | Test `available_actions` per lifecycle×capability (Decommissioned→4 disabled reason="Thiết bị đã thanh lý"; Out of Service→report/cm enabled, pm/cal disabled; Active+full-cap→4 enabled; thiếu-cap→reason quyền). |
| **QA-2** | D1 | Test tương đẳng 3-tầng: route `meta.requiredCapabilities` == `available_actions[key].capability` == svc `rbac.require` cho cả 4 action. |
| **QA-3** | D3 | Playwright: bấm nút từ màn quét → URL `?asset=<name>&source=qr-scan` (KHÔNG token); form đích field asset khoá + đúng asset. grep qr_token trong URL action = 0. |
| **QA-4** | D4 | Test token tự sinh qua 3 path (form/import/registration); count qr_token rỗng = 0 sau backfill. |
| **QA-5** | D5 | Test `build_asset_label_data` keys ⊇ {manufacturer_sn, asset_name, asset_code, device_model_name, qr_url}; preview render 5 field; QR quét được. |
| **QA-6** ✅ | D6 | **DONE Vòng 3.** `TestLabelWriteCapability`: print-user (write=0)→in 200, no-print→403+0-side-effect; `TestRegenerateQrToken`: print-only→rotate 403, write→rotate 200; version-guard v97.c30c69b8974d; IDOR bất biến. FE: `assetDetailQrPrint/Regenerate/RbacAffordance` + route `asset.print`. |

---

## Tham chiếu chéo

- API scan/label: `assetcore/api/imm00.py::get_asset_scan_info` (332) / `get_asset_label_data[_batch]` (384/414) / `regenerate_asset_qr_token` (485)
- Service: `assetcore/services/imm00.py::build_asset_scan_info` (407) / `build_asset_label_data` (563) / `ensure_asset_qr_token` (217) / `_build_qr_url` (546) / `resolve_qr_token` (277)
- Model QR-gen: `assetcore/assetcore/doctype/ac_asset/ac_asset.py::before_insert/_ensure_qr_token/after_insert` (50-94)
- Import path: `assetcore/api/import_data.py:348-350` (`new_doc().insert()` → before_insert)
- RBAC capability SSoT: `assetcore/services/shared/rbac.py::CAPABILITY_MAP` (66-115) + `AssetStatus` `constants.py:85-99`
- FE routes: `frontend/src/router/index.ts` (IncidentCreate 447 / PMWorkOrderCreate 307 / CMCreate 341 / CalibrationCreate 414)
- FE scan view: `frontend/src/views/asset/AssetScanInfoView.vue`; create views: `views/incident|pm|cm|calibration/*CreateView.vue`
- ADR liên quan: `./ADR-IMM00-ASSETCODE.md` (asset_code=name invariant — deep-link asset=name) + `../imm-04/ADR-001-asset-qr.md` (token, deep-link /a/<token>, RBAC read/write baseline)
- Core Doc: `docs/imm-00/04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`
