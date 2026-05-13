> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TIER 3 — WI/JD (Work Instruction / Job Description)

**Phiên bản:** 1.0
**Owner:** Trưởng đơn vị

---

## Quy ước
WI = hướng dẫn thực hiện 1 thao tác cụ thể (often mobile-friendly).
JD = mô tả công việc của 1 vị trí.

---

## WI-001 — Quét QR + Báo hỏng trên mobile
- Đối tượng: AC Clinical User.
- Bước:
  1. Mở app PWA AssetCore.
  2. Scan QR trên thiết bị.
  3. Chọn "Báo hỏng".
  4. Chọn severity, mô tả vấn đề, đính kèm photo.
  5. Submit.
- Lưu ý: nếu app offline → form lưu local, tự sync khi online.

## WI-002 — Thực hiện PM checklist trên mobile
- Đối tượng: AC Technician + AC Vendor SE.
- Bước:
  1. Mở WO PM được giao.
  2. Bắt đầu (set actual_start_at).
  3. Thực hiện từng task; nhập expected/actual; đính evidence.
  4. Ghi spare nếu dùng.
  5. Hoàn thành; submit.

## WI-003 — Thực hiện hiệu chuẩn nội bộ
- Đối tượng: AC Cal Lab Engineer.
- Bước:
  1. Kiểm tra reference standard còn hiệu lực.
  2. Mở WO Cal hoặc Calibration Record.
  3. Đo đạc theo phương pháp; ghi measurements.
  4. Pass → phát hành cert + upload PDF.
  5. Fail → stand-down asset + CAPA.

## WI-004 — Sử dụng AssetCore cho QMS Officer
- Đối tượng: AC QMS Officer.
- Hướng dẫn các thao tác chính: open NC, CAPA, Compliance Case, validate WO, approve Document.

## WI-005 — Phê duyệt Document trên hệ thống
- Đối tượng: Approver (Pháp chế / QMS Lead).
- Hướng dẫn: review, e-sign, comment.

## WI-006 — Phát hành QR/RFID cho thiết bị mới
- Đối tượng: KS BME.
- Bước in QR + dán + ghi vào Asset Identifier.

## WI-007 — Cấu hình PM Plan mới
- Đối tượng: KS BME.
- Hướng dẫn chọn asset, frequency, lead_time, tasks_template.

## WI-008 — Cấu hình Calibration Plan
- Tương tự WI-007 nhưng cho Cal.

## WI-009 — Mở Failure Report cho người dùng cuối
- Đối tượng: AC Clinical User.
- Hướng dẫn screen step-by-step (như WI-001 mở rộng).

## WI-010 — Vận hành SLA monitor
- Đối tượng: IT Admin.
- Hướng dẫn dashboard outbox/queue, retry failed.

---

## JD baseline (rút gọn)

### JD-001 — Trưởng phòng VTTBYT (cập nhật)
- Vai trò: Owner nghiệp vụ AssetCore.
- Trách nhiệm:
  - Phê duyệt PM/Cal Plan, Stand-down, Decommission cấp 1.
  - Đảm bảo dashboard VTTBYT hoạt động.
  - Báo cáo BGĐ định kỳ.
- Quyền: AC Asset Manager.

### JD-002 — Kỹ sư BME
- Trách nhiệm:
  - Tạo PM/Cal Plan; mở/đóng WO.
  - Triage Failure Report; root cause; CAPA propose.
- Quyền: AC BME Engineer.

### JD-003 — Kỹ thuật viên thiết bị
- Trách nhiệm: thực hiện WO, scan QR, nhập kết quả mobile.
- Quyền: AC Technician.

### JD-004 — QMS Officer
- Trách nhiệm: vận hành Document Control, CAPA, Compliance Case, validate WO QMS-critical, training tracking.
- Quyền: AC QMS Officer.

### JD-005 — Calibration Lab Engineer
- Trách nhiệm: thực hiện Cal nội bộ; phát hành cert.
- Quyền: AC Calibration Lab Engineer.

### JD-006 — Spare Warehouse Officer
- Trách nhiệm: quản lý kho phụ tùng; cấp phát theo WO; reorder.
- Quyền: AC Spare Warehouse Officer.

### JD-007 — Vendor Service Engineer (External)
- Trách nhiệm: thực hiện WO bảo trì hợp đồng.
- Quyền: AC Vendor Service Engineer (scoped).

---

Mỗi WI/JD là `AC QMS Artifact` Tier=`WI-JD`. WI có training_required=true (≥ 1 lần đầu, refresh hằng năm).
