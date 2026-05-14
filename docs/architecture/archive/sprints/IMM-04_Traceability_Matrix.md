# Traceability Matrix — Module IMM-04
# Lắp đặt, Định danh và Kiểm tra Ban đầu Thiết bị Y tế

**Phiên bản:** 1.0 | **Ngày:** 2026-04-15 | **Ban hành:** Tổ Kiến trúc AssetCore

---

## Quy ước ký hiệu

| Ký hiệu | Ý nghĩa |
|---|---|
| ✅ **COVERED** | Requirement được phủ đầy đủ — có Workflow, DocType, Rule và Test Case |
| ⚠️ **PARTIAL** | Requirement được phủ một phần — thiếu Rule hoặc Test Case |
| ❌ **GAP** | Requirement chưa được phủ — cần bổ sung thiết kế |

---

## Traceability Matrix Toàn bộ

| REQ ID | Mô tả Requirement (BA) | Workflow State | DocType | Field(s) | Rule/Validation | Test Case | KPI | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| **REQ-01** | Hệ thống phải cho phép lập phiếu tiếp nhận thiết bị mới từ PO | `Draft` | `Asset Commissioning` | `po_reference`, `master_item`, `vendor` | reqd=1 trên 3 trường; Link phải tồn tại | KB01-Step1, KB01-Step2 | — | ✅ COVERED |
| **REQ-02** | Hồ sơ CO, CQ bắt buộc phải có trước khi bàn giao | `Pending_Doc_Verify` | `Asset Commissioning` + `Commissioning Checklist` | `doc_type`, `is_mandatory`, `status` | VR-02: Chặn chuyển node nếu `mandatory=1` và `status=Missing` | KB01-Step4, UAT-TM-01 | — | ✅ COVERED |
| **REQ-03** | Thiếu tài liệu phụ (HDSD) chỉ cảnh báo, không chặn | `Pending_Doc_Verify` | `Asset Commissioning` | `manual_received` | VR-05: Soft Warning — `frappe.msgprint` | KB01-Step3 | — | ✅ COVERED |
| **REQ-04** | Điều kiện hạ tầng (điện, khí, đất) phải được xác nhận trước khi lắp | `To_Be_Installed` | `Asset Commissioning` (Child: Site Checklist) | `is_met`, `condition_name` | VR-06: Block nếu bất kỳ `is_met=0` với `is_critical=1` | KB02-Step3, KB02-Step4 | — | ✅ COVERED |
| **REQ-05** | Kỹ sư hãng log tiến độ lắp đặt, ghi nhận thời gian bắt đầu | `Installing` | `Asset Commissioning` | `installation_date`, `vendor_engineer_name` | `installation_date` auto-set = `now()` khi chuyển qua node | KB03-Step1 | **Avg Days to Install** | ✅ COVERED |
| **REQ-06** | Serial Number Hãng phải là duy nhất trên toàn hệ thống | `Identification` | `Asset Commissioning` | `vendor_serial_no` | VR-01: `frappe.db.exists("Asset", {"custom_vendor_serial": ...})` | UT-01, KB03-Step3 | — | ✅ COVERED |
| **REQ-07** | Bắt buộc dùng Barcode/QR, không được nhập tay Serial | `Identification` | `Asset Commissioning` | `vendor_serial_no`, `internal_tag_qr` | VR-08: Client Script lock keyboard tại field Serial | KB03-Step2 | — | ✅ COVERED |
| **REQ-08** | Hệ thống sinh mã định danh QR nội bộ bệnh viện | `Identification` | `Asset Commissioning` | `internal_tag_qr` | Auto-generate: `BV-{DEPT}-{YYYY}-{####}` | KB03-Step4 | — | ✅ COVERED |
| **REQ-09** | Phải có định danh đa lớp: SN Hãng, QR Nội bộ, Mã BYT | `Identification` | `Asset` (Custom Fields) | `custom_vendor_sn`, `custom_internal_qr`, `custom_moh_code` | Tất cả set khi Mint Asset; `custom_moh_code` optional | UT-01, KB03-Step4 | — | ⚠️ PARTIAL — `custom_moh_code` chưa có test case riêng |
| **REQ-10** | Kết quả đo kiểm an toàn điện phải được ghi đầy đủ | `Initial_Inspection` | `Commissioning Checklist` | `parameter`, `measured_val`, `test_result` | VR-03a: Tất cả rows phải có `test_result` trước khi Submit | KB04-Step1, KB04-Step2 | **First-Pass Rate** | ✅ COVERED |
| **REQ-11** | Khi tiêu chí rớt (Fail), bắt buộc ghi chú nguyên nhân | `Initial_Inspection` | `Commissioning Checklist` | `fail_note` | VR-03b: `if test_result==Fail and not fail_note: throw` | KB04-Step3, UT-03 | — | ✅ COVERED |
| **REQ-12** | Máy rớt test phải chuyển sang trạng thái chờ kiểm tra lại | `Initial_Inspection` → `Re_Inspection` | `Asset Commissioning` | `workflow_state` | State Machine: Nếu Fail → auto-push `Re_Inspection` | KB04-Step4 | — | ✅ COVERED |
| **REQ-13** | Thiết bị bức xạ phải có giấy phép Cục ATBXHN trước khi phát hành | `Clinical_Hold` | `Asset Commissioning` | `is_radiation_device`, `qa_license_doc` | VR-07: Auto-hold nếu `is_radiation=1`; Block release nếu `qa_license_doc` empty | UT-02, KB06-Step2 | — | ✅ COVERED |
| **REQ-14** | Không được phát hành nếu còn phiếu Non-Conformance chưa xử lý | `Clinical_Release` | `Asset Commissioning` + `Asset QA Non Conformance` | `resolution_status` | VR-04: `frappe.db.count("Asset QA NC", {ref=self.name, status=Open}) > 0` → throw | UT-02, UAT-WS-01 | — | ✅ COVERED |
| **REQ-15** | Chỉ PTP Khối 2 (VP_Block2) mới được phê duyệt phát hành | `Clinical_Release` | `Asset Commissioning` | `workflow_state` | Workflow Transition: `allow = VP_Block2` | KB05-Step1, UAT-K2-01 | — | ✅ COVERED |
| **REQ-16** | Sau khi phát hành, tự động tạo thẻ Tài sản trong ERPNext | `Clinical_Release` (on_submit) | `Asset` | `item_code`, `status`, `custom_comm_ref` | Hook `on_submit`: `frappe.get_doc("Asset").insert()` | KB05-Step3, INT-01 | — | ✅ COVERED |
| **REQ-17** | Tài sản sinh ra phải có liên kết ngược về phiếu Commissioning | Sau Submit | `Asset` | `custom_comm_ref` | `self.db_set('final_asset', new_asset.name)` sau Mint | INT-01 | — | ✅ COVERED |
| **REQ-18** | Dữ liệu không thể sửa sau khi phiếu đã được Submit | Sau `Clinical_Release` | `Asset Commissioning` | Tất cả fields | Frappe built-in: `docstatus=1` lock all fields | KB05-Step4, UAT-TM-02 | — | ✅ COVERED |
| **REQ-19** | KTV HTM không được tự phê duyệt phát hành | `Clinical_Release` | Role Permission | Workflow allow | Permission Matrix: HTM Tech Role không có quyền Submit | UAT-K2-01 | — | ✅ COVERED |
| **REQ-20** | Không cho phép tạo Asset trực tiếp, bắt buộc qua IMM-04 | Bất kỳ | `Asset` | — | Client Script: Disable nút New trên Asset List với các Role thường | UAT-K2-02 | — | ⚠️ PARTIAL — Chưa có Server-side guard, chỉ Client-side |
| **REQ-21** | Phải lưu Audit Trail khi chuyển trạng thái | Mọi chuyển State | `Asset Lifecycle Event` | `from_state`, `to_state`, `actor`, `timestamp` | Frappe Track Changes = 1; Event log bắn `imm04.*` | — | — | ⚠️ PARTIAL — Chưa có Test Case verify Audit Log cụ thể |
| **REQ-22** | Phải đo KPI Thời gian từ khi nhận thiết bị đến khi Release | Sau Release | Dashboard | `reception_date`, `release_date` | Công thức: `Avg(release_date - reception_date)` nhóm theo Vendor | — | **Avg Time to Release** | ⚠️ PARTIAL — KPI đã định nghĩa nhưng chưa có Report Query viết |
| **REQ-23** | Dashboard hiển thị số máy đang bị tạm giữ (Clinical Hold) | Mọi lúc | Dashboard Widget | `workflow_state = Clinical_Hold` | Query Count; Alert nếu > 5 máy | — | **Active Hold Count** | ⚠️ PARTIAL — Dashboard design OK nhưng chưa build Widget trên Frappe |
| **REQ-24** | Phiếu lỗi DOA phải có ảnh bằng chứng đính kèm | `Non_Conformance` | `Asset QA Non Conformance` | `damage_proof` | `reqd=1` trên field `damage_proof` khi `nc_type=DOA` | UAT-WS-01 | — | ✅ COVERED |
| **REQ-25** | Hệ thống gửi cảnh báo khi phiếu quá hạn SLA 7 ngày | Scheduled Job | `Asset Commissioning` | `expected_installation_date`, `installation_date` | Cronjob daily: Query quá hạn → Email Alert + Zalo webhook | — | **SLA Breach Count** | ⚠️ PARTIAL — Logic đã có, chưa có test cho Scheduler |

---

## Tổng kết Coverage

| Trạng thái | Số Requirement | Tỷ lệ |
|---|---|---|
| ✅ COVERED | 18 | 72% |
| ⚠️ PARTIAL | 7 | 28% |
| ❌ GAP | 0 | 0% |
| **TỔNG** | **25** | **100%** |

---

## Danh sách Gap cần xử lý trước Go-Live

| REQ ID | Vấn đề còn thiếu | Người chủ trì | Deadline |
|---|---|---|---|
| REQ-09 | Chưa có test case cho trường `custom_moh_code` (Mã BYT) | Dev + QA | Sprint 2 |
| REQ-20 | Cần thêm Server-side guard chống tạo Asset trực tiếp | Backend Dev | Sprint 2 |
| REQ-21 | Cần viết test case verify Audit Trail Log bị lock sau Submit | QA Lead | Sprint 3 |
| REQ-22 | Cần viết Report Query SQL cho KPI Avg Time to Release | Report Dev | Sprint 3 |
| REQ-23 | Cần build Dashboard Widget "Active Hold" trên Frappe Workspace | Frontend Dev | Sprint 3 |
| REQ-25 | Cần viết test case mô phỏng kịch bản Cronjob chạy quá hạn | QA Lead | Sprint 3 |
