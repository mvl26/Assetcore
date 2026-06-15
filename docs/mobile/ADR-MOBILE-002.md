# ADR-MOBILE-002 — Cơ chế push notification cho mobile: FCM Admin SDK trực tiếp

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-002 |
| Phase | A — Kiến trúc & Feasibility (A5 — Push FCM design) |
| Ngày | 2026-06-09 |
| Tác giả | BA Lead + System Architect (mobile) |
| **Status** | **Accepted** |
| Bám quyết định | D-AUTH · D-MVP · D-STACK (`00-overview.md §2`) · ADR-MOBILE-001 (kiến trúc nền) |
| Đặc tả đi kèm | [`06-push-fcm.md`](./06-push-fcm.md) (DocType device-token · MAP 6-event · payload · threat/audit) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source **Frappe v15.107.2** (site `miyano`, 2026-06-09).

---

## Context

ADR-MOBILE-001 đã chốt kiến trúc nền mobile (wire OAuth · RBAC 1 SSoT · reuse endpoint · OpenAPI hợp đồng · bearer-không-cookie) và ghi rõ: **push là channel #3 chèn tại `services/notifications.py::_dispatch`, thuộc Phase E** (ADR-001 decision (c) + consequences). Engine thông báo hiện có **2 kênh**: in-app (Notification Log) + email (`_safe_sendmail`).

Phase A5 phải chốt **cơ chế gửi push thực tế** trước khi Phase E impl, để không đi sai hướng (đặc biệt: bệnh viện NĐ98 thường self-host / air-gapped, không cho gọi ra Internet tới dịch vụ bên thứ ba ngoài tầm kiểm soát).

Có 2 con đường khả dĩ:
1. **Reuse `frappe.push_notification`** (module push có sẵn của Frappe v15).
2. **Gọi FCM Admin SDK / FCM HTTP v1 TRỰC TIẾP** từ BE, credentials trong `site_config`.

### Khảo sát source (đã verify read-only)

`frappe/push_notification.py` **KHÔNG gọi FCM trực tiếp** — mọi hàm là proxy POST tới **central relay server của Frappe Cloud** (`notification_relay.api.*`):

- `add_token` → `notification_relay.api.token.add` — `push_notification.py:27-29`
- `remove_token` → `notification_relay.api.token.remove` — `push_notification.py:40-42`
- `send_notification_to_user` → `notification_relay.api.send_notification.user` — `push_notification.py:130-133`
- `send_notification_to_topic` → `notification_relay.api.send_notification.topic` — `push_notification.py:175-178`
- mọi gửi qua `_send_post_request` → cần `frappe.conf.push_relay_server_url` + `is_enabled()` — `push_notification.py:240-251`
- `is_enabled()` đọc `Push Notification Settings.enable_push_notification_relay` — `push_notification.py:187-189`
- nếu relay tắt → raise `"Push Notification Relay is not enabled"` — `push_notification.py:240-241`
- credentials lấy bằng đăng ký với relay (`get_credential`) — `push_notification.py:217`

Doctype `Push Notification Settings` xác nhận tường minh bản chất relay:
> "Enabling this will **register your site on a central relay server** to send push notifications for all installed apps through Firebase Cloud Messaging." — `push_notification_settings/push_notification_settings.json:6` (field `enable_push_notification_relay:19-21`, `api_key:30-32`, `api_secret:35-37`).

⇒ Đường Frappe có sẵn **bắt buộc đi qua máy chủ relay Frappe Cloud** (đăng ký site + gọi ra Internet). KHÔNG phù hợp self-host / air-gapped / NĐ98 (mạng nội bộ bệnh viện không cho phụ thuộc Frappe Cloud cho thông báo nghiệp vụ).

---

## Decision

> **Push notification cho mobile = gọi FCM Admin SDK / FCM HTTP v1 TRỰC TIẾP từ AssetCore BE**, dùng **service-account credentials JSON lưu trong `site_config.json`** (KHÔNG commit, KHÔNG trả qua API). **KHÔNG** reuse `frappe.push_notification` (relay Frappe Cloud).

Hệ quả thiết kế (đặc tả chi tiết ở [`06-push-fcm.md`](./06-push-fcm.md)):

1. **Kênh #3 chèn tại `_dispatch`** (`notifications.py:366`) — SAU kênh 1 in-app + kênh 2 email, cùng `users` dedupe + `doc` reference. 1 điểm fan-out ⇒ mọi event (E1-E5 + 2 SLA emitter, 7 call-site `_dispatch` `:452/:498/:562/:627/:791/:931/:1116`) tự có push, KHÔNG sửa call-site. **In-app + email GIỮ NGUYÊN — push CHỈ THÊM.**
2. **Device-token registry tự quản:** DocType `AC Mobile Device Token` (map `user→fcm_token`, dedup UNIQUE token, RBAC self-scope bám SSoT `permissions.py`, invalidate-on-401). KHÔNG lệ thuộc token store của relay.
3. **Credentials trong `site_config`** (set bởi USER khi go-live, HARD-STOP — cùng nhóm `allow_cors`/`assetcore_qr_base_url`). BE đọc lúc gửi; KHÔNG đẩy xuống client; KHÔNG log; KHÔNG commit.
4. **Fail-safe:** lỗi gửi FCM KHÔNG vỡ in-app/email (pattern `_safe_sendmail`).

---

## Alternatives considered

| # | Phương án | Vì sao LOẠI / chọn |
|---|---|---|
| **B1** | **Reuse `frappe.push_notification` (relay Frappe Cloud)** | Bắt buộc đăng ký site lên central relay Frappe Cloud + gọi ra Internet (`push_notification.py:27-251`, doctype desc `:6`). **Trái mô hình air-gapped/on-prem NĐ98** — bệnh viện không cho phụ thuộc dịch vụ ngoài cho thông báo nghiệp vụ; token store + gửi nằm ngoài tầm kiểm soát site; RBAC/audit AssetCore không áp được lên token store relay. ⇒ **LOẠI.** |
| **B2 (CHỌN)** | **FCM Admin SDK / HTTP v1 trực tiếp, credentials site_config** | Site chỉ cần outbound HTTPS tới `fcm.googleapis.com` (whitelist được); credentials hoàn toàn trong tầm kiểm soát site; device-token registry tự quản ⇒ RBAC + audit NĐ98 (1 SSoT) áp dụng nguyên. ⇒ **CHỌN.** |
| B3 | **Tự dựng push server riêng (APNs/FCM gateway nội bộ)** | Tốn hạ tầng + vận hành; FCM đã là gateway chuẩn cho Android (D-STACK android trước). Không cần thêm lớp. ⇒ LOẠI (over-engineering cho MVP). |
| B4 | **WebSocket/realtime của Frappe (socketio) thay push** | Chỉ hoạt động khi app đang mở/kết nối; KHÔNG đánh thức app nền → không phải push thật cho field-tech rời máy. ⇒ LOẠI (không thay được push background). |
| B5 | **Email/SMS thay push** | Đã có email (kênh 2); SMS tốn phí + không deep-link mở màn native. Push miễn phí + deep-link. ⇒ LOẠI (push bổ sung, không thay). |

---

## Consequences

**Tích cực:**
- Air-gapped/on-prem khả thi: không phụ thuộc Frappe Cloud relay; credentials + token store trong tầm kiểm soát site (NĐ98).
- RBAC + audit 1 SSoT: device-token registry tự quản ⇒ self-scope (user chỉ thấy token mình) + vendor isolation + audit register/unregister theo pattern hiện có (`permissions.py`, `utils/lifecycle.py`).
- Channel #3 tại 1 điểm `_dispatch` ⇒ mọi event tự có push, không drift, không sửa call-site; in-app/email bất biến.
- Deep-link `data` payload ⇒ APK mở đúng màn native (không dùng deep-link SPA `/a/<token>` — ADR-001).

**Đánh đổi / việc phải làm (carry sang Phase B/E):**
- **Blocker triển khai (Phase B/E, HARD-STOP USER):** set FCM service-account credentials trong `site_config` + đăng ký FCM project ở Firebase console + cho phép outbound HTTPS tới FCM. (Đổi site_config/migrate/reload thuộc USER.)
- **Phụ thuộc Google FCM:** vẫn là dịch vụ Google (không tránh được cho push Android tiêu chuẩn). Air-gapped TUYỆT ĐỐI (no-Internet) ⇒ push không khả dụng — fallback in-app/email vẫn chạy (đó là lý do giữ 2 kênh cũ làm SSoT audit). Ghi rõ cho khách hàng khi go-live.
- **Impl Phase E:** tạo DocType + controller + RBAC wiring (`permission_query_conditions`/`has_permission`) + gửi FCM HTTP v1 + invalidate-on-401 + rate-limit endpoint register. Spec đầy đủ ở `06-push-fcm.md`.
- **Library FCM:** Phase E chọn cách gọi (Firebase Admin SDK Python HOẶC gọi REST FCM HTTP v1 + tự ký OAuth2 service-account token) — quyết định ở Phase E kèm test; ADR này chỉ chốt "direct, không relay".

---

## Tham chiếu chéo

- Đặc tả push đầy đủ (DocType/MAP/payload/threat/audit): [`06-push-fcm.md`](./06-push-fcm.md)
- ADR kiến trúc nền (channel #3 tại `_dispatch`, Phase E): [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- Kiến trúc — điểm chèn push: [`01-architecture.md §6.1`](./01-architecture.md)
- Feasibility — push gap: [`02-deploy-feasibility.md §0/§6/§7`](./02-deploy-feasibility.md)
- Engine thông báo: `assetcore/services/notifications.py::_dispatch`
- Frappe relay (lý do LOẠI B1): `frappe/push_notification.py` · `Push Notification Settings` doctype
