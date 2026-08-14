# -*- coding: utf-8 -*-
"""Cleanup test/junk AC Asset records and seed 3 realistic Vietnamese hospital assets
with full lifecycle data (PM/CM WOs, lifecycle events, downtime logs, depreciation).

Run:
    bench --site miyano execute assetcore.scripts.maintenance.cleanup_and_seed_assets.run
"""
from __future__ import annotations

import frappe
from frappe.utils import (
    add_days, add_months, add_to_date, get_datetime, now_datetime, nowdate, getdate,
)

# ───── Constants ──────────────────────────────────────────────────────────────

TECHNICIAN = "chuvanhieu357@gmail.com"   # KTV Chu Hiếu
CUSTODIAN_A = "snonamevx@gmail.com"      # Đoàn Ngọc Anh (BS phụ trách ICU)
CUSTODIAN_B = "sohaidiuuu@gmail.com"     # Trần Thị Tâm (BS phụ trách CĐHA)
ADMIN = "Administrator"

JUNK_PATTERNS = ("_Test", "Test Asset", "Sample", "Test ", "_test")
JUNK_DEVICE_MODELS = ("_Test Model",)

# 3 thiết bị thực tế cần đảm bảo tồn tại
TARGET_ASSETS = [
    {
        "asset_name": "Máy thở Dräger Evita V500 — ICU giường số 3",
        "device_model": "IMM-MDL-2026-0023",
        "asset_category": "Máy thở",
        "department": "Khoa-HSTC",
        "location": "AC-LOC-2026-0127",
        "supplier": "AC-SUP-2026-0017",
        "custodian": CUSTODIAN_A,
        "responsible_technician": TECHNICIAN,
        "manufacturer_sn": "EVT-2023-0891",
        "udi_code": "00884728000123",
        "byt_reg_no": "TTBYT-2022-0456-ICT",
        "byt_reg_expiry": "2027-08-14",
        "purchase_date": "2023-08-15",
        "gross_purchase_amount": 2_850_000_000.0,
        "warranty_expiry_date": "2026-08-14",
        "useful_life_years": 8,
        "residual_value": 285_000_000.0,
        "depreciation_method": "Straight Line",
        "depreciation_frequency": "Monthly",
        "depreciation_start_date": "2023-09-01",
        "in_service_date": "2023-09-01",
        "commissioning_date": "2023-09-01",
        "insurance_policy_no": "BH-PVI-2024-ICU-0017",
        "insurer_name": "Bảo hiểm PVI",
        "insured_value": 2_850_000_000.0,
        "insurance_start_date": "2024-01-01",
        "insurance_end_date": "2026-12-31",
        "notes": (
            "Máy thở Class III tại Khoa Hồi sức Tích cực, hỗ trợ thông khí "
            "xâm lấn/không xâm lấn. Sử dụng giường số 3 — bệnh nhân thở máy "
            "dài ngày. Đã qua 2 lần PM định kỳ và 1 lần thay van PEEP."
        ),
    },
    {
        "asset_name": "Monitor bệnh nhân Mindray BeneView T9 — ICU giường số 7",
        "device_model": "IMM-MDL-2026-0024",
        "asset_category": "Monitor theo dõi bệnh nhân",
        "department": "Khoa-HSTC",
        "location": "AC-LOC-2026-0127",
        "supplier": "AC-SUP-2026-0018",
        "custodian": CUSTODIAN_A,
        "responsible_technician": TECHNICIAN,
        "manufacturer_sn": "MBT9-2024-1122",
        "udi_code": "06901399200418",
        "byt_reg_no": "TTBYT-2024-1203-MDY",
        "byt_reg_expiry": "2029-03-19",
        "purchase_date": "2024-03-20",
        "gross_purchase_amount": 485_000_000.0,
        "warranty_expiry_date": "2027-03-19",
        "useful_life_years": 7,
        "residual_value": 48_500_000.0,
        "depreciation_method": "Straight Line",
        "depreciation_frequency": "Monthly",
        "depreciation_start_date": "2024-04-01",
        "in_service_date": "2024-04-01",
        "commissioning_date": "2024-04-01",
        "insurance_policy_no": "BH-PVI-2024-ICU-0018",
        "insurer_name": "Bảo hiểm PVI",
        "insured_value": 485_000_000.0,
        "insurance_start_date": "2024-04-01",
        "insurance_end_date": "2027-03-31",
        "notes": (
            "Monitor đa thông số 12.1 inch — theo dõi ECG 5-lead, SpO2, "
            "NIBP, IBP, EtCO2 cho bệnh nhân hậu phẫu nặng tại ICU. Có module "
            "kết nối HIS qua HL7 (đã cấu hình tại firmware 02.18.06)."
        ),
    },
    {
        "asset_name": "Máy siêu âm Philips EPIQ 7 — Khoa Chẩn đoán Hình ảnh",
        "device_model": "IMM-MDL-2026-0026",
        "asset_category": "Máy siêu âm chẩn đoán",
        "department": "Khoa-CDHA",
        "location": "AC-LOC-2026-0129",
        "supplier": "AC-SUP-2026-0018",
        "custodian": CUSTODIAN_B,
        "responsible_technician": TECHNICIAN,
        "manufacturer_sn": "EPQ7-2022-0445",
        "udi_code": "08714690238856",
        "byt_reg_no": "TTBYT-2022-0789-SHA",
        "byt_reg_expiry": "2027-05-09",
        "purchase_date": "2022-05-10",
        "gross_purchase_amount": 1_250_000_000.0,
        "warranty_expiry_date": "2025-05-09",
        "useful_life_years": 10,
        "residual_value": 125_000_000.0,
        "depreciation_method": "Straight Line",
        "depreciation_frequency": "Monthly",
        "depreciation_start_date": "2022-07-01",
        "in_service_date": "2022-07-01",
        "commissioning_date": "2022-07-01",
        "insurance_policy_no": "BH-BAOVIET-2024-CDHA-0033",
        "insurer_name": "Bảo Việt Insurance",
        "insured_value": 1_250_000_000.0,
        "insurance_start_date": "2024-01-01",
        "insurance_end_date": "2026-12-31",
        "notes": (
            "Hệ thống siêu âm cao cấp — đầu dò C5-1, S5-1, L12-3, X7-2t. "
            "Phục vụ siêu âm tim, sản phụ khoa, mạch máu, tổng quát. "
            "Hết bảo hành 05/2025; đang sử dụng hợp đồng bảo trì hằng năm với NCC."
        ),
    },
]


# ───── 1) Cleanup ─────────────────────────────────────────────────────────────

def cleanup_test_assets() -> dict:
    """Xóa toàn bộ AC Asset rác (test fixtures, _Test, asset_name=Test Asset, model=_Test Model)."""
    deleted: list[str] = []
    skipped: list[tuple[str, str]] = []

    # 1) Pattern asset_name
    or_filters = [["asset_name", "like", f"%{p}%"] for p in JUNK_PATTERNS]
    candidates = frappe.get_all(
        "AC Asset",
        or_filters=or_filters,
        fields=["name", "asset_name", "docstatus"],
        limit_page_length=0,
    )

    # 2) Asset with device_model in junk list
    if frappe.db.table_exists("IMM Device Model"):
        for m in JUNK_DEVICE_MODELS:
            if frappe.db.exists("IMM Device Model", m):
                extras = frappe.get_all(
                    "AC Asset", filters={"device_model": m},
                    fields=["name", "asset_name", "docstatus"], limit_page_length=0)
                seen = {c["name"] for c in candidates}
                candidates.extend([e for e in extras if e["name"] not in seen])

    print(f"[cleanup] {len(candidates)} junk asset candidates")
    for a in candidates:
        name = a["name"]
        try:
            _purge_asset_dependents(name)
            doc = frappe.get_doc("AC Asset", name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("AC Asset", name, force=1, ignore_permissions=True, delete_permanently=True)
            deleted.append(f"{name} ({a['asset_name']!r})")
            print(f"  [DEL] {name} — {a['asset_name']}")
        except Exception as e:
            skipped.append((name, str(e)))
            print(f"  [SKIP] {name}: {e}")

    return {"deleted": deleted, "skipped": skipped}


def _purge_asset_dependents(asset: str) -> None:
    """Cancel + delete all dependent docs of an asset before deleting it."""
    # Cancel submitted PM Work Orders / Asset Repair
    for dt, fld in [
        ("PM Work Order", "asset_ref"),
        ("Asset Repair", "asset_ref"),
        ("Asset Commissioning", "final_asset"),
    ]:
        if not frappe.db.table_exists(dt):
            continue
        rows = frappe.get_all(dt, filters={fld: asset}, fields=["name", "docstatus"], limit_page_length=0)
        for r in rows:
            try:
                d = frappe.get_doc(dt, r["name"])
                if d.docstatus == 1:
                    d.cancel()
                frappe.delete_doc(dt, r["name"], force=1, ignore_permissions=True, delete_permanently=True)
            except Exception as e:
                print(f"    [WARN] could not delete {dt} {r['name']}: {e}")

    # Soft dependents (no docstatus / no submit)
    for dt, fld in [
        ("PM Schedule", "asset_ref"),
        ("PM Task Log", "asset_ref"),
        ("Asset Lifecycle Event", "asset"),
        ("AC Asset Downtime Log", "asset"),
        ("IMM Audit Trail", "asset"),
        ("Asset Transfer", "asset"),
    ]:
        if not frappe.db.table_exists(dt):
            continue
        for r in frappe.get_all(dt, filters={fld: asset}, fields=["name"], limit_page_length=0):
            try:
                frappe.delete_doc(dt, r["name"], force=1, ignore_permissions=True, delete_permanently=True)
            except Exception as e:
                print(f"    [WARN] could not delete {dt} {r['name']}: {e}")


# ───── 2) Upsert 3 real assets with ALL fields filled ─────────────────────────

def _resolve_category(category_name: str) -> str:
    """Đổi TÊN danh mục (đọc được) → doc-name thật (``CAT-####``).

    ``AC Asset Category`` autoname ``CAT-####`` nên KHÔNG được gán thẳng chuỗi
    người đọc vào ``asset_category``: Frappe không kiểm link khi ghi qua script,
    nên giá trị sai lọt vào DB thành FK TREO — chính lỗi này (3 slug cũ
    ``Thiet-bi-*`` không còn trong bộ danh mục) đã làm ``demo_ops`` gãy ở
    ``_ensure_pm_template`` với "Could not find Loại thiết bị".
    Thiếu danh mục thì DỪNG HẲN, không seed dữ liệu hỏng.
    """
    name = frappe.db.get_value("AC Asset Category", {"category_name": category_name}, "name")
    if not name:
        frappe.throw(
            f"Thiếu danh mục '{category_name}' — seed dữ liệu tham chiếu trước "
            f"(assetcore.scripts.seed.seed_ref_data) rồi chạy lại."
        )
    return name


def seed_or_update_assets() -> list[str]:
    """Đảm bảo 3 asset thực tế tồn tại và điền đầy đủ TẤT CẢ field nghiệp vụ."""
    asset_names: list[str] = []

    for spec in TARGET_ASSETS:
        existing = frappe.get_all(
            "AC Asset", filters={"asset_name": spec["asset_name"]},
            fields=["name"], limit_page_length=1)
        if existing:
            name = existing[0]["name"]
            doc = frappe.get_doc("AC Asset", name)
            print(f"[upsert] UPDATE {name} — {spec['asset_name']}")
        else:
            doc = frappe.new_doc("AC Asset")
            doc.naming_series = "AC-ASSET-.YYYY.-.#####"
            doc.uom = "Cái"
            print(f"[upsert] CREATE — {spec['asset_name']}")

        # Apply ALL fields from spec (skip lifecycle/status — guarded)
        for k, v in spec.items():
            if k in ("lifecycle_status", "status", "calibration_status"):
                continue
            if k == "asset_category":
                v = _resolve_category(v)
            setattr(doc, k, v)

        # Auto-derive
        total_months = spec["useful_life_years"] * 12
        doc.total_depreciation_months = total_months
        doc.uom = "Cái"
        doc.is_pm_required = 1
        # Asset code = manufacturer_sn (readable + unique)
        doc.asset_code = spec["manufacturer_sn"]
        doc.item_code = f"ITM-{spec['manufacturer_sn']}"

        # fetch_from will pull pm_interval_days, gmdn_code, risk_classification, medical_device_class from model
        doc.flags.ignore_permissions = True
        doc.flags.ignore_links = True
        # Bypass lifecycle_status guard during seed
        doc.flags.allow_status_change = True
        if doc.is_new():
            doc.lifecycle_status = "Draft"
            doc.insert(ignore_permissions=True)

        # Set guarded fields directly via db (bypass validate)
        frappe.db.set_value("AC Asset", doc.name, {
            "status": "Active",
            "lifecycle_status": "Active",
            "calibration_status": "Not Required",
        }, update_modified=False)

        # Re-load and save remaining changes (now guard sees lifecycle_status==Active stable)
        doc = frappe.get_doc("AC Asset", doc.name)
        for k, v in spec.items():
            if k in ("lifecycle_status", "status", "calibration_status"):
                continue
            # Vòng áp field THỨ HAI cũng phải phân giải danh mục: bỏ sót ở đây thì
            # nó ghi đè giá trị đã phân giải ở vòng trên bằng chuỗi thô, và
            # flags.ignore_links=True bên dưới khiến link hỏng lọt thẳng vào DB.
            if k == "asset_category":
                v = _resolve_category(v)
            setattr(doc, k, v)
        doc.total_depreciation_months = total_months
        doc.asset_code = spec["manufacturer_sn"]
        doc.item_code = f"ITM-{spec['manufacturer_sn']}"
        doc.is_pm_required = 1
        doc.flags.ignore_permissions = True
        doc.flags.ignore_links = True
        doc.flags.allow_status_change = True
        doc.save(ignore_permissions=True)

        asset_names.append(doc.name)
        print(f"  → {doc.name}")

    frappe.db.commit()
    return asset_names


# ───── 3) Seed PM + CM Work Orders ────────────────────────────────────────────

# PM schedule plan per asset (offsets from today; negative = past)
PM_PLAN = {
    "Máy thở Dräger Evita V500 — ICU giường số 3": [
        ("-180d", "Bảo dưỡng định kỳ Quý — kiểm tra van PEEP, hiệu chuẩn cảm biến SpO2, vệ sinh bộ lọc khuẩn theo QP-03-2025"),
        ("-90d",  "Bảo dưỡng định kỳ Quý — thay màng lọc HEPA, kiểm tra áp lực hệ thống, calibration O2 sensor"),
        ("-7d",   "Bảo dưỡng định kỳ Quý — kiểm tra toàn diện theo checklist Class III; thay pin backup UPS internal"),
    ],
    "Monitor bệnh nhân Mindray BeneView T9 — ICU giường số 7": [
        ("-240d", "Bảo dưỡng định kỳ 6 tháng — calibration NIBP module, kiểm tra cáp ECG 5-lead, làm sạch đầu dò SpO2"),
        ("-60d",  "Bảo dưỡng định kỳ 6 tháng — kiểm tra pin lithium dự phòng, update firmware lên bản 02.18.06"),
    ],
    "Máy siêu âm Philips EPIQ 7 — Khoa Chẩn đoán Hình ảnh": [
        ("-330d", "Bảo dưỡng định kỳ 6 tháng — kiểm tra đầu dò C5-1 và L12-3, vệ sinh quạt tản nhiệt, calibration B-mode"),
        ("-150d", "Bảo dưỡng định kỳ 6 tháng — thay gel pad đầu dò X7-2t, kiểm tra hệ thống ổ cứng SSD"),
        ("-30d",  "Bảo dưỡng định kỳ 6 tháng — kiểm tra phantom độ phân giải theo IEC 61391-1, update QC report"),
    ],
}

# CM plan per asset — completed with downtime hours
CM_PLAN = {
    "Máy thở Dräger Evita V500 — ICU giường số 3": [
        {"offset_open_d": -150, "downtime_h": 6.5,
         "failure": "Báo lỗi 'Inspiratory valve fault' — bệnh nhân không nhận đủ thể tích thông khí Vt mục tiêu.",
         "repair": "Thay thế van inspiratory assy (P/N 8410055), kiểm tra rò rỉ hệ thống bằng leak test pass 100ml/min. Xác minh Vt, PEEP, FiO2.",
         "root_cause": "Mechanical",
         "priority": "Emergency"},
        {"offset_open_d": -45, "downtime_h": 2.5,
         "failure": "Cảm biến SpO2 báo 'Sensor disconnect' không liên tục, ảnh hưởng đến hiển thị bão hòa oxy.",
         "repair": "Thay cáp SpO2 module (P/N MS17522), test ổn định 4h liên tục với phantom finger.",
         "root_cause": "Electrical",
         "priority": "Urgent"},
    ],
    "Monitor bệnh nhân Mindray BeneView T9 — ICU giường số 7": [
        {"offset_open_d": -120, "downtime_h": 4.0,
         "failure": "Màn hình LCD chớp tắt khi vận hành >2h liên tục, nghi do nhiệt độ inverter.",
         "repair": "Thay LCD inverter assembly (P/N 022-000167-01), kiểm tra burn-in test 24h pass.",
         "root_cause": "Electrical",
         "priority": "Urgent"},
        {"offset_open_d": -20, "downtime_h": 1.5,
         "failure": "NIBP cuff đo áp lực sai lệch >10 mmHg so với chuẩn manomet.",
         "repair": "Hiệu chuẩn lại module NIBP qua phần mềm service Mindray (Cal NIBP routine), pass spec ±3 mmHg.",
         "root_cause": "Wear and Tear",
         "priority": "Normal"},
    ],
    "Máy siêu âm Philips EPIQ 7 — Khoa Chẩn đoán Hình ảnh": [
        {"offset_open_d": -200, "downtime_h": 8.0,
         "failure": "Đầu dò C5-1 mất tín hiệu 1 kênh (cột đứng trên B-mode), khả năng cao do crystal element bị hỏng.",
         "repair": "RMA đầu dò C5-1 (S/N 04A1234) về Philips, tạm dùng đầu dò backup. Lắp đầu dò replacement (S/N 04A8842), QC bằng phantom CIRS 040GSE pass.",
         "root_cause": "Wear and Tear",
         "priority": "Urgent"},
        {"offset_open_d": -75, "downtime_h": 3.0,
         "failure": "Hệ thống treo khi chạy chế độ 4D Live, screen freeze yêu cầu reboot.",
         "repair": "Update phần mềm hệ thống lên version 5.0.4, clear cache cardio module, kiểm tra dump log không còn exception.",
         "root_cause": "Software",
         "priority": "Normal"},
    ],
}


def _purge_existing_artifacts(asset_name: str) -> None:
    """Xóa toàn bộ PM/CM WOs, downtime logs, lifecycle events cũ để seed lại sạch."""
    for dt, fld in [
        ("PM Work Order", "asset_ref"),
        ("Asset Repair", "asset_ref"),
    ]:
        for r in frappe.get_all(dt, filters={fld: asset_name}, fields=["name", "docstatus"], limit_page_length=0):
            try:
                d = frappe.get_doc(dt, r["name"])
                if d.docstatus == 1:
                    d.flags.ignore_permissions = True
                    d.cancel()
                frappe.delete_doc(dt, r["name"], force=1, ignore_permissions=True, delete_permanently=True)
            except Exception as e:
                print(f"    [purge warn] {dt} {r['name']}: {e}")
    for dt, fld in [
        ("PM Task Log", "asset_ref"),
        ("AC Asset Downtime Log", "asset"),
        ("Asset Lifecycle Event", "asset"),
    ]:
        for r in frappe.get_all(dt, filters={fld: asset_name}, fields=["name"], limit_page_length=0):
            try:
                frappe.delete_doc(dt, r["name"], force=1, ignore_permissions=True, delete_permanently=True)
            except Exception as e:
                print(f"    [purge warn] {dt} {r['name']}: {e}")


def seed_work_orders_per_asset(asset_names: list[str]) -> dict:
    """Tạo PM + CM Work Orders đã Completed, kèm Lifecycle Event + Downtime Log."""
    stats = {"pm": 0, "cm": 0, "downtime": 0}

    # Step 0: purge existing artifacts on the 3 assets to avoid duplicates / conflicting open WOs
    for asset_name in asset_names:
        _purge_existing_artifacts(asset_name)
    frappe.db.commit()

    for asset_name in asset_names:
        asset = frappe.get_doc("AC Asset", asset_name)
        cat = asset.asset_category
        spec_name = asset.asset_name

        # Ensure PM Schedule exists (Active)
        pm_sched = frappe.get_all(
            "PM Schedule",
            filters={"asset_ref": asset_name, "status": "Active"},
            fields=["name", "checklist_template", "pm_interval_days", "pm_type"],
            limit_page_length=1,
        )
        if pm_sched:
            sched_name = pm_sched[0]["name"]
            checklist_tpl = pm_sched[0]["checklist_template"]
            sched_pm_type = pm_sched[0]["pm_type"]
            sched_interval = pm_sched[0]["pm_interval_days"]
        else:
            checklist_tpl = frappe.db.get_value(
                "PM Checklist Template", {"asset_category": cat, "pm_type": "Quarterly"}, "name"
            ) or frappe.db.get_value("PM Checklist Template", {"asset_category": cat}, "name")
            sched_interval = asset.pm_interval_days or 90
            sched_pm_type = "Quarterly" if sched_interval <= 91 else "Semi-Annual"
            sched_doc = frappe.get_doc({
                "doctype": "PM Schedule",
                "asset_ref": asset_name,
                "pm_type": sched_pm_type,
                "pm_interval_days": sched_interval,
                "checklist_template": checklist_tpl,
                "status": "Active",
                "responsible_technician": TECHNICIAN,
                "alert_days_before": 7,
                "next_due_date": add_days(nowdate(), sched_interval),
            }).insert(ignore_permissions=True)
            sched_name = sched_doc.name

        # PM Work Orders (completed in past)
        for offset_str, summary in PM_PLAN.get(spec_name, []):
            days = int(offset_str.replace("d", ""))
            due_date = add_days(nowdate(), days)
            completion = due_date  # completed on due date
            wo = frappe.new_doc("PM Work Order")
            wo.asset_ref = asset_name
            wo.pm_schedule = sched_name
            wo.pm_type = sched_pm_type
            wo.wo_type = "Preventive"
            wo.status = "Completed"
            wo.due_date = due_date
            wo.scheduled_date = due_date
            wo.completion_date = completion
            wo.assigned_to = TECHNICIAN
            wo.assigned_by = ADMIN
            wo.overall_result = "Pass"
            wo.technician_notes = summary
            wo.pm_sticker_attached = 1
            wo.duration_minutes = 90
            wo.is_late = 0
            # Populate checklist
            if checklist_tpl:
                tpl = frappe.get_doc("PM Checklist Template", checklist_tpl)
                for idx, item in enumerate(getattr(tpl, "checklist_items", []) or [], start=1):
                    wo.append("checklist_results", {
                        "checklist_item_idx": idx,
                        "description": getattr(item, "description", None) or getattr(item, "task_description", ""),
                        "measurement_type": getattr(item, "measurement_type", "Pass/Fail"),
                        "unit": getattr(item, "unit", ""),
                        "result": "Pass",
                        "measured_value": "OK",
                        "notes": "Đạt tiêu chuẩn theo SOP",
                    })
            wo.flags.ignore_links = True
            wo.flags.ignore_permissions = True
            wo.flags.ignore_validate = True
            wo.flags.ignore_mandatory = True
            wo.insert(ignore_permissions=True)
            try:
                wo.submit()
            except Exception as e:
                print(f"    [PM submit warn] {wo.name}: {e}")
                frappe.db.set_value("PM Work Order", wo.name, {
                    "docstatus": 1, "status": "Completed",
                    "completion_date": completion,
                }, update_modified=False)
            stats["pm"] += 1
            print(f"  [PM] {wo.name} — {asset_name} @ {completion}")

        # Update asset last_pm_date / next_pm_date
        pm_offsets = [int(o.replace("d", "")) for o, _ in PM_PLAN.get(spec_name, [])]
        if pm_offsets:
            last_offset = max(pm_offsets)
            frappe.db.set_value("AC Asset", asset_name, {
                "last_pm_date": add_days(nowdate(), last_offset),
                "next_pm_date": add_days(nowdate(), last_offset + (asset.pm_interval_days or 90)),
            }, update_modified=False)

        # Pick a PM WO to link as source for CM (BR-09-01 requires source)
        any_pm_wo = frappe.db.get_value(
            "PM Work Order", {"asset_ref": asset_name}, "name", order_by="due_date desc")

        # CM Work Orders + Downtime Logs + Lifecycle Events
        for cm in CM_PLAN.get(spec_name, []):
            open_dt = add_to_date(now_datetime(), days=cm["offset_open_d"])
            completion_dt = add_to_date(open_dt, hours=cm["downtime_h"])
            risk_class_raw = asset.risk_classification or "Medium"
            risk_class = {"Low": "Class I", "Medium": "Class II", "High": "Class III", "Critical": "Class III"}.get(risk_class_raw, "Class II")

            wo = frappe.new_doc("Asset Repair")
            wo.asset_ref = asset_name
            wo.asset_name = spec_name
            wo.asset_category = cat
            wo.risk_class = risk_class
            wo.serial_no = asset.manufacturer_sn
            wo.repair_type = "Corrective"
            wo.source_pm_wo = any_pm_wo  # BR-09-01: must have a source
            wo.priority = cm["priority"]
            wo.status = "Completed"
            wo.open_datetime = open_dt
            wo.assigned_datetime = add_to_date(open_dt, hours=0.5)
            wo.completion_datetime = completion_dt
            wo.mttr_hours = cm["downtime_h"]
            wo.sla_target_hours = 24.0
            wo.sla_breached = 0
            wo.is_repeat_failure = 0
            wo.assigned_to = TECHNICIAN
            wo.assigned_by = ADMIN
            wo.diagnosis_notes = f"Khảo sát hiện trường: {cm['failure']}"
            wo.failure_description = cm["failure"]
            wo.repair_summary = cm["repair"]
            wo.root_cause_category = cm["root_cause"]
            wo.dept_head_name = "Đoàn Ngọc Anh"
            wo.dept_head_confirmation_datetime = completion_dt
            wo.firmware_updated = 0
            wo.is_warranty_claim = 0
            wo.technician_notes = "Hoàn thành sửa chữa, thiết bị vận hành bình thường sau khi test."
            # Repair checklist (BR-09-04: tất cả phải Pass)
            wo.append("repair_checklist", {
                "test_description": "Kiểm tra điện áp hoạt động ổn định",
                "result": "Pass", "measured_value": "OK",
            })
            wo.append("repair_checklist", {
                "test_description": "Kiểm tra chức năng chính sau sửa chữa",
                "result": "Pass", "measured_value": "OK",
            })
            wo.append("repair_checklist", {
                "test_description": "Vận hành thử 30 phút không lỗi",
                "result": "Pass", "measured_value": "OK",
            })
            wo.flags.ignore_links = True
            wo.flags.ignore_permissions = True
            wo.flags.ignore_validate = True
            wo.flags.ignore_mandatory = True
            wo.insert(ignore_permissions=True)
            # Bypass before_insert overwriting open_datetime + on_submit recomputing mttr.
            # Force historical timestamps + completed state directly in DB.
            frappe.db.set_value("Asset Repair", wo.name, {
                "docstatus": 1,
                "status": "Completed",
                "open_datetime": open_dt,
                "assigned_datetime": add_to_date(open_dt, hours=0.5),
                "completion_datetime": completion_dt,
                "mttr_hours": cm["downtime_h"],
                "sla_target_hours": 24.0,
                "sla_breached": 0,
            }, update_modified=False)
            stats["cm"] += 1
            print(f"  [CM] {wo.name} — {asset_name} downtime={cm['downtime_h']}h")

            # `on_insert` may have transitioned asset → Under Repair; restore Active for next iter
            frappe.db.set_value("AC Asset", asset_name, {
                "lifecycle_status": "Active", "status": "Active",
            }, update_modified=False)
            # Close any open downtime log auto-created by transition_asset_status (we already have ours)
            open_logs = frappe.get_all("AC Asset Downtime Log",
                filters={"asset": asset_name, "is_open": 1},
                fields=["name"], limit_page_length=0)
            for ol in open_logs:
                frappe.db.set_value("AC Asset Downtime Log", ol["name"], {
                    "is_open": 0, "end_time": completion_dt,
                    "downtime_hours": cm["downtime_h"],
                }, update_modified=False)

            # Downtime Log (closed)
            dt_doc = frappe.get_doc({
                "doctype": "AC Asset Downtime Log",
                "naming_series": "DTL-.YYYY.-.#####",
                "asset": asset_name,
                "reason": "Sửa chữa",
                "start_time": open_dt,
                "end_time": completion_dt,
                "downtime_hours": cm["downtime_h"],
                "is_open": 0,
                "reference_doctype": "Asset Repair",
                "reference_name": wo.name,
                "notes": cm["failure"],
            }).insert(ignore_permissions=True)
            stats["downtime"] += 1

    frappe.db.commit()
    return stats


# ───── 4) Lifecycle Events ────────────────────────────────────────────────────

def seed_lifecycle_events(asset_names: list[str]) -> int:
    """Tạo các Asset Lifecycle Event để Tab Lịch sử có dữ liệu đầy đủ."""
    from assetcore.utils.lifecycle import create_lifecycle_event, log_audit_event

    count = 0
    for asset_name in asset_names:
        asset = frappe.get_doc("AC Asset", asset_name)
        comm_date = asset.commissioning_date or getdate(nowdate())

        # Clear existing events from prior seed runs (only ones we'd create) — keep DB clean
        # Skip cleanup here to avoid removing legitimate event history; we just append.

        events = [
            (add_to_date(comm_date, days=-7),  "registered",      "", "Commissioned",
             f"Đăng ký thiết bị {asset.asset_name} tại {asset.department} — bàn giao kỹ thuật."),
            (comm_date,                        "commissioned",    "Commissioned", "Active",
             f"Bàn giao chính thức cho khoa, đưa vào vận hành lâm sàng."),
            (add_to_date(comm_date, days=30),  "activated",       "Commissioned", "Active",
             "Hoàn tất 30 ngày vận hành ổn định, gắn nhãn QA approved."),
        ]
        # PM completed events
        for off_str, summary in PM_PLAN.get(asset.asset_name, []):
            days = int(off_str.replace("d", ""))
            events.append((
                add_days(nowdate(), days), "pm_completed", "Active", "Active",
                f"PM định kỳ hoàn thành: {summary[:120]}",
            ))
        # CM events
        for cm in CM_PLAN.get(asset.asset_name, []):
            open_dt = add_to_date(now_datetime(), days=cm["offset_open_d"])
            close_dt = add_to_date(open_dt, hours=cm["downtime_h"])
            events.append((open_dt, "repair_opened", "Active", "Under Repair", cm["failure"][:160]))
            events.append((close_dt, "repair_completed", "Under Repair", "Active",
                           f"Sửa chữa hoàn thành (MTTR={cm['downtime_h']}h): {cm['repair'][:130]}"))

        for ts, etype, from_st, to_st, note in events:
            try:
                le = frappe.get_doc({
                    "doctype": "Asset Lifecycle Event",
                    "naming_series": "ALE-.YYYY.-.#######",
                    "asset": asset_name,
                    "event_type": etype,
                    "timestamp": ts,
                    "actor": ADMIN,
                    "from_status": from_st,
                    "to_status": to_st,
                    "root_doctype": "AC Asset",
                    "root_record": asset_name,
                    "notes": note,
                }).insert(ignore_permissions=True)
                count += 1
            except Exception as e2:
                print(f"    [LE warn] {asset_name}/{etype}: {e2}")

        # Audit trail entry
        try:
            log_audit_event(
                asset=asset_name,
                event_type="System",
                actor=ADMIN,
                ref_doctype="AC Asset",
                ref_name=asset_name,
                change_summary=f"Seed thực tế hoàn tất cho {asset.asset_name} — full PM/CM/downtime/lifecycle.",
            )
        except Exception as e:
            print(f"    [audit warn] {asset_name}: {e}")

    frappe.db.commit()
    return count


# ───── 5) Depreciation schedule generation ────────────────────────────────────

def seed_depreciation(asset_names: list[str]) -> int:
    from assetcore.services.depreciation import generate_schedule
    n = 0
    for asset_name in asset_names:
        try:
            generate_schedule(asset_name)
            n += 1
            print(f"  [DEP] schedule generated for {asset_name}")
        except Exception as e:
            print(f"  [DEP warn] {asset_name}: {e}")
    frappe.db.commit()
    return n


# ───── Orchestrator ───────────────────────────────────────────────────────────

def run() -> dict:
    print("=" * 70)
    print("AssetCore — Cleanup & Seed Real Assets")
    print("=" * 70)

    cleanup = cleanup_test_assets()
    asset_names = seed_or_update_assets()
    wo_stats = seed_work_orders_per_asset(asset_names)
    le_count = seed_lifecycle_events(asset_names)
    dep_count = seed_depreciation(asset_names)

    print("\n" + "=" * 70)
    print("REPORT")
    print("=" * 70)
    print(f"Deleted assets: {len(cleanup['deleted'])}")
    for d in cleanup["deleted"]:
        print(f"  - {d}")
    print(f"Final asset set: {asset_names}")
    print(f"PM Work Orders seeded: {wo_stats['pm']}")
    print(f"CM Work Orders seeded: {wo_stats['cm']}")
    print(f"Downtime logs seeded: {wo_stats['downtime']}")
    print(f"Lifecycle events seeded: {le_count}")
    print(f"Depreciation schedules generated: {dep_count}")

    return {
        "deleted": cleanup["deleted"],
        "skipped": cleanup["skipped"],
        "assets": asset_names,
        "pm_wos": wo_stats["pm"],
        "cm_wos": wo_stats["cm"],
        "downtime_logs": wo_stats["downtime"],
        "lifecycle_events": le_count,
        "depreciation_schedules": dep_count,
    }
