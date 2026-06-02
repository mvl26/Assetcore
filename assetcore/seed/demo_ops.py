"""Demo operational data seeder for AssetCore (IMM-08 PM, IMM-11 Calibration).

Mục đích: sinh demo record cho các DocType vận hành đang RỖNG để có thể
"walk" workflow-button-theo-state trên UI (Software Factory rounds 11-15).

Nguyên tắc (KHÔNG vi phạm):
    - Mọi record đi qua SERVICE entry-point thật (imm08/imm11) → workflow +
      lifecycle event + audit trail sinh đúng. KHÔNG ``frappe.db.set_value`` lén
      để giả lập trạng thái.
    - Idempotent: chạy nhiều lần không tạo trùng (đánh dấu ``SEED_MARKER`` +
      kiểm tra tồn tại trước khi tạo).
    - KHÔNG xoá dữ liệu. Cleanup là thao tác destructive → cần phê duyệt riêng.

Gọi:
    bench --site <site> execute assetcore.seed.demo_ops.run
    bench --site <site> execute assetcore.seed.demo_ops.run --kwargs '{"as_admin": true}'

Trả về dict counts: số record tạo mới / đã tồn tại cho từng loại.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, nowdate

SEED_MARKER = "[SEED-DEMO]"
"""Đánh dấu nhận diện record do seeder tạo (để cleanup được khi cần)."""

DEMO_CALIBRATION_TECH = "Administrator"
"""Technician cho calibration demo — dùng Administrator để chắc chắn tồn tại."""


def _active_assets(limit: int = 5) -> list[dict]:
    """Lấy AC Asset đang ở lifecycle_status=Active (đủ điều kiện vận hành)."""
    return frappe.get_all(
        "AC Asset",
        filters={"lifecycle_status": "Active"},
        fields=["name", "asset_category", "device_model"],
        limit=limit,
    )


# ────────────────────────────────────────────────────────────
# IMM-11 — Calibration (cleanest: Active asset đã có schedule)
# ────────────────────────────────────────────────────────────

def _seed_calibrations(result: dict) -> None:
    """Sinh IMM Asset Calibration qua imm11, walk Scheduled→In Progress→Passed.

    Idempotent: bỏ qua asset đã có calibration mang SEED_MARKER trong
    ``traceability_reference``.
    """
    from assetcore.services import imm11

    created = existing = 0
    assets = _active_assets()
    for a in assets:
        asset = a["name"]
        # Idempotent guard: đã seed calibration HỢP LỆ (chưa cancel) cho asset?
        # Bỏ qua record docstatus=2 (Cancelled) — coi như chưa seed, tạo lại.
        if frappe.db.exists(
            "IMM Asset Calibration",
            {
                "asset": asset,
                "traceability_reference": SEED_MARKER,
                "docstatus": ["!=", 2],
            },
        ):
            existing += 1
            continue

        sched = frappe.db.get_value(
            "IMM Calibration Schedule", {"asset": asset}, "name"
        )
        try:
            # In-House: tránh VR-11-01 (External bắt buộc chọn lab supplier).
            # VR-11-06: In-House bắt buộc nhập serial thiết bị chuẩn.
            cal = imm11.create_calibration(
                asset=asset,
                calibration_type="In-House",
                scheduled_date=nowdate(),
                technician=DEMO_CALIBRATION_TECH,
                calibration_schedule=sched,
                reference_standard_serial="REF-STD-DEMO-001",
                traceability_reference=SEED_MARKER,
            )
            name = cal["name"]
            # Thêm 1 measurement (đạt) để có dữ liệu thực
            imm11.add_measurement(
                name,
                parameter_name="Output Accuracy",
                unit="%",
                nominal_value=100.0,
                tolerance_positive=2.0,
                tolerance_negative=2.0,
                measured_value=100.5,
            )
            # Walk: Scheduled → In Progress → Passed, rồi SUBMIT để chạy
            # on_submit (handle_calibration_pass) — sinh lifecycle event
            # "calibration_passed" + KHÔI PHỤC asset Calibrating→Active.
            # Nếu thiếu submit, asset kẹt ở Calibrating (seed không idempotent).
            imm11.update_calibration(name, {"status": "In Progress"})
            imm11.update_calibration(name, {"status": "Passed", "actual_date": nowdate()})
            imm11.submit_calibration(name)
            created += 1
        except Exception:  # noqa: BLE001 — log, tiếp tục asset khác
            frappe.log_error(
                frappe.get_traceback(),
                f"demo_ops: seed calibration failed for {asset}",
            )

    result["calibration"] = {"created": created, "existing": existing}


# ────────────────────────────────────────────────────────────
# IMM-08 — PM (cần PM Checklist Template + PM Schedule trước WO)
# ────────────────────────────────────────────────────────────

def _ensure_pm_template(asset_category: str) -> str | None:
    """Đảm bảo có PM Checklist Template Quarterly cho danh mục.

    Đây là master-data setup hợp lệ (KHÔNG phải hack) — service PM yêu cầu
    template để resolve schedule. Trả về tên template hoặc None nếu category rỗng.
    """
    if not asset_category:
        return None
    existing = frappe.db.get_value(
        "PM Checklist Template",
        {"asset_category": asset_category, "pm_type": "Quarterly"},
        "name",
    )
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "PM Checklist Template",
            "template_name": f"{SEED_MARKER} PM Quý - {asset_category}",
            "asset_category": asset_category,
            "pm_type": "Quarterly",
            "version": "1.0",
            "effective_date": nowdate(),
            "checklist_items": [
                {
                    "item_code": "VIS-01",
                    "description": "Kiểm tra ngoại quan, vệ sinh thiết bị",
                    "measurement_type": "Pass/Fail",
                    "is_critical": 0,
                },
                {
                    "item_code": "FUN-01",
                    "description": "Kiểm tra chức năng vận hành cơ bản",
                    "measurement_type": "Pass/Fail",
                    "is_critical": 1,
                },
            ],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _seed_pm_work_orders(result: dict) -> None:
    """Sinh PM Schedule + PM Work Order qua imm08.

    Mục tiêu: ≥2 WO ở ≥2 state (1 In Progress, 1 Completed).
    """
    from assetcore.services import imm08

    sched_created = wo_created = wo_existing = 0
    assets = _active_assets(limit=2)
    walked_states: list[str] = []

    for i, a in enumerate(assets):
        asset = a["name"]
        category = a.get("asset_category")
        # BR-08-06: High/Critical cần photo evidence không có trong luồng seed
        # → chỉ seed PM cho thiết bị rủi ro thấp/trung bình (demo workflow).
        risk = frappe.db.get_value("AC Asset", asset, "risk_classification")
        if risk in ("High", "Critical"):
            continue
        template = _ensure_pm_template(category)
        if not template:
            continue

        # PM Schedule (idempotent qua naming format:PMS-{asset}-{pm_type})
        sched_name = f"PMS-{asset}-Quarterly"
        if not frappe.db.exists("PM Schedule", sched_name):
            try:
                imm08.create_schedule(
                    {
                        "asset_ref": asset,
                        "pm_type": "Quarterly",
                        "pm_interval_days": 90,
                        "checklist_template": template,
                        "alert_days_before": 7,
                        "last_pm_date": nowdate(),
                        "next_due_date": add_days(nowdate(), 90),
                    }
                )
                sched_created += 1
            except Exception:  # noqa: BLE001
                frappe.log_error(
                    frappe.get_traceback(),
                    f"demo_ops: PM schedule failed {asset}",
                )
                continue

        if not frappe.db.exists("PM Schedule", sched_name):
            continue

        # Idempotent: đã có WO seed cho schedule này?
        existing_wo = frappe.db.exists(
            "PM Work Order",
            {"pm_schedule": sched_name, "technician_notes": ["like", f"%{SEED_MARKER}%"]},
        )
        if existing_wo:
            wo_existing += 1
            continue

        try:
            wo = imm08.create_adhoc_work_order(
                {
                    "asset_ref": asset,
                    "pm_schedule": sched_name,
                    "due_date": add_days(nowdate(), 7),
                    "pm_type": "Quarterly",
                    # Marker ngay khi tạo → idempotent + cleanup-identifiable
                    # cho CẢ WO dừng ở In Progress.
                    "technician_notes": f"{SEED_MARKER} demo PM WO",
                }
            )
            wo_name = wo["name"]
            # Walk Open → In Progress (mọi WO seed).
            imm08.assign_technician(
                wo_name, technician=DEMO_CALIBRATION_TECH, scheduled_date=nowdate()
            )
            walked_states.append("In Progress")
            # WO đầu tiên đủ điều kiện → walk tiếp tới Completed để phủ ≥2 state.
            if wo_created == 0:
                # Walk tới Completed: cần checklist_results matching rows
                wo_doc = frappe.get_doc("PM Work Order", wo_name)
                results = [
                    {"idx": row.idx, "result": "Pass", "notes": SEED_MARKER}
                    for row in (wo_doc.checklist_results or [])
                ]
                imm08.submit_result(
                    wo_name,
                    checklist_results=results,
                    overall_result="Pass",
                    technician_notes=f"{SEED_MARKER} PM hoàn thành (demo)",
                    pm_sticker_attached=1,
                    duration_minutes=45,
                )
                walked_states[-1] = "Completed"
            wo_created += 1
        except Exception:  # noqa: BLE001
            frappe.log_error(
                frappe.get_traceback(),
                f"demo_ops: PM WO failed {asset}",
            )

    result["pm_schedule"] = {"created": sched_created}
    result["pm_work_order"] = {
        "created": wo_created,
        "existing": wo_existing,
        "walked_states": walked_states,
    }


# ────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────

def run(as_admin: bool = True) -> dict:
    """Chạy toàn bộ seeder. Trả về dict counts.

    Args:
        as_admin: nếu True, set session.user='Administrator' để bỏ qua RBAC
            (seed là thao tác provisioning, không phải hành vi nghiệp vụ).
    """
    if as_admin:
        frappe.set_user("Administrator")

    result: dict = {}
    _seed_calibrations(result)
    _seed_pm_work_orders(result)
    frappe.db.commit()

    # Verify audit trail: đếm lifecycle event sinh ra cho asset Active
    active = [a["name"] for a in _active_assets()]
    result["lifecycle_events_for_active_assets"] = (
        frappe.db.count("Asset Lifecycle Event", {"asset": ["in", active]})
        if active
        else 0
    )
    return result
