# Copyright (c) 2026, AssetCore Team
# Service layer cho Module IMM-13 — Decommissioning & Disposal.
# Chứa toàn bộ business logic; controller chỉ delegate sang đây.

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, getdate

from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.constants import ErrorCode

_BOARD_THRESHOLD = 500_000_000  # 500 triệu VNĐ


# ─── Validation ──────────────────────────────────────────────────────────────

def validate_decommission_request(doc) -> None:
    """Chạy toàn bộ VR-01 → VR-05."""
    _vr01_check_active_work_orders(doc)
    _vr02_board_approval_threshold(doc)
    _vr03_bio_hazard_clearance(doc)
    _vr04_regulatory_clearance(doc)
    _vr05_data_destruction(doc)


def _vr01_check_active_work_orders(doc) -> None:
    """VR-01: Chặn nếu thiết bị còn Work Order đang mở."""
    if not doc.asset:
        return

    open_pm = frappe.db.get_all(
        "PM Work Order",
        filters={"asset": doc.asset, "status": ("not in", ["Completed", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=5,
    )
    open_cm = frappe.db.get_all(
        "Asset Repair",
        filters={"asset_ref": doc.asset, "status": ("not in", ["Completed", "Cannot Repair", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=5,
    )
    open_cal = frappe.db.get_all(
        "IMM Asset Calibration",
        filters={"asset": doc.asset, "status": ("not in", ["Completed", "Cancelled", "Failed"]), "docstatus": ("!=", 2)},
        fields=["name"],
        limit=5,
    )

    all_open = [r.name for r in (open_pm + open_cm + open_cal)]
    if all_open:
        names = ", ".join(all_open[:5])
        frappe.throw(
            _("Lỗi VR-01: Không thể thanh lý. Thiết bị <b>{0}</b> còn <b>{1}</b> lệnh công việc đang mở: <b>{2}</b>. "
              "Vui lòng đóng tất cả Work Order trước khi thanh lý.").format(
                doc.asset, len(all_open), names
            )
        )


def _vr02_board_approval_threshold(doc) -> None:
    """VR-02: Cảnh báo nếu giá trị sổ sách > 500 triệu VNĐ."""
    if doc.current_book_value and float(doc.current_book_value) > _BOARD_THRESHOLD:
        frappe.msgprint(
            _("Lưu ý VR-02: Giá trị sổ sách <b>{0:,.0f} VNĐ</b> vượt ngưỡng 500 triệu. "
              "Phiếu này cần phê duyệt của Ban Giám Đốc trước khi hoàn tất.").format(
                float(doc.current_book_value)
            ),
            alert=True,
            indicator="orange",
        )


def _vr03_bio_hazard_clearance(doc) -> None:
    """VR-03: biological_hazard = 1 → bắt buộc bio_hazard_clearance."""
    if doc.biological_hazard and not doc.bio_hazard_clearance:
        frappe.throw(
            _("Lỗi VR-03: Thiết bị có nguy cơ sinh học. "
              "Bắt buộc khai báo biện pháp xử lý an toàn sinh học tại trường "
              "'Biện pháp xử lý an toàn sinh học' (NĐ98/2021 §15).")
        )


def _vr04_regulatory_clearance(doc) -> None:
    """VR-04: regulatory_clearance_required = 1 → bắt buộc upload file."""
    if doc.regulatory_clearance_required and not doc.regulatory_clearance_doc:
        frappe.throw(
            _("Lỗi VR-04: Phiếu yêu cầu giấy phép thanh lý từ cơ quan quản lý. "
              "Vui lòng upload file giấy phép tại trường 'File giấy phép thanh lý' (NĐ98/2021 §16).")
        )


def _vr05_data_destruction(doc) -> None:
    """VR-05: data_destruction_required = 1 → bắt buộc confirmed trước Submit."""
    if doc.docstatus == 1:
        return  # Chỉ check trước submit
    if doc.data_destruction_required and not doc.data_destruction_confirmed:
        frappe.throw(
            _("Lỗi VR-05: Thiết bị có dữ liệu bệnh nhân cần xoá. "
              "Vui lòng xác nhận đã xoá dữ liệu tại trường 'Đã xoá dữ liệu (xác nhận)' trước khi Submit.")
        )


# ─── on_submit ───────────────────────────────────────────────────────────────

def on_submit_handler(doc) -> None:
    """Xử lý khi Submit Decommission Request.

    1. Set AC Asset.status = Decommissioned
    2. Log lifecycle event "decommissioned"
    3. Trigger IMM-14: tạo Asset Archive Record
    """
    _set_asset_decommissioned(doc.asset)
    log_lifecycle_event(
        doc=doc,
        event_type="decommissioned",
        from_status=doc.status or "Execution",
        to_status="Completed",
        notes=f"Thanh lý hoàn tất. Phương án: {doc.disposal_method or 'N/A'}",
    )
    doc.db_set("status", "Completed", commit=False)
    _trigger_imm14_archive(doc)


def on_cancel_handler(doc) -> None:
    """Block cancel nếu asset đã ở trạng thái Decommissioned."""
    if doc.asset:
        asset_status = frappe.db.get_value("AC Asset", doc.asset, "status")
        if asset_status == "Decommissioned":
            frappe.throw(
                _("Không thể huỷ phiếu thanh lý: Thiết bị {0} đã được đặt trạng thái 'Decommissioned'. "
                  "Vui lòng liên hệ quản trị viên.").format(doc.asset)
            )


def _set_asset_decommissioned(asset_name: str) -> None:
    """Đặt AC Asset.status = Decommissioned."""
    if not asset_name:
        return
    if not frappe.db.exists("AC Asset", asset_name):
        frappe.log_error(f"IMM-13: Asset {asset_name} not found khi set Decommissioned", "IMM-13 Warning")
        return
    frappe.db.set_value("AC Asset", asset_name, "status", "Decommissioned", update_modified=True)


def _trigger_imm14_archive(doc) -> None:
    """Tự động tạo Asset Archive Record (IMM-14)."""
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
            _("Hồ sơ lưu trữ <b><a href='/archive/{0}'>{0}</a></b> đã được tạo tự động (IMM-14).").format(aar.name),
            alert=True,
            indicator="green",
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-14 Auto-create failed from {doc.name}")


# ─── Business Logic ───────────────────────────────────────────────────────────

def get_asset_decommission_eligibility(asset_name: str) -> dict:
    """Kiểm tra thiết bị có đủ điều kiện thanh lý.

    Returns:
        dict với keys: eligible, reasons, asset_status, last_pm_date,
                       total_maintenance_cost, current_book_value, open_work_orders
    """
    if not frappe.db.exists("AC Asset", asset_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy thiết bị: {asset_name}")

    reasons = []
    open_wos = []

    # PM WOs
    pm_open = frappe.db.get_all(
        "PM Work Order",
        filters={"asset": asset_name, "status": ("not in", ["Completed", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
    )
    open_wos += [r.name for r in pm_open]

    # CM WOs
    cm_open = frappe.db.get_all(
        "Asset Repair",
        filters={"asset_ref": asset_name, "status": ("not in", ["Completed", "Cannot Repair", "Cancelled"]), "docstatus": ("!=", 2)},
        fields=["name"],
    )
    open_wos += [r.name for r in cm_open]

    if open_wos:
        reasons.append(f"Còn {len(open_wos)} Work Order đang mở: {', '.join(open_wos[:5])}")

    asset_doc = frappe.db.get_value("AC Asset", asset_name, ["status", "purchase_cost"], as_dict=True)

    return {
        "eligible": len(reasons) == 0,
        "reasons": reasons,
        "asset_status": asset_doc.get("status"),
        "current_book_value": asset_doc.get("purchase_cost", 0),
        "open_work_orders": open_wos,
    }


def get_dashboard_stats() -> dict:
    """KPI dashboard cho IMM-13."""
    import datetime
    year_start = datetime.date.today().replace(month=1, day=1).isoformat()

    ytd = frappe.db.count(
        "Decommission Request",
        {"status": "Completed", "creation": (">=", year_start)},
    )
    pending_approval = frappe.db.count("Decommission Request", {"status": "Pending Approval"})
    in_execution = frappe.db.count("Decommission Request", {"status": "Execution"})

    disposal_value = frappe.db.sql(
        "SELECT SUM(estimated_disposal_value) FROM `tabDecommission Request` "
        "WHERE status='Completed' AND creation >= %s",
        year_start,
    )
    total_disposal = float((disposal_value[0][0] or 0)) if disposal_value else 0

    return {
        "decommissioned_ytd": ytd,
        "pending_approval": pending_approval,
        "in_execution": in_execution,
        "total_disposal_value_ytd": total_disposal,
    }


# ─── Audit Trail ─────────────────────────────────────────────────────────────

def log_lifecycle_event(doc, event_type: str, from_status: str, to_status: str, notes: str = "") -> None:
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
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-13 ALE log failed: {doc.name}")


# ─── Scheduler ───────────────────────────────────────────────────────────────

def check_decommission_overdue() -> None:
    """Scheduler daily: cảnh báo phiếu mở > 60 ngày."""
    from frappe.utils import add_days
    threshold = add_days(nowdate(), -60)
    overdue = frappe.db.get_all(
        "Decommission Request",
        filters={
            "status": ("not in", ["Completed", "Rejected"]),
            "docstatus": ("!=", 2),
            "creation": ("<", threshold),
        },
        fields=["name", "asset", "status", "creation"],
    )
    if overdue:
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        recipients = _get_role_emails(["IMM HTM Manager", "IMM System Admin"])
        if recipients:
            _safe_sendmail(
                recipients=recipients,
                subject=f"[AssetCore] {len(overdue)} phiếu thanh lý quá hạn > 60 ngày",
                message=f"Có {len(overdue)} Decommission Request đang mở quá 60 ngày: "
                        + ", ".join(r.name for r in overdue[:10]),
            )
