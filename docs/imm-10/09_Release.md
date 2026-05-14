# IMM-10 — Release & User Guide

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Pre-release (BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> File này gom user guide tiếng Việt theo actor + traceability matrix + release notes template. Số liệu (LOC, # endpoint, # DocType) sẽ điền khi BE Sprint Wave 3 ship.

---

## I. User Guide tiếng Việt

### I.1 — Cho Tổ HC-QLCL (Compliance Officer)

**Mở Compliance Case từ vendor recall:**
1. Vào sidebar **Hậu kiểm → Compliance Cases → + Tạo mới**.
2. Chọn **Loại case** = `Recall`, **Mức độ** = `Critical` (nếu vendor đánh dấu Class C/D).
3. Điền **Số thông báo vendor** (`vendor_notice_no`) + đính kèm bản scan.
4. Nhập **Tiêu chí phạm vi**: model + lot range + serial range + ngày sản xuất.
5. **Submit Draft**.
6. Click **"Tìm phạm vi"** → hệ thống liệt kê asset bị ảnh hưởng. Review danh sách.
7. **Khoá phạm vi** → state chuyển `Disclosure Pending` (timer 48h bắt đầu).
8. Phối hợp Pháp chế gửi công văn → ấn **"Đã gửi công văn"** + log số công văn.
9. State chuyển `Action Pending` → click **"Tạo lệnh thu hồi hàng loạt"**.
10. Workshop thực thi WO → completion% tự cập nhật.
11. Khi 100%: ấn **"Đóng case"** → BGĐ phê duyệt.
12. 30/60/90 ngày sau: hệ thống nhắc effectiveness check.

**Theo dõi CAPA Tracker:**
- Vào **Hậu kiểm → CAPA Tracker**. Filter: severity, source module, status.
- CAPA quá hạn highlight đỏ — click vào để xem CAPA Record gốc.

### I.2 — Cho Pháp chế / Văn thư

1. Nhận thông báo email khi case ở `Disclosure Pending`.
2. Vào case → tab **Disclosure**.
3. Click **"Soạn công văn"** → template tự fill thông tin case.
4. Tải công văn xuống, ký, đóng dấu, gửi BYT (giấy hoặc cổng dịch vụ công).
5. Quay lại hệ thống, upload bản công văn đã ký + nhập **Số công văn**.
6. Click **"Đã gửi công văn"** → timer dừng.

### I.3 — Cho Workshop / Nhóm TBYT

1. Nhận WO Recall trong **PM Work Order** (nếu type=PM) hoặc **Asset Repair** (nếu type=Repair).
2. Trên WO có ref `case_ref` link tới Compliance Case — click để xem context.
3. Thực thi action theo `action_required` (Replace / Repair / Quarantine / Update Software).
4. Hoàn tất WO → completion% trên case tự cập nhật.

### I.4 — Cho BGĐ

1. Dashboard **Hậu kiểm** trên trang chủ — xem tóm tắt: # case mở, # case sắp breach, CAPA quá hạn.
2. Khi có yêu cầu phê duyệt close case → notification bell hiển thị.
3. Click vào case → review summary → ấn **"Phê duyệt đóng"**.
4. Trường hợp escalation (breach 48h): nhận notify trực tiếp + có thể can thiệp.

### I.5 — Cho khoa lâm sàng (Trưởng khoa)

1. Khi có recall ảnh hưởng thiết bị thuộc khoa, nhận notify nội bộ.
2. Vào case (chỉ đọc) — xem danh sách asset của khoa đang bị recall.
3. Stand-down các thiết bị (ngừng sử dụng) theo hướng dẫn nội bộ.
4. Sau khi Workshop xử lý xong, xác nhận tại từng asset → ký nhận trên hệ thống.

---

## II. Release Notes (template)

### v0.1.0 — Pre-release (planning)

- Khởi tạo bộ tài liệu IMM-10 (9 file): README, 02 Analysis & Design, 03 Diagrams, 04 Backend Design (skeleton), 05 API Specification (skeleton), 06 Frontend Design (skeleton), 07 Testing & QA (plan), 08 Deployment (plan), 09 Release (this file).
- Định danh phụ thuộc IMM-16 (Compliance Engine) — IMM-10 không tự định nghĩa Rule.

### v3.x.0 — GA (Sprint Wave 3, dự kiến)

*(Release notes thực tế viết khi ship code. Format mẫu:)*

```
## Backend
- DocType IMM Compliance Case + child tables (Affected Asset, Disclosure Log, Effectiveness Check)
- Workflow IMM-10 Compliance Workflow (8 states, N transitions)
- Service services/imm10.py với open_case / find_scope / bulk_create_recall_wo / close_case
- Scheduler: check_disclosure_breach (hourly), run_effectiveness_check (daily)
- Hook subscribe IMM-12/IMM-11 chronic failure signal

## Frontend
- View ComplianceDashboard, ComplianceCaseList, ComplianceCaseDetail
- DisclosureTimer component với countdown 48h
- CAPATracker view xuyên module

## Fixtures
- imm10_compliance_workflow.json, imm10_recall_action_template.json, imm10_sla_policy.json

## Migration
- Patch v3_x.imm10_create_compliance_case
- Patch v3_x.imm10_register_compliance_rules với IMM-16
```

---

## III. Traceability Matrix

| User Story | Business Rule | Use Case | Service Function | Endpoint | Test ID | Sprint |
|---|---|---|---|---|---|---|
| US-10-01 | BR-10-01 | UC-10-01 | `imm10.open_case` | POST `open_case` | U-01, U-02, UAT-IMM10-01 | Wave 3 / Sprint 1 |
| US-10-02 | BR-10-02 | UC-10-04 | `imm10.find_scope` | POST `find_scope` | U-03, U-04, I-03 | Wave 3 / Sprint 1 |
| US-10-03 | BR-10-01 | UC-10-05 | `imm10.send_disclosure` | POST `send_disclosure` | U-06, U-07, I-02, UAT-IMM10-03 | Wave 3 / Sprint 2 |
| US-10-04 | BR-10-03 | UC-10-06 | `imm10.bulk_create_recall_wo` | POST `bulk_create_recall_wo` | U-08, I-05, I-06 | Wave 3 / Sprint 2 |
| US-10-05 | — | UC-10-12 | `imm10.dashboard_summary` | GET `dashboard_summary` | (FE component test) | Wave 3 / Sprint 3 |
| US-10-06 | BR-10-07 | UC-10-10 | `imm10.run_effectiveness_check` | POST `run_effectiveness_check` | T-IDEM-04, UAT-IMM10-01 step 9 | Wave 3 / Sprint 4 |

(Sprint mapping refer Architecture line 278 — Đợt 3.)

---

## IV. Stat (placeholder)

| Metric | Giá trị |
|---|---|
| LOC backend (services/imm10.py) | *(Cập nhật mỗi release)* |
| LOC frontend (imm10) | *(Cập nhật mỗi release)* |
| # DocType mới | 5 dự kiến (Compliance Case + 3 child + Recall Action Template) |
| # Endpoint | ~13 dự kiến (refer §I.5) |
| # Workflow state | 8 dự kiến |
| # Test case | *(Cập nhật mỗi release)* |
| Coverage % | *(Cập nhật mỗi release — target ≥ 70% service)* |

---

## V. FAQ

**Q: Khác nhau giữa IMM-10 và IMM-16?**
A: IMM-16 là **engine compliance chung** (rule definition, internal audit, scorecard). IMM-10 **chuyên** về post-market: recall, FSCA, PMS signal, CAPA tracker xuyên module. IMM-10 đăng ký rule chuyên biệt vào IMM-16, không tự build engine.

**Q: Khi nào dùng PM Work Order vs Asset Repair cho recall?**
A: Action Replace / Quarantine / hardware swap → PM Work Order (IMM-08). Action Repair / Update Software / Update Setting → Asset Repair (IMM-09). Officer chọn lúc bulk-create.

**Q: Disclosure 48h tính từ khi nào?**
A: Từ `recall_confirmed_at` — thời điểm officer xác nhận case là regulatory-grade (không phải lúc nhận thông báo vendor).

**Q: Nếu vendor không cung cấp danh sách lot thì sao?**
A: Officer mở case với `vendor_notice_no` + scope rộng (chỉ model). Gửi công văn yêu cầu vendor. Cập nhật scope sau khi có lot list — nếu đã lock, mở case con.

**Q: CAPA tracker có thay thế DocType IMM CAPA Record không?**
A: Không. Tracker là **view aggregate** đọc từ `IMM CAPA Record` của các module khác (IMM-09/11/12/16). IMM-10 không sửa CAPA của module khác — chỉ filter và alert.

---

## VI. Tham chiếu

- **Architecture**: `../architecture/Ho_so_kien_truc_IMMIS.md` line 253, 278.
- **NĐ98/2021 + GMDN**: `../gmdn/Quyết định 3107_QĐ-BYT.md`, `Quyết định 69_QĐ-BYT.md`, `Quyết định 847_QĐ-BYT.md`.
- **Phase BA QMS**: `../ba/Phase_05_QMS_Governance_Design/05_Recall_FSCA_Workflow/`, `../ba/Phase_05_QMS_Governance_Design/03_CAPA_Workflow_Spec/`.
- **Cross-module**: [IMM-16](../imm-16/README.md), [IMM-12](../imm-12/README.md), [IMM-09](../imm-09/README.md), [IMM-11](../imm-11/README.md).
- **Skill build**: `.claude/skills/assetcore-be-module/`, `.claude/skills/assetcore-fe-module/`, `.claude/skills/assetcore-deployment/`.

---

*Cập nhật: 2026-05-10. Trạng thái: pre-release. Release notes thực tế viết Sprint Wave 3.*
