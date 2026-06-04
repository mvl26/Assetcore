# 06 — Frontend Design — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Stack | Vue 3 + TypeScript + Pinia + TanStack Vue Query + TailwindCSS |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

> ✅ Implemented (Wave 2). UI hiện có: `frontend/src/views/training/{Program,Session,Competency}{List,Detail}View.vue` (6 views); store `frontend/src/stores/imm06.ts`; API client `frontend/src/api/imm06.ts`. Types không có file riêng `types/imm06.ts` — interfaces khai báo inline trong `stores/imm06.ts` + `api/imm06.ts` (theo convention đơn giản hoá cho module này).
>
> **Đã ship (8 routes thực tế trong `router/index.ts`):** `/imm06/programs`, `/imm06/programs/new`, `/imm06/programs/:name`, `/imm06/sessions`, `/imm06/sessions/new`, `/imm06/sessions/:name`, `/imm06/competencies`, `/imm06/competencies/:name`.
>
> **Chưa ship (planned trong §I bên dưới — giữ làm backlog):** `/imm06/dashboard`, `/imm06/sessions/:name/run`, `/me/competencies`, `/imm06/gap-reports/:name`, các modal `RevokeCompetencyModal`/`SignoffModal`. Route `sessions/new` hiện reuse `SessionDetailView` (không có `SessionCreateView.vue` tách riêng).

---

## §0 Route Prefix Decision (Sprint 4 sign-off)

**Quyết định:** Giữ prefix `/imm06/*` cho mọi route IMM-06 (Decision B).

**Lý do:**
- Tránh xung đột với routes legacy đã có trong production (`/training` đã được dùng cho mục đích khác trong dashboard).
- Convention `views/training/*.vue` cho code organization, `/imm06/*` cho URL — hai layer độc lập, không cần align 1-1.
- IMM-06 là module có route IMM-coded duy nhất (exception so với convention domain-based) — đã document tại `docs/res/frameworks/code-alignment-plan.md` §4.6.

**Áp dụng:**
- Sidebar `MODULE_NAV.imm06` trỏ vào `/imm06/programs`, `/imm06/sessions`, `/imm06/competencies`.
- `router/index.ts` MODULE_ROUTE_PATTERNS map `^/imm06` → `imm06`.
- TASK FE-06-01 đóng (status: keep current prefix).

---

## §I Sitemap & Routes

| # | Status | Route | Component | API calls | Permission |
|---|:---:|---|---|---|---|
| 1 | ⬜ | `/imm06/dashboard` | `CompetencyDashboard.vue` | `get_dashboard_stats`, `get_competency_gaps_by_dept`, `get_expiring_competencies` | IMM Workshop Lead, IMM Training Officer, IMM System Admin, VP Block2 |
| 2 | ✅ | `/imm06/programs` | `ProgramListView.vue` | `list_programs` | All authenticated |
| 3 | ✅ | `/imm06/programs/new` | `ProgramDetailView.vue` (create mode — reuse) | `create_program` | IMM Training Officer, IMM System Admin |
| 4 | ✅ | `/imm06/programs/:name` | `ProgramDetailView.vue` | `get_program`, `update_program` | All authenticated (write: IMM Training Officer) |
| 5 | ✅ | `/imm06/sessions` | `SessionListView.vue` | `list_sessions` | All authenticated |
| 6 | ✅ | `/imm06/sessions/new` | `SessionDetailView.vue` (create mode — reuse, no separate SessionCreateView) | `create_session` | `_SESSION_WRITE_ROLES` |
| 7 | ✅ | `/imm06/sessions/:name` | `SessionDetailView.vue` | `get_session`, `confirm_session`, `cancel_session`, `enroll_participants`, `remove_participant` | All authenticated |
| 8 | ⬜ | `/imm06/sessions/:name/run` | `SessionRunView.vue` | `complete_session` | IMM Training Officer, IMM Biomed Technician |
| 9 | ✅ | `/imm06/competencies` | `CompetencyListView.vue` | `list_competencies` | All authenticated (role-scoped) |
| 10 | ✅ | `/imm06/competencies/:name` | `CompetencyDetailView.vue` | `get_user_competencies`, `revoke_competency`, `recertify_competency`, `signoff_competency` | All authenticated |
| 11 | ⬜ | `/me/competencies` | `MyCompetenciesView.vue` | `get_user_competencies` (self) | All authenticated |
| 12 | ⬜ | `/imm06/gap-reports/:name` | `GapReportView.vue` | `get_competency_gaps_by_dept` | `_DASHBOARD_ROLES` |
| 13 | ⬜ | (modal) | `RevokeCompetencyModal.vue` | `revoke_competency` | `_REVOKE_ROLES` |
| 14 | ⬜ | (modal) | `SignoffModal.vue` | `signoff_competency` | `_SIGNOFF_ROLES` |

**Chú thích:** ✅ Đã ship (router/index.ts) · ⬜ Backlog Wave 3

---

## §II Component Catalog

### `CompetencyDashboard.vue`

**Mục đích:** Tổng quan KPI, expiry timeline, gap matrix, compliance chart.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ IMM-06 Đào tạo & Năng lực — Dashboard                                │
│ ──────────────────────────────────────────────────────────────────── │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │
│ │ Active     │ │ Expiring   │ │ Expired    │ │ % Users    │         │
│ │ Competency │ │ 90 ngày    │ │ Not Renew  │ │ Competent  │         │
│ │   287      │ │    24      │ │    6       │ │  78.5%     │         │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘         │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐                        │
│ │ Completion │ │ Pass Rate  │ │ Gap Class  │                        │
│ │ Rate 90d   │ │   90d      │ │ III Assets │                        │
│ │  92.0%     │ │  87.5%     │ │     8      │                        │
│ └────────────┘ └────────────┘ └────────────┘                        │
│                                                                      │
│ ┌──── Expiry Timeline 90 ngày tới ─────┐ ┌──── Gap Matrix ──────┐  │
│ │ User           Model      Còn lại    │ │ Khoa │ II │ III      │  │
│ │ Nguyễn Văn A  Monitor X3  7 ngày  ⚠ │ │ ICU  │100%│ 70% ⚠    │  │
│ │ Trần Thị B    CT Scan     14 ngày    │ │ OR   │ 95%│100%      │  │
│ │ ...                                  │ │ ER   │ 80%│ 50% ⚠    │  │
│ │ [Xem tất cả →]                       │ └──────────────────────┘  │
│ └──────────────────────────────────────┘                            │
│                                                                      │
│ ┌──── Compliance theo Khoa ──────┐ ┌──── Recent Sessions ─────┐    │
│ │ ICU   ████████████░  93%        │ │ TRN-2026-0042  20/05  ✓ │    │
│ │ OR    ███████████░░  87%        │ │ TRN-2026-0041  18/05  ✓ │    │
│ │ ER    █████████░░░░  75%        │ │ TRN-2026-0040  15/05  ⏳│    │
│ └─────────────────────────────────┘ └────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

**KPI cards:**

> **Ground-truth binding (BR-06-14, 2026-06-04):** Các tile năng lực bind theo shape THẬT của `get_dashboard_stats()` (`data.competencies.*`). Cột "API field (roadmap)" giữ tên `kpis.*` cho bản mở rộng tương lai — KHÔNG bind hiện tại. Xem `05_API_Specification.md §D.1` envelope ground-truth.

| KPI | API field (bind THẬT) | API field (roadmap) | Click action |
|---|---|---|---|
| Active Competency | `data.competencies.active` | `kpis.total_active_competencies` | Filter `/imm06/competencies?status=Active` |
| **Sắp hết hạn** | `data.competencies.expiring` | `kpis.expiring_90d` | → drill `get_expiring_competencies(60)` (số PHẢI khớp tile) |
| **Đã hết hạn** | `data.competencies.expired` | `kpis.expired_not_renewed` | Filter `/imm06/competencies?status=Expired` |
| % Users Competent | *(roadmap)* | `kpis.users_competent_pct` | — |
| Completion Rate | *(roadmap)* | `kpis.training_completion_rate_90d` | `/imm06/sessions` filter 90d |
| Pass Rate | *(roadmap)* | `kpis.average_pass_rate_90d` | — |
| Gap Class III | *(roadmap)* | `kpis.total_gap_assets_class3` | Mở Gap Report mới nhất |

**Quy tắc bind tile "Sắp hết hạn" / "Đã hết hạn" (BR-06-14):**
- **Transport-agnostic:** tile hiển thị **verbatim** giá trị BE trả (`data.competencies.expiring` / `.expired`) — FE **KHÔNG** tự đếm lại từ list, **KHÔNG** lọc client-side theo `workflow_state` thuần. BE là SoT duy nhất (predicate LIVE date-derived).
- **Click tile → drill khớp số:** click "Sắp hết hạn" gọi `get_expiring_competencies(60)`; `count` trả về **PHẢI** bằng giá trị tile (INVARIANT card == drill). Nếu lệch → là bug BE, KHÔNG patch FE để che.
- **No EN leak:** nhãn tile dùng i18n VI (`imm06.status.expiring`="Sắp hết hạn", `imm06.status.expired`="Đã hết hạn") — KHÔNG render raw "Expiring"/"Expired"/"Active".
- **vue-tsc prod 0** sau khi đổi binding (type `DashboardStats.competencies` phải có `expiring`/`expired`/`active`).

---

### `ProgramListView.vue`

**Mục đích:** Danh sách Training Program với filter và nút tạo mới.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ Chương trình Đào tạo                          [+ Tạo Program mới]    │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter:  [Loại ▼]  [Device Model ▼]  [Active ▼]    [Tìm kiếm...]  │
│                                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Mã              │ Tên                   │ Loại     │ Hiệu lực │# │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ TRN-MON-INIT-01 │ Đào tạo Monitor X3    │ Initial  │ 24 tháng │23│ │
│ │ TRN-CT-INIT-01  │ CT Scanner cơ bản     │ Initial  │ 36 tháng │8 │ │
│ │ TRN-MON-REF-01  │ Refresher Monitor     │ Refresher│ 12 tháng │41│ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

`#` = số competency Active đang dùng program này.

---

### `ProgramDetailView.vue`

**Mục đích:** Form chi tiết Program + BR-06-04 change control banner khi sửa critical fields.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Program: TRN-MON-INIT-01                          Active ●       │
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Định danh ──────────────────────────────────────────────┐     │
│ │ Mã*:     [TRN-MON-INIT-01      ]  (read-only sau create) │     │
│ │ Tên*:    [Đào tạo Monitor Philips X3                   ] │     │
│ │ Mô tả:   [textarea                                      ] │     │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Phạm vi ───────────────────────────────────────────────┐      │
│ │ Device Model: [MDL-MON-PHILIPS-X3   ▼]                   │      │
│ │ ☑ Bắt buộc trước vận hành                               │      │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Loại & Nội dung ────────────────────────────────────────┐     │
│ │ Loại*: [Initial ▼]   Thời lượng*: [8] giờ               │     │
│ │ Nội dung*: [Rich text editor ...]                        │     │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Hiệu lực ──────────────────────────────────────────────┐      │
│ │ Hiệu lực*: [24] tháng  ☑ Yêu cầu tái chứng nhận        │      │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Đánh giá ──────────────────────────────────────────────┐      │
│ │ Phương pháp*: ⦿ Both ○ Theory ○ Practical               │      │
│ │ Điểm đạt*: [70]%   Y/c GV: [Biomed Engineer       ]    │      │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ ⚠ CẢNH BÁO: Sửa nội dung sẽ trigger re-cert cho 23 user Active  │
│                                                                  │
│   [Hủy]                            [Lưu] [Lưu và Trigger Recert] │
└──────────────────────────────────────────────────────────────────┘
```

**BR-06-04 banner:** Khi user sửa `content_outline`, `passing_score_pct`, `assessment_method`, `duration_hours` → banner màu vàng: *"Thay đổi sẽ kích hoạt tái chứng nhận cho N user Active. Có chắc chắn?"*. Sau Save: toast "Đã trigger re-cert cho N người."

---

### `SessionCreateView.vue`

**Mục đích:** Form tạo Training Session mới với bulk import participants.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Tạo Buổi Đào tạo                              Status: [Planned ●]│
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Liên kết ──────────────────────────────────────────────┐     │
│ │ Program*:    [TRN-MON-INIT-01           ▼]              │     │
│ │ (auto-fetch: hiệu lực 24t, điểm đạt 70%, Both)           │     │
│ │ Ngày tổ chức*: [📅 2026-05-20]                          │     │
│ │ Loại*:        ⦿ Onsite ○ Online ○ Hybrid                │     │
│ │ Địa điểm:     [Phòng đào tạo F3                       ] │     │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Giảng viên ─────────────────────────────────────────────┐    │
│ │ Nội bộ:    [biomed1@hosp.vn          ▼]                  │    │
│ │ Hoặc Ngoại: [Tên              ] [Tổ chức           ]    │    │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Học viên (15) ──────────────────────────────────[+ Thêm]┐    │
│ │ # User              Khoa     Vai trò              [✕]   │    │
│ │ 1 ktv1@hosp.vn      ICU      Operator             [✕]   │    │
│ │ 2 ktv2@hosp.vn      ICU      Operator             [✕]   │    │
│ │ [Bulk import CSV: email, department, role]                │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│   [Hủy]                              [Lưu Draft] [Lưu & Confirm] │
└──────────────────────────────────────────────────────────────────┘
```

**FE Validation:**

| Field | Rule |
|---|---|
| `training_program` | reqd |
| `session_date` | reqd; nếu < today cảnh báo "Buổi training trong quá khứ — chỉ dùng cho nhập lịch sử" |
| `instructor` OR `instructor_external_name` | tối thiểu 1 |
| `participants` | tối thiểu 1 nếu action = Confirm |
| `duration_planned_hours` | reqd, > 0 |

---

### `SessionDetailView.vue`

**Mục đích:** Chi tiết Session với action theo workflow_state.

**State-based actions:**

| State | Hiển thị | Actions |
|---|---|---|
| Planned | Form editable | [Sửa], [Xác nhận], [Hủy] |
| Confirmed | Read-only | [Bắt đầu] (Instructor/Tổ HC-QLCL) |
| In Progress | Link run mode | [Vào Run Mode] → `SessionRunView` |
| Completed | Summary table + competency list | [Verify] (IMM Workshop Lead) |
| Verified | Badge xanh | [Đóng] (IMM Workshop Lead) |
| Closed | Read-only | — |
| Cancelled | Banner đỏ + reason | — |

**Tab "Lịch sử":** Frappe Version timeline — workflow transitions + field changes.

---

### `SessionRunView.vue` (Instructor mode)

**Mục đích:** Chấm điểm participant real-time, hoàn thành session.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Run Mode — TRN-2026-0042                                         │
│ Program: TRN-MON-INIT-01 | 8 giờ | Pass: 70% (Both)             │
│ ──────────────────────────────────────────────────────────────── │
│  Tab: [Điểm danh] [Chấm điểm] [Tổng kết]                        │
│ ──────────────────────────────────────────────────────────────── │
│ Tab Chấm điểm (15 học viên):                                     │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ # User           Att%  Theory  Practical  Result  Note  │    │
│ ├──────────────────────────────────────────────────────────┤    │
│ │ 1 Nguyễn Văn A  [100] [85]    [80]       Pass ✓  [...] │    │
│ │ 2 Trần Thị B    [ 90] [75]    [82]       Pass ✓  [...] │    │
│ │ 3 Lê C          [ 60] [80]    [70]       Fail ✗  [att] │    │
│ └──────────────────────────────────────────────────────────┘    │
│  Auto-compute:                                                   │
│   Pass: att >= 80% AND avg(theory, practical) >= 70%             │
│   Conditional: avg in [65%, 70%)                                 │
│   Fail: còn lại                                                  │
│                                                                  │
│   [Lưu nháp]         [Hoàn thành buổi học → Tạo Competency]     │
└──────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Mỗi cell auto-recompute `overall_result` real-time khi nhập.
- "Lưu nháp" = update session (chưa chuyển workflow).
- "Hoàn thành" → `complete_session` API → toast: *"Đã tạo 13 Pending Assessment competency. Đã gửi email supervisor."*

---

### `CompetencyListView.vue`

**Mục đích:** Danh sách competency với filter động, role-scoped.

**Filters:** Status (All/Active/Expiring/Expired/Pending), User, Department, Device Model, Expiry date range.

**Columns:** Name, User, Device Model, Level, Status (badge), Achieved date, Expiry date, Days remaining, Department.

---

### `CompetencyDetailView.vue`

**Mục đích:** Chi tiết competency với action theo workflow_state.

**State-based actions:**

| State | Banner | Actions |
|---|---|---|
| Pending Assessment | Yellow "⏳ Chờ duyệt" | [Sign-off] (supervisor scope) → `SignoffModal` |
| Active | Green "✓ Active" + countdown | [Tạm ngưng] (Workshop Lead), [Thu hồi] → `RevokeModal`, [Tải chứng nhận] |
| Expiring | Orange "⚠ Sắp hết hạn ({days}d)" | [Tạo Refresher Session] (Tổ HC-QLCL) |
| Expired | Red "✗ Đã hết hạn" | [Tái chứng nhận] |
| Suspended | Orange "Tạm ngưng đến DD/MM/YYYY" | [Khôi phục] (Workshop Lead) |
| Revoked | Black + reason + CAPA link | Read-only terminal |

**Days countdown color:** > 90d → xanh; 30-90d → vàng; 0-30d → cam; < 0 → đỏ.

**Badge trạng thái phái sinh qua SSoT (BR-06-14, 2026-06-04):** Badge "Đang hiệu lực / Sắp hết hạn / Đã hết hạn" **KHÔNG** hardcode 1:1 từ `workflow_state` thuần. Vì scheduler có thể lỡ phiên (`auto_expire_competencies`) → record `expiry_date < today` vẫn còn cờ `Active`; nếu FE render thẳng cờ → hiện "Đang hiệu lực" cho năng lực ĐÃ hết hạn (rủi ro NĐ98). Quy tắc phái sinh (dùng `expiry_date` + `days_until_expiry` BE đã trả, hoặc helper SSoT FE `deriveCompetencyBadge(c)`):

| Điều kiện (ưu tiên trên→dưới) | Badge hiển thị |
|---|---|
| `workflow_state ∈ {Revoked}` | "Đã thu hồi" (đen, terminal) |
| `workflow_state ∈ {Suspended}` | "Tạm ngưng" (cam) |
| `expiry_date < today` (BẤT KỂ cờ Active/Expiring/Expired) | "Đã hết hạn" (đỏ) |
| `expiry_date ∈ [today, today+60]` ∧ cờ ∈ {Active, Expiring} | "Sắp hết hạn ({days}d)" (cam) |
| còn lại (cờ Active, `expiry_date > today+60`) | "Đang hiệu lực" (xanh) |
| `workflow_state == Pending Assessment` | "Chờ duyệt" (vàng) |

- **No hardcode 'Đang hiệu lực'** cho năng lực có `expiry_date < today` — derive theo bảng trên.
- **No EN leak:** nhãn qua i18n VI (`imm06.status.*`) — không render "Active/Expiring/Expired".
- Badge derive này KHỚP predicate BE (§V.2) → list filter + tile + badge đồng nhất.

---

### `MyCompetenciesView.vue`

**Mục đích:** Self-service portal — user xem hồ sơ năng lực của chính mình.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Hồ sơ Năng lực của tôi (Nguyễn Văn A — ICU)                     │
│ ──────────────────────────────────────────────────────────────── │
│ Tổng: 4 năng lực  |  Active: 3  |  Sắp hết hạn: 1  |  Đã hết: 0│
│                                                                  │
│ ┌──── Active (3) ────────────────────────────────────────────┐  │
│ │ ✓ Monitor Philips X3       Operator   HH: 20/05/2028  745d │  │
│ │   [Xem chứng nhận PDF]                                     │  │
│ │ ✓ CT Scanner Siemens       Operator   HH: 30/12/2027  605d │  │
│ │ ⚠ Defibrillator Zoll       Operator   HH: 03/06/2026   30d │  │
│ │   Cần tái chứng nhận! Lịch dự kiến: 01/06/2026            │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌──── Lịch sử / Đã thu hồi ──────────────────────────────────┐  │
│ │ Monitor v1 (Suspended — superseded by v2)                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ [Liên hệ Tổ HC-QLCL để đăng ký training]                        │
└──────────────────────────────────────────────────────────────────┘
```

**Mobile responsive:** < 768px → card list dọc. Tap card → expand chi tiết. Tap "Xem chứng nhận PDF" → mở viewer hoặc download.

---

### `GapReportView.vue`

**Mục đích:** Gap matrix khoa × device class, xuất Excel, email.

**Wireframe:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Gap Report — GAP-2026-0018 (04/05/2026)                          │
│ Scope: Hospital-wide                                             │
│ Tổng assets Class III: 28 | Có gap: 8 | Coverage tb: 73%        │
│ ──────────────────────────────────────────────────────────────── │
│ ┌── Ma trận Khoa × Class ──────────────────────────────────┐   │
│ │ Khoa │ Class II  │ Class III     │ Tổng gap             │   │
│ ├──────┼───────────┼───────────────┼─────────────────────┤   │
│ │ ICU  │ 100% ✓    │ 70%  ⚠ (gap 3)│ 3                   │   │
│ │ OR   │ 95%  ✓    │ 100% ✓        │ 0                   │   │
│ │ ER   │ 80%  ⚠    │ 50%  ⚠ (gap 5)│ 5                   │   │
│ └──────────────────────────────────────────────────────────┘   │
│ Click cell → list assets vi phạm BR-06-07                       │
│                                                                  │
│ [Xuất Excel] [Email IMM Workshop Lead]                           │
└──────────────────────────────────────────────────────────────────┘
```

---

### `RevokeCompetencyModal.vue`

**Mục đích:** Thu hồi competency với VR-08 CAPA gate.

**Wireframe:**

```
┌────────────────────────────────────────────────┐
│ Thu hồi Năng lực                          [✕] │
│ ────────────────────────────────────────────── │
│ ⚠ Hành động không thể hoàn tác. User sẽ mất  │
│   quyền vận hành thiết bị này ngay lập tức.   │
│                                                │
│ User:           Nguyễn Văn A                   │
│ Device Model:   Monitor Philips X3             │
│                                                │
│ Lý do thu hồi*: (tối thiểu 30 ký tự)          │
│ [textarea                                    ] │
│                                                │
│ Liên kết CAPA (bắt buộc nếu lý do nêu sự cố):│
│ [CAPA-2026-0011                            ▼] │
│                                                │
│ ☑ Tôi xác nhận đã thông báo người quản lý     │
│                                                │
│              [Hủy] [Xác nhận Thu hồi]          │
└────────────────────────────────────────────────┘
```

**VR-08 FE enforcement:** Nếu textarea chứa keyword `incident`, `sự cố`, `tai nạn`, `sai phạm` → CAPA field reqd + button disabled cho đến khi điền. Sau success: toast + redirect list + hiện danh sách WO open bị flag.

---

### `SignoffModal.vue`

**Mục đích:** Supervisor phê duyệt competency.

**Wireframe:**

```
┌─────────────────────────────────────────────┐
│ Phê duyệt Năng lực                     [✕] │
│ ─────────────────────────────────────────── │
│ User:           Nguyễn Văn A (ICU)          │
│ Device Model:   Monitor Philips X3          │
│ Achieved date:  20/05/2026                  │
│ Validity:       24 tháng → Expiry 20/05/2028│
│                                              │
│ Điểm đánh giá:                              │
│   Theory:    85/100   ✓                     │
│   Practical: 80/100   ✓                     │
│                                              │
│ Bạn xác nhận học viên đủ năng lực vận hành?│
│                                              │
│ Ghi chú (optional): [textarea             ] │
│                                              │
│              [Hủy] [Xác nhận Sign-off]      │
└─────────────────────────────────────────────┘
```

API: `signoff_competency`. Sau success: toast xanh + reload competency list.

---

## §III Pinia Store (`stores/imm06.ts`)

> ✅ Implemented — file `frontend/src/stores/imm06.ts` đã có. Snippet dưới là contract minh hoạ; code wins khi drift.

```typescript
// frontend/src/stores/imm06Store.ts
import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'
import type {
  TrainingProgram, TrainingSession, UserCompetency,
  DashboardStats, AuthorizationResult
} from '@/types/imm06'

interface IMM06State {
  programs: TrainingProgram[]
  sessions: TrainingSession[]
  competencies: UserCompetency[]
  dashboardStats: DashboardStats | null
  myCompetencies: UserCompetency[]
  loading: boolean
  error: string | null
}

export const useIMM06Store = defineStore('imm06', {
  state: (): IMM06State => ({
    programs: [],
    sessions: [],
    competencies: [],
    dashboardStats: null,
    myCompetencies: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetchDashboard() {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.get_dashboard_stats')
      this.dashboardStats = res.data
    },

    async fetchPrograms(filters = {}) {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.list_programs', { filters })
      this.programs = res.data.items
    },

    async createProgram(programData: Partial<TrainingProgram>) {
      const api = useApi()
      return api.run('assetcore.api.imm06.create_program', { program_data: programData })
    },

    async fetchSessions(filters = {}) {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.list_sessions', { filters })
      this.sessions = res.data.items
    },

    async createSession(sessionData: Partial<TrainingSession>) {
      const api = useApi()
      return api.run('assetcore.api.imm06.create_session', { session_data: sessionData })
    },

    async completeSession(name: string, participantsResults: object[]) {
      const api = useApi()
      return api.run('assetcore.api.imm06.complete_session', {
        name,
        participants_results: participantsResults
      })
    },

    async fetchCompetencies(filters = {}) {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.list_competencies', { filters })
      this.competencies = res.data.items
    },

    async fetchMyCompetencies() {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.get_user_competencies')
      this.myCompetencies = res.data.competencies
    },

    async revokeCompetency(name: string, revokeReason: string, revokeCapaRef?: string) {
      const api = useApi()
      return api.run('assetcore.api.imm06.revoke_competency', {
        name,
        revoke_reason: revokeReason,
        revoke_capa_ref: revokeCapaRef ?? ''
      })
    },

    async signoffCompetency(name: string) {
      const api = useApi()
      return api.run('assetcore.api.imm06.signoff_competency', { name })
    },

    async checkUserAuth(user: string, deviceModel: string): Promise<AuthorizationResult> {
      const api = useApi()
      const res = await api.run('assetcore.api.imm06.check_user_authorization', {
        user,
        device_model: deviceModel
      })
      return res.data
    },
  },
})
```

---

## §IV i18n — Key Labels

| Key | Vietnamese value |
|---|---|
| `imm06.status.pending_assessment` | Chờ duyệt |
| `imm06.status.active` | Đang hiệu lực |
| `imm06.status.expiring` | Sắp hết hạn |
| `imm06.status.expired` | Đã hết hạn |
| `imm06.status.suspended` | Tạm ngưng |
| `imm06.status.revoked` | Đã thu hồi |
| `imm06.status.planned` | Kế hoạch |
| `imm06.status.confirmed` | Đã xác nhận |
| `imm06.status.in_progress` | Đang diễn ra |
| `imm06.status.completed` | Đã hoàn thành |
| `imm06.status.verified` | Đã kiểm tra |
| `imm06.status.closed` | Đã đóng |
| `imm06.status.cancelled` | Đã hủy |
| `imm06.action.signoff` | Xác nhận Sign-off |
| `imm06.action.revoke` | Thu hồi năng lực |
| `imm06.action.suspend` | Tạm ngưng |
| `imm06.action.restore` | Khôi phục |
| `imm06.action.recertify` | Tái chứng nhận |
| `imm06.action.complete_session` | Hoàn thành buổi học |
| `imm06.action.confirm_session` | Xác nhận buổi học |
| `imm06.error.no_active_competency` | Người dùng chưa có năng lực vận hành thiết bị này |
| `imm06.error.competency_expired` | Năng lực đã hết hạn — yêu cầu tái chứng nhận |
| `imm06.error.capa_required` | Thu hồi do sự cố vận hành phải có CAPA reference |
| `imm06.error.signoff_required` | Cần chữ ký của cán bộ giám sát trước khi kích hoạt |
| `imm06.error.instructor_not_qualified` | Giảng viên không đủ điều kiện theo Program |
| `imm06.error.min_participant` | Phải có ít nhất 1 học viên trước khi xác nhận |
| `imm06.label.days_remaining` | Còn {n} ngày |
| `imm06.label.expiry` | Hết hạn |
| `imm06.label.achieved` | Ngày đạt |
| `imm06.label.recert_due` | Hạn tái chứng nhận |
| `imm06.label.gap_class3` | Gap Class III |
| `imm06.label.coverage` | Tỷ lệ phủ năng lực |

---

## §V Realtime Subscriptions

Module subscribe `frappe.realtime` cho live dashboard update:

```typescript
// imm06Store.ts — subscribeRealtime() action

import { frappe } from '@/frappe'

subscribeRealtime() {
  // Cập nhật competency state (sign-off, revoke, expiry)
  frappe.realtime.on('imm06_competency_changed', (data: {
    user: string
    device_model: string
    old_state: string
    new_state: string
  }) => {
    // Refresh competency list + dashboard KPI cards
    this.fetchCompetencies()
    this.fetchDashboard()
  })

  // Cập nhật session summary sau complete
  frappe.realtime.on('imm06_session_completed', (data: {
    session: string
    pass_count: number
    fail_count: number
  }) => {
    // Refresh session list + flash toast
    this.fetchSessions()
  })

  // Cảnh báo gap mới (weekly report)
  frappe.realtime.on('imm06_gap_alert', (data: {
    department: string
    device_class: string
    gap_count: number
  }) => {
    // Hiện toast warning + badge đỏ trên Dashboard nav
  })
}
```

**Published by:** `IMMUserCompetency.on_update` (imm06_competency_changed), `complete_session` API (imm06_session_completed), `generate_gap_report` scheduler (imm06_gap_alert).

---

## §VI UX Patterns

### Status badges

| State | Badge color | Icon |
|---|---|---|
| Active / Pass / Verified | Green | ✓ |
| Pending / Confirmed / Expiring | Yellow/Orange | ⏳ ⚠ |
| Failed / Expired / Cancelled | Red | ✗ |
| Suspended | Orange | (pause) |
| Revoked | Black | (stop) |
| Closed / Archived | Gray | (archive) |

### Toast messages

| Loại | Màu | Mẫu |
|---|---|---|
| Success | Xanh | "Đã hoàn thành buổi training. 13 năng lực Pending Assessment được tạo." |
| Warning | Vàng | "Năng lực sắp hết hạn trong 28 ngày" |
| Error | Đỏ | Hiển thị `response.error` trực tiếp (tiếng Việt từ VR/BR) |
| Info | Xanh nhạt | "Đã gửi email cho supervisor sign-off" |

### Responsive breakpoints

| Viewport | Layout |
|---|---|
| Desktop ≥ 1280px | 2 column (form + side panel history) |
| Tablet 768-1279px | 1 column, history collapse vào tab |
| Mobile < 768px | Card list dọc; `MyCompetenciesView` ưu tiên — operator xem hồ sơ trên điện thoại |

### Permission-driven UI

| UI Element | Hide khi |
|---|---|
| `+ Tạo Program` | role NOT IN {IMM Training Officer, IMM System Admin} |
| `+ Tạo Session` | role NOT IN `_SESSION_WRITE_ROLES` |
| [Sign-off] | role NOT IN `_SIGNOFF_ROLES`, hoặc Dept Manager mà user không thuộc khoa |
| [Thu hồi] | role NOT IN `_REVOKE_ROLES` |
| [Verify Session] | role NOT IN {IMM Workshop Lead, IMM System Admin} |
| Dashboard tab | role NOT IN `_DASHBOARD_ROLES` |
| Gap Report | role NOT IN `_DASHBOARD_ROLES` |
| Run Mode score editing | role NOT IN {IMM Training Officer, instructor of session, IMM System Admin} |
