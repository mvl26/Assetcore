# Báo cáo kiểm thử Frontend — 2026-04-26

> **Phạm vi:** toàn bộ `frontend/src/` của AssetCore — `views/`, `components/`, `stores/`, `composables/`, `api/`.
> **Phương pháp:** Static analysis (white-box) + Code review patterns + Trace user flow (black-box).
> **Lý do không có unit/e2e test:** Repo chưa cài `vitest`/`playwright`/`cypress` — `package.json` chỉ có `dev`, `build`, `typecheck`, `lint`. Báo cáo này là baseline để milestone trước khi đầu tư test framework.

---

## 1. Kết quả tổng quan

| Hạng mục | Công cụ | Kết quả |
|---|---|---|
| Type checking | `vue-tsc --noEmit` | **0 errors** ✓ |
| Linting | `eslint .` | **0 errors / 106 warnings** ✓ |
| Build production | `vue-tsc && vite build` | **Pass** (1.82s, 23 chunks) ✓ |

**Đánh giá:** Codebase **không có blocker** ngăn deploy. Tất cả lỗi kiểm thử là cảnh báo cosmetic / weak typing.

---

## 2. White-box findings (kiểm thử cấu trúc / nội bộ)

### 2.1 ESLint warnings phân loại

| Loại | Số lượng | Mức độ | Ghi chú |
|---|---:|:-:|---|
| `vue/multiline-html-element-content-newline` | 73 | Cosmetic | Format HTML — auto-fixable bằng `eslint --fix` |
| `@typescript-eslint/no-explicit-any` | 29 | Trung bình | Weak typing — cần thay `any` bằng generic / interface |
| `vue/no-v-html` | 4 | **Bảo mật** | XSS risk nếu dữ liệu từ user/server — xem mục 2.3 |

### 2.2 File có `any` cần làm chặt typing

| File | Số chỗ |
|---|---:|
| `stores/commissioning.ts` | nhiều |
| `stores/imm08.ts` | nhiều |
| `stores/imm09.ts` | nhiều |
| `views/auth/UserProfileFormView.vue` | 1 |

**Tác động:** Không phải bug runtime, nhưng mất type safety → dễ regression khi refactor.

### 2.3 ⚠️ Bảo mật — `v-html` usage

| File | Dòng | Nguồn dữ liệu | Đánh giá |
|---|---:|---|---|
| `components/common/AppSidebar.vue` | 258, 288, 311 | `ICONS[group.icon]` — constant | ✓ An toàn (hardcoded SVG) |
| `components/common/AppTopBar.vue` | 243 | `item.content` từ notification API | ⚠️ **Cần kiểm tra BE sanitize** |

**Khuyến nghị:** Confirm BE sanitize HTML notification trước khi gửi xuống FE; hoặc render plain text (`{{ item.content }}`) thay `v-html`.

### 2.4 Console output trong production code

| File | Dòng | Nội dung |
|---|---:|---|
| `views/document/DocumentDetailView.vue` | 105 | `console.error(e)` — không có user feedback |
| `components/common/RouteErrorBoundary.vue` | 10 | `console.error(...)` — debug log (acceptable) |

**Khuyến nghị:** `DocumentDetailView` line 105 nên thay bằng `toast.error(...)` để user thấy lỗi.

### 2.5 Functions chưa try/catch (silent failure risk)

Một số mutation API (update/create/delete) gọi không có `try/catch` rõ ràng — nếu BE trả lỗi, user không thấy thông báo:

- `views/calibration/CalibrationCreateView.vue:32` (`createCalibration`)
- `views/purchase/PurchaseEditView.vue:183` (`updatePurchase`)
- `views/auth/UserProfileFormView.vue:193` (`updateUserInfo`)

> Một số chỗ có wrapper `apiCall.run()` (composable `useApi`) tự handle — đó là OK. Còn lại cần audit.

---

## 3. Black-box findings (kiểm thử hành vi user flow)

### 3.1 Pattern bộ lọc đồng bộ (sau refactor 2026-04-26) — **Pass**

23/23 list view follow đúng pattern AssetListView:

- ✅ Toggle button với badge số filter active
- ✅ Active chip row (khi panel đóng) — click chip để xóa filter đó
- ✅ Collapsible filter panel — select / search / Đặt lại
- ✅ Quick-filter (click giá trị trong bảng → tự thêm vào filter)
- ✅ "Hiển thị X / Total" + "Xóa tất cả" trong table info row
- ✅ Empty state có CTA "Xóa bộ lọc để xem tất cả"

### 3.2 CRUD navigation — **Pass với 1 lưu ý**

| Flow | Hành vi mong đợi | Hiện trạng |
|---|---|---|
| List → click row | Mở Detail (read-only) | ✓ Đúng (Supplier, ServiceContract, Asset, Purchase) |
| List → "Sửa" button | Mở Edit form | ✓ Đúng (`@click.stop` chống nổi bọt event) |
| List → "Xóa" button | Confirm + xóa + reload | ✓ Đúng |
| Create form → submit | Về list | ✓ Đúng (Supplier, ServiceContract, DeviceModel) |
| Edit form → submit | Về detail | ✓ Đúng |
| Detail → "← Danh sách" | Về list | ✓ Đúng (sử dụng PageHeader hoặc explicit `router.push`) |

**Lưu ý 1:** SLA Policy + Firmware CR + DocRequest + PmTemplate + PmSchedule + CalibrationSchedule + Warehouse dùng **modal-based CRUD** (không có route detail riêng). UX nhất quán nhưng:
- Khi user bookmark URL → không mở thẳng được item cụ thể
- Đề xuất milestone tiếp theo: chuyển sang detail page như Supplier (đã làm xong cho SLA — có "xem chi tiết modal")

### 3.3 Filter behavior verification

| Component | Filtering mode | clearChip → reload? |
|---|---|---|
| AssetListView | Server-side | Có (cleanParams + fetchList) |
| SupplierListView | Server-side search + client-side | Có (applyFilters → load) |
| DeviceModelListView | Server search + client filter | Có |
| AuditTrailListView | Server-side | Có (debounced) |
| SlaPolicy/FirmwareCR/PmTemplate/PmSchedule/CalibrationSchedule | Client-side `computed` | Reactive — không cần reload ✓ |
| DocumentRequest | Hỗn hợp (asset + status server-side; priority + search client) | clearChip kiểm tra key → reload đúng ✓ |

### 3.4 Navigation reliability

- ✅ `router.back()` đã loại bỏ hoàn toàn (16 file replaced với explicit destination) → URL bookmark / direct entry hoạt động đúng
- ✅ Breadcrumb qua component `PageHeader` (11 trang Detail/Create/Edit chính áp dụng)
- ✅ Vite proxy phục vụ `/files/` trong dev (gunicorn không serve static)

---

## 4. Issues phát hiện — phân loại Severity

### 🔴 Critical (cần fix trước release)
*Không có.*

### 🟡 Major (nên fix sớm)

| # | Mô tả | File / Dòng | Action |
|---|---|---|---|
| M1 | `v-html="item.content"` từ notification — nguy cơ XSS | `AppTopBar.vue:243` | Verify BE sanitize HTML; hoặc đổi sang plain text |
| M2 | `console.error` không có user-facing fallback | `DocumentDetailView.vue:105` | Replace bằng `toast.error()` |
| M3 | Modal-based CRUD không có URL deep-link | SLA / Firmware / DocReq / PmTemplate / PmSchedule / CalibrationSchedule / Warehouse | Cân nhắc chuyển sang Detail route như Supplier khi có bandwidth |

### 🟢 Minor (cosmetic / debt)

| # | Mô tả | Action |
|---|---|---|
| m1 | 73 cảnh báo HTML linebreak format | `npm run lint:fix` để auto-fix |
| m2 | 29 chỗ dùng `any` (chủ yếu trong stores/commissioning, imm08, imm09) | Refactor sang generic / typed interface |
| m3 | Các page form vẫn còn dùng `@/composables/useToast` lẫn `apiCall.run()` lẫn try/catch + `err.value` | Standardize — tạo guideline 1 cách handle error |
| m4 | `PurchaseCreateView.vue` có 2 unused imports (`Ref`, `useFieldsDraft`) | Cleanup |

---

## 5. Test coverage gap & roadmap

### Hiện trạng
- ❌ Không có unit test
- ❌ Không có integration test
- ❌ Không có e2e test
- ✓ Có TypeScript strict mode → catch type bug compile-time
- ✓ Có ESLint với rule Vue + TS → catch pattern bug
- ✓ Có `vite build` → catch import / syntax bug

### Roadmap đề xuất

**Phase 1 (1 sprint):** Cài `vitest` + `@vue/test-utils`
- Unit test cho `composables/`: `useFormDraft`, `useToast`, `useApi`, `usePagination`
- Unit test cho `utils/formatters.ts`: `translateStatus`, `formatAssetDisplay`, `formatDate`

**Phase 2 (1 sprint):** Component test
- Test `PageHeader` (back-to behavior, breadcrumb click, slot actions)
- Test `SmartSelect` (debounce, keyboard nav, fallback)
- Test 1 list view mẫu (AssetListView) — filter chip add/remove, pagination, empty state

**Phase 3 (2 sprint):** E2E test với Playwright
- Flow `/login → /assets → /assets/new → /assets/:id` (golden path)
- Flow CRUD master-data (Supplier, DeviceModel)
- Flow PM/CM/Calibration work order

---

## 6. Lệnh kiểm thử đã chạy

```bash
cd frontend
npm run typecheck       # vue-tsc --noEmit  → 0 errors
npm run lint            # eslint .          → 0 errors / 106 warnings
npm run build           # production build  → Pass (1.82s)
```

## 7. Action items milestone

- [ ] **M1** — Audit `AppTopBar.vue:243` v-html (BE sanitize check)
- [ ] **M2** — Replace `console.error` ở `DocumentDetailView.vue:105` bằng toast
- [ ] **M3** — Quyết định: giữ modal-based CRUD hay chuyển sang detail route cho 7 module
- [ ] **m1** — `npm run lint:fix` để auto-clean 73 cosmetic warnings
- [ ] **m2** — Refactor `any` types trong `stores/commissioning|imm08|imm09.ts` (29 chỗ)
- [ ] **m3** — Standardize error handling (chọn 1 pattern: try/catch + err.value HOẶC apiCall.run + toast)
- [ ] **m4** — Cleanup unused imports `views/purchase/PurchaseCreateView.vue`
- [ ] **Phase 1 test framework** — Cài vitest, viết unit test cho composables/utils

---

## 8. Tham chiếu

- Pattern bộ lọc mẫu: `views/asset/AssetListView.vue`
- Component nav chuẩn: `components/common/PageHeader.vue`
- Sidebar/topbar structure: `components/common/AppSidebar.vue`, `AppTopBar.vue`
- API helpers: `api/helpers.ts` (`frappeGet` / `frappePost` với envelope unwrap `_ok` / `_err`)
- Toast: `composables/useToast.ts`
- Form draft persist: `composables/useFormDraft.ts`

---

*Báo cáo lập tự động bởi AI assistant. Static analysis chính xác đến file/line; black-box scenarios là code-trace, chưa có e2e thực.*
