# Playwright MCP — Patterns thường dùng trong AssetCore UI Test

## Login

```
browser_navigate: http://localhost:3000
browser_snapshot  → kiểm tra có redirect sang /login không
browser_fill_form: { "Email": "TEST_USER", "Mật khẩu": "TEST_PASSWORD" }
browser_click: "Đăng nhập" (hoặc button[type=submit])
browser_snapshot  → verify URL không còn là /login
```

## Navigate và chờ

```
browser_navigate: http://localhost:3000/imm01/needs-requests
browser_wait_for: selector=".table-wrapper" (chờ table load)
browser_snapshot  → đọc DOM
```

## Tìm và click button

```
browser_snapshot  → đọc accessibility tree để tìm exact label
browser_click: "Tạo đề xuất"   ← dùng text label từ snapshot
```

## Fill form

```
browser_fill_form: {
  "Lý do lâm sàng": "text dài ≥ 200 ký tự...",
  "Số lượng": "2",
  "Năm mục tiêu": "2027"
}
```

## Select dropdown

```
browser_select_option: element="select[name=request_type]" value="New"
hoặc dùng label: browser_select_option: element=".form-select" value="Replacement"
```

## Verify toast notification

```
browser_snapshot  → tìm element có class toast hoặc text thông báo
browser_evaluate: "document.querySelector('.toast')?.textContent"
```

## Verify URL sau navigate

```
browser_evaluate: "window.location.pathname"
→ expect: "/imm01/needs-requests/NR-2026-00001"
```

## Verify state badge

```
browser_snapshot  → tìm StatusBadge có text "Submitted", "Approved", v.v.
browser_evaluate: "document.querySelector('[class*=status-badge]')?.textContent?.trim()"
```

## Resize để test responsive

```
browser_resize: { width: 375, height: 812 }
browser_snapshot  → kiểm tra layout
browser_resize: { width: 1440, height: 900 }  ← restore
```

## Network request assertion

```
browser_network_requests  → filter theo URL pattern "/api/method/assetcore.api.imm01"
→ verify status 200, không có 4xx/5xx
```

## Chụp screenshot khi FAIL

```
browser_take_screenshot  → lưu để đính vào báo cáo FAIL
```

## Workflow action button

AssetCore action bar ở bottom, sticky. Pattern:
```
browser_snapshot  → tìm "sticky bottom" section
browser_click: "Nộp đề xuất" / "Phê duyệt ✓" / "Bác đề xuất"
```

## Tab navigation

```
browser_click: "Chấm điểm ưu tiên"   ← tab label
browser_snapshot  → verify tab content visible
```

## Table row click → detail

```
browser_snapshot  → tìm tbody tr đầu tiên
browser_click: row text (ví dụ: "NR-2026-00001")
browser_evaluate: "window.location.pathname"
→ expect: chứa "/imm01/needs-requests/"
```

## Kiểm tra không có console error

```
browser_console_messages  → filter type="error"
→ expect: rỗng hoặc không có lỗi critical
```

## Modal interaction

```
browser_snapshot  → verify modal mở (có overlay/backdrop)
browser_fill_form: { "Người duyệt": "admin@hospital.vn" }
browser_click: "Xác nhận phê duyệt"
browser_snapshot  → verify modal đóng
```

## ⚠️ Pitfall: Vite dev/HMR instability — KHÔNG tin click-flow sau phiên reload dài

Bug đã gặp 2026-06-01 (verify banner login G5): sau phiên dev server (Vite) reload/HMR kéo dài, click-flow Playwright cho kết quả SAI **dù logic đúng** — `v-model` desync + component instance churn (`email` ref đọc ra `""` dù DOM có giá trị; instance đọc ≠ instance xử lý event). BE trả đúng (`bench execute`), gọi handler trực tiếp trên instance ra đúng state, nhưng click qua DOM không render banner.

**Quy tắc:**

1. Verify UI quan trọng (auth, form submit) trên **build preview** (`npm run build` + preview) hoặc **tab/Vite mới khởi động sạch**, KHÔNG trên dev server đã HMR nhiều lần.
2. Khi Playwright cho kết quả MÂU THUẪN với BE (`bench execute` đúng + typecheck sạch) → nghi **dev-server instability TRƯỚC**, không vội kết luận FE bug. Reload trang sạch / restart Vite rồi test lại.
3. Cross-check 3 tầng trước khi tuyên bố "FE bug": (a) BE response qua `bench execute`, (b) gọi handler trực tiếp trên component instance, (c) click-flow DOM. Chỉ khi (a)+(b) đúng mà (c) sai LẶP LẠI trên tab sạch mới là FE bug thật.
4. Lưu ý kèm: thêm `@frappe.whitelist()` method mới → phải reload gunicorn/bench (worker cũ `--preload` chưa nạp → `AttributeError`); verify `bench execute assetcore.api.X.method` chạy được TRƯỚC khi test qua HTTP/Playwright (xem `assetcore-deploy` troubleshooting + LL-BE-16).

Cross-ref: `assetcore-be` LL-BE-16 (werkzeug reload không tin cậy), LL-FE-27 (bench execute trước khi sửa FE).
