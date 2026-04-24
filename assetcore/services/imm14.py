# Copyright (c) 2026, AssetCore Team
# Service layer cho Module IMM-14 — Record Archive & Lifecycle Closure.
# Chứa toàn bộ business logic; controller chỉ delegate sang đây.

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.constants import ErrorCode


# ─── Validation ──────────────────────────────────────────────────────────────

def validate_archive_record(doc) -> None:
    """VR-14-01 đến VR-14-04."""
    if not doc.asset:
        frappe.throw(_("Lỗi VR-14-01: Trường Thiết bị là bắt buộc."))
    if doc.retention_years is not None and int(doc.retention_years) < 10:
        frappe.throw(
            _("Lỗi VR-14-02: Số năm lưu trữ không được nhỏ hơn 10 năm (NĐ98/2021 §17).")
        )


def before_save_handler(doc) -> None:
    """Tính release_date và đếm tài liệu trước khi lưu."""
    if doc.archive_date and doc.retention_years:
        try:
            from dateutil.relativedelta import relativedelta
            from frappe.utils import getdate
            d = getdate(doc.archive_date)
            doc.release_date = (d + relativedelta(years=int(doc.retention_years))).isoformat()
        except Exception:
            pass
    doc.total_documents_archived = len(doc.documents or [])


# ─── on_submit ───────────────────────────────────────────────────────────────

def finalize_archive_handler(doc) -> None:
    """on_submit: VR-14-04 + set Asset Archived + log ALE.

    Raises:
        frappe.ValidationError: nếu status != Verified
    """
    if doc.status != "Verified":
        frappe.throw(
            _("Lỗi VR-14-04: Không thể hoàn tất lưu trữ. "
              "Phiếu chưa được QA Officer xác minh (status hiện tại: {0}).").format(doc.status)
        )
    _set_asset_archived(doc.asset)
    log_lifecycle_event(doc, "archived", "Verified", "Archived", "Hồ sơ thiết bị đã lưu trữ dài hạn")
    doc.db_set("status", "Archived", commit=False)


def _set_asset_archived(asset_name: str) -> None:
    """Đặt AC Asset.status = Archived."""
    if not asset_name:
        return
    if not frappe.db.exists("AC Asset", asset_name):
        frappe.log_error(f"IMM-14: Asset {asset_name} not found khi set Archived", "IMM-14 Warning")
        return
    frappe.db.set_value("AC Asset", asset_name, "status", "Archived", update_modified=True)


# ─── Compile Asset History ────────────────────────────────────────────────────

def compile_asset_history(archive_name: str) -> dict:
    """Tự động tổng hợp tài liệu từ tất cả module cho asset.

    Ghi đè documents table. Chuyển status sang Compiling.

    Returns:
        dict với keys: compiled, breakdown, missing_count
    """
    doc = frappe.get_doc("Asset Archive Record", archive_name)
    asset = doc.asset
    entries = []
    breakdown: dict[str, int] = {}

    # IMM-04: Commissioning
    comm = _collect_commissioning_docs(asset)
    entries += comm
    breakdown["Commissioning"] = len(comm)

    # IMM-08: PM
    pm = _collect_pm_records(asset)
    entries += pm
    breakdown["PM Record"] = len(pm)

    # IMM-09: Repair
    repair = _collect_repair_records(asset)
    entries += repair
    breakdown["Repair Record"] = len(repair)

    # IMM-11: Calibration
    cal = _collect_calibration_records(asset)
    entries += cal
    breakdown["Calibration"] = len(cal)

    # IMM-12: Incident
    inc = _collect_incident_records(asset)
    entries += inc
    breakdown["Incident"] = len(inc)

    # Mark missing if count == 0
    _add_missing_entries(entries, breakdown)

    doc.documents = []
    for e in entries:
        doc.append("documents", e)

    doc.total_documents_archived = len(entries)
    doc.status = "Compiling"
    doc.save(ignore_permissions=True)

    missing_count = sum(1 for e in entries if e.get("archive_status") == "Missing")
    return {"compiled": len(entries), "breakdown": breakdown, "missing_count": missing_count}


def _collect_commissioning_docs(asset: str) -> list[dict]:
    rows = frappe.db.get_all(
        "Asset Commissioning",
        filters={"final_asset": asset, "docstatus": ("!=", 2)},
        fields=["name", "commissioning_date"],
    )
    return [{
        "document_type": "Commissioning",
        "document_name": r.name,
        "document_date": r.commissioning_date,
        "archive_status": "Included",
    } for r in rows]


def _collect_pm_records(asset: str) -> list[dict]:
    rows = frappe.db.get_all(
        "PM Work Order",
        filters={"asset": asset, "docstatus": ("!=", 2)},
        fields=["name", "completed_date"],
        order_by="completed_date asc",
    )
    return [{
        "document_type": "PM Record",
        "document_name": r.name,
        "document_date": r.completed_date,
        "archive_status": "Included",
    } for r in rows]


def _collect_repair_records(asset: str) -> list[dict]:
    rows = frappe.db.get_all(
        "Asset Repair",
        filters={"asset_ref": asset, "docstatus": ("!=", 2)},
        fields=["name", "completion_datetime"],
        order_by="completion_datetime asc",
    )
    return [{
        "document_type": "Repair Record",
        "document_name": r.name,
        "document_date": str(r.completion_datetime)[:10] if r.completion_datetime else None,
        "archive_status": "Included",
    } for r in rows]


def _collect_calibration_records(asset: str) -> list[dict]:
    rows = frappe.db.get_all(
        "IMM Asset Calibration",
        filters={"asset": asset, "docstatus": ("!=", 2)},
        fields=["name", "calibration_date"],
        order_by="calibration_date asc",
    )
    return [{
        "document_type": "Calibration",
        "document_name": r.name,
        "document_date": r.calibration_date,
        "archive_status": "Included",
    } for r in rows]


def _collect_incident_records(asset: str) -> list[dict]:
    rows = frappe.db.get_all(
        "Incident Report",
        filters={"asset": asset, "docstatus": ("!=", 2)},
        fields=["name", "reported_date"],
        order_by="reported_date asc",
    )
    return [{
        "document_type": "Incident",
        "document_name": r.name,
        "document_date": r.reported_date,
        "archive_status": "Included",
    } for r in rows]


def _add_missing_entries(entries: list, breakdown: dict) -> None:
    """Thêm Missing entry nếu một loại tài liệu không có records."""
    required_types = ["Commissioning", "PM Record", "Repair Record", "Calibration"]
    for doc_type in required_types:
        if breakdown.get(doc_type, 0) == 0:
            entries.append({
                "document_type": doc_type,
                "document_name": None,
                "document_date": None,
                "archive_status": "Missing",
                "notes": f"Không tìm thấy hồ sơ {doc_type} cho thiết bị này",
            })


# ─── Read APIs ────────────────────────────────────────────────────────────────

def get_asset_full_history(asset_name: str) -> dict:
    """Lấy toàn bộ timeline vòng đời thiết bị từ Asset Lifecycle Events."""
    if not frappe.db.exists("AC Asset", asset_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy thiết bị: {asset_name}")

    asset_doc = frappe.db.get_value("AC Asset", asset_name, ["asset_name", "status"], as_dict=True)

    events = frappe.db.get_all(
        "Asset Lifecycle Event",
        filters={"asset": asset_name},
        fields=["event_type", "timestamp", "actor", "from_status", "to_status", "root_doctype", "root_record", "notes"],
        order_by="timestamp asc",
    )

    timeline = [{
        "date": str(e.timestamp)[:10] if e.timestamp else None,
        "event_type": e.event_type,
        "module": _event_to_module(e.root_doctype or ""),
        "record": e.root_record,
        "actor": e.actor,
        "notes": e.notes,
    } for e in events]

    return {
        "asset": asset_name,
        "asset_name": asset_doc.get("asset_name", ""),
        "asset_status": asset_doc.get("status", ""),
        "timeline": timeline,
        "total_events": len(timeline),
    }


def _event_to_module(root_doctype: str) -> str:
    mapping = {
        "Asset Commissioning": "IMM-04",
        "PM Work Order": "IMM-08",
        "Asset Repair": "IMM-09",
        "IMM Asset Calibration": "IMM-11",
        "Incident Report": "IMM-12",
        "Decommission Request": "IMM-13",
        "Asset Archive Record": "IMM-14",
    }
    return mapping.get(root_doctype, root_doctype)


def get_dashboard_stats() -> dict:
    """KPI dashboard cho IMM-14."""
    import datetime
    year_start = datetime.date.today().replace(month=1, day=1).isoformat()

    archived_ytd = frappe.db.count("Asset Archive Record", {"status": "Archived", "creation": (">=", year_start)})
    pending_verify = frappe.db.count("Asset Archive Record", {"status": "Compiling"})
    total_all_time = frappe.db.count("Asset Archive Record", {"status": "Archived"})

    return {
        "archived_ytd": archived_ytd,
        "pending_verification": pending_verify,
        "total_archived_all_time": total_all_time,
    }


# ─── Audit Trail ─────────────────────────────────────────────────────────────

def log_lifecycle_event(doc, event_type: str, from_status: str, to_status: str, notes: str = "") -> None:
    """Sinh immutable Asset Lifecycle Event."""
    try:
        frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "asset": doc.asset,
            "event_type": event_type,
            "timestamp": now_datetime(),
            "actor": frappe.session.user,
            "from_status": from_status,
            "to_status": to_status,
            "root_doctype": "Asset Archive Record",
            "root_record": doc.name,
            "notes": notes,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-14 ALE log failed: {doc.name}")


# ─── Scheduler ───────────────────────────────────────────────────────────────

def check_archive_expiry() -> None:
    """Scheduler monthly: cảnh báo AAR sắp hết hạn lưu trữ (60 ngày)."""
    from frappe.utils import add_days
    threshold_date = add_days(nowdate(), 60)
    expiring = frappe.db.get_all(
        "Asset Archive Record",
        filters={
            "status": "Archived",
            "release_date": ("<=", threshold_date),
            "release_date": (">=", nowdate()),
        },
        fields=["name", "asset", "release_date"],
    )
    if expiring:
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        recipients = _get_role_emails(["IMM HTM Manager", "IMM System Admin"])
        if recipients:
            items = "\n".join(f"- {r.name} (asset: {r.asset}, hết hạn: {r.release_date})" for r in expiring)
            _safe_sendmail(
                recipients=recipients,
                subject=f"[AssetCore] {len(expiring)} hồ sơ lưu trữ sắp hết hạn (≤60 ngày)",
                message=f"Các hồ sơ sau sắp hết hạn lưu trữ:\n{items}",
            )
