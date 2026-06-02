# Copyright (c) 2026, AssetCore Team
"""Unified dashboard overview across all IMM modules.

Trả về tổng hợp KPI, phân bổ trạng thái, và các danh sách gần đây cho toàn bộ
lifecycle HTM (IMM-00, 04, 05, 08, 09, 11) — phục vụ trang /dashboard.
"""
import frappe
from frappe.utils import today, add_days, now_datetime

from assetcore.utils.response import _ok, _err
from assetcore.services.imm00 import count_pending_approvals
from assetcore.services.imm08 import count_overdue_pm

# ─── Shared constants ────────────────────────────────────────────────────────
_DT_ASSET = "AC Asset"
_DT_COMM = "Asset Commissioning"
_STATUS_UNDER_REPAIR = "Under Repair"
_STATUS_OUT_OF_SERVICE = "Out of Service"
_OP_NOT_IN = "not in"


def _count(doctype: str, filters: dict = None) -> int:
    try:
        return frappe.db.count(doctype, filters=filters or {})
    except Exception:
        return 0


def _recent(doctype: str, fields: list[str], limit: int = 5, order_by: str = "modified desc", filters: dict = None) -> list[dict]:
    try:
        return frappe.get_all(doctype, filters=filters or {}, fields=fields, limit=limit, order_by=order_by) or []
    except Exception:
        return []


def _status_breakdown(doctype: str, status_field: str, values: list[str]) -> list[dict]:
    out = []
    for v in values:
        out.append({"state": v, "count": _count(doctype, {status_field: v})})
    return out


@frappe.whitelist()
def get_overview() -> dict:
    """GET /api/method/assetcore.api.dashboard.get_overview — Tổng quan toàn hệ thống."""
    try:
        today_str = today()
        next7 = add_days(today_str, 7)
        next30 = add_days(today_str, 30)

        # ── IMM-00: Thiết bị ─────────────────────────────────────────────────
        assets_total = _count(_DT_ASSET)
        assets_active = _count(_DT_ASSET, {"lifecycle_status": "Active"})
        assets_repair = _count(_DT_ASSET, {"lifecycle_status": _STATUS_UNDER_REPAIR})
        assets_calibrating = _count(_DT_ASSET, {"lifecycle_status": "Calibrating"})
        assets_out = _count(_DT_ASSET, {"lifecycle_status": _STATUS_OUT_OF_SERVICE})
        assets_decommissioned = _count(_DT_ASSET, {"lifecycle_status": "Decommissioned"})
        assets_byt_expiring = _count(_DT_ASSET, {"byt_reg_expiry": ["between", [today_str, next30]]})
        assets_byt_expired = _count(_DT_ASSET, {"byt_reg_expiry": ["<", today_str]})

        # ── IMM-04: Tiếp nhận ─────────────────────────────────────────────────
        comm_pending = _count(_DT_COMM, {"workflow_state": [_OP_NOT_IN, ["Clinical_Release", "Return_To_Vendor"]], "docstatus": ["!=", 2]})
        comm_released = _count(_DT_COMM, {"workflow_state": "Clinical_Release"})
        comm_hold = _count(_DT_COMM, {"workflow_state": "Clinical_Hold"})
        comm_open_nc = _count("Asset QA Non Conformance", {"status": ["!=", "Closed"]})

        # ── IMM-05: Hồ sơ ────────────────────────────────────────────────────
        doc_total = _count("Asset Document")
        doc_expiring = _count("Asset Document", {"expiry_date": ["between", [today_str, next30]]})
        # RC-08 (NextRound): KPI "Đã hết hạn" KHÔNG được filter theo workflow_state.
        # Phải đếm mọi doc có expiry_date < today **bất kể** Draft/Active/Expired —
        # vì doc Draft đã quá hạn vẫn là rủi ro pháp lý cần hiển thị lên KPI.
        doc_expired = _count("Asset Document", {"expiry_date": ["<", today_str]})
        doc_requests_open = _count("Document Request", {"status": [_OP_NOT_IN, ["Closed", "Fulfilled"]]})

        # ── IMM-08: PM ────────────────────────────────────────────────────────
        pm_open = _count("PM Work Order", {"status": [_OP_NOT_IN, ["Completed", "Cancelled"]]})
        # RC-10 (NextRound): "PM quá hạn" gọi single source of truth =
        # imm08.count_overdue_pm() để launcher widget, /pm/dashboard và endpoint
        # này không lệch nhau. WO status == "Overdue" được scheduler cron
        # `check_pm_overdue` set theo CLAUDE.md §11 (WO là operational record duy nhất).
        pm_overdue = count_overdue_pm()
        pm_due_next7 = _count("PM Work Order", {"status": [_OP_NOT_IN, ["Completed", "Cancelled"]], "due_date": ["between", [today_str, next7]]})
        pm_completed_30d = _count("PM Work Order", {"status": "Completed", "completion_date": [">=", add_days(today_str, -30)]})

        # ── IMM-09: CM / Sửa chữa ────────────────────────────────────────────
        cm_open = _count("Asset Repair", {"status": [_OP_NOT_IN, ["Completed", "Closed", "Cancelled"]]})
        cm_sla_breached = _count("Asset Repair", {"sla_breached": 1, "status": [_OP_NOT_IN, ["Completed", "Closed"]]})
        cm_repeat_failure = _count("Asset Repair", {"is_repeat_failure": 1})
        cm_completed_30d = _count("Asset Repair", {"status": "Completed", "completion_datetime": [">=", add_days(today_str, -30)]})

        # ── IMM-11: Hiệu chuẩn ───────────────────────────────────────────────
        # RC-R6 (root-cause): field đúng là `next_due_date`. Trước đây dùng
        # `next_calibration_date` (column KHÔNG tồn tại trên IMM Calibration
        # Schedule) → OperationalError bị try/except của get_overview nuốt im →
        # KPI calib_due/overdue âm thầm sai. SSOT cho drill-down date-window.
        calib_due = _count("IMM Calibration Schedule", {"next_due_date": ["between", [today_str, next30]]})
        calib_overdue = _count("IMM Calibration Schedule", {"next_due_date": ["<", today_str]})

        # ── Incident / CAPA ──────────────────────────────────────────────────
        incidents_open = _count("Incident Report", {"status": [_OP_NOT_IN, ["Closed", "Resolved"]]})
        incidents_critical = _count("Incident Report", {"severity": "Critical", "status": [_OP_NOT_IN, ["Closed", "Resolved"]]})
        # R8 §9.4.6 — phân bổ severity của incident MỞ cho donut click-through.
        # code = severity canonical (Critical/High/Medium/Low) → drill
        # /incidents/list?severity=<code>. Chỉ các mức canonical (loại null/khác).
        incident_severity_breakdown = [
            {"severity": sev, "code": sev, "label_vi": _SEVERITY_LABELS_VI[sev],
             "count": _count("Incident Report",
                             {"severity": sev, "status": [_OP_NOT_IN, ["Closed", "Resolved"]]})}
            for sev in ("Critical", "High", "Medium", "Low")
        ]
        capa_open = _count("IMM CAPA Record", {"status": [_OP_NOT_IN, ["Closed"]]})
        capa_overdue = _count("IMM CAPA Record", {"status": [_OP_NOT_IN, ["Closed"]], "due_date": ["<", today_str]})

        # ── Phân bổ lifecycle cho biểu đồ ──────────────────────────────────
        # Core Doc §9.1: mỗi entry mang 'code' = canonical lifecycle_status (English)
        # để FE donut segment-click drill tới /assets?lifecycle_status=<code>.
        # 'state' ở đây vốn đã English canonical → code = state. label_vi cho hiển thị.
        _lc_raw = [
            ("Commissioned", _count(_DT_ASSET, {"lifecycle_status": "Commissioned"})),
            ("Active", assets_active),
            (_STATUS_UNDER_REPAIR, assets_repair),
            ("Calibrating", assets_calibrating),
            (_STATUS_OUT_OF_SERVICE, assets_out),
            ("Decommissioned", assets_decommissioned),
        ]
        lifecycle_breakdown = [
            {"state": code, "code": code, "label_vi": _STATUS_LABELS_VI.get(code, code),
             "count": cnt}
            for code, cnt in _lc_raw
        ]

        # ── Các danh sách gần đây ────────────────────────────────────────────
        recent_incidents = _recent(
            "Incident Report",
            ["name", "asset", "severity", "status", "description", "reported_at"],
            limit=5, order_by="reported_at desc",
        )
        asset_ids = {r.get("asset") for r in recent_incidents if r.get("asset")}
        if asset_ids:
            amap = {a.name: a.asset_name for a in frappe.get_all(_DT_ASSET, filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"])}
            for r in recent_incidents:
                r["asset_name"] = amap.get(r.get("asset"), r.get("asset") or "")

        recent_pm = _recent(
            "PM Work Order",
            ["name", "asset_ref", "pm_type", "status", "due_date", "is_late"],
            limit=5, order_by="due_date asc",
            filters={"status": [_OP_NOT_IN, ["Completed", "Cancelled"]]},
        )
        pm_asset_ids = {r.get("asset_ref") for r in recent_pm if r.get("asset_ref")}
        if pm_asset_ids:
            amap = {a.name: a.asset_name for a in frappe.get_all(_DT_ASSET, filters={"name": ["in", list(pm_asset_ids)]}, fields=["name", "asset_name"])}
            for r in recent_pm:
                r["asset_name"] = amap.get(r.get("asset_ref"), r.get("asset_ref") or "")

        return _ok({
            "generated_at": str(now_datetime()),
            "assets": {
                "total": assets_total,
                "active": assets_active,
                "under_repair": assets_repair,
                "calibrating": assets_calibrating,
                "out_of_service": assets_out,
                "decommissioned": assets_decommissioned,
                "byt_expiring_30d": assets_byt_expiring,
                "byt_expired": assets_byt_expired,
            },
            "commissioning": {
                "pending": comm_pending,
                "released": comm_released,
                "hold": comm_hold,
                "open_nc": comm_open_nc,
            },
            "documents": {
                "total": doc_total,
                "expiring_30d": doc_expiring,
                "expired": doc_expired,
                "requests_open": doc_requests_open,
            },
            "pm": {
                "open": pm_open,
                "overdue": pm_overdue,
                "due_next_7d": pm_due_next7,
                "completed_30d": pm_completed_30d,
            },
            "cm": {
                "open": cm_open,
                "sla_breached": cm_sla_breached,
                "repeat_failure": cm_repeat_failure,
                "completed_30d": cm_completed_30d,
            },
            "calibration": {
                "due_30d": calib_due,
                "overdue": calib_overdue,
            },
            "incidents": {
                "open": incidents_open,
                "critical_open": incidents_critical,
            },
            "capa": {
                "open": capa_open,
                "overdue": capa_overdue,
            },
            "lifecycle_breakdown": lifecycle_breakdown,
            "incident_severity_breakdown": incident_severity_breakdown,
            "recent_incidents": recent_incidents,
            "recent_pm": recent_pm,
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Dashboard get_overview error")
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# HTM Command Center — API gộp 4 phần cho trang /dashboard (v2)
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_LABELS_VI = {
    "Active": "Đang hoạt động",
    _STATUS_UNDER_REPAIR: "Đang sửa chữa",
    "Under Maintenance": "Đang bảo trì",
    "Calibrating": "Đang hiệu chuẩn",
    _STATUS_OUT_OF_SERVICE: "Ngừng hoạt động",
    # Đồng bộ với FE constants/labels.ts + formatters.ts (chống drift donut↔list).
    "Commissioned": "Đã đưa vào sử dụng",
    "Decommissioned": "Đã thanh lý",
}

# R8 §9.4.6 — nhãn VI cho severity (đồng bộ SEVERITIES trong IncidentListView.vue,
# chống drift donut↔list). code canonical English giữ nguyên cho drill query.
_SEVERITY_LABELS_VI = {
    "Critical": "Nghiêm trọng",
    "High":     "Cao",
    "Medium":   "Trung bình",
    "Low":      "Thấp",
}

_STATUS_COLORS = {
    "Đang hoạt động":     "#10b981",
    "Đang sửa chữa":      "#ef4444",
    "Đang bảo trì":       "#f59e0b",
    "Đang hiệu chuẩn":    "#8b5cf6",
    "Ngừng hoạt động":    "#64748b",
    "Đã đưa vào sử dụng": "#3b82f6",
    "Đã thanh lý":        "#94a3b8",
}

# Core Doc §9.2 — đảo ngược _STATUS_LABELS_VI: nhãn VI → canonical lifecycle_status
# (English) mà AssetListView filter mong đợi. Một nguồn sự thật duy nhất, không
# hardcode chuỗi VI rời rạc. Dùng cho drill-down query (donut/KPI → /assets).
_VI_TO_CANONICAL = {vi: en for en, vi in _STATUS_LABELS_VI.items()}


def _canonical_status(label: str) -> str:
    """Map nhãn (VI hoặc đã canonical) → canonical lifecycle_status English.

    Nhãn VI → tra ngược; nhãn đã English (state canonical) → giữ nguyên;
    sentinel 'Chưa xác định'/unknown → giữ nguyên (FE hiện chip, list rỗng an toàn).
    """
    if label in _STATUS_LABELS_VI:        # đã là canonical English
        return label
    return _VI_TO_CANONICAL.get(label, label)


def _asset_drill(status_code: str) -> dict:
    """Core Doc §9.1 — drill descriptor tới AssetListView filtered theo lifecycle_status."""
    return {"route": "/assets", "query": {"lifecycle_status": status_code}}


def _drill(route: str, **query) -> dict:
    """Core Doc §9.1 — drill descriptor tổng quát (route + query canonical)."""
    return {"route": route, "query": {k: str(v) for k, v in query.items() if v}}


@frappe.whitelist()
def get_dashboard_data() -> dict:
    """GET /api/method/assetcore.api.dashboard.get_dashboard_data

    Trả về payload gộp 4 phần: KPI cards, donut chart, upcoming maintenance,
    active repairs — phục vụ trang HTM Command Center.
    """
    try:
        today_str = today()
        next30 = add_days(today_str, 30)

        # ── 1. KPI Metrics ────────────────────────────────────────────────────
        # RC-09 (NextRound): "Phiếu chờ duyệt" trên dashboard và /approvals/pending
        # phải đồng bộ. Dashboard widget mặc định scope="mine" (phiếu của tôi)
        # để khớp với list_my_pending_approvals. Trường `pending_commissioning_all`
        # giữ lại số global cho admin overview, FE quyết hiển thị field nào.
        kpi_metrics = {
            "total_assets":        _count(_DT_ASSET, {"docstatus": ["!=", 2]}),
            "under_repair":        _count(_DT_ASSET, {"lifecycle_status": _STATUS_UNDER_REPAIR}),
            "under_maintenance":   _count(_DT_ASSET, {"lifecycle_status": "Under Maintenance"}),
            "pending_commissioning": count_pending_approvals(scope="mine"),
            "pending_commissioning_all": count_pending_approvals(scope="all"),
            "overdue_pm":          count_overdue_pm(),
        }

        # ── 2. Donut chart: phân bổ trạng thái ───────────────────────────────
        status_rows = frappe.db.sql(
            """
            SELECT COALESCE(lifecycle_status, 'Chưa xác định') AS status, COUNT(*) AS cnt
            FROM `tabAC Asset`
            WHERE docstatus != 2
            GROUP BY lifecycle_status
            ORDER BY cnt DESC
            """,
            as_dict=True,
        ) or []
        labels, series, colors, codes = [], [], [], []
        for row in status_rows:
            raw = row["status"]                       # canonical English (hoặc 'Chưa xác định')
            label = _STATUS_LABELS_VI.get(raw, raw)   # nhãn VI hiển thị
            labels.append(label)
            series.append(int(row["cnt"] or 0))
            colors.append(_STATUS_COLORS.get(label, "#94a3b8"))
            # Core Doc §9.2: 'codes' canonical song song labels → FE emit code khi
            # click segment, route /assets?lifecycle_status=<code> (không nhãn VI).
            codes.append(_canonical_status(raw))
        asset_status_chart = {"labels": labels, "series": series, "colors": colors,
                              "codes": codes}

        # ── 3. Upcoming maintenance (PM + Calibration, ≤30 ngày) ────────────
        upcoming_rows = frappe.db.sql(
            """
            (SELECT s.asset_ref AS asset, a.asset_name, a.department,
                    COALESCE(d.department_name, a.department) AS department_name,
                    s.next_due_date AS due_date, 'PM' AS kind, s.pm_type AS detail
             FROM `tabPM Schedule` s
             JOIN `tabAC Asset` a ON a.name = s.asset_ref
             LEFT JOIN `tabAC Department` d ON d.name = a.department
             WHERE s.status = 'Active'
               AND s.next_due_date BETWEEN %(today)s AND %(next30)s)
            UNION ALL
            (SELECT c.asset AS asset, a.asset_name, a.department,
                    COALESCE(d.department_name, a.department) AS department_name,
                    c.next_due_date AS due_date, 'Hiệu chuẩn' AS kind, c.calibration_type AS detail
             FROM `tabIMM Calibration Schedule` c
             JOIN `tabAC Asset` a ON a.name = c.asset
             LEFT JOIN `tabAC Department` d ON d.name = a.department
             WHERE c.is_active = 1
               AND c.next_due_date BETWEEN %(today)s AND %(next30)s)
            ORDER BY due_date ASC
            LIMIT 10
            """,
            {"today": today_str, "next30": next30},
            as_dict=True,
        ) or []
        for r in upcoming_rows:
            d = r.get("due_date")
            r["due_date"] = str(d) if d else ""
            r["days_until"] = (d - frappe.utils.getdate(today_str)).days if d else None

        # ── 4. Active repairs (đang sửa chữa) ──────────────────────────────
        repair_rows = frappe.db.sql(
            """
            SELECT r.name, r.asset_ref AS asset, a.asset_name, a.department,
                   COALESCE(d.department_name, a.department) AS department_name,
                   r.status, r.priority, r.open_datetime,
                   TIMESTAMPDIFF(DAY, r.open_datetime, NOW()) AS downtime_days
            FROM `tabAsset Repair` r
            LEFT JOIN `tabAC Asset` a ON a.name = r.asset_ref
            LEFT JOIN `tabAC Department` d ON d.name = a.department
            WHERE r.status NOT IN ('Completed', 'Closed', 'Cancelled', 'Cannot Repair')
            ORDER BY r.open_datetime ASC
            LIMIT 20
            """,
            as_dict=True,
        ) or []
        for r in repair_rows:
            r["open_datetime"] = str(r["open_datetime"]) if r.get("open_datetime") else ""
            r["downtime_days"] = int(r["downtime_days"] or 0)

        return _ok({
            "generated_at":        str(now_datetime()),
            "kpi_metrics":         kpi_metrics,
            "asset_status_chart":  asset_status_chart,
            "upcoming_maintenance": upcoming_rows,
            "active_repairs":      repair_rows,
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_dashboard_data error")
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Persona dashboards — Core Doc: docs/architecture/FE_Persona_Dashboards.md
#
# Một endpoint trả layout + data theo persona. Mọi giá trị LẤY TỪ service thật
# (KHÔNG hardcode — CLAUDE.md "dashboard phải truy về source"). Persona KHÔNG phải
# security boundary: count/list đi qua frappe.get_all / service function tôn trọng
# DocPerm → user thiếu quyền nhận 0/rỗng, không leak.
# ─────────────────────────────────────────────────────────────────────────────

_VALID_PERSONAS = {
    "admin", "opsmgr", "workshop", "tech", "clinical", "doc", "store", "qa",
}


def _kpi(key: str, label_vi: str, value, foot_vi: str = "", tone: str = "info",
         drill: dict | None = None) -> dict:
    """Chuẩn hoá 1 KPI card (Core Doc §3 + §9.1). tone ∈ {primary,info,ok,warn,danger}.

    drill (optional, Core Doc §9.1): {route, query} → FE render RouterLink click-through
    tới list view đã pre-apply filter. None = card tĩnh (không drill được).
    """
    return {"key": key, "label_vi": label_vi, "value": value, "foot_vi": foot_vi,
            "tone": tone, "drill": drill}


def _overview_payload() -> dict:
    """Bóc data từ envelope get_overview() để tái sử dụng nội bộ (1 lần gọi)."""
    resp = get_overview()
    return resp.get("data") or {} if isinstance(resp, dict) else {}


def _current_dept() -> str | None:
    """Phòng/khoa của user hiện tại (clinical scope). Đọc field thật, None nếu trống."""
    try:
        emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "department")
        if emp:
            return emp
        # Fallback: custom field ac_department trên User (nếu có)
        return frappe.db.get_value("User", frappe.session.user, "ac_department")
    except Exception:
        return None


# ── Builders per persona ─────────────────────────────────────────────────────

def _build_opsmgr(ov: dict) -> dict:
    a, pm, inc, capa = ov.get("assets", {}), ov.get("pm", {}), ov.get("incidents", {}), ov.get("capa", {})
    # NR "chờ duyệt": Draft (docstatus=0) chưa trình BGĐ. board_approver chưa set.
    needs_pending = _count("IMM Needs Request", {"docstatus": 0})

    from assetcore.services.imm09 import get_kpis as cm_kpis
    dt = frappe.utils.getdate(today())
    mk = cm_kpis(dt.year, dt.month).get("kpis", {})

    kpis = [
        # §9.4: click → /assets?lifecycle_status=Active (canonical code, không VI).
        _kpi("active_assets", "Thiết bị đang hoạt động", a.get("active", 0),
             f"Tổng {a.get('total', 0)}", "primary", drill=_asset_drill("Active")),
        # §9.4.3 (R6): date-window drill → /pm/work-orders?due_before=today+7.
        _kpi("pm_due_7d", "PM đến hạn 7 ngày", pm.get("due_next_7d", 0),
             f"{pm.get('overdue', 0)} quá hạn", "warn",
             drill=_drill("/pm/work-orders", due_before=add_days(today(), 7))),
        # §9.4.1: click → /incidents/list?severity=Critical (list tập bao KPI compound).
        _kpi("incidents_critical", "Sự cố mở (Critical)", inc.get("critical_open", 0),
             f"{inc.get('open', 0)} sự cố mở", "danger",
             drill={"route": "/incidents/list", "query": {"severity": "Critical"}}),
        _kpi("needs_pending", "Đề xuất chờ duyệt", needs_pending, "Chưa phê duyệt", "info"),
    ]
    return {
        "kpis": kpis,
        "sections": {
            "asset_status_breakdown": ov.get("lifecycle_breakdown", []),
            # R8 §9.4.6 — severity donut click-through tới /incidents/list?severity=<code>.
            "incident_severity_breakdown": ov.get("incident_severity_breakdown", []),
            "maintenance_kpi": {
                "mttr_avg_hours": mk.get("mttr_avg_hours", 0),
                "sla_compliance_pct": mk.get("sla_compliance_pct", 0),
                "open_wos": mk.get("open_wos", 0),
                "repeat_failure_count": mk.get("repeat_failure_count", 0),
                # R8 §9.4.6 — bar-card drill: SLA → CM list vi phạm SLA;
                # open_wos / repeat → CM list filtered. MTTR là metric thời lượng
                # (không có list 1-1) → KHÔNG drill (canonical-value rule §9.5 #10).
                "drills": {
                    "sla_compliance_pct": _drill("/cm/work-orders", sla_breached="1"),
                    "open_wos": _drill("/cm/work-orders", status="Open"),
                    "repeat_failure_count": _drill("/cm/work-orders", is_repeat_failure="1"),
                },
            },
            "recent_events": ov.get("recent_incidents", []),
            "recent_pm": ov.get("recent_pm", []),
        },
    }


def _build_workshop(ov: dict) -> dict:
    pm, cm, calib = ov.get("pm", {}), ov.get("cm", {}), ov.get("calibration", {})
    from assetcore.services.imm09 import get_kpis as cm_kpis
    from assetcore.services.imm06 import list_user_competencies
    dt = frappe.utils.getdate(today())
    mk = cm_kpis(dt.year, dt.month).get("kpis", {})
    sla_pct = mk.get("sla_compliance_pct", 0)

    comp = list_user_competencies({}, page=1, page_size=10).get("data", [])
    wo_to_assign = _recent(
        "PM Work Order", ["name", "asset_ref", "pm_type", "status", "due_date"],
        limit=10, order_by="due_date asc",
        filters={"status": [_OP_NOT_IN, ["Completed", "Cancelled"]]},
    )
    _enrich_asset_name(wo_to_assign, "asset_ref")

    kpis = [
        # §9.4.7 (R9): COMPOUND (PM open + CM open, 2 doctype) → KHÔNG drill 1-list
        # (sẽ lệch count, vi phạm §9.5 #10). Section table 'wo_to_assign' bên dưới
        # liệt kê chi tiết PM WO. drill=None (card tĩnh, canonical-value rule).
        _kpi("wo_to_assign", "WO chờ phân công", pm.get("open", 0) + cm.get("open", 0),
             f"{pm.get('open', 0)} PM · {cm.get('open', 0)} CM", "info"),
        # §9.4.7 (R9): click → /cm/work-orders?sla_breached=1 (list tập bao KPI).
        _kpi("cm_sla_breached", "SLA vi phạm", cm.get("sla_breached", 0),
             f"SLA tuân thủ {sla_pct}%", "danger",
             drill=_drill("/cm/work-orders", sla_breached="1")),
        # §9.4.2: click → /pm/work-orders?status=Overdue (status canonical khớp WO).
        _kpi("pm_overdue", "PM quá hạn", pm.get("overdue", 0),
             f"{pm.get('due_next_7d', 0)} đến hạn 7 ngày", "warn",
             drill=_drill("/pm/work-orders", status="Overdue")),
        # §9.4.3 (R6): date-window drill. calib_due/overdue đếm theo
        # next_due_date (KHÔNG có status để ép) → drill bằng cửa sổ ngày để
        # list khớp KPI (tránh 'lệch count'). due_before=today+30; overdue=1.
        _kpi("calib_due", "Hiệu chuẩn đến hạn", calib.get("due_30d", 0),
             f"{calib.get('overdue', 0)} quá hạn", "ok",
             drill=_drill("/calibration/schedules", due_before=add_days(today(), 30))),
    ]
    return {
        "kpis": kpis,
        "sections": {
            "wo_to_assign": wo_to_assign,
            "tech_competency": comp,
            "calibration": calib,
        },
    }


def _build_tech(ov: dict) -> dict:
    me = frappe.session.user
    from assetcore.services.imm15 import list_allocations
    my_wo = _recent(
        "PM Work Order", ["name", "asset_ref", "pm_type", "status", "due_date"],
        limit=10, order_by="due_date asc",
        filters={"assigned_to": me, "status": [_OP_NOT_IN, ["Completed", "Cancelled"]]},
    )
    _enrich_asset_name(my_wo, "asset_ref")
    my_cm = _recent(
        "Asset Repair", ["name", "asset_ref", "status", "priority", "open_datetime"],
        limit=10, order_by="open_datetime desc",
        filters={"assigned_to": me, "status": [_OP_NOT_IN, ["Completed", "Closed", "Cancelled"]]},
    )
    _enrich_asset_name(my_cm, "asset_ref")
    my_reqs = list_allocations({"requested_by": me}, page=1, page_size=10).get("data", [])

    pm_today = _count("PM Work Order", {"assigned_to": me, "due_date": today(), "status": [_OP_NOT_IN, ["Completed", "Cancelled"]]})
    pm_week = _count("PM Work Order", {"assigned_to": me, "due_date": ["between", [today(), add_days(today(), 7)]], "status": [_OP_NOT_IN, ["Completed", "Cancelled"]]})
    cm_urgent = _count("Asset Repair", {"assigned_to": me, "priority": "P1", "status": [_OP_NOT_IN, ["Completed", "Closed", "Cancelled"]]})
    done_30d = _count("PM Work Order", {"assigned_to": me, "status": "Completed", "completion_date": [">=", add_days(today(), -30)]})

    kpis = [
        _kpi("today_jobs", "Việc hôm nay", pm_today + len(my_cm), f"{len(my_cm)} CM mở", "info"),
        _kpi("pm_week", "PM trong tuần", pm_week, "", "warn"),
        _kpi("cm_urgent", "CM khẩn cấp", cm_urgent, "P1 - Critical", "danger"),
        _kpi("done_30d", "Hoàn tất 30 ngày", done_30d, "", "ok"),
    ]
    return {
        "kpis": kpis,
        "sections": {"my_wo_today": my_wo, "my_cm": my_cm, "my_spare_requests": my_reqs},
    }


def _build_clinical(ov: dict) -> dict:
    dept = _current_dept()
    dept_configured = bool(dept)
    # Fail-CLOSED: clinical persona scope theo khoa. Nếu user chưa gắn khoa
    # (_current_dept→None), KHÔNG được bỏ filter → sẽ leak data toàn viện gắn
    # nhãn "khoa mình" (vượt ranh giới role, Core Doc §5.5). Khi không có khoa,
    # mọi count/list scope rỗng và FE hiển thị trạng thái "chưa gắn khoa".
    if not dept_configured:
        kpis = [
            _kpi("dept_assets", "Thiết bị khoa", 0, "", "primary"),
            _kpi("inc_open", "Sự cố đang xử lý", 0, "", "danger"),
            _kpi("nr_submitted", "Đề xuất đã nộp", 0, "", "info"),
            _kpi("awaiting_release", "Chờ nghiệm thu", _count(_DT_COMM, {"workflow_state": "Clinical_Hold"}), "", "warn"),
        ]
        return {
            "kpis": kpis,
            "sections": {
                "dept_incidents": [], "dept_needs": [],
                "department": "", "dept_configured": False,
            },
        }

    # AC Asset có field department; Incident Report KHÔNG có department trực tiếp →
    # scope incident theo các asset thuộc khoa (lấy danh sách asset của khoa).
    dept_assets_ids: list[str] = [r["name"] for r in frappe.get_all(
        _DT_ASSET, filters={"department": dept}, fields=["name"])]
    assets_dept = len(dept_assets_ids)

    # Khoa có thể chưa có asset nào → match nothing (sentinel) thay vì bỏ filter.
    inc_asset_filter = {"asset": ["in", dept_assets_ids or ["__none__"]]}
    inc_open = _count("Incident Report", {**inc_asset_filter, "status": [_OP_NOT_IN, ["Closed", "Resolved"]]})
    nr_submitted = _count("IMM Needs Request", {"requesting_department": dept, "docstatus": 1})
    awaiting = _count(_DT_COMM, {"workflow_state": "Clinical_Hold"})

    dept_incidents = _recent(
        "Incident Report", ["name", "asset", "severity", "status", "reported_at"],
        limit=8, order_by="reported_at desc",
        filters={**inc_asset_filter, "status": [_OP_NOT_IN, ["Closed", "Resolved"]]},
    )
    _enrich_asset_name(dept_incidents, "asset")
    dept_needs = _recent(
        "IMM Needs Request", ["name", "device_model_ref", "priority_class", "workflow_state"],
        limit=8, order_by="modified desc",
        filters={"requesting_department": dept, "docstatus": ["!=", 2]},
    )

    kpis = [
        _kpi("dept_assets", "Thiết bị khoa", assets_dept, "", "primary"),
        _kpi("inc_open", "Sự cố đang xử lý", inc_open, "", "danger"),
        _kpi("nr_submitted", "Đề xuất đã nộp", nr_submitted, "", "info"),
        _kpi("awaiting_release", "Chờ nghiệm thu", awaiting, "", "warn"),
    ]
    return {
        "kpis": kpis,
        "sections": {
            "dept_incidents": dept_incidents, "dept_needs": dept_needs,
            "department": dept, "dept_configured": True,
        },
    }


def _build_doc(ov: dict) -> dict:
    d, comm = ov.get("documents", {}), ov.get("commissioning", {})
    docs_expiring = _recent(
        "Asset Document", ["name", "doc_category", "doc_type_detail", "asset_ref", "expiry_date", "workflow_state"],
        limit=10, order_by="expiry_date asc",
        filters={"expiry_date": ["between", [today(), add_days(today(), 90)]]},
    )
    _enrich_asset_name(docs_expiring, "asset_ref")
    comm_queue = _recent(
        _DT_COMM, ["name", "asset", "workflow_state", "modified"],
        limit=10, order_by="modified desc",
        filters={"workflow_state": [_OP_NOT_IN, ["Clinical_Release", "Return_To_Vendor"]], "docstatus": ["!=", 2]},
    )
    _enrich_asset_name(comm_queue, "asset")

    kpis = [
        _kpi("docs_pending", "Tài liệu chờ duyệt", d.get("requests_open", 0), "", "info"),
        _kpi("docs_expiring", "Sắp hết hạn (30 ngày)", d.get("expiring_30d", 0),
             f"{d.get('expired', 0)} đã hết hạn", "warn"),
        _kpi("comm_pending", "Nghiệm thu đang xử lý", comm.get("pending", 0), "", "primary"),
        _kpi("comm_open_nc", "NC mở", comm.get("open_nc", 0), "Cần xử lý trước nghiệm thu", "danger"),
    ]
    return {"kpis": kpis, "sections": {"docs_expiring": docs_expiring, "commissioning_queue": comm_queue}}


def _build_store(ov: dict) -> dict:
    from assetcore.services.imm15 import get_dashboard_stats, get_low_stock_alerts, list_allocations
    stats = get_dashboard_stats()
    low = get_low_stock_alerts().get("alerts", [])
    pending = list_allocations({"allocation_status": ["in", ["Requested", "Approved"]]}, page=1, page_size=10).get("data", [])

    kpis = [
        # §9.4.5 (R7): click → /spare-parts?low_stock=1 (parts dưới định mức).
        _kpi("low_stock", "Dưới định mức", stats.get("low_stock_alerts", 0), "Cần đặt hàng", "danger",
             drill=_drill("/spare-parts", low_stock="1")),
        _kpi("pending_alloc", "Cấp phát đang xử lý", stats.get("pending_allocations", 0), "", "warn"),
        _kpi("pending_cycle", "Kiểm kê đang đếm", stats.get("pending_cycle_counts", 0), "", "info"),
        _kpi("stockout_30d", "Hết hàng 30 ngày",
             (stats.get("stockout_incidents_30d") or {}).get("value", 0), "", "primary"),
    ]
    return {"kpis": kpis, "sections": {"below_min": low, "pending_allocations": pending}}


def _build_qa(ov: dict) -> dict:
    capa = ov.get("capa", {})
    from assetcore.services.imm16 import (
        get_current_scorecard, list_compliance_findings, list_internal_audits,
    )
    sc = get_current_scorecard()
    # Scorecard field điểm tổng: thử các tên field phổ biến, KHÔNG bịa số.
    score = None
    if sc.get("exists") is not False:
        score = sc.get("overall_score") or sc.get("score") or sc.get("total_score")
    # RCA chưa hoàn tất: incident yêu cầu RCA nhưng chưa có root_cause_summary.
    rca_incomplete = _count("Incident Report", {
        "status": [_OP_NOT_IN, ["Closed", "Resolved"]],
        "rca_required": 1, "root_cause_summary": ["in", ["", None]],
    })

    findings = list_compliance_findings({"status": [_OP_NOT_IN, ["Closed"]]}, page=1, page_size=10).get("data", [])
    audits = list_internal_audits({}, page=1, page_size=8).get("data", [])
    capa_rows = _recent(
        "IMM CAPA Record", ["name", "source_ref", "severity", "status", "due_date"],
        limit=10, order_by="due_date asc",
        filters={"status": [_OP_NOT_IN, ["Closed"]]},
    )

    kpis = [
        # §9.4.8 (R10): date-window drill (overdue=1) → /capas?overdue=1 (khớp KPI).
        _kpi("capa_overdue", "CAPA quá hạn", capa.get("overdue", 0), "", "danger",
             drill=_drill("/capas", overdue="1")),
        # §9.4.8 (R10): not_closed=1 → /capas?not_closed=1 (status NOT IN Closed, khớp KPI).
        _kpi("capa_open", "CAPA đang xử lý", capa.get("open", 0), "", "warn",
             drill=_drill("/capas", not_closed="1")),
        # §9.4.8 (R10): predicate compound chuyên biệt (mở AND rca_required AND
        # root_cause_summary trống) — không có list filter 1-1 chung → KHÔNG drill
        # (canonical-value rule §9.5 #10). Section 'capa_todo'/findings backing.
        _kpi("rca_incomplete", "RCA chưa hoàn tất", rca_incomplete, "Critical/Chronic", "info"),
        _kpi("compliance_score", "Điểm tuân thủ", score,
             "Chưa có scorecard kỳ này" if score is None else "Mục tiêu ≥ 85", "ok"),
    ]
    return {
        "kpis": kpis,
        "sections": {"capa_todo": capa_rows, "compliance_findings": findings, "internal_audits": audits},
    }


def _build_admin(ov: dict) -> dict:
    total_users = _count("User", {"enabled": 1})
    disabled_users = _count("User", {"enabled": 0})
    # Pending: custom field imm_registration_status nếu có; fallback 0 (đọc thật, không bịa)
    try:
        pending_users = _count("User", {"imm_registration_status": "Pending"})
    except Exception:
        pending_users = 0
    vendor_engineers = _count("Has Role", {"role": "Vendor Engineer"})

    # Audit-chain status: verify từ utils.lifecycle nếu có verifier; nếu không → None.
    audit_status = None
    try:
        from assetcore.utils.lifecycle import verify_audit_chain  # type: ignore
        audit_status = "PASS" if verify_audit_chain() else "FAIL"
    except Exception:
        audit_status = None  # KHÔNG bịa "PASS" — để FE hiển thị "—"

    users_pending = _recent(
        "User", ["name", "full_name", "email", "creation"],
        limit=10, order_by="creation desc",
        filters={"enabled": 0},
    )
    audit_recent = ov.get("recent_incidents", [])

    # R1 §9.4.9 — admin (data.admin) drill: KPI người-dùng → /user-profiles filtered;
    # audit_chain (status PASS/FAIL, không phải tập record) → mở /audit-trail viewer.
    # query canonical (approval_status=Pending, role=Vendor Engineer) khớp filter list.
    kpis = [
        _kpi("total_users", "Tổng người dùng", total_users,
             f"{disabled_users} vô hiệu · {pending_users} chờ duyệt", "primary",
             drill=_drill("/user-profiles")),
        _kpi("pending_users", "Chờ phê duyệt", pending_users, "Đăng ký mới", "warn",
             drill=_drill("/user-profiles", approval_status="Pending")),
        _kpi("audit_chain", "Chuỗi audit", audit_status if audit_status is not None else "—",
             "Kiểm tra tính toàn vẹn", "ok", drill=_drill("/audit-trail")),
        _kpi("vendor_engineers", "Vendor Engineer", vendor_engineers, "Bên thứ ba, cô lập", "info",
             drill=_drill("/user-profiles", role="Vendor Engineer")),
    ]
    return {"kpis": kpis, "sections": {"users_pending": users_pending, "audit_recent": audit_recent}}


def _enrich_asset_name(rows: list[dict], asset_field: str) -> None:
    """Batch-enrich asset_name cho danh sách rows (tránh N+1) — LL-BE-2."""
    ids = {r.get(asset_field) for r in rows if r.get(asset_field)}
    if not ids:
        return
    amap = {a.name: a.asset_name for a in frappe.get_all(
        _DT_ASSET, filters={"name": ["in", list(ids)]}, fields=["name", "asset_name"])}
    for r in rows:
        r["asset_name"] = amap.get(r.get(asset_field), r.get(asset_field) or "")


_PERSONA_BUILDERS = {
    "opsmgr": _build_opsmgr,
    "workshop": _build_workshop,
    "tech": _build_tech,
    "clinical": _build_clinical,
    "doc": _build_doc,
    "store": _build_store,
    "qa": _build_qa,
    "admin": _build_admin,
}


@frappe.whitelist()
def get_persona_dashboard(persona: str | None = None) -> dict:
    """GET /api/method/assetcore.api.dashboard.get_persona_dashboard?persona=<code>

    Trả layout + data theo persona (Core Doc FE_Persona_Dashboards.md §3-§5).
    Persona không hợp lệ → payload rỗng an toàn (KHÔNG raise).

    LL-BE-1: type-hint là `str | None` (không `str = ""`) để Frappe v15
    `validate_argument_types` KHÔNG raise FrappeTypeError → HTTP 417 khi
    query param vắng/null (`persona=None`). Body normalize None → "" an toàn.
    """
    try:
        persona = (persona or "").strip().lower()
        if persona not in _VALID_PERSONAS:
            return _ok({"persona": persona, "generated_at": str(now_datetime()),
                        "kpis": [], "sections": {}})

        # get_overview() cung cấp phần lớn aggregate; gọi 1 lần, share cho builder.
        ov = _overview_payload()
        builder = _PERSONA_BUILDERS[persona]
        built = builder(ov)
        return _ok({
            "persona": persona,
            "generated_at": str(now_datetime()),
            "kpis": built.get("kpis", []),
            "sections": built.get("sections", {}),
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_persona_dashboard error")
        return _err(str(e))
