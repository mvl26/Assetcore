# IMM-15 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.2 (aligned với AC inventory backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — backbone LIVE, IMM transaction layer PLANNED |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | ISO 13485:2016 §7.5.8, §6.3; WHO HTM 4.5; NĐ 98/2021/NĐ-CP |

---

## 0. Phạm vi thay đổi vs hệ thống hiện tại

Xem `IMM-15_Module_Overview.md §2` cho danh sách đầy đủ. Tóm tắt:

- **Đã có (reuse):** `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement` (+ Item), `AC Warehouse`, `AC UOM`, `IMM Device Spare Part`, `Spare Parts Used`, toàn bộ `assetcore/api/inventory.py` (30 endpoint) và `assetcore/services/inventory.py` (`check_low_stock`, `validate/apply/reverse_stock_movement`, `get_available_qty`, `get_stock_overview`, …). Frontend `views/inventory/` (11 màn) đã LIVE cho master + giao dịch.
- **Mở rộng (extend) — fixture mới:** Thêm 7 Custom Field + 1 child table trên `AC Spare Part`: `imm_part_class`, `imm_abc_class`, `imm_xyz_class`, `imm_lead_time_days`, `imm_safety_stock_days`, `imm_traceability_required`, `imm_storage_condition`, `imm_alternative_parts` (table → `IMM Spare Alternative`). KHÔNG trùng các field đã có (`min_stock_level`, `max_stock_level`, `manufacturer_part_no`, `preferred_supplier`, `shelf_life_months`, `is_critical`).
- **Thêm mới (new):** 6 DocType nghiệp vụ (Allocation/Cycle Count/Forecast/Watchlist/Spare Alternative/Spare Batch-gated) + 2 workflow + 5 scheduler + `assetcore/api/imm15.py` (~16 endpoint mới) + `assetcore/services/imm15.py`.
- **Khác biệt cần ghi chú:** `IMM Spare Part Forecast` (PART-level, IMM-15) ≠ `IMM Demand Forecast` đã có (CATEGORY-level, IMM-01). Hai cái song hành, không gộp.

---

## 1. Scope

### 1.1 In Scope

| # | Chức năng | Mô tả |
|---|---|---|
| F-01 | Spare master extension | Mở rộng `AC Spare Part` với 7 CF + 1 alt parts table (`imm_*`) |
| F-02 | Critical Spare Watchlist | Mapping critical asset → spare bắt buộc on-hand |
| F-03 | Allocation theo Work Order | Phiếu cấp phát link WO (PM/CM/Repair) — workflow 6-state |
| F-04 | Issue / Return | Phát sinh `AC Stock Movement` (Issue / Receipt) khi Issue/Return; QC gate cho Return |
| F-05 | Cycle Count | Phiên kiểm kê (Full / ABC-A Monthly / Cycle / Spot) — workflow 4-state, post → `AC Stock Movement` (Adjustment) |
| F-06 | Variance & CAPA | Variance > 5% / 5M VND → required `root_cause` + CAPA (link IMM-16) |
| F-07 | Demand Forecast (part-level) | Snapshot quý: forecast_qty + reorder_point + safety_stock; method Moving Avg / PM-driven / Failure-rate / Manual. Distinct với `IMM Demand Forecast` của IMM-01 |
| F-08 | ABC / XYZ classification | Reclassify hàng quý theo consumption value + biến động |
| F-09 | Low-stock & Expiring alert | Scheduler 90/60/30/0d cho shelf-life (gated `IMM Spare Batch`); daily low-stock alert (extend `services.inventory.check_low_stock`) |
| F-10 | Emergency override | BR-15-03: bypass với double approval (Workshop Lead + Operations Manager) |
| F-11 | Traceability | `imm_traceability_required=1` → batch_no/serial_no bắt buộc khi Issue |
| F-12 | Reorder recommendation | Forecast Approved → recommended_action="Reorder" hiển thị trong dashboard / Spare Forecast Item; integrator chọn tạo `AC Purchase` thủ công (không auto-MR ở Wave 2 — Wave 3 trở đi) |
| F-13 | Dashboard KPI | Stock turnover, days-on-hand, stock-out, critical breach, accuracy, MAPE |
| F-14 | Audit trail | `IMM Audit Trail` + Frappe Version + `AC Stock Movement` (submitted = immutable) cho mọi action |

### 1.2 Out of Scope

| # | Chức năng | Module phụ trách |
|---|---|---|
| 1 | Procurement workflow (RFQ, PO) | `AC Purchase` / IMM-02 (Vendor) |
| 2 | Vendor master & contract | IMM-02 |
| 3 | Maintenance plan & schedule | IMM-08 |
| 4 | Repair / Failure root cause | IMM-09 / IMM-12 |
| 5 | Asset decommission | IMM-13/14 (chỉ trigger obsolete review) |
| 6 | Predictive failure modeling | IMM-17 (chỉ consume failure_rate) |
| 7 | Financial accounting | ERPNext Accounts (read-only inventory value) |
| 8 | Category-level procurement forecast | `IMM Demand Forecast` (IMM-01) |

---

## 2. Actors

| Actor | Vị trí thực tại BV | Quyền chính | Trách nhiệm |
|---|---|---|---|
| IMM Storekeeper | Kho trung tâm & Kho vận | R/W/C, Pick, Issue, Count | Quản lý kho, pick & issue phụ tùng, kiểm kê |
| IMM Workshop Lead | Trưởng Phân xưởng | R/W/C/Cancel/Amend, Approve, Override | Duyệt allocation, override emergency, review variance |
| IMM Biomed Technician | Kỹ sư Biomedical | R/W/C (request) | Tạo allocation request |
| IMM Technician | Kỹ thuật viên HTM | R/W/C (request), Count assist | Hỗ trợ kiểm kê |
| IMM QA Officer / Auditor | Tổ HC-QLCL | R, Verify | Verify cycle count, audit variance, gắn CAPA |
| IMM Operations Manager | Phó Trưởng Khối 1 (KH-TC) | R, Approve override, Approve forecast | Phê duyệt emergency override + forecast quý |
| IMM System Admin | IT/CMMS | Full | Quản trị, override, fixtures |
| IMM Department Head / Deputy | Trưởng/Phó khoa | R | Đối chiếu read-only |
| Vendor Engineer | KS hãng | R (limited) | Read theo hợp đồng |
| System (Scheduler) | — | system-only | Low-stock, breach, expiring, forecast, KPI |

> Mapping role thực tế lấy từ permissions[] trong `AC Spare Part` / `AC Stock Movement` / `AC Warehouse` JSON đã có.

---

## 3. User Stories (Gherkin)

### US-15-01 — Tạo Spare Allocation từ PM Work Order

```gherkin
As IMM Biomed Technician,
I want tạo phiếu cấp phát phụ tùng cho 1 PM Work Order,
So that phụ tùng được reserve và issue đúng theo WO.

Scenario: Tạo allocation hợp lệ
  Given tôi có role IMM Biomed Technician và 1 PM Work Order "WO-PM-2026-0007" Approved
  When tôi POST /api/method/assetcore.api.imm15.create_allocation với
    {work_order_ref: "WO-PM-2026-0007", asset, urgency: "Routine", warehouse_from: "AC-WH-0001",
     items: [{spare_part: "AC-SP-2026-0001", qty_requested: 2, used_for: "Replacement"}]}
  Then response.success = true
  And alc.name khớp regex "^SAL-2026-\d{4}$"
  And alc.workflow_state = "Requested"
  And alc.allocation_status = "Requested"
  And `AC Spare Part Stock.reserved_qty` cho (AC-WH-0001, AC-SP-2026-0001) tăng 2
```

### US-15-02 — Approve & Issue Allocation → AC Stock Movement

```gherkin
As IMM Workshop Lead,
I want approve allocation và Storekeeper issue,
So that AC Stock Movement (Issue) được tạo + tồn kho cập nhật đúng.

Scenario: Approve flow
  Given alc ở "Requested" với items hợp lệ
  When (Workshop Lead) POST approve_allocation(name)
  Then alc.workflow_state = "Approved", approved_by, qty_approved set
  And (Storekeeper) POST issue_allocation(name)
  Then alc.workflow_state = "Issued"
  And 1 AC Stock Movement được tạo: movement_type="Issue", reference_type="IMM Spare Allocation",
       reference_name=alc.name, items[].spare_part = alc.items[].spare_part, items[].qty = qty_issued
  And submit_stock_movement(...) tự động gọi → AC Spare Part Stock.qty_on_hand giảm đúng
  And alc.stock_movement_ref = "AC-SM-2026-#####"
```

### US-15-03 — Emergency Override (BR-15-03)

```gherkin
As IMM Technician,
When CM Work Order khẩn cần Critical spare nhưng tồn kho không đủ,
I trigger Emergency override flow.

Scenario: Override với double-approval
  Given alc.urgency = "Emergency" và item có imm_part_class = "Critical"
  And qty_requested > AC Spare Part Stock.available_qty
  When tôi POST issue_allocation(name)
  Then response.code = "REQUIRE_OVERRIDE"
  When Workshop Lead + Operations Manager cùng approve override
  Then issue được bypass, audit_flags = "EMERGENCY_OVERRIDE"
  And AC Stock Movement Issue được tạo (qty_on_hand có thể về 0 nhưng không âm — chính sách: throw nếu <0)
  And IMM Audit Trail ghi (actor1, actor2, asset, qty, reason)
```

### US-15-04 — Cycle Count với Variance CAPA

```gherkin
As IMM Storekeeper,
I want thực hiện kiểm kê chu kỳ và post variance,
So that tồn kho hệ thống = tồn kho thực tế.

Scenario: Variance > 5% phải có CAPA
  Given cycle count có 1 item: system_qty=100 (snapshot từ AC Spare Part Stock), counted_qty=92
  When tôi nhập counted_qty và submit Reviewed
  Then variance_qty = -8, variance_pct = -8.0%
  And capa_required = 1 (BR-15-05)
  And throw nếu thiếu root_cause (VR-15-04)

Scenario: Post tạo AC Stock Movement Adjustment
  When (Workshop Lead) POST post_cycle_count(name)
  Then status = "Posted"
  And 1 AC Stock Movement movement_type="Adjustment", reference_type="IMM Stock Cycle Count",
       reference_name=cyc.name được tạo & submit
  And AC Spare Part Stock.qty_on_hand được cập nhật về counted_qty
  And cyc.posted_movement_ref = "AC-SM-..."
```

### US-15-05 — Critical Spare Watchlist Breach

```gherkin
As System (scheduler),
When watchlist item có AC Spare Part Stock.qty_on_hand < min_required_on_hand,
I trigger red alert + CAPA seed.

Scenario: Breach detected
  Given Watchlist entry: asset=AC-ASSET-CT-01, spare_part=AC-SP-CT-TUBE, min=1
  And qty_on_hand(AC-SP-CT-TUBE, AC-WH-0001) = 0
  When scheduler check_critical_spare_breach chạy
  Then tạo Critical Breach Alert (idempotent theo (spare_part, asset, alert_date))
  And email khẩn Workshop Lead + Operations Manager + System Admin
  And IMM-16 nhận điểm penalty
```

### US-15-06 — Demand Forecast & Reorder Recommendation

```gherkin
As IMM Workshop Lead,
I want review demand forecast quý và approve,
So that hệ thống đề xuất reorder.

Scenario: Approve forecast
  Given forecast Q3-2026 ở Draft với 42 items
  When tôi POST approve_forecast(name)
  Then forecast.workflow_state = "Approved"
  And mỗi item có current_qty < reorder_point → recommended_action="Reorder"
  And UI hiển thị danh sách reorder để Operations Manager tạo `AC Purchase` thủ công
```

### US-15-07 — Return Items với QC Gate

```gherkin
As IMM Storekeeper,
When Biomed trả phụ tùng dư hoặc gỡ ra từ Asset,
I yêu cầu kiểm QC trước khi nhập kho.

Scenario: Return success
  Given alc đã Issue với qty_issued=5, dùng thực tế = 3
  When POST return_items(name, items=[{spare_part, qty_returned: 2, return_condition: "Good"}])
  Then alc.workflow_state = "Returned" (partial)
  And AC Stock Movement movement_type="Receipt" tạo cho 2 unit về kho gốc
  And nếu condition = "Damaged" → AC Stock Movement to_warehouse = "AC-WH-QC-HOLD"
```

### US-15-08 — Check Part Availability từ IMM-08/09/12

```gherkin
As IMM-08 PM Work Order controller,
Before submit WO,
I check spare availability through IMM-15.

Scenario: Inline check
  Given WO PM cần items [{AC-SP-001: 2}, {AC-SP-002: 1}]
  When IMM-08 gọi check_part_availability(items, warehouse)
  Then response data: [{spare_part, required, available, sufficient: true/false, lead_time_days, alternatives}]
  And nếu insufficient → IMM-08 gợi ý alternative_parts hoặc tạo AC Purchase
```

### US-15-09 — ABC Reclassification quarterly

```gherkin
As IMM System Admin,
Every quarter,
I run ABC reclassification dựa trên consumption value 12 tháng gần nhất.

Scenario: Reclassify
  When chạy bench execute assetcore.services.imm15.forecast_service.reclassify_abc
  Then mỗi AC Spare Part is_active=1 cập nhật imm_abc_class:
    A: top 80% consumption value (~20% items)
    B: tiếp theo 15% (~30% items)
    C: cuối 5% (~50% items)
  And IMM Audit Trail ghi từng transition
```

### US-15-10 — Dashboard tồn kho

```gherkin
As IMM Workshop Lead / Operations Manager,
I want dashboard tồn kho realtime,
So that quản trị tổng thể vật tư.

Acceptance:
  KPI-01 stock_turnover_year
  KPI-02 days_on_hand_avg
  KPI-03 stockout_incidents_30d
  KPI-04 critical_breach_hours_30d
  KPI-05 cycle_accuracy_pct
  KPI-06 forecast_mape_q
  Top 10 low-stock items (đỏ < min_stock_level)
  Top 10 critical breach watchlist
  Consumption trend 90 ngày (PM/CM/Repair stack — derive từ AC Stock Movement.reference_type)
```

---

## 4. Business Rules

| ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-15-01 | Allocation phải link Work Order (trừ Emergency có audit flag) | Controller `validate()` | Internal |
| BR-15-02 | `imm_traceability_required=1` → batch_no/serial_no reqd khi Issue | `before_submit` allocation item | ISO 13485 §7.5.8 |
| BR-15-03 | `qty_issued > AC Spare Part Stock.available_qty` → throw; Emergency + Critical → bypass với double-approval | `issue_allocation()` | WHO HTM 4.5 |
| BR-15-04 | Critical spare breach → trigger CAPA + email khẩn | Scheduler `check_critical_spare_breach` | ISO 13485 §8.5 |
| BR-15-05 | Cycle count variance > 5% hoặc > 5M VND → required CAPA + root_cause | VR-15-04 + post handler | ISO 13485 §8.5 |
| BR-15-06 | ABC reclassification quarterly | Service `reclassify_abc()` | Internal |
| BR-15-07 | Forecast Approved mới được dùng để gợi ý reorder; chưa auto tạo `AC Purchase` (Wave 3) | `approve_forecast()` gate | Internal |
| BR-15-08 | Returned items → QC Hold trước khi nhập kho lại nếu condition=Damaged | Workflow Return + service `process_return` | ISO 13485 §7.5.8 |
| BR-15-09 | Asset decommissioned → spare gắn duy nhất model → flag `imm_obsolete_review_required` | IMM-13 hook | Internal |
| BR-15-10 | Mọi action ghi `IMM Audit Trail` (allocation, count, override, exception). `AC Stock Movement` (submitted) là evidence chính. | Service layer wrap | NĐ 98, ISO 13485 |

---

## 5. Permission Matrix

> Mapping với role đã định nghĩa trong các DocType `AC *` JSON.

| Action | Storekeeper | Workshop Lead | Biomed Tech | Technician | QA/Auditor | Operations Mgr | System Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| View spare list | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit AC Spare Part custom_fields (`imm_*`) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create allocation | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Approve allocation | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Issue allocation (submit AC Stock Movement) | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Approve override (Emergency) | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cycle count create/edit | ✅ | ✅ | ❌ | ✅ (assist) | ❌ | ✅ | ✅ |
| Cycle count Review | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Cycle count Post (submit AC Stock Movement Adjustment) | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Generate forecast | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Approve forecast | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage Watchlist | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

`_APPROVE_ALLOCATION_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}`
`_ISSUE_ROLES = {"IMM Storekeeper", "IMM Operations Manager", "IMM System Admin"}`
`_OVERRIDE_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}` (cần ≥ 2 actor khác nhau)

---

## 6. Validation Rules

| VR ID | Field / Trigger | Rule | Error Message |
|---|---|---|---|
| VR-15-01 | Allocation `work_order_ref` | reqd trừ khi `urgency="Emergency"` AND audit flag set | "VR-15-01: Allocation phải gắn với 1 Work Order, hoặc đánh dấu Emergency với lý do." |
| VR-15-02 | Allocation Item `batch_no`/`serial_no` | reqd khi `AC Spare Part.imm_traceability_required=1` AND `qty_issued>0` | "VR-15-02: Phụ tùng {part} yêu cầu batch_no/serial_no khi Issue (traceability)." |
| VR-15-03 | Issue qty | `qty_issued ≤ AC Spare Part Stock.available_qty` (FOR UPDATE) (trừ Emergency override) | "VR-15-03: Tồn kho hiện tại ({avail}) không đủ cho yêu cầu ({req}). Cân nhắc Emergency override." |
| VR-15-04 | Cycle Count Item `root_cause` | reqd khi `|variance_pct| > 5` hoặc `|variance_value| > 5_000_000` | "VR-15-04: Chênh lệch vượt ngưỡng — bắt buộc nhập Nguyên nhân và đánh dấu CAPA." |
| VR-15-05 | Allocation `urgency` | IN {Routine/Urgent/Emergency} | "VR-15-05: Mức ưu tiên không hợp lệ ({u})." |
| VR-15-06 | (deprecated) min/max trên `AC Spare Part` | Đã enforce ở `AC Spare Part` controller (`min_stock_level ≤ max_stock_level`). IMM-15 không re-validate. | — |
| VR-15-07 | Forecast Item `reorder_point` | `≥ safety_stock` | "VR-15-07: Reorder point phải ≥ safety stock." |
| VR-15-08 | Allocation Item `qty_returned` | `≤ qty_issued` | "VR-15-08: Số lượng trả ({r}) không thể lớn hơn số đã cấp ({i})." |
| VR-15-09 | Watchlist `min_required_on_hand` | `> 0` và `AC Spare Part.imm_part_class="Critical"` | "VR-15-09: Watchlist chỉ áp dụng cho phụ tùng Critical với min on-hand > 0." |
| VR-15-10 | Emergency Override | cần đúng 2 approver khác nhau IN `_OVERRIDE_ROLES` | "VR-15-10: Emergency override yêu cầu 2 phê duyệt khác nhau." |
| VR-15-11 | Cycle Count `verified_by` ≠ `counted_by` | segregation of duties | "VR-15-11: Người verify phải khác người đếm." |
| VR-15-12 | Forecast `method` | IN {Moving_Avg/PM_Driven/Failure_Rate/Manual} | "VR-15-12: Phương pháp dự báo không hợp lệ." |
| VR-15-13 | (mới) Allocation `warehouse_from` | reqd, phải trỏ về `AC Warehouse.is_active=1` | "VR-15-13: Kho xuất không hợp lệ hoặc đã ngưng hoạt động." |

---

## 7. Non-Functional Requirements

| ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-15-01 | Performance — list spare | `list_spare_parts` (đã có) với 5k items + 50k movements | P95 < 2s |
| NFR-15-02 | Performance — check_part_availability | call từ IMM-08/09/12 | P95 < 300ms |
| NFR-15-03 | Concurrency | Issue allocation song song | `AC Spare Part Stock.qty_on_hand` atomic (FOR UPDATE qua `services.inventory._upsert_stock`) |
| NFR-15-04 | Audit | Mọi action ghi IMM Audit Trail + AC Stock Movement (submitted) | track_changes=1 + audit table |
| NFR-15-05 | Availability | Giờ hành chính + ca trực | 99.5% |
| NFR-15-06 | Concurrent users | Đồng thời | 30 users |
| NFR-15-07 | Data retention | Allocation, Cycle Count, AC Stock Movement | ≥ 10 năm (NĐ98) |
| NFR-15-08 | Scheduler reliability | Idempotent | Alert log unique theo (spare_part, alert_date) |
| NFR-15-09 | i18n | Error messages | `frappe._()` tiếng Việt |
| NFR-15-10 | API contract | Response chuẩn | `_ok()` / `_err()` |
| NFR-15-11 | Forecast accuracy | MAPE quý | ≤ 25% sau 4 quý warm-up |
| NFR-15-12 | Mobile UI | Cycle count trên tablet/phone | Responsive ≥ 360px |

---

## 8. Acceptance Criteria

| ID | Scenario | Pass criterion |
|---|---|---|
| AC-15-01 | Tạo allocation hợp lệ | name đúng pattern, workflow_state="Requested", `AC Spare Part Stock.reserved_qty` cập nhật |
| AC-15-02 | Approve + Issue → AC Stock Movement | `AC Stock Movement` (Issue) submitted, `qty_on_hand` giảm đúng, `stock_movement_ref` set |
| AC-15-03 | Emergency override | Cần 2 approver khác nhau, audit flag, throw nếu chỉ 1 |
| AC-15-04 | VR-15-02 traceability | Throw khi traceability_required=1 mà thiếu batch/serial |
| AC-15-05 | Cycle count variance CAPA | variance > 5% → required root_cause + capa_required=1 |
| AC-15-06 | Cycle count Post | Tạo `AC Stock Movement` Adjustment, `qty_on_hand` về `counted_qty` |
| AC-15-07 | Watchlist breach scheduler | Idempotent, email khẩn, CAPA seed |
| AC-15-08 | Forecast Approved → reorder list | UI hiển thị danh sách item cần reorder |
| AC-15-09 | check_part_availability | P95 < 300ms, trả đúng sufficient flag (dựa `available_qty`) |
| AC-15-10 | ABC reclassify | Phân hạng đúng top 80/15/5 consumption value |
| AC-15-11 | Return QC gate | Damaged → AC Stock Movement to_warehouse = AC-WH-QC-HOLD |
| AC-15-12 | Audit trail completeness | Mọi action có entry IMM Audit Trail + AC Stock Movement (submitted) |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| Spare Allocation | Phiếu cấp phát phụ tùng cho 1 Work Order, có workflow 6-state |
| Cycle Count | Phiên kiểm kê chu kỳ (Full/ABC-A Monthly/Cycle/Spot) |
| Critical Spare Watchlist | Mapping critical asset → spare bắt buộc on-hand |
| Demand Forecast (part-level) | Snapshot dự báo nhu cầu phụ tùng theo quý — `IMM Spare Part Forecast`, KHÁC `IMM Demand Forecast` (category-level, IMM-01) |
| Emergency Override | Bypass kiểm tra tồn kho cho Critical spare khi khẩn cấp, cần double-approval |
| Reorder Point | Mức tồn kho gợi ý tạo phiếu mua |
| Safety Stock | Tồn kho an toàn để đệm biến động cầu / lead-time |
| ABC class | A=top 80% giá trị tiêu thụ, B=15%, C=5% |
| XYZ class | X=biến động thấp, Y=trung bình, Z=cao (nhu cầu) |
| Days-on-Hand | Số ngày tồn kho hiện đáp ứng được mức tiêu thụ trung bình |
| Stock Turnover | Số lần quay vòng tồn kho / năm |
| MAPE | Mean Absolute Percentage Error |
| `AC Stock Movement` | Phiếu giao dịch của AC layer (LIVE) — tương đương Stock Entry của ERPNext, IMM-15 dùng làm record cho Issue/Receipt/Adjustment |
| `AC Spare Part Stock` | Bảng tồn của AC layer (LIVE) — tương đương Bin của ERPNext |
| RULE-F01..F04 | 4 nguyên tắc extension AC layer (xem Module Overview §9) |
