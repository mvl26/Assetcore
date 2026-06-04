# Copyright (c) 2026, AssetCore Team
# IMM-06 User Training & Competency Management — Service Layer.
from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, add_months, getdate, now_datetime, nowdate, date_diff

from assetcore.repositories.training_repo import (
    CompetencyAlertLogRepo,
    GapReportRepo,
    TrainingProgramRepo,
    TrainingSessionRepo,
    UserCompetencyRepo,
)
from assetcore.services.shared import ErrorCode, ServiceError, normalize_filters
from assetcore.services.shared import rbac
from assetcore.utils.lifecycle import log_audit_event


# ─── Status constants ────────────────────────────────────────────────────────

class ProgramStatus:
    DRAFT = "Draft"
    ACTIVE = "Active"
    ARCHIVED = "Archived"


class SessionStatus:
    PLANNED = "Planned"
    CONFIRMED = "Confirmed"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    VERIFIED = "Verified"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class CompetencyStatus:
    PENDING = "Pending Assessment"
    ACTIVE = "Active"
    EXPIRING = "Expiring"
    EXPIRED = "Expired"
    SUSPENDED = "Suspended"
    REVOKED = "Revoked"

    AUTHORIZED = (ACTIVE, EXPIRING)


# ─── BR-06-13 SoT — recertification_due_date (Vòng 22) ────────────────────────

RECERT_LEAD_DAYS = 60  # INVARIANT — lead time tái chứng nhận, đo bằng NGÀY (không phải tháng)


# ─── BR-06-14 SoT — predicate "Sắp/Đã hết hạn" năng lực (live, date-derived) ───

EXPIRY_WINDOW_DAYS = 60  # INVARIANT — cửa sổ nhìn trước "Sắp hết hạn"; KHỚP default get_expiring_competencies()


def _expiring_competency_filter() -> dict:
    """SoT DUY NHẤT cho predicate "Sắp hết hạn" (live, theo expiry_date vs today).

    expiring(c) ⟺ workflow_state ∈ {Active, Expiring}
                  ∧ expiry_date ∈ [today, today + EXPIRY_WINDOW_DAYS]

    Dùng CHUNG cho cả KPI count (get_dashboard_stats) lẫn drill
    (get_expiring_competencies) → tile card == drill list, KHÔNG drift.

    KHÔNG đếm theo workflow_state thuần: scheduler chỉ stamp 'Expiring' đúng mốc
    90/60/30 ngày → năng lực hết hạn trong 45 ngày (chưa trúng mốc) vẫn còn cờ
    'Active' nhưng PHẢI vào 'Sắp hết hạn'. Revoked/Suspended/Pending bị loại.

    Returns:
        dict filter Frappe (inclusive cả 2 biên cửa sổ).
    """
    cutoff_end = str(add_days(nowdate(), EXPIRY_WINDOW_DAYS))
    return {
        "workflow_state": ["in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]],
        "expiry_date": ["between", [nowdate(), cutoff_end]],
    }


def _expired_competency_filter() -> dict:
    """SoT DUY NHẤT cho predicate "Đã hết hạn" (live, theo expiry_date vs today).

    expired(c) ⟺ workflow_state ∈ {Active, Expiring, Expired}
                 ∧ expiry_date < today

    Bao gồm cả năng lực còn cờ 'Active'/'Expiring' mà scheduler lỡ phiên
    auto_expire (cửa-sổ-trễ-scheduler) → KHÔNG undercount operator quá hạn.
    Revoked/Suspended/Pending KHÔNG bao giờ bị đếm.

    Returns:
        dict filter Frappe (expiry_date < today, exclusive today).
    """
    return {
        "workflow_state": ["in", [
            CompetencyStatus.ACTIVE,
            CompetencyStatus.EXPIRING,
            CompetencyStatus.EXPIRED,
        ]],
        "expiry_date": ["<", nowdate()],
    }


def compute_competency_dates(achieved_date, validity_months: int) -> dict:
    """SoT DUY NHẤT cho expiry_date + recertification_due_date (BR-06-13).

    INVARIANT (quy ước duy nhất, không đổi):
        expiry_date              = achieved_date + validity_months tháng
        recertification_due_date = expiry_date − RECERT_LEAD_DAYS (60 ngày)

    Anchor = expiry_date (KHÔNG anchor achieved_date + (validity − 2) tháng — công thức
    đó trôi 0–2 ngày theo độ dài tháng 28/30/31 → nguồn gốc divergence). "60 ngày" khớp
    filter scheduler `check_recertification_due` (`add_days(nowdate(), 60)`) và mốc
    reminder T−90/−60/−30 đo bằng ngày.

    Mọi write-site (creation, signoff recompute, controller before_save,
    recertify_competency, set_computed_competency_fields, compute_expiry_dates) PHẢI gọi
    hàm này — CẤM inline `add_days(expiry, -60)` hay `add_months(achieved, validity-2)`.

    Thuần tính (không đọc DB). Cùng input → cùng output (idempotent).

    Args:
        achieved_date: ngày đạt năng lực (str ISO hoặc date).
        validity_months: số tháng hiệu lực.

    Returns:
        dict: {"expiry_date": <date>, "recertification_due_date": <date>}.
    """
    expiry = add_months(achieved_date, int(validity_months))
    return {
        "expiry_date": expiry,
        "recertification_due_date": add_days(expiry, -RECERT_LEAD_DAYS),
    }


# ─── Training Program ─────────────────────────────────────────────────────────

def list_training_programs(filters: dict, *, page: int = 1,
                            page_size: int = 20) -> dict:
    """Liệt kê chương trình đào tạo với phân trang.

    Loại trừ các bản ghi test fixture (`program_code` bắt đầu bằng `_Test`)
    khỏi danh sách hiển thị cho người dùng cuối — defense-in-depth khi
    fixture của bench run-tests bị leak sang DB live (xem `tests/test_imm06.py`).
    """
    nf = normalize_filters(filters)
    nf.setdefault("program_code", ["not like", "\\_Test%"])
    rows, pg = TrainingProgramRepo.list(
        filters=nf,
        fields=["name", "program_code", "program_name", "training_type",
                "target_device_model", "target_device_category", "is_active",
                "passing_score_pct", "validity_period_months", "duration_hours"],
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def create_training_program(data: dict) -> dict:
    """Tạo chương trình đào tạo mới."""
    _require_training_officer()
    if not data.get("target_device_model") and not data.get("target_device_category"):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Phải có ít nhất Device Model hoặc Device Category")
    # Strip empty-string Link fields to avoid Frappe link validation errors
    _LINK_FIELDS = ("target_device_model", "target_device_category", "qms_doc_ref")
    clean = {k: v for k, v in data.items() if not (k in _LINK_FIELDS and v == "")}
    doc = TrainingProgramRepo.create(clean)
    frappe.db.commit()
    return {"name": doc.name, "program_code": doc.program_code}


def get_training_program(name: str) -> dict:
    """Lấy chi tiết chương trình đào tạo."""
    doc = TrainingProgramRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy chương trình: {name}")
    result = doc.as_dict()
    if result.get("target_device_model"):
        result["target_device_model_name"] = frappe.db.get_value(
            "IMM Device Model", result["target_device_model"], "model_name") or result["target_device_model"]
    return result


# ─── Training Session ─────────────────────────────────────────────────────────

def list_training_sessions(filters: dict, *, page: int = 1,
                            page_size: int = 20) -> dict:
    """Liệt kê buổi đào tạo."""
    rows, pg = TrainingSessionRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "training_program", "session_date", "session_type",
                "instructor", "instructor_external_name", "location",
                "workflow_state", "duration_planned_hours"],
        order_by="session_date desc",
        page=page, page_size=page_size,
    )
    # Enrich human-readable names so the list never shows raw email / code.
    prog_ids = {r["training_program"] for r in rows if r.get("training_program")}
    user_ids = {r["instructor"] for r in rows if r.get("instructor")}
    prog_names = {
        p.name: p.program_name
        for p in frappe.get_all("IMM Training Program",
                                 filters={"name": ("in", list(prog_ids))},
                                 fields=["name", "program_name"])
    } if prog_ids else {}
    user_names = {
        u.name: u.full_name
        for u in frappe.get_all("User",
                                filters={"name": ("in", list(user_ids))},
                                fields=["name", "full_name"])
    } if user_ids else {}
    for r in rows:
        r["program_name"] = prog_names.get(r.get("training_program")) or r.get("training_program")
        r["instructor_full_name"] = user_names.get(r.get("instructor")) or ""
        r["trainer_name"] = r["instructor_full_name"] or r.get("instructor_external_name") or ""
    return {"data": rows, "pagination": pg}


def create_training_session(data: dict) -> dict:
    """Tạo buổi đào tạo mới liên kết với một chương trình."""
    _require_training_officer()
    program = data.get("training_program")
    if not program or not TrainingProgramRepo.exists(program):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy chương trình: {program}")
    if not data.get("instructor") and not data.get("instructor_external_name"):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Phải có ít nhất giảng viên nội bộ hoặc giảng viên bên ngoài")
    doc = TrainingSessionRepo.create(data)
    frappe.db.commit()
    return {"name": doc.name, "workflow_state": doc.workflow_state}


def start_training_session(session_name: str) -> dict:
    """Chuyển session sang In Progress."""
    _require_training_officer()
    doc = _get_session_or_raise(session_name)
    if doc.workflow_state not in (SessionStatus.CONFIRMED, SessionStatus.PLANNED):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể bắt đầu ở trạng thái {doc.workflow_state}")
    doc.workflow_state = SessionStatus.IN_PROGRESS
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    return {"name": session_name, "workflow_state": SessionStatus.IN_PROGRESS}


def complete_training_session(session_name: str, results: list[dict]) -> dict:
    """Hoàn thành session, cập nhật kết quả học viên, tạo competency records."""
    _require_training_officer()
    doc = _get_session_or_raise(session_name)
    if doc.workflow_state != SessionStatus.IN_PROGRESS:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Session phải ở trạng thái In Progress, hiện tại: {doc.workflow_state}")

    # Apply scores to participant rows
    result_map: dict[str, dict] = {r["user"]: r for r in results if r.get("user")}
    program_doc = frappe.get_doc("IMM Training Program", doc.training_program)
    pass_score = float(program_doc.passing_score_pct or 70.0)

    passing_participants = []
    for p in doc.participants:
        row_result = result_map.get(p.user)
        if not row_result:
            continue
        p.theory_score = row_result.get("theory_score", 0)
        p.practical_score = row_result.get("practical_score", 0)
        avg_score = (float(p.theory_score) + float(p.practical_score)) / 2.0
        p.overall_result = "Pass" if avg_score >= pass_score else "Fail"
        if p.overall_result == "Pass":
            passing_participants.append(p)

    # Save session as Completed first, then create competency records
    doc.workflow_state = SessionStatus.COMPLETED
    doc.flags.ignore_links = True
    TrainingSessionRepo.save(doc)
    frappe.db.commit()

    # Create competency records in separate transaction
    new_competencies: list[str] = []
    for p in passing_participants:
        comp_name = _create_competency_record(p, doc, program_doc)
        if comp_name:
            new_competencies.append(comp_name)
            frappe.db.set_value("IMM Training Participant", p.name, "competency_record", comp_name)
    if new_competencies:
        frappe.db.commit()

    return {
        "name": session_name,
        "workflow_state": SessionStatus.COMPLETED,
        "competencies_created": new_competencies,
    }


def _create_competency_record(participant, session_doc, program_doc) -> str | None:
    """Tạo IMM User Competency cho học viên đạt."""
    try:
        achieved_date = session_doc.session_date
        validity_months = int(program_doc.validity_period_months or 24)
        dates = compute_competency_dates(achieved_date, validity_months)  # SoT §V.1 — INVARIANT expiry−60d
        expiry_date = dates["expiry_date"]
        recert_due = dates["recertification_due_date"]

        doc = frappe.get_doc({
            "doctype": "IMM User Competency",
            "user": participant.user,
            "device_model": program_doc.target_device_model or "",
            "training_program": program_doc.name,
            "training_session": session_doc.name,
            "competency_level": "Operator",
            "achieved_date": achieved_date,
            "validity_months": validity_months,
            "expiry_date": expiry_date,
            "recertification_due_date": recert_due,
            "theory_score": participant.theory_score,
            "practical_score": participant.practical_score,
            "last_assessment_score": (participant.theory_score + participant.practical_score) / 2.0,
            "workflow_state": CompetencyStatus.PENDING,
        })
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-06: create_competency_record failed")
        return None


# ─── User Competency ─────────────────────────────────────────────────────────

def list_user_competencies(filters: dict, *, page: int = 1,
                            page_size: int = 20) -> dict:
    """Liệt kê hồ sơ năng lực."""
    rows, pg = UserCompetencyRepo.list(
        filters=normalize_filters(filters),
        # Vòng-22 recert SoT: recertification_due_date + is_expired +
        # department_at_assessment PHẢI nằm trong read-path để detail view
        # (training/CompetencyDetailView.vue) render "Hạn tái chứng nhận" thật,
        # và để superset-parity với get_expiring_competencies (không drift 2 đường đọc).
        fields=["name", "user", "device_model", "training_program",
                "competency_level", "achieved_date", "expiry_date",
                "workflow_state", "days_until_expiry",
                "recertification_due_date", "is_expired",
                "department_at_assessment"],
        order_by="expiry_date asc",
        page=page, page_size=page_size,
    )
    # Enrich device_model với model_name để FE hiển thị tên thay vì ID
    model_ids = list({r["device_model"] for r in rows if r.get("device_model")})
    if model_ids:
        model_names = dict(frappe.get_all(
            "IMM Device Model",
            filters={"name": ("in", model_ids)},
            fields=["name", "model_name"], as_list=True,
        ))
        for r in rows:
            mid = r.get("device_model")
            if mid:
                r["device_model_name"] = model_names.get(mid) or mid
    return {"data": rows, "pagination": pg}


def revoke_competency(competency_name: str, reason: str) -> dict:
    """Thu hồi năng lực (terminal state)."""
    _require_training_officer()
    doc = UserCompetencyRepo.get(competency_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy hồ sơ năng lực: {competency_name}")
    if doc.workflow_state == CompetencyStatus.REVOKED:
        raise ServiceError(ErrorCode.BAD_STATE, "Hồ sơ năng lực đã bị thu hồi")
    if not reason:
        raise ServiceError(ErrorCode.VALIDATION, "Bắt buộc phải có lý do thu hồi")

    doc.workflow_state = CompetencyStatus.REVOKED
    doc.revoke_reason = reason
    doc.revoked_by = frappe.session.user
    doc.revoked_date = now_datetime()
    doc.flags.ignore_workflow_status_check = True
    UserCompetencyRepo.save(doc)

    _invalidate_auth_cache(doc.user, doc.device_model)
    _log_competency_audit(competency_name, doc.user, "REVOKED", reason)
    frappe.db.commit()
    return {"name": competency_name, "workflow_state": CompetencyStatus.REVOKED}


def signoff_competency(competency_name: str, supervisor_user: str) -> dict:
    """Supervisor ký duyệt competency: Pending Assessment → Active."""
    doc = UserCompetencyRepo.get(competency_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy hồ sơ năng lực: {competency_name}")
    if doc.workflow_state != CompetencyStatus.PENDING:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Chỉ có thể ký duyệt ở trạng thái Pending Assessment, hiện tại: {doc.workflow_state}")

    doc.supervisor_signoff = supervisor_user
    doc.signoff_date = nowdate()
    doc.workflow_state = CompetencyStatus.ACTIVE

    # Recompute dates if missing — qua SoT §V.1 (INVARIANT expiry−60d)
    if doc.achieved_date and not doc.expiry_date:
        validity = int(doc.validity_months or 24)
        dates = compute_competency_dates(doc.achieved_date, validity)
        doc.expiry_date = dates["expiry_date"]
        doc.recertification_due_date = dates["recertification_due_date"]

    doc.flags.ignore_workflow_status_check = True
    UserCompetencyRepo.save(doc)
    archive_old_competency(doc.user, doc.device_model, exclude=competency_name)
    _invalidate_auth_cache(doc.user, doc.device_model)
    _log_competency_audit(competency_name, doc.user, "SIGNOFF", "")
    frappe.db.commit()
    return {
        "name": competency_name,
        "workflow_state": CompetencyStatus.ACTIVE,
        "expiry_date": str(doc.expiry_date) if doc.expiry_date else None,
    }


def archive_old_competency(user: str, device_model: str, exclude: str) -> int:
    """BR-06-11: Archive competency cũ cùng (user × device_model)."""
    rows = UserCompetencyRepo.find_all_active_for_user_model(user, device_model, exclude)
    count = 0
    for r in rows:
        UserCompetencyRepo.set_values(r["name"], {"workflow_state": CompetencyStatus.SUSPENDED})
        count += 1
    return count


def validate_user_authorized_for_asset(user: str, asset_name: str) -> dict:
    """Hook từ IMM-08/09/11 — kiểm tra user có năng lực cho asset."""
    cache_key = f"imm06:auth:{user}:{asset_name}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached

    device_model = frappe.db.get_value("AC Asset", asset_name, "device_model") or ""
    if not device_model:
        result = {"authorized": True, "reason": "No device model configured"}
        frappe.cache().set_value(cache_key, result, expires_in_sec=300)
        return result

    comp = UserCompetencyRepo.find_active_for_user_model(user, device_model)
    if comp:
        result = {
            "authorized": True,
            "competency": comp["name"],
            "competency_level": comp.get("competency_level"),
            "status": comp["workflow_state"],
            "expiry_date": str(comp.get("expiry_date") or ""),
        }
    else:
        result = {
            "authorized": False,
            "reason": f"Không có năng lực hợp lệ cho Device Model {device_model}",
        }
    frappe.cache().set_value(cache_key, result, expires_in_sec=300)
    return result


def get_asset_operator_coverage(asset: str) -> dict:
    """Docs §C.3 — Trả coverage operator cho 1 asset.

    Dùng bởi IMM-04 Clinical Release validate gate.

    Args:
        asset: tên AC Asset

    Returns:
        {asset, device_model, department, asset_class, operator_count,
         operator_users, required_min, gate_pass}
    """
    if not frappe.db.exists("AC Asset", asset):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Asset {asset} không tồn tại")

    a = frappe.db.get_value(
        "AC Asset", asset,
        ["device_model", "department", "risk_classification"],
        as_dict=True,
    ) or {}

    device_model = a.get("device_model") or ""
    department   = a.get("department") or ""
    asset_class  = a.get("risk_classification") or ""

    required_min = 2 if asset_class == "Class III" else 1

    operator_users: list[str] = []
    if device_model:
        rows = frappe.get_all(
            "IMM User Competency",
            filters={
                "device_model": device_model,
                "workflow_state": ["in", list(CompetencyStatus.AUTHORIZED)],
            },
            fields=["user"],
            ignore_permissions=True,
        )
        operator_users = sorted({r.user for r in rows if r.user})

    return {
        "asset":          asset,
        "device_model":   device_model,
        "department":     department,
        "asset_class":    asset_class,
        "operator_count": len(operator_users),
        "operator_users": operator_users,
        "required_min":   required_min,
        "gate_pass":      len(operator_users) >= required_min,
    }


def generate_gap_report(filters: dict) -> dict:
    """Tính ma trận coverage gap theo department × device_class."""
    scope = filters.get("scope", "Hospital-wide")
    assets = frappe.get_all(
        "AC Asset",
        filters={"lifecycle_status": ["in", ["Active", "Under Maintenance",
                                              "Under Repair", "Calibrating"]]},
        fields=["name", "device_model", "department", "risk_classification"],
    )

    # Aggregate active competencies
    comps = frappe.get_all(
        "IMM User Competency",
        filters={"workflow_state": ["in", list(CompetencyStatus.AUTHORIZED)]},
        fields=["user", "device_model", "department_at_assessment"],
    )
    comp_map: dict[str, set] = {}
    for c in comps:
        comp_map.setdefault(c.device_model or "", set()).add(c.user)

    total_assets = len(assets)
    gap_details: list[dict] = []
    assets_with_gap = 0

    for a in assets:
        dm = a.device_model or ""
        required_min = 2 if a.risk_classification == "Class III" else 1
        covered_users = comp_map.get(dm, set())
        gap_count = max(0, required_min - len(covered_users))
        if gap_count > 0:
            assets_with_gap += 1
        gap_details.append({
            "asset": a.name,
            "device_model": dm,
            "department": a.department or "",
            "required_min": required_min,
            "covered_users": len(covered_users),
            "gap_count": gap_count,
        })

    import json
    doc = GapReportRepo.create({
        "report_date": nowdate(),
        "scope": scope,
        "total_assets_class3": sum(1 for a in assets if a.risk_classification == "Class III"),
        "assets_with_gap_count": assets_with_gap,
        "gap_details": json.dumps(gap_details),
    })
    frappe.db.commit()
    return {"report": doc.name, "total_assets": total_assets,
            "assets_with_gap": assets_with_gap}


# ─── Scheduler Jobs ───────────────────────────────────────────────────────────

def check_expiring_competencies() -> None:
    """Daily: kiểm tra competency sắp hết hạn (90/60/30 ngày)."""
    today = nowdate()
    for milestone in (90, 60, 30):
        target_date = add_days(today, milestone)
        comps = frappe.get_all(
            "IMM User Competency",
            filters={"workflow_state": ["in", [CompetencyStatus.ACTIVE]],
                     "expiry_date": target_date},
            fields=["name", "user", "device_model", "expiry_date"],
        )
        for c in comps:
            if CompetencyAlertLogRepo.alert_exists(c.name, today, milestone):
                continue
            CompetencyAlertLogRepo.create({
                "competency": c.name,
                "alert_date": today,
                "milestone": str(milestone),
                "alert_level": {90: "Info", 60: "Warning", 30: "Critical"}[milestone],
            })
            if milestone <= 60:
                UserCompetencyRepo.set_values(c.name,
                                               {"workflow_state": CompetencyStatus.EXPIRING})
                _invalidate_auth_cache(c.user, c.device_model)
            _send_expiry_alert(c, milestone)


def auto_expire_competencies() -> None:
    """Daily: tự động expire competency quá hạn."""
    today = nowdate()
    expired = frappe.get_all(
        "IMM User Competency",
        filters={"workflow_state": ["in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]],
                 "expiry_date": ("<", today)},
        fields=["name", "user", "device_model"],
    )
    for c in expired:
        UserCompetencyRepo.set_values(c.name, {"workflow_state": CompetencyStatus.EXPIRED,
                                                "is_expired": 1})
        _invalidate_auth_cache(c.user, c.device_model)
        _log_competency_audit(c.name, c.user, "AUTO_EXPIRED", "")


# ─── Controller-callable validators ──────────────────────────────────────────

def validate_target_device_set(doc: "frappe.Document") -> None:
    """BR-06-01: Phải chỉ định ít nhất target_device_model hoặc target_device_category."""
    if not doc.target_device_model and not doc.target_device_category:
        frappe.throw(
            _("Chương trình đào tạo phải gắn với mẫu thiết bị (target_device_model) "
              "hoặc danh mục thiết bị (target_device_category).")
        )


def validate_passing_score_range(doc: "frappe.Document") -> None:
    """BR-06-02: Điểm đạt phải trong khoảng 1–100."""
    if doc.passing_score_pct is not None and not (1 <= doc.passing_score_pct <= 100):
        frappe.throw(_("Điểm đạt (passing_score_pct) phải từ 1 đến 100."))


def validate_score_bounds_config(doc: "frappe.Document") -> None:
    """Slide 21: cấu hình điểm của chương trình phải hợp lệ — max_score > min_score."""
    mn = float(getattr(doc, "min_score", 0) or 0)
    mx = float(getattr(doc, "max_score", 100) or 100)
    if mx <= mn:
        frappe.throw(_("Điểm tối đa (max_score) phải lớn hơn điểm tối thiểu (min_score)."))


def get_program_score_bounds(program_doc) -> tuple[float, float]:
    """Trả (min_score, max_score) của chương trình, mặc định [0, 100]."""
    mn = float(getattr(program_doc, "min_score", 0) or 0)
    mx = float(getattr(program_doc, "max_score", 0) or 0) or 100.0
    if mx <= mn:
        frappe.throw(_("Cấu hình điểm chương trình không hợp lệ: max_score phải > min_score."))
    return mn, mx


def validate_participant_scores(doc: "frappe.Document") -> None:
    """Slide 21: theory_score/practical_score mỗi học viên phải nằm trong
    [min_score, max_score] do chương trình định nghĩa."""
    if not doc.training_program:
        return
    try:
        program_doc = frappe.get_doc("IMM Training Program", doc.training_program)
    except Exception:
        return
    mn, mx = get_program_score_bounds(program_doc)
    for p in (doc.participants or []):
        for fld, lbl in (("theory_score", "Điểm lý thuyết"),
                         ("practical_score", "Điểm thực hành")):
            val = getattr(p, fld, None)
            if val in (None, ""):
                continue
            v = float(val)
            if v < mn or v > mx:
                frappe.throw(
                    _("{0} của học viên {1} ({2}) ngoài khoảng cho phép [{3}, {4}].").format(
                        lbl, p.user or "?", v, mn, mx))


def validate_validity_range(doc: "frappe.Document") -> None:
    """BR-06-03: Thời hạn hiệu lực phải > 0."""
    if doc.validity_period_months is not None and doc.validity_period_months <= 0:
        frappe.throw(_("Thời hạn hiệu lực (validity_period_months) phải lớn hơn 0."))


def flag_recertification_if_critical_change(doc: "frappe.Document") -> None:
    """Khi chương trình thay đổi điểm đạt hoặc thời hạn, đánh dấu để tái chứng nhận.

    Placeholder — mở rộng khi có scheduler tái chứng nhận batch.
    """
    pass


def validate_instructor_present(doc: "frappe.Document") -> None:
    """Cảnh báo khi thiếu giảng viên (không block validate)."""
    if not getattr(doc, "instructor", None) and not getattr(doc, "instructor_external_name", None):
        frappe.msgprint(
            _("Khuyến nghị: Vui lòng chỉ định giảng viên nội bộ hoặc bên ngoài."),
            alert=True,
        )


def validate_min_participants_for_confirm(doc: "frappe.Document") -> None:
    """BR-06-04 (controller-level): Kiểm tra này được enforce trong confirm_session().

    Chỉ cảnh báo ở validate — không throw để cho phép save draft.
    """
    if (
        getattr(doc, "workflow_state", None) == "Confirmed"
        and not (doc.participants or [])
    ):
        frappe.throw(_("Phải có ít nhất 1 học viên trước khi xác nhận buổi học (BR-06-04)."))


def validate_session_date_not_past(doc: "frappe.Document") -> None:
    """Cảnh báo khi ngày tổ chức đã qua (không block)."""
    from frappe.utils import getdate, nowdate as _nowdate
    if doc.session_date and getdate(doc.session_date) < getdate(_nowdate()):
        if getattr(doc, "workflow_state", None) in (None, "", SessionStatus.PLANNED):
            frappe.msgprint(_("Lưu ý: Ngày tổ chức buổi học đã qua."), alert=True)


def compute_overall_results(doc: "frappe.Document") -> None:
    """Tính overall_result cho tất cả học viên khi session Completed.

    Được gọi từ IMMTrainingSession.before_save().
    """
    if not doc.training_program:
        return
    try:
        program_doc = frappe.get_doc("IMM Training Program", doc.training_program)
    except Exception:
        return
    validate_participant_scores(doc)
    pass_score = float(program_doc.passing_score_pct or 70.0)
    assessment_method = program_doc.assessment_method or "Both"

    for p in (doc.participants or []):
        t = float(p.theory_score or 0.0)
        pr = float(p.practical_score or 0.0)
        att = float(p.attendance_pct or 0.0)

        if att < 80.0:
            p.overall_result = "Fail"
        else:
            if assessment_method == "Theory":
                avg = t
            elif assessment_method == "Practical":
                avg = pr
            else:
                avg = (t + pr) / 2.0
            p.overall_result = "Pass" if avg >= pass_score else "Fail"

        p.retake_required = 1 if p.overall_result == "Fail" else 0
        p.result = "Đạt" if p.overall_result == "Pass" else "Không đạt"


def create_competency_from_session(session_name: str) -> list:
    """Tạo IMM User Competency cho mỗi học viên Pass trong một buổi học.

    Helper được gọi từ IMMTrainingSession.on_update() khi workflow_state → Completed.
    Idempotent: bỏ qua học viên đã có hồ sơ từ cùng session.

    Args:
        session_name: tên IMM Training Session.

    Returns:
        list tên các IMM User Competency đã tạo.
    """
    doc = frappe.get_doc("IMM Training Session", session_name)
    program_doc = frappe.get_doc("IMM Training Program", doc.training_program)
    created: list[str] = []

    for p in (doc.participants or []):
        if p.overall_result != "Pass":
            continue
        # Idempotency
        if frappe.db.exists("IMM User Competency",
                             {"user": p.user, "training_session": session_name}):
            continue

        comp_name = _create_competency_record(p, doc, program_doc)
        if comp_name:
            p.competency_record = comp_name
            created.append(comp_name)

    if created:
        doc.flags.ignore_permissions = True
        doc.save()

    return created


def validate_expiry_after_achieved(doc: "frappe.Document") -> None:
    """BR-06-10: expiry_date phải sau achieved_date nếu cả hai được set."""
    from frappe.utils import getdate
    if doc.expiry_date and doc.achieved_date:
        if getdate(doc.expiry_date) <= getdate(doc.achieved_date):
            frappe.throw(_("Ngày hết hạn (expiry_date) phải sau ngày đạt (achieved_date)."))


def validate_signoff_required_for_active(doc: "frappe.Document") -> None:
    """BR-06-08: Khi workflow_state=Active phải có supervisor_signoff."""
    if getattr(doc, "workflow_state", None) == "Active" and not doc.supervisor_signoff:
        frappe.throw(_("Phải có người phê duyệt (supervisor_signoff) khi hồ sơ ở trạng thái Active."))


def set_computed_competency_fields(doc: "frappe.Document") -> None:
    """SoT owner cho compute hook: tính expiry_date + recertification_due_date (qua §V.1),
    cùng days_until_expiry và is_expired. Idempotent — chỉ set expiry/recert khi còn thiếu.

    `compute_expiry_dates` delegate vào hàm này (1 owner duy nhất — không 2 hàm ghi
    recert date song song)."""
    if doc.achieved_date and doc.validity_months and not doc.expiry_date:
        dates = compute_competency_dates(doc.achieved_date, int(doc.validity_months))  # SoT §V.1
        doc.expiry_date = dates["expiry_date"]
        doc.recertification_due_date = dates["recertification_due_date"]

    if doc.expiry_date:
        today_dt = getdate(nowdate())
        diff = date_diff(getdate(doc.expiry_date), today_dt)
        doc.days_until_expiry = diff
        doc.is_expired = 1 if diff < 0 else 0


def compute_expiry_dates(doc: "frappe.Document") -> None:
    """Tính expiry_date + recertification_due_date từ achieved_date + validity_months.

    Delegate 100% vào `set_computed_competency_fields` (SoT §V.1) — KHÔNG còn logic
    formula trùng lặp. Giữ public để tương thích call-site cũ (gọi từ before_save nếu wire)."""
    set_computed_competency_fields(doc)


def invalidate_authorization_cache(user: str, device_model: str) -> None:
    """Xoá cache kiểm tra năng lực cho (user × device_model)."""
    _invalidate_auth_cache(user, device_model)


# ─── Service wrappers matching API signatures ─────────────────────────────────

def list_programs(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    """Alias list_training_programs cho API imm06.py — enrich display names (BE-DC-06-01)."""
    res = list_training_programs(filters, page=page, page_size=page_size)
    _enrich_program_display_names(res.get("data", []))
    return res


def _enrich_program_display_names(items: list[dict]) -> None:
    if not items:
        return
    model_ids = {it.get("target_device_model") for it in items if it.get("target_device_model")}
    model_map: dict = {}
    if model_ids:
        try:
            rows = frappe.get_all(
                "IMM Device Model",
                filters={"name": ["in", list(model_ids)]},
                fields=["name", "model_name"],
                ignore_permissions=True,
            )
            model_map = {r["name"]: r.get("model_name") for r in rows}
        except Exception:
            pass
    for it in items:
        it["target_device_model_name"] = model_map.get(it.get("target_device_model"))


def get_program(name: str) -> dict:
    """Alias get_training_program cho API imm06.py."""
    return get_training_program(name)


def create_program(program_data: dict) -> dict:
    """Alias create_training_program cho API imm06.py."""
    return create_training_program(program_data)


def update_program(name: str, program_data: dict) -> dict:
    """Cập nhật Training Program theo name.

    Args:
        name: tên chương trình cần cập nhật.
        program_data: dict chứa các field cần thay đổi.

    Returns:
        dict với name và program_code sau khi cập nhật.
    """
    _require_training_officer()
    doc = TrainingProgramRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy chương trình: {name}")
    doc.update(program_data)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"name": doc.name, "program_code": doc.program_code}


def list_sessions(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    """Alias list_training_sessions cho API imm06.py — enrich display (BE-DC-06-01).

    Bổ sung `trainer_name`, `program_name`, `attendee_count` cho mỗi row.
    """
    res = list_training_sessions(filters, page=page, page_size=page_size)
    _enrich_session_display_names(res.get("data", []))
    return res


def _enrich_session_display_names(items: list[dict]) -> None:
    if not items:
        return
    prog_ids = {it.get("training_program") for it in items if it.get("training_program")}
    user_ids = {it.get("instructor")       for it in items if it.get("instructor")}
    names    = [it["name"] for it in items if it.get("name")]

    prog_map: dict = {}
    user_map: dict = {}
    attendee_map: dict = {}

    try:
        if prog_ids:
            rows = frappe.get_all(
                "IMM Training Program",
                filters={"name": ["in", list(prog_ids)]},
                fields=["name", "program_name"], ignore_permissions=True,
            )
            prog_map = {r["name"]: r.get("program_name") for r in rows}
    except Exception:
        pass
    try:
        if user_ids:
            rows = frappe.get_all(
                "User",
                filters={"name": ["in", list(user_ids)]},
                fields=["name", "full_name"], ignore_permissions=True,
            )
            user_map = {r["name"]: r.get("full_name") for r in rows}
    except Exception:
        pass
    # Attendee count = số participant rows / session
    try:
        if names:
            rows = frappe.db.sql(
                """SELECT parent, COUNT(*) FROM `tabIMM Training Participant`
                   WHERE parent IN ({placeholders}) GROUP BY parent""".format(
                    placeholders=", ".join(["%s"] * len(names)),
                ),
                tuple(names),
            )
            attendee_map = dict(rows)
    except Exception:
        pass

    for it in items:
        it["program_name"]    = prog_map.get(it.get("training_program"))
        it["trainer_name"]    = user_map.get(it.get("instructor"))
        it["attendee_count"]  = attendee_map.get(it.get("name"), 0)


def get_session(name: str) -> dict:
    """Lấy chi tiết Training Session kèm thông tin bổ sung.

    Args:
        name: tên buổi học.

    Returns:
        dict đầy đủ thông tin buổi học.
    """
    doc = TrainingSessionRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy buổi học: {name}")
    data = doc.as_dict()
    _transitions: dict[str, list[str]] = {
        SessionStatus.PLANNED: [SessionStatus.CONFIRMED, SessionStatus.CANCELLED],
        SessionStatus.CONFIRMED: [SessionStatus.IN_PROGRESS, SessionStatus.CANCELLED],
        SessionStatus.IN_PROGRESS: [SessionStatus.COMPLETED, SessionStatus.CANCELLED],
        SessionStatus.COMPLETED: [SessionStatus.VERIFIED],
        SessionStatus.VERIFIED: [SessionStatus.CLOSED],
    }
    data["allowed_transitions"] = _transitions.get(data.get("workflow_state", ""), [])

    # Convert to plain dict to avoid Frappe serialization filtering
    result = dict(data)

    # Enrich display names
    if result.get("training_program"):
        result["training_program_name"] = (
            frappe.db.get_value("IMM Training Program", result["training_program"], "program_name")
            or result["training_program"]
        )
    if result.get("instructor"):
        result["instructor_full_name"] = (
            frappe.db.get_value("User", result["instructor"], "full_name")
            or result["instructor"]
        )
    # BUG-006: Enrich IMM Trainer name (trainer_ref → trainer_ref_name)
    if result.get("trainer_ref"):
        result["trainer_ref_name"] = (
            frappe.db.get_value("IMM Trainer", result["trainer_ref"], "trainer_name")
            or result["trainer_ref"]
        )

    enriched_participants = []
    for p in result.get("participants") or []:
        ep = dict(p)
        if ep.get("user"):
            ep["user_full_name"] = (
                frappe.db.get_value("User", ep["user"], "full_name") or ep["user"]
            )
        if ep.get("department"):
            ep["department_name"] = (
                frappe.db.get_value("AC Department", ep["department"], "department_name")
                or ep["department"]
            )
        enriched_participants.append(ep)
    result["participants"] = enriched_participants

    return result


def create_session(session_data: dict) -> dict:
    """Alias create_training_session cho API imm06.py."""
    return create_training_session(session_data)


def confirm_session(name: str) -> dict:
    """Chuyển Session từ Planned → Confirmed.

    BR-06-04: Yêu cầu ≥1 học viên.

    Args:
        name: tên buổi học.

    Returns:
        dict với name và workflow_state mới.
    """
    _require_training_officer()
    doc = _get_session_or_raise(name)
    if doc.workflow_state != SessionStatus.PLANNED:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ có thể xác nhận buổi học ở trạng thái Planned. Hiện tại: {doc.workflow_state}",
        )
    if not doc.participants:
        raise ServiceError(
            ErrorCode.VALIDATION,
            "Phải có ít nhất 1 học viên trước khi xác nhận buổi học (BR-06-04).",
        )
    doc.workflow_state = SessionStatus.CONFIRMED
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(name, "", "SESSION_CONFIRMED", "Planned → Confirmed")
    return {"name": name, "workflow_state": SessionStatus.CONFIRMED}


_ENROLL_BLOCKED_STATES = (
    SessionStatus.COMPLETED,
    SessionStatus.VERIFIED,
    SessionStatus.CLOSED,
    SessionStatus.CANCELLED,
)


def enroll_participants(session: str, participants: list[dict]) -> dict:
    """Thêm học viên vào child table `participants` của Training Session.

    Slide 19: FE cần khả năng enroll/tạo trainee trước/đang buổi học, thay vì
    participants chỉ read-only và chỉ nhập kết quả khi complete_session.

    Mỗi phần tử `participants`:
        - user: Link User của học viên (bắt buộc nếu không có external_name).
        - external_name: tên học viên ngoài hệ thống (không có tài khoản User).
          Lưu vào `remarks`, đánh dấu role_at_session="External".
        - department: Link AC Department (tùy chọn).
        - role_at_session: vai trò trong buổi học (tùy chọn).

    BR: Không thể enroll khi session đã Completed/Verified/Closed/Cancelled.
    Permission: chỉ Training Officer / Ops Manager / System Admin.

    Args:
        session: tên buổi học.
        participants: danh sách dict học viên cần thêm.

    Returns:
        dict gồm name, workflow_state, added (số dòng thêm),
        participant_count (tổng sau khi thêm).
    """
    _require_training_officer()
    if not participants:
        raise ServiceError(ErrorCode.VALIDATION, "Danh sách học viên trống")
    doc = _get_session_or_raise(session)
    if doc.workflow_state in _ENROLL_BLOCKED_STATES:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Không thể thêm học viên khi buổi học ở trạng thái {doc.workflow_state}",
        )

    existing_users = {
        (p.user or "").strip() for p in (doc.participants or []) if p.user
    }
    added = 0
    has_external = False
    for raw in participants:
        if not isinstance(raw, dict):
            raise ServiceError(ErrorCode.INVALID_PARAMS,
                               "Mỗi học viên phải là object")
        user = (raw.get("user") or "").strip()
        external_name = (raw.get("external_name") or "").strip()
        if not user and not external_name:
            raise ServiceError(
                ErrorCode.VALIDATION,
                "Mỗi học viên cần `user` hoặc `external_name`",
            )
        if user:
            if user in existing_users:
                continue
            if not frappe.db.exists("User", user):
                raise ServiceError(ErrorCode.NOT_FOUND,
                                   f"Không tìm thấy User: {user}")
            existing_users.add(user)
        row = {
            "user": user or None,
            "department": (raw.get("department") or None),
            "role_at_session": (raw.get("role_at_session")
                                or ("External" if external_name else None)),
        }
        if external_name:
            row["remarks"] = f"External: {external_name}"
            has_external = True
        doc.append("participants", row)
        added += 1

    if added == 0:
        return {
            "name": session,
            "workflow_state": doc.workflow_state,
            "added": 0,
            "participant_count": len(doc.participants or []),
        }

    doc.flags.ignore_links = True
    if has_external:
        # IMM Training Participant.user is reqd:1 nhưng học viên ngoài hệ thống
        # không có tài khoản User — tên lưu ở remarks, role_at_session=External.
        doc.flags.ignore_mandatory = True
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(
        session, frappe.session.user, "PARTICIPANTS_ENROLLED",
        f"Thêm {added} học viên",
    )
    return {
        "name": session,
        "workflow_state": doc.workflow_state,
        "added": added,
        "participant_count": len(doc.participants or []),
    }


def remove_participant(session: str, row_name: str) -> dict:
    """Xóa 1 dòng học viên khỏi child table `participants`.

    BR: Không thể xóa khi session đã Completed/Verified/Closed/Cancelled.
    Permission: chỉ Training Officer / Ops Manager / System Admin.

    Args:
        session: tên buổi học.
        row_name: name của dòng IMM Training Participant cần xóa.

    Returns:
        dict gồm name, workflow_state, removed (bool),
        participant_count (tổng sau khi xóa).
    """
    _require_training_officer()
    doc = _get_session_or_raise(session)
    if doc.workflow_state in _ENROLL_BLOCKED_STATES:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Không thể xóa học viên khi buổi học ở trạng thái {doc.workflow_state}",
        )
    target = next(
        (p for p in (doc.participants or []) if p.name == row_name), None
    )
    if target is None:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy học viên: {row_name}")
    removed_user = target.user or target.remarks or row_name
    doc.participants.remove(target)
    doc.flags.ignore_links = True
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(
        session, frappe.session.user, "PARTICIPANT_REMOVED",
        f"Xóa học viên {removed_user}",
    )
    return {
        "name": session,
        "workflow_state": doc.workflow_state,
        "removed": True,
        "participant_count": len(doc.participants or []),
    }


def complete_session(name: str, participants_results: list) -> dict:
    """Alias complete_training_session cho API imm06.py."""
    return complete_training_session(name, participants_results)


def cancel_session(name: str, cancel_reason: str) -> dict:
    """Hủy Training Session (BR-06-05).

    Args:
        name: tên buổi học.
        cancel_reason: lý do hủy (bắt buộc).

    Returns:
        dict với name và workflow_state mới.
    """
    _require_training_officer()
    doc = _get_session_or_raise(name)
    if doc.workflow_state in (SessionStatus.COMPLETED, SessionStatus.CLOSED,
                               SessionStatus.CANCELLED):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Không thể hủy buổi học đã {doc.workflow_state}.",
        )
    if not cancel_reason or not cancel_reason.strip():
        raise ServiceError(ErrorCode.VALIDATION, "Bắt buộc nhập lý do hủy buổi học.")

    doc.workflow_state = SessionStatus.CANCELLED
    if hasattr(doc, "cancel_reason"):
        doc.cancel_reason = cancel_reason
    else:
        doc.status_remarks = cancel_reason
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(name, "", "SESSION_CANCELLED", cancel_reason[:120])
    return {"name": name, "workflow_state": SessionStatus.CANCELLED}


def verify_session(name: str) -> dict:
    """Chuyển Session từ Completed → Verified (BR-06-06).

    Returns:
        dict với name và workflow_state mới.
    """
    _require_training_officer()
    doc = _get_session_or_raise(name)
    if doc.workflow_state != SessionStatus.COMPLETED:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ có thể xác minh buổi học ở trạng thái Completed. Hiện tại: {doc.workflow_state}",
        )
    doc.workflow_state = SessionStatus.VERIFIED
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(name, "", "SESSION_VERIFIED", "Completed → Verified")
    return {"name": name, "workflow_state": SessionStatus.VERIFIED}


def close_session(name: str) -> dict:
    """Chuyển Session từ Verified → Closed (BR-06-07).

    Returns:
        dict với name và workflow_state mới.
    """
    _require_training_officer()
    doc = _get_session_or_raise(name)
    if doc.workflow_state != SessionStatus.VERIFIED:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ có thể đóng buổi học ở trạng thái Verified. Hiện tại: {doc.workflow_state}",
        )
    doc.workflow_state = SessionStatus.CLOSED
    TrainingSessionRepo.save(doc)
    frappe.db.commit()
    _log_competency_audit(name, "", "SESSION_CLOSED", "Verified → Closed")
    return {"name": name, "workflow_state": SessionStatus.CLOSED}


def list_competencies(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    """Alias list_user_competencies cho API imm06.py — enrich display (BE-DC-06-01).

    Bổ sung `user_full_name`, `device_model_name`.
    """
    res = list_user_competencies(filters, page=page, page_size=page_size)
    _enrich_competency_display_names(res.get("data", []))
    return res


def _enrich_competency_display_names(items: list[dict]) -> None:
    if not items:
        return
    user_ids  = {it.get("user")         for it in items if it.get("user")}
    model_ids = {it.get("device_model") for it in items if it.get("device_model")}

    def _map(doctype: str, ids: set, field: str) -> dict:
        if not ids:
            return {}
        try:
            rows = frappe.get_all(
                doctype, filters={"name": ["in", list(ids)]},
                fields=["name", field], ignore_permissions=True,
            )
            return {r["name"]: r.get(field) for r in rows}
        except Exception:
            return {}

    user_map  = _map("User",             user_ids,  "full_name")
    model_map = _map("IMM Device Model", model_ids, "model_name")

    for it in items:
        it["user_full_name"]    = user_map.get(it.get("user"))
        it["device_model_name"] = model_map.get(it.get("device_model"))


def get_user_competencies(user: str = "") -> dict:
    """Lấy tất cả hồ sơ năng lực của một nhân viên.

    Args:
        user: email/tên user. Mặc định là session user.

    Returns:
        dict với "user" và "items".
    """
    target_user = user or frappe.session.user
    rows, _ = UserCompetencyRepo.list(
        filters={"user": target_user},
        fields=["name", "device_model", "training_program", "competency_level",
                "workflow_state", "achieved_date", "expiry_date",
                "days_until_expiry", "is_expired", "last_assessment_score"],
        order_by="expiry_date asc",
        page_size=500,
    )
    return {"user": target_user, "items": rows}


def signoff_competency_by_name(name: str) -> dict:
    """Phê duyệt hồ sơ năng lực dùng session user làm supervisor.

    Args:
        name: tên hồ sơ năng lực.

    Returns:
        dict với name và workflow_state mới.
    """
    return signoff_competency(name, frappe.session.user)


def revoke_competency_with_capa(name: str, reason: str, capa_ref: str = "") -> dict:
    """Thu hồi hồ sơ năng lực, tuỳ chọn gắn CAPA reference.

    Args:
        name: tên hồ sơ năng lực.
        reason: lý do thu hồi (bắt buộc).
        capa_ref: tên IMM CAPA Record liên quan (tuỳ chọn).

    Returns:
        dict với name và workflow_state mới.
    """
    result = revoke_competency(name, reason)
    if capa_ref and result.get("name"):
        try:
            UserCompetencyRepo.set_values(name, {"revoke_capa_ref": capa_ref})
            frappe.db.commit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-06 revoke_competency_with_capa capa_ref")
    return result


def recertify_competency(name: str, new_session: str) -> dict:
    """Tái chứng nhận hồ sơ năng lực bằng buổi học mới.

    Args:
        name: tên hồ sơ năng lực cũ.
        new_session: tên Training Session đã Completed.

    Returns:
        dict với old_competency và new_competency.
    """
    _require_training_officer()
    old = UserCompetencyRepo.get(name)
    if not old:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy hồ sơ năng lực: {name}")

    session = TrainingSessionRepo.get(new_session)
    if not session:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy buổi học: {new_session}")
    if session.workflow_state != SessionStatus.COMPLETED:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Buổi học tái chứng nhận phải ở trạng thái Completed. Hiện tại: {session.workflow_state}",
        )

    participant = next(
        (p for p in (session.participants or []) if p.user == old.user), None,
    )
    if not participant:
        raise ServiceError(
            ErrorCode.NOT_FOUND,
            f"Nhân viên {old.user} không có trong danh sách học viên buổi học {new_session}.",
        )
    if participant.overall_result != "Pass":
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"Nhân viên chưa đạt trong buổi tái chứng nhận. Kết quả: {participant.overall_result or 'N/A'}",
        )

    program_doc = frappe.get_doc("IMM Training Program", session.training_program)
    achieved_today = nowdate()
    validity_months = int(program_doc.validity_period_months or 24)
    dates = compute_competency_dates(achieved_today, validity_months)  # SoT §V.1 — INVARIANT expiry−60d
    expiry_date = dates["expiry_date"]
    recert_due = dates["recertification_due_date"]

    new_comp_doc = frappe.new_doc("IMM User Competency")
    new_comp_doc.user = old.user
    new_comp_doc.device_model = old.device_model
    new_comp_doc.training_program = session.training_program
    new_comp_doc.training_session = new_session
    new_comp_doc.competency_level = old.competency_level
    new_comp_doc.achieved_date = achieved_today
    new_comp_doc.validity_months = validity_months
    new_comp_doc.expiry_date = expiry_date
    new_comp_doc.recertification_due_date = recert_due
    new_comp_doc.theory_score = participant.theory_score
    new_comp_doc.practical_score = participant.practical_score
    avg = ((participant.theory_score or 0) + (participant.practical_score or 0)) / 2.0
    new_comp_doc.last_assessment_score = avg
    new_comp_doc.workflow_state = CompetencyStatus.PENDING
    new_comp_doc.flags.ignore_permissions = True
    new_comp_doc.insert()

    # Mark old as Expired
    UserCompetencyRepo.set_values(name, {"workflow_state": CompetencyStatus.EXPIRED, "is_expired": 1})
    frappe.db.commit()
    _log_competency_audit(new_comp_doc.name, old.user, "RECERTIFIED", f"from {name}")
    return {"old_competency": name, "new_competency": new_comp_doc.name}


def get_dashboard_stats() -> dict:
    """KPI tổng quan IMM-06: số buổi học và hồ sơ năng lực theo trạng thái.

    Returns:
        dict tổng hợp KPI.
    """
    def _count(doctype: str, f: dict) -> int:
        try:
            return frappe.db.count(doctype, filters=f)
        except Exception:
            return 0

    return {
        "sessions": {
            "total": _count("IMM Training Session", {}),
            "planned": _count("IMM Training Session", {"workflow_state": SessionStatus.PLANNED}),
            "confirmed": _count("IMM Training Session", {"workflow_state": SessionStatus.CONFIRMED}),
            "in_progress": _count("IMM Training Session", {"workflow_state": SessionStatus.IN_PROGRESS}),
            "completed": _count("IMM Training Session", {"workflow_state": SessionStatus.COMPLETED}),
            "cancelled": _count("IMM Training Session", {"workflow_state": SessionStatus.CANCELLED}),
        },
        "competencies": {
            "total": _count("IMM User Competency", {}),
            "pending": _count("IMM User Competency", {"workflow_state": CompetencyStatus.PENDING}),
            "active": _count("IMM User Competency", {"workflow_state": CompetencyStatus.ACTIVE}),
            # BR-06-14: expiring/expired đếm theo SoT LIVE (date-derived), KHÔNG cờ
            # workflow_state thuần → INVARIANT card == drill (get_expiring_competencies).
            "expiring": _count("IMM User Competency", _expiring_competency_filter()),
            "expired": _count("IMM User Competency", _expired_competency_filter()),
            "revoked": _count("IMM User Competency", {"workflow_state": CompetencyStatus.REVOKED}),
        },
        "programs": {
            "total": _count("IMM Training Program", {}),
            "active": _count("IMM Training Program", {"is_active": 1}),
        },
    }


def get_competency_gaps_by_dept() -> dict:
    """Phân tích thiếu hụt năng lực theo khoa/phòng.

    Returns:
        dict với "items" là list {department, total, active, expired, missing}.
    """
    try:
        rows = frappe.db.sql("""
            SELECT
                uc.department_at_assessment AS department,
                COUNT(*) AS total,
                SUM(CASE WHEN uc.workflow_state = 'Active' THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN uc.workflow_state = 'Expiring' THEN 1 ELSE 0 END) AS expiring_count,
                SUM(CASE WHEN uc.workflow_state = 'Expired' THEN 1 ELSE 0 END) AS expired_count,
                SUM(CASE WHEN uc.workflow_state = 'Revoked' THEN 1 ELSE 0 END) AS revoked_count
            FROM `tabIMM User Competency` uc
            WHERE uc.department_at_assessment IS NOT NULL
              AND uc.department_at_assessment != ''
            GROUP BY uc.department_at_assessment
            ORDER BY expired_count DESC
        """, as_dict=True)
        return {"items": rows}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-06 get_competency_gaps_by_dept")
        return {"items": []}


def get_expiring_competencies(days: int = EXPIRY_WINDOW_DAYS) -> list:
    """Lấy danh sách hồ sơ năng lực sắp hết hạn trong `days` ngày.

    Drill của tile "Sắp hết hạn". Khi `days == EXPIRY_WINDOW_DAYS` (mặc định),
    dùng CHUNG predicate với KPI count (_expiring_competency_filter) → INVARIANT:
        kpis.competencies.expiring == len(get_expiring_competencies(60))

    Args:
        days: số ngày nhìn trước (mặc định EXPIRY_WINDOW_DAYS = 60).

    Returns:
        list dict hồ sơ sắp hết hạn, sắp xếp theo expiry_date tăng dần.
    """
    if days == EXPIRY_WINDOW_DAYS:
        filters = _expiring_competency_filter()  # SoT chung với KPI card
    else:
        cutoff_end = str(add_days(nowdate(), days))
        filters = {
            "workflow_state": ["in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]],
            "expiry_date": ["between", [nowdate(), cutoff_end]],
        }
    return frappe.get_all(
        "IMM User Competency",
        filters=filters,
        fields=[
            "name", "user", "device_model", "training_program",
            "expiry_date", "days_until_expiry", "recertification_due_date",
            "competency_level", "department_at_assessment",
        ],
        order_by="expiry_date asc",
    )


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_session_or_raise(session_name: str):
    doc = TrainingSessionRepo.get(session_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy buổi đào tạo: {session_name}")
    return doc


def _require_training_officer() -> None:
    if not rbac.can("training.write"):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ Training Manager/User mới được thực hiện thao tác này")


def _invalidate_auth_cache(user: str, device_model: str) -> None:
    cache_key = f"imm06:auth:{user}:{device_model}"
    try:
        frappe.cache().delete_value(cache_key)
    except Exception:
        pass


def _log_competency_audit(competency_name: str, user: str, action: str, note: str) -> None:
    try:
        log_audit_event(
            asset=user,
            event_type=f"competency_{action.lower()}",
            actor=frappe.session.user,
            ref_doctype="IMM User Competency",
            ref_name=competency_name,
            change_summary=f"IMM-06 {action}: {competency_name}. {note}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-06 audit trail failed: {action} {competency_name}")


def _send_expiry_alert(comp: dict, milestone: int) -> None:
    try:
        frappe.sendmail(
            recipients=[comp["user"]],
            subject=f"[AssetCore] Năng lực sắp hết hạn trong {milestone} ngày",
            message=(f"Hồ sơ năng lực {comp['name']} cho Device Model "
                     f"{comp['device_model']} sẽ hết hạn vào {comp['expiry_date']}."),
        )
    except Exception:
        pass


# ─── Scheduler Jobs (Wave 2) ──────────────────────────────────────────────────

def check_recertification_due() -> None:
    """Scheduler daily 03:00: tạo placeholder Refresher Session 60 ngày trước recertification_due_date."""
    due_date_limit = add_days(nowdate(), 60)
    due_comps = frappe.get_all(
        "IMM User Competency",
        filters={
            "workflow_state": ("in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]),
            "recertification_due_date": ("<=", due_date_limit),
        },
        fields=["name", "user", "device_model", "training_program",
                "recertification_due_date"],
    )
    created: list[str] = []
    for comp in due_comps:
        if not comp.training_program:
            continue
        # Check if Refresher Session already planned for this user/program
        existing = frappe.db.exists(
            "IMM Training Session",
            {
                "training_program": comp.training_program,
                "session_type": "Onsite",  # placeholder
                "workflow_state": "Planned",
            },
        )
        if existing:
            continue
        try:
            session = frappe.get_doc({
                "doctype": "IMM Training Session",
                "training_program": comp.training_program,
                "session_date": add_days(nowdate(), 30),
                "session_type": "Onsite",
                "duration_planned_hours": 8,
                "status_remarks": f"Auto-tạo cho tái chứng nhận {comp.name}",
            })
            session.flags.ignore_links = True
            session.insert(ignore_permissions=True)
            created.append(session.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-06: create recert session failed for {comp.name}")
    if created:
        try:
            from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
            recipients = _get_role_emails(["Training Manager", "PM Manager"])
            _safe_sendmail(
                recipients=recipients,
                subject=f"[AssetCore] {len(due_comps)} người cần tái chứng nhận trong 60 ngày",
                message=f"<p>{len(due_comps)} hồ sơ năng lực cần tái chứng nhận trong 60 ngày. {len(created)} phiên mới tạo.</p>",
            )
        except Exception:
            pass


def generate_weekly_gap_report() -> None:
    """Scheduler weekly Monday 02:00: tạo Gap Report và gửi email."""
    try:
        report = generate_gap_report({})
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        recipients = _get_role_emails(["PM Manager", "Commissioning Manager"])
        _safe_sendmail(
            recipients=recipients,
            subject=f"[AssetCore] Gap Report tuần này: {report.get('report_name')}",
            message=f"<p>Gap Report tuần này đã được tạo. Vui lòng kiểm tra hệ thống.</p>",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-06: generate_weekly_gap_report failed")


def handle_user_dept_change(doc, method=None) -> None:
    """Doc event User.on_update: invalidate auth cache nếu department thay đổi."""
    if not doc.has_value_changed("department"):
        return
    # Invalidate all competency caches for this user
    comps = frappe.get_all(
        "IMM User Competency",
        filters={"user": doc.name, "workflow_state": ("in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING])},
        fields=["device_model"],
    )
    for c in comps:
        if c.device_model:
            invalidate_authorization_cache(doc.name, c.device_model)
