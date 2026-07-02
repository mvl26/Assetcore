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
1. **Test colocate** cạnh file: `personas.ts` → `personas.test.ts`, `WorkflowStepper.vue` → `WorkflowStepper.test.ts`.
2. **TDD cho logic FE thuần** — viết test TRƯỚC khi code:
   - mapping/label dict (status/enum/persona) → test khớp với constant BE (chống LL-FE-3/8/21/30 enum-sync, EN-leak).
   - regression guard cho bug enum đã fix (vd `repairPriority.test.ts` chốt `Normal|Urgent|Emergency`, chống tái xuất Critical/High/Medium/Low).
   - composable/derive function (vd `derivePersonas`, `resolveCurrentPersona`).
   - component nhỏ render theo props (KpiCard, WorkflowStepper) — mount + assert text.
3. **vitest KHÔNG thay Playwright** — full user journey + workflow buttons + permission gate vẫn test ở Phần 2.
4. **DoD FE**: `npm run test` + `npm run typecheck` + `npm run build` đều exit 0 TRƯỚC khi mark Done (cùng với Playwright eval). Lint: 0 lỗi MỚI (lỗi pre-existing repo-wide không tính).
5. **Sau sweep đổi chuỗi HIỂN THỊ hàng loạt** (Việt-hoá / rename label / đổi text nút) → chạy **`vitest run` TOÀN BỘ**, KHÔNG chỉ test colocate. Test ở file TÊN KHÁC vẫn assert chuỗi hiển thị (vd `IncidentCreateView.assetMeta.test.ts` assert text nút mà `IncidentCreateView.test.ts` không có) → grep-colocate bỏ sót, chỉ full-suite mới bắt. Khi sửa: test assert chuỗi HIỂN THỊ → cập nhật sang bản mới; test assert **VALUE enum/payload** (contract, vd `pass_fail: 'Pass'`) → KHÔNG đổi.
   - **Trước khi khai Done: `grep` literal CŨ toàn repo (kể cả `*.test.ts`).** Đổi 1 nhãn **SSoT status/label** (không phải chuỗi tự do) nổ radius rộng: `RCA Required`→"Cần phân tích nguyên nhân gốc" + `SLA`→"cam kết dịch vụ" (2026-07-01) vỡ **≥5 file test ở module KHÁC** (`constants/incidentLabels.test.ts` · `utils/formatters.test.ts` · `views/incident/incidentListDrilldown.test.ts`·`slaBreachLiveSoT.test.ts` · `views/cm/cmSlaClockStop.test.ts`·`cmSlaBreachedDivergence.test.ts`). Cross-ref `assetcore-fe` [[LL-FE-53]].

## Anti-pattern
- Mark FE Done chỉ vì build pass mà bỏ vitest cho logic mới → bug enum/mapping lọt (đã gặp nhiều lần — xem LL-FE-3/8/30).
- Test mapping bằng cách hardcode lại dict trong test (tautology) → phải assert giá trị khớp **nguồn BE thật** (enum DocType / `rbac.CAPABILITY_MAP`).
- Sau khi đổi nhiều chuỗi hiển thị, chỉ chạy test colocate ("đã quét test cùng thư mục, không vỡ") → MISS test ở file tên khác assert chuỗi đó (session 2026-06-29 Việt-hoá UI). Luôn full `vitest run`.
