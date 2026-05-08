> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# RISK / ISSUE / DEPENDENCY LOG — ASSETCORE (Baseline)

**Phiên bản:** 1.0 (Baseline khởi tạo)
**Owner:** PMO – Risk Officer
**Cập nhật:** Hàng tuần

---

## A. RISK REGISTER

**Quy ước:** P (Probability) × I (Impact) → Score (1–25). Mức Cao ≥ 12; Trung bình 6–11; Thấp ≤ 5.

| ID | Loại | Mô tả | P (1–5) | I (1–5) | Score | Mức | Trigger | Owner | Mitigation | Contingency | Trạng thái |
|----|------|------|---------|---------|-------|-----|---------|-------|------------|-------------|------------|
| R-01 | Tổ chức | Kháng thay đổi từ kỹ thuật viên/khoa lâm sàng — không nhập dữ liệu trên hệ thống mới | 4 | 4 | 16 | Cao | UAT adoption < 60% | Trưởng VTTBYT | Co-design sớm với KTV; mobile UI; training nhiều đợt; gắn KPI cá nhân | Tăng cường champion mỗi khoa; chính sách bắt buộc | Open |
| R-02 | Dữ liệu | Dữ liệu legacy thiếu/sai → migration trễ | 4 | 4 | 16 | Cao | Sample audit > 20% lỗi | Migration Lead | Data quality rule sớm (Phase 03); dry-run; data steward phối hợp VTTBYT | Tách wave migration; chấp nhận import từng tranche | Open |
| R-03 | Kiến trúc | Custom hóa quá nhiều → khó nâng cấp ERPNext | 3 | 4 | 12 | Cao | ADR custom > 30 baseline | SA Lead | Build vs Configure log; ưu tiên hooks/server script; review từng wave | Giảm scope custom; thuê Frappe partner re-architect | Open |
| R-04 | QMS | Thiếu QMS Officer chuyên trách → QMS engine "decor" | 3 | 4 | 12 | Cao | QMS artifact tồn đọng > 30 ngày | Trưởng QLCL | Bổ nhiệm QMS Officer trước Phase 05; SLA approval | Outsource QMS consultant tạm thời | Open |
| R-05 | Tích hợp | HIS/LIS/PACS không có API hoặc owner không hợp tác | 3 | 4 | 12 | Cao | Survey trả lại "không có API" | IT Lead | Khảo sát Phase 07 sớm; chuẩn FHIR; làm bridge file/CSV nếu cần | Hoãn integration sang Wave 2/3 | Open |
| R-06 | Pháp lý | Hồ sơ giấy phép thiết bị mất/quá hạn → không qua kiểm tra | 3 | 5 | 15 | Cao | License expiry alert > 10% | Trưởng VTTBYT + Pháp chế | Số hóa license trong Phase 01; alert tự động | Khoanh vùng thiết bị đến khi đủ giấy phép | Open |
| R-07 | An ninh | Rò rỉ dữ liệu nhạy cảm (PHI nếu có) | 2 | 5 | 10 | Trung bình | Kiểm thử security fail | Trưởng CNTT (ATTT) | RBAC + audit log + phân vùng dữ liệu | IR plan; disclosure | Open |
| R-08 | Ngân sách | Chi phí Frappe partner & hạ tầng vượt | 3 | 3 | 9 | Trung bình | Burn-rate > 110% | PMO | Fixed-price cho Wave 1; review tháng | Cắt scope Wave 2 | Open |
| R-09 | Vendor | Vendor Frappe rời bỏ giữa chừng | 2 | 4 | 8 | Trung bình | Vendor giao hàng trễ 2 sprint | PMO | Multi-vendor hợp đồng; code in-repo BV | Tuyển in-house Frappe dev | Open |
| R-10 | Hạ tầng | DR site chưa sẵn sàng cho go-live | 3 | 3 | 9 | Trung bình | Sau cutover M5 chưa test DR | IT Lead | Lên kế hoạch DR ngay Phase 02 | Backup tape rotation thủ công | Open |
| R-11 | Quy trình | Workflow ban đầu phức tạp gây khó dùng | 3 | 3 | 9 | Trung bình | UAT comment > X | BA Lead | Co-design + iteration UX | Đơn giản hóa, làm thêm wave | Open |
| R-12 | KPI | KPI thiết kế nhưng không có nguồn dữ liệu | 3 | 3 | 9 | Trung bình | Phase 06 thiếu lineage | BA Lead | Metric Dictionary bắt buộc lineage | Drop KPI hoặc đợi data | Open |
| R-13 | Đào tạo | Thiếu thời gian training vì khoa lâm sàng bận | 3 | 3 | 9 | Trung bình | Tỉ lệ tham gia < 60% | Trainer + Trưởng khoa | Mini-session 30' + e-learning | Coaching tại chỗ | Open |
| R-14 | Pháp lý dự án | Thay đổi quy định Bộ Y tế giữa wave | 2 | 4 | 8 | Trung bình | Văn bản mới ban hành | Pháp chế | Theo dõi NĐ/TT định kỳ | CR khẩn | Open |
| R-15 | Audit | Audit nội bộ phát hiện gap tuân thủ | 2 | 3 | 6 | Trung bình | Audit Q3 finding > 5 NC | QMS | CAPA chuẩn | Roadmap fix | Open |

## B. ISSUE LOG (template)

| ID | Mở | Mô tả | Severity | Owner | Hành động | Trạng thái | Đóng |
|----|-----|------|----------|-------|-----------|------------|------|
| I-001 |  | (chưa có issue) | – | – | – | – | – |

## C. DEPENDENCY LOG (cấp dự án)

| ID | Loại | Phụ thuộc vào | Đầu mối | Cần trước phase | Trạng thái | Ghi chú |
|----|------|---------------|---------|-----------------|------------|--------|
| D-01 | Internal | Bổ nhiệm QMS Officer | HR + QLCL | Phase 05 | Open | Bắt buộc trước Wave 1 build |
| D-02 | Internal | Số hóa hồ sơ pháp lý thiết bị Wave 1 | Pháp chế + VTTBYT | Phase 03 (migration template) | Open | Cần kế hoạch riêng |
| D-03 | Internal | Hạ tầng DEV/UAT/STAGING/PROD + DR | CNTT | Phase 09 | Open | Trễ sẽ ảnh hưởng Wave 1 build |
| D-04 | External | Tài liệu IQ/OQ/PQ từ vendor OEM | Vendor + VTTBYT | Phase 01 (evidence inventory) | Open | – |
| D-05 | External | API/contract HIS/LIS | CNTT + Phòng KHTH | Phase 07 | Open | Có thể đẩy Wave 2 |
| D-06 | Internal | Quy chế quản lý thiết bị ban hành | BGĐ + VTTBYT + QLCL | Phase 04 | Open | Là input QMS Tier 1 |
| D-07 | Internal | Migration data steward được cử | VTTBYT | Phase 03 | Open | – |
| D-08 | Internal | Ngân sách Wave 2 phê duyệt | BGĐ + KTTC | Phase 09 | Open | Chỉ khóa khi UAT Wave 1 đạt |

## D. Quy trình quản lý

### Quản lý Risk
- **Mở**: bất kỳ ai trong team phát hiện → submit qua form Risk → PMO ghi nhận trong vòng 24h.
- **Đánh giá**: Risk Officer + owner trong vòng 3 ngày.
- **Mitigation**: chốt action trong 5 ngày.
- **Review**: Hàng tuần PMO; Cao escalate Steering.
- **Đóng**: Khi không còn trigger và mức về Thấp.

### Quản lý Issue
- Severity: Critical (block go-live), High, Medium, Low.
- Critical: SLA giải quyết 24h; cập nhật mỗi 4h cho Steering.
- High: 3 ngày làm việc.
- Medium/Low: theo backlog.

### Quản lý Dependency
- Mỗi dependency phải có "phải có trước phase X".
- Chậm > 50% timeline → tự động chuyển thành Risk.

## E. Phê duyệt baseline

| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| PMO |  |  |
| SA Lead |  |  |
| BA Lead |  |  |
| QMS Lead |  |  |
| Steering Chair |  |  |
