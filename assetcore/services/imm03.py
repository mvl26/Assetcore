# Copyright (c) 2026, AssetCore Team
"""Business logic for IMM-03 — Vendor Eval & Procurement Decision (Tier 2).

Bao gồm:
  - VR-03-01..VR-03-07
  - Gates G01..G05
  - Vendor evaluation scoring
  - AVL lifecycle (Approved/Conditional/Suspended/Expired)
  - Procurement Decision → mint AC Purchase
  - Vendor Scorecard quarterly (cron)
  - Supplier Audit handler
  - Validate hook trên AC Purchase (BR-03-08)
"""
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import today, now_datetime, add_years, getdate, add_months
from frappe.model.document import Document

from assetcore.services.shared import ErrorCode, ServiceError

# ─── Constants ────────────────────────────────────────────────────────────────

_DT_VE       = "IMM Vendor Evaluation"
_DT_PD       = "IMM Procurement Decision"
_DT_AVL      = "IMM AVL Entry"
_DT_VS       = "IMM Vendor Scorecard"
_DT_SA       = "IMM Supplier Audit"
_DT_SUPPLIER = "AC Supplier"
_DT_PURCHASE = "AC Purchase"
_DT_TS       = "IMM Tech Spec"
_DT_PP       = "IMM Procurement Plan"

ENVELOPE_HARD_LIMIT_PCT = 105.0  # > 105% cần justification

_METHOD_RULES = {
    # method: (max_value VND, requires_min_quotes)
    "Chỉ định thầu":         (50_000_000,    1),
    "Mua sắm trực tiếp":     (100_000_000,   1),
    "Chào hàng cạnh tranh":  (1_000_000_000, 3),
    "Đấu thầu rộng rãi":     (None,          3),
    "Mua sắm tập trung":     (None,          1),
}


# ─── Vendor Evaluation ────────────────────────────────────────────────────────

def validate_evaluation(doc: Document) -> None:
    _vr01_min_candidates(doc)
    _vr03_quotation_validity(doc)
    _check_avl_warnings(doc)
    _compute_eval_scores(doc)


def on_submit_evaluation(doc: Document) -> None:
    # Evaluation Evaluated state — downstream là PD. Nếu đỉnh HÒA (has_top_tie):
    # ghi 1 IMM Audit Trail bất biến 'eval_tie_unresolved' (vì sao KHÔNG có gợi ý
    # trúng thầu — căn cứ NĐ98). Idempotent: bỏ qua nếu đã có row (chống amend/resubmit).
    if doc.has_top_tie:
        _log_eval_tie_unresolved(doc)


def _log_eval_tie_unresolved(doc: Document) -> None:
    """Ghi audit 'eval_tie_unresolved' (event_type='System') — idempotent.

    Marker máy ``eval_tie_unresolved`` ở đầu ``change_summary`` cho phép phát hiện
    trùng (chống nhân đôi khi amend/resubmit) + câu Việt hoàn chỉnh (LL-BE-14).
    Best-effort: audit-fail KHÔNG vỡ submit (chỉ log_error)."""
    try:
        existing = frappe.db.exists("IMM Audit Trail", {
            "ref_doctype": _DT_VE,
            "ref_name": doc.name,
            "event_type": "System",
            "change_summary": ("like", "eval_tie_unresolved%"),
        })
        if existing:
            return
        from assetcore.utils.lifecycle import log_audit_event
        tied = doc.tied_candidates or ""
        top = max((c.weighted_score or 0) for c in (doc.candidates or [])) \
            if doc.candidates else 0
        log_audit_event(
            asset=None,
            event_type="System",
            ref_doctype=_DT_VE,
            ref_name=doc.name,
            change_summary=(
                "eval_tie_unresolved — Hòa điểm đỉnh, KHÔNG tự gợi ý trúng thầu "
                f"(spec: {doc.spec_ref or '—'}; NCC đồng hạng: {tied}; điểm: {top})"
            ),
        )
    except Exception:
        frappe.log_error(
            title="IMM-03 eval_tie_unresolved audit failed",
            message=frappe.get_traceback(),
        )


def _vr01_min_candidates(doc: Document) -> None:
    """VR-03-01: số candidate phù hợp method.

    Method được set ở Procurement Decision; ở Eval check ≥ 3 cho an toàn (đủ cho
    Đấu thầu rộng rãi / Chào hàng cạnh tranh). Decision tier sẽ check chi tiết hơn.
    Chỉ enforce khi state ≥ Quotation Received.
    """
    if doc.workflow_state in ("Draft", "Open RFQ"):
        return
    cnt = len(doc.candidates or [])
    if cnt < 3:
        # Soft warn — Decision tier sẽ enforce chính xác theo method
        frappe.msgprint(
            _("Đề xuất ≥ 3 candidate cho Đấu thầu rộng rãi/Chào hàng cạnh tranh "
              "(hiện: {0}).").format(cnt),
            indicator="orange",
        )


def _vr03_quotation_validity(doc: Document) -> None:
    """VR-03-03: quotation chưa hết hạn (chỉ kiểm khi state Quotation Received+)."""
    if doc.workflow_state in ("Draft", "Open RFQ"):
        return
    cur = getdate(today())
    expired = []
    for q in (doc.quotations or []):
        if q.quotation_validity and getdate(q.quotation_validity) < cur:
            expired.append(q.quotation_no or f"row {q.idx}")
    if expired:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-03-03: Quotation đã hết hạn: {0}").format(", ".join(expired)),
        )


def _check_avl_warnings(doc: Document) -> None:
    """Set in_avl flag cho mỗi candidate; warning nếu non-AVL chưa có sign-off."""
    spec = None
    if doc.spec_ref:
        try:
            spec = frappe.get_doc(_DT_TS, doc.spec_ref)
        except frappe.DoesNotExistError:
            pass
    category = spec.device_category if spec else None
    for cand in (doc.candidates or []):
        if not cand.supplier:
            continue
        cand.in_avl = _is_supplier_in_avl(cand.supplier, category)


def _avl_is_live(supplier: str, category: str | None = None) -> int:
    """SoT predicate 'AVL còn hiệu lực' (INV-AVL-LIVE, 02 §IV.6).

    Return 1 ⇔ tồn tại AVL của ``supplier`` với::

        docstatus = 1
        AND workflow_state ∈ {Approved, Conditional}
        AND (valid_to IS NULL OR valid_to >= CURDATE())

    1 truy vấn (``frappe.db.sql`` 1 câu, ``LIMIT 1``) — KHÔNG loop, KHÔNG migration
    (``valid_to`` đã tồn tại). ``>=`` inclusive ⇒ biên ``valid_to == hôm nay`` vẫn
    LIVE; bù khít ``check_avl_expiry`` dùng ``<`` (no off-by-one).

    Mệnh đề OR-NULL ``(valid_to IS NULL OR valid_to >= CURDATE())`` viết thẳng SQL
    (option #1 Core Doc 02 §IV.6) — TRÙNG TỪNG-BIT với reference predicate
    ``_sync_supplier_avl_status`` (line ~380) để không tái-drift.

    Đây là predicate DUY NHẤT — mọi điểm gọi eligibility/cổng/KPI ủy quyền về đây.
    """
    cat_clause = "AND device_category = %(category)s\n              " if category else ""
    return 1 if frappe.db.sql(
        f"""SELECT 1 FROM `tab{_DT_AVL}`
            WHERE supplier = %(supplier)s AND docstatus = 1
              {cat_clause}AND workflow_state IN ('Approved','Conditional')
              AND (valid_to IS NULL OR valid_to >= CURDATE())
            LIMIT 1""",
        {"supplier": supplier, "category": category},
    ) else 0


def _is_supplier_in_avl(supplier: str, category: str | None) -> int:
    """Eligibility flag candidate — ủy quyền về predicate SoT ``_avl_is_live``
    (INV-AVL-LIVE, 02 §IV.6). KHÔNG còn check ``workflow_state`` thuần; tên public
    giữ nguyên cho backward-compat (FE đọc ``cand.in_avl`` 1/0 không đổi shape)."""
    return _avl_is_live(supplier, category)


# Epsilon trên giá trị weighted_score ĐÃ round(…, 4) — chênh ≤ ngưỡng này coi như
# HÒA (loại bỏ float-noise tầng sâu). 1e-9 << 5e-5 (nửa ulp của round-4) ⇒ chỉ bắt
# trùng-bit thực sự, KHÔNG gộp 2 điểm round khác nhau.
_TIE_EPSILON = 1e-9


def _resolve_recommendation(candidates) -> tuple[str | None, list[str]]:
    """Cổng tie-break thuần (INV-VE-TIE §IV.7) — KHÔNG I/O, test đơn vị không cần DB.

    Input: iterable candidate có ``.supplier`` + ``.weighted_score`` (đã round 4).
    Trả ``(recommended, tied)``:

      - ``top = max(weighted_score)``. Nếu ``top <= 0`` (chưa chấm) →
        ``(None, [])`` (giữ hành vi empty/zero).
      - ``tied = [c.supplier for c if abs((c.score or 0) - top) <= _TIE_EPSILON]``.
      - ``len(tied) == 1`` → ``(tied[0], [])`` (higher-score-wins — hành vi cũ).
      - ``len(tied) >= 2`` (HÒA đỉnh) → ``(None, sorted(tied))``: KHÔNG auto-gợi-ý
        (phi-tất-định bị cấm), surface danh sách đồng hạng cho người chấm + audit.

    Ordering ``sorted(tied)`` CHỈ để hiển thị/audit ổn định — KHÔNG dùng để chọn
    winner khi hòa (auto-award first-row bị kill — INV-VE-TIE).
    """
    cands = list(candidates or [])
    if not cands:
        return None, []
    top = max((c.weighted_score or 0) for c in cands)
    if top <= 0:
        return None, []
    tied = [c.supplier for c in cands
            if abs((c.weighted_score or 0) - top) <= _TIE_EPSILON]
    if len(tied) == 1:
        return tied[0], []
    return None, sorted(tied)


def _compute_eval_scores(doc: Document) -> None:
    """Compute weighted_score per candidate dựa trên scores (JSON) × group weights,
    rồi áp cổng tie-break INV-VE-TIE (§IV.7) — KHÔNG auto-award khi đỉnh HÒA.

    Sau khi tính điểm, ủy quyền chọn winner cho ``_resolve_recommendation`` (thuần):
      - 1 đỉnh duy nhất → ``recommended_candidate`` = supplier đó, ``has_top_tie=0``.
      - ≥2 đỉnh hòa → ``recommended_candidate=None``, ``has_top_tie=1``,
        ``tied_candidates = ','.join(sorted(tied))`` + ``frappe.logger('imm03')``
        warning 'eval_tie_unresolved' (spec_ref, suppliers, score). KHÔNG raise.
      - top ≤ 0 (chưa chấm) → reset về None/0/'' (giữ hành vi empty/zero).

    An toàn ở validate context (chạy mỗi save) — chỉ gán field trên ``doc``, KHÔNG
    ghi DB. Audit Trail bất biến ghi ở ``on_submit_evaluation`` (idempotent)."""
    weights = _parse_weighting(doc.weighting_scheme)
    crit_groups = {c.criterion: c.group for c in (doc.criteria or [])}
    crit_weights = {c.criterion: (c.weight_pct or 0) / 100 for c in (doc.criteria or [])}
    for cand in (doc.candidates or []):
        scores = _parse_json_field(cand.scores) or {}
        total = 0.0
        for crit_name, crit_score in scores.items():
            grp = crit_groups.get(crit_name)
            if not grp:
                continue
            grp_w = (weights.get(grp, 0) / 100)
            crit_w = crit_weights.get(crit_name, 0)
            total += float(crit_score) * grp_w * crit_w
        cand.weighted_score = round(total * 5, 4)  # scale to 0..5

    # Cổng tie-break — KHÔNG auto-gợi-ý khi đỉnh hòa (INV-VE-TIE §IV.7)
    recommended, tied = _resolve_recommendation(doc.candidates or [])
    doc.recommended_candidate = recommended
    if tied:  # ≥2 candidate đồng hạng nhất → surface + KHÔNG auto-award
        doc.has_top_tie = 1
        doc.tied_candidates = ",".join(tied)
        top = max((c.weighted_score or 0) for c in (doc.candidates or []))
        frappe.logger("imm03").warning(
            "eval_tie_unresolved spec_ref=%s suppliers=%s score=%s",
            doc.spec_ref, doc.tied_candidates, top,
        )
    else:
        doc.has_top_tie = 0
        doc.tied_candidates = ""


def _parse_weighting(raw) -> dict:
    if not raw:
        return {"Technical": 35, "Commercial": 25, "Financial": 10, "Support": 15, "Compliance": 15}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {"Technical": 35, "Commercial": 25, "Financial": 10, "Support": 15, "Compliance": 15}


def _parse_json_field(raw):
    if not raw: return {}
    if isinstance(raw, dict): return raw
    try: return json.loads(raw)
    except Exception: return {}


# ─── Procurement Decision ─────────────────────────────────────────────────────

def validate_decision(doc: Document) -> None:
    _validate_gate_g04_method(doc)
    _vr04_envelope_check(doc)
    _vr07_unique_decision_per_spec(doc)


def before_submit_decision(doc: Document) -> None:
    _vr05_winner_avl_required(doc)
    _validate_gate_g05(doc)
    if not doc.awarded_date:
        doc.awarded_date = today()


def on_submit_decision(doc: Document) -> None:
    """Mint AC Purchase và link Plan Line."""
    if not doc.ac_purchase_ref:
        po_name = _mint_ac_purchase(doc)
        doc.db_set("ac_purchase_ref", po_name)
    if doc.plan_ref and doc.plan_line:
        _update_plan_line_status(doc.plan_ref, doc.plan_line, "Awarded")
    frappe.publish_realtime("imm03_decision_awarded", {
        "name": doc.name,
        "ac_purchase": doc.ac_purchase_ref,
        "winner_supplier": doc.winner_supplier,
        "spec_ref": doc.spec_ref,
        "plan_line": doc.plan_line,
    })


def on_cancel_decision(doc: Document) -> None:
    # Revert plan line status nếu cần
    if doc.plan_ref and doc.plan_line:
        _update_plan_line_status(doc.plan_ref, doc.plan_line, "In Procurement")


def _validate_gate_g04_method(doc: Document) -> None:
    """G04: procurement_method hợp pháp với giá trị + loại."""
    if not doc.procurement_method or doc.workflow_state in ("Draft",):
        return
    rule = _METHOD_RULES.get(doc.procurement_method)
    if not rule:
        return
    max_val, _min_quotes = rule
    if max_val and doc.awarded_price and doc.awarded_price > max_val:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G04: Phương án '{0}' chỉ áp dụng cho gói ≤ {1:,} VND (awarded: {2:,})")
            .format(doc.procurement_method, max_val, doc.awarded_price),
        )
    if doc.procurement_method == "Chỉ định thầu" and not (doc.method_legal_basis or "").strip():
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("G04: 'Chỉ định thầu' yêu cầu method_legal_basis (cơ sở pháp lý)"),
        )


def _vr04_envelope_check(doc: Document) -> None:
    """VR-03-04: awarded_price ≤ 105% allocated_budget của plan_line."""
    if not (doc.plan_ref and doc.plan_line and doc.awarded_price):
        return
    plan = frappe.get_doc(_DT_PP, doc.plan_ref)
    line = next((it for it in plan.plan_items or [] if it.name == doc.plan_line), None)
    if not line or not line.allocated_budget:
        doc.envelope_check_pct = 0
        return
    pct = round(doc.awarded_price / line.allocated_budget * 100, 2)
    doc.envelope_check_pct = pct
    if pct > ENVELOPE_HARD_LIMIT_PCT and doc.workflow_state in ("Pending Approval", "Awarded"):
        # Hard block khi vượt 105% và chưa có justification
        if not (doc.method_legal_basis or "").strip():
            raise ServiceError(
                ErrorCode.CONFLICT,
                _("VR-03-04: Awarded {0:,} > 105% envelope {1:,} ({2}%) — yêu cầu giải trình ở method_legal_basis")
                .format(doc.awarded_price, line.allocated_budget, pct),
            )


def _vr05_winner_avl_required(doc: Document) -> None:
    """VR-03-05: winner_supplier phải có AVL **còn hiệu lực** (Approved/Conditional)
    cho device_category. Dùng predicate SoT ``_avl_is_live`` (INV-AVL-LIVE,
    02 §IV.6) → raise ServiceError(BUSINESS_RULE) nếu trả 0. Chặn trao thầu cho
    AVL đã hết hạn trong cửa sổ trễ scheduler (INV-AVL-LIVE-1)."""
    if not doc.winner_supplier or not doc.spec_ref:
        return
    spec = frappe.get_doc(_DT_TS, doc.spec_ref)
    category = spec.device_category
    if not _avl_is_live(doc.winner_supplier, category):
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("VR-03-05: Winner '{0}' không có AVL còn hiệu lực (Approved/Conditional) cho category '{1}'")
            .format(doc.winner_supplier, category or "—"),
        )


def _vr07_unique_decision_per_spec(doc: Document) -> None:
    """VR-03-07: 1 Tech Spec ↔ 1 Decision Awarded."""
    if not doc.spec_ref or doc.workflow_state in ("Draft", "Cancelled", "Withdrawn"):
        return
    existing = frappe.db.sql(
        f"""SELECT name FROM `tab{_DT_PD}`
            WHERE spec_ref = %s AND docstatus = 1
              AND workflow_state IN ('Awarded', 'Contract Signed', 'PO Issued')
              AND name != %s
            LIMIT 1""",
        (doc.spec_ref, doc.name or ""),
    )
    if existing:
        raise ServiceError(
            ErrorCode.DUPLICATE,
            _("VR-03-07: Tech Spec {0} đã có Decision Awarded ({1})")
            .format(doc.spec_ref, existing[0][0]),
        )


def _validate_gate_g05(doc: Document) -> None:
    """G05: contract_doc + funding_source + board_approver bắt buộc."""
    missing = []
    if not doc.funding_source:    missing.append("funding_source")
    if not doc.board_approver:    missing.append("board_approver")
    if not doc.contract_doc:      missing.append("contract_doc")
    if missing:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G05: Thiếu trường bắt buộc trước Award: {0}").format(", ".join(missing)),
        )


def _mint_ac_purchase(doc: Document) -> str:
    """Tạo AC Purchase từ Decision."""
    po = frappe.new_doc(_DT_PURCHASE)
    po.supplier = doc.winner_supplier
    po.purchase_date = now_datetime()
    po.procurement_decision_ref = doc.name  # native back-ref (Slide 09 traceability)
    if frappe.db.has_column(_DT_PURCHASE, "imm_procurement_decision"):
        po.imm_procurement_decision = doc.name  # legacy custom field (BR-03-08)
    if getattr(doc, "plan_ref", None) and frappe.db.has_column(
        _DT_PURCHASE, "imm_procurement_plan"
    ):
        po.imm_procurement_plan = doc.plan_ref
    po.imm_tech_spec = doc.spec_ref
    po.imm_funding_source = doc.funding_source
    spec = frappe.get_doc(_DT_TS, doc.spec_ref)
    po.append("devices", {
        "device_model": spec.device_model_ref,
        "qty": doc.quantity or 1,
        "unit_price": (doc.awarded_price or 0) / max(doc.quantity or 1, 1),
    })
    po.insert(ignore_permissions=True)
    return po.name


def _update_plan_line_status(plan_name: str, plan_line: str, status: str) -> None:
    try:
        plan = frappe.get_doc(_DT_PP, plan_name)
        for it in plan.plan_items or []:
            if it.name == plan_line:
                it.status = status
        plan.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 plan line update failed")


# ─── AVL ──────────────────────────────────────────────────────────────────────

def validate_avl(doc: Document) -> None:
    """Auto-compute valid_to = valid_from + validity_years."""
    if doc.valid_from and doc.validity_years:
        doc.valid_to = add_years(doc.valid_from, int(doc.validity_years))


def activate_avl(doc: Document) -> None:
    """Khi AVL submit (Approved), update Supplier custom field."""
    if doc.workflow_state != "Approved":
        return
    _sync_supplier_avl_status(doc.supplier)


def _sync_supplier_avl_status(supplier: str) -> None:
    """Sync AC Supplier.imm_avl_status và imm_avl_categories từ active AVL entries.

    Mệnh đề 'active' (workflow_state ∈ {Approved,Conditional} AND (valid_to IS NULL
    OR valid_to >= CURDATE())) là **reference predicate** của ``_avl_is_live``
    (INV-AVL-LIVE-3 parity, 02 §IV.6). KHÔNG đổi mệnh đề này lẻ — đổi phải đồng bộ
    ``_avl_is_live`` (giữ trùng-từng-bit để không tái-drift)."""
    rows = frappe.db.sql(
        f"""SELECT device_category, workflow_state FROM `tab{_DT_AVL}`
            WHERE supplier = %s AND docstatus = 1
              AND workflow_state IN ('Approved','Conditional')
              AND (valid_to IS NULL OR valid_to >= CURDATE())""",
        (supplier,), as_dict=True,
    )
    if not rows:
        # Không còn AVL active → set Expired
        if frappe.db.has_column(_DT_SUPPLIER, "imm_avl_status"):
            frappe.db.set_value(_DT_SUPPLIER, supplier, "imm_avl_status", "Expired")
            frappe.db.set_value(_DT_SUPPLIER, supplier, "imm_avl_categories", "")
        return
    statuses = {r.workflow_state for r in rows}
    overall = "Approved" if "Approved" in statuses else "Conditional"
    cats = sorted({r.device_category for r in rows if r.device_category})
    if frappe.db.has_column(_DT_SUPPLIER, "imm_avl_status"):
        frappe.db.set_value(_DT_SUPPLIER, supplier, "imm_avl_status", overall)
        frappe.db.set_value(_DT_SUPPLIER, supplier, "imm_avl_categories", ", ".join(cats))


# ─── Supplier Audit ───────────────────────────────────────────────────────────

def on_submit_audit(doc: Document) -> None:
    """Nếu có finding Critical → suspend AVL của vendor đó."""
    if frappe.db.has_column(_DT_SUPPLIER, "imm_last_audit_date"):
        frappe.db.set_value(_DT_SUPPLIER, doc.supplier, "imm_last_audit_date", doc.audit_date)
        next_due = add_months(getdate(doc.audit_date), 12)
        frappe.db.set_value(_DT_SUPPLIER, doc.supplier, "imm_next_audit_date", next_due)

    if doc.overall_result == "Fail" or any(
        f.severity == "Critical" for f in (doc.findings or [])
    ):
        # Suspend tất cả AVL active của vendor — direct DB update vì AVL đã submitted
        avls = frappe.get_all(_DT_AVL, filters={
            "supplier": doc.supplier, "docstatus": 1,
            "workflow_state": ["in", ["Approved", "Conditional"]],
        }, pluck="name")
        for a in avls:
            frappe.db.set_value(
                _DT_AVL, a,
                {"workflow_state": "Suspended",
                 "suspension_reason": f"Suspended by Audit {doc.name}: {doc.overall_result}"},
                update_modified=False,
            )
        _sync_supplier_avl_status(doc.supplier)


# ─── AC Purchase delivery (Slide 14b) ─────────────────────────────────────────

def set_actual_delivery_on_received(doc: Document, method: str | None = None) -> None:
    """Khi AC Purchase chuyển sang Received mà chưa nhập ngày giao thực tế,
    mặc định = hôm nay (Slide 14b — phân biệt deadline vs ngày giao thực tế).

    Idempotent: chỉ set khi status == 'Received' và actual_delivery_date trống.
    """
    if doc.status == "Received" and not doc.actual_delivery_date:
        doc.actual_delivery_date = today()


# ─── AC Purchase ↔ PO model match (Slide 18) ──────────────────────────────────

def validate_receipt_against_po(po_name: str, received_items: list) -> None:
    """Slide 18 — phiếu nhập kho/tiếp nhận tham chiếu PO phải khớp model/phụ tùng.

    Stock agent gọi hàm này trước khi ghi nhận receipt. `received_items` là list
    dict, mỗi item tối thiểu có:
      - {"device_model": "<IMM Device Model>"}  cho thiết bị, HOẶC
      - {"spare_part": "<AC Spare Part>"}       cho phụ tùng

    Raise ServiceError(BUSINESS_RULE) nếu có item không nằm trong PO lines.
    """
    if not po_name:
        raise ServiceError(ErrorCode.VALIDATION, _("Thiếu tham chiếu PO."))
    if not frappe.db.exists(_DT_PURCHASE, po_name):
        raise ServiceError(
            ErrorCode.NOT_FOUND, _("PO {0} không tồn tại.").format(po_name)
        )
    po = frappe.get_doc(_DT_PURCHASE, po_name)
    po_models = {r.device_model for r in (po.get("devices") or []) if r.device_model}
    po_spares = {r.spare_part for r in (po.get("items") or []) if r.spare_part}

    mismatches: list[str] = []
    for it in received_items or []:
        dm = it.get("device_model")
        sp = it.get("spare_part")
        if dm:
            if dm not in po_models:
                mismatches.append(_("Model {0} không có trong PO").format(dm))
        elif sp:
            if sp not in po_spares:
                mismatches.append(_("Phụ tùng {0} không có trong PO").format(sp))
        else:
            mismatches.append(_("Item nhận không xác định model/phụ tùng"))

    if mismatches:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("Slide-18: Hàng nhận không khớp PO {0}: {1}").format(
                po_name, "; ".join(mismatches)
            ),
        )


# ─── AC Purchase validate hook (BR-03-08) ─────────────────────────────────────

def validate_ac_purchase_imm_link(doc: Document, method: str | None = None) -> None:
    """Hook: nếu AC Purchase chứa item nhóm thiết bị y tế (HTM scope) mà thiếu
    `imm_procurement_decision`, throw cảnh báo.

    Stub V1: nếu AC Purchase có field `imm_procurement_decision` (custom field
    được patch v3_1.003 thêm) và rỗng + có ít nhất 1 device row → soft warning.
    Hard enforce sẽ kích hoạt khi `enforce_imm_link=1` ở config.
    """
    if not hasattr(doc, "imm_procurement_decision"):
        return  # Custom field chưa tạo yet — patch chưa chạy
    if doc.imm_procurement_decision:
        return  # OK
    if not (doc.devices or []):
        return  # PO không có device row — không phải TBYT
    # Soft warn — chuyển hard sau khi field được rollout đầy đủ
    frappe.msgprint(
        _("BR-03-08 (warn): AC Purchase chứa thiết bị nhưng chưa link IMM-03 Procurement Decision. "
          "Khuyến nghị tạo PO qua quy trình IMM-03."),
        indicator="orange", title=_("Cảnh báo BR-03-08"),
    )


# ─── Schedulers ───────────────────────────────────────────────────────────────

def check_avl_expiry() -> None:
    """Daily — AVL hết hạn → set Expired; cảnh báo 60d/30d."""
    today_d = getdate(today())
    # Auto-expire
    rows = frappe.db.sql(
        f"""SELECT name, supplier FROM `tab{_DT_AVL}`
            WHERE docstatus = 1 AND workflow_state IN ('Approved','Conditional')
              AND valid_to < CURDATE()""",
        as_dict=True,
    )
    for r in rows:
        # AVL is a submitted doc — use db.set_value to bypass re-submit validation
        frappe.db.set_value(_DT_AVL, r.name, "workflow_state", "Expired",
                            update_modified=False)
        _sync_supplier_avl_status(r.supplier)


def check_audit_due() -> None:
    """Daily — vendor > 12 tháng chưa audit → log."""
    if not frappe.db.has_column(_DT_SUPPLIER, "imm_next_audit_date"):
        return
    rows = frappe.db.sql(
        f"""SELECT name FROM `tab{_DT_SUPPLIER}`
            WHERE imm_next_audit_date IS NOT NULL
              AND imm_next_audit_date <= CURDATE()""",
        as_dict=True,
    )
    if rows:
        frappe.logger("imm03").info(f"IMM-03 audit due: {len(rows)} vendors")


def check_decision_overdue() -> None:
    """Daily — Decision Draft/Negotiation > 60d."""
    rows = frappe.db.sql(
        f"""SELECT name FROM `tab{_DT_PD}`
            WHERE docstatus = 0
              AND workflow_state IN ('Draft','Method Selected','Negotiation')
              AND DATEDIFF(CURDATE(), creation) > 60""",
        as_dict=True,
    )
    if rows:
        frappe.logger("imm03").info(f"IMM-03 decision overdue: {len(rows)}")


def update_vendor_scorecard() -> None:
    """Cron quarterly — tổng hợp KPI feedback từ IMM-04/09/15/10.

    V0.1: skeleton — tạo Scorecard với placeholder values cho mỗi vendor có AVL active.
    Wire dữ liệu thực từ IMM-04/09/15/10 khi có API tương ứng.
    """
    today_d = getdate(today())
    quarter = (today_d.month - 1) // 3 + 1
    year = today_d.year

    # AVL còn hiệu lực (INV-AVL-LIVE parity — KHÔNG sinh scorecard cho NCC có AVL
    # đã hết hạn trong cửa sổ trễ scheduler). Cùng mệnh đề với _avl_is_live / _sync.
    suppliers = frappe.db.sql_list(
        f"""SELECT DISTINCT supplier FROM `tab{_DT_AVL}`
            WHERE docstatus = 1 AND workflow_state IN ('Approved','Conditional')
              AND (valid_to IS NULL OR valid_to >= CURDATE())"""
    )
    for sup in suppliers:
        # Idempotent — skip nếu đã có scorecard cho kỳ này
        if frappe.db.exists(_DT_VS, {
            "supplier": sup, "period_year": year, "period_quarter": quarter,
        }):
            continue
        sc = frappe.new_doc(_DT_VS)
        sc.supplier = sup
        sc.period_year = year
        sc.period_quarter = quarter
        sc.generated_at = now_datetime()
        sc.generated_by = "Administrator"
        # Placeholder — wire data thực sau
        for dim, w in [("Delivery", 20), ("Quality", 25), ("Aftersales", 20),
                       ("Spare", 15), ("Compliance", 20)]:
            sc.append("kpi_rows", {
                "dimension": dim, "weight_pct": w,
                "raw_value": 0, "normalized_score": 3.0,  # neutral baseline
                "weighted": round(3.0 * w / 100, 4),
                "source_module": "TBD",
            })
        sc.overall_score = round(sum(r.weighted for r in sc.kpi_rows), 4)
        sc.commentary = "Auto-generated Q-skeleton. Wire IMM-04/09/15/10 metrics khi LIVE."
        sc.insert(ignore_permissions=True)
        if frappe.db.has_column(_DT_SUPPLIER, "imm_overall_score"):
            frappe.db.set_value(_DT_SUPPLIER, sup, "imm_overall_score", sc.overall_score)
    frappe.db.commit()
