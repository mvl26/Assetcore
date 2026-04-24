# IMM-13 — Ngừng sử dụng và Điều chuyển (Module Overview)

| Thuộc tính    | Giá trị                                              |
|---------------|------------------------------------------------------|
| Module        | IMM-13 — Suspension & Transfer                       |
| Phiên bản     | 2.0.0                                                |
| Ngày cập nhật | 2026-04-24                                           |
| Trạng thái    | IN DEVELOPMENT                                       |
| Tác giả       | AssetCore Team                                       |
| Chuẩn áp dụng | WHO HTM Decommissioning Guide · WHO 2025 §3.2 · NĐ98/2021 |

---

## 1. Mục đích

IMM-13 là **lifecycle gateway** kiểm soát giai đoạn chuyển tiếp cuối vòng đời thiết bị y tế — khi thiết bị cần **ngừng sử dụng lâm sàng** hoặc **điều chuyển** trước khi đến giai đoạn đóng hồ sơ (IMM-14).

Module này KHÔNG phải là quy trình thanh lý/hủy thiết bị. Vai trò chính xác:

| Chức năng | Thuộc IMM-13 | Thuộc IMM-14 |
|---|---|---|
| Đình chỉ sử dụng lâm sàng | ✓ | — |
| Đánh giá kỹ thuật & residual risk | ✓ | — |
| Review thay thế thiết bị | ✓ | — |
| Điều chuyển nội viện / liên cơ sở | ✓ | — |
| Phê duyệt ngừng sử dụng | ✓ | — |
| Thực thi ngừng / điều chuyển | ✓ | — |
| Đóng hồ sơ kế toán–kho–tài sản | — | ✓ |
| Lưu trữ hồ sơ vĩnh viễn | — | ✓ |
| Thanh lý / hủy vật chất | — | ✓ |

Tuân thủ:
- **WHO HTM Decommissioning Guide** — kiểm tra kỹ thuật, residual risk trước ngừng
- **WHO 2025 §3.2** — transfer/relocation as part of lifecycle management
- **NĐ98/2021** — điều chuyển và thanh lý TBYT, §15 nguy hại sinh học, §16 giấy phép

---

## 2. Vị trí trong kiến trúc lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│   IMM-08  PM      IMM-09  Repair    IMM-11  Calibration  IMM-12  CM     │
│      │ chronic failure / EOL flag          │ critical failure           │
│      └──────────────────────┬──────────────┘                            │
│                             ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │        IMM-13 — Suspension & Transfer Gateway                   │   │
│   │                                                                 │   │
│   │  ┌───────────┐   ┌──────────────┐   ┌────────────────────────┐ │   │
│   │  │ Suspension│   │ Replacement  │   │   Residual Risk        │ │   │
│   │  │ Request   │──▶│ Review       │──▶│   Assessment           │ │   │
│   │  └───────────┘   └──────────────┘   └────────────────────────┘ │   │
│   │         │                                       │               │   │
│   │         ▼                           ┌───────────┴──────────┐   │   │
│   │  ┌─────────────┐            Transfer│                      │Retire  │
│   │  │  Approval   │◀──────────────────▶│                      │   │   │
│   │  └─────────────┘                   │                      │   │   │
│   │         │ on_submit                │                      │   │   │
│   │         ▼                          ▼                      ▼   │   │
│   │  ┌─────────────┐       ┌────────────────┐    ┌────────────────┐│   │
│   │  │ Asset.status│       │  Asset.location│    │ Trigger IMM-14 ││   │
│   │  │=Suspended / │       │  updated       │    │ (Decommission  ││   │
│   │  │ Transferred │       │  ALE logged    │    │  Request)      ││   │
│   │  └─────────────┘       └────────────────┘    └────────────────┘│   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   Output:  Asset status = Suspended | Transferred | Pending Decommission│
│            → IMM-14 triggered nếu outcome = Decommission               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming Series | Submittable | Mô tả |
|---|---|---|---|
| `Decommission Request` | `DR-.YY.-.MM.-.#####` | Yes | Phiếu yêu cầu ngừng sử dụng/điều chuyển — workflow 8 states, gateway chuyển Asset sang trạng thái cuối vòng đời |

### 3.2 Child Tables

| Child DocType | Parent Field | Mục đích |
|---|---|---|
| `Suspension Checklist Item` | `suspension_checklist` | Danh mục công việc thực thi ngừng sử dụng (thu hồi, kiểm kê, vệ sinh sinh học, xóa dữ liệu) |
| `Transfer Detail` | `transfer_details` | Thông tin điều chuyển: đơn vị nhận, ngày, người tiếp nhận, điều kiện kèm theo |

### 3.3 DocTypes tham chiếu

| DocType | Quan hệ | Ghi chú |
|---|---|---|
| `AC Asset` | Link (required) | Thiết bị thực — status được cập nhật khi on_submit |
| `Asset Lifecycle Event` | Embedded via service | Audit trail bất biến cho mọi transition |
| `Decommission Request` (IMM-14) | Auto-trigger on retire | Nếu outcome = Decommission, auto-create IMM-14 closure record |
| `Asset Transfer` | Link (optional) | Record điều chuyển tài sản (ERPNext core extension) |

---

## 4. Actors & Permission Matrix

| Actor | Vai trò | Create | Read | Write | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|---|
| IMM HTM Manager | Người khởi tạo & giám sát | ✓ | ✓ | ✓ | — | — | — |
| IMM Biomed Engineer | Đánh giá kỹ thuật & residual risk | — | ✓ | ✓ (tech fields) | — | — | — |
| IMM QA Officer | Đánh giá tuân thủ & clearance | — | ✓ | ✓ (compliance fields) | — | — | — |
| IMM Finance (KH-TC) | Review kinh tế/replacement | — | ✓ | ✓ (finance fields) | — | — | — |
| IMM Network Manager | Điều phối điều chuyển nội viện | — | ✓ | ✓ (transfer fields) | — | — | — |
| IMM VP Block2 | Phê duyệt cấp khối | — | ✓ | — | ✓ | — | — |
| IMM CMMS Admin | Quản trị, submit, trigger IMM-14 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| System Manager | Full access | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 5. Workflow States (Tổng quan)

```
Draft
  │ [Gửi đánh giá KT]
  ▼
Pending Tech Review
  │ [Hoàn thành KT]                    [Từ chối KT]
  ▼                                         ▼
Under Replacement Review              Cancelled
  │ [Quyết định thay thế]
  ├──── outcome: Transfer ──────▶ Approved for Transfer
  │                                    │ [Bắt đầu điều chuyển]
  │                                    ▼
  │                              Transfer In Progress
  │                                    │ [Hoàn thành điều chuyển]
  │                                    ▼
  │                              Transferred (Completed)
  │
  └──── outcome: Suspend/Retire ─▶ Pending Decommission
                                        │ [Submit → trigger IMM-14]
                                        ▼
                                   Completed (→ IMM-14 opened)
```

### Bảng states đầy đủ

| State | docstatus | Mô tả | Actor có thể edit |
|---|---|---|---|
| `Draft` | 0 | Phiếu vừa tạo, đang nhập thông tin | HTM Manager, CMMS Admin |
| `Pending Tech Review` | 0 | Kỹ sư đang đánh giá kỹ thuật & residual risk | Biomed Engineer, QA Officer |
| `Under Replacement Review` | 0 | Đang review khả năng thay thế, kinh tế học | HTM Manager, Finance, QA |
| `Approved for Transfer` | 0 | Phê duyệt điều chuyển, chờ thực thi | Network Manager, HTM Manager |
| `Transfer In Progress` | 0 | Đang tiến hành điều chuyển vật lý | Network Manager, HTM Manager |
| `Transferred` | 1 | Điều chuyển hoàn tất — terminal (asset moved) | — (submitted) |
| `Pending Decommission` | 0 | Chờ submit để trigger IMM-14 | CMMS Admin |
| `Completed` | 1 | Ngừng sử dụng hoàn tất — IMM-14 opened | — (submitted) |
| `Cancelled` | 2 | Phiếu bị hủy | System Manager, CMMS Admin |

---

## 6. Integration Points

| Module / DocType | Chiều | Cơ chế | Trigger |
|---|---|---|---|
| **IMM-08 PM** | Input | Auto-flag nếu failure_rate > threshold | Scheduler daily |
| **IMM-09 Repair** | Input | `Cannot Repair` outcome → suggest DR | on_submit CM WO |
| **IMM-11 Calibration** | Input | Calibration fail + out_of_tolerance → flag | on_submit Calibration |
| **IMM-12 Corrective** | Input | Chronic failure pattern → auto-flag retirement candidate | Scheduler weekly |
| **AC Asset** | Output | `asset.status` cập nhật (Suspended/Transferred/Decommissioned) | DR on_submit |
| **Asset Lifecycle Event** | Output | Immutable ALE mọi transition | every state change |
| **IMM-14 Archive** | Output | Auto-create Decommission closure record nếu outcome=Retire | DR on_submit |
| **Asset Transfer (ERPNext)** | Output | Cập nhật location khi điều chuyển | execute_transfer |

---

## 7. QMS Document Mapping

| Loại tài liệu | Mã | Nội dung |
|---|---|---|
| Quality Control | QC-IMMIS-04 | Kiểm soát chất lượng module IMM-13 |
| Procedure | PR-IMMIS-13-01 | Quy trình ngừng sử dụng thiết bị y tế |
| Procedure | PR-IMMIS-13-02 | Quy trình điều chuyển thiết bị nội viện |
| Procedure | PR-IMMIS-13-03 | Quy trình đánh giá residual risk trước decommission |
| Work Instruction | WI-IMMIS-13-01 | Hướng dẫn đánh giá kỹ thuật thiết bị ngừng |
| Work Instruction | WI-IMMIS-13-02 | Hướng dẫn đánh giá residual risk |
| Work Instruction | WI-IMMIS-13-03 | Hướng dẫn thực hiện điều chuyển vật lý |
| Work Instruction | WI-IMMIS-13-04 | Hướng dẫn xử lý thiết bị nguy hại sinh học |
| Biểu mẫu | BM-IMMIS-13-01 | Phiếu đánh giá kỹ thuật & residual risk |
| Hồ sơ LOG | HS-LOG-IMMIS-13 | Log điều chuyển và ngừng sử dụng |
| Hồ sơ REC | HS-REC-IMMIS-13 | Record phiếu DR đã hoàn tất |
| Hồ sơ REP | HS-REP-IMMIS-13 | Báo cáo tổng hợp ngừng sử dụng định kỳ |
| Dashboard KPI | KPI-DASH-IMMIS-13 | Dashboard theo dõi KPI/KRI IMM-13 |

---

## 8. KPIs / KRIs

| Chỉ số | Loại | Định nghĩa | Ngưỡng cảnh báo | Tần suất |
|---|---|---|---|---|
| Retirement Candidate Rate | KRI | % thiết bị được flagged là retirement candidate / tổng active fleet | > 15% | Monthly |
| Transfer Completion Rate | KPI | % phiếu Transfer In Progress → Transferred trong SLA 30 ngày | < 80% = alert | Monthly |
| Residual Risk Closure Rate | KPI | % phiếu có residual risk đã được đánh giá đầy đủ | < 100% = block | Per DR |
| Avg Days Draft→Completed | KPI | Thời gian trung bình xử lý phiếu DR | > 45 ngày = alert | Weekly |
| Suspension Without Review | KRI | Số phiếu Completed không có residual risk assessment | > 0 = critical | Daily |
| High-Value Pending > 14d | KRI | Phiếu book_value > 500M chưa phê duyệt quá 14 ngày | > 0 = escalate | Daily |
| Bio-hazard Open Items | KRI | Phiếu có biological_hazard chưa có clearance đang mở | > 0 = block | Real-time |

---

## 9. Dependencies & Pre-conditions

| Điều kiện | Mô tả |
|---|---|
| Asset phải tồn tại | `AC Asset` với status không phải `Decommissioned` hoặc đã có DR |
| Không còn Work Order mở | Mọi WO (PM/CM/Calibration) phải đóng trước khi submit DR |
| Residual risk phải được đánh giá | `residual_risk_level` phải được điền trước khi chuyển sang Replacement Review |
| Bio-hazard clearance | Nếu `biological_hazard=True`, bắt buộc `bio_hazard_clearance` |
| Data destruction | Nếu `data_destruction_required=True`, bắt buộc confirm trước submit |
| Regulatory clearance | Nếu cần giấy phép, bắt buộc upload file |

---

## 10. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType `Decommission Request` (v2) | IN DEV | Mở rộng với suspension + transfer fields |
| Child: `Suspension Checklist Item` | IN DEV | Thay thế Decommission Checklist Item |
| Child: `Transfer Detail` | IN DEV | Mới — tracking điều chuyển |
| Workflow 8 states | IN DEV | Revised cho Suspension & Transfer |
| API layer (12 endpoints) | IN DEV | `assetcore/api/imm13.py` |
| Service layer `imm13.py` | IN DEV | 8+ functions |
| Scheduler: retirement candidate check | IN DEV | Daily |
| Frontend Vue 3 (5 screens) | IN DEV | imm13 store + router |
| Dashboard KPI-DASH-IMMIS-13 | IN DEV | — |
| UAT | TODO | 20 test cases |
| IMM-14 trigger integration | TODO | Sau khi IMM-14 ổn định |

---

## 11. Tài liệu liên quan

- `IMM-13_Functional_Specs.md` — Use cases UC-13-01 → UC-13-08, Business Rules BR-13-01 → BR-13-12
- `IMM-13_Technical_Design.md` — ERD, field definitions, service layer, workflow JSON
- `IMM-13_API_Interface.md` — 12 endpoints OpenAPI 3.0
- `IMM-13_UI_UX_Guide.md` — 5 screens, wireframes, component specs, store
- `IMM-13_UAT_Script.md` — 20 test cases với acceptance criteria
- `IMM-14_Module_Overview.md` — Module đóng hồ sơ (Archive & Disposal Closure)

---

*End of Module Overview v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển*
