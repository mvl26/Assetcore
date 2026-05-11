# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory Tracking — Service Layer.
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, nowdate

from assetcore.repositories.allocation_repo import (
    AllocationRepo,
    CriticalWatchlistRepo,
    CycleCountRepo,
)
from assetcore.services.shared import ErrorCode, Roles, ServiceError, normalize_filters
from assetcore.utils.lifecycle import log_audit_event


# ─── Status constants ────────────────────────────────────────────────────────

class AllocationStatus:
    REQUESTED = "Requested"
    APPROVED = "Approved"
    PICKED = "Picked"
    ISSUED = "Issued"
    RETURNED = "Returned"
    CANCELLED = "Cancelled"

    OPEN = (REQUESTED, APPROVED, PICKED)


class CycleCountStatus:
    PLANNED = "Planned"
    COUNTING = "Counting"
    REVIEWED = "Reviewed"
    POSTED = "Posted"


# ─── Spare Allocation ─────────────────────────────────────────────────────────

def list_allocations(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    """Liệt kê phiếu cấp phát phụ tùng."""
    rows, pg = AllocationRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "work_order_ref", "asset", "warehouse_from",
                "requested_by", "requested_date", "urgency",
                "allocation_status", "total_value"],
        order_by="requested_date desc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def create_allocation(work_order_ref: str, items: list[dict],
                      asset: str = "", warehouse: str = "",
                      urgency: str = "Routine") -> dict:
    """Tạo phiếu cấp phát phụ tùng mới."""
    _require_storekeeper_or_tech()
    if not items:
        raise ServiceError(ErrorCode.VALIDATION, "Phiếu cấp phát phải có ít nhất 1 dòng phụ tùng")
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải chọn kho xuất")

    # VR-15-13: warehouse active
    wh_active = frappe.db.get_value("AC Warehouse", warehouse, "is_active")
    if wh_active == 0:
        raise ServiceError(ErrorCode.VALIDATION, f"Kho {warehouse} không còn hoạt động")

    doc = frappe.get_doc({
        "doctype": AllocationRepo.DOCTYPE,
        "work_order_ref": work_order_ref,
        "asset": asset,
        "warehouse_from": warehouse,
        "requested_by": frappe.session.user,
        "requested_date": nowdate(),
        "required_date": add_days(nowdate(), 3),
        "urgency": urgency,
        "allocation_status": AllocationStatus.REQUESTED,
        "items": items,
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    _write_allocation_audit(doc.name, "CREATED", {})
    frappe.db.commit()
    return {"name": doc.name, "allocation_status": AllocationStatus.REQUESTED}


def issue_allocation(allocation_name: str) -> dict:
    """Xuất kho — tạo AC Stock Movement và cập nhật trạng thái."""
    _require_storekeeper()
    doc = AllocationRepo.get(allocation_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy phiếu cấp phát: {allocation_name}")
    if doc.allocation_status not in (AllocationStatus.APPROVED, AllocationStatus.REQUESTED):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể xuất kho ở trạng thái: {doc.allocation_status}")

    # Validate stock for each item
    for item in doc.items:
        from assetcore.services.inventory import get_available_qty
        avail = get_available_qty(doc.warehouse_from, item.spare_part)
        qty_needed = float(item.qty_requested or 0)
        is_emergency = doc.urgency == "Emergency"
        if not is_emergency and avail < qty_needed:
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                f"Tồn kho không đủ cho {item.spare_part}: cần {qty_needed}, có {avail}",
            )
        item.qty_issued = min(qty_needed, avail) if not is_emergency else qty_needed

    # Create AC Stock Movement
    sm = _create_stock_movement_for_issue(doc)
    doc.stock_movement_ref = sm.name
    doc.allocation_status = AllocationStatus.ISSUED

    # Compute total value
    doc.total_value = sum(
        float(item.qty_issued or 0) * float(item.unit_value or 0)
        for item in doc.items
    )
    AllocationRepo.save(doc)
    _write_allocation_audit(allocation_name, "ISSUED",
                             {"stock_movement": sm.name})
    frappe.db.commit()
    return {"name": allocation_name, "allocation_status": AllocationStatus.ISSUED,
            "stock_movement_ref": sm.name}


def return_allocation(allocation_name: str, return_items: list[dict]) -> dict:
    """Trả phụ tùng — tạo AC Stock Movement Receipt."""
    _require_storekeeper()
    doc = AllocationRepo.get(allocation_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy phiếu cấp phát: {allocation_name}")
    if doc.allocation_status != AllocationStatus.ISSUED:
        raise ServiceError(ErrorCode.BAD_STATE,
                           "Chỉ có thể trả phụ tùng khi phiếu đã ở trạng thái Issued")

    # VR-15-08: qty_returned <= qty_issued
    issued_map = {item.spare_part: float(item.qty_issued or 0) for item in doc.items}
    for ri in return_items:
        sp = ri.get("spare_part")
        qty_ret = float(ri.get("qty_returned", 0))
        if qty_ret > issued_map.get(sp, 0):
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"Số lượng trả {qty_ret} > số đã xuất {issued_map.get(sp, 0)} cho {sp}",
            )
        for item in doc.items:
            if item.spare_part == sp:
                item.qty_returned = qty_ret

    sm = _create_stock_movement_for_return(doc, return_items)
    doc.stock_movement_return_ref = sm.name
    doc.allocation_status = AllocationStatus.RETURNED
    AllocationRepo.save(doc)
    _write_allocation_audit(allocation_name, "RETURNED",
                             {"stock_movement": sm.name})
    frappe.db.commit()
    return {"name": allocation_name, "allocation_status": AllocationStatus.RETURNED}


# ─── Cycle Count ─────────────────────────────────────────────────────────────

def create_cycle_count(warehouse: str, items: list[dict]) -> dict:
    """Tạo phiên kiểm kê kho."""
    _require_storekeeper()
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải chọn kho kiểm kê")
    wh_active = frappe.db.get_value("AC Warehouse", warehouse, "is_active")
    if wh_active == 0:
        raise ServiceError(ErrorCode.VALIDATION, f"Kho {warehouse} không còn hoạt động")

    doc = frappe.get_doc({
        "doctype": CycleCountRepo.DOCTYPE,
        "warehouse": warehouse,
        "count_date": nowdate(),
        "count_type": "Cycle",
        "counted_by": frappe.session.user,
        "status": CycleCountStatus.PLANNED,
        "items": items,
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": CycleCountStatus.PLANNED}


def submit_cycle_count(count_name: str, counted_items: list[dict]) -> dict:
    """Hoàn tất kiểm kê — tính variance và điều chỉnh tồn kho."""
    doc = CycleCountRepo.get(count_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy phiên kiểm kê: {count_name}")
    if doc.status not in (CycleCountStatus.PLANNED, CycleCountStatus.COUNTING):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể submit ở trạng thái: {doc.status}")
    # VR-15-11: verified_by != counted_by
    if doc.verified_by and doc.verified_by == doc.counted_by:
        raise ServiceError(ErrorCode.BUSINESS_RULE,
                           "Người xác nhận phải khác người kiểm kê")

    from assetcore.services.inventory import get_available_qty
    counted_map = {ci["spare_part"]: float(ci.get("counted_qty", 0))
                   for ci in counted_items}
    total_variance = 0
    var_count = 0

    for item in doc.items:
        system_qty = get_available_qty(doc.warehouse, item.spare_part)
        counted_qty = counted_map.get(item.spare_part, item.counted_qty or 0)
        item.system_qty = system_qty
        item.counted_qty = counted_qty
        item.variance_qty = counted_qty - system_qty
        item.variance_pct = abs(item.variance_qty / system_qty * 100) if system_qty else 0
        unit_cost = frappe.db.get_value("AC Spare Part", item.spare_part, "unit_cost") or 0
        item.variance_value = item.variance_qty * float(unit_cost)
        total_variance += abs(item.variance_value)
        if abs(item.variance_pct) > 5 or abs(item.variance_value) > 5_000_000:
            item.capa_required = 1
            var_count += 1

    doc.variance_count = var_count
    doc.variance_value = total_variance
    doc.status = CycleCountStatus.REVIEWED
    CycleCountRepo.save(doc)

    try:
        log_audit_event(
            asset="",
            event_type="cycle_count_submitted",
            actor=frappe.session.user,
            ref_doctype=CycleCountRepo.DOCTYPE,
            ref_name=count_name,
            change_summary=f"Cycle Count {count_name} — variance items: {var_count}",
        )
    except Exception:
        pass
    frappe.db.commit()
    return {"name": count_name, "status": CycleCountStatus.REVIEWED,
            "variance_count": var_count}


def get_stock_snapshot(warehouse: str) -> list[dict]:
    """Trả snapshot tồn kho hiện tại của một kho."""
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải cung cấp kho")
    rows = frappe.get_all(
        "AC Spare Part Stock",
        filters={"warehouse": warehouse},
        fields=["spare_part", "qty_on_hand", "reserved_qty", "available_qty",
                "last_movement_date"],
    )
    return rows


def get_critical_watchlist() -> list[dict]:
    """Trả list phụ tùng critical đang dưới mức tồn tối thiểu."""
    from assetcore.services.inventory import get_available_qty
    entries = CriticalWatchlistRepo.get_active_entries()
    result = []
    for e in entries:
        avail = get_available_qty(e["warehouse"], e["spare_part"])
        below = avail < float(e["min_required_on_hand"] or 0)
        result.append({
            "name": e["name"],
            "spare_part": e["spare_part"],
            "warehouse": e["warehouse"],
            "critical_asset": e["critical_asset"],
            "available_qty": avail,
            "min_required": float(e["min_required_on_hand"] or 0),
            "below_minimum": below,
        })
    return [r for r in result if r["below_minimum"]]


def check_low_stock_and_alert() -> None:
    """Scheduler daily: kiểm tra critical watchlist và gửi alert."""
    from assetcore.services.inventory import get_available_qty
    entries = CriticalWatchlistRepo.get_active_entries()
    alerts = []
    for e in entries:
        avail = get_available_qty(e["warehouse"], e["spare_part"])
        if avail < float(e["min_required_on_hand"] or 0):
            alerts.append(e)
            CriticalWatchlistRepo.set_values(e["name"], {
                "last_breach_date": now_datetime(),
            })
    if alerts:
        try:
            frappe.sendmail(
                recipients=_get_storekeeper_emails(),
                subject=f"[AssetCore] {len(alerts)} phụ tùng critical dưới mức tối thiểu",
                message=f"Có {len(alerts)} phụ tùng critical dưới mức tồn tối thiểu. "
                        f"Vui lòng kiểm tra ngay.",
            )
        except Exception:
            pass


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _create_stock_movement_for_issue(alloc_doc) -> object:
    """Tạo AC Stock Movement kiểu Issue cho phiếu cấp phát."""
    items = []
    for item in alloc_doc.items:
        items.append({
            "spare_part": item.spare_part,
            "qty": float(item.qty_issued or item.qty_requested or 0),
            "warehouse": alloc_doc.warehouse_from,
        })
    sm = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Issue",
        "reference_type": "IMM Spare Allocation",
        "reference_name": alloc_doc.name,
        "movement_date": nowdate(),
        "notes": f"Xuất kho theo phiếu cấp phát {alloc_doc.name}",
        "items": items,
    })
    sm.flags.ignore_links = True
    sm.insert(ignore_permissions=True)
    sm.submit()
    return sm


def _create_stock_movement_for_return(alloc_doc, return_items: list[dict]) -> object:
    """Tạo AC Stock Movement kiểu Receipt cho phiếu trả."""
    items = []
    for ri in return_items:
        if float(ri.get("qty_returned", 0)) > 0:
            items.append({
                "spare_part": ri["spare_part"],
                "qty": float(ri["qty_returned"]),
                "warehouse": alloc_doc.warehouse_from,
            })
    sm = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Receipt",
        "reference_type": "IMM Spare Allocation",
        "reference_name": alloc_doc.name,
        "movement_date": nowdate(),
        "notes": f"Trả phụ tùng từ phiếu {alloc_doc.name}",
        "items": items,
    })
    sm.flags.ignore_links = True
    sm.insert(ignore_permissions=True)
    sm.submit()
    return sm


def _write_allocation_audit(allocation_name: str, action: str, payload: dict) -> None:
    try:
        log_audit_event(
            asset="",
            event_type=f"allocation_{action.lower()}",
            actor=frappe.session.user,
            ref_doctype=AllocationRepo.DOCTYPE,
            ref_name=allocation_name,
            change_summary=f"IMM-15 Allocation {action}: {allocation_name}",
        )
    except Exception:
        pass


def _require_storekeeper() -> None:
    from assetcore.services.shared import has_any_role
    allowed = (Roles.STOREKEEPER, Roles.SYS_ADMIN, Roles.OPS_MANAGER)
    if not has_any_role(allowed):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ Thủ kho hoặc Admin có thể thực hiện thao tác này")


def _require_storekeeper_or_tech() -> None:
    from assetcore.services.shared import has_any_role
    allowed = (Roles.STOREKEEPER, Roles.SYS_ADMIN, Roles.OPS_MANAGER,
               Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN)
    if not has_any_role(allowed):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Không có quyền tạo phiếu cấp phát")


def _get_storekeeper_emails() -> list[str]:
    rows = frappe.db.sql(
        """SELECT DISTINCT u.email FROM `tabHas Role` hr
           JOIN `tabUser` u ON u.name = hr.parent
           WHERE hr.role = %s AND hr.parenttype = 'User' AND u.enabled = 1""",
        (Roles.STOREKEEPER,), as_dict=True,
    )
    return [r.email for r in rows if r.email]


# ─── Scheduler Jobs & Controller Hooks (Wave 2) ───────────────────────────────

def _seed_breach_capa(entry: dict) -> None:
    """Tạo CAPA record nếu chưa có CAPA đang mở cho spare + asset này."""
    try:
        spare = entry.get("spare_part", "")
        asset = entry.get("critical_asset", "")
        existing = frappe.db.exists(
            "IMM CAPA Record",
            {
                "reference_doctype": "AC Spare Part",
                "reference_name": spare,
                "status": ("not in", ["Closed", "Cancelled"]),
            },
        )
        if existing:
            return
        capa = frappe.get_doc({
            "doctype": "IMM CAPA Record",
            "source": "Critical Stock Breach",
            "reference_doctype": "AC Spare Part",
            "reference_name": spare,
            "description": (
                f"Tồn kho phụ tùng critical '{spare}' vi phạm mức tồn tối thiểu. "
                f"Thiết bị liên quan: {asset}. Auto-seeded bởi scheduler IMM-15."
            ),
            "severity": "High",
            "status": "Open",
        })
        capa.flags.ignore_links = True
        capa.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-15: _seed_breach_capa failed for {entry.get('spare_part')}")


def check_critical_spare_breach() -> None:
    """Scheduler daily 02:30: quét Watchlist, phát hiện breach → seed CAPA + email khẩn."""
    entries = CriticalWatchlistRepo.get_active_entries()
    if not entries:
        return
    from assetcore.services.inventory import get_available_qty
    breach_entries = []
    for entry in entries:
        avail = get_available_qty(entry["warehouse"], entry["spare_part"])
        if avail < float(entry["min_required_on_hand"] or 0):
            breach_entries.append(entry)
            CriticalWatchlistRepo.set_values(entry["name"], {
                "last_breach_date": now_datetime(),
            })
            # Seed CAPA if no open CAPA for this spare+asset
            _seed_breach_capa(entry)
    if breach_entries:
        try:
            from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
            recipients = _get_role_emails([Roles.WORKSHOP, Roles.STOREKEEPER])
            parts = ", ".join(e["spare_part"] for e in breach_entries)
            _safe_sendmail(
                recipients=recipients,
                subject=f"[KHẨN] {len(breach_entries)} phụ tùng critical dưới mức tối thiểu",
                message=f"<p>Các phụ tùng sau vi phạm mức tồn tối thiểu: <b>{parts}</b>. Vui lòng xử lý ngay.</p>",
            )
        except Exception:
            pass


def check_expiring_batches() -> None:
    """Scheduler daily 03:00: kiểm tra batch/lot sắp hết hạn (gated — chỉ chạy nếu IMM Spare Batch tồn tại)."""
    if not frappe.db.table_exists("tabIMM Spare Batch"):
        return
    expiry_limit = add_days(nowdate(), 30)
    expiring = frappe.get_all(
        "IMM Spare Batch",
        filters={"expiry_date": ("<=", expiry_limit), "expiry_date": (">=", nowdate())},
        fields=["name", "spare_part", "batch_code", "expiry_date", "qty_on_hand"],
    )
    if not expiring:
        return
    try:
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        recipients = _get_role_emails([Roles.STOREKEEPER, Roles.WORKSHOP])
        items_html = "".join(
            f"<li>{b['spare_part']} — Batch {b['batch_code']} — Hết hạn: {b['expiry_date']}</li>"
            for b in expiring
        )
        _safe_sendmail(
            recipients=recipients,
            subject=f"[AssetCore] {len(expiring)} batch phụ tùng sắp hết hạn",
            message=f"<p>Các batch sau sẽ hết hạn trong 30 ngày:</p><ul>{items_html}</ul>",
        )
    except Exception:
        pass


def compute_inventory_kpis() -> None:
    """Scheduler daily 04:00: snapshot KPI tồn kho (turnover, days-on-hand, stockout, accuracy)."""
    try:
        total_parts = frappe.db.count("AC Spare Part", {"is_active": 1})
        total_stock_value = frappe.db.sql(
            "SELECT COALESCE(SUM(qty_on_hand * unit_cost), 0) FROM `tabAC Spare Part Stock` s "
            "JOIN `tabAC Spare Part` p ON p.name = s.spare_part WHERE p.is_active = 1",
        )
        stock_value = float((total_stock_value or [[0]])[0][0])
        stockout_count = frappe.db.count("AC Spare Part Stock", {"qty_on_hand": ("<=", 0)})
        breach_count = len(CriticalWatchlistRepo.get_active_entries())  # approximate
        frappe.logger("imm15").info(
            f"IMM-15 KPI snapshot: parts={total_parts}, stock_value={stock_value:.0f}, "
            f"stockout={stockout_count}, watchlist_active={breach_count}"
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-15: compute_inventory_kpis failed")


def generate_spare_demand_forecast() -> None:
    """Scheduler monthly 1st 02:00: tạo IMM Spare Part Forecast Draft (Moving_Avg)."""
    try:
        from frappe.utils import get_first_day, add_months
        today = frappe.utils.getdate(nowdate())
        # Forecast for next quarter
        period_start = get_first_day(add_months(nowdate(), 1))
        period_str = f"{today.year}-Q{((today.month - 1) // 3) + 2}"
        spare_parts = frappe.get_all(
            "AC Spare Part", filters={"is_active": 1}, fields=["name"], limit_page_length=500
        )
        if not spare_parts:
            return
        items = []
        for sp in spare_parts:
            # Simple moving average: consumption in last 3 months
            consumed = frappe.db.sql(
                """SELECT COALESCE(SUM(qty), 0) FROM `tabAC Stock Movement Item` i
                   JOIN `tabAC Stock Movement` m ON m.name = i.parent
                   WHERE i.spare_part = %s AND m.movement_type = 'Issue'
                   AND m.movement_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)""",
                (sp.name,),
            )
            avg_monthly = float((consumed or [[0]])[0][0]) / 3
            items.append({
                "spare_part": sp.name,
                "forecast_qty": round(avg_monthly * 3, 2),
                "reorder_point": round(avg_monthly * 1.5, 2),
                "safety_stock": round(avg_monthly, 2),
                "historical_consumption_12m": avg_monthly * 12,
                "recommended_action": "Reorder" if avg_monthly > 0 else "Hold",
            })
        doc = frappe.get_doc({
            "doctype": "IMM Spare Part Forecast",
            "forecast_period": period_str,
            "period_start": period_start,
            "period_end": frappe.utils.add_months(period_start, 3),
            "method": "Moving_Avg",
            "generated_by": "Administrator",
            "items": items,
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-15: generate_spare_demand_forecast failed")


def reclassify_abc() -> None:
    """Cron quarterly: ABC/XYZ reclassification cho tất cả AC Spare Part theo consumption value 12m."""
    try:
        parts = frappe.get_all(
            "AC Spare Part", filters={"is_active": 1},
            fields=["name", "unit_cost"],
        )
        consumption_map: dict[str, float] = {}
        for sp in parts:
            val = frappe.db.sql(
                """SELECT COALESCE(SUM(i.qty * %s), 0)
                   FROM `tabAC Stock Movement Item` i
                   JOIN `tabAC Stock Movement` m ON m.name = i.parent
                   WHERE i.spare_part = %s AND m.movement_type = 'Issue'
                   AND m.movement_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)""",
                (sp.unit_cost or 0, sp.name),
            )
            consumption_map[sp.name] = float((val or [[0]])[0][0])
        if not consumption_map:
            return
        sorted_parts = sorted(consumption_map.items(), key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in sorted_parts)
        cumulative = 0.0
        for part_name, value in sorted_parts:
            if total > 0:
                cumulative += value
                pct = cumulative / total * 100
                cls = "A" if pct <= 80 else ("B" if pct <= 95 else "C")
            else:
                cls = "C"
            frappe.db.set_value("AC Spare Part", part_name, "imm_abc_class", cls)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-15: reclassify_abc failed")


def reserve_for_pm(doc, method=None) -> None:
    """Doc event IMM PM Work Order.before_submit: tạo IMM Spare Allocation từ planned spares."""
    try:
        planned_spares = getattr(doc, "imm_planned_spares", None) or []
        if not planned_spares:
            return
        items = [{"spare_part": row.spare_part, "qty_requested": row.qty}
                 for row in planned_spares if row.spare_part]
        if not items:
            return
        warehouse = frappe.db.get_value("AC Spare Part Stock", {"spare_part": items[0]["spare_part"]}, "warehouse") or ""
        create_allocation(
            work_order_ref=doc.name,
            items=items,
            asset=getattr(doc, "asset_ref", "") or "",
            warehouse=warehouse,
            urgency="Routine",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-15: reserve_for_pm failed for {doc.name}")


def reserve_for_repair(doc, method=None) -> None:
    """Doc event Asset Repair.before_submit: tạo IMM Spare Allocation từ spare_parts_used."""
    try:
        spare_parts_used = getattr(doc, "spare_parts_used", None) or []
        if not spare_parts_used:
            return
        items = [{"spare_part": row.spare_part, "qty_requested": row.qty or 1}
                 for row in spare_parts_used if row.spare_part]
        if not items:
            return
        warehouse = frappe.db.get_value("AC Spare Part Stock", {"spare_part": items[0]["spare_part"]}, "warehouse") or ""
        create_allocation(
            work_order_ref=doc.name,
            items=items,
            asset=getattr(doc, "asset_ref", "") or "",
            warehouse=warehouse,
            urgency="Urgent",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-15: reserve_for_repair failed for {doc.name}")


def flag_obsolete_on_decommission(doc, method=None) -> None:
    """Doc event AC Asset.on_update: nếu status=Decommissioned → flag imm_obsolete_review_required."""
    if not doc.has_value_changed("status"):
        return
    if doc.status != "Decommissioned":
        return
    try:
        # Find spare parts linked to this asset's device model
        device_model = frappe.db.get_value("AC Asset", doc.name, "device_model")
        if not device_model:
            return
        linked_parts = frappe.get_all(
            "IMM Device Spare Part",
            filters={"parent_device_model": device_model},
            fields=["spare_part"],
        )
        for lp in linked_parts:
            if lp.spare_part:
                frappe.db.set_value("AC Spare Part", lp.spare_part, "imm_obsolete_review_required", 1)
        if linked_parts:
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-15: flag_obsolete_on_decommission failed for {doc.name}")
