# IMM-08 — Preventive Maintenance (Bảo trì Định kỳ)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-08 quản lý toàn bộ vòng đời **bảo trì định kỳ (Preventive Maintenance)** thiết bị y tế: từ thiết lập lịch tự động sau commissioning, scheduler tạo PM Work Order khi đến hạn, phân công KTV, thực hiện theo checklist chuẩn, ghi nhận kết quả/lỗi, đến cập nhật lịch PM kỳ kế tiếp.

Module đảm bảo:

- Không thiết bị nào bị bỏ sót PM (scheduler tự động).
- Mọi action có audit trail (PM Task Log immutable).
- Lỗi phát sinh trong PM tự sinh CM Work Order liên kết ngược (`source_pm_wo`).
- KPI compliance được tính đúng theo `completion_date` chứ không phải `due_date` (BR-08-03).

---

## 2. Vị trí trong kiến trúc

```
┌────────────────────────────────────────────────────────────────┐
│  IMM-04 Installation  ──submit──▶  Asset.commissioning_date    │
│           │                                                    │
│           ▼ on_submit hook                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  IMM-08 Preventive Maintenance                           │  │
│  │                                                          │  │
│  │  PM Schedule (per asset × pm_type)                       │  │
│  │      │ scheduler 06:00 daily                             │  │
│  │      ▼                                                   │  │
│  │  PM Work Order (Open → In Progress → Completed)          │  │
│  │      │ submit                                            │  │
│  │      ├─▶ PM Task Log (immutable)                         │  │
│  │      ├─▶ Asset.custom_last_pm_date / next_pm_date        │  │
│  │      └─▶ CM Work Order (nếu Fail-Minor / Fail-Major)     │  │
│  │            │                                             │  │
│  └────────────┼─────────────────────────────────────────────┘  │
│               ▼                                                │
│         IMM-09 Repair / IMM-12 Corrective                      │
└────────────────────────────────────────────────────────────────┘
```

Kế thừa primitive từ **IMM-00 Foundation** (hiện wave 1 vẫn dùng ERPNext `Asset` core; kế hoạch v3 sẽ chuyển sang `AC Asset`).

---

## 3. DocTypes

### 3.1 Master / Cấu hình (2)

| DocType | Naming | Submittable | Mục đích |
|---|---|---|---|
| `PM Schedule` | `PMS-{asset_ref}-{pm_type}` | No | Lịch PM định kỳ — 1 dòng / cặp (asset, pm_type) |
| `PM Checklist Template` | `PMCT-{asset_category}-{pm_type}` | No | Template checklist chuẩn theo Asset Category × PM Type |

### 3.2 Operational (1)

| DocType | Naming | Submittable | Mục đích |
|---|---|---|---|
| `PM Work Order` | `PM-WO-.YYYY.-.#####` | Yes | Phiếu thực hiện PM (PM hoặc CM-from-PM) |

### 3.3 Audit (1)

| DocType | Naming | Submittable | Mục đích |
|---|---|---|---|
| `PM Task Log` | autoname hash | No (in_create=1) | Nhật ký bất biến mỗi lần PM hoàn thành |

### 3.4 Child tables (2)

| Child DocType | Parent | Mục đích |
|---|---|---|
| `PM Checklist Item` | PM Checklist Template | Định nghĩa mục kiểm tra (template) |
| `PM Checklist Result` | PM Work Order | Kết quả từng mục KTV điền |

**Tổng: 6 DocTypes** (2 master + 1 operational + 1 audit + 2 child).

---

## 4. Service Functions

### 4.1 Scheduler tasks — `assetcore/tasks.py`

| Function | Tần suất | Mô tả |
|---|---|---|
| `generate_pm_work_orders` | Daily 06:00 | Quét PM Schedule có `next_due_date <= today + alert_days_before`, tạo PM Work Order idempotent, clone checklist từ template |
| `check_pm_overdue` | Daily 08:00 | PM WO `Open / In Progress` quá `due_date` → set `status = Overdue`, gửi email leo thang (≤7d Workshop, 8–30d PTP, >30d BGĐ) |

### 4.2 Doctype controller logic — `pm_work_order.py`

| Method | Trigger | Mô tả |
|---|---|---|
| `validate()` | save | Kiểm tra checklist 100% (BR-08-08), ảnh Class III (BR-08-06), CM source (BR-08-02) |
| `on_submit()` | submit | Set completion fields, advance PM Schedule, sync Asset PM dates, tạo PM Task Log, auto-create CM WO khi Fail |

### 4.3 API endpoints — `assetcore/api/imm08.py`

9 whitelisted REST endpoints (xem `IMM-08_API_Interface.md`).

---

## 5. Workflow States — `PM Work Order.status`

```
            ┌─────────────────────────────────────┐
            │                                     │
            ▼                                     │
   ┌─────────────┐ assign_technician  ┌─────────────────────┐
   │    Open     │ ──────────────────▶│    In Progress      │
   └─────────────┘                    └─────────────────────┘
         │                                     │
         │ scheduler (today > due)             │ submit_pm_result
         ▼                                     ▼
   ┌─────────────┐                    ┌─────────────────────┐
   │   Overdue   │ ──── KTV resume ──▶│      Completed      │
   └─────────────┘                    └─────────────────────┘
         │                                     ▲
         │ reschedule_pm                       │ submit (after busy)
         ▼                                     │
   ┌─────────────────────┐                    │
   │ Pending–Device Busy │ ───────────────────┘
   └─────────────────────┘

   ┌────────────────────────┐    Halted state (terminal-ish):
   │ Halted–Major Failure   │    set bởi report_major_failure
   └────────────────────────┘    → tạo CM WO khẩn
                                  → Asset.status = Out of Service
   ┌─────────────┐
   │  Cancelled  │   Workshop Manager huỷ (lý do bắt buộc)
   └─────────────┘
```

7 states: `Open · In Progress · Pending–Device Busy · Overdue · Completed · Halted–Major Failure · Cancelled`.

### Schedulers liên quan

| Job | Cron | Tác động |
|---|---|---|
| `generate_pm_work_orders` | `daily` (06:00) | Tạo `PM Work Order` mới |
| `check_pm_overdue` | `daily` (08:00) | Set `Overdue` + gửi email |

(IMM-04 `Asset Commissioning.on_submit` → tạo `PM Schedule` đầu tiên — xem `services/imm04.py`.)

---

## 6. Roles & Permissions

| Role | PM Schedule | PM Checklist Template | PM Work Order | PM Task Log |
|---|---|---|---|---|
| `Workshop Head` | R/W/Create/Delete | R/W/Create/Delete | R/W/Create/Submit/Cancel | R/Create |
| `CMMS Admin` | R/W/Create/Delete | R/W/Create/Delete | R/W/Create/Submit/Cancel/Delete | R/Create |
| `HTM Technician` | R | R | R/W | R |
| `Biomed Engineer` | R | R | R/W | R |
| `VP Block2` (PTP) | R | R | R | R |
| `System Manager` | full | — | full | R/Create |

(Role names theo wave-1 fixtures — sẽ map sang IMM roles trong v3.)

---

## 7. Business Rules

| ID | Rule | Enforce tại |
|---|---|---|
| BR-08-01 | PM WO phải có Checklist Template tương ứng Asset Category × PM Type trước khi scheduler tạo | `tasks.generate_pm_work_orders` (skip + email Admin nếu thiếu) |
| BR-08-02 | CM WO phát sinh từ PM bắt buộc có `source_pm_wo` | `pm_work_order._validate_cm_source()` + `mandatory_depends_on` |
| BR-08-03 | `next_pm_date = completion_date + pm_interval_days` (KHÔNG tính từ `due_date`) | `pm_work_order._update_pm_schedule()` + `_update_asset_fields()` |
| BR-08-04 | Asset `status = Out of Service` → block tạo PM WO mới | `tasks.generate_pm_work_orders` skip; `report_major_failure` set Out of Service |
| BR-08-05 | PM WO submit sau `due_date` → `is_late = True` | `pm_work_order._set_completion()` |
| BR-08-06 | Asset Class III/C/D bắt buộc upload ảnh trước/sau PM | `pm_work_order._validate_photo_for_high_risk()` |
| BR-08-07 | Mỗi `pm_type` (Quarterly/Semi-Annual/Annual/Ad-hoc) là 1 PM Schedule độc lập | Naming `PMS-{asset_ref}-{pm_type}` đảm bảo unique |
| BR-08-08 | Checklist 100% có result trước khi Submit Completed/Halted | `pm_work_order._validate_checklist_complete()` |
| BR-08-09 | Fail-Minor → tự sinh CM WO priority Medium; Fail-Major → CM WO Critical + Asset Out of Service | `pm_work_order._handle_failures()` |
| BR-08-10 | PM Task Log immutable (no Update/Delete) | DocType `in_create=1`, perms không có `delete` cho user role |

---

## 8. Dependencies

| Module / Component | Phụ thuộc qua |
|---|---|
| **IMM-04 Installation** | `Asset Commissioning.on_submit` → `services.imm04` tạo `PM Schedule` đầu (`first_pm_date = commissioning_date + pm_interval_days`) |
| **IMM-05 Asset Document** | Service Manual là nguồn dữ liệu để Workshop Head soạn `PM Checklist Template` |
| **IMM-09 Repair (CM)** | PM `Halted–Major Failure` hoặc `Fail-*` → tạo `PM Work Order` `wo_type=Corrective` (đóng vai trò CM WO trong wave 1) |
| **IMM-11 Calibration** | Có thể trigger Calibration WO khi PM Type yêu cầu kiểm định cùng kỳ (manual rule) |
| **Asset (ERPNext core)** | Đọc `asset_category`, `custom_risk_class`, `status`; ghi `custom_last_pm_date`, `custom_next_pm_date`, `custom_pm_status` |
| **Frappe Scheduler** | 2 jobs daily |
| **Frappe Email Queue** | Gửi alert leo thang + thông báo Major Failure |

---

## 9. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocTypes (6) | ✅ Đã code | `pm_schedule`, `pm_checklist_template`, `pm_checklist_item`, `pm_work_order`, `pm_checklist_result`, `pm_task_log` |
| Controller `pm_work_order.py` | ✅ | validate + on_submit lifecycle |
| Service / Tasks | ✅ | `tasks.generate_pm_work_orders`, `tasks.check_pm_overdue` |
| API (9 endpoint) | ✅ | `assetcore/api/imm08.py` |
| Frontend (4 view) | ✅ | `PMDashboardView`, `PMCalendarView`, `PMWorkOrderListView`, `PMWorkOrderDetailView` |
| Pinia store | ✅ | `frontend/src/stores/imm08.ts` |
| Hook IMM-04 → IMM-08 | ✅ | `services/imm04.py` tạo PM Schedule on commissioning submit |
| UAT scripts | ✅ | `assetcore/tests/uat_imm08.py` (10 TC) |
| Migration sang IMM-00 v3 (`AC Asset`) | ⚠️ Pending | Wave 1 vẫn dùng `Asset` core + `custom_*` fields |

---

*End of Module Overview v2.0.0 — IMM-08 Preventive Maintenance*
