# WORKFLOW SPECIFICATION — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** Thực tế có 14 workflow JSON tại `assetcore/assetcore/workflow/`. Naming `IMM-<NN> <Tên>` cho module workflow, `AC <Tên>` cho cross. State Title Case có space; action label tiếng Việt. Tham chiếu: `00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** Tech Lead + BA Lead
**Áp dụng:** Frappe Workflow Engine — JSON config trong `assetcore/assetcore/workflow/`

---

## 0. Quy ước chung

- **Workflow name:** `IMM-<NN> <Tên>` cho module workflow; `AC <Tên>` cho shared.
- **State name:** **Title Case có space** — `Pending Review`, `In Progress`, `Cannot Repair`, `Pending–Device Busy`. KHÔNG snake_case.
- **Action label:** **tiếng Việt có dấu** — `Bắt đầu sửa chữa`, `Phê duyệt`, `Yêu cầu RCA`.
- **State style/badge:** dùng key `style` của Frappe (`Primary`/`Success`/`Warning`/`Danger`/`Info`/`Inverse`).
- **Side effects:** mọi action quan trọng → gọi `assetcore.utils.lifecycle.log_audit_event(...)` + `create_lifecycle_event(...)`.
- **E-signature:** re-auth password hoặc PIN cho action thuộc QMS-critical (release, decommission, CAPA close, calibration approve fail).
- **SLA:** đo qua `IMM SLA Policy` fixture; check qua scheduler hourly/daily.

---

## 1. `AC Asset Lifecycle` — `AC Asset` (8 states · 16 transitions)

**Mục đích:** Workflow điều hành cho bản thể tài sản — từ commissioning đến decommission.

### States
| State | Style | Mô tả |
|---|---|---|
| Draft | Primary | Mới tạo, chưa commissioning |
| Commissioned | Info | Đã pass IQ/OQ/PQ |
| Active | Success | Đang sử dụng lâm sàng |
| Under Maintenance | Warning | Tạm dừng cho PM |
| Under Repair | Warning | Tạm dừng cho CM |
| Calibrating | Warning | Đang hiệu chuẩn |
| Out of Service | Danger | Stand-down (không đủ điều kiện sử dụng) |
| Decommissioned | Inverse | Đã giải nhiệm/thanh lý |

### Transitions (16) — sample
| Action | From | To | Roles | Side effect |
|---|---|---|---|---|
| Commission | Draft | Commissioned | `IMM HTM Engineer` + `IMM QA Officer` | LE `commissioned` |
| Activate | Commissioned | Active | `IMM Operations Manager` | LE `released_for_use`, e-sig |
| Bắt đầu bảo trì | Active | Under Maintenance | system (PM WO start) | LE `pm_started` |
| Hoàn thành bảo trì | Under Maintenance | Active | system (PM WO close) | LE `pm_completed` |
| Bắt đầu sửa chữa | Active | Under Repair | system (Asset Repair start) | LE `repair_started` |
| Hoàn thành sửa chữa | Under Repair | Active | system (Asset Repair close) | LE `repair_completed` |
| Không thể sửa chữa | Under Repair | Out of Service | `IMM Workshop Lead` | LE `cannot_repair` |
| Bắt đầu hiệu chuẩn | Active | Calibrating | system (Cal start) | LE `cal_started` |
| Hiệu chuẩn đạt | Calibrating | Active | `IMM QA Officer` | LE `cal_passed`, e-sig |
| Hiệu chuẩn không đạt | Calibrating | Out of Service | `IMM QA Officer` | LE `cal_failed`, trigger CAPA |
| Đưa ra khỏi sử dụng | Active | Out of Service | `IMM Operations Manager` + `IMM QA Officer` | e-sig, LE `stand_down` |
| Khôi phục hoạt động | Out of Service | Active | `IMM Operations Manager` | LE `restored` |
| Sửa chữa lại | Out of Service | Under Repair | `IMM Workshop Lead` | – |
| Thanh lý | Out of Service | Decommissioned | `IMM Operations Manager` + `IMM Finance Officer` | LE `decommissioned`, e-sig |

---

## 2. `IMM-04 Workflow` — `Asset Commissioning` (11 states · 23 transitions)

**Mục đích:** Workflow phức tạp nhất — IQ/OQ/PQ commissioning với nhánh DOA, non-conformance, clinical hold.

### States (11)
Draft · Pending Doc Verify · To Be Installed · Installing · Identification · Initial Inspection · Non Conformance · Clinical Hold · Re Inspection · Clinical Release · Return To Vendor

### Action label tiêu biểu
- `Gửi kiểm tra tài liệu`, `Xác nhận đủ tài liệu`, `Yêu cầu bổ sung tài liệu`
- `Bắt đầu lắp đặt`, `Báo cáo sự cố`, `Lắp đặt hoàn thành`, `Báo cáo DOA`
- `Bắt đầu kiểm tra`, `Phê duyệt phát hành`, `Giữ lâm sàng`
- `Báo cáo lỗi baseline`, `Gỡ giữ lâm sàng`, `Phê duyệt sau tái kiểm`
- `Khắc phục xong`, `Trả lại nhà cung cấp`

### Side effects
- `on_submit` (passing) → tự sinh `PM Schedule` + `IMM Calibration Schedule` (`services/imm08/imm11`).
- Non Conformance → tạo `Asset QA Non Conformance`.
- Clinical Release → activate `AC Asset` (sang state Active).

---

## 3. `IMM-05 Document Workflow` — `Asset Document` (6 states · 9 transitions)

**States:** Draft · Pending Review · Approved · Rejected · Archived · Expired

**Action label:**
- `Gửi duyệt`, `Phê duyệt`, `Từ chối`, `Gửi lại`, `Lưu trữ`, `Hủy bỏ`

**Side effects:**
- Approved → set `effective_date`; daily cron `imm05.check_document_expiry` đẩy sang `Expired` khi quá hạn.
- Expired → tạo `Expiry Alert Log` để chống duplicate notification.

**E-sig:** action `Phê duyệt` cho document Tier 1/2 (license, SOP).

---

## 4. `IMM-08 PM Workflow` — `PM Work Order` (7 states · 13 transitions)

**States:** Open · In Progress · Pending–Device Busy · Overdue · Halted–Major Failure · Completed · Cancelled

**Action label:**
- `Bắt đầu thực hiện`, `Đánh dấu trễ hạn`, `Hủy phiếu`
- `Hoàn thành PM`, `Báo lỗi nghiêm trọng`, `Thiết bị bận - hoãn`
- `Tiếp tục thực hiện`, `Bắt đầu muộn`, `Tiếp tục sau xử lý`

**Side effects:**
- `Bắt đầu thực hiện` → set `AC Asset.workflow_state = Under Maintenance` + LE `pm_started`.
- `Hoàn thành PM` → set asset back về `Active` + LE `pm_completed` + cập nhật `last_pm_date`/`next_pm_due`.
- `Báo lỗi nghiêm trọng` → auto-create `Incident Report` qua service.
- SLA: hourly cron, vi phạm → set `is_overdue=1` + LE `sla_breached`.

**Permission Query:** `assetcore.permissions.pm_work_order_query` — KTV chỉ thấy WO assigned hoặc trong khoa của mình; vendor chỉ thấy WO hợp đồng.

---

## 5. `IMM-09 Repair Workflow` — `Asset Repair` (9 states · 15 transitions)

**States:** Open · Assigned · Diagnosing · Pending Parts · In Repair · Completed · Pending Inspection · Cannot Repair · Cancelled

**Action label:**
- `Phân công KTV`, `Bắt đầu chẩn đoán`, `Yêu cầu linh kiện`
- `Linh kiện đã nhận - bắt đầu sửa`, `Hoàn thành sửa chữa - chờ kiểm tra`
- `Xác nhận hoàn thành`, `Kiểm tra thất bại - sửa lại`
- `Không thể sửa chữa`

**Side effects:**
- `Phân công KTV` → set `assigned_user`, LE `repair_assigned`.
- `Yêu cầu linh kiện` → tạo request stock, cron check.
- `Hoàn thành` → set asset state → `Active`; cập nhật MTTR.
- `Không thể sửa chữa` → asset → `Out of Service`.

**Permission Query:** `assetcore.permissions.asset_repair_query`.

---

## 6. `IMM-11 Calibration Workflow` — `IMM Asset Calibration` (8 states · 13 transitions)

**States:** Draft · Scheduled · Sent to Lab · Certificate Received · Passed · Failed · Conditionally Passed · Cancelled

**Action label:**
- `Gửi phòng hiệu chuẩn`, `Hủy lịch`, `Đạt hiệu chuẩn`, `Không đạt hiệu chuẩn`
- `Đạt có điều kiện`, `Hủy hiệu chuẩn`, `Nhận chứng chỉ`
- `Phê duyệt đạt`, `Phê duyệt không đạt`, `Phê duyệt có điều kiện`
- `CAPA hoàn tất - chuyển có điều kiện`

**Side effects:**
- `Đạt hiệu chuẩn` → asset → `Active`; cập nhật `last_calibration_date`/`next_calibration_due`.
- `Không đạt hiệu chuẩn` → asset → `Out of Service`; tạo `IMM CAPA Record` + `Asset QA Non Conformance`.
- `Phê duyệt đạt/không đạt` cần e-sig (`IMM QA Officer`).

---

## 7. `IMM-12 Incident Workflow` — `Incident Report` (7 states · 10 transitions)

**States:** Open · Acknowledged · In Progress · Resolved · RCA Required · Closed · Cancelled

**Action label:**
- `Tiếp nhận sự cố`, `Hủy sự cố`, `Bắt đầu xử lý`
- `Đánh dấu đã giải quyết`, `Yêu cầu RCA`, `Đóng sự cố`
- `RCA hoàn tất - đóng sự cố`, `Mở lại điều tra`, `Mở lại sự cố`

**Side effects:**
- `Tiếp nhận sự cố` → SLA timer start; LE `incident_acknowledged`.
- `Yêu cầu RCA` → tự sinh `IMM RCA Record` qua `services/imm12.create_rca_from_incident`.
- `Đánh dấu đã giải quyết` → tạo `Asset Repair` nếu cần sửa chữa.
- Cron `imm12.detect_chronic_failures` daily.

**Permission Query:** `assetcore.permissions.incident_report_query` — clinical user chỉ thấy incident trong khoa của mình.

---

## 8. `IMM-12 RCA Workflow` — `IMM RCA Record` (4 states · 4 transitions)

**States:** Draft · RCA In Progress · Closed · Cancelled

**Action label:**
- `Bắt đầu phân tích RCA`, `Hủy RCA`, `Hoàn thành RCA`

**Side effects:**
- `Hoàn thành RCA` → tự sinh `IMM CAPA Record` (nếu cần).
- Đóng → set incident → `Closed`.

---

## 9. `IMM-01 Needs Workflow` — `IMM Needs Request` (8 states · 24 transitions)

**Mục đích:** Workflow nhiều transition nhất — quản lý approve nhu cầu thiết bị từ khoa → VTTBYT → BGĐ.

> States/transitions chi tiết → đọc JSON trực tiếp `imm_01_needs_workflow.json`. Các action chính:
- Submit từ Department → `Pending Department Head Approval`
- Approve Department Head → `Pending VTTBYT Review`
- Approve `IMM HTM Engineer` (technical review) → `Pending Operations Manager`
- Approve Operations Manager → `Pending Board Approval`
- Approve `IMM Board Approver` → `Approved` → consume vào `IMM Procurement Plan`

---

## 10. `IMM-01 Plan Workflow` — `IMM Procurement Plan` (4 states · 4 transitions)

States: Draft → Pending Review → Approved → Active.

---

## 11. `IMM-02 Spec Workflow` — `IMM Tech Spec` (7 states · 9 transitions)

States: Draft → HTM Review → QA Review → Pending Approval → Approved → Locked → Superseded.

E-sig khi `Locked` (đã đem ra public bidding/RFQ).

---

## 12. `IMM-03 AVL Workflow` — `IMM AVL Entry` (5 states · 7 transitions)

States: Draft · Pending Review · Approved · Suspended · Expired.

Cron: `imm03.check_avl_expiry` daily.

---

## 13. `IMM-03 Vendor Eval Workflow` — `IMM Vendor Evaluation` (5 states · 6 transitions)

States: Draft · Scoring · Pending Approval · Finalized · Rejected.

---

## 14. `IMM-03 Decision Workflow` — `IMM Procurement Decision` (9 states · 8 transitions)

States: Draft · Negotiation · Pending Finance Review · Pending QA Review · Pending Risk Review · Pending Board Approval · Approved · Cancelled · Superseded.

E-sig ở mọi gate approve.

---

## 15. Workflow chưa có JSON (cần spec sau)

Các DocType submittable nhưng chưa có workflow JSON:

| DocType | Trạng thái | Ghi chú |
|---|---|---|
| `IMM CAPA Record` | Submit-only, no workflow | Orchestration nằm trong `services/imm12.py` — cần workflow rõ ràng cho audit |
| `IMM Lock-in Risk Assessment` | Submit-only | Cân nhắc thêm workflow approve/reject |
| `IMM Supplier Audit` | Submit-only | – |
| `IMM Market Benchmark` | Submit-only | – |
| `IMM Demand Forecast` | Auto-generate, no workflow | – |
| `Firmware Change Request` | Submit-only | Cần CCB workflow |
| `Asset QA Non Conformance` | Submit-only | – |
| `Asset Transfer` | No-submit | – |
| `IMM Vendor Scorecard` | Auto-generate quarterly | – |

---

## 16. Quy ước chung (cập nhật)

- Mọi action workflow log vào `IMM Audit Trail` qua `assetcore.utils.lifecycle.log_audit_event`.
- Lifecycle event tạo qua `create_lifecycle_event` (KHÔNG insert trực tiếp `Asset Lifecycle Event`).
- Allowed Self-Approval: mặc định **False**, ghi nhận trong JSON workflow.
- E-signature enforce qua workflow JSON `next_state` + custom validator (chưa hard-code, đang spec — đánh dấu TODO).
- Mọi transition có **comment field** cho người duyệt (`workflow_state_change_comment`).

---

## 17. Tiêu chí nghiệm thu

- ✓ 14 workflow JSON deploy được qua `bench migrate`.
- ✓ State + transition khớp với fixtures `Workflow State` + `Workflow Action Master` trong `hooks.py`.
- ✓ Test transition pass cho từng role được phép; test negative (role không được) trả 403.
- ✓ Lifecycle event publish đúng cho 100% transition QMS-critical.
- ✓ Audit chain `verify_audit_chain` hợp lệ sau N transitions.

---

## 18. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QA Officer |  | 2026-05-07 |
