# 09 — Phát hành (Release: User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | User guide + release notes + traceability |
| Owner | BA + Tech Lead + Customer Success |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [07 Testing](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) |

---

# Phần I — User Guide (Hướng dẫn sử dụng)

## I.1. Giới thiệu

IMM-07 là cockpit theo dõi hiệu suất thiết bị y tế — tự động tính KPI hằng đêm, cảnh báo thiết bị cần thay thế, và cung cấp drill-down về dữ liệu nguồn. Tài liệu này dành cho Trưởng phòng VT-TBYT, Tổ trưởng Workshop, KTV và QMS Risk.

## I.2. Nhận biết bạn đang ở đâu

Sidebar trái > "Theo dõi hiệu suất (IMM-07)" → 4 mục con: Cockpit · Snapshot KPI · Tín hiệu thay thế · Cấu hình.

## I.3. Các vai trò

| Vai trò | Quyền chính |
|---|---|
| Trưởng phòng | Cockpit + transition signal + checker threshold |
| WS Lead | Re-compute + maker threshold |
| KTV | Drill-down trong khoa của mình |
| QMS Risk | Verify chain + read-only |
| CNTT Admin | KPI definition CRUD |

## I.4. Quy trình chính

1. **Hằng ngày sáng**: Trưởng phòng mở Cockpit, xem 6 KPI tile, click drill-down nếu có anomaly.
2. **Khi có signal**: Trưởng phòng take signal, plan action, close khi xong.
3. **Hằng tuần**: QMS Risk verify hash chain.
4. **Hằng tháng**: Export báo cáo BYT PDF.

## I.5. Thao tác per role

**Trưởng phòng:**
- Cockpit: 1 click, không action.
- Take signal: vào Tín hiệu thay thế > chọn signal > "Tiếp nhận".
- Plan action: vào detail signal > nhập action_taken > "Lập kế hoạch".
- Close: "Đóng" sau khi action hoàn tất.
- Mark False Positive: confirm modal + ghi lý do.

**WS Lead:**
- Re-compute: vào Snapshot detail > "Tính lại" + nhập lý do.
- Maker threshold: vào Cấu hình > Ngưỡng > Tạo mới + Submit cho Trưởng phòng duyệt.

**KTV:**
- Drill-down: chỉ xem record nguồn của khoa được phân.

**QMS Risk:**
- Verify chain: vào Cấu hình > "Verify" + chọn period.

**CNTT Admin:**
- KPI definition: clone version mới khi đổi formula (BR-04).

## I.6. Bảng điều khiển (Dashboard)

6 KPI tile + 2 chart trend + bảng signal Open mới nhất. Cache 5 phút — refresh manual qua nút reload.

## I.7. FAQ

- **Vì sao snapshot có badge vàng "incomplete"?** Asset thiếu lifecycle event 24h gần nhất. Liên hệ Workshop để bổ sung log.
- **Vì sao verify chain báo lỗi?** Có ai đó sửa snapshot trực tiếp DB. Báo CNTT + QMS Risk ngay.
- **Có thể edit KPI cũ không?** Không (BR-01). Phải re-compute với lý do.

## I.8. Phím tắt & Mã trạng thái

- `g + c` → Cockpit.
- `g + s` → Snapshot list.
- `g + r` → Replacement signal.

State signal: Draft / Open / InReview / ActionPlanned / FalsePositive / Closed.

## I.9. Liên hệ hỗ trợ

- Bug nghiệp vụ: BA `<email>` *(BA bổ sung trong sprint kế tiếp)*.
- Lỗi hệ thống: CNTT `<email>` *(BA bổ sung)*.
- Audit / compliance: QMS Risk `<email>` *(BA bổ sung)*.

## I.10. Lịch sử cập nhật tài liệu

| Phiên bản | Ngày | Thay đổi | Người |
|---|---|---|---|
| 0.1 | 2026-05-10 | Khởi tạo doc skeleton (light-touch generation) | doc-curator |

---

# Phần II — Release Notes

## II.1. Tóm tắt

IMM-07 v3.x.0 — Release đầu tiên của module Theo dõi hiệu suất. Cung cấp cockpit KPI, snapshot tự động, replacement signal, và hash chain audit.

## II.2. Tính năng mới

- Cockpit 6 KPI tile + drill-down.
- Cron compute_metrics_daily / weekly / monthly.
- Replacement signal workflow 6 state.
- Threshold maker/checker workflow.
- Hash chain verify.

## II.3. Cải tiến (Improvements)

*(Lần đầu release — N/A.)*

## II.4. Sửa lỗi (Bug fixes)

*(Lần đầu release — N/A.)*

## II.5. Thay đổi không backward-compat (Breaking)

Không. Module mới.

## II.6. Deprecations

Không.

## II.7. Yêu cầu nâng cấp

- Frappe v15+, ERPNext v15+.
- IMM-04, 08, 09, 11 đã deploy.
- Migrate + import fixture KPI definition + threshold default.

## II.8. Downtime / Compatibility / Known issues

- Downtime deploy: ≤ 2h, off-peak.
- Known issue: utilization KPI dựa trên log thủ công của khoa (chính xác phụ thuộc kỷ luật ghi). HIS integration roadmap.

## II.9. Liên kết & Lịch sử versioning

| Version | Ngày | Highlight |
|---|---|---|
| v3.x.0 | *(Sprint Wave 3)* | First release IMM-07 |

---

# Phần III — Traceability Matrix

## III.1. Cách dùng

Mỗi user story → ≥ 1 test → ≥ 1 code reference. Audit BYT yêu cầu show được full chain.

## III.2. Matrix chính

| User Story | Use Case | Test ID | Code reference |
|---|---|---|---|
| IMM07-US-01 | UC-01 | UT-IMM07-S-01, UT-IMM07-S-02 | `services/imm07.py:compute_metrics` |
| IMM07-US-02 | UC-01 | UT-IMM07-S-02 | `services/imm07.py:compute_metrics` (data_gap branch) |
| IMM07-US-03 | UC-02, UC-03 | UAT-IMM07-01, UAT-IMM07-02 | `api/imm07.py:cockpit_summary`, `drill_down` |
| IMM07-US-04 | UC-03 | UAT-IMM07-02 | `api/imm07.py:drill_down` |
| IMM07-US-05 | UC-04 | UAT-IMM07-05 | *(Sprint Wave 3)* |
| IMM07-US-06 | UC-05 | UT-IMM07-V-01 | `doctype/imm_performance_metric_definition/` |
| IMM07-US-07 | UC-06 | *(Sprint Wave 3)* | Workflow `imm_07_threshold_approval` |
| IMM07-US-08 | UC-07 | UT-IMM07-S-04, UT-IMM07-S-05 | `services/imm07.py:transition_signal` |
| IMM07-US-09 | UC-08 | UT-IMM07-S-06, UT-IMM07-S-07 | `services/imm07.py:verify_chain` |
| IMM07-US-10 | UC-09 | UAT-IMM07-04 | `api/imm07.py:recompute_one` |

## III.3. Reverse lookup

| Code | User Story |
|---|---|
| `services/imm07.py` | US-01, 02, 08, 09, 10 |
| `api/imm07.py` | US-03, 04, 10 |
| Workflow JSON | US-07, 08 |

## III.4. Coverage gaps

- US-05 Export báo cáo BYT — chưa có test → `*(Sprint Wave 3)*`.
- US-07 Threshold workflow — integration test pending.

## III.5. Cập nhật quy ước

Mỗi PR thêm endpoint phải update bảng III.2.

## III.6. Audit-readiness — quick links

- Hash chain verify: API `verify_chain` + UI Cấu hình > Verify.
- Lifecycle event: query `IMM Audit Trail` filter `module=IMM-07`.
- KPI definition version: DocType list `IMM Performance Metric Definition`.

## III.7. Bảng thống kê thông tin ứng dụng (Application statistics)

| Hạng mục | Giá trị |
|---|---|
| LOC service | *(Cập nhật mỗi release)* |
| LOC API | *(Cập nhật mỗi release)* |
| Số DocType | 4 |
| Số endpoint API | 10 |
| Số workflow | 2 |
| Số cron job | 4 |
| Coverage service | *(Cập nhật mỗi release)* |
| Coverage API | *(Cập nhật mỗi release)* |

---

## Trace tới đợt triển khai

Module IMM-07 thuộc **Đợt 3** (Architecture line 278) cùng với IMM-10, IMM-13, IMM-14, IMM-17. Pre-requisite: Đợt 1 (IMM-04, 05, 08, 09, 11, 12) đã ổn định + Đợt 2 (IMM-15, 16) đã deploy.
