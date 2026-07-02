# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — Tier 1 API Layer.
#
# Notification framework (Sprint 2026-05-29): dùng shared `handle`/`parse_json`
# từ `assetcore.utils.api_handler`. `handle()` tự hydrate envelope notification
# (message_code/severity/title/action_hint) khi service raise nthrow(MSG.*).
# KHÔNG còn `_handle`/`_err` cục bộ làm rớt message_code.

from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from assetcore.services import imm09 as svc
from assetcore.services.shared import ServiceError
from assetcore.services.shared import rbac
from assetcore.services.shared.scope import apply_vendor_scope, assert_vendor_can_access
from assetcore.utils.api_handler import _service_error_to_envelope, handle, parse_json


@frappe.whitelist()
def list_repair_work_orders(filters: str = "{}", mine: int = 0,
                            page: int = 1, page_size: int = 20):
    # parse_json BÊN TRONG try/except (mirror imm08.list_pm_work_orders:30-32) — malformed `filters`
    # → ServiceError(INVALID_PARAMS) chuyển thành Error-trên-HTTP-200 envelope thay vì raise uncaught
    # = HTTP-500 (khớp contract C7 200-oneOf [RepairWorkOrderListEnvelope, Error]).
    # C-LISTREAD-MINE-CM (A2-symmetry CUỐI / ADR-MOBILE-017): tab "Phiếu CM của tôi"
    #   (MyWorkOrdersView, MVP-5b) truyền mine=1 → scope assigned_to == session.user. Inject SAU
    #   apply_vendor_scope (vendor-scope vẫn áp trước). mine=0/absent ⇒ filters byte-identical
    #   baseline (web-FE RepairWorkOrderListView KHÔNG đổi). count==rows giữ: count_with_or +
    #   get_all dùng CÙNG filters dict (đã có assigned_to). Mirror list_pm_work_orders:28-42.
    try:
        f = parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _service_error_to_envelope(e)
    f = apply_vendor_scope(f, "Asset Repair")
    if int(mine or 0):
        f["assigned_to"] = frappe.session.user
    return handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_repair_work_order(name: str):
    def _run():
        assert_vendor_can_access("Asset Repair", name)
        return svc.get_work_order(name)
    return handle(_run)


@frappe.whitelist(methods=["POST"])
def create_repair_work_order(asset_ref: str, repair_type: str, priority: str,
                             failure_description: str, incident_report: str = "",
                             source_pm_wo: str = "", fault_image: str = "") -> dict:
    # AUTH-02 — explicit server-side gate (don't trust FE button hiding).
    rbac.require("repair.create")
    return handle(
        svc.create_work_order,
        asset_ref=asset_ref, repair_type=repair_type, priority=priority,
        failure_description=failure_description,
        incident_report=incident_report, source_pm_wo=source_pm_wo,
        fault_image=fault_image,
    )


@frappe.whitelist(methods=["POST"])
def assign_technician(name: str, technician: str, priority: str = ""):
    rbac.require("repair.write")
    return handle(svc.assign_technician, name, technician=technician, priority=priority)


@frappe.whitelist(methods=["POST"])
def submit_diagnosis(name: str, diagnosis_notes: str, needs_parts: int = 0):
    rbac.require("repair.write")
    return handle(svc.submit_diagnosis, name,
                  diagnosis_notes=diagnosis_notes,
                  needs_parts=int(needs_parts))


@frappe.whitelist(methods=["POST"])
def start_repair(name: str) -> dict:
    rbac.require("repair.write")
    return handle(svc.start_repair, name)


@frappe.whitelist(methods=["POST"])
def request_spare_parts(name: str, parts: str = "[]"):
    rbac.require("repair.write")
    parts_list = parse_json(parts, field_name="parts", default=[])
    return handle(svc.request_spare_parts, name, parts_list)


@frappe.whitelist(methods=["POST"])
def close_work_order(name: str, repair_summary: str, root_cause_category: str,
                     dept_head_name: str, checklist_results: str = "[]",
                     spare_parts: str = "[]", firmware_updated: int = 0,
                     firmware_change_request: str = "", cannot_repair: int = 0,
                     cannot_repair_reason: str = ""):
    rbac.require("repair.submit")
    checklist = parse_json(checklist_results, field_name="checklist_results", default=[])
    parts = parse_json(spare_parts, field_name="spare_parts", default=[])
    return handle(
        svc.close_work_order, name,
        repair_summary=repair_summary, root_cause_category=root_cause_category,
        dept_head_name=dept_head_name, checklist_results=checklist,
        spare_parts=parts, firmware_updated=int(firmware_updated),
        firmware_change_request=firmware_change_request,
        cannot_repair=int(cannot_repair), cannot_repair_reason=cannot_repair_reason,
    )


@frappe.whitelist(methods=["POST"])
def confirm_inspection(name: str) -> dict:
    """Nghiệm thu sau sửa chữa: Pending Inspection → Completed."""
    rbac.require("repair.submit")
    return handle(svc.confirm_inspection, name)


@frappe.whitelist()
def get_repair_kpis(year: str = "", month: str = ""):
    today = getdate(nowdate())
    return handle(svc.get_kpis,
                  int(year) if year else today.year,
                  int(month) if month else today.month)


@frappe.whitelist()
def get_asset_repair_history(asset_ref: str, limit: str = "10"):
    return handle(svc.get_asset_history, asset_ref, limit=int(limit))


@frappe.whitelist()
def search_spare_parts(query: str = "", limit: str = "10") -> dict:
    return handle(svc.search_spare_parts, query, limit=int(limit))


@frappe.whitelist()
def get_mttr_report(year: str = "", month: str = "") -> dict:
    today = getdate(nowdate())
    return handle(svc.get_mttr_report,
                  int(year) if year else today.year,
                  int(month) if month else today.month)
