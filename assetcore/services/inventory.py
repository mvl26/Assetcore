# Copyright (c) 2026, AssetCore Team
# IMM-00 Inventory Sub-Domain — stock math & movement application
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime
from assetcore.services.purchase import _DT_PUR

_DT_STOCK   = "AC Spare Part Stock"
_DT_PART    = "AC Spare Part"
_DT_WH      = "AC Warehouse"


# ─── Canonical low-stock predicate (SINGLE SOURCE OF TRUTH) ───────────────────
# R7 §9.4.5 / BUG-15-03 — Mọi nơi đếm/liệt kê "dưới định mức" trong toàn hệ thống
# (KPI imm15, dashboard /inventory, danh sách /stock, drill, scheduler email kho)
# PHẢI dùng CHUNG fragment này. KHÔNG nhân bản SQL.
#
# 🔧 Self-Correction (vòng 23, BR-15-17 / VR-15-17 — 04 §II.A): "dưới định mức / cần
# đặt lại" so theo tồn KHẢ DỤNG (qty_on_hand − reserved_qty), KHÔNG phải tồn vật lý.
# Lý do: bin reserved-full (on_hand=100, reserved=100 ⟹ available=0) với min=20 thoả
# 100 ≥ 20 ⟹ predicate cũ KHÔNG flag low ⟹ dashboard báo "đủ tồn" dù 0 đơn vị cấp
# phát được → trễ sửa thiết bị (R-15-04). Đảo quyết định round-3.
#
#   effective_min(bin)  = COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)
#   available_for_min   = (s.qty_on_hand − COALESCE(s.reserved_qty, 0))   -- RAW, KHÔNG clamp
#   low(bin)            ⟺ effective_min > 0 AND available_for_min < effective_min
#
# Biểu thức RAW (KHÔNG cột stored `available_qty` đã MAX(0,…) clamp) để bắt cả oversell
# (reserved > on_hand ⟹ raw < 0 < effective_min ⟹ vẫn low). Đối chứng: bin reserved=0
# GIỮ NGUYÊN hành vi cũ (available raw == qty_on_hand) → KHÔNG false-positive.
#
# Đánh giá PER-BIN (mỗi spare_part × warehouse) — KHÔNG SUM-toàn-kho (sẽ che bin
# riêng lẻ dưới định mức / dưới min_stock_override). Yêu cầu alias bảng:
#   s = `tabAC Spare Part Stock`, p = `tabAC Spare Part`.
EFFECTIVE_MIN_EXPR = "COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)"

# Tồn KHẢ DỤNG (raw — KHÔNG clamp) dùng trong predicate + ORDER BY "thiếu nhiều nhất".
AVAILABLE_FOR_MIN_EXPR = "(s.qty_on_hand - COALESCE(s.reserved_qty, 0))"

LOW_STOCK_COND = (
    f"p.is_active = 1 "
    f"AND {EFFECTIVE_MIN_EXPR} > 0 "
    f"AND {AVAILABLE_FOR_MIN_EXPR} < {EFFECTIVE_MIN_EXPR}"
)


def count_low_stock_bins(warehouse: str = "") -> int:
    """Canonical: số bin (spare_part × kho) dưới định mức theo effective_min."""
    cond = " AND s.warehouse = %(wh)s" if warehouse else ""
    row = frappe.db.sql(
        f"""SELECT COUNT(*)
            FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE {LOW_STOCK_COND}{cond}""",
        {"wh": warehouse} if warehouse else {},
    )
    return int((row or [[0]])[0][0])


def low_stock_part_ids() -> list[str]:
    """Canonical: part-distinct của các bin dưới định mức (drill từ KPI low_stock)."""
    rows = frappe.db.sql(
        f"""SELECT DISTINCT s.spare_part
            FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE {LOW_STOCK_COND}""")
    return [r[0] for r in rows]


# ─── Stock querying ──────────────────────────────────────────────────────────

def get_stock_row(warehouse: str, spare_part: str) -> dict | None:
    key = f"{warehouse}::{spare_part}"
    return frappe.db.get_value(
        _DT_STOCK, key,
        ["name", "qty_on_hand", "reserved_qty", "available_qty"],
        as_dict=True,
    ) or None


def get_available_qty(warehouse: str, spare_part: str) -> float:
    row = get_stock_row(warehouse, spare_part)
    if not row:
        return 0.0
    return float(row.get("available_qty") or 0)


def get_total_stock(spare_part: str) -> float:
    """Tổng tồn của 1 phụ tùng qua tất cả kho."""
    return float(frappe.db.sql("""
        SELECT COALESCE(SUM(qty_on_hand), 0)
        FROM `tabAC Spare Part Stock`
        WHERE spare_part = %s
    """, spare_part)[0][0] or 0)


# ─── Soft-reservation ledger (SoT) ───────────────────────────────────────────
# IMM-15 §III-bis / VR-15-14 — reserved_qty is the SINGLE-SOURCE-OF-TRUTH writer.
#
# INVARIANT (per bin = warehouse × spare_part):
#   reserved_qty(bin)  = Σ held qty of EVERY IMM Spare Allocation line whose parent
#                        allocation_status ∈ RESERVING_STATES (holding, not yet issued)
#   available_qty(bin) = MAX(0, qty_on_hand − reserved_qty)   # before_save clamp
#
# held qty of a line = COALESCE(NULLIF(qty_approved, 0), qty_requested) — once the
# approver adjusts qty_approved the hold tracks the approved amount; before approval
# (qty_approved=0) it holds the requested amount.
#
# RELEASE on terminal: Issued / Returned / Cancelled leave RESERVING_STATES → the
# line's hold drops out of the sum, so reserved_qty falls accordingly. Issue ALSO
# subtracts qty_on_hand (real movement) — recompute runs AFTER so the same qty is
# never double-counted (subtracted from on-hand AND held as reserved).
#
# RULE-R01: reserved_qty is written ONLY here. NO inline `reserved_qty +=/-=` anywhere
# in imm15.py — every allocation transition calls this one function.
RESERVING_STATES = frozenset({"Requested", "Approved", "Picked"})

# Alias kept for the doc's §III-bis.2 naming; both refer to the same SoT set.
_HOLDING_ALLOCATION_STATES = RESERVING_STATES


def recompute_reserved(warehouse: str, spare_part: str) -> float:
    """SoT: recompute reserved_qty for one bin (warehouse × spare_part).

    INVARIANT: reserved_qty == Σ COALESCE(NULLIF(qty_approved,0), qty_requested) over
    every IMM Spare Allocation Item whose parent allocation has
    warehouse_from = ``warehouse``, spare_part = ``spare_part`` and
    allocation_status ∈ :data:`RESERVING_STATES` (Requested / Approved / Picked).

    Absolute & idempotent — recomputed straight from the DB (NOT a running delta), so
    a crash mid-transition self-heals on the next call. Writes reserved_qty onto
    ``AC Spare Part Stock`` (creating the bin with qty_on_hand=0 if it is missing);
    ``before_save`` then derives available_qty = MAX(0, qty_on_hand − reserved_qty).

    The bin row is locked ``FOR UPDATE`` while summing so two concurrent issues cannot
    both read a stale availability and oversell (anti-oversell, §III-bis.4/.5).

    Args:
        warehouse:  AC Warehouse name (allocation.warehouse_from).
        spare_part: AC Spare Part name.

    Returns:
        float: the freshly-written reserved_qty for the bin.
    """
    key = f"{warehouse}::{spare_part}"

    # Lock the bin row (or create it) before summing so concurrent transitions on the
    # same bin serialize — neither reads a stale available_qty.
    if frappe.db.exists(_DT_STOCK, key):
        frappe.db.sql(
            f"SELECT name FROM `tab{_DT_STOCK}` WHERE name = %s FOR UPDATE", key
        )

    reserved = float(frappe.db.sql(
        f"""SELECT COALESCE(SUM(COALESCE(NULLIF(i.qty_approved, 0), i.qty_requested)), 0)
            FROM `tabIMM Spare Allocation Item` i
            JOIN `tabIMM Spare Allocation` a ON a.name = i.parent
            WHERE a.warehouse_from = %(wh)s
              AND i.spare_part = %(sp)s
              AND a.allocation_status IN %(states)s""",
        {"wh": warehouse, "sp": spare_part,
         "states": tuple(RESERVING_STATES)},
    )[0][0] or 0)

    if frappe.db.exists(_DT_STOCK, key):
        doc = frappe.get_doc(_DT_STOCK, key)
        doc.reserved_qty = reserved
        doc.save(ignore_permissions=True)
    else:
        # Bin not seeded yet (no movement) but an allocation already holds it.
        doc = frappe.get_doc({
            "doctype": _DT_STOCK,
            "warehouse": warehouse,
            "spare_part": spare_part,
            "qty_on_hand": 0,
            "reserved_qty": reserved,
        })
        doc.insert(ignore_permissions=True)

    return reserved


# ─── Upsert helper ───────────────────────────────────────────────────────────

def _upsert_stock(warehouse: str, spare_part: str, delta: float, *, touch_dt=None) -> None:
    key = f"{warehouse}::{spare_part}"
    touch_dt = touch_dt or now_datetime()

    if frappe.db.exists(_DT_STOCK, key):
        doc = frappe.get_doc(_DT_STOCK, key)
        doc.qty_on_hand = float(doc.qty_on_hand or 0) + float(delta)
        doc.last_movement_date = touch_dt
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": _DT_STOCK,
            "warehouse": warehouse,
            "spare_part": spare_part,
            "qty_on_hand": float(delta),
            "reserved_qty": 0,
            "last_movement_date": touch_dt,
        })
        doc.insert(ignore_permissions=True)


# ─── Stock Movement hooks ────────────────────────────────────────────────────

_REF_DOCTYPE_MAP = {
    "Asset Repair": "Asset Repair",
    "PM Work Order": "PM Work Order",
    _DT_PUR: _DT_PUR,
}


def validate_stock_movement(doc) -> None:
    """Validate business rules before submit (BR-INV-07, BR-INV-08)."""
    ref_type = doc.get("reference_type") or ""
    ref_name = (doc.get("reference_name") or "").strip()

    # BR-INV-08: For linked doc types, verify the referenced document exists
    if ref_type in _REF_DOCTYPE_MAP and ref_name:
        dt = _REF_DOCTYPE_MAP[ref_type]
        if not frappe.db.exists(dt, ref_name):
            frappe.throw(_("Chứng từ {0} '{1}' không tồn tại").format(ref_type, ref_name))

    # BR-INV-07: Manual and Adjustment require notes
    if ref_type == "Manual" or doc.get("movement_type") == "Adjustment":
        if not (doc.get("notes") or "").strip():
            frappe.throw(_("Phiếu Manual / Điều chỉnh bắt buộc phải có Ghi chú (lý do)"))

    # Slide 27: Phiếu Xuất kho bắt buộc có Khoa/Phòng nhận
    if doc.get("movement_type") == "Issue":
        if not (doc.get("receiver_department") or "").strip():
            frappe.throw(_("Phiếu Xuất kho bắt buộc phải chỉ định Khoa/Phòng nhận"))

    # Slide 18: Khi phiếu Nhập kho tham chiếu PO, validate với procurement (IMM-03)
    if doc.get("movement_type") == "Receipt" and ref_type == _DT_PUR and ref_name:
        _validate_receipt_against_po(ref_name, doc)


def _validate_receipt_against_po(po_name: str, doc) -> None:
    """Slide 18: gọi validator procurement (IMM-03) cho phiếu Nhập kho theo PO.

    Validator do agent IMM-03 cung cấp. Import lazy; nếu chưa có
    (ImportError/AttributeError) → log TODO warning thay vì crash.
    """
    try:
        from assetcore.services.imm03 import validate_receipt_against_po
    except (ImportError, AttributeError):
        frappe.log_error(
            message=f"TODO[Slide18]: assetcore.services.imm03.validate_receipt_against_po "
                    f"chưa khả dụng — bỏ qua kiểm tra PO {po_name} cho phiếu {doc.get('name')}",
            title="Stock Receipt PO validation skipped",
        )
        return
    received_items = [
        {"spare_part": r.spare_part,
         "qty": float(r.stock_qty or 0) or float(r.qty or 0)}
        for r in (doc.items or [])
    ]
    try:
        validate_receipt_against_po(po_name, received_items)
    except (ImportError, AttributeError):
        frappe.log_error(
            message=f"TODO[Slide18]: validate_receipt_against_po lỗi import/attr cho PO {po_name}",
            title="Stock Receipt PO validation skipped",
        )


def apply_stock_movement(doc) -> None:
    """Apply a submitted AC Stock Movement to AC Spare Part Stock.

    Dùng stock_qty (= qty * conversion_factor, đã quy về stock UOM) nếu có.
    Fallback về qty khi conversion_factor = 1 hoặc chưa điền.
    """
    validate_stock_movement(doc)
    t = doc.movement_type
    for row in doc.items:
        stock_qty = float(row.stock_qty or 0) or float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, +stock_qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, +stock_qty)
        elif t == "Adjustment":
            _upsert_stock(doc.from_warehouse, row.spare_part, stock_qty)


def reverse_stock_movement(doc) -> None:
    """Reverse a previously-applied movement (cancel)."""
    t = doc.movement_type
    for row in doc.items:
        stock_qty = float(row.stock_qty or 0) or float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, -stock_qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, +stock_qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, +stock_qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, -stock_qty)
        elif t == "Adjustment":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)


# ─── Overview / KPIs ─────────────────────────────────────────────────────────

def get_stock_overview() -> dict:
    total_parts     = frappe.db.count(_DT_PART, {"is_active": 1})
    total_warehouses = frappe.db.count(_DT_WH, {"is_active": 1})

    total_value = frappe.db.sql("""
        SELECT COALESCE(SUM(s.qty_on_hand * p.unit_cost), 0)
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
    """)[0][0] or 0

    # Per-warehouse-bin low-stock evaluation via the canonical predicate
    # (LOW_STOCK_COND / EFFECTIVE_MIN_EXPR) — MUST match the stock-level page,
    # IMM-15 KPI, drill and scheduler. Each spare-part × warehouse bin is
    # compared against its effective minimum (per-bin override falls back to
    # the part-level min). SUM(qty_on_hand) across warehouses is intentionally
    # NOT used: it hides bins individually below their effective min.
    low_stock = frappe.db.sql(f"""
        SELECT s.name AS bin, s.spare_part, p.part_name, s.warehouse,
               s.qty_on_hand AS total_qty,
               {EFFECTIVE_MIN_EXPR} AS min_stock_level
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE {LOW_STOCK_COND}
        ORDER BY ({EFFECTIVE_MIN_EXPR} - {AVAILABLE_FOR_MIN_EXPR}) DESC
        LIMIT 10
    """, as_dict=True)

    # The full per-bin low-stock count (the dashboard KPI must reflect every
    # flagged bin, not just the 10 shown in the list widget).
    low_stock_count = count_low_stock_bins()

    if low_stock:
        wh_ids = list({r["warehouse"] for r in low_stock if r.get("warehouse")})
        wh_map = {w["name"]: w for w in frappe.get_all(
            _DT_WH, filters={"name": ["in", wh_ids]},
            fields=["name", "warehouse_code", "warehouse_name"],
        )} if wh_ids else {}
        for r in low_stock:
            wh = wh_map.get(r.get("warehouse")) or {}
            r["warehouse_code"] = wh.get("warehouse_code") or r.get("warehouse")
            r["warehouse_name"] = wh.get("warehouse_name") or r.get("warehouse")

    movement_30d = frappe.db.sql("""
        SELECT movement_type, COUNT(*) AS cnt
        FROM `tabAC Stock Movement`
        WHERE docstatus = 1 AND movement_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY movement_type
    """, as_dict=True)

    return {
        "total_parts":      total_parts,
        "total_warehouses": total_warehouses,
        "total_value":      float(total_value),
        "low_stock_count":  int(low_stock_count),
        "low_stock_items":  low_stock,
        "movement_30d":     {m["movement_type"]: m["cnt"] for m in movement_30d},
    }


# ─── Search (replacement for imm09.search_spare_parts) ───────────────────────

def search_parts(
    query: str, *, limit: int = 10,
    warehouse: str | None = None, show_stock_only: bool = False,
) -> list[dict]:
    if not query or len(query) < 2:
        return []

    q_param = f"%{query}%"
    name_filter = "(p.part_name LIKE %(q)s OR p.part_code LIKE %(q)s OR p.manufacturer_part_no LIKE %(q)s)"

    if warehouse:
        # Show stock levels for the given warehouse; optionally restrict to parts with stock
        stock_cond = "AND COALESCE(s.available_qty, 0) > 0" if show_stock_only else ""
        rows = frappe.db.sql(f"""
            SELECT p.name, p.name AS spare_part, p.part_code, p.part_name, p.manufacturer_part_no,
                   p.unit_cost, p.stock_uom, p.purchase_uom,
                   COALESCE(s.qty_on_hand, 0)  AS qty_on_hand,
                   COALESCE(s.available_qty, 0) AS available_qty
            FROM `tabAC Spare Part` p
            LEFT JOIN `tabAC Spare Part Stock` s
                   ON s.spare_part = p.name AND s.warehouse = %(wh)s
            WHERE p.is_active = 1 AND {name_filter} {stock_cond}
            ORDER BY p.part_name ASC
            LIMIT %(lim)s
        """, {"q": q_param, "lim": int(limit), "wh": warehouse}, as_dict=True)
    else:
        rows = frappe.db.sql(f"""
            SELECT p.name, p.name AS spare_part, p.part_code, p.part_name, p.manufacturer_part_no,
                   p.unit_cost, p.stock_uom, p.purchase_uom,
                   NULL AS qty_on_hand, NULL AS available_qty
            FROM `tabAC Spare Part` p
            WHERE p.is_active = 1 AND {name_filter}
            ORDER BY p.part_name ASC
            LIMIT %(lim)s
        """, {"q": q_param, "lim": int(limit)}, as_dict=True)

    return rows


# ─── Scheduler: low-stock alert ──────────────────────────────────────────────

def check_low_stock() -> None:
    """Daily scheduler: email kho phụ tùng (Inventory Manager) về các BIN dưới định mức.

    R7 §9.4.5 / BUG-15-03: đánh giá PER-BIN qua canonical predicate
    (LOW_STOCK_COND / effective_min = override-per-bin fallback part-min).
    Trước đây SUM(qty_on_hand) GROUP BY part → che bin riêng lẻ dưới định mức
    (đặc biệt bin có min_stock_override cao) → email thiếu cảnh báo. Nay mỗi bin
    low xuất hiện riêng, định mức hiển thị = effective_min.

    R21: dùng SSoT notify_roles.STOREKEEPER (role THẬT, persona-role cũ không có).
    """
    from assetcore.utils.email import get_role_emails, safe_sendmail
    from assetcore.services.shared import notify_roles
    low = frappe.db.sql(f"""
        SELECT p.part_code, p.part_name, s.warehouse, s.qty_on_hand AS qty,
               {EFFECTIVE_MIN_EXPR} AS effective_min
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE {LOW_STOCK_COND}
        ORDER BY ({EFFECTIVE_MIN_EXPR} - {AVAILABLE_FOR_MIN_EXPR}) DESC
    """, as_dict=True)

    if not low:
        return

    emails = get_role_emails(list(notify_roles.STOREKEEPER))
    if not emails:
        return

    wh_names = {
        w["name"]: (w.get("warehouse_name") or w["name"])
        for w in frappe.get_all(
            _DT_WH, filters={"name": ["in", list({r.warehouse for r in low})]},
            fields=["name", "warehouse_name"])
    }
    lines = [
        f"- {r.part_code or r.part_name} · {r.part_name} @ "
        f"{wh_names.get(r.warehouse, r.warehouse)}: tồn {r.qty} / định mức {r.effective_min}"
        for r in low
    ]
    safe_sendmail(
        recipients=emails,
        subject=_("⚠️ Cảnh báo tồn kho thấp — {0} điểm tồn").format(len(low)),
        message=_("Các điểm tồn (phụ tùng × kho) sau đang dưới định mức:\n\n") + "\n".join(lines),
    )
