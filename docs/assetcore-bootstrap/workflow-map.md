# WORKFLOW MAP — ASSETCORE FOUNDATION
# Dùng để giao cho Claude Code tạo Workflow fixtures
# Version 0.1 | April 2026

---

## WF-01 — PM WORK ORDER WORKFLOW

**DocType:** IMM PM Work Order
**Workflow Name:** PM Work Order Workflow

| # | State | Is Active | Role (Allow Transition FROM this state) | Action Button |
|---|---|---|---|---|
| 1 | Draft | - | IMM Workshop Lead | — |
| 2 | Scheduled | ✓ | IMM Workshop Lead, IMM Technician | Schedule |
| 3 | Assigned | ✓ | IMM Workshop Lead | Assign |
| 4 | In Progress | ✓ | IMM Technician | Start Work |
| 5 | Completed | ✓ | IMM Workshop Lead | Complete |
| 6 | Verified | ✓ | IMM Operations Manager | Verify |
| 7 | Closed | - | IMM Operations Manager | Close |
| 8 | Cancelled | - | IMM Workshop Lead | Cancel |

**Transitions:**

| From | To | Action | Role | Condition |
|---|---|---|---|---|
| Draft | Scheduled | Schedule | IMM Workshop Lead | scheduled_date is set |
| Scheduled | Assigned | Assign Technician | IMM Workshop Lead | assigned_technician is set |
| Assigned | In Progress | Start Work | IMM Technician | actual_start_datetime is set |
| In Progress | Completed | Mark Complete | IMM Technician | pm_result is set AND checklist_completion_pct >= 80 |
| Completed | Verified | Verify | IMM Workshop Lead, IMM Operations Manager | — |
| Verified | Closed | Close WO | IMM Operations Manager | — |
| Draft | Cancelled | Cancel | IMM Workshop Lead | — |
| Scheduled | Cancelled | Cancel | IMM Workshop Lead | — |
| Assigned | Cancelled | Cancel | IMM Workshop Lead | — |

---

## WF-02 — CM WORK ORDER WORKFLOW

**DocType:** IMM CM Work Order
**Workflow Name:** CM Work Order Workflow

| # | State | Is Active | Description |
|---|---|---|---|
| 1 | Reported | ✓ | Sự cố mới được báo cáo |
| 2 | Triaged | ✓ | Đã phân loại mức độ và phương án xử lý |
| 3 | Assigned | ✓ | Đã phân công KTV |
| 4 | Diagnosing | ✓ | Đang chẩn đoán nguyên nhân |
| 5 | In Repair | ✓ | Đang sửa chữa |
| 6 | Waiting Parts | ✓ | Chờ linh kiện/phụ tùng |
| 7 | Testing | ✓ | Đang kiểm tra sau sửa chữa |
| 8 | Completed | ✓ | Sửa chữa hoàn tất |
| 9 | Closed | - | Đã đóng hồ sơ |
| 10 | Cancelled | - | Đã huỷ |

**Transitions:**

| From | To | Action | Role | Condition |
|---|---|---|---|---|
| Reported | Triaged | Triage | IMM Workshop Lead | triage_result is set |
| Triaged | Assigned | Assign | IMM Workshop Lead | assigned_technician is set |
| Assigned | Diagnosing | Start Diagnosis | IMM Technician | — |
| Diagnosing | In Repair | Start Repair | IMM Technician | root_cause is set |
| Diagnosing | Waiting Parts | Wait for Parts | IMM Technician, IMM Workshop Lead | — |
| Waiting Parts | In Repair | Parts Received | IMM Workshop Lead, IMM Storekeeper | — |
| In Repair | Testing | Start Testing | IMM Technician | repair_actions is set |
| Testing | Completed | Complete | IMM Technician | post_repair_test_result = Pass |
| Testing | In Repair | Retest Failed | IMM Technician | post_repair_test_result = Fail |
| Completed | Closed | Close | IMM Workshop Lead | — |
| Reported | Cancelled | Cancel | IMM Workshop Lead | — |
| Triaged | Cancelled | Cancel | IMM Workshop Lead | — |

---

## WF-03 — DOCUMENT REVIEW WORKFLOW

**DocType:** IMM Document Repository
**Workflow Name:** Document Review Workflow

| # | State | Description |
|---|---|---|
| 1 | Draft | Mới tạo, chưa nộp |
| 2 | Submitted | Đã nộp, chờ duyệt |
| 3 | Under Review | Đang được xem xét |
| 4 | Approved | Đã duyệt |
| 5 | Active | Đang hiệu lực |
| 6 | Rejected | Bị từ chối |
| 7 | Expired | Hết hạn (auto) |
| 8 | Superseded | Đã thay thế |

**Transitions:**

| From | To | Action | Role | Condition |
|---|---|---|---|---|
| Draft | Submitted | Submit for Review | IMM Document Officer | primary_attachment is set |
| Submitted | Under Review | Start Review | IMM QA Officer, IMM Department Head | — |
| Under Review | Approved | Approve | IMM Department Head | — |
| Under Review | Rejected | Reject | IMM Department Head | — |
| Rejected | Draft | Revise | IMM Document Officer | — |
| Approved | Active | Activate | IMM System Admin (auto) | — |
| Active | Superseded | Supersede | IMM Document Officer | — |

---

## WF-04 — COMMISSIONING WORKFLOW

**DocType:** IMM Commissioning Record
**Workflow Name:** Commissioning Workflow

| # | State | Description |
|---|---|---|
| 1 | Draft | Mới tạo |
| 2 | In Progress | Đang thực hiện lắp đặt |
| 3 | Completed | Hoàn tất kiểm tra |
| 4 | Approved | Đã được duyệt, tài sản được release |
| 5 | Rejected | Kiểm tra không đạt |

**Transitions:**

| From | To | Action | Role | Condition |
|---|---|---|---|---|
| Draft | In Progress | Start Commissioning | IMM Technician | installation_date is set |
| In Progress | Completed | Submit for Approval | IMM Workshop Lead | overall_inspection_result is set |
| Completed | Approved | Approve & Release | IMM Department Head | overall_inspection_result = Pass |
| Completed | Rejected | Reject | IMM Department Head | overall_inspection_result = Fail |
| Rejected | In Progress | Retry | IMM Workshop Lead | — |

---

## WF-05 — CALIBRATION WORKFLOW

**DocType:** IMM Calibration Record
**Workflow Name:** Calibration Workflow

| # | State | Description |
|---|---|---|
| 1 | Scheduled | Đã lên lịch hiệu chuẩn |
| 2 | In Progress | Đang thực hiện |
| 3 | Completed | Hoàn tất, có chứng chỉ |
| 4 | Expired | Hết hạn chứng chỉ (auto daily) |
| 5 | Cancelled | Đã huỷ |

**Transitions:**

| From | To | Action | Role | Condition |
|---|---|---|---|---|
| Scheduled | In Progress | Start | IMM Technician | actual_date is set |
| In Progress | Completed | Complete | IMM Technician | certificate_number is set AND certificate_expiry is set |
| Scheduled | Cancelled | Cancel | IMM Workshop Lead | — |
| In Progress | Cancelled | Cancel | IMM Workshop Lead | — |

---

## BẢNG TỔNG HỢP WORKFLOW

| DocType | Workflow Name | States | Roles liên quan | Auto transition |
|---|---|---|---|---|
| IMM PM Work Order | PM Work Order Workflow | 8 | Workshop Lead, Technician, Ops Manager | Tạo tự động từ scheduler |
| IMM CM Work Order | CM Work Order Workflow | 10 | Workshop Lead, Technician, Storekeeper | Không |
| IMM Document Repository | Document Review Workflow | 8 | Document Officer, QA Officer, Dept Head | Expired tự động |
| IMM Commissioning Record | Commissioning Workflow | 5 | Technician, Workshop Lead, Dept Head | Không |
| IMM Calibration Record | Calibration Workflow | 5 | Technician, Workshop Lead | Expired tự động |
