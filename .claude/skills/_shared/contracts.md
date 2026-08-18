# Hợp đồng BE ↔ FE (dùng chung)

> SSoT của phần **giao diện giữa hai phía**. Skill BE/FE/test và agent be-dev/fe-dev/qa trỏ tới đây.
> Chi tiết đầy đủ pipeline thông báo: `assetcore-be/references/notification-contract.md`.

## 1. Envelope — mọi phản hồi đi qua một đường

```
service  → nthrow(MSG.<CODE>, **ctx)   → ServiceError(message_code, http_status, context)
api      → handle(...)                 → envelope hydrate từ registry
FE       → ApiError(messageCode, context, severity, title, actionHint)
FE       → useNotify → severity routing: success|info|warning|error → toast · critical → modal
```

- Registry **duy nhất**: `assetcore/utils/messages.py`. Không `frappe.throw(_("chuỗi"))`,
  không `ServiceError(..., "literal")`, không `toast.error("chuỗi")` cho lỗi nghiệp vụ.
- Envelope luôn có `message_code` + `severity`. Thiếu một trong hai = vi phạm hợp đồng.
- `http_status` quyết định bucket `ErrorCode`: 400 INVALID_PARAMS · 401 UNAUTHORIZED ·
  403 FORBIDDEN · 404 NOT_FOUND · 409 CONFLICT · 422 BUSINESS_RULE · 429 RATE_LIMITED · 500 INTERNAL.

## 2. Ba bẫy status-line (client/test hay branch nhầm)

| Bẫy | Thực tế | Phải làm |
|---|---|---|
| Lỗi nghiệp vụ 404/409/422 | trả **trên HTTP-200**, status-line KHÔNG phản ánh | branch theo `envelope.http_status` / `code`, **không** theo HTTP status-line |
| Hai loại 403 | dispatcher-403 (chưa auth → re-auth) ≠ in-handler cap-403 (đã auth, thiếu quyền → hiện message) | phân biệt trước khi tự động đăng nhập lại |
| DocType hook raise | `frappe.ValidationError` ra **HTTP 417**, kèm `frappe.local.response["message_code"]` | test/FE đọc `message_code`, không đọc status |

## 3. Không rò rỉ nội bộ

- `except Exception` → `log_error(get_traceback())` + message **HẰNG**. Không `_err(str(e))`.
- Message lỗi trùng-định-danh **không** được lộ bản ghi hiện hữu (`{ref}` của record người khác).
- Mọi `@frappe.whitelist()` **mutating** phải gate bằng capability ở đầu thân hàm
  (`rbac.require` / `has_any_role`), **không** gate bằng tên role (role-name không tồn tại = bypass âm thầm).

## 4. Hợp đồng khi BE ‖ FE chạy SONG SONG

Khi hai phía cùng làm một lượt, symbol phía kia **có thể chưa có trên đĩa**. Trước khi bind/gọi
bất kỳ khoá payload · endpoint · hằng số nào của phía kia:

```bash
grep -rn "<symbol>" assetcore/      # FE kiểm BE
grep -rn "<symbol>" frontend/src/   # BE kiểm FE
```

**0 hit ⇒ ba việc bắt buộc:**
1. Viết mã **fail-safe** — thiếu khoá không được làm vỡ UI hay luồng.
2. Liệt kê symbol đó vào `contract_unverified` trong báo cáo.
3. **KHÔNG** tuyên bố acceptance liên quan đã đạt.

Chỉ ghi vào `landed_symbols` những thứ **chính mình vừa grep lại thấy** sau khi sửa
(định dạng `symbol → file:line`) — không ghi dự định.

> Đây là bài học có giá: FE từng ship consumer của `create_prefill` mà BE chưa bao giờ emit ⇒
> hợp đồng chết, nút mở màn tạo trống.

## 5. Trường mới = additive/optional

Thêm field vào envelope/API: **optional + có default an toàn**. Không đổi ý nghĩa field cũ,
không fork `*_v2`. Client cũ phải chạy tiếp không sửa gì.

## 6. Nguồn danh sách người dùng

Mọi ô chọn người **phải** qua `ApproverSelect context="user"|capability` /
`list_assignable_users`. Không `SmartSelect doctype="User"` trần — "user AssetCore" được định nghĩa
bằng base role `AssetCore System User`, không phải bằng bảng `User`.
