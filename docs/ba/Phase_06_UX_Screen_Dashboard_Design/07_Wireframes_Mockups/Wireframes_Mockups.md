> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# WIREFRAMES & MOCKUPS — ASSETCORE (Wave 1 Key Screens)

**Phiên bản:** 1.0
**Owner:** UX
**Định dạng tài liệu:** ASCII wireframe (low-fi). Hi-fi mockups (Figma) sẽ phát hành kèm.

---

## 1. Asset Profile (Desktop)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Logo  Search...                            🔔  👤 Anita Doan (Asset Manager)  │
├────────────────────────────────────────────────────────────────────────────────┤
│ Asset: MA-2026-0001  CT Scanner GE Optima  [Released for Use]  📷 QR  ⚙ Edit │
├──────────────┬────────────┬────────────┬────────────┬────────────┬────────────┤
│ Overview     │ Lifecycle  │ Documents  │ Maintenance│ Risk       │ Audit      │
├──────────────┴────────────┴────────────┴────────────┴────────────┴────────────┤
│  Định danh                          │  Vận hành                                │
│  Asset Code: BV01-IMG-CT-000123     │  State: Released for Use ✓              │
│  Serial: GE-12345                   │  Commission: 2026-04-15                  │
│  Model: Optima 660 (GE)             │  Released: 2026-05-02                    │
│                                     │  Warranty: 2029-04-15                    │
│  Vị trí                             │                                          │
│  Cơ sở: BV01 - Tòa B - CĐHA - P101  │  PM/Cal status                          │
│  Custodian: KTV Nguyễn Văn A        │  Last PM: 2026-04-10  Next: 2026-07-10   │
│                                     │  Last Cal: 2026-03-20 Next: 2026-09-20   │
│  Phân loại                          │  PM Compliance: ✓                        │
│  Risk class: 2b                     │                                          │
│  Criticality: A (Life-critical)     │  Replacement signal: OK                  │
│                                     │                                          │
│  [ 📞 Báo hỏng ]  [ 📋 Tạo PM Plan ]  [ 🚫 Stand down ]  [ 🖨 In hồ sơ ]      │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Failure Report (Mobile)

```
┌──────────────────────────┐
│  ← Báo hỏng thiết bị     │
├──────────────────────────┤
│  📷 Đã quét:             │
│  MA-2026-0001 CT Optima  │
│  CĐHA P101               │
│                          │
│  Mức độ:                 │
│  ( ) Critical            │
│  ( ) High                │
│  (•) Medium              │
│  ( ) Low                 │
│                          │
│  Mô tả ngắn:             │
│  ┌────────────────────┐  │
│  │ Hình ảnh CT bị mờ. │  │
│  │ Bệnh nhân chờ.     │  │
│  └────────────────────┘  │
│                          │
│  📷 Thêm ảnh (tùy chọn)  │
│                          │
│  [ Submit Failure Rep. ] │
└──────────────────────────┘
```

## 3. WO PM Mobile Execution

```
┌──────────────────────────┐
│  WO-2026-000123 (PM)     │
│  CT Optima — CĐHA P101   │
│  Status: In Progress     │
├──────────────────────────┤
│  ▶ Started: 09:14        │
│  Pause | Complete        │
├──────────────────────────┤
│  Tasks (5/8)             │
│  ☑ 1. Kiểm tra điện      │
│  ☑ 2. Vệ sinh ngoài      │
│  ☑ 3. Test chức năng     │
│  ☑ 4. Đo dòng rò         │
│  ☑ 5. Kiểm tra cảm biến  │
│  ☐ 6. Calib sơ bộ        │
│  ☐ 7. Backup config      │
│  ☐ 8. Test cuối          │
├──────────────────────────┤
│  Spare items: + Add      │
│  - none -                │
├──────────────────────────┤
│  📷 Add evidence         │
│                          │
│  [ Submit when done ]    │
└──────────────────────────┘
```

## 4. QMS Officer Home (Desktop)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Logo                                                  🔔 (12) 👤 QMS Officer  │
├────────────────────────────────────────────────────────────────────────────────┤
│  Inbox                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ NC mới       │  │ CAPA pending │  │ Cases open   │  │ Doc review   │         │
│  │     8        │  │    14        │  │     5        │  │    9         │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                                 │
│  Validate WO queue (15)                                                         │
│  - WO-...0123 PM completed     [Validate]                                       │
│  - WO-...0124 Cal completed    [Validate]                                       │
│  - ...                                                                          │
│                                                                                 │
│  Upcoming                                                                       │
│  - QMS Artifact PR-003 — review due 2026-05-12                                  │
│  - Effectiveness check CAPA-2026-0014 due 2026-05-14                            │
│                                                                                 │
│  Quick: + Open NC   + Open Compliance Case   + Document Upload                  │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 5. Executive Dashboard (BGĐ)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Executive Dashboard — Asset & QMS Overview     Period: April 2026  [▼]      │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │ PM Compl.   │ │ Cal Compl.  │ │ Avg MTTR    │ │ Downtime    │             │
│  │   92%       │ │   89%       │ │   18.2h     │ │   124h      │             │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘             │
│                                                                              │
│  Compliance hotspots                                                         │
│  - License expired & in-use:  2  ⚠   →  drill                                │
│  - PM overdue critical: 5      →  drill                                       │
│  - Open CAPA aging > 60 days: 6 →  drill                                      │
│  - Recall in progress: 1                                                      │
│                                                                              │
│  Asset count by state                                                        │
│  [ Released 1,234 │ Stand-down 12 │ Retired 45 ... ]                          │
│                                                                              │
│  Trend (12 months) — Downtime hours                                          │
│  [ Sparkline chart ]                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6. CAPA Detail screen

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ CAPA-2026-0014 — Recurring Failures CT Optima [In Progress]                    │
├────────────────────────────────────────────────────────────────────────────────┤
│  Sources: NC-2026-0034, NC-2026-0048    [+ Link]                              │
│  Severity: Major                                                                │
│  Owner: KS BME — Trần Văn B                                                    │
│  Approver: QMS Lead — Lê Thị C                                                  │
├────────────────────────────────────────────────────────────────────────────────┤
│  Root Cause                                                                     │
│  RCA Method: 5 Why                                                              │
│  Root cause: Lỗi hiệu chuẩn cảm biến do quá trình PM không bao gồm step X       │
├────────────────────────────────────────────────────────────────────────────────┤
│  Action Plan                                                                    │
│  - [ ] Cập nhật PM checklist BM-002 (owner KS BME, due 2026-05-20)              │
│  - [x] Đào tạo lại KTV (owner QMS Officer, completed 2026-05-05)                │
│  - [ ] Audit lần Cal kế tiếp (owner Cal Lab, due 2026-06-01)                    │
├────────────────────────────────────────────────────────────────────────────────┤
│  Effectiveness Check                                                            │
│  - 30 days check (2026-06-15)                                                   │
│  - 60 days check (2026-07-15)                                                   │
│  - 90 days check (2026-08-15)                                                   │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 7. Notes
- Wireframes này chỉ là low-fi minh họa cấu trúc; hi-fi và component library Figma sẽ phát hành kèm.
- Mobile UI tuân thủ touch target ≥ 44px.
- Dark mode optional.

## 8. Tiêu chí nghiệm thu
- ≥ 12 wireframes Wave 1 (Asset Profile, FR Mobile, WO Mobile, QMS Home, Asset Manager Home, BME Home, Cal Lab Home, Department Head Home, Vendor Portal, Doc Review, CAPA Detail, Recall Tracker, Executive Dashboard).
- Mockup hi-fi Figma đồng bộ.
- Người dùng key đã review qua walk-through.
