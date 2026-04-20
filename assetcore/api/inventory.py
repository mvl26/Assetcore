# Copyright (c) 2026, AssetCore Team
# IMM-00 Inventory API — Tier 1 (HTTP → service → envelope)
from __future__ import annotations

import json

import frappe
from frappe import _

from assetcore.services import inventory as svc
from assetcore.utils.helpers import _err, _ok

_DT_WH   = "AC Warehouse"
_DT_PART = "AC Spare Part"
_DT_STOCK = "AC Spare Part Stock"
_DT_MOV  = "AC Stock Movement"

_MSG_WH_NOT_FOUND   = "Không tìm thấy kho"
_MSG_PART_NOT_FOUND = "Không tìm thấy phụ tùng"
_MSG_MOV_NOT_FOUND  = "Không tìm thấy phiếu"


def _parse_json(raw, default):
    if not raw:
        return default
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


# ─── Warehouse ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_warehouses(page: int = 1, page_size: int = 30, active_only: int = 1) -> dict:
    filters = {"is_active": 1} if int(active_only) else {}
    total = frappe.db.count(_DT_WH, filters)
    rows = frappe.get_all(
        _DT_WH, filters=filters,
        fields=["name", "warehouse_code", "warehouse_name", "department",
                "location", "manager", "is_active"],
        limit_start=(int(page) - 1) * int(page_size),
        limit_page_length=int(page_size),
        order_by="warehouse_name asc",
    )
    wh_names = [r["name"] for r in rows]
    if wh_names:
        enrichment = frappe.db.sql("""
            SELECT s.warehouse,
                   COUNT(*) AS stock_count,
                   COALESCE(SUM(s.qty_on_hand * p.unit_cost), 0) AS total_value
            FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE s.warehouse IN %(wh)s
            GROUP BY s.warehouse
        """, {"wh": wh_names}, as_dict=True)
        enrich_map = {e["warehouse"]: e for e in enrichment}
    else:
        enrich_map = {}
    for r in rows:
        e = enrich_map.get(r["name"], {})
        r["stock_count"] = int(e.get("stock_count") or 0)
        r["total_value"]  = float(e.get("total_value") or 0)
    return _ok({"items": rows, "pagination": {"page": page, "page_size": page_size, "total": total}})


@frappe.whitelist(methods=["POST"])
def create_warehouse() -> dict:
    data = frappe.local.form_dict
    code = (data.get("warehouse_code") or "").strip()
    name = (data.get("warehouse_name") or "").strip()
    if not code or not name:
        return _err(_("Mã kho và tên kho là bắt buộc"), 400)
    try:
        doc = frappe.get_doc({
            "doctype": _DT_WH,
            "warehouse_code": code,
            "warehouse_name": name,
            "location":   data.get("location")   or None,
            "department": data.get("department") or None,
            "manager":    data.get("manager")    or None,
            "is_active":  int(data.get("is_active", 1)),
            "notes":      data.get("notes") or None,
        })
        doc.insert()
        return _ok({"name": doc.name})
    except frappe.DuplicateEntryError:
        return _err(_("Mã kho '{0}' đã tồn tại").format(code), 409)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 400)


@frappe.whitelist(methods=["POST"])
def update_warehouse(name: str) -> dict:
    if not frappe.db.exists(_DT_WH, name):
        return _err(_(_MSG_WH_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_WH, name)
    for k in ("warehouse_code", "warehouse_name", "location", "department", "manager", "notes"):
        v = frappe.local.form_dict.get(k)
        if v is not None:
            setattr(doc, k, v)
    if "is_active" in frappe.local.form_dict:
        doc.is_active = int(frappe.local.form_dict.get("is_active") or 0)
    doc.save()
    return _ok({"name": doc.name})


# ─── Spare Part ──────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_spare_parts(page: int = 1, page_size: int = 30, q: str = "",
                     category: str = "", active_only: int = 1) -> dict:
    filters: dict = {}
    if int(active_only):
        filters["is_active"] = 1
    if category:
        filters["part_category"] = category

    or_filters = []
    if q:
        or_filters = [
            ["part_name", "like", f"%{q}%"],
            ["part_code", "like", f"%{q}%"],
            ["manufacturer_part_no", "like", f"%{q}%"],
        ]

    if or_filters:
        like = f"%{q}%"
        extra_conds = []
        extra_params: list = [like, like, like]
        if int(active_only):
            extra_conds.append("is_active = 1")
        if category:
            extra_conds.append("part_category = %s")
            extra_params.append(category)
        and_sql = (" AND " + " AND ".join(extra_conds)) if extra_conds else ""
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabAC Spare Part`"
            f" WHERE (part_name LIKE %s OR part_code LIKE %s"
            f" OR manufacturer_part_no LIKE %s){and_sql}",
            extra_params
        )[0][0]
    else:
        total = frappe.db.count(_DT_PART, filters)

    rows = frappe.get_all(
        _DT_PART, filters=filters, or_filters=or_filters,
        fields=["name", "part_code", "part_name", "part_category",
                "manufacturer", "manufacturer_part_no", "preferred_supplier",
                "unit_cost", "uom", "min_stock_level", "max_stock_level",
                "is_critical", "is_active"],
        limit_start=(int(page) - 1) * int(page_size),
        limit_page_length=int(page_size),
        order_by="part_name asc",
    )

    part_ids = [r["name"] for r in rows]
    stock_totals = {
        row[0]: float(row[1])
        for row in frappe.db.sql("""
            SELECT spare_part, COALESCE(SUM(qty_on_hand), 0)
            FROM `tabAC Spare Part Stock`
            WHERE spare_part IN %(ids)s
            GROUP BY spare_part
        """, {"ids": part_ids})
    } if part_ids else {}

    for r in rows:
        ts = stock_totals.get(r["name"], 0.0)
        r["total_stock"] = ts
        r["is_low_stock"] = ts < (r.get("min_stock_level") or 0) if r.get("min_stock_level") else False

    return _ok({"items": rows, "pagination": {"page": page, "page_size": page_size, "total": total}})


@frappe.whitelist()
def get_spare_part(name: str) -> dict:
    if not frappe.db.exists(_DT_PART, name):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_PART, name).as_dict()

    doc["stock_by_warehouse"] = frappe.db.sql("""
        SELECT s.warehouse, w.warehouse_name, s.qty_on_hand, s.reserved_qty,
               s.available_qty, s.last_movement_date
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
        WHERE s.spare_part = %s
        ORDER BY w.warehouse_name
    """, name, as_dict=True)

    doc["total_stock"] = svc.get_total_stock(name)

    doc["recent_movements"] = frappe.db.sql("""
        SELECT m.name, m.movement_type, m.movement_date,
               m.from_warehouse, m.to_warehouse, m.status, mi.qty, mi.unit_cost
        FROM `tabAC Stock Movement Item` mi
        JOIN `tabAC Stock Movement` m ON m.name = mi.parent
        WHERE mi.spare_part = %s AND m.docstatus IN (0, 1)
        ORDER BY m.movement_date DESC
        LIMIT 20
    """, name, as_dict=True)

    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def create_spare_part() -> dict:
    data = frappe.local.form_dict
    doc = frappe.get_doc({
        "doctype": _DT_PART,
        "part_code": data.get("part_code"),
        "part_name": data.get("part_name"),
        "part_category": data.get("part_category"),
        "manufacturer": data.get("manufacturer"),
        "manufacturer_part_no": data.get("manufacturer_part_no"),
        "preferred_supplier": data.get("preferred_supplier"),
        "unit_cost": float(data.get("unit_cost") or 0),
        "uom": data.get("uom") or "Nos",
        "min_stock_level": int(data.get("min_stock_level") or 0),
        "max_stock_level": int(data.get("max_stock_level") or 0),
        "shelf_life_months": int(data.get("shelf_life_months") or 0),
        "is_critical": int(data.get("is_critical", 0)),
        "is_active": int(data.get("is_active", 1)),
        "specifications": data.get("specifications"),
    })
    doc.insert()
    return _ok({"name": doc.name, "part_code": doc.part_code})


@frappe.whitelist(methods=["POST"])
def update_spare_part(name: str) -> dict:
    if not frappe.db.exists(_DT_PART, name):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_PART, name)
    editable = [
        "part_name", "part_category", "manufacturer", "manufacturer_part_no",
        "preferred_supplier", "unit_cost", "uom", "min_stock_level",
        "max_stock_level", "shelf_life_months", "is_critical", "is_active",
        "specifications",
    ]
    for k in editable:
        v = frappe.local.form_dict.get(k)
        if v is not None:
            setattr(doc, k, v)
    doc.save()
    return _ok({"name": doc.name})


# ─── Stock Overview & Levels ─────────────────────────────────────────────────

@frappe.whitelist()
def get_stock_overview() -> dict:
    return _ok(svc.get_stock_overview())


@frappe.whitelist()
def list_stock_levels(page: int = 1, page_size: int = 50,
                      warehouse: str = "", spare_part: str = "",
                      low_only: int = 0) -> dict:
    page     = int(page)
    pg_size  = int(page_size)
    offset   = (page - 1) * pg_size

    if int(low_only):
        wh_cond = "AND s.warehouse = %(wh)s" if warehouse else ""
        sp_cond = "AND s.spare_part = %(sp)s" if spare_part else ""
        sql_p: dict = {}
        if warehouse:  sql_p["wh"] = warehouse
        if spare_part: sql_p["sp"] = spare_part
        low_cond = """
            COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0) > 0
            AND s.qty_on_hand < COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)
        """
        total = frappe.db.sql(f"""
            SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE {low_cond} {wh_cond} {sp_cond}
        """, sql_p)[0][0]
        sql_p["off"] = offset
        sql_p["lim"] = pg_size
        rows = frappe.db.sql(f"""
            SELECT s.name, s.warehouse, s.spare_part, s.qty_on_hand,
                   s.reserved_qty, s.available_qty, s.last_movement_date,
                   s.min_stock_override,
                   p.part_name, p.uom, p.unit_cost, p.min_stock_level,
                   p.is_critical,
                   w.warehouse_name,
                   COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0) AS min_level
            FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
            WHERE {low_cond} {wh_cond} {sp_cond}
            ORDER BY s.warehouse, p.part_name
            LIMIT %(off)s, %(lim)s
        """, sql_p, as_dict=True)
        for r in rows:
            r["is_low"] = True
            r["stock_value"] = float((r.get("qty_on_hand") or 0) * (r.get("unit_cost") or 0))
            r["is_critical"] = bool(r.get("is_critical"))
        return _ok({"items": rows, "pagination": {"page": page, "page_size": pg_size, "total": total}})

    filters: dict = {}
    if warehouse:
        filters["warehouse"] = warehouse
    if spare_part:
        filters["spare_part"] = spare_part

    total = frappe.db.count(_DT_STOCK, filters)
    rows = frappe.get_all(
        _DT_STOCK, filters=filters,
        fields=["name", "warehouse", "spare_part", "part_name", "uom",
                "qty_on_hand", "reserved_qty", "available_qty",
                "last_movement_date", "min_stock_override"],
        limit_start=offset,
        limit_page_length=pg_size,
        order_by="warehouse, part_name asc",
    )

    part_ids = list({r["spare_part"] for r in rows})
    wh_ids   = list({r["warehouse"]  for r in rows})
    part_map = {p["name"]: p for p in frappe.get_all(
        _DT_PART, filters={"name": ["in", part_ids]},
        fields=["name", "min_stock_level", "unit_cost", "is_critical"]
    )} if part_ids else {}
    wh_map = {w["name"]: w["warehouse_name"] for w in frappe.get_all(
        _DT_WH, filters={"name": ["in", wh_ids]},
        fields=["name", "warehouse_name"]
    )} if wh_ids else {}

    for r in rows:
        pm = part_map.get(r["spare_part"], {})
        min_level = r.get("min_stock_override") or pm.get("min_stock_level") or 0
        r["min_level"]      = min_level
        r["is_low"]         = bool(min_level and (r["qty_on_hand"] or 0) < min_level)
        r["unit_cost"]      = float(pm.get("unit_cost") or 0)
        r["stock_value"]    = float((r["qty_on_hand"] or 0) * (pm.get("unit_cost") or 0))
        r["is_critical"]    = bool(pm.get("is_critical"))
        r["warehouse_name"] = wh_map.get(r["warehouse"], r["warehouse"])

    return _ok({"items": rows, "pagination": {"page": page, "page_size": pg_size, "total": total}})


# ─── Stock Movement ──────────────────────────────────────────────────────────

@frappe.whitelist()
def list_stock_movements(page: int = 1, page_size: int = 30,
                          movement_type: str = "", warehouse: str = "",
                          status: str = "") -> dict:
    conditions = ["1=1"]
    params: dict = {}
    if movement_type:
        conditions.append("movement_type = %(t)s"); params["t"] = movement_type
    if warehouse:
        conditions.append("(from_warehouse = %(w)s OR to_warehouse = %(w)s)"); params["w"] = warehouse
    if status:
        conditions.append("status = %(s)s"); params["s"] = status

    where_sql = " AND ".join(conditions)
    total_row = frappe.db.sql(f"SELECT COUNT(*) FROM `tabAC Stock Movement` WHERE {where_sql}", params)
    total = total_row[0][0] if total_row else 0

    params["lim_start"] = (int(page) - 1) * int(page_size)
    params["lim_size"]  = int(page_size)

    rows = frappe.db.sql(f"""
        SELECT name, movement_type, movement_date, from_warehouse, to_warehouse,
               status, reference_type, reference_name, requested_by,
               total_value, docstatus, creation
        FROM `tabAC Stock Movement`
        WHERE {where_sql}
        ORDER BY movement_date DESC
        LIMIT %(lim_start)s, %(lim_size)s
    """, params, as_dict=True)

    return _ok({"items": rows, "pagination": {"page": page, "page_size": page_size, "total": total}})


@frappe.whitelist()
def get_stock_movement(name: str) -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_MOV, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_stock_movement(payload: str = "") -> dict:
    data = _parse_json(payload, {}) or dict(frappe.local.form_dict)
    items = data.get("items") or []
    if isinstance(items, str):
        items = _parse_json(items, [])

    doc = frappe.get_doc({
        "doctype": _DT_MOV,
        "movement_type": data.get("movement_type"),
        "movement_date": data.get("movement_date") or frappe.utils.now_datetime(),
        "from_warehouse": data.get("from_warehouse") or None,
        "to_warehouse": data.get("to_warehouse") or None,
        "supplier": data.get("supplier") or None,
        "reference_type": data.get("reference_type") or None,
        "reference_name": data.get("reference_name") or None,
        "requested_by": data.get("requested_by") or frappe.session.user,
        "notes": data.get("notes"),
        "items": [{
            "spare_part": i.get("spare_part"),
            "qty": float(i.get("qty") or 0),
            "unit_cost": float(i.get("unit_cost") or 0),
            "serial_no": i.get("serial_no"),
            "notes": i.get("notes"),
        } for i in items],
    })
    doc.insert()

    if int(data.get("auto_submit") or 0):
        doc.submit()

    return _ok({"name": doc.name, "status": doc.status, "docstatus": doc.docstatus})


@frappe.whitelist(methods=["POST"])
def submit_stock_movement(name: str) -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_MOV, name)
    if doc.docstatus != 0:
        return _err(_("Phiếu đã được duyệt hoặc đã huỷ"), 400)
    doc.submit()
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist(methods=["POST"])
def cancel_stock_movement(name: str) -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_MOV, name)
    if doc.docstatus != 1:
        return _err(_("Chỉ huỷ được phiếu đã duyệt"), 400)
    doc.cancel()
    return _ok({"name": doc.name, "status": doc.status})


# ─── Search (autocomplete) ───────────────────────────────────────────────────

@frappe.whitelist()
def search_parts_autocomplete(q: str = "", limit: int = 10) -> dict:
    return _ok(svc.search_parts(q, limit=int(limit)))


# ─── Warehouse detail & delete ────────────────────────────────────────────────

@frappe.whitelist()
def get_warehouse(name: str) -> dict:
    if not frappe.db.exists(_DT_WH, name):
        return _err(_(_MSG_WH_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_WH, name).as_dict()
    doc["stock_items"] = frappe.db.sql("""
        SELECT s.spare_part, p.part_name, p.part_code, p.uom,
               s.qty_on_hand, s.reserved_qty, s.available_qty,
               s.last_movement_date,
               COALESCE(p.unit_cost, 0) AS unit_cost,
               COALESCE(s.qty_on_hand * p.unit_cost, 0) AS stock_value
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE s.warehouse = %s
        ORDER BY p.part_name
    """, name, as_dict=True)
    doc["total_value"] = sum(float(r.get("stock_value") or 0) for r in doc["stock_items"])
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def delete_warehouse(name: str) -> dict:
    if not frappe.db.exists(_DT_WH, name):
        return _err(_(_MSG_WH_NOT_FOUND), 404)
    has_stock = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabAC Spare Part Stock`
        WHERE warehouse = %s AND qty_on_hand > 0
    """, name)[0][0]
    if has_stock:
        return _err(_("Không thể ngừng kho đang có tồn kho"), 400)
    frappe.db.set_value(_DT_WH, name, "is_active", 0)
    frappe.db.commit()
    return _ok({"name": name, "is_active": 0})


# ─── Spare Part delete ────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def delete_spare_part(name: str) -> dict:
    if not frappe.db.exists(_DT_PART, name):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    total_stock = frappe.db.sql("""
        SELECT COALESCE(SUM(qty_on_hand), 0)
        FROM `tabAC Spare Part Stock` WHERE spare_part = %s
    """, name)[0][0] or 0
    if float(total_stock) > 0:
        return _err(_("Không thể ngừng phụ tùng đang có tồn kho"), 400)
    frappe.db.set_value(_DT_PART, name, "is_active", 0)
    frappe.db.commit()
    return _ok({"name": name, "is_active": 0})


# ─── Stock Movement update & delete ──────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def update_stock_movement(name: str, payload: str = "") -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_MOV, name)
    if doc.docstatus != 0:
        return _err(_("Chỉ có thể sửa phiếu ở trạng thái nháp"), 400)

    data = _parse_json(payload, {}) or dict(frappe.local.form_dict)
    for field in ("movement_date", "from_warehouse", "to_warehouse",
                  "supplier", "reference_type", "reference_name", "notes"):
        val = data.get(field)
        if val is not None:
            setattr(doc, field, val or None)

    items_raw = data.get("items")
    if items_raw is not None:
        if isinstance(items_raw, str):
            items_raw = _parse_json(items_raw, [])
        doc.items = []
        for i in items_raw:
            doc.append("items", {
                "spare_part": i.get("spare_part"),
                "qty": float(i.get("qty") or 0),
                "unit_cost": float(i.get("unit_cost") or 0),
                "serial_no": i.get("serial_no"),
                "notes": i.get("notes"),
            })

    doc.save()
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist(methods=["POST"])
def delete_stock_movement(name: str) -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_MOV, name)
    if doc.docstatus != 0:
        return _err(_("Chỉ có thể xoá phiếu ở trạng thái nháp"), 400)
    doc.delete()
    frappe.db.commit()
    return _ok({"deleted": name})
