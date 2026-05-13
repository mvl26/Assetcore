# 09 — Release & User Guide (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | User guide + Release notes + Traceability |
| Owner | BA + Trainer + QLCL |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [08 Deployment](./08_Deployment.md) |

> Module thuộc **Đợt 3** (Architecture line 278). User guide tiếng Việt, target end-user là Workshop / Kho / KH-TC / DPO / QLCL / Trưởng phòng VT-TBYT.

---

## I. User guide (theo actor)

### I.1. HTM Engineer (Workshop / Tổ TBYT)

**Khi nào dùng**: nhận thông báo có Decommission Decision IMM-13 đã được duyệt, cần đóng vòng đời asset.

**Các bước**:

1. Đăng nhập, vào menu IMMIS → IMM-14 → "Tạo closure mới".
2. Chọn Decommission Decision (chỉ thấy decision đã Approved và chưa có closure).
3. Bấm "Tạo" → mở trang detail tab Reconciliation.
4. **Đóng các Work Order còn mở** (PM/CM/Calib): bấm "Đóng" hoặc "Transfer" cho từng dòng.
5. Báo Storekeeper xử lý phụ tùng tồn (mục B), Accountant ghi giá trị (mục C), QLCL archive hồ sơ (mục D).
6. Tab Sanitization: nếu asset có dữ liệu bệnh nhân (badge ❗), báo DPO vào ký.
7. Tab Documents: upload biên bản + ảnh hiện trạng.
8. Khi mọi dòng `done` → bấm "Submit for Approval".
9. Báo Trưởng phòng vào duyệt.

### I.2. Storekeeper (Kho)

1. Nhận notify khi closure tới state Reconciling, mở tab Reconciliation, mục B.
2. Mỗi dòng phụ tùng tồn → chọn `decision`:
   - **Reuse**: nhập kho lại làm phụ tùng tự do.
   - **Scrap**: huỷ, ghi note lý do.
   - **Transfer**: chuyển sang asset khác (chọn asset đích).
3. Bấm "Mark Done" cho từng dòng.

### I.3. Accountant (KH-TC / TCKT)

1. Mở mục C "Sổ tài sản" trong tab Reconciliation.
2. Đối chiếu `book_value` hệ thống với sổ tài sản kế toán.
3. Chọn `disposal_method` (disposal/donation/sale/trade-in/internal_reassignment).
4. Nhập `final_value` (giá trị thanh lý / điều chuyển).
5. Bấm "Mark Done".

Khi closure cần rollback (do TPP yêu cầu): nhận notify, mở closure → bấm "Confirm Rollback" hoặc "Reject".

### I.4. DPO / IT (CNTT)

Chỉ dùng khi asset có `has_patient_data = true`:

1. Mở tab Sanitization.
2. Check từng item theo SOP CNTT (xoá ổ cứng, reset config, gỡ login...).
3. Bấm "Ký xác nhận" — hệ thống ghi `signed_by` + timestamp.

### I.5. QLCL Officer

1. Mở mục D "Hồ sơ pháp lý" trong tab Reconciliation.
2. Verify danh sách IMM-05 docs còn `active` cho asset.
3. Mỗi doc → bấm "Mark archive-ready".
4. Tab Documents: kiểm biên bản đã upload đủ chưa (biên bản huỷ, biên bản giao nhận nếu donation).

Sau khi closure đã Closed: định kỳ xuất Closure Report PDF cho audit cuối năm.

### I.6. Department Head (Trưởng phòng VT-TBYT)

1. Nhận notify "Closure chờ duyệt".
2. Mở closure, kiểm tra summary.
3. Nếu OK → bấm "Approve", gõ closure_no xác nhận → asset chuyển `decommissioned`.
4. Nếu thiếu → bấm "Send back" + ghi note.

Rollback (trong vòng 30 ngày): mở closure đã Closed → "Request Rollback" + lý do → chờ Accountant confirm.

### I.7. Auditor

- Xem dashboard `/imm-14/dashboard` để có cái nhìn tổng quan end-of-life.
- Mở từng closure (read-only) để verify evidence cho audit.
- Xuất Closure Report PDF khi cần.

---

## II. Release notes

### v3.0.0-imm14-ga *(dự kiến cuối Đợt 3)*

**New features**:

- DocType mới: `IMM Asset Closure`, `IMM Reconciliation Line`, `IMM Sanitization Item`, `IMM Closure Document`.
- Workflow `IMM Asset Closure` 8 state với rollback có giới hạn thời gian.
- 10 endpoint REST (`/api/method/assetcore.api.imm14.*`).
- 4 trang UI: List · Create · Detail (4 tab) · Dashboard.
- Print Format Closure Report (A4 PDF) — 7 mục + 5 chỗ ký.
- Cron đối soát kho hàng tuần với IMM-15.
- Hook `imm14_asset_closed` cho IMM-15 / IMM-16 dashboard.
- Migration script cho legacy asset đã thanh lý trước go-live.

**Compliance evidence**:

- Closure record là chứng từ chính cho NĐ98/2021 thanh lý thiết bị.
- Sanitization PII/PHI có chữ ký DPO + timestamp đáp ứng NĐ13/2023.
- QC-IMMIS-04 đầy đủ artifact (PR/WI/BM/HS/KPI-DASH).

**Known limitations**:

- API tích hợp ERP tài chính chưa có — Accountant nhập `final_value` thủ công (giai đoạn sau).
- Mobile UI chưa optimize — chỉ desktop responsive.

**Breaking changes**: Không.

**Migration note**:

- Trước go-live, chạy patch `add_asset_has_patient_data` (default false). HTM Engineer review và bật flag cho asset có lưu trữ dữ liệu bệnh nhân (gợi ý: máy siêu âm, monitor, máy thở, X-quang số, CT/MRI).

---

## III. Traceability matrix

| Story | UC | BR | Endpoint | DocType | Test | QMS code |
|---|---|---|---|---|---|---|
| US-14-01 | UC-14-01 | BR-14-03 | `create_closure` | IMM Asset Closure | INT-14-06 | PR-IMMIS-14-01 |
| US-14-01 | UC-14-02 | — | `update_reconciliation` (scope=work_order) | IMM Reconciliation Line | INT-14-02 | PR-IMMIS-14-02 |
| US-14-02 | UC-14-03 | BR-14-05 | `sign_sanitization` | IMM Sanitization Item | INT-14-03 | PR-IMMIS-14-02, WI-14-02 |
| US-14-03 | UC-14-04 | BR-14-08 | `update_reconciliation` (spare_stock) | IMM Reconciliation Line | INT-14-04 | PR-IMMIS-14-02 |
| US-14-04 | UC-14-05 | — | `update_reconciliation` (book_value) | IMM Reconciliation Line | UAT-14-01 | PR-IMMIS-14-02 |
| US-14-05 | UC-14-06 | BR-14-07 | `update_reconciliation` (document) | IMM Reconciliation Line | INT-14-05 | PR-IMMIS-14-02 |
| US-14-05 | UC-14-07 | BR-14-01, 02 | `finalize` | IMM Asset Closure (submit) | INT-14-01, 07 | PR-IMMIS-14-03 |
| US-14-05 | UC-14-08 | BR-14-04 | `request_rollback`, `confirm_rollback` | IMM Asset Closure | INT-14-08, 09 | PR-IMMIS-14-03 |
| US-14-06 | UC-14-07 | — | (Print Format) | IMM Asset Closure | UAT-14-01 | BM-IMMIS-14-01, HS-REP-14-01 |
| US-14-07 | UC-14-09 | — | `list_closure` | (read-only) | (FE component test) | KPI-DASH-IMMIS-14 |
| US-14-07 | UC-14-10 | — | (CLI script) | IMM Asset Closure | UAT-14-04 | HS-REC-IMMIS-14-01 |

---

## IV. Đợt triển khai (Architecture line 278)

| Đợt | Module IMM-14 ở đâu | Điều kiện chuyển giai đoạn |
|---|---|---|
| Đợt 1 | KHÔNG (chỉ scope IMM-04, 05, 08, 09, 11, 12) | Asset registry + WO + dashboard cơ bản đã ổn |
| Đợt 2 | KHÔNG (chỉ scope IMM-01, 02, 03, 06, 15, 16) | QMS + spare parts + compliance scorecard đã ổn |
| **Đợt 3** ✅ | **IMM-14 cùng IMM-07, 10, 13, 17** | Đã có data lineage, chất lượng dữ liệu và cơ chế management review |

Điều kiện vào Đợt 3: Đợt 1 và Đợt 2 đã GA, IMM-15 đối soát ổn (nguồn input phụ tùng), IMM-13 deploy trước IMM-14 (cùng đợt nhưng IMM-13 phải sẵn sàng trước).

---

## V. Statistics (placeholder)

| Mục | Số liệu |
|---|---|
| LOC backend | *(Cập nhật mỗi release)* |
| LOC frontend | *(Cập nhật mỗi release)* |
| Số endpoint | 10 (theo [05](./05_API_Specification.md)) |
| Số DocType mới | 4 |
| Số role mới | 6 |
| Số test case | *(Cập nhật mỗi release)* |
| Coverage | ≥70% (CONVENTIONS §6) |

---

## VI. Tham chiếu

- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md` line 260, 278, 414, 425–430.
- WHO HTM: `../WHO/WHO - Decommissioning medical devices.md` §3.1, §3.2, §3.6, §3.8.
- GMDN: `../gmdn/Quyết định 3107_QĐ-BYT.md`, `Quyết định 69_QĐ-BYT.md`.
- BA: `../ba/Phase_04_Process_Workflow_Design`, `../ba/Phase_05_QMS_Governance_Design`.
- Skill: `assetcore-be-module`, `assetcore-fe-module`, `assetcore-doctype-designer`, `assetcore-workflow-builder`, `assetcore-htm-domain`, `assetcore-deployment`.

---

*Hết file 09. Release notes phiên bản kế tiếp append vào §II khi có hot-fix / iteration.*
