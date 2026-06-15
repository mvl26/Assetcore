# 06 — Push FCM design · DocType AC Mobile Device Token · MAP 6-event → kênh #3

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A — Kiến trúc & Feasibility** (vòng 5 / PHASE A · A5 Push-FCM design) |
| Bám quyết định | D-AUTH (OAuth2+refresh) · D-MVP (field-tech) · D-STACK (native) — `00-overview.md §2` · **ADR-MOBILE-002** (cơ chế push) |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** chốt **cơ chế push** (FCM Admin SDK TRỰC TIẾP vs reuse Frappe relay) + đặc tả **DocType AC Mobile Device Token** mức BA (KHÔNG impl) + bảng **MAP 6-event notification → FCM** (kênh #3, KHÔNG phá in-app/email) + spec **payload push + deep-link native** + bảo mật server-key/credentials trong `site_config` + threat + audit NĐ98.
> **Đây là đặc tả (spec), KHÔNG impl.** Impl thực tế = **Phase E** (kênh #3 + device-token registry + gửi FCM). Tài liệu này = HỢP ĐỒNG để BE Phase E + repo-native xây không lệch.
> **Verify:** mọi claim kỹ thuật có `file:line` đối chiếu source THẬT tại **Frappe v15.107.2** (site `miyano`, 2026-06-09). KHÔNG bịa field/endpoint/cap.

> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`05-personas-mvp.md`](./05-personas-mvp.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

> **Quyết định đặt số (convention `00-overview.md §6`):** doc này dùng số **`06`** vì `05` đã cấp cho `05-personas-mvp.md` (A4). Theo convention chống-trùng-số `00-overview §6` ("Số kế tiếp cấp khi có doc mới"), `06` là số kế tiếp khả dụng. Ghi rõ lý do tại đây theo yêu cầu acceptance.

---

## 0. Context / Scope / Actor

### 0.1 Bám 3 quyết định nền + ADR-MOBILE-002 (KHÔNG re-litigate)

- **D-AUTH** (OAuth2 + refresh): mỗi request push-register vẫn đi qua bearer → `set_user` → RBAC capability 1 SSoT (xem `ADR-MOBILE-001` decision (b), `03-auth-oauth2.md §3`). Device-token register/unregister là endpoint **cần bearer** (KHÔNG allow_guest).
- **D-MVP** (field-tech): MVP luồng (6) "thông báo đẩy" — kiến trúc Phase A, impl Phase E (`00-overview.md §2 D-MVP`).
- **D-STACK** (native): app native nhận push qua FCM SDK của Android/iOS; deep-link mở thẳng màn native bằng `data` payload (KHÔNG dùng deep-link SPA `/a/<token>` — `ADR-MOBILE-001` consequences).
- **ADR-MOBILE-002** (doc này chốt): cơ chế push = **FCM Admin SDK TRỰC TIẾP** (service-account credentials trong `site_config`), KHÔNG reuse Frappe push relay (relay = Frappe Cloud, không air-gapped). Evidence: §1 + ADR.

### 0.2 Scope tài liệu này

| Trong scope (Phase A — đặc tả) | Ngoài scope |
|---|---|
| Chốt cơ chế push (direct SDK vs relay) + sơ đồ luồng register→event→FCM→APK | Impl gửi FCM / kênh #3 trong `_dispatch` (Phase E) |
| Spec DocType **AC Mobile Device Token** (field/naming/dedup/RBAC/lifecycle) mức BA | Tạo file doctype JSON/controller (Phase E impl) |
| Bảng MAP 6-event → FCM + điểm fan-out `_dispatch` (KHÔNG phá 2 kênh cũ) | Sửa `services/notifications.py` (Phase E) |
| Spec payload FCM (title/body VI + data + deep-link) + ánh xạ route native | Đăng ký FCM project / set credentials site_config (Phase B/E — HARD-STOP USER) |
| opt-in/opt-out mức field `enabled` (wiring chi tiết để Phase E) | Notification list/read endpoint (Phase D/E — chỉ tham chiếu, KHÔNG bồi) |
| Bảo mật server-key `site_config` + threat + audit NĐ98 | Offline cache / sync conflict policy (Phase E) |
| 2 path STUB device-token vào OpenAPI (shape/security/operationId) | Bồi request/response đầy đủ device-token (Phase E) |

### 0.3 Actor

| Actor | Vai trò trong luồng push |
|---|---|
| **Kỹ thuật viên hiện trường (field-tech)** | Đăng nhập APK → APK lấy FCM token từ SDK → gọi `register_device_token`; nhận push; tap → mở deep-link màn native. Persona: `05-personas-mvp.md §1`. |
| **AssetCore BE (Frappe)** | Lưu token (DocType AC Mobile Device Token); khi event xảy ra → `_dispatch` fan-out kênh #3 gửi FCM tới token enabled của recipient. |
| **FCM (Google Firebase Cloud Messaging)** | Hạ tầng đẩy thực; BE gọi FCM HTTP v1 (Admin SDK) bằng service-account credentials trong `site_config`. |
| **Admin / System Manager** | Xem TẤT CẢ device-token (quản trị/thu hồi); user thường chỉ thấy token của mình (RBAC §2.3). |

### 0.4 WHO HTM / NĐ98 grounding

- Push là **kênh cảnh báo vận hành** cho stage 5 (Maintenance) — đẩy nhanh "thời gian tới hiện trường" khi có incident/SLA-breach/PM-due/calibration-due. KHÔNG thay quy trình; chỉ rút ngắn độ trễ thông báo.
- **NĐ98 audit:** action register/unregister device-token là thao tác có hệ quả an ninh (token định danh thiết bị nhận thông báo nghiệp vụ) ⇒ phải sinh **record + audit trail** (§5.4). KHÔNG có push nào được phép thay thế bản ghi in-app (Notification Log = bằng chứng bất biến NĐ98 — §3.3).

---

## 1. Cơ chế push — FCM direct SDK vs reuse Frappe relay (CHỐT)

### 1.1 Khảo sát Frappe push có sẵn — CHỈ là proxy tới relay Frappe Cloud

Frappe v15 CÓ module `frappe/push_notification.py`, NHƯNG mọi hàm gửi đều **proxy POST tới central relay server** (`notification_relay.api.*`), KHÔNG gọi FCM trực tiếp:

| Hàm Frappe | Thực chất gọi | Evidence |
|---|---|---|
| `PushNotification.add_token` | `notification_relay.api.token.add` (relay) | `frappe/push_notification.py:27-29` |
| `PushNotification.remove_token` | `notification_relay.api.token.remove` (relay) | `frappe/push_notification.py:40-42` |
| `send_notification_to_user` | `notification_relay.api.send_notification.user` (relay) | `frappe/push_notification.py:130-133` |
| `send_notification_to_topic` | `notification_relay.api.send_notification.topic` (relay) | `frappe/push_notification.py:175-178` |
| `_send_post_request` (mọi call) | gated `is_enabled()` + `frappe.conf.push_relay_server_url` | `frappe/push_notification.py:240-251` |
| `is_enabled()` | đọc `Push Notification Settings.enable_push_notification_relay` | `frappe/push_notification.py:187-189` |

Doctype `Push Notification Settings` mô tả tường minh bản chất relay:

> "Enabling this will **register your site on a central relay server** to send push notifications for all installed apps through Firebase Cloud Messaging." — `push_notification_settings/push_notification_settings.json:6` (+ field `enable_push_notification_relay:19-21`, `api_key:30-32`, `api_secret:35-37`).

**Kết luận khả thi:** đường Frappe có sẵn = **gọi qua máy chủ relay của Frappe Cloud** (cần `push_relay_server_url` + đăng ký credential từ relay — `:217 get_credential`). ⇒ **KHÔNG dùng được cho self-host / air-gapped** (bệnh viện NĐ98 thường mạng nội bộ, không cho gọi ra Frappe Cloud). Nếu disable relay → `_send_post_request` raise `"Push Notification Relay is not enabled"` (`:240-241`).

### 1.2 Quyết định (chốt tại ADR-MOBILE-002)

> **Push = FCM Admin SDK TRỰC TIẾP** — BE gọi thẳng **FCM HTTP v1** bằng **service-account credentials** (JSON) lưu trong `site_config.json` (KHÔNG commit). **KHÔNG** reuse `frappe.push_notification` (relay Frappe Cloud).

Lý do (đầy đủ Context/Decision/Alternatives/Consequences ở [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md)):
- Relay = phụ thuộc Frappe Cloud + gọi ra Internet ⇒ trái mô hình air-gapped/on-prem NĐ98.
- FCM Admin SDK direct = bệnh viện chỉ cần outbound HTTPS tới `fcm.googleapis.com` (hoặc whitelisted), credentials nằm hoàn toàn trong tầm kiểm soát site.
- Device-token registry tự quản (DocType §2) ⇒ KHÔNG lệ thuộc token store của relay; RBAC/audit của AssetCore áp dụng nguyên (1 SSoT).

### 1.3 Sơ đồ luồng (register → event → FCM send → APK receive)

```
┌─────────────┐   (a) login OAuth2 (03-auth)      ┌──────────────────────────┐
│  APK native │ ────────────────────────────────► │  AssetCore BE (Frappe)   │
│ (field-tech)│   (b) FCM SDK cấp fcm_token        │                          │
│             │ ──register_device_token──(bearer)─►│  upsert AC Mobile Device │
│             │     {fcm_token,platform,...}       │  Token (dedup theo token)│
└─────────────┘                                    │  + audit register (§5.4) │
       ▲                                           └────────────┬─────────────┘
       │                                                        │
       │                          (sự kiện nghiệp vụ xảy ra)    │
       │                          incident/approval/assign/...  ▼
       │                                           ┌──────────────────────────┐
       │                                           │ notifications._dispatch  │
       │                                           │  Kênh1 in-app (GIỮ)      │
       │                                           │  Kênh2 email  (GIỮ)      │
       │                                           │  Kênh3 push (THÊM, Phase E│
       │                                           │   → tra token enabled    │
       │                                           │     của recipient)       │
       │                                           └────────────┬─────────────┘
       │                                                        │ FCM HTTP v1
       │                                                        ▼  (service-account
       │                                           ┌──────────────────────────┐  từ site_config)
       │   (d) push hiện trên máy / tap            │   FCM (Google)           │
       └───────────────────────────────────────── │   fcm.googleapis.com     │
           data.deeplink → mở màn native           └──────────────────────────┘
           (e) APK 401 từ FCM (token chết)
               → BE disable token (§2.5 invalidate-on-401)
```

- **(c) gửi:** kênh #3 chỉ THÊM trong `_dispatch` (§3) — KHÔNG sửa call-site. Lỗi FCM KHÔNG vỡ in-app/email (fail-safe, theo pattern `_safe_sendmail`).
- **(e) token chết:** FCM trả `UNREGISTERED`/`401`/`NotRegistered` → BE set `enabled=0` (§2.5), lần sau bỏ qua token đó.

---

## 2. DocType AC Mobile Device Token — spec mức BA (KHÔNG impl)

> Đặc tả để Phase E tạo doctype. KHÔNG tạo file JSON/controller ở Phase A. KHÔNG dựng hệ quyền thứ 2 — RBAC bám SSoT `permissions.py`/`rbac.py` (xem §2.3).

### 2.1 Field

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `user` | Link → User | ✔ | Chủ sở hữu token (đối tượng nhận push). Mặc định = `frappe.session.user` lúc register (KHÔNG cho client tự set user khác — §5.3 threat). |
| `fcm_token` | Data (Long Text nếu vượt 140) | ✔ | FCM registration token do SDK cấp. **UNIQUE** (dedup §2.4). |
| `platform` | Select: `android` / `ios` | ✔ | Nền tảng thiết bị. (MVP: android trước — `00-overview §1`.) |
| `device_label` | Data | ✘ | Nhãn thiết bị do user/SDK đặt (vd "Galaxy A54 — KTV Phạm Văn Đức"). Hiển thị khi user quản lý token. |
| `app_version` | Data | ✘ | Phiên bản APK (để debug/migration payload theo version). |
| `last_seen` | Datetime | ✘ | Lần cuối token còn sống (cập nhật mỗi register/refresh hoặc gửi push thành công). Dùng dọn token cũ. |
| `enabled` | Check (default 1) | ✔ | Cờ opt-in/opt-out + invalidate. `0` ⇒ KHÔNG gửi push (§2.5 + §5.1). |

> **KHÔNG bịa thêm field.** Field trên là tối thiểu đủ cho register/dedup/RBAC/lifecycle. Nếu Phase E cần thêm (vd `device_id` ổn định để re-bind khi FCM token xoay) → bổ sung kèm RED test, ghi delta vào doc này.

### 2.2 Naming

- **`autoname`: `hash`** (system-generated PK) — token KHÔNG nên làm PK (FCM token dài + có thể chứa ký tự không hợp lệ cho `name`; token còn rotate). PK ổn định + `fcm_token` UNIQUE đảm bảo dedup.
- KHÔNG dùng `field:fcm_token` làm autoname (token quá dài, đổi giá trị khi rotate → vỡ PK). UNIQUE constraint trên `fcm_token` (§2.4) lo phần chống-trùng.
- Convention bám DocType hệ thống (vd `ac_spare_part_stock` dùng autoname) — KHÔNG naming_series cho registry kỹ thuật nội bộ.

### 2.3 RBAC — bám SSoT, KHÔNG dựng hệ quyền thứ 2

| Chủ thể | Quyền trên AC Mobile Device Token |
|---|---|
| **User thường (field-tech)** | CHỈ thấy/sửa/xoá token **của mình** (`user == frappe.session.user`). |
| **Admin / System Manager** | Xem TẤT CẢ token (quản trị, thu hồi token nghi ngờ). |
| **Vendor Engineer** | Isolation: chỉ token của chính họ (KHÔNG thấy token user khác) — cùng nguyên tắc `_VENDOR_ROLE` (`permissions.py:46`). |

Thực thi (Phase E) bám pattern hiện có, KHÔNG viết RBAC mới:
- **Row-level self-scope** qua `permission_query_conditions` + `has_permission` so `user == frappe.session.user` — cùng kiểu owner/self-scope mà `permissions.py` dùng cho WO (`reported_by`/`assigned_to`) và vendor isolation (`permissions.py:90/188`). Đăng ký hook trong `hooks.py::permission_query_conditions` + `has_permission` (cùng cơ chế các doctype khác).
- **Admin read-all** = role `System Manager` (Frappe built-in) — KHÔNG tạo capability mới. DocPerm cấp read/write theo Role Profile chuẩn.
- KHÔNG thêm capability vào `CAPABILITY_MAP` cho register/unregister: đây là thao tác **self-service** (user thao tác trên token của chính mình), gate bằng **bearer (đã login) + row-level self-scope**, KHÔNG cần cap nghiệp vụ. (Nếu Phase E thấy cần cap quản trị token → promote vào `rbac.py` kèm test, ghi delta — KHÔNG bịa ở Phase A.)

### 2.4 UNIQUE / dedup theo `fcm_token`

- `fcm_token` **UNIQUE** ở DB. Register là **UPSERT theo `fcm_token`**: nếu token đã tồn tại → cập nhật (`user`/`platform`/`device_label`/`app_version`/`last_seen`/`enabled=1`) thay vì tạo bản ghi mới ⇒ tránh trùng + tránh gửi push 2 lần cùng 1 thiết bị.
- Edge: cùng `fcm_token` đổi `user` (đổi tài khoản đăng nhập trên cùng máy) ⇒ upsert đổi `user` về user hiện tại (token thuộc thiết bị, gắn user đang đăng nhập). Re-bind sạch, không để token cũ gửi push cho user trước.

### 2.5 Lifecycle token (invalidate-on-401-FCM)

```
register ──► enabled=1, last_seen=now
   │
   ├─ user opt-out (PATCH enabled=0) ─────────► enabled=0 (KHÔNG gửi, GIỮ record cho audit)
   │
   ├─ unregister (logout/gỡ app) ────────────► xoá record HOẶC enabled=0 (Phase E chốt; mặc định disable để giữ audit)
   │
   └─ FCM trả UNREGISTERED/NotRegistered/401 ─► BE set enabled=0 (invalidate-on-401)
        khi gửi push (kênh #3)                   lần sau bỏ qua token này
```

- **invalidate-on-401-FCM:** khi gửi FCM (Phase E) nhận lỗi token chết (`UNREGISTERED` / HTTP 404 `messaging/registration-token-not-registered`) → BE set `enabled=0` cho token đó. KHÔNG xoá ngay (giữ `last_seen` + record cho audit/forensics).
- Token sống lại = APK register lại token mới (FCM rotate) → upsert (§2.4) bật `enabled=1`.

---

## 3. MAP 6-event notification → FCM (kênh #3 — KHÔNG phá in-app/email)

### 3.1 Khẳng định bất biến (BẮT BUỘC)

> **Push = KÊNH THỨ 3, CHỈ THÊM.** Kênh 1 (in-app Notification Log) + Kênh 2 (email) **GIỮ NGUYÊN**, KHÔNG sửa, KHÔNG thay. Push thêm SAU 2 kênh trong cùng `_dispatch`, cùng danh sách `users` đã dedupe + cùng `doc` reference. Lỗi push KHÔNG vỡ in-app/email (fail-safe — pattern `_safe_sendmail`).

- Kênh 1 in-app: `services/notifications.py::_dispatch` → `enqueue_create_notification` (`:385`). Notification Log = bản ghi bất biến = audit NĐ98.
- Kênh 2 email: `_dispatch` → `_safe_sendmail` cho user `_user_wants_email` (`:401-409`).
- Kênh 3 push (Phase E): chèn NGAY trong `_dispatch` (sau kênh 1/2) — tra token `enabled` của mỗi `user`, gửi FCM. **1 điểm fan-out duy nhất ⇒ mọi event tự có push, KHÔNG sửa từng call-site.**

### 3.2 Bảng 5 dispatch fn + SLA-emitter → điểm fan-out

| # | Dispatch fn (def) | Trigger | `_dispatch(...)` fan-out | Recipient |
|---|---|---|---|---|
| E1 | `notify_assignment` (`notifications.py:416`) | WO gán cho KTV (PM WO / Asset Repair on_update+on_submit) | `:452` | assignee |
| E2 | `notify_approval_pending` (`:461`) | doc chuyển VÀO state cần duyệt (động từ Workflow meta) | `:498` | approver |
| E3 | `notify_incident_created` (`:506`) | Incident Report after_insert (báo hỏng IMM-12) | `:562` | assigned_to / fallback reported_by |
| E4 | `notify_calibration_due` (`:578`) | scheduler set calibration_status → Due Soon/Overdue (IMM-11) | `:627` | responsible_technician / fallback custodian |
| E5 | `notify_escalation` (`:752`) | WO chuyển VÀO state escalation (IMM-08 Halted/Major Failure) | `:791` | supervisor + role quản trị |
| SLA-a | `_emit_sla_notification` (`:907`) | scheduler SLA-breach scan Asset Repair (warning/breach) | `:931` | recipient của WO |
| SLA-b | (incident SLA emitter, `_dispatch` `:1116`) | scheduler SLA-breach sự cố (tiếp nhận/xử lý) IMM-12 | `:1116` | recipient sự cố |

> **Lưu ý số dòng:** cột "def" = vị trí `def notify_*`; cột "fan-out" = dòng gọi `_dispatch(...)` THẬT (nơi kênh #3 thực sự chèn — vì kênh #3 nằm TRONG thân `_dispatch:366`, các dòng fan-out chỉ là call-site). 7 call-site `_dispatch` đầy đủ: `:452 :498 :562 :627 :791 :931 :1116` (verified `grep -n "_dispatch(" notifications.py`, 2026-06-09). Phase E chèn 1 lần trong `_dispatch:366` ⇒ phủ cả 7.
> **Đối chiếu task:** task nêu điểm fan-out `:416/461/506/578/752` — đó là **vị trí def** 5 dispatch fn (E1-E5), KHÔNG phải dòng gọi `_dispatch`. Doc này ghi CẢ HAI để không nhầm; điểm chèn kênh #3 THẬT = trong `_dispatch:366`.

### 3.3 Vì sao chèn tại `_dispatch` (1 điểm), KHÔNG per-event

- `_dispatch` đã: dedupe `users` (`:380`), có `document_type`/`document_name` (`:374-375` → dùng dựng deep-link §4). Chèn kênh #3 tại đây = mọi event (kể cả event mới Phase F) tự có push.
- KHÔNG bồi push vào từng `notify_*` ⇒ tránh drift + tránh quên event mới.

---

## 4. Payload FCM + deep-link native

### 4.1 Cấu trúc payload (FCM HTTP v1 message)

```jsonc
{
  "message": {
    "token": "<fcm_token của 1 device enabled>",
    "notification": {
      "title": "<title VI ngắn>",          // vd: "Cần duyệt: PM Work Order PMWO-2026-0042"
      "body":  "<body VI>"                 // rút gọn ≤1000 ký tự, strip HTML (giống Frappe :122-128)
    },
    "data": {                               // data-only → APK tự điều hướng (KHÔNG render từ notification)
      "doctype":  "PM Work Order",          // = _dispatch document_type (:374)
      "name":     "PMWO-2026-0042",         // = _dispatch document_name (:375)
      "event":    "approval_pending",       // mã event (E1..E5/sla) — APK map UX
      "deeplink": "assetcore://wo/pm/PMWO-2026-0042"  // §4.2
    },
    "android": { "priority": "high" }       // incident/SLA-breach = high; PM-due = normal (Phase E tinh chỉnh)
  }
}
```

- **title/body tiếng Việt:** tái dùng `subject`/`message` mà `_dispatch` đã dựng (cùng nội dung in-app/email) → strip HTML cho push (Frappe strip pattern `push_notification.py:127-128`; body ≤1000 ký tự `:122`).
- **data-only routing:** deep-link đặt trong `data` (KHÔNG chỉ trong `notification`) để APK điều hướng cả khi app foreground/background.

### 4.2 Ánh xạ deep-link → route native (`data.deeplink`)

> Native KHÔNG dùng deep-link SPA `/a/<token>` (`ADR-MOBILE-001` consequences). Deep-link dạng custom-scheme `assetcore://<route>` để APK mở đúng màn.

| event (E#) | doctype | deeplink (đề xuất) | Màn native đích |
|---|---|---|---|
| E1 assignment | PM Work Order / Asset Repair | `assetcore://wo/<pm\|cm>/<name>` | Chi tiết phiếu được gán |
| E2 approval_pending | (theo doctype) | `assetcore://approve/<doctype>/<name>` | Màn duyệt |
| E3 incident_created | Incident Report | `assetcore://incident/<name>` | Chi tiết sự cố |
| E4 calibration_due | AC Asset | `assetcore://asset/<asset_name>` | Hồ sơ thiết bị (cờ overdue — `05-personas §`) |
| E5 escalation | PM Work Order | `assetcore://wo/pm/<name>` | Chi tiết WO escalation |
| SLA-a/b | Asset Repair / Incident Report | `assetcore://wo/cm/<name>` · `assetcore://incident/<name>` | Phiếu sắp/đã vi phạm SLA |

- APK parse `data.deeplink` → router native push màn tương ứng; nếu chưa login → giữ deeplink, mở sau khi đăng nhập (D-AUTH).
- Tên route native CHỐT ở **repo native Phase D**; bảng trên là HỢP ĐỒNG đề xuất (BE chỉ phát `doctype/name/event/deeplink`, KHÔNG ép route native cụ thể).

---

## 5. opt-in/opt-out · bảo mật server-key · threat · audit NĐ98

### 5.1 opt-in / opt-out (mức field `enabled`)

- **opt-in:** APK register token → `enabled=1`. User chưa register = không nhận push (mặc định an toàn).
- **opt-out:** user tắt push trong APK → PATCH `enabled=0` (giữ record cho audit). Có thể opt-out per-device (mỗi token 1 record).
- **Wiring chi tiết để Phase E:** mức field `enabled` là SSoT on/off ở tầng push. Tích hợp với "Cài đặt thông báo" hiện có (`_user_wants_email` cho email) → Phase E quyết định gộp/tách preference push vs email. KHÔNG đụng ở Phase A.

### 5.2 Bảo mật server-key / credentials (site_config — KHÔNG commit, KHÔNG trả qua API)

- **FCM service-account credentials JSON** (hoặc đường dẫn tới file) lưu trong **`site_config.json`** (vd `fcm_service_account_path` / `fcm_project_id`) — set bởi USER khi go-live (HARD-STOP, cùng nhóm với `assetcore_qr_base_url`/`allow_cors` ở `02-deploy-feasibility §7`).
- **TUYỆT ĐỐI KHÔNG:** commit credentials vào repo; KHÔNG trả credentials/server-key qua bất kỳ API nào; KHÔNG log credentials. Cùng kỷ luật `site_config` mà Frappe relay đã dùng cho `api_secret` (`get_password`, không lộ — `push_notification.py:202`).
- BE đọc credentials lúc gửi FCM (Phase E), KHÔNG bao giờ đẩy xuống client. APK KHÔNG biết server-key — chỉ biết `fcm_token` của chính nó (do FCM SDK cấp).
- **Quy trình THỰC THI đặt creds go-live (runbook, HARD-STOP USER):** numbered steps đặt `fcm_service_account_path`/`fcm_project_id` trong `site_config` (cùng nhóm `allow_cors`/host) + rollback xoay key khi lộ → **[`10-deploy-ops.md §4`](./10-deploy-ops.md)** (`10` = execute go-live; doc này = spec cơ chế/bảo mật).

### 5.3 Threat model

| Threat | Vector | Chặn |
|---|---|---|
| **Token leak** | `fcm_token` của user A bị lộ | Token chỉ cho phép FCM đẩy tới đúng thiết bị; nội dung push KHÔNG chứa secret (chỉ doctype/name/VI text). Lộ token ⇒ tối đa nhận push trùng, không leo quyền. |
| **Spoof register cho user khác** | Client gửi `register_device_token` với `user=<nạn nhân>` | **RBAC chặn:** server ÉP `user = frappe.session.user` (KHÔNG nhận `user` từ client). Row-level self-scope (§2.3) ⇒ không thể tạo/sửa token cho user khác. |
| **Đánh cắp server-key** | Lộ FCM service-account | Credentials chỉ trong `site_config` (§5.2), không qua API/log/repo. Rò rỉ = sự cố vận hành (xoay credentials ở Firebase console). |
| **Token chết gửi rác** | FCM token đã unregister | invalidate-on-401 (§2.5) tự disable. |
| **Đăng ký token spam** | 1 user spam nhiều token | dedup theo `fcm_token` (§2.4) + có thể rate-limit endpoint register (Phase E, theo pattern rate-limit endpoint nhạy cảm hiện có). |

### 5.4 Audit NĐ98 (register / unregister)

- **register_device_token** + **unregister_device_token** PHẢI sinh **audit trail** (NĐ98 — truy xuất ai-đăng-ký-thiết-bị-nào-khi-nào). DocType AC Mobile Device Token là record bất biến đủ làm bằng chứng (create/modify/owner tự có trong Frappe doc metadata); nếu cần chain mạnh hơn → bồi lifecycle audit (SHA-256 chain `utils/lifecycle.py`) ở Phase E theo pattern các action nghiệp vụ khác.
- **Notification Log (kênh 1) GIỮ là bằng chứng gửi** — push KHÔNG thay (§3.1). Bản ghi NĐ98 về "đã thông báo" vẫn ở Notification Log, không phụ thuộc FCM nhận hay không.

### 5.5 KHÔNG bồi notification list/read endpoint (Phase D/E)

- Tài liệu này KHÔNG đặc tả endpoint đọc/đánh-dấu-đã-đọc danh sách thông báo (notification list/read) — đó là **Phase D/E**. Chỉ tham chiếu: in-app list dùng Notification Log của Frappe (kênh 1). Phase D/E sẽ chốt endpoint mobile cho notification inbox nếu cần.

---

## 6. Bounds (ranh giới phase — KHÔNG overlap)

| Phase | Việc thuộc phase | Doc này (A5) làm gì |
|---|---|---|
| **A (A5 — doc này)** | Chốt cơ chế push (ADR-002) + spec DocType device-token + MAP 6-event + payload/deep-link + bảo mật/threat/audit (đặc tả) | ✔ Toàn bộ §0-§6 |
| **B — Provisioning** | Set FCM credentials `site_config` (cùng `allow_cors`/host) — HARD-STOP USER | Chỉ nêu yêu cầu (§5.2) |
| **C — API contract** | Bồi schema request/response device-token đầy đủ; namespace `api/mobile/v1` | OpenAPI chỉ STUB 2 path (shape/security/operationId) |
| **D — Repo native MVP** | APK lấy FCM token + gọi register + handle deep-link + opt-out UI | Chỉ HỢP ĐỒNG payload/deep-link (§4) |
| **E — Push/Offline/Sync (IMPL)** | Chèn kênh #3 trong `_dispatch`; tạo DocType + controller + RBAC wiring; gửi FCM HTTP v1; invalidate-on-401; rate-limit register | Doc này là spec ĐẦU VÀO cho E |
| **B (device/session registry — nếu tách)** | Registry phiên/thiết bị mức auth | KHÔNG overlap: device-token = registry PUSH (FCM), khác session/OAuth Bearer Token registry |

> **Không overlap với Phase B device/session registry:** AC Mobile Device Token chỉ map `user → fcm_token` cho mục đích PUSH. Quản lý phiên đăng nhập / revoke OAuth token là việc của OAuth Bearer Token (`03-auth-oauth2.md §2`) — 2 thực thể khác nhau, KHÔNG gộp.

---

## 7. Tham chiếu chéo

- Tổng quan + 3 quyết định + convention số: [`00-overview.md`](./00-overview.md) (§3 roadmap Phase E = push impl; §6 convention số)
- Kiến trúc + điểm chèn push: [`01-architecture.md`](./01-architecture.md) (§6.1 Push channel #3 tại `_dispatch`)
- Feasibility (push gap): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) (§0 TL;DR FCM · §6 row Push · §7 gap #7)
- Auth (bearer cho register): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- Hợp đồng envelope/error: [`04-api-contract.md`](./04-api-contract.md)
- Persona field-tech (nhận push): [`05-personas-mvp.md`](./05-personas-mvp.md)
- **ADR cơ chế push (chốt):** [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md)
- ADR kiến trúc nền: [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- **Bảo mật & Tuân thủ (A7) — SSoT bảo mật mobile** (threat device-token §5.3 ở doc này được phủ trong bề mặt mobile toàn cảnh; server-key/site_config = nhóm config-go-live): [`08-security-compliance.md`](./08-security-compliance.md) (T4 token storage · §3 nhóm b) · ADR mô hình bảo mật: [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- OpenAPI (2 path STUB device-token): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- Engine thông báo (insert kênh #3): `assetcore/services/notifications.py::_dispatch`
- RBAC SSoT (self-scope/vendor isolation pattern): `assetcore/permissions.py` · `assetcore/services/shared/rbac.py`
- Frappe relay (lý do KHÔNG dùng): `frappe/push_notification.py` · `Push Notification Settings` doctype
