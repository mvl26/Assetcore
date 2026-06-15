# 12 — Phase-B pre-flight: verifier OAuth Client (B0-PREFLIGHT)

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A→B bridge** (item B-prep ĐẦU TIÊN, KHÔNG-provisioning) · B0-PREFLIGHT |
| Bám quyết định | **D-AUTH** (OAuth2 + refresh) · D-MVP (field-tech) · D-STACK (native) — `00-overview.md §2` |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | Stable (doc-only + verifier read-only) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** biến **checklist OAuth Client** (field-spec [`03-auth-oauth2.md §4`](./03-auth-oauth2.md) · blocker **B-1** [`11-phase-a-exit.md §2`](./11-phase-a-exit.md)) thành **hợp đồng THỰC THI có thể chạy**: một verifier READ-ONLY trả báo cáo có cấu trúc cho biết Phase B đã provision đúng `OAuth Client` chưa.
> **doc-only + verifier read-only:** doc này TRỎ NGƯỢC các nguồn (KHÔNG nhân đôi bảng field `03 §4`). Verifier chỉ ĐỌC config — KHÔNG tạo/sửa record, KHÔNG đụng `frappe.integrations.oauth2`/`oauth.py`.
> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`10-deploy-ops.md`](./10-deploy-ops.md) · [`11-phase-a-exit.md`](./11-phase-a-exit.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Mục tiêu / Out-of-scope / Lý do cấp số 12

### 0.1 Mục tiêu

Cung cấp **pre-flight check tự động hoá** cho điều kiện tiên quyết **B-1** (tạo `OAuth Client`):

- Trước khi mở Phase B (hoặc ngay sau khi USER tạo record), chạy 1 lệnh → biết ngay client đã cấu hình đúng 7 điều kiện B-1 chưa, sai ở đâu (blocker tiếng Việt).
- Thay việc "đọc bằng mắt" checklist `03 §4` bằng kiểm tra **đo được, lặp lại được**.
- Là **gate khách quan** cho checklist go/no-go A→B ([`11-phase-a-exit.md §3`](./11-phase-a-exit.md)).

### 0.2 Out-of-scope (BẮT BUỘC)

| KHÔNG làm | Vì sao |
|---|---|
| Tạo/sửa/xoá record `OAuth Client` | Tạo record = Phase B, **HARD-STOP USER** (DB write). Verifier chỉ ĐỌC. |
| Sửa `frappe.integrations.oauth2.py` / `frappe.oauth.py` | KHÔNG modify core (CLAUDE.md §19); WIRE-not-write (`ADR-MOBILE-001 a`). |
| Thêm capability / cap mới | 1 SSoT quyền (`ADR-MOBILE-001 b`); chỉ đọc config. |
| Đưa endpoint này vào hợp đồng app native | Đây là tiện ích **admin-only nội bộ**, NGOÀI hợp đồng app (xem §0.4). |
| Nhân đôi bảng field `03 §4` | Field-spec có 1 nguồn duy nhất; doc này TRỎ NGƯỢC. |

### 0.3 Lý do cấp số 12

Theo convention [`00-overview.md §6`](./00-overview.md) ("Số kế tiếp cấp khi có doc mới"): số `00`–`11` đã cấp; số khả dụng kế tiếp = **`12`**. Doc này là **`12-phase-b-preflight.md`** — KHÔNG ghi đè `00`–`11`. **Số kế tiếp = `13-…`**.

### 0.4 Vị trí trong kiến trúc (admin-only, ngoài hợp đồng app)

Verifier là **endpoint vận hành nội bộ** (admin/diagnostic), **KHÔNG** thuộc hợp đồng máy-đọc của app native:

- KHÔNG vào [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) — yaml chỉ chứa endpoint app native gọi (OAuth provider + 9 nghiệp vụ + 2 device-token). App native KHÔNG bao giờ gọi verifier này.
- Gate **System Manager** (DocPerm `OAuth Client` read = System Manager), KHÔNG `allow_guest`.

---

## 1. Lệnh chạy verifier + diễn giải 7 check

### 1.1 Lệnh chạy (read-only, an toàn)

```bash
bench --site miyano execute assetcore.api.mobile.preflight.verify_oauth_client
```

- READ-ONLY: chỉ `frappe.db.count` + `frappe.get_all`/`get_doc` (đọc). KHÔNG ghi DB.
- Chạy được cả khi `OAuth Client` count = 0 (hiện trạng thật @source) — trả report sạch, **KHÔNG raise / KHÔNG leak traceback**.
- Gọi qua HTTP (admin đã đăng nhập, System Manager): `POST /api/method/assetcore.api.mobile.preflight.verify_oauth_client` (KHÔNG `allow_guest`).

### 1.2 Cấu trúc report trả về

```json
{
  "ready": false,
  "client_count": 0,
  "checks": [
    {"field": "client_count", "expected": ">=1", "actual": 0, "pass": false}
  ],
  "blockers": ["Chưa có OAuth Client — Phase B chưa provision."],
  "checked_client": null
}
```

| Khoá | Ý nghĩa |
|---|---|
| `ready` | `true` CHỈ KHI có ≥1 client THOẢ toàn bộ 7 điều kiện B-1. |
| `client_count` | Số record `OAuth Client` (read-only count). |
| `checks` | Danh sách 7 điều kiện B-1, mỗi mục `{field, expected, actual, pass}`. |
| `blockers` | Mô tả **tiếng Việt** từng điều kiện CHƯA đạt (rỗng nếu `ready=true`). |
| `checked_client` | `name` client được chấm (record đầu theo `creation`) hoặc `null` khi count==0. |

### 1.3 7 check — diễn giải

| # | `field` | Kỳ vọng (`expected`) | Ý nghĩa |
|---|---|---|---|
| 1 | `client_count` | `>=1` | Phải có ≥1 record `OAuth Client` (B-1 #1). count==0 → blocker "Chưa có OAuth Client". |
| 2 | `grant_type` | `Authorization Code` | BẮT BUỘC Authorization Code (Implicit deprecated, không PKCE). |
| 3 | `response_type` | `Code` | Khớp `response_type=code` ở bước authorize (`03 §1`). |
| 4 | `default_redirect_uri` | `assetcore://oauth/callback` | Custom-scheme native; phải == `default_redirect_uri` **VÀ** nằm trong `redirect_uris`. Sai → provider reject. |
| 5 | `scopes` | `all openid` | Coarse (`ADR-MOBILE-001 b` · `03 §3.2`); quyền thực = RBAC capability theo user. |
| 6 | `skip_authorization` | `0` | Hiện màn Allow/Deny lần đầu; `1` chỉ cho first-party trusted có chủ đích. |
| 7 | `allowed_roles` | `>=1 role (field-tech least-priv)` | Giới hạn role KTV → least-privilege, giảm bề mặt (T5, `08 §3b`). |

> **Phạm vi chấm:** verifier chấm record `OAuth Client` ĐẦU TIÊN theo `creation` (best-effort). Khi Phase B chỉ tạo 1 client native, đây chính là record đó. Nếu site có nhiều client (vd thêm client web), chọn lọc/đặt tên rõ để record native là record được chấm.

---

## 2. Ánh xạ 7 check ↔ B-1 field ↔ runbook

> **KHÔNG nhân đôi bảng field.** Mỗi check trỏ về 1 dòng trong bảng field thật `03 §4` (nguồn) + bước tương ứng trong runbook `10 §1` (thực thi).

| Check (verifier) | Field-spec nguồn ([`03 §4`](./03-auth-oauth2.md)) | Bước thực thi ([`10 §1`](./10-deploy-ops.md)) |
|---|---|---|
| `client_count >= 1` | §4 lời mở ("OAuth Client count = 0 ⇒ Phase B PHẢI tạo client") | `10 §1` step 1 (New OAuth Client) |
| `grant_type == 'Authorization Code'` | §4 dòng `grant_type` | `10 §1` step 1 (`grant_type = Authorization Code`) |
| `response_type == 'Code'` | §4 dòng `response_type` | `10 §1` step 1 (`response_type = Code`) |
| `default_redirect_uri == native scheme ∈ redirect_uris` | §4 dòng `redirect_uris` + `default_redirect_uri` | `10 §1` step 1 (`redirect_uris`+`default_redirect_uri` = `assetcore://oauth/callback`) |
| `scopes == 'all openid'` | §4 dòng `scopes` | `10 §1` step 1 (`scopes = all openid`) |
| `skip_authorization == 0` | §4 dòng `skip_authorization` | `10 §1` step 1 (`skip_authorization = 0`) |
| `allowed_roles non-empty` | §4 dòng `allowed_roles` | `10 §1` step 1 (`allowed_roles` = role field-tech) |

> **Quan hệ với blocker B-1:** toàn bộ 7 check này hợp thành điều kiện **B-1** ([`11-phase-a-exit.md §2`](./11-phase-a-exit.md)). `ready=true` ⇒ B-1 ĐẠT (riêng B-1; B-2..B-8 vẫn cần — xem `11 §2`).
> **Quan hệ với token-response contract (B1):** pre-flight này kiểm OAuth Client **provisioning** (config record). Khi `ready=true` + token cấp xong, hợp đồng **RESPONSE** của `get_token`/`revoke_token` (200-keys / `OAuthError400` 400 / revoke empty-200) đã đóng băng = **PASSTHROUGH OAuthlib** — đặc tả + guard tại [`03-auth-oauth2.md §2 / §2.3.1`](./03-auth-oauth2.md) + [`04-api-contract.md §5b`](./04-api-contract.md) (`TC-MOB-OAUTH-TOKEN-*`). Pre-flight (config) và token-response (shape) là 2 mặt độc lập của B-1.

---

## 3. Cách đọc report + hành động khắc phục

### 3.1 `ready = true`

B-1 đã đạt. Tiếp tục các blocker còn lại Phase B: **B-2** (CORS), **B-3** (public HTTPS host), **B-4** (QR deep-link host), **B-5** (rate-limit nginx), **B-6/B-7** (FCM + reload) — toàn bộ HARD-STOP USER, danh sách hợp nhất tại [`11-phase-a-exit.md §2`](./11-phase-a-exit.md), runbook [`10-deploy-ops.md`](./10-deploy-ops.md).

### 3.2 `ready = false` + `client_count = 0`

Hiện trạng thật @source (chưa provision). Hành động: USER tạo `OAuth Client` theo runbook [`10 §1`](./10-deploy-ops.md) (điền field theo checklist [`03 §4`](./03-auth-oauth2.md)). **HARD-STOP USER** (DB write). Sau đó chạy lại verifier.

### 3.3 `ready = false` + `client_count >= 1`

Đã có client nhưng cấu hình sai. Đọc `blockers` (tiếng Việt) → mỗi blocker chỉ rõ field sai + giá trị hiện tại. Sửa record `OAuth Client` (USER, Desk → OAuth Client → record được chấm = `checked_client`) theo đúng dòng field-spec [`03 §4`](./03-auth-oauth2.md).

> **Bảng SSoT-derived (KHÔNG tay-chép):** mỗi dòng dưới là **stem nguyên-văn** của 1 trong **6 record-level blocker** mà `verify_oauth_client()` (qua `_evaluate_client()`) phát — cột "Blocker (stem)" bám message THẬT trong `preflight.py`, cột "Field" + "Sửa" trỏ đúng dòng field-spec [`03 §4`](./03-auth-oauth2.md). Bảng được **machine-guard** (F-B5, `tests/test_mobile_preflight.py::TestMobilePreflightBlockerViDocGuard`, TC-MOB-PRE-18..21): nếu `preflight.py` reword/thêm/bớt blocker mà bảng này KHÔNG cập nhật → test ĐỎ. KHÔNG sửa bảng bằng tay rời khỏi blocker thật.

| Field | Blocker (stem nguyên-văn từ `verify_oauth_client()`) | Sửa (theo [`03 §4`](./03-auth-oauth2.md)) |
|---|---|---|
| `grant_type` | `grant_type phải là 'Authorization Code' (Implicit đã deprecated, không hỗ trợ PKCE)` | Đổi field `grant_type` → `Authorization Code` (03 §4 dòng `grant_type`). |
| `response_type` | `response_type phải là 'Code' (khớp response_type=code ở bước authorize)` | Đổi field `response_type` → `Code` (03 §4 dòng `response_type`). |
| `default_redirect_uri` | `default_redirect_uri phải == 'assetcore://oauth/callback' VÀ nằm trong redirect_uris (custom-scheme native; sai → provider reject)` | Sửa `default_redirect_uri` = `assetcore://oauth/callback` + thêm cùng dòng vào `redirect_uris` (03 §4 dòng `redirect_uris`/`default_redirect_uri`). |
| `scopes` | `scopes nên là 'all openid' (coarse — quyền thực do RBAC capability theo user, 03 §3.2)` | Đặt field `scopes` = `all openid` (03 §4 dòng `scopes`; quyền thực = RBAC theo user, không nới scope ở đây). |
| `skip_authorization` | `skip_authorization phải = 0 (hiện màn Allow/Deny lần đầu); chỉ đặt 1 cho first-party trusted có chủ đích` | Đặt `skip_authorization` = `0` (03 §4 dòng `skip_authorization`; chỉ đặt 1 cho first-party trusted có chủ đích). |
| `allowed_roles` | `allowed_roles rỗng — phải giới hạn role field-tech (KTV) để least-privilege, giảm bề mặt (T5, 08 §3b)` | Thêm role field-tech (KTV) vào `allowed_roles` (03 §4 dòng `allowed_roles`; least-privilege). |

> ℹ️ Blocker count==0 ('Chưa có OAuth Client') KHÔNG nằm bảng này — đó là nhánh `client_count = 0` (§3.2), guard riêng tại F-B4 TC-MOB-PRE-16. Bảng §3.3 chỉ phủ **6 blocker cấp-record** (client đã tồn tại nhưng cấu hình sai).

> ⚠️ Nếu vừa đổi capability/Role Profile cho role field-tech → cần `bench migrate` HOẶC bust `ac_caps::*` + reload gunicorn để cap-set live HTTP (B-7, `10 §1` step 3). **HARD-STOP USER.** Verifier chỉ chấm config OAuth Client, KHÔNG kiểm cap-set live.

---

## 4. Acceptance / KPI

| Tiêu chí | Đo bằng |
|---|---|
| Verifier chạy được read-only, count==0 → `ready=false` + blocker VI, KHÔNG raise/leak | `bench --site miyano execute assetcore.api.mobile.preflight.verify_oauth_client` |
| 7 check B-1 đủ mặt; mỗi check `{field, expected, actual, pass}` | report `checks` (len ≥1 khi count==0; =7 khi count≥1) |
| Drift-guard ĐỎ nếu Frappe đổi schema `OAuth Client` (doc không drift âm thầm) | `assetcore/tests/test_mobile_preflight.py` (TC-MOB-PRE-01..05) |
| Verifier không ghi DB (count bất biến) + chịu count==0 | TC-MOB-PRE-07/09 |
| Gate System Manager (no allow_guest) — admin-only, ngoài hợp đồng app | `@frappe.whitelist()` + `frappe.only_for("System Manager")`; KHÔNG vào openapi yaml |
| No-regression OAS | `test_oas_generator` · `test_oas_signatures` · `test_mobile_oas` GREEN |

---

## Tham chiếu chéo

- **Field-spec nguồn (checklist OAuth Client — KHÔNG nhân đôi):** [`03-auth-oauth2.md §4`](./03-auth-oauth2.md)
- **Runbook thực thi go-live (tạo OAuth Client numbered steps):** [`10-deploy-ops.md §1`](./10-deploy-ops.md)
- **Blocker B-1 + danh sách Phase-B prereqs hợp nhất:** [`11-phase-a-exit.md §2`](./11-phase-a-exit.md)
- **3 quyết định + glossary:** [`00-overview.md §2`](./00-overview.md) · convention đặt tên [`00-overview.md §6`](./00-overview.md)
- **ADR quyền 1 SSoT (wire-not-write · capability):** [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) (a/b)
- **Verifier (code):** `../../assetcore/api/mobile/preflight.py` — `verify_oauth_client()`
- **Drift-guard test:** `../../assetcore/tests/test_mobile_preflight.py`
- **Provider Frappe (chỉ đọc, KHÔNG sửa):** `../../../frappe/frappe/integrations/doctype/oauth_client/oauth_client.json`
