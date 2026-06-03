# IMM-08 — Doc Curator Report (Light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: Light-touch (append-only, không rewrite)
- Module: IMM-08 — Bảo trì định kỳ (PM)
- Khối kiến trúc: C. KHỐI 3
- Đợt triển khai: 1
- Owner: PTP Khối 2 · Workshop / Nhóm TBYT

## 1. Phạm vi

Theo gap audit, 3 section bị thiếu:
- §II.6 Process metrics
- §II.9 As-Is vs To-Be
- §III.4 UC relationships

Yêu cầu user: KHÔNG đụng Pitch (I.1) / Stakeholder (I.3) / KPI (I.5) / Workflow (state machine §IV.3) đã có. KHÔNG chạm folder khác.

## 2. Thay đổi đã thực hiện

| File | Loại thay đổi | Chi tiết |
|---|---|---|
| `README.md` | Append + update value | Cập nhật `Cập nhật cuối` 2026-05-08 → 2026-05-10. Append 3 row metadata: `Khối kiến trúc = C. KHỐI 3`, `Đợt triển khai = 1`, `Owner = PTP Khối 2 · Workshop / Nhóm TBYT`. KHÔNG đổi heading, KHÔNG đổi schema cột cũ (`Module / Wave / Trạng thái / Số file / Cập nhật cuối` giữ nguyên). |
| `02_Analysis_Design.md` | Insert §II.6 | Bảng 8 process metrics (PM completion rate, schedule adherence, MTTPM, first-time-pass, major failure rate, checklist coverage, reschedule ratio, audit trail completeness) + technical mapping + lưu ý baseline. Nguồn: WHO HTM *Medical equipment maintenance programme overview* (Performance indicators) + WHO *Computerized maintenance management system* (Reports & KPIs). |
| `02_Analysis_Design.md` | Insert §II.9 | Bảng so sánh As-Is vs To-Be theo 8 trục (Lịch PM, Phân công, Checklist, Hồ sơ PM, Báo cáo KPI, Major Failure, Escalation, Compliance audit) + bảng ROI 5 chỉ số. Nguồn: WHO HTM *Medical equipment maintenance programme overview* (Programme planning) + WHO *Computerized maintenance management system* (Why a CMMS). |
| `02_Analysis_Design.md` | Insert §III.4 | Bảng quan hệ UC (extend / include / generalize) cho 12 dòng quan hệ + ghi chú generalize theo `pm_type` + bảng cross-module relationships (IMM-04 / IMM-09 / IMM-15 / IMM-16). Đồng bộ với UC diagram §III.1 và Business Rules §IV.2. |

## 3. Không đụng (theo yêu cầu user + light-touch)

- §I.1 Pitch — giữ nguyên
- §I.3 Stakeholders & Actors — giữ nguyên
- §I.5 KPI mục tiêu — giữ nguyên
- §IV.3 State Machine (workflow) — giữ nguyên
- README heading `# IMM-08 — Tài liệu module` — giữ nguyên (không đổi sang tên module dài)
- Schema cột metadata cũ trong README — giữ y nguyên, chỉ APPEND
- Các file 03–09 trong cùng folder — KHÔNG chạm
- Folder khác (architecture/, WHO/, gmdn/, template/, ba/, các module khác) — KHÔNG chạm

## 4. Source mapping

| Section mới | WHO HTM source | Section nguồn |
|---|---|---|
| §II.6 Process metrics | `WHO - Medical equipment maintenance programme overview.md` | "Performance indicators" |
| §II.6 Process metrics | `WHO - Computerized maintenance management system.md` | "Reports & KPIs" |
| §II.9 As-Is vs To-Be | `WHO - Medical equipment maintenance programme overview.md` | "Programme planning" |
| §II.9 As-Is vs To-Be | `WHO - Computerized maintenance management system.md` | "Why a CMMS" |
| §III.4 UC relationships | Internal (UC diagram §III.1 + BR §IV.2) | — |

## 5. Việc còn lại / khuyến nghị

- Baseline As-Is (tỷ lệ compliance ~60%, admin time 1–2h/tuần) là ước tính từ interview Wave 1 — cần BA chốt lại số thật khi go-live từng cơ sở (ghi chú `*(Baseline As-Is cần khảo sát từng cơ sở khi go-live)*` đã thêm trong file).
- Threshold cảnh báo của các metric ở §II.6 (vd MTTPM > +20% baseline) cần Workshop Manager + Biomed Engineer review sau 3 tháng vận hành để chốt thực tế.
- DoD checklist §I và §II ở cuối file 02 hiện đánh dấu `[x]` cho toàn bộ — cân nhắc cập nhật để phản ánh việc bổ sung II.6/II.9/III.4 (không thực hiện trong run này vì user cấm rewrite section đã có).

## 6. Checklist tự kiểm

- [x] README giữ schema cột cũ, chỉ append
- [x] Heading wording cũ giữ nguyên
- [x] 3 section thiếu đã thêm đúng vị trí (II.6 giữa II.5/II.7; II.9 giữa II.8/II.10; III.4 giữa III.3/III.5)
- [x] Không thêm placeholder `<XX>` chưa thay
- [x] Pitch / Stakeholder / KPI / Workflow không bị chạm
- [x] Folder khác không bị chạm
- [x] _REPORT.md phát sinh trong cùng folder target

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Code-to-Doc Sync Pass

**Scope**: Đối chiếu docs vs code thực tế sau commits `797f5b6` (bug fix mod 6/8/9) + uncommitted PM/CM view changes trên `feature/hieuc/wave-2`.

**File đã chạm:**
- `README.md` — bump `Cập nhật cuối` → 2026-05-14.
- `06_Frontend_Design.md` — đồng bộ thuật ngữ UI: "KTV" → "Kỹ thuật viên" trong mockup PM Calendar/List/Detail (section 3.a Mockup 2/3/4), bảng route §1, bảng filter §3.2, cột list §3.3, panel detail §3.4. **Giữ nguyên** tên role "HTM Technician" / "KTV HTM" trong cột `Roles` và mọi spec backend — đây là role constant, không phải display label.

**Endpoint count verify:** code có 23 `@frappe.whitelist` trong `assetcore/api/imm08.py` — đúng số liệu docs (`05_API_Specification.md` §0 + README).

**Workflow state verify:**
- `PM Schedule.status` (DocType JSON `pm_schedule.json` line 55) = `Active\nPaused\nSuspended` → khớp `04_Backend_Design.md` §I.1 bảng field (line 46). FE `PmScheduleListView.vue` vừa đổi `Cancelled` → `Suspended` (uncommitted) để khớp BE — không phải doc drift.
- `PM Work Order.status` (DocType JSON `pm_work_order.json` line 78) = `Open\nIn Progress\nPending–Device Busy\nOverdue\nCompleted\nHalted–Major Failure\nCancelled` → khớp `04_Backend_Design.md` §III state table (line 128–134).

**Không chạm:** Pitch (I.1), Stakeholder (I.3), KPI (I.5), Workflow (IV.3), tên role, ErrorCode, business rules. Folder ngoài `docs/imm-08/` không bị động.

**Việc còn lại / cần user confirm:**
- IMM-00 commit uncommitted rewrite `get_asset_kpi` (compute on-the-fly từ `AC Asset Downtime Log` + `Asset Repair` + `PM Work Order`) đụng tới KPI mà IMM-08 dashboard tiêu thụ qua `get_pm_dashboard_stats`. Cần BA IMM-00 confirm trước khi reflect xuống IMM-08 (hiện docs IMM-08 chỉ cite `get_pm_dashboard_stats`, không cite trực tiếp `get_asset_kpi` → không cần sửa IMM-08, nhưng cần note cross-module).
- Screenshot post-build (§3.b) vẫn pending — chưa add file vào `docs/imm-08/screenshots/`.

**Bug-fix references:**
- `797f5b6` — fix bug FE views + API imm08 (đã reflect: terminology consistent với mockup).
- Uncommitted `feature/hieuc/wave-2` — PM views Vietnamese terminology + PM Schedule status fix `Cancelled`→`Suspended`.

## 2026-05-14 — Full sync 02-09 với code

| File | Số chỗ sửa | Loại drift chính |
|---|---|---|
| 02_Analysis_Design.md | 1 | Header thêm `Cập nhật 2026-05-14` |
| 03_Diagrams.md | 1 | Header `Cập nhật` |
| 04_Backend_Design.md | 7 | Controller hooks (`validate_work_order`/`handle_work_order_submit`); service public fn list (đúng tên `submit_result`, `report_major_failure`, `reschedule`, `generate_pm_work_orders_from_schedule`, `create_pm_schedule_from_commissioning`); §4b Repository (4 Repo trong `pm_repo.py`); §7 scheduler đúng 1 entry + doc_events; §8 integration Pattern A/C cite signature thật `gate_wo_submit(doc, method=None)`; tổng quan kiến trúc đổi từ "controller chứa logic" → "3-tier strict" + `_create_cm_wo_from_failure`; header date |
| 05_API_Specification.md | 4 | `KTV` → `Kỹ thuật viên` trong API table mô tả `assign_technician` / `submit_pm_result`; section heading §3, §4; header date |
| 07_Testing_QA.md | 3 | Cảnh báo test code hợp nhất `test_imm08.py` (không tách `test_imm08_service.py` v.v.); scheduler test trỏ `services.imm08.generate_pm_work_orders_from_schedule`; header date |
| 08_Deployment.md | 1 | Header date |
| 09_Release.md | 1 | Header thêm `Cập nhật` (giữ `Ngày phát hành 2026-05-08`) |

**Bug-fix references:** uncommitted `feature/hieuc/wave-2` — đã reflect: hooks function name `create_pm_schedule_from_commissioning`, 3-tier service+repo pattern, scheduler hợp nhất.

**Việc còn lại cần user quyết:**
- 02_Analysis_Design.md vẫn dùng actor "KTV / KTV HTM" trong UML/Mermaid — chưa đổi vì xem như role constant. Nếu BA muốn rename display → cần task riêng.
- §4 04 cite `submit_pm_result` nhưng service file đặt là `submit_result`; giữ alias API name `submit_pm_result` vì khớp endpoint, đã ghi cả hai trong bảng public functions.
