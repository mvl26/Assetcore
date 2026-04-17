# IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu

## Module Overview

IMM-04 quản lý toàn bộ quá trình đưa thiết bị y tế vào vận hành: từ lúc nhận hàng từ nhà cung cấp, kiểm tra tài liệu, lắp đặt thực tế, định danh nội bộ (QR/serial), đo kiểm an toàn điện, đến khi phê duyệt chính thức và tạo Asset record trên hệ thống. Module là gateway bắt buộc — không có phiếu IMM-04 được Submit, thiết bị không tồn tại trong hệ thống và không được phép sử dụng lâm sàng.

---

## Trạng thái Implementation

| Feature | Status | Ghi chú |
|---|---|---|
| DocType `Asset Commissioning` + child tables | DONE | Đầy đủ fields, naming `ACC-YYYY-#####` |
| Workflow 11 states (Frappe Workflow Engine) | DONE | `imm_04_workflow.json` active |
| API layer (`assetcore/api/imm04.py`) | DONE | 17 endpoints |
| Service layer (`assetcore/services/imm04.py`) | DONE | Tách khỏi controller |
| Validation rules VR-01 đến VR-07 | DONE | Backend enforce |
| Gate G01 — G06 | DONE | Gate logic trong service + controller |
| Auto-mint Asset on Submit | DONE | `mint_core_asset()` |
| QR code — data generation | DONE | `generate_qr_label()` API |
| QR code — print label UI | PARTIAL | Frontend render; không có PDF template server-side |
| Auto-import docs sang IMM-05 | DONE | `create_initial_document_set()`, graceful skip nếu IMM-05 chưa deploy |
| GW-2 compliance gate (IMM-05 check) | DONE | `_gw2_check_document_compliance()` |
| PM schedule auto-create (IMM-08) | TODO | `fire_release_event()` bắn event nhưng chưa trigger IMM-08 |
| PDF Biên bản Bàn giao (Print Format) | TODO | API stub `generate_handover_pdf()` trả URL, nhưng Print Format chưa config |
| Dashboard KPIs | DONE | `get_dashboard_stats()` |
| UAT | 31/32 PASS | 1 case còn thiếu: PM schedule auto-create |

---

## Lifecycle Position

```
IMM-01 (Planning) → IMM-02 (Budget) → IMM-03 (Procurement / PO)
                                              |
                                              v
                                    [IMM-04 Installation]
                                              |
                              +--------------+--------------+
                              v                             v
                       IMM-05 (Document Set)        IMM-08 (PM Schedule)
                              |
                              v
                    IMM-07→12 (Operations: PM, Repair, Calibration...)
                              |
                              v
                    IMM-13→14 (End-of-Life / Decommission)
```

IMM-04 là **deployment gateway**: nhận input từ PO (IMM-03), output là Asset record + trigger IMM-05 + IMM-08.

---

## Workflow States (11 states)

| State | Tên hiển thị | Gate? | Điều kiện vào | Điều kiện ra |
|---|---|---|---|---|
| `Draft` | Nháp | — | Tạo mới | Gửi kiểm tra tài liệu |
| `Pending Doc Verify` | Chờ kiểm tài liệu | G01 | Biomed Engineer submit | Tài liệu bắt buộc (CO, CQ, Manual) đã nhận |
| `To Be Installed` | Chờ lắp đặt | G02 | G01 passed | Bắt đầu lắp đặt hoặc báo sự cố |
| `Installing` | Đang lắp đặt | — | Biomed/Vendor Engineer xác nhận | Hoàn thành lắp hoặc báo DOA |
| `Identification` | Định danh | — | Lắp xong | Gán serial + QR, bắt đầu kiểm tra |
| `Initial Inspection` | Kiểm tra ban đầu | G03 | Định danh xong | Baseline test 100% Pass/N/A |
| `Clinical Hold` | Tạm giữ lâm sàng | G04 | QA Officer giữ (Class C/D/Radiation) | Upload giấy phép BYT/ATBX |
| `Re Inspection` | Tái kiểm | — | Baseline có Fail row | Tái kiểm và Pass |
| `Non Conformance` | Không phù hợp | — | DOA hoặc lỗi nghiêm trọng | Khắc phục xong hoặc trả vendor |
| `Clinical Release` | Phát hành lâm sàng | G05+G06 | NC đã đóng hết + Board Approver ký | Submit → tạo Asset |
| `Return To Vendor` | Trả lại nhà cung cấp | — | NC không khắc phục được | Terminal state |

**Roles tham gia:** Biomed Engineer, Vendor Engineer, QA Officer, CMMS Admin, System Manager, VP Block2, Workshop Head.

---

## DocTypes

### Asset Commissioning (primary)

DocType name: `Asset Commissioning` | Naming: `ACC-YYYY-#####`

| Field | Loại | Bắt buộc | Mô tả |
|---|---|---|---|
| `po_reference` | Link → Purchase Order | Y | PO nguồn |
| `master_item` | Link → Item | Y | Model thiết bị |
| `vendor` | Link → Supplier | Y | Nhà cung cấp |
| `clinical_dept` | Link → Department | Y | Khoa/phòng nhận |
| `expected_installation_date` | Date | Y | Ngày hẹn lắp |
| `vendor_serial_no` | Data | Y | Serial NSX — unique toàn hệ thống (VR-01) |
| `internal_tag_qr` | Data | — | QR nội bộ: `BV-{DEPT}-{YYYY}-{SEQ}` |
| `custom_moh_code` | Data | — | Mã BYT |
| `risk_class` | Select | — | A / B / C / D / Radiation |
| `is_radiation_device` | Check | — | Auto-sync từ risk_class |
| `installation_date` | Datetime | — | Auto-set khi vào state Installing |
| `overall_inspection_result` | Select | — | Pass / Fail |
| `final_asset` | Link → Asset | — | Asset được tạo khi Submit |
| `board_approver` | Link → User | — | G06: người phê duyệt BGĐ |
| `qa_license_doc` | Attach | — | Giấy phép BYT/Cục ATBXHN |
| `handover_doc` | Attach | — | Biên bản bàn giao |
| `baseline_tests` | Table | Y | Child: Commissioning Checklist |
| `commissioning_documents` | Table | — | Child: Commissioning Document Record |
| `lifecycle_events` | Table | — | Child: Asset Lifecycle Event (immutable) |

### Child Tables

| DocType | Mô tả | Key fields |
|---|---|---|
| `Commissioning Checklist` | Lưới đo kiểm an toàn điện | parameter, measured_val, unit, test_result (Pass/Fail/N/A), fail_note, is_critical |
| `Commissioning Document Record` | Bảng kiểm hồ sơ | doc_type, is_mandatory, status (Pending/Received/Waived), file_url, expiry_date |
| `Asset QA Non Conformance` | Phiếu NC — độc lập, link qua `ref_commissioning` | nc_type (DOA/Other), severity, description, resolution_status, root_cause, corrective_action |
| `Asset Lifecycle Event` | Audit trail bất biến — VR-06 | event_type, from_status, to_status, actor, event_timestamp, ip_address |

---

## Business Rules (BR-04-01 to BR-04-08)

| BR | Rule | Control |
|---|---|---|
| BR-04-01 | Mỗi thiết bị phải có PO hợp lệ (docstatus=1) | Validate trước khi insert |
| BR-04-02 (G01) | CO, CQ, Manual phải Received/Waived trước khi lắp đặt | `validate_gate_g01()` service |
| BR-04-03 (VR-01) | Vendor Serial Number unique toàn hệ thống | Check Asset + Commissioning table |
| BR-04-04 (G03) | 100% baseline test Pass hoặc N/A trước khi Release | `validate_checklist_completion()` |
| BR-04-05 (VR-07) | Thiết bị bức xạ phải có giấy phép BYT trước khi Release | `validate_radiation_hold()` |
| BR-04-06 (VR-04) | Không được Release nếu còn NC chưa đóng | `block_release_if_nc_open()` + G05 |
| BR-04-07 (G06) | Bắt buộc Board Approver ký trước khi Submit | `validate_gate_g05_g06()` service |
| BR-04-08 (BR-07) | GW-2: Thiết bị phải có Chứng nhận ĐKLH trong IMM-05 | `_gw2_check_document_compliance()` |

---

## API Endpoints

Module: `assetcore.api.imm04`

| # | Method | Endpoint | Mô tả |
|---|---|---|---|
| 1 | GET | `get_form_context?name=` | Document đầy đủ + workflow state + allowed transitions |
| 2 | GET | `list_commissioning` | Paginated list với filters |
| 3 | POST | `create_commissioning` | Tạo phiếu mới |
| 4 | POST | `save_commissioning` | Inline edit (top-level fields + child table rows) |
| 5 | POST | `transition_state` | Thực hiện workflow action (permission-checked) |
| 6 | POST | `submit_commissioning` | Submit phiếu (chỉ VP Block2 / Workshop Head) |
| 7 | POST | `approve_clinical_release` | Board approval: validate G05+G06, mint Asset, trigger IMM-05/08 |
| 8 | GET | `get_dashboard_stats` | KPIs: pending, hold, NC open, released this month, overdue SLA |
| 9 | GET | `generate_qr_label?name=` | QR data + label payload để frontend render |
| 10 | GET | `get_barcode_lookup?barcode=` | Tra cứu thiết bị theo QR nội bộ hoặc serial NSX |
| 11 | GET | `get_po_details?po_name=` | Auto-fill vendor/model khi chọn PO |
| 12 | GET | `search_link` | Autocomplete cho Link fields (PO, Item, Supplier, Department) |
| 13 | POST | `assign_identification` | Gán serial + QR + mã BYT (state Identification) |
| 14 | GET | `check_sn_unique?vendor_sn=` | Kiểm tra serial trùng (on-blur validation) |
| 15 | POST | `submit_baseline_checklist` | KTV nộp kết quả đo kiểm, validate BR-04-04 |
| 16 | POST | `clear_clinical_hold` | QA Officer gỡ Clinical Hold sau khi upload giấy phép |
| 17 | POST | `report_nonconformance` | Tạo NC record (BR-04-06) |
| 18 | POST | `report_doa` | Báo DOA: tạo Critical NC + transition Non Conformance |
| 19 | POST | `upload_document` | Upload file cho document record row |
| 20 | POST | `close_nonconformance` | Đóng NC với root_cause + corrective_action |
| 21 | POST | `generate_handover_pdf` | Xuất URL PDF Biên bản Bàn giao (Print Format) |

**Response format chuẩn:** `{"success": true, "data": ...}` hoặc `{"success": false, "error": "...", "code": "ERROR_CODE"}`

---

## Integration Points

```
IMM-03 (PO)
    └─[po_reference]──► IMM-04 Asset Commissioning
                              │
                    on_submit (docstatus=1)
                              │
              ┌───────────────┼───────────────┐
              v               v               v
        ERPNext Asset    IMM-05 Draft     IMM-08 PM
        (mint_core_asset) (document set)  (TODO: trigger)
              │
         [final_asset]
              │
        IMM-07→12 (Work Orders)
        IMM-13→14 (Decommission)
```

| Từ | Sang | Cơ chế |
|---|---|---|
| IMM-03 / Purchase Order | IMM-04 | `po_reference` field; `get_po_details()` auto-fill |
| IMM-04 on_submit | ERPNext Asset | `mint_core_asset()` → lưu vào `final_asset` |
| IMM-04 on_submit | IMM-05 Asset Document | `create_initial_document_set()` — auto-import documents Received |
| IMM-04 state=Clinical Release | IMM-05 GW-2 check | `_gw2_check_document_compliance()` block submit nếu thiếu ĐKLH |
| IMM-04 on_submit | IMM-08 PM Schedule | `fire_release_event()` bắn realtime event; **PM auto-create chưa implement** |
| IMM-04 NC record | QMS / CAPA | `Asset QA Non Conformance` — link `ref_commissioning` |

---

## Known Gaps / TODO

| Gap | Mức độ | Ghi chú |
|---|---|---|
| IMM-08 PM schedule auto-create | HIGH | `fire_release_event()` bắn event nhưng IMM-08 chưa có listener; UAT case 32 FAIL |
| PDF Print Format "Biên bản Lắp đặt Nghiệm thu" | MEDIUM | API `generate_handover_pdf()` có nhưng Print Format chưa config trong Frappe |
| G04: Clinical Hold auto-transition (Class C/D/Radiation) | MEDIUM | Hiện tại QA Officer tự chuyển; chưa auto-detect sau Initial Inspection |
| QR code label — print template | LOW | Frontend render OK; không có server-side PDF template cho nhãn QR |
| Workflow state naming consistency | LOW | Code dùng cả `Clinical_Release` (underscore) và `Clinical Release` (space) — cần chuẩn hóa |
| SLA enforcement | LOW | `overdue_sla` tính trong dashboard nhưng không có auto-escalation |

---

## QMS Compliance

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Audit trail bất biến | ISO 13485 §4.2.5 | `lifecycle_events` table — VR-06 block edit |
| Serial number tracking (UDI) | WHO HTM / NĐ98 | `vendor_serial_no` unique (VR-01) + `internal_tag_qr` |
| Phân loại rủi ro thiết bị | NĐ 98/2021/NĐ-CP | `risk_class` (A/B/C/D/Radiation) + Clinical Hold cho Class C/D |
| Giấy phép bức xạ | NĐ 142/2020/NĐ-CP | `qa_license_doc` bắt buộc (VR-07) trước khi Release |
| Chứng nhận đăng ký lưu hành | TT 46/2017/TT-BYT | GW-2 gate (BR-07/BR-08) — check IMM-05 trước Submit |
| Non-conformance management | ISO 13485 §8.3 | `Asset QA Non Conformance` + close workflow bắt buộc (VR-04) |
| Board approval trước đưa vào sử dụng | Quy trình BV | `board_approver` bắt buộc (G06) |

---

## Tài liệu liên quan

- `IMM-04_Functional_Specs.md` — chi tiết nghiệp vụ, user stories, acceptance criteria
- `IMM-04_Technical_Design.md` — ERD, service layer design, gate logic
- `IMM-04_API_Interface.md` — OpenAPI spec đầy đủ với request/response examples
- `IMM-04_UAT_Script.md` — 32 test cases, kết quả 31/32 PASS
- `IMM-04_UI_UX_Guide.md` — wireframes, component specs, frontend flow
