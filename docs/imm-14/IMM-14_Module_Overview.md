# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — Lưu trữ & Kết thúc Hồ sơ (Record Archive & Lifecycle Closure) |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | IN DEVELOPMENT |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-14 là **bước cuối cùng trong vòng đời thiết bị y tế**: đóng và lưu trữ toàn bộ hồ sơ theo quy định. Module này:

- Biên soạn toàn bộ lịch sử thiết bị từ commissioning → vận hành → bảo trì → sự cố → hiệu chuẩn → thanh lý
- Tạo báo cáo tóm tắt vòng đời cuối cùng (Device Life Summary Report)
- Lưu trữ tài liệu trong **10 năm** theo NĐ98/2021 §17
- Cập nhật `Asset.status = "Archived"` khi hoàn tất

Module được **tự động kích hoạt** bởi IMM-13 (on_submit) nhưng cũng có thể khởi tạo thủ công bởi CMMS Admin.

---

## 2. Vị trí trong kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│  IMM-13 (Decommission Request — Completed)                      │
│        │ on_submit → auto-create Asset Archive Record           │
│        ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   IMM-14 — Asset Archive Record (final lifecycle step)   │   │
│  │                                                          │   │
│  │   Workflow 4 states · compile_asset_history()            │   │
│  │   DocType: Asset Archive Record + 1 child                │   │
│  │   API:    assetcore/api/imm14.py    (9 endpoints)        │   │
│  │   Service:assetcore/services/imm14.py                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│        │ on_submit (finalize)                                   │
│        └──► AC Asset.status = "Archived"                        │
│            Asset Lifecycle Event "archived"                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Asset Archive Record` | `AAR-.YY.-.#####` | Yes | Hồ sơ lưu trữ cuối vòng đời — compile toàn bộ tài liệu, báo cáo tóm tắt |

### 3.2 Child Table

| Child DocType | Parent field | Mục đích |
|---|---|---|
| `Archive Document Entry` | `documents` | Danh mục tài liệu được lưu trữ (commissioning, PM, repair, calibration, incident...) |

---

## 4. Actors

| Actor | Vai trò | Hành động chính |
|---|---|---|
| HTM Manager | Giám sát quy trình | Kích hoạt archive, review |
| CMMS Admin | Thực hiện lưu trữ | Compile history, finalize, submit |
| QA Officer | Xác minh | Verify tính đầy đủ của tài liệu |

---

## 5. Service Functions

File: `assetcore/services/imm14.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `create_archive_record(asset, dr_name, ...)` | API + IMM-13 trigger | Tạo AAR record |
| `compile_asset_history(archive_name)` | API (on demand) | Auto-populate `documents` từ tất cả module liên quan |
| `_collect_commissioning_docs(asset)` | internal | Lấy Asset Commissioning records |
| `_collect_pm_records(asset)` | internal | Lấy PM Work Order records |
| `_collect_repair_records(asset)` | internal | Lấy Asset Repair records |
| `_collect_calibration_records(asset)` | internal | Lấy IMM Asset Calibration records |
| `_collect_incident_records(asset)` | internal | Lấy Incident Report records |
| `verify_archive(name, verified_by, notes)` | API | Chuyển Compiling → Verified |
| `finalize_archive(name)` | API | Submit → Archived, set asset.status = Archived |
| `log_lifecycle_event(doc, event_type, ...)` | internal | Sinh immutable ALE |
| `get_asset_full_history(asset_name)` | API | Full timeline mọi sự kiện |
| `get_dashboard_stats()` | API | KPI dashboard |

---

## 6. Workflow States & Transitions

Workflow 4 states.

### 6.1 Bảng trạng thái

| State | doc_status | Mô tả | Actor |
|---|---|---|---|
| `Draft` | 0 | Vừa được tạo (auto từ IMM-13 hoặc thủ công) | CMMS Admin |
| `Compiling` | 0 | Đang tổng hợp tài liệu | CMMS Admin |
| `Verified` | 0 | QA đã xác minh tính đầy đủ | QA Officer |
| `Archived` | 1 | Hoàn tất lưu trữ — terminal | System Manager |

### 6.2 Ma trận chuyển trạng thái

| From → To | Action | Actor |
|---|---|---|
| Draft → Compiling | Bắt đầu tổng hợp | CMMS Admin |
| Compiling → Verified | Xác minh đầy đủ | QA Officer |
| Compiling → Draft | Yêu cầu bổ sung | QA Officer |
| Verified → Archived | Hoàn tất lưu trữ (Submit) | CMMS Admin / System Manager |

---

## 7. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `assetcore.services.imm14.check_archive_expiry` | Monthly | AAR gần đến hạn giải phóng (60 ngày trước) → thông báo | HTM Manager |

---

## 8. Roles & Permissions

| Role | Quyền trên Asset Archive Record |
|---|---|
| IMM HTM Manager | Read |
| IMM QA Officer | Read / Write (verify action) |
| IMM CMMS Admin | Create / Read / Write / Submit |
| System Manager | Full |

---

## 9. Business Rules

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-14-01 | AAR phải link đến Decommission Request hoặc có asset rõ ràng | validate() | NĐ98/2021 |
| BR-14-02 | `retention_years` ≥ 10 — không được giảm xuống dưới 10 | validate() | NĐ98/2021 §17 |
| BR-14-03 | `release_date` = archive_date + retention_years — computed, read-only | validate() / before_save | NĐ98/2021 §17 |
| BR-14-04 | Chỉ Submit khi status = Verified | on_submit | ISO 13485 §4.2 |

---

## 10. KPIs

| KPI | Định nghĩa |
|---|---|
| Archives YTD | Số AAR Archived trong năm |
| Avg Documents per Archive | Số tài liệu trung bình mỗi AAR |
| Missing Document Rate | % Archive Document Entry có status = Missing |
| Expiring Archives (30d) | Số hồ sơ hết hạn lưu trữ trong 30 ngày tới |

---

## 11. Dependencies

| Module | Quan hệ |
|---|---|
| IMM-13 | Nguồn trigger — auto-create AAR trên on_submit |
| IMM-04 | Dữ liệu commissioning |
| IMM-08 | Dữ liệu PM |
| IMM-09 | Dữ liệu repair |
| IMM-11 | Dữ liệu calibration |
| IMM-12 | Dữ liệu incident |
| AC Asset | Output: status = Archived |

---

## 12. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType + child table | IN DEV | `AAR-.YY.-.#####` naming |
| Workflow 4 states | IN DEV | Controller-driven |
| API layer (9 endpoints) | IN DEV | `assetcore/api/imm14.py` |
| Service layer | IN DEV | `assetcore/services/imm14.py` |
| `compile_asset_history()` | IN DEV | Aggregate từ IMM-04/08/09/11/12 |
| Auto-create từ IMM-13 | IN DEV | `on_submit` IMM-13 |
| Frontend Vue 3 | IN DEV | 2 views + store |

---

## 13. Tài liệu liên quan

- `IMM-14_Functional_Specs.md`
- `IMM-14_Technical_Design.md`
- `IMM-14_API_Interface.md`
- `IMM-14_UAT_Script.md`
- `IMM-14_UI_UX_Guide.md`

*End of Module Overview v1.0.0 — IMM-14*
