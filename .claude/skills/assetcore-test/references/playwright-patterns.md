# Playwright MCP — Patterns thường dùng trong AssetCore UI Test

## Login

```
browser_navigate: http://localhost:3000
browser_snapshot  → kiểm tra có redirect sang /login không
browser_fill_form: { "Email": "TEST_USER", "Mật khẩu": "TEST_PASSWORD" }
browser_click: "Đăng nhập" (hoặc button[type=submit])
browser_snapshot  → verify URL không còn là /login
```

### LL-QA-10: Login cần test-user có password biết-trước — sau cleanup chỉ còn 3 user gốc → BLOCKED-on-user

Triệu chứng → cần verify RBAC/anti-leak theo persona scoped (KTV/vendor) nhưng không login được vì không biết password user đó.
Nguyên nhân → sau cleanup DB chỉ còn 3 user gốc; persona scoped không có credential biết-trước.
Rule (kiểm được):
1. TRƯỚC live-walk @:3000: đọc `.env` lấy `TEST_USER`/`TEST_PASSWORD` (SKILL.md:482-490) — KHÔNG hardcode creds.
2. Cần persona scoped (KTV/vendor) để verify RBAC/anti-leak mà KHÔNG có user+pw → **BLOCKED**, báo USER cấp test-user. KHÔNG bịa login, KHÔNG dùng `Administrator` thay persona (Admin bypass mọi gate → false-green).
3. MCP unstable (OOM, lock) sau 2 recovery fail → fallback static code-audit, báo USER sớm (SKILL.md:569-592).
Cross-ref: SKILL.md:482-490 (.env creds), 569-592 (MCP recovery + fallback); LL-TEST-11/14 (role-gated ≠ bug).

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

### LL-QA-9: Artifact eval → kho bền `.playwright/eval/`; `.playwright-mcp/` chỉ là output tạm phải sweep sau mỗi run

Triệu chứng → ảnh `browser_take_screenshot` rơi mặc định vào `.playwright-mcp/` (kho output tạm), lẫn vào `git status`, suýt commit nhầm / không tập trung 1 chỗ.
Nguyên nhân → MCP default ghi ra `.playwright-mcp/` thay vì kho bền; không sweep → tích lũy rác transient (`page-*.yml`, `*.log`).
Rule (kiểm được):
1. Set `filename` của `browser_take_screenshot` = **path tuyệt đối dưới `.playwright/eval/`** (kho bền). Khi MCP vẫn rớt mặc định vào `.playwright-mcp/`, cuối session chạy:
   ```bash
   bash .claude/scripts/tidy-eval-artifacts.sh   # sweep .playwright-mcp/* → .playwright/eval/ + xoá page-*.yml / *.log transient
   ```
2. Báo cáo eval **THAM CHIẾU path dưới `.playwright/eval/`** — KHÔNG attach/đính kèm ra ngoài.
3. Self-check cuối session (phải RỖNG): `git status --porcelain -uall | grep -iE '\.(png|jpg|jpeg|webp)$'` → có output nghĩa là ảnh còn ngoài kho bền, chưa sweep.
Cross-ref: `.claude/scripts/tidy-eval-artifacts.sh:45-48` (sweep `.playwright-mcp` → `.playwright/eval`); `.gitignore:51-52` (cả 2 đã ignore); memory/feedback_tidy_eval_artifacts.md; R-11 ở SKILL.md (cùng mục tiêu hygiene — kho bền nay là `.playwright/eval/`).

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

**LL-QA-11 — Decision gate trước khi tuyên bố "FE bug":** khi Playwright click-flow cho kết quả SAI, nghi **Vite HMR instability TRƯỚC**, không vội báo FE bug. Chỉ kết luận FE bug thật khi đủ 3 điều kiện:
- (a) BE đúng qua `bench execute` (response/state mong đợi), VÀ
- (b) gọi handler trực tiếp trên component instance ra đúng + `npm run typecheck` sạch, VÀ
- (c) click-flow DOM vẫn SAI **lặp lại trên tab Vite mới khởi động sạch HOẶC `npm run build` + preview**.
(a)+(b) đúng mà (c) chỉ sai trên dev-server đã HMR nhiều lần = dev-server churn (v-model desync / instance churn), KHÔNG phải FE bug. Thêm `@frappe.whitelist()` mới → reload gunicorn trước (xem rule 4 / LL-QA-8 / LL-BE-16) để loại trừ `AttributeError` phantom.

Cross-ref: `assetcore-be` LL-BE-16 (werkzeug reload không tin cậy), LL-FE-27 (bench execute trước khi sửa FE), memory/gunicorn_preload_staleness.md; bug 2026-06-01 verify banner login G5 (cùng section trên).
