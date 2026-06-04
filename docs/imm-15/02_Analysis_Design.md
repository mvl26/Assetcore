# 02 — Phân tích thiết kế nghiệp vụ — IMM-15 Theo dõi tồn kho phụ tùng

> ✅ Module IMPLEMENTED — Wave 2 (`services/imm15.py`, `api/imm15.py`, 14 IMM DocType folders, fixture `imm15_custom_fields.json`). UI một số route chi tiết Allocation/Cycle Count/Forecast chưa wire — xem `_REPORT.md` §TODO.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.0.2 |
| Ngày | 2026-05-27 |
| Trạng thái | IMPLEMENTED — Wave 2 |

---

## I. Module Overview

### I.0. Khảo sát hiện trạng (As-Is)

Khảo sát theo WHO HTM — *Inventory and maintenance 2025* và *Introduction to medical equipment inventory management*: phần lớn bệnh viện VN quản lý phụ tùng phân tán, không có liên kết phụ tùng → Work Order → asset. Pattern truyền thống ghi nhận:

- Mỗi xưởng/kỹ sư giữ kho riêng, không có master chung; thủ kho không nhìn được toàn bộ tồn kho.
- Cấp phát phụ tùng ghi sổ tay/Excel, không gắn Work Order → mất audit trail nguyên nhân tiêu hao.
- Không có Watchlist Critical Spare → khi máy thở/máy gây mê hỏng, phụ tùng có thể đã hết từ trước mà không ai biết.
- Kiểm kê thủ công định kỳ 6–12 tháng/lần, sai lệch >15% so với sổ; không có cycle count theo phân loại ABC/XYZ.
- Không có dự báo nhu cầu part-level — nhập dư hoặc thiếu dựa trên kinh nghiệm.

Chi tiết pain points và quy trình As-Is xem §II.1 và §II.2.

*(Khảo sát cụ thể tại site triển khai — BA bổ sung trong sprint kế tiếp.)*

### I.1. Pitch

Bệnh viện hiện quản lý phụ tùng thiết bị y tế phân tán: mỗi kỹ sư giữ kho riêng, không có hệ thống truy nguyên từ phụ tùng → Work Order → thiết bị. Hệ quả là phụ tùng Critical bị hết khi cần (2–3 lần/tháng), không phát hiện ra cho đến khi kỹ sư ra kho lấy. Số lần máy nằm chờ phụ tùng (asset downtime do spares) chiếm 28% tổng downtime. Kiểm kê thủ công sai lệch >15% so với sổ sách.

**IMM-15 giải quyết:** Xây dựng lớp nghiệp vụ (transaction layer) bên trên AC Inventory Backbone (LIVE — Wave 1) để:
1. Chuẩn hóa cấp phát phụ tùng theo Work Order (không cấp ngoài WO trừ Emergency)
2. Critical Spare Watchlist — cảnh báo tức thì khi tồn Critical xuống dưới ngưỡng
3. Cycle Count workflow — kiểm kê tự động tạo AC Stock Movement Adjustment, variance > 5% → CAPA
4. Dự báo nhu cầu phụ tùng cấp phần tử (part-level), phân biệt rõ với dự báo procurement category-level của IMM-01

### I.2. Vị trí trong WHO HTM Lifecycle

```
Needs → Procurement → Installation → Operation → [MAINTENANCE ← IMM-15] → Decommission

WHO HTM 4.5: Parts & Supplies Management
WHO HTM 5.x: CMMS Support

IMM-15 kết nối:
  IMM-08 (PM) → reserve_for_pm() → IMM Spare Allocation
  IMM-09 (Repair) → reserve_for_repair() → IMM Spare Allocation
  IMM-12 (CM) → Emergency override path
  IMM-16 (Compliance) ← Stock accuracy KPI, breach count
  IMM-17 (Predictive) ↔ Failure-rate driven forecast
```

### I.3. Stakeholders

| Actor | Frappe Role (30-role catalog) | Quan tâm chính |
|---|---|---|
| Thủ kho | `Inventory User` | Pick & issue phụ tùng, kiểm kê chính xác |
| Trưởng phân xưởng / Quản lý kho | `Inventory Manager` | Duyệt allocation, override Emergency, post cycle count |
| Kỹ sư bảo trì / sửa chữa | `Repair User` (CM), `PM User` (PM), `Calibration User` (CAL) | Request phụ tùng theo Work Order |
| Kỹ thuật viên HTM (hỗ trợ kiểm kê) | `Inventory User` | Hỗ trợ kiểm kê chu kỳ |
| Kiểm soát CL / Compliance | `Compliance Manager` / `AssetCore Auditor` | Verify cycle count, gắn CAPA |
| Phó Trưởng khối (override approver 2) | `Inventory Manager` (+ optional `AssetCore Super Admin`) | Phê duyệt override Emergency + forecast |
| Admin hệ thống | `AssetCore Super Admin` | Quản trị, fixtures |
| Trưởng/Phó khoa (read-only) | `AssetCore System User` | Báo cáo read-only |
| Hệ thống (Scheduler) | — | Low-stock, breach, forecast, KPI |

### I.4. Phạm vi

**In Scope:**
- Spare master extension: 7 Custom Fields + alternative parts table trên AC Spare Part
- Critical Spare Watchlist: mapping critical asset → spare + min on-hand + breach alert
- Allocation workflow (6 states): Requested → Approved → Picked → Issued → Returned / Cancelled
- Issue/Return sinh AC Stock Movement (Issue/Receipt) — RULE-F03
- Cycle Count workflow (4 states): Planned → Counting → Reviewed → Posted
- Variance > 5% / 5M VND → CAPA required
- Demand Forecast part-level (phân biệt với IMM-01 category-level)
- ABC/XYZ classification hàng quý
- Low-stock và expiring batch alert
- Emergency override double-approval

**Out of Scope:**
- Procurement workflow (RFQ, PO) — AC Purchase / IMM-02
- Maintenance plan/schedule — IMM-08
- Predictive failure modeling — IMM-17
- Financial accounting — ERPNext Accounts
- Category-level procurement forecast — IMM Demand Forecast (IMM-01)

**Dependencies:**
- AC Spare Part, AC Spare Part Stock, AC Stock Movement (Wave 1 — LIVE)
- IMM-08 (PM Work Order), IMM-09 (Repair), IMM-12 (CM)

### I.5. KPIs

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Stock Turnover | `consumed_value_year / avg_inventory_value` | ≥ 4 |
| Days-on-Hand | `avg_qty_on_hand / daily_consumption` | 30–60 (Critical: 60–90) |
| Stock-out Incidents | Số WO block do thiếu spare/tháng | ≤ 2 |
| Critical Breach Hours | Tổng giờ Watchlist breach/tháng | 0 |
| Cycle Count Accuracy | `1 - Σ|variance_qty| / Σsystem_qty` | ≥ 98% |
| Forecast MAPE | `mean(|actual - forecast| / actual) × 100` | ≤ 25% |
| Emergency Override Count | Số lần bypass BR-15-03/tháng | ≤ 3 |

### I.6. Compliance

| Yêu cầu | Nguồn | Đáp ứng |
|---|---|---|
| Identification & Traceability | ISO 13485 §7.5.8 | imm_traceability_required + batch_no; Allocation link WO + AC Stock Movement |
| Infrastructure | ISO 13485 §6.3 | imm_storage_condition, shelf-life alert |
| Parts & Supplies | WHO HTM 4.5 | Critical Spare Watchlist + min stock + lead-time |
| CAPA Trigger | ISO 13485 §8.5 | BR-15-04 breach, BR-15-05 variance |
| Audit Trail | ISO 13485 §4.2.5 | IMM Audit Trail + AC Stock Movement (submitted) |
| NĐ 98/2021 | NĐ98 | Spare gắn asset có ĐK lưu hành |

### I.7. Rủi ro & Giả định

| # | Loại | Mô tả | Tác động | Hướng xử lý |
|---|---|---|---|---|
| R-15-01 | Rủi ro nghiệp vụ | Emergency Override bị lạm dụng → mất kiểm soát tồn kho | Stock accuracy giảm, audit fail | KPI Emergency Override Count ≤ 3/tháng; double-approval; review hàng tháng |
| R-15-02 | Rủi ro dữ liệu | Cycle Count snapshot stale (>24h) → variance ảo | CAPA sai, gây nhiễu | Warning banner; Inventory Manager refresh snapshot trước Post |
| R-15-03 | Rủi ro phụ thuộc | AC Inventory Backbone (Wave 1) chưa LIVE đầy đủ → IMM-15 không thể go-live | Trì hoãn Đợt 2 | Gate release IMM-15 sau khi AC Backbone LIVE 100% (xem §08 Deployment) |
| R-15-04 | Rủi ro tích hợp | IMM-08/09/12 chưa hoàn tất `reserve_for_*` API | Allocation không tự động tạo từ WO | Pha 1: tạo Allocation thủ công; Pha 2: bật auto-reserve khi PM/CM ổn |
| R-15-05 | Rủi ro chất lượng dự báo | <6 tháng dữ liệu consumption → Forecast Moving_Avg sai lệch lớn | KPI Forecast MAPE >25% | Fallback Manual; cảnh báo Inventory Manager (override 2) |
| R-15-06 | Rủi ro tuân thủ | Thiếu batch_no/serial_no cho phụ tùng có ĐK lưu hành | Vi phạm NĐ98/ISO 13485 | VR-15-02 chặn issue; cấu hình `imm_traceability_required` đúng |

**Giả định:**

- AC Spare Part, AC Spare Part Stock, AC Stock Movement đã được scaffold và LIVE từ Wave 1.
- IMM-08, IMM-09, IMM-12 đã LIVE (Đợt 1) — cung cấp `work_order_ref` để link Allocation.
- IMM-16 (Compliance) cùng Đợt 2 — sẵn sàng nhận CAPA seed từ breach và variance.
- Bệnh viện có chính sách phân loại Critical Spare riêng — BA cấu hình Watchlist theo từng site.

### I.8. Roadmap & Phụ thuộc

**Đợt triển khai:** Đợt 2 (Wave 2 — theo lộ trình AssetCore §"Đợt triển khai").

| Pha | Phạm vi | Tiền đề |
|---|---|---|
| Pha 1 — Master & Allocation | Spare master extension (7 Custom Fields), Allocation workflow 6-state, Issue/Return + AC Stock Movement | AC Inventory Backbone LIVE; IMM-08/09/12 LIVE |
| Pha 2 — Cycle Count & Watchlist | Cycle Count workflow 4-state, Critical Spare Watchlist, breach scheduler | Pha 1 stable; IMM-16 LIVE để nhận CAPA |
| Pha 3 — Forecast & ABC/XYZ | Demand Forecast part-level, ABC/XYZ classification quarterly, reorder recommendation | Pha 1 ≥ 6 tháng dữ liệu consumption |

**Phụ thuộc thượng nguồn:**

- AC Inventory Backbone (Wave 1) — `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement` (RULE-F01..F04).
- IMM-08 (PM Work Order), IMM-09 (Repair), IMM-12 (CM) — cung cấp `work_order_ref`.

**Phụ thuộc hạ nguồn:**

- IMM-16 (Compliance) — nhận breach + variance để mở CAPA.
- IMM-17 (Predictive) — tiêu thụ failure-rate driven forecast.
- IMM-13 (Decommission) — flag `imm_obsolete_review_required` khi asset thanh lý.

**Tham chiếu chuẩn:** WHO HTM — *Inventory and maintenance 2025*, *Introduction to medical equipment inventory management* (phần Parts & Supplies, Stock control, Reorder & forecast).

---

## II. BPMN — Quy trình nghiệp vụ

### II.1. As-Is (Quy trình hiện tại)

```
Kỹ sư cần phụ tùng
  → Đến kho vật lý (phân tán ở từng xưởng)
  → Tự lấy hoặc nhờ thủ kho (không ghi nhận WO)
  → Ghi vào sổ tay / Excel
  → Cuối tháng: đối chiếu thủ công (sai lệch 15%+)
  → Không có cảnh báo tự động khi hết phụ tùng Critical
  → Asset nằm chờ phụ tùng 2-3 ngày
```

### II.2. Pain Points

| # | Vấn đề | Hệ quả |
|---|---|---|
| P-01 | Không liên kết phụ tùng → Work Order | Không có audit trail cấp phát |
| P-02 | Không có Watchlist phụ tùng Critical | Hết phụ tùng phát hiện muộn → downtime |
| P-03 | Kiểm kê thủ công | Sai lệch 15%, mất 2–3 ngày mỗi đợt |
| P-04 | Không có dự báo nhu cầu part-level | Nhập dư/thiếu không có cơ sở |
| P-05 | Phụ tùng nhập kho không ghi lô/ngày hết hạn | Dùng phụ tùng hết date không phát hiện |

### II.3. To-Be Flowchart

```
IMM-08/09/12 WO Submit
        │ reserve_for_pm/repair/cm()
        ▼
  IMM Spare Allocation (Requested)
        │ Inventory Manager approve
        ▼
  IMM Spare Allocation (Approved)
        │ Inventory User pick
        ▼
  IMM Spare Allocation (Picked)
        │ Inventory User issue
        │ → AC Stock Movement (Issue) submitted
        │ → AC Spare Part Stock.qty_on_hand -=
        ▼
  IMM Spare Allocation (Issued)
        │ Returned (partial OK)
        │ → AC Stock Movement (Receipt) submitted
        │ → QC gate: Damaged → to QC Hold warehouse
        ▼
  IMM Spare Allocation (Returned)

  Emergency Path:
    Requested → Issued (double approval: Inventory Manager + Inventory Manager (override 2))
    audit_flags = "EMERGENCY_OVERRIDE"

  Cycle Count (song song):
    Scheduler → Planned → Counting → Reviewed → Posted
                                              → AC Stock Movement (Adjustment)
                                              → seed CAPA if variance > 5% / 5M VND
```

### II.4. Decision Points

| Decision | Yes | No |
|---|---|---|
| urgency = Emergency? | Bypass workflow to double-approval → Issued | Normal flow Requested → Approved |
| imm_traceability_required? | batch_no/serial_no bắt buộc | Không yêu cầu |
| qty_issued > available_qty? | Emergency + Critical → override | Throw VR-15-03 |
| variance_pct > 5% OR variance_value > 5M? | capa_required=1, root_cause bắt buộc | Không cần CAPA |
| Return condition = Damaged? | to_warehouse = QC Hold | to_warehouse = original |

### II.5. RACI Matrix

| Hoạt động | Inventory User | Inventory Manager | Repair User | Inventory Manager (override 2) | Compliance Manager | System |
|---|---|---|---|---|---|---|
| Tạo Allocation Request | C | — | R | — | — | — |
| Approve Allocation | I | R | — | R(override) | — | — |
| Pick & Issue | R | I | — | — | — | — |
| Emergency Override | I | R | — | R | — | A |
| Cycle Count Counting | R | — | — | — | C | — |
| Review Variance | I | R | — | — | R | — |
| Post Adjustment | I | R | — | R | I | — |
| Approve Forecast | I | R | — | R | — | — |
| Breach CAPA trigger | I | I | — | I | R | — |

### II.6. Exception Flows

| Exception | Xử lý |
|---|---|
| PO nhập hàng nhưng không ghi nhận kho | AC Stock Movement (Receipt) trước khi issue |
| Phụ tùng trả về bị hỏng | Return condition=Damaged → to_warehouse=QC Hold; flag for write-off |
| Variance cực lớn (> 50%) | Post blocked — Inventory Manager + Compliance Manager phải ký cả hai |
| Forecast method fail (không đủ 6m data) | Fallback sang Manual; cảnh báo Inventory Manager (override 2) |

---

## III. Use Cases

### III.1. Actor Catalog

| Actor | Hành động chính |
|---|---|
| Inventory User | Pick, Issue, Return, Count |
| Inventory Manager | Approve, Override, Review Variance, Post |
| Repair User | Create Allocation Request |
| Technician | Assist Count |
| Inventory Manager (override 2) | Override Emergency, Approve Forecast |
| Compliance Manager / Auditor | Verify Count, Assign CAPA |
| AssetCore Super Admin | Config, Override, Fixtures |
| Scheduler (System) | Low-stock alert, breach alert, forecast, KPI |

### III.2. UC-01: Cấp phát phụ tùng theo Work Order

| Thuộc tính | Nội dung |
|---|---|
| Actor chính | Repair User (request), Inventory Manager (approve), Inventory User (issue) |
| Pre-condition | WO đang ở trạng thái Open/In Progress; AC Spare Part Stock available_qty > 0 |
| Post-condition | AC Stock Movement (Issue) submitted; AC Spare Part Stock.qty_on_hand giảm; IMM Audit Trail ghi |

**Main Flow:**

| # | Actor | Hành động |
|---|---|---|
| 1 | Repair User | Tạo IMM Spare Allocation với work_order_ref, asset, danh sách spare parts cần |
| 2 | System | Kiểm tra VR-15-01 (WO link bắt buộc), VR-15-13 (warehouse active) |
| 3 | Inventory Manager | Approve Allocation; kiểm tra available_qty |
| 4 | Inventory User | Pick các phụ tùng theo danh sách |
| 5 | Inventory User | Issue — hệ thống tạo AC Stock Movement (Issue, reference_type=IMM Spare Allocation) |
| 6 | System | on_submit AC Stock Movement → apply_stock_movement → qty_on_hand -= |
| 7 | System | Ghi IMM Audit Trail action=ISSUED |

**Alternative: Emergency Override**

| # | Actor | Hành động |
|---|---|---|
| 1a | Repair User | Tạo Allocation với urgency=Emergency |
| 2a | Inventory Manager | Approve Emergency (1/2) |
| 3a | Inventory Manager (override 2) | Approve Emergency (2/2) — VR-15-10: approved_by ≠ override_approver_2 |
| 4a | System | Bypass stock check nếu imm_part_class=Critical; audit_flags=EMERGENCY_OVERRIDE |
| 5a | Inventory User | Issue → AC Stock Movement |

### III.3. UC-02: Kiểm kê chu kỳ (Cycle Count)

| Thuộc tính | Nội dung |
|---|---|
| Actor chính | Inventory User (count), Inventory Manager / Compliance Manager (review), Inventory Manager (post) |
| Pre-condition | Cycle Count session Planned đã tạo với snapshot system_qty từ AC Spare Part Stock |
| Post-condition | AC Stock Movement (Adjustment) submitted; CAPA tạo nếu variance > threshold |

**Main Flow:**

| # | Actor | Hành động |
|---|---|---|
| 1 | Inventory User | Mở phiên Cycle Count, nhập counted_qty cho từng spare |
| 2 | System | Tính variance_qty = counted_qty − system_qty; variance_pct; variance_value |
| 3 | System | VR-15-04: variance_pct > 5% OR variance_value > 5M → set capa_required=1, bắt buộc root_cause |
| 4 | Inventory Manager / QA | Review; VR-15-11: verified_by ≠ counted_by |
| 5 | Inventory Manager | Post → on_submit tạo AC Stock Movement (Adjustment, reference_type=IMM Stock Cycle Count) |
| 6 | System | apply_stock_movement → qty_on_hand := counted_qty |
| 7 | System | seed_capa_for_variance cho items có capa_required=1 |

### III.4. UC Catalog tổng hợp

| UC-ID | Tên | Actor chính | Trigger | Outcome chính |
|---|---|---|---|---|
| UC-01 | Cấp phát phụ tùng theo Work Order | Repair User, Inventory Manager, Inventory User | WO Submit + reserve_for_pm/repair/cm | AC Stock Movement (Issue) submitted; qty_on_hand giảm |
| UC-02 | Kiểm kê chu kỳ (Cycle Count) | Inventory User, Inventory Manager, Compliance Manager | Scheduler / Manual planning | AC Stock Movement (Adjustment) submitted; CAPA seed nếu variance > ngưỡng |
| UC-03 | Cảnh báo Critical Spare Watchlist breach | Scheduler, Inventory Manager, Inventory Manager (override 2) | qty_on_hand < min_required_on_hand | Email khẩn + CAPA seed (IMM-16) |
| UC-04 | Emergency Override cấp phát | Inventory Manager, Inventory Manager (override 2) | urgency=Emergency, stock không đủ | Allocation Issued với audit_flags=EMERGENCY_OVERRIDE; double-approval |
| UC-05 | Trả phụ tùng về kho (Return) | Inventory User, Compliance Manager | Allocation Issued + qty_returned > 0 | AC Stock Movement (Receipt); Damaged → QC Hold |
| UC-06 | Demand Forecast part-level | Scheduler, Inventory Manager (override 2) | Cron tháng (≥6 tháng dữ liệu) | IMM Spare Part Forecast Approved + reorder recommendation |
| UC-07 | ABC/XYZ classification quarterly | Scheduler, Inventory Manager | Cron quý | Cập nhật imm_part_class + imm_xyz_class trên AC Spare Part |
| UC-08 | Quản lý Critical Spare Watchlist (CRUD) | Inventory Manager, Compliance Manager | Asset Critical mới hoặc thay đổi min stock | Watchlist entry active; scheduler theo dõi |

UC-01 và UC-02 đã chi tiết tại §III.2 và §III.3. UC-03..UC-08 chi tiết hoá trong sprint Wave 3 — *(BA bổ sung trong sprint kế tiếp)*.

---

## IV. Functional Specifications

### IV.1. User Stories (Gherkin)

**US-15-01: Allocation theo Work Order**

```gherkin
Given IMM PM Work Order "WO-2026-00234" đang ở trạng thái In Progress
  And AC Spare Part "SP-FILTER-001" có available_qty = 5 tại AC Warehouse "WH-01"
When Repair User tạo IMM Spare Allocation với work_order_ref="WO-2026-00234", qty=2
  And Inventory Manager Approve
  And Inventory User Issue
Then IMM Spare Allocation ở trạng thái Issued
  And AC Stock Movement (Issue) được tạo và submitted
  And AC Spare Part Stock.qty_on_hand = 3 tại WH-01
  And IMM Audit Trail ghi action="ISSUED" với actor=Inventory User
```

**US-15-02: Emergency override khi Critical Spare hết**

```gherkin
Given AC Spare Part "SP-PUMP-CRITICAL" là imm_part_class=Critical, available_qty=0
  And IMM CM Work Order "CM-2026-00089" đang hoạt động (máy thở ICU)
When Repair User tạo Allocation với urgency=Emergency
  And Inventory Manager approve (approver 1)
  And Inventory Manager (override 2) approve (approver 2, khác Inventory Manager)
Then Allocation bypass VR-15-03 stock check
  And audit_flags có "EMERGENCY_OVERRIDE"
  And AC Stock Movement tạo với qty_issued=1 (thậm chí qty_on_hand < 0 — debt)
  And cảnh báo email Inventory Manager (override 2) + AssetCore Super Admin
```

**US-15-03: Cycle Count → CAPA khi variance**

```gherkin
Given IMM Stock Cycle Count "CYC-2026-00012" ở trạng thái Counting
  And IMM Cycle Count Item: spare_part=SP-BATTERY-001, system_qty=10, counted_qty=8
When Inventory User save counted_qty=8
Then variance_qty = -2, variance_pct = 20%
  And capa_required=1 (vì 20% > threshold 5%)
  And root_cause field bắt buộc điền trước khi Review
When Inventory Manager Post
  And verified_by ≠ counted_by (VR-15-11)
Then AC Stock Movement (Adjustment) tạo: qty_on_hand trở thành 8
  And CAPA seed với link IMM-16
```

**US-15-04: Critical Spare Watchlist breach**

```gherkin
Given IMM Critical Spare Watchlist entry:
  critical_asset=AC-ASSET-00045 (máy thở),
  spare_part=SP-CIRCUIT-CRITICAL,
  min_required_on_hand=2, warehouse=WH-01
  And AC Spare Part Stock.qty_on_hand=1 (< 2)
When Scheduler check_critical_spare_breach() chạy
Then watchlist.last_breach_date=now(), watchlist.breach_count_30d += 1
  And CAPA tạo nếu chưa có open CAPA
  And email khẩn gửi Inventory Manager + Inventory Manager (override 2) + AssetCore Super Admin
```

**US-15-05: Demand Forecast part-level**

```gherkin
Given AC Spare Part "SP-FILTER-001" có 12 tháng consumption history
When Scheduler generate_spare_demand_forecast() chạy ngày 1 hàng tháng
Then IMM Spare Part Forecast Draft tạo cho quý tới (method=Moving_Avg)
  And IMM Spare Forecast Item có forecast_qty, reorder_point, safety_stock đúng
  And current_qty = Σ tồn KHẢ DỤNG (qty_on_hand − reserved_qty) toàn kho  # vòng 23
  And recommended_action="Reorder" nếu current_qty < reorder_point
When Inventory Manager (override 2) approve_forecast()
Then Forecast ở trạng thái Approved
  And Dashboard hiển thị reorder recommendations
```

**US-15-06: Low-stock theo tồn KHẢ DỤNG — bin reserved-full (vòng 23, BR-15-17/VR-15-17)**

```gherkin
# Acceptance chính của vòng 23 — RED-prove: TRƯỚC fix scenario này FAIL.
Given AC Spare Part Stock bin (SP-X × WH-01): qty_on_hand=100, reserved_qty=100
  And available_qty=0 (= MAX(0, 100−100)); effective_min=20
When đếm/liệt kê low-stock
Then count_low_stock_bins() ĐẾM bin này vào (TRƯỚC fix: bỏ sót vì 100 ≥ 20)
  And get_low_stock_alerts() drill HIỆN bin này
  And low_stock_part_ids() chứa SP-X
  And get_dashboard_stats.low_stock_alerts == len(get_low_stock_alerts().alerts) == count_low_stock_bins()  # cùng 1 số
  And generate_spare_forecast: current_qty(SP-X) phản ánh available → recommended_action="Reorder" nếu available < reorder_point

# Đối chứng (no false-positive khi không giữ chỗ):
Given bin (SP-Y × WH-01): qty_on_hand=25, reserved_qty=0 (available=25); effective_min=20
Then bin Y KHÔNG low (25 ≥ 20) — y hệt hành vi cũ
```

### IV.2. Business Rules

| BR-ID | Rule | Enforce tại |
|---|---|---|
| BR-15-01 | Mọi consumption phải link Work Order — không issue ngoài WO trừ Emergency | Controller validate allocation |
| BR-15-02 | imm_traceability_required=1 → batch_no/serial_no bắt buộc khi issue | before_submit allocation item |
| BR-15-03 | qty_issued > available_qty → throw; Emergency + Critical → bypass với double-approval | issue_allocation() |
| BR-15-04 | Critical Watchlist breach → trigger CAPA + email khẩn | Scheduler |
| BR-15-05 | Variance > 5% hoặc > 5M VND → capa_required=1, root_cause bắt buộc | VR-15-04 + post handler |
| BR-15-06 | ABC reclassification mỗi quý | Scheduler cron quarterly |
| BR-15-07 | Forecast Approved mới được dùng gợi ý reorder | approve_forecast() gate |
| BR-15-08 | Returned items → QC check; Damaged → kho QC Hold | Workflow Return |
| BR-15-09 | Asset decommissioned → flag imm_obsolete_review_required trên spare | IMM-13 hook |
| BR-15-10 | Mọi allocation, count, override, exception ghi IMM Audit Trail | Service layer |
| BR-15-11 | **Cảnh báo batch sắp hết hạn (cửa sổ `EXPIRY_WINDOW_DAYS`=30):** scheduler `check_expiring_batches` chỉ chọn batch CÒN tồn (`qty_on_hand > 0`) có `nowdate() ≤ expiry_date ≤ add_days(nowdate(), 30)`. Batch hết hạn sau 31+ ngày KHÔNG vào; batch ĐÃ quá hạn (`expiry_date < today`, cờ `is_expired`) KHÔNG vào (đi theo quy trình hủy/quarantine riêng). Email Inventory Manager chỉ khi recipients≠∅ VÀ có batch trong cửa sổ. Số trong subject = `len(expiring)` đúng cửa sổ. **Decision (ghi rõ): batch rỗng (qty=0) BỊ LOẠI** để diệt noise — nếu vận hành muốn cảnh báo cả lô rỗng, gỡ guard `qty_on_hand>0` và cập nhật rule này. | Scheduler daily 03:00 — xem 04 §VII + VR-15-16 |
| BR-15-15 | **Số đã xuất == số đã giữ chỗ** = `COALESCE(NULLIF(qty_approved,0), qty_requested)`. Issue dispense theo số ĐÃ DUYỆT (không phải qty_requested thuần) — điều chỉnh phê duyệt KHÔNG bị bỏ qua; reserved-vs-issued KHÔNG lệch. Helper SoT `effective_alloc_qty(item)` dùng chung cho qty_issued + VR-15-03 gate. Backward-compat: qty_approved chưa set → = qty_requested. | issue_allocation() — xem 04 §III-bis.7 |
| BR-15-16 | **line_value = value_qty × unit_value; total_value = Σ line_value** (lifecycle-aware value_qty = qty_issued nếu đã xuất, ngược lại effective_alloc_qty). MỘT writer duy nhất ở controller validate() — service KHÔNG tự set total_value (tránh clobber requested-based). line_value KHÔNG còn dead column. Sau Issue với approver cắt số → total_value theo số đã xuất (khớp BR-15-15). | controller validate() — xem 04 §III-bis.8 |
| BR-15-17 | **(vòng 23) "Dưới định mức / cần đặt lại" so theo tồn KHẢ DỤNG**, KHÔNG tồn vật lý. Predicate canonical `LOW_STOCK_COND` = `effective_min > 0 AND (qty_on_hand − COALESCE(reserved_qty,0)) < effective_min` (biểu thức RAW, bắt cả oversell). Bin reserved-full (on_hand=100, reserved=100, min=20) ⟹ available=0 < 20 ⟹ **low** (trước đây bị bỏ sót vì 100≥20). Bin reserved=0 GIỮ NGUYÊN hành vi cũ. `count_low_stock_bins`, `low_stock_part_ids`, `get_low_stock_alerts`, `get_dashboard_stats.low_stock_alerts`, scheduler `check_low_stock` dùng CHUNG 1 fragment. `current_qty` forecast + `_sum_part_stock` đổi sang `Σ(qty_on_hand−reserved_qty)` ⟹ `Reorder` kích cho part giữ-chỗ-hết. | `LOW_STOCK_COND` SoT + `_sum_part_stock` — xem 04 §II.A, §III.6.2 |

### IV.3. Validation Rules

| VR-ID | Mô tả | Error Code | Thông báo lỗi |
|---|---|---|---|
| VR-15-01 | work_order_ref bắt buộc trừ Emergency + audit-flagged | BUSINESS_RULE | "VR-15-01: Cấp phát phụ tùng phải liên kết Work Order" |
| VR-15-02 | imm_traceability_required=1 → batch_no/serial_no reqd | VALIDATION | "VR-15-02: Phụ tùng {part} yêu cầu số lô/serial" |
| VR-15-03 | qty_issued ≤ available_qty (= qty_on_hand − reserved_qty THẬT, trừ Emergency+Critical override) — allocation OPEN khác đã giữ chỗ làm available giảm → chống double-issue. Xem **VR-15-14** invariant. | BUSINESS_RULE | "VR-15-03: Tồn kho không đủ — available: {n}" |
| VR-15-04 | variance_pct > 5% / variance_value > 5M → root_cause reqd | VALIDATION | "VR-15-04: Chênh lệch {pct}% — cần nhập nguyên nhân" |
| VR-15-05 | urgency IN {Routine/Urgent/Emergency} | VALIDATION | "VR-15-05: Mức độ khẩn cấp không hợp lệ" |
| VR-15-07 | reorder_point ≥ safety_stock | VALIDATION | "VR-15-07: Điểm đặt hàng phải ≥ safety stock" |
| VR-15-08 | qty_returned ≤ qty_issued | VALIDATION | "VR-15-08: Số lượng trả không được vượt số đã xuất" |
| VR-15-09 | Watchlist: spare phải là Critical, min > 0 | VALIDATION | "VR-15-09: Chỉ phụ tùng Critical mới được thêm vào Watchlist" |
| VR-15-10 | Emergency: approved_by ≠ override_approver_2, cả hai trong _OVERRIDE_ROLES | BUSINESS_RULE | "VR-15-10: Emergency override cần 2 người duyệt khác nhau" |
| VR-15-11 | Cycle count: verified_by ≠ counted_by | BUSINESS_RULE | "VR-15-11: Người kiểm tra phải khác người kiểm kê" |
| VR-15-12 | Forecast method IN {Moving_Avg/PM_Driven/Failure_Rate/Manual} | VALIDATION | "VR-15-12: Phương pháp dự báo không hợp lệ" |
| VR-15-13 | AC Warehouse.is_active=1 | VALIDATION | "VR-15-13: Kho {wh} không còn hoạt động" |
| VR-15-14 | **INVARIANT reservation (SoT):** ∀ bin (warehouse × spare_part): `reserved_qty == Σ qty giữ-chỗ allocation HOLDING {Requested, Approved, Picked}`; `available_qty == MAX(0, qty_on_hand − reserved_qty)`. Issue/Cancel/Return giải phóng reserved (RELEASE on terminal). Một hàm `recompute_reserved` SoT — KHÔNG inline. | — | (invariant, không phải lỗi runtime đơn lẻ — xem 04 §III-bis) |
| VR-15-15 | **INVARIANT data-contract:** ∀ `horizon_months`: field `IMM Spare Forecast Item.historical_consumption_12m` == tổng qty Issue (movement_type='Issue', docstatus=1) của `spare_part` trong CHÍNH XÁC 12 tháng trailing (`CURDATE() − INTERVAL 12 MONTH`) = `get_consumption(part, months=12)`. TÁCH khỏi `lookback_months = max(horizon×4, 12)` (chỉ dùng cho forecast_qty/avg_monthly/reorder_point/safety_stock). Label DB "Tiêu thụ 12 tháng" giữ nguyên. | — | (invariant — xem 04 §III.6.1; bug gốc horizon=6 → 24 tháng → SAI 2×) |
| VR-15-16 | **INVARIANT expiry-window + naming-contract (SoT):** `check_expiring_batches` (1) gate bằng `frappe.db.table_exists("IMM Spare Batch")` — DocType NAME, KHÔNG prefix `tab` (truyền `"tabIMM Spare Batch"` → tìm `tabtabIMM Spare Batch` → luôn False → job chết âm thầm); (2) filter = list-of-conditions `[["expiry_date",">=",nowdate()],["expiry_date","<=",add_days(nowdate(),30)],["qty_on_hand",">",0]]` — **KHÔNG** dict-literal trùng key `expiry_date` (Python nuốt cận trên); (3) field thật `batch_no` trong cả `fields=[]` và HTML render; (4) bỏ `except Exception: pass` quanh filter — chỉ giữ try/except bên trong `_safe_sendmail` (SMTP no-user), KHÔNG dùng để che unknown-column/KeyError. | — | (invariant — xem 04 §VII; bug gốc vòng 21: dup-key + batch_code + gate sai) |
| VR-15-17 | **INVARIANT low-stock = tồn KHẢ DỤNG (SoT, vòng 23):** ∀ bin: `low(bin) ⟺ effective_min>0 ∧ (qty_on_hand − COALESCE(reserved_qty,0)) < effective_min`. Một fragment `LOW_STOCK_COND` (services/inventory.py) — grep **0 chỗ** còn `s.qty_on_hand < effective_min` ngoài fragment (kể cả `api/inventory.py::_list_stock_all` inline). Đồng nhất 3 con số: `get_dashboard_stats.low_stock_alerts == len(get_low_stock_alerts().alerts) == count_low_stock_bins()` (KHÔNG divergence card-vs-drill). `_sum_part_stock` = `SUM(qty_on_hand − COALESCE(reserved_qty,0))` 1 aggregate (no N+1). Biểu thức RAW (KHÔNG cột `available_qty` clamp) để bắt oversell. | — | (invariant — xem 04 §II.A, §III.6.2; bug gốc round-3: low so vật lý → reserved-full bin "đủ tồn") |

### IV.4. Architecture Rules (CRITICAL)

| Rule | Nội dung |
|---|---|
| RULE-F01 | KHÔNG tạo DocType "IMM Spare Item" mới — luôn dùng AC Spare Part |
| RULE-F02 | KHÔNG tạo bảng tồn song song — luôn đọc/ghi qua AC Spare Part Stock |
| RULE-F03 | Mọi movement (Issue/Return/Adjustment) phải sinh AC Stock Movement submitted |
| RULE-F04 | IMM-15 transaction DocType chỉ LINK vào AC Stock Movement qua stock_movement_ref |
| RULE-S01 | Logic nghiệp vụ ở services/imm15.py, KHÔNG ở controller |
| RULE-R01 | `reserved_qty` CHỈ được ghi qua `services.inventory.recompute_reserved` (SoT, tuyệt đối/idempotent). CẤM `reserved_qty +=/-=` rải rác trong imm15.py. **(vòng 23)** Low-stock predicate + forecast `current_qty` so theo tồn **KHẢ DỤNG** `(qty_on_hand − COALESCE(reserved_qty,0))` — KHÔNG còn tồn vật lý thuần (BR-15-17 / VR-15-17). |

### IV.5. Edge Cases

| Case | Xử lý |
|---|---|
| WO bị cancel sau khi Allocation Issued | Allocation ở trạng thái Issued không tự cancel; Inventory User Return thủ công |
| available_qty = 0 + Emergency + non-Critical | Throw VR-15-03 — không bypass |
| reserved_qty > qty_on_hand (điều chỉnh kho giảm tồn khi còn phiếu giữ) | `available_qty` kẹp 0 (before_save MAX(0,…)), KHÔNG âm; reserved giữ nguyên đến khi phiếu Issue/Cancel |
| 2 allocation OPEN cùng bin, on_hand chỉ đủ 1 | #1 giữ chỗ → available=0 → #2 issue FAIL VR-15-03 (anti-oversell). Emergency+Critical vẫn bypass |
| Approve cắt qty_approved (10→4) rồi Issue | Issue dispense **4** (= effective_alloc_qty), KHÔNG phải 10; qty_issued==reserved==4 (BR-15-15). Trước fix: xuất 10 (over-issue) |
| Trả toàn bộ qty về kho | Allocation về Returned; AC Stock Movement (Receipt) |
| Cycle Count snapshot bị stale (> 24h) | Warning banner; Inventory Manager có thể refresh snapshot |
| Forecast với < 6 tháng data | Method fallback → Manual; cảnh báo trong email |
| ABC reclassify đổi từ A → C | Không auto-giảm min_stock_level; chỉ cảnh báo để review thủ công |

---

## V. Non-Functional Requirements

### V.1. Performance

| Chỉ tiêu | Mục tiêu |
|---|---|
| check_part_availability P95 | < 300ms |
| List Allocation (1000 records) | < 2s |
| Post Cycle Count (500 items) | < 10s |
| Scheduler check_critical_spare_breach | < 5 phút cho 500 watchlist entries |

### V.2. Concurrency

- Issue allocation song song trên cùng spare_part: `AC Spare Part Stock.qty_on_hand` consistent qua `FOR UPDATE` lock
- Cycle Count snapshot: atomic read từ `AC Spare Part Stock`

### V.3. Availability

- AC Inventory Backbone (LIVE): 99.5% uptime
- Scheduler jobs: retry 3 lần nếu fail; alert nếu còn fail

### V.4. Compliance

- Audit retention: ≥ 10 năm (ISO 13485 §4.2.5)
- Traceability: mọi Issue có link WO (trừ Emergency-flagged)
- Change control: IMM Audit Trail bất biến sau khi ghi

### V.5. Scalability

- Hỗ trợ ≥ 10,000 AC Spare Part records
- ≥ 100,000 AC Stock Movement records/năm
- Cycle Count: ≥ 1,000 items/session
