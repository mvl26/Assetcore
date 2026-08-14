# SPEC — Chuẩn hoá cấu trúc file & thư mục FRONTEND

> **Trạng thái:** ✅ **ĐÃ THI HÀNH TOÀN BỘ L0–L5 ngày 2026-08-13** (chưa commit). Mọi bảng «hiện trạng» bên dưới giữ nguyên số đo **TRƯỚC** khi thi hành — đó là ảnh chụp gốc, đừng viết đè. Kết quả thực tế + các chỗ spec đo sai: xem §11.
> **Phạm vi:** chỉ `frontend/`. Backend (`assetcore/`) có spec riêng, làm sau.
> **Ngày đo:** 2026-08-13 · **Nhánh:** `feature/hieuc/develop-v0.2.0`
> **Nguyên tắc:** mọi con số trong tài liệu này đều **đo từ đĩa** và **tái lập được** bằng lệnh ở §9.

---

## 1. Mục tiêu

1. **Dọn file test về đúng chỗ** — mỗi file test phải nhìn tên là biết nó kiểm cái gì, nhìn thư mục là biết nó thuộc về ai.
2. **Thêm rule cưỡng chế** để Claude (và người) **không thể** tạo file test lung tung — rule bằng văn bản **cộng với** guard bằng máy.
3. **Dọn các file lệch quy ước** (thư mục rỗng, file tàn dư, 2 nguồn cùng chức năng).
4. **Chuẩn hoá tên** file/thư mục FE.

### Ngoài phạm vi (cố ý)

| Việc | Vì sao loại |
|---|---|
| Tách file `.vue` khổng lồ (`AssetDetailView.vue` 1.334 dòng…) | User chốt: *"không cần chia file"* |
| Chuyển sang `src/features/<miền>/` (vertical slice) | Chi phí 426 file + 1.220 import + ~5.589 trích dẫn — quyết định riêng, không thuộc đợt này |
| Đổi tên thư mục miền (`cm`→`corrective-maintenance`…) | §3.2 chứng minh **thư mục đã đúng chuẩn**; đổi tên tốn hàng nghìn trích dẫn mà không được gì |
| Sửa cấu trúc BE | Spec riêng |

---

## 2. Kết luận nhanh

| Câu hỏi | Trả lời (có số) |
|---|---|
| Tên **thư mục** có sai chuẩn không? | **KHÔNG.** 0/22 thư mục vi phạm kebab-case |
| Tên file **`.vue`** có sai không? | **KHÔNG.** 0/209 vi phạm PascalCase |
| Tên file **`.ts` nguồn** có sai không? | **Gần như không.** 2/122 sai |
| Vậy vấn đề tên nằm ở đâu? | **Toàn bộ ở file TEST.** 318 camelCase / 86 PascalCase, 47 tên nhiều dấu chấm, 2 tên nhúng mã ticket, 1 file lạc đuôi `.spec.ts` |
| "Test nằm lung tung" thực chất là gì? | **190/404 file sai TÊN** (đứng đúng thư mục) + **50/404 file sai CHỖ** (guard đọc đĩa, cần nhà riêng). Chỉ 50 file thực sự phải di chuyển |
| Rủi ro lớn nhất khi động vào? | **Guard xanh giả**: 7 guard quét thư mục **không chốt số lượng tối thiểu** → dời thư mục là chúng đếm 0 và **PASS** |

---

## 3. Hiện trạng đo được

### 3.1 Kiểm kê `frontend/src/`

| Thư mục | file nguồn | file test | LOC | Ghi chú |
|---|---|---|---|---|
| `views/` | 142 | **270** | **96.835** | 72% toàn bộ FE; 22 thư mục miền |
| `components/` | 74 | 54 | 21.281 | 9 nhóm; `common/` 33, `ui/` 8 primitive |
| `api/` | 29 | 21 | 10.983 | 22 theo miền + 7 hạ tầng |
| `stores/` | 18 | 16 | 6.008 | |
| `router/` | 2 | 11 | 3.873 | 148 route · 134 lazy-import |
| `composables/` | 20 | 7 | 3.668 | |
| `constants/` | 8 | 10 | 3.500 | có **cả** `label.ts` **và** `labels.ts` |
| `utils/` | 11 | 11 | 2.489 | |
| `types/` | 14 | 0 | 1.647 | |
| `test/` | 5 | 0 | 529 | harness dùng chung |
| `i18n/` | 2 | 1 | 415 | ⇄ `locales/` — **2 nguồn chuỗi** |
| `services/` | **1** | 0 | 100 | tàn dư, cạnh `api/` 29 file |
| `design/` · `directives/` | 0 · 1 | 1 · 0 | 143 · 42 | |
| `__tests__/` | 0 | **1** | 84 | lệch với 403 file co-located |
| `__snapshots__/` · `assets/` | 0 | 0 | 0 | **rỗng** |

Ngoài `src/`: `vite.config.ts` · `vitest.config.ts` · `tsconfig{,.node,.vitest}.json` · `tailwind.config.js` · `postcss.config.js` · `eslint.config.js` · `scripts/` (2 `.mjs`) · `public/` · `dist/`.

> Alias `@` khai ở **3 nơi độc lập**: `vite.config.ts:116` · `vitest.config.ts:16` · `tsconfig.json:19`. Sai lệch một nơi = gãy một đường (build / test / type-check).

### 3.2 Chuẩn hoá tên — kết quả kiểm tra

| Đối tượng | Chuẩn áp dụng | Vi phạm | Chi tiết |
|---|---|---|---|
| Thư mục trong `src/` | `kebab-case` | **0** | `master-data`, `tech-specs` là kebab hợp lệ; từ đơn (`asset`, `pm`, `cm`, `eol`) cũng là kebab hợp lệ |
| File `.vue` | `PascalCase` | **0 / 209** | |
| File `.ts` nguồn | `camelCase` | **2 / 122** | `i18n/messages.types.ts` (chấm giữa tên) · `views/tech-specs/TechSpecDetailView.spec.ts` (đuôi `.spec.ts`) |
| **File test** | *(chưa có chuẩn)* | **toàn bộ** | 318 camelCase · 86 PascalCase · 47 file có >2 dấu chấm · 2 file nhúng mã ticket (`…acr92.test.ts`, `…acr95.test.ts`) · 1 file `.spec.ts` |

**⇒ Kết luận quan trọng:** phần "chuẩn hoá tên" của FE **chỉ còn đúng một mặt trận là file test**. Mã nguồn đã đạt chuẩn 100%.

### 3.3 Phân loại toàn bộ 404 file test FE

| Nhóm | Số | Định nghĩa | Việc phải làm |
|---|---|---|---|
| **A** | **78** | Trùng tên nguồn cùng thư mục (`AssetDetailView.test.ts` ↔ `AssetDetailView.vue`) | ✅ đã đúng — giữ nguyên |
| **B** | **35** | Dạng `<Nguồn>.<khía-cạnh>.test.ts` (`imm04.transition.test.ts` ↔ `imm04.ts`) | ✅ đã đúng — giữ nguyên |
| **C1** | **190** | Kiểm **đúng 1 nguồn** trong cùng thư mục nhưng **tên không nói ra điều đó** (`smartSelectResilience.test.ts` → thật ra kiểm `SmartSelect.vue`) | 🔤 **ĐỔI TÊN tại chỗ** (không di chuyển) |
| **C2** | **11** | Chạm nhiều nguồn trong cùng thư mục (test hành vi nhóm) | 🔤 đặt tên theo nhóm, giữ chỗ |
| **C3** | **50** | **Guard đọc đĩa** (`readFileSync`/`readdirSync`) — cưỡng chế quy ước, parity doc↔mã, ngân sách adoption | 📁 **DI CHUYỂN** sang nhà riêng |
| **C4** | **40** | Không import nguồn cục bộ — test route/khởi động/tích hợp chéo | 📁 phân loại từng cái (§6, lô L3) |
| | **404** | | |

> Tổng file test đọc đĩa (mọi nhóm): **59**.

**⇒ "Test nằm lung tung" thực chất là 2 vấn đề khác nhau:** 190 file **sai tên** nhưng đúng chỗ, và 50 file **sai chỗ**. Chỉ 50 file cần di chuyển thật.

### 3.4 Chín điểm lệch quy ước (danh sách đóng)

| # | Điểm lệch | Hiện trạng | Xử lý |
|---|---|---|---|
| 1 | `src/__snapshots__/` | thư mục **rỗng** | xoá |
| 2 | `.playwright-mcp/` (gốc repo) | thư mục **rỗng**, đã gitignore | xoá |
| 3 | `src/services/` | **1 file** `frappeResource.ts` cạnh `api/` 29 file | gộp vào `api/` |
| 4 | `src/__tests__/` | **1 file** `responsiveDoD.test.ts` giữa 403 file co-located | chuyển theo §5 |
| 5 | `constants/label.ts` ⇄ `labels.ts` | 86 LOC / 6 nơi dùng ⇄ 916 LOC / 59 nơi dùng — lệch nhau **1 chữ `s`** | gộp về `labels.ts` |
| 6 | `src/i18n/` ⇄ `src/locales/` | 2 nguồn chuỗi song song (`messages.ts` vs `vi.json`/`en.json`) | chốt 1 SSoT — **cần quyết định** |
| 7 | `views/tech-specs/TechSpecDetailView.spec.ts` | file `.spec.ts` **duy nhất** trong repo | đổi `.test.ts` |
| 8 | `i18n/messages.types.ts` | dấu chấm giữa tên file nguồn | đổi `messageTypes.ts` |
| 9 | 2 file test nhúng mã ticket | `connectionsLegacyKeysRetired.acr92.test.ts`, `connectionsListAssetDeepLink.acr95.test.ts` | mã ticket chuyển vào mô tả test, bỏ khỏi tên file |

---

## 4. Rủi ro đặc thù — đọc kỹ trước khi thi hành

### 🔴 R1 — Guard **xanh giả** khi dời thư mục *(rủi ro số 1)*

5 guard quét đệ quy `resolve(SRC, 'views')`. Trong nhóm quét thư mục, **7 file không hề chốt số lượng tối thiểu**:

| Guard | Chốt dân số? | Hậu quả khi thư mục quét bị dời |
|---|---|---|
| `views/detailShellAdoption.test.ts` | **0** | đếm 0 file → **PASS** |
| `views/detailTabBarAdoption.test.ts` | **0** | đếm 0 → **PASS** |
| `components/common/bareConfirmBudget.test.ts` | **0** | đếm 0 → **PASS** |
| `utils/navigationGuard.meta.test.ts` | **0** | như trên |
| `components/ui/uiPrimitiveHygiene.test.ts` | **0** | như trên |
| `api/userSource.guard.test.ts` | **0** | như trên |
| `constants/appVersion.test.ts` | **0** | như trên |
| `listShellAdoption` · `detailAccessAdoption` · `responsiveDoD` · `modalOverlayHygiene` | 1–2 | đỏ (may mắn) |

**Nghĩa là:** dời file mà không sửa guard ⇒ suite **vẫn xanh 4.011 test**, trong khi guard đã ngừng canh. Đây đúng loại *false-green* mà STATE dự án đã ghi là bài học lặp lại.

### 🔴 R2 — 17 file giải đường dẫn **theo độ sâu**

17 file test dùng `resolve(HERE, '../..')` / `'../../..'`. Dời file **sâu thêm 1 cấp** ⇒ trỏ nhầm thư mục, **âm thầm**, không lỗi biên dịch.

### 🟠 R3 — 59 file test đọc đĩa nằm **ngoài tầm `vue-tsc`**

`vue-tsc` chỉ phủ đồ thị import. Lớp guard đọc **văn bản mã nguồn** không được compiler bảo vệ.

### 🟠 R4 — Trích dẫn ngoài `frontend/`

| Nguồn | Số lần nhắc |
|---|---|
| `.claude/` (skills, rule) | **3.930** lần nhắc `frontend/src/...` |
| `docs/` | **1.659** lần |
| 4 doc UI/UX (**có guard parity canh docs↔đĩa**) | `views/` **659** lần · `components/` 140 lần |
| BE `.py` | 29 lần — **8 file test BE đọc thẳng file FE** |
| **Tên file test bị nhắc trong `docs/` + `.claude/`** | **384 / 404 file** |
| Riêng chi phí đổi tên nhóm C1 | **864** lần nhắc, chỉ **8/190** file đổi tên được miễn phí |

**⇒ Đổi tên test KHÔNG miễn phí.** Mỗi lô đổi tên phải kèm sweep trích dẫn trong **cùng một commit**.

### 🟠 R5 — `scripts/ui-audit-inventory.mjs` hardcode đường quét

`ui-audit-inventory.mjs:141` — `COMPONENT_DIRS = [resolve(SRC,'components'), resolve(SRC,'views')]`. Bộ dò này sinh ra bảng 148 route trong `docs/ui-ux/00_AUDIT_HIEN_TRANG.md`, và có guard `uiAuditDocParity.test.ts` (15 TC) đối chiếu. Dời thư mục mà quên file này ⇒ bảng audit sai lệch.

---

## 5. Chuẩn đích (target convention)

### 5.1 Ba nhà cho file test — không có nhà thứ tư

| Loại test | Nhà | Tên file |
|---|---|---|
| **1 · Test của MỘT file nguồn** | **`<thư-mục-nguồn>/tests/`** *(sửa 2026-08-13 theo yêu cầu user — trước đây là «cạnh chính file nguồn»)* | `<Nguồn>.test.ts` — nếu là test duy nhất<br>`<Nguồn>.<khiaCanh>.test.ts` — nếu tách nhiều khía cạnh |
| **2 · Guard / parity / ngân sách** (đọc đĩa, cưỡng chế quy ước, đối chiếu doc↔mã) | **`src/guards/`** | `<chuDe>.guard.test.ts` |
| **3 · Tích hợp / khởi động / route** (không thuộc file nguồn nào) | **`src/integration/`** | `<luong>.integration.test.ts` |

`<Nguồn>` phải **khớp chính xác** tên file nguồn (`PascalCase` cho `.vue`, `camelCase` cho `.ts`).
`<khiaCanh>` là `camelCase`, **đã lược bỏ tiền tố trùng tên nguồn**.

**Ví dụ ĐÚNG / SAI:**

| ❌ Hiện tại | ✅ Sau chuẩn hoá | Vì sao |
|---|---|---|
| `components/common/BaseModalA11y.test.ts` | `components/common/BaseModal.a11y.test.ts` | Nguồn là `BaseModal.vue`; tên phải nói ra |
| `components/common/smartSelectResilience.test.ts` | `components/common/SmartSelect.resilience.test.ts` | Nguồn là `SmartSelect.vue` (Pascal), test đang viết thường |
| `views/asset/assetScanInfoSerial.test.ts` | `views/asset/AssetScanInfoView.serial.test.ts` | |
| `api/connectionsLegacyKeysRetired.acr92.test.ts` | `guards/connectionsLegacyKeys.guard.test.ts` | Đọc đĩa ⇒ là guard; **bỏ mã ticket khỏi tên** |
| `views/detailShellAdoption.test.ts` | `guards/detailShellAdoption.guard.test.ts` | Quét `SRC/views` ⇒ guard |
| `src/__tests__/responsiveDoD.test.ts` | `guards/responsiveDoD.guard.test.ts` | |
| `views/tech-specs/TechSpecDetailView.spec.ts` | `views/tech-specs/TechSpecDetailView.test.ts` | Bỏ đuôi `.spec.ts` |
| `App.auth.test.ts` | `integration/appAuth.integration.test.ts` | Test khởi động app, không thuộc 1 nguồn |

### 5.2 Quy tắc bổ sung — bắt buộc

| # | Quy tắc |
|---|---|
| N1 | **Cấm** mã ticket / mã sổ (`AC-CR-*`, `acr92`, `D7`…) trong **tên file**. Mã đi vào `describe()`/`it()` |
| N2 | **Cấm** đuôi `.spec.ts`. Chỉ dùng `.test.ts` |
| N3 | **Cấm** thư mục `__tests__/`. Test vào `<thư-mục-nguồn>/tests/`, hoặc `guards/`, hoặc `integration/`. **Cấm** đặt test ngang hàng file nguồn *(sửa 2026-08-13)* |
| N4 | **Cấm** dấu chấm trong tên file **nguồn** (`messages.types.ts` ❌ → `messageTypes.ts` ✅) |
| N5 | Mọi guard đọc đĩa **phải** lấy đường dẫn từ `src/test/paths.ts`, **cấm** `resolve(HERE, '../..')` |
| N6 | Mọi guard quét thư mục **phải** chốt dân số tối thiểu: `expect(files.length).toBeGreaterThanOrEqual(N)` |
| N7 | Thư mục: `kebab-case` · `.vue`: `PascalCase` · `.ts` nguồn: `camelCase` |

### 5.3 Cây thư mục đích

```
frontend/src/
  api/            components/     composables/    constants/
  design/         directives/     i18n/           router/
  stores/         types/          utils/          views/
  assets/
  <mỗi thư mục có file nguồn>/tests/   ← MỚI (2026-08-13) · MỌI test co-located nằm ở đây,
                                          KHÔNG đặt ngang hàng file nguồn
  guards/         ← MỚI · ~50 guard đọc đĩa (chuyển từ views/, router/, components/, api/, constants/, utils/, __tests__/)
  integration/    ← MỚI · test khởi động / route / luồng chéo
  test/           ← GIỮ · harness dùng chung + paths.ts (MỚI)
  ──────────
  services/       ← XOÁ (gộp vào api/)
  locales/        ← XOÁ hoặc i18n/ XOÁ (chốt 1 SSoT)
  __tests__/      ← XOÁ
  __snapshots__/  ← XOÁ (rỗng)
```

---

## 6. Kế hoạch triển khai — 5 lô, mỗi lô 1 PR, dừng được sau bất kỳ lô nào

> **Baseline phải ĐO LẠI đầu mỗi lô.** STATE ghi 403 file / 4.011 test (2026-08-11) — coi là **có thể stale**. Hôm nay đếm được **404 file test** trên đĩa.

### L0 · Dọn lệch quy ước — *rủi ro ~0, không đụng test nào*

| Việc | Chạm |
|---|---|
| Xoá `src/__snapshots__/`, `.playwright-mcp/` | 0 dòng mã |
| `src/services/frappeResource.ts` → `src/api/` | 1 file + ~3 import |
| Gộp `constants/label.ts` → `constants/labels.ts` | 1 file + 6 import |
| `i18n/messages.types.ts` → `messageTypes.ts` | 1 file + import |
| `TechSpecDetailView.spec.ts` → `.test.ts` | 1 file |
| Chốt SSoT chuỗi `i18n/` **hoặc** `locales/` | **cần quyết định trước** |

**Guard:** `vue-tsc --noEmit` 0 lỗi · `npx vitest run` **số test không đổi** · `eslint` 0 error mới.
**Rollback:** 1 `git revert`.

### L1 · Chống xanh giả — *lô quan trọng nhất, KHÔNG dời file nào*

| Việc | Chi tiết |
|---|---|
| Tạo `src/test/paths.ts` | export `FRONTEND_ROOT · SRC · VIEWS · COMPONENTS · GUARDS · REPO_ROOT · DOCS` |
| Gỡ đường dẫn theo độ sâu | **17 file** bỏ `resolve(HERE,'../..')` → dùng `paths.ts` |
| Chốt dân số | **7 guard** hiện 0 assert phải thêm `toBeGreaterThanOrEqual(N)`, N = số đo đầu lô |
| Bộ dò dùng chung nguồn | `scripts/ui-audit-inventory.mjs:141` đọc `paths.ts` thay vì hardcode |
| **Bài kiểm tra hiệu lực** | Đổi tên tạm `src/views` → `src/views__tmp`, chạy full suite: **mọi guard quét PHẢI ĐỎ**. Revert ngay. Guard nào không đỏ = chưa đạt, sửa tiếp |

**Chạm:** ~25 file test, **0 file nguồn**.
**Giá trị độc lập:** kể cả dừng ở đây, lô này vẫn đáng — nó bịt một lớp false-green đang tồn tại thật.
**🔒 CỔNG CHẶN: không được bắt đầu L2/L3 khi bài kiểm tra hiệu lực chưa pass.**

### L2 · Dựng `src/guards/` + di chuyển 50 guard

- Tạo `src/guards/`, chuyển **50 file nhóm C3** vào, đổi tên `<chuDe>.guard.test.ts`.
- Vì L1 đã bỏ đường dẫn theo độ sâu ⇒ di chuyển **không** làm lệch path.
- Sweep trích dẫn `docs/` + `.claude/` cho đúng 50 tên này **trong cùng commit**.

**DoD:** số test **không đổi** · mỗi guard vẫn báo đúng dân số (không có guard nào tụt về 0) · `uiAuditDocParity` + `uiFixPlanParity` + `uiListShellLot1Parity` + `uiDetailShellLot1Parity` xanh.

### L3 · Dựng `src/integration/` + phân loại 40 file nhóm C4

Với mỗi file: nếu nó import một nguồn ở **thư mục khác** → chuyển về cạnh nguồn đó và đổi tên theo §5.1; nếu là luồng chéo/khởi động/route → vào `src/integration/`.
Kèm sweep trích dẫn.

### L4 · Đổi tên 190 file nhóm C1 — *làm theo lô con, không làm một phát*

Chia theo thư mục, làm từ **rẻ đến đắt** (chi phí = số lần tên file bị nhắc trong `docs/` + `.claude/`):

| Đợt | Thư mục | Ghi chú |
|---|---|---|
| 4a | `components/` (common, ui, dashboard, asset, import…) | ít trích dẫn nhất |
| 4b | `api/` · `stores/` · `constants/` · `utils/` | |
| 4c | `views/` các miền nhỏ (settings, admin, audit, eol, system, tech-specs, master-data, dashboard) | |
| 4d | `views/` các miền lớn (pm, cm, incident, inventory, compliance, calibration, procurement, purchase, needs, training, document, commissioning, auth) | |
| 4e | `views/asset/` | đắt nhất — `AssetScanInfoView.test.ts` riêng nó bị nhắc **113** lần |

**Cách làm mỗi đợt:**
1. Sinh bảng ánh xạ tên cũ → tên mới (script, xem §8), **người duyệt bảng trước khi chạy**.
2. `git mv` theo bảng.
3. `sed` sweep `docs/` + `.claude/` theo đúng bảng đó.
4. Chạy full suite — **số test phải bằng** trước khi đổi.
5. Commit: 1 đợt = 1 commit.

### L5 · Khoá quy ước bằng máy (guard cưỡng chế) — *xem §7*

---

## 7. Rule cho Claude — để không tạo file test lung tung

Rule bằng văn bản dễ bị bỏ qua. Bắt buộc **2 lớp**: văn bản + guard bằng máy.

### 7.1 Lớp 1 — Guard bằng máy *(lớp thật sự có hiệu lực)*

**File mới:** `frontend/src/guards/testFileConvention.guard.test.ts`

Guard này quét toàn bộ `src/**/*.test.ts` và **ĐỎ** nếu vi phạm bất kỳ điều nào:

| Kiểm tra | Điều kiện đỏ |
|---|---|
| K1a · Không ngang hàng nguồn | File test nằm NGANG HÀNG file nguồn thay vì trong `tests/` |
| K1b · Có nhà hợp lệ | File trong `tests/` mà thư mục CHA không có nguồn cùng tên, **và** không ở `guards/`, **và** không ở `integration/` |
| K1c · `tests/` không mồ côi | Thư mục `tests/` rỗng, hoặc thư mục cha không chứa file nguồn nào |
| K2 · Khớp tên nguồn | File dạng `<X>.<khiaCanh>.test.ts` mà `<X>.vue`/`<X>.ts` không tồn tại cùng thư mục |
| K3 · Không mã ticket | Tên file khớp `/\.(ac|acr|cr)\d+\./i` hoặc chứa `AC-CR`/`AC-UX` |
| K4 · Không `.spec.ts` | Tồn tại bất kỳ file `*.spec.ts` |
| K5 · Không `__tests__/` | Tồn tại thư mục `__tests__` bất kỳ (tên đúng là `tests`) |
| K6 · Guard phải ở `guards/` | File **quét thư mục** (`readdirSync` **hoặc `import.meta.glob`**) mà không ở `src/guards/`; hoặc test trong `tests/` đọc file **ngoài thư mục cha** của nó |
| K7 · Guard không dùng path theo độ sâu | File trong `guards/` chứa `resolve(HERE` |
| K8 · Guard quét phải chốt dân số | File trong `guards/` có `readdirSync` mà không có `toBeGreaterThan`/`toBeGreaterThanOrEqual` |
| K9 · Tên thư mục/nguồn | Thư mục không kebab-case · `.vue` không PascalCase · `.ts` nguồn không camelCase |

**Nguyên tắc allowlist:** mọi ngoại lệ tồn dư đưa vào allowlist **đóng băng, CHỈ-GIẢM** (guard tự đỏ nếu allowlist dài ra) — cùng khuôn `modalInlineErrorAdoption.test.ts` đang dùng.

### 7.2 Lớp 2 — Rule văn bản, sửa đúng 3 chỗ

| File | Sửa gì |
|---|---|
| `.claude/skills/assetcore-fe/SKILL.md` | Thêm mục **“Vị trí & tên file test FE (BẮT BUỘC)”**: bảng 3 nhà §5.1 + 7 quy tắc §5.2 + câu chốt *“Trước khi tạo file test, xác định nó thuộc nhà nào trong 3 nhà. Không có nhà thứ tư.”* |
| `.claude/skills/assetcore-test/SKILL.md` | Thêm cùng bảng, kèm: *“Test FE mới PHẢI làm `testFileConvention.guard.test.ts` xanh. Chạy guard này TRƯỚC khi báo xong.”* |
| `CLAUDE.md` §15 (Code Style) | Thêm 1 dòng trỏ tới spec này + `guards/testFileConvention.guard.test.ts` là SSoT cưỡng chế |

**Văn bản rule đề xuất (dán nguyên):**

> **Vị trí & tên file test FE — BẮT BUỘC (SSoT: `frontend/src/guards/testFileConvention.guard.test.ts`)**
> Mỗi file test chỉ được ở **một trong ba nhà**:
> 1. **`<thư-mục-nguồn>/tests/`** — `<Nguồn>.test.ts` hoặc `<Nguồn>.<khiaCanh>.test.ts`. `<Nguồn>` khớp **chính xác** tên file nguồn ở **thư mục cha** của `tests/`.
> 2. **`src/guards/`** — test đọc đĩa / cưỡng chế quy ước / parity doc↔mã. Tên `<chuDe>.guard.test.ts`. Bắt buộc lấy path từ `src/test/paths.ts` và chốt dân số tối thiểu.
> 3. **`src/integration/`** — test khởi động app, route, luồng chéo nhiều nguồn. Tên `<luong>.integration.test.ts`.
>
> **CẤM:** đặt test ngang hàng file nguồn · `__tests__/` · `tests/` mồ côi · đuôi `.spec.ts` · mã ticket trong tên file · `resolve(HERE,'../..')` trong guard · guard quét thư mục mà không chốt dân số.
> **Trước khi báo xong:** chạy `npx vitest run src/guards/testFileConvention.guard.test.ts`.

### 7.3 Lớp 3 — tuỳ chọn, chặn từ hook

Có thể thêm `PostToolUse` hook (matcher `Write|Edit`) chạy guard convention khi đường dẫn khớp `frontend/src/**/*.test.ts` — chặn ngay lúc tạo file thay vì đợi chạy suite. **Đề xuất làm sau L5**, khi guard đã ổn định.

---

## 8. Sinh bảng ánh xạ đổi tên (dùng cho L4)

Script đề xuất `frontend/scripts/test-rename-plan.mjs` — **chỉ in ra bảng, không tự sửa**:

1. Duyệt mọi `src/**/*.test.ts`.
2. Bỏ qua nhóm A/B (đã đúng).
3. Với mỗi file còn lại: đọc các import `from './X.vue'` / `from '@/<dir>/X.ts'` **trong cùng thư mục**.
   - Đúng 1 nguồn ⇒ đề xuất `<Nguồn>.<khiaCanh>.test.ts`, trong đó `<khiaCanh>` = tên cũ **đã lược tiền tố trùng `<Nguồn>`**, camelCase hoá.
   - Có `readFileSync`/`readdirSync` ⇒ đề xuất `guards/<chuDe>.guard.test.ts`.
   - Không import nguồn cục bộ ⇒ đề xuất `integration/<luong>.integration.test.ts`.
4. In thêm **số lần tên cũ bị nhắc** trong `docs/` + `.claude/` để xếp thứ tự lô.
5. Xuất CSV: `cũ,mới,sốTríchDẫn,nhóm` → **người duyệt** rồi mới `git mv` + `sed`.

---

## 9. Lệnh đo lại (mọi số trong tài liệu này phải tái lập được)

```bash
cd frontend/src

# Kiểm kê
find . -name '*.test.ts' | wc -l                       # 404
find . -name '*.vue' | wc -l                           # 209
find . -name '*.ts' ! -name '*.test.ts' | wc -l        # 122

# Tên
find . -type d | while read d; do basename "$d" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$|^__[a-z]+__$' || echo "$d"; done   # 0
find . -name '*.vue' | while read f; do basename "$f" .vue | grep -qE '^[A-Z][A-Za-z0-9]*$' || echo "$f"; done          # 0
find . -name '*.spec.ts'                                # 1
find . -name '*.test.ts' | grep -iE '\.(acr|cr)[0-9]+\.'  # 2

# Guard
grep -rl "readFileSync\|readdirSync" . --include=*.test.ts | wc -l    # 59
grep -rln "resolve(HERE" . --include=*.test.ts | wc -l                # 17

# Trích dẫn ngoài (chạy ở gốc repo)
cd ../..
grep -rho "frontend/src/[a-zA-Z/]*" .claude/ | wc -l     # 3930
grep -rho "frontend/src/[a-zA-Z/]*" docs/ | wc -l        # 1659
```

---

## 10. Quyết định cần chốt trước khi thi hành

| # | Quyết định | Ảnh hưởng |
|---|---|---|
| **Q1** | `src/i18n/` hay `src/locales/` là SSoT chuỗi? | Chặn lô **L0**. Liên quan `i18n/messageParity.guard.test.ts` (đang đọc chéo `assetcore/utils/messages.py`) |
| **Q2** | Tên nhà cho guard: `src/guards/` — đồng ý? | Tên này sẽ đi vào hàng trăm trích dẫn, **chỉ đặt được một lần** |
| **Q3** | L4 (đổi tên 190 file / 864 trích dẫn) làm **toàn bộ** hay chỉ **áp cho file mới + đổi dần khi đụng tới**? | Toàn bộ = sạch ngay, tốn 864 lần sửa. Đổi dần = 0 chi phí hôm nay, nhưng repo còn 2 kiểu tên trong nhiều tháng |

---

## 11. Nhật ký sửa đổi

| Ngày | Nội dung |
|---|---|
| 2026-08-13 | Bản đầu — phân tích hiện trạng + kế hoạch L0–L5. Chưa thi hành. |
| 2026-08-13 | **THI HÀNH XONG L0–L5.** Baseline đo lại từ đĩa trước khi bắt đầu: **405 file test / 4030 test — 0 đỏ** (STATE cũ ghi 401/4000 = stale). Kết thúc: **406 file / 4057 test — 0 đỏ**, `vue-tsc` exit 0. Chi tiết bên dưới. |

### 11.1 Kết quả đo được (trước → sau)

| Chỉ số | Trước | Sau |
|---|---|---|
| File `.spec.ts` | 1 | **0** |
| File test nhúng mã ticket trong tên | 2 | **0** |
| `resolve(HERE, '../..')` trong test | 17 | **0** *(1 hit còn lại là regex literal trong chính guard cưỡng chế)* |
| `resolve(process.cwd(), …)` trong test | 14 | **0** *(3 hit còn lại là chú thích/regex)* |
| Test đọc đĩa nằm **ngoài** `src/guards/` | 59, rải khắp cây | **0 file quét thư mục**; 26 test co-located chỉ đọc file **cạnh nó** |
| Thư mục lệch quy ước (`__tests__/` · `design/` · `services/` · `i18n/` · `__snapshots__/` · `.playwright-mcp/`) | 6 | **0** |
| Nhóm C1 (test sai tên) | 221 | **0** |
| Guard **xanh giả** khi `src/views` biến mất | 16 file vẫn XANH | **0** — cả 35 guard ĐỎ |

### 11.2 Chỗ spec đo SAI — sửa lại cho lần sau

| Mục | Spec nói | Đo lại từ đĩa | Vì sao lệch |
|---|---|---|---|
| §3.3 nhóm **C3** (guard phải dời) | 50 | **33** | Spec phân loại bằng «file có chứa `readFileSync`». Đo lại theo **ĐỐI TƯỢNG ĐỌC**: 26 file là test HÀNH VI co-located chỉ kèm 1–2 `it` đọc **chính file nguồn cạnh nó** — dời chúng là sai. |
| §3.3 nhóm **C4** | 40 | **13** | Cùng nguyên nhân — định nghĩa «không import nguồn cục bộ» chặt hơn nhiều so với ước lượng. |
| §3.3 nhóm **C1** | 190 | **221** | Ước lượng thiếu. |
| §4 R4 chi phí sweep C1 | 864 | **368** | Đếm theo *lần nhắc đường dẫn*, không theo *tên file thật bị nhắc*. |
| §4 R1 bảng «7 guard không chốt dân số» | 7 file, có tên | **7 file nhưng KHÁC thành phần** | 3 file spec liệt kê **đã khoá rồi** (`detailShellAdoption` dùng `.toBe(TOTAL_DETAIL_VIEWS)`, `uiPrimitiveHygiene` + `DetailPageShell` dùng `toHaveLength`/`toBe`) — `toBeGreaterThan` không phải cách duy nhất chốt. Ngược lại `modalOverlayHygiene` + `detailAccessAdoption` bị chấm «đỏ may mắn» nhưng assert của chúng là `<=` trên **hằng số**, dân số tụt về 0 vẫn PASS. |
| §5.1 ví dụ `App.auth.test.ts` | «không thuộc 1 nguồn» ⇒ `integration/` | Đúng đích, **sai lý do** | File đó **có** `import App from '@/App.vue'`. Lý do đúng: nó mount cả app + router ⇒ test khởi động. |
| §9 lệnh đo | không phủ `import.meta.glob` | thiếu 1 lớp guard | `utils/depreciationMethodLeak.test.ts` quét **toàn bộ `/src/**/*.vue`** bằng `import.meta.glob` ⇒ lọt mọi bộ đếm dựa trên `readFileSync`/`readdirSync`. K6/K8 nay bắt cả lớp này. |

### 11.3 Sai khác có chủ ý so với spec (kèm lý do)

1. **§3.4 #5 — KHÔNG gộp `constants/label.ts` vào `labels.ts`.** Đo ra hai miền khác nhau: `label.ts` = SSoT **khổ tem in QR** (`LABEL_FORMATS`/`pageRuleFor`/`MAX_LABEL_BATCH`), `labels.ts` = **từ điển nhãn VI cho enum** (40+ map). Gộp sẽ biến `labels.ts` thành sọt rác và mâu thuẫn LL-FE-56. **Thay bằng đổi tên `label.ts` → `labelFormats.ts`** — bẫy lệch-1-chữ-`s` biến mất, 0 thiệt hại ngữ nghĩa.
2. **Q1 — `src/i18n/` gộp VÀO `src/locales/`, giữ nguyên vai trò từng file.** KHÔNG nhồi `messages.ts` thành `vi.json`: `messages.ts` là registry mã nghiệp vụ **sinh tự động** từ BE `assetcore/utils/messages.py`, có guard parity; chuyển thành JSON viết tay là giết pipeline đó.
3. **Bài kiểm tra hiệu lực chạy 2 LƯỢT, không phải 1.** Lượt `src/views` một mình **không chấm được 31/59 guard** vì chúng nằm TRONG `views/` và biến mất cùng thư mục. Phải thêm lượt `src/components`.
4. **`paths.ts` ném lỗi ngay lúc import** (`requireDir`) thay vì chỉ dựa vào assert dân số ở từng guard. Đây là lý do sau L2 **cả 35/35 guard đều ĐỎ** khi thư mục neo biến mất — mạnh hơn nhiều so với chốt dân số rời rạc.
5. **K6 nới theo luật, không theo allowlist:** test ngoài `guards/` được đọc đĩa **nếu chỉ đọc file cạnh nó**. Nhờ vậy 26 test hành vi giữ nguyên vị trí mà không cần allowlist 26 dòng.
6. **K8 đòi dấu hiệu TƯỜNG MINH** (`listFiles(…{min})` hoặc dấu `// [K8] dân số:`) thay vì dò `toBeGreaterThan` chung chung — vì `toBeGreaterThan(-1)` là kiểm **chỉ số**, đã làm 4 guard trông như đã khoá mà thực ra chưa.
7. **Hệ quả của việc dời 8 file «lai» (user chốt):** 2 guard khoá bất biến «mỗi view/primitive có test đặt CẠNH nó» bị vỡ (`capaDetailStates`, `ErrorState.test.ts` đã dời) ⇒ phải nới sang «có test ở cạnh nguồn **hoặc** trong `guards/`».
8. **Đổi quy ước tên kéo theo phải sửa guard đang cưỡng chế tên CŨ:** 4 guard khoá `<ten>DetailStates.test.ts` / `<ten>ListStates.test.ts` → đổi sang `<Nguồn>.states.test.ts`.

### 11.4 Công cụ mới sinh ra trong đợt này

| File | Vai trò |
|---|---|
| `frontend/src/test/paths.ts` | SSoT đường dẫn cho mọi guard. Neo bằng **mốc** (`package.json`+`vite.config.ts`), `requireDir()` ném lỗi lúc import, `listFiles(dir,{ext,min})` ném lỗi khi hụt dân số. |
| `frontend/src/guards/testFileConvention.guard.test.ts` | Cưỡng chế K1–K9 + allowlist K2 **đóng băng, chỉ-giảm** (35 dòng). Đã kiểm bằng **6 phép thử âm tính** — tạo file sai → guard ĐỎ đúng luật. |
| `frontend/scripts/test-rename-plan.mjs` | Sinh bảng ánh xạ đổi tên (chỉ in, `--csv`, `--group`). Tách khía cạnh theo **token camelCase** + phát hiện **trùng đích** + bảng `OVERRIDES` cho người đặt tay. |
