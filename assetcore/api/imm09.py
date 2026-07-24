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
def list_repair_work_orders(filters: str = "{}", mine: int = 0, search: str = None,
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
    # CR-18: free-text search server-side. Inject `search` vào filters dict SAU
    #   vendor-scope + mine → service pop_search dịch sang OR-LIKE (name/asset_ref/
    #   asset_name) AND các filter khác. CHỈ khi non-empty ⇒ absent/rỗng byte-
    #   identical baseline (web-FE CMWorkOrderListView KHÔNG regress). KHÔNG nới
    #   quyền: search chỉ thêm OR-clause TRONG tập đã scope, KHÔNG bypass.
    if search is not None and str(search).strip():
        f["search"] = str(search)
    return handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_repair_work_order(name: str):
    def _run():
        assert_vendor_can_access("Asset Repair", name)
        return svc.get_work_order(name)
    return handle(_run)


@frappe.whitelist(methods=["POST"])
def attach_repair_checklist_photo(work_order_name: str = "", checklist_item_idx: str = "",
                                 client_request_id: str = "", **_ignore) -> dict:
    """POST (multipart) /api/method/assetcore.api.imm09.attach_repair_checklist_photo

    BR-09-15/16 (mobile CR-15/G6): đính ảnh bằng chứng cho MỘT mục checklist sửa chữa
    (NĐ98 Class C/D) → File private + đúng 1 lifecycle `repair_checklist_photo_attached`.
    Single-step multipart: server đọc `frappe.request.files["file"]`, tự validate + tạo
    + link File (robust, KHÔNG orphan như 2-bước upload→file_url). ĐỐI XỨNG
    attach_pm_checklist_photo (imm08) — KHÁC module/doctype/discriminator (Frappe child
    `idx`).

    `client_request_id` (CR-24 §4 photo-level closure · BR-09-16-IDEMP idempotency): khoá
    per-ảnh do client (mobile write-outbox PHA-2) sinh, ổn định qua re-drain của CÙNG ảnh.
    Non-empty + cùng (wo, idx) gọi lặp ⇒ trả File ĐÃ đính (KHÔNG File/event trùng — dedupe
    composite scoped key `{wo}::{idx}::{key}` trên `File.ac_client_request_id`). Rỗng/thiếu
    ⇒ hành vi at-least-once cũ. Param TƯỜNG MINH (multipart form part — KHÔNG bị `**_ignore`
    nuốt câm); default `""` (KHÔNG None — tránh HTTP-417 coercion).

    `**_ignore` nuốt kwargs spoof KHÁC. Guest/no-token → dispatcher-403 (POST @whitelist
    KHÔNG allow_guest); permission (assignee OR repair.write) + validation ở service →
    Decision-B HTTP-200 qua `handle`. `checklist_item_idx` parse int ở boundary; giá trị
    lỗi/không-tồn-tại → service trả VALIDATION (reject TRƯỚC File.insert).
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
        svc.attach_repair_checklist_photo,
        work_order_name,
        idx,
        filedata=filedata,
        filename=filename,
        content_type=content_type,
        client_request_id=client_request_id,
    )


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
                     cannot_repair_reason: str = "", client_request_id: str = ""):
    # CR-24 op#5/5: `client_request_id` (str='' KHÔNG str|None → tránh HTTP 417
    #   pydantic-coercion) pass-through xuống service cho idempotency dedup mobile
    #   write-outbox re-drain. Optional ⇒ 0 whitelist/tag mới (oas_baseline bất biến).
    # ISS-005: close_work_order = hành động KTV (RACI 'Sửa chữa+checklist' = KTV HTM
    #   R/A) → chuyển 'Pending Inspection', KHÔNG doc.submit (service imm09:1617-1690).
    #   Gate `repair.create` — KHỚP EXACT cả FE (CMWorkOrderDetailView canCompleteRepair
    #   = can('repair.create'), :81/:106) LẪN service (imm09:1637) ⇒ contract 3-lớp
    #   nhất quán. KHÔNG `repair.submit`: đó là gate của confirm_inspection (nghiệm thu
    #   = doc.submit → Completed, Trưởng khoa/QA) — giữ SoD 2-actor. Trước đây API gate
    #   repair.submit (lệch FE+service) ⇒ Repair User (submit=0) bấm 'Hoàn thành sửa
    #   chữa' (nút FE bật vì repair.create) → 403 câm.
    rbac.require("repair.create")
    checklist = parse_json(checklist_results, field_name="checklist_results", default=[])
    parts = parse_json(spare_parts, field_name="spare_parts", default=[])
    return handle(
        svc.close_work_order, name,
        repair_summary=repair_summary, root_cause_category=root_cause_category,
        dept_head_name=dept_head_name, checklist_results=checklist,
        spare_parts=parts, firmware_updated=int(firmware_updated),
        firmware_change_request=firmware_change_request,
        cannot_repair=int(cannot_repair), cannot_repair_reason=cannot_repair_reason,
        client_request_id=client_request_id,
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
