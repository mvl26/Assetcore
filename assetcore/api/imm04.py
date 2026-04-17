# Copyright (c) 2026, AssetCore Team and contributors
# REST API cho Module IMM-04 — Asset Commissioning (Decoupled Frontend)

import frappe
from frappe import _
from frappe.utils import get_first_day, nowdate, add_days, now_datetime


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ok(data: dict | list) -> dict:
    """Chuẩn trả về thành công."""
    return {"success": True, "data": data}


def _err(message: str, code: str = "GENERIC_ERROR") -> dict:
    """Chuẩn trả về lỗi."""
    return {"success": False, "error": message, "code": code}


def _get_workflow_transitions(doc_name: str, workflow_name: str = "IMM-04 Workflow") -> list[dict]:
    """
    Lấy danh sách transition được phép cho user hiện tại dựa trên state hiện tại.

    Returns:
        List of {action, next_state, allowed_role}
    """
    user_roles = frappe.get_roles(frappe.session.user)
    current_state = frappe.db.get_value("Asset Commissioning", doc_name, "workflow_state")

    try:
        workflow = frappe.get_doc("Workflow", workflow_name)
    except frappe.DoesNotExistError:
        return []

    allowed: list[dict] = []
    for trans in workflow.transitions:
        if trans.state != current_state:
            continue
        if trans.allowed in user_roles:
            allowed.append({
                "action": trans.action,
                "next_state": trans.next_state,
                "allowed_role": trans.allowed,
            })

    return allowed


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET FORM CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_form_context(name: str) -> dict:
    """
    Trả về document đầy đủ + workflow state + allowed transitions cho role hiện tại.

    Endpoint: GET /api/method/assetcore.api.imm04.get_form_context?name=IMM04-26-04-00001
    """
    if not name:
        return _err("Thiếu tham số name", "MISSING_PARAM")

    if not frappe.db.exists("Asset Commissioning", name):
        return _err(f"Không tìm thấy phiếu '{name}'", "NOT_FOUND")

    try:
        frappe.has_permission("Asset Commissioning", ptype="read", doc=name, throw=True)
    except frappe.PermissionError:
        return _err("Bạn không có quyền xem phiếu này", "PERMISSION_DENIED")

    doc = frappe.get_doc("Asset Commissioning", name)
    doc_dict = doc.as_dict()

    # Serialize child tables
    baseline_tests = [
        {
            "idx": row.idx,
            "parameter": row.parameter,
            "measured_val": row.measured_val,
            "unit": row.unit,
            "test_result": row.test_result,
            "fail_note": row.fail_note,
            "is_critical": row.get("is_critical") or 0,
            "measurement_type": row.get("measurement_type") or "",
            "expected_min": row.get("expected_min"),
            "expected_max": row.get("expected_max"),
            "na_applicable": row.get("na_applicable") or 0,
        }
        for row in doc.baseline_tests
    ]

    commissioning_documents = [
        {
            "idx": row.idx,
            "doc_type": row.doc_type,
            "status": row.status,
            "received_date": str(row.received_date or ""),
            "remarks": row.remarks or "",
            "is_mandatory": row.get("is_mandatory") or 0,
            "file_url": row.get("file_url") or "",
            "doc_number": row.get("doc_number") or "",
            "expiry_date": str(row.get("expiry_date") or ""),
        }
        for row in doc.commissioning_documents
    ]

    lifecycle_events = [
        {
            "idx": row.idx,
            "event_type": row.get("event_type") or "",
            "from_status": row.get("from_status") or "",
            "to_status": row.get("to_status") or "",
            "actor": row.get("actor") or "",
            "event_timestamp": str(row.get("event_timestamp") or ""),
            "ip_address": row.get("ip_address") or "",
            "remarks": row.get("remarks") or "",
        }
        for row in (doc.get("lifecycle_events") or [])
    ]

    allowed_transitions = _get_workflow_transitions(name)

    return _ok({
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
        "po_reference": doc.po_reference,
        "master_item": doc.master_item,
        "vendor": doc.vendor,
        "clinical_dept": doc.clinical_dept,
        "expected_installation_date": str(doc.expected_installation_date or ""),
        "installation_date": str(doc.installation_date or ""),
        "reception_date": str(doc.get("reception_date") or ""),
        "risk_class": doc.get("risk_class") or "",
        "board_approver": doc.get("board_approver") or "",
        "clinical_head": doc.get("clinical_head") or "",
        "qa_officer": doc.get("qa_officer") or "",
        "facility_checklist_pass": doc.get("facility_checklist_pass") or 0,
        "overall_inspection_result": doc.get("overall_inspection_result") or "",
        "handover_doc": doc.get("handover_doc") or "",
        "commissioned_by": doc.get("commissioned_by") or "",
        "commissioning_date": str(doc.get("commissioning_date") or ""),
        "vendor_engineer_name": doc.vendor_engineer_name,
        "is_radiation_device": doc.is_radiation_device,
        "doa_incident": doc.doa_incident,
        "vendor_serial_no": doc.vendor_serial_no,
        "internal_tag_qr": doc.internal_tag_qr,
        "custom_moh_code": doc.custom_moh_code,
        "site_photo": doc.site_photo,
        "installation_evidence": doc.installation_evidence,
        "qa_license_doc": doc.qa_license_doc,
        "final_asset": doc.final_asset,
        "amend_reason": doc.amend_reason,
        "amended_from": doc.amended_from,
        "modified": str(doc.modified),
        "owner": doc.owner,
        "baseline_tests": baseline_tests,
        "commissioning_documents": commissioning_documents,
        "lifecycle_events": lifecycle_events,
        "allowed_transitions": allowed_transitions,
        "is_locked": doc.docstatus == 1,
        "current_user_roles": frappe.get_roles(frappe.session.user),
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIST COMMISSIONING
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_commissioning(
    filters: str | dict | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Paginated list với filters.

    Endpoint: GET /api/method/assetcore.api.imm04.list_commissioning
    Params:
        filters: JSON string hoặc dict, e.g. {"workflow_state": "Installing"}
        page: trang hiện tại (bắt đầu từ 1)
        page_size: số record mỗi trang (max 100)
    """
    import json

    try:
        frappe.has_permission("Asset Commissioning", ptype="read", throw=True)
    except frappe.PermissionError:
        return _err("Không có quyền truy cập", "PERMISSION_DENIED")

    # Parse filters
    parsed_filters: dict = {}
    if filters:
        if isinstance(filters, str):
            try:
                parsed_filters = json.loads(filters)
            except (ValueError, TypeError):
                return _err("filters không hợp lệ — phải là JSON string", "INVALID_PARAM")
        elif isinstance(filters, dict):
            parsed_filters = filters

    # Sanitize pagination
    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)
    start = (page - 1) * page_size

    # Allowed filter keys (whitelist để tránh SQL injection qua field name)
    ALLOWED_FILTER_KEYS = {
        "workflow_state", "po_reference", "master_item", "vendor",
        "clinical_dept", "docstatus", "is_radiation_device",
        "doa_incident", "vendor_serial_no", "internal_tag_qr",
        "expected_installation_date", "final_asset",
    }
    safe_filters: dict = {k: v for k, v in parsed_filters.items() if k in ALLOWED_FILTER_KEYS}

    # Không lấy cancelled docs theo mặc định
    if "docstatus" not in safe_filters:
        safe_filters["docstatus"] = ("!=", 2)

    fields = [
        "name", "workflow_state", "docstatus",
        "po_reference", "master_item", "vendor",
        "clinical_dept", "expected_installation_date",
        "installation_date", "vendor_serial_no",
        "internal_tag_qr", "final_asset", "modified",
    ]

    records = frappe.get_all(
        "Asset Commissioning",
        filters=safe_filters,
        fields=fields,
        order_by="modified desc",
        limit_start=start,
        limit_page_length=page_size,
    )

    total = frappe.db.count("Asset Commissioning", safe_filters)

    return _ok({
        "items": records,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# 3. TRANSITION STATE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def transition_state(name: str, action: str) -> dict:
    """
    Thực hiện workflow transition — validate permission trước khi apply.

    Endpoint: POST /api/method/assetcore.api.imm04.transition_state
    Body: {name, action}
    """
    if not name or not action:
        return _err("Thiếu tham số name hoặc action", "MISSING_PARAM")

    if not frappe.db.exists("Asset Commissioning", name):
        return _err(f"Không tìm thấy phiếu '{name}'", "NOT_FOUND")

    try:
        frappe.has_permission("Asset Commissioning", ptype="write", doc=name, throw=True)
    except frappe.PermissionError:
        return _err("Bạn không có quyền chỉnh sửa phiếu này", "PERMISSION_DENIED")

    # Kiểm tra action có nằm trong allowed transitions không
    allowed = _get_workflow_transitions(name)
    allowed_actions = [t["action"] for t in allowed]

    if action not in allowed_actions:
        current_state = frappe.db.get_value("Asset Commissioning", name, "workflow_state")
        return _err(
            f"Hành động '{action}' không hợp lệ từ trạng thái '{current_state}' "
            f"với vai trò của bạn. Hành động cho phép: {allowed_actions}",
            "TRANSITION_NOT_ALLOWED",
        )

    try:
        doc = frappe.get_doc("Asset Commissioning", name)
        # Apply workflow action thông qua Frappe workflow engine
        frappe.model.workflow.apply_workflow(doc, action)
        doc.save(ignore_permissions=False)

        return _ok({
            "name": name,
            "action_applied": action,
            "new_state": doc.workflow_state,
            "docstatus": doc.docstatus,
            "message": f"Chuyển trạng thái thành công: {action} → {doc.workflow_state}",
        })

    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-04 Transition Failed — {name}")
        return _err(f"Lỗi hệ thống: {str(e)}", "SYSTEM_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 4. GENERATE QR LABEL
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def generate_qr_label(name: str) -> dict:
    """
    Trả về dữ liệu QR để frontend render (không sinh ảnh server-side).

    Endpoint: GET /api/method/assetcore.api.imm04.generate_qr_label?name=IMM04-...
    """
    if not name:
        return _err("Thiếu tham số name", "MISSING_PARAM")

    if not frappe.db.exists("Asset Commissioning", name):
        return _err(f"Không tìm thấy phiếu '{name}'", "NOT_FOUND")

    try:
        frappe.has_permission("Asset Commissioning", ptype="read", doc=name, throw=True)
    except frappe.PermissionError:
        return _err("Không có quyền truy cập", "PERMISSION_DENIED")

    doc = frappe.get_doc("Asset Commissioning", name)

    if not doc.internal_tag_qr:
        return _err(
            "Phiếu chưa có mã QR nội bộ. Thiết bị cần ở trạng thái Identification trở lên.",
            "QR_NOT_GENERATED",
        )

    # Dữ liệu để frontend render QR + in nhãn
    return _ok({
        "qr_value": doc.internal_tag_qr,
        "label": {
            "title": "ASSETCORE — NHÃN THIẾT BỊ",
            "commissioning_id": doc.name,
            "internal_qr": doc.internal_tag_qr,
            "vendor_serial": doc.vendor_serial_no or "N/A",
            "model": doc.master_item or "N/A",
            "vendor": doc.vendor or "N/A",
            "dept": doc.clinical_dept or "N/A",
            "moh_code": doc.custom_moh_code or "N/A",
            "installation_date": str(doc.installation_date or "Chưa lắp đặt"),
            "status": doc.workflow_state,
            "asset_id": doc.final_asset or "Chưa có",
            "print_date": str(nowdate()),
        },
        "scan_url": f"/app/asset-commissioning/{doc.name}",
        # IMM-05 deep-link: quét QR dẫn thẳng tới danh sách hồ sơ của asset
        "docs_url": f"/documents/asset/{doc.final_asset}" if doc.final_asset else None,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 5. SUBMIT COMMISSIONING
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_commissioning(name: str) -> dict:
    """
    Submit phiếu commissioning — chỉ VP Block2 hoặc Workshop Head.

    Endpoint: POST /api/method/assetcore.api.imm04.submit_commissioning
    Body: {name}
    """
    if not name:
        return _err("Thiếu tham số name", "MISSING_PARAM")

    if not frappe.db.exists("Asset Commissioning", name):
        return _err(f"Không tìm thấy phiếu '{name}'", "NOT_FOUND")

    # Chỉ role được submit
    SUBMIT_ROLES = {"VP Block2", "Workshop Head"}
    user_roles = set(frappe.get_roles(frappe.session.user))

    if not SUBMIT_ROLES.intersection(user_roles):
        return _err(
            "Chỉ VP Block2 hoặc Workshop Head mới được phép Submit phiếu.",
            "PERMISSION_DENIED",
        )

    doc = frappe.get_doc("Asset Commissioning", name)

    if doc.docstatus == 1:
        return _err("Phiếu đã được Submit trước đó.", "ALREADY_SUBMITTED")

    if doc.docstatus == 2:
        return _err("Phiếu đã bị Cancel, không thể Submit.", "DOC_CANCELLED")

    if doc.workflow_state != "Clinical_Release":
        return _err(
            f"Phiếu phải ở trạng thái 'Clinical_Release' trước khi Submit. "
            f"Trạng thái hiện tại: {doc.workflow_state}",
            "WRONG_STATE",
        )

    try:
        doc.submit()
        return _ok({
            "name": name,
            "docstatus": 1,
            "final_asset": doc.final_asset,
            "message": f"Phiếu {name} đã được Submit thành công. Tài sản {doc.final_asset} đã được tạo.",
        })

    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-04 Submit Failed — {name}")
        return _err(f"Lỗi hệ thống khi Submit: {str(e)}", "SYSTEM_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET BARCODE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_barcode_lookup(barcode: str) -> dict:
    """
    Tìm thiết bị theo barcode/QR — hỗ trợ cả internal_tag_qr và vendor_serial_no.

    Endpoint: GET /api/method/assetcore.api.imm04.get_barcode_lookup?barcode=BV-ICU-2026-0001
    """
    if not barcode:
        return _err("Thiếu tham số barcode", "MISSING_PARAM")

    barcode = barcode.strip()

    DOCTYPE = "Asset Commissioning"
    FIELDS = [
        "name", "workflow_state", "docstatus",
        "master_item", "vendor", "clinical_dept",
        "installation_date", "final_asset",
        "vendor_serial_no", "internal_tag_qr",
        "is_radiation_device", "doa_incident",
    ]

    # Ưu tiên tìm theo internal QR trước
    record = frappe.db.get_value(DOCTYPE, {"internal_tag_qr": barcode}, FIELDS, as_dict=True)

    if not record:
        record = frappe.db.get_value(DOCTYPE, {"vendor_serial_no": barcode}, FIELDS, as_dict=True)

    if not record:
        return _err(
            f"Không tìm thấy thiết bị với mã '{barcode}' trong hệ thống.",
            "NOT_FOUND",
        )

    # Lấy baseline test summary
    doc = frappe.get_doc(DOCTYPE, record.name)
    baseline_summary = [
        {
            "parameter": row.parameter,
            "measured_val": row.measured_val,
            "unit": row.unit,
            "test_result": row.test_result,
        }
        for row in doc.baseline_tests
    ]

    return _ok({
        "commissioning_id": record.name,
        "workflow_state": record.workflow_state,
        "docstatus": record.docstatus,
        "is_released": record.workflow_state == "Clinical_Release",
        "device": {
            "model": record.master_item,
            "vendor": record.vendor,
            "dept": record.clinical_dept,
            "installation_date": str(record.installation_date or ""),
            "vendor_serial": record.vendor_serial_no,
            "internal_qr": record.internal_tag_qr,
            "is_radiation": bool(record.is_radiation_device),
            "doa_incident": bool(record.doa_incident),
        },
        "asset_id": record.final_asset,
        "baseline_tests": baseline_summary,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET DASHBOARD STATS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """
    KPIs cho Dashboard IMM-04.

    Endpoint: GET /api/method/assetcore.api.imm04.get_dashboard_stats
    Returns:
        pending_count, hold_count, open_nc_count, released_this_month,
        overdue_sla, states_breakdown, recent_list
    """
    try:
        frappe.has_permission("Asset Commissioning", ptype="read", throw=True)
    except frappe.PermissionError:
        return _err("Không có quyền truy cập Dashboard", "PERMISSION_DENIED")

    DOCTYPE = "Asset Commissioning"
    TERMINAL_STATES = {"Clinical_Release", "Return_To_Vendor"}

    # Đếm theo state
    states_count = frappe.db.sql(
        """
        SELECT workflow_state, COUNT(*) AS count
        FROM `tabAsset Commissioning`
        WHERE docstatus != 2
        GROUP BY workflow_state
        ORDER BY count DESC
        """,
        as_dict=True,
    )

    state_map = {s.workflow_state: s.count for s in states_count}
    pending_count = sum(v for k, v in state_map.items() if k not in TERMINAL_STATES)
    hold_count = state_map.get("Clinical_Hold", 0)

    # NC chưa xử lý
    open_nc_count = frappe.db.count(
        "Asset QA Non Conformance",
        {"resolution_status": "Open", "docstatus": ("!=", 2)},
    )

    # Phát hành trong tháng này
    first_day = get_first_day(nowdate())
    released_this_month = frappe.db.count(
        DOCTYPE,
        {
            "workflow_state": "Clinical_Release",
            "docstatus": 1,
            "modified": (">=", str(first_day)),
        },
    )

    # Quá hạn SLA (30 ngày)
    overdue_cutoff = add_days(nowdate(), -30)
    overdue_sla = frappe.db.count(
        DOCTYPE,
        {
            "expected_installation_date": ("<", str(overdue_cutoff)),
            "workflow_state": ("not in", list(TERMINAL_STATES)),
            "docstatus": ("!=", 2),
        },
    )

    # 10 phiếu gần nhất
    recent_list = frappe.get_all(
        DOCTYPE,
        filters={"docstatus": ("!=", 2)},
        fields=[
            "name", "workflow_state", "master_item",
            "vendor", "clinical_dept", "expected_installation_date", "modified",
        ],
        order_by="modified desc",
        limit_page_length=10,
    )

    return _ok({
        "kpis": {
            "pending_count": pending_count,
            "hold_count": hold_count,
            "open_nc_count": open_nc_count,
            "released_this_month": released_this_month,
            "overdue_sla": overdue_sla,
        },
        "states_breakdown": states_count,
        "recent_list": recent_list,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 8. SAVE COMMISSIONING (Inline edit)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def save_commissioning(name: str, fields: str | dict | None = None) -> dict:
    """
    Lưu thay đổi inline trên phiếu Commissioning.

    Endpoint: POST /api/method/assetcore.api.imm04.save_commissioning
    Body: {name, fields: {field_name: value, baseline_tests: [...], commissioning_documents: [...]}}
    """
    import json

    if not name:
        return _err("Thiếu tham số name", "MISSING_PARAM")

    if not frappe.db.exists("Asset Commissioning", name):
        return _err(f"Không tìm thấy phiếu '{name}'", "NOT_FOUND")

    try:
        frappe.has_permission("Asset Commissioning", ptype="write", doc=name, throw=True)
    except frappe.PermissionError:
        return _err("Bạn không có quyền chỉnh sửa phiếu này", "PERMISSION_DENIED")

    doc = frappe.get_doc("Asset Commissioning", name)

    if doc.docstatus == 1:
        return _err("Phiếu đã Submit, không thể chỉnh sửa", "DOC_LOCKED")

    # Parse fields
    parsed_fields: dict = {}
    if fields:
        if isinstance(fields, str):
            try:
                parsed_fields = json.loads(fields)
            except (ValueError, TypeError):
                return _err("fields không hợp lệ — phải là JSON", "INVALID_PARAM")
        elif isinstance(fields, dict):
            parsed_fields = fields

    # Whitelist of editable top-level fields
    EDITABLE_FIELDS = {
        "vendor_engineer_name", "qa_license_doc", "site_photo",
        "installation_evidence", "custom_moh_code",
        "risk_class", "reception_date", "clinical_head", "qa_officer",
        "board_approver", "facility_checklist_pass", "overall_inspection_result",
        "handover_doc", "radiation_license_no", "notes",
    }

    try:
        # Update top-level fields
        for key, value in parsed_fields.items():
            if key in EDITABLE_FIELDS:
                doc.set(key, value)

        # Update baseline_tests child table
        if "baseline_tests" in parsed_fields and isinstance(parsed_fields["baseline_tests"], list):
            for update_row in parsed_fields["baseline_tests"]:
                idx = update_row.get("idx")
                if idx is None:
                    continue
                for existing_row in doc.baseline_tests:
                    if existing_row.idx == idx:
                        if "measured_val" in update_row:
                            existing_row.measured_val = update_row["measured_val"]
                        if "test_result" in update_row:
                            existing_row.test_result = update_row["test_result"]
                        if "fail_note" in update_row:
                            existing_row.fail_note = update_row["fail_note"]
                        break

        # Update commissioning_documents child table
        if "commissioning_documents" in parsed_fields and isinstance(parsed_fields["commissioning_documents"], list):
            for update_row in parsed_fields["commissioning_documents"]:
                idx = update_row.get("idx")
                if idx is None:
                    continue
                for existing_row in doc.commissioning_documents:
                    if existing_row.idx == idx:
                        if "status" in update_row:
                            existing_row.status = update_row["status"]
                        if "received_date" in update_row:
                            existing_row.received_date = update_row["received_date"] or None
                        if "remarks" in update_row:
                            existing_row.remarks = update_row["remarks"]
                        break

        doc.save(ignore_permissions=False)

        return _ok({
            "name": doc.name,
            "workflow_state": doc.workflow_state,
            "message": "Đã lưu thành công",
        })

    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-04 Save Failed — {name}")
        return _err(f"Lỗi hệ thống: {str(e)}", "SYSTEM_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 9. CREATE COMMISSIONING
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_commissioning(data: str | dict | None = None) -> dict:
    """
    Tạo phiếu Commissioning mới.

    Endpoint: POST /api/method/assetcore.api.imm04.create_commissioning
    Body: {data: {po_reference, master_item, vendor, clinical_dept, ...}}
    """
    import json

    try:
        frappe.has_permission("Asset Commissioning", ptype="create", throw=True)
    except frappe.PermissionError:
        return _err("Bạn không có quyền tạo phiếu mới", "PERMISSION_DENIED")

    # Parse data
    parsed_data: dict = {}
    if data:
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except (ValueError, TypeError):
                return _err("data không hợp lệ — phải là JSON", "INVALID_PARAM")
        elif isinstance(data, dict):
            parsed_data = data

    # Required fields (vendor_serial_no is set at Identification step, not at creation)
    REQUIRED = ["po_reference", "master_item", "vendor", "clinical_dept",
                "expected_installation_date"]
    missing = [f for f in REQUIRED if not parsed_data.get(f)]
    if missing:
        return _err(f"Thiếu trường bắt buộc: {', '.join(missing)}", "MISSING_FIELDS")

    try:
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "po_reference": parsed_data["po_reference"],
            "master_item": parsed_data["master_item"],
            "vendor": parsed_data["vendor"],
            "clinical_dept": parsed_data["clinical_dept"],
            "expected_installation_date": parsed_data["expected_installation_date"],
            "vendor_serial_no": parsed_data.get("vendor_serial_no", ""),
            "vendor_engineer_name": parsed_data.get("vendor_engineer_name", ""),
            "is_radiation_device": parsed_data.get("is_radiation_device", 0),
            "reception_date": parsed_data.get("reception_date") or None,
            "risk_class": parsed_data.get("risk_class", ""),
            "commissioned_by": parsed_data.get("commissioned_by", ""),
            "doa_incident": parsed_data.get("doa_incident", 0),
        })

        # Add commissioning_documents nếu có
        docs_data = parsed_data.get("commissioning_documents", [])
        for doc_row in docs_data:
            doc.append("commissioning_documents", {
                "doc_type": doc_row.get("doc_type", ""),
                "is_mandatory": doc_row.get("is_mandatory", 0),
                "status": doc_row.get("status", "Pending"),
                "received_date": doc_row.get("received_date") or None,
                "remarks": doc_row.get("remarks", ""),
            })

        # Add baseline_tests nếu có
        tests_data = parsed_data.get("baseline_tests", [])
        for test_row in tests_data:
            doc.append("baseline_tests", {
                "parameter": test_row.get("parameter", ""),
                "is_critical": test_row.get("is_critical", 0),
                "measurement_type": test_row.get("measurement_type", ""),
                "measured_val": test_row.get("measured_val", ""),
                "expected_min": test_row.get("expected_min"),
                "expected_max": test_row.get("expected_max"),
                "unit": test_row.get("unit", ""),
                "test_result": test_row.get("test_result", "N/A"),
                "na_applicable": test_row.get("na_applicable", 0),
                "fail_note": test_row.get("fail_note", ""),
            })

        doc.insert(ignore_permissions=False)

        return _ok({
            "name": doc.name,
            "workflow_state": doc.workflow_state,
            "message": f"Phiếu {doc.name} đã được tạo thành công",
        })

    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-04 Create Failed")
        return _err(f"Lỗi hệ thống: {str(e)}", "SYSTEM_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 10. GET PO DETAILS (Auto-fill vendor/model)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_po_details(po_name: str) -> dict:
    """
    Lấy thông tin PO để auto-fill vendor, model khi user chọn PO.

    Endpoint: GET /api/method/assetcore.api.imm04.get_po_details?po_name=PO-2026-0041
    """
    if not po_name:
        return _err("Thiếu tham số po_name", "MISSING_PARAM")

    if not frappe.db.exists("Purchase Order", po_name):
        return _err(f"Không tìm thấy PO '{po_name}'", "NOT_FOUND")

    po = frappe.get_doc("Purchase Order", po_name)

    # Lấy item đầu tiên từ PO (thường là thiết bị chính)
    items = []
    for item in po.items:
        is_radiation = frappe.db.get_value("Item", item.item_code, "custom_is_radiation") or 0
        items.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "is_radiation": bool(is_radiation),
        })

    return _ok({
        "po_name": po.name,
        "supplier": po.supplier,
        "supplier_name": po.supplier_name,
        "transaction_date": str(po.transaction_date),
        "items": items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 11. SEARCH LINK — Autocomplete for Link fields
# ─────────────────────────────────────────────────────────────────────────────

_ALLOWED_DOCTYPES = {
    "Purchase Order": {
        "label_field": "name",
        "search_fields": ["name", "supplier"],
        "filters": {"docstatus": 1},
        "extra_fields": ["supplier", "supplier_name", "transaction_date"],
    },
    "Item": {
        "label_field": "item_name",
        "search_fields": ["item_code", "item_name"],
        "filters": {"disabled": 0},
        "extra_fields": ["item_code", "item_name"],
    },
    "Supplier": {
        "label_field": "supplier_name",
        "search_fields": ["name", "supplier_name"],
        "filters": {},
        "extra_fields": ["supplier_name"],
    },
    "Department": {
        "label_field": "department_name",
        "search_fields": ["name", "department_name"],
        "filters": {},
        "extra_fields": ["department_name"],
    },
}


@frappe.whitelist()
def search_link(doctype: str, query: str = "", page_length: int = 10) -> dict:
    """
    Tìm kiếm autocomplete cho Link fields trong IMM-04.

    Endpoint: GET /api/method/assetcore.api.imm04.search_link
              ?doctype=Purchase Order&query=PO-2026&page_length=10

    Returns:
        {success: true, data: [{value, label, description}]}
    """
    if doctype not in _ALLOWED_DOCTYPES:
        return _err(f"DocType '{doctype}' không được phép tìm kiếm", "FORBIDDEN_DOCTYPE")

    config = _ALLOWED_DOCTYPES[doctype]
    search_fields: list[str] = config["search_fields"]
    filters: dict = dict(config["filters"])
    extra_fields: list[str] = config["extra_fields"]

    # Build OR conditions for search
    or_filters = []
    if query:
        q = f"%{query}%"
        for field in search_fields:
            or_filters.append([doctype, field, "like", q])

    try:
        fields = [*{*extra_fields, "name"}]
        results = frappe.db.get_all(
            doctype,
            filters=filters,
            or_filters=or_filters or None,
            fields=fields,
            limit=int(page_length),
            order_by="modified desc",
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-04 search_link Error")
        return _err(f"Lỗi tìm kiếm: {str(e)}", "SEARCH_ERROR")

    label_field = config["label_field"]
    items = []
    for row in results:
        value = row.get("name") or row.get(label_field, "")
        label = row.get(label_field) or value
        # Build description from remaining extra fields
        desc_parts = [
            str(row[f]) for f in extra_fields
            if f != label_field and row.get(f)
        ]
        items.append({
            "value": value,
            "label": label,
            "description": " | ".join(desc_parts) if desc_parts else "",
        })

    return _ok(items)


# ─────────────────────────────────────────────────────────────────────────────
# 12. REPORT NON CONFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def report_nonconformance(commissioning_name: str, nc_data: str | dict | None = None) -> dict:
    """Tạo NC record cho commissioning. BR-04-06."""
    import json
    if isinstance(nc_data, str):
        try:
            nc_data = json.loads(nc_data)
        except Exception:
            return _err("Dữ liệu NC không hợp lệ.", "INVALID_DATA")
    nc_data = nc_data or {}
    try:
        doc = frappe.get_doc({
            "doctype": "Asset QA Non Conformance",
            "ref_commissioning": commissioning_name,
            "nc_type": nc_data.get("nc_type", "Other"),
            "severity": nc_data.get("severity", "Minor"),
            "description": nc_data.get("description", ""),
            "resolution_status": "Open",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return _ok({"name": doc.name, "nc_type": doc.nc_type, "severity": doc.severity})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "report_nonconformance error")
        return _err(str(e), "CREATE_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 13. ASSIGN IDENTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def assign_identification(
    name: str,
    vendor_serial_no: str = "",
    internal_tag_qr: str = "",
    custom_moh_code: str = "",
) -> dict:
    """Gán định danh thiết bị (VR-01). Chỉ dùng ở state Identification."""
    try:
        doc = frappe.get_doc("Asset Commissioning", name)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy Commissioning: {name}", "NOT_FOUND")
    if doc.workflow_state != "Identification":
        return _err("Chỉ có thể gán định danh khi ở trạng thái Identification.", "INVALID_STATE")
    # VR-01: check unique serial
    if vendor_serial_no:
        dup = frappe.db.exists("Asset Commissioning", {
            "vendor_serial_no": vendor_serial_no,
            "name": ("!=", name),
            "docstatus": ("!=", 2),
        })
        if dup:
            return _err(
                f"VR-01: Serial '{vendor_serial_no}' đã được gán cho Commissioning {dup}.",
                "VALIDATION_ERROR",
            )
    doc.vendor_serial_no = vendor_serial_no or doc.vendor_serial_no
    doc.internal_tag_qr = internal_tag_qr or doc.internal_tag_qr
    doc.custom_moh_code = custom_moh_code or doc.custom_moh_code
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _ok({
        "name": doc.name,
        "vendor_serial_no": doc.vendor_serial_no,
        "internal_tag_qr": doc.internal_tag_qr,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 14. CHECK SN UNIQUE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def check_sn_unique(vendor_sn: str, exclude_name: str = "") -> dict:
    """Kiểm tra Serial Number có bị trùng không. Dùng cho on-blur validation (VR-01)."""
    if not vendor_sn:
        return _ok({"is_unique": True})
    filters = {"vendor_serial_no": vendor_sn, "docstatus": ("!=", 2)}
    if exclude_name:
        filters["name"] = ("!=", exclude_name)
    existing = frappe.db.get_value("Asset Commissioning", filters, ["name", "master_item"], as_dict=True)
    if existing:
        return _ok({"is_unique": False, "existing_commissioning": existing.name, "item": existing.master_item})
    return _ok({"is_unique": True})


# ─────────────────────────────────────────────────────────────────────────────
# 15. SUBMIT BASELINE CHECKLIST
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_baseline_checklist(name: str, results: str | list | None = None) -> dict:
    """KTV submit kết quả baseline. Validates BR-04-04 (100% Pass or N/A)."""
    import json
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except Exception:
            return _err("Dữ liệu kết quả không hợp lệ.", "INVALID_DATA")
    results = results or []
    try:
        doc = frappe.get_doc("Asset Commissioning", name)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy: {name}", "NOT_FOUND")
    if doc.workflow_state != "Initial Inspection":
        return _err("Chỉ submit checklist khi ở trạng thái Initial Inspection.", "INVALID_STATE")
    # Update checklist results
    result_map = {r.get("parameter"): r for r in results}
    for row in doc.baseline_tests or []:
        if row.parameter in result_map:
            r = result_map[row.parameter]
            row.measured_val = r.get("measured_val", "")
            row.test_result = r.get("test_result", "")
            row.fail_note = r.get("fail_note", "")
    # BR-04-04: check for fails
    fails = [r.parameter for r in (doc.baseline_tests or []) if r.test_result == "Fail"]
    if fails:
        return _err(
            f"BR-04-04: Thông số sau không đạt: {', '.join(fails)}. Chuyển sang Re Inspection.",
            "VALIDATION_ERROR",
        )
    # Check if radiation/Class C/D → auto Clinical Hold
    from assetcore.services.imm04 import check_auto_clinical_hold
    is_high_risk = check_auto_clinical_hold(doc)
    doc.overall_inspection_result = "Pass"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _ok({
        "name": doc.name,
        "overall_result": "Pass",
        "clinical_hold_required": is_high_risk,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 16. CLEAR CLINICAL HOLD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def clear_clinical_hold(name: str, license_no: str = "") -> dict:
    """QA Officer gỡ Clinical Hold sau khi upload giấy phép BYT."""
    try:
        doc = frappe.get_doc("Asset Commissioning", name)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy: {name}", "NOT_FOUND")
    if doc.workflow_state != "Clinical Hold":
        return _err("Commissioning không ở trạng thái Clinical Hold.", "INVALID_STATE")
    if not doc.qa_license_doc and not license_no:
        return _err(
            "BR-04-05: Phải upload giấy phép BYT trước khi gỡ Clinical Hold.",
            "VALIDATION_ERROR",
        )
    if license_no:
        doc.radiation_license_no = license_no
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _ok({"name": doc.name, "license_no": doc.radiation_license_no})


# ─────────────────────────────────────────────────────────────────────────────
# 17. GENERATE HANDOVER PDF
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def upload_document(commissioning: str, doc_index: int, doc_type: str = "", file_url: str = "", expiry_date: str = "", doc_number: str = "") -> dict:
    """Update a document record row: mark Received + set file_url."""
    try:
        doc = frappe.get_doc("Asset Commissioning", commissioning)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy: {commissioning}", "NOT_FOUND")
    idx = int(doc_index)
    for row in doc.commissioning_documents:
        if row.idx == idx:
            row.status = "Received"
            if file_url:
                row.file_url = file_url
            if expiry_date:
                row.expiry_date = expiry_date
            if doc_number:
                row.doc_number = doc_number
            row.uploaded_by = frappe.session.user
            row.uploaded_at = frappe.utils.now_datetime()
            break
    doc.save(ignore_permissions=True)
    all_mandatory = all(r.status in ("Received", "Waived") for r in doc.commissioning_documents if r.is_mandatory)
    return _ok({"commissioning": commissioning, "doc_index": idx, "all_mandatory_received": all_mandatory})


@frappe.whitelist(methods=["POST"])
def close_nonconformance(nc_name: str, root_cause: str = "", corrective_action: str = "") -> dict:
    """Close an NC with root_cause + corrective_action evidence."""
    if not root_cause or not corrective_action:
        return _err("root_cause và corrective_action là bắt buộc khi đóng NC.", "VALIDATION_ERROR")
    try:
        nc = frappe.get_doc("Asset QA Non Conformance", nc_name)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy NC: {nc_name}", "NOT_FOUND")
    nc.resolution_status = "Closed"
    nc.root_cause = root_cause
    nc.corrective_action = corrective_action
    nc.closed_by = frappe.session.user
    nc.closed_date = nowdate()
    nc.save(ignore_permissions=True)
    frappe.db.commit()
    return _ok({"name": nc_name, "status": "Closed"})


@frappe.whitelist(methods=["POST"])
def approve_clinical_release(commissioning: str, board_approver: str, approval_remarks: str = "") -> dict:
    """Board approves Clinical Release → validate G05+G06, create Asset, trigger IMM-05+IMM-08."""
    try:
        doc = frappe.get_doc("Asset Commissioning", commissioning)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy: {commissioning}", "NOT_FOUND")
    if doc.workflow_state != "Clinical Release":
        return _err(f"Phiếu phải ở Clinical Release. Hiện tại: {doc.workflow_state}", "INVALID_STATE")
    if not board_approver:
        return _err("board_approver là bắt buộc.", "VALIDATION_ERROR")
    open_nc = frappe.db.count("Asset QA Non Conformance", {"ref_commissioning": commissioning, "resolution_status": "Open"})
    if open_nc > 0:
        return _err(f"VR-04: Còn {open_nc} NC chưa đóng. Giải quyết trước khi Release.", "OPEN_NC")
    doc.board_approver = board_approver
    if approval_remarks:
        doc.notes = (doc.notes or "") + f"\n[Board Approval] {approval_remarks}"
    doc.save(ignore_permissions=True)
    try:
        doc.submit()
        return _ok({
            "commissioning": commissioning,
            "new_status": "Clinical Release",
            "asset_ref": doc.final_asset,
            "commissioning_date": str(doc.commissioning_date or nowdate()),
            "pm_schedule_created": False,
            "device_record_queued": True,
        })
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "approve_clinical_release failed")
        return _err(str(e), "SYSTEM_ERROR")


@frappe.whitelist(methods=["POST"])
def report_doa(commissioning: str, description: str, evidence_file: str = "") -> dict:
    """Report Dead-on-Arrival → create Critical NC + transition to Non Conformance."""
    if not description:
        return _err("description là bắt buộc.", "VALIDATION_ERROR")
    nc = frappe.get_doc({
        "doctype": "Asset QA Non Conformance",
        "ref_commissioning": commissioning,
        "nc_type": "DOA",
        "severity": "Critical",
        "description": description,
        "resolution_status": "Open",
    })
    nc.insert(ignore_permissions=True)
    frappe.db.commit()
    return _ok({"nc_name": nc.name, "commissioning": commissioning, "severity": "Critical"})


# ─────────────────────────────────────────────────────────────────────────────
# 17. GENERATE HANDOVER PDF
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def generate_handover_pdf(name: str) -> dict:
    """Tạo PDF biên bản bàn giao từ commissioning record."""
    try:
        doc = frappe.get_doc("Asset Commissioning", name)
    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy: {name}", "NOT_FOUND")
    if doc.workflow_state != "Clinical Release":
        return _err("Chỉ xuất biên bản khi đã Clinical Release.", "INVALID_STATE")
    try:
        pdf_url = f"/api/method/frappe.utils.pdf.get_pdf?doctype=Asset+Commissioning&name={frappe.utils.quote(name)}&format=Biên+bản+Bàn+giao"
        return _ok({"pdf_url": pdf_url, "name": name})
    except Exception as e:
        return _err(str(e), "PDF_ERROR")
