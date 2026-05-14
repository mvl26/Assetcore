> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# QMS ARTIFACT MATRIX (4 TẦNG) — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead

---

## 1. Khung 4 tầng

| Tier | Mã | Tên | Bản chất | Approver | Tần suất review |
|------|----|------|---------|----------|------------------|
| Tier 1 | QC | Quality Control / Chính sách / Quy chế | Định hướng chiến lược, ràng buộc cao | BGĐ + Trưởng QLCL | 1 năm |
| Tier 2 | PR/SOP | Procedure / Standard Operating Procedure | Quy trình chuẩn vận hành | Trưởng đơn vị + Trưởng QLCL | 1 năm |
| Tier 3 | WI/JD | Work Instruction / Job Description | Hướng dẫn công việc / mô tả vị trí | Trưởng đơn vị | 6 tháng |
| Tier 4 | BM/HS/KPI-DASH | Biểu mẫu / Hồ sơ / KPI-Dashboard | Bằng chứng vận hành | QMS Officer | 3 tháng |

## 2. Danh mục artifact baseline Wave 1

### 2.1 Tier 1 — QC

| ID | Tên | Owner | Mục đích |
|----|-----|-------|---------|
| QC-001 | Chính sách Quản lý Trang thiết bị Y tế | BGĐ | Định hướng tổng thể |
| QC-002 | Quy chế Quản lý Vòng đời Thiết bị HTM | BGĐ + VTTBYT | Khung quản trị |
| QC-003 | Chính sách Hệ thống Quản lý Chất lượng QMS | BGĐ + QLCL | Khung QMS |
| QC-004 | Chính sách Bảo mật và Quyền riêng tư dữ liệu | BGĐ + IT (ATTT) | Khung an toàn thông tin |
| QC-005 | Chính sách Quản lý Rủi ro thiết bị y tế | BGĐ + QLCL | Khung rủi ro |

### 2.2 Tier 2 — PR/SOP (Wave 1 cốt lõi)

| ID | Tên | Owner | Module IMM |
|----|-----|-------|------------|
| PR-001 | SOP Tiếp nhận, lắp đặt, định danh & kiểm tra ban đầu | VTTBYT + QMS | IMM-04 |
| PR-002 | SOP Quản lý hồ sơ pháp lý thiết bị | Pháp chế + VTTBYT + QMS | IMM-05 |
| PR-003 | SOP Bảo trì định kỳ (PM) | VTTBYT | IMM-08 |
| PR-004 | SOP Sửa chữa, phụ tùng, cập nhật phần mềm | VTTBYT | IMM-09 |
| PR-005 | SOP Hiệu chuẩn | VTTBYT + QMS | IMM-11 |
| PR-006 | SOP Bảo trì khắc phục (CM) | VTTBYT | IMM-12 |
| PR-007 | SOP Quản lý CAPA | QMS | toàn hệ thống |
| PR-008 | SOP Recall / FSCA | QMS + Pháp chế | toàn hệ thống |
| PR-009 | SOP Quản lý thay đổi (Change Control) | QMS + IT | toàn hệ thống |
| PR-010 | SOP Quản lý hồ sơ Tài liệu QMS (Document Control) | QMS | toàn hệ thống |
| PR-011 | SOP Stand-down / Decommission / Disposal | VTTBYT + QMS + KTTC + Pháp chế | IMM-13/14 (Wave 2) |
| PR-012 | SOP Quản lý hợp đồng dịch vụ thiết bị | Procurement + VTTBYT | toàn hệ thống |
| PR-013 | SOP Quản lý sự cố thiết bị (Adverse Event / Vigilance) | QMS + Pháp chế | IMM-10 |
| PR-014 | SOP Đào tạo người dùng thiết bị y tế | QMS + Khoa | IMM-06 |
| PR-015 | SOP Backup / Restore / DR cho hệ thống AssetCore | IT | toàn hệ thống |

### 2.3 Tier 3 — WI/JD

| ID | Tên | Owner |
|----|-----|-------|
| WI-001 | WI Quét QR + Báo hỏng trên mobile | VTTBYT |
| WI-002 | WI Thực hiện PM checklist trên mobile | VTTBYT |
| WI-003 | WI Thực hiện hiệu chuẩn nội bộ | Cal Lab Eng |
| WI-004 | WI Sử dụng AssetCore cho QMS Officer | QMS |
| WI-005 | WI Phê duyệt Document trên hệ thống | QMS + Pháp chế |
| WI-006 | WI Phát hành QR/RFID cho thiết bị mới | VTTBYT |
| WI-007 | WI Cấu hình PM Plan mới | KS BME |
| WI-008 | WI Cấu hình Calibration Plan | KS BME / Cal Lab |
| WI-009 | WI Mở Failure Report cho người dùng cuối | VTTBYT (training) |
| WI-010 | WI Vận hành SLA monitor | IT |
| JD-001 | JD Trưởng phòng VTTBYT (cập nhật phần liên quan AssetCore) | HR |
| JD-002 | JD Kỹ sư BME | HR |
| JD-003 | JD Kỹ thuật viên thiết bị | HR |
| JD-004 | JD QMS Officer | HR |
| JD-005 | JD Calibration Lab Engineer | HR |
| JD-006 | JD Spare Warehouse Officer | HR |
| JD-007 | JD Vendor Service Engineer (External) | VTTBYT |

### 2.4 Tier 4 — BM/HS/KPI-DASH

| ID | Tên | Owner |
|----|-----|-------|
| BM-001 | Biểu mẫu Báo hỏng thiết bị | VTTBYT |
| BM-002 | Biểu mẫu PM checklist (per Device Model) | VTTBYT |
| BM-003 | Biểu mẫu Cal Certificate template | Cal Lab |
| BM-004 | Biểu mẫu Biên bản lắp đặt | VTTBYT |
| BM-005 | Biểu mẫu IQ/OQ/PQ | VTTBYT + QMS |
| BM-006 | Biểu mẫu Stand-down | VTTBYT |
| BM-007 | Biểu mẫu Decommission đánh giá kỹ thuật | VTTBYT + QMS |
| BM-008 | Biểu mẫu Disposal/Donation | KTTC + Pháp chế |
| BM-009 | Biểu mẫu Đào tạo + competency | QMS + HR |
| BM-010 | Biểu mẫu Recall response per asset | QMS |
| BM-011 | Biểu mẫu CAPA template | QMS |
| BM-012 | Biểu mẫu Change Control Request | QMS + IT |
| HS-001 | Hồ sơ thiết bị (asset profile) | VTTBYT |
| HS-002 | Hồ sơ pháp lý thiết bị | Pháp chế |
| HS-003 | Hồ sơ PM/CM/Cal lịch sử | VTTBYT |
| KPI-DASH-001 | KPI PM Compliance Rate | VTTBYT |
| KPI-DASH-002 | KPI Cal Compliance Rate | QLCL |
| KPI-DASH-003 | KPI Avg MTTR | VTTBYT |
| KPI-DASH-004 | KPI Downtime hours | VTTBYT |
| KPI-DASH-005 | KPI License expiring | Pháp chế |
| KPI-DASH-006 | KPI CAPA aging | QMS |
| KPI-DASH-007 | KPI Recurring failures | VTTBYT |
| KPI-DASH-008 | KPI Vendor SLA breach | Procurement |
| KPI-DASH-009 | KPI Adoption rate WO | PMO |
| KPI-DASH-010 | KPI License expired & in-use | QMS + Pháp chế |

(25 KPI Wave 1 → mỗi KPI nên có 1 Tier 4 artifact với metric definition + dashboard ref.)

## 3. Quan hệ mỗi artifact ↔ DocType

| Artifact | DocType liên quan |
|----------|--------------------|
| QC-001..005 | Áp dụng toàn hệ thống — không gắn DocType cụ thể |
| PR-001 | AC Medical Asset, AC IQ-OQ-PQ Record, AC Document Record |
| PR-002 | AC Document Record (LEGAL) |
| PR-003 | AC PM Plan, AC Work Order (PM) |
| PR-004 | AC Work Order (CM), AC Software Update Record |
| PR-005 | AC Calibration Plan, AC Calibration Record |
| PR-006 | AC Failure Report, AC Work Order (CM) |
| PR-007 | AC NC, AC CAPA |
| PR-008 | AC Compliance Case (Recall) |
| PR-009 | AC Change Control Request |
| PR-010 | AC Document Record, AC QMS Artifact |
| BM-002 | AC Work Order Task template |
| BM-005 | AC IQ-OQ-PQ Record |
| KPI-DASH-* | AC Metric Definition + AC Dashboard Widget |

## 4. Approval chain (lấy từ Phase_04 §3.5)

| Tier | Workflow |
|------|----------|
| Tier 1 | Author → Trưởng đơn vị → Trưởng QLCL → BGĐ |
| Tier 2 | Author → Trưởng đơn vị → Trưởng QLCL |
| Tier 3 | Author → Trưởng đơn vị |
| Tier 4 | Author → QMS Officer |

## 5. Versioning + Periodic Review
- Tier 1/2: review tối thiểu 1 năm.
- Tier 3: 6 tháng.
- Tier 4: 3 tháng.
- Khi có change đáng kể → CR qua CCB → publish phiên bản mới → obsolete cũ.

## 6. Training requirements
- Mọi PR/SOP yêu cầu training. QMS Artifact `training_required=true`.
- Training tracking với `AC Training Record`.
- Compliance dashboard: % completed.

## 7. Mapping với chuẩn quốc tế
- ISO 13485 §4.2: Document Control + Records.
- ISO 9001 §7.5: Documented information.
- WHO HTM Framework: alignment với guidance documents.
- JCI: FMS, MMU (đối với loại thiết bị áp dụng).

## 8. Tiêu chí nghiệm thu Wave 1
- 5 QC + 15 PR/SOP + 17 WI/JD + ~30 BM/HS/KPI-DASH baseline đã có draft.
- Tất cả Tier 1/2 baseline được approved trước go-live Wave 1.
- Tier 3/4 active đầy đủ cho người dùng được training.
- Training compliance ≥ 80% cho role chính trước go-live.
