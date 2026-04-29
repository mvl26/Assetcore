# Copyright (c) 2026, AssetCore Team
# IMM-00 Inventory API — Tier 1 (HTTP → service → envelope)
from __future__ import annotations

import json

import frappe
from frappe import _

from assetcore.services import inventory as svc
from assetcore.services import uom as uom_svc
from assetcore.utils.helpers import _err, _ok, _parse_json

_DT_WH   = "AC Warehouse"
_DT_PART = "AC Spare Part"
_DT_STOCK = "AC Spare Part Stock"
_DT_MOV  = "AC Stock Movement"

_MSG_WH_NOT_FOUND   = "Không tìm thấy kho"
_MSG_PART_NOT_FOUND = "Không tìm thấy phụ tùng"
_MSG_MOV_NOT_FOUND  = "Không tìm thấy phiếu"
_AND = " AND "


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

    dept_codes = {r["department"] for r in rows if r.get("department")}
    loc_codes  = {r["location"]   for r in rows if r.get("location")}
    dept_map = (
        {d.name: d.department_name for d in frappe.get_all(
            "AC Department", filters={"name": ["in", list(dept_codes)]},
            fields=["name", "department_name"])}
        if dept_codes else {}
    )
    loc_map = (
        {l.name: l.location_name for l in frappe.get_all(
            "AC Location", filters={"name": ["in", list(loc_codes)]},
            fields=["name", "location_name"])}
        if loc_codes else {}
    )
    for r in rows:
        r["department_name"] = dept_map.get(r.get("department") or "", "") or r.get("department") or ""
        r["location_name"]   = loc_map.get(r.get("location") or "", "")   or r.get("location")   or ""
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

def _count_spare_parts(q: str, active_only: int, category: str) -> int:
    like = f"%{q}%"
    conds, params = [], [like, like, like]
    if active_only:
        conds.append("is_active = 1")
    if category:
        conds.append("part_category = %s")
        params.append(category)
    suffix = (_AND + _AND.join(conds)) if conds else ""
    return frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabAC Spare Part`"
        f" WHERE (part_name LIKE %s OR part_code LIKE %s"
        f" OR manufacturer_part_no LIKE %s){suffix}",
        params,
    )[0][0]


def _enrich_stock_totals(rows: list) -> None:
    part_ids = [r["name"] for r in rows]
    if not part_ids:
        return
    totals = {
        row[0]: float(row[1])
        for row in frappe.db.sql("""
            SELECT spare_part, COALESCE(SUM(qty_on_hand), 0)
            FROM `tabAC Spare Part Stock`
            WHERE spare_part IN %(ids)s
            GROUP BY spare_part
        """, {"ids": part_ids})
    }
    for r in rows:
        ts = totals.get(r["name"], 0.0)
        r["total_stock"] = ts
        r["is_low_stock"] = ts < (r["min_stock_level"] or 0) if r.get("min_stock_level") else False


@frappe.whitelist()
def list_spare_parts(page: int = 1, page_size: int = 30, q: str = "",
                     category: str = "", active_only: int = 1) -> dict:
    page, pg_size, active = int(page), int(page_size), int(active_only)
    filters: dict = {}
    if active:
        filters["is_active"] = 1
    if category:
        filters["part_category"] = category

    or_filters = [
        ["part_name", "like", f"%{q}%"],
        ["part_code", "like", f"%{q}%"],
        ["manufacturer_part_no", "like", f"%{q}%"],
    ] if q else []

    total = _count_spare_parts(q, active, category) if or_filters else frappe.db.count(_DT_PART, filters)

    rows = frappe.get_all(
        _DT_PART, filters=filters, or_filters=or_filters,
        fields=["name", "part_code", "part_name", "part_category",
                "manufacturer", "manufacturer_part_no", "preferred_supplier",
                "unit_cost", "stock_uom", "purchase_uom", "min_stock_level", "max_stock_level",
                "is_critical", "is_active"],
        limit_start=(page - 1) * pg_size,
        limit_page_length=pg_size,
        order_by="part_name asc",
    )
    _enrich_stock_totals(rows)
    return _ok({"items": rows, "pagination": {"page": page, "page_size": pg_size, "total": total}})


@frappe.whitelist()
def get_spare_part(name: str) -> dict:
    if not frappe.db.exists(_DT_PART, name):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_PART, name).as_dict()

    doc["stock_by_warehouse"] = frappe.db.sql("""
        SELECT s.warehouse, w.warehouse_code, w.warehouse_name,
               s.qty_on_hand, s.reserved_qty,
               s.available_qty, s.last_movement_date
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
        WHERE s.spare_part = %s
        ORDER BY w.warehouse_code
    """, name, as_dict=True)

    doc["total_stock"] = sum(float(r.get("qty_on_hand") or 0) for r in doc["stock_by_warehouse"])

    doc["recent_movements"] = frappe.db.sql("""
        SELECT m.name, m.movement_type, m.movement_date,
               m.from_warehouse, m.to_warehouse, m.status, mi.qty, mi.unit_cost
        FROM `tabAC Stock Movement Item` mi
        JOIN `tabAC Stock Movement` m ON m.name = mi.parent
        WHERE mi.spare_part = %s AND m.docstatus IN (0, 1)
        ORDER BY m.movement_date DESC
        LIMIT 20
    """, name, as_dict=True)
    _enrich_movement_warehouses(doc["recent_movements"])

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
        "stock_uom": data.get("stock_uom") or "Cái",
        "purchase_uom": data.get("purchase_uom") or "",
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
        "preferred_supplier", "unit_cost", "stock_uom", "purchase_uom", "min_stock_level",
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


_LOW_COND = (
    "COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0) > 0 "
    "AND s.qty_on_hand < COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)"
)


def _list_stock_low(warehouse: str, spare_part: str, offset: int, pg_size: int) -> tuple[list, int]:
    sql_p: dict = {}
    wh_cond = "AND s.warehouse = %(wh)s" if warehouse else ""
    sp_cond = "AND s.spare_part = %(sp)s" if spare_part else ""
    if warehouse:  sql_p["wh"] = warehouse
    if spare_part: sql_p["sp"] = spare_part

    total = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE {_LOW_COND} {wh_cond} {sp_cond}
    """, sql_p)[0][0]
    sql_p["off"] = offset
    sql_p["lim"] = pg_size
    rows = frappe.db.sql(f"""
        SELECT s.name, s.warehouse, s.spare_part, s.qty_on_hand,
               s.reserved_qty, s.available_qty, s.last_movement_date,
               s.min_stock_override,
               p.part_name, p.stock_uom AS uom, p.unit_cost, p.min_stock_level,
               p.is_critical,
               w.warehouse_code, w.warehouse_name,
               COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0) AS min_level
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
        WHERE {_LOW_COND} {wh_cond} {sp_cond}
        ORDER BY s.warehouse, p.part_name
        LIMIT %(off)s, %(lim)s
    """, sql_p, as_dict=True)
    for r in rows:
        r["is_low"] = True
        r["stock_value"] = float((r.get("qty_on_hand") or 0) * (r.get("unit_cost") or 0))
        r["is_critical"] = bool(r.get("is_critical"))
    return rows, total


def _list_stock_all(warehouse: str, spare_part: str, offset: int, pg_size: int) -> tuple[list, int]:
    filters: dict = {}
    if warehouse:  filters["warehouse"] = warehouse
    if spare_part: filters["spare_part"] = spare_part

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
    wh_map = {w["name"]: w for w in frappe.get_all(
        _DT_WH, filters={"name": ["in", wh_ids]},
        fields=["name", "warehouse_code", "warehouse_name"]
    )} if wh_ids else {}

    for r in rows:
        pm = part_map.get(r["spare_part"], {})
        min_level = r.get("min_stock_override") or pm.get("min_stock_level") or 0
        r["min_level"]      = min_level
        r["is_low"]         = bool(min_level and (r["qty_on_hand"] or 0) < min_level)
        r["unit_cost"]      = float(pm.get("unit_cost") or 0)
        r["stock_value"]    = float((r["qty_on_hand"] or 0) * (pm.get("unit_cost") or 0))
        r["is_critical"]    = bool(pm.get("is_critical"))
        wh = wh_map.get(r["warehouse"]) or {}
        r["warehouse_code"] = wh.get("warehouse_code") or r["warehouse"]
        r["warehouse_name"] = wh.get("warehouse_name") or r["warehouse"]
    return rows, total


@frappe.whitelist()
def list_stock_levels(page: int = 1, page_size: int = 50,
                      warehouse: str = "", spare_part: str = "",
                      low_only: int = 0) -> dict:
    page    = int(page)
    pg_size = int(page_size)
    offset  = (page - 1) * pg_size
    if int(low_only):
        rows, total = _list_stock_low(warehouse, spare_part, offset, pg_size)
    else:
        rows, total = _list_stock_all(warehouse, spare_part, offset, pg_size)
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

    _enrich_movement_warehouses(rows)
    return _ok({"items": rows, "pagination": {"page": page, "page_size": page_size, "total": total}})


def _enrich_movement_warehouses(rows: list) -> None:
    """Batch-enrich a list of movement rows with warehouse_code / warehouse_name."""
    wh_ids = {r.get(f) for r in rows for f in ("from_warehouse", "to_warehouse") if r.get(f)}
    if not wh_ids:
        return
    wh_map = {w.name: w for w in frappe.get_all(
        _DT_WH, filters={"name": ["in", list(wh_ids)]},
        fields=["name", "warehouse_code", "warehouse_name"],
    )}
    for r in rows:
        for field in ("from_warehouse", "to_warehouse"):
            wh = wh_map.get(r.get(field))
            r[f"{field}_code"] = wh.warehouse_code if wh else ""
            r[f"{field}_name"] = wh.warehouse_name if wh else ""


def _enrich_warehouse_fields(doc: dict) -> dict:
    _enrich_movement_warehouses([doc])
    return doc


@frappe.whitelist()
def get_stock_movement(name: str) -> dict:
    if not frappe.db.exists(_DT_MOV, name):
        return _err(_(_MSG_MOV_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_MOV, name).as_dict()
    return _ok(_enrich_warehouse_fields(doc))


@frappe.whitelist()
def search_reference_docs(reference_type: str, query: str = "", limit: int = 20) -> dict:
    """GET — Search linked documents for reference type picker in Stock Movement."""
    query = (query or "").strip()
    limit = min(int(limit), 50)
    like = f"%{query}%"

    if reference_type == "Asset Repair":
        rows = frappe.db.sql("""
            SELECT ar.name,
                   CONCAT(ar.name, ' — ', COALESCE(a.asset_name, ar.asset_ref)) AS label,
                   ar.repair_type AS description
            FROM `tabAsset Repair` ar
            LEFT JOIN `tabAC Asset` a ON a.name = ar.asset_ref
            WHERE ar.name LIKE %s OR a.asset_name LIKE %s
            ORDER BY ar.creation DESC
            LIMIT %s
        """, [like, like, limit], as_dict=True)
        return _ok(rows)

    if reference_type == "PM Work Order":
        rows = frappe.db.sql("""
            SELECT wo.name,
                   CONCAT(wo.name, ' — ', COALESCE(a.asset_name, wo.asset_ref)) AS label,
                   wo.status AS description
            FROM `tabPM Work Order` wo
            LEFT JOIN `tabAC Asset` a ON a.name = wo.asset_ref
            WHERE wo.name LIKE %s OR a.asset_name LIKE %s
            ORDER BY wo.creation DESC
            LIMIT %s
        """, [like, like, limit], as_dict=True)
        return _ok(rows)

    if reference_type == "AC Purchase":
        rows = frappe.db.sql("""
            SELECT p.name,
                   CONCAT(p.name, IF(p.invoice_no, CONCAT(' · ', p.invoice_no), '')) AS label,
                   CONCAT(COALESCE(s.supplier_name, p.supplier), ' — ', p.status) AS description
            FROM `tabAC Purchase` p
            LEFT JOIN `tabAC Supplier` s ON s.name = p.supplier
            WHERE p.docstatus = 1
              AND (p.name LIKE %s OR p.invoice_no LIKE %s OR s.supplier_name LIKE %s)
            ORDER BY p.purchase_date DESC
            LIMIT %s
        """, [like, like, like, limit], as_dict=True)
        return _ok(rows)

    return _err(_("Loại chứng từ không hỗ trợ tìm kiếm liên kết"), 400)


def _build_movement_item(i: dict) -> dict:
    """Build a movement item dict, resolving stock_qty via UOM conversion."""
    spare_part = i.get("spare_part") or ""
    qty = float(i.get("qty") or 0)
    uom = (i.get("uom") or "").strip()

    if i.get("stock_qty"):
        stock_qty = float(i["stock_qty"])
        cf = float(i.get("conversion_factor") or 1)
    elif spare_part and uom:
        stock_uom = uom_svc.get_stock_uom(spare_part)
        cf = uom_svc.get_conversion_factor(spare_part, uom, stock_uom) if uom != stock_uom else 1.0
        stock_qty = qty * cf
    else:
        cf = float(i.get("conversion_factor") or 1)
        stock_qty = qty * cf

    return {
        "spare_part": spare_part,
        "qty": qty,
        "uom": uom or None,
        "conversion_factor": cf,
        "stock_qty": stock_qty,
        "unit_cost": float(i.get("unit_cost") or 0),
        "serial_no": i.get("serial_no"),
        "notes": i.get("notes"),
    }


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
        "items": [_build_movement_item(i) for i in items],
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
def search_parts_autocomplete(q: str = "", limit: int = 10,
                              warehouse: str = "", show_stock_only: int = 0) -> dict:
    return _ok(svc.search_parts(
        q, limit=int(limit),
        warehouse=warehouse or None,
        show_stock_only=bool(int(show_stock_only)),
    ))


# ─── Warehouse detail & delete ────────────────────────────────────────────────

@frappe.whitelist()
def get_warehouse(name: str) -> dict:
    if not frappe.db.exists(_DT_WH, name):
        return _err(_(_MSG_WH_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_WH, name).as_dict()
    doc["stock_items"] = frappe.db.sql("""
        SELECT s.spare_part, p.part_name, p.part_code, p.stock_uom AS uom,
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
            doc.append("items", _build_movement_item(i))

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


# ─────────────────────────────────────────────────────────────────────────────
# UOM ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_uom_info(spare_part: str) -> dict:
    """GET — Trả về stock_uom, purchase_uom và bảng quy đổi của phụ tùng."""
    try:
        return _ok(uom_svc.get_spare_part_uom_info(spare_part))
    except Exception as e:
        return _err(str(e), 400)


@frappe.whitelist()
def convert_qty(spare_part: str, qty: float, from_uom: str, to_uom: str) -> dict:
    """GET — Quy đổi số lượng giữa 2 đơn vị cho 1 phụ tùng."""
    try:
        result = uom_svc.convert_qty(spare_part, float(qty), from_uom, to_uom)
        factor = uom_svc.get_conversion_factor(spare_part, from_uom, to_uom)
        return _ok({
            "spare_part": spare_part,
            "from_qty": float(qty),
            "from_uom": from_uom,
            "to_qty": result,
            "to_uom": to_uom,
            "factor": factor,
        })
    except uom_svc.UOMConversionNotFound as e:
        return _err(str(e), 404)
    except Exception as e:
        return _err(str(e), 400)


@frappe.whitelist()
def list_parts_uom(search: str = "", limit: int = 200) -> dict:
    """GET — Danh sách phụ tùng kèm stock_uom và purchase_uom (cho UOM management view)."""
    filters: list = [["is_active", "=", 1]]
    if search:
        filters.append(["part_name", "like", f"%{search}%"])
    items = frappe.get_all(
        _DT_PART,
        filters=filters,
        fields=["name", "part_code", "part_name", "stock_uom", "purchase_uom"],
        limit=int(limit),
        order_by="part_name asc",
    )
    return _ok({"items": items})


@frappe.whitelist()
def list_uoms(search: str = "", limit: int = 30) -> dict:
    """GET — Tìm kiếm AC UOM (dùng cho SmartSelect)."""
    filters: dict = {"is_active": 1}
    if search:
        filters["uom_name"] = ["like", f"%{search}%"]
    items = frappe.get_all(
        "AC UOM",
        filters=filters,
        fields=["name as value", "uom_name as label", "symbol", "must_be_whole_number"],
        limit=int(limit),
        order_by="uom_name asc",
    )
    return _ok({"items": items, "total": len(items)})


@frappe.whitelist(methods=["POST"])
def seed_ac_uoms() -> dict:
    """POST — Tạo AC UOM y tế chuẩn Việt Nam nếu chưa có."""
    created = uom_svc.seed_ac_uoms()
    return _ok({"created": created, "count": len(created)})


# ─── AC UOM master CRUD ──────────────────────────────────────────────────────

_DT_UOM = "AC UOM"
_MSG_UOM_NOT_FOUND = "Không tìm thấy đơn vị tính"


@frappe.whitelist()
def list_uoms_full(search: str = "", active_only: int = 0, limit: int = 200) -> dict:
    """GET — Full list AC UOM với use_count (số lần được dùng ở spare parts)."""
    filters: dict = {}
    if int(active_only):
        filters["is_active"] = 1
    if search:
        filters["uom_name"] = ["like", f"%{search}%"]
    items = frappe.get_all(
        _DT_UOM, filters=filters,
        fields=["name", "uom_name", "symbol", "must_be_whole_number",
                "is_active", "description"],
        order_by="uom_name asc", limit=int(limit),
    )
    if items:
        names = [i["name"] for i in items]
        counts = {r[0]: int(r[1]) for r in frappe.db.sql("""
            SELECT uom_name, cnt FROM (
              SELECT stock_uom AS uom_name, COUNT(*) AS cnt
              FROM `tabAC Spare Part` WHERE stock_uom IN %(names)s GROUP BY stock_uom
              UNION ALL
              SELECT purchase_uom, COUNT(*) FROM `tabAC Spare Part`
              WHERE purchase_uom IN %(names)s GROUP BY purchase_uom
            ) t GROUP BY uom_name
        """, {"names": names})}
        for i in items:
            i["use_count"] = counts.get(i["name"], 0)
    return _ok({"items": items, "total": len(items)})


@frappe.whitelist()
def get_uom(name: str) -> dict:
    if not frappe.db.exists(_DT_UOM, name):
        return _err(_(_MSG_UOM_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_UOM, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_uom() -> dict:
    data = frappe.local.form_dict
    uom_name = (data.get("uom_name") or "").strip()
    if not uom_name:
        return _err(_("Tên đơn vị tính là bắt buộc"), 400)
    if frappe.db.exists(_DT_UOM, uom_name):
        return _err(_("Đơn vị '{0}' đã tồn tại").format(uom_name), 409)
    try:
        doc = frappe.get_doc({
            "doctype":               _DT_UOM,
            "uom_name":              uom_name,
            "symbol":                data.get("symbol") or "",
            "must_be_whole_number":  int(data.get("must_be_whole_number") or 0),
            "is_active":             int(data.get("is_active", 1)),
            "description":           data.get("description") or "",
        })
        doc.insert()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 400)


@frappe.whitelist(methods=["POST"])
def update_uom(name: str) -> dict:
    if not frappe.db.exists(_DT_UOM, name):
        return _err(_(_MSG_UOM_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_UOM, name)
    data = frappe.local.form_dict
    for k in ("symbol", "description"):
        v = data.get(k)
        if v is not None:
            setattr(doc, k, v)
    for k in ("must_be_whole_number", "is_active"):
        if k in data:
            setattr(doc, k, int(data.get(k) or 0))
    doc.save()
    return _ok({"name": doc.name})


_UOM_LINK_TABLES = [
    (_DT_PART,                   "stock_uom"),
    (_DT_PART,                   "purchase_uom"),
    ("AC Purchase Item",         "uom"),
    ("AC Stock Movement Item",   "uom"),
    ("AC Spare Part Stock",      "uom"),
    ("AC Asset",                 "uom"),
    ("Spare Parts Used",         "uom"),
    ("IMM Device Spare Part",    "uom"),
    ("AC UOM Conversion",        "uom"),
]


def _count_uom_references(uom_name: str) -> dict[str, int]:
    """Đếm usage của 1 UOM ở tất cả bảng tham chiếu. Trả dict {doctype.field: count}."""
    counts: dict[str, int] = {}
    for dt, field in _UOM_LINK_TABLES:
        try:
            n = frappe.db.count(dt, {field: uom_name})
            if n:
                counts[f"{dt}.{field}"] = int(n)
        except Exception:
            pass
    return counts


@frappe.whitelist(methods=["POST"])
def delete_uom(name: str) -> dict:
    """Soft-delete (is_active=0) nếu đang được tham chiếu; hard-delete nếu không.

    Quét 9 bảng tham chiếu AC UOM. Nếu có bất kỳ ref nào → soft-delete (set is_active=0).
    Nếu `frappe.delete_doc` vẫn raise `LinkExistsError` (trường hợp edge), fall back soft-delete.
    """
    if not frappe.db.exists(_DT_UOM, name):
        return _err(_(_MSG_UOM_NOT_FOUND), 404)

    refs = _count_uom_references(name)
    if refs:
        frappe.db.set_value(_DT_UOM, name, "is_active", 0)
        reason = ", ".join(f"{k}={v}" for k, v in refs.items())
        return _ok({
            "name": name, "soft_deleted": True,
            "reason": f"Đang dùng: {reason}",
            "references": refs,
        })

    try:
        frappe.delete_doc(_DT_UOM, name)
        return _ok({"name": name, "deleted": True})
    except frappe.LinkExistsError as e:
        frappe.db.set_value(_DT_UOM, name, "is_active", 0)
        return _ok({
            "name": name, "soft_deleted": True,
            "reason": f"Không thể xóa cứng ({str(e)[:100]}), đã deactivate",
        })


# ─── Part UOM assignment ─────────────────────────────────────────────────────

@frappe.whitelist()
def list_parts_missing_uom(limit: int = 500) -> dict:
    """GET — Phụ tùng đang thiếu stock_uom (cần gán để dùng được trong stock)."""
    items = frappe.get_all(
        _DT_PART,
        filters=[["is_active", "=", 1],
                 ["stock_uom", "in", [None, ""]]],
        fields=["name", "part_code", "part_name", "manufacturer",
                "manufacturer_part_no", "part_category"],
        limit=int(limit),
        order_by="part_name asc",
    )
    return _ok({"items": items, "total": len(items)})


@frappe.whitelist(methods=["POST"])
def update_part_uom(spare_part: str, stock_uom: str = "", purchase_uom: str = "") -> dict:
    """POST — Cập nhật stock_uom / purchase_uom cho 1 spare part."""
    if not frappe.db.exists(_DT_PART, spare_part):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    if stock_uom and not frappe.db.exists(_DT_UOM, stock_uom):
        return _err(_("stock_uom '{0}' không tồn tại trong AC UOM").format(stock_uom), 400)
    if purchase_uom and not frappe.db.exists(_DT_UOM, purchase_uom):
        return _err(_("purchase_uom '{0}' không tồn tại").format(purchase_uom), 400)

    updates: dict = {}
    if stock_uom:
        updates["stock_uom"] = stock_uom
    if purchase_uom is not None:
        updates["purchase_uom"] = purchase_uom or None

    if updates:
        frappe.db.set_value(_DT_PART, spare_part, updates, update_modified=True)
    return _ok({"name": spare_part, **updates})


@frappe.whitelist(methods=["POST"])
def bulk_assign_default_uom(default_uom: str = "Cái") -> dict:
    """POST — Gán default stock_uom cho toàn bộ phụ tùng đang thiếu."""
    if not frappe.db.exists(_DT_UOM, default_uom):
        return _err(_("UOM default '{0}' không tồn tại").format(default_uom), 400)
    affected = frappe.db.sql("""
        SELECT name FROM `tabAC Spare Part`
        WHERE is_active = 1 AND (stock_uom IS NULL OR stock_uom = '')
    """, as_dict=True)
    for p in affected:
        frappe.db.set_value(_DT_PART, p["name"], "stock_uom", default_uom, update_modified=False)
    frappe.db.commit()
    return _ok({"default_uom": default_uom, "assigned": len(affected)})


# ─── Per-part conversions ────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def upsert_uom_conversion(spare_part: str, uom: str, conversion_factor: float,
                            is_purchase_uom: int = 0, is_issue_uom: int = 0) -> dict:
    """POST — Thêm/sửa 1 dòng conversion trên AC Spare Part.uom_conversions."""
    if not frappe.db.exists(_DT_PART, spare_part):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    if not frappe.db.exists(_DT_UOM, uom):
        return _err(_("UOM '{0}' không tồn tại").format(uom), 400)
    factor = float(conversion_factor or 0)
    if factor <= 0:
        return _err(_("Hệ số quy đổi phải > 0"), 400)

    doc = frappe.get_doc(_DT_PART, spare_part)
    if uom == doc.stock_uom:
        return _err(_("Không thêm quy đổi cho chính stock_uom (hệ số mặc định = 1)"), 400)

    existing = next((r for r in (doc.uom_conversions or []) if r.uom == uom), None)
    if existing:
        existing.conversion_factor = factor
        existing.is_purchase_uom = int(is_purchase_uom or 0)
        existing.is_issue_uom = int(is_issue_uom or 0)
    else:
        doc.append("uom_conversions", {
            "uom": uom, "conversion_factor": factor,
            "is_purchase_uom": int(is_purchase_uom or 0),
            "is_issue_uom": int(is_issue_uom or 0),
        })
    doc.save(ignore_permissions=True)
    return _ok({"spare_part": spare_part, "uom": uom, "conversion_factor": factor})


@frappe.whitelist(methods=["POST"])
def remove_uom_conversion(spare_part: str, uom: str) -> dict:
    """POST — Xóa 1 dòng conversion."""
    if not frappe.db.exists(_DT_PART, spare_part):
        return _err(_(_MSG_PART_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_PART, spare_part)
    before = len(doc.uom_conversions or [])
    doc.uom_conversions = [r for r in (doc.uom_conversions or []) if r.uom != uom]
    if len(doc.uom_conversions) == before:
        return _err(_("Không tìm thấy quy đổi '{0}'").format(uom), 404)
    doc.save(ignore_permissions=True)
    return _ok({"spare_part": spare_part, "removed": uom})
