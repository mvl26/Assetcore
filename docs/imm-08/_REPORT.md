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
