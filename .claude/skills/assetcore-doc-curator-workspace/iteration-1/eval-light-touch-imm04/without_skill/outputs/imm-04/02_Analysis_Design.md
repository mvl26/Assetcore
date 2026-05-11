# 02 — Phân tích thiết kế nghiệp vụ (Analysis & Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | BA + System Analyst |
| Liên kết | 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Phân tích nghiệp vụ end-to-end — module overview, quy trình BPMN, use case UML, functional specs (user stories + AC + business rules). Đây là hợp đồng giữa BA và Dev.

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng

**As-Is — Trước khi có hệ thống:** Tại phần lớn bệnh viện Việt Nam, quá trình lắp đặt và nghiệm thu thiết bị y tế được thực hiện qua sổ giấy, file Excel hoặc email rời rạc. KTV nhận máy từ kho vật tư, tự photo hồ sơ CO/CQ, ghi số serial bằng tay vào sổ tài sản. Không có quy trình định danh nội bộ chuẩn hóa (mã QR / mã nội bộ). Kết quả đo kiểm an toàn điện ghi vào biên bản giấy, dễ thất lạc. Thiếu gate kiểm soát bắt buộc trước khi thiết bị đưa vào sử dụng lâm sàng — Class C/D không nhất thiết qua QA sign-off.

**Hạn chế chính:** (1) Không audit trail — không biết ai đã phê duyệt gì, khi nào. (2) Không ràng buộc pháp lý tự động — thiết bị bức xạ vào vận hành mà chưa có giấy phép. (3) Serial number không kiểm tra unique — trùng lặp phát sinh gây nhầm lẫn tài sản. (4) Không có kết nối sang hệ thống tài chính / bảo trì — asset record phải nhập tay sau đó.

## I.1. Pitch

IMM-04 là **deployment gateway** bắt buộc trong vòng đời thiết bị y tế tại AssetCore. Mọi thiết bị từ khi nhận hàng từ nhà cung cấp đều phải đi qua pipeline 11 bước: tiếp nhận → kiểm tra hồ sơ → lắp đặt → định danh (QR + serial) → đo kiểm an toàn điện → kiểm duyệt lâm sàng → phê duyệt BGĐ → tạo Asset chính thức. Không có phiếu IMM-04 ở trạng thái `Clinical Release` thì thiết bị không được phép sử dụng và không có bản ghi Asset trên hệ thống — đảm bảo 100% traceability từ ngày đầu.

## I.2. Vị trí trong WHO HTM lifecycle

| Phase | Có liên quan? | Ghi chú |
|---|---|---|
| Needs Assessment | — | Đầu vào từ IMM-01/02 |
| Procurement | ✅ INPUT | Nhận PO từ IMM-03 (`po_reference`) |
| Installation & Commissioning | ✅ CORE | Toàn bộ pipeline lắp đặt, định danh, kiểm tra |
| Operation | ✅ OUTPUT | Tạo Asset record, auto-import sang IMM-05 |
| Maintenance | ✅ OUTPUT | `fire_release_event` trigger IMM-08 PM schedule |
| Decommission | — | Asset record được tạo ở đây, kết thúc ở IMM-13 |

IMM-04 nhận input từ **IMM-03** (PO), sản xuất output cho **IMM-05** (hồ sơ tài liệu), **IMM-08** (lịch PM), và toàn bộ các module operation thông qua `Asset` record.

## I.3. Stakeholders & Actors

| Vai trò | Người dùng thực | Quan tâm chính | Tần suất | Loại |
|---|---|---|---|---|
| HTM Technician | KTV HTM phòng kỹ thuật | Tạo phiếu nhanh, điền đủ hồ sơ | Hàng tuần | Primary |
| Biomed Engineer | Kỹ sư Biomedical | Gán serial/QR, đo kiểm baseline | Hàng tuần | Primary |
| Vendor Engineer | KTV NCC (Philips, GE…) | Xác nhận lắp đặt, khai báo DOA | Theo dự án | Primary |
| QA Officer | Tổ HC-QLCL | Cấp phép bức xạ, Clinical Hold | Khi có thiết bị nguy cơ cao | Approver |
| Workshop Head | Trưởng phân xưởng | Submit/Cancel, quản lý overdue | Hàng tuần | Approver |
| VP Block2 | Phó Trưởng Khối 2 | Ký duyệt cuối, nhận báo cáo | Theo sự vụ | Approver |
| CMMS Admin | IT/CMMS | Override workflow, cấu hình | Khi cần | Secondary |
| Purchase User | Kế toán tài sản | Nhận thông báo kích hoạt khấu hao | Passive | Secondary |
| System Auditor | Kiểm toán nội bộ / BYT | Xem lịch sử bất biến, kiểm tra compliance | Định kỳ | Auditor |

## I.4. Scope

**In-scope:**
- DocType `Asset Commissioning` + 4 child tables + `Asset QA Non Conformance`
- Workflow 11 states + 22 transitions + 6 Gates (G01–G06) + 7 Validation Rules (VR-01 → VR-07)
- 31 REST endpoint (`assetcore/api/imm04.py`) — bao gồm gate status, approval flow, purchase linkage
- Auto-mint `Asset` record khi Submit (`mint_core_asset`)
- Auto-import sang IMM-05 (`create_initial_document_set`)
- GW-2 compliance gate (BR-07)
- Sinh QR data nội bộ (`BV-{DEPT}-{YYYY}-{SEQ}`)
- Dashboard KPIs, scheduler cảnh báo phiếu overdue

**Out-of-scope:**
- PM Schedule auto-create (IMM-08 — `fire_release_event` đã bắn, listener chưa cài)
- PDF Print Format Biên bản Bàn giao (stub trả URL)
- QR label PDF template server-side
- Auto-detect Clinical Hold sau Initial Inspection (QA Officer trigger thủ công)
- SLA email tự động (dashboard hiện overdue)

**Assumptions:**
- PO từ IMM-03 đã tồn tại và hợp lệ trước khi tạo phiếu
- `Item.custom_risk_class` và `Item.custom_is_radiation` đã được điền trên master data
- Role và User Permission đã được cấu hình đúng trước khi go-live

**Dependencies:**
- IMM-03 (Purchase Order): `po_reference` Link
- ERPNext Asset DocType: custom fields `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`
- IMM-05 (Asset Document): GW-2 gate query
- IMM-08 (PM Schedule): listener chưa implement
- Frappe Workflow Engine, `frappe.publish_realtime`

## I.5. KPI mục tiêu

| KPI | Định nghĩa | Baseline | Target | Đo ở đâu |
|---|---|---|---|---|
| KPI-04-01: Tỷ lệ phiếu hoàn thành đúng hạn | % phiếu đạt Clinical Release trong 30 ngày từ `reception_date` | Không đo được (As-Is) | ≥ 85% | `get_dashboard_stats().overdue_sla` |
| KPI-04-02: Tỷ lệ serial không trùng | % phiếu vào Identification mà `vendor_serial_no` unique ngay lần đầu | N/A | 100% | VR-01 block count |
| KPI-04-03: Tỷ lệ baseline test Pass lần đầu | % phiếu Initial Inspection không cần Re Inspection | Không đo được | ≥ 90% | Lifecycle event counter |
| KPI-04-04: Thời gian xử lý trung bình | Trung bình ngày từ Draft → Clinical Release | ~15 ngày (ước tính) | ≤ 10 ngày | Calculated field |
| KPI-04-05: % audit trail đầy đủ | Phiếu có đủ lifecycle event cho mọi transition | 0% (sổ giấy) | 100% | VR-06 + lifecycle_events count |

## I.6. Ràng buộc Compliance

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| NĐ 98/2021/NĐ-CP | Thiết bị Y tế phải có Chứng nhận ĐK lưu hành trước khi sử dụng lâm sàng (GW-2 gate) | Điều 28-32 |
| NĐ 142/2020/NĐ-CP | Thiết bị bức xạ phải có Giấy phép trước khi đưa vào hoạt động (VR-07, Clinical Hold) | Điều 25-27 |
| WHO HTM 2025 | Commissioning checklist, document receipt, clinical sign-off bắt buộc | §3.4, §5.1.2 |
| ISO 13485:2016 | Device record phải có audit trail, NC phải closed trước release (G05) | §7.5, §8.3 |
| TT 46/2017/TT-BYT | Đăng ký lưu hành TBYT (Chứng nhận ĐKLH `Active` hoặc Exempt) | Điều 5-7 |
| QĐ 3107/QĐ-BYT | Phân loại rủi ro TBYT A/B/C/D — quyết định gate Clinical Hold (VR-07 với Class C/D) | `docs/gmdn/Quyết định 3107_QĐ-BYT.md` |

**Source documents tham chiếu (read-only):**
- WHO HTM lifecycle / Commissioning: `docs/WHO/WHO - Inventory and maintenance 2025.md`, `docs/WHO/WHO - Introduction to medical equipment inventory management.md`
- WHO Maintenance programme: `docs/WHO/WHO - Medical equipment maintenance programme overview.md`
- Phân loại GMDN / risk class: `docs/gmdn/Quyết định 3107_QĐ-BYT.md`, `docs/gmdn/Quyết định 69_QĐ-BYT.md`, `docs/gmdn/Quyết định 847_QĐ-BYT.md`
- Kiến trúc tổng: `docs/architecture/Ho_so_kien_truc_IMMIS.md`

## I.7. Risk & Open questions

**Risk:**

| Risk | Likelihood | Impact | Giảm thiểu |
|---|---|---|---|
| Race condition trên `vendor_serial_no` | Low | Medium | Thêm DB UNIQUE constraint (tech-debt) |
| `mint_core_asset` không rollback khi IMM-05 import fail | Medium | Medium | Wrap try/except + savepoint (tech-debt) |
| PM auto-create không hoạt động (UAT TC-32 FAIL) | High | Medium | Track in backlog; IMM-08 implement listener |
| Mixed naming `Clinical Release` vs `Clinical_Release` | Low | Low | Chuẩn hóa trong sprint kế tiếp |
| Print Format Biên bản chưa config | Medium | Low | Config Frappe Print Format trước go-live |

**Open questions:**

| Câu hỏi | Owner | Deadline |
|---|---|---|
| IMM-08 listener cho `imm04_asset_released` — sprint nào? | Tech Lead IMM-08 | Sprint 8 |
| Chuẩn hóa `Clinical Release` (space) vs `Clinical_Release` (underscore)? | Tech Lead | Sprint 7 |
| PDF Biên bản Bàn giao — cần config Print Format trong Frappe? | Workshop Head + BA | Sprint 7 |

## I.8. Roadmap thực thi

| Sprint | Hạng mục | Owner | Status |
|---|---|---|---|
| Sprint 4 | DocType schema + Workflow 11 states | BE Dev | ✅ DONE |
| Sprint 5 | Service layer VR-01 → VR-07 + Gates G01-G06 | BE Dev | ✅ DONE |
| Sprint 5 | API layer 17 endpoints (nay 31) | BE Dev | ✅ DONE |
| Sprint 6 | Frontend Vue 3 list/detail/form | FE Dev | ✅ DONE |
| Sprint 6 | QR data generation + barcode lookup | BE Dev | ✅ DONE |
| Sprint 7 | Print Format Biên bản Bàn giao | BA + BE Dev | ⚠️ TODO |
| Sprint 7 | Chuẩn hóa workflow state naming | Tech Lead | ⚠️ TODO |
| Sprint 7 | DB UNIQUE constraint cho `vendor_serial_no` | DBA | ⚠️ TODO |
| Sprint 8 | IMM-08 listener `imm04_asset_released` | BE Dev IMM-08 | ❌ TODO |
| Sprint 9 | Rollback transaction `mint_core_asset` | BE Dev | ❌ TODO |

---

# Phần II — Quy trình nghiệp vụ (Business Process / BPMN)

## II.1. Phân biệt 3 khái niệm

| Khái niệm | Mục đích | Phạm vi trong file này |
|---|---|---|
| **BPMN / Business Process** | Mô tả luồng nghiệp vụ end-to-end giữa các vai trò (As-Is / To-Be) | §II.2–II.9 — flowchart Mermaid + RACI |
| **Use Case (UML)** | Mô tả tương tác giữa Actor và hệ thống ở góc nhìn chức năng | §III — UC diagram + UC spec |
| **Activity Diagram** | Mô tả luồng điều khiển bên trong 1 use case (gates / decisions) | §II.10 — per UC chính |

Quy ước: BPMN trả lời "ai làm gì khi nào trong quy trình", Use Case trả lời "hệ thống cung cấp chức năng gì cho ai", Activity Diagram trả lời "khi thực thi UC, các bước rẽ nhánh ra sao".

## II.2. As-Is process

Trước khi có IMM-04, bệnh viện tiếp nhận thiết bị theo quy trình thủ công: nhận hàng → ký biên bản giấy → KTV tự ghi sổ serial → lắp đặt → điền form đo kiểm giấy → họp nghiệm thu → nhập tay vào sổ tài sản. Không có gate check bắt buộc, không có audit trail tự động.

```mermaid
flowchart TD
    subgraph NCC["Nhà Cung Cấp"]
        A1[Giao hàng + hồ sơ giấy]
    end
    subgraph KTV["KTV / Biomed"]
        A1 --> B1[Ký biên bản giấy]
        B1 --> B2[Ghi serial vào sổ]
        B2 --> B3[Lắp đặt thực tế]
        B3 --> B4[Đo kiểm giấy]
    end
    subgraph BGD["BGĐ / QA"]
        B4 --> C1[Họp nghiệm thu thủ công]
        C1 --> C2[Ký duyệt biên bản]
    end
    subgraph KeToan["Kế toán"]
        C2 --> D1[Nhập tài sản vào sổ kế toán]
    end
```

## II.3. Pain points

| # | Pain | Tác động |
|---|---|---|
| 1 | Serial number ghi tay dễ nhầm / trùng lặp | Nhầm tài sản, không truy xuất được lịch sử bảo trì |
| 2 | Không gate cho thiết bị bức xạ | Rủi ro pháp lý nghiêm trọng (NĐ 142/2020) |
| 3 | Không audit trail — không biết ai ký gì, khi nào | Không đáp ứng kiểm toán nội bộ / BYT |
| 4 | Hồ sơ CO/CQ/Manual thất lạc sau nghiệm thu | Không có tài liệu khi bảo hành / bảo trì |
| 5 | Tạo tài sản trong hệ thống kế toán phụ thuộc con người | Trễ, sai sót, không đồng bộ |

## II.4. To-Be process (với AssetCore)

```mermaid
flowchart TD
    subgraph NCC["Nhà Cung Cấp / Vendor Eng"]
        A1[Giao hàng] --> A2[Xác nhận lắp đặt hoàn thành]
        A2 --> A3{DOA?}
        A3 -->|Có| A4[Báo cáo DOA → NC]
    end
    subgraph KTV["HTM Technician / Biomed Engineer"]
        B1[Tạo phiếu từ PO] --> B2[Kiểm tra hồ sơ CO/CQ/Manual]
        B2 -->|G01 Pass| B3[Chuyển To Be Installed]
        B3 --> B4[Bắt đầu lắp đặt]
        B4 --> B5[Gán Serial + sinh QR nội bộ]
        B5 --> B6[Đo kiểm an toàn điện baseline]
        B6 -->|G03 Pass| B7[Chuyển Clinical Release]
        B6 -->|Fail| B8[Re Inspection]
        B8 --> B6
    end
    subgraph QA["QA Officer"]
        B7 --> C1{Class C/D/Radiation?}
        C1 -->|Có| C2[Trigger Clinical Hold]
        C2 --> C3[Upload giấy phép BYT]
        C3 --> C4[Gỡ Hold]
        C1 -->|Không| D1
        C4 --> D1
    end
    subgraph BGD["Workshop Head / VP Block2"]
        D1[Phê duyệt Clinical Release]
        D1 -->|G05+G06 Pass| D2[Submit → Clinical Release]
    end
    subgraph System["Hệ thống"]
        D2 --> E1[Mint Asset record]
        E1 --> E2[Auto-import sang IMM-05]
        E2 --> E3[Publish imm04_asset_released]
        F1[Lifecycle Event auto-log] -.auto.-> B1
        F1 -.auto.-> B5
        F1 -.auto.-> D2
    end
    A4 --> B4
```

## II.5. Decision points

| Điểm | Câu hỏi | Quy tắc |
|---|---|---|
| G01 — Doc gate | CO/CQ/Manual đã đủ? | 100% `is_mandatory=1` docs phải Received hoặc Waived |
| G02 — Facility gate | Cơ sở hạ tầng đạt? | `facility_checklist_pass=1` trước Installing |
| G03 — Baseline gate | Kết quả đo kiểm đạt? | 100% Pass/N/A; nếu Fail → Re Inspection |
| G04 — Clinical Hold | Class nguy cơ cao? | risk_class ∈ {C, D, Radiation} → QA phải upload license |
| G05 — NC gate | Còn NC chưa đóng? | resolution_status="Open" bất kỳ → block Release |
| G06 — Board approver | Đã chỉ định BGĐ ký? | `board_approver` bắt buộc trước Submit |

## II.6. Process metrics

| Metric | Mục tiêu | Đo ở đâu |
|---|---|---|
| Thời gian Draft → Clinical Release | ≤ 10 ngày | `reception_date` → `commissioning_date` |
| % phiếu overdue (>30 ngày) | ≤ 5% | Dashboard `overdue_sla` |
| % audit trail coverage | 100% | Lifecycle event count per phiếu |
| % baseline pass lần đầu | ≥ 90% | Count Re Inspection occurrences |

## II.7. RACI matrix

| Hoạt động | HTM Tech | Biomed | Vendor Eng | QA Officer | Workshop Head | VP Block2 | CMMS Admin |
|---|---|---|---|---|---|---|---|
| Tạo phiếu từ PO | R | A | — | — | C | — | C |
| Kiểm tra hồ sơ (G01) | R | A | — | — | C | — | — |
| Gán serial/QR | — | R/A | C | — | — | — | — |
| Đo kiểm baseline | — | R/A | C | — | — | — | — |
| Clinical Hold | — | I | — | R/A | C | — | C |
| Upload giấy phép | — | C | — | R/A | — | — | — |
| Phê duyệt cuối | — | — | — | C | R | A | — |
| Submit phiếu | — | — | — | — | R | A | — |
| Kiểm toán | I | I | — | I | I | I | I |

## II.8. Exception flow

**Exception 1 — DOA (Dead-on-Arrival):** KTV phát hiện máy hỏng khi khui hộp ở trạng thái Installing. KTV gọi `report_doa()` → tạo NC với `nc_type=DOA`, severity=Critical → phiếu chuyển Non Conformance → nếu không sửa được → Return To Vendor. NCC phải xác nhận trước khi đóng case.

**Exception 2 — Amend sau Cancel:** Nếu phiếu bị Cancel (chỉ cho phép ở Draft, Non Conformance, Return To Vendor), Workshop Head amend bản mới. Lưu ý: không cancel được nếu `final_asset` đã tồn tại.

**Exception 3 — Risk class change:** Nếu KTV thay đổi `risk_class` sau trạng thái Initial Inspection, hệ thống báo VR-05 warning nhưng không block. QA Officer cần xem xét lại việc có cần Clinical Hold hay không.

## II.9. So sánh As-Is vs To-Be

| Khía cạnh | As-Is | To-Be (AssetCore) |
|---|---|---|
| Audit trail | Sổ giấy, email | Lifecycle Event bất biến, tự động per transition |
| Serial unique | Không kiểm tra | VR-01 enforce cross-table |
| Gate bức xạ | Không có | VR-07 + Clinical Hold + G04 |
| Tạo Asset record | Nhập tay kế toán | Auto-mint on Submit |
| Hồ sơ tài liệu | Thất lạc | Auto-import sang IMM-05 |
| Thời gian xử lý | ~15 ngày (ước tính) | Target ≤ 10 ngày |

## II.10. Activity diagram per UC chính

### UC-04-01: Tạo phiếu từ PO

```mermaid
flowchart TD
    Start([Bắt đầu]) --> A[KTV chọn PO hợp lệ]
    A --> B[Hệ thống auto-fill vendor, item, risk_class]
    B --> C[KTV điền clinical_dept, expected_installation_date]
    C --> D{PO tồn tại và hợp lệ?}
    D -->|Không| Err1[Báo lỗi NOT_FOUND]
    D -->|Có| E[Populate mandatory docs CO/CQ/Manual]
    E --> F{risk_class ∈ C/D/Radiation?}
    F -->|Có| G[Thêm row License mandatory]
    F -->|Không| H
    G --> H[Set reception_date = today]
    H --> I[Insert Doc workflow_state=Draft]
    I --> J[Log lifecycle event created]
    J --> End([Phiếu tạo thành công])
    Err1 --> End
```

### UC-04-05: Gán Serial + sinh QR

```mermaid
flowchart TD
    Start([Bắt đầu]) --> A[Biomed nhập vendor_serial_no]
    A --> B[Gọi check_sn_unique on blur]
    B --> C{SN đã tồn tại?}
    C -->|Có| Err[Hiện lỗi VR-01 inline]
    Err --> A
    C -->|Không| D[Gọi assign_identification]
    D --> E{State = Identification?}
    E -->|Không| Err2[Lỗi INVALID_STATE]
    E -->|Có| F[Sinh internal_tag_qr = BV-DEPT-YYYY-SEQ]
    F --> G[Log lifecycle event Identification]
    G --> H[Hiển thị QR label + nút in]
    H --> End([Hoàn thành])
```

---

# Phần III — Use Case Specification (UML)

## III.1. Use Case Diagram

### III.1.a. Biểu đồ use case tổng quát

```plantuml
@startuml
left to right direction
actor "HTM Technician" as TECH
actor "Biomed Engineer" as BIO
actor "Vendor Engineer" as VENDOR
actor "QA Officer" as QA
actor "Workshop Head" as WH
actor "VP Block2" as VP
actor "System Scheduler" as SCH <<system>>

rectangle "IMM-04 Asset Commissioning" {
    usecase "UC-01 Tạo phiếu từ PO" as UC01
    usecase "UC-02 Kiểm tra hồ sơ (G01)" as UC02
    usecase "UC-03 Lắp đặt thực tế" as UC03
    usecase "UC-04 Gán Serial + QR" as UC04
    usecase "UC-05 Đo kiểm baseline (G03)" as UC05
    usecase "UC-06 Clinical Hold / Release" as UC06
    usecase "UC-07 Phê duyệt cuối + Submit" as UC07
    usecase "UC-08 Báo NC / DOA" as UC08
    usecase "UC-09 Đóng NC" as UC09
    usecase "UC-10 Xem dashboard" as UC10
    usecase "UC-11 Sinh QR label" as UC11
    usecase "UC-12 Barcode lookup" as UC12
}

TECH --> UC01
TECH --> UC08
BIO --> UC02
BIO --> UC03
BIO --> UC04
BIO --> UC05
BIO --> UC11
VENDOR --> UC03
VENDOR --> UC08
QA --> UC06
WH --> UC07
VP --> UC07
SCH --> UC10
UC07 ..> UC01 : <<include>>
UC05 ..> UC06 : <<extend>> [risk_class C/D/Rad]
UC08 ..> UC09 : <<include>>
@enduml
```

## III.2. Actor catalog

| Actor | Loại | Mô tả | Goal chính |
|---|---|---|---|
| HTM Technician | Primary | KTV phòng kỹ thuật HTM | Tạo và theo dõi phiếu, upload hồ sơ |
| Biomed Engineer | Primary | Kỹ sư Biomedical | Lắp đặt, định danh, đo kiểm |
| Vendor Engineer | Primary | KTV nhà cung cấp | Xác nhận lắp đặt, khai báo DOA |
| QA Officer | Approver | Tổ HC-QLCL | Clinical Hold, cấp phép bức xạ |
| Workshop Head | Approver | Trưởng phân xưởng | Submit, quản lý overdue |
| VP Block2 | Approver | Phó Trưởng Khối 2 | Phê duyệt cuối cùng |
| System Scheduler | System | Frappe scheduler | Check overdue, SLA alert |

## III.3. Use Case Specifications

### UC-01: Tạo phiếu Commissioning từ PO

| Mục | Giá trị |
|---|---|
| ID | UC-IMM04-01 |
| Brief | Tạo phiếu Asset Commissioning mới từ 1 PO hợp lệ |
| Primary actor | HTM Technician / Biomed Engineer |
| Pre-condition | PO tồn tại, user có role HTM Technician hoặc Biomed Engineer |
| Post-condition | Phiếu ở Draft, mandatory docs pre-populated, lifecycle event ghi nhận |
| Trigger | KTV nhấn "Tạo phiếu mới" và chọn PO |

#### Main flow
| Bước | Actor | System |
|---|---|---|
| 1 | Chọn PO từ dropdown | Gọi `get_po_details` auto-fill vendor, item |
| 2 | Điền clinical_dept, expected_installation_date | Validate date không là quá khứ xa |
| 3 | Nhấn Lưu / Tạo | Gọi `create_commissioning`, set `reception_date=today`, populate docs |
| 4 | — | Trả `name = ACC-YY-MM-#####`, `workflow_state=Draft` |
| 5 | — | Log lifecycle event `commissioning_created` |

#### Alternative A1 — PO có nhiều item
- 1a. Hệ thống hiện dropdown chọn item từ PO items list
- 1b. KTV chọn 1 item; phiếu tạo cho item đó

#### Exception E1 — PO không tồn tại
- 3a. Hệ thống trả `NOT_FOUND` — "Không tìm thấy PO. Vui lòng kiểm tra lại."

### UC-04: Gán Serial Number + sinh QR

| Mục | Giá trị |
|---|---|
| ID | UC-IMM04-04 |
| Brief | Biomed Engineer gán vendor serial và sinh mã QR nội bộ |
| Primary actor | Biomed Engineer |
| Pre-condition | Phiếu ở state `Identification` |
| Post-condition | `vendor_serial_no` unique, `internal_tag_qr` được sinh |
| Trigger | Phiếu vào state Identification sau khi lắp đặt xong |

#### Main flow
| Bước | Actor | System |
|---|---|---|
| 1 | Quét barcode hoặc nhập SN | Gọi `check_sn_unique` on-blur |
| 2 | — | Kiểm tra UNIQUE (VR-01) trả `is_unique=true/false` |
| 3 | Nhấn "Xác nhận định danh" | Gọi `assign_identification` |
| 4 | — | Sinh `internal_tag_qr = BV-{DEPT}-{YYYY}-{SEQ}` |
| 5 | — | Log lifecycle event `identification_assigned` |
| 6 | — | Hiển thị nút "Sinh QR label" → `generate_qr_label` |

#### Exception E1 — Serial trùng
- 2a. Hệ thống hiện inline error "VR-01: Serial đã được gán cho phiếu ACC-..."

## III.4. Use Case relationships

**`<<include>>`:**
| Caller UC | Included UC | Lý do |
|---|---|---|
| UC-07 Phê duyệt cuối | UC-01 Tạo phiếu | Phiếu phải tồn tại |
| UC-08 Báo NC/DOA | UC-09 Đóng NC | NC tạo ra phải được đóng |

**`<<extend>>`:**
| Base UC | Extension UC | Điều kiện |
|---|---|---|
| UC-05 Đo kiểm baseline | UC-06 Clinical Hold | risk_class ∈ {C, D, Radiation} |

## III.5. UC ↔ User Story mapping

| Use Case | US ID | Note |
|---|---|---|
| UC-01 | US-04-01 | Tạo từ PO hợp lệ |
| UC-04 | US-04-02 | VR-01 block SN trùng |
| UC-02 (G01) | US-04-03 | Block khi thiếu CO |
| UC-05 (G03) | US-04-04 | Baseline Fail → Re Inspection |
| UC-06 (VR-07) | US-04-05 | Auto Clinical Hold |
| UC-07 (G05+G06) | US-04-06, US-04-07 | Block release + Submit sinh Asset |
| UC-08 (DOA) | US-04-08 | Khai báo DOA |

## III.6. UC ↔ Sequence Diagram mapping

| Use Case | Sequence Diagram | File |
|---|---|---|
| UC-01 Tạo phiếu từ PO | SD-04-01 Tạo phiếu từ PO — Happy path | `03_Diagrams.md` §III.3 |
| UC-07 Submit → Mint Asset | SD-04-02 Submit phiếu → Mint Asset | `03_Diagrams.md` §III.3 |
| UC-04 Assign Identification (VR-01) | SD-04-03 SN trùng → block | `03_Diagrams.md` §III.3 |

UC còn lại (UC-02/03/05/06/08) không cần sequence diagram riêng — luồng đơn giản, đã mô tả đủ trong Activity Diagram §II.10.

---

# Phần IV — Functional Specifications

## IV.1. User Stories & Acceptance Criteria

### US-04-01 — Tạo phiếu từ PO
**Là HTM Technician, tôi muốn tạo phiếu nghiệm thu từ PO, để bắt đầu quy trình lắp đặt có kiểm soát.**
- Priority: Must | Estimate: 3 SP

**AC-01 (Given-When-Then):**
- Given: tôi có role HTM Technician, PO-2026-00023 tồn tại
- When: tôi POST `create_commissioning` với `{po_reference, master_item, vendor, clinical_dept, expected_installation_date}`
- Then: response.success=true, data.name khớp `ACC-\d{2}-\d{2}-\d{5}`, workflow_state=Draft, mandatory docs pre-populated

**AC-02:**
- Given: risk_class=C trên Item
- When: phiếu tạo
- Then: row "License" mandatory xuất hiện trong `commissioning_documents`

### US-04-02 — VR-01 block serial trùng
**Là Biomed Engineer, tôi muốn hệ thống cảnh báo ngay khi nhập serial trùng, để tránh nhầm lẫn tài sản.**
- Priority: Must | Estimate: 2 SP

**AC-01:**
- Given: ACC-A đã có `vendor_serial_no = "SN-12345"`
- When: tôi nhập "SN-12345" vào ACC-B và blur khỏi field
- Then: inline error "VR-01: Serial 'SN-12345' đã được gán cho phiếu ACC-A"

**AC-02:**
- Given: SN mới chưa có trong hệ thống
- When: tôi blur
- Then: không có lỗi, field valid

## IV.2. Business Rules

| ID | Rule | Implement ở | Liên kết test |
|---|---|---|---|
| BR-04-01 | Asset chỉ tạo qua `mint_core_asset()` trong `on_submit` | `AssetCommissioning.on_submit()` | TC-04-02 |
| BR-04-02 (G01) | CO/CQ/Manual mandatory phải Received/Waived trước rời Pending Doc Verify | `validate_gate_g01()` | TC-04-05, 06 |
| BR-04-03 (VR-01) | `vendor_serial_no` UNIQUE trên Asset + Commissioning | `_vr01_unique_serial_number()` | TC-04-03, 04 |
| BR-04-04 (G03) | 100% baseline Pass/N/A; Fail → Re Inspection | `validate_gate_g03()` | TC-04-15..18 |
| BR-04-05 (VR-07) | Bức xạ → `qa_license_doc` bắt buộc trước Release | `validate_radiation_hold()` | TC-04-19..21 |
| BR-04-06 (VR-04/G05) | No Open NC trước Release | `validate_gate_g05_g06()` | TC-04-22..24 |
| BR-04-07 (G06) | `board_approver` bắt buộc trước Submit | `validate_gate_g05_g06()` | TC-04-25 |
| BR-04-08 (BR-07/GW-2) | Asset có CN ĐK lưu hành Active hoặc Exempt trước Submit | `_gw2_check_document_compliance()` | TC-04-26 |

## IV.3. State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft: create_commissioning
    Draft --> Pending_Doc_Verify: Gửi kiểm tra tài liệu
    Pending_Doc_Verify --> Draft: Yêu cầu bổ sung
    Pending_Doc_Verify --> To_Be_Installed: Xác nhận đủ tài liệu [G01]
    To_Be_Installed --> Installing: Bắt đầu lắp đặt [G02]
    To_Be_Installed --> Non_Conformance: Báo cáo sự cố
    Installing --> Identification: Lắp đặt hoàn thành
    Installing --> Non_Conformance: Báo cáo DOA
    Identification --> Initial_Inspection: Bắt đầu kiểm tra
    Initial_Inspection --> Clinical_Release: Phê duyệt phát hành [G03]
    Initial_Inspection --> Clinical_Hold: Giữ lâm sàng [VR-07]
    Initial_Inspection --> Re_Inspection: Lỗi baseline
    Clinical_Hold --> Clinical_Release: Gỡ giữ lâm sàng
    Re_Inspection --> Clinical_Release: Phê duyệt sau tái kiểm
    Non_Conformance --> To_Be_Installed: Khắc phục xong
    Non_Conformance --> Return_To_Vendor: Trả lại NCC
    Clinical_Release --> [*]: Submit [G05+G06+GW-2] → mint Asset
    Return_To_Vendor --> [*]: Terminal
```

**Bảng State:**

| State | docstatus | Role chuyển trạng thái | Action button |
|---|---|---|---|
| Draft | 0 | HTM Tech / Biomed / CMMS Admin | Gửi kiểm tra tài liệu |
| Pending Doc Verify | 0 | Biomed Engineer | Xác nhận đủ tài liệu / Trả về Draft |
| To Be Installed | 0 | Biomed / Vendor Eng | Bắt đầu lắp đặt |
| Installing | 0 | Biomed / Vendor Eng | Lắp đặt hoàn thành / Báo DOA |
| Identification | 0 | Biomed Engineer | Bắt đầu kiểm tra |
| Initial Inspection | 0 | Biomed / QA / System Manager | Phê duyệt / Giữ lâm sàng / Báo lỗi |
| Clinical Hold | 0 | QA Officer / CMMS Admin | Gỡ giữ lâm sàng |
| Re Inspection | 0 | Biomed / System Manager | Phê duyệt sau tái kiểm |
| Clinical Release | 1 (submit) | Workshop Head / VP Block2 | Submit → Mint Asset |
| Non Conformance | 0 | Biomed / Workshop Head | Khắc phục / Trả NCC |
| Return To Vendor | 1 | — | Terminal |

## IV.4. Input — Output

**(a) Input fields chính và validation:**

| Field | Type | Required | Validation | Cascade |
|---|---|---|---|---|
| `po_reference` | Link PO | YES | PO tồn tại + không Cancelled | Auto-fill: vendor, master_item |
| `master_item` | Link Item | YES | `is_fixed_asset=1` | Auto-fill: risk_class |
| `vendor` | Link Supplier | YES | Tồn tại | — |
| `clinical_dept` | Link Dept | YES | Active | — |
| `vendor_serial_no` | Data | YES (Identification) | UNIQUE (VR-01) | — |
| `risk_class` | Select A/B/C/D/Radiation | — | Auto-fetch từ Item; warning nếu đổi sau Initial Inspection | Cascade: is_radiation_device, License row |
| `board_approver` | Link User | YES (before Submit) | role = Board / VP Block2 | — |
| `baseline_tests` | Child Table | YES | 100% result điền; Fail → `fail_note` | — |

**(b) Output records:**
- `Asset Commissioning` DocType (auto naming `ACC-YY-MM-#####`)
- `Asset` ERPNext record (khi Submit)
- `Asset Document` × N (auto-import sang IMM-05)
- `Asset Lifecycle Event` rows (immutable)
- `Asset QA Non Conformance` (khi báo NC/DOA)
- Realtime event `imm04_asset_released`

**(c) Notification / side effects:**
- Email Workshop Head khi phiếu overdue >30 ngày (scheduler daily)
- Email QA Officer khi Clinical Hold aging (daily)
- Realtime push Purchase User khi Asset released

## IV.5. Edge cases & Errors

| ID | Edge case | Hành vi mong đợi | Error code (BE) |
|---|---|---|---|
| EC-04-01 | Hai KTV nhập cùng SN trong 1 giây (race condition) | App-layer check VR-01 bắt được; DB UNIQUE (TODO) cần thêm | `VALIDATION` |
| EC-04-02 | Cancel phiếu khi `final_asset` đã tồn tại | Block với message "Không thể Cancel khi Asset đã được tạo" | `BAD_STATE` |
| EC-04-03 | Submit khi `workflow_state` ≠ `Clinical_Release` | Block với `WRONG_STATE` | `BAD_STATE` |
| EC-04-04 | Upload doc có `expiry_date < today` | Block với VR-DocExpiry message | `VALIDATION` |
| EC-04-05 | Đổi `risk_class` sau Initial Inspection | Warning msgprint (không block) — VR-05 | `BUSINESS_RULE` (cảnh báo) |
| EC-04-06 | `baseline_tests` empty khi vào Initial Inspection | Warning FE; không block submit nếu không có test nào | `VALIDATION` |
| EC-04-07 | PO đã được dùng cho phiếu khác (concurrent) | Không block — 1 PO có thể nhiều phiếu (nhiều item) | — |

## IV.6. Out of scope & Open issues

**Out of scope confirm:**
- PM Schedule auto-create → IMM-08
- PDF Print Format Biên bản Bàn giao
- Electronic signature (chữ ký số)

**Open issues:**
- DB UNIQUE constraint cho `vendor_serial_no` (Owner: DBA, Deadline: Sprint 7)
- Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` (Owner: Tech Lead, Sprint 7)

---

# Phần V — Yêu cầu phi chức năng (Non-Functional Requirements)

## V.1. Hiệu năng

| Metric | Target | Đo ở đâu |
|---|---|---|
| Tải form đầy đủ (50+ field, 3 child table) | P95 < 2s | Browser DevTools / Lighthouse |
| `check_sn_unique` on-blur | < 500ms | API response time |
| `get_dashboard_stats` | < 1s | API response time |
| List 100 phiếu với filter | P95 < 1.5s | API response time |
| Scheduler `check_commissioning_overdue` | Chạy trong 5 phút | Frappe scheduler log |

## V.2. Bảo mật

- Authentication: Frappe session cookie + API key (token)
- Authorization: RBAC 3 cấp — Role (HTM Technician / Biomed Engineer…) + DocPerm + workflow allow_edit role
- Audit trail: `lifecycle_events` child table immutable (VR-06), `track_changes=1` trên DocType
- Submit chỉ VP Block2 / Workshop Head (whitelist kiểm tra trong API layer)
- Không lưu patient data trên phiếu này
- CSRF: `X-Frappe-CSRF-Token` cho mọi POST từ browser

## V.3. Khả dụng

| Metric | Target |
|---|---|
| Uptime giờ hành chính | ≥ 99.5% |
| RTO (Recovery Time Objective) | ≤ 4 giờ |
| RPO (Recovery Point Objective) | ≤ 24 giờ (daily backup) |

## V.4. Khả mở rộng

- ≥ 50 user đồng thời không degradation
- Dataset: 10,000 phiếu/site — không ảnh hưởng performance
- Multi-site: 1 codebase, N site độc lập hoàn toàn

## V.5. Khả dụng UX

- WCAG 2.1 AA contrast, keyboard navigation
- Browser: Chrome ≥ 120, Edge ≥ 120, Firefox ≥ 122; Safari ≥ 17 best-effort
- Ngôn ngữ: tiếng Việt primary
- Responsive: desktop-first ≥ 1280px, tablet ≥ 768px
- KTV mới dùng được trong < 30 phút training

## V.6. Bảo trì

- Code coverage: service ≥ 85%, API ≥ 60%
- Mọi public service function có docstring + AC
- Linting: ruff/black 100% pass
- Tech debt budget: ≤ 20% sprint

## V.7. Tuân thủ

- Lifecycle event lưu ≥ 5 năm (NĐ98), không xóa được
- Audit trail truy xuất qua `lifecycle_events` immutable (VR-06)
- Phân tách trách nhiệm: HTM Tech tạo ≠ Workshop Head submit ≠ VP Block2 ký duyệt
- Document control: CO/CQ/Manual phải Received/Waived trước rời Pending Doc Verify (G01)
- Thiết bị bức xạ: Clinical Hold bắt buộc có giấy phép BYT (NĐ 142/2020)

---

## DoD — File 02 hoàn chỉnh

### I. Module Overview
- [x] Khảo sát hiện trạng As-Is + bảng pain points
- [x] Pitch ≤ 5 câu
- [x] Lifecycle phase + position rõ
- [x] ≥ 1 Primary + 1 Auditor stakeholder
- [x] Scope In + Out + Assumption + Dependency
- [x] ≥ 3 KPI có target số
- [x] ≥ 1 ràng buộc compliance

### II. Business Process
- [x] As-Is + ≥ 3 pain point
- [x] To-Be swimlane ≥ 4 lane
- [x] Decision points có quy tắc
- [x] RACI matrix
- [x] ≥ 2 exception flow
- [x] Activity diagram cho UC-01, UC-04

### III. Use Case Spec
- [x] Use case diagram tổng quát
- [x] Actor catalog ≥ 4 actor
- [x] UC-01, UC-04 có textual spec đầy đủ
- [x] ≥ 1 include + ≥ 1 extend

### IV. Functional Specs
- [x] User Stories có ID + AC Given-When-Then
- [x] Business Rules đánh số + nơi implement
- [x] State machine vẽ rõ
- [x] ≥ 5 edge case
- [x] Error code khai báo

### V. Non-Functional Requirements
- [x] 7 nhóm NFR đủ
- [x] Mỗi NFR có target đo được
- [x] Compliance section đối chiếu NĐ98 + WHO HTM
