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


# ─── CTA gating & approval RBAC (GATE-8 / LL-FE-51) ───────────────────────────
#
# ROOT CAUSE (bug "mọi user login đều thấy + bấm 'Chốt hồ sơ'"): lock/withdraw
# BYPASS `apply_workflow` — chúng set `workflow_state` trực tiếp qua `doc.submit()`
# nên Frappe KHÔNG enforce role của transition workflow. Trước đây service chỉ
# guard STATE, thiếu guard ROLE → lỗ RBAC. Fix: mirror role-name của các transition
# rời 'Pending Approval' trong fixtures/workflow.json 'IMM-02 Spec Workflow'
# ('Phê duyệt spec' → Locked, 'Rút spec' → Withdrawn) làm SoT + enforce ở service.

# SoT — bộ role được phép duyệt (khớp `allowed` của transition 'Pending Approval').
# Đây là gate role-name THẬT của workflow (không phải role-name bịa → không phải
# RBAC dead-gate); đổi transition = phải đồng bộ set này (invariant test khoá).
_SPEC_APPROVAL_ROLES = frozenset({
    "Procurement Manager", "AssetCore Super Admin", "System Manager",
})


def _has_spec_approver_role(user: str | None = None) -> bool:
    """True nếu `user` có ≥1 role duyệt spec (mirror transition 'Pending Approval')."""
    user = user or frappe.session.user
    return bool(_SPEC_APPROVAL_ROLES.intersection(frappe.get_roles(user)))


def _require_spec_approver() -> None:
    """Chặn cứng lock/withdraw — chỉ role duyệt spec mới được thực hiện.

    Pattern như imm16._require_qa_or_admin. Gọi ở ĐẦU _lock_spec/_withdraw_spec
    (capability → state, defense-in-depth).
    """
    if not _has_spec_approver_role():
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            _("Chỉ người có quyền duyệt hồ sơ kỹ thuật mới được thực hiện thao tác này"),
        )


def _can_reissue_actor(user: str | None = None) -> bool:
    """Reissue = tạo Tech Spec MỚI (copy_doc + insert) → gate theo quyền CREATE
    THẬT trên IMM Tech Spec (DocPerm: Spec User / Spec Manager / Super Admin).

    KHÔNG hardcode role-name và KHÔNG bắt buộc role duyệt — người soạn hồ sơ được
    phát hành lại. Mirror chính xác điều kiện mà `new.insert()` sẽ enforce ⇒ giữ
    invariant map ⊆ guard-permitted (cờ can_reissue advertise ⟺ insert cho phép).
    """
    user = user or frappe.session.user
    return bool(frappe.has_permission(_DT_TS, ptype="create", user=user))


def _require_reissue_actor() -> None:
    """Chặn cứng reissue — chỉ người có quyền soạn (create) Tech Spec mới reissue."""
    if not _can_reissue_actor():
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            _("Chỉ người có quyền soạn hồ sơ kỹ thuật mới được phát hành lại"),
        )


# Guard-state predicates THỰC của lock/withdraw/reissue — SSoT DÙNG CHUNG cho cả
# cờ CTA (_spec_cta_flags) VÀ guard BAD_STATE ở endpoint (không nới lỏng guard).
# LƯU Ý: withdraw hợp lệ CẢ từ 'Locked' dù fixture KHÔNG có transition
# Locked→Withdrawn — cờ phải khớp guard-predicate service THỰC, không dùng
# blanket fixture-transition-map.
def _spec_lock_state_ok(state: str | None) -> bool:
    return (state or "Draft") == "Pending Approval"


def _spec_withdraw_state_ok(state: str | None) -> bool:
    return (state or "Draft") in ("Pending Approval", "Locked")


def _spec_reissue_state_ok(state: str | None) -> bool:
    return (state or "Draft") == "Withdrawn"


def _spec_cta_flags(doc, user: str | None = None) -> dict:
    """SSoT cờ CTA duyệt cho FE — derive server-side từ
    (guard-state predicate THỰC ∧ role/capability của user).

    Reuse bởi get_tech_spec (display hint) — KHÔNG nới guard. INVARIANT
    (map ⊆ guard-permitted): mỗi cờ True ⟹ endpoint tương ứng KHÔNG reject
    (state guard + _require_spec_approver / _require_reissue_actor cùng điều kiện).
    `allowed_transitions` CHỈ là danh sách đích để hiển thị, không phải quyền.

    Args:
        doc: IMM Tech Spec document (đọc `workflow_state`).
        user: user để tính role (mặc định session user).

    Returns:
        {allowed_transitions: list[str], can_lock, can_withdraw, can_reissue}
    """
    user = user or frappe.session.user
    state = getattr(doc, "workflow_state", None) or "Draft"
    is_approver = _has_spec_approver_role(user)
    reissue_ok = _can_reissue_actor(user)

    can_lock     = _spec_lock_state_ok(state) and is_approver
    can_withdraw = _spec_withdraw_state_ok(state) and is_approver
    can_reissue  = _spec_reissue_state_ok(state) and reissue_ok

    allowed: list[str] = []
    if can_lock:
        allowed.append("Locked")
    if can_withdraw:
        allowed.append("Withdrawn")
    if can_reissue:
        allowed.append("Draft")  # reissue tạo bản mới ở Draft
    return {
        "allowed_transitions": allowed,
        "can_lock": bool(can_lock),
        "can_withdraw": bool(can_withdraw),
        "can_reissue": bool(can_reissue),
    }


# ─── Intermediate workflow transitions — SSoT next-ACTION+role (khớp
#     imm_02_spec_workflow.json 'IMM-02 Spec Workflow') ──────────────────────────
# Đóng bug "Spec kẹt ở Draft/Reviewing/Benchmarked/Risk Assessed dù đủ quyền": FE
# chỉ có 3 nút EXCEPTION lock/withdraw/reissue (cờ _spec_cta_flags), còn endpoint
# transition_workflow LIVE nhưng 0 nút render 6 transition TRUNG GIAN. Fix: BE là
# SoT — get_tech_spec emit `allowed_actions` (ĐÃ LỌC role) để FE render 1 nút/action.
#
# Mirror imm03._AVL_VALID_TRANSITIONS (RICHER: (action, next_state, allowed_roles)).
# KHÁC 3 cờ EXCEPTION (_spec_cta_flags): 2 cạnh rời 'Pending Approval'
# ('Phê duyệt spec'→Locked, 'Rút spec'→Withdrawn) do endpoint lock_spec/withdraw_spec
# xử lý (BYPASS apply_workflow — doc.submit) → KHÔNG surface qua transition_workflow;
# gom vào _SPEC_EXCEPTION_ACTIONS để invariant test trừ khỏi tập action workflow.
#
# allowed_roles = domain-role fixture ('allowed') + AssetCore Super Admin + System
# Manager (đã backfill → QTV/Admin duyệt được — đóng root-cause 'không duyệt được dù
# đủ quyền'). Invariant `test_spec_valid_transitions_reconciles_workflow_json` chốt
# (state,action,next_state,roles) == workflow json EXACT + completeness (thiếu cạnh
# → RED). allowed_actions CHỈ là hint hiển thị (⊆ guard-permitted) — apply_workflow
# vẫn enforce role như lớp 2, KHÔNG nới lỏng.


class SpecState:
    """Workflow states của IMM Tech Spec (khớp imm_02_spec_workflow.json states[])."""
    DRAFT            = "Draft"
    REVIEWING        = "Reviewing"
    BENCHMARKED      = "Benchmarked"
    RISK_ASSESSED    = "Risk Assessed"
    PENDING_APPROVAL = "Pending Approval"
    LOCKED           = "Locked"
    WITHDRAWN        = "Withdrawn"

    ALL = frozenset({
        DRAFT, REVIEWING, BENCHMARKED, RISK_ASSESSED,
        PENDING_APPROVAL, LOCKED, WITHDRAWN,
    })


# +2 admin role đã backfill vào MỌI transition fixture (QTV/Admin thao tác được).
_SPEC_ADMIN_ROLES = frozenset({"AssetCore Super Admin", "System Manager"})

_SPEC_VALID_TRANSITIONS: dict[str, list[tuple[str, str, frozenset]]] = {
    SpecState.DRAFT: [
        ("Gửi rà soát", SpecState.REVIEWING,
         frozenset({"Spec User"}) | _SPEC_ADMIN_ROLES),
    ],
    SpecState.REVIEWING: [
        ("Yêu cầu chỉnh spec", SpecState.DRAFT,
         frozenset({"Spec User", "Needs Manager"}) | _SPEC_ADMIN_ROLES),
        ("Hoàn tất benchmark", SpecState.BENCHMARKED,
         frozenset({"Needs Manager"}) | _SPEC_ADMIN_ROLES),
    ],
    SpecState.BENCHMARKED: [
        ("Đánh giá rủi ro xong", SpecState.RISK_ASSESSED,
         frozenset({"Spec Manager"}) | _SPEC_ADMIN_ROLES),
    ],
    SpecState.RISK_ASSESSED: [
        ("Trình duyệt spec", SpecState.PENDING_APPROVAL,
         frozenset({"Commissioning Manager"}) | _SPEC_ADMIN_ROLES),
    ],
    SpecState.PENDING_APPROVAL: [
        ("Yêu cầu chỉnh risk", SpecState.RISK_ASSESSED,
         frozenset({"Procurement Manager"}) | _SPEC_ADMIN_ROLES),
    ],
    # Terminal workflow-engine (docstatus 1) → 0 transition trung gian.
    SpecState.LOCKED: [],
    SpecState.WITHDRAWN: [],
}

# 2 cạnh rời 'Pending Approval' do endpoint lock_spec ('Phê duyệt spec'→Locked) /
# withdraw_spec ('Rút spec'→Withdrawn) xử lý (BYPASS apply_workflow). KHÔNG surface
# qua transition_workflow. Invariant: (wf_actions − map_actions) == set này.
_SPEC_EXCEPTION_ACTIONS = frozenset({"Phê duyệt spec", "Rút spec"})


def spec_allowed_actions(workflow_state, user_roles=None) -> list[str]:
    """SSoT derive tập nhãn ACTION trung gian hợp lệ cho ``workflow_state``, ĐÃ LỌC
    theo role của user (server-driven CTA, GATE-8/LL-FE-51). Trả ``list[str]``
    (⊆ tập action user được phép). ``user_roles`` truyền 1 LẦN từ caller (N+1-free);
    ``None`` → KHÔNG lọc (full SoT của state). Degrade an toàn: state
    unknown/terminal (Locked/Withdrawn) → ``[]`` (FE render 0 nút).
    Mirror imm03.avl_allowed_transitions."""
    rows = _SPEC_VALID_TRANSITIONS.get(workflow_state or "", [])
    if user_roles is None:
        return [action for action, _next, _roles in rows]
    ur = set(user_roles)
    return [action for action, _next, roles in rows if roles & ur]


def spec_transition_target(workflow_state, action):
    """Trả ``(next_state, allowed_roles)`` cho ``(workflow_state, action)`` nếu ∈ SoT
    ``_SPEC_VALID_TRANSITIONS``, else ``None``. API tier dùng để reject action ngoài
    SoT (nhảy-cóc / action lạ) → BAD_STATE (apply_workflow enforce role như lớp 2).
    Mirror imm03.avl_transition_target."""
    for act, next_state, roles in _SPEC_VALID_TRANSITIONS.get(workflow_state or "", []):
        if act == action:
            return next_state, roles
    return None


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

    # Cập nhật Tech Spec.candidate_count + benchmark_ref (direct DB write to avoid re-validate)
    if doc.spec_ref and doc.name:
        try:
            frappe.db.set_value(_DT_TS, doc.spec_ref, {
                "benchmark_ref": doc.name,
                "candidate_count": len(doc.candidates or []),
            })
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

    # Update Tech Spec link (direct DB write to avoid re-validate)
    if doc.spec_ref and doc.name:
        try:
            update = {"lock_in_risk_ref": doc.name, "lock_in_score": doc.lock_in_score}
            if doc.mitigation_plan:
                update["mitigation_plan"] = doc.mitigation_plan
            if doc.mitigation_evidence:
                update["mitigation_evidence"] = doc.mitigation_evidence
            frappe.db.set_value(_DT_TS, doc.spec_ref, update)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-02 lock-in sync failed")


# ─── Requirements management (docs §3.5, §3.6) ───────────────────────────────

def add_requirement_to_spec(spec: str, requirement: dict) -> dict:
    """Thêm 1 row vào child table `requirements` của Tech Spec (docs §3.5).

    Tách khỏi `update_tech_spec` để semantic rõ ràng: chỉ thao tác requirements,
    không touch các field khác.

    Args:
        spec: tên Tech Spec
        requirement: dict các field của child row (criterion, is_mandatory,
                     spec_value, unit, test_method, ...)

    Returns:
        {name, total_mandatory, total_optional, requirement_idx}
    """
    if not requirement:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("requirement không được rỗng"))
    doc = frappe.get_doc(_DT_TS, spec)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE,
                            _("Spec đã submit/cancel — không thêm requirement"))
    row = doc.append("requirements", requirement)
    doc.save()
    return {
        "name": doc.name,
        "requirement_idx": row.idx,
        "total_mandatory": doc.total_mandatory,
        "total_optional":  doc.total_optional,
    }


def bulk_import_requirements_from_csv(spec: str, rows: list[dict]) -> dict:
    """Bulk thêm requirements từ list dict (đã parse từ CSV ở FE) — docs §3.6.

    Args:
        spec: tên Tech Spec
        rows: list of dict, mỗi dict là 1 row trong child table

    Returns:
        {name, imported, total_mandatory, total_optional}
    """
    if not isinstance(rows, list):
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("rows phải là list"))
    doc = frappe.get_doc(_DT_TS, spec)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE,
                            _("Spec đã submit/cancel — không import requirements"))
    imported = 0
    for r in rows:
        if not r:
            continue
        doc.append("requirements", r)
        imported += 1
    if imported == 0:
        raise ServiceError(ErrorCode.VALIDATION, _("Không có row hợp lệ để import"))
    doc.save()
    return {
        "name": doc.name,
        "imported": imported,
        "total_mandatory": doc.total_mandatory,
        "total_optional":  doc.total_optional,
    }


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
