# Copyright (c) 2026, AssetCore Team
"""Business logic for IMM-02 — Tech Spec & Market Analysis (Tier 2)."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today, now_datetime
from frappe.model.document import Document

from assetcore.services.shared import ErrorCode, ServiceError

# ─── Constants ────────────────────────────────────────────────────────────────

_DT_TS = "IMM Tech Spec"
_DT_MB = "IMM Market Benchmark"
_DT_LR = "IMM Lock-in Risk Assessment"
_DT_NR = "IMM Needs Request"
_DT_PP = "IMM Procurement Plan"

MIN_MANDATORY_REQUIREMENTS = 8
MIN_BENCHMARK_CANDIDATES   = 3
INFRA_DOMAINS_REQUIRED = (
    "Electrical", "Medical Gas", "Network/IT", "HIS-PACS-LIS", "HVAC", "Space-Layout",
)
LOCK_IN_DEFAULT_WEIGHTS = {
    "Protocol Standard": 0.30,
    "Consumable Source": 0.20,
    "Software License":  0.20,
    "Parts Source":      0.15,
    "Service Tooling":   0.15,
}
LOCK_IN_THRESHOLD_DEFAULT = 2.5


# ─── Tech Spec lifecycle ──────────────────────────────────────────────────────

def before_insert_tech_spec(doc: Document) -> None:
    if not doc.draft_date:
        doc.draft_date = today()
    if not doc.version:
        doc.version = "1.0"
    # Fetch device_category từ IMM Device Model nếu chưa có
    # (fetch_from chỉ trigger khi user nhập trên form; backend set programmatic cần manual fetch)
    if doc.device_model_ref and not doc.device_category:
        doc.device_category = frappe.db.get_value(
            "IMM Device Model", doc.device_model_ref, "asset_category",
        )


def validate_tech_spec(doc: Document) -> None:
    _vr01_unique_per_plan_line(doc)
    _vr02_mandatory_min_count(doc)
    _vr03_test_method_present(doc)
    _vr05_infra_completeness(doc)
    _rollup_requirement_counts(doc)
    _rollup_infra_status(doc)
    _check_workflow_gates_ts(doc)


def before_submit_tech_spec(doc: Document) -> None:
    """G04 lock-in check trước khi submit (Locked)."""
    _validate_gate_g04(doc)
    if not doc.approval_date:
        doc.approval_date = today()


def on_submit_tech_spec(doc: Document) -> None:
    # Update Procurement Plan Line.status = "In Procurement" cho line tương ứng
    if doc.source_plan and doc.source_needs_request:
        try:
            plan = frappe.get_doc(_DT_PP, doc.source_plan)
            for it in plan.plan_items or []:
                if it.needs_request == doc.source_needs_request:
                    it.status = "In Procurement"
            plan.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-02 update plan line failed")
    frappe.publish_realtime("imm02_spec_locked", {
        "name": doc.name, "source_plan": doc.source_plan,
        "source_needs_request": doc.source_needs_request,
        "device_model_ref": doc.device_model_ref,
    })


# ─── VR-01..VR-05 ─────────────────────────────────────────────────────────────

def _vr01_unique_per_plan_line(doc: Document) -> None:
    """1 (source_plan, source_plan_line) ↔ 1 Tech Spec Active (chưa Withdrawn)."""
    if not doc.source_plan or not doc.source_needs_request:
        return
    existing = frappe.db.sql(
        f"""SELECT name FROM `tab{_DT_TS}`
            WHERE source_needs_request = %s
              AND docstatus < 1
              AND workflow_state NOT IN ('Withdrawn')
              AND name != %s
            LIMIT 1""",
        (doc.source_needs_request, doc.name or ""),
    )
    if existing:
        raise ServiceError(
            ErrorCode.DUPLICATE,
            _("VR-02-01: Needs Request {0} đã có Tech Spec Active ({1})")
            .format(doc.source_needs_request, existing[0][0]),
        )


def _vr02_mandatory_min_count(doc: Document) -> None:
    """≥ 1 mandatory requirement."""
    if not doc.requirements:
        return  # Cho phép Draft rỗng; G01 enforce N=8 khi chuyển Reviewing
    mandatory = [r for r in doc.requirements if r.is_mandatory]
    if not mandatory:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-02-02: Cần ≥ 1 mandatory requirement"),
        )


def _vr03_test_method_present(doc: Document) -> None:
    """Mandatory requirement phải có test_method."""
    for r in (doc.requirements or []):
        if r.is_mandatory and not (r.test_method or "").strip():
            raise ServiceError(
                ErrorCode.VALIDATION,
                _("VR-02-03: Requirement '{0}' (mandatory) phải có test_method")
                .format(r.parameter or f"row {r.idx}"),
            )


def _vr05_infra_completeness(doc: Document) -> None:
    """6/6 mục Infra có status (chỉ enforce khi rời Benchmarked)."""
    if (doc.workflow_state or "Draft") not in ("Risk Assessed", "Pending Approval", "Locked"):
        return
    have = {it.domain for it in (doc.infra_compat or []) if it.compatibility_status}
    missing = [d for d in INFRA_DOMAINS_REQUIRED if d not in have]
    if missing:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-02-05: Infra compat thiếu mục: {0}").format(", ".join(missing)),
        )


# ─── Rollups ──────────────────────────────────────────────────────────────────

def _rollup_requirement_counts(doc: Document) -> None:
    mandatory = sum(1 for r in (doc.requirements or []) if r.is_mandatory)
    optional  = sum(1 for r in (doc.requirements or []) if not r.is_mandatory)
    doc.total_mandatory = mandatory
    doc.total_optional  = optional
    # Auto seq
    for i, r in enumerate(doc.requirements or [], 1):
        r.seq = i


def _rollup_infra_status(doc: Document) -> None:
    items = doc.infra_compat or []
    if not items:
        doc.infra_status_overall = ""
        return
    statuses = [it.compatibility_status for it in items if it.compatibility_status]
    if not statuses:
        doc.infra_status_overall = ""
    elif "Need Major Upgrade" in statuses:
        doc.infra_status_overall = "Need Major Upgrade"
    elif "Need Upgrade" in statuses:
        doc.infra_status_overall = "Partial"
    elif all(s in ("Compatible", "N/A") for s in statuses):
        doc.infra_status_overall = "All Compatible"
    else:
        doc.infra_status_overall = "Partial"


# ─── Gates ────────────────────────────────────────────────────────────────────

def _check_workflow_gates_ts(doc: Document) -> None:
    state = (doc.workflow_state or "Draft")
    if state == "Reviewing":
        _validate_gate_g01(doc)
    if state == "Benchmarked":
        _validate_gate_g02(doc)
    if state == "Risk Assessed":
        _validate_gate_g03(doc)


def _validate_gate_g01(doc: Document) -> None:
    """G01: requirements ≥ 8 mandatory + 100% test_method."""
    mandatory = [r for r in (doc.requirements or []) if r.is_mandatory]
    if len(mandatory) < MIN_MANDATORY_REQUIREMENTS:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G01: Cần ≥ {0} mandatory requirement (hiện: {1})")
            .format(MIN_MANDATORY_REQUIREMENTS, len(mandatory)),
        )
    missing = [r.parameter for r in mandatory if not (r.test_method or "").strip()]
    if missing:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G01: Mandatory requirement thiếu test_method: {0}")
            .format(", ".join(missing[:5])),
        )


def _validate_gate_g02(doc: Document) -> None:
    """G02: ≥ 3 benchmark candidate."""
    if not doc.candidate_count or doc.candidate_count < MIN_BENCHMARK_CANDIDATES:
        # Tính thử nếu doc.benchmark_ref có data
        cnt = 0
        if doc.benchmark_ref:
            cnt = frappe.db.count("Benchmark Candidate", {"parent": doc.benchmark_ref})
        if cnt < MIN_BENCHMARK_CANDIDATES:
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                _("G02: Cần ≥ {0} benchmark candidate (hiện: {1})")
                .format(MIN_BENCHMARK_CANDIDATES, cnt),
            )
        doc.candidate_count = cnt


def _validate_gate_g03(doc: Document) -> None:
    """G03: 6/6 mục Infra có status."""
    have = {it.domain for it in (doc.infra_compat or []) if it.compatibility_status}
    missing = [d for d in INFRA_DOMAINS_REQUIRED if d not in have]
    if missing:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G03: Infra compat chưa đầy đủ — thiếu: {0}").format(", ".join(missing)),
        )


def _validate_gate_g04(doc: Document) -> None:
    """G04: lock_in_score ≤ threshold OR có mitigation_plan + evidence."""
    score = doc.lock_in_score or 0
    threshold = LOCK_IN_THRESHOLD_DEFAULT
    if doc.lock_in_risk_ref:
        try:
            lr = frappe.get_doc(_DT_LR, doc.lock_in_risk_ref)
            score = lr.lock_in_score or 0
            threshold = lr.threshold_used or threshold
            doc.lock_in_score = score
            if not doc.mitigation_plan:
                doc.mitigation_plan = lr.mitigation_plan
            if not doc.mitigation_evidence:
                doc.mitigation_evidence = lr.mitigation_evidence
        except frappe.DoesNotExistError:
            pass

    if score > threshold:
        if not (doc.mitigation_plan and (doc.mitigation_plan or "").strip()):
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                _("G04: Lock-in score {0} vượt ngưỡng {1} — cần mitigation_plan")
                .format(score, threshold),
            )
        if not doc.mitigation_evidence:
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                _("G04: Lock-in score {0} vượt ngưỡng — cần mitigation_evidence (file)")
                .format(score),
            )


# ─── Market Benchmark ─────────────────────────────────────────────────────────

def validate_market_benchmark(doc: Document) -> None:
    weights = _parse_weighting(doc.weighting_scheme)
    for cand in (doc.candidates or []):
        cand.recommendation_score = round(_compute_candidate_score(cand, weights), 4)
    # Sort & pick top
    cands = sorted((doc.candidates or []),
                   key=lambda c: c.recommendation_score or 0, reverse=True)
    if cands:
        top = cands[0]
        doc.recommended_candidate = f"{top.manufacturer} {top.model}"
    else:
        doc.recommended_candidate = ""

    # Cập nhật Tech Spec.candidate_count + benchmark_ref
    if doc.spec_ref:
        try:
            ts = frappe.get_doc(_DT_TS, doc.spec_ref)
            ts.benchmark_ref = doc.name
            ts.candidate_count = len(doc.candidates or [])
            ts.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-02 spec sync failed")


def _parse_weighting(raw) -> dict:
    if not raw:
        return {"price": 30, "spec": 40, "support": 20, "brand": 10}
    if isinstance(raw, dict):
        return raw
    import json
    try:
        return json.loads(raw)
    except Exception:
        return {"price": 30, "spec": 40, "support": 20, "brand": 10}


def _compute_candidate_score(cand: Document, weights: dict) -> float:
    """Score candidate theo weighted: spec_match% (spec), inverse price (price),
    support tier mapping (support), brand placeholder (brand).
    """
    spec    = (cand.spec_match_pct or 0) / 100  # 0..1
    # Inverse price: lower = better; normalize chỉ trong list — đơn giản hóa: 1/(1+log(price))
    price   = 0.5  # placeholder; normalize requires full list
    support = {"Tier1": 1.0, "Tier2": 0.7, "Tier3": 0.4}.get(cand.support_tier or "", 0.5)
    brand   = 0.7  # placeholder
    w = weights
    score = (
        spec    * (w.get("spec", 40)    / 100) +
        price   * (w.get("price", 30)   / 100) +
        support * (w.get("support", 20) / 100) +
        brand   * (w.get("brand", 10)   / 100)
    )
    return score * 5  # scale 0..5


# ─── Lock-in Risk Assessment ──────────────────────────────────────────────────

def validate_lock_in_assessment(doc: Document) -> None:
    """Compute lock_in_score từ items × default weights."""
    score = 0.0
    for it in (doc.items or []):
        w = LOCK_IN_DEFAULT_WEIGHTS.get(it.dimension, 0.0)
        it.weight_pct = round(w * 100, 2)
        it.weighted = round((it.score or 0) * w, 4)
        score += it.weighted
    doc.lock_in_score = round(score, 4)
    if not doc.threshold_used:
        doc.threshold_used = LOCK_IN_THRESHOLD_DEFAULT

    # Update Tech Spec link
    if doc.spec_ref:
        try:
            ts = frappe.get_doc(_DT_TS, doc.spec_ref)
            ts.lock_in_risk_ref = doc.name
            ts.lock_in_score = doc.lock_in_score
            if doc.mitigation_plan: ts.mitigation_plan = doc.mitigation_plan
            if doc.mitigation_evidence: ts.mitigation_evidence = doc.mitigation_evidence
            ts.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-02 lock-in sync failed")


# ─── Scheduler ────────────────────────────────────────────────────────────────

def check_overdue_drafts() -> None:
    """Daily — Tech Spec docstatus=0, > 30d Draft/Reviewing."""
    rows = frappe.db.sql(
        f"""SELECT name, source_plan, draft_date FROM `tab{_DT_TS}`
            WHERE docstatus = 0
              AND workflow_state IN ('Draft','Reviewing','Benchmarked')
              AND DATEDIFF(CURDATE(), draft_date) > 30""",
        as_dict=True,
    )
    if rows:
        frappe.logger("imm02").info(f"IMM-02 overdue drafts: {len(rows)}")


def benchmark_freshness_alert() -> None:
    """Weekly — cảnh báo benchmark > 6 tháng được dùng cho spec mới."""
    rows = frappe.db.sql(
        f"""SELECT mb.name, mb.benchmark_date FROM `tab{_DT_MB}` mb
            WHERE mb.docstatus = 1
              AND DATEDIFF(CURDATE(), mb.benchmark_date) > 180""",
        as_dict=True,
    )
    if rows:
        frappe.logger("imm02").info(f"IMM-02 stale benchmarks: {len(rows)}")
