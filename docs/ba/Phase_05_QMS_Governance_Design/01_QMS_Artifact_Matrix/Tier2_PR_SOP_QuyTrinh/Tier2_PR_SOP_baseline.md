> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TIER 2 — PR/SOP (Quy trình / Tiêu chuẩn vận hành)

**Phiên bản:** 1.0
**Owner:** Trưởng đơn vị + Trưởng QLCL

---

## Cấu trúc SOP chung
Mỗi SOP có:
1. Mục đích
2. Phạm vi áp dụng
3. Định nghĩa thuật ngữ
4. Trách nhiệm
5. Quy trình thực hiện (các bước + actor + thời điểm)
6. Hồ sơ/bằng chứng phát sinh
7. Tham chiếu (luật, tiêu chuẩn, SOP khác)
8. Phụ lục (biểu mẫu liên kết)
9. Ghi chú phiên bản

---

## PR-001 — SOP Tiếp nhận, Lắp đặt, Định danh & Kiểm tra ban đầu
- **Module IMM:** 04
- **Trách nhiệm:** VTTBYT, QMS, Vendor.
- **Bước chính:**
  1. Tiếp nhận hàng (theo PR ERPNext).
  2. Lắp đặt tại địa điểm.
  3. Phát hành Asset Code + QR/RFID.
  4. Thực hiện IQ/OQ/PQ.
  5. Cập nhật hồ sơ Document Record.
  6. Chuyển sang IMM-05 + IMM-06.
- **Hồ sơ phát sinh:** AC Medical Asset, IQ/OQ/PQ Record, Lifecycle Event installed/commissioned.

## PR-002 — SOP Quản lý Hồ sơ Pháp lý Thiết bị
- **Module IMM:** 05
- **Trách nhiệm:** Pháp chế, VTTBYT, QMS.
- **Bước chính:**
  1. Thu thập license/certification từ vendor.
  2. Số hóa + upload Document Record.
  3. Set effective_date + expiry_date.
  4. Theo dõi expiry + alert.
  5. Gia hạn hoặc Compliance Case nếu hết hạn.
- **Hồ sơ:** Document Record (LEGAL/CE/FDA), Lifecycle Event license_registered.

## PR-003 — SOP Bảo trì định kỳ (PM)
- **Module IMM:** 08
- **Trách nhiệm:** VTTBYT, KS BME, KTV/Vendor SE, QMS validate.
- **Bước:**
  1. Thiết lập PM Plan per asset / nhóm asset.
  2. Cron sinh WO PM theo lead time.
  3. Assign + thực hiện checklist.
  4. Validator kiểm tra (nếu QMS-critical).
  5. Đóng WO; cập nhật next_pm_due.
- **Bằng chứng:** WO PM với task pass/fail, photos, vendor report; Lifecycle Event pm_completed.

## PR-004 — SOP Sửa chữa, Phụ tùng và Cập nhật phần mềm
- **Module IMM:** 09
- **Trách nhiệm:** VTTBYT, Kho phụ tùng, Vendor SE.
- **Bước:**
  1. Xác định phụ tùng cần.
  2. Cấp phát từ kho (Stock Entry).
  3. Lắp đặt; test.
  4. Đối với firmware/SW: backup config; update; validate; rollback nếu fail.
- **Bằng chứng:** WO Spare Item, Stock Entry, Software Update Record.

## PR-005 — SOP Hiệu chuẩn
- **Module IMM:** 11
- **Trách nhiệm:** Cal Lab Eng, Vendor Cal, QMS.
- **Bước:**
  1. Calibration Plan.
  2. WO Cal sinh tự động.
  3. Thực hiện, ghi đo đạc, cấp certificate.
  4. Pass → đóng + cập nhật next_due. Fail → stand-down + CAPA.
- **Bằng chứng:** Calibration Record, Cal Cert, Lifecycle Event calibrated.

## PR-006 — SOP Bảo trì khắc phục (CM)
- **Module IMM:** 12
- **Trách nhiệm:** Người báo hỏng, KS BME, KTV/Vendor SE, QMS.
- **Bước:**
  1. Failure Report (web/mobile).
  2. WO CM tự sinh + assign.
  3. Triage → repair → validate → close.
  4. Root cause + CAPA nếu áp dụng.
- **Bằng chứng:** Failure Report, WO CM, Stock Entry, CAPA (nếu).

## PR-007 — SOP Quản lý CAPA
- **Trách nhiệm:** QMS Officer + Lead.
- **Bước:**
  1. Open NC.
  2. Triage; convert to CAPA.
  3. Action plan + owner + timeline.
  4. Effectiveness check.
  5. Close hoặc reopen.

## PR-008 — SOP Recall / FSCA
- **Trách nhiệm:** QMS Lead, Pháp chế, VTTBYT.
- **Bước:**
  1. Nhận thông báo recall (vendor/Bộ Y tế).
  2. Mở Compliance Case Recall.
  3. Identify scope → bulk WO type=Recall.
  4. Disclosure Bộ Y tế trong 48h.
  5. Theo dõi đến đóng.

## PR-009 — SOP Quản lý thay đổi (Change Control)
- **Trách nhiệm:** QMS + IT + ARB + CCB.
- **Bước:**
  1. Submit CR.
  2. Impact analysis.
  3. CCB approve/reject.
  4. Implement.
  5. Verify.

## PR-010 — SOP Quản lý Hồ sơ Tài liệu QMS (Document Control)
- **Trách nhiệm:** QMS Officer.
- **Nội dung:** versioning, review, approval, training, retention.

## PR-011 — SOP Stand-down / Decommission / Disposal (Wave 2)
- **Trách nhiệm:** VTTBYT + QMS + Pháp chế + KTTC.
- **Nội dung:** quy trình multi-level approval, evidence yêu cầu, kết nối ERPNext Asset Disposal.

## PR-012 — SOP Quản lý hợp đồng dịch vụ thiết bị
- **Trách nhiệm:** Procurement + VTTBYT.
- **Nội dung:** lifecycle hợp đồng, gắn Service Provider, theo dõi SLA.

## PR-013 — SOP Quản lý sự cố thiết bị (Adverse Event / Vigilance)
- **Trách nhiệm:** QMS + Pháp chế.
- **Nội dung:** ghi nhận, phân loại, báo cáo Bộ Y tế, CAPA.

## PR-014 — SOP Đào tạo người dùng thiết bị y tế
- **Trách nhiệm:** QMS + Khoa.
- **Nội dung:** kế hoạch, triển khai, competency, release-for-use.

## PR-015 — SOP Backup / Restore / DR cho hệ thống AssetCore
- **Trách nhiệm:** IT.
- **Nội dung:** lịch backup, drill, restore quy trình.

---

Mỗi PR/SOP tồn tại như một `AC QMS Artifact` Tier=`PR-SOP`. Khi training_required=true, áp cho tất cả role liên quan.
