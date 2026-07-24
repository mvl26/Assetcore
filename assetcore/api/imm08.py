# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-08 — Preventive Maintenance.
# Tier 1 — parse HTTP input → gọi services.imm08 → _ok / _err envelope.

from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from assetcore.services import imm08 as svc
from assetcore.services.shared import ServiceError
from assetcore.services.shared import rbac
from assetcore.services.shared.scope import apply_vendor_scope, assert_vendor_can_access
from assetcore.utils.api_handler import _service_error_to_envelope, handle, parse_json


def _form_dict(*strip: str) -> dict:
    """Lấy frappe.local.form_dict loại bỏ các key control."""
    data = dict(frappe.local.form_dict)
    for k in ("cmd", "doctype", *strip):
        data.pop(k, None)
    return data


# ─── PM Work Orders ───────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_work_orders(filters: str = "{}", mine: int = 0, search: str = None,
                        page: int = 1, page_size: int = 20) -> dict:
    # C-LISTREAD-MINE-PM (A2 closure ĐỐI XỨNG / ADR-MOBILE-016): tab "Phiếu PM của tôi"
    #   (MyWorkOrdersView, MVP-5a) truyền mine=1 → scope assigned_to == session.user. Inject
    #   SAU apply_vendor_scope (vendor-scope vẫn áp trước). mine=0/absent ⇒ filters
    #   byte-identical baseline (web-FE PMWorkOrderListView KHÔNG đổi). count==rows giữ:
    #   count_with_or + get_all dùng CÙNG filters dict (đã có assigned_to). Mirror IncidentMine.
    try:
        f = parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _service_error_to_envelope(e)
    f = apply_vendor_scope(f, "PM Work Order")
    if int(mine or 0):
        f["assigned_to"] = frappe.session.user
    # CR-18: free-text search server-side. Inject `search` vào filters dict SAU
    #   vendor-scope + mine → service pop_search dịch sang OR-LIKE (name/asset_ref/
    #   asset_name) AND các filter khác. CHỈ khi non-empty ⇒ absent/rỗng byte-
    #   identical baseline (web-FE PMWorkOrderListView KHÔNG regress). KHÔNG nới
    #   quyền: search chỉ thêm OR-clause TRONG tập đã scope, KHÔNG bypass.
    if search is not None and str(search).strip():
        f["search"] = str(search)
    return handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_work_order(name: str) -> dict:
    try:
        assert_vendor_can_access("PM Work Order", name)
    except ServiceError as e:
        return _service_error_to_envelope(e)
    return handle(svc.get_work_order, name)


@frappe.whitelist(methods=["POST"])
def attach_pm_checklist_photo(work_order_name: str = "", checklist_item_idx: str = "",
                             client_request_id: str = "", **_ignore) -> dict:
    """POST (multipart) /api/method/assetcore.api.imm08.attach_pm_checklist_photo

    BR-08-14 (mobile CR-14/G6): đính ảnh bằng chứng cho MỘT mục checklist PM (NĐ98
    Class C/D) → File private + đúng 1 lifecycle `pm_checklist_photo_attached`.
    Single-step multipart: server đọc `frappe.request.files["file"]`, tự validate +
    tạo + link File (robust, KHÔNG orphan như 2-bước upload→file_url). ĐỐI XỨNG
    attach_incident_photo (imm12) — KHÁC module/doctype/field.

    `client_request_id` (CR-24 §4 photo-level closure · BR-08-14-IDEMP idempotency): khoá
    per-ảnh do client (mobile write-outbox PHA-2) sinh, ổn định qua mọi re-drain của CÙNG
    ảnh. Non-empty + cùng (wo, idx) gọi lặp ⇒ trả File ĐÃ đính (KHÔNG File/event trùng —
    dedupe composite scoped key `{wo}::{idx}::{key}` trên `File.ac_client_request_id`).
    Rỗng/thiếu ⇒ hành vi at-least-once cũ. Param TƯỜNG MINH (multipart form part — KHÔNG bị
    `**_ignore` nuốt câm); default `""` (KHÔNG None — tránh HTTP-417 coercion).

    `**_ignore` nuốt kwargs spoof KHÁC. Guest/no-session → dispatcher-403 (POST @whitelist
    không allow_guest); permission (assignee OR pm.write) + validation ở service →
    Decision-B HTTP-200 qua `handle`. `checklist_item_idx` parse int ở boundary; giá
    trị lỗi/không-tồn-tại → service trả VALIDATION (reject TRƯỚC File.insert).
    """
    files = frappe.request.files if getattr(frappe, "request", None) else None
    upload = files.get("file") if files else None
    # File present check nằm ở service (sau permission/idx — thứ tự spec): filedata=None
    # khi thiếu file → service raise VALIDATION 'Thiếu tệp ảnh'.
    if upload is not None:
        filedata = upload.stream.read()
        filename = upload.filename or ""
        content_type = upload.content_type or ""
    else:
        filedata, filename, content_type = None, "", ""
    try:
        idx = int(checklist_item_idx)
    except (TypeError, ValueError):
        idx = -1  # sentinel không khớp row nào → service VALIDATION idx-not-found (đúng thứ tự)
    return handle(
        svc.attach_pm_checklist_photo,
        work_order_name,
        idx,
        filedata=filedata,
        filename=filename,
        content_type=content_type,
        client_request_id=client_request_id,
    )


@frappe.whitelist(methods=["POST"])
def assign_technician(name: str, technician: str, scheduled_date: str = None) -> dict:
    # AUTH-02 — block FE-bypass: only PM writers can re-assign.
    # VERB-FLIP (R35 PM-dispatch / ADR-MOBILE-012): write-action DISPATCH (Open/Overdue→In
    # Progress + asset→Under Maintenance, KHÔNG idempotent) ⇒ POST-only (sibling add_measurement).
    rbac.require("pm.write")
    return handle(svc.assign_technician, name,
                   technician=technician, scheduled_date=scheduled_date)


@frappe.whitelist(methods=["POST"])
def submit_pm_result(name: str, checklist_results: str = "[]",
                      overall_result: str = "Pass", technician_notes: str = "",
                      pm_sticker_attached: int = 0, duration_minutes: int = 0,
                      client_request_id: str = "") -> dict:
    # CR-24-PM: `client_request_id` = khoá idempotency do client (mobile write-outbox)
    #   sinh — optional default str="" (NULL-semantics: rỗng ⇒ 0 dedup, legacy y nguyên;
    #   KHÔNG None → tránh 417 khi form gửi rỗng). Anti-spoof: KHÔNG nhận `user`.
    #   Nguồn khoá (HANDOFF §2.1 header-parity, parity imm09/imm00/imm11): body param
    #   THẮNG header X-Idempotency-Key / alias Idempotency-Key; cả hai vắng ⇒ NO-OP dedup.
    rbac.require("pm.submit")
    try:
        results = parse_json(checklist_results, field_name="checklist_results", default=[])
    except ServiceError as e:
        return _service_error_to_envelope(e)
    return handle(
        svc.submit_result, name,
        checklist_results=results, overall_result=overall_result,
        technician_notes=technician_notes,
        pm_sticker_attached=int(pm_sticker_attached),
        duration_minutes=int(duration_minutes),
        client_request_id=str(client_request_id or ""),
    )


@frappe.whitelist(methods=["POST"])
def report_major_failure(pm_wo_name: str, failure_description: str) -> dict:
    # VERB-FLIP (R36 PM→CM escalation / ADR-MOBILE-013): write KHÔNG idempotent — mỗi call tạo 1 CM WO khẩn +
    # đặt asset Out of Service + Incident IMM-12 + email ⇒ POST-only (sibling assign_technician/add_measurement).
    # SIGNATURE-FIX: DROP failed_item_indexes — service report_major_failure(pm_wo_name, *, failure_description)
    # services/imm08.py:744 KHÔNG nhận field này; handler cũ parse + pass-through `failed_item_indexes=` ⇒
    # TypeError → HTTP-500 mỗi call. Align handler↔service signature (service+CoreDoc§200+web-FE đều bỏ qua).
    rbac.require("pm.write")
    return handle(svc.report_major_failure, pm_wo_name,
                   failure_description=failure_description)


@frappe.whitelist(methods=["POST"])
def reschedule_pm(name: str, new_date: str, reason: str) -> dict:
    rbac.require("pm.reschedule")
    return handle(svc.reschedule, name, new_date=new_date, reason=reason)


@frappe.whitelist(methods=["POST"])
def create_pm_work_order() -> dict:
    rbac.require("pm.create")
    return handle(svc.create_adhoc_work_order, _form_dict())


# ─── PM Calendar & Dashboard ─────────────────────────────────────────────────

@frappe.whitelist()
def get_pm_calendar(year: int, month: int, asset_ref: str = None,
                     technician: str = None) -> dict:
    return handle(svc.get_calendar,
                   year=int(year), month=int(month),
                   asset_ref=asset_ref, technician=technician)


@frappe.whitelist()
def get_pm_dashboard_stats(year: int = None, month: int = None) -> dict:
    today = getdate(nowdate())
    return handle(svc.get_dashboard_stats,
                   year=int(year) if year else today.year,
                   month=int(month) if month else today.month)


@frappe.whitelist()
def get_asset_pm_history(asset_ref: str, limit: int = 10) -> dict:
    return handle(svc.get_asset_history, asset_ref, limit=int(limit))


# ─── PM Schedules ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_schedules(asset_ref: str = None, status: str = None,
                       page: int = 1, page_size: int = 20) -> dict:
    return handle(svc.list_schedules,
                   asset_ref=asset_ref, status=status,
                   page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_schedule(name: str) -> dict:
    return handle(svc.get_schedule, name)


@frappe.whitelist()
def get_due_pm_schedules(days: int = 30, limit: int = 50) -> dict:
    # F8 "Nhắc việc" (mobile CR-28b) — PM sắp/quá hạn. ĐỐI XỨNG get_due_calibrations
    #   (api/imm11.py:202): bare @whitelist → GET, DocPerm-governed (KHÔNG cap-gate).
    return handle(svc.get_due_pm_schedules, int(days), int(limit))


@frappe.whitelist(methods=["POST"])
def create_pm_schedule() -> dict:
    rbac.require("pm.create")
    return handle(svc.create_schedule, _form_dict())


@frappe.whitelist(methods=["POST"])
def update_pm_schedule(name: str) -> dict:
    rbac.require("pm.write")
    return handle(svc.update_schedule, name, _form_dict("name"))


@frappe.whitelist(methods=["POST"])
def set_pm_schedule_status(name: str, status: str) -> dict:
    rbac.require("pm.write")
    return handle(svc.set_schedule_status, name, status)


@frappe.whitelist(methods=["POST"])
def delete_pm_schedule(name: str) -> dict:
    rbac.require("pm.delete")
    return handle(svc.delete_schedule, name)


# ─── PM Checklist Templates ──────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_templates(asset_category: str = None, pm_type: str = None,
                       page: int = 1, page_size: int = 20) -> dict:
    return handle(svc.list_templates,
                   asset_category=asset_category, pm_type=pm_type,
                   page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_template(name: str) -> dict:
    return handle(svc.get_template, name)


@frappe.whitelist(methods=["POST"])
def create_pm_template() -> dict:
    rbac.require("pm.create")
    data = _form_dict()
    items_raw = data.get("checklist_items")
    if items_raw is not None:
        try:
            data["checklist_items"] = parse_json(items_raw, field_name="checklist_items", default=[])
        except ServiceError as e:
            return _service_error_to_envelope(e)
    return handle(svc.create_template, data)


@frappe.whitelist(methods=["POST"])
def update_pm_template(name: str) -> dict:
    rbac.require("pm.write")
    data = _form_dict("name")
    if "checklist_items" in data:
        try:
            data["checklist_items"] = parse_json(data["checklist_items"],
                                                   field_name="checklist_items", default=[])
        except ServiceError as e:
            return _service_error_to_envelope(e)
    return handle(svc.update_template, name, data)


@frappe.whitelist(methods=["POST"])
def approve_pm_template(name: str) -> dict:
    rbac.require("pm.submit")
    return handle(svc.approve_template, name)


@frappe.whitelist(methods=["POST"])
def version_pm_template(source_name: str, new_version: str) -> dict:
    rbac.require("pm.write")
    return handle(svc.version_template, source_name, new_version)


@frappe.whitelist(methods=["POST"])
def delete_pm_template(name: str) -> dict:
    rbac.require("pm.delete")
    return handle(svc.delete_template, name)


@frappe.whitelist(methods=["POST"])
def apply_pm_template_to_category(template_name: str) -> dict:
    """Bulk-tạo PM Schedule cho mọi asset cùng danh mục với template."""
    rbac.require("pm.create")
    return handle(svc.apply_template_to_category_assets, template_name)
