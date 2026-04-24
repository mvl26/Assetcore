# IMM-06 — Bàn giao & Đào tạo (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | DESIGN — Wave 2 |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-06 là **handover gateway** trong vòng đời thiết bị y tế: sau khi IMM-04 đạt `Clinical Release`, thiết bị phải được bàn giao chính thức từ HTM/Nhà cung cấp sang khoa lâm sàng sử dụng thực tế. Kèm theo là các buổi đào tạo nhân sự vận hành, an toàn, và xử lý khẩn cấp.

Không có phiếu IMM-06 ở trạng thái `Handed Over` (docstatus=1) thì **nhân viên lâm sàng không được sử dụng thiết bị độc lập** (IMM-07 không ghi nhận ca trực bình thường).

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│  IMM-04 (Asset Commissioning — Clinical Release)             │
│        │ commissioning_ref                                   │
│        ▼                                                     │
│  ┌───────────────────────────────────────────────────────┐   │
│  │   IMM-06 — Handover Record + Training Session         │   │
│  │                                                       │   │
│  │   Workflow 5 states · 3 Gate · 4 VR · 5 BR           │   │
│  │   DocType: Handover Record + Training Session +       │   │
│  │            Training Trainee (child)                   │   │
│  │   API:    assetcore/api/imm06.py    (8 endpoints)     │   │
│  │   Service:assetcore/services/imm06.py                 │   │
│  └───────────────────────────────────────────────────────┘   │
│        │ on_submit                                           │
│        ├──► Asset Lifecycle Event (handover_completed)       │
│        └──► IMM-07 Daily Operation Log (trigger enabled)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocTypes

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Handover Record` | `HR-.YY.-.MM.-.#####` | Yes | Phiếu bàn giao chính thức — workflow 5 states |
| `Training Session` | `TS-.YY.-.MM.-.#####` | No | Buổi đào tạo nhân sự — linked to Handover Record |

### 3.2 Child Tables

| Child DocType | Parent field | Mục đích |
|---|---|---|
| `Training Trainee` | `trainees` (trong Training Session) | Danh sách học viên, điểm, pass/fail |

---

## 4. Actors

| Actor | Role hệ thống | Trách nhiệm chính |
|---|---|---|
| HTM Technician | `HTM Technician` | Tạo phiếu bàn giao, lên lịch đào tạo |
| Biomed Engineer | `Biomed Engineer` | Dẫn buổi đào tạo kỹ thuật, ký xác nhận |
| Vendor Trainer | `Vendor Engineer` | Đào tạo do nhà cung cấp thực hiện |
| Clinical Dept Head | `Department Head` | Nhận bàn giao, ký xác nhận khoa |
| QA Officer | `QA Officer` | Xác nhận competency, phê duyệt bàn giao |
| CMMS Admin | `CMMS Admin` | Override workflow khi cần |

---

## 5. Workflow States

| State | doc_status | Loại | Mô tả |
|---|---|---|---|
| `Draft` | 0 | — | Phiếu mới tạo, chưa gửi |
| `Training Scheduled` | 0 | Info | Đã lên lịch đào tạo ít nhất 1 buổi |
| `Training Completed` | 0 | Success | Tất cả buổi đào tạo đã hoàn thành |
| `Handover Pending` | 0 | Warning | Chờ ký nhận bàn giao |
| `Handed Over` | 1 | Success | Bàn giao hoàn thành — terminal positive |
| `Cancelled` | 2 | Danger | Hủy bỏ — terminal negative |

### 5.1 Transition matrix

| From → To | Action | Role |
|---|---|---|
| Draft → Training Scheduled | Lên lịch đào tạo | HTM Technician / Biomed Engineer |
| Training Scheduled → Training Completed | Xác nhận hoàn thành đào tạo | Biomed Engineer / QA Officer |
| Training Scheduled → Draft | Huỷ lịch | HTM Technician |
| Training Completed → Handover Pending | Gửi bàn giao | Biomed Engineer |
| Handover Pending → Handed Over | Ký nhận bàn giao | Clinical Dept Head / CMMS Admin |
| Handover Pending → Training Scheduled | Yêu cầu đào tạo thêm | QA Officer |
| Any → Cancelled | Hủy bỏ | CMMS Admin |

---

## 6. Service Functions

File: `assetcore/services/imm06.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `create_handover_record(commissioning_ref, ...)` | API | Tạo phiếu bàn giao từ commissioning |
| `get_handover_record(name)` | API | Lấy chi tiết phiếu + training sessions |
| `list_handover_records(filters)` | API | Danh sách phiếu với pagination |
| `schedule_training(handover_name, ...)` | API | Tạo Training Session mới |
| `complete_training(session_name, scores)` | API | Ghi nhận kết quả đào tạo |
| `confirm_handover(name, dept_head_signoff)` | API | Xác nhận bàn giao, submit |
| `get_asset_training_history(asset_name)` | API | Lịch sử đào tạo theo thiết bị |
| `get_dashboard_stats()` | API | KPI tổng quan bàn giao |
| `validate_commissioning_released(doc)` | `before_insert` | VR-01: commissioning phải Clinical Release |
| `validate_no_duplicate_handover(doc)` | `validate` | VR-02: asset chưa có Handed Over khác |
| `validate_training_completion(doc)` | `validate` | VR-03: phải có ít nhất 1 buổi đào tạo |
| `log_lifecycle_event(asset, event_type, ...)` | `on_submit` | Ghi audit trail bất biến |

---

## 7. KPIs

| KPI | Mô tả | Target |
|---|---|---|
| Handover completion rate | % phiếu Handed Over / tổng thiết bị Released tháng | ≥ 95% |
| Avg days Draft→Handed Over | Trung bình thời gian bàn giao | ≤ 14 ngày |
| Training pass rate | % học viên đạt (score ≥ 70) | ≥ 90% |
| Pending handover count | Số phiếu đang chờ bàn giao | ≤ 5 |
| Sessions per asset | Trung bình số buổi đào tạo / thiết bị | ≥ 1 |

---

## 8. Business Rules

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-06-01 | Commissioning phải ở trạng thái Clinical Release trước khi tạo Handover | `before_insert` | WHO HTM §6.2 |
| BR-06-02 | Asset chưa có Handover Record Handed Over mới được tạo mới | `validate` | Tránh trùng lặp |
| BR-06-03 | Phải có ít nhất 1 Training Session completed trước Handover Pending | `validate_gate` | ISO 13485 §7.3 |
| BR-06-04 | dept_head_signoff bắt buộc trước khi Handed Over | `confirm_handover()` | Quy trình BV |
| BR-06-05 | Tất cả trainees phải có kết quả (passed/failed) trước khi complete_training | `complete_training()` | ISO 13485 §6.2 |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-04 (Asset Commissioning) | Nguồn dữ liệu | Field `commissioning_ref` (Link → Asset Commissioning); VR-01: phải Clinical Release |
| IMM-07 (Daily Operation Log) | Output | Phiếu Handed Over cho phép ghi Daily Log |
| Asset Lifecycle Event | Audit trail | Ghi event `handover_completed` trên on_submit |

---

## 10. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType Handover Record | DESIGN | Cần tạo migration |
| DocType Training Session | DESIGN | Cần tạo migration |
| Child Table Training Trainee | DESIGN | Cần tạo migration |
| Workflow 5 states | DESIGN | JSON cần config |
| API layer (8 endpoints) | DESIGN | `assetcore/api/imm06.py` |
| Service layer | DESIGN | `assetcore/services/imm06.py` |
| Frontend views (3) | DESIGN | Vue 3 components |

---

## 11. Tài liệu liên quan

- `IMM-06_Functional_Specs.md` — user stories, acceptance criteria, validation rules
- `IMM-06_Technical_Design.md` — schema, service functions, hooks
- `IMM-06_API_Interface.md` — 8 endpoints với request/response
- `IMM-06_UAT_Script.md` — test cases
- `IMM-06_UI_UX_Guide.md` — wireframes, routes, component specs

*End of Module Overview v1.0.0 — IMM-06*
