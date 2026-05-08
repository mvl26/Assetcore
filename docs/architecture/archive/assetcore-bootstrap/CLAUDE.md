# AssetCore — CLAUDE.md
# Tài liệu context bắt buộc đọc trước khi làm bất cứ việc gì

---

## 1. TỔNG QUAN DỰ ÁN

| Thuộc tính | Giá trị |
|---|---|
| Tên hệ thống | AssetCore (IMMIS CH1) |
| Mục tiêu | Quản lý vòng đời tài sản thiết bị y tế theo WHO HTM/CMMS |
| Nền tảng | Frappe Framework v15 + ERPNext v15 |
| Tên app Frappe | `assetcore` |
| Ngôn ngữ backend | Python 3.11 |
| Ngôn ngữ frontend | JavaScript / Vue (Frappe standard) |
| Cơ sở dữ liệu | MariaDB 10.11 |
| Chuẩn nghiệp vụ | WHO HTM, CMMS, ISO 9001, Nghị định 98/2021/NĐ-CP Việt Nam |
| Khách hàng mục tiêu | Bệnh viện Nhi Đồng 1, TP.HCM |

---

## 2. KIẾN TRÚC 4 KHỐI – 17 MODULE

```
KHỐI 1 — PLANNING & PROCUREMENT
  IMM-01  Đánh giá nhu cầu và dự toán
  IMM-02  Thông số kỹ thuật và phân tích thị trường
  IMM-03  Đánh giá nhà cung cấp và quyết định mua sắm

KHỐI 2 — DEPLOYMENT & IMPLEMENTATION
  IMM-04  Lắp đặt, định danh và kiểm tra ban đầu        ← ĐỢT 1 ƯU TIÊN
  IMM-05  Đăng ký, cấp phép và hồ sơ                    ← ĐỢT 1 ƯU TIÊN
  IMM-06  Đào tạo người dùng

KHỐI 3 — OPERATIONS & MAINTENANCE
  IMM-07  Theo dõi hiệu suất
  IMM-08  Bảo trì định kỳ (PM)                           ← ĐỢT 1 ƯU TIÊN
  IMM-09  Sửa chữa, phụ tùng và cập nhật phần mềm       ← ĐỢT 1 ƯU TIÊN
  IMM-10  Hậu kiểm và tuân thủ
  IMM-11  Hiệu năng và hiệu chuẩn                        ← ĐỢT 1 ƯU TIÊN
  IMM-12  Bảo trì khắc phục (CM)                         ← ĐỢT 1 ƯU TIÊN
  IMM-15  Theo dõi tồn kho phụ tùng
  IMM-16  Theo dõi tuân thủ
  IMM-17  Phân tích dự đoán

KHỐI 4 — END-OF-LIFE
  IMM-13  Ngừng sử dụng và điều chuyển
  IMM-14  Giải nhiệm thiết bị
```

**Đợt 1 (ưu tiên):** IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12
**Đợt 2:** IMM-01, IMM-02, IMM-03, IMM-06, IMM-15, IMM-16
**Đợt 3:** IMM-07, IMM-10, IMM-13, IMM-14, IMM-17

---

## 3. CẤU TRÚC APP FRAPPE

```
assetcore/
├── CLAUDE.md                          ← File này
├── setup.py
├── requirements.txt
├── assetcore/
│   ├── __init__.py
│   ├── hooks.py
│   ├── patches.txt
│   ├── modules.txt
│   │
│   ├── imm_master/                    ← Master data dùng chung
│   │   ├── doctype/
│   │   │   ├── imm_device_model/
│   │   │   ├── imm_asset_profile/
│   │   │   ├── imm_location_ext/
│   │   │   └── imm_audit_trail/
│   │   └── __init__.py
│   │
│   ├── imm_deployment/                ← IMM-04, IMM-05, IMM-06
│   │   ├── doctype/
│   │   │   ├── imm_commissioning_record/
│   │   │   └── imm_document_repository/
│   │   └── __init__.py
│   │
│   ├── imm_operations/                ← IMM-08, IMM-09, IMM-11, IMM-12
│   │   ├── doctype/
│   │   │   ├── imm_pm_work_order/
│   │   │   ├── imm_cm_work_order/
│   │   │   ├── imm_calibration_record/
│   │   │   └── imm_incident_report/
│   │   └── __init__.py
│   │
│   ├── imm_planning/                  ← IMM-01, IMM-02, IMM-03
│   │   └── __init__.py
│   │
│   └── imm_eol/                       ← IMM-13, IMM-14
│       └── __init__.py
```

---

## 4. NGUYÊN TẮC BẮT BUỘC — KHÔNG ĐƯỢC VI PHẠM

### 4.1. Nguyên tắc dữ liệu

```
RULE-D01: Mọi IMM DocType phải có field `asset` (Link → Asset)
RULE-D02: Mọi IMM DocType phải có field `imm_status` (Select)
RULE-D03: Mọi thay đổi trạng thái phải ghi vào IMM Audit Trail
RULE-D04: Không xóa record — chỉ dùng is_cancelled = 1
RULE-D05: Naming series bắt buộc cho mọi transaction DocType
RULE-D06: Timestamp tự động cho mọi event (creation, modified)
RULE-D07: Mọi document đính kèm phải link về asset hoặc transaction
```

### 4.2. Nguyên tắc ERPNext/Frappe

```
RULE-F01: KHÔNG override/sửa Core ERPNext DocType (Asset, Asset Repair, v.v.)
RULE-F02: Mở rộng bằng cách tạo DocType mới có Link về core DocType
RULE-F03: Dùng Custom Field nếu chỉ cần thêm 1-2 field vào core DocType
RULE-F04: Workflow bắt buộc cho mọi DocType có approval flow
RULE-F05: Role Permission phải bám theo actor thật (không dùng System Manager cho nghiệp vụ)
RULE-F06: Dùng Frappe Scheduler cho automation định kỳ
RULE-F07: Frappe hooks.py để đăng ký events, scheduler, permissions
```

### 4.3. Nguyên tắc code

```
RULE-C01: Mỗi DocType controller phải có validate(), before_submit(), on_submit()
RULE-C02: Mỗi controller phải có file test tương ứng (test_*.py)
RULE-C03: Dùng frappe.throw() không dùng raise Exception()
RULE-C04: Log lỗi bằng frappe.log_error()
RULE-C05: Tất cả text người dùng thấy phải wrap bằng _() để i18n
RULE-C06: Không hardcode tên khoa, tên bệnh viện trong code
RULE-C07: Dùng frappe.get_doc() và frappe.db.get_value() đúng cách
```

---

## 5. NAMING CONVENTION

### 5.1. DocType names
- Master data: `IMM [Entity Name]` — ví dụ: `IMM Device Model`, `IMM Location Ext`
- Transaction: `IMM [Module Code] [Document Type]` — ví dụ: `IMM PM Work Order`, `IMM CM Incident Report`
- Child table: `IMM [Parent] [Child]` — ví dụ: `IMM PM Checklist Item`

### 5.2. Naming series cho transaction DocType
```
IMM-04-COM-.YYYY.-.####    → IMM Commissioning Record
IMM-05-DOC-.YYYY.-.####    → IMM Document Repository
IMM-08-PM-.YYYY.-.####     → IMM PM Work Order
IMM-09-CM-.YYYY.-.####     → IMM CM Work Order
IMM-11-CAL-.YYYY.-.####    → IMM Calibration Record
IMM-12-INC-.YYYY.-.####    → IMM Incident Report
```

### 5.3. Module name trong Frappe
- `imm_master`
- `imm_deployment`
- `imm_operations`
- `imm_planning`
- `imm_eol`

### 5.4. Field naming
- Link fields: `asset`, `device_model`, `location`, `assigned_technician`
- Status fields: `imm_status`, `workflow_state`
- Date fields: `scheduled_date`, `completion_date`, `due_date`
- Boolean flags: `is_cancelled`, `is_overdue`, `requires_approval`
- Child tables: `checklist_items`, `spare_parts_used`, `document_attachments`

---

## 6. ROLE MAP (ACTOR → FRAPPE ROLE)

| Actor thực tế | Frappe Role | Quyền chính |
|---|---|---|
| Trưởng phòng VT,TBYT | IMM Department Head | Approve, View All, Report |
| PTP Khối 2 (CMMS) | IMM Operations Manager | Approve WO, View Dashboard |
| Kỹ thuật viên TBYT | IMM Technician | Create/Edit WO, Complete Task |
| Nhân viên hồ sơ | IMM Document Officer | Create/Edit Document |
| Trưởng workshop | IMM Workshop Lead | Approve Repair, Assign Tech |
| Nhân viên kho | IMM Storekeeper | View/Edit Spare Parts |
| QLCL | IMM QA Officer | CAPA, Audit, Compliance |
| Admin CNTT | IMM System Admin | Full access |

---

## 7. SCHEMA ERPNext HIỆN CÓ (KHÔNG ĐƯỢC DUPLICATE)

Các bảng sau **đã tồn tại** trong ERPNext — chỉ LINK tới, không tạo lại:

| ERPNext DocType | Dùng cho | Quan hệ với AssetCore |
|---|---|---|
| `Asset` | Master tài sản | Tất cả IMM DocType link về đây |
| `Asset Repair` | Sửa chữa cơ bản | IMM CM Work Order extend thêm field |
| `Asset Maintenance` | Bảo trì cơ bản | IMM PM Work Order link về đây |
| `Asset Maintenance Log` | Log bảo trì | IMM PM Work Order tạo log tại đây |
| `Asset Movement` | Điều chuyển | IMM-13 dùng kết hợp |
| `Asset Category` | Phân loại tài sản | IMM Device Model tham chiếu |
| `Location` | Vị trí | IMM Location Ext mở rộng |
| `Asset Activity` | Lịch sử activity | AssetCore ghi vào đây |
| `Supplier` | Nhà cung cấp | IMM Vendor Profile link về đây |

### Custom Fields được phép thêm vào Core DocType:
```
Asset:
  + imm_device_model (Link → IMM Device Model)
  + imm_medical_device_class (Select: Class I/II/III)
  + imm_registration_number (Data) — số đăng ký BYT
  + imm_serial_number_manufacturer (Data) — S/N nhà sản xuất
  + imm_lifecycle_status (Select: Active/Inactive/Under Repair/Calibrating/Decommissioned)
  + imm_risk_class (Select: Low/Medium/High/Critical)
  + imm_department (Link → Department)
  + imm_responsible_technician (Link → User)
  + imm_last_pm_date (Date)
  + imm_next_pm_date (Date)
  + imm_last_calibration_date (Date)
  + imm_next_calibration_date (Date)
```

---

## 8. WORKFLOW STATES CHUẨN

### Pattern workflow chung cho WO (Work Order):
```
Draft → Scheduled → Assigned → In Progress → Pending Review → Completed → Verified → Closed
                                           ↘ Cancelled
                                           ↘ Escalated → [quay về In Progress]
```

### Pattern workflow cho Document/Record:
```
Draft → Submitted → Under Review → Approved → Active
                               ↘ Rejected → [quay về Draft]
      Expired ← [tự động khi quá hạn]
```

### Pattern workflow cho Incident/CM:
```
Reported → Triaged → Assigned → Diagnosing → In Repair → Testing → Completed → Closed
                              ↘ Escalated
                              ↘ Waiting Parts
```

---

## 9. AUTOMATION / SCHEDULER

```python
# hooks.py — scheduler jobs
scheduler_events = {
    "daily": [
        "assetcore.imm_operations.scheduler.check_pm_due_dates",
        "assetcore.imm_operations.scheduler.check_calibration_expiry",
        "assetcore.imm_deployment.scheduler.check_document_expiry",
        "assetcore.imm_operations.scheduler.escalate_overdue_wo",
    ],
    "hourly": [
        "assetcore.imm_operations.scheduler.sync_asset_lifecycle_status",
    ]
}
```

---

## 10. HƯỚNG DẪN LÀM VIỆC VỚI CLAUDE CODE

### Khi được yêu cầu build một DocType mới:
1. Đọc Module Spec Sheet tương ứng trong `/docs/specs/`
2. Kiểm tra RULE-F01: có trùng với ERPNext core không?
3. Tạo folder `assetcore/[module]/doctype/[doctype_name]/`
4. Tạo 4 file: `[name].json`, `[name].py`, `[name].js`, `test_[name].py`
5. Đăng ký trong `modules.txt` và `hooks.py`
6. Chạy `bench migrate` để kiểm tra
7. Viết ít nhất 3 test case: create, validate_error, workflow_transition

### Khi được yêu cầu build Workflow:
1. Tạo file `[module]/workflow/[workflow_name].json`
2. Map đúng states, transitions, roles theo ROLE MAP ở mục 6
3. Đăng ký trong hooks.py fixtures

### Khi được yêu cầu build Scheduler:
1. Tạo file `[module]/scheduler.py`
2. Đăng ký trong hooks.py `scheduler_events`
3. Viết test với mock datetime

### Thứ tự ưu tiên khi có conflict thiết kế:
```
1. Nghiệp vụ bệnh viện > 2. Tương thích ERPNext > 3. Performance > 4. Code elegance
```

---

## 11. CÁC FILE QUAN TRỌNG CẦN ĐỌC

```
/docs/specs/                   → Module Spec Sheet cho từng module
/docs/data-dictionary.md       → Data Dictionary toàn hệ thống
/docs/workflow-map.md          → Workflow state map chi tiết
/docs/role-permission-matrix.md → Ma trận phân quyền
/fixtures/                     → Demo data và fixture data
```

---

## 12. ĐỊNH NGHĨA "DONE" CHO MỖI DOCTYPE

Một DocType được coi là DONE khi:
- [ ] File JSON tạo được DocType đúng cấu trúc
- [ ] Controller Python có validate(), before_submit(), on_submit()
- [ ] Workflow được tạo và gán vào DocType
- [ ] Permission được set đúng theo Role Map
- [ ] Naming series hoạt động
- [ ] Ít nhất 3 test case pass
- [ ] Audit trail ghi được khi submit
- [ ] `bench migrate` không có lỗi
