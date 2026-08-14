# Frontend Unit Tests (vitest) — deep reference

> Heavy reference cho `assetcore-test` SKILL.md **Phần 1.5 — Frontend Unit Tests (vitest)**.
> Đọc khi viết test cho logic FE thuần (constants, mapping, composable, component nhỏ).

> Harness FE thêm 2026-05-29 (phase persona-redesign). Trước đó dự án CHƯA có FE test runner — nay TDD cho logic FE thuần (constants, mapping, composable, component nhỏ) chạy được không cần browser.

## Chạy
```bash
cd frontend
npm run test          # chạy 1 lần (vitest run)
npm run test:watch    # watch mode khi dev
npm run typecheck     # vue-tsc --noEmit — bắt type drift
```
Config: `frontend/vitest.config.ts` (env jsdom, `@vitejs/plugin-vue` để mount SFC).

## Quy tắc
1. **Vị trí & tên file — SSoT là R-13 của `assetcore-test/SKILL.md`, cưỡng chế bằng
   `frontend/src/guards/testFileConvention.guard.test.ts`.** Tóm tắt: test của MỘT file nguồn
   nằm trong thư mục con **`tests/`** của chính thư mục chứa nguồn, tên khớp CHÍNH XÁC tên nguồn:
   `constants/personas.ts` → `constants/tests/personas.test.ts` ·
   `components/common/WorkflowStepper.vue` → `components/common/tests/WorkflowStepper.test.ts` ·
   nhiều khía cạnh → `<Nguồn>.<khiaCanh>.test.ts`.
   **KHÔNG** đặt ngang hàng file nguồn (quy ước cũ, đã bỏ 2026-08-13) · **KHÔNG** dùng `__tests__/`.
   Test đọc đĩa/cưỡng chế quy ước → `src/guards/`; test khởi động/luồng chéo → `src/integration/`.
2. **TDD cho logic FE thuần** — viết test TRƯỚC khi code:
   - mapping/label dict (status/enum/persona) → test khớp với constant BE (chống LL-FE-3/8/21/30 enum-sync, EN-leak).
   - regression guard cho bug enum đã fix (vd `labels.repairPriority.test.ts` chốt `Normal|Urgent|Emergency`, chống tái xuất Critical/High/Medium/Low).
   - composable/derive function (vd `derivePersonas`, `resolveCurrentPersona`).
   - component nhỏ render theo props (KpiCard, WorkflowStepper) — mount + assert text.
3. **vitest KHÔNG thay Playwright** — full user journey + workflow buttons + permission gate vẫn test ở Phần 2.
4. **DoD FE**: `npm run test` + `npm run typecheck` + `npm run build` đều exit 0 TRƯỚC khi mark Done (cùng với Playwright eval). Lint: 0 lỗi MỚI (lỗi pre-existing repo-wide không tính).
5. **Sau sweep đổi chuỗi HIỂN THỊ hàng loạt** (Việt-hoá / rename label / đổi text nút) → chạy **`vitest run` TOÀN BỘ**, KHÔNG chỉ những test nằm gần file vừa sửa. Test ở file TÊN KHÁC vẫn assert chuỗi hiển thị (vd `incidentCreateAssetMeta.guard.test.ts` assert text nút mà `IncidentCreateView.test.ts` không có) → chỉ soi test cùng thư mục sẽ bỏ sót, chỉ full-suite mới bắt. Khi sửa: test assert chuỗi HIỂN THỊ → cập nhật sang bản mới; test assert **VALUE enum/payload** (contract, vd `pass_fail: 'Pass'`) → KHÔNG đổi.
   - **Trước khi khai Done: `grep` literal CŨ toàn repo (kể cả `*.test.ts`).** Đổi 1 nhãn **SSoT status/label** (không phải chuỗi tự do) nổ radius rộng: `RCA Required`→"Cần phân tích nguyên nhân gốc" + `SLA`→"cam kết dịch vụ" (2026-07-01) vỡ **≥5 file test ở module KHÁC** (`constants/labels.incidentLabels.test.ts` · `utils/formatters.test.ts` · `views/incident/IncidentListView.drilldown.test.ts`·`slaBreachLiveSoT.test.ts` · `views/cm/CMWorkOrderDetailView.slaClockStop.test.ts`·`CMWorkOrderListView.slaBreachedDivergence.test.ts`). Cross-ref `assetcore-fe` [[LL-FE-53]].

## Anti-pattern
- Mark FE Done chỉ vì build pass mà bỏ vitest cho logic mới → bug enum/mapping lọt (đã gặp nhiều lần — xem LL-FE-3/8/30).
- Test mapping bằng cách hardcode lại dict trong test (tautology) → phải assert giá trị khớp **nguồn BE thật** (enum DocType / `rbac.CAPABILITY_MAP`).
- Sau khi đổi nhiều chuỗi hiển thị, chỉ chạy những test nằm gần file vừa sửa ("đã quét test cùng thư mục, không vỡ") → MISS test ở file tên khác assert chuỗi đó (session 2026-06-29 Việt-hoá UI). Luôn full `vitest run`.
