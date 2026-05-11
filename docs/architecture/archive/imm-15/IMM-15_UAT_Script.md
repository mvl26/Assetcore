# IMM-15 UAT Script

**Module:** IMM-15 — Theo dõi tồn kho phụ tùng (Spare Parts Inventory Tracking)
**Version:** 1.0-draft
**Ngày:** 2026-05-04
**Trạng thái:** PLANNED (Wave 2 — chưa implement). UAT script chuẩn bị trước khi build.

---

## 1. Tổng quan

### 1.1 Mục tiêu UAT

Xác nhận module IMM-15 hoạt động đúng theo Functional Spec, bao gồm:

- Allocation flow (Requested → Approved → Picked → Issued → Returned)
- Emergency override với double-approval (BR-15-03)
- Traceability (batch_no/serial_no) khi `imm_traceability_required=1`
- Cycle Count + Variance CAPA + Stock Reconciliation
- Demand Forecast + Auto Material Request
- Critical Watchlist breach detection + CAPA seed
- Scheduler jobs (low_stock, breach, expiring batch, forecast)
- Permission matrix
- Audit trail completeness
- Integration với IMM-08 PM, IMM-09 Repair, IMM-12 CM
- Tuân thủ RULE-F01..F03 (extend ERPNext core)

### 1.2 Preconditions

| # | Điều kiện | Cách chuẩn bị |
|---|---|---|
| PC-01 | Có ≥ 5 Asset đã mint từ IMM-04 (1 Critical: CT, 1 Major: Monitor) | Chạy IMM-04 flow đến Clinical_Release |
| PC-02 | ERPNext Item group "Medical Spare Part" đã có | Setup script |
| PC-03 | Có ≥ 10 Item: 2 Critical (CT-Tube, MRI-Coil), 4 Major, 4 Consumable | Chạy fixture seed |
| PC-04 | Custom Fields trên Item đã sync (`bench migrate`) | Verify qua Customize Form Item |
| PC-05 | 2 Workflows đã active | Verify Setup > Workflow |
| PC-06 | User role: Storekeeper, Workshop Head, Biomed Engineer, HTM Technician, VP Block 1, Tổ HC-QLCL, CMMS Admin, Accountant | Tạo test users |
| PC-07 | Có ≥ 2 Warehouse (Kho trung tâm, Kho phân xưởng) | ERPNext setup |
| PC-08 | Có Stock Entry Material Receipt seed tồn kho ban đầu | Manual seed |
| PC-09 | Có 1 PM Work Order Approved (IMM-08) chờ allocation | IMM-08 prereq |
| PC-10 | Có 1 CM Work Order Emergency (IMM-12) | IMM-12 prereq |
| PC-11 | Critical Spare Watchlist đã seed cho CT, MRI | Fixture |
| PC-12 | IMM Audit Trail DocType đã active | Verify |

### 1.3 Test Data

| Item | Class | ABC | Min | Max | Lead | Stock đầu | Traceability |
|---|---|---|---|---|---|---|:---:|
| SPARE-CT-TUBE-01 | Critical | A | 1 | 3 | 90 | 1 | ☑ |
| SPARE-MRI-COIL | Critical | A | 1 | 2 | 60 | 1 | ☑ |
| SPARE-MON-BAT | Major | B | 6 | 20 | 30 | 12 | ☐ |
| SPARE-FILT-01 | Consumable | C | 4 | 30 | 14 | 10 | ☐ |
| SPARE-DEF-PAD | Consumable | B | 4 | 20 | 14 | 2 (low) | ☐ |
| SPARE-PUMP-SEAL | Major | B | 2 | 8 | 21 | 0 (out) | ☐ |

| Asset | Loại | Khoa | Watchlist |
|---|---|---|---|
| AC-ASSET-CT-01 | CT Philips | ICU | [SPARE-CT-TUBE-01 min=1] |
| AC-ASSET-MRI-01 | MRI Siemens | Chẩn đoán | [SPARE-MRI-COIL min=1] |
| AC-ASSET-MON-01 | Monitor Philips | ICU | — |
| AC-ASSET-PUMP-01 | Pump | OR | — |

---

## 2. Kịch bản kiểm thử

### TC-15-01: Tạo Allocation từ PM Work Order (Happy Path)

**Actor:** Biomed Engineer (`test_biomed`)
**Precondition:** PC-01, PC-09

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Login với `test_biomed` | Đăng nhập thành công | ☐ |
| 2 | Mở `/imm15/allocations/new` | Form trống, status = Requested | ☐ |
| 3 | Chọn WO Type = "IMM PM Work Order" | DocType picker filter đúng | ☐ |
| 4 | Chọn WO Ref = "WO-PM-2026-0007" | `asset` tự fetch = AC-ASSET-MON-01 | ☐ |
| 5 | Chọn Warehouse from = "Kho trung tâm" | — | ☐ |
| 6 | Urgency = Routine, required_date = today+5 | — | ☐ |
| 7 | Thêm row: SPARE-MON-BAT, qty=2, used_for=Replacement | Cột Available = 12, OK ✅ | ☐ |
| 8 | Click "Tạo & Gửi duyệt" (Lưu Draft) | Doc saved, name = `SAL-2026-#####` | ☐ |
| 9 | Verify naming: regex `SAL-\d{4}-\d{4}` | Đúng | ☐ |
| 10 | Verify workflow_state = "Requested" | Đúng | ☐ |
| 11 | Verify total_value = `12 × unit_value` | Đúng | ☐ |
| 12 | Verify IMM Audit Trail entry "ALLOCATION_CREATED" | Có entry | ☐ |

---

### TC-15-02: Approve + Pick + Issue → Stock Entry

**Actor:** Workshop Head → Storekeeper
**Precondition:** TC-15-01 passed

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | (Workshop Head) Mở allocation | Thấy nút [Approve] | ☐ |
| 2 | Click [Approve] | workflow_state → Approved, approved_by, approval_date set | ☐ |
| 3 | Verify qty_approved = qty_requested mặc định | Đúng | ☐ |
| 4 | (Storekeeper) Click [Pick] | workflow_state → Picked | ☐ |
| 5 | Click [Issue] | Dialog issue: hỏi batch_no (nếu traceability), confirm | ☐ |
| 6 | Confirm (SPARE-MON-BAT không cần batch) | workflow_state → Issued | ☐ |
| 7 | Verify Stock Entry tạo: type="Material Issue", link `imm_allocation_ref` | Đúng | ☐ |
| 8 | Verify Bin.actual_qty(SPARE-MON-BAT, KTT) = 12 - 2 = 10 | Đúng | ☐ |
| 9 | Verify allocation.stock_entry_ref = "SE-..." | Đúng | ☐ |
| 10 | IMM Audit Trail entry "ALLOCATION_ISSUED" | Có entry với actor, payload | ☐ |

---

### TC-15-03: Traceability Required (VR-15-02)

**Actor:** Storekeeper
**Precondition:** SPARE-CT-TUBE-01 (`imm_traceability_required=1`), 1 Allocation Approved

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Tạo allocation cho SPARE-CT-TUBE-01, qty=1 | Saved | ☐ |
| 2 | Approve, Pick | OK | ☐ |
| 3 | Click Issue mà KHÔNG nhập batch_no | Lỗi VR-15-02: "Phụ tùng SPARE-CT-TUBE-01 yêu cầu batch_no/serial_no..." | ☐ |
| 4 | Nhập batch_no = "BATCH-2026-04" | — | ☐ |
| 5 | Click Issue | Success, Stock Entry có batch_no | ☐ |

---

### TC-15-04: Emergency Override (BR-15-03 + VR-15-10)

**Actor:** HTM Technician (request) + Workshop Head + VP Block 1 (override)
**Precondition:** PC-10 (CM WO), tồn kho SPARE-CT-TUBE-01 = 0

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | (HTM Tech) Tạo allocation: WO=CM, urgency=Emergency, item=SPARE-CT-TUBE-01 qty=1 | Saved Requested | ☐ |
| 2 | (Storekeeper) Click Issue | Lỗi REQUIRE_OVERRIDE: stock=0, cần override | ☐ |
| 3 | (Workshop Head) Mở Emergency Override Modal | Modal hiện | ☐ |
| 4 | Approver 2 = Workshop Head (cùng user) | Lỗi VR-15-10: "2 phê duyệt khác nhau" | ☐ |
| 5 | Approver 2 = VP Block 1 | OK | ☐ |
| 6 | Lý do = "CT khẩn cấp ICU 03:00..." (≥ 30 ký tự) | — | ☐ |
| 7 | Confirm Override & Issue | workflow_state → Issued | ☐ |
| 8 | Verify allocation.audit_flags chứa "EMERGENCY_OVERRIDE" | Đúng | ☐ |
| 9 | Verify Bin.actual_qty = -1 (negative cho phép Emergency) hoặc theo policy | Theo policy | ☐ |
| 10 | IMM Audit Trail: 2 actor, action=EMERGENCY_OVERRIDE, payload có reason | Có | ☐ |
| 11 | KPI dashboard: emergency_override_count_30d += 1 | Đúng | ☐ |

---

### TC-15-05: Return Items với QC Gate (BR-15-08)

**Actor:** Storekeeper
**Precondition:** TC-15-02 passed (allocation Issued, qty_issued=2)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở allocation Issued | Thấy nút [Trả phụ tùng] | ☐ |
| 2 | Dialog: SPARE-MON-BAT qty_returned=1, return_condition=Good | — | ☐ |
| 3 | Confirm | workflow_state → Returned | ☐ |
| 4 | Verify Stock Entry Material Receipt vào KTT (Good) | Đúng | ☐ |
| 5 | Verify Bin.actual_qty(SPARE-MON-BAT, KTT) = 10 + 1 = 11 | Đúng | ☐ |
| 6 | Tạo lần return mới với qty_returned=1, condition=Damaged | — | ☐ |
| 7 | Verify Stock Entry vào QC Hold warehouse (KHÔNG vào KTT) | Đúng | ☐ |
| 8 | Verify VR-15-08: qty_returned > qty_issued → throw | Throw lỗi | ☐ |

---

### TC-15-06: Cycle Count với Variance CAPA (BR-15-05)

**Actor:** Storekeeper + Workshop Head + Tổ HC-QLCL
**Precondition:** Bin SPARE-FILT-01 = 10

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | (Storekeeper) Tạo Cycle Count: warehouse=KTT, type=Cycle, items=[SPARE-FILT-01, SPARE-MON-BAT] | Saved Planned | ☐ |
| 2 | Verify system_qty auto-fetch từ Bin: SPARE-FILT-01=10, SPARE-MON-BAT=11 | Đúng | ☐ |
| 3 | Bắt đầu đếm → Counting | OK | ☐ |
| 4 | Nhập counted_qty: SPARE-FILT-01=4, SPARE-MON-BAT=11 | Variance computed | ☐ |
| 5 | Verify variance_pct cho FILT-01 = -60% (vượt 5%) → row đỏ + capa_required=1 | Đúng | ☐ |
| 6 | Cố submit Reviewed mà không nhập root_cause | Lỗi VR-15-04 | ☐ |
| 7 | Nhập root_cause=Damage, notes ngấm nước | — | ☐ |
| 8 | (Workshop Head) Hoàn tất đếm → Reviewed | OK | ☐ |
| 9 | Verify VR-15-11: verified_by ≠ counted_by | Storekeeper khác Workshop Head → OK | ☐ |
| 10 | (Workshop Head) Click [Post] | status → Posted | ☐ |
| 11 | Verify Stock Reconciliation tạo: chỉ có SPARE-FILT-01 (variance ≠ 0) | Đúng | ☐ |
| 12 | Verify Bin.actual_qty(SPARE-FILT-01, KTT) = 4 (counted_qty) | Đúng | ☐ |
| 13 | Verify CAPA seed (link IMM-16) cho SPARE-FILT-01 | CAPA tạo | ☐ |
| 14 | IMM Audit Trail: action=CYCLE_COUNT_POSTED + variance summary | Có | ☐ |

---

### TC-15-07: Critical Watchlist Breach (BR-15-04)

**Actor:** System (scheduler) + Workshop Head
**Precondition:** PC-11; Bin SPARE-CT-TUBE-01 = 0 (sau TC-15-04 Emergency)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Chạy `bench execute assetcore.tasks.check_critical_spare_breach` | — | ☐ |
| 2 | Verify Critical Breach Alert tạo cho (CT-TUBE-01, AC-ASSET-CT-01) | Có 1 record | ☐ |
| 3 | Verify Watchlist.last_breach_date = now, breach_count_30d += 1 | Đúng | ☐ |
| 4 | Verify CAPA seed (IMM-16) | CAPA Open | ☐ |
| 5 | Verify email khẩn gửi Workshop Head + VP Block 1 + CMMS Admin | Email queue có 3 recipients | ☐ |
| 6 | Chạy lại scheduler cùng ngày | KHÔNG tạo duplicate alert | ☐ |
| 7 | Realtime event `imm15.critical_breach_detected` publish | Browser dashboard nhận event | ☐ |

---

### TC-15-08: Demand Forecast + Auto Material Request (BR-15-07)

**Actor:** System + Workshop Head
**Precondition:** Có ≥ 12 tháng consumption data (mock)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Chạy `bench execute assetcore.tasks.generate_demand_forecast` | Forecast Draft tạo | ☐ |
| 2 | Verify forecast.method = "Moving_Avg", items > 0 | Đúng | ☐ |
| 3 | Verify VR-15-07 trên mỗi item: reorder_point ≥ safety_stock | Đúng | ☐ |
| 4 | (Workshop Head) Mở forecast, review | — | ☐ |
| 5 | Click [Approve & Auto-MR] | workflow_state → Approved | ☐ |
| 6 | Verify ERPNext Material Request được tạo cho item có current_qty < reorder_point | MR Draft tạo | ☐ |
| 7 | Verify MR group theo lead_time + warehouse | Đúng | ☐ |
| 8 | Forecast Draft KHÔNG sinh MR (BR-15-07) | Tạo forecast khác Draft, verify không có MR | ☐ |

---

### TC-15-09: Validation Rules

**Actor:** Biomed Engineer + Storekeeper

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| **VR-15-01** | | | |
| 1 | Tạo allocation không link WO, urgency=Routine | Lỗi: "Allocation phải gắn với 1 Work Order..." | ☐ |
| **VR-15-03** | | | |
| 2 | Allocation qty=100 nhưng Bin=12, urgency=Routine, Issue | Lỗi: "Tồn kho hiện tại (12) không đủ..." | ☐ |
| **VR-15-05** | | | |
| 3 | API tạo allocation với urgency="Critical" (sai enum) | Lỗi VR-15-05 | ☐ |
| **VR-15-06** | | | |
| 4 | Sửa Item: imm_min_strategic_stock=10, imm_max=5 | Lỗi VR-15-06 | ☐ |
| **VR-15-08** | | | |
| 5 | Allocation Issued qty=2, return qty=3 | Lỗi VR-15-08 | ☐ |
| **VR-15-09** | | | |
| 6 | Watchlist với spare có imm_part_class=Major | Lỗi VR-15-09: "Chỉ Critical part_class..." | ☐ |
| **VR-15-12** | | | |
| 7 | Forecast với method="LinearReg" | Lỗi VR-15-12 | ☐ |

---

### TC-15-10: Permission Matrix

**Mục đích:** Xác nhận RBAC đúng theo Functional Spec §5

| Action | storekeeper | workshop | biomed | htm_tech | qa | vp_b1 | accountant |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create allocation | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Approve allocation | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Issue allocation | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Approve override | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Cycle count create | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Cycle count Post | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Approve forecast | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Manage Watchlist | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Read dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Test Steps:**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | (storekeeper) Try Approve allocation | Button hidden / 403 | ☐ |
| 2 | (workshop) Try Issue (state Picked) | Button hidden (chỉ Storekeeper) | ☐ |
| 3 | (biomed) Try Post cycle count | 403 | ☐ |
| 4 | (htm_tech) Create allocation Routine | Success | ☐ |
| 5 | (accountant) Read dashboard | Success | ☐ |
| 6 | (accountant) Try create allocation | 403 | ☐ |
| 7 | (qa) Verify cycle count Reviewed | Success | ☐ |

---

### TC-15-11: Scheduler Jobs

**Actor:** System

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Bin SPARE-DEF-PAD = 2, min = 4 → Run `check_low_stock` | Low-Stock Alert tạo, email gửi | ☐ |
| 2 | Run lại cùng ngày | Idempotent (no duplicate) | ☐ |
| 3 | Setup batch SPARE-CT-TUBE-01 expiry = today+90 → Run `check_expiring_batches` | Alert level Info, email Storekeeper | ☐ |
| 4 | Đổi expiry = today+30 → Run lại | Alert level Critical | ☐ |
| 5 | Đổi expiry = today → Run | Alert Danger + flag block-issue | ☐ |
| 6 | Run `compute_inventory_kpis` | IMM Inventory KPI Snapshot today tạo | ☐ |
| 7 | Run `generate_demand_forecast` (manual cho test) | Forecast Draft tạo cho period tới | ☐ |

---

### TC-15-12: Integration với IMM-08 PM Work Order

**Actor:** Biomed Engineer + Storekeeper
**Precondition:** PM Work Order đang được tạo cho AC-ASSET-MON-01

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Trong IMM-08 PM Work Order form, thêm spare list = [{SPARE-MON-BAT: 2}] | — | ☐ |
| 2 | IMM-08 inline gọi `check_part_availability(items, KTT)` | Response: sufficient=true, available=12 | ☐ |
| 3 | Submit PM Work Order | hook `before_submit` reserve spare | ☐ |
| 4 | Verify Bin.reserved_qty(SPARE-MON-BAT) += 2 | Đúng | ☐ |
| 5 | PM Work Order chuyển In_Progress → completion | Auto-tạo IMM Spare Part Allocation Requested | ☐ |
| 6 | Allocation Approved → Picked → Issued (như TC-15-02) | Stock Entry tạo, reserved_qty giảm | ☐ |
| 7 | Verify `get_consumption_by_wo(WO)` trả về allocation + items + value | Đúng | ☐ |
| 8 | Verify NFR-15-02: `check_part_availability` P95 < 300ms | Đo bằng k6 | ☐ |

---

### TC-15-13: Audit Trail Completeness (BR-15-10)

**Mục đích:** Mọi action sinh entry IMM Audit Trail

| Step | Hành động | Verify Audit Trail entry | Pass/Fail |
|---|---|---|:---:|
| 1 | Create allocation | action=ALLOCATION_CREATED, payload có name, asset, urgency | ☐ |
| 2 | Approve allocation | action=ALLOCATION_APPROVED, actor, qty_approved | ☐ |
| 3 | Issue allocation | action=ALLOCATION_ISSUED, stock_entry_ref | ☐ |
| 4 | Emergency override | action=EMERGENCY_OVERRIDE, 2 actors, reason | ☐ |
| 5 | Return items | action=ALLOCATION_RETURNED, qty_returned, condition | ☐ |
| 6 | Cancel allocation | action=ALLOCATION_CANCELLED, reason | ☐ |
| 7 | Cycle count Post | action=CYCLE_COUNT_POSTED, variance_value, capa_seeded | ☐ |
| 8 | Watchlist breach | action=CRITICAL_BREACH_DETECTED | ☐ |
| 9 | ABC reclassify | action=ABC_RECLASSIFIED, item, old_class, new_class | ☐ |
| 10 | Forecast Approve | action=FORECAST_APPROVED, mr_count | ☐ |

---

### TC-15-14: API Endpoints

**Mục đích:** Test ~22 endpoints

| # | Endpoint | Method | Test | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|---|:---:|
| 1 | `list_spare_items` | GET | low_stock_only=true | Chỉ items có actual<min | ☐ |
| 2 | `get_item_inventory_view` | GET | item_code=SPARE-CT-TUBE-01 | Bin breakdown + watchlist | ☐ |
| 3 | `list_allocations` | GET | filter status=Issued | Chỉ Issued | ☐ |
| 4 | `get_allocation` | GET | name=SAL-... | Full doc + child items | ☐ |
| 5 | `create_allocation` | POST | Valid PM | Created Requested | ☐ |
| 6 | `create_allocation` | POST | thiếu work_order_ref + Routine | VR-15-01 | ☐ |
| 7 | `approve_allocation` | POST | Requested + Workshop | Approved | ☐ |
| 8 | `approve_allocation` | POST | Storekeeper role | FORBIDDEN | ☐ |
| 9 | `issue_allocation` | POST | Picked + Storekeeper + đủ | Issued + Stock Entry | ☐ |
| 10 | `issue_allocation` | POST | thiếu batch_no traceability | VR-15-02 | ☐ |
| 11 | `return_items` | POST | Damaged | QC Hold warehouse | ☐ |
| 12 | `cancel_allocation` | POST | Approved | Cancelled | ☐ |
| 13 | `cancel_allocation` | POST | Issued | INVALID_STATE | ☐ |
| 14 | `create_cycle_count` | POST | Valid | Planned | ☐ |
| 15 | `post_cycle_count` | POST | Reviewed + variance + root_cause | Posted + SR + CAPA | ☐ |
| 16 | `get_demand_forecast` | GET | period=2026-Q3 | Doc Approved hoặc Draft | ☐ |
| 17 | `generate_forecast` | POST | method=PM_Driven | Draft tạo | ☐ |
| 18 | `approve_forecast` | POST | Draft | Approved + MR auto | ☐ |
| 19 | `get_critical_watchlist` | GET | — | List + breach status | ☐ |
| 20 | `add_to_watchlist` | POST | spare Major | VR-15-09 | ☐ |
| 21 | `get_dashboard_stats` | GET | — | KPIs + trends | ☐ |
| 22 | `check_part_availability` | GET | items + warehouse | sufficient flag, P95 < 300ms | ☐ |
| 23 | `get_consumption_by_asset` | GET | asset=AC-ASSET-CT-01 | Total + transactions | ☐ |

---

## 3. Test Sign-off

| Nhóm | TC | Pass | Fail | Block | Tester | Ngày |
|---|:---:|:---:|:---:|:---:|---|---|
| Allocation Happy Path | TC-15-01, 02 | — | — | — | | |
| Traceability + Override | TC-15-03, 04 | — | — | — | | |
| Return + QC Gate | TC-15-05 | — | — | — | | |
| Cycle Count | TC-15-06 | — | — | — | | |
| Watchlist Breach | TC-15-07 | — | — | — | | |
| Forecast + Auto MR | TC-15-08 | — | — | — | | |
| Validation Rules | TC-15-09 | — | — | — | | |
| Permission | TC-15-10 | — | — | — | | |
| Scheduler | TC-15-11 | — | — | — | | |
| Integration IMM-08 | TC-15-12 | — | — | — | | |
| Audit Trail | TC-15-13 | — | — | — | | |
| API | TC-15-14 | — | — | — | | |
| **TỔNG** | **14** | — | — | — | | |

### Sign-off Criteria

- **Pass:** 100% TC Pass (0 Fail, 0 Block)
- **Conditional Pass:** ≥ 90% Pass, Fail items đều P2 (cosmetic), có remediation plan
- **Fail:** Bất kỳ P0/P1 Fail → block release. Đặc biệt TC-15-04 (Emergency Override), TC-15-07 (Watchlist breach), TC-15-13 (Audit) là P0.

### Approvers

| Role | Tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Workshop Head đại diện | | | |
| VP Block 1 (PTP Khối 1) | | | |
| Tổ HC-QLCL đại diện | | | |
