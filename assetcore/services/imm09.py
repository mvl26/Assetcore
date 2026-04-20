# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — Tier 2 Business Service Layer.

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import (
    add_days,
    get_datetime,
    now_datetime,
    nowdate,
    time_diff_in_seconds,
)

from assetcore.repositories.asset_repo import AssetRepo, LifecycleEventRepo
from assetcore.repositories.repair_repo import FirmwareChangeRequestRepo, RepairRepo
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import (
    AssetStatus,
    ErrorCode,
    ServiceError,
)


# ─── Constants riêng cho IMM-09 ───────────────────────────────────────────────

class RepairStatus:
    OPEN = "Open"
    ASSIGNED = "Assigned"
    DIAGNOSING = "Diagnosing"
    PENDING_PARTS = "Pending Parts"
    IN_REPAIR = "In Repair"
    PENDING_INSPECTION = "Pending Inspection"
    COMPLETED = "Completed"
    CANNOT_REPAIR = "Cannot Repair"
    CANCELLED = "Cancelled"

    ACTIVE = (OPEN, ASSIGNED, DIAGNOSING, PENDING_PARTS, IN_REPAIR, PENDING_INSPECTION)
    CANNOT_START = (COMPLETED, CANNOT_REPAIR, CANCELLED)


class RiskClass:
    I = "Class I"
    II = "Class II"
    III = "Class III"


# SLA matrix (giờ) — BR-09-05
_SLA_MATRIX: dict[tuple[str, str], float] = {
    (RiskClass.III, "Emergency"): 4.0,
    (RiskClass.III, "Urgent"): 24.0,
    (RiskClass.III, "Normal"): 120.0,
    (RiskClass.II, "Emergency"): 8.0,
    (RiskClass.II, "Urgent"): 48.0,
    (RiskClass.II, "Normal"): 72.0,
    (RiskClass.I, "Emergency"): 24.0,
    (RiskClass.I, "Urgent"): 72.0,
    (RiskClass.I, "Normal"): 480.0,
}
_SLA_DEFAULT = 480.0


def get_sla_target(risk_class: str, priority: str) -> float:
    return _SLA_MATRIX.get((risk_class, priority), _SLA_DEFAULT)


# ─── Validators (gọi từ controller / service) ────────────────────────────────

def validate_repair_source(doc) -> None:
    """BR-09-01: WO phải có nguồn (incident_report OR source_pm_wo)."""
    if not doc.incident_report and not doc.source_pm_wo:
        frappe.throw(_("Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc"))


def validate_asset_not_under_repair(asset_ref: str) -> None:
    if RepairRepo.exists({
        "asset_ref": asset_ref,
        "status": ("in", list(RepairStatus.ACTIVE)),
        "docstatus": ("!=", 2),
    }):
        existing = RepairRepo.find_one(
            {"asset_ref": asset_ref,
             "status": ("in", list(RepairStatus.ACTIVE)),
             "docstatus": ("!=", 2)},
            fields=["name"],
        )
        frappe.throw(_(f"Thiết bị đang có WO sửa chữa đang mở: {existing['name']}"))


def check_repeat_failure(asset_ref: str) -> bool:
    """Kiểm tra tái hỏng trong 30 ngày gần nhất."""
    cutoff_date = add_days(nowdate(), -30)
    return RepairRepo.exists({
        "asset_ref": asset_ref,
        "status": RepairStatus.COMPLETED,
        "completion_datetime": (">=", cutoff_date),
        "docstatus": 1,
    })


def validate_spare_parts_stock_entries(doc) -> None:
    """BR-09-02: Mỗi dòng Spare Parts phải có stock_entry_ref."""
    stock_entry_exists = frappe.db.exists("DocType", "Stock Entry")
    for row in (doc.spare_parts_used or []):
        if not row.stock_entry_ref:
            frappe.throw(_(f"Vật tư '{row.item_name}' (dòng {row.idx}) thiếu phiếu xuất kho"))
        if stock_entry_exists and not frappe.db.exists("Stock Entry", row.stock_entry_ref):
            frappe.throw(_(f"Phiếu xuất kho '{row.stock_entry_ref}' không tồn tại"))


def validate_firmware_change_request(doc) -> None:
    """BR-09-03: firmware_updated=True → phải có FCR Approved."""
    if not doc.firmware_updated:
        return
    if not doc.firmware_change_request:
        frappe.throw(_("Cập nhật firmware yêu cầu phải có Firmware Change Request được phê duyệt"))
    fcr_status = FirmwareChangeRequestRepo.get_value(doc.firmware_change_request, "status")
    if fcr_status != "Approved":
        frappe.throw(_(f"FCR '{doc.firmware_change_request}' chưa được phê duyệt (status: {fcr_status})"))


def validate_repair_checklist_complete(doc) -> None:
    """BR-09-04: Tất cả Repair Checklist phải Pass trước Submit."""
    if not doc.repair_checklist:
        frappe.throw(_("Phải điền Repair Checklist trước khi hoàn thành sửa chữa"))
    for row in doc.repair_checklist:
        if not row.result:
            frappe.throw(_(f"Mục kiểm tra #{row.idx} '{row.test_description}' chưa điền kết quả"))
        if row.result == "Fail":
            frappe.throw(_(f"Mục kiểm tra #{row.idx} '{row.test_description}' chưa Pass — không thể hoàn thành"))


# ─── Asset state transitions ─────────────────────────────────────────────────

def set_asset_under_repair(asset_ref: str, wo_name: str) -> None:
    transition_asset_status(
        asset_name=asset_ref, to_status=AssetStatus.UNDER_REPAIR,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=wo_name,
        reason=f"Repair WO {wo_name} opened",
    )


def complete_repair(doc) -> None:
    """Xử lý khi WO được Submit: tính MTTR, cập nhật Asset, tạo Lifecycle Event."""
    doc.completion_datetime = now_datetime()
    open_dt = get_datetime(doc.open_datetime)
    close_dt = get_datetime(doc.completion_datetime)
    doc.mttr_hours = round(time_diff_in_seconds(close_dt, open_dt) / 3600.0, 2)

    doc.sla_target_hours = get_sla_target(doc.risk_class or RiskClass.I, doc.priority or "Normal")
    doc.sla_breached = 1 if doc.mttr_hours > doc.sla_target_hours else 0
    doc.status = RepairStatus.COMPLETED

    asset_updates: dict[str, Any] = {"last_repair_date": nowdate()}
    if doc.firmware_updated and doc.firmware_change_request:
        new_ver = FirmwareChangeRequestRepo.get_value(
            doc.firmware_change_request, "version_after")
        if new_ver:
            asset_updates["firmware_version"] = new_ver

    AssetRepo.set_values(doc.asset_ref, asset_updates)
    RepairRepo.set_values(doc.name, {
        "status": RepairStatus.COMPLETED,
        "completion_datetime": doc.completion_datetime,
        "mttr_hours": doc.mttr_hours,
        "sla_target_hours": doc.sla_target_hours,
        "sla_breached": doc.sla_breached,
    })

    transition_asset_status(
        asset_name=doc.asset_ref, to_status=AssetStatus.ACTIVE,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
        reason=f"Repair completed — MTTR: {doc.mttr_hours}h | SLA: {'Breached' if doc.sla_breached else 'Met'}",
    )

    # BR-11: nếu thiết bị yêu cầu hiệu chuẩn → tạo CAL WO recalibration
    try:
        from assetcore.services.imm11 import create_post_repair_calibration
        create_post_repair_calibration(doc.asset_ref)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-09 → IMM-11 recalibration hook failed")


def _create_lifecycle_event(*, asset: str, event_type: str, from_status: str,
                             to_status: str, root_record: str, notes: str = "") -> None:
    try:
        LifecycleEventRepo.create({
            "asset": asset,
            "event_type": event_type,
            "timestamp": now_datetime(),
            "actor": frappe.session.user,
            "from_status": from_status,
            "to_status": to_status,
            "root_record": root_record,
            "notes": notes,
        })
    except Exception:
        pass


# ─── Scheduler jobs ───────────────────────────────────────────────────────────

def check_repair_sla_breach() -> None:
    """Hourly: kiểm tra WO đang vượt SLA."""
    active_wos, _ = RepairRepo.list(
        filters={"status": ("in", [RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING,
                                    RepairStatus.PENDING_PARTS, RepairStatus.IN_REPAIR]),
                 "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class",
                "open_datetime", "sla_target_hours", "assigned_to"],
        page_size=1000,
    )
    for wo in active_wos:
        open_dt = get_datetime(wo["open_datetime"])
        elapsed_h = round(time_diff_in_seconds(now_datetime(), open_dt) / 3600.0, 2)
        sla = wo.get("sla_target_hours") or get_sla_target(
            wo.get("risk_class") or RiskClass.I, wo.get("priority") or "Normal")
        if elapsed_h >= sla:
            RepairRepo.set_values(wo["name"], {"sla_breached": 1})
            frappe.publish_realtime(
                "cm_sla_breached",
                {"wo": wo["name"], "asset": wo["asset_ref"]},
                user=wo.get("assigned_to"),
            )


def check_repair_overdue() -> None:
    """Daily 07:00: tổng hợp WO chưa hoàn thành quá 7 ngày."""
    cutoff = add_days(nowdate(), -7)
    overdue, _ = RepairRepo.list(
        filters={"status": ("in", [RepairStatus.OPEN, RepairStatus.ASSIGNED, RepairStatus.PENDING_PARTS]),
                 "open_datetime": ("<", cutoff),
                 "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class", "open_datetime"],
        page_size=1000,
    )
    if not overdue:
        return
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
    rows = frappe.db.sql("""
        SELECT asset_ref, AVG(mttr_hours) AS avg_mttr
        FROM (
            SELECT asset_ref, mttr_hours,
                   ROW_NUMBER() OVER (PARTITION BY asset_ref ORDER BY completion_datetime DESC) AS rn
            FROM `tabAsset Repair`
            WHERE docstatus = 1 AND status = %(completed)s AND mttr_hours IS NOT NULL
        ) ranked
        WHERE rn <= 12
        GROUP BY asset_ref
    """, {"completed": RepairStatus.COMPLETED}, as_dict=True)
    for r in rows:
        AssetRepo.set_values(r.asset_ref, {"mttr_hours": round(r.avg_mttr, 2)})


# ─── Business operations (gọi từ API) ─────────────────────────────────────────

_OPEN_STATUSES = (
    RepairStatus.OPEN, RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING,
    RepairStatus.PENDING_PARTS, RepairStatus.IN_REPAIR,
)


def list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = RepairRepo.list(
        filters=_normalize_filters(filters),
        fields=["name", "asset_ref", "asset_name", "repair_type", "priority",
                "status", "open_datetime", "completion_datetime", "mttr_hours",
                "sla_breached", "is_repeat_failure", "assigned_to",
                "root_cause_category", "risk_class"],
        order_by="open_datetime desc",
        page=page, page_size=page_size,
    )
    user_ids = {r.get("assigned_to") for r in rows if r.get("assigned_to")}
    if user_ids:
        users = frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"])
        user_map = {u.name: u.full_name for u in users}
        for r in rows:
            r["assigned_to_name"] = user_map.get(r.get("assigned_to"), r.get("assigned_to") or "")
    return {"data": rows, "pagination": pg}


def get_work_order(name: str) -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")
    data = doc.as_dict()
    data["asset_info"] = AssetRepo.get_value(
        doc.asset_ref,
        ["asset_name", "asset_category", "lifecycle_status", "risk_classification",
         "manufacturer_sn", "last_repair_date", "mttr_hours"],
        as_dict=True,
    ) or {}
    return data


def create_work_order(*, asset_ref: str, repair_type: str, priority: str,
                      failure_description: str, incident_report: str = "",
                      source_pm_wo: str = "") -> dict:
    if not incident_report and not source_pm_wo:
        raise ServiceError(
            "CM_NO_SOURCE",
            "CM-001: Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc",
        )
    asset_data = AssetRepo.get_value(
        asset_ref, ["asset_name", "risk_classification"], as_dict=True)
    if not asset_data:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy thiết bị: {asset_ref}")

    open_wo = RepairRepo.find_one(
        {"asset_ref": asset_ref, "status": ["not in", list(RepairStatus.CANNOT_START)]},
        fields=["name"],
    )
    if open_wo:
        raise ServiceError(
            ErrorCode.CONFLICT,
            f"CM-002: Thiết bị đang có phiếu sửa chữa đang mở: {open_wo['name']}",
        )

    risk_class = asset_data.get("risk_classification") or RiskClass.II
    sla_hours = get_sla_target(risk_class, priority)

    doc = frappe.get_doc({
        "doctype": RepairRepo.DOCTYPE,
        "asset_ref": asset_ref,
        "asset_name": asset_data.get("asset_name") or "",
        "repair_type": repair_type,
        "priority": priority,
        "failure_description": failure_description,
        "incident_report": incident_report,
        "source_pm_wo": source_pm_wo,
        "status": RepairStatus.OPEN,
        "sla_target_hours": sla_hours,
        "risk_class": risk_class,
        "open_datetime": now_datetime(),
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)

    transition_asset_status(
        asset_name=asset_ref, to_status=AssetStatus.UNDER_REPAIR,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
        reason=f"Repair WO {doc.name} created ({repair_type})",
    )
    frappe.db.commit()
    return {"name": doc.name, "status": RepairStatus.OPEN, "sla_target_hours": sla_hours}


def assign_technician(name: str, *, technician: str, priority: str = "") -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")
    if doc.status != RepairStatus.OPEN:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể phân công ở trạng thái {doc.status}")
    doc.assigned_to = technician
    doc.assigned_by = frappe.session.user
    doc.assigned_datetime = now_datetime()
    doc.status = RepairStatus.ASSIGNED
    if priority:
        doc.priority = priority
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    return {"name": name, "status": RepairStatus.ASSIGNED, "assigned_to": technician}


def submit_diagnosis(name: str, *, diagnosis_notes: str, needs_parts: int = 0) -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")
    if doc.status not in (RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể nộp chẩn đoán ở trạng thái {doc.status}")
    doc.diagnosis_notes = diagnosis_notes
    doc.status = RepairStatus.PENDING_PARTS if int(needs_parts) else RepairStatus.IN_REPAIR
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    _create_lifecycle_event(
        asset=doc.asset_ref, event_type="diagnosis_submitted",
        from_status=RepairStatus.ASSIGNED, to_status=doc.status,
        root_record=name,
    )
    return {"name": name, "status": doc.status}


def start_repair(name: str) -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")
    if doc.status not in (RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING, RepairStatus.PENDING_PARTS):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể bắt đầu sửa chữa ở trạng thái {doc.status}")
    doc.status = RepairStatus.IN_REPAIR
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    return {"name": name, "status": RepairStatus.IN_REPAIR}


def request_spare_parts(name: str, parts: list[dict]) -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")
    updated = 0
    for part in parts:
        for row in doc.spare_parts_used:
            if row.item_code == part.get("item_code"):
                row.stock_entry_ref = part.get("stock_entry_ref")
                updated += 1
    if doc.status == RepairStatus.PENDING_PARTS:
        doc.status = RepairStatus.IN_REPAIR
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    return {"name": name, "status": doc.status, "updated": updated}


def close_work_order(name: str, *, repair_summary: str, root_cause_category: str,
                     dept_head_name: str, checklist_results: list | None = None,
                     spare_parts: list | None = None, firmware_updated: int = 0,
                     firmware_change_request: str = "", cannot_repair: int = 0,
                     cannot_repair_reason: str = "") -> dict:
    doc = RepairRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO: {name}")

    if int(cannot_repair):
        return _mark_cannot_repair(doc, name, cannot_repair_reason)

    doc.repair_summary = repair_summary
    doc.root_cause_category = root_cause_category
    doc.dept_head_name = dept_head_name
    doc.dept_head_confirmation_datetime = now_datetime()
    doc.firmware_updated = int(firmware_updated)
    if firmware_change_request:
        doc.firmware_change_request = firmware_change_request
    if checklist_results:
        _apply_checklist(doc, checklist_results)
    if spare_parts:
        _apply_spare_parts(doc, spare_parts)

    doc.status = RepairStatus.PENDING_INSPECTION
    doc.flags.ignore_links = True
    doc.submit()  # submit() gọi save() internally; ignore_links set trước
    return {
        "name": name,
        "status": RepairStatus.COMPLETED,
        "mttr_hours": doc.mttr_hours,
        "sla_breached": doc.sla_breached,
    }


def _mark_cannot_repair(doc, name: str, reason: str) -> dict:
    doc.status = RepairStatus.CANNOT_REPAIR
    doc.cannot_repair_reason = reason
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    transition_asset_status(
        asset_name=doc.asset_ref, to_status=AssetStatus.OUT_OF_SERVICE,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=name,
        reason=f"Cannot repair: {reason}",
    )
    return {"name": name, "status": RepairStatus.CANNOT_REPAIR,
            "asset_status": AssetStatus.OUT_OF_SERVICE}


def _apply_checklist(doc, results: list[dict]) -> None:
    if not results:
        return
    for r in results:
        if "description" in r and "test_description" not in r:
            r["test_description"] = r.pop("description")
    if not doc.repair_checklist:
        for r in results:
            doc.append("repair_checklist", {
                "test_description": r.get("test_description", ""),
                "result": r.get("result", ""),
                "measured_value": r.get("measured_value", ""),
                "notes": r.get("notes", ""),
            })
        return
    for r in results:
        for row in doc.repair_checklist:
            if row.idx == r.get("idx"):
                row.result = r.get("result")
                row.measured_value = r.get("measured_value", "")
                row.notes = r.get("notes", "")


def _apply_spare_parts(doc, parts: list[dict]) -> None:
    for p in parts:
        doc.append("spare_parts_used", p)


# ─── Reports / KPIs ──────────────────────────────────────────────────────────

def get_kpis(year: int, month: int) -> dict:
    start, end = _month_range(year, month)
    between = ("between", [start, end])

    completed = frappe.get_all(
        RepairRepo.DOCTYPE,
        filters={"status": RepairStatus.COMPLETED, "docstatus": 1,
                 "completion_datetime": between},
        fields=["name", "mttr_hours", "sla_breached", "is_repeat_failure", "root_cause_category"],
    )
    total = len(completed)
    mttr_avg = round(sum(w.mttr_hours or 0 for w in completed) / total, 2) if total else 0
    sla_met = sum(1 for w in completed if not w.sla_breached)
    sla_compliance = round(sla_met / total * 100, 1) if total else 0
    repeat_failures = sum(1 for w in completed if w.is_repeat_failure)

    root_cause_count: dict[str, int] = {}
    for w in completed:
        rc = w.root_cause_category or "Unknown"
        root_cause_count[rc] = root_cause_count.get(rc, 0) + 1

    open_wos = RepairRepo.count({"status": ("in", list(_OPEN_STATUSES)), "docstatus": 0})

    return {
        "kpis": {
            "total_completed": total,
            "mttr_avg_hours": mttr_avg,
            "sla_compliance_pct": sla_compliance,
            "repeat_failure_count": repeat_failures,
            "open_wos": open_wos,
        },
        "root_cause_breakdown": [
            {"category": k, "count": v}
            for k, v in sorted(root_cause_count.items(), key=lambda x: -x[1])
        ],
    }


def get_asset_history(asset_ref: str, *, limit: int = 10) -> dict:
    history, _ = RepairRepo.list(
        filters={"asset_ref": asset_ref, "docstatus": 1},
        fields=["name", "repair_type", "priority", "open_datetime", "completion_datetime",
                "mttr_hours", "sla_breached", "root_cause_category", "repair_summary"],
        order_by="open_datetime desc",
        page_size=int(limit),
    )
    return {"asset_ref": asset_ref, "history": history}


def search_spare_parts(query: str, *, limit: int = 10) -> list[dict]:
    if not query or len(query) < 2:
        return []
    rows = frappe.db.sql(
        """
        SELECT DISTINCT part_name, manufacturer_part_no, estimated_cost
        FROM `tabIMM Device Spare Part`
        WHERE part_name LIKE %(q)s OR manufacturer_part_no LIKE %(q)s
        ORDER BY part_name ASC
        LIMIT %(lim)s
        """,
        {"q": f"%{query}%", "lim": int(limit)},
        as_dict=True,
    )
    return [
        {
            "item_code": r.get("manufacturer_part_no") or r.get("part_name") or "",
            "item_name": r.get("part_name") or "",
            "manufacturer_part_no": r.get("manufacturer_part_no") or "",
            "qty": 1, "uom": "Nos",
            "unit_cost": float(r.get("estimated_cost") or 0),
            "total_cost": float(r.get("estimated_cost") or 0),
            "stock_entry_ref": "", "notes": "", "idx": 0,
        }
        for r in rows
    ]


def get_mttr_report(year: int, month: int) -> dict:
    start_cur, end_cur = _month_range(year, month)
    completed = frappe.get_all(
        RepairRepo.DOCTYPE,
        filters={"status": RepairStatus.COMPLETED, "docstatus": 1,
                 "completion_datetime": ("between", [start_cur, end_cur])},
        fields=["mttr_hours", "is_repeat_failure", "total_parts_cost"],
    )
    total = len(completed)
    mttr_avg = round(sum(r.mttr_hours or 0 for r in completed) / total, 2) if total else 0
    first_fix_rate = (
        round(sum(1 for r in completed if not r.is_repeat_failure) / total * 100, 1)
        if total else 0
    )
    avg_cost = round(sum(r.total_parts_cost or 0 for r in completed) / total, 0) if total else 0

    backlog_count = RepairRepo.count({
        "status": ("in", list(_OPEN_STATUSES)),
        "docstatus": 0,
    })
    backlog_raw = frappe.db.sql("""
        SELECT clinical_dept AS dept, COUNT(*) AS count
        FROM `tabAsset Repair`
        WHERE status NOT IN ('Completed','Cannot Repair','Cancelled') AND docstatus = 0
        GROUP BY clinical_dept
    """, as_dict=True)

    return {
        "mttr_avg": mttr_avg,
        "first_fix_rate": first_fix_rate,
        "backlog_count": backlog_count,
        "cost_per_repair": avg_cost,
        "mttr_trend": _mttr_trend(year, month),
        "backlog_by_dept": [{"dept": r.dept or "—", "count": r.count} for r in backlog_raw],
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _month_range(y: int, m: int) -> tuple[str, str]:
    start = f"{y}-{m:02d}-01"
    end = f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"
    return start, end


def _mttr_trend(y: int, m: int) -> list[dict]:
    offset = m - 6
    window_start = f"{y + offset // 12}-{offset % 12 + 1:02d}-01"
    rows = frappe.db.sql("""
        SELECT DATE_FORMAT(completion_datetime, '%%Y-%%m') AS month,
               AVG(mttr_hours) AS avg_mttr
        FROM `tabAsset Repair`
        WHERE docstatus = 1 AND status = 'Completed'
          AND completion_datetime >= %s
        GROUP BY DATE_FORMAT(completion_datetime, '%%Y-%%m')
    """, (window_start,), as_dict=True)
    by_month = {r.month: round(r.avg_mttr or 0, 2) for r in rows}
    trend = []
    for i in range(5, -1, -1):
        o = m - 1 - i
        key = f"{y + o // 12}-{o % 12 + 1:02d}"
        trend.append({"month": key, "value": by_month.get(key, 0)})
    return trend


_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def _normalize_filters(f: dict | None) -> dict:
    out: dict = {}
    for k, v in (f or {}).items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out
