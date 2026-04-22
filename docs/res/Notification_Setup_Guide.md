# AssetCore — Notification Setup Guide

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | Hướng dẫn cấu hình Notification trên Frappe Desk cho AssetCore |
| Phiên bản | 1.0.0 |
| Ngày | 2026-04-20 |
| Đối tượng | System Admin / IMM Operations Manager |
| Phụ thuộc | Frappe v15 (DocType `Notification`, `Notification Log`) |

---

## 1. Tổng quan kiến trúc

Frappe có 2 DocType liên quan:

- **`Notification`** (rule definition) — bạn tạo qua Desk; định nghĩa **khi nào** gửi, **gửi cho ai**, **template** ra sao.
- **`Notification Log`** (instance) — Frappe tự sinh ra mỗi lần điều kiện `Notification` đúng. Đây là bảng frontend đọc qua endpoint `assetcore.api.layout.get_unread_notifications`.

Khi user click chuông trên AppTopBar:
1. FE gọi `get_unread_notifications` → đọc Notification Log.
2. User click 1 item → FE call `mark_notification_as_read` + dùng `resolveNotificationRoute(document_type, document_name)` để điều hướng sang trang chi tiết DocType tương ứng.

**Để FE điều hướng đúng**, mọi rule Notification phải đảm bảo trường `Document Type` và `Document Name` được Frappe ghi vào Notification Log (Frappe tự xử lý khi `Send to: Email` hoặc `Send Alert On: Save/Submit/...`).

---

## 2. Truy cập trang cấu hình

Trên Frappe Desk:

```
http://<site>/app/notification
```

Hoặc menu **Settings → Notification**.

Click **+ New** để tạo rule mới.

---

## 3. Mẫu cấu hình các rule chính

### 3.1 IMM-04 — Phiếu Commissioning chuyển sang `Pending_Doc_Verify`

| Trường | Giá trị |
|---|---|
| **Subject** | `Phiếu nghiệm thu {{ doc.name }} cần kiểm tra hồ sơ` |
| **Channel** | `System Notification` (mặc định cho Notification Log) |
| **Document Type** | `Asset Commissioning` |
| **Send Alert On** | `Value Change` |
| **Value Changed** | `workflow_state` |
| **Condition** | `doc.workflow_state == "Pending_Doc_Verify"` |
| **Recipients → Receiver by Role** | `IMM Document Officer` |
| **Message (Markdown)** | `Phiếu **{{ doc.name }}** từ NCC {{ doc.vendor }} đã chuyển sang trạng thái Pending_Doc_Verify. Vui lòng kiểm tra CO/CQ/Manual.` |

→ FE sẽ điều hướng tới `/commissioning/{name}` khi user click.

---

### 3.2 IMM-05 — Asset Document sắp hết hạn (≤ 30 ngày)

> Notification "Days Before" yêu cầu Frappe Scheduler chạy daily.

| Trường | Giá trị |
|---|---|
| **Subject** | `Tài liệu {{ doc.doc_type_detail }} sắp hết hạn` |
| **Document Type** | `Asset Document` |
| **Send Alert On** | `Days Before` |
| **Days Before** | `30` |
| **Date Field** | `expiry_date` |
| **Condition** | `doc.workflow_state == "Active" and doc.expiry_date` |
| **Recipients → Receiver by Role** | `Tổ HC-QLCL` (hoặc `IMM Document Officer`) |
| **Message** | `Tài liệu **{{ doc.doc_type_detail }}** của thiết bị {{ doc.asset_ref }} sẽ hết hạn vào {{ doc.expiry_date }}.` |

→ Cron `frappe.email.doctype.notification.notification.trigger_offset_alerts` chạy mỗi sáng.

---

### 3.3 IMM-05 — Document chuyển trạng thái `Pending_Review`

| Trường | Giá trị |
|---|---|
| **Subject** | `Tài liệu {{ doc.name }} chờ duyệt` |
| **Document Type** | `Asset Document` |
| **Send Alert On** | `Value Change` |
| **Value Changed** | `workflow_state` |
| **Condition** | `doc.workflow_state == "Pending_Review"` |
| **Recipients → Receiver by Role** | `IMM QA Officer` |

---

### 3.4 IMM-08 — PM Work Order `Overdue`

| Trường | Giá trị |
|---|---|
| **Subject** | `PM Work Order {{ doc.name }} quá hạn` |
| **Document Type** | `PM Work Order` |
| **Send Alert On** | `Value Change` |
| **Value Changed** | `status` |
| **Condition** | `doc.status == "Overdue"` |
| **Recipients** | `Receiver by Document Field: assigned_to` + `Receiver by Role: IMM Workshop Lead` |
| **Message** | `Phiếu PM **{{ doc.name }}** cho thiết bị {{ doc.asset_ref }} đã quá hạn. Hạn dự kiến: {{ doc.due_date }}.` |

---

### 3.5 IMM-08 — PM Sắp đến hạn (≤ 7 ngày)

| Trường | Giá trị |
|---|---|
| **Document Type** | `PM Work Order` |
| **Send Alert On** | `Days Before` |
| **Days Before** | `7` |
| **Date Field** | `due_date` |
| **Condition** | `doc.status in ("Open", "Assigned")` |
| **Recipients → Receiver by Document Field** | `assigned_to` |

---

### 3.6 IMM-09 — CM Work Order vi phạm SLA

| Trường | Giá trị |
|---|---|
| **Document Type** | `Asset Repair` |
| **Send Alert On** | `Value Change` |
| **Value Changed** | `sla_breached` |
| **Condition** | `doc.sla_breached == 1` |
| **Recipients → Receiver by Role** | `IMM Department Head, IMM Operations Manager` |

---

### 3.7 IMM-09 — Tái hỏng (Repeat Failure)

| Trường | Giá trị |
|---|---|
| **Document Type** | `Asset Repair` |
| **Send Alert On** | `Value Change` |
| **Value Changed** | `is_repeat_failure` |
| **Condition** | `doc.is_repeat_failure == 1` |
| **Recipients → Receiver by Role** | `IMM QA Officer` |

---

### 3.8 IMM-12 — Incident Critical → bắt buộc CAPA

| Trường | Giá trị |
|---|---|
| **Document Type** | `Incident Report` |
| **Send Alert On** | `New` |
| **Condition** | `doc.severity == "Critical"` |
| **Recipients → Receiver by Role** | `IMM QA Officer, IMM System Admin` |
| **Subject** | `🚨 Critical Incident {{ doc.name }} - Asset {{ doc.asset }}` |

---

## 4. Mapping DocType → Route Frontend

`resolveNotificationRoute()` trong `frontend/src/api/layout.ts` hỗ trợ:

| DocType (BE) | Route FE |
|---|---|
| `AC Asset` | `/assets/<name>` |
| `Asset Document` | `/documents/view/<name>` |
| `Asset Commissioning` | `/commissioning/<name>` |
| `PM Work Order` | `/pm/work-orders/<name>` |
| `Asset Repair` / `CM Work Order` | `/cm/work-orders/<name>` |
| `Incident Report` | `/incidents/<name>` |
| `IMM CAPA Record` | `/capas/<name>` |
| `Asset Transfer` | `/asset-transfers/<name>` |
| `Service Contract` | `/service-contracts/<name>` |
| `IMM Calibration` / `Calibration Result` | `/calibration/<name>` |
| `IMM Device Model` | `/device-models/<name>` |
| `AC Supplier` | `/suppliers/<name>` |
| `Document Request` | `/documents/requests` |
| `Firmware Change Request` | `/cm/firmware` |

Khi thêm DocType mới: cập nhật map `DOCTYPE_TO_ROUTE` trong `layout.ts` cùng với khai báo route trong `router/index.ts`.

---

## 5. Test rule sau khi tạo

1. Tại trang Notification rule → click **Menu (3 chấm) → Send Test Email** để verify template render.
2. Tạo / sửa 1 record DocType target để trigger event thực — ví dụ chuyển workflow `Asset Commissioning` để rule §3.1 fire.
3. Verify Notification Log:
   ```
   http://<site>/app/notification-log
   ```
   filter `For User = <recipient email>`.
4. Login FE → kiểm tra chuông hiển thị badge số chưa đọc → click → điều hướng đúng route.

---

## 6. Troubleshooting

| Triệu chứng | Nguyên nhân & cách fix |
|---|---|
| Notification rule không fire | Kiểm tra `Enabled = 1`; condition syntax (Jinja2 + Python expression). |
| Notification Log tạo nhưng không có `document_type` | Rule dùng channel `Email` only — phải bật `System Notification`. |
| FE click → trang trắng | DocType chưa có trong `DOCTYPE_TO_ROUTE` → fallback về `/dashboard`. Bổ sung mapping. |
| "Days Before" không trigger | Frappe Scheduler chưa chạy → `bench --site <site> scheduler enable && bench --site <site> scheduler resume`. |
| Notification chỉ gửi cho creator | Recipients để trống `Receiver by Role` — phải set rõ Role hoặc Document Field. |

---

## 7. Tham chiếu

- Backend API: `assetcore/api/layout.py`
- Frontend API: `frontend/src/api/layout.ts`
- AppTopBar component: `frontend/src/components/common/AppTopBar.vue`
- Frappe Notification docs: https://docs.frappe.io/framework/user/en/notification
- IMM workflow specs: `docs/imm-04..09/IMM-XX_Functional_Specs.md`

---

*Cập nhật khi thêm DocType vào FE router hoặc thay đổi role mapping — 2026-04-20.*
