# 04 — Backend Design (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Trạng thái BE | **Chưa scaffold** — file này định nghĩa skeleton, field detail sẽ chốt tại Sprint Wave 3 |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [05 API](./05_API_Specification.md) · [03 Diagrams](./03_Diagrams.md) |

> Thiết kế tuân thủ kiến trúc 3-tier (API → Service → Repository) theo `CONVENTIONS.md §2`. KHÔNG modify ERPNext core — chỉ extend qua DocType mới và hooks.

---

## I. DocType (skeleton)

IMM-13 dự kiến 3 DocType chính + 1 child + 1 single config. Chi tiết field *(thiết kế trong Sprint Wave 3 — sau khi BE scaffold)*; phần dưới chỉ liệt kê tên + mục đích + 1-dòng quan hệ.

| DocType | Loại | Mục đích | Quan hệ |
|---|---|---|---|
| `IMM Asset Reassignment` | Master submittable | Hồ sơ điều chuyển nội viện 1 asset | Link `AC Asset` + Link `Location` (from / to) |
| `IMM Replacement Review` | Master submittable | Bảng đối chiếu cost-of-repair vs replacement-cost | Link `AC Asset` + child table `IMM Cost Item` |
| `IMM Residual Risk` | Master submittable | Đánh giá residual risk theo WHO §3.2 | Link `IMM Replacement Review` + child table `IMM Residual Risk Item` |
| `IMM Residual Risk Item` | Child | Mỗi dòng là 1 risk × likelihood × impact × mitigation | Parent: `IMM Residual Risk` |
| `IMM-13 Settings` | Single | Ngưỡng cron escalation, ngưỡng cost auto-trigger, role mapping | – |

**Naming series** *(dự kiến)*:
- `IMM Asset Reassignment` → `RAS-.YY.-.MM.-.####.`
- `IMM Replacement Review` → `RPV-.YY.-.MM.-.####.`
- `IMM Residual Risk` → `RSK-.YY.-.MM.-.####.`

**Permissions** (CONVENTIONS §5):
- `IMM HTM Engineer` (KTV): create, read, write Draft → PendingDeptConfirm
- `IMM Department Head` (Trưởng khoa): read all in their facility, transition PendingDeptConfirm → PendingApproval
- `IMM Operations Manager` (PTP Khối 2): approve/reject
- `IMM QA Officer` (Tổ HC-QLCL): sign Residual Risk
- `IMM Finance Officer` (Phòng TCKT): write cost field on `IMM Replacement Review`
- `IMM Auditor`: read all + audit chain endpoint

KHÔNG tạo DocType mới cho `Lifecycle Event`, `Audit Trail`, `Location` — dùng sẵn từ IMM-00 / Asset registry.

---

## II. Service layer (3-tier)

Theo `CONVENTIONS.md §2` — strict split:

```
assetcore/api/imm13.py            # @frappe.whitelist endpoints
assetcore/services/imm13.py       # business logic (orchestration)
assetcore/repositories/
    asset_reassignment_repo.py    # data access
    replacement_review_repo.py
    residual_risk_repo.py
```

### II.1 Service functions (signature dự kiến)

| Function | Mô tả |
|---|---|
| `stand_down(asset: str, reason: str, evidence: list[str], actor: str) -> str` | Khởi tạo IMM Asset Reassignment kiểu stand-down, transition Asset → Out of Service sau approval chain |
| `request_reassignment(asset: str, target_location: str, reason: str) -> str` | Khởi tạo IMM Asset Reassignment |
| `confirm_reassignment(reassignment: str, role: str)` | Xác nhận tại 1 trong 3 cấp (dept_source / dept_target / approver) |
| `commit_reassignment(reassignment: str)` | Atomic update `Asset.location` + Lifecycle Event `reassigned` |
| `create_replacement_review(asset: str) -> str` | Khởi tạo Replacement Review |
| `submit_residual_risk(review: str, items: list, signature: str)` | Ký residual risk |
| `approve_retire(review: str, signature: str) -> str` | Duyệt retire proposal + emit event `retire_proposed` cho IMM-14 |
| `escalate_stale_oos(now: datetime)` | Cron hàm — find Asset Out-of-Service > N ngày |
| `verify_location_consistency()` | Cron hàm — check `Asset.location` khớp reassignment mới nhất |

### II.2 Repository functions

| Repo | Function chính |
|---|---|
| `asset_reassignment_repo` | `find_by_asset(asset)`, `find_pending_dept_confirm(facility)`, `update_state(...)` |
| `replacement_review_repo` | `find_for_asset(asset)`, `submit(name, payload)` |
| `residual_risk_repo` | `attach_items(review, items)`, `verify_signature_chain(review)` |

### II.3 Controller hooks (DocType class)

Controller mỗi DocType chỉ chứa **validate / on_submit / on_cancel** — KHÔNG chứa business logic (CLAUDE.md §15). Mọi nghiệp vụ delegate sang `services/imm13.py`.

---

## III. Workflow

3 workflow JSON (sẽ chốt ở Sprint Wave 3, lưu `assetcore/workflow/imm_13_*.json`):

### III.1 `IMM Asset Reassignment Workflow`

| State | Style | Mô tả | Role |
|---|---|---|---|
| Draft | Primary | Mới tạo | IMM HTM Engineer |
| Pending Dept Confirm Source | Warning | Chờ Trưởng khoa nguồn | IMM Department Head |
| Pending Dept Confirm Target | Warning | Chờ Trưởng khoa đích | IMM Department Head |
| Pending Approval | Warning | Chờ PTP Khối 2 | IMM Operations Manager |
| Approved | Success | Đã commit | – |
| Rejected | Danger | Bị từ chối | – |
| Cancelled | Inverse | Hủy | – |

Transitions chính (action label tiếng Việt):
- `Gửi xác nhận` (Draft → Pending Dept Confirm Source)
- `Trưởng khoa nguồn xác nhận` (→ Pending Dept Confirm Target)
- `Trưởng khoa đích chấp nhận` (→ Pending Approval)
- `Duyệt` (→ Approved) — **side effect**: invoke `services/imm13.commit_reassignment` → cập nhật `Asset.location` + Lifecycle Event `reassigned` + e-sign
- `Từ chối` / `Hủy`

### III.2 `IMM Replacement Review Workflow`

| State | Mô tả |
|---|---|
| Draft | KTV khởi tạo |
| Pending Finance | Chờ TCKT điền cost |
| Pending Risk Assessment | Chờ Tổ QLCL ký residual risk |
| Pending Approval | Chờ PTP Khối 2 |
| Approved | Đã pass sang IMM-14 |
| Rejected | – |

Side effect khi `Approved`: emit lifecycle event `retire_proposed` (kèm payload Asset ref + Review ref + Risk ref) — IMM-14 listener pickup.

### III.3 `IMM Residual Risk Workflow`

| State | Mô tả |
|---|---|
| Draft | Đang đánh giá |
| Signed | QA Officer e-sign |

Side effect khi `Signed`: ghi `signature_hash` SHA-256, gọi `log_audit_event`.

---

## IV. Hooks

Trong `hooks.py`:

```python
doc_events = {
    "Asset Repair": {
        "on_update_after_submit": "assetcore.events.imm13.handle_repair_cannot_repair",
    },
    "IMM Asset Calibration": {
        "on_update_after_submit": "assetcore.events.imm13.handle_calibration_failed",
    },
    "IMM Asset Reassignment": {
        "on_submit": "assetcore.events.imm13.on_reassignment_submit",
    },
}

scheduler_events = {
    "daily": [
        "assetcore.services.imm13.escalate_stale_oos",
        "assetcore.services.imm13.verify_location_consistency",
    ],
    "hourly": [
        "assetcore.services.imm13.retry_handoff_imm14",
    ],
}
```

(Chính xác từng đường dẫn module sẽ confirm khi BE scaffold — section này là design intent.)

---

## V. Integration với module khác

| Module | Direction | Cơ chế |
|---|---|---|
| IMM-09 (Repair) | IN | Listener `on_update_after_submit` → seed stand-down nếu `outcome = cannot_repair` |
| IMM-11 (Calibration) | IN | Listener tương tự cho `cal_failed` không khắc phục |
| IMM-12 (Incident) | IN | Khi RCA kết luận "thiết bị không an toàn vĩnh viễn" |
| IMM-07 (Performance) | IN | Replacement signal — utilization < ngưỡng X tháng |
| IMM-08 (PM) | IN | PM finding `end_of_life` |
| IMM-04 (Installation) | OUT | Trigger re-commissioning lite khi reassign sang khoa khác chuyên ngành |
| IMM-14 (Decommission) | OUT | Emit event `retire_proposed` |
| IMM-01 (Needs) | OUT | Khi Replacement Review khuyến nghị "thay mới" → seed nhu cầu |
| IMM-15 (Inventory) | Sync | Cron verify location consistency |
| IMM-06 (Training) | Read | Check competency của khoa đích |

---

## VI. Skeleton checklist (BE scaffold task list)

- [ ] Tạo DocType JSON cho 4 DocType + 1 child + 1 single
- [ ] Tạo workflow JSON cho 3 workflow
- [ ] Sinh fixture role + permission cho 5 role mới (overlap với IMM-04/05/14)
- [ ] Sinh `services/imm13.py` skeleton 9 function (xem §II.1)
- [ ] Sinh `repositories/*_repo.py` 3 file
- [ ] Sinh `api/imm13.py` (xem [05 API](./05_API_Specification.md))
- [ ] Sinh `events/imm13.py` cho hooks
- [ ] Update `hooks.py`
- [ ] Sinh `tests/test_imm13.py` skeleton (xem [07 Testing](./07_Testing_QA.md))
- [ ] Update `services/shared/constants.py:ErrorCode` — thêm namespace `IMM13_*`

*(Skeleton chi tiết sinh trong Sprint Wave 3 — Sprint 1–2.)*
