# IMM-13 — Thanh lý Thiết bị Y tế (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — Thanh lý Thiết bị Y tế (Decommissioning & Disposal) |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | IN DEVELOPMENT |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-13 là **lifecycle closure gateway** trong vòng đời thiết bị y tế: quy trình thanh lý chính thức đưa thiết bị ra khỏi sử dụng lâm sàng, từ khởi tạo yêu cầu → đánh giá kỹ thuật → định giá tài chính → phê duyệt đa cấp → thực thi thanh lý → hoàn tất.

Không có phiếu IMM-13 ở trạng thái `Completed` (docstatus=1) thì thiết bị **không được thanh lý** và record Asset không được set `Decommissioned`. Module này là **terminal node** trong luồng lifecycle — chỉ đến sau tất cả các hoạt động vận hành (IMM-08/09/11/12).

Tuân thủ **NĐ98/2021** về quản lý trang thiết bị y tế và **WHO HTM Decommissioning Guide**.

---

## 2. Vị trí trong kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│  IMM-08/09/11/12 (PM / CM / Calibration / Incident)             │
│        │ Cannot Repair / End of Life trigger                    │
│        ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   IMM-13 — Decommission Request (terminal gateway EOL)   │   │
│  │                                                          │   │
│  │   Workflow 8 states · 5 VR · Multi-party approval       │   │
│  │   DocType: Decommission Request + 1 child                │   │
│  │   API:    assetcore/api/imm13.py    (12 endpoints)       │   │
│  │   Service:assetcore/services/imm13.py                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│        │ on_submit                                              │
│        ├──► AC Asset.status = "Decommissioned"                  │
│        ├──► Asset Lifecycle Event (decommissioned)              │
│        └──► IMM-14 Asset Archive Record (auto-create)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Decommission Request` | `DR-.YY.-.MM.-.#####` | Yes | Phiếu yêu cầu thanh lý — workflow 8 states, gateway set Asset Decommissioned |

### 3.2 Child Table

| Child DocType | Parent field | Mục đích |
|---|---|---|
| `Decommission Checklist Item` | `checklist` | Danh mục công việc thực thi thanh lý (thu hồi thiết bị, kiểm kê phụ tùng, xoá dữ liệu, vệ sinh sinh học) |

### 3.3 DocType tham chiếu

| DocType | Link | Ghi chú |
|---|---|---|
| `Asset Lifecycle Event` | embedded via service | Audit trail bất biến cho mọi transition |
| `Asset Archive Record` | auto-create on_submit | IMM-14 — lưu trữ hồ sơ |

---

## 4. Actors

| Actor | Vai trò | Hành động chính |
|---|---|---|
| HTM Manager | Người khởi tạo chính | Tạo yêu cầu, hoàn tất thực thi |
| Biomed Engineer | Đánh giá kỹ thuật | Điền technical review, condition assessment |
| Finance Director | Định giá tài chính | Xác nhận book value, disposal value |
| QA Officer | Kiểm tra tuân thủ | Xem xét clearance sinh học, hồ sơ pháp lý |
| VP Block2 | Phê duyệt cấp khối | Phê duyệt thanh lý thiết bị giá trị cao |
| Board (BGĐ) | Phê duyệt cao nhất | Thiết bị có giá trị > 500 triệu VNĐ |
| CMMS Admin | Quản trị hệ thống | Submit, đóng hồ sơ, trigger IMM-14 |

---

## 5. Service Functions

File: `assetcore/services/imm13.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `validate_decommission_request(doc)` | `validate()` | Chạy VR-01 → VR-05 |
| `_vr01_check_active_work_orders(doc)` | `validate()` | VR-01: Chặn nếu còn WO mở |
| `_vr02_board_approval_threshold(doc)` | `validate()` | VR-02: book_value > 500M → cần Board |
| `_vr03_bio_hazard_clearance(doc)` | `validate()` | VR-03: bio_hazard=1 → bắt buộc bio_hazard_clearance |
| `_vr04_regulatory_clearance(doc)` | `validate()` | VR-04: regulatory_clearance_required → bắt buộc file |
| `_vr05_data_destruction(doc)` | `validate()` | VR-05: data_destruction_required → bắt buộc confirmation |
| `submit_technical_review(name, reviewer, notes, approved)` | API | Đổi state Technical Review → Financial Valuation / Rejected |
| `submit_financial_valuation(name, reviewer, ...)` | API | Đổi state Financial Valuation → Pending Approval |
| `approve_decommission(name, approver, notes)` | API | Board Approved |
| `reject_decommission(name, reason)` | API | → Rejected terminal |
| `execute_decommission(name, executor, ...)` | API | → Execution → Completed |
| `on_submit_handler(doc)` | `on_submit` | Set asset.status = Decommissioned, log ALE, trigger IMM-14 |
| `log_lifecycle_event(doc, event_type, ...)` | internal | Sinh immutable ALE record |
| `get_asset_decommission_eligibility(asset_name)` | API | Kiểm tra WO mở, book value, last PM |
| `get_dashboard_stats()` | API | KPI: YTD count, disposal value, avg time |

---

## 6. Workflow States & Transitions

Workflow 8 states — `workflow_state_field = workflow_state`.

### 6.1 Bảng trạng thái

| State | doc_status | Mô tả | allow_edit |
|---|---|---|---|
| `Draft` | 0 | Phiếu vừa tạo, đang nhập thông tin | HTM Manager |
| `Technical Review` | 0 | Kỹ sư đang đánh giá tình trạng thiết bị | Biomed Engineer |
| `Financial Valuation` | 0 | Tài chính đang định giá | Finance Director |
| `Pending Approval` | 0 | Chờ phê duyệt đa cấp | VP Block2 / Board |
| `Board Approved` | 0 | BGĐ đã phê duyệt, chờ thực hiện | HTM Manager |
| `Execution` | 0 | Đang tiến hành thanh lý thực tế | HTM Manager / Biomed |
| `Completed` | 1 | Thanh lý hoàn tất — terminal positive | System Manager |
| `Rejected` | 2 | Phiếu bị từ chối — terminal negative | System Manager |

### 6.2 Ma trận chuyển trạng thái

| From → To | Action (vi) | Người thực hiện |
|---|---|---|
| Draft → Technical Review | Gửi đánh giá kỹ thuật | HTM Manager / CMMS Admin |
| Technical Review → Financial Valuation | Hoàn thành đánh giá kỹ thuật | Biomed Engineer |
| Technical Review → Rejected | Từ chối tại bước kỹ thuật | Biomed Engineer |
| Financial Valuation → Pending Approval | Hoàn thành định giá tài chính | Finance Director |
| Pending Approval → Board Approved | Phê duyệt thanh lý | VP Block2 / CMMS Admin |
| Pending Approval → Rejected | Từ chối phê duyệt | VP Block2 / Board |
| Board Approved → Execution | Bắt đầu thực thi thanh lý | HTM Manager |
| Execution → Completed | Hoàn tất thanh lý | CMMS Admin / System Manager |
| Execution → Rejected | Huỷ khi đang thực hiện | System Manager |

---

## 7. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `assetcore.services.imm13.check_decommission_overdue` | Daily | Phiếu mở > 60 ngày → cảnh báo | HTM Manager (email) |
| `assetcore.services.imm13.check_pending_approvals` | Daily | Phiếu Pending Approval > 14 ngày → escalate | VP Block2 |

---

## 8. Roles & Permissions

| Role | Quyền trên Decommission Request |
|---|---|
| IMM HTM Manager | Create / Read / Write |
| IMM Biomed Engineer | Read / Write (không create, không submit) |
| IMM Finance Director | Read / Write (financial fields) |
| IMM QA Officer | Read / Write (clearance fields) |
| IMM VP Block2 | Read / Submit / Print / Export |
| IMM CMMS Admin | Read / Write / Submit / Cancel / Delete |
| System Manager | Full |

---

## 9. Business Rules

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-13-01 (VR-01) | Không thể thanh lý nếu còn Work Order mở trên asset | `_vr01_check_active_work_orders()` | WHO HTM §8.1 |
| BR-13-02 (VR-02) | Book value > 500 triệu VNĐ → bắt buộc Board Approval | `_vr02_board_approval_threshold()` | Quy chế tài chính BV |
| BR-13-03 (VR-03) | Thiết bị nguy hại sinh học → bắt buộc khai báo `bio_hazard_clearance` | `_vr03_bio_hazard_clearance()` | NĐ98/2021 §15 |
| BR-13-04 (VR-04) | `regulatory_clearance_required = 1` → bắt buộc upload file giấy phép | `_vr04_regulatory_clearance()` | NĐ98/2021 §16 |
| BR-13-05 (VR-05) | `data_destruction_required = 1` → bắt buộc `data_destruction_confirmed = 1` trước Submit | `_vr05_data_destruction()` | ISO 27001 / HIPAA |

---

## 10. KPIs

| KPI | Định nghĩa | Tần suất tính |
|---|---|---|
| Assets Decommissioned YTD | Số phiếu Completed trong năm hiện tại | Real-time |
| Avg Time Draft→Completed | Thời gian trung bình (ngày) từ tạo đến hoàn tất | Weekly |
| Total Disposal Value Recovered | Tổng `estimated_disposal_value` của phiếu Completed | Monthly |
| Disposal by Method | Phân bổ theo `disposal_method` (Auction/Transfer/Scrap/etc.) | Monthly |
| High-Value Pending Approval | Số phiếu book_value > 500M chưa được phê duyệt | Real-time |

---

## 11. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-09 (Cannot Repair) | Nguồn trigger | `Asset.status = Out of Service` → suggest IMM-13 |
| IMM-08/11/12 | Nguồn dữ liệu | `last_service_date`, `total_maintenance_cost` |
| AC Asset | Output | `asset.status = Decommissioned` trên on_submit |
| IMM-14 (Archive) | Output | Auto-create `Asset Archive Record` trên on_submit |
| Asset Lifecycle Event | Audit trail | Immutable event `decommissioned` |

---

## 12. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType + child table | IN DEV | `DR-.YY.-.MM.-.#####` naming |
| Workflow 8 states | IN DEV | Controller-driven |
| API layer (12 endpoints) | IN DEV | `assetcore/api/imm13.py` |
| Service layer | IN DEV | `assetcore/services/imm13.py` |
| Validation VR-01 → VR-05 | IN DEV | Backend enforce |
| Auto-set Asset Decommissioned | IN DEV | `on_submit` |
| Auto-create IMM-14 Archive | IN DEV | `on_submit` |
| Frontend Vue 3 | IN DEV | 3 views + store |
| Dashboard KPIs | IN DEV | `get_dashboard_stats()` |
| UAT | TODO | — |

---

## 13. Tài liệu liên quan

- `IMM-13_Functional_Specs.md` — yêu cầu nghiệp vụ, user stories, acceptance criteria
- `IMM-13_Technical_Design.md` — schema, validation impl, hooks, indexes
- `IMM-13_API_Interface.md` — 12 endpoints với request/response
- `IMM-13_UAT_Script.md` — test cases
- `IMM-13_UI_UX_Guide.md` — wireframes, routes, component specs

*End of Module Overview v1.0.0 — IMM-13*
