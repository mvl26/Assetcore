# IMM-11 — Calibration / Hiệu chuẩn

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-11 — Calibration / Hiệu chuẩn |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | DRAFT — chưa implement code |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-11 quản lý toàn bộ chu trình hiệu chuẩn (calibration) thiết bị y tế đo lường: lập lịch tự động, thực hiện qua lab ISO/IEC 17025 hoặc nội bộ, lưu chứng chỉ, xử lý kết quả Fail bằng CAPA bắt buộc và Lookback assessment trên các thiết bị cùng `device_model`.

Module nằm trong Wave 1 và **chưa có code backend** (`api/imm11.py`, `services/imm11.py`, các DocType chuyên dụng đều chưa tồn tại). Toàn bộ tài liệu là đặc tả ahead-of-code; mọi mục đánh dấu `⚠️ Pending implementation` cần triển khai trước khi bật module.

**Nguyên tắc kiến trúc kế thừa từ IMM-00:**

| Nguyên tắc | Nội dung |
|---|---|
| Reuse foundation | IMM-11 dùng `AC Asset`, `AC Supplier`, `IMM Device Model`, `IMM SLA Policy`, `IMM CAPA Record`, `Asset Lifecycle Event` của IMM-00 — không tạo mới các entity tương đương. |
| Service layer | Mọi business logic đặt trong `assetcore/services/imm11.py`; controller chỉ delegate. |
| Vendor Calibration Lab | Lab hiệu chuẩn là `AC Supplier` với `vendor_type = "Calibration Lab"` và `iso_17025_certified = 1` (BR-00-06). |
| HTM fields trên Asset | Trạng thái calibration nằm trên `AC Asset` (`calibration_status`, `next_calibration_date`, `last_calibration_date`) — không sidecar profile. |
| Audit trail | Mọi action phải gọi `log_audit_event()` + `create_lifecycle_event()`. |

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  IMM-00 Foundation                                               │
│   AC Asset · AC Supplier (iso_17025_certified)                   │
│   IMM Device Model (calibration_interval_days)                   │
│   IMM SLA Policy · IMM CAPA Record · Asset Lifecycle Event       │
│   Services: get_sla_policy · validate_asset_for_operations       │
│             create_capa · log_audit_event · create_lifecycle_event│
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│  IMM-11 Calibration  (⚠️ Pending implementation)                 │
│                                                                  │
│   DocTypes (đề xuất):                                            │
│     • IMM Calibration Schedule  (CAL-SCH-.YYYY.-.#####)          │
│     • IMM Asset Calibration     (CAL-.YYYY.-.#####)  submittable │
│     • IMM Calibration Measurement  (child)                       │
│                                                                  │
│   Services: assetcore/services/imm11.py                          │
│   API:      assetcore/api/imm11.py                               │
│   Schedulers: 3 daily jobs                                       │
└──────────────┬───────────────────────────────────────────────────┘
               │ trigger
               ▼
       IMM-04 commissioning  →  tạo Calibration Schedule đầu tiên
       IMM-09 repair          →  recalibration sau sửa chữa
       IMM-12 corrective      →  CAPA escalation khi Fail nghiêm trọng
```

---

## 3. DocTypes (đề xuất)

⚠️ Pending implementation — JSON DocType, controller, fixtures đều chưa tồn tại.

| DocType | Naming | Loại | Mục đích |
|---|---|---|---|
| IMM Calibration Schedule | `CAL-SCH-.YYYY.-.#####` | Non-submittable | Master record chu kỳ calibration của 1 asset; nguồn cho scheduler tạo WO. |
| IMM Asset Calibration | `CAL-.YYYY.-.#####` | Submittable | Phiếu hiệu chuẩn 1 lần thực hiện; immutable sau Submit (BR-11-05). |
| IMM Calibration Measurement | (child) | Child | Kết quả từng tham số đo (nominal, tolerance, measured, pass/fail). |

**Tái sử dụng từ IMM-00:** `IMM CAPA Record`, `Asset Lifecycle Event`, `IMM Audit Trail`, `AC Asset`, `AC Supplier` (Calibration Lab), `IMM Device Model`, `IMM SLA Policy`.

---

## 4. Service Functions (đề xuất)

⚠️ Pending implementation — file `assetcore/services/imm11.py` chưa tồn tại.

| Function | Caller | Mô tả |
|---|---|---|
| `create_calibration_schedule_from_commissioning(commissioning_doc)` | IMM-04 `on_submit` | Tạo Calibration Schedule đầu tiên dựa trên `Device Model.calibration_interval_days`. |
| `create_due_calibration_wos()` | Scheduler daily | Tạo draft `IMM Asset Calibration` cho các Schedule có `next_due_date <= today + 30`. |
| `check_calibration_expiry()` | Scheduler daily | Cập nhật `calibration_status` (On Schedule / Due Soon / Overdue). |
| `handle_calibration_pass(cal_doc)` | `on_submit` Pass | Cập nhật `last_calibration_date` / `next_calibration_date`, log lifecycle event `calibration_completed`. |
| `handle_calibration_fail(cal_doc)` | `on_submit` Fail | (BR-11-02) `transition_asset_status(→ Out of Service)` + `create_capa()` + lookback. |
| `perform_lookback_assessment(device_model, exclude_asset)` | `handle_calibration_fail` | Trả về danh sách `AC Asset` cùng `device_model` đang Active (BR-11-03). |
| `create_post_repair_calibration(asset)` | IMM-09 `on_submit` | Tạo CAL WO sau sửa chữa nếu thiết bị có Schedule active. |
| `compute_measurement_results(measurements)` | `before_submit` | Set `out_of_tolerance`, `pass_fail`, `overall_result`. |

**Phụ thuộc IMM-00 services (bắt buộc gọi qua, không reimplement):**

| IMM-00 Service | Dùng cho |
|---|---|
| `get_sla_policy(priority, risk_class)` | Tra SLA cho calibration WO theo `risk_classification` của asset. |
| `validate_asset_for_operations(asset)` | Gate trước khi tạo CAL WO (BR-00-05). |
| `transition_asset_status(asset, to_status, ...)` | Chuyển asset Out of Service / Active (BR-00-02, BR-00-04, BR-00-10). |
| `create_capa(asset, source_type="Asset Calibration", ...)` | Auto-create CAPA khi Fail (BR-11-02). |
| `log_audit_event(...)` | Mỗi state change, mỗi submit (BR-00-03). |
| `create_lifecycle_event(asset, event_type, ...)` | `calibration_scheduled`, `calibration_sent_to_lab`, `calibration_completed`, `calibration_failed`, `calibration_conditionally_passed`. |

---

## 5. Workflow States

Áp dụng cho `IMM Asset Calibration` (submittable). State machine quản lý qua controller hooks.

| State | Mô tả | Actor đặt | Điều kiện vào |
|---|---|---|---|
| Scheduled | Lịch đã tạo, chờ thực hiện | Scheduler / Workshop Lead | Schedule đến hạn trong 30 ngày |
| Sent to Lab | Đã bàn giao thiết bị cho lab | IMM Technician | Track External; có `lab_supplier`, `sent_date` |
| In Progress | Đang đo nội bộ | IMM Technician | Track In-House |
| Certificate Received | Đã nhận chứng chỉ, chờ nhập số liệu | IMM Technician | Track External; có `certificate_file` |
| Passed | Tất cả tham số trong tolerance | System (auto) | `before_submit` + `overall_result = Passed` |
| Failed | ≥1 tham số ngoài tolerance | System (auto) | `before_submit` + `overall_result = Failed` → trigger CAPA |
| Conditionally Passed | CAPA Closed + recalibration Pass | System (auto) | CAPA closed + new CAL Pass cho cùng asset |
| Cancelled | Hủy lịch (chỉ trước Submit) | Workshop Lead | Manual cancel khi `docstatus = 0` |

```
[Scheduled] ─ External ─► [Sent to Lab] ─► [Certificate Received] ─┐
     │                                                              │
     └─ In-House ──────────► [In Progress] ─────────────────────────┤
                                                                    │
                                          ┌──── all params Pass ───►[Passed]
                                          │
                                          └──── any param Fail ───►[Failed]
                                                                    │
                                              CAPA Closed +         │
                                              recalibration Pass ◄──┘
                                                    │
                                                    ▼
                                          [Conditionally Passed]
```

---

## 6. Roles & Permissions

Tái sử dụng 8 role IMM-00.

| Role | Quyền chính trong IMM-11 |
|---|---|
| IMM Workshop Lead | Create/Write/Submit `IMM Asset Calibration`, `IMM Calibration Schedule`; phân công KTV, chọn lab |
| IMM Technician | Read/Write `IMM Asset Calibration` (chỉ assigned); upload certificate, nhập measurement |
| IMM Operations Manager | Read all; xem dashboard, compliance report |
| IMM QA Officer | Read CAL; Write/Close `IMM CAPA Record` (lookback findings, RCA) |
| IMM Department Head | Read all; nhận escalation overdue > 30 ngày |
| IMM System Admin | Quản lý DocType, scheduler, fixtures |
| IMM Storekeeper | Read CAL; Write `AC Supplier` (Calibration Lab) |
| IMM Document Officer | Read CAL + Audit Trail |

Permission Query: IMM Technician chỉ xem `IMM Asset Calibration` mà `technician = session.user` hoặc `assigned_by = session.user`.

---

## 7. Business Rules

| ID | Business Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-11-01 | Track External: bắt buộc `lab_supplier` (AC Supplier với `vendor_type=Calibration Lab` và `iso_17025_certified=1`), `certificate_file`, `lab_accreditation_number` trước Submit | `IMMAssetCalibration.validate()` | ISO/IEC 17025; BR-00-06 |
| BR-11-02 | Submit với `overall_result = Failed` → tự động `transition_asset_status(→ Out of Service)` + `create_capa()` bắt buộc | `IMMAssetCalibration.on_submit()` → `handle_calibration_fail()` | ISO 13485:8.5.2; NĐ98 Đ.40 |
| BR-11-03 | Lookback assessment bắt buộc khi Fail: list toàn bộ `AC Asset` cùng `device_model` đang `lifecycle_status=Active`. CAPA chỉ Close được khi `lookback_status != Pending` | `perform_lookback_assessment()` + `IMMCAPARecord.before_submit()` | WHO HTM §5.4.6 |
| BR-11-04 | `next_calibration_date = certificate_date + Device Model.calibration_interval_days` (tính từ ngày cấp chứng chỉ, KHÔNG từ due_date) | `handle_calibration_pass()` | Internal |
| BR-11-05 | `IMM Asset Calibration` immutable sau Submit. Không Cancel/Delete; chỉ Amend với `amendment_reason` bắt buộc | Submittable + `on_cancel` block | ISO 13485:4.2.5; NĐ98 Đ.40 |
| BR-11-06 | Decommissioned asset → suspend Calibration Schedule (BR-00-04 cascade) | `transition_asset_status()` IMM-00 | WHO HTM |
| BR-11-07 | Khi tạo CAL WO, gate `validate_asset_for_operations()` — block nếu asset Out of Service / Decommissioned (trừ recalibration sau CAPA — flag `is_recalibration=1`) | `services/imm11.py` create entry | BR-00-05 |

---

## 8. Dependencies

### 8.1 IMM-00 services (mandatory)

| IMM-00 element | IMM-11 sử dụng |
|---|---|
| `get_sla_policy()` | Tính SLA response/resolution cho CAL WO. |
| `validate_asset_for_operations()` | Gate tạo CAL WO mới. |
| `transition_asset_status()` | Chuyển asset Out of Service khi Fail; Active sau recalibration Pass. |
| `create_capa()` | Auto-create CAPA khi Fail (BR-11-02). |
| `log_audit_event()` | Mọi state change của CAL record. |
| `create_lifecycle_event()` | 5 event types: `calibration_scheduled/sent_to_lab/completed/failed/conditionally_passed`. |
| `AC Supplier.iso_17025_certified` | Validate lab trước Submit (BR-11-01). |
| `IMM Device Model.calibration_interval_days` | Tính `next_calibration_date`. |
| `AC Asset.calibration_status` | Snapshot trạng thái cal hiện tại trên Asset. |
| `AC Asset.next_calibration_date` | Field driver cho overdue scheduler. |

### 8.2 Module hàng xóm

| Module | Chiều | Trigger |
|---|---|---|
| IMM-04 Installation | IN | `on_submit` Commissioning → `create_calibration_schedule_from_commissioning()` |
| IMM-05 Registration | IN | Cung cấp `device_model`, IFU specs (tolerance) |
| IMM-08 PM | BOTH | CAL có thể link `pm_work_order`; KPI tính riêng |
| IMM-09 Repair | IN | `on_submit` repair completed → `create_post_repair_calibration()` cho thiết bị đo lường |
| IMM-12 Corrective | OUT | CAPA từ Fail nghiêm trọng có thể escalate Incident Report P2 |
| IMM-13 End of Life | OUT | Decommission → suspend Schedule (BR-11-06) |

---

## 9. Trạng thái triển khai (DRAFT)

⚠️ Toàn bộ module **chưa có code**. Bảng tracking các artefact cần build:

| Artefact | Status | Ghi chú |
|---|---|---|
| `assetcore/api/imm11.py` | ❌ Pending | Chưa tồn tại |
| `assetcore/services/imm11.py` | ❌ Pending | Chưa tồn tại |
| DocType `IMM Calibration Schedule` JSON + controller | ❌ Pending | — |
| DocType `IMM Asset Calibration` JSON + controller | ❌ Pending | Submittable |
| Child DocType `IMM Calibration Measurement` JSON | ❌ Pending | — |
| Custom fields trên `AC Asset` (`calibration_status`, `next_calibration_date`, `last_calibration_date`) | ❌ Pending | Cần fixtures |
| Workflow JSON cho `IMM Asset Calibration` | ❌ Pending | — |
| Hooks: `on_submit` IMM-04 → `create_calibration_schedule_from_commissioning` | ❌ Pending | hooks.py registration |
| Hooks: `on_submit` IMM-09 → `create_post_repair_calibration` | ❌ Pending | — |
| Scheduler: `create_due_calibration_wos` (daily) | ❌ Pending | — |
| Scheduler: `check_calibration_expiry` (daily) | ❌ Pending | — |
| Scheduler: CAPA overdue (reuse IMM-00 `check_capa_overdue`) | ✅ Available | IMM-00 đã có |
| Permission fixtures + Permission Query | ❌ Pending | — |
| Frontend views + Pinia store | ❌ Pending | Mockup only — xem UI/UX Guide |
| Test suite (target 70% coverage) | ❌ Pending | — |

**Roadmap đề xuất (sau khi IMM-00 v3 implement xong):**

| Sprint | Hạng mục |
|---|---|
| 11.1 | DocType JSON + controller skeleton + custom fields trên AC Asset |
| 11.2 | Service layer (services/imm11.py) + integrate IMM-00 services |
| 11.3 | API layer (api/imm11.py) + scheduler jobs + hooks |
| 11.4 | Workflow JSON + permission fixtures |
| 11.5 | Frontend (CalibrationDashboard, CalibrationForm, CAPA panel) |
| 11.6 | Test suite + UAT execution |

---

## 10. KPI Definitions

| KPI | Công thức | Target |
|---|---|---|
| Calibration Compliance Rate | `Completed on time / Total scheduled × 100%` | ≥ 95% |
| Out-of-Tolerance Rate | `Failed CAL / Total CAL × 100%` | < 5% |
| CAPA Closure Rate (30d) | `Closed within 30d / Total opened × 100%` | ≥ 90% |
| Certificate Storage Coverage | `Assets with valid cert / Total calibratable assets` | 100% |
| Avg Days Sent → Cert Received | `AVG(certificate_date - sent_date)` | ≤ 14 ngày |

---

## 11. QMS & Compliance Mapping

| Yêu cầu | WHO HTM | ISO Standard | NĐ 98/2021 |
|---|---|---|---|
| Calibration interval theo IFU | §5.4.2 | ISO 13485 §7.6 | Điều 38 |
| Lab ISO/IEC 17025 | §5.4.3 | ISO/IEC 17025 | Điều 39 K.1 |
| Measurement traceability | §5.4.4 | ISO/IEC 17025 §6.5 | Điều 39 K.2 |
| Fail → CAPA bắt buộc | §5.4.5 | ISO 13485 §8.5.2 | Điều 40 K.1 |
| Lookback assessment | §5.4.6 | ISO 13485 §8.5.3 | Điều 40 K.2 |
| Immutable records (7 năm) | §6.4 | ISO 13485 §4.2.5 | Điều 40 K.3 |

---

## 12. Tài liệu liên quan

- [Functional Specs](IMM-11_Functional_Specs.md) — FR, BR, VR, NFR, Gherkin
- [Technical Design](IMM-11_Technical_Design.md) — ERD, data dictionary, service layer
- [API Interface](IMM-11_API_Interface.md) — Endpoint specs (Pending)
- [UI/UX Guide](IMM-11_UI_UX_Guide.md) — Frontend mockups
- [UAT Script](IMM-11_UAT_Script.md) — Test cases (Pending execution)
