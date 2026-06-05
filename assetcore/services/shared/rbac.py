# Copyright (c) 2026, AssetCore Team
"""RBAC capability layer — code hoi capability, KHONG so ten role.

Binding capability -> (DocType, ptype) o day; quyen that do DocPerm/Workflow
(data) quyet dinh qua frappe.has_permission. Doi quyen = sua DocPerm o /app,
khong deploy.
"""
from __future__ import annotations

import frappe

# Map DocType -> domain word (hoac _shared / _audit)
# Nguon: docs/res/rbac/role-redesign-module-based.md §5
_DOMAIN_DOCTYPES: dict[str, list[str]] = {
    "Data": ["AC Asset Category", "AC Department", "AC Location", "AC Supplier",
        "AC UOM", "AC UOM Conversion", "IMM Device Model", "IMM Device Spare Part",
        "AC Authorized Technician", "Service Contract", "Service Contract Asset",
        "Required Document Type", "IMM SLA Policy"],
    "Needs": ["IMM Needs Request", "Needs Priority Scoring", "IMM Demand Forecast",
        "Forecast Driver", "Budget Estimate Line", "IMM Procurement Plan",
        "Procurement Plan Line"],
    "Spec": ["IMM Tech Spec", "Tech Spec Document", "Tech Spec Requirement",
        "IMM Market Benchmark", "Benchmark Candidate", "Infra Compatibility Item",
        "IMM Lock In Risk Assessment", "Lock In Risk Item"],
    "Procurement": ["IMM Vendor Evaluation", "Vendor Eval Candidate",
        "Vendor Eval Criterion", "IMM Vendor Scorecard", "IMM AVL Entry",
        "IMM Procurement Decision", "IMM Supplier Audit", "Vendor Quotation Line",
        "Vendor Cert", "AC Purchase", "AC Purchase Item", "AC Purchase Device Item"],
    "Commissioning": ["Asset Commissioning", "Commissioning Checklist",
        "Commissioning Document Record", "Asset Transfer", "Asset Decommission"],
    "Document": ["Asset Document", "Document Request", "Expiry Alert Log"],
    "Training": ["IMM Training Program", "IMM Training Session",
        "IMM Training Participant", "IMM Trainer", "IMM User Competency",
        "IMM Competency Alert Log", "IMM Competency Gap Report", "IMM Gap Detail Row"],
    "PM": ["PM Work Order", "PM Schedule", "PM Task Log", "PM Checklist Template",
        "PM Checklist Item", "PM Checklist Result"],
    "Repair": ["Asset Repair", "Repair Checklist", "Spare Parts Used",
        "Firmware Change Request"],
    "Calibration": ["IMM Asset Calibration", "IMM Calibration Schedule",
        "IMM Calibration Measurement"],
    "Corrective": ["Incident Report", "IMM RCA Record", "IMM RCA Five Why Step",
        "IMM RCA Related Incident", "Asset QA Non Conformance"],
    "Inventory": ["AC Spare Part", "AC Spare Part Stock", "AC Stock Movement",
        "AC Stock Movement Item", "AC Warehouse", "IMM Spare Allocation",
        "IMM Spare Allocation Item", "IMM Spare Alternative", "IMM Spare Batch",
        "IMM Spare Part Forecast", "IMM Spare Forecast Item",
        "IMM Critical Spare Watchlist", "IMM Stock Cycle Count",
        "IMM Stock Cycle Count Item", "IMM Cycle Count Item"],
    "Compliance": ["IMM Compliance Finding", "IMM Compliance Rule",
        "IMM Compliance Scorecard", "IMM Scorecard Department Row",
        "IMM Scorecard Module Row", "Scorecard Kpi Row", "IMM CAPA Record",
        "IMM CAPA Action Step", "IMM Internal Audit", "IMM Audit Checklist Item",
        "Audit Finding", "IMM Management Review", "IMM MR Attendee",
        "IMM MR Output Action"],
    "_shared": ["AC Asset", "Asset Lifecycle Event",
        "AC Asset Depreciation Schedule", "AC Asset Downtime Log"],
    "_audit": ["IMM Audit Trail"],
}

DOMAIN_DOCTYPES = _DOMAIN_DOCTYPES
DOCTYPE_DOMAIN: dict[str, str] = {
    dt: dom for dom, dts in _DOMAIN_DOCTYPES.items() for dt in dts
}

# Dai dien 1 DocType chinh cho moi domain (de resolve cap CRUD)
_DOMAIN_PRIMARY: dict[str, str] = {
    "Data": "IMM Device Model", "Needs": "IMM Needs Request",
    "Spec": "IMM Tech Spec", "Procurement": "IMM Vendor Evaluation",
    "Commissioning": "Asset Commissioning", "Document": "Asset Document",
    "Training": "IMM Training Program", "PM": "PM Work Order",
    "Repair": "Asset Repair", "Calibration": "IMM Asset Calibration",
    "Corrective": "Incident Report", "Inventory": "AC Stock Movement",
    "Compliance": "IMM CAPA Record",
    # ADR-001-asset-qr D4: AC Asset registry (IMM-00) cần capability prefix
    # `asset.*` ĐỘC LẬP để gate QR deep-link resolve (`asset.read`) + in/regenerate
    # label (`asset.write`) THEO DocPerm AC Asset, KHÔNG hardcode role-name (chống
    # RBAC dead-gate). _shared (line 55) và _DOMAIN_PRIMARY là 2 map độc lập — AC
    # Asset ở cả hai KHÔNG xung đột: _shared chỉ map DocType→domain cho audit/scope,
    # _DOMAIN_PRIMARY sinh CAPABILITY_MAP prefix. Thêm 6 cap asset.{read,write,
    # create,delete,submit,cancel} → CAP_SET_VERSION đổi → FE auto-invalidate
    # persisted-caps stale (lesson IMM-14) + after_migrate invalidate_capabilities().
    "Asset": "AC Asset",
}

_PTYPES = ("read", "write", "create", "delete", "submit", "cancel")

CAPABILITY_MAP: dict[str, tuple[str, str]] = {}
for _dom, _dt in _DOMAIN_PRIMARY.items():
    _prefix = _dom.lower()
    for _pt in _PTYPES:
        CAPABILITY_MAP[f"{_prefix}.{_pt}"] = (_dt, _pt)

CAPABILITY_MAP.update({
    "pm.reschedule":        ("PM Work Order", "write"),
    "incident.acknowledge": ("Incident Report", "write"),
    "incident.close":       ("Incident Report", "submit"),
    "cal.send_lab":         ("IMM Asset Calibration", "write"),
    "doc.approve":          ("Asset Document", "submit"),
    "capa.close":           ("IMM CAPA Record", "submit"),
    "data.admin":           ("IMM Device Model", "delete"),
    "audit.read":           ("IMM Audit Trail", "read"),
    # R18 FIX: auto-gen trỏ training.submit -> (IMM Training Program,"submit"),
    # nhưng Program/Session đều is_submittable=0 → "submit" permtype không bao giờ
    # resolve True → toàn bộ manager-action IMM-06 (confirm/verify/close session +
    # competency sign-off) chết trên UI cho MỌI user. Phân biệt Manager/User intended
    # nằm ở DocPerm "delete" trên IMM Training Session (Manager delete=1, User=0),
    # và "delete" resolve được trên doctype non-submittable.
    "training.submit":      ("IMM Training Session", "delete"),
    # IMM-14 Giải nhiệm thiết bị: tạo hồ sơ = create, duyệt (giải nhiệm) = submit.
    # Gate theo CAPABILITY THẬT (DocPerm trên Asset Decommission), KHÔNG hardcode
    # role-name (tránh anti-pattern RBAC dead-gate).
    "decommission.read":    ("Asset Decommission", "read"),
    "decommission.create":  ("Asset Decommission", "create"),
    "decommission.approve": ("Asset Decommission", "submit"),
})


# ── Cap-set version stamp (AC4) ────────────────────────────────────────────────
# Hash on dinh theo NOI DUNG sorted(CAPABILITY_MAP keys). Khi them/bo cap (vd
# decommission.*) → version DOI → FE phat hien persisted-caps cu da stale va
# invalidate truoc khi render gate-button (KHONG can xoa localStorage tay).
# Backward-compat: them vao caps dict duoi khoa rieng CAP_VERSION_KEY (gia tri
# str, KHONG phai bool) → consumer cu doc caps[x] is True KHONG bi anh huong.
# BE-FE naming contract: FE store (auth.ts splitCapVersion) tach key NAY ra khoi
# cap-map boolean → DUNG `__cap_version` (KHONG `__version__`, tranh va app version).
CAP_VERSION_KEY = "__cap_version"


def _compute_cap_set_version() -> str:
    import hashlib

    keys = ",".join(sorted(CAPABILITY_MAP))
    digest = hashlib.sha256(keys.encode("utf-8")).hexdigest()[:12]
    # Prefix so cap de doc nhanh khi debug; hash dam bao doi-ten-cap cung doi version.
    return f"v{len(CAPABILITY_MAP)}.{digest}"


CAP_SET_VERSION: str = _compute_cap_set_version()


def can(cap: str, doc=None) -> bool:
    """True neu user hien tai co quyen tuong ung capability.

    Stale-safe (USER REWORK IMM-14, 2026-06-04): cap KHONG co trong
    CAPABILITY_MAP → DENY (return False), KHONG raise KeyError. Worker
    gunicorn cu (chua co cap moi trong RAM) phai degrade thanh "nut an / 403",
    KHONG "loi server 500". require() ke thua → PermissionError thay vi KeyError.
    """
    binding = CAPABILITY_MAP.get(cap)
    if binding is None:
        return False
    dt, ptype = binding
    return bool(frappe.has_permission(dt, ptype, doc=doc))


def require(cap: str, doc=None) -> None:
    """Chan cung o BE — goi dau moi whitelisted method nhay cam."""
    if not can(cap, doc):
        frappe.throw(
            frappe._("Khong du quyen: {0}").format(cap),
            frappe.PermissionError,
        )


def _cache_key(user: str) -> str:
    return f"ac_caps::{user}"


def get_capabilities(user: str | None = None) -> dict[str, bool]:
    """Resolve toan bo capability cho user — cache 1h theo user."""
    user = user or frappe.session.user
    key = _cache_key(user)
    cached = frappe.cache().get_value(key)
    if cached is not None:
        # AC4 self-heal: cache cu (truoc khi co version stamp) duoc bo sung
        # version stamp hien tai → consumer luon nhan duoc field phu.
        if isinstance(cached, dict):
            cached.setdefault(CAP_VERSION_KEY, CAP_SET_VERSION)
        return cached
    caps = {c: can(c) for c in CAPABILITY_MAP}
    # Version stamp (AC4) — khoa rieng, gia tri str (KHONG bool) → can() bo qua.
    caps[CAP_VERSION_KEY] = CAP_SET_VERSION
    frappe.cache().set_value(key, caps, expires_in_sec=3600)
    return caps


def invalidate_capabilities(user: str | None = None) -> None:
    if user:
        frappe.cache().delete_value(_cache_key(user))
    else:
        frappe.cache().delete_keys("ac_caps::*")
