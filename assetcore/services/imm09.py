# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — Service Layer

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, get_datetime, add_days
from typing import Optional

_DOCTYPE_REPAIR = "Asset Repair"


def validate_repair_source(doc) -> None:
    """BR-09-01: WO phải có nguồn (incident_report OR source_pm_wo)."""
    if not doc.incident_report and not doc.source_pm_wo:
        frappe.throw(_("Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc"))


def validate_asset_not_under_repair(asset_ref: str) -> None:
    """Ngăn tạo WO duplicate khi thiết bị đang sửa chữa."""
    existing = frappe.db.exists(_DOCTYPE_REPAIR, {
        "asset_ref": asset_ref,
        "status": ("in", ["Open", "Assigned", "Diagnosing", "Pending Parts", "In Repair", "Pending Inspection"]),
        "docstatus": ("!=", 2),
    })
    if existing:
        frappe.throw(_(f"Thiết bị đang có WO sửa chữa đang mở: {existing}"))


def check_repeat_failure(asset_ref: str) -> bool:
    """Kiểm tra tái hỏng trong 30 ngày gần nhất."""
    cutoff_date = add_days(nowdate(), -30)
    return bool(frappe.db.exists(_DOCTYPE_REPAIR, {
        "asset_ref": asset_ref,
        "status": "Completed",
        "completion_datetime": (">=", cutoff_date),
        "docstatus": 1,
    }))


def set_asset_under_repair(asset_ref: str, wo_name: str) -> None:
    """Set Asset.status = 'Under Repair' + tạo Lifecycle Event."""
    prev_status = frappe.db.get_value("Asset", asset_ref, "status") or "Active"
    frappe.db.set_value("Asset", asset_ref, "status", "Under Repair")
    _create_lifecycle_event(
        asset=asset_ref, event_type="repair_opened",
        from_status=prev_status, to_status="Under Repair",
        root_record=wo_name,
    )


def validate_spare_parts_stock_entries(doc) -> None:
    """BR-09-02: Mỗi dòng Spare Parts phải có stock_entry_ref."""
    for row in (doc.spare_parts_used or []):
        if not row.stock_entry_ref:
            frappe.throw(_(f"Vật tư '{row.item_name}' (dòng {row.idx}) thiếu phiếu xuất kho"))
        if not frappe.db.exists("Stock Entry", row.stock_entry_ref):
            frappe.throw(_(f"Phiếu xuất kho '{row.stock_entry_ref}' không tồn tại trong hệ thống"))


def validate_firmware_change_request(doc) -> None:
    """BR-09-03: firmware_updated=True → phải có FCR Approved."""
    if not doc.firmware_updated:
        return
    if not doc.firmware_change_request:
        frappe.throw(_("Cập nhật firmware yêu cầu phải có Firmware Change Request được phê duyệt và liên kết"))
    fcr_status = frappe.db.get_value("Firmware Change Request", doc.firmware_change_request, "status")
    if fcr_status != "Approved":
        frappe.throw(_(f"Firmware Change Request '{doc.firmware_change_request}' chưa được phê duyệt (status: {fcr_status})"))


def validate_repair_checklist_complete(doc) -> None:
    """BR-09-04: Tất cả Repair Checklist phải Pass trước Submit."""
    if not doc.repair_checklist:
        frappe.throw(_("Phải điền Repair Checklist trước khi hoàn thành sửa chữa"))
    for row in doc.repair_checklist:
        if not row.result:
            frappe.throw(_(f"Mục kiểm tra #{row.idx} '{row.test_description}' chưa điền kết quả"))
        if row.result == "Fail":
            frappe.throw(_(f"Mục kiểm tra #{row.idx} '{row.test_description}' chưa Pass — không thể hoàn thành"))


def get_sla_target(risk_class: str, priority: str) -> float:
    """Trả về SLA target (giờ) theo risk class và priority."""
    sla_matrix = {
        ("Class III", "Emergency"): 4.0,
        ("Class III", "Urgent"):    24.0,
        ("Class III", "Normal"):    120.0,
        ("Class II",  "Emergency"): 8.0,
        ("Class II",  "Urgent"):    48.0,
        ("Class II",  "Normal"):    72.0,
        ("Class I",   "Emergency"): 24.0,
        ("Class I",   "Urgent"):    72.0,
        ("Class I",   "Normal"):    480.0,
    }
    return sla_matrix.get((risk_class, priority), 480.0)


def complete_repair(doc) -> None:
    """Xử lý khi WO được Submit: tính MTTR, cập nhật Asset, tạo Lifecycle Event."""
    from frappe.utils import time_diff_in_seconds
    doc.completion_datetime = now_datetime()
    # MTTR in hours (simple calendar time, not working hours)
    open_dt = get_datetime(doc.open_datetime)
    close_dt = get_datetime(doc.completion_datetime)
    diff_seconds = time_diff_in_seconds(close_dt, open_dt)
    doc.mttr_hours = round(diff_seconds / 3600.0, 2)

    doc.sla_target_hours = get_sla_target(doc.risk_class or "Class I", doc.priority or "Normal")
    doc.sla_breached = 1 if doc.mttr_hours > doc.sla_target_hours else 0

    asset_updates = {
        "status": "Active",
        "custom_last_repair_date": nowdate(),
    }
    if doc.firmware_updated and doc.firmware_change_request:
        new_ver = frappe.db.get_value("Firmware Change Request", doc.firmware_change_request, "version_after")
        if new_ver:
            asset_updates["custom_firmware_version"] = new_ver

    doc.status = "Completed"
    frappe.db.set_value("Asset", doc.asset_ref, asset_updates)
    frappe.db.set_value(_DOCTYPE_REPAIR, doc.name, {
        "status": "Completed",
        "completion_datetime": doc.completion_datetime,
        "mttr_hours": doc.mttr_hours,
        "sla_target_hours": doc.sla_target_hours,
        "sla_breached": doc.sla_breached,
    })

    _create_lifecycle_event(
        asset=doc.asset_ref, event_type="repair_completed",
        from_status="Under Repair", to_status="Active",
        root_record=doc.name,
        notes=f"MTTR: {doc.mttr_hours}h | SLA: {'Breached' if doc.sla_breached else 'Met'}",
    )


def _create_lifecycle_event(asset: str, event_type: str, from_status: str,
                             to_status: str, root_record: str, notes: str = "") -> None:
    """Tạo Asset Lifecycle Event (immutable audit trail)."""
    try:
        frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "asset": asset,
            "event_type": event_type,
            "timestamp": now_datetime(),
            "actor": frappe.session.user,
            "from_status": from_status,
            "to_status": to_status,
            "root_record": root_record,
            "notes": notes,
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Lifecycle event failure should not block the main operation


def check_repair_sla_breach() -> None:
    """Hourly: kiểm tra WO đang vượt SLA."""
    from frappe.utils import time_diff_in_seconds
    active_wos = frappe.get_all(
        _DOCTYPE_REPAIR,
        filters={"status": ("in", ["Assigned", "Diagnosing", "Pending Parts", "In Repair"]), "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class", "open_datetime", "sla_target_hours", "assigned_to"],
    )
    for wo in active_wos:
        open_dt = get_datetime(wo.open_datetime)
        elapsed_h = round(time_diff_in_seconds(now_datetime(), open_dt) / 3600.0, 2)
        sla = wo.sla_target_hours or get_sla_target(wo.risk_class or "Class I", wo.priority or "Normal")
        if elapsed_h >= sla:
            frappe.db.set_value(_DOCTYPE_REPAIR, wo.name, "sla_breached", 1)
            frappe.publish_realtime("cm_sla_breached", {"wo": wo.name, "asset": wo.asset_ref}, user=wo.assigned_to)


def check_repair_overdue() -> None:
    """Daily 07:00: tổng hợp WO chưa hoàn thành quá 7 ngày."""
    cutoff = add_days(nowdate(), -7)
    overdue = frappe.get_all(
        _DOCTYPE_REPAIR,
        filters={"status": ("in", ["Open", "Assigned", "Pending Parts"]), "open_datetime": ("<", cutoff), "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class", "open_datetime"],
    )
    if overdue:
        try:
            wm = frappe.db.get_value("User", {"role_profile_name": "Workshop Manager"}, "name")
            if wm:
                frappe.sendmail(
                    recipients=[wm],
                    subject=f"[AssetCore] {len(overdue)} WO sửa chữa quá 7 ngày",
                    message=f"Có {len(overdue)} phiếu sửa chữa quá 7 ngày chưa hoàn thành.",
                )
        except Exception:
            pass


def update_asset_mttr_avg() -> None:
    """Monthly 1st 06:00: cập nhật MTTR trung bình 12 tháng cho từng thiết bị."""
    assets = frappe.get_all("Asset", filters={"status": "Active"}, pluck="name")
    for asset in assets:
        completed = frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": asset, "docstatus": 1, "status": "Completed"},
            fields=["mttr_hours"],
            order_by="completion_datetime desc",
            limit=12,
        )
        if completed:
            avg = sum(w.mttr_hours or 0 for w in completed) / len(completed)
            frappe.db.set_value("Asset", asset, "custom_mttr_avg_hours", round(avg, 2))
