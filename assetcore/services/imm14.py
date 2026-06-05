# Copyright (c) 2026, AssetCore Team
"""IMM-14 — Giải nhiệm thiết bị (Decommission Closure Gate) — Service layer.

Cổng "Hồ sơ giải nhiệm" (Decommission Closure Record): KHÔNG asset nào chuyển
sang lifecycle_status='Decommissioned' nếu chưa tồn tại 1 'Asset Decommission'
record docstatus=1 (Approved) trỏ đúng asset đó.

Core Doc: docs/imm-14/04_Backend_Design.md §IX · docs/imm-14/05_API_Specification.md §6

Nguyên tắc (CLAUDE.md §15):
- Controller chỉ delegate; business logic tập trung ở đây.
- Mọi đổi trạng thái asset đi qua `transition_asset_status` (KHÔNG set_value status).
- Side-effect (lifecycle event / audit / cancel depreciation) do
  `transition_asset_status` lo — service imm14 CHỈ orchestrate (validate +
  build reason + gọi transition). KHÔNG nhân bản logic.
- Message hiển thị user qua MSG.* (notification-contract) — KHÔNG hardcode VI.
"""
from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from assetcore.services.shared import AssetStatus
from assetcore.utils.notify import nthrow
from assetcore.utils.messages import MSG

_DOCTYPE_ASSET = "AC Asset"
_DOCTYPE_DECOM = "Asset Decommission"

# disposal_method ∈ {Huỷ, Điều chuyển/Donation, Bán/Trade-in, Lưu trữ} (BR-14-W2-02)
_VALID_DISPOSAL_METHODS = (
    "Huỷ",
    "Điều chuyển/Donation",
    "Bán/Trade-in",
    "Lưu trữ",
)

# risk_classification ∈ {Low, Medium, High, Critical} ≡ NĐ98 A/B/C/D.
# "C/D" trong acceptance = High / Critical → bắt buộc patient_data_sanitized (WHO §3.6).
_PATIENT_DATA_REQUIRED_RISK = ("High", "Critical")

# độ dài tối thiểu lý do giải nhiệm (BR-14-W2-04)
_MIN_REASON_LEN = 20


# ─────────────────────────────────────────────────────────────────────────────
# GATE predicate (BR-14-W2-01) — SoT cho "asset có closure approved chưa"
# ─────────────────────────────────────────────────────────────────────────────

def _has_approved_decommission(asset: str, *, exclude: str | None = None) -> bool:
    """True nếu tồn tại 1 'Asset Decommission' docstatus=1 trỏ đúng asset.

    `exclude`: bỏ qua 1 record (dùng khi kiểm duplicate cho record đang xét).
    """
    filters: dict = {"asset": asset, "docstatus": 1}
    if exclude:
        filters["name"] = ["!=", exclude]
    return bool(frappe.db.exists(_DOCTYPE_DECOM, filters))


def assert_decommission_gate(asset: str, *, root_record: str | None = None) -> None:
    """GATE chính (BR-14-W2-01): chặn vào Decommissioned nếu chưa có closure approved.

    Gọi từ `transition_asset_status` khi to_status == Decommissioned. Cho qua khi:
      - đã có 1 Asset Decommission docstatus=1 cho asset, HOẶC
      - `root_record` là record đang trong tiến trình submit (docstatus đang
        chuyển 0→1 trong cùng transaction — docstatus in-memory = 1).

    Vi phạm → ServiceError(CONFLICT/BAD_STATE, message VI), lifecycle_status GIỮ NGUYÊN.
    """
    if _has_approved_decommission(asset):
        return
    # Record đang submit ngay lúc này: doc đã set docstatus=1 in-memory nhưng
    # transition chạy trong cùng on_submit (chưa commit). Chấp nhận nếu record
    # trỏ đúng asset và đang ở docstatus=1.
    if root_record and frappe.db.exists(
        _DOCTYPE_DECOM, {"name": root_record, "asset": asset, "docstatus": 1}
    ):
        return
    nthrow(MSG.IMM14_GATE_NO_CLOSURE, asset=asset)


# ─────────────────────────────────────────────────────────────────────────────
# create_decommission — tạo Asset Decommission docstatus=0 (BR-14-W2-06/07)
# ─────────────────────────────────────────────────────────────────────────────

def create_decommission(
    asset: str,
    disposal_method: str,
    decommission_reason: str,
    patient_data_sanitized: bool | int = 0,
    responsible: str | None = None,
    sanitization_note: str = "",
) -> dict:
    """Tạo 'Asset Decommission' docstatus=0. KHÔNG đổi asset status.

    Validate: asset tồn tại + terminal (BR-14-W2-06) + duplicate (BR-14-W2-07)
    + field-level (qua controller validate → validate_before_approve).

    Returns: {name, asset, workflow_state, docstatus}.
    """
    _assert_asset_creatable(asset)

    doc = frappe.get_doc({
        "doctype": _DOCTYPE_DECOM,
        "asset": asset,
        "disposal_method": disposal_method,
        "decommission_reason": decommission_reason,
        "patient_data_sanitized": 1 if patient_data_sanitized else 0,
        "responsible": responsible or frappe.session.user,
        "sanitization_note": sanitization_note or "",
    })
    doc.insert(ignore_permissions=True)
    return {
        "name": doc.name,
        "asset": doc.asset,
        "workflow_state": doc.workflow_state or "Draft",
        "docstatus": doc.docstatus,
    }


def _assert_asset_creatable(asset: str) -> None:
    """BR-14-W2-06 (terminal) + BR-14-W2-07 (duplicate active)."""
    status = frappe.db.get_value(_DOCTYPE_ASSET, asset, "lifecycle_status")
    if status is None:
        nthrow(MSG.IMM14_ASSET_NOT_FOUND, asset=asset)
    if status == AssetStatus.DECOMMISSIONED:
        nthrow(MSG.IMM14_ALREADY_DECOMMISSIONED, asset=asset)
    # BR-14-W2-07: đã có record docstatus ∈ {0,1} cho asset → chặn tạo mới.
    existing = frappe.db.get_value(
        _DOCTYPE_DECOM, {"asset": asset, "docstatus": ["<", 2]}, "name"
    )
    if existing:
        nthrow(MSG.IMM14_DUPLICATE_ACTIVE, asset=asset, existing=existing)


# ─────────────────────────────────────────────────────────────────────────────
# Controller hooks — before_insert / validate / on_submit / on_cancel
# ─────────────────────────────────────────────────────────────────────────────

def before_insert_decommission(doc) -> None:
    """Snapshot asset_name + risk_classification; re-check terminal/duplicate.

    Chạy cả khi tạo qua UI/REST (không qua create_decommission) → giữ gate bền.
    """
    asset = doc.asset
    if not asset or not frappe.db.exists(_DOCTYPE_ASSET, asset):
        nthrow(MSG.IMM14_ASSET_NOT_FOUND, asset=asset or "")
    _assert_asset_creatable(asset)
    snap = frappe.db.get_value(
        _DOCTYPE_ASSET, asset,
        ["asset_name", "risk_classification"], as_dict=True,
    ) or {}
    doc.asset_name_snapshot = snap.get("asset_name") or asset
    doc.risk_classification_snapshot = snap.get("risk_classification") or ""
    if not doc.workflow_state:
        doc.workflow_state = "Draft"


def validate_before_approve(doc, method=None) -> None:
    """BR-14-W2-02..05: field-level + sanitization gate. Thiếu → raise (no submit)."""
    method_value = (doc.disposal_method or "").strip()
    if not method_value:
        nthrow(MSG.IMM14_DISPOSAL_METHOD_REQUIRED)
    if method_value not in _VALID_DISPOSAL_METHODS:
        nthrow(MSG.IMM14_DISPOSAL_METHOD_INVALID, value=method_value)

    reason = (doc.decommission_reason or "").strip()
    if len(reason) < _MIN_REASON_LEN:
        nthrow(MSG.IMM14_REASON_TOO_SHORT, min=_MIN_REASON_LEN)

    if not (doc.responsible or "").strip():
        nthrow(MSG.IMM14_RESPONSIBLE_REQUIRED)

    # BR-14-W2-03: risk High/Critical ⇒ patient_data_sanitized PHẢI = 1 (WHO §3.6).
    risk = (doc.risk_classification_snapshot or "").strip()
    if risk in _PATIENT_DATA_REQUIRED_RISK and not int(doc.patient_data_sanitized or 0):
        nthrow(MSG.IMM14_PATIENT_DATA_REQUIRED, risk=risk)


def on_decommission_submit(doc, method=None) -> None:
    """Hook on_submit (idempotent). Gọi transition_asset_status → Decommissioned.

    Side-effect (lifecycle event 'decommissioned' + audit 'State Change' chứa
    disposal_method + patient_data + cancel pending depreciation) do
    transition_asset_status lo. KHÔNG nhân bản. reason build sao cho audit
    change_summary chứa disposal_method + patient_data (acceptance c).
    """
    from assetcore.services.imm00 import transition_asset_status

    asset = doc.asset
    current = frappe.db.get_value(_DOCTYPE_ASSET, asset, "lifecycle_status")
    actor = doc.responsible or frappe.session.user

    if current == AssetStatus.DECOMMISSIONED:
        # BR-14-W2-08: asset đã Decommissioned (idempotent re-run) → no double effect.
        # transition_asset_status cũng guard prev==to → return; ở đây short-circuit
        # để chắc chắn không double + vẫn set decommissioned_on nếu còn trống.
        if not doc.decommissioned_on:
            frappe.db.set_value(
                _DOCTYPE_DECOM, doc.name, "decommissioned_on",
                now_datetime(), update_modified=False,
            )
        return

    sanitized_label = "Có" if int(doc.patient_data_sanitized or 0) else "Không"
    reason = (
        f"Phương thức: {doc.disposal_method}. "
        f"Đã xử lý dữ liệu bệnh nhân: {sanitized_label}. "
        f"Hồ sơ giải nhiệm: {doc.name}."
    )

    # transition tự áp NEG-09 + gate (qua assert_decommission_gate dưới);
    # raise → submit roll-back, docstatus giữ 0, lifecycle_status GIỮ NGUYÊN.
    transition_asset_status(
        asset,
        AssetStatus.DECOMMISSIONED,
        actor=actor,
        reason=reason,
        root_doctype=_DOCTYPE_DECOM,
        root_record=doc.name,
    )

    frappe.db.set_value(
        _DOCTYPE_DECOM, doc.name, "decommissioned_on",
        now_datetime(), update_modified=False,
    )
    frappe.db.set_value(
        _DOCTYPE_DECOM, doc.name, "workflow_state", "Approved",
        update_modified=False,
    )


def on_decommission_cancel(doc, method=None) -> None:
    """Hook on_cancel. Out-of-scope vòng 2 (rollback) → KHÔNG đảo asset status.

    Ghi 1 audit 'State Change' note: record bị huỷ nhưng asset GIỮ Decommissioned.
    """
    from assetcore.services.imm00 import log_audit_event

    frappe.db.set_value(
        _DOCTYPE_DECOM, doc.name, "workflow_state", "Cancelled",
        update_modified=False,
    )
    try:
        log_audit_event(
            asset=doc.asset,
            event_type="State Change",
            actor=frappe.session.user,
            ref_doctype=_DOCTYPE_DECOM,
            ref_name=doc.name,
            change_summary=(
                f"Hồ sơ giải nhiệm {doc.name} bị huỷ. "
                f"Trạng thái thiết bị giữ nguyên (rollback ngoài phạm vi vòng 2)."
            ),
        )
    except Exception:  # noqa: BLE001
        frappe.log_error(frappe.get_traceback(),
                         "imm14.on_decommission_cancel audit failed")


# ─────────────────────────────────────────────────────────────────────────────
# approve_decommission — orchestrator cho API (validate → submit → transition)
# ─────────────────────────────────────────────────────────────────────────────

def approve_decommission(name: str) -> dict:
    """Duyệt hồ sơ giải nhiệm: validate gate → doc.submit() (0→1) → hook on_submit.

    Idempotent: record đã docstatus=1 → no-op success (KHÔNG double effect).
    NEG-09 / gate raise trong on_submit → submit roll-back, lifecycle_status giữ.

    Returns: {name, workflow_state, docstatus, asset, lifecycle_status, decommissioned_on}.
    """
    if not frappe.db.exists(_DOCTYPE_DECOM, name):
        nthrow(MSG.IMM14_RECORD_NOT_FOUND, name=name)

    doc = frappe.get_doc(_DOCTYPE_DECOM, name)

    if doc.docstatus == 1:
        # Đã approved → idempotent no-op (KHÔNG submit/transition lần 2).
        return _approve_payload(doc)

    if doc.docstatus == 2:
        nthrow(MSG.IMM14_RECORD_NOT_FOUND, name=name)

    # Terminal guard trước submit (asset đã Decommissioned bởi record khác).
    asset_status = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "lifecycle_status")
    if asset_status == AssetStatus.DECOMMISSIONED:
        nthrow(MSG.IMM14_ALREADY_DECOMMISSIONED, asset=doc.asset)

    # validate (controller validate cũng chạy lại) + submit → on_submit transition.
    doc.submit()
    doc.reload()
    return _approve_payload(doc)


def _approve_payload(doc) -> dict:
    lifecycle = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "lifecycle_status")
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state or "Approved",
        "docstatus": doc.docstatus,
        "asset": doc.asset,
        "lifecycle_status": lifecycle,
        "decommissioned_on": doc.decommissioned_on,
    }


# ─────────────────────────────────────────────────────────────────────────────
# get_decommission — đọc chi tiết (enrich)
# ─────────────────────────────────────────────────────────────────────────────

def get_decommission(name: str) -> dict:
    """Đọc chi tiết hồ sơ giải nhiệm + enrich asset_name, responsible_name, lifecycle."""
    if not frappe.db.exists(_DOCTYPE_DECOM, name):
        nthrow(MSG.IMM14_RECORD_NOT_FOUND, name=name)
    doc = frappe.get_doc(_DOCTYPE_DECOM, name)
    out = doc.as_dict()
    out["asset_name"] = doc.asset_name_snapshot or frappe.db.get_value(
        _DOCTYPE_ASSET, doc.asset, "asset_name")
    out["responsible_name"] = frappe.db.get_value(
        "User", doc.responsible, "full_name") if doc.responsible else None
    out["lifecycle_status"] = frappe.db.get_value(
        _DOCTYPE_ASSET, doc.asset, "lifecycle_status")
    return out
