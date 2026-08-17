---
name: assetcore-test
description: >
  Viết và chạy test cho AssetCore — bao gồm unit test service layer (Python/Frappe),
  workflow smoke test, integration test, UAT scripts, và UI test bằng Playwright MCP.
  Dùng khi user nói "viết test", "TDD", "kiểm thử", "test case cho IMM-XX",
  "bench run-tests", "test fails", "DoD", "playwright", "test UI", "kiểm tra giao diện",
  "chạy e2e", "UI xong chưa", "verify UI IMM-XX". Bắt buộc dùng trước khi khai báo
  bất kỳ feature BE hoặc FE nào là "xong" — CLAUDE.md §17 mandates TDD.
---

# AssetCore Test — Backend Unit + Playwright UI

## Overview

Skill này bao 2 loại test: **Backend (Python/Frappe)** + **UI (Playwright MCP)**, cộng FE unit test (vitest).
Nguyên tắc cốt lõi: **"test xanh" ≠ "feature chạy"** — phải chạy THẬT, ĐỌC output, assert ĐÚNG side-effect/artifact thật, và POST-RUN cleanup là phần BẮT BUỘC của DONE. Mọi feature phải pass cả 2 loại test trước khi được khai báo Done (CLAUDE.md §17).

## When to Use

- Viết/chạy unit test service layer, workflow smoke test, integration test, UAT cho module IMM-XX.
- Viết FE unit test (vitest) cho logic FE thuần (constants/mapping/composable/component nhỏ).
- Chạy UI test (Playwright MCP) — full user journey, workflow buttons, permission gate, DoD UI.
- Trước khi khai báo BẤT KỲ feature BE/FE nào là "xong" — TDD-gate (CLAUDE.md §17).
- **KHÔNG dùng khi**: chỉ viết BE logic chưa cần test (→ `assetcore-be`), chỉ build FE view (→ `assetcore-fe`), audit/security review toàn module (→ `assetcore-audit`), hoặc deploy/migrate (→ `assetcore-deploy`).

## Process — viết & chạy test THẬT, cleanup là phần của DONE

Quy trình từng bước (spine — chi tiết ở mục dưới):
1. **Đọc NGUYÊN TẮC BẤT BIẾN R-0..R-12** — luật data/cleanup/runtime-evidence trước khi chạm test → §NGUYÊN TẮC BẤT BIẾN
2. **Chọn tầng test pyramid 80/15/5** — phân bổ unit/integration/E2E, đừng đẩy logic lên Playwright → §Phần 3 — Test strategy
3. **Backend tests RED-first** — service-layer `bench run-tests`, assert `e.code`/side-effect THẬT, fixture tự dọn → §Phần 1
4. **FE unit vitest** — logic FE thuần (mapping/enum khớp nguồn BE), không thay Playwright → §Phần 1.5
5. **Playwright UI + runtime-data** — full user journey trên `localhost:3000`, data thực tế, console+network sạch → §Phần 2
6. **POST-RUN cleanup R-12** — `tidy-eval-artifacts.sh` + tear-down data scoped; chưa dọn = chưa DONE → §NGUYÊN TẮC BẤT BIẾN / R-12
7. **Verification** — paste `Ran N ... OK` THẬT, artifact thật, self-check rỗng → §Verification

---

## NGUYÊN TẮC BẤT BIẾN — Đọc trước khi làm bất cứ điều gì

### R-0: Hai chế độ test có quy tắc data KHÁC NHAU

| Loại test | Nơi chạy | Quy tắc data |
|---|---|---|
| **Backend unit test** (Python) | `assetcore/tests/` | Dùng prefix `_Test` — Frappe auto-rollback/cleanup |
| **UI test** (Playwright) | Browser trên `localhost:3000` | **TUYỆT ĐỐI KHÔNG dùng tên test** — phải dùng data thực tế |

> Backend unit tests dùng `_Test` prefix vì Frappe wrap từng test trong savepoint và rollback.
> UI test KHÔNG được dùng `_Test` vì data tạo ra qua UI **không được rollback tự động** → gây rác.

---

### R-1: UI Test — Dữ liệu PHẢI thực tế — TUYỆT ĐỐI không dùng tên "test"

**Sai (cấm tuyệt đối trong UI test):**
- Tên rule: `TEST-R`, `Test Rule`, `IMM-Rule-01`, `testcomp`
- Tên khoa: `Dept`, `dept01`, `Unknown`, `Test Dept`, `Test WH IMM-15`
- Người dùng: `test@test.com`, `admin`, `testuser`
- Mô tả: `test`, `testing`, `some description`, `abc`, `123`
- Thiết bị: `Test Device`, `Asset 01`, `machine01`, `Test Asset IMM-15`, `Máy XQuangNew`
- Phụ tùng: `Test Part IMM-15`, `_TestSCSupplier`

**Đúng — dùng context bệnh viện Việt Nam thực tế:**
- Tên khoa: `Khoa Ngoại Tổng hợp`, `Khoa Hồi sức tích cực (ICU)`, `Phòng Mổ số 2`
- Tên thiết bị: `Máy thở Dräger Evita V500`, `Máy siêu âm Philips EPIQ 7`, `Monitor bệnh nhân Mindray BeneView T9`
- Nhà cung cấp: `Công ty TNHH Dräger Medical Vietnam`, `Meditronic Vietnam Co., Ltd`
- Phụ tùng: `Van PEEP máy thở Dräger Evita V500`, `Cảm biến SpO2 Masimo SET`
- Mô tả sự cố: `Thiết bị báo lỗi E-001 khi bệnh nhân thở thụ động`, `Màn hình hiển thị nhiễu sau 3 giờ vận hành`
- Ghi chú kỹ thuật: `Thay thế van PEEP do mòn — ref phụ tùng SP-DR-0234`

---

### R-2: Kiểm tra data tồn tại TRƯỚC KHI tạo bản ghi mới

**LUÔN làm trước bước 1 của bất kỳ UI test nào:**

```
1. Navigate → list page của master data cần thiết
2. Snapshot → verify dữ liệu có sẵn
3. Nếu thiếu → TẠO MASTER DATA THỰC TẾ TRƯỚC (xem R-3)
4. Chỉ sau khi có đủ master data → bắt đầu test operational record
```

**Dependency map — mỗi DocType cần những gì:**

| Bản ghi cần tạo | Master data bắt buộc phải có trước |
|---|---|
| AC Asset | AC Supplier, AC Location, AC Department |
| Work Order (PM/CM/Cal) | AC Asset đang Active |
| AC Incident Report | AC Asset đang Active, AC Department |
| AC CAPA | AC Incident Report hoặc Work Order gốc |
| AC Spare Part | AC UOM (đơn vị tính) |
| AC Spare Part Stock | AC Spare Part, AC Warehouse |
| AC Stock Movement | AC Spare Part, AC Warehouse (nguồn + đích) |
| AC Compliance Rule | (không cần) |
| AC Compliance Finding | AC Compliance Rule, AC Asset |
| AC Purchase | AC Supplier |
| AC Needs Request | AC Department |

---

### R-3: Khi master data chưa có — TẠO THỰC TẾ, không tạo tạm

**Ví dụ sai — tạo khoa tạm để vượt qua bước validation:**
> ~~Tạo "Dept-Temp-01" để có khoa cho test user~~

**Đúng — tạo khoa thực tế:**
> Navigate → `/departments` → Tạo "Khoa Nội thần kinh" với đầy đủ thông tin → sau đó quay lại tạo user

**Checklist khi tạo master data mới:**
- [ ] Tên đúng chuẩn tên bệnh viện Việt Nam (không viết tắt, không mã hóa)
- [ ] Điền đầy đủ tất cả optional fields có ý nghĩa
- [ ] Xác nhận bản ghi đã được lưu và có thể tìm thấy trong list

**Inventory master data mẫu có sẵn (departments/warehouses/assets/suppliers/locations/spare parts):** dùng làm input UI test — xem inventory chi tiết ở reference.

> Chi tiết: see [references/playwright-ui-tests.md](references/playwright-ui-tests.md) (mục "Inventory master data mẫu có sẵn").

---

### R-4: Điền ĐẦY ĐỦ tất cả fields có thể điền

Khi test tạo bản ghi mới, **bắt buộc điền tất cả fields hiển thị** — không bỏ trống bất kỳ field optional nào có ý nghĩa.

Checklist fields bắt buộc theo loại bản ghi:
- **Work Order (PM/CM/Cal)**: asset, loại, ngày dự kiến, kỹ thuật viên, mô tả triệu chứng, địa điểm
- **Incident**: thiết bị, mô tả sự cố, mức độ, khoa/phòng, người báo cáo, thời gian xảy ra
- **CAPA**: root cause method, mô tả nguyên nhân gốc rễ, hành động khắc phục, người phụ trách, hạn xử lý
- **Needs Request**: thiết bị cần mua, lý do, khoa đề xuất, ưu tiên, tổng CAPEX ước tính
- **Compliance Rule**: tên rule cụ thể, phạm vi (khoa hoặc toàn viện), threshold, tần suất kiểm tra
- **Compliance Finding**: asset vi phạm, rule vi phạm, giá trị thực tế vs ngưỡng, mức độ, khoa chịu trách nhiệm

---

### R-5: Mỗi page test phải đi qua FULL user journey

Không chỉ test "list page load" — phải test toàn bộ luồng:
1. **Pre-check**: verify master data đủ (xem R-2 dependency map)
2. **Tạo mới** → điền đầy đủ fields → submit → verify record tạo thành công với tên đúng format
3. **Xem chi tiết** → click vào record → verify tất cả fields hiển thị đúng, không có `undefined`, `[object Object]`, `null`
4. **Workflow actions** → test từng nút hành động theo đúng state transition → verify trạng thái thay đổi đúng
5. **Filter** → áp dụng ít nhất 1 bộ lọc → verify kết quả đúng
6. **Edge case** → thử tạo bản ghi thiếu field bắt buộc → verify lỗi hiện rõ ràng

---

### R-6: Trang chi tiết PHẢI có đủ các chức năng

Mỗi trang chi tiết bản ghi phải có:
- [ ] Hiển thị tất cả fields (không thiếu field nào so với DocType)
- [ ] Tất cả workflow action buttons phù hợp với state hiện tại
- [ ] Lịch sử/audit trail (ít nhất hiển thị các action đã thực hiện)
- [ ] Liên kết đến bản ghi liên quan (CAPA, Work Order, Asset, v.v.)
- [ ] Nút quay lại (breadcrumb hoặc back button)

**Nếu trang chi tiết thiếu workflow actions → BUG, phải fix trước khi khai báo PASS.**

---

### R-7: Không khai báo PASS khi còn lỗi console

Sau mỗi page test, luôn chạy `browser_console_messages` và `browser_network_requests`. Test chỉ PASS khi:
- 0 lỗi JS console (TypeError, ReferenceError, Uncaught, v.v.)
- 0 API calls trả về 4xx hoặc 5xx trên trang hiện tại
- 0 field hiển thị `undefined`, `[object Object]`, `null` chuỗi

> **named principle: browser-testing-with-devtools** — dùng **runtime data** (console errors + network requests) làm BẰNG CHỨNG, không suy từ code. DevTools MCP → Playwright MCP của dự án: `browser_console_messages`/`browser_network_requests` chính là cặp bằng chứng R-7 này. Runtime ≠ mental-model: code "trông đúng" không thay được console sạch + status code thật.

---

### R-8: Dữ liệu tạo trong UI test PHẢI được theo dõi và dọn dẹp

**Ghi lại mọi bản ghi tạo ra:**
Mỗi UI test session phải ghi rõ:
```
Data tạo trong session này:
  - [DocType]: [name] — [mô tả ngắn, lý do tạo]
  - ...
```

**Sau test session:**
- Các bản ghi operational (Work Order, Incident, CAPA, Finding) tạo để test có thể giữ lại nếu dữ liệu thực tế
- Nếu cần xóa: dùng `assetcore.scripts.cleanup_junk_data` script, hoặc qua UI (Cancel → Delete nếu DocType cho phép)
- **Tuyệt đối không để lại** bản ghi có tên chứa: `test`, `Test`, `TEST`, `_T-`, `IMM-XX`, `placeholder`, các mã giả

---

### R-9: Backend test fixture PHẢI tự dọn — không rely on `frappe.db.rollback`

**Bug đã gặp 2026-05-27:** sau nhiều lần `bench --site miyano run-tests --app assetcore`, DB tích luỹ 776+ records test (`Test Asset IMM-15`, `_Diag Asset`, `_TEST-PROG-*`, `Test Part IMM-15`, `Test WH IMM-15`, `Dräger Evita V500 — ICU-decom/-pm/-event/-trans`, etc.).

Lý do leak:
- `FrappeTestCase` rollback PER-test, không per-class. Test tạo doc trong `setUpClass` → commit → KHÔNG rollback.
- Test gọi service function `frappe.db.commit()` bên trong (lifecycle event, audit trail) → savepoint rollback không tới được.
- Test pass `delete=False` hoặc dùng `frappe.db.set_value` trực tiếp bypass ORM.

**Quy tắc:**

1. Mọi fixture tạo trong `setUpClass` PHẢI xoá trong `tearDownClass` (cancel docstatus=1 trước, xoá children trước parents, commit cuối).
   > Chi tiết: see [references/backend-tests.md](references/backend-tests.md) (mục "R-9 fixture cleanup — `tearDownClass` template").

2. Đặt prefix dễ grep, KHÔNG dùng pattern mơ hồ:
   - `_Test{Module}{Purpose}-{uniq}` — VD `_TestIMM15Asset-abc123`
   - **KHÔNG** dùng `_%` placeholder (`_` là SQL wildcard → match toàn bảng khi cleanup)
   - **KHÔNG** dùng tên giống real data (`Dräger Evita V500 — ICU-decom`) — sẽ confuse cleanup

3. **Pre-release verify** (mỗi sprint):
   ```bash
   bench --site miyano mariadb -e "
     SELECT 'AC Asset' AS dt, COUNT(*) FROM \`tabAC Asset\`
     WHERE LOWER(name) LIKE '%test%' OR LOWER(asset_name) LIKE '%test%'
     UNION ALL SELECT 'IMM Audit Trail', COUNT(*) FROM \`tabIMM Audit Trail\`
     WHERE LOWER(change_summary) LIKE '%_test%';"
   ```
   Tất cả phải = 0.

Reference: `assetcore-deploy` Phần 3.

---

### R-10: KHÔNG chạy `bench run-tests` song song với destructive DB op

Bug 2026-05-27: trong lúc cleanup 13:55, test chạy parallel tạo data mới timestamps 14:31 → phải cleanup vòng 2.

**Trước khi cleanup hoặc destructive op:**
- [ ] `bench --site <site> set-maintenance-mode on`
- [ ] Confirm không có terminal khác chạy `bench run-tests`
- [ ] Scheduler tạm pause: `bench --site <site> disable-scheduler`
- [ ] Sau cleanup: `enable-scheduler` + `set-maintenance-mode off`

### R-11: Screenshot/artifact Playwright → `.playwright/eval/` — KHÔNG để gốc repo

> ⚠️ **CẬP NHẬT 2026-06-11 (LL-QA-2):** kho ảnh bền nay là **`.playwright/eval/`**, KHÔNG còn `.playwright-mcp/`. `.playwright-mcp/` chỉ là output TẠM của MCP — sweep về `.playwright/eval/` sau mỗi run. Mọi chỗ R-11 ghi `.playwright-mcp/` là kho cuối ĐÃ LỖI THỜI; đọc convention mới ở LL-QA-2 + chạy `bash .claude/scripts/tidy-eval-artifacts.sh` để sweep.

**Bug đã gặp 2026-05-29:** bước [User] eval lưu screenshot ra **gốc repo** với tên tuỳ ý (`3a-imm08-pm-dashboard.png`, `dashboard-admin.png`, ...) → 21 file PNG rải khắp root, lẫn vào `git status`, suýt commit nhầm.

**Quy tắc:**

1. **Mọi** `browser_take_screenshot` (và artifact eval khác) PHẢI ghi vào `.playwright/eval/` — đã gitignore (`.gitignore:50-52`). Dùng subfolder theo phiên/phase cho gọn:
   ```
   .playwright/eval/<phase>-<module>-<screen>.png
   # vd: .playwright/eval/3a-imm08-pm-dashboard.png
   ```
   Khi gọi tool, set `filename` = đường dẫn tuyệt đối dưới `.playwright/eval/`. KHÔNG để mặc định rơi ra cwd (gốc repo). Nếu MCP buộc ghi vào `.playwright-mcp/` → sweep về `.playwright/eval/` cuối run (LL-QA-2).

2. **TUYỆT ĐỐI KHÔNG** lưu `.png`/`.jpg`/artifact eval ra gốc repo hay trong `frontend/`, `assetcore/`. Screenshot là bằng chứng tạm, không phải source → không bao giờ commit.

3. **Self-check cuối mỗi session eval** (phải rỗng):
   ```bash
   git status --porcelain --untracked-files=all | grep -iE '\.(png|jpg|jpeg|webp)$'
   # Có output → đã rơi artifact ra ngoài .playwright/eval/ → bash .claude/scripts/tidy-eval-artifacts.sh
   ```

4. Báo cáo eval **tham chiếu đường dẫn** screenshot dưới `.playwright/eval/`, không attach/đính kèm ra ngoài.

---

### R-12: POST-RUN CLEANUP là phần BẮT BUỘC của "DONE" — verdict KHÔNG = DONE nếu chưa dọn (LL-QA-1/2/3)

**Triệu chứng→nguyên nhân:** test/eval/Playwright/factory-run sinh artifact rác (ảnh chụp, scratch script `_scan_junk*.py`, MCP snapshot `page-*.yml`) → `git add .` lọt commit (R-11 risk). USER feedback 2026-06-11: "sau khi làm xong PHẢI dọn sạch... ảnh rác cho gọn vào `.playwright/eval`".

**Rule kiểm-được — cuối MỖI kỳ test/eval/factory-run, TRƯỚC khi tuyên bố DONE:**

1. Chạy **`bash .claude/scripts/tidy-eval-artifacts.sh`** (idempotent; `--dry` xem trước). Script: sweep `.playwright-mcp/*` → `.playwright/eval/`, xoá scratch (`_scan_junk*.py`/`_cleanup_junk*.py`/`*.py.tmp.*`/`*.py.orig`/MCP `page-*.yml`/`*.log`). Guard `git ls-files --error-unmatch` → CHỈ đụng file UNTRACKED, KHÔNG xoá asset thật (swagger-ui favicon `assetcore/public/swagger-ui/*.png`, FE/docs img trong subdir).

2. **Self-check phải rỗng** (có output = CHƯA dọn = CHƯA DONE):
   ```bash
   git status --porcelain -uall | grep -iE '\.(png|jpg|jpeg|webp|gif)$|_scan_junk|\.py\.tmp\.|\.py\.orig'
   ```

3. **Scratch debug callable** (LL-TEST-15): đặt trong `apps/assetcore/assetcore/<name>.py`, chạy `bench execute`, rồi `rm` NGAY sau dùng — KHÔNG để ở repo root. gitignore chặn `_scan_junk*.py`/`*.py.tmp.*`/`*.py.orig` (`.gitignore:54-57`) nhưng dọn vẫn là phần của DONE, KHÔNG ỷ gitignore.

Reference: `memory/feedback_tidy_eval_artifacts.md`, `.claude/scripts/tidy-eval-artifacts.sh`.

---

## Phần 1 — Backend Tests (Python/Frappe)

Layout `assetcore/tests/`; chạy `bench --site miyano run-tests --module assetcore.tests.test_immXX`. Ưu tiên service-layer test (assert `e.code`, không `e.message`); workflow smoke test `tests/test_workflows.py` là deploy gate (đếm state/transition từ JSON, không đoán). Event-driven/side-effect feature PHẢI assert side-effect THẬT (không chỉ return) — chống false-green.

> Heavy reference: see [references/backend-tests.md](references/backend-tests.md) — layout, test template, service/permission/workflow/UAT template, fixture rules, coverage targets, event-driven assert side-effect, quick audit script, và toàn bộ LL-TEST/LL-QA backend test-execution.

## Phần 1.5 — Frontend Unit Tests (vitest)

TDD cho logic FE thuần (constants/mapping/persona/composable/component nhỏ) — `cd frontend && npm run test`. **Vị trí & tên file: xem R-13 ngay dưới** (test nằm trong `<thư-mục-nguồn>/tests/`, KHÔNG ngang hàng file nguồn). Mapping/enum phải assert khớp **nguồn BE thật** (không hardcode lại dict = tautology). vitest KHÔNG thay Playwright. DoD FE: `npm run test` + `typecheck` + `build` đều exit 0.

> Heavy reference: see [references/frontend-unit-tests.md](references/frontend-unit-tests.md) — cách chạy, quy tắc TDD, anti-pattern enum-sync. (Vị trí/tên file test: R-13 là SSoT, reference chỉ trỏ về.)

### 🧭 R-13: Vị trí & tên file test FE — BẮT BUỘC (SSoT: `frontend/src/guards/testFileConvention.guard.test.ts`)

Mỗi file test FE chỉ được ở **một trong ba nhà — không có nhà thứ tư**:

| # | Loại test | Nhà | Tên file |
|---|---|---|---|
| 1 | Test của **MỘT** file nguồn | **`<thư-mục-nguồn>/tests/`** | `<Nguồn>.test.ts` · `<Nguồn>.<khiaCanh>.test.ts` |
| 2 | **Guard / parity / ngân sách** (đọc đĩa, cưỡng chế quy ước, doc↔mã) | **`src/guards/`** | `<chuDe>.guard.test.ts` |
| 3 | **Tích hợp / khởi động / route** | **`src/integration/`** | `<luong>.integration.test.ts` |

`<Nguồn>` khớp **CHÍNH XÁC** tên file nguồn ở **thư mục cha** của `tests/`. `<khiaCanh>` camelCase, đã lược tiền tố trùng tên nguồn.
Vd: `views/cm/CMCreateView.vue` ⇒ `views/cm/tests/CMCreateView.qrPrefill.test.ts`.
`src/guards/` và `src/integration/` **KHÔNG** thêm tầng `tests/` — chúng đã là nhà test riêng.

**CẤM:** đặt test **ngang hàng** file nguồn · `__tests__/` (dùng `tests/`) · `tests/` **mồ côi** (cha không có nguồn) · `.spec.ts` · mã ticket trong tên file (đưa vào `describe()`) · dấu chấm trong tên file **nguồn** `.ts` · test ngoài `guards/` mà quét thư mục (`readdirSync`/`import.meta.glob`) hoặc đọc file ngoài **thư mục cha** của `tests/` · guard dùng đường dẫn theo **độ sâu** (`resolve(HERE,'../..')` / `process.cwd()`) thay vì `@/test/paths` · guard quét thư mục mà **không chốt dân số** (`listFiles(DIR,{ext,min:N})` hoặc dấu `// [K8] dân số:`).

> **Vì sao chốt dân số là bắt buộc:** guard quét thư mục rồi khẳng định "không tìm thấy vi phạm". Nếu thư mục bị dời/đổi tên, bộ quét trả **0 file**, khẳng định đó đúng một cách **rỗng tuếch**, và suite vẫn XANH trong khi guard đã ngừng canh. `vue-tsc` KHÔNG bắt được — nó chỉ phủ đồ thị import, không phủ lớp đọc văn bản mã nguồn.

**Test FE mới PHẢI làm `testFileConvention.guard.test.ts` XANH. Chạy guard này TRƯỚC khi báo xong:**
```bash
cd frontend && npx vitest run src/guards/testFileConvention.guard.test.ts
```
Spec đầy đủ + kế hoạch L0–L5: `docs/architecture/SPEC_chuan_hoa_cau_truc_frontend.md`.

### 🧭 R-14: Vị trí & tên file test BE — BẮT BUỘC

> SSoT cưỡng chế: `assetcore/tests/guards/test_test_layout_convention.py` (K1–K9 + guard §5.4).
> Spec đầy đủ: `docs/architecture/SPEC_chuan_hoa_cau_truc_backend.md`.

Mỗi file test chỉ được ở **một trong bốn nhà**:

| # | Loại test | Nhà | Tên file |
|---|---|---|---|
| 1 | Test của **một DocType** (validate, hooks, naming, permission trên chính doc) | `assetcore/assetcore/doctype/<dt>/` — **chuẩn Frappe** | `test_<dt>.py` |
| 2 | Test của **một module logic** (`services/<X>.py` / `api/<X>.py`) | `assetcore/tests/<X>/` | `test_<X>[_<khia_canh>].py` |
| 3 | **Guard / hợp đồng / parity** — đọc đĩa, lint OAS, đối chiếu doc↔mã, không cần DB | `assetcore/tests/guards/` | `test_<chu_de>.py` |
| 4 | **Tích hợp cắt ngang ≥2 module** | `assetcore/tests/integration/` | `test_<luong>.py` |

Helper dùng chung → `assetcore/tests/_helpers/` (`paths.py`, `_asset_cleanup.py`, `oas_baseline.py`).

**CẤM (guard sẽ ĐỎ):**
- Để file test ở **gốc `assetcore/tests/`** · thư mục con thiếu `__init__.py` (R2 — `--module` sẽ gãy) · mã ticket trong **tên file** (đưa vào docstring/`test_*` method).
- **Đổi tên file trong `patches/`** — Frappe nhận diện patch bằng **chuỗi dotted path** (`patch_handler.py:228`); đổi tên patch ĐÃ CHẠY ⇒ Frappe coi là patch mới ⇒ **chạy lại trên production** (R3).
- Test **ghi DB** (`frappe.get_doc/new_doc/insert/db.set/delete_doc`) mà lớp cơ sở không phải **`FrappeTestCase`** — không rollback ⇒ rác rơi vào site thật.
- Test **quét thư mục** (`os.walk`/`glob`/`listdir`) mà không ở `tests/guards/`; hoặc guard quét mà **không chốt dân số** (`list_files(DIR, ext, min_count=N)` / `assertGreater(len(files), N)`).
- Guard tính đường dẫn theo **độ sâu** (`Path(__file__).resolve().parents[N]`, `os.path.dirname(os.path.dirname(...))`, `process.cwd()`) — phải lấy anchor từ **`assetcore.tests._helpers.paths`**.

**Ranh giới `utils/` ⇄ `services/shared/` (§5.4 — MỘT CHIỀU):**

| Nhà | Chứa gì | Được import |
|---|---|---|
| `assetcore/utils/` | hạ tầng kỹ thuật, không biết nghiệp vụ (response envelope, pagination, attachment, email, idempotency, FCM, `ServiceError`) | thư viện ngoài + `frappe`. **CẤM** import `services/**` ở mức module |
| `assetcore/services/shared/` | nhân nghiệp vụ dùng chung (scope/RBAC, state machine, filters, connection meta) | được import `utils/` |

Lazy-import **bên trong hàm** là lối thoát hợp lệ (không tạo vòng lúc nạp module) — vd `utils/fcm.py` gọi `services.mobile_device_token` chỉ khi gặp dead-token.

**Trước khi báo xong:**
```bash
bench --site <site> run-tests --module assetcore.tests.guards.test_test_layout_convention
```

**Kỷ luật rollback (bệnh gốc §3.4):** test BE ghi DB **PHẢI** kế thừa `FrappeTestCase`
(Frappe bọc mỗi test trong savepoint và rollback). Trước lô B4 có **75 file** chỉ dùng
`unittest.TestCase` ⇒ commit thẳng vào site ⇒ 45 CAPA + 24 hiệu chuẩn mồ côi và **16 script
`purge_*`/`cleanup_*`** sinh ra để dọn hậu quả. Allowlist K7 nay **đóng băng ở 0**: file mới
KHÔNG thể ghi DB mà không rollback.

> ⚠️ `FrappeTestCase` rollback **per-test**, KHÔNG per-class. Fixture tạo trong
> `setUpClass` + commit vẫn LEAK — phải tự dọn ở `tearDownClass` (R-9).

## Phần 2 — UI Tests (Playwright MCP)

Playwright MCP là phương tiện DUY NHẤT — không đoán từ code. Base `http://localhost:3000` (`bench start` chạy song song). Đọc `.env` lấy creds (KHÔNG hardcode). Dùng bộ dữ liệu mẫu thực tế (R-1/R-3). Mỗi module đi đủ full user journey (R-5) + DoD UI checklist. MCP hay chết sau 1-2 calls → có recovery recipe; 2 lần fail → fallback static code-audit, báo USER sớm.

> Heavy reference: see [references/playwright-ui-tests.md](references/playwright-ui-tests.md) — credentials, bộ dữ liệu mẫu, pre-test checklist, login, MCP tools, MCP recovery recipe, full user journey, DoD UI checklist + report, module→URL mapping, và toàn bộ LL-TEST UI patterns + bug-patterns table.
>
> Playwright command patterns (login/navigate/fill/select/toast/network) + LL-QA-9/10/11: see [references/playwright-patterns.md](references/playwright-patterns.md).

---

## Phần 3 — Test strategy (named principle: test-driven-development)

**Test pyramid 80/15/5** — phân bổ công sức test theo tầng, đáy rộng đỉnh hẹp. Map sang 3 loại test của dự án (Phần 1/1.5/2):

| % | Tầng | Ở AssetCore | Ví dụ tailor |
|---|------|-------------|--------------|
| **~80%** | Unit — service-layer (Python/Frappe), nhanh, isolated | `tests/test_immXX.py` assert `e.code` / side-effect doc; FE unit (vitest) cho mapping/enum | `test_imm09._on_repair_complete` sinh Lifecycle Event đúng; FE `statusLabel(s)` khớp BE enum |
| **~15%** | Integration — qua boundary (workflow / DB / API) | workflow smoke `tests/test_workflows.py` (đếm state/transition từ JSON); permission gate; cross-service hook | transition PM `Draft→Scheduled→Done` chạy đủ; reject low-role 403 |
| **~5%** | E2E — full user journey trên browser thật | Playwright MCP (R-5 full journey), CHỈ luồng tới-hạn | tạo Work Order PM end-to-end + workflow button + console sạch |

Đỉnh đắt và giòn → giữ ít, chỉ luồng critical. Đáy rẻ và bền → là phần lớn suite. Đừng đẩy logic xuống test bằng Playwright khi 1 unit test service-layer bắt được.

**Beyonce Rule** — *"if you liked it you shoulda put a test on it"*: hạ tầng / refactor / migrate KHÔNG có nhiệm vụ bắt bug của bạn — **test mới có**. Hệ quả kiểm-được: **mọi bug fix PHẢI kèm 1 test guard RED-trước-GREEN-sau** (Prove-It) — viết test reproduce bug (fail vì đúng lý do), rồi fix, rồi xanh; revert fix mà test vẫn xanh = guard giả, viết lại. Đây là cùng nguyên tắc R-9/LL-TEST-18: side-effect chưa được test = chưa được bảo vệ.

**Test sizes** (resource model — phân loại theo tài nguyên tiêu thụ, trực giao với pyramid):

| Size | Ràng buộc | Tốc độ | Ở AssetCore |
|------|-----------|--------|-------------|
| **Small** | 1 process, no I/O/network/DB | ms | pure mapping/enum, validator thuần (FE vitest, service pure-func) |
| **Medium** | localhost, có test-DB, không external service | giây | `bench run-tests` service/workflow/permission (đa số BE suite) |
| **Large** | browser/external service OK | phút | Playwright MCP journey, in-PDF/QR artifact assert |

Small chiếm đa số → nhanh, ổn định, dễ debug khi đỏ. Large (Playwright) đắt → đừng lạm dụng.

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Code grep thấy ổn, set `tests_ran=true`/`PASS`" | False-green. PHẢI chạy THẬT `bench run-tests` + ĐỌC dòng `Ran N ... OK`/`FAILED` (LL-TEST-21). `errors=1` ở `setUpClass` abort cả class mà grep không thấy. |
| "Feature mới pass ngay lần đầu → ngon" | Pass-ngay trên feature side-effect (notification/hook/SLA) = NGHI false-green: data dựng khớp giả định sai (LL-TEST-21 §4). Assert side-effect THẬT (row Notification Log / doc B tồn tại / Email Queue). |
| "Test đếm `<div class=label>` == N → N trang PDF, xanh" | Đếm template ≠ output render. Assert ARTIFACT thật: `pypdf` page-count + MediaBox / PIL pixel (LL-TEST-29, LL-TEST-26). |
| "Guard có `assertIn` key 'success' → contract ổn" | "Có-mặt" ≠ "đúng-ràng-buộc". Phải `assertEqual` type/value thật (LL-TEST-26). Revert fix mà test vẫn xanh = proxy, viết lại. |
| "UI test xài tên `Test Asset IMM-15` cho nhanh" | UI data KHÔNG rollback → rác prod (R-0/R-1/R-8). Dùng tên bệnh viện VN thực tế. |
| "fixture rollback tự lo, khỏi tearDown" | `FrappeTestCase` rollback PER-test; `setUpClass`+commit/lifecycle KHÔNG rollback → leak 776+ records (R-9). tearDownClass purge qua `_asset_cleanup.purge_asset` (LL-TEST-22). |
| "Detail thiếu nút workflow → bug, report luôn" | Có thể là role-gating đúng (LL-TEST-14/11) hoặc Vite HMR churn (LL-QA-11). Verify role + `v-if` + tab sạch TRƯỚC khi report. |
| "Sửa `api/*.py` xong, `run-tests` xanh → feature live trên HTTP" | gunicorn `--preload` đông cứng import: code live ở `run-tests`/`execute` nhưng CHƯA live HTTP tới khi USER reload → verdict `blocked-reload` (LL-QA-15, LL-TEST-25). |
| "Sửa endpoint module này, module kia không touch nên vẫn xanh" | SSoT introspect-được (tổng endpoint) đổi → suite KHÁC hardcode count ĐỎ (LL-TEST-27). Chạy LẠI MỌI suite assert vào nó; KHÔNG cộng số per-module từ trí nhớ. |
| "Full BE suite ĐỎ `Asset None not found` → 'môi trường' / 'bug module này'" | **Cả 2 kết luận đều sai nếu chưa chạy lại ISOLATED.** Lỗi CHỈ xuất hiện ở full-suite mà KHÔNG có khi `--module <mod>` chạy riêng = **fixture-contamination** (asset leak từ module/phiên khác), KHÔNG phải bug module (false-red) và KHÔNG được bỏ qua là "environmental" (false-green). Verdict THẬT = chạy LẠI đúng module ISOLATED (`--module assetcore.tests.test_immXX`); isolated xanh → module OK, đỏ → bug thật. (LL multi_session_concurrency + factory_engine_crash) |
| "Eval xong dọn ảnh là đủ" | tidy-eval CHỈ dọn FILE. User/data scoped tạo lúc eval → tear-down DB hoặc flag 🔴 "chờ purge" (LL-TEST-28, R-12). |

## Red Flags — STOP

- Set `verdict=PASS`/`tests_ran=true` mà KHÔNG có output `Ran N ... OK` THẬT của lượt chạy này.
- Báo aggregate "N test xanh" bằng cách cộng số per-module từ trí nhớ (chỉ chạy thật 1 module).
- Test đếm phần tử template (HTML block/div/thẻ/"có key") rồi SUY RA output/contract đúng (proxy).
- Feature side-effect mới (notification/hook/scheduler/SLA) pass ngay lần đầu, side-effect KHÔNG được assert thật.
- UI test data chứa `test`/`Test`/`TEST`/`IMM-XX`/tên giả/mã tạm (R-1).
- Tuyên bố "đã verify live trên HTTP / máy in tem / quét QR" khi BE `.py` sửa sau `--preload` boot mà USER chưa reload.
- `try/except: pass` quanh delete chain trong tearDown (nuốt exception = leak thầm).
- Report "code leak"/"stuck workflow"/"thiếu nút" mà chưa loại trừ enrich-sibling / role-gate / Vite-HMR.
- Console error / API 4xx-5xx còn trên trang mà vẫn khai PASS (R-7).
- Gán full-suite `Asset None not found` là "environmental"/"bug module" mà CHƯA chạy lại module đó ISOLATED (`--module`) để phân biệt fixture-contamination vs bug thật.
- Kết thúc session test/eval/factory mà `git status` còn `.png`/`_scan_junk`/`.py.tmp` rớt ngoài `.playwright/eval/` (R-11/R-12).

## Verification

Trước khi khai báo test "xong" — phải có BẰNG CHỨNG (không "có vẻ đúng"):

### Backend
- [ ] `bench --site miyano run-tests --module assetcore.tests.test_immXX` chạy THẬT — paste dòng `Ran N ... OK`/`FAILED` (LL-TEST-21).
- [ ] Workflow smoke test còn pass: `--module assetcore.tests.guards.test_workflows`; `EXPECTED_WORKFLOWS` update nếu thêm workflow mới (đếm từ JSON).
- [ ] Sửa SSoT introspect-được (tổng endpoint/cap-set/status-map/schema) → chạy LẠI MỌI suite assert vào nó (LL-TEST-27).
- [ ] Feature side-effect (notification/hook/scheduler/SLA): assert side-effect THẬT xảy ra (row tồn tại), KHÔNG chỉ return; RED fail vì đúng lý do (LL-TEST-18/21).
- [ ] Output sinh ra (PDF/ảnh/file): assert ARTIFACT render thật (`pypdf` page+MediaBox / PIL pixel), KHÔNG template (LL-TEST-29).
- [ ] Permission gate: mỗi mutating endpoint có test reject low-role (LL-TEST-19). Không có `except: pass` mới.
- [ ] Fixture `setUpClass` dọn ở `tearDownClass` (`_asset_cleanup.purge_asset`); local-var fixture `self.addCleanup` (R-9, LL-TEST-22).
- [ ] BE `.py` sửa sau gunicorn `--preload`: `bench execute` OK nhưng việc cần HTTP/Playwright/in-thật → verdict **`blocked-reload`** tới khi USER reload (LL-QA-15, LL-TEST-25).

### UI (tất cả phải pass)
- [ ] Pre-check master data đủ (R-2) — nếu tạo mới thì dùng tên thực tế (R-3).
- [ ] Dữ liệu test là THỰC TẾ (không có "test", "IMM-XX", tên giả); tất cả fields điền đầy đủ (R-1/R-4).
- [ ] Tất cả trang chi tiết có đủ workflow action buttons (đã loại trừ role-gate / Vite-HMR — LL-TEST-14, LL-QA-11).
- [ ] 0 console error + 0 API 4xx/5xx trên mọi trang (R-7); Playwright chạy THẬT trên `localhost:3000` — không đoán từ code.
- [ ] DoD UI checklist (xem [references/playwright-ui-tests.md](references/playwright-ui-tests.md)) đủ ô + DoD Report 0 FAIL.

### POST-RUN cleanup (phần của DONE — R-12)
- [ ] `bash .claude/scripts/tidy-eval-artifacts.sh` đã chạy; self-check `git status -uall | grep -iE '...'` RỖNG (R-11/R-12).
- [ ] Eval tạo user/data scoped → đã tear-down DB hoặc flag 🔴 "chờ purge" trong STATE/open_issues (LL-TEST-28).
- [ ] Pre-release: count `%test%` trên AC Asset / IMM Audit Trail = 0 (R-9).

### Reference files
- `assetcore/tests/imm00/test_imm00.py` — DocType-level pattern
- `assetcore/tests/guards/test_workflows.py` — smoke test
- `/home/miyano/frappe-bench/apps/assetcore/.env` — `TEST_USER` / `TEST_PASSWORD`
- `docs/imm-XX/07_Testing_QA.md` — UAT scenarios nguồn
- `.claude/skills/assetcore-test/references/playwright-patterns.md` — Playwright patterns
- `.claude/skills/assetcore-test/references/backend-tests.md` — backend test deep-dive
- `.claude/skills/assetcore-test/references/frontend-unit-tests.md` — vitest deep-dive
- `.claude/skills/assetcore-test/references/playwright-ui-tests.md` — UI test deep-dive

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
