# Copyright (c) 2026, AssetCore Team
"""IMM-00 Foundation Service Layer — v3.0.0

Nguyên tắc: controllers chỉ gọi service; business logic tập trung ở đây.
"""
import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from assetcore.utils.lifecycle import (
    log_audit_event as _log_audit_event,
    create_lifecycle_event as _create_lifecycle_event,
    verify_audit_chain as _verify_audit_chain,
)
from assetcore.utils.email import get_role_emails, safe_sendmail


_DOCTYPE_ASSET = "AC Asset"
_DOCTYPE_CAPA = "IMM CAPA Record"

_STATUS_DRAFT = "Draft"
_STATUS_COMMISSIONED = "Commissioned"
_STATUS_ACTIVE = "Active"
_STATUS_UNDER_MAINTENANCE = "Under Maintenance"
_STATUS_UNDER_REPAIR = "Under Repair"
_STATUS_CALIBRATING = "Calibrating"
_STATUS_OUT_OF_SERVICE = "Out of Service"
_STATUS_DECOMMISSIONED = "Decommissioned"
_BLOCKED_STATUSES = (_STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED)
_DOWNTIME_STATUSES = (_STATUS_UNDER_MAINTENANCE, _STATUS_UNDER_REPAIR,
                      _STATUS_CALIBRATING, _STATUS_OUT_OF_SERVICE)
_DOWNTIME_REASON_MAP = {
    _STATUS_UNDER_MAINTENANCE: "Bảo trì",
    _STATUS_UNDER_REPAIR: "Sửa chữa",
    _STATUS_CALIBRATING: "Hiệu chuẩn",
    _STATUS_OUT_OF_SERVICE: "Hỏng hóc",
}
_DT_DOWNTIME_LOG = "AC Asset Downtime Log"

_ROLE_DEPT_HEAD = "IMM Department Head"
_ROLE_OPS_MANAGER = "IMM Operations Manager"

# ────────────────────────────────────────────
# Asset Lifecycle State Machine (BR-00-02)
# ────────────────────────────────────────────
# Định nghĩa các transition hợp lệ. KHÔNG có entry trong dict = trạng thái cuối.
# Sửa ở đây = sửa luôn workflow JSON: assetcore/workflow/ac_asset_lifecycle_workflow.json
_VALID_ASSET_TRANSITIONS: dict[str, set[str]] = {
    _STATUS_DRAFT:            {_STATUS_COMMISSIONED, _STATUS_DECOMMISSIONED},
    _STATUS_COMMISSIONED:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_ACTIVE:           {_STATUS_UNDER_MAINTENANCE, _STATUS_UNDER_REPAIR,
                               _STATUS_CALIBRATING, _STATUS_OUT_OF_SERVICE,
                               _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_MAINTENANCE:{_STATUS_ACTIVE, _STATUS_UNDER_REPAIR,
                               _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_REPAIR:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_CALIBRATING:      {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_OUT_OF_SERVICE:   {_STATUS_ACTIVE, _STATUS_UNDER_REPAIR, _STATUS_DECOMMISSIONED},
    _STATUS_DECOMMISSIONED:   set(),  # terminal
}


class InvalidAssetTransition(Exception):
    """Raised khi transition không nằm trong _VALID_ASSET_TRANSITIONS."""


# ────────────────────────────────────────────
# Audit + Lifecycle (re-export from utils)
# ────────────────────────────────────────────

def log_audit_event(**kwargs) -> str:
    return _log_audit_event(**kwargs)


def create_lifecycle_event(**kwargs) -> str:
    return _create_lifecycle_event(**kwargs)


def verify_audit_chain(asset: str) -> dict:
    return _verify_audit_chain(asset)


# ────────────────────────────────────────────
# Asset status transitions (BR-00-02, 04, 05, 10)
# ────────────────────────────────────────────

def transition_asset_status(
    asset_name: str,
    to_status: str,
    actor: str = None,
    reason: str = "",
    root_doctype: str = None,
    root_record: str = None,
) -> None:
    prev_status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status") or ""
    if prev_status == to_status:
        return

    # State machine guard — chỉ cho phép transition đã định nghĩa.
    # Nếu prev_status rỗng (asset mới insert), không validate (asset chưa đi vào lifecycle).
    if prev_status:
        allowed = _VALID_ASSET_TRANSITIONS.get(prev_status, set())
        if to_status not in allowed:
            allowed_str = ", ".join(sorted(allowed)) or "(không có)"
            raise InvalidAssetTransition(
                f"Không thể chuyển '{asset_name}' từ '{prev_status}' → '{to_status}'. "
                f"Trạng thái cho phép từ '{prev_status}': {allowed_str}"
            )

    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status", to_status)

    create_lifecycle_event(
        asset=asset_name,
        event_type=_lifecycle_event_for(to_status),
        actor=actor or frappe.session.user,
        from_status=prev_status,
        to_status=to_status,
        root_doctype=root_doctype,
        root_record=root_record,
        notes=reason,
    )
    log_audit_event(
        asset=asset_name,
        event_type="State Change",
        actor=actor or frappe.session.user,
        ref_doctype=root_doctype or _DOCTYPE_ASSET,
        ref_name=root_record or asset_name,
        change_summary=f"lifecycle_status: {prev_status} -> {to_status}. {reason}",
        from_status=prev_status,
        to_status=to_status,
    )

    _sync_downtime_log(
        asset=asset_name, prev=prev_status, nxt=to_status,
        root_doctype=root_doctype, root_record=root_record, reason_note=reason,
    )

    if to_status == _STATUS_DECOMMISSIONED:
        _suspend_all_schedules(asset_name)


def _sync_downtime_log(*, asset: str, prev: str, nxt: str,
                        root_doctype: str | None, root_record: str | None,
                        reason_note: str) -> None:
    """Tự động open/close AC Asset Downtime Log theo transition.
    - Vào downtime status → open log mới
    - Ra khỏi downtime status → close log đang mở
    - Downtime → Downtime (vd: Under Repair → Out of Service) → close log cũ + open log mới
    """
    was_down = prev in _DOWNTIME_STATUSES
    is_down = nxt in _DOWNTIME_STATUSES
    if was_down:
        _close_open_downtime_log(asset)
    if is_down:
        _open_downtime_log(
            asset=asset, reason=_DOWNTIME_REASON_MAP.get(nxt, "Khác"),
            ref_dt=root_doctype, ref_name=root_record, note=reason_note,
        )


def _open_downtime_log(*, asset: str, reason: str, ref_dt: str | None,
                        ref_name: str | None, note: str) -> str:
    doc = frappe.get_doc({
        "doctype": _DT_DOWNTIME_LOG,
        "asset": asset,
        "reason": reason,
        "reference_doctype": ref_dt,
        "reference_name": ref_name,
        "start_time": frappe.utils.now_datetime(),
        "is_open": 1,
        "notes": note or "",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _close_open_downtime_log(asset: str) -> None:
    rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": asset, "is_open": 1},
        fields=["name"], limit=5,
    )
    if not rows:
        return
    now_dt = frappe.utils.now_datetime()
    for r in rows:
        doc = frappe.get_doc(_DT_DOWNTIME_LOG, r["name"])
        doc.end_time = now_dt
        doc.save(ignore_permissions=True)


def _lifecycle_event_for(to_status: str) -> str:
    return {
        "Active": "activated",
        "Commissioned": "commissioned",
        "Under Maintenance": "pm_started",
        "Under Repair": "repair_opened",
        "Calibrating": "calibration_started",
        "Out of Service": "out_of_service",
        "Decommissioned": "decommissioned",
    }.get(to_status, "restored")


def _suspend_all_schedules(asset_name: str) -> None:
    """BR-00-04: Decommissioned -> tat co PM/Cal tren AC Asset."""
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, {
        "is_pm_required": 0,
        "is_calibration_required": 0,
        "next_pm_date": None,
        "next_calibration_date": None,
    })


_GMDN_STATUS_ACTIVE = "In Use"
_GMDN_STATUS_INACTIVE = "Not Use"
_GMDN_BLOCKED_LIFECYCLE = (_STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED)


def update_gmdn_status(asset_name: str, gmdn_status: str, reason: str) -> dict:
    """Cập nhật GMDN Status cho AC Asset. BR-00-11, BR-00-12."""
    if gmdn_status not in (_GMDN_STATUS_ACTIVE, _GMDN_STATUS_INACTIVE):
        frappe.throw(_("GMDN Status không hợp lệ"))
    if not reason or len(reason.strip()) < 5:
        frappe.throw(_("Lý do thay đổi tối thiểu 5 ký tự"))

    if not frappe.db.exists(_DOCTYPE_ASSET, asset_name):
        frappe.throw(_("Không tìm thấy thiết bị"))

    data = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["gmdn_status", "lifecycle_status"], as_dict=True,
    )
    old_status = data.gmdn_status or _GMDN_STATUS_ACTIVE
    lifecycle = data.lifecycle_status or ""

    if gmdn_status == _GMDN_STATUS_ACTIVE and lifecycle in _GMDN_BLOCKED_LIFECYCLE:
        frappe.throw(_("Không thể kích hoạt GMDN khi thiết bị ở trạng thái '{0}'").format(lifecycle))

    if old_status == gmdn_status:
        frappe.throw(_(f"GMDN Status đã là '{gmdn_status}'"))

    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "gmdn_status", gmdn_status)

    log_audit_event(
        asset=asset_name,
        event_type="State Change",
        actor=frappe.session.user,
        ref_doctype=_DOCTYPE_ASSET,
        ref_name=asset_name,
        change_summary=f"GMDN: {old_status} → {gmdn_status}. Lý do: {reason}",
        from_status=old_status,
        to_status=gmdn_status,
    )

    return {"name": asset_name, "gmdn_status": gmdn_status, "previous": old_status}


def toggle_gmdn_status_via_qr(asset_name: str) -> dict:
    """Toggle GMDN Status qua QR scan. Default reason = 'Quét QR @ <timestamp>'."""
    if not frappe.db.exists(_DOCTYPE_ASSET, asset_name):
        frappe.throw(_("Không tìm thấy thiết bị"))
    current = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "gmdn_status") or _GMDN_STATUS_INACTIVE
    target = _GMDN_STATUS_ACTIVE if current == _GMDN_STATUS_INACTIVE else _GMDN_STATUS_INACTIVE
    from frappe.utils import now
    reason = f"Quét QR lúc {now()}"
    return update_gmdn_status(asset_name, target, reason)


def validate_asset_for_operations(asset_name: str) -> None:
    """BR-00-05: Out of Service / Decommissioned -> block tao Work Order."""
    status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status")
    if status in _BLOCKED_STATUSES:
        frappe.throw(_(f"Khong the tao Work Order - thiet bi dang o trang thai '{status}' (BR-00-05)."))


# ────────────────────────────────────────────
# SLA Policy lookup (BR-00-07)
# ────────────────────────────────────────────

def get_sla_policy(priority: str, risk_class: str = None) -> dict:
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "risk_class": risk_class, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    if rows:
        return rows[0]
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "is_default": 1, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    return rows[0] if rows else {}


# ────────────────────────────────────────────
# CAPA lifecycle
# ────────────────────────────────────────────

def create_capa(asset: str, source_type: str, source_ref: str, severity: str,
                description: str, responsible: str, due_days: int = 30) -> str:
    doc = frappe.get_doc({
        "doctype": _DOCTYPE_CAPA,
        "asset": asset,
        "source_type": source_type,
        "source_ref": source_ref,
        "severity": severity,
        "description": description,
        "responsible": responsible,
        "opened_date": nowdate(),
        "due_date": add_days(nowdate(), due_days),
        "status": "Open",
    }).insert(ignore_permissions=True)
    log_audit_event(
        asset=asset, event_type="CAPA", actor=frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=doc.name,
        change_summary=f"CAPA opened: severity={severity}",
    )
    return doc.name


def close_capa(capa_name: str, root_cause: str, corrective_action: str,
               preventive_action: str, effectiveness_check: str = None,
               actor: str = None) -> None:
    doc = frappe.get_doc(_DOCTYPE_CAPA, capa_name)
    doc.root_cause = root_cause
    doc.corrective_action = corrective_action
    doc.preventive_action = preventive_action
    if effectiveness_check:
        doc.effectiveness_check = effectiveness_check
    doc.status = "Closed"
    doc.closed_date = nowdate()
    doc.submit()
    log_audit_event(
        asset=doc.asset, event_type="CAPA", actor=actor or frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=capa_name,
        change_summary="CAPA closed",
    )


# ────────────────────────────────────────────
# Scheduler jobs
# ────────────────────────────────────────────

def check_capa_overdue() -> None:
    rows = frappe.db.sql(
        """
        SELECT name, asset, responsible, due_date
        FROM `tabIMM CAPA Record`
        WHERE status IN ('Open', 'In Progress')
          AND docstatus = 0
          AND due_date < %s
        """,
        (nowdate(),),
        as_dict=True,
    )
    if not rows:
        return
    names = [r.name for r in rows]
    frappe.db.sql(
        f"UPDATE `tabIMM CAPA Record` SET status = 'Overdue' WHERE name IN ({', '.join(['%s'] * len(names))})",
        names,
    )
    recipients = set(get_role_emails(["IMM QA Officer"]))
    recipients.update([r.responsible for r in rows if r.responsible])
    recipients.discard("")
    if recipients:
        body = "\n".join(f"- {r.name} | {r.asset} | due {r.due_date}" for r in rows)
        safe_sendmail(list(recipients), f"[AssetCore] {len(rows)} CAPA overdue",
                      f"Cac CAPA sau da qua han:\n\n{body}")


def check_vendor_contract_expiry() -> None:
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "AC Supplier",
            filters={"contract_end": target, "is_active": 1},
            fields=["name", "supplier_name", "contract_end"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.supplier_name} | ket thuc {r.contract_end}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] HD NCC con {d} ngay",
                          f"{len(rows)} hop dong NCC sap het han trong {d} ngay:\n\n{body}")


def check_registration_expiry() -> None:
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "byt_reg_expiry": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "byt_reg_no", "byt_reg_expiry"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.asset_name} | BYT {r.byt_reg_no} | {r.byt_reg_expiry}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] Dang ky BYT con {d} ngay",
                          f"{len(rows)} thiet bi co dang ky BYT sap het han trong {d} ngay:\n\n{body}")


_DT_TRANSFER = "Asset Transfer"
_TRANSFER_ROLES_APPROVE = {"IMM Department Head", "IMM Operations Manager", "IMM System Admin"}
_ERR_TRANSFER_NOT_FOUND = "Phiếu luân chuyển '{0}' không tồn tại"
_TRANSFER_STATUS_PENDING   = "Pending Approval"
_TRANSFER_STATUS_APPROVED  = "Approved"
_TRANSFER_STATUS_REJECTED  = "Rejected"
_TRANSFER_STATUS_RECEIVED  = "Received"
_TRANSFER_STATUS_CANCELLED = "Cancelled"


def create_transfer_request(data: dict) -> dict:
    """Tạo phiếu yêu cầu luân chuyển thiết bị (status = Pending Approval).

    data: asset, transfer_type, to_location, reason
          [to_department, to_custodian, expected_return_date, notes]
    """
    required = ("asset", "transfer_type", "to_location", "reason")
    missing = [f for f in required if not data.get(f)]
    if missing:
        frappe.throw(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)))

    asset_name = data["asset"]
    if not frappe.db.exists(_DOCTYPE_ASSET, asset_name):
        frappe.throw(_("Thiết bị '{0}' không tồn tại").format(asset_name))

    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}

    doc = frappe.new_doc(_DT_TRANSFER)
    doc.asset          = asset_name
    doc.transfer_date  = data.get("transfer_date") or nowdate()
    doc.transfer_type  = data["transfer_type"]
    doc.from_location  = prev.get("location")
    doc.from_department= prev.get("department")
    doc.from_custodian = prev.get("custodian")
    doc.to_location    = data["to_location"]
    doc.to_department  = data.get("to_department")
    doc.to_custodian   = data.get("to_custodian")
    doc.expected_return_date = data.get("expected_return_date")
    doc.reason         = data["reason"]
    doc.notes          = data.get("notes")
    doc.status         = _TRANSFER_STATUS_PENDING
    doc.insert(ignore_permissions=False)

    _notify_transfer_approvers(doc)
    log_audit_event(
        asset=asset_name, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=doc.name,
        change_summary=f"Yêu cầu luân chuyển đến {data['to_location']}",
    )
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


def approve_transfer_request(name: str) -> dict:
    """Phê duyệt phiếu luân chuyển: cập nhật vị trí thiết bị ngay."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    roles = set(frappe.get_roles(frappe.session.user))
    if not _TRANSFER_ROLES_APPROVE.intersection(roles):
        frappe.throw(_("Chỉ Trưởng khoa / Quản lý vận hành mới được phê duyệt luân chuyển"))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể phê duyệt").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":        _TRANSFER_STATUS_APPROVED,
        "approved_by":   frappe.session.user,
        "approval_date": nowdate(),
    })

    transfer_asset(
        asset_name=doc.asset,
        to_location=doc.to_location,
        to_department=doc.to_department,
        to_custodian=doc.to_custodian,
        transfer_doc=name,
        actor=frappe.session.user,
    )

    _notify_transfer_requester(doc, approved=True)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_APPROVED}


def reject_transfer_request(name: str, rejection_reason: str) -> dict:
    """Từ chối phiếu luân chuyển."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    roles = set(frappe.get_roles(frappe.session.user))
    if not _TRANSFER_ROLES_APPROVE.intersection(roles):
        frappe.throw(_("Chỉ Trưởng khoa / Quản lý vận hành mới được từ chối luân chuyển"))

    if not rejection_reason or len(rejection_reason.strip()) < 5:
        frappe.throw(_("Lý do từ chối là bắt buộc (tối thiểu 5 ký tự)"))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể từ chối").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":           _TRANSFER_STATUS_REJECTED,
        "rejected_by":      frappe.session.user,
        "rejection_reason": rejection_reason.strip(),
    })

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Từ chối: {rejection_reason}",
    )
    _notify_transfer_requester(doc, approved=False)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_REJECTED}


def confirm_receipt(name: str, handover_notes: str = "") -> dict:
    """Bên nhận xác nhận đã tiếp nhận thiết bị (status → Received)."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_APPROVED:
        frappe.throw(_("Phiếu phải ở trạng thái 'Approved' trước khi xác nhận tiếp nhận"))

    updates: dict = {
        "status":        _TRANSFER_STATUS_RECEIVED,
        "received_by":   frappe.session.user,
        "received_date": nowdate(),
    }
    if handover_notes:
        updates["handover_notes"] = handover_notes
    frappe.db.set_value(_DT_TRANSFER, name, updates)

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Tiếp nhận tại {doc.to_location}",
    )
    create_lifecycle_event(
        asset=doc.asset, event_type="transferred",
        actor=frappe.session.user,
        root_doctype=_DT_TRANSFER, root_record=name,
        notes=f"Tiếp nhận hoàn tất bởi {frappe.session.user}",
    )
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_RECEIVED, "received_by": frappe.session.user}


def cancel_transfer_request(name: str) -> dict:
    """Hủy phiếu luân chuyển (chỉ khi đang Pending Approval)."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    current_status = frappe.db.get_value(_DT_TRANSFER, name, "status")
    if current_status not in (_TRANSFER_STATUS_PENDING, _TRANSFER_STATUS_REJECTED):
        frappe.throw(_("Chỉ có thể hủy phiếu đang Pending Approval hoặc Rejected"))

    frappe.db.set_value(_DT_TRANSFER, name, "status", _TRANSFER_STATUS_CANCELLED)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_CANCELLED}


def _notify_transfer_approvers(doc) -> None:
    recipients = get_role_emails(list(_TRANSFER_ROLES_APPROVE))
    if not recipients:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    safe_sendmail(
        recipients=recipients,
        subject=f"[Yêu cầu phê duyệt] Luân chuyển thiết bị: {asset_name}",
        message=(
            f"<p>Có yêu cầu luân chuyển thiết bị mới cần phê duyệt.</p>"
            f"<ul>"
            f"<li>Phiếu: <strong>{doc.name}</strong></li>"
            f"<li>Thiết bị: {asset_name} ({doc.asset})</li>"
            f"<li>Loại: {doc.transfer_type}</li>"
            f"<li>Từ: {doc.from_location or '—'} → Đến: {doc.to_location}</li>"
            f"<li>Lý do: {doc.reason}</li>"
            f"<li>Người yêu cầu: {frappe.session.user}</li>"
            f"</ul>"
            f"<p>Vui lòng vào hệ thống để phê duyệt hoặc từ chối.</p>"
        ),
    )


def _notify_transfer_requester(doc, approved: bool) -> None:
    owner = frappe.db.get_value(_DT_TRANSFER, doc.name, "owner")
    if not owner:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    action = "được phê duyệt" if approved else "bị từ chối"
    body = (
        f"<p>Yêu cầu luân chuyển thiết bị <strong>{asset_name}</strong> đã {action}.</p>"
        f"<ul><li>Phiếu: {doc.name}</li>"
        f"<li>Người xử lý: {frappe.session.user}</li>"
    )
    if not approved and doc.rejection_reason:
        body += f"<li>Lý do từ chối: {doc.rejection_reason}</li>"
    body += "</ul>"
    safe_sendmail(
        recipients=[owner],
        subject=f"[Luân chuyển thiết bị] Phiếu {doc.name} {action}",
        message=body,
    )


def transfer_asset(
    asset_name: str,
    to_location: str,
    to_department: str = None,
    to_custodian: str = None,
    transfer_doc: str = None,
    actor: str = None,
) -> None:
    """Cập nhật vị trí / phòng ban / phụ trách AC Asset và ghi audit trail."""
    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, {
        "location": to_location,
        "department": to_department,
        "custodian": to_custodian,
    })
    summary = (
        f"Luân chuyển: vị trí {prev.get('location')} → {to_location}"
        + (f", phòng ban {prev.get('department')} → {to_department}" if to_department else "")
        + (f", phụ trách {prev.get('custodian')} → {to_custodian}" if to_custodian else "")
    )
    create_lifecycle_event(
        asset=asset_name,
        event_type="transferred",
        actor=actor or frappe.session.user,
        root_doctype=_DT_TRANSFER,
        root_record=transfer_doc,
        notes=summary,
    )
    log_audit_event(
        asset=asset_name,
        event_type="Transfer",
        actor=actor or frappe.session.user,
        ref_doctype=_DT_TRANSFER,
        ref_name=transfer_doc,
        change_summary=summary,
    )


def check_insurance_expiry() -> None:
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "insurance_end_date": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "insurance_policy_no", "insurer_name", "insurance_end_date"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.asset_name} | HĐ {r.insurance_policy_no or '?'} | {r.insurer_name or '?'} | {r.insurance_end_date}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Bảo hiểm thiết bị còn {d} ngày",
                f"{len(rows)} thiết bị có bảo hiểm sắp hết hạn trong {d} ngày:\n\n{body}",
            )


def check_service_contract_expiry() -> None:
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "Service Contract",
            filters={"contract_end": target, "docstatus": 1},
            fields=["name", "contract_title", "supplier", "contract_end"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.contract_title} | NCC {r.supplier} | {r.contract_end}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Hợp đồng dịch vụ còn {d} ngày",
                f"{len(rows)} hợp đồng dịch vụ sắp hết hạn trong {d} ngày:\n\n{body}",
            )


def rollup_asset_kpi() -> None:
    """Monthly 1st 06:00: rollup KPI (MTTR avg, uptime_pct) cho tung thiet bi."""
    # MTTR: avg of last 12 completed repairs per asset
    repair_rows = frappe.db.sql(
        """
        SELECT asset_ref, AVG(mttr_hours) AS avg_mttr, COUNT(*) AS repair_count
        FROM (
            SELECT asset_ref, mttr_hours,
                   ROW_NUMBER() OVER (PARTITION BY asset_ref ORDER BY completion_datetime DESC) AS rn
            FROM `tabAsset Repair`
            WHERE docstatus = 1 AND status = 'Completed' AND mttr_hours IS NOT NULL
        ) ranked
        WHERE rn <= 12
        GROUP BY asset_ref
        """,
        as_dict=True,
    )
    for r in repair_rows:
        if frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "mttr_hours", round(r.avg_mttr, 2))

    # Uptime: (days_in_month - days_in_repair) / days_in_month * 100
    from frappe.utils import get_first_day, get_last_day, date_diff
    month_start = get_first_day(nowdate())
    month_end = get_last_day(nowdate())
    days_in_month = date_diff(month_end, month_start) + 1

    downtime_rows = frappe.db.sql(
        """
        SELECT asset_ref, SUM(mttr_hours) AS total_downtime_h
        FROM `tabAsset Repair`
        WHERE docstatus = 1 AND status = 'Completed'
          AND completion_datetime >= %s AND completion_datetime <= %s
        GROUP BY asset_ref
        """,
        (str(month_start), str(month_end)),
        as_dict=True,
    )
    for r in downtime_rows:
        if not frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            continue
        downtime_days = (r.total_downtime_h or 0) / 24.0
        uptime_pct = round(max(0, (days_in_month - downtime_days) / days_in_month * 100), 2)
        frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "uptime_pct", uptime_pct)
