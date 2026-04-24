# Copyright (c) 2026, AssetCore Team
# Service layer cho Module IMM-13 — Suspension & Transfer Gateway (v2.0).
# Chứa toàn bộ business logic; controller chỉ delegate sang đây.

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, getdate, add_days

from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.constants import ErrorCode

_HIGH_VALUE_THRESHOLD = 500_000_000  # 500 triệu VNĐ


# ─── Validation (BR-13-01 → BR-13-10) ────────────────────────────────────────

def validate_suspension_request(doc) -> None:
    """Orchestrate BR-13-01..BR-13-10 validation."""
    _br01_check_active_work_orders(doc)
    _br02_check_duplicate_dr(doc)
    _br03_bio_hazard_clearance(doc)
    _br04_regulatory_clearance(doc)
    _br06_residual_risk_required(doc)
    _br07_high_risk_needs_replacement_review(doc)
    _br09_validate_transfer_location(doc)
    _br10_transfer_requires_receiving_officer(doc)


def before_submit_handler(doc) -> None:
    """BR-05: data_destruction; BR-08: high value approval."""
    _br05_data_destruction_confirmed(doc)
    _br08_high_value_needs_approval(doc)


def on_submit_handler(doc) -> None:
    """Atomic: update asset + log ALE + optional trigger IMM-14."""
    if doc.outcome == "Transfer":
        _execute_transfer(doc)
        log_lifecycle_event(doc, "transferred", doc.workflow_state or "Approved for Transfer", "Transferred")
    elif doc.outcome == "Retire":
        _execute_suspension(doc, "Decommissioned")
        log_lifecycle_event(doc, "decommissioned", doc.workflow_state or "Pending Decommission", "Completed")
        _trigger_imm14_archive(doc)
    else:  # Suspend
        _execute_suspension(doc, "Suspended")
        log_lifecycle_event(doc, "suspended", doc.workflow_state or "Pending Decommission", "Completed")


def on_cancel_handler(doc) -> None:
    """Log cancellation lifecycle event."""
    log_lifecycle_event(
        doc,
        "suspension_cancelled",
        doc.workflow_state or "Cancelled",
        "Cancelled",
        notes=doc.rejection_reason or "Hủy phiếu",
    )


def insert_default_checklist(doc) -> None:
    """Auto-insert 7 default checklist items on before_insert."""
    if doc.suspension_checklist:
        return  # Already has items, skip

    default_tasks = [
        ("Thu hồi thiết bị từ khoa sử dụng", "Physical"),
        ("Gắn nhãn 'NGỪNG SỬ DỤNG' lên thiết bị", "Physical"),
        ("Kiểm kê phụ tùng / phụ kiện kèm theo", "Documentation"),
        ("Xóa dữ liệu bệnh nhân (nếu applicable)", "Data"),
        ("Vệ sinh / khử khuẩn thiết bị", "Biological"),
        ("Chụp ảnh tình trạng thiết bị", "Documentation"),
        ("Lưu kho tạm / chuyển vị trí quy định", "Physical"),
    ]
    for task_name, category in default_tasks:
        doc.append("suspension_checklist", {
            "task_name": task_name,
            "task_category": category,
            "completed": 0,
        })


# ─── BR Validators ────────────────────────────────────────────────────────────

def _br01_check_active_work_orders(doc) -> None:
    """BR-13-01: Chặn nếu thiết bị còn Work Order đang mở."""
    if not doc.asset:
        return
    open_wos = _get_open_work_orders(doc.asset)
    if open_wos:
        names = ", ".join(open_wos[:5])
        frappe.throw(
            _("Lỗi BR-13-01: Không thể ngừng sử dụng. Thiết bị <b>{0}</b> còn "
              "<b>{1}</b> lệnh công việc đang mở: <b>{2}</b>. "
              "Vui lòng đóng tất cả Work Order trước khi ngừng sử dụng.").format(
                doc.asset, len(open_wos), names
            )
        )


def _br02_check_duplicate_dr(doc) -> None:
    """BR-13-02: Không cho tạo DR trùng cho cùng asset."""
    if not doc.asset or doc.name:
        # doc.name exists if already saved (editing existing)
        existing = frappe.db.get_value(
            "Decommission Request",
            {"asset": doc.asset, "docstatus": ("!=", 2), "name": ("!=", doc.name or "")},
            "name",
        )
    else:
        existing = frappe.db.get_value(
            "Decommission Request",
            {"asset": doc.asset, "docstatus": ("!=", 2)},
            "name",
        )
    if existing:
        frappe.throw(
            _("Lỗi BR-13-02: Đã có Phiếu Ngừng sử dụng <b>{0}</b> đang xử lý cho thiết bị này.").format(existing)
        )


def _br03_bio_hazard_clearance(doc) -> None:
    """BR-13-03: biological_hazard = 1 → bắt buộc bio_hazard_clearance."""
    if doc.biological_hazard and not doc.bio_hazard_clearance:
        frappe.throw(
            _("Lỗi BR-13-03: Thiết bị có nguy cơ sinh học. "
              "Bắt buộc khai báo biện pháp xử lý an toàn sinh học (NĐ98/2021 §15).")
        )


def _br04_regulatory_clearance(doc) -> None:
    """BR-13-04: regulatory_clearance_required = 1 → bắt buộc upload file."""
    if doc.regulatory_clearance_required and not doc.regulatory_clearance_doc:
        frappe.throw(
            _("Lỗi BR-13-04: Phiếu yêu cầu giấy phép từ cơ quan quản lý. "
              "Vui lòng upload file giấy phép tại trường 'File giấy phép' (NĐ98/2021 §16).")
        )


def _br05_data_destruction_confirmed(doc) -> None:
    """BR-13-05: data_destruction_required = 1 → bắt buộc confirmed trước Submit."""
    if doc.data_destruction_required and not doc.data_destruction_confirmed:
        frappe.throw(
            _("Lỗi BR-13-05: Thiết bị có dữ liệu bệnh nhân cần xoá. "
              "Vui lòng xác nhận đã xoá dữ liệu trước khi Submit.")
        )


def _br06_residual_risk_required(doc) -> None:
    """BR-13-06: Sau khi có technical review, residual_risk_level bắt buộc."""
    states_requiring_risk = ["Under Replacement Review", "Approved for Transfer",
                              "Pending Decommission", "Transfer In Progress", "Transferred", "Completed"]
    if doc.workflow_state in states_requiring_risk and not doc.residual_risk_level:
        frappe.throw(
            _("Lỗi BR-13-06: Bắt buộc đánh giá mức độ rủi ro tồn dư trước khi tiến hành.")
        )


def _br07_high_risk_needs_replacement_review(doc) -> None:
    """BR-13-07: Thiết bị rủi ro cao cần đánh giá thay thế."""
    if doc.residual_risk_level == "High" and not doc.replacement_needed:
        frappe.msgprint(
            _("Cảnh báo BR-13-07: Thiết bị có rủi ro tồn dư cao. "
              "Vui lòng xem xét nhu cầu thay thế tại phần Quyết định kết quả."),
            alert=True,
            indicator="orange",
        )


def _br09_validate_transfer_location(doc) -> None:
    """BR-13-09: outcome=Transfer → transfer_to_location bắt buộc."""
    if doc.outcome == "Transfer" and not doc.transfer_to_location:
        frappe.throw(
            _("Lỗi BR-13-09: Kết quả 'Điều chuyển' yêu cầu khai báo địa điểm nhận.")
        )


def _br10_transfer_requires_receiving_officer(doc) -> None:
    """BR-13-10: outcome=Transfer → receiving_officer bắt buộc."""
    if doc.outcome == "Transfer" and not doc.receiving_officer:
        frappe.throw(
            _("Lỗi BR-13-10: Kết quả 'Điều chuyển' yêu cầu khai báo cán bộ tiếp nhận.")
        )


def _br08_high_value_needs_approval(doc) -> None:
    """BR-13-08: Giá trị > 500 triệu cần approved=1 trước khi Submit."""
    if doc.current_book_value and float(doc.current_book_value) > _HIGH_VALUE_THRESHOLD:
        if not doc.approved:
            frappe.throw(
                _("Lỗi BR-13-08: Giá trị sổ sách vượt 500 triệu VNĐ. "
                  "Phiếu này cần phê duyệt của HTM Manager trước khi hoàn tất.")
            )


# ─── Execution Helpers ────────────────────────────────────────────────────────

def _get_open_work_orders(asset_name: str) -> list:
    """Lấy danh sách Work Order đang mở cho asset."""
    open_pm = frappe.db.get_all(
        "PM Work Order",
        filters={"asset": asset_name, "status": ("not in", ["Completed", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=10,
    )
    open_cm = frappe.db.get_all(
        "Asset Repair",
        filters={"asset_ref": asset_name, "status": ("not in", ["Completed", "Cannot Repair", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=10,
    )
    open_cal = frappe.db.get_all(
        "IMM Asset Calibration",
        filters={"asset": asset_name, "status": ("not in", ["Completed", "Cancelled", "Failed"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=10,
    )
    return [r.name for r in (open_pm + open_cm + open_cal)]


def _execute_transfer(doc) -> None:
    """Đặt asset status=Transferred, cập nhật location."""
    if not doc.asset:
        return
    update_fields = {"status": "Transferred"}
    if doc.transfer_to_location:
        update_fields["location"] = doc.transfer_to_location
    if doc.transfer_to_department:
        update_fields["department"] = doc.transfer_to_department
    frappe.db.set_value("AC Asset", doc.asset, update_fields, update_modified=True)


def _execute_suspension(doc, new_status: str) -> None:
    """Đặt asset status = new_status."""
    if not doc.asset:
        return
    if not frappe.db.exists("AC Asset", doc.asset):
        frappe.log_error(f"IMM-13: Asset {doc.asset} not found khi set {new_status}", "IMM-13 Warning")
        return
    frappe.db.set_value("AC Asset", doc.asset, "status", new_status, update_modified=True)


def _trigger_imm14_archive(doc) -> None:
    """Tự động tạo Asset Archive Record (IMM-14) khi Retire."""
    try:
        aar = frappe.get_doc({
            "doctype": "Asset Archive Record",
            "asset": doc.asset,
            "decommission_request": doc.name,
            "archive_date": nowdate(),
            "archived_by": frappe.session.user,
            "retention_years": 10,
            "status": "Draft",
            "archive_notes": f"Tự động tạo từ IMM-13 {doc.name}",
        })
        aar.insert(ignore_permissions=True)
        frappe.msgprint(
            _("Hồ sơ lưu trữ <b>{0}</b> đã được tạo tự động (IMM-14).").format(aar.name),
            alert=True,
            indicator="green",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-14 Auto-create failed from {doc.name}")


def _get_htm_manager_emails() -> list:
    """Lấy danh sách email HTM Manager."""
    try:
        from assetcore.utils.helpers import _get_role_emails
        return _get_role_emails(["IMM HTM Manager", "IMM System Admin"])
    except Exception:
        return []


# ─── Business Logic APIs ──────────────────────────────────────────────────────

def get_asset_suspension_eligibility(asset_name: str) -> dict:
    """Check if asset can have a DR created.

    Returns:
        dict với keys: eligible, reasons, open_work_orders, asset_status, asset_name
    """
    if not frappe.db.exists("AC Asset", asset_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy thiết bị: {asset_name}")

    asset_doc = frappe.db.get_value(
        "AC Asset", asset_name, ["status", "asset_name"], as_dict=True
    )

    reasons = []
    if asset_doc.status in ("Decommissioned", "Archived", "Transferred"):
        reasons.append(f"Thiết bị đã ở trạng thái {asset_doc.status}")

    existing_dr = frappe.db.get_value(
        "Decommission Request",
        {"asset": asset_name, "docstatus": ("!=", 2)},
        "name",
    )
    if existing_dr:
        reasons.append(f"Đã có Phiếu Ngừng sử dụng đang xử lý: {existing_dr}")

    open_wos = _get_open_work_orders(asset_name)
    if open_wos:
        reasons.append(f"Còn {len(open_wos)} Work Order đang mở")

    return {
        "eligible": len(reasons) == 0,
        "reasons": reasons,
        "open_work_orders": open_wos,
        "asset_status": asset_doc.status,
        "asset_name": asset_doc.asset_name,
    }


def get_retirement_candidates() -> list:
    """Return assets flagged as retirement candidates."""
    candidates = frappe.db.get_all(
        "AC Asset",
        filters={"is_retirement_candidate": 1, "status": ("not in", ["Decommissioned", "Archived"])},
        fields=["name", "asset_name", "status", "retirement_flag_reason",
                "retirement_flagged_date", "device_model"],
        order_by="retirement_flagged_date desc",
    )
    return [dict(c) for c in candidates]


def get_dashboard_metrics() -> dict:
    """KPI metrics for IMM-13 dashboard."""
    import datetime
    year_start = datetime.date.today().replace(month=1, day=1).isoformat()

    suspended_ytd = frappe.db.count(
        "Decommission Request",
        {"docstatus": 1, "outcome": ("in", ["Suspend", "Retire"]), "creation": (">=", year_start)},
    )
    transferred_ytd = frappe.db.count(
        "Decommission Request",
        {"docstatus": 1, "outcome": "Transfer", "creation": (">=", year_start)},
    )
    retirement_candidates = frappe.db.count(
        "AC Asset",
        {"is_retirement_candidate": 1, "status": ("not in", ["Decommissioned", "Archived"])},
    )
    pending_approval = frappe.db.count(
        "Decommission Request",
        {"workflow_state": "Pending Decommission", "docstatus": 0},
    )

    states = frappe.db.sql(
        """
        SELECT workflow_state, COUNT(*) as cnt
        FROM `tabDecommission Request`
        WHERE docstatus = 0
        GROUP BY workflow_state
        """,
        as_dict=True,
    )

    return {
        "suspended_ytd": suspended_ytd,
        "transferred_ytd": transferred_ytd,
        "retirement_candidates_count": retirement_candidates,
        "pending_approval_count": pending_approval,
        "open_by_state": {r.workflow_state: r.cnt for r in states},
    }


# ─── Audit Trail ─────────────────────────────────────────────────────────────

def log_lifecycle_event(
    doc, event_type: str, from_status: str, to_status: str, notes: str = ""
) -> None:
    """Sinh immutable Asset Lifecycle Event cho mọi transition."""
    try:
        frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "asset": doc.asset,
            "event_type": event_type,
            "timestamp": now_datetime(),
            "actor": frappe.session.user,
            "from_status": from_status,
            "to_status": to_status,
            "root_doctype": "Decommission Request",
            "root_record": doc.name,
            "notes": notes,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-13 ALE log failed: {doc.name}")


# ─── Scheduler ───────────────────────────────────────────────────────────────

def check_retirement_candidates() -> None:
    """Scheduler daily job: kiểm tra ứng viên thanh lý."""
    candidates = frappe.db.get_all(
        "AC Asset",
        filters={"is_retirement_candidate": 1, "status": ("not in", ["Decommissioned", "Archived"])},
        fields=["name", "asset_name", "retirement_flag_reason"],
        limit=50,
    )
    if candidates:
        emails = _get_htm_manager_emails()
        if emails:
            try:
                from assetcore.utils.helpers import _safe_sendmail
                _safe_sendmail(
                    recipients=emails,
                    subject=f"[AssetCore] {len(candidates)} thiết bị đề xuất thanh lý",
                    message=f"Có {len(candidates)} thiết bị đang được đề xuất thanh lý: "
                            + ", ".join(r.name for r in candidates[:10]),
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "IMM-13 check_retirement_candidates email failed")


def check_overdue_dr() -> None:
    """Scheduler daily job: cảnh báo DR mở > 60 ngày."""
    threshold = add_days(nowdate(), -60)
    overdue = frappe.db.get_all(
        "Decommission Request",
        filters={
            "workflow_state": ("not in", ["Transferred", "Completed", "Cancelled"]),
            "docstatus": ("!=", 2),
            "creation": ("<", threshold),
        },
        fields=["name", "asset", "workflow_state", "creation"],
    )
    if overdue:
        emails = _get_htm_manager_emails()
        if emails:
            try:
                from assetcore.utils.helpers import _safe_sendmail
                _safe_sendmail(
                    recipients=emails,
                    subject=f"[AssetCore] {len(overdue)} phiếu ngừng sử dụng quá hạn > 60 ngày",
                    message=f"Có {len(overdue)} Decommission Request đang mở quá 60 ngày: "
                            + ", ".join(r.name for r in overdue[:10]),
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "IMM-13 check_overdue_dr email failed")
