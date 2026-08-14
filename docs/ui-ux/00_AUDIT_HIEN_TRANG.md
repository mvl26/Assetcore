# Bản đồ hiện trạng UI/UX toàn Frontend — AssetCore

| Mục | Giá trị |
|---|---|
| Phạm vi | Toàn FE (`frontend/src/router/index.ts` + `frontend/src/views/`) — **không thuộc riêng IMM-XX** |
| Loại tài liệu | Core Doc cross-cutting (UI/UX baseline) — đầu vào ghim cho VÒNG 2–5 |
| Owner | BA (đo + đặc tả) · FE dev (thi hành từ vòng 2) |
| Trạng thái | In Progress — **baseline vòng 1 đã chốt** |
| Ngày đo | 2026-07-31 |
| Nhánh | `feature/hieuc/core-refinement` @ `3a6a391` |

## Tài liệu liên quan
- **Spec thi hành vòng 2**: [`01_DESIGN_SYSTEM.md`](./01_DESIGN_SYSTEM.md) — token ngữ nghĩa + hợp đồng API 7 primitive (**ADR-UX-04** ở §9 dưới đây là quyết định gốc)
- **Spec thi hành vòng 3**: [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md) — khuôn màn danh sách `ListPageShell` (primitive #8), 4 trạng thái loại trừ, diệt *false-empty* (**ADR-UX-05** ở §9)
- **Spec thi hành vòng 4**: [`03_DETAIL_PAGE_SHELL.md`](./03_DETAIL_PAGE_SHELL.md) — khuôn màn **chi tiết** `DetailPageShell` (tier-1 `components/common/`), 4 trạng thái `error > loading > notfound > content`, tắt panel thao tác ngoài trạng thái có-dữ-liệu (**ADR-UX-06**, **ADR-UX-07** ở §9)
- **Spec thi hành vòng 5 + capstone**: [`04_PHUONG_AN_SUA_TOAN_BO.md`](./04_PHUONG_AN_SUA_TOAN_BO.md) — hợp đồng **hộp thoại** tại SSoT `BaseModal.vue` + `useFocusTrap.ts` (no-fork), **và** phương án sửa **toàn bộ 135 route** chia 5 nhóm khuôn × 5 đợt (**ADR-UX-08/09/10** ở §9)
- Guard bất biến: `frontend/src/guards/uiAuditDocParity.guard.test.ts` (khoá A1+A2+A5 — bảng không mục theo thời gian) · `frontend/src/guards/uiFixPlanParity.guard.test.ts` (khoá phủ-kín-route của phương án tổng — **0 route mồ côi**)
- Bộ đo lại (CHỈ ĐỌC): `frontend/scripts/ui-audit-inventory.mjs` — xem §1.5; vòng 2–5 **phải** chạy `--check`
- Chính sách chữ VI trên UI: `memory/ui_copy_language_policy.md` + `assetcore-fe` LL-FE-53
- Nợ UI cũ theo module: `memory/imm0123_ui_bugs.md`, `memory/imm1516_ui_bugs.md`, `memory/wave2_ui_bugs_20260526.md`
- Sổ CR nghiệp vụ (KHÁC sổ này): `docs/imm-09/05_API_Specification.md §10.4` — `AC-CR-*` đã tới **AC-CR-102**

---

## §0. Phạm vi & Boundaries

Vòng 1 **CHỈ ĐO và VIẾT DOC**. Không sửa một dòng nghiệp vụ nào.

**Always (luôn áp dụng cho vòng 2–5 khi tiêu thụ tài liệu này):**
- Mọi hạng mục UI/UX phải truy được về **1 dòng trong §3** (route + file) — không sửa "cho đẹp" ngoài bảng.
- Mọi ô ❌ chỉ được đổi thành ✅ khi có **test render** chứng minh (không đổi doc trước code).
- Chữ hiển thị theo `LL-FE-53`: dịch đầy đủ tiếng Việt; giữ QR/PIN + viết tắt VN thông dụng.
- Sửa lớp hiển thị: giữ nguyên hợp đồng API và `data-testid` đang được test khoá.

**Never:**
- KHÔNG đổi endpoint / envelope / DocType để "cho khớp UI" — nợ UI không được đẩy sang BE.
- KHÔNG xoá `data-testid` đang có test.
- KHÔNG thêm thư viện UI mới (design system giải bằng primitive nội bộ — xem §7).
- KHÔNG coi ô `n/a` là "đã xong": `n/a` = tiêu chí không áp dụng cho màn đó (xem §1.3).

---

## §1. Phương pháp đo — tái lập được

### 1.1 Nguồn số
| Số | Cách đo | Kết quả 2026-07-31 |
|---|---|---|
| Chuỗi `path: '…'` thô | `grep -c "path: '" frontend/src/router/index.ts` | **149** |
| **Route thật (bản ghi route)** | 149 trừ chuỗi là **đích chuyển hướng** trong lambda | **148** |
| Route có view thật | route có `component: () => import('@/views/…')` giải được trên đĩa | **135** |
| Route chuyển hướng | có `redirect`, không có `component` | **13** |
| File view distinct | các view file được ≥1 route trỏ tới | **130** |
| File `.vue` trong `views/` | `find frontend/src/views -name '*.vue' \| wc -l` | **137** |

> **DELTA 149 → 148 (đã truy, không phải sai số).** Đề mục vòng 1 ghi "hôm nay = 149" theo phép đếm
> thô `grep -c "path: '"`. Đếm thật cho **148 bản ghi route**: chuỗi thứ 149 nằm ở
> `frontend/src/router/index.ts:289` — `redirect: (to) => ({ path: '/documents', query: … })` — tức
> **đích chuyển hướng bên trong hàm**, không phải khai báo route (`/documents` đã có route riêng ở
> `:267`). Nếu đưa nó thành 1 dòng thì `/documents` bị đếm 2 lần và mọi thống kê §2 lệch theo.
> Bộ dò vì thế bỏ mọi `path:` mà **cùng dòng phía trước có `redirect` hoặc `=>`**.
> Chính guard `uiAuditDocParity` đã phát hiện sai lệch này ở lần chạy đầu (`"/documents ×2"`).

> Chênh 137 − 130 = **7 file `.vue` trong `views/` không route nào trỏ tới** (view con của shell dashboard theo persona + view nhúng). Không phải mã chết — xem §3 cột *view file*.

### 1.2 Bộ dò 7 tiêu chí (regex trên file `.vue` thật)
| # | Cột | ✅ khi | Bằng chứng ghi trong §3.2 |
|---|---|---|---|
| 1 | **loading** | template render cờ chờ: `v-if/v-show` trên `isLoading\|loading\|pending\|isFetching`, hoặc `<LoadingSpinner>` / `<SkeletonLoader>` | tên cờ / component |
| 2 | **skeleton** | có `<SkeletonLoader>` \| `animate-pulse` \| `class="skeleton` | primitive dùng |
| 3 | **empty-state có hướng dẫn** | có câu rỗng VI (*Chưa có / Không có / Không tìm thấy / Trống*) **VÀ** trong ±12 dòng có CTA (`<button>`, `<RouterLink>`) hoặc câu hướng dẫn (*Hãy/Bấm/Nhấn/Tạo/Thử/Xoá bộ lọc*) | "câu rỗng + CTA" vs "câu rỗng NHƯNG cụt" |
| 4 | **error-state có nút thử lại** | nút «Thử lại/Tải lại» có `@click`, **hoặc** `<DetailLoadError @retry>`, **hoặc** `<RouteErrorBoundary>`, **hoặc** màn form có banner lỗi + nút gửi lại | nguồn nút retry |
| 5 | **responsive ≤768px** | **0 hazard**. Tailwind là mobile-first nên KHÔNG đếm số utility; chỉ tính 3 hazard thật: `grid-cols-N (N≥3)` áp ngay từ mobile · `<table>` không nằm trong khung `overflow-x-*` · chiều rộng cứng ≥480px | liệt kê hazard |
| 6 | **nhãn tiếng Việt đầy đủ** | 0 chuỗi EN lộ ở lớp hiển thị (text node + `placeholder/title/label`). Blacklist viết tắt: CAPEX/OPEX/SLA/KPI/CAPA/RCA/MTTR/MTBF/WO/PO/OEE/TCO/RTO/RPO/BOM/SOP + 40 từ EN thường gặp. **Loại trừ**: mã bản ghi/naming series (`PM-WO-2026-XXXXX`) vì là *value*, không phải copy | liệt kê chuỗi lộ |
| 7 | **a11y label** | số nhãn máy đọc (`aria-label`, `aria-labelledby`, `sr-only`, `<label for=`) ≥ số control (`<input>/<select>/<textarea>`) và ≥1 | `n nhãn / m control + k nút-icon` |

**Hợp thành 1 cấp (chống báo nợ giả):** nếu view uỷ quyền trạng thái cho component bọc bằng prop (`:loading` / `:error` / `@retry` — vd 8 dashboard persona → `PersonaDashboardShell.vue`), 4 tiêu chí trạng thái-tải được cộng từ component đó. Component chỉ được render mà **không** nhận `:loading`/`:error` (vd `SmartSelect`) **KHÔNG** được cộng — trạng thái nội bộ của 1 ô chọn không phải trạng thái của trang.

**Shell view** (`<component :is>` — `/dashboard`, `/assets/labels/print`): ô = **hợp** của mọi delegate; ✅ chỉ khi **mọi** delegate ✅.

### 1.3 Quy ước `n/a` (KHÔNG phải ✅, cũng KHÔNG phải nợ)
- Route `redirect` (13 route): cả 7 ô `n/a` — không có giao diện riêng.
- Màn **tĩnh** (không import `@/api/*`, `@/stores/*`, không `useQuery`): `loading`/`skeleton`/`error` = `n/a` (không có gì để tải).
- Màn **không render tập** (không có `v-for`): `empty` = `n/a`.
- Màn **không có control tương tác trực tiếp** (0 `<input>/<select>/<textarea>` và 0 nút-icon): `a11y` = `n/a`.

### 1.4 Mức đau (deterministic, không cảm tính)
Trọng số theo ô ❌: `empty 2 · error 2 · responsive 2 · nhãn VI 2 · loading 1 · skeleton 1 · a11y 1` (tối đa 11).
`P0 ≥ 7` · `P1 = 4–6` · `P2 ≤ 3`.

### 1.5 Bộ dò đã thành MÃ CHẠY ĐƯỢC — `frontend/scripts/ui-audit-inventory.mjs`

Phép đo ở §1.1–§1.4 chỉ có giá trị nếu **vòng 5 đo lại được và chấm DELTA**. Vì thế toàn bộ bộ dò
được cài đặt lại thành script **CHỈ ĐỌC** (không sửa một dòng `.vue` nào):

```bash
node frontend/scripts/ui-audit-inventory.mjs --summary   # §2.1 + §2.2 tính lại từ mã nguồn
node frontend/scripts/ui-audit-inventory.mjs             # bảng markdown 148 dòng (khuôn §3.1)
node frontend/scripts/ui-audit-inventory.mjs --json      # máy đọc: cờ + bằng chứng từng route
node frontend/scripts/ui-audit-inventory.mjs --check [--verbose]   # đối chiếu với §3.1 hiện tại
```

**Số script tự đo được (2026-07-31, độc lập với bảng tay):**

| Số | Script | Bảng §3.1 | Khớp |
|---|---|---|---|
| Route thật | **148** | 148 | ✅ |
| Route có view | **135** | 135 | ✅ |
| Route redirect | **13** | 13 | ✅ |
| File view distinct | **130** | 130 | ✅ |
| Route P0 | **11** | 11 | ✅ |

**Đối chiếu ô (`--check`, chạy SAU khi đã hiệu đính §3.4):** **32 / 1036 ô lệch (3,1 %)** — tức
96,9 % số ô của bảng tay được mã độc lập tái lập. *(Trước hiệu đính: 35/1036; 5 ô sửa tay ở §3.4 kéo
xuống 32 — 4 ô về khớp, 1 ô cố ý lệch vì regex không nhìn thấy được, xem dòng cuối bảng.)*
32 ô lệch KHÔNG phải sai số ngẫu nhiên mà là **4 lớp khác biệt quy ước**, ghi ra đây để vòng sau
không "sửa" nhầm bên nào:

| Lớp lệch | Ô | Ai chặt hơn | Xử lý |
|---|---|---|---|
| **Biểu mẫu có banner lỗi + nút gửi lại** tính là *Lỗi+Thử lại* ✅ (§1.2 cho phép, regex không dựng được ngữ cảnh "gửi lại") | 11 | bảng tay rộng hơn | giữ bảng tay; script cố ý **bi quan** (94 ❌ vs 83 ❌) |
| **`<label>` thiếu `for=`** bị bảng tay tính là a11y ❌ ngay cả khi đủ `aria-label` | 10 | bảng tay chặt hơn | giữ bảng tay (đúng WCAG 2.1 AA hơn); script phơi `labelsMissingFor` trong `--json` |
| **Hợp thành 1 cấp** (ADR-UX-03): shell/persona uỷ quyền trạng thái — script lấy **giao** của mọi delegate, bảng tay lấy đại diện | 10 | tuỳ ô | vòng 5 đo lại **bằng script**, chốt 1 quy ước duy nhất |
| **Hazard chỉ thấy khi RENDER** (`/assets` ≤768px — thanh công cụ tràn ngang) | 1 | bảng tay chặt hơn | **giữ bảng tay**; đây là bằng chứng regex KHÔNG thay được mắt (§3.4) |

> **Kết luận dùng số nào:** bảng §3.1 (đã hiệu đính tay + render thật) là **bản chốt của vòng 1**.
> Script là **thước đo lại** cho vòng 2–5: chạy `--check` sau mỗi vòng, số ô lệch phải **giảm** khi
> nợ được trả, và mọi route mới phải xuất hiện ở cả hai nguồn.

**Hai lỗi bộ dò đã tự bắt và sửa trong lúc đối chiếu** (giữ lại để không tái phạm):
1. `path:` rút gọn 1 dòng `{ path: '/pm', redirect: '/pm/dashboard' }` — neo `^\s*redirect:` bỏ sót
   **9/13** route chuyển hướng, biến chúng thành "không giải được" giả.
2. Thuộc tính **bound** `:title="expr"` bị đọc như chữ hiển thị ⇒ tên state EN trong biểu thức
   (`'Pending Approval'` — là *value* gửi BE) báo nợ nhãn VI giả cho màn thực ra đã Việt hoá.
   Cùng lý do: `placeholder="CAPA-XXXX"` là **mặt nạ mã**, không phải viết tắt chưa dịch (LL-FE-53).

---

## §2. Số đo tổng quan

### 2.1 Nợ theo tiêu chí (mẫu số = 135 route có view)
| Tiêu chí | ❌ | n/a | ✅ | Tỷ lệ ❌ |
|---|---|---|---|---|
| a11y label | **87** | 16 | 32 | 64% |
| error-state có nút thử lại | **83** | 3 | 49 | 61% |
| skeleton | **75** | 3 | 57 | 56% |
| responsive ≤768px | **31** | 0 | 104 | 23% |
| empty-state có hướng dẫn | **26** | 19 | 90 | 19% |
| loading | **23** | 3 | 109 | 17% |
| nhãn tiếng Việt đầy đủ | **4** | 0 | 131 | 3% |

> Cột *responsive* đã cộng **3 route** phát hiện thêm ở bước hiệu đính (§3.4): `/assets` (đo bằng mắt @390px),
> `/needs-requests/:id` và `/procurement-plans` (bảng ngoài khung cuộn, trích dẫn dòng mã). Cột *empty*
> giữ **26** vì hiệu đính cộng 1 (`/assets/:id`) và trừ 1 (`/compliance/heatmap`).

> **Chốt nguồn chấm DELTA từ vòng 3 (BA, 2026-07-31 — không sửa bảng tay ở trên).** Bảng này là **bảng TAY**
> (mẫu số 135 route có view). Chạy **bộ dò** `node frontend/scripts/ui-audit-inventory.mjs` trên cùng đĩa cho
> mẫu số **148 route** và kết quả khác: *Lỗi+Thử lại* ❌ **94** (tay: 83) · *Rỗng+HD* ❌ **28** (tay: 26) ·
> *a11y* ❌ **78** (tay: 87). Nguyên nhân đã ghi ở **AC-UX-031** (3 quy ước chưa chốt) — **ĐÃ CHỐT ở vòng 5 bằng ADR-UX-10** (§9): bộ dò là SSoT cho DELTA, bảng tay dưới đây **đóng băng** làm ảnh chụp vòng 1.
> ⇒ Quy ước tạm thời: **mọi DELTA của vòng 3–4 chấm bằng BỘ DÒ** (chạy TRƯỚC/SAU, so số), **không** chấm bằng
> bảng tay. Bảng tay giữ nguyên làm ảnh chụp vòng 1.

### 2.2 Phân bố mức đau (148 route)
| Mức | Số route | Ghi chú |
|---|---|---|
| P0 | **11** | dồn ở màn tạo/sửa (form) và 2 màn quản trị |
| P1 | **49** | +2 `/assets`, `/assets/:id` · −1 `/compliance/heatmap` (§3.4) |
| P2 | **88** | gồm 13 route redirect (mặc định P2) |

---

## §3. Bảng hiện trạng — 148 route × 7 tiêu chí

Đọc bảng: `✅` đạt · `❌` nợ · `n/a` không áp dụng (§1.3). Cột *view file* là đường dẫn
tương đối repo, đã kiểm tra tồn tại trên đĩa. Dòng `— (redirect)` là route chuyển hướng,
không có giao diện riêng. Thứ tự dòng = thứ tự khai báo trong `frontend/src/router/index.ts`.

### 3.1 Bảng đầy đủ

> ⚠️ **Cách đọc bảng này kể từ 2026-08-03 (`ADR-UX-11`, §9).** Bảng **SỐNG theo LÔ adoption**, không còn đóng
> băng toàn phần như `ADR-UX-10` phát biểu ban đầu:
> - Route **đã qua một lô** ⇒ ô của cột tương ứng phản ánh **đĩa hôm nay**, và được **guard ép 2 chiều**
>   (`frontend/src/guards/uiListShellLot1Parity.guard.test.ts`: `view import ListPageShell` ⟺ ô «Lỗi+Thử lại» = ✅).
> - Route **chưa qua lô nào** ⇒ ô vẫn là **ảnh chụp vòng 1** (2026-07-31), có thể lệch so với bộ dò.
> - **Cấm** chấm-tay-lại ô nào ngoài sổ lô đang chạy. Mọi con số tổng/DELTA vẫn đọc từ **bộ dò** (`ADR-UX-10`).
> - 🆕 **Ngoại lệ kể từ 2026-08-04 (`ADR-UX-22`, §9) — cột «Lỗi+Thử lại» đã ĐỐI SOÁT TOÀN CỘT.** Lô 2 của
>   `AC-UX-047` chốt: **riêng cột này** không còn ảnh chụp vòng 1 ở bất kỳ dòng nào — cả **148** ô khớp
>   **từng ô** với bộ dò và được guard `uiListShellLot1Parity.guard.test.ts` ép mỗi lượt chạy test.
>   Đối soát 2026-08-04 đã lật **15** ô (chỉ cột này, không đụng 6 cột còn lại):
>   **10 ô ✅→❌** (doc lạc quan hơn đĩa): `/login` (1) · `/a/:token` (13) · `/assets/:id/info` (14) ·
>   `/assets/:id/edit` (18) · `/reference-data` (27) · `/calibration/new` (59) · `/user-profiles/new` (118) ·
>   `/user-profiles/:user` (119) · `/account/change-password` (120) · `/needs-requests/new` (123);
>   **5 ô ❌→✅** (mã đã trả nợ, doc chưa ghi nhận): `/capas/:id` (70) · `/purchases` (108) ·
>   `/user-profiles` (117) · `/procurement-plans` (125) · `/vendor-profiles` (135) — trong đó 4 dòng cuối là
>   **nợ vòng 3** đã hẹn xử lý ở lô 2, và `/capas/:id` là hệ quả của vòng 4 (`DetailPageShell`).
>   ⇒ Sau đối soát: **69 ô ❌ / 63 ô ✅ / 16 ô n/a**, khớp bộ dò **69**. **Cấm** chấm-tay ô cột này —
>   sửa mã rồi chạy lại bộ dò, guard sẽ đòi cập nhật.
> - 6 cột còn lại (Loading · Skeleton · Rỗng+HD · ≤768px · Nhãn VI · a11y) **vẫn** là ảnh chụp vòng 1 cho
>   route chưa qua lô — bộ dò 2026-08-04 còn **49** ô lệch ở 6 cột đó (`node frontend/scripts/ui-audit-inventory.mjs --check`).
>   Đó là nợ đã biết, **không** phải mục tiêu của `AC-UX-047`.
> - Sổ **lô 1 lớp DANH SÁCH** (12 route): [`02_LIST_PAGE_SHELL.md §12.2`](./02_LIST_PAGE_SHELL.md).
> - Sổ **lô 1 lớp CHI TIẾT** (8 route, `AC-UX-048`): [`03_DETAIL_PAGE_SHELL.md §12.2`](./03_DETAIL_PAGE_SHELL.md).
>   Guard `frontend/src/guards/uiDetailShellLot1Parity.guard.test.ts` bám cột «Trạng thái» của **sổ lô** chứ không bám
>   ô §3.1 hai chiều — vì dòng **134** `/procurement-decisions/:id` đang ✅ **sai từ bảng tay vòng 1** (đĩa
>   2026-08-03: `DecisionDetailView.vue` có **0** hit `DetailLoadError`/`@retry`/«Thử lại»). Chi tiết:
>   **ADR-UX-12** (§9). Chiều được ép: route `ĐÃ ĐÓNG` trong sổ ⇒ ô §3.1 **phải** là ✅.

| # | Route (`path`) | View file | Loading | Skeleton | Rỗng+HD | Lỗi+Thử lại | ≤768px | Nhãn VI | a11y | Đau |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `/login` | `frontend/src/views/auth/LoginView.vue` | ✅ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P2 |
| 2 | `/register` | `frontend/src/views/auth/RegisterView.vue` | ❌ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P1 |
| 3 | `/set-password` | `frontend/src/views/auth/SetPasswordView.vue` | ❌ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P1 |
| 4 | `/profile` | `frontend/src/views/auth/ProfileView.vue` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 5 | `/settings/notifications` | `frontend/src/views/settings/NotificationSettingsView.vue` | ✅ | ❌ | n/a | ✅ | ✅ | ✅ | n/a | P2 |
| 6 | `/unauthorized` | `frontend/src/views/auth/UnauthorizedView.vue` | n/a | n/a | n/a | n/a | ✅ | ✅ | n/a | P2 |
| 7 | `/` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 8 | `/launcher` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 9 | `/modules` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 10 | `/dashboard` | `frontend/src/views/dashboard/DashboardView.vue` | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | n/a | P2 |
| 11 | `/assets` | `frontend/src/views/asset/AssetListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 12 | `/qr-scan` | `frontend/src/views/system/QRScanView.vue` | n/a | n/a | n/a | n/a | ✅ | ✅ | ✅ | P2 |
| 13 | `/a/:token` | `frontend/src/views/system/QrResolveView.vue` | ✅ | ❌ | n/a | ❌ | ✅ | ✅ | n/a | P2 |
| 14 | `/assets/:id/info` | `frontend/src/views/asset/AssetScanInfoView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | n/a | P2 |
| 15 | `/assets/new` | `frontend/src/views/asset/AssetCreateView.vue` | ❌ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P1 |
| 16 | `/assets/labels/print` | `frontend/src/views/asset/AssetLabelPrintView.vue` | ❌ | ❌ | n/a | ❌ | ✅ | ✅ | ✅ | P1 |
| 17 | `/assets/:id` | `frontend/src/views/asset/AssetDetailView.vue` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | P1 |
| 18 | `/assets/:id/edit` | `frontend/src/views/asset/AssetEditView.vue` | ✅ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P2 |
| 19 | `/suppliers` | `frontend/src/views/purchase/SupplierListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 20 | `/suppliers/new` | `frontend/src/views/purchase/SupplierFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 21 | `/suppliers/:id` | `frontend/src/views/purchase/SupplierDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | n/a | P2 |
| 22 | `/suppliers/:id/edit` | `frontend/src/views/purchase/SupplierFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 23 | `/device-models` | `frontend/src/views/asset/DeviceModelListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 24 | `/device-models/new` | `frontend/src/views/asset/DeviceModelFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 25 | `/device-models/:id` | `frontend/src/views/asset/DeviceModelFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 26 | `/sla-policies` | `frontend/src/views/master-data/SlaPolicyListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 27 | `/reference-data` | `frontend/src/views/master-data/ReferenceDataView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 28 | `/commissioning` | `frontend/src/views/commissioning/CommissioningListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 29 | `/commissioning/new` | `frontend/src/views/commissioning/CommissioningCreateView.vue` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 30 | `/commissioning/:id` | `frontend/src/views/commissioning/CommissioningDetailView.vue` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | P2 |
| 31 | `/commissioning/:id/nc` | `frontend/src/views/commissioning/CommissioningNCView.vue` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 32 | `/commissioning/:id/timeline` | `frontend/src/views/commissioning/CommissioningTimelineView.vue` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | n/a | P2 |
| 33 | `/documents` | `frontend/src/views/document/DocumentManagement.vue` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 34 | `/documents/new` | `frontend/src/views/document/DocumentCreateView.vue` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 35 | `/documents/view/:name` | `frontend/src/views/document/DocumentDetailView.vue` | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | ❌ | P2 |
| 36 | `/documents/asset/:assetId` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 37 | `/documents/requests` | `frontend/src/views/document/DocumentRequestListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 38 | `/pm` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 39 | `/pm/dashboard` | `frontend/src/views/pm/PMDashboardView.vue` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 40 | `/pm/calendar` | `frontend/src/views/pm/PMCalendarView.vue` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | P0 |
| 41 | `/pm/work-orders` | `frontend/src/views/pm/PMWorkOrderListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 42 | `/pm/work-orders/new` | `frontend/src/views/pm/PMWorkOrderCreateView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 43 | `/pm/work-orders/:id` | `frontend/src/views/pm/PMWorkOrderDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 44 | `/pm/schedules` | `frontend/src/views/pm/PmScheduleListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 45 | `/pm/templates` | `frontend/src/views/pm/PmTemplateListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 46 | `/cm` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 47 | `/cm/dashboard` | `frontend/src/views/cm/CMDashboardView.vue` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | P0 |
| 48 | `/cm/create` | `frontend/src/views/cm/CMCreateView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 49 | `/cm/work-orders` | `frontend/src/views/cm/CMWorkOrderListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 50 | `/cm/work-orders/:id` | `frontend/src/views/cm/CMWorkOrderDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 51 | `/cm/work-orders/:id/diagnose` | `frontend/src/views/cm/CMDiagnoseView.vue` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | P0 |
| 52 | `/cm/work-orders/:id/parts` | `frontend/src/views/cm/CMPartsView.vue` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | P0 |
| 53 | `/cm/work-orders/:id/checklist` | `frontend/src/views/cm/CMChecklistView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 54 | `/cm/firmware` | `frontend/src/views/document/FirmwareCrListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 55 | `/cm/firmware/:id` | `frontend/src/views/document/FirmwareCrDetailView.vue` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| 56 | `/cm/mttr` | `frontend/src/views/cm/CMMttrView.vue` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | P1 |
| 57 | `/calibration/dashboard` | `frontend/src/views/calibration/CalibrationDashboard.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | n/a | P2 |
| 58 | `/calibration` | `frontend/src/views/calibration/CalibrationListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 59 | `/calibration/new` | `frontend/src/views/calibration/CalibrationCreateView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 60 | `/calibration/schedules` | `frontend/src/views/calibration/CalibrationScheduleListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 61 | `/calibration/:id` | `frontend/src/views/calibration/CalibrationDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 62 | `/incidents/dashboard` | `frontend/src/views/incident/IMM12DashboardView.vue` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | n/a | P2 |
| 63 | `/incidents/list` | `frontend/src/views/incident/IncidentListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 64 | `/incidents/new` | `frontend/src/views/incident/IncidentCreateView.vue` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 65 | `/incidents/:id` | `frontend/src/views/incident/IncidentDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | P2 |
| 66 | `/incidents` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 67 | `/rca` | `frontend/src/views/incident/RCAListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 68 | `/rca/:id` | `frontend/src/views/incident/RCADetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | P0 |
| 69 | `/capas` | `frontend/src/views/incident/CAPAListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 70 | `/capas/:id` | `frontend/src/views/incident/CAPADetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 71 | `/audit-trail` | `frontend/src/views/audit/AuditTrailListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 72 | `/compliance/rules` | `frontend/src/views/compliance/ComplianceRuleListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 73 | `/compliance/rules/:id` | `frontend/src/views/compliance/ComplianceRuleDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 74 | `/compliance/findings` | `frontend/src/views/compliance/FindingListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 75 | `/compliance/findings/:id` | `frontend/src/views/compliance/FindingDetailView.vue` | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | ❌ | P2 |
| 76 | `/compliance/audits` | `frontend/src/views/compliance/InternalAuditListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 77 | `/compliance/audits/:id` | `frontend/src/views/compliance/InternalAuditDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 78 | `/compliance/scorecard` | `frontend/src/views/compliance/ScorecardView.vue` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 79 | `/compliance/mr` | `frontend/src/views/compliance/ManagementReviewListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 80 | `/compliance/mr/:id` | `frontend/src/views/compliance/ManagementReviewDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 81 | `/compliance/heatmap` | `frontend/src/views/compliance/ComplianceHeatmapView.vue` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 82 | `/asset-transfers` | `frontend/src/views/asset/AssetTransferListView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 83 | `/asset-transfers/new` | `frontend/src/views/asset/AssetTransferCreateView.vue` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 84 | `/asset-transfers/:id` | `frontend/src/views/asset/AssetTransferDetailView.vue` | ✅ | ❌ | n/a | ✅ | ✅ | ✅ | ✅ | P2 |
| 85 | `/decommissions` | `frontend/src/views/eol/DecommissionListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 86 | `/decommissions/:id` | `frontend/src/views/eol/DecommissionDetailView.vue` | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | n/a | P2 |
| 87 | `/service-contracts` | `frontend/src/views/purchase/ServiceContractListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 88 | `/service-contracts/new` | `frontend/src/views/purchase/ServiceContractCreateView.vue` | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | P1 |
| 89 | `/service-contracts/:id` | `frontend/src/views/purchase/ServiceContractDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 90 | `/depreciation` | `frontend/src/views/asset/DepreciationView.vue` | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | P1 |
| 91 | `/inventory` | `frontend/src/views/inventory/InventoryDashboardView.vue` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | n/a | P2 |
| 92 | `/warehouses` | `frontend/src/views/inventory/WarehouseListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 93 | `/warehouses/:name` | `frontend/src/views/inventory/WarehouseDetailView.vue` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| 94 | `/spare-parts` | `frontend/src/views/inventory/SparePartListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 95 | `/spare-parts/:name` | `frontend/src/views/inventory/SparePartDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 96 | `/stock` | `frontend/src/views/inventory/StockLevelView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | P2 |
| 97 | `/stock-movements` | `frontend/src/views/inventory/StockMovementListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 98 | `/stock-movements/new` | `frontend/src/views/inventory/StockMovementCreateView.vue` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | P0 |
| 99 | `/stock-movements/:name/edit` | `frontend/src/views/inventory/StockMovementEditView.vue` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | P0 |
| 100 | `/stock-movements/:name` | `frontend/src/views/inventory/StockMovementDetailView.vue` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | n/a | P1 |
| 101 | `/inventory/uom` | `frontend/src/views/inventory/UomConversionView.vue` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | P0 |
| 102 | `/inventory/forecasts` | `frontend/src/views/inventory/SpareForecastView.vue` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 103 | `/inventory/watchlist` | `frontend/src/views/inventory/WatchlistView.vue` | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 104 | `/inventory/cycle-counts` | `frontend/src/views/inventory/CycleCountListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 105 | `/inventory/cycle-counts/new` | `frontend/src/views/inventory/CycleCountCreateView.vue` | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P1 |
| 106 | `/inventory/cycle-counts/:name` | `frontend/src/views/inventory/CycleCountDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | P2 |
| 107 | `/approvals/pending` | `frontend/src/views/audit/PendingApprovalsView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | n/a | P2 |
| 108 | `/purchases` | `frontend/src/views/purchase/PurchaseListView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 109 | `/purchases/new` | `frontend/src/views/purchase/PurchaseCreateView.vue` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | P1 |
| 110 | `/purchases/:name/edit` | `frontend/src/views/purchase/PurchaseEditView.vue` | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | P1 |
| 111 | `/purchases/:name` | `frontend/src/views/purchase/PurchaseDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 112 | `/purchase-orders` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 113 | `/purchase-orders/new` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 114 | `/purchase-orders/:name` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 115 | `/purchase-orders/:name/edit` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 116 | `/admin/roles` | `frontend/src/views/admin/RoleAdminView.vue` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | P0 |
| 117 | `/user-profiles` | `frontend/src/views/auth/UserProfileListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | P1 |
| 118 | `/user-profiles/new` | `frontend/src/views/auth/UserProfileFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 119 | `/user-profiles/:user` | `frontend/src/views/auth/UserProfileFormView.vue` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | P2 |
| 120 | `/account/change-password` | `frontend/src/views/auth/ChangePasswordView.vue` | ❌ | ❌ | n/a | ❌ | ✅ | ✅ | ❌ | P2 |
| 121 | `/account/profile` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 122 | `/needs-requests` | `frontend/src/views/needs/NeedsRequestListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 123 | `/needs-requests/new` | `frontend/src/views/needs/NeedsRequestCreateView.vue` | ❌ | ❌ | n/a | ❌ | ❌ | ✅ | ❌ | P1 |
| 124 | `/needs-requests/:id` | `frontend/src/views/needs/NeedsRequestDetailView.vue` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | P2 |
| 125 | `/procurement-plans` | `frontend/src/views/needs/ProcurementPlanListView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 126 | `/procurement-plans/:id` | `frontend/src/views/needs/ProcurementPlanDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | P1 |
| 127 | `/tech-specs` | `frontend/src/views/tech-specs/TechSpecListView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P1 |
| 128 | `/tech-specs/new` | `frontend/src/views/tech-specs/TechSpecCreateView.vue` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | P0 |
| 129 | `/tech-specs/:id` | `frontend/src/views/tech-specs/TechSpecDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 130 | `/vendor-evaluations` | `frontend/src/views/procurement/VendorEvalListView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P1 |
| 131 | `/vendor-evaluations/:id` | `frontend/src/views/procurement/VendorEvalDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | P1 |
| 132 | `/approved-vendors` | `frontend/src/views/procurement/AvlListView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P1 |
| 133 | `/procurement-decisions` | `frontend/src/views/procurement/DecisionListView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 |
| 134 | `/procurement-decisions/:id` | `frontend/src/views/procurement/DecisionDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 135 | `/vendor-profiles` | `frontend/src/views/procurement/VendorProfileListView.vue` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | P1 |
| 136 | `/vendor-profiles/:id` | `frontend/src/views/procurement/VendorProfileDetailView.vue` | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| 137 | `/imm06` | — *(redirect)* | n/a | n/a | n/a | n/a | n/a | n/a | n/a | P2 |
| 138 | `/imm06/programs` | `frontend/src/views/training/ProgramListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 139 | `/imm06/programs/new` | `frontend/src/views/training/ProgramDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 140 | `/imm06/programs/:name` | `frontend/src/views/training/ProgramDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 141 | `/imm06/sessions` | `frontend/src/views/training/SessionListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 142 | `/imm06/sessions/new` | `frontend/src/views/training/SessionDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 143 | `/imm06/sessions/:name` | `frontend/src/views/training/SessionDetailView.vue` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 144 | `/imm06/dashboard` | `frontend/src/views/training/TrainingDashboardView.vue` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | n/a | P2 |
| 145 | `/imm06/competencies` | `frontend/src/views/training/CompetencyListView.vue` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | P2 |
| 146 | `/imm06/competencies/:name` | `frontend/src/views/training/CompetencyDetailView.vue` | ✅ | ❌ | n/a | ✅ | ✅ | ✅ | ❌ | P2 |
| 147 | `/debug/asset-dashboard` | `frontend/src/components/commissioning/AssetDashboard.vue` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | n/a | P1 |
| 148 | `/:pathMatch(.*)*` | `frontend/src/views/system/NotFoundView.vue` | n/a | n/a | n/a | n/a | ✅ | ✅ | n/a | P2 |

### 3.2 Bằng chứng đo — 11 route P0

Chuỗi bằng chứng là kết quả regex thật trên file `.vue` (§1.2), không phải nhận xét cảm tính.

| Route | View file | Điểm đau | Bằng chứng từng ô ❌ |
|---|---|---|---|
| `/stock-movements/new` | `frontend/src/views/inventory/StockMovementCreateView.vue` | 9/11 | **loading**: không render cờ loading · **skeleton**: không có · **empty**: câu rỗng NHƯNG cụt (0 CTA) · **error**: có khối lỗi NHƯNG 0 nút thử lại · **responsive**: 8 utility sm:/md: · hazard: grid-cols-12 từ mobile · **a11y**: 7 nhãn máy-đọc / 9 control + 2 nút-icon |
| `/pm/calendar` | `frontend/src/views/pm/PMCalendarView.vue` | 8/11 | **loading**: không render cờ loading · **skeleton**: không có · **empty**: không có nhánh rỗng · **error**: không có khối lỗi · **responsive**: 1 utility sm:/md: · hazard: grid-cols-7 từ mobile |
| `/stock-movements/:name/edit` | `frontend/src/views/inventory/StockMovementEditView.vue` | 8/11 | **skeleton**: không có · **empty**: câu rỗng NHƯNG cụt (0 CTA) · **error**: có khối lỗi NHƯNG 0 nút thử lại · **responsive**: 6 utility sm:/md: · hazard: grid-cols-12 từ mobile · **a11y**: 5 nhãn máy-đọc / 6 control + 2 nút-icon · 5 <label> thiếu for= |
| `/admin/roles` | `frontend/src/views/admin/RoleAdminView.vue` | 8/11 | **skeleton**: không có · **empty**: không có nhánh rỗng · **error**: không có khối lỗi · **responsive**: 0 utility sm:/md: · hazard: grid-cols-3 từ mobile · **a11y**: 0 nhãn máy-đọc / 4 control + 0 nút-icon |
| `/vendor-profiles/:id` | `frontend/src/views/procurement/VendorProfileDetailView.vue` | 8/11 | **skeleton**: không có · **empty**: câu rỗng NHƯNG cụt (0 CTA) · **error**: có khối lỗi NHƯNG 0 nút thử lại · **responsive**: 0 utility sm:/md: · hazard: <table> không có khung overflow-x · **a11y**: 0 nhãn máy-đọc / 3 control + 0 nút-icon · 5 <label> thiếu for= |
| `/cm/dashboard` | `frontend/src/views/cm/CMDashboardView.vue` | 7/11 | **empty**: câu rỗng NHƯNG cụt (0 CTA) · **error**: không có khối lỗi · **responsive**: 2 utility sm:/md: · hazard: grid-cols-6 từ mobile · **a11y**: 0 nhãn máy-đọc / 0 control + 1 nút-icon |
| `/cm/work-orders/:id/diagnose` | `frontend/src/views/cm/CMDiagnoseView.vue` | 7/11 | **loading**: không render cờ loading · **skeleton**: không có · **empty**: không có nhánh rỗng · **error**: có khối lỗi NHƯNG 0 nút thử lại · **a11y**: 1 nhãn máy-đọc / 5 control + 1 nút-icon · 4 <label> thiếu for= |
| `/cm/work-orders/:id/parts` | `frontend/src/views/cm/CMPartsView.vue` | 7/11 | **loading**: không render cờ loading · **skeleton**: không có · **empty**: câu rỗng NHƯNG cụt (0 CTA) · **error**: có khối lỗi NHƯNG 0 nút thử lại · **a11y**: 0 nhãn máy-đọc / 3 control + 2 nút-icon · 1 <label> thiếu for= |
| `/rca/:id` | `frontend/src/views/incident/RCADetailView.vue` | 7/11 | **skeleton**: không có · **error**: có khối lỗi NHƯNG 0 nút thử lại · **responsive**: 0 utility sm:/md: · hazard: grid-cols-12 từ mobile · **vi**: 1 chuỗi EN: Hủy RCA |
| `/inventory/uom` | `frontend/src/views/inventory/UomConversionView.vue` | 7/11 | **loading**: không render cờ loading · **skeleton**: không có · **error**: không có khối lỗi · **responsive**: 1 utility sm:/md: · hazard: <table> không có khung overflow-x · **a11y**: 1 nhãn máy-đọc / 15 control + 0 nút-icon · 9 <label> thiếu for= |
| `/tech-specs/new` | `frontend/src/views/tech-specs/TechSpecCreateView.vue` | 7/11 | **loading**: không render cờ loading · **skeleton**: không có · **error**: có khối lỗi NHƯNG 0 nút thử lại · **responsive**: 0 utility sm:/md: · hazard: <table> không có khung overflow-x · **a11y**: 0 nhãn máy-đọc / 3 control + 0 nút-icon · 1 <label> thiếu for= |

### 3.3 Bằng chứng — 4 route còn chuỗi EN tĩnh (cột *Nhãn VI* = ❌)

| Route | View file | Chuỗi lộ ra lớp hiển thị |
|---|---|---|
| `/incidents/:id` | `frontend/src/views/incident/IncidentDetailView.vue` | «Bắt buộc có RCA Hoàn thành trước khi đóng (BR-12-02)» · «Cần RCA» · «Tình trạng SLA» |
| `/rca/:id` | `frontend/src/views/incident/RCADetailView.vue` | «Hủy RCA» |
| `/inventory/cycle-counts/:name` | `frontend/src/views/inventory/CycleCountDetailView.vue` | «Xem danh sách CAPA» |
| `/user-profiles` | `frontend/src/views/auth/UserProfileListView.vue` | «Import» — **2 chỗ**: text node `:164` và `title="Import Người dùng"` `:329` |

> **Vòng 3 đóng 1/4 dòng** (`AC-UX-042`): `/user-profiles` dịch «Import» → «Nhập từ Excel» / «Nhập người dùng từ Excel»
> (spec `02_LIST_PAGE_SHELL.md §4.2`). Sổ **AC-UX-029** hạ còn **3 route**. 3 dòng còn lại giữ nguyên ở vòng 3.
> Nếu bộ dò vẫn báo leak sau khi land ⇒ **mở lại** AC-UX-029 cho đủ 4 (bộ dò bắt cả text node lẫn thuộc tính `title=`).

### 3.4 Hiệu đính TAY — ô nào «đo bằng mắt», ô nào «suy từ grep»

Cờ regex chỉ là **proxy**: nó trả lời "có khuôn hay không", không trả lời "khuôn có đúng không".
Bảng dưới liệt kê **mọi ô đã bị sửa TAY** sau khi render thật (§5) hoặc sau khi đọc trực tiếp mã
nguồn. Ô nào không có tên ở đây thì mặc định là **suy từ grep** (§1.2).

| Route | Ô | Trước | Sau | Nguồn sự thật | Bằng chứng |
|---|---|---|---|---|---|
| `/assets` | ≤768px | ✅ | ❌ | **đo bằng mắt** | `.playwright/eval/uiaudit-09-mobile390-assets.png` @390px: hàng nút công cụ tràn ngang, «Xuất Excel» bị cắt, **trang cuộn ngang được**. Regex báo ✅ vì `<table>` ĐÃ nằm trong `overflow-x-auto` (`AssetListView.vue:426`) — hazard nằm ở thanh công cụ, **không có bộ dò tĩnh nào bắt được**. Mức đau P2 → **P1** |
| `/assets/:id` | Rỗng+HD | ✅ | ❌ | **đọc mã** | `AssetDetailView.vue:928-932` — nhánh rỗng chỉ có đúng câu «Chưa có sự kiện vòng đời», 0 hướng dẫn, 0 CTA ⇒ không đạt định nghĩa §1.2 (câu rỗng **VÀ** hướng dẫn/CTA). Mức đau P2 → **P1** |
| `/compliance/heatmap` | Rỗng+HD | ❌ | ✅ | **đo bằng mắt + đọc mã** | `.playwright/eval/uiaudit-06-report-heatmap.png` + `ComplianceHeatmapView.vue:91-94`: «Chưa có dữ liệu tuân thủ cho kỳ này.» **+** «Chọn kỳ khác hoặc đợi đánh giá tuân thủ chạy.» — đây chính là mẫu ĐÚNG mà §5 mục 6 khen. Ô ❌ cũ **tự mâu thuẫn với §5**. Mức đau P1 → **P2** |
| `/needs-requests/:id` | ≤768px | ✅ | ❌ | **đọc mã** | `NeedsRequestDetailView.vue:600` và `:653` — 2 bảng «Đầu tư mua sắm» / «Chi phí vận hành 5 năm» nằm thẳng trong `.card`, **không** khung `overflow-x` (chỉ bảng `:479` có). Mức đau giữ **P2** |
| `/procurement-plans` | ≤768px | ✅ | ❌ | **đọc mã** | `ProcurementPlanListView.vue:345` — bảng chọn đề xuất nằm trong khung chỉ có `overflow-y-auto` (cuộn DỌC), không cuộn ngang. Mức đau giữ **P1** |

**8 dòng được render thật — trạng thái sau hiệu đính** (`*` = có ô sửa tay):

| Route | Loại màn | Kết luận đối chiếu ảnh ⇄ bảng |
|---|---|---|
| `/login` | đăng nhập | Khớp. Khuyết tật nhìn thấy (thiếu «Quên mật khẩu?») là **nợ luồng**, không thuộc 7 ô ⇒ vào sổ AC-UX-024 |
| `/dashboard` | dashboard | Khớp. 2 panel «Không có dữ liệu» cụt đã được ghi ở §5; ô *Rỗng+HD* của route này là `n/a` vì shell không tự render tập — nợ nằm ở view persona (AC-UX-011, AC-UX-021) |
| `/assets` * | danh sách | **Sửa 1 ô** (≤768px) |
| `/assets/:id` * | chi tiết | **Sửa 1 ô** (Rỗng+HD) |
| `/capas/:id` | workflow | Ô *Nhãn VI* giữ ✅ **có chủ đích**: chuỗi tiếng Anh nhìn thấy trên màn là **dữ liệu do BE sinh**, không phải chữ FE viết (rubric §1.2 chỉ chấm lớp copy). Nợ đã ghi riêng ở **AC-UX-004** |
| `/compliance/heatmap` * | báo cáo | **Sửa 1 ô** (Rỗng+HD) |
| `/duong-dan-khong-ton-tai-uiaudit` | 404 | Khớp (`/:pathMatch(.*)*`). Khuyết tật căn giữa `min-h-[60vh]` là mỹ thuật ⇒ AC-UX-030 |
| `/settings/notifications` | biểu mẫu | Khớp. «Không có nút Lưu / không phản hồi» là nợ luồng ⇒ AC-UX-025; ô *a11y* `n/a` đúng vì 0 `<input>` và công tắc đã có `role="switch"` + `aria-checked` (`:106-109`) |

---

## §4. Kết quả test (số ĐỌC BẰNG MẮT từ output)

Lệnh: `cd frontend && npx vitest run` (toàn bộ FE, timeout tool 600000ms) — chạy 2026-07-31.

**Lần chạy chốt (sau khi thêm guard §8), `Duration 36.11s`:**
```
 Test Files  1 failed | 289 passed (290)
      Tests  1 failed | 2857 passed (2858)
```

**Lần chạy nền (trước khi thêm guard), `Duration 45.06s`** — để đối chiếu delta:
```
 Test Files  1 failed | 288 passed (289)
      Tests  1 failed | 2842 passed (2843)
```
Delta `+1 file / +15 test` = đúng bằng guard mới `uiAuditDocParity.guard.test.ts`; **số file đỏ không đổi (1)**
⇒ guard không làm hỏng gì và cũng không che lỗi sẵn có.

**Lần chạy XÁC NHẬN LẠI — sau khi thêm `ui-audit-inventory.mjs` + 5 ô hiệu đính §3.4, `Duration 42.78s`:**
```
 Test Files  1 failed | 289 passed (290)
      Tests  1 failed | 2857 passed (2858)
```
Trùng khít lần chạy chốt ⇒ **số test ĐỎ không tăng** (TC-UX-S01 đạt). Script kiểm kê là `.mjs`
chạy tay, **không** thêm file test; 5 ô sửa nằm trong tài liệu, **không** đụng `.vue`.

Guard riêng (A6): `npx vitest run src/guards/uiAuditDocParity.guard.test.ts`
```
 Test Files  1 passed (1)
      Tests  15 passed (15)
```
Chạy LẠI sau khi hiệu đính §3.4 ⇒ 5 ô sửa tay vẫn hợp lệ với bất biến A1+A2+A5.

**File ĐỎ (1):**
1. `frontend/src/views/dashboard/personas/tests/personaDashboards.test.ts` — `D-FE-1: current=opsmgr → render OpsmgrDashboardView`, dòng 59:
   `expect(w.html()).toContain('Trưởng phòng VT-TTBYT')`.
   **Nguyên nhân gốc (đã truy):** commit **`44cbff9` "fix(fe): drop the persona name from the ops dashboard title"** (2026-07-31 09:26) rút tiêu đề «Bảng điều khiển — Trưởng phòng VT-TTBYT» về «Bảng điều khiển», **không cập nhật test đi kèm** ⇒ test-drift, KHÔNG phải lỗi runtime.
   **Xử lý:** thuộc FE dev (file nằm dưới `frontend/src/views/` — vòng này bị A7 cấm chạm). Ghi sổ **AC-UX-023**, vòng 2.

Guard mới của vòng này (A6): `npx vitest run src/guards/uiAuditDocParity.guard.test.ts` → xem §8.

---

## §5. Render thật (Playwright MCP)

Môi trường: Vite dev `http://localhost:3000` (proxy site `miyano`), phiên đăng nhập sẵn có — persona hiển thị **«Chu Hiếu — Phòng Vật tư Trang thiết bị»**, dashboard nhận diện là **Cán bộ đảm bảo chất lượng / Kiểm toán**. Viewport 1440×900 (ảnh 1–8) và 390×844 (ảnh 9–10). Ảnh nằm ở `.playwright/eval/` (gitignored).

> **Ghi chú phạm vi:** persona này không có quyền tạo Sự cố (`/incidents/new` → `/unauthorized`), nên "màn biểu mẫu" lấy `/settings/notifications`. **KHÔNG có màn nào trả 417/500** ⇒ vòng này **không có mục BLOCKED-RELOAD**.

| # | Loại màn | Route | Ảnh |
|---|---|---|---|
| 1 | Đăng nhập | `/login` | `.playwright/eval/uiaudit-01-login.png` |
| 2 | Dashboard | `/dashboard` | `.playwright/eval/uiaudit-02-dashboard.png` |
| 3 | Danh sách | `/assets` | `.playwright/eval/uiaudit-03-list-assets.png` |
| 4 | Chi tiết | `/assets/AC-ASSET-2026-78105` | `.playwright/eval/uiaudit-04-detail-asset.png` |
| 5 | Workflow | `/capas/CAPA-2026-02432` | `.playwright/eval/uiaudit-05-workflow-capa.png` |
| 6 | Báo cáo | `/compliance/heatmap` | `.playwright/eval/uiaudit-06-report-heatmap.png` |
| 7 | 404 | `/duong-dan-khong-ton-tai-uiaudit` | `.playwright/eval/uiaudit-07-404.png` |
| 8 | Biểu mẫu | `/settings/notifications` | `.playwright/eval/uiaudit-08-form-notifications.png` |
| 9 | Danh sách @390px | `/assets` | `.playwright/eval/uiaudit-09-mobile390-assets.png` |
| 10 | Danh sách @390px | `/compliance/mr` | `.playwright/eval/uiaudit-10-mobile390-mr-enum-leak.png` |

### Khuyết tật NHÌN THẤY ĐƯỢC

**1. `/login`** — thiếu lối thoát «Quên mật khẩu?» (hệ thống CÓ `/set-password` nhưng màn đăng nhập không dẫn tới) ⇒ người quên mật khẩu vào ngõ cụt. Placeholder ô mật khẩu là `••••••••` (giả dạng chữ đã che) thay vì gợi ý thật. Nhãn «Email / Tên đăng nhập», «Mật khẩu» là `<label>` **không** `for=` ⇒ khớp ô ❌ a11y ở §3.

**2. `/dashboard`** — trong CÙNG một màn, phụ đề đã dịch («hành động khắc phục/phòng ngừa», «phân tích nguyên nhân gốc») nhưng **3 thẻ KPI vẫn để nguyên viết tắt EN**: «CAPA QUÁ HẠN», «CAPA ĐANG XỬ LÝ», «RCA CHƯA HOÀN TẤT», kèm chú thích **«Critical/Chronic»** chưa dịch. Hai panel rỗng («Vi phạm tuân thủ», «Kiểm toán nội bộ») chỉ có chữ **«Không có dữ liệu»** — cụt, 0 hướng dẫn, 0 CTA. Điểm tốt cần giữ: thẻ «ĐIỂM TUÂN THỦ» hiện `—` + «Chưa có scorecard kỳ này» (không bịa số 0).

**3. `/assets`** — cột **DANH MỤC in mã thô `CAT-28039`** thay vì tên danh mục; 3 cột (**GMDN**, **KHOA/PHÒNG**, **GIÁ TRỊ CÒN LẠI**) rỗng 100% nhưng vẫn chiếm chỗ; ô rỗng dùng **2 ký tự gạch khác nhau** (`—` ở GMDN vs `–` ở Giá trị còn lại). Nút «In nhãn hàng loạt» xám (disabled) **không kèm lý do/tooltip**. Tiêu đề «Danh sách Thiết bị» lặp 2 lần (thanh trên + H1).

**4. `/assets/:id`** — nhận diện bản ghi lặp 2 khối liền nhau (H1 «IMM-MDL-2026-0770» + card «TÀI SẢN / IMM-MDL-2026-0770 / AC-ASSET-…»). Tab **«chỉ số hiệu suất» viết thường** lệch với 5 tab Title-Case còn lại. Ô chọn «Khổ tem» **cắt chữ** («Tem 60×100mm» đè vào mũi tên) rồi **lặp lại y nguyên** ở badge «Khổ: Tem 60×100mm» ngay bên cạnh. Nhãn KPI lộ EN **«Tổng downtime»** và viết tắt mơ hồ **«Thời gian sửa chữa TB»** (TB = thiết bị hay trung bình?).

**5. `/capas/:id`** — **tiêu đề bản ghi in nguyên tiếng Anh**: «Calibration failed; out-of-tolerance parameters: Nhiệt độ» (chuỗi do BE sinh). Hai badge **«Trạng thái: Đang mở»** và **«Tiến trình: Đang mở»** trùng nghĩa ⇒ dual-track `status`/`workflow_state` rò ra người dùng. **Không có thanh bước workflow** dù design system đã có `WorkflowStepper.vue`. «Người phụ trách: **Administrator**» (user hệ thống, không phải họ tên). 6 trường nội dung đều `—` mà không câu hướng dẫn. Mã thiết bị `AC-ASSET-2026-70872` in dạng chữ thường, **không phải link** ⇒ tham chiếu chết.

**6. `/compliance/heatmap`** — nút **«Tải dữ liệu» vỡ 3 dòng** («Tải / dữ / liệu») vì hộp quá hẹp: lỗi layout thấy ngay ở 1440px. Breadcrumb + phụ đề lộ **mã nội bộ «IMM-16»** và từ EN **«Module»**. Điểm tốt cần nhân bản: empty-state ở đây ĐÚNG chuẩn — «Chưa có dữ liệu tuân thủ cho kỳ này.» + hướng dẫn «Chọn kỳ khác hoặc đợi đánh giá tuân thủ chạy.»

**7. 404** — nội dung VI đầy đủ + 2 lối thoát («Quay lại», «Về Bảng điều khiển»): đạt. Khuyết tật nhẹ: khối căn theo `min-h-[60vh]` nên **hụt xuống nửa dưới màn hình trống trơn**; không có ô tìm kiếm/gợi ý.

**8. `/settings/notifications`** — biểu mẫu 1 công tắc, **không có nút Lưu và không có phản hồi «đã lưu»** ⇒ người dùng không biết thao tác đã ăn chưa. Tên màn lệch giữa thanh trên («Cài đặt thông báo») và H1 («Thông báo»).

**9. `/assets` @390px** — bảng đã chuyển sang **thẻ dọc (đạt)**, nhưng **hàng nút công cụ tràn ngang**: «Xuất Excel» bị cắt mất chữ và trang **cuộn ngang được** (thanh cuộn ngang hiện ở đáy). Tiêu đề trên thanh trên bị icon tìm kiếm đè.

**10. `/compliance/mr` @390px** — **enum trạng thái lộ tiếng Anh trên badge: «Held», «Minutes Approved»** đứng cạnh badge VI «Bản nháp», «Đã đóng». Truy nguồn: `ManagementReviewListView.vue:42` CÓ map VI (`Held → Đã họp`, `Minutes Approved → Biên bản đã duyệt`) nhưng **chỉ dùng cho `<option>` bộ lọc (`:122`)**; badge dòng render `<StatusBadge :state="r.status" />` (`:152`, `:188`) với **giá trị thô**, mà `STATUS_MAP` trong `utils/formatters.ts:43` **không có 2 khoá này** ⇒ rơi về fallback in nguyên văn. H1 bị cắt («Soát xét …») do bị 2 nút chiếm chỗ.

**Ảnh chụp cây a11y (không thấy bằng mắt nhưng đọc được từ snapshot):** hàng danh sách là `generic [cursor=pointer]` — tức `<div>` bắt `@click`, **không có `role`/`tabindex`/thẻ `<a>`** ⇒ không thao tác được bằng bàn phím, trình đọc màn hình không thông báo là mục bấm được. Hai nút phân trang trước/sau (`BasePagination.vue`) **không có tên** (`button [disabled]`, `button` rỗng).

**Console khi render:** `403 FORBIDDEN` trên `assetcore.api.imm00.list_suppliers` tại `/assets` bị **nuốt câm** — danh sách nhà cung cấp trong bộ lọc rỗng mà không một dòng giải thích. (401 trong log là do thao tác đăng nhập thử của phiên đo, không phải lỗi sản phẩm.)

---

## §6. Sổ backlog AC-UX

**Namespace:** `grep -rn "AC-UX-" docs/` trước khi cấp số ⇒ **0 kết quả** (sổ trống). Sổ này **độc lập** với `AC-CR-*` (đã tới AC-CR-102) — không dùng chung dãy số.

Quy ước: `vòng` = vòng factory dự kiến xử lý (2–10). `Nguồn`: `§3` = đo tĩnh trên bảng hiện trạng · `§5` = nhìn thấy khi render thật.

| Mã | Route / File | Triệu chứng | Đau | Vòng | Nguồn |
|---|---|---|---|---|---|
| **AC-UX-001** | mọi màn danh sách dạng thẻ/dòng (mẫu: `/compliance/mr`, `/assets`) | Hàng bấm được là `<div>` gắn `@click`, không `role`/`tabindex`/`<a>` ⇒ bàn phím không tới được, trình đọc màn hình không biết bấm được | P0 | 2 | §5 |
| **AC-UX-002** | `frontend/src/components/common/BasePagination.vue` | Nút trang trước/sau **không có tên máy đọc** (snapshot: `button [disabled]`, `button` rỗng) | P0 | 2 | §5 |
| **AC-UX-003** | `/compliance/mr`, `/compliance/mr/:id` · `utils/formatters.ts:43` `STATUS_MAP` | Enum trạng thái in tiếng Anh trên badge («Held», «Minutes Approved») cạnh badge VI; map VI đã có nhưng chỉ dùng cho bộ lọc. **ĐÓNG vòng 8** — `STATUS_MAP` nhận `Held`/`Minutes Approved`/`Minutes_Approved` + màu chủ ý trong `STATUS_COLOR` + guard **parity 2 nguồn** (nhãn `MR_STATUSES` của `ManagementReviewListView` === `translateStatus(value)` cho cả 4 state); hợp đồng ở [`07 §7`](./07_DETAIL_TAB_BAR_SSOT.md) | P0 | 2 | §5 |
| **AC-UX-004** | `/capas`, `/capas/:id` (chuỗi do BE sinh) | Tiêu đề bản ghi tiếng Anh («Calibration failed; out-of-tolerance parameters: …») hiển thị nguyên văn cho người dùng cuối | P0 | 3 | §5 |
| **AC-UX-005** | 83 route theo bảng tay §3.1 — **94 theo bộ dò** lúc mở sổ (nguồn chấm delta, xem chú thích §2.1) | Lỗi tải không có nút «Thử lại» ⇒ người dùng phải F5 hoặc bỏ cuộc. **Vòng 3 đóng 4 route** (`/purchases`, `/user-profiles`, `/vendor-profiles`, `/procurement-plans`); **vòng 6 đóng tiếp 12 route (lô 1 của AC-UX-047)** ⇒ đo lại bộ dò **2026-08-03: còn 77** (89 − 12); **đo lại 2026-08-04: còn 69** — 8 đơn vị chênh KHÔNG do lô danh sách mà do **lô 1 lớp CHI TIẾT** (`AC-UX-048`, 8 route áp `DetailPageShell` ⇒ có `@retry`) ⇒ phép trừ tay `89 − flipped` là **số ảo**, con số duy nhất được tin là **bộ dò đo LIVE** (`ADR-UX-22`); **vòng 7 đóng 12 route lô 2 ⇒ còn 57** (đo LIVE, KHÔNG phải `77 − 12 = 65`: token `77` đã stale 8 đơn vị từ 2026-08-03). Sau lô 2, **0 route `*ListView`** còn ❌ — phần còn lại chuyển **AC-UX-047** | P0 | 3–4 | §3 |
| **AC-UX-006** | 87 route (cột *a11y* = ❌ trong §3.1); mẫu nặng: `AssetListView.vue` (0 nhãn / 8 control / 5 `<label>` thiếu `for=`) | Control không có nhãn máy đọc; `<label>` không gắn `for=`/`id` | P0 | 3 | §3 |
| **AC-UX-007** | 17 route có `<table>` ngoài khung cuộn (xem §7.1 bảng hazard) | Bảng tràn ngang ở ≤768px, không cuộn được trong khung riêng ⇒ vỡ trang | P1 | 2 | §3 |
| **AC-UX-008** | `/assets` @390px (hàng nút công cụ) | Thanh công cụ tràn ngang, «Xuất Excel» bị cắt, trang cuộn ngang | P1 | 2 | §5 |
| **AC-UX-009** | 11 route dùng `grid-cols-N (N≥3)` từ mobile — nặng nhất `grid-cols-12` (7 route), `grid-cols-7` (2 route) | Lưới nhiều cột áp ngay ở mobile ⇒ ô bị bóp còn vài chục pixel | P1 | 3 | §3 |
| **AC-UX-010** | 75 route (cột *Skeleton* = ❌) | Không có khung xương lúc chờ ⇒ nhảy layout / màn trắng | P1 | 3 | §3 |
| **AC-UX-011** | 26 route (cột *Rỗng+HD* = ❌) | Trạng thái rỗng cụt («Không có dữ liệu») hoặc không có nhánh rỗng | P1 | 3 | §3 |
| **AC-UX-012** | `/compliance/heatmap` | Nút «Tải dữ liệu» vỡ 3 dòng ngay ở 1440px | P1 | 2 | §5 |
| **AC-UX-013** | `/assets`, `/assets/:id`, `/settings/notifications` (khuôn `AppTopBar` + `PageHeader`) | Tiêu đề trang lặp 2–3 lần và **lệch chữ** giữa thanh trên với H1 | P1 | 2 | §5 |
| **AC-UX-014** | `/assets` (cột Danh mục) · `/compliance/*` (breadcrumb) | Mã nội bộ lộ ra UI: `CAT-28039` thay tên danh mục; `IMM-16` trong breadcrumb/phụ đề | P1 | 3 | §5 |
| **AC-UX-015** | `/assets` | 3 cột rỗng 100% vẫn chiếm chỗ; **2 glyph gạch khác nhau** (`—` vs `–`) cho cùng ý "không có" | P1 | 3 | §5 |
| **AC-UX-016** | `/assets` → `assetcore.api.imm00.list_suppliers` | 403 bị nuốt câm: bộ lọc nhà cung cấp rỗng, 0 lời giải thích | P1 | 4 | §5 |
| **AC-UX-017** | `/capas/:id` | Hai badge «Trạng thái» và «Tiến trình» cùng giá trị ⇒ lộ dual-track `status`/`workflow_state` | P1 | 4 | §5 |
| **AC-UX-018** | `/capas/:id` | Không dùng `WorkflowStepper.vue` dù đã có sẵn ⇒ người dùng không thấy bước kế tiếp | P1 | 4 | §5 |
| **AC-UX-019** | `/capas/:id` | Mã thiết bị `AC-ASSET-…` in dạng chữ, không phải link ⇒ tham chiếu chết | P1 | 4 | §5 |
| **AC-UX-020** | `/capas/:id` (và mọi màn hiện người phụ trách) | Hiện `Administrator` thay vì họ tên đầy đủ | P1 | 4 | §5 |
| **AC-UX-021** | `frontend/src/views/dashboard/personas/*` (3 thẻ KPI) | Thẻ KPI để nguyên viết tắt EN (CAPA/RCA) + chú thích «Critical/Chronic» chưa dịch, trong khi phụ đề CÙNG màn đã dịch | P1 | 2 | §5 |
| **AC-UX-022** | `/assets/:id` | Ô chọn «Khổ tem» cắt chữ + badge lặp lại y nguyên giá trị vừa chọn | P1 | 3 | §5 |
| **AC-UX-023** | `frontend/src/views/dashboard/personas/tests/personaDashboards.test.ts:59` | **Test ĐỎ**: kỳ vọng chuỗi «Trưởng phòng VT-TTBYT» đã bị commit `44cbff9` gỡ khỏi tiêu đề; test chưa cập nhật | P1 | 2 | §4 |
| **AC-UX-024** | `/login` | Không có «Quên mật khẩu?» dù hệ thống có `/set-password` ⇒ ngõ cụt | P2 | 4 | §5 |
| **AC-UX-025** | `/settings/notifications` | Không nút Lưu, không phản hồi «đã lưu» ⇒ không biết thao tác đã ăn chưa | P2 | 4 | §5 |
| **AC-UX-026** | `/assets/:id` | Tab «chỉ số hiệu suất» viết thường lệch 5 tab Title-Case còn lại | P2 | 3 | §5 |
| **AC-UX-027** | `/assets/:id` | Nhãn KPI «Tổng downtime» (EN) và «Thời gian sửa chữa TB» (viết tắt mơ hồ) | P2 | 3 | §5 |
| **AC-UX-028** | `AppSidebar.vue` | Nhãn menu bị cắt («Hành động khắc phục/p…») không tooltip ⇒ không đọc được tên đầy đủ | P2 | 3 | §5 |
| **AC-UX-029** | **3 route** (hạ từ 4 — `/user-profiles` tách sang **AC-UX-042**, đóng ở vòng 3): `/incidents/:id`, `/rca/:id`, `/inventory/cycle-counts/:name` | Chuỗi EN tĩnh còn trong template: «Tình trạng SLA», «Cần RCA», «Hủy RCA», «Xem danh sách CAPA» | P2 | 3 | §3 |
| **AC-UX-030** | `/` (404 view) | Khối 404 căn `min-h-[60vh]` ⇒ nửa dưới màn hình trống; không ô tìm kiếm/gợi ý | P2 | 5 | §5 |
| **AC-UX-031** | `frontend/scripts/ui-audit-inventory.mjs` ⇄ §3.1 | **32/1036 ô lệch** giữa bộ dò tự động và bảng tay, do 3 quy ước chưa chốt (biểu mẫu tính là có «Thử lại» · `<label>` thiếu `for=` · hợp thành 1 cấp cho shell). Chưa chốt 1 nguồn ⇒ vòng 5 không chấm DELTA sạch được. **ĐÓNG vòng 5 — ADR-UX-10**: bộ dò = SSoT cho DELTA, bảng tay §3.1 đóng băng (ảnh chụp vòng 1), 3 quy ước lệch trở thành **sai lệch đã ghi nhận** chứ không phải nợ | P2 | 5 | §1.5 |
| **AC-UX-032** | `frontend/tailwind.config.js` | **0 token màu ngữ nghĩa** (chỉ `brand.*`, `ink.*`) ⇒ **1690** lần hardcode `emerald/amber/rose/red/green-*` trong `views/` (**6119** nếu tính cả `slate/gray/blue/indigo/teal`); badge & cảnh báo lệch tông giữa các module | P1 | 2 | §7.2 |
| **AC-UX-033** | `frontend/src/components/ui/` | **Thư mục không tồn tại** — 0 primitive tầng 0 dùng chung; mỗi màn tự dựng khung rỗng/lỗi/bảng ⇒ nợ nhân bản theo số route | P1 | 2 | §7.2 |
| **AC-UX-034** | `tailwind.config.js` ⇄ `src/assets/styles/main.css` | 2 nguồn màu song song, **0 guard parity** ⇒ thêm token 1 bên là trôi âm thầm (không ai phát hiện tới lúc render lệch) | P1 | 2 | §7.2 |
| **AC-UX-035** | `frontend/src/assets/styles/main.css:12-20` | `:root` có `primary/success/warning/danger/neutral` nhưng **thiếu `--color-info`**, trong khi `.alert-info` đã dùng họ blue ⇒ ngữ nghĩa «thông tin» không có SSoT | P2 | 2 | §7.2 |
| **AC-UX-036** | `frontend/src/components/common/SkeletonLoader.vue` | 5 biến thể tự viết khối `.skeleton` rời (6 khối/dòng ở `table`) — không đi qua primitive ⇒ sửa shimmer/bo góc phải sửa 5 chỗ | P2 | 2 | §7.2 |
| **AC-UX-037** | 45 file `.vue` chứa chuỗi `Thử lại` | Copy nút thử lại **không có SSoT** ⇒ primitive mới rất dễ đẻ biến thể («Tải lại», «Thử lần nữa») cạnh `DetailLoadError.vue:71` | P2 | 2 | §5 |
| **AC-UX-038** | `components/ui/*` ⇄ 135 route có view · `components/common/StatusBadge.vue` | Vòng 2 **chỉ dựng tầng 0**, chưa áp primitive vào route nào (trừ `Skeleton`) ⇒ nợ adoption + 2 nguồn badge cùng tồn tại, chuyển vòng 3 | P1 | 3 | §7.2 |
| **AC-UX-039** | `components/ui/` (thiếu `FormField` · `IconButton` · `ClickableRow` · `PageTitle`) | 4 primitive trong danh sách §7.2 **không** nằm trong bộ 7 của vòng 2 ⇒ nợ a11y (87 route) và tiêu đề lặp (AC-UX-013) chưa có khuôn | P1 | 3 | §7.2 |
| **AC-UX-040** | `frontend/tailwind.config.js` (`theme.extend.colors.neutral`) | Bẫy **deep-merge**: khai 3 bậc `{50,500,700}` KHÔNG thay bảng `neutral` mặc định của Tailwind ⇒ `neutral-100…900` (xám ấm) vẫn dùng được và lệch tông với 3 bậc slate mới | P2 | 3 | §2.5 của `01_DESIGN_SYSTEM.md` |

| **AC-UX-041** | `frontend/src/components/ui/` (thiếu `ListPageShell`) · 4 màn danh sách đích | **Lỗi giả dạng rỗng (*false-empty*)**: API hỏng ⇒ view rơi vào nhánh «chưa có dữ liệu» ⇒ người dùng tin là KHÔNG có bản ghi và không có đường thử lại. 4 trạng thái (tải/lỗi/rỗng/có dữ liệu) hiện **không loại trừ** nhau, mỗi màn tự chế | P0 | 3 | §3 |
| **AC-UX-042** | `frontend/src/views/auth/UserProfileListView.vue:164` (text node) · `:329` (`title=`) | Chuỗi EN «Import» / «Import Người dùng» ở lớp hiển thị (tách khỏi **AC-UX-029**, `LL-FE-53`) | P2 | 3 | §3 |
| **AC-UX-043** | `frontend/src/views/auth/UserProfileListView.vue:92-107` | `load()` **0 `try/catch`**; `loading.value = false` nằm SAU `await` ⇒ API ném thì cờ **không bao giờ hạ**: khung xương quay mãi + unhandled rejection trong `onMounted` `:113-117` | P0 | 3 | §3 |
| **AC-UX-044** | `frontend/src/stores/imm01.ts:108-113` (`fetchPlans`) | Không set `loading`, không clear `error` đầu lượt ⇒ nhánh `v-if="store.loading"` (`ProcurementPlanListView.vue:213`) là **mã chết** và lỗi cũ dính lại sau lượt nạp mới. Vòng 3 **không được** sửa `stores/` ⇒ view tự giữ cờ | P1 | 4 | §3 |
| **AC-UX-045** | `frontend/src/views/procurement/VendorProfileListView.vue:88-90` ⇄ `:167-169` | **Double-state**: banner lỗi và khung rỗng «Chưa có nhà cung cấp nào.» hiện **cùng lúc**; banner không có nút thử lại | P1 | 3 | §3 |
| **AC-UX-046** | `VendorProfileListView.vue:116-118` · `ProcurementPlanListView.vue:233-235` | Nhánh rỗng **mã chết**: `v-if="…length === 0"` nằm trong `v-else-if="…length"` ⇒ không bao giờ render (in «Không có dữ liệu») | P2 | 3 | §3 |
| **AC-UX-047** | Bộ dò **đo LIVE 2026-08-04 (sau lô 2)** — nợ còn lại: **`[NO-CON=50]`** route có cột *Lỗi+Thử lại* = ❌, **0** trong đó là màn danh sách | Adoption `ListPageShell` diện rộng — phần còn lại của **AC-UX-005**; chia lô, mỗi lô kèm test render. **Lô 1 = 12 route ĐÃ ĐÓNG (2026-08-03)**, đặc tả ở [`02 §12`](./02_LIST_PAGE_SHELL.md): `/stock-movements` · `/asset-transfers` · `/warehouses` · `/device-models` · `/suppliers` · `/spare-parts` · `/documents/requests` · `/pm/templates` · `/cm/firmware` · `/sla-policies` · `/incidents/list` · `/rca`. **Lô 2 = 12 route DANH SÁCH CUỐI CÙNG** (đặc tả [`02 §13`](./02_LIST_PAGE_SHELL.md), chốt 2026-08-04): `/assets` · `/calibration` · `/calibration/schedules` · `/capas` · `/compliance/rules` · `/compliance/findings` · `/compliance/audits` · `/compliance/mr` · `/tech-specs` · `/vendor-evaluations` · `/approved-vendors` · `/procurement-decisions` ⇒ **ĐÃ ĐÓNG 2026-08-04**: bộ dò đo LIVE `69 → 57`, lọc `❌ AND /ListView/` = **0 route** — **họ `*ListView` hết nợ cột này**, phần còn lại (57) là màn chi tiết/tạo/sửa/tiện ích, không áp `ListPageShell`. Adopter `*ListView` **16 → 28**, test trạng thái **16 → 28** file. Guard `uiListShellLot1Parity.guard.test.ts` **KHÔNG còn** phép trừ ảo `89 − flipped`: nó **neo vào bộ dò đo LIVE** (`ADR-UX-22`) + parity **từng ô** cột này trên cả 148 dòng. **⚠️ ĐÍNH CHÍNH 2026-08-04 (BA Self-Correction, `ADR-UX-23`)**: câu «CUỐI CÙNG» của lô 2 đúng theo **cột *Lỗi+Thử lại*** nhưng **không** đồng nghĩa «mọi màn danh sách đã áp khuôn» — đo từ đĩa cùng ngày còn **12** file `*ListView.vue` chưa có `ListPageShell` (adopter **28/40**), trong đó `/audit-trail` và `/needs-requests` in banner lỗi **KÈM** câu «Không có… phù hợp» (lỗi giả dạng rỗng THẬT) mà bộ dò vẫn chấm ✅ vì nó đo **sự có mặt** của nút «Thử lại», không đo **loại trừ**. **Lô 3 = 12 route CÒN LẠI THẬT SỰ** (đặc tả [`02 §14`](./02_LIST_PAGE_SHELL.md), chốt 2026-08-04): `/audit-trail` · `/cm/work-orders` · `/service-contracts` · `/decommissions` · `/inventory/cycle-counts` · `/pm/work-orders` · `/pm/schedules` · `/needs-requests` · `/commissioning` · `/imm06/programs` · `/imm06/sessions` · `/imm06/competencies` ⇒ nghiệm thu = **adoption 28 → 40/40**, non-adopter **12 → 0** (guard `AC-UX-070`), test trạng thái **28 → 40** file. Token `[NO-CON=…]` **KHÔNG đổi** vì lô 3 vô hình với bộ dò — đó chính là lý do phải có phép đo thứ hai. **⇒ ĐÓNG HẲN 2026-08-04 (vòng 9)**: đo lại từ đĩa sau khi lô 3 land — `grep -L ListPageShell views/*/*ListView.vue` đếm được **0** dòng, `grep -l` được **40/40**, test trạng thái `*ListStates.test.ts` = **40** file, tổng file test FE **363 → 376**. Bộ dò đo LIVE cùng ngày vẫn `❌ 57` và `--check` = **0 ô lệch** — đúng như dự báo: lô 3 trả **nợ ADOPTION**, một đại lượng KHÁC với cột *Lỗi+Thử lại*, nên token `[NO-CON=57]` giữ nguyên. Nợ còn lại (57) là màn chi tiết/tạo/sửa/tiện ích, KHÔNG áp `ListPageShell`. Từ nay non-adopter bị **đóng băng ở 0** bằng guard `AC-UX-070` (CHỈ-GIẢM hai chiều). **🆕 2026-08-04 (vòng 10, lô 2 lớp CHI TIẾT — `AC-UX-048`):** 21 màn `*DetailView` áp `DetailPageShell` ⇒ bộ dò đo LIVE lật **7 ô ❌ → ✅** ở cột này (`/rca/:id` · `/service-contracts/:id` · `/purchases/:name` · `/procurement-plans/:id` · `/tech-specs/:id` · `/vendor-evaluations/:id` · `/vendor-profiles/:id`) và token đi **57 → `[NO-CON=50]`** — **số do `node frontend/scripts/ui-audit-inventory.mjs --summary` in ra**, KHÔNG phải phép trừ tay. 14 ô còn lại của lô 2 vốn đã ✅ (nay ✅ **đúng lý do**) | P0 | 4 | §3 |
| **AC-UX-048** | **21/32** màn chi tiết KHÔNG có lối nạp lại nào — không dùng `DetailLoadError` và cũng không có `@retry` (đo 2026-07-31): `asset/AssetDetailView` · `asset/AssetTransferDetailView` · `commissioning/CommissioningDetailView` · `compliance/FindingDetailView` · `document/DocumentDetailView` · `document/FirmwareCrDetailView` · `incident/CAPADetailView` *(đóng ở vòng 4)* · `incident/RCADetailView` · `inventory/SparePartDetailView` · `inventory/StockMovementDetailView` · `inventory/WarehouseDetailView` · `needs/NeedsRequestDetailView` · `needs/ProcurementPlanDetailView` · `procurement/DecisionDetailView` · `procurement/VendorEvalDetailView` · `procurement/VendorProfileDetailView` · `purchase/PurchaseDetailView` · `purchase/ServiceContractDetailView` · `purchase/SupplierDetailView` · `tech-specs/TechSpecDetailView` · `training/CompetencyDetailView` | Nạp bản ghi hỏng ⇒ trang trắng / khung rỗng «—» / dòng chữ đỏ cụt (14 màn còn `text-red-500`); panel thao tác vẫn hiện trên bản ghi không tồn tại. Vòng 4 đóng **1** (CAPA) ⇒ còn **20**; adoption `DetailPageShell` diện rộng. **Lô 1 (8 route) ĐÃ ĐÓNG 2026-08-03 ⇒ đo lại từ đĩa — nợ còn lại: `[NO-DET=0]`** màn chi tiết không có lối nạp lại nào. **Lô 1 = 8 route**, đặc tả ở [`03_DETAIL_PAGE_SHELL.md §12`](./03_DETAIL_PAGE_SHELL.md): `/stock-movements/:name` · `/warehouses/:name` · `/spare-parts/:name` · `/asset-transfers/:id` · `/cm/firmware/:id` · `/compliance/findings/:id` · `/suppliers/:id` · `/procurement-decisions/:id` — cả 8 đã áp khuôn (`20 → 12`); guard `uiDetailShellLot1Parity.guard.test.ts` ép `NO-DET == 20 − số route lô 1 ĐÃ ĐÓNG` **và** khớp số đo lại từ đĩa. **Nợ còn lại (12 màn)** cho lô 2–3: `asset/AssetDetailView` · `commissioning/CommissioningDetailView` · `document/DocumentDetailView` · `incident/RCADetailView` · `needs/NeedsRequestDetailView` · `needs/ProcurementPlanDetailView` · `procurement/VendorEvalDetailView` · `procurement/VendorProfileDetailView` · `purchase/PurchaseDetailView` · `purchase/ServiceContractDetailView` · `tech-specs/TechSpecDetailView` · `training/CompetencyDetailView`. **⇒ LÔ 2 = ĐÓNG HẲN họ `*DetailView` (vòng 10, chốt BA 2026-08-04)** — đặc tả [`03 §13`](./03_DETAIL_PAGE_SHELL.md): **21 màn CÒN LẠI** (`Asset` · `Calibration` · `CMWorkOrder` · `Commissioning` · `ComplianceRule` · `Document` · `Decommission` · `Incident` · `RCA` · `CycleCount` · `NeedsRequest` · `ProcurementPlan` · `PMWorkOrder` · `VendorEval` · `VendorProfile` · `Purchase` · `ServiceContract` · `TechSpec` · `Competency` · `Program` · `Session`). **Phép đo của lô 2 KHÔNG phải cột *Lỗi+Thử lại*** (bài học `ADR-UX-23` ở lớp danh sách) mà là **dấu vân tay IMPORT** `from '@/components/common/DetailPageShell.vue'`: adoption **11/32 → 32/32**, non-adopter **21 → 0**, khoá vĩnh viễn bằng guard `AC-UX-071`. Kèm `AC-UX-053` (SSoT lỗi `useDetailAccess` **3 → 21**, guard `AC-UX-072`) và `AC-UX-073` (chống 2 thanh tab, `ADR-UX-25`). **LÔ 2 ĐÃ LAND 2026-08-04 — đo lại TỪ ĐĨA:** adoption `DetailPageShell` = **32/32** (non-adopter **0**), `useDetailAccess` = **21**, màn 0-lối-nạp-lại = **0** ⇒ token trên dòng này là `[NO-DET=0]`; công thức của `uiDetailShellLot1Parity.guard.test.ts` đã được nới bằng số hạng lô 2 (`LOT2_NO_RECOVERY`, `ADR-UX-26`, [`03 §13.8`](./03_DETAIL_PAGE_SHELL.md)) và giữ nguyên vế đo-từ-đĩa. **AC-UX-048 + AC-UX-053: ĐÓNG HẲN** | P0 | 4–5 | §3 |
| **AC-UX-049** | `frontend/src/views/needs/ProcurementPlanDetailView.vue:168, 192, 219, 231, 241` | 5 chỗ gate hiển thị bằng **hardcode** `plan.workflow_state === 'Draft'` (vi phạm GATE-8 / LL-FE-51). **CẤM sửa ở vòng 4**: cần BE emit cờ `can_edit` trong `get_procurement_plan` trước — **hard-dependency**, sửa FE trước sẽ tạo dead-control | P1 | 5 | §3 |
| **AC-UX-050** | `frontend/src/views/compliance/InternalAuditDetailView.vue:24` | `const loading = ref(false)` ⇒ lượt render **trước** `onMounted` rơi vào nhánh `!audit` ⇒ **nháy 404 một nhịp** rồi mới ra khung xương (false-notfound flash). **ĐÓNG vòng 4** — `ref(true)` + test khoá nhịp render đầu (`InternalAuditDetailView.states.test.ts`) | P1 | 4 | §3 |
| **AC-UX-051** | `frontend/src/views/incident/CAPADetailView.vue:81-90` ⇄ `:180` | `catch` gom mọi lỗi vào **một chuỗi phẳng** (không phân loại 403/404/khác) và không reset lỗi đầu lượt; template in **dòng `text-red-500`** «Không tìm thấy…» ⇒ 403 thiếu quyền và 500 mất mạng đều bị **dán nhãn 404**, không nút quay lại, không nút nạp lại. **ĐÓNG vòng 4** — `loadErrorKind`/`toApiError` phân loại 3 ca + `DetailPageShell` (`capaDetailStates.guard.test.ts`) | P0 | 4 | §3 |
| **AC-UX-052** | **9** file / **12** nút-tab tự chế (đo lại 2026-08-04, quét `src/views` **+** `src/components`) — bản đồ per-file ở [`07 §1.3`](./07_DETAIL_TAB_BAR_SSOT.md) | Thanh tab tự chế bằng `activeTab === '…'` + `<nav>`/`<button>` riêng mỗi màn ⇒ lệch a11y (`role="tablist"`/`role="tab"`/`aria-selected`) và lệch cuộn ngang mobile so với `DetailTabBar.vue`. **Đính chính (BA Self-Correction 2026-08-04):** con số cũ «**27/32** màn chi tiết» **SAI về bản chất** — nó đếm *màn không import `DetailTabBar`*, trong khi **24/27 màn đó không có tab nào cả** (không có nợ để trả). Số màn chi tiết **thật sự có tab** = **8/32** (5 đã dùng SSoT — 4 import trực tiếp + `InternalAuditDetailView` gián tiếp qua `DetailPageShell`, ADR-UX-07). Bộ dò cũ (`grep -L`) và `grep role="tablist"` đều **dò ngược**: 8/9 bản fork **không có** `role` nào. Công thức đúng ở `07 §1.2`. **Lô 1 ĐÓNG vòng 8** — 3 file / 5 nút (`AssetDetailView` · `CommissioningDetailView` · `NeedsRequestDetailView`) ⇒ **12 → 7 nút, 9 → 6 file**; phần còn lại khoá bằng bản đồ CHỈ-GIẢM `detailTabBarAdoption.guard.test.ts` (AC-UX-069), lô 2 mở vòng sau. **Giao thoa với lô 2 của `AC-UX-048` (vòng 10):** 7 màn đang **import trực tiếp** `DetailTabBar` nay bọc trong `DetailPageShell` ⇒ quyết định **hoisting** (`AC-UX-073` / `ADR-UX-25`) — bản đồ nút-tab tự chế **không đổi** (7 nút / 6 file), nhưng danh sách «bắt buộc dùng SSoT» của guard di trú sang `MUST_USE_SSOT_VIA_SHELL` (8 mục) | P2 | 5 | §3 |
| **AC-UX-053** | `frontend/src/composables/useDetailAccess.ts` (3/32 màn dùng: `pm`, `cm`, `incident`) | Composable phân loại lỗi nạp đã có nhưng chưa lan; sau khi ≥8 màn áp `DetailPageShell` cần chốt: shell nhận thẳng object `access` hay giữ 3 prop rời (`errorKind`/`errorMessage`/`doc`). **⇒ CHỐT 2026-08-04 (`ADR-UX-27`, vòng 10):** **giữ 3 prop rời** — shell vẫn «dumb như tầng 0», không import composable (giữ luật tầng `03 §3.0`); **nguồn** của 3 prop bắt buộc là `useDetailAccess` ở phía view. Thi hành trong lô 2 (`03 §13`): lan **3 → 21** màn, phần lõi «`blocked === true` ⇒ **0** phần tử CTA» khoá bằng sub-case *(d)* của 21 file trạng thái; **11** màn legacy còn `loadErrorKind` cục bộ **đóng băng** trong sổ CHỈ-GIẢM của `AC-UX-072` | P2 | 5 | §3 |

| **AC-UX-054** | `frontend/src/components/common/BaseModal.vue` (**36** lần dùng ở **19** file) | Hộp thoại SSoT thiếu **toàn bộ** hợp đồng dialog: **0** `role="dialog"` / `aria-modal` / `aria-labelledby`, **0** đóng bằng `Escape`, **0** bẫy focus, **0** trả focus về nơi mở ⇒ người dùng bàn phím Tab **ra sau nền** và kích hoạt được nút đang bị nền che; trình đọc màn hình không biết đây là hộp thoại. **ĐÓNG vòng 5** — hợp đồng ở [`04 §3`](./04_PHUONG_AN_SUA_TOAN_BO.md), composable `useFocusTrap.ts` | P0 | 5 | §1.1 của `04` |
| **AC-UX-055** | **30** file `.vue` tự vẽ overlay `fixed inset-0` không qua `BaseModal` (danh sách: `04 §5.2`) | `role="dialog"` chỉ **2/30** · có `Escape` **6/30** · bẫy focus **0/30** ⇒ mỗi hộp thoại một hành vi bàn phím khác nhau. Vòng 5 **đóng băng ở 30** bằng guard CHỈ-GIẢM; di trú thực hiện theo lô ở đợt B–E | P1 | 5 | §1.2 của `04` |
| **AC-UX-056** | **4** file lai: `asset/AssetDetailView` · `asset/DepreciationView` · `calibration/CalibrationScheduleListView` · `master-data/ReferenceDataView` | Vừa import `BaseModal` **vừa** tự vẽ overlay ⇒ cùng một màn có 2 khuôn hộp thoại; đồng thời là **lỗ hổng** của guard AC-UX-055 (thêm 1 dòng `import BaseModal` là thoát guard). Khoá riêng, đóng băng ở **4** | P2 | 5 | §1.2 của `04` |
| **AC-UX-057** | `frontend/src/components/common/CommandPalette.vue:109-114`, `:132-145`, `:20/:63/:67-73/:152` | Logic Tab-wrap + return-focus **tự viết** — bản fork duy nhất trong repo; sửa lỗi bẫy focus phải sửa 2 nơi. **ĐÓNG vòng 5**: di trú sang `useFocusTrap`, giữ nguyên 7 TC | P2 | 5 | §4 của `04` |
| **AC-UX-058** | **42** call-site `confirm(...)` trần trong **28** file — đo lại 2026-08-04 (quét thô `grep -rn "[^.a-zA-Z_]confirm(" frontend/src/views frontend/src/components --include=*.vue` = 47/31, **trừ 5 dòng chú thích** ⇒ 42/28) ⇄ `composables/useNotify.ts` → `useModal.ts` | Hộp thoại **của trình duyệt**: không style được, nút OK/Cancel theo ngôn ngữ trình duyệt (vỡ LL-FE-53), không test render được, không tuân hợp đồng dialog. **Đính chính:** số cũ «44/31» đếm **thiếu strip-comment** và đã cũ; hạ tầng thay thế **KHÔNG chết** — `useNotify().confirm` đã có **7** call-site ở 5 view (ADR-UX-16). Lô 1 (7 file / 21 call-site) ĐÓNG vòng 7 — hợp đồng ở [`06_CONFIRM_DIALOG_SSOT.md`](./06_CONFIRM_DIALOG_SSOT.md) | P1 | 5 | §1.2 của `04` |
| **AC-UX-059** | `assetcore/services/imm16.py` ⇄ `AC Asset` (nghiệp vụ, **chưa code — chờ BA chốt**) | **Hợp đồng vòng đời link thiết bị mồ côi chưa chốt** ⇒ mọi bản vá là vá tạm. Hai câu hỏi chặn: (a) xoá `AC Asset` còn CAPA/hiệu chuẩn tham chiếu thì **CHẶN** hay cho xoá rồi hạ link về trạng thái «thiết bị đã xoá»; (b) hành động **chuyển trạng thái** có được bỏ qua validate các link KHÔNG liên quan không. **Ghi sổ ở vòng 6 (FE), KHÔNG code trong vòng này** — chặn AC-UX-060/061 | P0 | 6 | §STATE 🔴 #6 |
| **AC-UX-060** | `assetcore/services/imm16.py:2111` (`advance_capa_state`) · `assetcore/api/imm16.py:306` | **Ngõ cụt chuyển trạng thái CAPA**: 1 link hỏng KHÔNG liên quan (vd `ac_asset` trỏ thiết bị đã xoá) chặn transition hợp lệ ⇒ hồ sơ CAPA kẹt vĩnh viễn. Hướng: `doc.flags.ignore_links=True` (tiền lệ `services/imm16.py:632`) hoặc tách đường ghi chỉ-cập-nhật-trạng-thái. Prove-It RED→GREEN. **Ghi sổ, KHÔNG code trong vòng FE này** | P0 | 6 | §STATE 🔴 #6 |
| **AC-UX-061** | `AC Asset` (xoá) ⇄ `IMM CAPA Record` · `IMM Asset Calibration` | **Không có chặn/cascade khi xoá `AC Asset` còn ràng buộc** ⇒ dữ liệu mồ côi đã tích luỹ: **45** CAPA + **24** hiệu chuẩn trỏ tài sản không tồn tại (đo bằng SQL 2026-07-31; tổng `AC Asset` = 194). Cần invariant «sau khi xoá asset, không tồn tại CAPA/hiệu chuẩn trỏ asset không tồn tại» + patch dọn (chạy SAU khi user duyệt). **Ghi sổ, KHÔNG code trong vòng FE này** | P0 | 6 | §STATE 🔴 #6 + #8 |
| **AC-UX-062** | `frontend/src/components/common/BaseModal.vue` (SSoT, **19** file tiêu thụ) — nợ ở **15/19** file | **Lỗi CHẶN hành động chỉ đến bằng toast tự tắt sau 4000ms** (`composables/useToast.ts:33` → `:45`) trong khi hộp thoại vẫn mở ⇒ người dùng quay lại hộp thoại thì không còn dấu vết vì sao thao tác hỏng. 15/19 file tiêu thụ `BaseModal` có **0** `role="alert"` và **0** `data-testid="modal-error"`; 4 file còn lại chỉ có `role="alert"` **ngoài** hộp thoại. Hợp đồng + lô 1 (5 file / 8 hộp thoại) ở [`05_MODAL_INLINE_ERROR.md`](./05_MODAL_INLINE_ERROR.md) — ADR-UX-13/14 | P0 | 6 | §1 của `05` |
| **AC-UX-063** | `frontend/src/api/axios.ts:136-146` (`parseServerMessages`) ⇄ `:182` (`handle400`) · `:277` (`makeBusinessRuleError` fallback, ném ở `:310`) | **Chuỗi kỹ thuật thô của máy chủ đổ thẳng ra giao diện** khi 400/417/422 không có `message_code`: traceback Python, `cannot import name`, câu SQL, tên tệp `.py`, thẻ HTML của Frappe. Ví dụ tiêu thụ trực tiếp: `views/master-data/ReferenceDataView.vue:175` (`e.message` → render `:503`). Cần `sanitizeBusinessMessage` tại **một cửa** + log thô chỉ khi DEV — hợp đồng ở [`05 §7`](./05_MODAL_INLINE_ERROR.md), ADR-UX-15 | P1 | 6 | §1.2 của `05` |

| **AC-UX-064** | `frontend/src/components/common/NotificationModal.vue:39` (nghe `keydown` toàn cục) · `:48` (overlay tự vẽ `fixed inset-0 … z-[10000]`) ⇄ `BaseModal.vue` | **Hộp thoại chặn thao tác rẽ nhánh khỏi SSoT**: tự vẽ overlay ⇒ 0 bẫy focus, 0 trả focus, `aria-labelledby` không theo instance; **và** nghe `Escape` song song với `useFocusTrap` (2 listener, `document` rồi `window`) ⇒ **một lần nhấn ESC huỷ HAI xác nhận** trong hàng đợi (phần tử kế tiếp bị `resolve(false)` dù chưa từng hiển thị — `06 §4.2`). Sửa: render qua `BaseModal` + bỏ listener + prop `layer` cho tầng xếp chồng (ADR-UX-17) | P0 | 7 | §3/§4 của `06` |
| **AC-UX-065** | 7 file lô 1 / **21** call-site (`06 §5.2`) ⇄ `frontend/src/composables/useNotify.ts:31-40` (`ConfirmOpts` thiếu `tone`) | **Quy ước gọi chưa lan**: `notify.confirm` mới có 7 call-site trong khi 42 chỗ vẫn gọi `confirm()` trần; `ConfirmOpts` không diễn đạt được hành động **phá huỷ** (thiếu `tone`) nên không nối được `danger` của `BaseModal`. Di trú 7 file nặng nhất (**50%** nợ) theo bảng copy đóng băng + viết lại 4 test đang `vi.stubGlobal('confirm')` sang harness spy `notify.confirm` | P1 | 7 | §5/§7 của `06` |
| **AC-UX-066** | `frontend/src/guards/bareConfirmBudget.guard.test.ts` (MỚI) | **Không có guard cho nợ `confirm()`**: allowlist theo tên file (khuôn AC-UX-055) mù với hồi quy **bên trong** file đã có tên; và trần treo lơ lửng khiến doc trôi khỏi đĩa (số «44/31» sống sót qua 2 vòng). Ngân sách theo cặp **(file, số lần)**, CHỈ-GIẢM **hai chiều** — giảm mà quên hạ sổ cũng ĐỎ (ADR-UX-18) | P1 | 7 | §6 của `06` |

| **AC-UX-067** | `frontend/src/components/common/DetailTabBar.vue` (SSoT, **4** view import trực tiếp + 1 gián tiếp qua `DetailPageShell`) | **SSoT thanh tab không diễn đạt được số đếm trong nút tab** ⇒ màn cần badge (vd «Không phù hợp × 3» ở `/commissioning/:id`) buộc phải tự chế cả thanh tab chỉ vì một con số. Mở rộng **CHỈ-THÊM**: trường tuỳ chọn `DetailTab.badge` (kiểu `string` hoặc `number`), render **bên trong** `<button role="tab">`, **không** thêm tab-stop, rỗng/`0`/`'0'` ⇒ **không có phần tử** trong DOM. Hợp đồng cũ (role/aria/`type="button"`/`overflow-x-auto`/`shrink-0`/testid `tab-<key>`) giữ **100%**; `DetailTabBar.test.ts` 3 describe cũ **0 dòng đổi** — ADR-UX-19 | P1 | 8 | §3 của `07` |
| **AC-UX-068** | `views/asset/AssetDetailView.vue:698-712` · `views/commissioning/CommissioningDetailView.vue:437-467` · `views/needs/NeedsRequestDetailView.vue:415-429` | **Lô 1 di trú 3 thanh tab tự chế** về SSoT (5/12 nút). Ba hành vi **không được hồi quy**: (a) Asset giữ **nạp lười** — `onTabChange` đúng **1** lần/lần bấm, panel `data-testid="tab-panel-related"` giữ `v-if`; (b) Commissioning tab **theo route** — bấm vẫn `router.push`, `activeTab` vẫn là `computed` từ `route.name`, **cấm** state cục bộ; (c) Needs giữ **`v-show`** để không mất chữ đã gõ ở «Chấm điểm ưu tiên»/«Dự toán». Kèm viết lại `AssetDetailView.tabBarResponsive.test.ts` theo lối **dời lời hứa** (RWD chấm ở SSoT + mount thật), **không** xoá assert — ADR-UX-20 | P2 | 8 | §4/§5 của `07` |
| **AC-UX-069** | `frontend/src/guards/detailTabBarAdoption.guard.test.ts` (MỚI) | **Không có guard cho nợ thanh tab** — nên con số sai «27/32» sống qua **3** vòng và **3** bản fork trốn được vào `src/components/` (mọi bộ dò trước chỉ quét `src/views/`). Ngân sách theo cặp **(file, số nút-tab)** đo bằng dấu vân tay tích cực «thẻ `<button>` có ràng buộc `:class` đọc biến trạng thái tab (`activeTab ===` hoặc `tab ===`)», quét **2 cây**, CHỈ-GIẢM **hai chiều** (giảm mà quên hạ sổ cũng ĐỎ); + danh sách «bắt buộc dùng SSoT» và dấu vân tay fork cho ca phép đo mù (nút điều hướng bằng `router.push`) — ADR-UX-21. Gộp guard **parity nhãn MR 2 nguồn** (AC-UX-003) | P1 | 8 | §6/§7 của `07` |

| **AC-UX-070** | `frontend/src/guards/listShellAdoption.guard.test.ts` (MỚI) | **Không có phép đo nào nhìn thấy adoption khuôn danh sách** — cột *Lỗi+Thử lại* của bộ dò chấm theo **sự có mặt** của nút «Thử lại», nên **12** màn danh sách vừa in lỗi vừa in «Chưa có dữ liệu» vẫn được chấm ✅ và lô 2 tuyên bố nhầm «họ danh sách CUỐI CÙNG». Ngân sách theo cặp **(file `*ListView.vue`, adopter true/false)** quét `views/**` đệ quy, dấu vân tay `from '@/components/ui/ListPageShell.vue'`; **đóng băng non-adopter = 0** sau lô 3, CHỈ-GIẢM **hai chiều** (thêm `*ListView` mới không có khuôn ⇒ ĐỎ; áp khuôn mà quên hạ sổ ⇒ ĐỎ); + ép mỗi adopter có `*ListStates.test.ts` cạnh nó và ép bộ đếm công bố ở [`02 §14.1`](./02_LIST_PAGE_SHELL.md) khớp số đọc từ đĩa — `ADR-UX-23` | P1 | 9 | §6/§14 của `02` |

| **AC-UX-071** | `frontend/src/guards/detailShellAdoption.guard.test.ts` (MỚI) | **Không có phép đo nào nhìn thấy adoption khuôn CHI TIẾT** — đúng lỗ hổng mà `AC-UX-070` vừa bịt ở lớp danh sách. Cột *Lỗi+Thử lại* của bộ dò chấm theo **sự có mặt** của lối nạp lại nên không phân biệt được «có nút Thử lại» với «4 trạng thái LOẠI TRỪ nhau bằng cấu trúc»; hôm nay **5 màn** đang được chấm ✅ trong khi đĩa **0 hit** cho cả ba dấu `DetailLoadError` / `@retry` / `DetailPageShell` (`/assets/:id` · `/commissioning/:id` · `/documents/view/:name` · `/needs-requests/:id` · `/imm06/competencies/:name`). Ngân sách theo cặp **(file `*DetailView.vue`, adopter true/false)** quét `views/**` đệ quy, dấu vân tay IMPORT `from '@/components/common/DetailPageShell.vue'`, `TOTAL_DETAIL_VIEWS = 32`; CHỈ-GIẢM **hai chiều** (thêm `*DetailView` mới không có khuôn ⇒ ĐỎ; áp khuôn mà quên hạ sổ ⇒ ĐỎ) + parity 2 chiều với sổ lô 2 ở [`03 §13.2`](./03_DETAIL_PAGE_SHELL.md) + ép mỗi adopter có `*DetailStates.test.ts` cạnh nó. **Đóng băng non-adopter = 0** sau lô 2 | P1 | 10 | §6/§13 của `03` |

| **AC-UX-072** | `frontend/src/guards/detailAccessAdoption.guard.test.ts` (MỚI) | **Logic phân loại lỗi nạp bị chép tay ở từng màn**: `useDetailAccess.ts` (SSoT của CR-74 — 3 kind `unknown`/`forbidden`/`notfound`, hằng `ACCESS_DENIED_HINT`, luật «403 in-envelope KHÔNG logout») mới lan **3/32** màn, trong khi **11** màn đã áp `DetailPageShell` vẫn tự gọi `loadErrorKind` ⇒ 11 bản sao có thể trôi khỏi SSoT mà không ai đỏ. Guard ép: adopter ⇒ phải import `useDetailAccess`; ngoài sổ legacy ⇒ **0** hit `loadErrorKind(`; `LEGACY_LOCAL_KIND_BUDGET` đóng băng đúng **11** file (`AssetTransfer` · `Finding` · `InternalAudit` · `ManagementReview` · `FirmwareCr` · `CAPA` · `SparePart` · `StockMovement` · `Warehouse` · `Decision` · `Supplier`) — **CHỈ được xoá dòng, cấm thêm dòng** — `ADR-UX-27`. Đích đo được của vòng 10: `grep -l useDetailAccess` **3 → 21** (**không phải 24** — 3 màn đang dùng nằm TRONG 21 màn của lô, xem đính chính BA ở [`03 §13.1`](./03_DETAIL_PAGE_SHELL.md)) | P1 | 10 | §6/§13.7 của `03` |

| **AC-UX-073** | `frontend/src/components/common/DetailPageShell.vue` (prop `tabs`) ⇄ **7** màn tự gắn `DetailTabBar` (`Asset` · `Calibration` · `CMWorkOrder` · `Commissioning` · `Incident` · `NeedsRequest` · `PMWorkOrder`) | **Nguy cơ 2 thanh tab / 2 `role="tablist"` trong 1 màn** khi bọc 7 màn này vào `DetailPageShell`: shell đã có đường vẽ tab qua prop `tabs`, view lại còn thẻ `<DetailTabBar>` cục bộ ⇒ hoặc nhân đôi, hoặc mỗi màn chọn một kiểu. Quyết định **ADR-UX-25: HOISTING** — 7 màn truyền `:tabs` + `active-tab` cho shell và **xoá** `import DetailTabBar` (đúng hình dạng `InternalAuditDetailView` đã chạy từ `ADR-UX-07`); kiểu prop `tabs` nới thành `DetailTab[]` để `badge` (`AC-UX-067`) không bị hợp đồng che mất; `detailTabBarAdoption.guard.test.ts` di trú 7 đường dẫn sang `MUST_USE_SSOT_VIA_SHELL` (**8** mục, có assert độ dài) trong CÙNG lượt. Nghiệm thu: DOM render có **đúng 1** `[data-testid="detail-tabs"]` và **đúng 1** `[role="tablist"]` | P1 | 10 | §13.4.2/§13.11 của `03` |

**Tổng: 73 mục — AC-UX-001 … AC-UX-073, liên tục, không trùng.**

---

## §7. Xếp hạng nợ — đầu vào GHIM cho VÒNG 2

### 7.1 Top-5 nhóm nợ (số route đếm trực tiếp từ bảng §3.1, không ước lượng)

| Hạng | Nhóm nợ | Số route ❌ | % trên 135 route có view | Mã AC-UX | Vòng |
|---|---|---|---|---|---|
| 1 | **Thiếu nhãn a11y cho control** | **87** | 64% | AC-UX-001, 002, 006 | 2–3 |
| 2 | **Lỗi tải không có nút «Thử lại»** | **83** | 61% | AC-UX-005 | 2–3 |
| 3 | **Thiếu skeleton lúc chờ** | **75** | 56% | AC-UX-010 | 3 |
| 4 | **Hazard responsive ≤768px** | **31** | 23% | AC-UX-007, 008, 009 | 2–3 |
| 5 | **Empty-state cụt / không có** | **26** | 19% | AC-UX-011 | 3 |

Phân rã nhóm 4 (31 route) theo loại hazard — đếm từ cột *≤768px* của §3.1:

| Hazard | Số route | Route (rút gọn) |
|---|---|---|
| `<table>` ngoài khung cuộn ngang | 17 | `/commissioning`, `/documents/requests`, `/pm/work-orders`, `/pm/templates`, `/cm/work-orders`, `/cm/firmware`, `/compliance/mr/:id`, `/service-contracts/:id`, `/inventory/uom`, `/purchases`, `/procurement-plans`, `/procurement-plans/:id`, `/needs-requests/:id`, `/tech-specs/new`, `/tech-specs/:id`, `/vendor-evaluations/:id`, `/vendor-profiles/:id` |
| `grid-cols-12` từ mobile | 7 | xem cột *≤768px* = ❌ + evidence "grid-cols-12" |
| chiều rộng cứng ≥480px | 6 | mẫu: `/needs-requests/new` (`w-[1100px]`) |
| `grid-cols-7` (lịch) | 2 | `/pm/calendar` |
| `grid-cols-6` / `grid-cols-3` | 2 | `/cm/dashboard`, `/admin/roles` |
| thanh công cụ tràn ngang (chỉ thấy khi RENDER) | 1 | `/assets` @390px — xem §3.4 |

> Ghi chú: 1 route có thể dính >1 hazard nên tổng dòng > 31.
> Hazard cuối **không có bộ dò tĩnh** (regex không dựng được layout) ⇒ chỉ lộ ra khi render thật.

### 7.2 Nợ design-system

**Primitive ĐANG THIẾU** (đối chiếu 30 file trong `frontend/src/components/common/` — đã `ls` xác nhận không tồn tại):

| Primitive thiếu | Vì sao cần | Bằng chứng nợ hiện tại |
|---|---|---|
| **`EmptyState.vue`** | 1 khuôn duy nhất cho "rỗng": câu + lý do + CTA | 26 route ❌ + mỗi màn tự viết chữ («Không có dữ liệu» cụt ở `/dashboard` vs mẫu ĐÚNG ở `/compliance/heatmap`) |
| **`ListLoadError.vue`** (đối xứng `DetailLoadError.vue`) | Màn **danh sách** không có primitive lỗi+thử lại; `DetailLoadError` chỉ dùng cho *DetailView* (12 view) | 83 route ❌ ô «Lỗi+Thử lại» |
| **`DataTable.vue`** | Bọc sẵn `overflow-x-auto`, thẻ dọc ở ≤768px, cột rỗng tự ẩn | 15 route quên khung cuộn; `/assets` giữ 3 cột rỗng 100% |
| **`FormField.vue`** (label ↔ id ↔ error) | Bắt buộc `for=`/`aria-describedby` từ khuôn | 87 route ❌ a11y; `AssetListView` 5 `<label>` thiếu `for=` |
| **`IconButton.vue`** (bắt buộc `aria-label`) | Nút chỉ có icon đang phát sinh khắp nơi | nút phân trang không tên (AC-UX-002) |
| **`ClickableRow` / dùng `<RouterLink>` cho dòng** | Dòng bấm được phải là phần tử tương tác thật | AC-UX-001 |
| **`PageTitle` SSoT** (thanh trên + H1 lấy CÙNG 1 nguồn) | Đang có `AppTopBar` và `PageHeader` khai báo tiêu đề độc lập | AC-UX-013 (lặp và lệch chữ) |

**Token ĐANG THIẾU** (đối chiếu `frontend/tailwind.config.js` — chỉ có `brand.*`, `ink.*`, font, animation):

| Token thiếu | Hệ quả đo được |
|---|---|
| **Màu ngữ nghĩa** `success / warning / danger / info` | **1690** lần dùng thẳng `emerald-*/amber-*/rose-*/red-*/green-*` trong `views/` ⇒ badge & cảnh báo lệch tông giữa các module |
| **Token "không có giá trị"** (1 glyph duy nhất) | `/assets` dùng cả `—` và `–` cho cùng ý; nơi khác dùng chữ «Chưa có» |
| **Token breakpoint nghiệp vụ** (`table→card` ở đâu) | Mỗi màn tự quyết ⇒ `/assets` có thẻ dọc ở 390px còn 15 màn khác vỡ bảng |
| **Token trạng thái ↔ nhãn VI (SSoT)** | `STATUS_MAP` (`utils/formatters.ts:43`) không phủ hết enum BE ⇒ «Held», «Minutes Approved» lọt ra UI |
| **Token chiều rộng vùng thao tác** (toolbar) | Thanh công cụ `/assets` tràn ngang ở 390px; nút «Tải dữ liệu» vỡ 3 dòng ở 1440px |

> **Hiệu chỉnh phạm vi vòng 2 (BA, 2026-07-31 — Self-Correction, không xoá bảng trên).** Bộ primitive **thực thi ở vòng 2**
> là 7 primitive tầng 0 của **ADR-UX-04** (§9): `Button` · `Badge` · `Card` · `DataTable` · `EmptyState` · `ErrorState` · `Skeleton`.
> Đối chiếu với bảng «Primitive ĐANG THIẾU» ở trên:
> `EmptyState` ✅ vào vòng 2 · `DataTable` ✅ vòng 2 · **`ListLoadError` đổi hiện thân thành `ui/ErrorState.vue`** (khuôn chung
> lỗi + «Thử lại», dùng được cho cả danh sách lẫn khối con; `DetailLoadError.vue` giữ nguyên vì mang ngữ nghĩa CR-74) ·
> **`FormField`, `IconButton`, `ClickableRow`, `PageTitle` dời sang vòng 3** (ghi sổ **AC-UX-039**) ·
> `Button`/`Badge`/`Card`/`Skeleton` bổ sung vào vòng 2 vì 3 primitive kia **bọc lại chúng** (không dựng trước thì phải fork CSS).
> 4 token còn lại trong bảng dưới (glyph «không có», breakpoint bảng→thẻ, enum→VI, chiều rộng toolbar) **giữ nguyên ở vòng 3–5** —
> vòng 2 chỉ đóng **token màu ngữ nghĩa** (AC-UX-032) + `--color-info` (AC-UX-035).

> **Bổ sung vòng 3 (BA, 2026-07-31 — không xoá bảng trên).** `ErrorState` (vòng 2) mới là **khối** hiển thị lỗi;
> nó **không** trả lời được câu hỏi *“khi nào hiện khối nào”* — mà đó chính là chỗ sinh ra nợ `AC-UX-041` (*false-empty*).
> Vòng 3 thêm **primitive thứ 8 `ListPageShell.vue`** = **khuôn trạng thái** của màn danh sách (4 trạng thái loại trừ,
> ưu tiên `error > loading > empty > content`), COMPOSE lại `PageHeader` / `ListFilterBar` / `BasePagination` **qua slot**
> chứ không viết mới. Quyết định gốc: **ADR-UX-05** (§9). Spec thi hành: [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md).
> 3 primitive còn nợ của bảng trên (`FormField`, `IconButton`, `ClickableRow`, `PageTitle`) **vẫn ở AC-UX-039**.

---

## §8. Guard bất biến (A6)

`frontend/src/guards/uiAuditDocParity.guard.test.ts` — khoá 3 bất biến, chạy trong bộ FE bình thường:

| Bất biến | Nội dung |
|---|---|
| **INV-UIAUDIT-1** (A1) | Mọi chuỗi `path: '…'` trong `router/index.ts` xuất hiện **đúng 1 lần** ở bảng §3.1, và ngược lại (0 dòng thừa). |
| **INV-UIAUDIT-2** (A2) | Mỗi dòng có đủ **7 ô** ∈ `{✅, ❌, n/a}` (không ô rỗng), cột *view file* trỏ file **có thật trên đĩa** (trừ dòng redirect), cột *đau* ∈ `{P0,P1,P2}`. |
| **INV-UIAUDIT-3** (A5) | Sổ `AC-UX-*` đánh số **liên tục từ 001**, không trùng, mỗi mục có mức đau ∈ `{P0,P1,P2}` và vòng ∈ `{2,3,4,5}`. |

Khi FE thêm/xoá route mà quên cập nhật §3.1 ⇒ INV-UIAUDIT-1 đỏ ngay.

---

## §9. Quyết định kiến trúc

### ADR-UX-01: Rubric 7 tiêu chí có trạng thái `n/a`, chấm đau bằng trọng số
- **Status**: Accepted — 2026-07-31
- **Context**: 148 route rất khác nhau (redirect, màn tĩnh, biểu mẫu, danh sách). Chấm nhị phân ✅/❌ cho mọi ô sẽ dựng **nợ giả** (bắt màn 404 tĩnh phải có skeleton) và làm bảng mất giá trị ưu tiên.
- **Decision**: 3 giá trị `✅/❌/n/a` + quy ước áp dụng ở §1.3; mức đau tính bằng **trọng số cố định** (§1.4), không cảm tính.
- **Alternatives**: (a) nhị phân — loại vì nợ giả; (b) cho người chấm tay điểm 1–5 — loại vì không tái lập được giữa các vòng.
- **Consequences**: Ô `n/a` không được coi là "đạt" khi thống kê (mẫu số §2.1 luôn ghi rõ). Đổi quy ước `n/a` ⇒ phải sửa ADR này + chạy lại toàn bảng.

### ADR-UX-02: Sổ `AC-UX-*` tách khỏi `AC-CR-*`
- **Status**: Accepted — 2026-07-31
- **Context**: Sổ `AC-CR-*` đang là ledger **hợp đồng API/nghiệp vụ** (tới AC-CR-102) và đã va chạm số 3 lần trong run-4.
- **Decision**: Nợ lớp hiển thị đi sổ riêng `AC-UX-*` bắt đầu từ 001, khai báo trong tài liệu này.
- **Alternatives**: dùng chung `AC-CR-*` — loại vì trộn 2 loại nợ khác vòng đời (hợp đồng cần ratify BE↔FE↔mobile; nợ UI chỉ đụng lớp hiển thị).
- **Consequences**: Trước khi cấp số mới **phải** `grep -rn "AC-UX-" docs/`. Mục nào leo lên thành đổi hợp đồng BE (vd AC-UX-004 tiêu đề do BE sinh) thì **mở thêm** một `AC-CR-*` và liên kết chéo, không đổi mã cũ.

### ADR-UX-03: Hợp thành 1 cấp khi đo trạng thái tải
- **Status**: Accepted — 2026-07-31
- **Context**: 8 dashboard persona uỷ quyền loading/error/skeleton cho `PersonaDashboardShell.vue`; đo trên file cha sẽ báo ❌ sai. Ngược lại, cộng bừa từ mọi component con sẽ báo ✅ sai (`SmartSelect` có loading nội bộ của riêng nó).
- **Decision**: chỉ cộng từ component **được truyền `:loading` / `:error` / `@retry`** từ cha (xem §1.2).
- **Alternatives**: (a) chỉ đo file cha; (b) cộng từ mọi con — cả hai đều cho số sai đã kiểm chứng trong quá trình đo.
- **Consequences**: Nếu FE đổi cách truyền trạng thái (vd dùng provide/inject), bộ đo phải cập nhật cùng lúc, nếu không bảng sẽ trôi.

### ADR-UX-04: Tầng 0 design system — token ngữ nghĩa SSoT 2 chiều + 7 primitive bọc `@layer`
- **Status**: Accepted — 2026-07-31 (spec thi hành đầy đủ: [`01_DESIGN_SYSTEM.md`](./01_DESIGN_SYSTEM.md))
- **Context**: §7.2 đo được nợ gốc của lớp hiển thị **không nằm ở từng màn** mà ở chỗ thiếu tầng 0:
  `tailwind.config.js` chỉ có `brand.*`/`ink.*` (**0** token ngữ nghĩa) ⇒ **1690** lần hardcode `emerald/amber/rose/red/green-*`
  trong `views/` (**6119** nếu tính cả `slate/gray/blue/indigo/teal`), và `frontend/src/components/ui/` **không tồn tại**
  ⇒ mỗi màn tự chế khung rỗng/lỗi/bảng. Sửa 135 route khi chưa có tầng 0 = nhân bản nợ; đồng thời `main.css` có **2 nguồn màu**
  (`:root` CSS var ⇄ Tailwind) mà **không guard** nào ràng buộc.

- **Decision** — 4 điều, thi hành nguyên khối ở vòng 2:
  1. **Đặt tên token**: Tailwind `theme.extend.colors.<họ>.<bậc>` ⇄ CSS var `--ac-color-<họ>-<bậc>`, **ánh xạ 1-1 bắt buộc**.
     Họ = `success` · `warning` · `danger` · `info` · `neutral` (5). Bậc = `50` (nền nhạt) · `500` (nền tảng) · `700` (chữ đậm) — **đúng 3**.
     **Bậc 500 khoá cứng bằng biến đang chạy**: `success #059669`, `warning #d97706`, `danger #dc2626`, `neutral #64748b`;
     `info` mới = `#2563eb` (= `brand.600`, đúng họ blue mà `.alert-info` đang dùng) và `:root` bổ sung `--color-info` cùng giá trị
     ⇒ **0 đổi màu hiển thị**. Tiền tố `--ac-` để không đụng biến `--color-*` cũ đang được tham chiếu **6** chỗ trong `frontend/src`
     (**4** trong `main.css`, đo bằng `grep -rn "var(--color-" src`).
  2. **Hợp đồng API 7 primitive** (`components/ui/`, có `index.ts` barrel), khai đủ props/slots/emits/testid ở `01 §3`:
     `Button` (variant ×5, size, loading→`aria-busy`) · `Badge` (tone ×5 = 5 họ token, size ×3 sao đúng `StatusBadge`) ·
     `Card` (padding, interactive, title) · `DataTable` (columns/rows/loading/clickable/emptyLabel/caption, slot `cell-<key>`) ·
     `EmptyState` (title/hint/actionLabel) · `ErrorState` (message/hint/retryable/retryLabel) · `Skeleton` (0 prop, class fallthrough).
     `data-testid` chuẩn hoá tiền tố `ui-*`. Primitive là **dumb**: 0 API, 0 store, 0 router.
  3. **Luật no-fork**: primitive **bọc** class `@layer components` sẵn có (`.btn-*`, `.card*`, `.table-wrapper/.table-header/.table-cell`,
     `.skeleton`), **cấm** chép lại chuỗi utility của class đó. `Badge` là ngoại lệ duy nhất (chưa có class `@layer`) và phải dùng
     token ngữ nghĩa (`bg-<họ>-50 text-<họ>-700`). Hệ quả: `ui/*.vue` **0 hit** class palette thô — khoá bằng guard vệ sinh.
  4. **Guard 2 chiều là điều kiện tồn tại của token**: `src/guards/designTokens.guard.test.ts` chặn cả token mồ côi lẫn var mồ côi;
     `ui/uiPrimitiveHygiene.guard.test.ts` chặn palette thô / thiếu test co-located / chuỗi EN.
     Chống shelf-ware: `common/SkeletonLoader.vue` **phải** render qua `ui/Skeleton.vue` với bất biến **đếm phần tử không đổi**
     (`table` rows=5 ⇒ đúng **30** `.skeleton`; `kpi-cards` 16 · `form` 15 · `card` 7 · `list` 20) và **0 dòng** trong 49 view đang dùng nó bị sửa.

- **Alternatives**:
  (a) *Chép thang màu Tailwind đầy đủ (50…950) cho 5 họ* — loại: 55 token cho 3 nhu cầu thật, và bậc 500 sẽ **không** trùng biến cũ
      (`emerald-500 #10b981 ≠ --color-success #059669`) ⇒ đổi màu hiển thị, vi phạm bất biến vòng 2.
  (b) *Chỉ dùng CSS var, bỏ token Tailwind* — loại: view viết bằng utility class, không có `bg-success-50` thì hardcode vẫn tiếp diễn.
  (c) *Chỉ dùng Tailwind, bỏ CSS var* — loại: `main.css` (`.kpi-card::before`, `.btn`, `html`) đang đọc `var(--color-*)` ở runtime.
  (d) *Lấy thư viện UI ngoài (PrimeVue/shadcn)* — loại: vi phạm Never của §0 và ném bỏ toàn bộ `@layer components` đang chạy.
  (e) *Áp primitive vào 10 route P0 ngay vòng 2* — loại: trộn 2 rủi ro (dựng khuôn + đổi 10 màn) trong 1 vòng, và vi phạm A10
      (`views/**` phải sạch) ⇒ dời vòng 3, ghi sổ **AC-UX-038**.

- **Consequences**:
  - Thêm/bớt **bất kỳ** token nào phải sửa **2 file cùng lượt** (`tailwind.config.js` + `main.css`), nếu không guard parity đỏ ngay.
  - Thêm primitive thứ 8 ⇒ phải kèm `<Name>.test.ts` + dòng export trong `index.ts`, nếu không INV-UI-2 đỏ.
  - **Bẫy deep-merge**: khai 3 bậc cho `neutral` **không** thay bảng `neutral` mặc định của Tailwind ⇒ `neutral-100…900` (xám ấm)
    vẫn dùng được và lệch tông. Vòng 2 chặn trong `ui/` bằng INV-UI-4; toàn FE chờ **AC-UX-040** (vòng 3).
  - `class` động phải là **map tĩnh** (`Record<Tone,string>`) — Tailwind JIT purge chuỗi ghép `` `bg-${tone}-50` ``.
  - Di trú `@layer components` từ `slate/emerald/red…` sang `var(--ac-color-*)` **KHÔNG** thuộc vòng 2 (giữ bất biến 0-đổi-màu) — vòng 3+.
  - Số hardcode trong `views/` (1690/6119) **không giảm** ở vòng 2; chỉ giảm khi adoption chạy (vòng 3–5).

### ADR-UX-05: `ListPageShell` là primitive #8 — 4 trạng thái LOẠI TRỪ, ưu tiên `error > loading > empty > content`
- **Status**: Accepted — 2026-07-31 (bổ sung, **không** thay thế ADR-UX-04; spec thi hành: [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md))
- **Context**: ADR-UX-04 chốt “đúng 7 primitive, thêm primitive thứ 8 phải hỏi BA”. PM đã hỏi ở vòng 3. Lý do phải thêm:
  bộ dò đếm **94/148** route thiếu lối «Thử lại», nhưng đọc mã 4 màn danh sách cho thấy nợ **không phải** “thiếu một khối lỗi”
  mà là **thiếu máy trạng thái**: `PurchaseListView.vue:157` rơi thẳng vào `v-else-if="!rows.length"` ⇒ HTTP 500 hiện ra là
  «Chưa có đơn hàng nào»; `UserProfileListView.vue:92-107` không có `catch` nên cờ `loading` kẹt `true`;
  `VendorProfileListView.vue` hiện **đồng thời** banner lỗi và khung rỗng; `ProcurementPlanListView.vue:201` có nút trông như
  thử lại nhưng chỉ `store.clearError()`. Bốn màn, bốn kiểu hỏng khác nhau, **cùng một nguyên nhân**.
- **Decision** — 4 điều:
  1. **Thêm `components/ui/ListPageShell.vue` làm primitive #8** (barrel 8 export, guard vệ sinh 8 == 8 == 8; `ListPageShell`
     đứng giữa `ErrorState` và `Skeleton` theo thứ tự alphabet mà guard đang so).
  2. **Bốn trạng thái loại trừ bằng CẤU TRÚC** (`v-if / v-else-if / v-else` một chuỗi), ưu tiên **`error > loading > empty > content`**,
     phơi ra `data-state` để test chấm được. Hệ quả bắt buộc: mọi hàm nạp **xoá lỗi ở đầu lượt** và **hạ `loading` trong `finally`**.
  3. **COMPOSE, không viết lại**: `PageHeader` / `ListFilterBar` / `BasePagination` vào slot `#header` / `#filters` / `#pagination`.
     Slot `#filters` render ở **cả 4** trạng thái — người dùng phải sửa được chính bộ lọc gây lỗi.
  4. **Áp thật cho 4 màn ngay trong vòng dựng** (không để shelf-ware như vòng 2), nhưng **chỉ 4** — adoption diện rộng là `AC-UX-047`.
- **Alternatives**:
  (a) *Nhét máy trạng thái vào `DataTable`* — loại: `DataTable` chỉ bọc phần bảng; header/filter/KPI nằm ngoài nó, và 4 màn đích
      chưa dùng `DataTable` (đổi cả markup bảng = trộn 2 rủi ro trong 1 vòng). Ngoài ra `DataTable` đã có slot `error` riêng ⇒ lồng vào
      shell sẽ ra **2** nút «Thử lại».
  (b) *Viết composable `useListLoad()` thay vì component* — loại (tạm): giải được phần state nhưng **không** ép được thứ tự render,
      nên vẫn cho phép màn tự chế nhánh rỗng cạnh nhánh lỗi. Cân nhắc lại ở vòng 4 như **lớp bổ sung**, không thay thế.
  (c) *Vá lẻ 4 màn, không dựng khuôn* — loại: đúng cái sai vòng 1 đã chỉ ra (nợ nhân bản theo số route; 90 route còn lại sẽ lặp lại).
  (d) *Giữ nguyên 7 primitive, dùng `ErrorState` trực tiếp trong view* — loại: `ErrorState` không quyết định thứ tự ưu tiên ⇒
      `/vendor-profiles` (đã có `ErrorState`-tương-đương dạng banner) vẫn hiện **lỗi + rỗng cùng lúc**.
- **Consequences**:
  - `ListPageShell.vue` chịu **toàn bộ** guard vệ sinh tầng 0 (`INV-UI-1/2/3/4`): 0 palette thô, có test co-located,
    **0 text node** (allowlist chữ cứng hiện chỉ có `'Thử lại'`) ⇒ mọi chữ hiển thị do **caller** truyền.
  - Prop phải **khai đủ** (`emptyTitle`/`emptyHint`/`errorMessage`/`isEmpty`): prop không khai rơi vào `$attrs` và **in ra DOM ở cả 4 trạng thái**
    ⇒ chuỗi rỗng vẫn “có mặt” lúc lỗi, phá đúng bất biến vừa dựng.
  - Chữ rỗng phải là **literal tĩnh trong template của view** (không `computed`) — nếu không, cột *Rỗng+HD* đang ✅ của
    `/purchases`, `/user-profiles`, `/procurement-plans` **lật thành ❌** (bộ dò tìm cụm rỗng trong template, cửa sổ ±12 dòng).
  - Shell **dumb tuyệt đối**: cấm import `vue-router` / `@/stores` / `@/api` / `@/components/common` — `ProcurementPlanListView.create.test.ts`
    mock `vue-router` chỉ với `useRouter`, và `common/SkeletonLoader` đã phụ thuộc ngược vào `ui/Skeleton`.
  - Ưu tiên `error > loading` đánh đổi: nếu view **quên** xoá lỗi đầu lượt thì nút «Thử lại» trông như chết ⇒ phải có test
    “bấm thử lại → lượt 2 thành công → `data-state='content'`” cho **từng** màn.

### ADR-UX-06: `DetailPageShell` là **tier-1** (`components/common/`), KHÔNG phải primitive #9 — 4 trạng thái `error > loading > notfound > content`
- **Status**: Accepted — 2026-07-31 (bổ sung, **không** thay thế ADR-UX-04/05; spec thi hành: [`03_DETAIL_PAGE_SHELL.md`](./03_DETAIL_PAGE_SHELL.md))
- **Context**: Vòng 3 đóng *false-empty* cho lớp **danh sách**. Lớp **chi tiết** có nợ song song và nặng hơn: đo trên đĩa hôm nay,
  **21/32** màn `*DetailView.vue` không có bất kỳ lối nạp lại nào, **14** màn còn dòng chữ đỏ `text-red-500` cụt, và nợ *“view render
  khung chi tiết RỖNG nhưng panel thao tác vẫn hiện”* đã được ghi ngay trong chú thích `DetailLoadError.vue:6-8` từ CR-74 mà chỉ vá
  được 11/32 màn. Ba màn đích của vòng 4 tự viết lại **ba bản sao** của cùng một chuỗi `loading → !record → content`, và **ba bản sai
  khác nhau**: CAPA gom mọi lỗi thành 404 (`AC-UX-051`), kiểm toán nháy 404 một nhịp vì `loading = ref(false)` (`AC-UX-050`),
  soát xét đúng nhưng bố trí CTA theo kiểu riêng.
- **Decision** — 4 điều:
  1. **Khuôn nằm ở tier-1** `frontend/src/components/common/DetailPageShell.vue`, **không** thêm vào `components/ui/`.
     Ba lý do cứng: (i) nó **compose** hai component tier-1 đang là SSoT (`DetailLoadError`, `DetailTabBar`) mà primitive tầng 0 bị
     cấm import ngược; (ii) guard `uiPrimitiveHygiene.guard.test.ts` khoá 3 vế *(số export == số `.vue` == số test)* ở **8** — file thứ 9
     làm đỏ ngay; (iii) hợp đồng của nó **mang chữ tiếng Việt do caller truyền** (`entityLabel`, `backLabel`), khác luật primitive
     “copy khai trong `withDefaults`”.
  2. **Bốn trạng thái loại trừ bằng CẤU TRÚC**, ưu tiên **`error > loading > notfound > content`**, phơi `data-state`.
     `notfound` là trạng thái **riêng** (không phải “content rỗng”) vì render khung chi tiết toàn `—` chính là lỗi đang phải sửa.
  3. **Lỗi thắng cả `loading` lẫn dữ liệu cũ.** Ở màn chi tiết, giữ bản ghi cũ dưới banner lỗi nguy hiểm hơn màn danh sách:
     người dùng **thao tác trên dữ liệu cũ**. Hệ quả bắt buộc: mọi `load()` xoá lỗi đầu lượt, `doc = null` khi hỏng,
     `loading` khởi tạo **`true`**.
  4. **Áp thật cho 3 màn ngay trong vòng dựng** (`CAPADetailView`, `InternalAuditDetailView`, `ManagementReviewDetailView`);
     adoption diện rộng là `AC-UX-048`, vòng 5.
- **Alternatives**:
  (a) *Thêm `ui/DetailPageShell.vue` làm primitive #9* — loại: vỡ guard tầng 0 và tạo phụ thuộc ngược tầng 0 → tier-1 (xem Decision 1).
  (b) *Chỉ lan `useDetailAccess` cho 21 màn còn lại* — loại (tạm): composable giải phần **phân loại lỗi** nhưng **không ép được thứ tự
      render** ⇒ vẫn cho phép panel thao tác hiện cạnh khung rỗng, đúng nợ đang trả. Giữ làm **lớp bổ sung** (`AC-UX-053`).
  (c) *Mở rộng `ListPageShell` thành khuôn dùng chung cho cả danh sách và chi tiết* — loại: hai máy trạng thái **khác nhau về bản chất**
      (`empty` = 0 bản ghi, đúng nghiệp vụ; `notfound` = sai mã, luôn là lỗi). Gộp ⇒ prop bùng nổ và mất chính bất biến vừa dựng ở vòng 3.
  (d) *Vá lẻ 3 màn không dựng khuôn* — loại: đúng cái sai vòng 1 đã chỉ ra; 29 màn còn lại sẽ chép tiếp bản sao thứ 4, 5, 6.
- **Consequences**:
  - `DetailPageShell` **không** chịu guard vệ sinh tầng 0 (`INV-UI-*` chỉ quét `components/ui/`) ⇒ phải tự khoá bằng
    `detailPageShell.guard.test.ts` + 3 lệnh `grep -c` trong `03 §6.3` (no-fork: `DetailLoadError` ≥1, `DetailTabBar` ≥1, nhãn nút nạp lại **= 0**).
  - Đưa nội dung view vào **slot** làm mất type-narrowing của `v-else` ⇒ mọi slot deref bản ghi phải bọc `v-if="<record>"`,
    và `npm run typecheck` trở thành điều kiện đóng vòng (`03 §7.2`).
  - Hai nhánh `error` và `notfound` cùng render `DetailLoadError` với `kind` khác nhau ⇒ hợp đồng chấm là
    **đúng 1** phần tử `[data-testid="detail-load-error"]`, phân biệt bằng `[data-kind]` (không đếm 2 khối riêng).

### ADR-UX-07: Panel thao tác là vùng `#actions` của shell, chỉ render ở `content`; thanh tab là vùng **prop-driven**, không phải slot
- **Status**: Accepted — 2026-07-31 (chi tiết hoá ADR-UX-06)
- **Context**: Nợ gốc ghi trong `DetailLoadError.vue:7` là *“view render khung chi tiết RỖNG, panel thao tác vẫn hiện”*. Hiện mỗi màn đặt
  CTA một chỗ khác nhau: CAPA có thẻ `card` riêng, kiểm toán và soát xét nhét vào `#actions` của `PageHeader`. Song song đó, **27/32**
  màn chi tiết tự chế thanh tab (`AC-UX-052`) dù `DetailTabBar.vue` đã là SSoT có a11y + cuộn ngang mobile.
  > **Đính chính 2026-08-04 (giữ nguyên văn ADR, sửa số ở đây):** «27/32» **SAI về bản chất** — đó là số màn *không import*
  > `DetailTabBar`, mà **24** trong đó **không có tab nào**. Số đúng: **8/32** màn chi tiết có tab, **5** đã dùng SSoT, **3** còn
  > tự chế; tính cả `src/components/` thì nợ toàn FE = **9 file / 12 nút-tab**. Xem [`07 §1.1`](./07_DETAIL_TAB_BAR_SSOT.md).
  > **Quyết định của ADR-UX-07 không đổi** — chỉ tiền đề định lượng được sửa.
- **Decision**:
  1. **Một vùng thao tác duy nhất** — slot `#actions` của shell, render **bên trong** nhánh `content` ⇒ tắt panel ngoài trạng thái
     có-dữ-liệu **bằng cấu trúc**, không nhờ prop hay quy ước. `#kpi` cùng luật (số 0 tính trên bản ghi không tồn tại là tín hiệu giả).
  2. Ba màn đích **dời** CTA từ `PageHeader #actions` sang `#actions` của shell; `PageHeader` giữ tiêu đề/breadcrumb trong `#header`.
  3. **Thanh tab KHÔNG phải slot**: shell nhận `tabs` + `activeTab` (prop) và tự render `DetailTabBar`. Slot cho phép mỗi màn tự chế lại
     tab bar — đúng nợ đang trả; vùng prop-driven **ép** dùng SSoT và làm phép đo `grep -c DetailTabBar` có nghĩa.
- **Alternatives**:
  (a) *Giữ CTA trong `PageHeader #actions`* — loại: `PageHeader` là component **hiển thị tiêu đề**, không biết trạng thái nạp; muốn tắt
      panel khi lỗi thì phải truyền cờ trạng thái xuống nó ⇒ rò máy trạng thái ra một component thứ hai.
  (b) *Slot `#tabs` tự do* — loại: xem Decision 3. (Nếu sau này có màn cần tab bar đặc thù ⇒ mở ADR mới, không lén thêm slot.)
  (c) *Cho phép cả hai (slot **và** prop)* — loại: hai đường làm cùng một việc ⇒ trôi dạt, và test đếm `data-testid` sẽ thấy **2** nút
      trùng tên khi ai đó điền cả hai (`03 §7.6`).
- **Consequences**:
  - Vị trí CTA của 2 màn (kiểm toán, soát xét) **đổi**: từ góc phải header xuống dải `card p-4` ngay dưới header — cùng khuôn với màn
    CAPA hiện có, và dễ thao tác hơn ở màn hẹp. Nếu USER phản đối, đảo lại **chỉ ở lớp view**, hợp đồng shell không đổi.
  - 5 file test cũ **không** stub `DetailPageShell` ⇒ chúng trở thành test tích hợp cho khuôn mới: CTA lọt ra ngoài `content` là đỏ ngay.
  - `activeTab` phải nới thành `ref<string>` (emit trả `string`), nếu không `v-model:active-tab` đỏ typecheck (`03 §7.4`).

---

### ADR-UX-08: `BaseModal` giữ nguyên vị trí **tier-1** (`components/common/`) — hợp đồng hộp thoại cài tại SSoT, 0 dòng sửa ở nơi tiêu thụ
- **Status**: Accepted — 2026-07-31 (spec thi hành: [`04_PHUONG_AN_SUA_TOAN_BO.md`](./04_PHUONG_AN_SUA_TOAN_BO.md) §3)
- **Context**: `BaseModal.vue` được dùng **36** lần ở **19** file và thiếu **toàn bộ** hợp đồng dialog (AC-UX-054). Hai đường đi khả dĩ: (a) nâng nó thành primitive #9 trong `components/ui/`; (b) sửa tại chỗ. Đường (a) đổi đường dẫn import ⇒ **19 file phải sửa** — mâu thuẫn trực tiếp với bất biến 0-churn của vòng và với chính lý do tồn tại của SSoT.
- **Decision**: giữ `components/common/BaseModal.vue` (tier-1, cùng tầng `DetailPageShell` theo ADR-UX-06). Toàn bộ `role="dialog"` · `aria-modal` · `aria-labelledby` ⇄ `<h2 id>` · `Escape` · bẫy focus · trả focus cài **tại SSoT**. `id` tiêu đề sinh bằng **bộ đếm module** (`nextDialogId()`), **không** dùng `useId()` của Vue 3.5.
- **Alternatives**: (a) primitive #9 — loại vì 19 file churn; (b) `useId()` — loại vì bộ đếm của nó theo **app instance**: 2 lần `mount()` trong cùng file test là 2 app ⇒ cùng cho `v-0` ⇒ bất biến "2 hộp thoại đồng thời id khác nhau" đỏ oan; (c) để mỗi màn tự thêm ARIA — loại vì đó chính là nợ đang đo (30 file tự vẽ, 2/30 có `role=dialog`).
- **Consequences**: `EXPECTED_PRIMITIVES` giữ **8**, `ui/uiPrimitiveHygiene.guard.test.ts` **không đổi**. Auto-focus khi mở làm `document.activeElement` đổi trong mọi test cũ có mount view chứa modal ⇒ phải chạy **toàn** suite trước khi khai xong. Đổi bất kỳ prop/slot/emit/`data-testid`/chuỗi class nào của `BaseModal` từ nay là **breaking change** cho 19 file.

### ADR-UX-09: `useFocusTrap` là nguồn DUY NHẤT của Tab-wrap + return-focus; phím do component gọi, không listener toàn cục
- **Status**: Accepted — 2026-07-31 (spec thi hành: `04` §2)
- **Context**: Bẫy focus hiện tồn tại **đúng 1 bản** — tự viết trong `CommandPalette.vue:109-145`. Thêm bản thứ hai cho `BaseModal` = fork ngay từ ngày đầu. Nhưng CommandPalette đã có bộ điều phối phím riêng (Arrow/Home/End/Enter/Escape) trong một `switch`, nên một composable "nuốt" toàn bộ `keydown` sẽ giành mất phím của nó.
- **Decision** — 4 điều: (1) `composables/useFocusTrap.ts` là nơi **duy nhất** chứa selector tabbable + logic wrap + return-focus (guard nguồn khoá: chuỗi `[tabindex]:not([tabindex="-1"])` chỉ được xuất hiện ở file này); (2) điều phối phím Tab bằng **`handleTabKey(e)` do component gọi** từ `@keydown` của chính nó — **không** đăng ký listener `keydown` toàn cục cho Tab; (3) `Escape` có **đúng 1 chủ sở hữu** mỗi hộp thoại (`BaseModal` uỷ cho composable qua `onEscape`; `CommandPalette` giữ nhánh `case 'Escape'` sẵn có và **không** truyền `onEscape`); (4) **ngăn xếp topmost** ở module-scope: chỉ hộp thoại trên cùng nhận `Escape`/Tab.
- **Alternatives**: (a) thư viện ngoài (`focus-trap`, `@vueuse`) — loại: §0 cấm thêm dependency UI, và bản tự viết chỉ ~60 dòng; (b) composable tự đăng ký `keydown` toàn cục cho mọi phím — loại vì cướp phím của CommandPalette và làm thứ tự xử lý phụ thuộc thứ tự mount; (c) directive `v-focus-trap` — loại: khó truyền `onEscape`/`initialFocus` và khó test đơn vị.
- **Consequences**: Lọc "đang hiển thị" **không được** dùng `offsetParent` (jsdom không có layout ⇒ luôn `null` ⇒ danh sách rỗng ⇒ test đỏ mà mã "trông đúng"); dùng `hidden`/`aria-hidden`/`getComputedStyle`. Hệ quả phụ: ở trình duyệt thật tập tabbable của CommandPalette **rộng hơn** trước — đổi có chủ đích, đã ghi ở `04 §4`. `tabindex` **dương** không hỗ trợ (repo hiện 0 hit). `deactivate()` phải **idempotent** vì bị gọi từ cả `onBeforeUnmount` lẫn `watch`.

### ADR-UX-10: Bộ dò `ui-audit-inventory.mjs` là SSoT cho DELTA — bảng tay §3.1 đóng băng làm ảnh chụp vòng 1
- **Status**: Accepted — 2026-07-31 (đóng **AC-UX-031**)
- **Context**: Từ vòng 3 tồn tại **2 nguồn số**: bảng chấm tay §3.1 (mẫu số 135) và bộ dò (mẫu số 148), lệch **32/1036 ô** do 3 quy ước chưa chốt. Quy ước tạm "vòng 3–4 chấm bằng bộ dò" chưa bao giờ được nâng thành quyết định ⇒ mỗi vòng lại tranh luận lại, và capstone (`04`) thì cần **một** thước đo cho DoD của cả 5 nhóm.
- **Decision**: bộ dò là **thước đo chính thức** cho mọi DELTA từ vòng 5 trở đi (`--summary` để so nhanh, `--json` để chấm theo nhóm). Bảng tay §3.1 **đóng băng** làm ảnh chụp vòng 1: chỉ cập nhật khi **thêm/xoá route** (để `uiAuditDocParity` xanh), **không** cập nhật các ô ✅/❌ theo tiến độ sửa. 3 điểm lệch quy ước được ghi nhận là **sai lệch đã biết của thước đo**, không phải nợ phải đóng.
- **Alternatives**: (a) chấm tay lại toàn bộ 135 route mỗi vòng — loại: không tái lập được, tốn 1 vòng chỉ để đếm; (b) sửa bộ dò cho khớp bảng tay — loại: bảng tay mới là thứ chủ quan; (c) giữ song song 2 nguồn — loại: đúng nguyên nhân của AC-UX-031.
- **Consequences**: DoD của mọi đợt trong `04 §10` phát biểu bằng **số của bộ dò**. Đổi heuristic của bộ dò = đổi thước ⇒ phải chạy lại baseline TRƯỚC/SAU trong cùng một lượt và ghi vào tài liệu, nếu không mọi DELTA lịch sử mất nghĩa. Bảng tay từ nay **không** phản ánh hiện trạng — ai đọc §3.1 phải đọc kèm cảnh báo này.

### ADR-UX-11: §3.1 là bảng SỐNG theo LÔ adoption — doc⇄đĩa khoá bằng guard parity 2 chiều
- **Status**: Accepted — 2026-08-03 · **làm rõ & thu hẹp phạm vi `ADR-UX-10`** (không thay thế: bộ dò VẪN là SSoT cho mọi con số DELTA) · **supersede** gạch đầu dòng «KHÔNG đụng bảng §3.1» ở `02 §0 Never`
- **Context**: `ADR-UX-10` đóng băng cả ô ✅/❌ của §3.1 để chặn việc chấm-tay-lại mỗi vòng. Hệ quả không lường trước đã xảy ra: vòng 3 áp `ListPageShell` cho 4 màn thật, bộ dò ghi ✅, **§3.1 vẫn ❌** ⇒ tài liệu ĐO nói sai về đĩa ở 4 dòng, và không tồn tại **sổ per-route** cho biết lô nào đã đóng. Với `AC-UX-047` (89 route, chia ≥ 8 lô) mà không có sổ per-route thì mỗi lô sau phải đo lại từ đầu để biết mình đang ở đâu — đúng thất bại «đo lại 3 lần» của run-5.
- **Decision**: ô ✅/❌ của **§3.1 được lật**, nhưng **chỉ** theo cơ chế máy móc: (1) mỗi lô adoption khai một **sổ lô** trong Core Doc khuôn tương ứng (lô 1 = `02 §12.2`); (2) lật **đúng** các route trong sổ, cột tương ứng khuôn đã áp; (3) một **guard parity 2 chiều** ép `view import khuôn` ⟺ `ô = ✅`, và ép token nợ còn lại `[NO-CON=N]` ở §6 khớp số ô đã lật. **Cấm** chấm tay lại bất kỳ ô nào ngoài sổ lô. Bảng tổng hợp **§2.1 giữ nguyên đóng băng**; mọi con số DELTA vẫn đọc từ **bộ dò**.
- **Alternatives**: (a) giữ nguyên đóng băng hoàn toàn — loại: tài liệu ĐO nói dối về đĩa, và nợ per-route không truy được; (b) sinh lại §3.1 từ bộ dò mỗi vòng — loại: mất cột «Đau» chấm tay + mất lịch sử, và `uiFixPlanParity` đang khoá §3.1 ⇄ `04 §11` theo cột view file; (c) mở thêm bảng tiến độ thứ 3 — loại: 3 nguồn số, đúng nguyên nhân `AC-UX-031`.
- **Consequences**: Lô adoption nào cũng phải land **mã + doc trong CÙNG một lượt** — quên doc thì guard đỏ, không có cửa "sửa doc sau". 4 dòng vòng 3 (`/purchases`, `/user-profiles`, `/procurement-plans`, `/vendor-profiles`) hiện **stale ❌**: xếp vào **lô 2** kèm mở rộng guard, **không** sửa ở lô 1 để phép đếm `−12` của lô 1 còn kiểm chứng được. §3.1 từ nay phản ánh hiện trạng **cho các route đã qua lô**; các route chưa qua lô vẫn là ảnh chụp vòng 1 — cảnh báo này phải đứng ngay dưới tiêu đề §3.1.

### ADR-UX-12: Sổ lô mang cột «Trạng thái» per-route — parity 2 chiều bám SỔ, không bám ô §3.1
- **Status**: Accepted — 2026-08-03 · **mở rộng `ADR-UX-11`** sang lớp CHI TIẾT (không thay thế: §3.1 vẫn là bảng SỐNG theo lô, bộ dò vẫn là SSoT cho DELTA)
- **Context**: `ADR-UX-11` ép `view import khuôn` ⟺ `ô §3.1 = ✅` **hai chiều**, và điều đó chạy tốt cho lô 1 lớp danh sách vì cả 12 ô đều đang ❌ đúng. Lô 1 lớp CHI TIẾT vấp một dữ kiện mới: dòng **134** `/procurement-decisions/:id` của §3.1 đang chấm ô *Lỗi+Thử lại* = **✅**, nhưng đo lại từ đĩa 2026-08-03 thì `DecisionDetailView.vue` có **0** hit `DetailLoadError` / `@retry` / «Thử lại» ⇒ đó là **sai số của bảng tay vòng 1** (bảng tay đếm 83 route nợ, bộ dò đếm 94 — chênh lệch đã biết, `ADR-UX-10`). Nếu ép 2 chiều lên §3.1, guard sẽ **ĐỎ ngay từ bước BA** vì một lỗi chấm tay có từ trước, và cách "chữa" duy nhất là chấm-tay-lại ô đó — đúng hành vi mà `ADR-UX-10` cấm.
- **Decision**: mỗi sổ lô mang thêm **cột «Trạng thái»** (`CHƯA` / `ĐÃ ĐÓNG`) — đây là **SSoT tiến độ per-route**. Guard ép **2 chiều giữa mã và cột này** (`import khuôn` ⟺ `ĐÃ ĐÓNG`), và ép **một chiều** `ĐÃ ĐÓNG` ⇒ `ô §3.1 = ✅` (+ ⇒ file test trạng thái tồn tại). Token nợ ở §6 khớp `mốc − số ĐÃ ĐÓNG` **và** khớp phép đo lại từ đĩa. Ô §3.1 vẫn được lật, nhưng nó là **hệ quả**, không còn là nơi lưu tiến độ.
- **Alternatives**: (a) ép 2 chiều lên §3.1 như lô danh sách — loại: guard đỏ vì lỗi chấm tay có từ trước, buộc phải chấm-tay-lại (vi phạm `ADR-UX-10`); (b) sửa ngay ô 134 cho khớp đĩa — loại: đó là chấm-tay-lại một ô **ngoài sổ lô đang chạy**, `ADR-UX-11` cấm, và làm mất bằng chứng của sai số bảng tay; (c) bỏ hẳn ràng buộc với §3.1 — loại: tài liệu ĐO lại được phép nói dối về đĩa, đúng thất bại của vòng 3.
- **Consequences**: cột «Trạng thái» phải đổi **cùng lượt** với mã (quên ⇒ đỏ 2 chiều). Guard xanh ở **cả hai đầu**: bước BA (8 ô `CHƯA`, `NO-DET=20`) và sau khi FE land (8 ô `ĐÃ ĐÓNG`, `NO-DET=12`). Ô 134 giữ nguyên ✅ cho tới khi FE land — lúc đó nó ✅ **đúng lý do**, và sai số bảng tay tự tan mà không cần chấm-tay-lại. Mọi lô sau (danh sách lẫn chi tiết) dùng chung khuôn sổ + guard này.

### ADR-UX-22: Token nợ neo vào **bộ dò đo LIVE**, không vào phép trừ tay; cột «Lỗi+Thử lại» đối soát TỪNG Ô

- **Status**: Accepted — 2026-08-04 · **thu hẹp `ADR-UX-11`** cho riêng cột *Lỗi+Thử lại* (không thay thế: 6 cột còn lại vẫn theo lô) · **supersede** cách tính `NO-CON == 89 − flipped` của guard lô 1
- **Context**: sau lô 1, dự án có **ba** con số cho cùng một đại lượng «bao nhiêu route thiếu lối nạp lại»:
  bảng tay `§3.1` đếm **64** · bộ dò đếm **69** · token nợ ghi **77**. Cả ba đều "xanh" vì guard lô 1 chỉ ép
  `token == 89 − số ô lô 1 đã lật`, tức **so tài liệu với chính tài liệu**. Lệch 8 đơn vị sinh ra ở nơi guard
  không nhìn: lô 1 lớp **CHI TIẾT** (`AC-UX-048`) áp `DetailPageShell` cho 8 route ⇒ 8 route đó có `@retry`
  và rời khỏi tập nợ, nhưng phép trừ `89 − 12` không biết điều đó. Lệch 15 ô giữa `§3.1` và bộ dò đi **cả hai
  chiều** (10 ô doc lạc quan hơn đĩa, 5 ô doc bi quan hơn đĩa) ⇒ không thể chữa bằng cách "trừ thêm".
- **Decision**: (1) `[NO-CON=N]` là **số bộ dò in ra khi chạy**, guard tự chạy
  `node frontend/scripts/ui-audit-inventory.mjs --json` rồi so — **không** phép trừ nào được phép đứng giữa;
  (2) cột *Lỗi+Thử lại* của `§3.1` bị ép **parity từng ô trên cả 148 dòng** với bộ dò; (3) mọi phép đo
  chỉ đi qua **một** cài đặt duy nhất — bộ dò — nên không tồn tại "bộ parse thứ hai" để lệch.
- **Alternatives**: (a) giữ phép trừ, chỉ sửa mốc 89→69 — loại: mốc sẽ lại stale ngay lô sau vì lớp CHI TIẾT
  và các vòng khác vẫn tiếp tục lật ô của cột này; (b) chỉ ép **tổng số** ô ❌ khớp bộ dò — loại: hai lỗi ngược
  chiều triệt tiêu nhau, tổng vẫn đúng mà từng ô vẫn sai (đúng ca 10 ✅→❌ ⇄ 5 ❌→✅ hôm nay);
  (c) sinh lại cả `§3.1` từ bộ dò — loại: mất cột «Đau» chấm tay + `uiFixPlanParity` đang khoá `§3.1` ⇄ `04 §11`.
- **Consequences**: bất kỳ thay đổi FE nào **thêm/bớt** lối nạp lại ở **bất kỳ** màn nào (không chỉ màn danh sách)
  sẽ làm guard ĐỎ cho tới khi ô tương ứng ở `§3.1` + token được cập nhật trong **cùng lượt** — đây là chi phí
  cố ý, đổi lấy việc tài liệu ĐO không bao giờ nói dối về cột này nữa. Guard phải **spawn** tiến trình `node`
  (0,15 s) trong test; chấp nhận vì đó là cách duy nhất giữ **một** cài đặt đo. Phép trừ tay chỉ còn được dùng
  làm **kỳ vọng** trong đặc tả (vd `69 − 12 = 57`), không còn là **điều kiện nghiệm thu**.

### Chỉ mục ADR-UX-13 … 18 — đặt tại tài liệu chủ đề (không nhân bản ở đây)

Từ vòng 6, ADR nằm **cùng tài liệu thi hành** để quyết định và hợp đồng đọc liền mạch. Sổ chung giữ **con trỏ**, tránh 2 bản trôi khỏi nhau:

| ADR | Nội dung | Nơi đặt |
|---|---|---|
| **ADR-UX-13** | Lỗi CHẶN đi kênh **inline trong hộp thoại**, toast chỉ cho lỗi KHÔNG chặn | [`05 §10`](./05_MODAL_INLINE_ERROR.md) |
| **ADR-UX-14** | Vùng lỗi tách thành `ModalInlineError.vue` (tier-1), không nhúng thẳng vào `BaseModal` | [`05 §10`](./05_MODAL_INLINE_ERROR.md) |
| **ADR-UX-15** | Làm sạch câu lỗi tại **một cửa** `parseServerMessages`, không tại nơi hiển thị | [`05 §10`](./05_MODAL_INLINE_ERROR.md) |
| **ADR-UX-16** | View gọi `useNotify().confirm()`, **không** gọi `useModal()` trực tiếp | [`06 §12`](./06_CONFIRM_DIALOG_SSOT.md) |
| **ADR-UX-17** | `BaseModal` thêm prop tuỳ chọn `layer` — hộp thoại **hệ thống** nằm trên hộp thoại **nghiệp vụ** | [`06 §12`](./06_CONFIRM_DIALOG_SSOT.md) |
| **ADR-UX-18** | Ngân sách nợ đo theo cặp **(file, số lần)**, CHỈ-GIẢM **hai chiều** | [`06 §12`](./06_CONFIRM_DIALOG_SSOT.md) |

---

## §10. Ghim cho vòng sau

| Vòng | Ghim | Tiêu chí đóng |
|---|---|---|
| **2** | ~~Primitive `EmptyState` + `ListLoadError` + `IconButton`; áp cho **nhóm 1 & 2** trên **10 route P0**; sửa AC-UX-002, 003, 008, 012, 013, 021~~ → **thay bằng ADR-UX-04**: dựng **tầng 0** (15 token ngữ nghĩa + 7 primitive + 3 guard) + adoption `SkeletonLoader`→`ui/Skeleton` + sửa test-drift **AC-UX-023**; sổ mới **AC-UX-032…037** | `tokens.parity` + `uiPrimitiveHygiene` + 7 test primitive + `SkeletonLoader.test.ts` xanh · `uiAuditDocParity` **15/15** · `vitest run` **0 file đỏ** (delta +10 file) · `git status` **0** file dưới `views/`(trừ test AC-UX-023)/`stores/`/`api/`/`.py` |
| **3** | **(ĐÃ XONG — đo lại 2026-07-31: 5 file / 40 test XANH, `ui/*.vue` = 8)** `ListPageShell` = primitive #8 + áp cho **4 màn danh sách** — **AC-UX-041…043, 045, 046** + nhãn VI `/user-profiles` (**AC-UX-042**); spec [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md) | `ui/*.vue` = **8**, barrel 8 export, `uiPrimitiveHygiene` XANH · 4/4 màn `grep -l ListPageShell` · 4 test màn XANH (lỗi ⇒ **0** `ui-empty`, **đúng 1** «Thử lại», thử lại **gọi lại hàm nạp**, bộ lọc còn trong DOM) · bộ dò: cột *Lỗi+Thử lại* **94 → 90**, **0** ô ✅ lật thành ❌ · `vitest run` 0 file đỏ (**+5** file) · `uiAuditDocParity` **15/15** · `git status` **0** file `.py`/`stores/`/`api/` |
| **3 (dời tiếp sang 4)** | `FormField` + `IconButton` + `ClickableRow` + `PageTitle` (**AC-UX-039**); **áp** 7 primitive vòng 2 vào route (**AC-UX-038**); nhóm 3, 4, 5 (skeleton / responsive / empty); chốt bậc màu `neutral` (**AC-UX-040**); các mục vòng 2 cũ còn nợ: AC-UX-002, 003, 008, 012, 013, 021 | 15 route bảng-tràn hết hazard (bọc `DataTable`); 87 → giảm theo số route đã bọc `FormField`; §3.1 đổi ✅ đúng số route đã sửa |
| **4** | **(đang chạy)** `DetailPageShell` = khuôn màn **CHI TIẾT** (tier-1 `components/common/`, **KHÔNG** primitive #9) + áp cho **3 màn**: `CAPADetailView` · `InternalAuditDetailView` · `ManagementReviewDetailView` — **AC-UX-050, 051** (+ mở sổ **AC-UX-048, 049, 052, 053**); spec [`03_DETAIL_PAGE_SHELL.md`](./03_DETAIL_PAGE_SHELL.md), quyết định **ADR-UX-06/07** | `ui/*.vue` vẫn **8** + `vitest run src/components/ui` XANH · `grep -c` trên shell: `DetailLoadError` ≥1, `DetailTabBar` ≥1, nhãn nút nạp lại **0** · ma trận 16 tổ hợp ⇒ **đúng 1** vùng thân bài · probe `#actions` vắng mặt ở error/loading/notfound · 3/3 view `grep -c DetailPageShell` ≥1, `v-else-if="!(capa\|audit\|mr)"` **0**, `text-red-500` **0**, `status ===` **0** · 5 test cũ ≥ **50** test XANH · `vitest run` **0 file đỏ** (+4 file: 305→309) · `npm run typecheck` XANH · `uiAuditDocParity` **15/15** · `git status` **0** file `.py`/`stores/`/`api/`/`ui/` |
| **4 (dời sang 5)** | Nhóm workflow & liên kết chết (AC-UX-016…020); **adoption `ListPageShell` diện rộng (AC-UX-047)**; sửa `stores/imm01.ts::fetchPlans` (**AC-UX-044**) | `WorkflowStepper` dùng ở ≥1 màn workflow; 403 câm có thông báo; cột *Lỗi+Thử lại* giảm tiếp theo số lô đã áp; `fetchPlans` set `loading` + clear `error` (nhánh `v-if="store.loading"` hết là mã chết) |
| **5** | **(đề mục THẬT của vòng 5 — PM ghim 2026-07-31)** Hợp đồng **hộp thoại** tại SSoT `BaseModal.vue` + `useFocusTrap.ts` (trích từ `CommandPalette`, no-fork) — **AC-UX-054…058**; **và** capstone [`04_PHUONG_AN_SUA_TOAN_BO.md`](./04_PHUONG_AN_SUA_TOAN_BO.md) phủ **135 route** × 5 nhóm × 5 đợt; quyết định **ADR-UX-08/09/10** | `BaseModal.dialog.test.ts` + `useFocusTrap.test.ts` xanh (`aria-labelledby` **bằng đúng** `id` của `<h2>`; ESC emit **đúng 1 lần** và **0** sau unmount; `document.activeElement` thật cho wrap + trả focus) · **19 file tiêu thụ + `BaseModal.responsive.test.ts` = 0 dòng đổi** (`git diff --stat`) · `CommandPalette.test.ts` **7/7** · `BaseModal.responsive.test.ts` **4/4** · guard overlay: allowlist **≤30** + hybrid **≤4** + mutation-test 2 chiều · `uiFixPlanParity` **0 route mồ côi** · `vitest run` 0 đỏ (**308 → 312** file) · `git status -- '*.py'` rỗng |
| **5 → DỜI sang [`04`](./04_PHUONG_AN_SUA_TOAN_BO.md) đợt C** | Adoption `DetailPageShell` diện rộng (**AC-UX-048** — 20 màn còn lại) + `DetailTabBar` cho ~~27 màn~~ **9 file / 12 nút-tab tự chế** (**AC-UX-052** — số «27» đã đính chính 2026-08-04, xem [`07 §1.1`](./07_DETAIL_TAB_BAR_SSOT.md); **lô 1 = 3 file ĐÓNG vòng 8**); gỡ 5 hardcode `workflow_state === 'Draft'` ở `ProcurementPlanDetailView` (**AC-UX-049**) **sau khi** BE emit cờ `can_edit`; chốt hợp đồng `useDetailAccess` ⇄ shell (**AC-UX-053**). *Không mất — trở thành **đợt C** (32 route, ~8 vòng) của phương án tổng.* | mỗi lô kèm test trạng thái (404/403/lỗi mạng/`null`); `grep -L DetailLoadError views/*/*DetailView.vue` giảm đúng số lô; `text-red-500` ở màn chi tiết **14 → 0**; `AC-UX-049` chỉ đóng khi có test chứng minh gate đọc cờ server |
| **5 → DỜI sang [`04`](./04_PHUONG_AN_SUA_TOAN_BO.md) đợt E** | Đánh bóng còn lại (**AC-UX-030**) — phần **AC-UX-031** đã **ĐÓNG ngay ở vòng 5** bằng **ADR-UX-10** (bộ dò = SSoT cho DELTA, bảng tay §3.1 đóng băng) | `AC-UX-030`: màn 404 hết khoảng trống nửa dưới + có lối đi tiếp; DELTA của mọi đợt chấm bằng `ui-audit-inventory.mjs --json` theo nhóm (`04 §10`) |

**Cảnh báo tái đo:** mọi con số trong tài liệu này là **ảnh chụp 2026-07-31**. Vòng sau **phải đo lại bằng chính bộ dò §1.2** rồi chấm DELTA — KHÔNG chép lại số cũ.
