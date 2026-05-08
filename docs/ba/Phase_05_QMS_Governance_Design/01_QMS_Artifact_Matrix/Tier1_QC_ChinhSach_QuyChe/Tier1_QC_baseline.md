> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TIER 1 — QC (Quality Control / Chính sách / Quy chế)

**Phiên bản:** 1.0
**Owner:** BGĐ + Trưởng QLCL

---

## QC-001 — Chính sách Quản lý Trang thiết bị Y tế
- **Mục đích:** Tuyên bố cam kết của BV về quản lý vòng đời TBYT theo nguyên tắc HTM/IMMIS/WHO.
- **Phạm vi:** Toàn BV; mọi loại TBYT thuộc danh mục quản lý.
- **Tuyên bố chính sách (mẫu):**
  - BV cam kết quản lý từng thiết bị y tế từ nhu cầu đến giải nhiệm thông qua hệ thống AssetCore.
  - Mọi thiết bị có hồ sơ pháp lý hợp lệ trước khi sử dụng.
  - Mọi thiết bị quan trọng có kế hoạch PM/Calibration đầy đủ và được thực hiện đúng hạn.
  - Mọi sự cố thiết bị được ghi nhận, xử lý và truy nguyên có hệ thống.
  - QMS được duy trì và cải tiến liên tục.
- **Trách nhiệm:** Phòng VTTBYT chủ trì; Phòng QLCL giám sát; các phòng liên quan phối hợp.
- **Đo lường:** thông qua KPI dashboard.

## QC-002 — Quy chế Quản lý Vòng đời Thiết bị HTM
- **Mục đích:** Khung quản trị áp dụng 4 khối – 17 module IMM cho mọi thiết bị.
- **Nội dung:**
  1. Phân loại thiết bị theo Risk Class + Criticality.
  2. Quy trình tiếp nhận → định danh → commissioning → release-for-use.
  3. Quy trình PM/CM/Calibration.
  4. Quy trình Stand-down → Decommission → Disposal.
  5. Quản lý hồ sơ pháp lý.
  6. Quản lý phụ tùng + hợp đồng.
  7. Báo cáo và dashboard.
  8. Vai trò và trách nhiệm.

## QC-003 — Chính sách QMS
- **Mục đích:** Cam kết hệ thống QMS xuyên suốt AssetCore.
- **Nội dung:**
  - Document Control 4 tầng.
  - CAPA + Compliance Case.
  - Risk Register + Change Control.
  - Internal Audit + Management Review.
  - Tham chiếu ISO 9001/13485.

## QC-004 — Chính sách Bảo mật và Quyền riêng tư
- **Mục đích:** Khung an toàn thông tin cho dữ liệu HTM và liên kết PHI (nếu có tích hợp HIS).
- **Nội dung:**
  - RBAC + ABAC.
  - Audit log immutable.
  - Quản lý vendor external.
  - Tuân thủ NĐ 13/2023, ISO 27001.

## QC-005 — Chính sách Quản lý Rủi ro thiết bị y tế
- **Mục đích:** Khung định kỳ đánh giá rủi ro per asset, per process.
- **Nội dung:**
  - Phương pháp (FMEA, ISO 14971).
  - Risk register.
  - Mitigation plans.
  - Liên kết CAPA/Recall.

---

Mỗi QC artifact tồn tại như một `AC QMS Artifact` Tier=`QC`, được approval bởi BGĐ + Trưởng QLCL. Thay đổi qua Change Control.
