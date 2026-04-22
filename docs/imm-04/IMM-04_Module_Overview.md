# IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE — 31/32 UAT PASS |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-04 là **deployment gateway** trong vòng đời thiết bị y tế: từ lúc nhận hàng từ NCC → kiểm tra hồ sơ → lắp đặt thực tế → định danh nội bộ (QR + serial) → đo kiểm an toàn điện → tạm giữ lâm sàng (Class C/D/Radiation) → phê duyệt BGĐ → tạo `Asset` chính thức trên hệ thống.

Không có phiếu IMM-04 ở trạng thái `Clinical Release` (docstatus=1) thì **không có Asset record** và thiết bị không được phép sử dụng lâm sàng.

---

## 2. Vị trí trong kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│  IMM-03 (Procurement / PO)                                      │
│        │ po_reference                                           │
│        ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   IMM-04 — Asset Commissioning (deployment gateway)      │   │
│  │                                                          │   │
│  │   Workflow 11 states · 6 Gate · 7 VR · 8 BR             │   │
│  │   DocType: Asset Commissioning + 4 children              │   │
│  │   API:    assetcore/api/imm04.py    (17 endpoints)       │   │
│  │   Service:assetcore/services/imm04.py                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│        │ on_submit                                              │
│        ├──► ERPNext Asset (mint_core_asset)                     │
│        ├──► IMM-05 Asset Document Set (auto-import)             │
│        └──► IMM-08 PM Schedule (TODO — fire_release_event only) │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Asset Commissioning` | `IMM04-.YY.-.MM.-.#####` | Yes | Phiếu nghiệm thu thiết bị — workflow 11 states, gateway tạo Asset |

### 3.2 Child Tables (gắn vào Asset Commissioning)

| Child DocType | Parent field | Mục đích |
|---|---|---|
| `Commissioning Checklist` | `baseline_tests` | Lưới đo kiểm an toàn điện (parameter, measured_val, unit, test_result Pass/Fail/N/A, fail_note, is_critical) |
| `Commissioning Document Record` | `commissioning_documents` | Bảng kiểm hồ sơ CO/CQ/Manual/Warranty/License (status Pending/Received/Waived) |
| `Asset Lifecycle Event` | `lifecycle_events` | Audit trail bất biến — VR-06 (event_type, from_status, to_status, actor, event_timestamp, ip_address) |

### 3.3 DocType liên quan (độc lập, link qua field)

| DocType | Naming | Link |
|---|---|---|
| `Asset QA Non Conformance` | `NC-.YY.-.MM.-.#####` | `ref_commissioning` → Asset Commissioning |

---

## 4. Service Functions

File: `assetcore/services/imm04.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `initialize_commissioning(doc)` | `before_insert` (hooks.py) | Set `reception_date`, fetch `risk_class` từ Item, populate mandatory docs |
| `_populate_mandatory_documents(doc)` | internal | Pre-fill CO/CQ/Manual + License (C/D/Radiation) + Radiation License |
| `validate_commissioning(doc)` | wrapper | Chạy VR-01 → VR-06 + document expiry |
| `_vr01_unique_serial_number(doc)` | `validate()` | VR-01: vendor_serial_no unique trên Asset + Commissioning |
| `_vr05_risk_class_change_warning(doc)` | `validate()` | VR-05: cảnh báo nếu đổi risk_class sau Initial Inspection |
| `_vr06_immutable_lifecycle_events(doc)` | `validate()` | VR-06: block edit lifecycle_events row đã có |
| `_validate_document_expiry(doc)` | `validate()` | Throw nếu doc đã expired; warning < 30 ngày |
| `validate_gate_g01(doc)` | `validate()` | G01: 100% mandatory docs Received/Waived trước khi rời Pending Doc Verify |
| `validate_gate_g03(doc)` | `validate()` | G03: 100% baseline test Pass/N/A trước Clinical Release |
| `validate_gate_g05_g06(doc)` | `validate()` | G05: no Open NC; G06: bắt buộc `board_approver` trước Clinical Release |
| `check_auto_clinical_hold(doc)` | service + API | VR-07: trả True nếu risk_class ∈ {C,D,Radiation} → set `is_radiation_device=1` |
| `log_lifecycle_event(doc, event_type, from_status, to_status, remarks)` | controller hooks | Append immutable lifecycle event |
| `handle_commissioning_cancel(doc)` | `on_cancel` | Block cancel nếu `final_asset` đã tồn tại |
| `create_erpnext_asset(doc)` | `on_submit` | Mint ERPNext Asset record (alias `mint_core_asset` trong controller) |
| `check_commissioning_overdue()` | scheduler `daily` | Cảnh báo Workshop Head phiếu mở > 30 ngày |

Controller `asset_commissioning.py` cũng triển khai: `mint_core_asset()`, `create_initial_document_set()` (auto-import sang IMM-05), `_gw2_check_document_compliance()` (BR-07), `fire_release_event()` (publish_realtime + notify Purchase User), `_generate_internal_qr()` (sinh `BV-{DEPT}-{YYYY}-{SEQ}`).

---

## 5. Workflow States & Transitions

Workflow JSON: `assetcore/assetcore/workflow/imm_04_workflow.json` — `IMM-04 Workflow`.
`workflow_state_field = workflow_state`.

### 5.1 11 States

| State | doc_status | Type | allow_edit | Gate? |
|---|---|---|---|---|
| `Draft` | 0 | Success | System Manager | — |
| `Pending Doc Verify` | 0 | Warning | Biomed Engineer | G01 |
| `To Be Installed` | 0 | Success | Biomed Engineer | G02 (facility checklist) |
| `Installing` | 0 | Success | Biomed Engineer | — |
| `Identification` | 0 | Success | Biomed Engineer | VR-01 trigger |
| `Initial Inspection` | 0 | Success | Biomed Engineer | G03 |
| `Non Conformance` | 0 | Warning | Biomed Engineer | — |
| `Clinical Hold` | 0 | Warning | QA Officer | G04 |
| `Re Inspection` | 0 | Success | Biomed Engineer | — |
| `Clinical Release` | 1 | Success | System Manager | G05 + G06 (terminal positive) |
| `Return To Vendor` | 1 | Danger | System Manager | terminal negative |

### 5.2 Transition matrix (rút gọn)

| From → To | Action (vi) | Allowed Role |
|---|---|---|
| Draft → Pending Doc Verify | Gửi kiểm tra tài liệu | Biomed Engineer / CMMS Admin |
| Pending Doc Verify → To Be Installed | Xác nhận đủ tài liệu | Biomed Engineer |
| Pending Doc Verify → Draft | Yêu cầu bổ sung tài liệu | Biomed Engineer |
| To Be Installed → Installing | Bắt đầu lắp đặt | Biomed Engineer |
| To Be Installed → Non Conformance | Báo cáo sự cố | Biomed Engineer / Vendor Engineer |
| Installing → Identification | Lắp đặt hoàn thành | Biomed Engineer / Vendor Engineer |
| Installing → Non Conformance | Báo cáo DOA | Biomed Engineer / Vendor Engineer |
| Identification → Initial Inspection | Bắt đầu kiểm tra | Biomed Engineer |
| Initial Inspection → Clinical Release | Phê duyệt phát hành | System Manager / CMMS Admin |
| Initial Inspection → Clinical Hold | Giữ lâm sàng | QA Officer / CMMS Admin |
| Initial Inspection → Re Inspection | Báo cáo lỗi baseline | Biomed Engineer |
| Clinical Hold → Clinical Release | Gỡ giữ lâm sàng | QA Officer / CMMS Admin |
| Re Inspection → Clinical Release | Phê duyệt sau tái kiểm | System Manager / CMMS Admin |
| Non Conformance → To Be Installed | Khắc phục xong | Biomed Engineer |
| Non Conformance → Return To Vendor | Trả lại nhà cung cấp | System Manager |

---

## 6. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `assetcore.services.imm04.check_commissioning_overdue` | Daily | docstatus=0, không ở terminal state, reception_date > 30 ngày | Workshop Head (email) |
| `assetcore.tasks.check_clinical_hold_aging` | Daily | Phiếu Clinical Hold > N ngày → escalate | QA Officer |
| `assetcore.tasks.check_commissioning_sla` | Daily | SLA lắp đặt vi phạm | Workshop Head |

---

## 7. Roles & Permissions

| Role | Quyền trên Asset Commissioning |
|---|---|
| HTM Technician | Create / Read / Write |
| Biomed Engineer | Read / Write (không create, không submit) |
| Workshop Head | Read / Write=0 / Submit / Cancel / Amend / Print / Export |
| VP Block2 | Read / Submit / Cancel / Print / Export |
| QA Risk Team | Read / Write |
| QA Officer (workflow) | Edit ở state Clinical Hold; trigger transition `Giữ lâm sàng` / `Gỡ giữ lâm sàng` |
| Vendor Engineer (workflow) | Edit ở state Installing/To Be Installed; trigger DOA / Lắp đặt hoàn thành |
| System Manager / CMMS Admin (workflow) | Phê duyệt cuối — `Clinical Release` / `Return To Vendor` |

---

## 8. Business Rules

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-04-01 | Asset chỉ được tạo qua pipeline IMM-04 (`mint_core_asset` trong `on_submit`) | `AssetCommissioning.on_submit()` | ISO 13485 §7.5 |
| BR-04-02 (G01) | CO/CQ/Manual `is_mandatory=1` phải Received/Waived trước khi rời Pending Doc Verify | `validate_gate_g01()` | WHO HTM §3.4 |
| BR-04-03 (VR-01) | `vendor_serial_no` UNIQUE trên Asset + Commissioning | `validate_unique_serial()` + `_vr01_unique_serial_number()` | UDI / WHO HTM §5.1.2 |
| BR-04-04 (G03) | 100% baseline test Pass/N/A trước Clinical Release; nếu Fail → tự ép Re Inspection | `validate_checklist_completion()` + `validate_gate_g03()` | ISO 13485 §7.5.1 |
| BR-04-05 (VR-07) | Thiết bị bức xạ phải có `qa_license_doc` trước Clinical Release | `validate_radiation_hold()` | NĐ 142/2020 |
| BR-04-06 (VR-04) | No Open NC trước khi Release | `validate_gate_g05_g06()` + `block_release_if_nc_open()` | ISO 13485 §8.3 |
| BR-04-07 (G06) | `board_approver` bắt buộc trước Submit | `validate_gate_g05_g06()` | Quy trình BV |
| BR-04-08 (BR-07/GW-2) | Asset phải có Chứng nhận ĐKLH `Active` trong IMM-05 hoặc Exempt trước Submit | `_gw2_check_document_compliance()` | TT 46/2017/TT-BYT |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-03 (Purchase Order) | Nguồn dữ liệu | Field `po_reference` (Link → Purchase Order); API `get_po_details()` auto-fill |
| ERPNext Asset | Output | `mint_core_asset()` lưu vào `final_asset` (Link → Asset); custom fields `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref` |
| IMM-05 (Asset Document) | Output | `create_initial_document_set()` — graceful skip nếu Asset Document chưa tồn tại; GW-2 gate (BR-07) |
| IMM-08 (PM Schedule) | Output (TODO) | `fire_release_event()` publish realtime `imm04_asset_released` — listener IMM-08 chưa cài |
| IMM-12 / QMS | NC handoff | `Asset QA Non Conformance` có cờ `transfer_to_capa` |

---

## 10. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType + child tables | ✅ DONE | `IMM04-YY-MM-#####` naming |
| Workflow 11 states | ✅ DONE | `imm_04_workflow.json` active |
| API layer (17 endpoints) | ✅ DONE | `assetcore/api/imm04.py` |
| Service layer | ✅ DONE | `assetcore/services/imm04.py` |
| Validation VR-01 → VR-07 | ✅ DONE | Backend enforce |
| Gates G01 → G06 | ✅ DONE | Service + controller |
| Auto-mint Asset on Submit | ✅ DONE | `mint_core_asset()` |
| QR data generation | ✅ DONE | `generate_qr_label()` API + `_generate_internal_qr()` |
| QR PDF print template | ⚠️ PARTIAL | Frontend render OK; không có server-side PDF |
| Auto-import sang IMM-05 | ✅ DONE | `create_initial_document_set()` + graceful skip |
| GW-2 gate (BR-07) | ✅ DONE | `_gw2_check_document_compliance()` |
| PM auto-create (IMM-08) | ❌ TODO | Event fire OK, IMM-08 chưa có listener (UAT TC-32 FAIL) |
| Print Format Biên bản Bàn giao | ❌ TODO | API stub trả URL; chưa config Print Format |
| Dashboard KPIs | ✅ DONE | `get_dashboard_stats()` |
| UAT | ✅ 31/32 PASS | TC-32 (PM auto-create) FAIL |

---

## 11. Tài liệu liên quan

- `IMM-04_Functional_Specs.md` — yêu cầu nghiệp vụ, user stories, acceptance criteria
- `IMM-04_Technical_Design.md` — schema, validation impl, hooks, indexes
- `IMM-04_API_Interface.md` — 17 endpoints với request/response
- `IMM-04_UAT_Script.md` — 32 test cases (31 PASS / 1 FAIL)
- `IMM-04_UI_UX_Guide.md` — wireframes, routes, component specs

*End of Module Overview v2.0.0 — IMM-04*
