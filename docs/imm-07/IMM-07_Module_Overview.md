# IMM-07 — Vận hành hàng ngày (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | DESIGN — Wave 2 |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-07 là **daily operations tracking layer** trong vòng đời thiết bị y tế: sau khi IMM-06 hoàn tất bàn giao, nhân viên lâm sàng ghi nhận trạng thái vận hành hàng ngày theo ca trực — giờ chạy máy, số chu kỳ, trạng thái thiết bị, bất thường phát sinh. Dữ liệu IMM-07 là nguồn cấp cho bảo trì dự phòng (IMM-08) và báo cáo sự cố (IMM-15).

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│  IMM-06 (Handover Record — Handed Over)                      │
│        │ asset reference                                     │
│        ▼                                                     │
│  ┌───────────────────────────────────────────────────────┐   │
│  │   IMM-07 — Daily Operation Log                        │   │
│  │                                                       │   │
│  │   Workflow 3 states · 2 Gate · 3 VR · 4 BR           │   │
│  │   DocType: Daily Operation Log (standalone)           │   │
│  │   API:    assetcore/api/imm07.py    (8 endpoints)     │   │
│  │   Service:assetcore/services/imm07.py                 │   │
│  └───────────────────────────────────────────────────────┘   │
│        │ on anomaly (Critical/Major)                        │
│        └──► Incident Report (IMM-15 trigger)               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Daily Operation Log` | `DOL-.YY.-.MM.-.DD.-.#####` | Yes | Nhật ký vận hành theo ca — 1 record/ca/thiết bị |

---

## 4. Actors

| Actor | Role hệ thống | Trách nhiệm chính |
|---|---|---|
| Clinical Operator | `Clinical Operator` | Tạo log, ghi nhận trạng thái, báo bất thường |
| Nurse | `Nurse` | Ghi log theo ca, xác nhận trạng thái |
| Department Head | `Department Head` | Review và phê duyệt log ca |
| HTM Technician | `HTM Technician` | Đọc log để lên lịch bảo trì, xử lý bất thường |

---

## 5. Workflow States

| State | doc_status | Loại | Mô tả |
|---|---|---|---|
| `Open` | 0 | — | Log đang được điền trong ca |
| `Logged` | 0 | Info | Đã lưu đủ thông tin ca trực |
| `Reviewed` | 1 | Success | Trưởng khoa đã review — terminal positive |

### 5.1 Transition matrix

| From → To | Action | Role |
|---|---|---|
| Open → Logged | Nộp nhật ký ca | Clinical Operator / Nurse |
| Logged → Reviewed | Phê duyệt ca | Department Head / HTM Technician |
| Logged → Open | Yêu cầu chỉnh sửa | Department Head |

---

## 6. Service Functions

File: `assetcore/services/imm07.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `create_daily_log(asset, log_date, shift, ...)` | API | Tạo log mới |
| `get_daily_log(name)` | API | Chi tiết log |
| `list_daily_logs(filters)` | API | Danh sách với pagination |
| `submit_log(name)` | API | Nộp log (Open → Logged) |
| `review_log(name, reviewer_notes)` | API | Phê duyệt log (Logged → Reviewed) |
| `get_asset_operation_summary(asset, days)` | API | Tổng hợp runtime, uptime%, anomaly |
| `get_dashboard_stats(dept)` | API | Dashboard: thiết bị theo status hôm nay |
| `report_anomaly_from_log(log_name, severity)` | API | Tạo Incident Report từ bất thường |
| `validate_single_log_per_shift(doc)` | `validate` | VR-01: 1 log/ca/thiết bị/ngày |
| `validate_meter_hours(doc)` | `validate` | VR-02: end_meter ≥ start_meter |
| `compute_runtime_hours(doc)` | `before_save` | Tính runtime = end - start |
| `log_lifecycle_event(asset, ...)` | `on_submit` | Ghi audit trail |

---

## 7. KPIs

| KPI | Mô tả | Target |
|---|---|---|
| Asset uptime % today | % thiết bị Running / tổng active | ≥ 90% |
| Total runtime hours today | Tổng giờ chạy máy trong ngày | Monitor |
| Fault count today | Số thiết bị Fault trong ngày | Alert nếu > 0 |
| Anomaly rate | % ca có bất thường / tổng ca | ≤ 5% |
| Log completion rate | % ca đã Review / tổng ca trong ngày | ≥ 95% |

---

## 8. Business Rules

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-07-01 | 1 log mỗi ca (Sáng/Chiều/Tối) mỗi thiết bị mỗi ngày | `validate` | Nhất quán dữ liệu |
| BR-07-02 | end_meter_hours ≥ start_meter_hours | `validate` | Tính toán đúng runtime |
| BR-07-03 | Nếu anomaly_detected=1 phải có anomaly_description | `validate` | Audit trail |
| BR-07-04 | Anomaly Major/Critical → tạo Incident Report tự động | `on_submit` | WHO HTM §8.3 |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-06 (Handover Record) | Điều kiện tiên quyết | Asset phải có Handover Handed Over |
| IMM-08 (PM Schedule) | Output | Runtime hours cộng dồn → trigger PM |
| IMM-15 (Incident Report) | Output | `report_anomaly_from_log()` tạo Incident |
| Asset Lifecycle Event | Audit trail | Ghi event `operation_logged` |

---

## 10. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType Daily Operation Log | DESIGN | Cần tạo migration |
| Workflow 3 states | DESIGN | JSON cần config |
| API layer (8 endpoints) | DESIGN | `assetcore/api/imm07.py` |
| Service layer | DESIGN | `assetcore/services/imm07.py` |
| Frontend views (3) | DESIGN | Vue 3 components |

---

## 11. Tài liệu liên quan

- `IMM-07_Functional_Specs.md` — user stories, acceptance criteria, validation rules
- `IMM-07_Technical_Design.md` — schema, service functions, hooks
- `IMM-07_API_Interface.md` — 8 endpoints với request/response
- `IMM-07_UAT_Script.md` — test cases
- `IMM-07_UI_UX_Guide.md` — wireframes, routes, component specs

*End of Module Overview v1.0.0 — IMM-07*
