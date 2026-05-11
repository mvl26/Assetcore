# IMM-06 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản | 0.1.0 (Wave 2 — DRAFT) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan màn hình

| # | Trang | Frontend Route (Vue) | Frappe Desk URL | Component |
|---|---|---|---|---|
| 1 | Dashboard IMM-06 | `/imm06/dashboard` | `/app/imm06-dashboard` | `views/imm06/CompetencyDashboard.vue` |
| 2 | Training Program List | `/imm06/programs` | `/app/imm-training-program` | `views/imm06/ProgramListView.vue` |
| 3 | Training Program Detail/Edit | `/imm06/programs/:code` | `/app/imm-training-program/{code}` | `views/imm06/ProgramDetailView.vue` |
| 4 | Training Session List | `/imm06/sessions` | `/app/imm-training-session` | `views/imm06/SessionListView.vue` |
| 5 | Training Session Detail | `/imm06/sessions/:name` | `/app/imm-training-session/{name}` | `views/imm06/SessionDetailView.vue` |
| 6 | Training Session Create | `/imm06/sessions/new` | `/app/imm-training-session/new` | `views/imm06/SessionCreateView.vue` |
| 7 | Session Run Mode (Instructor) | `/imm06/sessions/:name/run` | — | `views/imm06/SessionRunView.vue` |
| 8 | Competency List | `/imm06/competencies` | `/app/imm-user-competency` | `views/imm06/CompetencyListView.vue` |
| 9 | Competency Detail | `/imm06/competencies/:name` | `/app/imm-user-competency/{name}` | `views/imm06/CompetencyDetailView.vue` |
| 10 | My Competencies (self-service) | `/me/competencies` | — | `views/imm06/MyCompetenciesView.vue` |
| 11 | Asset Operator Coverage tab | `/assets/:name/coverage` | `/app/asset/{name}` (tab) | (embed in Asset detail) |
| 12 | Gap Report | `/imm06/gap-reports/:name` | `/app/imm-competency-gap-report/{name}` | `views/imm06/GapReportView.vue` |
| 13 | Revoke Modal | (modal) | — | `components/imm06/RevokeCompetencyModal.vue` |
| 14 | Sign-off Modal | (modal) | — | `components/imm06/SignoffModal.vue` |

State management: `frontend/src/stores/imm06Store.ts` (Pinia).

---

## 1. Dashboard IMM-06 (`CompetencyDashboard.vue`)

### 1.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm06/dashboard` |
| API | `imm06.get_dashboard_stats`, `get_competency_gaps_by_dept`, `get_expiring_competencies` |
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

### 1.2 Layout wireframe

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
│ │ ...                                  │ │ ER   │ 80%│ 50% 🔴    │  │
│ │ [Xem tất cả →]                       │ │ CT   │100%│100%      │  │
│ └──────────────────────────────────────┘ └──────────────────────┘  │
│                                                                      │
│ ┌──── Compliance theo Khoa ──────┐ ┌──── Recent Sessions ─────┐    │
│ │ ICU   ████████████░  93%        │ │ TRN-2026-0042  20/05  ✅│   │
│ │ OR    ███████████░░  87%        │ │ TRN-2026-0041  18/05  ✅│   │
│ │ ER    █████████░░░░  75%        │ │ TRN-2026-0040  15/05  ⏳│   │
│ │ CT    ████████░░░░░  62%   ⚠️   │ │ ...                     │   │
│ └─────────────────────────────────┘ └────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 KPIs

| KPI | API field | Click action |
|---|---|---|
| Active Competency | `kpis.total_active_competencies` | Filter list status=Active |
| Expiring 90d | `kpis.expiring_90d` | `get_expiring_competencies(90)` |
| Expired | `kpis.expired_not_renewed` | Filter list status=Expired |
| % Users Competent | `kpis.users_competent_pct` | — |
| Completion Rate | `kpis.training_completion_rate_90d` | Sessions list 90d |
| Pass Rate | `kpis.average_pass_rate_90d` | — |
| Gap Class III | `kpis.total_gap_assets_class3` | Mở Gap Report mới nhất |

### 1.4 Realtime

Subscribe channel `imm06_competency_changed`, `imm06_session_completed`, `imm06_gap_alert` → update KPI cards mà không cần reload.

---

## 2. Training Program List (`ProgramListView.vue`)

### 2.1 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│ Chương trình Đào tạo                          [+ Tạo Program mới]    │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter:                                                             │
│  [Loại ▼]  [Device Model ▼]  [Active ▼]              [Tìm kiếm]    │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Mã             │ Tên                  │ Loại     │ Hiệu lực │ # │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ TRN-MON-INIT-01│ Đào tạo Monitor X3   │ Initial  │ 24 tháng │ 23│ │
│ │ TRN-CT-INIT-01 │ CT Scanner cơ bản    │ Initial  │ 36 tháng │ 8 │ │
│ │ TRN-MON-REF-01 │ Refresher Monitor    │ Refresher│ 12 tháng │ 41│ │
│ └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

`#` cột = số competency Active hiện đang dùng program này.

### 2.2 Actions

| Button | Action | Permission |
|---|---|---|
| `+ Tạo Program mới` | Navigate `/imm06/programs/new` | Tổ HC-QLCL, CMMS Admin |
| Click row | Navigate detail | All |

---

## 3. Training Program Detail/Edit (`ProgramDetailView.vue`)

### 3.1 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ Program: TRN-MON-INIT-01                          Active ●       │
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Định danh ─────────────────────────────────────────────┐     │
│ │ Mã*:     [TRN-MON-INIT-01      ]  (read-only sau create) │     │
│ │ Tên*:    [Đào tạo Monitor Philips X3                   ] │     │
│ │ Mô tả:   [textarea                                      ] │     │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Phạm vi áp dụng ──────────────────────────────────────┐      │
│ │ Device Model:    [MDL-MON-PHILIPS-X3   ▼]               │      │
│ │ Device Category: [                       ▼]              │      │
│ │ ☑ Bắt buộc trước vận hành                               │      │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Loại & Nội dung ──────────────────────────────────────┐      │
│ │ Loại*: [Initial ▼]   Thời lượng*: [8] giờ              │      │
│ │ Nội dung*: [Rich text editor]                          │      │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Hiệu lực ────────────────────────────────────────────┐       │
│ │ Hiệu lực*: [24] tháng    ☑ Yêu cầu tái chứng nhận     │       │
│ └────────────────────────────────────────────────────────┘      │
│ ┌─ Đánh giá ────────────────────────────────────────────┐       │
│ │ Phương pháp*: ⦿ Both ○ Theory ○ Practical              │       │
│ │ Điểm đạt*:   [70]%                                     │       │
│ │ Y/c giảng viên: [Biomed Engineer                  ]    │       │
│ └────────────────────────────────────────────────────────┘      │
│ ┌─ QMS ─────────────────────────────────────────────────┐       │
│ │ QMS Doc Ref: [WI-IMMIS-06-01      ▼]                   │       │
│ └────────────────────────────────────────────────────────┘      │
│                                                                  │
│ ⚠ CẢNH BÁO: Sửa nội dung sẽ trigger re-cert cho 23 user Active │
│                                                                  │
│   [Hủy]                            [Lưu] [Lưu và Trigger Recert] │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 BR-06-04 banner

Khi user sửa các trường critical (`content_outline`, `passing_score_pct`, `assessment_method`, `duration_hours`), banner màu vàng hiện cảnh báo: *"Thay đổi sẽ kích hoạt tái chứng nhận cho N user Active. Có chắc chắn?"*

Sau Save thành công: toast "Đã trigger re-cert cho N người. Tổ HC-QLCL sẽ nhận task lập lịch Refresher."

---

## 4. Training Session Create (`SessionCreateView.vue`)

### 4.1 Layout wireframe

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
│ ┌─ Giảng viên ────────────────────────────────────────────┐     │
│ │ Nội bộ:    [biomed1@hosp.vn          ▼]                 │     │
│ │ Hoặc Ngoại: [Tên              ] [Tổ chức           ]   │     │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌─ Thời lượng ───────────────────────────────────────────┐      │
│ │ Dự kiến*: [8] giờ                                      │      │
│ └─────────────────────────────────────────────────────────┘     │
│ ┌─ Tài liệu ─────────────────────────────────────────────┐      │
│ │ 📎 Slides/handout: [Chọn file...]                       │      │
│ └─────────────────────────────────────────────────────────┘     │
│ ┌─ Học viên (15) ───────────────────────────────[+ Thêm]┐       │
│ │ # User              Khoa     Vai trò                  │       │
│ │ 1 ktv1@hosp.vn      ICU      Operator         [✕]    │       │
│ │ 2 ktv2@hosp.vn      ICU      Operator         [✕]    │       │
│ │ ... (Bulk import CSV)                                  │       │
│ └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│   [Hủy]                              [Lưu Draft] [Lưu & Confirm] │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Validation FE

| Field | Validate FE |
|---|---|
| `training_program` | reqd |
| `session_date` | reqd, >= today (cảnh báo nếu < today: "Buổi training trong quá khứ — chỉ dùng cho nhập lịch sử") |
| `instructor` OR `instructor_external_name` | tối thiểu 1 |
| `participants` | tối thiểu 1 nếu Confirm |
| `duration_planned_hours` | reqd, > 0 |

### 4.3 Bulk import participants

Modal upload CSV: `email, department, role`. FE parse → preview → confirm thêm vào table.

---

## 5. Session Detail (`SessionDetailView.vue`)

### 5.1 Layout — theo workflow_state

**Planned:** Form editable + nút [Sửa], [Xác nhận].

**Confirmed:** Form read-only + nút [Bắt đầu] (Instructor / Tổ HC-QLCL). Email reminder gửi participants tự động.

**In Progress:** Hiện link [Vào Run Mode] → mở `SessionRunView.vue`.

**Completed:** Hiện bảng tổng kết (pass/fail count, danh sách competency tự sinh). Banner: *"Đã tạo N Pending Assessment competency — đang chờ supervisor sign-off"*. Nút [Verify] (Workshop Head).

**Verified:** Hiện badge xanh + nút [Đóng] (Workshop Head, CMMS Admin).

**Closed:** Read-only.

**Cancelled:** Banner đỏ với reason.

### 5.2 Tab "Lịch sử"

Frappe Version timeline — render workflow transitions + field changes.

---

## 6. Session Run Mode (`SessionRunView.vue`) — Instructor view

### 6.1 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ 🎯 Run Mode — TRN-2026-0042                               │
│ Program: TRN-MON-INIT-01 | 8 giờ | Pass: 70% (Theory + Practical)│
│ ──────────────────────────────────────────────────────────────── │
│  Tab: [Điểm danh] [Chấm điểm] [Tổng kết]                        │
│ ──────────────────────────────────────────────────────────────── │
│ Tab Chấm điểm (15 học viên):                                     │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ # User           Att%  Theory  Practical  Result  Note  │    │
│ ├──────────────────────────────────────────────────────────┤    │
│ │ 1 Nguyễn Văn A  [100] [85]    [80]       Pass ✅ [...] │    │
│ │ 2 Trần Thị B    [ 90] [75]    [82]       Pass ✅ [...] │    │
│ │ 3 Lê C          [ 60] [80]    [70]       Fail ❌ [att<80%]│    │
│ │ ...                                                       │    │
│ └──────────────────────────────────────────────────────────┘    │
│  Auto-compute Result:                                            │
│   - Pass: att ≥ 80% AND avg(theory, practical) ≥ 70%            │
│   - Conditional: ≥ 65% nhưng < 70%                              │
│   - Fail: còn lại                                                │
│                                                                  │
│   [Lưu nháp]            [Hoàn thành buổi học → Tạo Competency]  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Behavior

- Mỗi cell auto-recompute `overall_result` real-time khi instructor nhập.
- Save nháp gọi `update_session` (chưa chuyển workflow).
- "Hoàn thành" gọi `complete_session` API → BE validate VR-06, tạo competency, return summary.
- Hiển thị toast: *"Đã hoàn thành buổi training. Tạo 13 Pending Assessment competency. Đã gửi email cho supervisor sign-off."*

---

## 7. My Competencies — Self-service (`MyCompetenciesView.vue`)

### 7.1 Route & Component

| Item | Value |
|---|---|
| Route | `/me/competencies` |
| API | `imm06.get_user_competencies()` (no param → session.user) |
| Permission | All authenticated |

### 7.2 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ 👤 Hồ sơ Năng lực của tôi (Nguyễn Văn A — ICU)                  │
│ ──────────────────────────────────────────────────────────────── │
│ Tổng: 4 năng lực  |  Active: 3  |  Sắp hết hạn: 1  |  Đã hết: 0│
│                                                                  │
│ ┌──── Active (3) ────────────────────────────────────────────┐  │
│ │ ✅ Monitor Philips X3      Operator    HH: 20/05/2028  745d│  │
│ │    [Xem chứng nhận PDF]                                    │  │
│ │ ✅ CT Scanner Siemens       Operator   HH: 30/12/2027  605d│  │
│ │ ⚠ Defibrillator Zoll       Operator   HH: 03/06/2026   30d│  │
│ │    Cần tái chứng nhận! Lịch dự kiến: 01/06/2026            │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌──── Lịch sử / Đã thu hồi ──────────────────────────────────┐  │
│ │ 📦 Monitor v1 (Suspended — superseded by v2)               │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ [Liên hệ Tổ HC-QLCL để đăng ký training]                        │
└──────────────────────────────────────────────────────────────────┘
```

### 7.3 Mobile responsive

< 768px: hiển thị card list dọc thay vì table. Tap card → expand chi tiết. Tap "Xem chứng nhận PDF" → mở viewer hoặc download.

---

## 8. Competency Detail (`CompetencyDetailView.vue`)

### 8.1 Layout — theo state

**Pending Assessment:** Form read-only metadata + nút [Sign-off] (chỉ supervisor scope). Click → mở SignoffModal.

**Active:** Hiện thông tin đầy đủ + countdown badge expiry. Tab Lịch sử (audit trail). Nút [Tạm ngưng] (Workshop Head), [Thu hồi] (Tổ HC-QLCL → mở RevokeModal), [Tải chứng nhận PDF].

**Expiring:** Banner vàng *"Còn 28 ngày — đề nghị đăng ký Refresher"*. Nút [Tạo Refresher Session] (Tổ HC-QLCL).

**Expired:** Banner đỏ *"Đã hết hạn từ DD/MM/YYYY — vui lòng tái chứng nhận"*. Nút [Tái chứng nhận].

**Suspended:** Banner cam *"Tạm ngưng đến DD/MM/YYYY"*. Nút [Khôi phục] (Workshop Head).

**Revoked:** Banner đen + lý do + CAPA link. Read-only terminal.

### 8.2 Status badge

| State | Badge |
|---|---|
| Pending Assessment | Yellow "⏳ Chờ duyệt" |
| Active | Green "✅ Active" + days countdown |
| Expiring | Orange "⚠️ Sắp hết hạn ({days}d)" |
| Expired | Red "❌ Đã hết hạn" |
| Suspended | Orange "🚫 Tạm ngưng" |
| Revoked | Black "🛑 Đã thu hồi" |

Days countdown color theo IMM-05 pattern: > 90 xanh, 30-90 vàng, 0-30 cam, < 0 đỏ.

---

## 9. Sign-off Modal (`SignoffModal.vue`)

### 9.1 Layout

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
│   Theory:    85/100   ✅                    │
│   Practical: 80/100   ✅                    │
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

## 10. Revoke Modal (`RevokeCompetencyModal.vue`)

### 10.1 Layout

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
│              [Hủy] [🛑 Xác nhận Thu hồi]      │
└────────────────────────────────────────────────┘
```

VR-08 enforce client-side: nếu textarea chứa keyword `incident`, `sự cố`, `tai nạn`, `sai phạm` → field CAPA reqd, button disabled cho đến khi điền.

API: `revoke_competency`. Sau success: toast + redirect list. Hiện danh sách WO open của user đã bị flagged.

---

## 11. Asset Operator Coverage Tab (Asset detail)

### 11.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Asset: AC-ASSET-2026-0001 (CT Scanner Siemens) — Class III    │
│ Khoa: ICU                                                       │
│ ──────────────────────────────────────────────────────────────  │
│ [Thông tin] [Hồ sơ] [Năng lực operator ●] [Bảo trì]             │
│                                                                 │
│ Coverage: ✅ Đủ (5 / 2 yêu cầu)                                  │
│                                                                 │
│ ──── Active Operators (5) ────                                  │
│   ✅ Nguyễn Văn A     Operator    HH: 20/05/2028               │
│   ✅ Trần Thị B       Operator    HH: 30/12/2027               │
│   ✅ Lê C             Senior Op   HH: 15/08/2027               │
│   ⚠ Phạm D           Operator    HH: 10/06/2026 (28d)          │
│   ✅ Hoàng E          Trainer     HH: 05/03/2029               │
│                                                                 │
│ ──── Suspended/Expired (1) ────                                 │
│   ❌ Vũ F             Expired 02/04/2026 — Cần tái chứng nhận │
│                                                                 │
│ [+ Đăng ký người vào training]                                  │
└─────────────────────────────────────────────────────────────────┘
```

API: `get_asset_operator_coverage(asset)`. Render `gate_pass` badge.

---

## 12. Gap Report (`GapReportView.vue`)

### 12.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Gap Report — GAP-2026-0018 (04/05/2026)                  │
│ Scope: Hospital-wide                                             │
│ ──────────────────────────────────────────────────────────────── │
│ Tổng assets Class III: 28 | Có gap: 8 | Coverage trung bình: 73%│
│                                                                  │
│ ┌── Ma trận Khoa × Class ──────────────────────────────────┐   │
│ │ Khoa │ Class II  │ Class III    │ Tổng gap              │   │
│ ├──────┼───────────┼──────────────┼──────────────────────┤   │
│ │ ICU  │ 100% ✅   │ 70%  ⚠ (gap 3)│ 3                    │   │
│ │ OR   │ 95%  ✅   │ 100% ✅       │ 0                    │   │
│ │ ER   │ 80%  ⚠   │ 50%  🔴 (gap 5)│ 5                   │   │
│ │ CT   │ 100% ✅   │ 100% ✅       │ 0                    │   │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Click cell → mở list assets vi phạm BR-06-07                    │
│                                                                  │
│ [Xuất Excel] [Email Workshop Head]                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 13. UX Patterns chung

### 13.1 Toast / Notification

| Loại | Màu | Nội dung mẫu |
|---|---|---|
| Success | Xanh | "✅ Đã hoàn thành buổi training. 13 năng lực Pending Assessment được tạo." |
| Warning | Vàng | "⚠️ Năng lực sắp hết hạn trong 28 ngày" |
| Error | Đỏ | Hiển thị `response.error` (tiếng Việt từ VR/`_err`) |
| Info | Xanh nhạt | "📧 Đã gửi email cho supervisor sign-off" |

### 13.2 Empty states

| Page | Empty message |
|---|---|
| Program List | "Chưa có chương trình đào tạo. [+ Tạo mới]" |
| Session List | "Chưa có buổi training nào." |
| My Competencies | "Bạn chưa có năng lực nào. Liên hệ Tổ HC-QLCL để đăng ký training." |
| Coverage tab | "Chưa có operator competent. Cần tổ chức training cho khoa." |

### 13.3 Loading states

Skeleton loader cho list/grid. Spinner cho actions (sign-off, revoke, complete session).

### 13.4 Status indicators

Toàn module dùng pattern màu nhất quán:

| Trạng thái | Màu | Icon |
|---|---|---|
| Active / Pass / Verified | Green | ✅ |
| Pending / Confirmed / Expiring | Yellow/Orange | ⏳ ⚠️ |
| Failed / Expired / Cancelled | Red | ❌ |
| Suspended | Orange | 🚫 |
| Revoked | Black | 🛑 |
| Closed / Archived | Gray | 📦 |

### 13.5 Responsive

- Desktop ≥ 1280px: Layout 2 column (form + side panel history)
- Tablet 768-1279px: 1 column, history collapse vào tab
- Mobile < 768px: My Competencies portal ưu tiên — operator có thể xem hồ sơ trên điện thoại

### 13.6 Realtime updates

Pinia store subscribe `imm06_competency_changed` → update list real-time mà không cần reload. Đặc biệt quan trọng cho Run Mode (instructor) khi multiple participants được chấm điểm.

---

## 14. Permission-driven UI

| UI Element | Hide khi |
|---|---|
| `+ Tạo Program` | role NOT IN {Tổ HC-QLCL, CMMS Admin} |
| `+ Tạo Session` | role NOT IN {Tổ HC-QLCL, Biomed Engineer, Workshop Head, CMMS Admin} |
| Nút [Sign-off] | role NOT IN `_SIGNOFF_ROLES`, hoặc Department Manager mà user không thuộc khoa |
| Nút [Revoke] | role NOT IN `_REVOKE_ROLES` |
| Nút [Verify Session] | role NOT IN {Workshop Head, CMMS Admin} |
| Tab Dashboard | role NOT IN {Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL} |
| Gap Report | role NOT IN {Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL} |
| List Competency (toàn bộ) | non-admin role — backend filter; FE không cần check |
| Run Mode Score editing | role NOT IN {Tổ HC-QLCL, instructor of session, CMMS Admin} |

---

## 15. Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order qua form fields, Enter submit, Esc close modal |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt mô tả đầy đủ |
| Color contrast | Tất cả badge đảm bảo WCAG AA (4.5:1) |
| Screen reader | Toast + modal `role="alert"` / `role="dialog"`; Run Mode table có `<caption>` |
| Color-blind safe | Không chỉ dựa vào màu — luôn kèm icon (✅⚠️❌) |
| Focus indicator | 2px outline rõ ràng cho mọi interactive element |

---

## 16. Wireframe legend

| Symbol | Meaning |
|---|---|
| `[Label]` | Input field |
| `[Value ▼]` | Dropdown |
| `⦿` / `○` | Radio (selected / not) |
| `☑` / `☐` | Checkbox |
| `[Button]` | Action button |
| `📅` | Date picker |
| `📎` | File attach |
| `*` | Required field |
| `✅⚠️❌` | Status indicator |
