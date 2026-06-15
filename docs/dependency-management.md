# Dependency Management — AssetCore

> Mục tiêu: giữ thư viện **không bị rot / hết hỗ trợ (deprecated)** theo thời gian,
> với version được khai báo **rõ ràng** ở một nơi duy nhất cho mỗi bề mặt.

AssetCore có **2 bề mặt dependency** tách biệt — quản theo 2 cách khác nhau:

| Bề mặt | Khai báo ở | Cập nhật bằng | Ai quản |
|--------|-----------|---------------|---------|
| **Backend (Python)** | `pyproject.toml` → `[tool.bench.frappe-dependencies]` | `bench update` / `bench get-app` | Framework (Frappe) |
| **Frontend (Vue/Vite)** | `frontend/package.json` | Dependabot PR + `npm` | App |

---

## 1. Backend — Frappe-managed (KHÔNG pin lib lẻ)

AssetCore là một **Frappe app**: nó KHÔNG sở hữu dependency Python riêng. Toàn bộ
lib BE (`requests`, `pdfkit`, `openpyxl`, `redis`, `pydantic`, `cryptography`,
`PyYAML`, …) được **Frappe ghim & cài** qua `apps/frappe/pyproject.toml` (SSoT).
App chỉ import trực tiếp `frappe` + `yaml` — cả hai do Frappe cung cấp sẵn.

→ **Không pin lib BE trong app** (sẽ chọi resolver của site bench). Thay vào đó
ràng buộc **phiên bản framework** ở `pyproject.toml`:

```toml
[tool.bench.frappe-dependencies]
frappe = ">=15.0.0,<16.0.0"
```

`bench` đọc range này khi cài/cập nhật app và **cảnh báo khi frappe nằm ngoài
range** → đây chính là cơ chế chống "framework quá cũ". **Nâng frappe = nâng cả
lib BE** trong một bước có kiểm soát.

### Nâng framework (quy trình riêng, có chủ đích — KHÔNG tự động)
1. Đọc release notes Frappe major mới + breaking changes.
2. Trên **staging**: `bench update --version=version-16` (hoặc `bench get-app frappe --branch …`).
3. `bench --site <site> migrate` → chạy `bench run-tests` (BE suite).
4. Smoke test luồng nghiệp vụ chính → nếu xanh, mở range trong
   `[tool.bench.frappe-dependencies]` (vd `">=16.0.0,<17.0.0"`).
5. Commit + rollout prod.

> Packaging: app dùng `pyproject.toml` (flit_core) chuẩn Frappe v15. `setup.py` +
> `requirements.txt` cũ đã bỏ. Khi reinstall/migrate, verify bằng
> `bench setup requirements` (build editable đọc pyproject).

---

## 2. Frontend — `package.json` + Dependabot

`frontend/package.json` là SSoT cho FE. Mọi version dùng range `^` (cho minor/patch
tự trôi) và được Dependabot theo dõi (`.github/dependabot.yml`).

### Cadence
- **Hằng tuần**: Dependabot gom **minor/patch** vào 1 PR (`fe-minor-patch`). Merge
  sau khi CI xanh (gate bên dưới).
- **Major**: Dependabot mở **PR riêng từng package**. KHÔNG merge thẳng — chạy quy
  trình "wave" + sửa breaking-change (xem §3).
- **Hằng quý**: review thủ công `npm outdated` cho các major còn treo.

### Gate bắt buộc (phải XANH trước khi merge bất kỳ PR nâng cấp FE nào)
```bash
cd frontend
npm ci
npm test            # vitest — toàn bộ unit/component test
npm run typecheck   # vue-tsc --noEmit
npm run build       # vue-tsc + vite build
```
`npm run lint` là tham khảo (KHÔNG block; có debt pre-existing — xem §4).

---

## 3. Quy trình nâng major FE an toàn ("wave")
1. **Baseline xanh trước** (`npm ci` + 3 gate) — nếu baseline đỏ thì không quy được lỗi cho việc nâng.
2. Nâng theo nhóm rủi ro tăng dần, validate sau MỖI nhóm:
   - **A** minor/patch (`npm update`).
   - **B** tooling (typescript, vue-tsc, vitest, jsdom, plugin-vue, @types).
   - **C** lint stack (eslint, plugin-vue, vue-eslint-parser, typescript-eslint).
   - **D** runtime libs (vue-router, vue-i18n, @vueuse, **tailwind** — rủi ro code/visual cao nhất, làm sau cùng).
3. Sửa breaking-change ngay khi gate đỏ; chỉ sang nhóm kế khi xanh lại.
4. Major chạm **render/CSS** (tailwind) → BẮT BUỘC thêm **visual-QA** (Playwright screenshot các màn chính), vì `test`/`build` KHÔNG bắt được regression màu/spacing.

---

## 4. Exceptions — version giữ chủ ý (KHÔNG phải rot)

| Package | Giữ ở | Latest | Lý do |
|---------|-------|--------|-------|
| `tailwindcss` | **3.4.x** | 4.x | v4 đổi config model + cấm `@apply` component-class (cần chuyển ~8 class sang `@utility`) + đổi default ngầm (`border`→`currentColor`, ring width/color) → **cần migration + visual-QA riêng**, không gói trong dep-sweep. 3.4 vẫn được vá. Track qua Dependabot. |
| `@types/node` | **22.x** | 25.x | Ghim theo **major Node runtime** (hiện Node 22). Dùng types > runtime dễ tham chiếu API chưa có. Nâng khi đổi Node engine. |
| `eslint` | 10.x | — | Lưu ý: hệ plugin (`eslint-plugin-vue`, `typescript-eslint`) phải hỗ trợ eslint major trước khi nâng — nếu peer chặn, giữ eslint ở major mà plugin hỗ trợ. |

> **Lint debt (pre-existing, ngoài scope dep-upgrade):** `npm run lint` còn ~20 error
> (`vue/no-mutating-props`, `no-undef` thiếu global, `no-require-imports`,
> `no-useless-assignment`). Không block build/test. Dọn trong một pass refactor riêng.

---

## 5. Snapshot nâng cấp 2026-06-15
Wave nâng FE lên latest (giữ exceptions §4): vue 3.5, vue-router 5, vue-i18n 11,
@vueuse 14, pinia 3, @tanstack/vue-query 5.101, axios 1.18, vite 8.0.16, vitest 4,
jsdom 29, @vitejs/plugin-vue 6, typescript 6, vue-tsc 3, eslint 10 + plugin-vue 10
+ vue-eslint-parser 10 + typescript-eslint 8.61, @types/node 22. Lockfile regen
sạch, 0 vulnerability, **1383 test / typecheck / build XANH**.

Breaking-change đã sửa trong wave (tham chiếu khi nâng lần sau):
- **vue-tsc 3** chặt hơn template-ref → gỡ 2 dead-ref, chuyển composable sang `useTemplateRef` (`src/composables/useMaskedDateInput.ts`).
- **jsdom 29 + vitest 4**: iframe `src=blob:` → opaque-origin → `localStorage` SecurityError; chặn navigate ở test (`usePdfLabelPrint.test.ts`).
- **vue-router 5**: `RouteMeta` weak-type → augment đủ field (`src/types/vue-router.d.ts`).
