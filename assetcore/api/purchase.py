# Copyright (c) 2026, AssetCore Team
# IMM-00 Purchase API — CRUD for AC Purchase documents
from __future__ import annotations

import frappe
from frappe import _

from assetcore.utils.helpers import _err, _ok, _parse_json
from assetcore.services import purchase as svc
from assetcore.services.purchase import _DT_PUR

_MSG_NOT_FOUND = "Không tìm thấy đơn hàng"


def _enrich_purchase(doc: dict) -> dict:
    """Enrich supplier name + device model names + linked commissioning states."""
    sup = doc.get("supplier")
    if sup:
        row = frappe.db.get_value("AC Supplier", sup, ["supplier_name"], as_dict=True)
        if row:
            doc["supplier_name"] = row.supplier_name

    devices = doc.get("devices") or []
    if devices:
        model_ids = {d.get("device_model") for d in devices if d.get("device_model")}
        model_map = {}
        if model_ids:
            for m in frappe.get_all("IMM Device Model",
                                     filters={"name": ["in", list(model_ids)]},
                                     fields=["name", "model_name", "manufacturer"]):
                model_map[m.name] = m

        comm_ids = {d.get("commissioning_ref") for d in devices if d.get("commissioning_ref")}
        comm_map = {}
        if comm_ids:
            for c in frappe.get_all("Asset Commissioning",
                                     filters={"name": ["in", list(comm_ids)]},
                                     fields=["name", "workflow_state", "final_asset"]):
                comm_map[c.name] = c

        for d in devices:
            m = model_map.get(d.get("device_model") or "")
            if m:
                d["device_model_name"] = m.get("model_name")
                d["manufacturer"]      = m.get("manufacturer")
            c = comm_map.get(d.get("commissioning_ref") or "")
            if c:
                d["commissioning_state"] = c.get("workflow_state")
                d["final_asset"]          = c.get("final_asset")
    return doc


def _get_doc(name: str):
    """Load AC Purchase by name; raises tuple (response_dict,) on not-found."""
    try:
        return frappe.get_doc(_DT_PUR, name)
    except frappe.DoesNotExistError:
        return None


# ─── List ─────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_purchases(page: int = 1, page_size: int = 30, status: str = "",
                   supplier: str = "") -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if supplier:
        filters["supplier"] = supplier

    total = frappe.db.count(_DT_PUR, filters)
    rows = frappe.get_all(
        _DT_PUR,
        filters=filters,
        fields=["name", "purchase_date", "supplier", "invoice_no",
                "status", "total_value", "expected_delivery"],
        order_by="purchase_date DESC",
        limit_start=(int(page) - 1) * int(page_size),
        limit_page_length=int(page_size),
    )
    # enrich supplier names
    sup_ids = {r.supplier for r in rows if r.supplier}
    sup_map = {}
    if sup_ids:
        for s in frappe.get_all("AC Supplier", filters={"name": ["in", list(sup_ids)]},
                                fields=["name", "supplier_name"]):
            sup_map[s.name] = s.supplier_name
    for r in rows:
        r["supplier_name"] = sup_map.get(r.supplier, r.supplier)
    return _ok({"data": rows, "total": total})


# ─── Detail ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_purchase(name: str) -> dict:
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    return _ok(_enrich_purchase(doc.as_dict()))


# ─── Create ───────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_purchase(payload: str = "") -> dict:
    data = _parse_json(payload, {}) or dict(frappe.local.form_dict)
    data.pop("payload", None)
    data.pop("cmd", None)

    if not data.get("supplier"):
        return _err(_("Thiếu trường bắt buộc: supplier"), 400)

    items   = data.get("items")   or []
    devices = data.get("devices") or []
    if not items and not devices:
        return _err(_("Phải có ít nhất 1 thiết bị hoặc 1 phụ tùng"), 400)

    doc = frappe.get_doc({
        "doctype": _DT_PUR,
        "purchase_date": data.get("purchase_date") or frappe.utils.now_datetime(),
        "supplier": data["supplier"],
        "invoice_no": data.get("invoice_no") or "",
        "expected_delivery": data.get("expected_delivery"),
        "notes": data.get("notes") or "",
        "items": [
            {
                "spare_part": r["spare_part"],
                "qty": float(r.get("qty") or 1),
                "unit_cost": float(r.get("unit_cost") or 0),
            }
            for r in items if r.get("spare_part")
        ],
        "devices": [
            {
                "device_model":     d["device_model"],
                "qty":              1,
                "unit_cost":        float(d.get("unit_cost") or 0),
                "vendor_serial_no": d.get("vendor_serial_no") or "",
                "warranty_months":  int(d.get("warranty_months") or 0),
                "clinical_dept":    d.get("clinical_dept") or "",
                "notes":            d.get("notes") or "",
            }
            for d in devices if d.get("device_model")
        ],
    })
    doc.insert(ignore_permissions=True)

    if int(data.get("auto_submit") or 0):
        doc.submit()

    return _ok({"name": doc.name, "status": doc.status})


# ─── Update ───────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def update_purchase(name: str, payload: str = "") -> dict:
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    data = _parse_json(payload, {})
    if not data:
        return _err(_("Không có dữ liệu cập nhật"), 400)
    if doc.docstatus != 0:
        return _err(_("Chỉ được sửa phiếu ở trạng thái Nháp"), 400)

    editable = ["purchase_date", "supplier", "invoice_no", "expected_delivery", "notes"]
    for f in editable:
        if f in data:
            doc.set(f, data[f])

    if "items" in data:
        doc.set("items", [
            {"spare_part": r["spare_part"], "qty": float(r.get("qty") or 1),
             "unit_cost": float(r.get("unit_cost") or 0)}
            for r in data["items"] if r.get("spare_part")
        ])

    if "devices" in data:
        # Preserve commissioning_ref on existing rows matched by device_model + vendor_serial_no
        existing_links: dict[tuple[str, str], str] = {}
        for row in (doc.get("devices") or []):
            if row.commissioning_ref:
                key = (row.device_model or "", row.vendor_serial_no or "")
                existing_links[key] = row.commissioning_ref

        new_rows = []
        for d in data["devices"]:
            if not d.get("device_model"):
                continue
            key = (d["device_model"], d.get("vendor_serial_no") or "")
            new_rows.append({
                "device_model":      d["device_model"],
                "qty":               1,
                "unit_cost":         float(d.get("unit_cost") or 0),
                "vendor_serial_no":  d.get("vendor_serial_no") or "",
                "warranty_months":   int(d.get("warranty_months") or 0),
                "clinical_dept":     d.get("clinical_dept") or "",
                "notes":             d.get("notes") or "",
                "commissioning_ref": existing_links.get(key, ""),
            })
        doc.set("devices", new_rows)

    doc.save(ignore_permissions=True)
    return _ok({"name": doc.name, "status": doc.status})


# ─── Submit / Cancel / Delete ─────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_purchase(name: str) -> dict:
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    if doc.docstatus != 0:
        return _err(_("Phiếu không ở trạng thái Nháp"), 400)
    doc.submit()
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist(methods=["POST"])
def cancel_purchase(name: str) -> dict:
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    if doc.docstatus != 1:
        return _err(_("Chỉ được huỷ phiếu đã duyệt"), 400)
    doc.cancel()
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist(methods=["POST"])
def delete_purchase(name: str) -> dict:
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    if doc.docstatus != 0:
        return _err(_("Chỉ được xoá phiếu Nháp"), 400)
    frappe.delete_doc(_DT_PUR, name, ignore_permissions=True)
    return _ok({"deleted": name})


# ─── Mark as Received ─────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def mark_received(name: str) -> dict:
    """Mark a Submitted purchase as Received (goods arrived)."""
    doc = _get_doc(name)
    if not doc:
        return _err(_(_MSG_NOT_FOUND), 404)
    if doc.docstatus != 1 or doc.status != "Submitted":
        return _err(_("Chỉ được xác nhận nhận hàng cho phiếu đã duyệt"), 400)
    doc.db_set("status", "Received")
    return _ok({"name": doc.name, "status": "Received"})


# ─── Linked stock movements ───────────────────────────────────────────────────

@frappe.whitelist()
def get_purchase_movements(name: str) -> dict:
    """Return all AC Stock Movements linked to this purchase."""
    if not frappe.db.exists(_DT_PUR, name):
        return _err(_(_MSG_NOT_FOUND), 404)
    return _ok(svc.get_purchase_movements(name))


@frappe.whitelist(methods=["POST"])
def create_receipt_movement(name: str, to_warehouse: str,
                            requested_by: str = "", auto_submit: int = 0) -> dict:
    """Create a Receipt Stock Movement from an approved AC Purchase."""
    if not frappe.db.exists(_DT_PUR, name):
        return _err(_(_MSG_NOT_FOUND), 404)
    try:
        movement = svc.create_receipt_movement(
            purchase_name=name,
            to_warehouse=to_warehouse,
            requested_by=requested_by or frappe.session.user,
            auto_submit=bool(int(auto_submit)),
        )
        return _ok({"movement_name": movement.name, "status": movement.status})
    except frappe.ValidationError as exc:
        return _err(str(exc), 400)


# ─── Purchases by spare part ─────────────────────────────────────────────────

@frappe.whitelist()
def get_part_purchases(spare_part: str, limit: int = 20) -> dict:
    """Return AC Purchases that contain a given spare part."""
    if not frappe.db.exists("AC Spare Part", spare_part):
        return _err(_("Không tìm thấy phụ tùng"), 404)
    rows = frappe.db.sql("""
        SELECT p.name, p.purchase_date, p.supplier, p.invoice_no,
               p.status, p.total_value,
               pi.qty, pi.unit_cost, pi.total_cost,
               s.supplier_name
        FROM `tabAC Purchase Item` pi
        JOIN `tabAC Purchase` p ON p.name = pi.parent
        LEFT JOIN `tabAC Supplier` s ON s.name = p.supplier
        WHERE pi.spare_part = %s AND p.docstatus IN (0, 1)
        ORDER BY p.purchase_date DESC
        LIMIT %s
    """, [spare_part, int(limit)], as_dict=True)
    return _ok(rows)


# ─── Linked commissioning records ────────────────────────────────────────────

@frappe.whitelist()
def get_purchase_commissionings(name: str) -> dict:
    """Return all Asset Commissioning records that reference this AC Purchase."""
    if not frappe.db.exists(_DT_PUR, name):
        return _err(_(_MSG_NOT_FOUND), 404)
    rows = frappe.get_all(
        "Asset Commissioning",
        filters={"po_reference": name},
        fields=["name", "workflow_state", "master_item", "vendor",
                "clinical_dept", "vendor_serial_no", "final_asset",
                "expected_installation_date", "commissioning_date"],
        order_by="creation DESC",
    )
    return _ok(rows)


# ─── Search (for Stock Movement reference picker) ────────────────────────────

@frappe.whitelist()
def search_purchases(query: str = "", limit: int = 20) -> dict:
    q = (query or "").strip()
    like = f"%{q}%"
    limit = min(int(limit), 50)
    rows = frappe.db.sql("""
        SELECT p.name,
               CONCAT(p.name, IF(p.invoice_no, CONCAT(' · ', p.invoice_no), '')) AS label,
               CONCAT(s.supplier_name, ' — ', p.status) AS description
        FROM `tabAC Purchase` p
        LEFT JOIN `tabAC Supplier` s ON s.name = p.supplier
        WHERE p.docstatus = 1
          AND (p.name LIKE %s OR p.invoice_no LIKE %s OR s.supplier_name LIKE %s)
        ORDER BY p.purchase_date DESC
        LIMIT %s
    """, [like, like, like, limit], as_dict=True)
    return _ok(rows)
