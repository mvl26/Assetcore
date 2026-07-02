# 05 — Persona & MVP field-tech (Hành trình end-to-end · MÀN↔API · OFFLINE · QUYỀN per-màn)

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A — Kiến trúc & Feasibility** (vòng 4 / PHASE A · A4 Persona & MVP) |
| Bám quyết định | D-AUTH (OAuth2+refresh) · **D-MVP (field-tech)** · D-STACK (native) — `00-overview.md §2` |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** chốt **persona kỹ thuật viên hiện trường (field-tech / KTV)** + **hành trình end-to-end** (login→quét QR→triage→hành động→phiếu-của-tôi) + bảng **MÀN↔API** (endpoint đã tồn tại, `file:line`) + phân loại **nhu cầu OFFLINE per-màn** (yêu cầu cho Phase E, CHƯA impl) + map **QUYỀN/capability per-màn** bám SSoT `rbac.py`.
> **Bounds (Phase A):** KHÔNG bồi 6 path nghiệp vụ vào OpenAPI (để Phase C — giữ STUB) · KHÔNG đụng FE web · KHÔNG sửa code services/api nghiệp vụ · KHÔNG dựng hệ quyền thứ 2. Tái dùng endpoint, KHÔNG viết lại nghiệp vụ.
> **Verify:** mọi `file:line` đã đối chiếu source thật tại Frappe v15.107.2 (site `miyano`, 2026-06-09). Capability verified runtime: `CAP_SET_VERSION = v97.c30c69b8974d`, `len(CAPABILITY_MAP) = 97`. KHÔNG bịa role/endpoint/cap.

> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`06-push-fcm.md`](./06-push-fcm.md) · [`07-offline-sync.md`](./07-offline-sync.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) · [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

> **Quyết định đặt số (convention `00-overview.md §6`):** doc này dùng số **`05`** (KHÔNG `04`) vì `04-api-contract.md` (A3) đã chiếm `04`. Theo convention chống-trùng-số "Số kế tiếp cấp khi có doc mới", `05` là số kế tiếp khả dụng. Nếu mandate ép tên `04-personas-mvp.md` thì đổi sang `05` vì lý do tránh đụng số `04` đã cấp — ghi rõ tại đây.

---

## 0. Context / Scope / Actor

### 0.1 D-MVP — quyết định nền (in nguyên, KHÔNG re-litigate)

> **MVP nhắm kỹ thuật viên hiện trường (field-tech).** 6 luồng cốt lõi: (1) đăng nhập OAuth2; (2) quét QR → hồ sơ thiết bị; (3) báo hỏng; (4) yêu cầu PM/CM/Hiệu chuẩn; (5) "phiếu của tôi" (list+detail); (6) thông báo đẩy (push — kiến trúc Phase A, impl sau). Tái dùng endpoint nghiệp vụ đã có, permission-aware. KHÔNG mở rộng sang persona quản lý/giám đốc ở MVP. (`00-overview.md §2 D-MVP`)

### 0.2 Scope tài liệu này

| Trong scope (Phase A — đặc tả) | Ngoài scope |
|---|---|
| Persona field-tech: mục tiêu · môi trường · ràng buộc mạng · thiết bị quét | Bồi 6 path nghiệp vụ schema vào OpenAPI (Phase C) |
| Ánh xạ persona↔Role Profile/role THẬT (evidence `rbac.py`/catalog) | Tạo OAuth Client record / set site_config (Phase B — HARD-STOP USER) |
| Hành trình end-to-end ≥5 bước (action↔màn↔endpoint↔cap↔output) | Thiết kế sync engine / conflict policy / device-token (Phase E) |
| Bảng MÀN↔API grounded `file:line` (endpoint đã có) | Sửa code services/api nghiệp vụ · sửa FE web · push (Phase E) |
| Phân loại OFFLINE per-màn (**yêu cầu** cho Phase E) | Impl offline cache / idempotency-key (Phase E) |
| Map QUYỀN/capability per-màn bám SSoT `rbac.py` | Map scope→capability THỰC THI (Phase C cân nhắc — `03-auth §3`) |

### 0.3 WHO HTM / NĐ98 grounding (vì sao field-tech là persona MVP đúng)

5 luồng MVP nằm gọn trong **WHO HTM Stage 5 — Maintenance** (PM/CM/Calibration/Incident) cộng "đọc hồ sơ" (cross-cutting IMM-00 master + IMM-05 registration). Đây là stage có **tần suất thao tác cao nhất tại hiện trường** (trong khoa/phòng, cạnh máy), nên là ứng viên số 1 cho di động. Audit NĐ98 (SHA-256 lifecycle chain `utils/lifecycle.py`) áp dụng nguyên vẹn: bearer→`set_user`→mọi action sinh record đúng actor (`00-overview.md §5`).

---

## 1. Persona — Kỹ thuật viên hiện trường (Field-technician / KTV)

### 1.1 Định nghĩa persona

| Thuộc tính | Mô tả |
|---|---|
| **Tên persona** | Kỹ thuật viên hiện trường (field-tech / KTV) — kỹ sư/kỹ thuật viên TTBYT (trang thiết bị y tế). |
| **Mục tiêu công việc** | Tại chỗ-cạnh-máy: tra cứu hồ sơ thiết bị (định danh/model/risk class/lịch sử/cờ quá hạn), **báo hỏng** ngay khi phát hiện sự cố, **yêu cầu** bảo trì định kỳ (PM) / sửa chữa (CM) / hiệu chuẩn (Cal), và theo dõi **phiếu việc của mình**. KHÔNG làm việc quản lý/duyệt (đó là persona Trưởng xưởng/Trưởng phòng — ngoài MVP). |
| **Môi trường dùng máy** | **Di động trong khoa/phòng bệnh viện** — đứng cạnh thiết bị, một tay cầm điện thoại. KHÔNG ngồi bàn làm việc dùng web SPA. Màn hình nhỏ, thao tác nhanh, ít gõ. |
| **Ràng buộc mạng** | **Mạng chập chờn** — Wi-Fi bệnh viện yếu/chết vùng (tầng hầm CĐHA, phòng chì X-quang), 4G phập phù. ⇒ App PHẢI chịu được mất kết nối tạm: đọc-từ-cache + ghi-an-toàn-khi-có-mạng (chi tiết phân loại OFFLINE §4 — yêu cầu cho Phase E). |
| **Thiết bị quét** | Điện thoại có camera → **quét QR** dán trên thiết bị (tem nhãn QR sinh bởi IMM-00, `D5 label spec` — `00-overview` / STATE). QR payload = URL `<base>/a/<token>`; app native **tự decode QR → parse `token` ra khỏi URL → gọi API** (KHÔNG mở `/a/<token>` vì là SPA-only, không server route — `ADR-MOBILE-001` Consequences + `02-deploy-feasibility §4.2`). |
| **Đầu vào (Input)** | Tài khoản Frappe (bearer-OAuth2 D-AUTH) · ảnh QR quét được · nội dung sự cố/yêu cầu KTV nhập. |
| **Đầu ra (Output)** | Hồ sơ thiết bị xem được · Incident Report (báo hỏng) · PM/CM/Calibration Work Order (yêu cầu) · danh sách phiếu-của-tôi. Mọi action sinh record + lifecycle event (audit NĐ98). |

### 1.2 Ánh xạ persona ↔ Role Profile / role THẬT (KHÔNG bịa role mới)

> **SSoT:** Role Profile (DocType core Frappe) gán bộ role chọn sẵn cho User — `assetcore/setup/role_profile_catalog.py`. Persona là **nhãn FE-only** (`frontend/src/constants/personas.ts`), KHÔNG phải DocType; persona ánh xạ tới **TÊN Role Profile thật**. Mobile KHÔNG tạo role/persona mới — dùng đúng Role Profile đã có.

Persona "field-tech" ↔ Role Profile **"Kỹ thuật viên"** (`role_profile_catalog.py:55-58`):

| Role Profile | Domain roles (catalog) | Role nền |
|---|---|---|
| **"Kỹ thuật viên"** | `PM User` · `Repair User` · `Calibration User` · `Corrective User` | `AssetCore System User` (`BASE_ROLE`, `role_profile_catalog.py:32`) |

**Capability mà persona "Kỹ thuật viên" RESOLVE** (verified runtime DocPerm 2026-06-09 — `frappe.has_permission` qua `rbac.can`, `rbac.py:156-168`):

| Capability | Binding (`CAPABILITY_MAP`, `rbac.py`) | Role cấp (DocPerm) | KTV có? |
|---|---|---|---|
| `asset.read` | `("AC Asset","read")` (auto-gen `rbac.py:88-91`) | mọi `*User` role có `read` trên AC Asset | ✅ |
| `asset.print` | `("AC Asset","print")` (`rbac.py:128`) | mọi `*User` role có `print` trên AC Asset | ✅ |
| `corrective.read` | `("Incident Report","read")` | Corrective User `read` | ✅ |
| `corrective.create` | `("Incident Report","create")` | Corrective User `create` | ✅ |
| `pm.read` | `("PM Work Order","read")` | PM User `read` | ✅ |
| `pm.create` | `("PM Work Order","create")` | PM User `create` | ✅ |
| `repair.read` | `("Asset Repair","read")` | Repair User `read` | ✅ |
| `repair.create` | `("Asset Repair","create")` | Repair User `create` | ✅ |
| `calibration.read` | `("IMM Asset Calibration","read")` | Calibration User `read` | ✅ |
| `calibration.create` | `("IMM Asset Calibration","create")` | Calibration User `create` | ✅ |

⇒ Persona "Kỹ thuật viên" có ĐỦ cap cho cả 5 feature MVP — **không cần cấp thêm quyền nào**. (Verified: DocPerm `Corrective User=read/create`, `PM User=read/create`, `Repair User=read/create`, `Calibration User=read/create` trên doctype tương ứng + `*User=read/print` trên AC Asset.)

### 1.3 Persona đối chiếu read-only (PARITY — KHÔNG vào được báo-hỏng)

> Bám `04-api-contract §4` #5 (`FORBIDDEN`/403) + `03-auth §3.2` (1 SSoT) + V4-GATE báo-hỏng (`ADR-IMM12-REPORT-FAILURE`). MVP nhắm field-tech, NHƯNG cùng bearer→RBAC nên persona read-only (nếu được cấp token Phase B) PHẢI bị chặn nhất quán với gate web đã có.

Persona có **`corrective.read` nhưng KHÔNG `corrective.create`** (read-only trên Incident Report) — verified DocPerm 2026-06-09:

| Persona / Role Profile | Role | DocPerm Incident Report | `corrective.create`? | Báo-hỏng? |
|---|---|---|---|---|
| Giám sát vận hành (qua role **Commissioning Manager**, profile "Trưởng phòng VT-TTBYT") | Commissioning Manager | `read/print` (KHÔNG create) — catalog note `role_profile_catalog.py:42-46` | ❌ | **KHÔNG** (403 VI sạch) |
| Cán bộ QA/Kiểm toán (qua role **AssetCore Auditor**) | AssetCore Auditor | `read/print` (KHÔNG create) | ❌ | **KHÔNG** (403 VI sạch) |

**Parity với gate đã có:** màn "Báo hỏng" gate `corrective.create` ở **cả 3 tầng** (route-guard FE web `router/index.ts:454` → api-tier `imm12.py:55,93-96` `_CAP_REPORT="corrective.create"` qua `rbac.can`+`_err(_MSG_FORBIDDEN,403)` → service create gate). Persona `corrective.read-only` gọi `report_incident` trực tiếp → **403, message VI hằng số "Không có quyền thực hiện hành động này", KHÔNG leak raw cap** (`imm12.py:39,53-55` cố ý dùng `rbac.can` thay `rbac.require` để no-leak). Mobile TÁI DÙNG y nguyên gate này (bearer→set_user→cùng `has_permission`) — KHÔNG nới lỏng, KHÔNG dựng kiểm tra cap thứ 2 ở lớp app.

---

## 2. Hành trình end-to-end field-tech (≥5 bước, phủ đủ 5 feature MVP)

> Mỗi bước: **hành động KTV · màn app · endpoint BE tái dùng (`file:line`) · capability cần · output**. Endpoint = đường RPC `/api/method/<dotted>` (tái dùng nguyên, `ADR-MOBILE-001 (c)`). Bearer-OAuth2 (D-AUTH) gắn mọi request từ bước 2 trở đi.

### Bước 1 — Đăng nhập OAuth2 (feature MVP #1)

- **Hành động KTV:** mở app → "Đăng nhập" → WebView/Custom Tab `/authorize` → login Frappe → app nhận `code` → đổi lấy token.
- **Màn app:** `LoginView` (WebView OAuth) → `Splash/HomeView`.
- **Endpoint BE (tái dùng provider Frappe, KHÔNG code):** `frappe.integrations.oauth2.authorize` (`oauth2.py:75`) → `frappe.integrations.oauth2.get_token` (`oauth2.py:124`). Sequence đầy đủ a→f + PKCE S256 + refresh + revoke: [`03-auth-oauth2.md §1`](./03-auth-oauth2.md).
- **Capability cần:** — (auth flow, chưa tới RBAC capability). Token chỉ cấp cho user có role trong `allowed_roles` OAuth Client (Phase B).
- **Output:** `access_token` (TTL 3600s) + `refresh_token` lưu Keychain/Keystore; bearer sẵn sàng cho mọi request sau.

### Bước 2 — Quét QR → mở hồ sơ thiết bị (feature MVP #2)

- **Hành động KTV:** đứng cạnh máy → quét tem QR → app decode → parse `token` khỏi URL `<base>/a/<token>` → gọi API.
- **Màn app:** `QrScanView` (camera) → `AssetScanInfoView` (thẻ thông tin nhanh + "Thao tác nhanh").
- **Endpoint BE (tái dùng):** `assetcore.api.imm00.resolve_qr_token` (`imm00.py:312`) HOẶC `assetcore.api.imm00.get_asset_scan_info` (`imm00.py:355`) — scan-info trả thẳng hồ sơ + `available_actions` (SSoT, không hardcode) + cờ `pm_overdue`/`calibration_overdue`.
- **Capability cần:** `asset.read`.
- **Output:** hồ sơ thiết bị (tên/model/lifecycle_status/risk_classification/location + cờ quá hạn) + danh sách hành động khả dụng (Báo hỏng / PM / CM / Cal) — mỗi action kèm route + enabled/disabled-reason.

### Bước 2b — Xem chi tiết thiết bị (feature MVP #2, mở rộng)

- **Hành động KTV:** từ màn scan-info hoặc list → "Xem chi tiết".
- **Màn app:** `AssetDetailView`.
- **Endpoint BE (tái dùng):** `assetcore.api.imm00.get_asset` (`imm00.py:271`) — permission-aware, trả label-friendly + cờ overdue SSoT (server-flag, FE KHÔNG so client clock — `memory/overdue_server_flag_ssot.md`).
- **Capability cần:** `asset.read`.
- **Output:** hồ sơ đầy đủ (định danh, model, risk class, lifecycle, location, cờ `pm_overdue`/`calibration_overdue`).

### Bước 2c — Tab lịch sử thiết bị (read-history quartet, feature MVP #2 mở rộng)

- **Hành động KTV:** từ màn hồ sơ thiết bị → chuyển tab "Lịch sử" để xem máy này từng có sự-cố / sửa-chữa / bảo-trì gì.
- **Màn app:** `AssetDetailView` các tab read-only (mới→cũ, ≤`limit`).
- **Endpoint BE (tái dùng, GET read-only, permission-aware — KHÔNG audit):**
  - Tab **"Sự cố"** → `assetcore.api.imm12.get_asset_incident_history` (`getAssetIncidentHistory` — Incident Report).
  - Tab **"Vòng đời"** → `assetcore.api.imm00.get_asset_timeline` (`getAssetTimeline` — Asset Lifecycle Event, trục audit-trail CLAUDE.md §10).
  - Tab **"Lịch sử sửa chữa"** → `assetcore.api.imm09.get_asset_repair_history` (`getAssetRepairHistory` — Asset Repair CM; rows-key `history`/asset-key `asset_ref`, 200 SINGLE-shape).
  - Tab **"Lịch sử bảo trì"** → `assetcore.api.imm08.get_asset_pm_history` (`getAssetPmHistory` — PM Task Log; "PM lần cuối khi nào, Pass/Fail, trễ hạn không, lần PM tới?"). 2 param `asset_ref` (required, no-default) + `limit` (int default 10, minimum 1). 200 = SINGLE `AssetPmHistoryEnvelope` `{success, data:{asset_ref, history[]}}`; `AssetPmHistoryItem` 10 field `{name,pm_work_order,pm_type,completion_date,technician,overall_result,is_late,days_late,next_pm_date,summary}` — `overall_result` enum `[Pass, Pass with Minor Issues, Fail]`, `is_late`/`days_late` integer (KHÔNG boolean), dates string no-`date-time`. ADR-MOBILE-023. **🟢 CONTRACT-ONLY** (endpoint LIVE `imm08.get_asset_pm_history:124` — KHÔNG reload/migrate). **ĐÓNG quartet** device-profile read-history (sự-cố + vòng-đời + CM + PM).
- **Capability cần:** `asset.read` (read-only persona OK — KHÔNG audit, `history[]` rỗng nếu chưa từng PM, KHÔNG 404).
- **Output:** danh sách lịch-sử theo tab (mới→cũ), powering tab "Lịch sử" màn hồ-sơ-thiết-bị flow-2.

### Bước 3 — Triage & Báo hỏng (feature MVP #3)

- **Hành động KTV:** phát hiện sự cố → từ scan-info bấm "Báo hỏng" → form prefill `asset` (khoá, badge "Tạo từ quét QR") → nhập mô tả/mức độ → gửi.
- **Màn app:** `IncidentCreateView` (asset khoá khi `source=qr-scan`, parity FE web `IncidentCreateView.vue`).
- **Endpoint BE (tái dùng):** `assetcore.api.imm12.report_incident` (`imm12.py:71`). Cap-gate api-tier `imm12.py:93-96` (`corrective.create`, no-leak). Service emit lifecycle `incident_reported` + provenance + audit (`services/imm12.py`).
- **Capability cần:** `corrective.create` (read-only persona → 403 VI sạch, §1.3).
- **Output:** Incident Report tạo + lifecycle event `incident_reported` + redirect màn chi tiết phiếu; (downstream IMM-09 CM / IMM-16 CAPA theo nghiệp vụ — ngoài thao tác KTV).

### Bước 4 — Yêu cầu PM / CM / Hiệu chuẩn (feature MVP #4)

> 1 bước hành trình, 3 nhánh action (3 endpoint create riêng — KTV chọn loại). Mỗi nhánh: form prefill `asset` khoá khi `source=qr-scan`.

- **4a — Yêu cầu PM:**
  - Màn: `PMWorkOrderCreateView` · Endpoint: `assetcore.api.imm08.create_pm_work_order` (`imm08.py:91`) · Cap: `pm.create` · Output: PM Work Order.
- **4b — Yêu cầu CM (sửa chữa):**
  - Màn: `CMCreateView` · Endpoint: `assetcore.api.imm09.create_repair_work_order` (`imm09.py:36`) · Cap: `repair.create` · Output: Asset Repair WO.
- **4c — Yêu cầu Hiệu chuẩn:**
  - Màn: `CalibrationCreateView` · Endpoint: `assetcore.api.imm11.create_calibration` (`imm11.py:90`) · Cap: `calibration.create` · Output: IMM Asset Calibration record.
- **Phụ trợ chọn lịch (chỉ-đọc khi tạo PM):** `assetcore.api.imm08.list_pm_schedules` (`imm08.py:122`) — load lịch PM của asset để KTV chọn. Cap: `pm.read`. (Lưu ý dead-end khi 0 lịch — carry FE web BUG-PM-2 STATE; mobile cần lối thoát tương tự.)

### Bước 5 — "Phiếu của tôi" (list + theo dõi) (feature MVP #5)

- **Hành động KTV:** mở tab "Phiếu của tôi" → xem các phiếu mình tạo/được giao (PM/CM/Incident), lọc theo trạng thái, mở chi tiết.
- **Màn app:** `MyWorkOrdersView` (tab/segment: PM · CM · Báo hỏng) → detail tái dùng `get_*` tương ứng.
- **Endpoint BE (tái dùng, permission-aware, scope `reported_by`/`assigned_to`):**
  - PM: `assetcore.api.imm08.list_pm_work_orders` (`imm08.py:28`) · Cap: `pm.read`.
  - CM: `assetcore.api.imm09.list_repair_work_orders` (`imm09.py:21`) · Cap: `repair.read`.
  - Báo hỏng: `assetcore.api.imm12.list_incidents` (`imm12.py:197`) · Cap: `corrective.read` · tab "Báo hỏng của tôi" truyền **`mine=1`** → scope `reported_by==session.user` (param `IncidentMine`; [ADR-MOBILE-015](./ADR-MOBILE-015.md)).
  - Hiệu chuẩn (nếu hiển thị): `assetcore.api.imm11.list_calibrations` (`imm11.py:71`) · Cap: `calibration.read`.
- **Capability cần:** `pm.read` / `repair.read` / `corrective.read` / `calibration.read` (KTV có đủ §1.2).
- **Output:** danh sách phiếu (pagination contract `04-api-contract §6`) — `total` permission-aware == Σ items; lặp trang tới `page > total_pages`.

> **Bao phủ 5 feature MVP:** (1) Bước 1 login · (2) Bước 2/2b quét QR→hồ sơ · (3) Bước 3 báo hỏng · (4) Bước 4a/4b/4c yêu cầu PM/CM/Cal · (5) Bước 5 phiếu-của-tôi. ✅ Đủ. (Feature #6 push = Phase E, ngoài hành trình MVP này.)

### Bước 5b — Theo dõi điều chuyển / nhận bàn giao (IMM-13 · Đợt-2, READ-only)

- **Hành động KTV:** mở tab "Điều chuyển" → xem các phiếu luân chuyển thiết bị (Asset Transfer) liên quan (lọc theo `asset`/`status`), mở chi tiết 1 phiếu để **nhận bàn giao** (xem `from→to` vị trí/phòng/người phụ trách + lý do + trạng thái duyệt/nhận).
- **Màn app:** `TransferListView` (filter `asset`/`status` + pagination) → `TransferDetailView` (`getTransfer`).
- **Endpoint BE (READ, permission-aware):**
  - List: `assetcore.api.imm00.list_transfers` (`imm00.py:2048`) — 200 SINGLE `TransferListEnvelope` rows-key `data.items[]` (KHÔNG `oneOf` — handler 0 `try/except`).
  - Detail: `assetcore.api.imm00.get_transfer` (`imm00.py:2081`) — 200 `oneOf [TransferDetailEnvelope | Error]` (404→HTTP-200 nhánh Error).
- **Output:** danh sách/chi tiết phiếu điều chuyển (`status` ∈ `[Pending Approval, Approved, Rejected, Received, Cancelled]`). slot `{200,401,403}`.

> **Đợt-2 (READ-only):** chỉ surface READ (theo dõi + nhận bàn giao); 4 write điều chuyển (tạo/duyệt/từ chối/nhận) đã LIVE @BE nhưng wire mobile ở đợt sau. **CONTRACT-ONLY** (6 endpoint LIVE @`imm00.py`, `git diff` api/imm00.py + services/imm00.py = TRỐNG ⇒ KHÔNG reload). Guard `TestMobileTransferReadContract` (16 TC). [ADR-MOBILE-021](./ADR-MOBILE-021.md).

---

## 3. Bảng MÀN ↔ API (grounded `file:line` — endpoint đã VERIFIED tồn tại)

> Mọi `file:line` grep ra ĐÚNG tại Frappe v15.107.2 (2026-06-09). Đường gọi = `/api/method/<dotted>` (RPC). Schema request/response chi tiết = **Phase C** (giữ STUB OpenAPI).

| Màn app (MVP) | Endpoint BE (`/api/method/<dotted>`) | `file:line` | Verb | Capability |
|---|---|---|---|---|
| `LoginView` (OAuth) | `frappe.integrations.oauth2.authorize` → `.get_token` | `oauth2.py:75` / `:124` | GET → POST | — (allowed_roles) |
| `QrScanView` → resolve | `assetcore.api.imm00.resolve_qr_token` | `imm00.py:312` | GET | `asset.read` |
| `AssetScanInfoView` | `assetcore.api.imm00.get_asset_scan_info` | `imm00.py:355` | GET | `asset.read` |
| `AssetDetailView` | `assetcore.api.imm00.get_asset` | `imm00.py:271` | GET | `asset.read` |
| `AssetListView` (tra cứu) | `assetcore.api.imm00.list_assets` | `imm00.py:159` | GET | `asset.read` |
| `IncidentCreateView` (báo hỏng) | `assetcore.api.imm12.report_incident` | `imm12.py:71` | POST | `corrective.create` |
| `MyWorkOrdersView` › Báo hỏng | `assetcore.api.imm12.list_incidents` | `imm12.py:197` | GET | `corrective.read` |
| `PMWorkOrderCreateView` | `assetcore.api.imm08.create_pm_work_order` | `imm08.py:91` | POST | `pm.create` |
| `PMWorkOrderCreateView` › chọn lịch | `assetcore.api.imm08.list_pm_schedules` | `imm08.py:122` | GET | `pm.read` |
| `MyWorkOrdersView` › PM | `assetcore.api.imm08.list_pm_work_orders` | `imm08.py:28` | GET | `pm.read` |
| `PMWorkOrderDetailView` › Phân công | `assetcore.api.imm08.assign_technician` | `imm08.py:47` | POST¹ | `pm.write` |
| `CMCreateView` | `assetcore.api.imm09.create_repair_work_order` | `imm09.py:36` | POST | `repair.create` |
| `MyWorkOrdersView` › CM | `assetcore.api.imm09.list_repair_work_orders` | `imm09.py:21` | GET | `repair.read` |
| `CalibrationCreateView` | `assetcore.api.imm11.create_calibration` | `imm11.py:90` | POST | `calibration.create` |
| `MyWorkOrdersView` › Cal | `assetcore.api.imm11.list_calibrations` | `imm11.py:71` | GET | `calibration.read` |
| `AppResume` / `SessionGuard` (CSRF warm-up) | `assetcore.api.layout.ping_session` | `layout.py:238` | GET | — (`allow_guest=True` — free; KHÔNG cap, slot {200}-only) |

> **Verify command (acceptance grep):**
> `grep -n "^def resolve_qr_token\|^def get_asset_scan_info\|^def get_asset\|^def list_assets" assetcore/api/imm00.py` → 312/355/271/159 ✓
> `grep -n "^def report_incident\|^def list_incidents" assetcore/api/imm12.py` → 71/197 ✓
> `grep -n "^def create_pm_work_order\|^def list_pm_work_orders\|^def list_pm_schedules\|^def assign_technician" assetcore/api/imm08.py` → 91/28/122/47 ✓
> `grep -n "^def create_repair_work_order\|^def list_repair_work_orders" assetcore/api/imm09.py` → 36/21 ✓
> `grep -n "^def create_calibration\|^def list_calibrations" assetcore/api/imm11.py` → 90/71 ✓
> `grep -n "^def ping_session" assetcore/api/layout.py` → 238 ✓ (`@frappe.whitelist(allow_guest=True)` :237; LUÔN `_ok` → slot {200}-only, CSRF warm-up + app-resume who-am-I-lite)
>
> ¹ `assign_technician` `api/imm08.py:46` hiện bare `@frappe.whitelist()` (nhận GET) — **VERB-FLIP-THIS-ROUND** sang `methods=['POST']` (đóng verb-parity gap R33 BỎ SÓT; write-action DISPATCH KHÔNG idempotent). Mobile contract: `assignPmTechnician` (path 44) — [`04-api-contract.md §8.25`](./04-api-contract.md) / [`ADR-MOBILE-012.md`](./ADR-MOBILE-012.md) / [`docs/imm-08/05_API_Specification.md §0.1.1`](../imm-08/05_API_Specification.md).

---

## 4. Phân loại nhu cầu OFFLINE per-màn (YÊU CẦU cho Phase E — CHƯA impl)

> ⚠️ **Đây là YÊU CẦU nghiệp vụ cho Phase E (Push/Offline/Sync), KHÔNG thiết kế sync engine ở vòng này.** Không có idempotency-key/conflict-policy/sync-queue nào được impl ở Phase A. Mục này CHỈ gán nhãn nhu cầu + lý do nghiệp vụ để Phase E thiết kế. Ràng buộc mạng chập chờn (§1.1) là động lực.
>
> 3 nhãn: **`read-cache-ok`** (đọc — cache an toàn, hiển thị dữ liệu cũ kèm cờ "ngoại tuyến/cập nhật lúc…") · **`idempotent-write-needed`** (ghi — cần xếp hàng offline + cơ chế idempotent để retry KHÔNG tạo bản ghi trùng) · **`online-only`** (bắt buộc có mạng — KHÔNG cache/queue).

| Màn app | Nhãn OFFLINE | Lý do nghiệp vụ (ngắn) |
|---|---|---|
| `LoginView` (OAuth) | **online-only** | OAuth flow + cấp token cần BE trực tiếp; không thể cache login. Refresh-token im lặng cần mạng. |
| `QrScanView` (decode) | **read-cache-ok** (local decode) | Decode QR là client-side; resolve token có thể đọc cache nếu asset đã xem trước (vùng chết mạng). |
| `AssetScanInfoView` | **read-cache-ok** | Hồ sơ thiết bị đổi chậm → cache OK; hiển thị "cập nhật lúc…" + cờ overdue có thể stale, refresh khi có mạng. |
| `AssetDetailView` | **read-cache-ok** | Như trên — dữ liệu master/registration ít đổi; cache giảm phụ thuộc mạng tầng hầm. |
| `AssetListView` | **read-cache-ok** | Danh sách thiết bị (paginated) cache trang đã tải; làm tươi nền khi có mạng. |
| `IncidentCreateView` (báo hỏng) | **idempotent-write-needed** | Sự cố phát hiện tại chỗ KHI mạng chết → PHẢI cho ghi offline + xếp hàng; retry KHÔNG được tạo Incident trùng (Phase E: idempotency-key). Mất báo hỏng = rủi ro an toàn thiết bị y tế (NĐ98 incident reporting). |
| `PMWorkOrderCreateView` | **idempotent-write-needed** | Yêu cầu PM tại hiện trường; cùng yêu cầu xếp-hàng + idempotent như báo hỏng. |
| `list_pm_schedules` (chọn lịch) | **read-cache-ok** | Lịch PM của asset đọc-trước-khi-tạo; cache để form không chết khi mạng phập phù. |
| `CMCreateView` | **idempotent-write-needed** | Yêu cầu sửa chữa tại chỗ; xếp-hàng + idempotent. |
| `CalibrationCreateView` | **idempotent-write-needed** | Yêu cầu hiệu chuẩn; xếp-hàng + idempotent. |
| `MyWorkOrdersView` (list PM/CM/Incident/Cal) | **read-cache-ok** | Theo dõi phiếu: cache danh sách đã tải; `total` permission-aware làm tươi khi có mạng. |

> **Bàn giao Phase E:** với mọi màn `idempotent-write-needed`, Phase E phải thiết kế: (1) hàng đợi ghi offline; (2) idempotency-key (client-gen, BE dedupe) để retry không tạo trùng; (3) chính sách conflict (server-wins / báo người dùng). Đường write hiện tại (report_incident/create_*) **CHƯA có idempotency-key** — đó là việc Phase E, KHÔNG sửa ở Phase A.
>
> → **Đặc tả CHỐT cho 3 nhãn OFFLINE trên (A6):** [`07-offline-sync.md`](./07-offline-sync.md) — read-cache (ETag/`If-Modified-Since` cho `read-cache-ok`) · write-queue idempotency-key contract + conflict policy optimistic-lock qua `modified` (cho `idempotent-write-needed`) · lifecycle hàng đợi queued→sent→acked/conflict/failed · audit NĐ98 chỉ-khi-ghi-thật. Quyết định: [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md). (Cross-link 2 chiều: `07 §1` ánh xạ 1-1 với 3 nhãn của §4 này.)

---

## 5. Map QUYỀN / capability per-màn (bám SSoT `rbac.py` — KHÔNG hệ quyền thứ 2)

> **SSoT:** `assetcore/services/shared/rbac.py` (`CAPABILITY_MAP` 97 cap, `v97.c30c69b8974d`). Bearer→`set_user`→`rbac.can(cap)`→`frappe.has_permission` (`rbac.py:156-168`). Mobile KHÔNG đọc/parse OAuth scope để tự gate → đó là "hệ quyền thứ 2" (cấm — `ADR-MOBILE-001 (b)` + `03-auth §3.2` anti-pattern). Scope coarse `all openid`; quyền THỰC = capability/DocPerm theo user.

| Màn app | Capability cần | Binding (`rbac.py`) | KTV có? | Persona corrective.read-only |
|---|---|---|---|---|
| `LoginView` | — (allowed_roles OAuth Client) | — | ✅ | ✅ (nếu trong allowed_roles) |
| `QrScanView` / `AssetScanInfoView` / `AssetDetailView` / `AssetListView` | `asset.read` | `("AC Asset","read")` `rbac.py:88-91` | ✅ | ✅ (read OK) |
| `IncidentCreateView` (báo hỏng) | `corrective.create` | `("Incident Report","create")` | ✅ | ❌ **chặn 403 VI sạch** (§1.3) |
| `MyWorkOrdersView` › Báo hỏng | `corrective.read` | `("Incident Report","read")` | ✅ | ✅ (read OK) |
| `PMWorkOrderCreateView` | `pm.create` | `("PM Work Order","create")` | ✅ | ❌ (không có cap) |
| `list_pm_schedules` / `MyWorkOrdersView` › PM | `pm.read` | `("PM Work Order","read")` | ✅ | tuỳ DocPerm read |
| `CMCreateView` | `repair.create` | `("Asset Repair","create")` | ✅ | ❌ (không có cap) |
| `MyWorkOrdersView` › CM | `repair.read` | `("Asset Repair","read")` | ✅ | tuỳ DocPerm read |
| `CalibrationCreateView` | `calibration.create` | `("IMM Asset Calibration","create")` | ✅ | ❌ (không có cap) |
| `MyWorkOrdersView` › Cal | `calibration.read` | `("IMM Asset Calibration","read")` | ✅ | tuỳ DocPerm read |
| (In nhãn QR — nếu app hỗ trợ) | `asset.print` | `("AC Asset","print")` `rbac.py:128` | ✅ | tuỳ DocPerm print |

**Nguyên tắc gate (parity 3-tầng đã có):** màn "create" (báo hỏng/PM/CM/Cal) gate ở route + api-tier + service — mobile TÁI DÙNG api-tier gate (vd `imm12.py:93-96` cho báo hỏng) qua bearer. Persona thiếu `*.create` → màn ẩn nút HOẶC API trả 403 VI sạch (no-leak raw cap). **KHÔNG** nới lỏng ở lớp app, **KHÔNG** thêm kiểm tra cap thứ 2.

---

## 6. Tham chiếu chéo (2 chiều)

- **Mapping thô flow→endpoint (nguồn của bảng §3):** [`02-deploy-feasibility.md §6`](./02-deploy-feasibility.md) — bảng MVP feature ↔ endpoint (cap level). Doc này (§3) bồi chi tiết MÀN↔API grounded `file:line`.
- **Scope↔capability 1 SSoT (nền của §5):** [`03-auth-oauth2.md §3`](./03-auth-oauth2.md) — invariant 1 SSoT; anti-pattern "hệ quyền thứ 2".
- **Quyết định kiến trúc (reuse-endpoint, capability=1 SSoT, no session-cookie):** [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) (a)(b)(c)(e).
- **Hợp đồng envelope/error/pagination (output các màn):** [`04-api-contract.md`](./04-api-contract.md) §2/§3/§4/§6 — 6 path nghiệp vụ giữ STUB (Phase C).
- **Auth sequence a→f (bước 1 hành trình):** [`03-auth-oauth2.md §1`](./03-auth-oauth2.md).
- **Tổng quan + 3 quyết định + glossary:** [`00-overview.md`](./00-overview.md) §2 · §7.
- **Exit gate (A11) — traceability matrix 6 flow (gom MÀN↔API §3 + offline §4 + cap §5 + push):** [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) (bảng §3/§4/§5 của doc này = nguồn từng cột matrix).
- **Source SSoT:** `assetcore/services/shared/rbac.py` (capability) · `assetcore/setup/role_profile_catalog.py` (Role Profile↔role) · `assetcore/api/imm00.py` · `imm08.py` · `imm09.py` · `imm11.py` · `imm12.py` (endpoint nghiệp vụ — tái dùng, KHÔNG sửa).

---

## 7. Self-Correction & bàn giao

### 7.1 Self-Correction (mâu thuẫn endpoint/capability)

Rà soát vòng A4 — **KHÔNG phát hiện mâu thuẫn** giữa endpoint/capability đã chốt (`02-§6`, `03-§3`, `04-§10`) và source thật:

- 13 endpoint nghiệp vụ + 2 endpoint auth: `file:line` grep ĐÚNG (§3 verify command).
- Capability binding khớp `02-§6` + `04-§10` (asset.read / corrective.create / pm.create / repair.create / calibration.create + các `*.read`).
- Cap-gate báo-hỏng `corrective.create` (api-tier `imm12.py:55,93-96`) khớp claim parity 3-tầng + read-only chặn 403 no-leak (verified DocPerm: Commissioning Manager/Auditor = read-only Incident Report).

⇒ KHÔNG cần sửa `ADR-MOBILE-001` vòng này. Nếu Phase C phát hiện cap mismatch khi bồi schema → ghi vào doc + ADR TRƯỚC, KHÔNG sửa code nghiệp vụ ở Phase A.

### 7.2 Bàn giao Phase C / E

- **Phase C:** bồi 6 path nghiệp vụ schema vào OpenAPI (request/response từ type-hints+docstring) — đường + cap đã chốt ở §3. Dọn nợ `str=None`→`str=""` (vd `list_pm_schedules` `imm08.py:122`, `create_calibration` `imm11.py:90`) — `04-§8`. Cân nhắc map scope→capability-group.
- **Phase E:** thiết kế offline cho các màn `idempotent-write-needed`/`read-cache-ok` (§4) — hàng đợi + idempotency-key + conflict-policy ĐÃ đặc tả ở [`07-offline-sync.md`](./07-offline-sync.md) + [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) (A6 — hợp đồng, impl Phase E). Push channel #3 (`notifications.py::_dispatch`) — cơ chế + DocType device-token + MAP 6-event + payload ĐÃ đặc tả ở [`06-push-fcm.md`](./06-push-fcm.md) + [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) (feature #6 MVP).
- **Carry FE-web (tham khảo parity mobile, KHÔNG sửa ở đây):** BUG-PM-2 (QR→PM 0-schedule dead-end) — mobile `PMWorkOrderCreateView` cần lối thoát tương tự (STATE open thread).
