# IMM-08 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |
| Môi trường | UAT / Staging |
| Người phê duyệt | Workshop Manager · VP Block2 · QA Officer |

---

## 0. Phạm vi UAT

10 test cases (TC-08-01 → TC-08-10) bao trùm:

- Auto-create WO + idempotency
- Happy path submit + lifecycle update
- Overdue detection + escalation
- Minor / Major failure flow
- BR-08-04 block Out of Service
- Calendar + Dashboard UI
- Hook IMM-04 → IMM-08 (commissioning auto-tạo PM Schedule)
- Mobile checklist UX

**Ngưỡng chấp nhận (DoD):**

- ≥ 8/10 TC Pass.
- TC-08-01, TC-08-02, TC-08-03, TC-08-05 **bắt buộc** Pass.
- Không có Critical bug chưa xử lý.

---

## 1. Dữ liệu seed

| Mã seed | Asset | Risk | PM Type | next_due_date | Ghi chú |
|---|---|---|---|---|---|
| SEED-PM-01 | AC-ASSET-UAT-001 | II | Quarterly | hôm nay | Happy path |
| SEED-PM-02 | AC-ASSET-UAT-002 | II | Annual | today − 10 | Overdue case |
| SEED-PM-03 | AC-ASSET-UAT-003 | III | Quarterly | hôm nay | Major Failure case (cần ảnh) |
| SEED-PM-04 | AC-ASSET-UAT-004 | II | Quarterly | hôm nay | Out of Service case |

PM Checklist Template `PMCT-Mechanical Ventilator-Quarterly` với ≥ 5 items (≥ 1 critical).

User test: `ktv_test@hospital.vn` (HTM Technician), `wm_test@hospital.vn` (Workshop Head), `ptp_test@hospital.vn` (VP Block2).

Seed script: `bench --site miyano execute assetcore.scripts.uat.uat_imm08.setup_seed`.

---

## 2. Test Cases

### TC-08-01 — Tự động tạo PM Work Order

**BR liên quan:** BR-08-01 (template), BR-08-04 (Out of Service skip), idempotent.
**Actor:** Scheduler.
**Seed:** SEED-PM-01.

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | `bench --site miyano execute assetcore.tasks.generate_pm_work_orders` | Hoàn thành không lỗi, log `[IMM-08] generate_pm_work_orders: N WOs created` | ☐ |
| 2 | Truy cập `/pm/work-orders?asset_ref=AC-ASSET-UAT-001` | 1 PM WO mới, status=Open, due_date=hôm nay | ☐ |
| 3 | Email Workshop Head | Có email `[AssetCore] N PM Work Order mới được tạo hôm nay` | ☐ |
| 4 | Mở `/pm/calendar` | SEED-PM-01 hiển thị ngày hôm nay với màu vàng/Open | ☐ |
| 5 | Chạy lại scheduler (idempotent) | KHÔNG tạo WO thứ 2 cho cùng schedule | ☐ |

---

### TC-08-02 — Happy path: Phân công + Submit đúng hạn

**BR liên quan:** BR-08-03 (next_pm_date), BR-08-05 (is_late), BR-08-08 (checklist 100%), BR-08-10 (Task Log immutable).
**Actor:** Workshop Head → KTV.
**Tiền điều kiện:** TC-08-01 Pass, có WO Open.

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | WM mở `/pm/work-orders/{name}`, click "Phân công" → ktv_test | Status = "In Progress", assigned_to/by set | ☐ |
| 2 | Login KTV, mở WO | Hiển thị checklist clone từ template | ☐ |
| 3 | Điền tất cả items = Pass + giá trị đo trong range | Progress bar 100% | ☐ |
| 4 | Tích "Đã gắn sticker", nhập duration_minutes=45 | Form valid, nút "Hoàn thành" enable | ☐ |
| 5 | Click "Hoàn thành" | API `submit_pm_result` 200, response `new_status="Completed"`, `is_late=false`, `next_pm_date` đúng | ☐ |
| 6 | Kiểm tra PM Schedule | `last_pm_date=today`, `next_due_date=today+pm_interval_days` (BR-08-03) | ☐ |
| 7 | Kiểm tra PM Task Log | 1 entry mới, `is_late=false`, `days_late=0` | ☐ |
| 8 | Thử update PM Task Log qua UI/console | Bị block (no write perm) — BR-08-10 | ☐ |
| 9 | Kiểm tra Asset | `custom_last_pm_date=today`, `custom_next_pm_date=today+interval`, `custom_pm_status="On Schedule"` | ☐ |

---

### TC-08-03 — Overdue + Escalation

**BR liên quan:** BR-08-05.
**Actor:** Scheduler → Workshop Head + VP Block2.
**Seed:** SEED-PM-02 (due_date = today − 10).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | Tạo PM WO cho SEED-PM-02 (nếu chưa có) | WO due_date=today−10, status=Open | ☐ |
| 2 | `bench --site miyano execute assetcore.tasks.check_pm_overdue` | Hoàn thành, log `N WOs marked Overdue` | ☐ |
| 3 | Kiểm tra WO | status = "Overdue" | ☐ |
| 4 | Kiểm tra dashboard `/pm/dashboard` | SEED-PM-02 trong bảng "Quá hạn", màu đỏ | ☐ |
| 5 | Kiểm tra email Workshop Head | Có alert "PM WO ... quá hạn 10 ngày" | ☐ |
| 6 | Kiểm tra email VP Block2 (vì 8 ≤ 10 ≤ 30) | Có email leo thang | ☐ |
| 7 | KTV submit kết quả Pass | `is_late=true`, `days_late=10` | ☐ |
| 8 | KPI compliance giảm | Dashboard hiển thị compliance_rate_pct giảm | ☐ |

---

### TC-08-04 — Phát hiện Fail-Minor → CM WO tự sinh

**BR liên quan:** BR-08-09 (auto CM), BR-08-02 (source_pm_wo).
**Actor:** KTV.
**Seed:** WO mới của SEED-PM-01 (sau reset).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | KTV mở WO, điền 9/10 items = Pass | Progress 90% | ☐ |
| 2 | Item #4 (không Critical) chọn `Fail-Minor`, nhập notes | Notes mandatory enforce (VR-08-06) | ☐ |
| 3 | Item #10 = Pass | Progress 100% | ☐ |
| 4 | overall_result = "Pass with Minor Issues", submit | Status = Completed | ☐ |
| 5 | Kiểm tra CM WO mới | `wo_type=Corrective`, `source_pm_wo` trỏ về WO này (BR-08-02) | ☐ |
| 6 | CM WO `technician_notes` | Chứa "Tạo tự động từ PM failure. Lỗi: ..." | ☐ |
| 7 | Asset.status | Vẫn "Active" (không bị Out of Service) | ☐ |

---

### TC-08-05 — Major Failure → Asset Out of Service

**BR liên quan:** BR-08-04, BR-08-09.
**Actor:** KTV → Workshop Head + VP Block2.
**Seed:** SEED-PM-03 (Class III).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | KTV mở WO của SEED-PM-03 | Banner "Class III ⚠ Cần ảnh" hiển thị | ☐ |
| 2 | Đánh dấu item Critical = `Fail-Major` | Toast warning, nút "Báo lỗi Major" highlight | ☐ |
| 3 | Click "Báo lỗi Major", nhập description ≥ 10 ký tự | Modal confirm | ☐ |
| 4 | Confirm | API `report_major_failure` 200 | ☐ |
| 5 | Kiểm tra WO | status = "Halted–Major Failure" | ☐ |
| 6 | Kiểm tra Asset | status = "Out of Service" (BR-08-04) | ☐ |
| 7 | Kiểm tra CM WO | mới tạo, `source_pm_wo` đúng, `technician_notes` chứa `[MAJOR FAILURE]` | ☐ |
| 8 | Email | Workshop Head + VP Block2 nhận email khẩn HTML | ☐ |
| 9 | Chạy lại scheduler `generate_pm_work_orders` | KHÔNG tạo PM WO mới cho SEED-PM-03 (BR-08-04) | ☐ |
| 10 | Set Asset.status="Active" + chạy scheduler | PM WO mới tạo bình thường | ☐ |

---

### TC-08-06 — BR-08-04 block PM cho Out of Service

**Actor:** Scheduler.
**Seed:** SEED-PM-04.

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | `frappe.db.set_value("Asset","AC-ASSET-UAT-004","status","Out of Service")` | Done | ☐ |
| 2 | Chạy `generate_pm_work_orders` | Log `Skip PM WO creation for AC-ASSET-UAT-004 — Out of Service`, không tạo WO | ☐ |
| 3 | Restore status="Active", chạy lại | WO được tạo bình thường | ☐ |

---

### TC-08-07 — Calendar View + Reschedule

**Actor:** Workshop Head.
**BR liên quan:** VR-08-09 (reason ≥ 5 ký tự).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | Mở `/pm/calendar?year=2026&month=4` | Tháng hiện tại load, events màu hoá theo status | ☐ |
| 2 | Filter theo KTV ktv_test | Chỉ hiện WO của KTV đó | ☐ |
| 3 | Click event | Drawer slide-in chi tiết WO | ☐ |
| 4 | Mở WO bất kỳ, click "Hoãn lịch", nhập new_date + reason "Bận" (4 ký tự) | API trả `MISSING_REASON` | ☐ |
| 5 | Nhập lại reason ≥ 5 ký tự | API 200, status = "Pending–Device Busy", due_date update | ☐ |
| 6 | Kiểm tra technician_notes | Có dòng `[Hoãn lịch ... → ...]: ...` | ☐ |

---

### TC-08-08 — Dashboard KPI

**Actor:** VP Block2.

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | Mở `/pm/dashboard` | 5 KPI cards load | ☐ |
| 2 | Compliance rate khớp công thức | `(on_time / total) × 100` | ☐ |
| 3 | Bảng "Quá hạn" | Chỉ hiện WO status=Overdue | ☐ |
| 4 | Trend 6 tháng | 6 entry, ratio đúng | ☐ |
| 5 | Đổi sang tháng 3/2026 | Dashboard refetch và hiển thị data tháng 3 | ☐ |

---

### TC-08-09 — Tích hợp IMM-04 → IMM-08

**BR liên quan:** Hook `Asset Commissioning.on_submit`.
**Actor:** KTV (commissioning).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | Tạo Asset Commissioning mới với asset_category="Mechanical Ventilator" | Saved | ☐ |
| 2 | Submit ACC-... | Submit thành công | ☐ |
| 3 | Kiểm tra PM Schedule | 1 record mới: asset_ref đúng, pm_type theo template, `created_from_commissioning` link đúng | ☐ |
| 4 | next_due_date | = `commissioning_date + pm_interval_days` (first PM) | ☐ |
| 5 | Chạy `generate_pm_work_orders` ngay | (Sẽ KHÔNG tạo nếu next_due_date > today + alert_days_before — kỳ vọng skip) | ☐ |

---

### TC-08-10 — Mobile Checklist UX

**Actor:** KTV (điện thoại 375px).

| # | Hành động | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|
| 1 | Mở WO trên Chrome Android viewport 375px | Layout one-item-per-screen | ☐ |
| 2 | Tap nút Pass/Fail | Tap target ≥ 48px, không nhầm nút | ☐ |
| 3 | Swipe left/right | Chuyển checklist item | ☐ |
| 4 | Click "Đính kèm ảnh" | Camera mở, ảnh attach vào item | ☐ |
| 5 | Class III WO không upload ảnh, click Hoàn thành | Block với toast "Class III bắt buộc upload ảnh" (VR-08-04) | ☐ |
| 6 | (Optional) Tắt WiFi giữa chừng | Form không crash, hiển thị toast offline | ☐ |
| 7 | Bật lại WiFi và submit | Submit thành công | ☐ |

---

## 3. Tổng hợp kết quả

| Test Case | Mô tả | Kết quả | Người ký |
|---|---|---|---|
| TC-08-01 | Tự động tạo PM WO | ☐ Pass / ☐ Fail | |
| TC-08-02 | Happy path submit | ☐ Pass / ☐ Fail | |
| TC-08-03 | Overdue + escalation | ☐ Pass / ☐ Fail | |
| TC-08-04 | Fail-Minor → CM WO | ☐ Pass / ☐ Fail | |
| TC-08-05 | Major Failure → Out of Service | ☐ Pass / ☐ Fail | |
| TC-08-06 | BR-08-04 block | ☐ Pass / ☐ Fail | |
| TC-08-07 | Calendar + Reschedule | ☐ Pass / ☐ Fail | |
| TC-08-08 | Dashboard KPI | ☐ Pass / ☐ Fail | |
| TC-08-09 | Hook IMM-04 → IMM-08 | ☐ Pass / ☐ Fail | |
| TC-08-10 | Mobile UX | ☐ Pass / ☐ Fail | |

---

## 4. Escalation rules

| Tình huống | Severity | Hành động |
|---|---|---|
| TC-08-05 (Major Failure) không block WO mới | Blocker | Không release |
| TC-08-03 (Overdue) không gửi alert VP Block2 | Major | Fix trước release |
| TC-08-09 (IMM-04 hook) fail | Blocker | PM Schedule không tự tạo |
| TC-08-01 idempotent fail (tạo WO trùng) | Major | Fix trước release |
| Calendar không hiển thị đúng màu | Minor | Có thể release với workaround |
| Mobile offline sync không hoạt động | Minor | Document limitation, fix v2.1 |

---

## 5. Tài liệu liên quan

| Document | Path |
|---|---|
| Module Overview | `docs/imm-08/IMM-08_Module_Overview.md` |
| Functional Specs | `docs/imm-08/IMM-08_Functional_Specs.md` |
| API Interface | `docs/imm-08/IMM-08_API_Interface.md` |
| Technical Design | `docs/imm-08/IMM-08_Technical_Design.md` |
| UI/UX Guide | `docs/imm-08/IMM-08_UI_UX_Guide.md` |
| Automated UAT | `assetcore/tests/uat_imm08.py` |

---

*End of UAT Script v2.0.0 — IMM-08 Preventive Maintenance*
