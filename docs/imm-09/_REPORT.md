# IMM-09 — Doc Curator Report (Light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: Light-touch (append-only, không rewrite)
- Module: IMM-09 — Sửa chữa, phụ tùng và cập nhật phần mềm
- Khối: C. KHỐI 3 · Đợt: 1 · Owner: PTP Khối 2 · Workshop / Nhóm TBYT

---

## 1. Gap audit (trước khi sửa)

| Section | Template chuẩn | Trạng thái IMM-09 | Hành động |
|---|---|---|---|
| README — Khối kiến trúc | Có | ❌ Thiếu row | Append |
| README — Đợt triển khai | Có | ❌ Thiếu row | Append |
| README — Owner | Có | ❌ Thiếu row | Append |
| README — Cập nhật cuối | Có | 🟡 2026-05-08 | Update → 2026-05-10 |
| 02 §II.6 Process metrics | Có | ❌ Thiếu | Bổ sung (theo WHO CMMS) |
| 02 §II.9 So sánh As-Is vs To-Be | Có | ❌ Thiếu | Bổ sung |
| 02 §III.4 Use Case relationships | Có | ❌ Thiếu | Bổ sung |
| 02 §I.1 Pitch | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 02 §I.3 Stakeholders | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 02 §I.5 KPI | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 04 Workflow | — | ✅ Stable | KHÔNG đụng |

---

## 2. File đã chạm

| File | Loại thay đổi | Section thêm |
|---|---|---|
| `README.md` | Update + Append | +3 row metadata (Khối / Đợt / Owner); update `Cập nhật cuối` |
| `02_Analysis_Design.md` | Append section | +§II.6 Process metrics · +§II.9 As-Is vs To-Be · +§III.4 UC relationships |
| `_REPORT.md` | Tạo mới | (file này) |

KHÔNG chạm: `03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md`.

KHÔNG chạm Pitch / Stakeholder / KPI / Workflow (per user constraint).

---

## 3. Source mapping cho section mới

| Section | Source ưu tiên | Áp dụng |
|---|---|---|
| §II.6 Process metrics | WHO HTM — *CMMS* chapter (MTTR, SLA, audit-readiness) | MTTR theo asset_class · SLA % · repeat failure rate · spare parts traceability · audit-readiness · FCR coverage |
| §II.9 As-Is vs To-Be | WHO HTM CMMS + ground truth từ `services/imm09.py` (BR-09-01..05) | 12 khía cạnh: tạo WO, phân công, vật tư, firmware, checklist, MTTR, SLA, repeat failure, asset status, audit, báo cáo, NĐ98 |
| §III.4 UC relationships | UC catalog hiện có (III.1, III.3, III.5) + Business Rules (IV.2) | 8 `<<include>>` + 4 `<<extend>>` |

---

## 4. Placeholder còn lại (cần BA / khảo sát fill)

- §II.6 MTTR baseline class B/C: `*(Cần khảo sát baseline)*`
- §II.6 % SLA compliance baseline: `*(Cần khảo sát baseline)*`

---

## 5. Cảnh báo lệch template (KHÔNG tự sửa — báo để BA quyết)

- **Heading wording cũ**: `# IMM-09 — Tài liệu module` (README.md line 1) — template gợi ý `# IMM-09 — <Tên module>`. Theo light-touch rules (recipe README "KHÔNG đụng heading wording"), giữ nguyên. Nếu BA muốn rename → cần task riêng.
- **README schema cũ** (`Module | Wave | Trạng thái | Số file | Cập nhật cuối`): giữ y nguyên 5 row đầu, chỉ APPEND 3 row mới ở cuối — đúng quy tắc append-only.
- **Section II.1 (Phân biệt 3 khái niệm)** không có trong file hiện tại. Template có (optional). Không tự thêm vì không nằm trong scope task.

---

## 6. Checklist self-check

- [x] Heading wording cũ — không đổi
- [x] README schema cũ — không đổi tên cột, chỉ append
- [x] Pitch / Stakeholder / KPI / Workflow — không đụng
- [x] Folder khác (imm-08, imm-04, ...) — không chạm
- [x] Section mới có content thực, không bịa số liệu (placeholder rõ ràng)
- [x] Link nội bộ trong README vẫn trỏ đúng file thật
- [x] File _REPORT.md tạo trong scope `docs/imm-09/`

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Code-to-Doc Sync Pass

**Scope**: Đối chiếu docs vs code sau commits `797f5b6` + uncommitted CM view changes (`CMMttrView.vue`, `CMPartsView.vue`, `CMWorkOrderDetailView.vue`) trên `feature/hieuc/wave-2`.

**File đã chạm:**
- `README.md` — bump `Cập nhật cuối` → 2026-05-14.
- `06_Frontend_Design.md` — đồng bộ thuật ngữ UI:
  - Mockup Detail (§3.a, line ~151): `KTV: Nguyễn Văn A` → `Kỹ thuật viên: Nguyễn V.A`.
  - Mockup List filter chips (§3.c, line ~258, 260): `[KTV▼]` → `[Kỹ thuật viên▼]`; column header `KTV` → `Kỹ thuật viên`.
  - `ACTION_MAP['Open']` (§7, line ~510): action label `'Phân công KTV'` → `'Phân công kỹ thuật viên'` (khớp button trong `CMWorkOrderDetailView.vue` mới).
  - Glossary (§9, line ~580): `Assigned To = KTV thực hiện` → `Kỹ thuật viên thực hiện`.
- **Giữ nguyên** role names trong `meta.roles` (`KTV HTM`) và trong tham số `roles: ['KTV HTM']` của `ACTION_MAP` — đây là role constant Frappe, KHÔNG phải display label.

**Endpoint count verify:** code có 12 `@frappe.whitelist` trong `api/imm09.py` — khớp `05_API_Specification.md` §0 (`Catalog 12 endpoints`) và README. `search_spare_parts` đã live + đồng bộ với inventory module IMM-15.

**Workflow / DocType verify:**
- `Asset Repair` status options (DocType JSON) khớp `04_Backend_Design.md` §III state table.
- `mttr_hours`, `sla_breached`, `is_repeat_failure`, `total_parts_cost` field đều tồn tại trong code; docs cite đúng.

**Không chạm:** Pitch (I.1), Stakeholder (I.3), KPI (I.5), Workflow (IV.3), business rules BR-09-01..05, ErrorCode, role names. Folder ngoài `docs/imm-09/` không động.

**Việc còn lại / cần user confirm:**
- IMM-00 uncommitted rewrite `get_asset_kpi` đọc `Asset Repair` records để compute `mttr_hours` + `total_repair_cost` aggregate. Pattern này song song với `get_repair_kpis` IMM-09 nhưng output khác (per-asset vs cohort). Có thể cần section "Cross-module integration" trong `04_Backend_Design.md` IMM-09 mention "IMM-00 `get_asset_kpi` reads `Asset Repair` table" — **chưa thêm** vì chờ IMM-00 commit ổn định.
- Bug-fix CM views (terminology) đã reflect; logic action button chưa thay đổi nên không cần sửa diagram §03.

**Bug-fix references:**
- `797f5b6` — fix bug FE views + API imm08/09 (terminology + roles).
- Uncommitted `feature/hieuc/wave-2` — CM views Vietnamese terminology (`KTV`→`Kỹ thuật viên`, `SL`→`Số lượng`, currency suffix `Kđ`→`nghìn đồng`).

## 2026-05-14 — Full sync 02-09 với code

| File | Số chỗ sửa | Loại drift chính |
|---|---|---|
| 02_Analysis_Design.md | 1 | Header `Cập nhật 2026-05-14` |
| 03_Diagrams.md | 1 | Header `Cập nhật` |
| 04_Backend_Design.md | 5 | Controller `before_insert` đúng pattern (`check_repeat_failure(asset_ref)` trả bool gán `is_repeat_failure`); §7 scheduler flag 3 function **chưa wire** trong `hooks.py` (gap thực); §8 integration thêm Pattern B (IMM-09→IMM-15 lazy-import `create_allocation`) + Pattern C (IMM-16 `gate_wo_submit(doc, method=None)` signature thật, KHÔNG phải `(asset_ref, wo_type="CM")`) + cite line numbers; header date |
| 05_API_Specification.md | 2 | `Phân công KTV` → `Phân công Kỹ thuật viên` trong mô tả endpoint; header date |
| 07_Testing_QA.md | 1 | Header date |
| 08_Deployment.md | 1 | Header date |
| 09_Release.md | 1 | Header thêm `Cập nhật` (giữ `Ngày phát hành 2026-05-08`) |

**Bug-fix references:** uncommitted `feature/hieuc/wave-2` — đã reflect: terminology + Pattern C signature đúng `(doc, method=None)`, Pattern B lazy-import `imm15.create_allocation` (đã hiện diện trong service line ~500).

**Code-to-doc gap đáng chú ý (cần wire trong patch tiếp theo):**
- `assetcore/hooks.py::scheduler_events` chưa đăng ký `check_repair_sla_breach` (hourly), `check_repair_overdue` (daily), `update_asset_mttr_avg` (monthly). 3 function tồn tại trong `services/imm09.py` nhưng không bao giờ chạy. Đã flag trong §7 với cảnh báo ⚠.

**Việc còn lại cần user quyết:**
- Wire 3 scheduler job IMM-09 vào `hooks.py` — cần BE Lead approve trước khi thêm.
- 02_Analysis_Design.md vẫn dùng "KTV HTM" trong UML; giữ vì role constant. Đổi display label trong UML cần task riêng.
