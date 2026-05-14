> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PROJECT CHARTER — ASSETCORE

**Mã dự án:** ASSETCORE-2026
**Phiên bản:** 1.0 — Baseline
**Ngày phát hành:** 2026-05-05
**Owner nghiệp vụ:** Phòng Vật tư – Trang thiết bị Y tế (VTTBYT)
**Owner kỹ thuật:** Phòng CNTT bệnh viện
**Sponsor:** Ban Giám đốc Bệnh viện
**Phương pháp triển khai:** Wave-based, ưu tiên 6 module IMM cốt lõi (Wave 1)

---

## 1. Bối cảnh

Bệnh viện đang vận hành >X.000 thiết bị y tế trải dài nhiều khoa/phòng/cơ sở. Việc quản lý hiện hữu chủ yếu dựa trên Excel, file giấy, các phần mềm rời rạc; không đồng nhất hồ sơ pháp lý, lịch sử PM/CM, hiệu chuẩn, recall, decommission. Hệ quả: thời gian chết tăng, chi phí sửa chữa khó kiểm soát, không truy vết được trách nhiệm, không đáp ứng được kiểm tra của Bộ Y tế / kiểm toán nội bộ / ISO 13485 / 15189 / JCI.

AssetCore được khởi tạo như một **operating architecture thống nhất** trên nền **ERPNext v15 / Frappe**, kết hợp logic HTM (Healthcare Technology Management) theo khung WHO/IMMIS với logic CMMS hiện đại, để quản lý toàn bộ vòng đời thiết bị y tế từ nhu cầu đầu tư đến giải nhiệm.

## 2. Mục tiêu dự án

### 2.1 Mục tiêu chiến lược (Strategic Outcomes)
- O1. Có **một hồ sơ sống** duy nhất cho từng thiết bị y tế từ "cradle to grave".
- O2. Bảo đảm **tuân thủ pháp lý và QMS** trên 100% thiết bị thuộc danh mục quản lý.
- O3. Giảm **downtime kế hoạch và ngoài kế hoạch** ≥ 30% sau Wave 1+2.
- O4. Tăng **tỉ lệ hoàn thành PM đúng hạn** lên ≥ 95%.
- O5. Cung cấp **dashboard điều hành** drill-down về record nguồn cho BGĐ và Ban điều hành thiết bị.
- O6. Sẵn sàng tích hợp HIS/EMR/LIS/RIS/PACS/BHYT/Tài chính trong vòng 24 tháng.

### 2.2 Mục tiêu vận hành (Operational Goals)
- G1. Triển khai 4 khối – 17 module IMM theo 3 wave trong 12–18 tháng.
- G2. Thiết kế tách bạch ERPNext core (lõi) và `assetcore` app (lớp HTM).
- G3. Mọi nghiệp vụ quan trọng đều có workflow + SLA + audit trail + bằng chứng số.
- G4. QMS chạy xuyên suốt (Document, CAPA, Compliance, Risk, Change Control).

## 3. Phạm vi (cao cấp — chi tiết tại 03_Scope_Statement)

**In scope (bắt buộc):**
- 4 khối IMM (A: Planning & Procurement | B: Deployment & Implementation | C: Operations & Maintenance | D: End-of-Life Management).
- 17 module IMM-01 → IMM-17.
- Engine trung tâm: Asset Registry, Lifecycle Event, Unified Work Order, Document/QMS, Compliance/CAPA/Audit, Metric/Dashboard.
- Đối tượng: tất cả thiết bị y tế thuộc danh mục quản lý của Phòng VTTBYT.

**Out of scope (Wave 1):**
- Tích hợp sâu HIS/EMR/LIS/RIS/PACS (chỉ thiết kế contract, build sau).
- Quản lý vật tư tiêu hao (chỉ liên kết, không thay thế module Stock của ERPNext).
- Tài sản ngoài thiết bị y tế (CNTT, hành chính, xe cộ…).

## 4. Tiêu chí thành công (Success Criteria)

| # | Tiêu chí | Đo lường | Ngưỡng đạt |
|---|----------|----------|------------|
| SC-01 | Hoàn thành Wave 1 (IMM-04, 05, 08, 09, 11, 12) | Số module nghiệm thu UAT | 6/6 |
| SC-02 | Migration thiết bị từ legacy | % thiết bị có hồ sơ đầy đủ | ≥ 95% |
| SC-03 | Workflow + audit trail | % nghiệp vụ quan trọng có audit trail | 100% |
| SC-04 | Drill-down dashboard | % KPI có lineage về record nguồn | 100% |
| SC-05 | Hồ sơ pháp lý số hóa | % thiết bị có giấy phép số hóa | ≥ 90% |
| SC-06 | Adoption | % work order tạo trên hệ thống (không qua giấy/Zalo) | ≥ 90% sau hypercare |
| SC-07 | QMS artifact | Số lượng artifact 4 tầng được phê duyệt | ≥ baseline tối thiểu cho Wave 1 |

## 5. Ràng buộc (Constraints)

- **C1 — Công nghệ:** ERPNext v15 / Frappe; ưu tiên cấu hình; chỉ custom khi core không đáp ứng đúng logic HTM/QMS.
- **C2 — Pháp lý:** Tuân thủ Thông tư/Nghị định Bộ Y tế VN về quản lý TTBYT, Nghị định 98/2021/NĐ-CP, Thông tư hướng dẫn liên quan.
- **C3 — Khung tham chiếu:** WHO HTM/IMMIS, ISO 13485, ISO 15189, IEC 62353, IEC 60601, JCI standards.
- **C4 — Hạ tầng:** Triển khai on-premise + DR site; hỗ trợ multi-site cho hệ thống bệnh viện vệ tinh.
- **C5 — Bảo mật:** RBAC; e-signature; audit log không thể xóa; phân vùng dữ liệu nhạy cảm.

## 6. Giả định (Assumptions)

- A1. Có đủ nguồn lực BA + SA + Dev + QA + QMS Officer cho cả vòng đời dự án.
- A2. Phòng VTTBYT cam kết cung cấp dữ liệu legacy ở định dạng có cấu trúc (Excel chuẩn hóa) trước migration.
- A3. Vendor chính của các thiết bị Wave 1 sẵn sàng cung cấp tài liệu kỹ thuật (manual, IQ/OQ/PQ template).
- A4. Có ngân sách cho hạ tầng DEV/UAT/STAGING/PROD và hợp đồng hỗ trợ Frappe/ERPNext.

## 7. Rủi ro chiến lược (Strategic Risks — chi tiết tại 05_Risk_Issue_Dependency_Log)

- R1. Kháng thay đổi từ kỹ thuật viên/khoa lâm sàng (mức Cao).
- R2. Dữ liệu legacy thiếu/sai → migration bị trễ (mức Cao).
- R3. Custom hóa quá nhiều → khó nâng cấp ERPNext về sau (mức Trung bình).
- R4. Thiếu QMS Officer chuyên trách → QMS engine không vận hành thực chất (mức Trung bình).
- R5. Phụ thuộc 1 vendor Frappe → bài toán kế thừa (mức Thấp–Trung bình).

## 8. Tổ chức dự án (cấp cao)

- **Steering Committee:** BGĐ + Trưởng VTTBYT + Trưởng CNTT + Trưởng QLCL.
- **Architecture Review Board:** SA Lead, BA Lead, IT Lead, QMS Lead.
- **Change Control Board:** PMO + ARB + Owner nghiệp vụ liên quan.
- **Project Team:** PM, BA, SA, Dev, QA, QMS Officer, Trainer, Migration Lead.

## 9. Mốc lớn (cấp cao)

| Mốc | Mô tả | Thời điểm dự kiến |
|-----|-------|-------------------|
| M0 | Charter ký, kickoff | T0 |
| M1 | Kết thúc Phase 01 (Discovery & BA) | T0 + 6 tuần |
| M2 | Kết thúc Phase 02–03 (Architecture + Data) | T0 + 12 tuần |
| M3 | Kết thúc Phase 04–07 (Process, QMS, UX, Integration design) | T0 + 18 tuần |
| M4 | Kết thúc Phase 08–10 (QA, Plan, Hand-off) | T0 + 22 tuần |
| M5 | Wave 1 build & UAT | T0 + 22 → 36 tuần |
| M6 | Wave 1 Go-live + Hypercare | T0 + 36 → 40 tuần |
| M7 | Wave 2 + 3 | T0 + 40 → 72 tuần |

## 10. Phê duyệt

| Vai trò | Họ tên | Chữ ký | Ngày |
|---------|--------|--------|------|
| Sponsor — BGĐ |  |  |  |
| Trưởng VTTBYT |  |  |  |
| Trưởng CNTT |  |  |  |
| Trưởng QLCL |  |  |  |
| PM dự án |  |  |  |

---

**Tham chiếu:** IMMIS CH1, AssetCore Blueprint, WHO HTM Framework, ERPNext v15 Documentation.
