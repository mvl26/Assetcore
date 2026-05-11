# Launcher Redesign — IMMIS Navigation Hub

**Ngày**: 2026-05-05
**Phạm vi**: `frontend/src/views/modules/LauncherView.vue`
**Mục tiêu**: tái thiết kế trang launcher (`/launcher`) theo bố cục mockup mới, mở rộng từ 6 segment donut sang **Hub Điều Hướng Module Theo Kiến Trúc IMMIS** với đầy đủ 17 module (IMM-01 → IMM-17).
**Tài liệu nguồn**: `frontend/src/assets/3121215752684005422.jpg`

---

## 1. Phân tích mockup

### 1.1. Tinh thần tổng thể (look & feel)

| Khía cạnh | Launcher hiện tại | Mockup mới |
|---|---|---|
| Theme | Dark cosmic (radial gradient slate-900 → black) | **Light, sky-blue, hospital ambience** |
| Background | Solid radial dark | Bầu trời + cụm nhà bệnh viện 2 bên (illustration nhẹ) |
| Centerpiece | Donut 6 segment + tâm "AssetCore" | **Bán nguyệt lifecycle wheel** + tâm "IMMIS" với icon máy tính + cloud |
| Module display | Label viền ngoài donut | **4 group cards** (panel trắng) bao quanh wheel |
| Tone chữ | Trắng/tối | Navy/xám đậm trên nền trắng |
| Brand | "AssetCore" generic | **Logo bệnh viện + "Phòng Vật tư, Thiết bị Y tế"** + dải "HTM · CMMS · IMMIS" |
| Avatar/topbar | Greeting + link dashboard | **Search · Notification (badge) · Avatar người dùng** |

→ Đây không chỉ là refactor CSS — phải **đổi mental model**: từ "dashboard nội bộ tối giản" sang **"cổng điều hướng cho khách viếng/bác sĩ/lãnh đạo"** — formal hơn, gắn brand bệnh viện rõ hơn.

### 1.2. Cấu trúc layout (đo từ ảnh)

```
┌───────────────────────────────────────────────────────────────────────┐
│  [Logo BV]  BỆNH VIỆN NHI ĐỒNG 1     [HTM · CMMS · IMMIS]     🔍 🔔¹ 👤│ ← Topbar (~80px)
│            Phòng Vật tư, Thiết bị Y tế                                  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│              Hub Điều Hướng Module Theo Kiến Trúc IMMIS               │ ← Title + tagline
│         Điều phối vòng đời thiết bị y tế từ lập kế hoạch đến…         │
│                                                                       │
│                       ╭──── lifecycle wheel ────╮                     │
│                      ╱  Needs │ Tech │ Impl │ O&M ╲                   │ ← Bán nguyệt 5-arc
│                     │       ┌─────────┐         │                     │   (gradient màu)
│                     │       │ 🖥 IMMIS │         │                     │   tâm = IMMIS hub
│                     │       └─────────┘         │                     │
│                                                                       │
│   ┌─ Khối 1 ──────────────────┐    ┌─ Khối 2 ──────────────────┐     │
│   │ 🗂 Kế Hoạch & Mua Sắm     │    │ ▶ Deployment & Implement. │     │ ← 4 group cards
│   │  ┌────────┐ ┌────────┐    │    │ ┌────────┐ ┌────────┐    │     │   panel trắng + shadow
│   │  │ IMM-01 │ │ IMM-02 │    │    │ │ IMM-04 │ │ IMM-03 │    │     │   bo góc 12px
│   │  └────────┘ └────────┘    │    │ └────────┘ └────────┘    │     │
│   │  ┌────────┐ ┌────────┐    │    │ ┌────────┐ ┌────────┐    │     │
│   │  │ IMM-04 │ │ IMM-13 │    │    │ │ IMM-06 │ │ IMM-13 │    │     │
│   │  └────────┘ └────────┘    │    │ └────────┘ └────────┘    │     │
│   └────────────────────────────┘    └────────────────────────────┘     │
│                                                                       │
│   ┌─ Khối 3 ──────────────────┐    ┌─ Khối 4 ──────────────────┐     │
│   │ 🛠 Deployment & Sử Dụng   │    │ 📊 Operations & Maintenance│     │
│   │  IMM-07 · IMM-08          │    │  IMM-07 · IMM-09          │     │
│   └────────────────────────────┘    └────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
```

### 1.3. Chi tiết các thành phần

#### A. Topbar
- **Trái**: logo bệnh viện (huy hiệu tròn) + tên cơ quan 2 dòng:
  - Dòng 1: `BỆNH VIỆN NHI ĐỒNG 1` (uppercase, navy đậm)
  - Dòng 2: `PHÒNG VẬT TƯ, THIẾT BỊ Y TẾ` (small, xám)
- **Giữa**: pill `HTM · CMMS · IMMIS` với icon nhỏ bên trái (gradient xanh)
- **Phải**: 🔍 search icon · 🔔 notification icon (badge số 1 đỏ) · avatar tròn + tên + chevron dropdown

#### B. Title block
- H1 lớn (~28-32px): `Hub Điều Hướng Module Theo Kiến Trúc IMMIS` — màu navy đậm
- Subtitle (~14-15px, xám): `Điều phối vòng đời thiết bị y tế từ lập kế hoạch đến giải nhiệm.`

#### C. Lifecycle wheel (centerpiece)
- **Hình**: bán nguyệt (semi-circle) phía trên, không phải full donut
- **5 arc** màu gradient từ trái → phải:
  1. **Cam đậm** — Decommissioning / "Thiết bị vòng đời sửa nhau" (text mờ trong ảnh)
  2. **Vàng** — Needs assessment, planning & ...
  3. **Xanh lá nhạt** — Technical specification & vendor ...
  4. **Xanh dương** — Implementation, commissioning
  5. **Xanh dương đậm** — "Vận hành & Bảo trì" / Operations
- **Tâm**: monitor icon + cloud icon nhỏ + label `IMMIS` to giữa, xung quanh có cluster các icon thiết bị nhỏ (8 icons) tượng trưng asset network
- **Mục đích**: minh họa **lifecycle WHO HTM** — không phải nút bấm, là branding visual

#### D. 4 Group cards (chính)
Mỗi card = panel trắng, bo góc 12px, viền 1px xám rất nhạt, nhẹ shadow.

Header card có icon + tiêu đề:
- 🗂 **Kế Hoạch & Mua Sắm** (xanh navy nhạt header)
- ▶ **Deployment & Implementation** (xanh dương)
- 🛠 **Deployment & Sử Dụng** (xanh teal/cyan)
- 📊 **Operations & Maintenance** (tím navy)

Body = grid 2 cột module tiles. Mỗi tile:
- Icon vuông màu (~36×36) bo góc 8px
- Code IMM-xx (font weight 700, ~13px)
- Label tiếng Việt 2 dòng (~13px)
- Hover: nhẹ shadow + dịch lên 2px

**Khối 1 (mockup)** chứa: IMM-01, IMM-02, IMM-04, IMM-13
**Khối 2 (mockup)** chứa: IMM-04, IMM-03, IMM-06, IMM-13
**Khối 3 (mockup)** chứa: IMM-07, IMM-08
**Khối 4 (mockup)** chứa: IMM-07, IMM-09

> ⚠ **Mockup không cover 17 module**. IMM-05, IMM-10, IMM-11, IMM-12, IMM-14, IMM-15, IMM-16, IMM-17 không xuất hiện. Có duplicate (IMM-04, IMM-07, IMM-13 lặp 2 lần). → Mockup là **mood reference**, không phải spec dữ liệu cuối cùng.

---

## 2. Khoảng cách so với hiện trạng

### 2.1. Constants (`@/constants/modules.ts`)

Hiện đã có **6 ModuleGroup** (planning, deployment, operations, eol, master, system). Mockup gợi ý 4 group nghiệp vụ + giữ master/system riêng. **Quyết định**:
- **Giữ 6 group** (đã đúng kiến trúc 4-khối + master + system) nhưng chỉ render 4 group nghiệp vụ ở grid chính.
- Master Data + Hệ thống → chuyển thành **secondary row** dưới grid (hoặc collapse panel) để không phá bố cục mockup.

### 2.2. 17 module — mapping đầy đủ (đã đối chiếu BA `Ho_so_kien_truc_IMMIS.md` §A.4 và codebase)

| Module | Tên BA chính thức | Khối | Đợt | Route FE | DocType chính | Trạng thái |
|---|---|---|---|---|---|---|
| **IMM-01** | Đánh giá nhu cầu và dự toán | 1 | 2 | `/needs-requests`, `/procurement-plans` | `imm_needs_request`, `imm_procurement_plan`, `imm_demand_forecast`, `budget_estimate_line`, `needs_priority_scoring` | ✅ Đầy đủ |
| **IMM-02** | Thông số kỹ thuật và phân tích thị trường | 1 | 2 | `/tech-specs` | `imm_tech_spec`, `imm_market_benchmark`, `imm_lock_in_risk_assessment`, `infra_compatibility_item`, `tech_spec_requirement`, `tech_spec_document` | ✅ Đầy đủ |
| **IMM-03** | Đánh giá nhà cung cấp và quyết định mua sắm | 1 | 2 | `/vendor-evaluations`, `/approved-vendors`, `/procurement-decisions` | `imm_vendor_evaluation`, `imm_vendor_scorecard`, `imm_avl_entry`, `imm_procurement_decision`, `imm_supplier_audit`, `vendor_cert` | ✅ Đầy đủ |
| **IMM-04** | Lắp đặt, định danh và kiểm tra ban đầu | 2 | 1 | `/commissioning` | `asset_commissioning`, `commissioning_checklist`, `asset_qa_non_conformance` | ✅ Đầy đủ |
| **IMM-05** | Đăng ký, cấp phép và hồ sơ | 2 | 1 | `/documents`, `/documents/requests` | `asset_document`, `document_request`, `expiry_alert_log`, `required_document_type` | ✅ Đầy đủ |
| **IMM-06** | Đào tạo người dùng | 2 | 2 | — | — | ⏳ Chưa có (placeholder disabled) |
| **IMM-07** | Theo dõi hiệu suất | 3 | 3 | partial via `/dashboard` | `ac_asset_downtime_log` (partial) | ⏳ Một phần — link tạm về dashboard, badge "Một phần" |
| **IMM-08** | Bảo trì định kỳ (PM) | 3 | 1 | `/pm/dashboard` (calendar/work-orders/schedules/templates) | `pm_work_order`, `pm_schedule`, `pm_checklist_template`, `pm_task_log` | ✅ Đầy đủ |
| **IMM-09** | Sửa chữa, phụ tùng và cập nhật phần mềm | 3 | 1 | `/cm/dashboard`, `/cm/firmware`, `/cm/mttr` | `asset_repair`, `repair_checklist`, `spare_parts_used`, `firmware_change_request` | ✅ Đầy đủ |
| **IMM-10** | Hậu kiểm và tuân thủ (post-market surveillance, recall, FSCA) | 3 | 3 | partial via `/capas` | `imm_capa_record` (CAPA có; recall/FSCA chưa) | ⏳ Một phần |
| **IMM-11** | Hiệu năng và hiệu chuẩn | 3 | 1 | `/calibration`, `/calibration/dashboard` | `imm_asset_calibration`, `imm_calibration_measurement`, `imm_calibration_schedule` | ✅ Đầy đủ |
| **IMM-12** | Bảo trì khắc phục (sự cố, triage, RCA) | 3 | 1 | `/incidents/dashboard`, `/incidents/list`, `/capas` | `incident_report`, `imm_rca_record`, `imm_rca_five_why_step` | ✅ Đầy đủ |
| **IMM-13** | Ngừng sử dụng và điều chuyển | 4 | 3 | `/asset-transfers` | `asset_transfer` | ✅ Đầy đủ |
| **IMM-14** | Giải nhiệm thiết bị | 4 | 3 | `/depreciation` (đối soát kế toán) | `ac_asset_depreciation_schedule` | ✅ Một phần (chưa có closure record) |
| **IMM-15** | Theo dõi tồn kho phụ tùng | 3 | 2 | `/inventory`, `/warehouses`, `/spare-parts`, `/stock`, `/stock-movements` | `ac_spare_part`, `ac_spare_part_stock`, `ac_stock_movement`, `ac_warehouse` | ✅ Đầy đủ |
| **IMM-16** | Theo dõi tuân thủ (audit, NC/CAPA, scorecard) | 3 | 2 | `/audit-trail`, `/capas` | `imm_audit_trail`, `audit_finding`, `imm_capa_record` | ✅ Đầy đủ |
| **IMM-17** | Phân tích dự đoán (predictive analytics) | 3 | 3 | — | — | ⏳ Chưa có (placeholder disabled) |

**Tổng kết tình trạng**:
- ✅ **13/17 module có FE+BE đầy đủ**: IMM-01, 02, 03, 04, 05, 08, 09, 11, 12, 13, 15, 16, và IMM-14 (một phần).
- ⏳ **2/17 module có một phần** (IMM-07, IMM-10): có thể link sang trang gần nhất với badge "Một phần".
- ⏳ **2/17 module chưa có FE+BE** (IMM-06, IMM-17): hiển thị tile disabled với badge "Sắp ra mắt".

**Quy tắc render trên launcher** *(cập nhật 2026-05-05 lần 3)*:
- **Mỗi module = ĐÚNG 1 tile** mang code IMM-XX. Tổng = 17 tile tổ chức theo 4 khối (3-3-9-2).
- Sub-function của module (vd: IMM-08 PM có dashboard/work-orders/calendar/schedules/templates) nằm trong **sidebar của module đó**, KHÔNG render thành nhiều tile trên launcher.
- Tile disabled (IMM-06, IMM-17): KHÔNG `router.push`, opacity giảm, cursor `not-allowed`, badge "Sắp ra mắt".
- Tile "Một phần" (IMM-07, IMM-10, IMM-14): vẫn click được, link tạm về route gần nhất (/dashboard, /capas, /depreciation), hiển thị badge "Một phần".

**Phủ sidebar cho từng module** *(verify 2026-05-05)*:
- 13 module có sidebar nav riêng: IMM-01, 02, 03, 04, 05, 08, 09, 11, 12, 13, 14, 15, 16. Mỗi nav cover toàn bộ list/dashboard/calendar route của module.
- 4 module disabled/một phần (IMM-06, 07, 10, 17): tile click sang route đại diện → sidebar fallback (system hoặc imm12).
- Trang `*/new`, `*/edit`, `:id`, modal: KHÔNG có trong sidebar (đúng nguyên tắc) — truy cập qua nút trên list page hoặc workflow trong detail page.
- Master (Tài sản & Đối tác): nav gồm Assets, QR scan, Device models, Suppliers, Service contracts, SLA policies.
- System: nav gồm Dashboard tổng quan, Người dùng, Reference data, Phê duyệt chờ.

### 2.3. Visual stack

| Yếu tố | Hiện tại | Cần đổi |
|---|---|---|
| Theme | Dark | **Light** (background `#f6faff` + sky illustration optional) |
| Layout | SVG donut + overlay tuyệt đối | **CSS Grid** (header / wheel / 2×2 group cards) |
| Branding | "AssetCore AC" tile | **Logo BV (slot)** + "BỆNH VIỆN NHI ĐỒNG 1" + sub |
| Topbar action | Greeting + dashboard link | **Search button + Notification button + User dropdown** |
| Centerpiece | Donut clickable | **Bán nguyệt SVG tĩnh** (presentational, không click) — tách khỏi navigation |
| Navigation | Click segment → first card route | **Click module tile → route trực tiếp** (giữ keyboard `1-9` chuyển khối, hoặc đổi thành tab) |

---

## 3. Đề xuất kiến trúc UI mới

### 3.1. Component breakdown

```
LauncherView.vue
├── <LauncherTopbar>            ← logo BV, dải HTM·CMMS·IMMIS, actions
├── <LauncherHero>               ← H1 + tagline + lifecycle wheel SVG
│   └── <LifecycleWheelSVG>     ← bán nguyệt 5 arc + tâm IMMIS (PURE PRESENTATIONAL)
├── <ModuleGroupGrid>            ← grid 2×2 group nghiệp vụ
│   └── <ModuleGroupCard> × 4
│       └── <ModuleTile> × N    ← icon + code + label, click → route
└── <SecondaryRow>               ← Master Data + Hệ thống (compact, tách biệt visual)
```

→ Tách `LifecycleWheelSVG` thành component riêng vì là branding asset, không liên quan navigation.

### 3.2. Layout grid (desktop ≥1280px)

```css
.launcher {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  grid-template-areas:
    "topbar"
    "hero"
    "groups"
    "secondary";
  background: linear-gradient(180deg, #eaf3ff 0%, #f8fbff 50%, #ffffff 100%);
}
.groups {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 32px 24px;
}
```

Tablet (768-1279): `grid-template-columns: 1fr` (stack 4 group dọc).
Mobile (<768): wheel ẩn / thu nhỏ, group cards full width.

### 3.3. Token màu mới

| Token | Hex | Dùng cho |
|---|---|---|
| `--bg-sky-1` | `#eaf3ff` | gradient nền top |
| `--bg-sky-2` | `#f8fbff` | gradient nền mid |
| `--surface` | `#ffffff` | card background |
| `--border` | `#e2e8f0` | card border |
| `--shadow-card` | `0 2px 12px rgba(15,23,42,0.06)` | card |
| `--text-primary` | `#0f172a` | H1, label |
| `--text-secondary` | `#475569` | sub, description |
| `--accent-planning` | `#1e40af` | header card khối 1 |
| `--accent-deployment` | `#0ea5e9` | header card khối 2 |
| `--accent-deploy-use` | `#06b6d4` | header card khối 3 |
| `--accent-operations` | `#6366f1` | header card khối 4 |

### 3.4. Lifecycle Wheel SVG

- ViewBox `0 0 200 110` (bán nguyệt)
- 5 arc đồng tâm với góc 36° mỗi arc, gap 1°, gradient fill (orange → yellow → lime → cyan → blue)
- Tâm: rect bo góc + emoji/icon máy tính SVG inline + text "IMMIS"
- Quanh tâm: 6-8 icon thiết bị nhỏ (rect + serial line) bố trí radial — chỉ trang trí
- **Không tương tác** → `pointer-events: none`, `aria-hidden="true"`

### 3.5. Accessibility / hành vi
- Topbar search → mở `<dialog>` quick-jump (giữ Cmd/Ctrl-K)
- Notification → router.push('/notifications') (cần có route, hoặc dropdown panel)
- User avatar → dropdown: Hồ sơ · Đăng xuất
- Module tile = `<button>` hoặc `<router-link>` — Tab focus → ring xanh
- Keyboard `1-4` jump khối, focus khối đầu; `Esc` về dashboard (giữ)
- Reduced motion: tắt transition translateY khi hover

---

## 4. Triển khai theo giai đoạn

### Phase 1 — Skeleton & data (không phá hiện tại)
1. Audit `MODULE_GROUPS` cho đủ 17 module: bổ sung IMM-06, IMM-07, IMM-10 (nếu có), IMM-17. Dùng `disabled: true` cho card chưa có route.
2. Tạo asset logo BV (placeholder) ở `frontend/src/assets/hospital-logo.svg`.
3. Tạo component `LifecycleWheelSVG.vue`.

### Phase 2 — UI mới (feature flag)
4. Refactor `LauncherView.vue` → light theme + grid 2×2.
5. Topbar mới: search trigger, notification badge (đọc từ store), user dropdown (tái dùng nếu đã có).
6. Group card layout với module tile 2 cột.
7. Secondary row Master + System (collapse).

### Phase 3 — Polish
8. Hover/focus states, dark-mode toggle (optional, mặc định light).
9. Responsive breakpoints (1280 / 768 / 480).
10. Smoke test: tất cả route module tile click được, role-based filter còn hoạt động.
11. Visual diff với mockup.

### Phase 4 — Decommission cũ
12. Xóa donut SVG code, ICON_PATHS map cũ, COLORS map cũ.
13. Update `docs/res/Frontend_Router_Navigation_Map.md` nếu route đổi.

---

## 5. Quyết định triển khai (đã xác nhận với user 2026-05-05)

1. **Logo BV**: dùng `frontend/src/assets/logo-nd1.png` (logo Bệnh Viện Nhi Đồng 1, màu xanh dương).
2. **Ảnh mockup chỉ là tham khảo** — không bám sát phân nhóm/duplicate trong ảnh. **Phải hiển thị đầy đủ 17 module + chức năng phần mềm hiện có** (xem §2.2 cho mapping).
3. **Module chưa có route** (IMM-06, IMM-17): hiển thị tile dạng `disabled` với badge "Sắp ra mắt", click không điều hướng.
4. **Search & Notification topbar**: Phase 1 dùng placeholder (không bắt buộc functional ngay).
5. **Background**: dùng gradient sky tone xanh nhạt; KHÔNG illustration cụm nhà bệnh viện (giảm chi phí asset, không phá readability).
6. **Kiến trúc điều hướng** *(quan trọng — quyết định 2026-05-05 lần 2)*:
   - **`/launcher` LÀ TRANG CHỦ** điều hành — không có "Dashboard điều hành" tách rời. Module IMM-07 (Theo dõi hiệu suất) link tạm về `/dashboard` chỉ là legacy view, không phải home.
   - **KHÔNG có shortcut `Esc → /dashboard`**. Launcher là root.
   - **Mỗi module có sidebar riêng**: vào trang của module IMM-XX → AppSidebar chỉ hiện chức năng thuộc module đó. Không trộn nhiều module trong một sidebar.
   - **Cross-cutting**: 2 sidebar đặc biệt cho `master` (Tài sản & Đối tác) và `system` (Hệ thống — Dashboard, Người dùng, Reference data).
   - **Cơ chế kỹ thuật**: `route.meta.moduleId` được auto-tag từ `MODULE_RULES` regex trong `router/index.ts`. AppSidebar đọc `moduleId` và lookup `MODULE_NAV[moduleId]` để render items.
   - **Logo trong sidebar** + nút "Trang chủ Launcher" ở footer: cả hai đều `router.push('/launcher')` để user luôn về home được.

---

## 6. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Mockup chỉ cover ~10/17 module → có thể bố cục thực tế chật | Trung bình | Group card scroll dọc khi >6 tiles, hoặc "Xem thêm" |
| Light theme phá visual identity hiện tại của các trang con (vẫn dark cosmic?) | Thấp | Audit các view khác — hầu hết đã light theme |
| Logo BV bản quyền | Trung bình | Confirm với BA / Phòng Vật tư trước khi commit asset |
| Lifecycle wheel chiếm không gian, đẩy module cards xuống fold | Cao | Có thể thu nhỏ wheel còn 240×120px, hoặc đổi thành thanh ngang trên mobile |

---

## 7. Kết luận

Mockup đẩy launcher từ **"công cụ điều hướng nội bộ"** → **"cổng IMMIS có brand bệnh viện"**. Thay đổi không chỉ cosmetic mà còn ở **information architecture**:
- 4 khối nghiệp vụ là first-class (giống CLAUDE.md §7).
- Master Data và Hệ thống trở thành secondary.
- Lifecycle wheel thành **branding/visual hook**, không phải navigation.

Khuyến nghị bắt đầu **Phase 1** (audit data & component skeleton) và xác nhận 5 câu hỏi ở §5 trước khi vẽ UI.
