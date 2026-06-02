# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory Tracking — Service Layer (3-tier).
#
# Responsibilities:
#   - Allocation lifecycle: Requested → Approved → Picked → Issued → Returned / Cancelled
#   - Cycle Count lifecycle: Planned → Counting → Reviewed → Posted
#   - Spare Part Forecast: generation + approval
#   - Critical Spare Watchlist management
#   - Dashboard / low-stock alerts queries
#
# Tier rules:
#   - All data access via repositories (`assetcore.repositories.*`)
#   - All errors via ServiceError(code, message)
#   - List/get endpoints enrich Link IDs with display names (Data Contract)
from __future__ import annotations

import frappe
from frappe.utils import add_days, add_months, get_first_day, now_datetime, nowdate

from assetcore.repositories.allocation_repo import (
    AllocationRepo,
    CriticalWatchlistRepo,
    CycleCountRepo,
    SparePartForecastRepo,
    SparePartRepo,
    StockMovementRepo,
)
from assetcore.services.shared import ErrorCode, ServiceError, normalize_filters
from assetcore.services.shared import rbac
from assetcore.utils.lifecycle import log_audit_event


def _safe_get_value(doctype: str, name: str, field: str | list, *, as_dict: bool = False):
    """Wrapper around frappe.db.get_value that gracefully handles missing custom fields.

    Wave-3 custom fields on AC Spare Part (imm_part_class, imm_lead_time_days, ...)
    may not be installed yet — fall back to None / {} instead of raising.
    """
    try:
        return frappe.db.get_value(doctype, name, field, as_dict=as_dict)
    except Exception:
        return {} if as_dict else None


def _safe_set_value(doctype: str, name: str, field: str, value) -> None:
    try:
        frappe.db.set_value(doctype, name, field, value)
    except Exception:
        pass


def _ref_type_for_movement(desired: str) -> str:
    """Return desired reference_type if AC Stock Movement allows it; else 'Manual'.

    Wave-3 patch `extend_ac_stock_movement_reference_type` adds IMM-15 options.
    Before that patch runs we degrade to 'Manual' to avoid Select validation errors.
    """
    try:
        meta = frappe.get_meta("AC Stock Movement")
        df = meta.get_field("reference_type")
        if df and df.options and desired in df.options.split("\n"):
            return desired
    except Exception:
        pass
    return "Manual"


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


class ForecastState:
    DRAFT = "Draft"
    APPROVED = "Approved"


# Capability gates (Inventory domain) — quyen that do DocPerm quyet dinh.
_CAP_APPROVE = "inventory.submit"   # duyet/post (Manager-level)
_CAP_OPERATE = "inventory.write"    # thao tac thuong (User+)


# ─── Display name helpers (Data Contract BE-DC-15-01) ────────────────────────

def _enrich_display_names(rows: list[dict], mapping: dict[str, tuple[str, str]]) -> list[dict]:
    """Bulk-resolve Link IDs → display names.

    mapping: { field_in_row: (doctype, display_field) }
    """
    if not rows:
        return rows
    for field, (doctype, display_field) in mapping.items():
        ids = {r[field] for r in rows if r.get(field)}
        if not ids:
            continue
        name_map = {
            r["name"]: r.get(display_field) or r["name"]
            for r in frappe.get_all(
                doctype,
                filters={"name": ("in", list(ids))},
                fields=["name", display_field],
            )
        }
        out_field = field.replace("_ref", "") + "_name" if field.endswith("_ref") else f"{field}_name"
        # special cases
        if field == "asset":
            out_field = "asset_name"
        elif field == "warehouse" or field == "warehouse_from":
            out_field = "warehouse_name"
        elif field == "spare_part":
            out_field = "part_name"
        elif field == "counted_by" or field == "verified_by" or field == "requested_by" or field == "approved_by" or field == "added_by":
            out_field = f"{field}_name"
        elif field == "critical_asset":
            out_field = "critical_asset_name"
        for r in rows:
            r[out_field] = name_map.get(r.get(field), r.get(field) or "")
    return rows


# ─── Spare Allocation: List / Create / Approve / Issue / Return / Cancel ─────

def list_allocations(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    """List allocations với display names cho asset / warehouse / requester."""
    rows, pg = AllocationRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "work_order_ref", "work_order_doctype", "asset",
                "warehouse_from", "requested_by", "requested_date", "urgency",
                "allocation_status", "total_value", "stock_movement_ref"],
        order_by="requested_date desc, modified desc",
        page=page, page_size=page_size,
    )
    _enrich_display_names(rows, {
        "asset": ("AC Asset", "asset_name"),
        "warehouse_from": ("AC Warehouse", "warehouse_name"),
        "requested_by": ("User", "full_name"),
    })
    return {"data": rows, "pagination": pg}


def get_allocation(name: str) -> dict:
    """Get full allocation incl. items + display names."""
    doc = AllocationRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu cấp phát {name}")
    data = doc.as_dict()
    # enrich items
    for item in data.get("items", []):
        if item.get("spare_part"):
            sp = frappe.db.get_value("AC Spare Part", item["spare_part"],
                                     ["part_name", "stock_uom", "unit_cost"], as_dict=True) or {}
            item["part_name"] = sp.get("part_name") or item["spare_part"]
            item["uom"] = item.get("uom") or sp.get("stock_uom")
            item["unit_value"] = item.get("unit_value") or sp.get("unit_cost") or 0
    # header display names
    data["asset_name"] = frappe.db.get_value("AC Asset", data.get("asset"), "asset_name") or data.get("asset") or ""
    data["warehouse_name"] = frappe.db.get_value("AC Warehouse", data.get("warehouse_from"), "warehouse_name") or data.get("warehouse_from") or ""
    data["requested_by_name"] = frappe.db.get_value("User", data.get("requested_by"), "full_name") or data.get("requested_by") or ""
    return data


def create_allocation(work_order_ref: str, items: list[dict],
                      asset: str = "", warehouse: str = "",
                      urgency: str = "Routine") -> dict:
    """Tạo phiếu cấp phát (state=Requested)."""
    _require_storekeeper_or_tech()
    _vr_05_urgency_valid(urgency)
    if not items:
        raise ServiceError(ErrorCode.VALIDATION,
                           "Phiếu cấp phát phải có ít nhất 1 dòng phụ tùng")
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải chọn kho xuất")
    _vr_13_warehouse_active(warehouse)

    # VR-15-01: WO ref bắt buộc trừ Emergency
    if not work_order_ref and urgency != "Emergency":
        raise ServiceError(ErrorCode.BUSINESS_RULE,
                           "VR-15-01: Cấp phát phụ tùng phải liên kết Work Order")

    doc = frappe.get_doc({
        "doctype": AllocationRepo.DOCTYPE,
        "work_order_doctype": "IMM PM Work Order" if work_order_ref else None,
        "work_order_ref": work_order_ref or None,
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
    return {"name": doc.name, "workflow_state": AllocationStatus.REQUESTED,
            "allocation_status": AllocationStatus.REQUESTED}


def approve_allocation(allocation: str) -> dict:
    """Duyệt allocation: Requested → Approved (§3.3)."""
    _require_any_role(_CAP_APPROVE,
                      "Chỉ cấp quản lý (Inventory/Store Manager) mới được duyệt allocation")
    doc = AllocationRepo.get(allocation)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"IMM Spare Allocation {allocation} không tồn tại")
    if doc.allocation_status != AllocationStatus.REQUESTED:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"{allocation} không ở trạng thái Requested")
    doc.allocation_status = AllocationStatus.APPROVED
    doc.approved_by = frappe.session.user
    doc.approval_date = now_datetime()
    doc.flags.ignore_links = True
    AllocationRepo.save(doc)
    _write_allocation_audit(allocation, "APPROVED", {})
    frappe.db.commit()
    return {"name": allocation, "workflow_state": AllocationStatus.APPROVED}


def issue_allocation(allocation_name: str) -> dict:
    """Xuất kho — tạo AC Stock Movement (Issue) (§3.4)."""
    _require_any_role(_CAP_OPERATE,
                      "Chỉ Thủ kho / Operations Manager mới được xuất kho")
    doc = AllocationRepo.get(allocation_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"IMM Spare Allocation {allocation_name} không tồn tại")
    if doc.allocation_status not in (AllocationStatus.APPROVED, AllocationStatus.REQUESTED):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể xuất kho ở trạng thái: {doc.allocation_status}")

    from assetcore.services.inventory import get_available_qty
    is_emergency = doc.urgency == "Emergency"

    for item in doc.items:
        sp_meta = _safe_get_value(
            "AC Spare Part", item.spare_part,
            ["imm_traceability_required", "imm_part_class"], as_dict=True,
        ) or {}
        # Fallback to is_critical when imm_part_class custom field unavailable
        if not sp_meta.get("imm_part_class"):
            sp_meta["imm_part_class"] = "Critical" if _safe_get_value(
                "AC Spare Part", item.spare_part, "is_critical") else "Major"
        is_critical = (sp_meta.get("imm_part_class") == "Critical")

        # VR-15-02 traceability
        if sp_meta.get("imm_traceability_required") and not (item.batch_no or item.serial_no):
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"VR-15-02: Phụ tùng {item.spare_part} yêu cầu số lô/serial",
            )

        # VR-15-03 stock sufficiency (bypass cho Emergency+Critical)
        avail = get_available_qty(doc.warehouse_from, item.spare_part)
        qty_needed = float(item.qty_requested or 0)
        if avail < qty_needed and not (is_emergency and is_critical):
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                f"VR-15-03: Tồn kho không đủ — available: {avail}, cần: {qty_needed}",
            )
        item.qty_issued = qty_needed

    sm = _create_stock_movement_for_issue(doc)
    doc.stock_movement_ref = sm.name
    doc.allocation_status = AllocationStatus.ISSUED
    doc.total_value = sum(
        float(item.qty_issued or 0) * float(item.unit_value or 0)
        for item in doc.items
    )
    doc.flags.ignore_links = True
    AllocationRepo.save(doc)
    _write_allocation_audit(allocation_name, "ISSUED",
                            {"stock_movement": sm.name})
    try:
        frappe.publish_realtime("imm15_allocation_issued",
                                {"name": allocation_name, "asset": doc.asset,
                                 "stock_movement_ref": sm.name})
    except Exception:
        pass
    frappe.db.commit()
    return {"name": allocation_name, "workflow_state": AllocationStatus.ISSUED,
            "stock_movement_ref": sm.name}


def return_items(allocation: str, items: list[dict]) -> dict:
    """Trả phụ tùng (§3.5). Damaged → QC Hold warehouse (nếu cấu hình)."""
    _require_any_role(_CAP_OPERATE,
                      "Chỉ Thủ kho / Operations Manager mới được nhận trả phụ tùng")
    doc = AllocationRepo.get(allocation)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"IMM Spare Allocation {allocation} không tồn tại")
    if doc.allocation_status != AllocationStatus.ISSUED:
        raise ServiceError(ErrorCode.BAD_STATE,
                           "Chỉ có thể trả phụ tùng khi phiếu đã Issued")

    issued_map = {it.spare_part: float(it.qty_issued or 0) for it in doc.items}
    for ri in items:
        sp = ri.get("spare_part")
        qty_ret = float(ri.get("qty_returned", 0))
        if qty_ret > issued_map.get(sp, 0):
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"VR-15-08: Số lượng trả ({qty_ret}) vượt số đã xuất ({issued_map.get(sp, 0)})",
            )
        for it in doc.items:
            if it.spare_part == sp:
                it.qty_returned = qty_ret
                it.return_condition = ri.get("return_condition", "Good")

    sm = _create_stock_movement_for_return(doc, items)
    doc.stock_movement_return_ref = sm.name
    doc.allocation_status = AllocationStatus.RETURNED
    doc.flags.ignore_links = True
    AllocationRepo.save(doc)
    _write_allocation_audit(allocation, "RETURNED",
                            {"stock_movement": sm.name})
    frappe.db.commit()
    return {"name": allocation, "workflow_state": AllocationStatus.RETURNED,
            "stock_movement_return_ref": sm.name}


# Backward compat alias (old name)
def return_allocation(allocation_name: str, return_items_list: list[dict]) -> dict:
    return return_items(allocation_name, return_items_list)


# ─── Cycle Count: Create / Post ──────────────────────────────────────────────

def list_cycle_counts(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = CycleCountRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "warehouse", "count_date", "count_type", "counted_by",
                "verified_by", "status", "variance_count", "variance_value"],
        order_by="count_date desc",
        page=page, page_size=page_size,
    )
    _enrich_display_names(rows, {
        "warehouse": ("AC Warehouse", "warehouse_name"),
        "counted_by": ("User", "full_name"),
        "verified_by": ("User", "full_name"),
    })
    return {"data": rows, "pagination": pg}


def create_cycle_count(warehouse: str, items: list[dict],
                       count_type: str = "Cycle",
                       count_date: str = "") -> dict:
    """Tạo phiên kiểm kê (§3.6) — snapshot system_qty."""
    _require_any_role(_CAP_OPERATE,
                      "Không có quyền tạo phiên kiểm kê")
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải chọn kho kiểm kê")
    _vr_13_warehouse_active(warehouse)

    from assetcore.services.inventory import get_available_qty
    snap_items = []
    for it in items:
        sp = it.get("spare_part") if isinstance(it, dict) else it
        if not sp:
            continue
        sys_qty = get_available_qty(warehouse, sp)
        snap_items.append({"spare_part": sp, "system_qty": sys_qty,
                           "counted_qty": 0})

    doc = frappe.get_doc({
        "doctype": CycleCountRepo.DOCTYPE,
        "warehouse": warehouse,
        "count_date": count_date or nowdate(),
        "count_type": count_type,
        "counted_by": frappe.session.user,
        "status": CycleCountStatus.PLANNED,
        "items": snap_items,
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "workflow_state": CycleCountStatus.PLANNED,
            "items_count": len(snap_items)}


def submit_cycle_count(count_name: str, counted_items: list[dict]) -> dict:
    """Hoàn tất kiểm kê — tính variance (chuyển sang Reviewed). Internal helper."""
    doc = CycleCountRepo.get(count_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy phiên kiểm kê: {count_name}")
    if doc.status not in (CycleCountStatus.PLANNED, CycleCountStatus.COUNTING):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể submit ở trạng thái: {doc.status}")
    from assetcore.services.inventory import get_available_qty
    counted_map = {ci["spare_part"]: float(ci.get("counted_qty", 0))
                   for ci in counted_items if ci.get("spare_part")}
    total_var_value = 0.0
    var_count = 0
    for item in doc.items:
        sys_qty = item.system_qty if item.system_qty else get_available_qty(doc.warehouse, item.spare_part)
        cnt = counted_map.get(item.spare_part, item.counted_qty or 0)
        item.system_qty = sys_qty
        item.counted_qty = cnt
        item.variance_qty = cnt - sys_qty
        item.variance_pct = abs(item.variance_qty / sys_qty * 100) if sys_qty else 0
        unit_cost = frappe.db.get_value("AC Spare Part", item.spare_part, "unit_cost") or 0
        item.variance_value = item.variance_qty * float(unit_cost)
        total_var_value += abs(item.variance_value)
        if abs(item.variance_pct) > 5 or abs(item.variance_value) > 5_000_000:
            item.capa_required = 1
            var_count += 1
    doc.variance_count = var_count
    doc.variance_value = total_var_value
    doc.status = CycleCountStatus.REVIEWED
    CycleCountRepo.save(doc)
    frappe.db.commit()
    return {"name": count_name, "workflow_state": CycleCountStatus.REVIEWED,
            "variance_count": var_count}


def post_cycle_count(cycle_count: str, verified_by: str = "",
                     notes: str = "") -> dict:
    """Post cycle count: Reviewed → Posted, tạo AC Stock Movement Adjustment (§3.7)."""
    _require_any_role(_CAP_APPROVE,
                      "Chỉ Workshop Lead / Operations Manager mới được post cycle count")
    doc = CycleCountRepo.get(cycle_count)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy phiên kiểm kê: {cycle_count}")
    if doc.status != CycleCountStatus.REVIEWED:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Cycle Count {cycle_count} chưa ở trạng thái Reviewed")

    # VR-15-11 segregation
    verifier = verified_by or frappe.session.user
    if verifier == doc.counted_by:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            "VR-15-11: Người kiểm tra phải khác người kiểm kê (segregation)",
        )

    # VR-15-04 — variance >5% phải có root_cause
    for item in doc.items:
        if (abs(float(item.variance_pct or 0)) > 5
                and not (item.root_cause or "").strip()):
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"VR-15-04: Item {item.spare_part} chưa nhập root_cause cho variance > 5%",
            )

    sm = _create_stock_movement_for_adjustment(doc)
    doc.verified_by = verifier
    doc.notes = (doc.notes or "") + ("\n" + notes if notes else "")
    doc.posted_movement_ref = sm.name
    doc.status = CycleCountStatus.POSTED
    CycleCountRepo.save(doc)
    capa_count = _seed_capa_for_cycle_variance(doc)
    try:
        frappe.publish_realtime("imm15_cycle_count_posted",
                                {"name": cycle_count, "adjustment_ref": sm.name,
                                 "capa_count": capa_count})
    except Exception:
        pass
    frappe.db.commit()
    return {"name": cycle_count, "workflow_state": CycleCountStatus.POSTED,
            "adjustment_ref": sm.name, "capa_created": capa_count}


# ─── Forecast ─────────────────────────────────────────────────────────────────

def list_spare_forecasts(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = SparePartForecastRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "forecast_period", "period_start", "period_end", "method",
                "workflow_state", "generated_by", "approved_by", "docstatus"],
        order_by="period_start desc",
        page=page, page_size=page_size,
    )
    _enrich_display_names(rows, {
        "generated_by": ("User", "full_name"),
        "approved_by": ("User", "full_name"),
    })
    return {"data": rows, "pagination": pg}


def generate_spare_forecast(horizon_months: int = 3,
                            method: str = "Moving_Avg",
                            forecast_period: str = "") -> dict:
    """Tạo IMM Spare Part Forecast (Moving Avg) cho `horizon_months` (§3.8).

    Logic:
      - Đọc consumption (Issue) `horizon_months * 4` tháng qua (default 12m)
      - avg_monthly = consumption / lookback_months
      - forecast_qty = avg_monthly × horizon_months
      - safety_stock = avg_monthly × (lead_time_days + safety_stock_days) / 30
      - reorder_point = safety_stock + (avg_monthly × lead_time_days / 30)
      - recommended_action: Reorder / Hold / Obsolete
    """
    _require_any_role(_CAP_OPERATE,
                      "Không có quyền tạo forecast")
    horizon_months = max(1, int(horizon_months or 3))
    lookback_months = max(horizon_months * 4, 12)

    today = frappe.utils.getdate(nowdate())
    period_start = get_first_day(add_months(nowdate(), 1))
    period_end = add_months(period_start, horizon_months)
    if not forecast_period:
        forecast_period = f"{today.year}-Q{((today.month - 1) // 3) + 2}"

    # Custom IMM fields may be absent (Wave 3 patch). Fall back to core fields only.
    try:
        parts, _pg = SparePartRepo.list(
            filters={"is_active": 1},
            fields=["name", "imm_lead_time_days", "imm_safety_stock_days", "unit_cost"],
            page_size=2000,
        )
    except Exception:
        parts, _pg = SparePartRepo.list(
            filters={"is_active": 1},
            fields=["name", "unit_cost"],
            page_size=2000,
        )
    if not parts:
        raise ServiceError(ErrorCode.VALIDATION,
                           "Không có phụ tùng active để forecast")

    items = []
    for sp in parts:
        total_consumed = StockMovementRepo.get_consumption(sp["name"], months=lookback_months)
        avg_monthly = total_consumed / lookback_months if lookback_months else 0
        lead = float(sp.get("imm_lead_time_days") or 30)
        sft = float(sp.get("imm_safety_stock_days") or 14)
        safety_stock = round(avg_monthly * sft / 30, 2)
        reorder_point = round(safety_stock + (avg_monthly * lead / 30), 2)
        forecast_qty = round(avg_monthly * horizon_months, 2)
        current_qty = _sum_part_stock(sp["name"])
        if total_consumed <= 0:
            action = "Obsolete" if current_qty == 0 else "Hold"
        elif current_qty < reorder_point:
            action = "Reorder"
        elif current_qty > reorder_point * 3:
            action = "ReduceMin"
        else:
            action = "Hold"
        items.append({
            "spare_part": sp["name"],
            "forecast_qty": forecast_qty,
            "reorder_point": reorder_point,
            "safety_stock": safety_stock,
            "current_qty": current_qty,
            "historical_consumption_12m": round(total_consumed, 2),
            "recommended_action": action,
        })

    doc = frappe.get_doc({
        "doctype": SparePartForecastRepo.DOCTYPE,
        "forecast_period": forecast_period,
        "period_start": period_start,
        "period_end": period_end,
        "method": method,
        "generated_by": frappe.session.user,
        "items": items,
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "forecast_period": forecast_period,
            "workflow_state": ForecastState.DRAFT,
            "items_count": len(items)}


def approve_forecast(forecast: str) -> dict:
    """Duyệt forecast: Draft → Approved (§3.9)."""
    _require_any_role(_CAP_APPROVE,
                      "Chỉ Workshop Lead / Operations Manager mới được duyệt forecast")
    doc = SparePartForecastRepo.get(forecast)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"IMM Spare Part Forecast {forecast} không tồn tại")
    doc.approved_by = frappe.session.user
    if hasattr(doc, "workflow_state"):
        doc.workflow_state = ForecastState.APPROVED
    SparePartForecastRepo.save(doc)
    if doc.docstatus == 0:
        try:
            doc.submit()
        except Exception:
            pass
    reorder_count = sum(
        1 for it in (doc.items or [])
        if (it.recommended_action or "") == "Reorder"
    )
    try:
        frappe.publish_realtime("imm15_forecast_approved",
                                {"name": forecast, "reorder_count": reorder_count})
    except Exception:
        pass
    frappe.db.commit()
    return {"name": forecast, "workflow_state": ForecastState.APPROVED,
            "reorder_recommendations": reorder_count}


# ─── Watchlist ────────────────────────────────────────────────────────────────

def list_watchlist(filters: dict, *, page: int = 1, page_size: int = 50) -> dict:
    rows, pg = CriticalWatchlistRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "watchlist_name", "critical_asset", "spare_part",
                "warehouse", "min_required_on_hand", "active",
                "last_breach_date", "breach_count_30d"],
        order_by="modified desc",
        page=page, page_size=page_size,
    )
    _enrich_display_names(rows, {
        "critical_asset": ("AC Asset", "asset_name"),
        "spare_part": ("AC Spare Part", "part_name"),
        "warehouse": ("AC Warehouse", "warehouse_name"),
    })
    return {"data": rows, "pagination": pg}


def add_to_watchlist(watchlist_name: str, critical_asset: str,
                     spare_part: str, min_required_on_hand: float,
                     warehouse: str) -> dict:
    """Thêm entry vào Critical Watchlist (§3.10).

    VR-15-09: chỉ phụ tùng Critical mới được thêm.
    """
    _require_any_role(_CAP_OPERATE,
                      "Chỉ Workshop Lead / Operations Manager mới được quản lý watchlist")
    if not (watchlist_name and spare_part and warehouse):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Thiếu trường bắt buộc cho watchlist")
    part_class = _safe_get_value("AC Spare Part", spare_part, "imm_part_class")
    if part_class != "Critical":
        # graceful fallback: also accept is_critical=1
        is_critical = _safe_get_value("AC Spare Part", spare_part, "is_critical")
        if not is_critical:
            raise ServiceError(
                ErrorCode.VALIDATION,
                "VR-15-09: Chỉ phụ tùng Critical mới được thêm vào Watchlist",
            )
    if float(min_required_on_hand or 0) <= 0:
        raise ServiceError(ErrorCode.VALIDATION,
                           "min_required_on_hand phải > 0")
    if CriticalWatchlistRepo.exists(watchlist_name):
        raise ServiceError(ErrorCode.DUPLICATE,
                           f"Watchlist '{watchlist_name}' đã tồn tại")
    doc = CriticalWatchlistRepo.create({
        "watchlist_name": watchlist_name,
        "critical_asset": critical_asset,
        "spare_part": spare_part,
        "min_required_on_hand": float(min_required_on_hand),
        "warehouse": warehouse,
        "active": 1,
    })
    frappe.db.commit()
    return {"name": doc.name, "active": True}


# ─── Dashboard / Alerts ──────────────────────────────────────────────────────

def get_dashboard_stats(period: str = "") -> dict:
    """KPI snapshot cho IMM-15 dashboard (§3.12)."""
    if not period:
        today = frappe.utils.getdate(nowdate())
        period = f"{today.year}-{today.month:02d}"

    def _kpi(value, target=None, target_min=None, target_max=None, *,
             higher_better=True) -> dict:
        status = "green"
        if target is not None:
            if higher_better and value < target:
                status = "yellow" if value >= target * 0.8 else "red"
            elif not higher_better and value > target:
                status = "yellow" if value <= target * 1.2 else "red"
        if target_min is not None and target_max is not None:
            if value < target_min or value > target_max:
                status = "yellow"
        out = {"value": value, "status": status}
        if target is not None:
            out["target"] = target
        if target_min is not None:
            out["target_min"] = target_min
        if target_max is not None:
            out["target_max"] = target_max
        return out

    # Stock turnover (12m): total Issue value / avg stock value
    issue_value = frappe.db.sql(
        """SELECT COALESCE(SUM(i.qty * p.unit_cost), 0)
           FROM `tabAC Stock Movement Item` i
           JOIN `tabAC Stock Movement` m ON m.name = i.parent
           JOIN `tabAC Spare Part` p ON p.name = i.spare_part
           WHERE m.movement_type='Issue' AND m.docstatus=1
             AND m.movement_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)"""
    )
    issue_val = float((issue_value or [[0]])[0][0])
    stock_val = frappe.db.sql(
        """SELECT COALESCE(SUM(s.qty_on_hand * p.unit_cost), 0)
           FROM `tabAC Spare Part Stock` s
           JOIN `tabAC Spare Part` p ON p.name = s.spare_part"""
    )
    stock_val_f = float((stock_val or [[0]])[0][0])
    turnover = round(issue_val / stock_val_f, 2) if stock_val_f else 0
    days_on_hand = round((stock_val_f / (issue_val / 365)), 1) if issue_val else 0

    stockout_30d = frappe.db.count("AC Spare Part Stock", {"qty_on_hand": ("<=", 0)})

    breach_entries = CriticalWatchlistRepo.get_active_entries()
    from assetcore.services.inventory import get_available_qty
    critical_breach = sum(
        1 for e in breach_entries
        if get_available_qty(e["warehouse"], e["spare_part"]) < float(e["min_required_on_hand"] or 0)
    )

    cyc_total = frappe.db.count("IMM Stock Cycle Count", {"status": "Posted"})
    cyc_accurate = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIMM Stock Cycle Count`
           WHERE status='Posted' AND COALESCE(variance_count,0)=0
             AND count_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"""
    )
    accurate = float((cyc_accurate or [[0]])[0][0])
    cyc_30d_total = frappe.db.count("IMM Stock Cycle Count",
                                    {"status": "Posted",
                                     "count_date": (">=", add_days(nowdate(), -30))})
    accuracy_pct = round(accurate / cyc_30d_total * 100, 2) if cyc_30d_total else 100

    emergency_count = frappe.db.count(
        "IMM Spare Allocation",
        {"urgency": "Emergency",
         "requested_date": (">=", add_days(nowdate(), -30))},
    )

    pending_allocations = frappe.db.count(
        "IMM Spare Allocation",
        {"allocation_status": ("in", [AllocationStatus.REQUESTED, AllocationStatus.APPROVED])},
    )
    pending_cycle_counts = frappe.db.count(
        "IMM Stock Cycle Count",
        {"status": ("in", [CycleCountStatus.PLANNED, CycleCountStatus.COUNTING, CycleCountStatus.REVIEWED])},
    )
    low_stock_alerts = _count_low_stock()

    return {
        "period": period,
        "stock_turnover_year": _kpi(turnover, target=4.0, higher_better=True),
        "days_on_hand_avg": _kpi(days_on_hand, target_min=30, target_max=60),
        "stockout_incidents_30d": _kpi(stockout_30d, target=2, higher_better=False),
        "critical_breach_hours_30d": _kpi(critical_breach, target=0, higher_better=False),
        "cycle_count_accuracy_pct": _kpi(accuracy_pct, target=98, higher_better=True),
        "forecast_mape_pct": _kpi(22, target=25, higher_better=False),  # placeholder
        "emergency_override_count_30d": _kpi(emergency_count, target=3, higher_better=False),
        "low_stock_alerts": low_stock_alerts,
        "pending_allocations": pending_allocations,
        "pending_cycle_counts": pending_cycle_counts,
    }


def get_low_stock_alerts(warehouse: str = "") -> dict:
    """Alerts: parts có qty_on_hand < min_stock_level (§3.13)."""
    cond = " AND s.warehouse = %(wh)s" if warehouse else ""
    rows = frappe.db.sql(
        f"""SELECT s.spare_part, p.part_name, s.warehouse, s.qty_on_hand,
                   p.min_stock_level
            FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE p.is_active=1 AND COALESCE(p.min_stock_level,0) > 0
              AND s.qty_on_hand < p.min_stock_level {cond}
            ORDER BY (p.min_stock_level - s.qty_on_hand) DESC
            LIMIT 100""",
        {"wh": warehouse} if warehouse else {},
        as_dict=True,
    )
    # mark watchlist membership
    watch_set = set()
    if rows:
        wl = frappe.get_all("IMM Critical Spare Watchlist",
                            filters={"active": 1},
                            fields=["spare_part", "warehouse"])
        watch_set = {(w["spare_part"], w["warehouse"]) for w in wl}
    alerts = []
    for r in rows:
        r["is_in_watchlist"] = (r["spare_part"], r["warehouse"]) in watch_set
        # enrich warehouse_name
        r["warehouse_name"] = frappe.db.get_value("AC Warehouse", r["warehouse"], "warehouse_name") or r["warehouse"]
        r["imm_part_class"] = _safe_get_value("AC Spare Part", r["spare_part"], "imm_part_class") or ""
        alerts.append(r)
    return {"alerts": alerts, "total": len(alerts)}


# ─── Stock snapshot ──────────────────────────────────────────────────────────

def get_stock_snapshot(warehouse: str) -> list[dict]:
    """Snapshot tồn kho 1 warehouse (display names)."""
    if not warehouse:
        raise ServiceError(ErrorCode.VALIDATION, "Phải cung cấp kho")
    rows = frappe.get_all(
        "AC Spare Part Stock",
        filters={"warehouse": warehouse},
        fields=["spare_part", "qty_on_hand", "reserved_qty", "available_qty",
                "last_movement_date"],
    )
    _enrich_display_names(rows, {
        "spare_part": ("AC Spare Part", "part_name"),
    })
    return rows


def get_critical_watchlist() -> list[dict]:
    """Watchlist entries dưới mức tồn tối thiểu."""
    from assetcore.services.inventory import get_available_qty
    entries = CriticalWatchlistRepo.get_active_entries()
    result = []
    for e in entries:
        avail = get_available_qty(e["warehouse"], e["spare_part"])
        below = avail < float(e["min_required_on_hand"] or 0)
        result.append({
            "name": e["name"],
            "spare_part": e["spare_part"],
            "part_name": frappe.db.get_value("AC Spare Part", e["spare_part"], "part_name") or e["spare_part"],
            "warehouse": e["warehouse"],
            "warehouse_name": frappe.db.get_value("AC Warehouse", e["warehouse"], "warehouse_name") or e["warehouse"],
            "critical_asset": e["critical_asset"],
            "critical_asset_name": frappe.db.get_value("AC Asset", e["critical_asset"], "asset_name") or e["critical_asset"],
            "available_qty": avail,
            "min_required": float(e["min_required_on_hand"] or 0),
            "below_minimum": below,
        })
    return [r for r in result if r["below_minimum"]]


def check_low_stock_and_alert() -> None:
    """(Legacy alias) Scheduler-friendly entry."""
    check_critical_spare_breach()


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _create_stock_movement_for_issue(alloc_doc) -> object:
    items = []
    for item in alloc_doc.items:
        items.append({
            "spare_part": item.spare_part,
            "qty": float(item.qty_issued or item.qty_requested or 0),
            "warehouse": alloc_doc.warehouse_from,
        })
    # Slide 27: phiếu Xuất kho bắt buộc có Khoa/Phòng nhận — lấy từ Khoa quản lý
    # của tài sản được cấp phát phụ tùng.
    receiver_department = None
    if alloc_doc.get("asset"):
        receiver_department = _safe_get_value("AC Asset", alloc_doc.asset, "department")
    if not receiver_department:
        raise ServiceError(
            ErrorCode.VALIDATION,
            "Không xác định được Khoa/Phòng nhận để xuất kho — "
            f"tài sản {alloc_doc.get('asset') or '(trống)'} chưa gán Khoa quản lý",
        )
    sm = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Issue",
        "from_warehouse": alloc_doc.warehouse_from,
        "receiver_department": receiver_department,
        "reference_type": _ref_type_for_movement("IMM Spare Allocation"),
        "reference_name": alloc_doc.name,
        "movement_date": nowdate(),
        "notes": f"Xuất kho theo phiếu cấp phát {alloc_doc.name}",
        "items": items,
    })
    sm.flags.ignore_links = True
    sm.insert(ignore_permissions=True)
    sm.submit()
    return sm


def _create_stock_movement_for_return(alloc_doc, items: list[dict]) -> object:
    sm_items = []
    for ri in items:
        if float(ri.get("qty_returned", 0)) > 0:
            warehouse = alloc_doc.warehouse_from
            if ri.get("return_condition") == "Damaged":
                # Try QC Hold warehouse fallback
                qc_wh = frappe.db.get_value("AC Warehouse",
                                            {"warehouse_name": ("like", "%QC Hold%")}, "name")
                warehouse = qc_wh or warehouse
            sm_items.append({
                "spare_part": ri["spare_part"],
                "qty": float(ri["qty_returned"]),
                "warehouse": warehouse,
            })
    sm = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Receipt",
        "to_warehouse": alloc_doc.warehouse_from,
        "reference_type": _ref_type_for_movement("IMM Spare Allocation"),
        "reference_name": alloc_doc.name,
        "movement_date": nowdate(),
        "notes": f"Trả phụ tùng từ phiếu {alloc_doc.name}",
        "items": sm_items,
    })
    sm.flags.ignore_links = True
    sm.insert(ignore_permissions=True)
    sm.submit()
    return sm


def _create_stock_movement_for_adjustment(cyc_doc) -> object:
    items = []
    for it in cyc_doc.items:
        delta = float(it.variance_qty or 0)
        if delta == 0:
            continue
        items.append({
            "spare_part": it.spare_part,
            "qty": delta,
            "warehouse": cyc_doc.warehouse,
        })
    sm = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Adjustment",
        "from_warehouse": cyc_doc.warehouse,
        "reference_type": _ref_type_for_movement("IMM Stock Cycle Count"),
        "reference_name": cyc_doc.name,
        "movement_date": nowdate(),
        "notes": f"Điều chỉnh từ Cycle Count {cyc_doc.name}",
        "items": items,
    })
    sm.flags.ignore_links = True
    sm.insert(ignore_permissions=True)
    if items:
        sm.submit()
    return sm


def _seed_capa_for_cycle_variance(cyc_doc) -> int:
    """Seed CAPA records cho items có capa_required=1."""
    count = 0
    for it in cyc_doc.items:
        if not it.capa_required:
            continue
        existing = frappe.db.exists("IMM CAPA Record", {
            "reference_doctype": "AC Spare Part",
            "reference_name": it.spare_part,
            "status": ("not in", ["Closed", "Cancelled"]),
        })
        if existing:
            continue
        try:
            capa = frappe.get_doc({
                "doctype": "IMM CAPA Record",
                "source": "Cycle Count Variance",
                "reference_doctype": "AC Spare Part",
                "reference_name": it.spare_part,
                "description": (
                    f"Cycle Count {cyc_doc.name} phát hiện variance "
                    f"{it.variance_qty} ({it.variance_pct:.1f}%) cho {it.spare_part}. "
                    f"Root cause: {it.root_cause or 'N/A'}"
                ),
                "severity": "Medium",
                "status": "Open",
            })
            capa.flags.ignore_links = True
            capa.insert(ignore_permissions=True)
            count += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"IMM-15: _seed_capa_for_cycle_variance failed for {it.spare_part}")
    return count


def _sum_part_stock(spare_part: str) -> float:
    row = frappe.db.sql(
        """SELECT COALESCE(SUM(qty_on_hand), 0) FROM `tabAC Spare Part Stock`
           WHERE spare_part = %s""",
        (spare_part,),
    )
    return float((row or [[0]])[0][0])


def _count_low_stock() -> int:
    row = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
           JOIN `tabAC Spare Part` p ON p.name = s.spare_part
           WHERE p.is_active=1 AND COALESCE(p.min_stock_level,0) > 0
             AND s.qty_on_hand < p.min_stock_level"""
    )
    return int((row or [[0]])[0][0])


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


def _require_any_role(cap: str, message: str) -> None:
    # `cap` la capability key (inventory.*) — KHONG so ten role.
    if not rbac.can(cap):
        raise ServiceError(ErrorCode.FORBIDDEN, message)


def _require_storekeeper_or_tech() -> None:
    _require_any_role(_CAP_OPERATE, "Không có quyền tạo phiếu cấp phát")


def _vr_05_urgency_valid(urgency: str) -> None:
    if urgency not in ("Routine", "Urgent", "Emergency"):
        raise ServiceError(ErrorCode.VALIDATION,
                           "VR-15-05: Mức độ khẩn cấp không hợp lệ")


def _vr_13_warehouse_active(warehouse: str) -> None:
    if frappe.db.get_value("AC Warehouse", warehouse, "is_active") == 0:
        raise ServiceError(ErrorCode.VALIDATION,
                           f"VR-15-13: Kho {warehouse} không còn hoạt động")


# ─── Scheduler Jobs (kept compatible with hooks.py) ──────────────────────────

def _seed_breach_capa(entry: dict) -> None:
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
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-15: _seed_breach_capa failed for {entry.get('spare_part')}")


def check_critical_spare_breach() -> None:
    """Daily 02:30 — scan watchlist, seed CAPA + email khẩn."""
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
            _seed_breach_capa(entry)
            try:
                frappe.publish_realtime("imm15_critical_breach", {
                    "watchlist": entry["name"], "asset": entry["critical_asset"],
                    "spare_part": entry["spare_part"], "qty": avail,
                })
            except Exception:
                pass
    if breach_entries:
        try:
            from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
            recipients = _get_role_emails(["Inventory Manager"])
            parts = ", ".join(e["spare_part"] for e in breach_entries)
            _safe_sendmail(
                recipients=recipients,
                subject=f"[KHẨN] {len(breach_entries)} phụ tùng critical dưới mức tối thiểu",
                message=f"<p>Các phụ tùng sau vi phạm mức tồn tối thiểu: <b>{parts}</b>.</p>",
            )
        except Exception:
            pass


def check_expiring_batches() -> None:
    """Daily 03:00 (gated)."""
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
        recipients = _get_role_emails(["Inventory Manager"])
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
    """Daily 04:00 — log KPI snapshot."""
    try:
        total_parts = frappe.db.count("AC Spare Part", {"is_active": 1})
        total_stock_value = frappe.db.sql(
            "SELECT COALESCE(SUM(qty_on_hand * unit_cost), 0) FROM `tabAC Spare Part Stock` s "
            "JOIN `tabAC Spare Part` p ON p.name = s.spare_part WHERE p.is_active = 1",
        )
        stock_value = float((total_stock_value or [[0]])[0][0])
        stockout_count = frappe.db.count("AC Spare Part Stock", {"qty_on_hand": ("<=", 0)})
        breach_count = len(CriticalWatchlistRepo.get_active_entries())
        frappe.logger("imm15").info(
            f"IMM-15 KPI snapshot: parts={total_parts}, stock_value={stock_value:.0f}, "
            f"stockout={stockout_count}, watchlist_active={breach_count}"
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-15: compute_inventory_kpis failed")


def generate_spare_demand_forecast() -> None:
    """Monthly 1st — tạo forecast Draft (Moving_Avg)."""
    try:
        generate_spare_forecast(horizon_months=3, method="Moving_Avg")
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "IMM-15: generate_spare_demand_forecast failed")


def reclassify_abc() -> None:
    """Cron quarterly — ABC reclassification dựa trên consumption value 12m."""
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
    """Hook IMM PM Work Order.before_submit — tạo allocation Requested từ planned spares."""
    try:
        planned_spares = getattr(doc, "imm_planned_spares", None) or []
        if not planned_spares:
            return
        items = [{"spare_part": row.spare_part, "qty_requested": row.qty}
                 for row in planned_spares if row.spare_part]
        if not items:
            return
        warehouse = frappe.db.get_value(
            "AC Spare Part Stock", {"spare_part": items[0]["spare_part"]}, "warehouse"
        ) or ""
        if not warehouse:
            return
        create_allocation(
            work_order_ref=doc.name, items=items,
            asset=getattr(doc, "asset_ref", "") or "",
            warehouse=warehouse, urgency="Routine",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-15: reserve_for_pm failed for {doc.name}")


def reserve_for_repair(doc, method=None) -> None:
    """Hook Asset Repair.before_submit — tạo allocation từ spare_parts_used."""
    try:
        spare_parts_used = getattr(doc, "spare_parts_used", None) or []
        if not spare_parts_used:
            return
        items = [{"spare_part": row.spare_part, "qty_requested": row.qty or 1}
                 for row in spare_parts_used if row.spare_part]
        if not items:
            return
        warehouse = frappe.db.get_value(
            "AC Spare Part Stock", {"spare_part": items[0]["spare_part"]}, "warehouse"
        ) or ""
        if not warehouse:
            return
        create_allocation(
            work_order_ref=doc.name, items=items,
            asset=getattr(doc, "asset_ref", "") or "",
            warehouse=warehouse, urgency="Urgent",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-15: reserve_for_repair failed for {doc.name}")


def flag_obsolete_on_decommission(doc, method=None) -> None:
    """Hook AC Asset.on_update — flag spare obsolete khi asset Decommissioned."""
    if not doc.has_value_changed("status"):
        return
    if doc.status != "Decommissioned":
        return
    try:
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
                frappe.db.set_value("AC Spare Part", lp.spare_part,
                                    "imm_obsolete_review_required", 1)
        if linked_parts:
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-15: flag_obsolete_on_decommission failed for {doc.name}")
