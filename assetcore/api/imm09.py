# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — API Layer

import frappe
import json
from frappe import _
from frappe.utils import now_datetime, nowdate, add_days
import math


_DOCTYPE = "Asset Repair"
_STATUS_IN_REPAIR = "In Repair"
_STATUS_PENDING_PARTS = "Pending Parts"
_STATUS_CANNOT_REPAIR = "Cannot Repair"
_STATUS_UNDER_REPAIR = "Under Repair"
_STATUS_OUT_OF_SERVICE = "Out of Service"


def _ok(data):
    return {"success": True, "data": data}

def _err(msg: str, code: int = 400):
    frappe.local.response["http_status_code"] = code
    return {"success": False, "error": msg}


@frappe.whitelist()
def list_repair_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20):
    """Danh sách Asset Repair WO có phân trang."""
    try:
        f = json.loads(filters) if isinstance(filters, str) else filters
        page, page_size = int(page), int(page_size)
        offset = (page - 1) * page_size

        fields = ["name", "asset_ref", "asset_name", "repair_type", "priority", "status",
                  "open_datetime", "completion_datetime", "mttr_hours", "sla_breached",
                  "is_repeat_failure", "assigned_to", "root_cause_category", "risk_class"]

        total = frappe.db.count(_DOCTYPE, f)
        data = frappe.get_all(_DOCTYPE, filters=f, fields=fields,
                               order_by="open_datetime desc", limit=page_size, start=offset)

        return _ok({
            "data": data,
            "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": math.ceil(total / page_size)},
        })
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_repair_work_order(name: str):
    """Chi tiết 1 WO gồm spare parts, checklist, asset info."""
    try:
        doc = frappe.get_doc(_DOCTYPE, name)
        data = doc.as_dict()
        # Asset enrichment
        asset = frappe.db.get_value("Asset", doc.asset_ref,
            ["asset_name", "asset_category", "status", "custom_risk_class", "serial_no",
             "custom_last_repair_date", "custom_mttr_avg_hours"], as_dict=True) or {}
        data["asset_info"] = asset
        return _ok(data)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy WO: {name}", 404)
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def assign_technician(name: str, technician: str, priority: str = ""):
    """Phân công KTV → status Assigned."""
    try:
        doc = frappe.get_doc(_DOCTYPE, name)
        if doc.status not in ("Open",):
            return _err(f"Không thể phân công ở trạng thái {doc.status}")
        doc.assigned_to = technician
        doc.assigned_by = frappe.session.user
        doc.assigned_datetime = now_datetime()
        doc.status = "Assigned"
        if priority:
            doc.priority = priority
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        return _ok({"name": name, "status": "Assigned", "assigned_to": technician})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def submit_diagnosis(name: str, diagnosis_notes: str, needs_parts: int = 0):
    """KTV nộp kết quả chẩn đoán → Diagnosing hoặc Pending Parts."""
    try:
        doc = frappe.get_doc(_DOCTYPE, name)
        if doc.status not in ("Assigned", "Diagnosing"):
            return _err(f"Không thể nộp chẩn đoán ở trạng thái {doc.status}")
        doc.diagnosis_notes = diagnosis_notes
        doc.status = _STATUS_PENDING_PARTS if int(needs_parts) else _STATUS_IN_REPAIR
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)

        # Create lifecycle event
        from assetcore.services.imm09 import _create_lifecycle_event
        _create_lifecycle_event(
            asset=doc.asset_ref, event_type="diagnosis_submitted",
            from_status="Assigned", to_status=doc.status,
            root_record=name,
        )
        return _ok({"name": name, "status": doc.status})
    except Exception as e:
        return _err(str(e))


def _apply_checklist(doc, checklist_results: str) -> None:
    results = json.loads(checklist_results) if isinstance(checklist_results, str) else checklist_results
    if not results:
        return
    if not doc.repair_checklist:
        for r in results:
            doc.append("repair_checklist", {
                "test_description": r.get("description", r.get("test_description", "")),
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


def _apply_spare_parts(doc, spare_parts: str) -> None:
    parts = json.loads(spare_parts) if isinstance(spare_parts, str) else spare_parts
    for p in parts:
        doc.append("spare_parts_used", p)


def _mark_cannot_repair(doc, name: str, reason: str) -> dict:
    from assetcore.services.imm09 import _create_lifecycle_event
    doc.status = _STATUS_CANNOT_REPAIR
    doc.cannot_repair_reason = reason
    doc.flags.ignore_links = True
    doc.save(ignore_permissions=True)
    frappe.db.set_value("Asset", doc.asset_ref, "status", _STATUS_OUT_OF_SERVICE)
    _create_lifecycle_event(
        asset=doc.asset_ref, event_type="cannot_repair",
        from_status=_STATUS_UNDER_REPAIR, to_status=_STATUS_OUT_OF_SERVICE,
        root_record=name, notes=reason,
    )
    return _ok({"name": name, "status": _STATUS_CANNOT_REPAIR, "asset_status": _STATUS_OUT_OF_SERVICE})


@frappe.whitelist()
def close_work_order(name: str, repair_summary: str, root_cause_category: str,
                     dept_head_name: str, checklist_results: str = "[]",
                     spare_parts: str = "[]", firmware_updated: int = 0,
                     firmware_change_request: str = "", cannot_repair: int = 0,
                     cannot_repair_reason: str = ""):
    """Đóng WO sau nghiệm thu (submit) hoặc đánh dấu Cannot Repair."""
    try:
        doc = frappe.get_doc(_DOCTYPE, name)

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

        doc.status = "Pending Inspection"
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        doc.flags.ignore_links = True
        doc.submit()
        return _ok({"name": name, "status": "Completed", "mttr_hours": doc.mttr_hours, "sla_breached": doc.sla_breached})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_repair_kpis(year: int = None, month: int = None):
    """KPIs: MTTR avg, SLA compliance, repeat failure rate, top root causes."""
    try:
        from frappe.utils import getdate
        import datetime
        today = getdate(nowdate())
        y = int(year) if year else today.year
        m = int(month) if month else today.month

        start = f"{y}-{m:02d}-01"
        if m == 12:
            end = f"{y+1}-01-01"
        else:
            end = f"{y}-{m+1:02d}-01"

        completed = frappe.get_all(_DOCTYPE,
            filters={"status": "Completed", "docstatus": 1,
                     "completion_datetime": ("between", [start, end])},
            fields=["name", "mttr_hours", "sla_breached", "is_repeat_failure", "root_cause_category"])

        total = len(completed)
        mttr_avg = round(sum(w.mttr_hours or 0 for w in completed) / total, 2) if total else 0
        sla_met = sum(1 for w in completed if not w.sla_breached)
        sla_compliance = round(sla_met / total * 100, 1) if total else 0
        repeat_failures = sum(1 for w in completed if w.is_repeat_failure)

        root_cause_count: dict = {}
        for w in completed:
            rc = w.root_cause_category or "Unknown"
            root_cause_count[rc] = root_cause_count.get(rc, 0) + 1

        open_wos = frappe.db.count(_DOCTYPE, {"status": ("in", ["Open", "Assigned", "Diagnosing", _STATUS_PENDING_PARTS, _STATUS_IN_REPAIR]), "docstatus": 0})

        return _ok({
            "kpis": {
                "total_completed": total,
                "mttr_avg_hours": mttr_avg,
                "sla_compliance_pct": sla_compliance,
                "repeat_failure_count": repeat_failures,
                "open_wos": open_wos,
            },
            "root_cause_breakdown": [{"category": k, "count": v} for k, v in sorted(root_cause_count.items(), key=lambda x: -x[1])],
        })
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_asset_repair_history(asset_ref: str, limit: int = 10):
    """Lịch sử sửa chữa của 1 thiết bị."""
    try:
        history = frappe.get_all(_DOCTYPE,
            filters={"asset_ref": asset_ref, "docstatus": 1},
            fields=["name", "repair_type", "priority", "open_datetime", "completion_datetime",
                    "mttr_hours", "sla_breached", "root_cause_category", "repair_summary"],
            order_by="open_datetime desc",
            limit=int(limit))
        return _ok({"asset_ref": asset_ref, "history": history})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def create_repair_work_order(
    asset_ref: str,
    repair_type: str,
    priority: str,
    failure_description: str,
    incident_report: str = "",
    source_pm_wo: str = "",
) -> dict:
    """Tạo mới Asset Repair WO. Bắt buộc có incident_report hoặc source_pm_wo (BR-09-01)."""
    try:
        if not incident_report and not source_pm_wo:
            return _err("CM-001: Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc")

        if not frappe.db.exists("Asset", asset_ref):
            return _err(f"Không tìm thấy thiết bị: {asset_ref}", 404)

        # Check duplicate open WO
        open_wo = frappe.db.get_value(_DOCTYPE, {"asset_ref": asset_ref, "status": ["not in", ["Completed", _STATUS_CANNOT_REPAIR, "Cancelled"]]}, "name")
        if open_wo:
            return _err(f"CM-002: Thiết bị đang có phiếu sửa chữa đang mở: {open_wo}")

        from assetcore.services.imm09 import get_sla_target
        risk_class = frappe.db.get_value("Asset", asset_ref, "custom_risk_class") or "Class II"
        sla_hours = get_sla_target(risk_class, priority)

        doc = frappe.get_doc({
            "doctype": _DOCTYPE,
            "asset_ref": asset_ref,
            "repair_type": repair_type,
            "priority": priority,
            "failure_description": failure_description,
            "incident_report": incident_report,
            "source_pm_wo": source_pm_wo,
            "status": "Open",
            "sla_target_hours": sla_hours,
            "risk_class": risk_class,
            "open_datetime": now_datetime(),
        })
        asset_name = frappe.db.get_value("Asset", asset_ref, "asset_name") or ""
        doc.asset_name = asset_name
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)

        frappe.db.set_value("Asset", asset_ref, "status", _STATUS_UNDER_REPAIR)

        from assetcore.services.imm09 import _create_lifecycle_event
        _create_lifecycle_event(
            asset=asset_ref, event_type="repair_opened",
            from_status="Active", to_status=_STATUS_UNDER_REPAIR,
            root_record=doc.name,
        )
        frappe.db.commit()
        return _ok({"name": doc.name, "status": "Open", "sla_target_hours": sla_hours})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def request_spare_parts(name: str, parts: str = "[]"):
    """Kho xác nhận đã xuất vật tư (cập nhật stock_entry_ref)."""
    try:
        parts_list = json.loads(parts) if isinstance(parts, str) else parts
        doc = frappe.get_doc(_DOCTYPE, name)
        updated = 0
        for part in parts_list:
            for row in doc.spare_parts_used:
                if row.item_code == part.get("item_code"):
                    row.stock_entry_ref = part.get("stock_entry_ref")
                    updated += 1
        if doc.status == _STATUS_PENDING_PARTS:
            doc.status = _STATUS_IN_REPAIR
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        return _ok({"name": name, "status": doc.status, "updated": updated})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist(methods=["POST"])
def start_repair(name: str) -> dict:
    """KTV bắt đầu thực hiện sửa chữa → status In Repair."""
    try:
        doc = frappe.get_doc(_DOCTYPE, name)
        if doc.status not in ("Assigned", "Diagnosing", _STATUS_PENDING_PARTS):
            return _err(f"Không thể bắt đầu sửa chữa ở trạng thái {doc.status}")
        doc.status = _STATUS_IN_REPAIR
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        return _ok({"name": name, "status": _STATUS_IN_REPAIR})
    except Exception as e:
        return _err(str(e))


def _month_range(y: int, m: int) -> tuple[str, str]:
    start = f"{y}-{m:02d}-01"
    end = f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"
    return start, end


def _mttr_trend(y: int, m: int) -> list:
    trend = []
    for i in range(5, -1, -1):
        offset = m - 1 - i
        tm = offset % 12 + 1
        ty = y + offset // 12
        start, end = _month_range(ty, tm)
        rows = frappe.get_all(_DOCTYPE,
            filters={"status": "Completed", "docstatus": 1,
                     "completion_datetime": ("between", [start, end])},
            fields=["mttr_hours"])
        avg = round(sum(r.mttr_hours or 0 for r in rows) / len(rows), 2) if rows else 0
        trend.append({"month": start[:7], "value": avg})
    return trend


@frappe.whitelist()
def get_mttr_report(year: int = None, month: int = None) -> dict:
    """MTTR report: trend 6 tháng, first-fix rate, backlog, cost per repair."""
    try:
        from frappe.utils import getdate
        today = getdate(nowdate())
        y = int(year) if year else today.year
        m = int(month) if month else today.month

        start_cur, end_cur = _month_range(y, m)
        completed = frappe.get_all(_DOCTYPE,
            filters={"status": "Completed", "docstatus": 1,
                     "completion_datetime": ("between", [start_cur, end_cur])},
            fields=["mttr_hours", "is_repeat_failure", "total_parts_cost"])

        total = len(completed)
        mttr_avg = round(sum(r.mttr_hours or 0 for r in completed) / total, 2) if total else 0
        first_fix_rate = round(sum(1 for r in completed if not r.is_repeat_failure) / total * 100, 1) if total else 0
        avg_cost = round(sum(r.total_parts_cost or 0 for r in completed) / total, 0) if total else 0

        backlog_count = frappe.db.count(_DOCTYPE, {
            "status": ("in", ["Open", "Assigned", "Diagnosing", _STATUS_PENDING_PARTS, _STATUS_IN_REPAIR]),
            "docstatus": 0,
        })
        backlog_raw = frappe.db.sql("""
            SELECT clinical_dept AS dept, COUNT(*) AS count
            FROM `tabAsset Repair`
            WHERE status NOT IN ('Completed','Cannot Repair','Cancelled') AND docstatus = 0
            GROUP BY clinical_dept
        """, as_dict=True)

        return _ok({
            "mttr_avg": mttr_avg,
            "first_fix_rate": first_fix_rate,
            "backlog_count": backlog_count,
            "cost_per_repair": avg_cost,
            "mttr_trend": _mttr_trend(y, m),
            "backlog_by_dept": [{"dept": r.dept or "—", "count": r.count} for r in backlog_raw],
        })
    except Exception as e:
        return _err(str(e))
