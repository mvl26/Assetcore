"""HARD RESET cho các module IMM-00/04/05/08/09 — xóa dữ liệu rác (UAT/Test/Demo),
xóa orphan (link asset không tồn tại), điền các field quan trọng còn thiếu bằng
dữ liệu thực tế bệnh viện.

Phạm vi:
  • IMM-00: Asset Transfer, Service Contract, Incident Report, IMM CAPA Record
  • IMM-04: Asset Commissioning, Asset QA Non-Conformance
  • IMM-05: Asset Document, Document Request
  • IMM-08: PM Schedule, PM Work Order, PM Checklist Template
  • IMM-09: Asset Repair, Firmware Change Request

Quy tắc:
  • Xóa nếu name / text fields chứa UAT|Test|Demo|Dummy|Fake
  • Xóa nếu asset_ref / asset trỏ đến record đã bị xóa
  • Với Submitted doc bị lock → cancel trước rồi delete
  • Điền các field thiếu bằng data thực tế (mô tả VN, ngày hợp lý, actor thật)

Run: bench --site miyano execute assetcore.scripts.maintenance.hard_reset_modules.hard_reset_modules
"""
from __future__ import annotations

import random
import re

import frappe
from frappe.utils import add_days, now, nowdate


RE_JUNK = re.compile(r"\b(uat|test|demo|dummy|fake|placeholder)\b", re.IGNORECASE)


def _is_junk(*values) -> bool:
    for v in values:
        if v and RE_JUNK.search(str(v)):
            return True
    return False


def _force_delete(doctype: str, name: str) -> bool:
    """Cancel nếu submitted → delete. Fallback db.delete nếu frappe.delete_doc fail."""
    try:
        doc = frappe.get_doc(doctype, name)
        if doc.docstatus == 1:
            doc.flags.ignore_permissions = True
            doc.cancel()
        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True, ignore_missing=True)
        return True
    except Exception:
        try:
            frappe.db.set_value(doctype, name, "docstatus", 2)
            frappe.db.delete(doctype, {"name": name})
            return True
        except Exception:
            return False


def _get_valid_assets() -> set[str]:
    return set(frappe.get_all("AC Asset", pluck="name"))


# ─── 1. Scan & xóa junk/orphan trong mỗi DocType ─────────────────────────────

SCAN_CONFIG = [
    # (doctype, text_fields, asset_link_field)
    ("Asset Transfer",        ["name", "reason", "notes"],                                   "asset"),
    ("Service Contract",      ["name", "contract_title", "coverage_description", "notes"],   None),
    ("Incident Report",       ["name", "description", "immediate_action"],                   "asset"),
    ("IMM CAPA Record",       ["name"],                                                      None),
    ("Asset Commissioning",   ["name", "asset_description"],                                 "final_asset"),
    ("Asset QA Non-Conformance", ["name", "description", "resolution_notes"],                None),
    ("Asset Document",        ["name", "doc_description"],                                   "asset_ref"),
    ("Document Request",      ["name", "reason"],                                            "asset_ref"),
    ("PM Schedule",           ["name", "notes"],                                             "asset_ref"),
    ("PM Work Order",         ["name", "technician_notes", "completion_notes"],              "asset_ref"),
    ("PM Checklist Template", ["name", "template_name", "description"],                      None),
    ("Asset Repair",          ["name", "diagnosis_notes", "repair_summary", "technician_notes"], "asset_ref"),
    ("Firmware Change Request", ["name", "reason", "description"],                           "asset_ref"),
]


def _scan_and_delete_junk(valid_assets: set[str]) -> dict:
    """Trả về dict {doctype: deleted_count}."""
    deleted = {}
    for (dt, text_fields, asset_field) in SCAN_CONFIG:
        if not frappe.db.table_exists(f"tab{dt}"):
            continue
        # Lấy các field tồn tại trên DocType để tránh lỗi SQL
        meta = frappe.get_meta(dt)
        existing_fields = {f.fieldname for f in meta.fields} | {"name"}
        fetch_fields = [f for f in text_fields if f in existing_fields] or ["name"]
        if asset_field and asset_field in existing_fields:
            fetch_fields.append(asset_field)

        records = frappe.get_all(dt, fields=fetch_fields, limit=None)
        dt_deleted = 0
        for r in records:
            text_vals = [r.get(f) for f in text_fields if f in existing_fields]
            is_junk = _is_junk(*text_vals, r.get("name"))
            asset_val = r.get(asset_field) if asset_field else None
            is_orphan = bool(asset_val) and asset_val not in valid_assets
            if is_junk or is_orphan:
                reason = "junk" if is_junk else "orphan"
                if _force_delete(dt, r.name):
                    dt_deleted += 1
                    print(f"  🗑  [{reason}] {dt}/{r.name}")
        if dt_deleted:
            deleted[dt] = dt_deleted
    return deleted


# ─── 2. Điền field còn thiếu cho các DocType còn lại ─────────────────────────

def _fill_asset_transfer():
    """Điền reason, transfer_date, notes nếu thiếu."""
    reasons = [
        "Luân chuyển sang khoa khác theo kế hoạch vận hành quý",
        "Mượn cho ca phẫu thuật cấp cứu — trả trong 72h",
        "Chuyển về phòng kỹ thuật HTM để bảo dưỡng định kỳ",
        "Bàn giao sang phòng dự phòng do đổi vị trí lắp đặt",
        "Điều chuyển nội bộ theo yêu cầu của Trưởng khoa",
    ]
    recs = frappe.get_all("Asset Transfer", pluck="name")
    updated = 0
    for n in recs:
        updates = {}
        doc = frappe.db.get_value("Asset Transfer", n, ["reason","transfer_date","notes","transfer_type"], as_dict=True)
        if not doc: continue
        if not doc.reason: updates["reason"] = random.choice(reasons)
        if not doc.transfer_date: updates["transfer_date"] = nowdate()
        if not doc.transfer_type: updates["transfer_type"] = "Internal"
        if not doc.notes: updates["notes"] = "Đã xác nhận bàn giao & kiểm tra ngoại quan thiết bị."
        if updates:
            frappe.db.set_value("Asset Transfer", n, updates)
            updated += 1
    print(f"  ✅ Asset Transfer — điền {updated} record")


def _fill_service_contract():
    titles = [
        "HĐ Bảo trì PM thiết bị chẩn đoán hình ảnh 2026",
        "HĐ Hiệu chuẩn hàng năm Quatest 3 — 2026",
        "HĐ Full Service GE Healthcare khối XR-CT — 2026",
        "HĐ Sửa chữa thiết bị ICU 2025-2026",
        "HĐ Gia hạn bảo hành Philips Monitor — 2026",
    ]
    recs = frappe.get_all("Service Contract", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("Service Contract", n,
            ["contract_title","contract_start","contract_end","sla_response_hours","coverage_description","contract_value","contract_type"], as_dict=True)
        if not d: continue
        u = {}
        if not d.contract_title: u["contract_title"] = random.choice(titles)
        if not d.contract_start: u["contract_start"] = add_days(nowdate(), -90)
        if not d.contract_end: u["contract_end"] = add_days(nowdate(), 275)
        if not d.sla_response_hours: u["sla_response_hours"] = 24
        if not d.contract_value: u["contract_value"] = random.choice([80_000_000, 120_000_000, 250_000_000, 620_000_000])
        if not d.contract_type: u["contract_type"] = "Preventive Maintenance"
        if not d.coverage_description:
            u["coverage_description"] = "Bao gồm visit định kỳ, thay thế linh kiện hao mòn, support 24/7, hiệu chuẩn định kỳ."
        if u:
            frappe.db.set_value("Service Contract", n, u)
            updated += 1
    print(f"  ✅ Service Contract — điền {updated} record")


def _fill_incident_report():
    descriptions = [
        "<p>Thiết bị báo alarm giả liên tục 3 lần/giờ — đã kiểm tra lead nhưng chưa hết.</p>",
        "<p>Thiết bị ngắt đột ngột trong ca mổ, đã chuyển sang thiết bị dự phòng, không ảnh hưởng BN.</p>",
        "<p>Phát hiện output bất thường trong lần đo QA tuần — cần hiệu chuẩn khẩn.</p>",
        "<p>Lỗi firmware làm treo màn hình, đã restart và khôi phục.</p>",
    ]
    recs = frappe.get_all("Incident Report", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("Incident Report", n,
            ["description","severity","status","reported_at","reported_by","incident_type"], as_dict=True)
        if not d: continue
        u = {}
        if not d.description: u["description"] = random.choice(descriptions)
        if not d.severity: u["severity"] = random.choice(["Low","Medium","High"])
        if not d.status: u["status"] = "Open"
        if not d.reported_at: u["reported_at"] = now()
        if not d.reported_by: u["reported_by"] = "Administrator"
        if not d.incident_type: u["incident_type"] = "Malfunction"
        if u:
            frappe.db.set_value("Incident Report", n, u)
            updated += 1
    print(f"  ✅ Incident Report — điền {updated} record")


def _fill_asset_commissioning():
    """IMM-04: điền các field thường thiếu."""
    recs = frappe.get_all("Asset Commissioning", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("Asset Commissioning", n,
            ["asset_description","expected_installation_date","reception_date","vendor_serial_no"], as_dict=True)
        if not d: continue
        u = {}
        if not d.asset_description: u["asset_description"] = "Thiết bị y tế — tiếp nhận theo quy trình IMM-04"
        if not d.expected_installation_date: u["expected_installation_date"] = add_days(nowdate(), 7)
        if not d.reception_date: u["reception_date"] = nowdate()
        if not d.vendor_serial_no: u["vendor_serial_no"] = f"SN-VDR-{random.randint(100000, 999999)}"
        if u:
            frappe.db.set_value("Asset Commissioning", n, u)
            updated += 1
    print(f"  ✅ Asset Commissioning — điền {updated} record")


def _fill_pm_schedule():
    recs = frappe.get_all("PM Schedule", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("PM Schedule", n,
            ["pm_interval_days","next_due_date","status","pm_type","alert_days_before","notes"], as_dict=True)
        if not d: continue
        u = {}
        if not d.pm_interval_days: u["pm_interval_days"] = 180
        if not d.next_due_date: u["next_due_date"] = add_days(nowdate(), 30)
        if not d.status: u["status"] = "Active"
        if not d.pm_type: u["pm_type"] = "Preventive"
        if not d.alert_days_before: u["alert_days_before"] = 14
        if not d.notes: u["notes"] = "Lịch bảo trì định kỳ theo SOP PM-001 — IEC 60601."
        if u:
            frappe.db.set_value("PM Schedule", n, u)
            updated += 1
    print(f"  ✅ PM Schedule — điền {updated} record")


def _fill_pm_work_order():
    notes_samples = [
        "Đã kiểm tra vận hành, không phát hiện bất thường. Vệ sinh cơ bản hoàn tất.",
        "Thay thế bộ lọc khí đầu vào. Kiểm tra và hiệu chỉnh các thông số vận hành.",
        "Test chức năng an toàn điện theo IEC 60601. Kết quả đạt.",
        "Cập nhật firmware v2.3, kiểm tra backup pin. Tình trạng tốt.",
    ]
    recs = frappe.get_all("PM Work Order", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("PM Work Order", n,
            ["technician_notes","due_date","status","pm_type"], as_dict=True)
        if not d: continue
        u = {}
        if not d.technician_notes: u["technician_notes"] = random.choice(notes_samples)
        if not d.due_date: u["due_date"] = add_days(nowdate(), random.randint(-30, 60))
        if not d.pm_type: u["pm_type"] = "Preventive"
        if u:
            frappe.db.set_value("PM Work Order", n, u)
            updated += 1
    print(f"  ✅ PM Work Order — điền {updated} record")


def _fill_asset_repair():
    diagnosis = [
        "Phát hiện cảm biến pressure bị drift — hiệu chuẩn lại và thay thế filter.",
        "Board điều khiển bị lỗi capacitor, đã thay mới theo spec từ hãng.",
        "Kết nối dây nguồn bị lỏng gây chập chờn — thay connector + siết lại.",
        "Firmware lỗi logic — reset và nâng cấp bản mới, test lại OK.",
    ]
    summary = [
        "Sửa chữa hoàn tất, test chức năng đạt, bàn giao lại cho khoa sử dụng.",
        "Thay linh kiện + test an toàn điện. Đã hiệu chuẩn lại.",
        "Đã khắc phục triệt để, ghi nhận root cause cho báo cáo MTBF.",
    ]
    recs = frappe.get_all("Asset Repair", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("Asset Repair", n,
            ["diagnosis_notes","repair_summary","technician_notes","priority","repair_type","status","open_datetime"], as_dict=True)
        if not d: continue
        u = {}
        if not d.diagnosis_notes: u["diagnosis_notes"] = random.choice(diagnosis)
        if not d.repair_summary: u["repair_summary"] = random.choice(summary)
        if not d.technician_notes: u["technician_notes"] = "Đã thực hiện theo SOP sửa chữa CM-001."
        if not d.priority: u["priority"] = random.choice(["Normal","Urgent","Emergency"])
        if not d.repair_type: u["repair_type"] = "Corrective"
        if not d.status: u["status"] = "Open"
        if not d.open_datetime: u["open_datetime"] = now()
        if u:
            frappe.db.set_value("Asset Repair", n, u)
            updated += 1
    print(f"  ✅ Asset Repair — điền {updated} record")


def _fill_asset_document():
    recs = frappe.get_all("Asset Document", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("Asset Document", n,
            ["version","notes","doc_category","doc_type_detail","issued_date","issuing_authority"], as_dict=True)
        if not d: continue
        u = {}
        if not d.version: u["version"] = "1.0"
        if not d.notes: u["notes"] = "Tài liệu kèm thiết bị — lưu trữ theo ISO 13485."
        if not d.issued_date: u["issued_date"] = add_days(nowdate(), -60)
        if not d.issuing_authority: u["issuing_authority"] = "Nhà sản xuất"
        if u:
            frappe.db.set_value("Asset Document", n, u)
            updated += 1
    print(f"  ✅ Asset Document — điền {updated} record")


def _fill_pm_checklist_template():
    recs = frappe.get_all("PM Checklist Template", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("PM Checklist Template", n,
            ["template_name","version","pm_type","effective_date"], as_dict=True)
        if not d: continue
        u = {}
        if not d.template_name: u["template_name"] = "Mẫu checklist PM thiết bị y tế tổng quát"
        if not d.version: u["version"] = "1.0"
        if not d.pm_type: u["pm_type"] = "Preventive"
        if not d.effective_date: u["effective_date"] = nowdate()
        if u:
            frappe.db.set_value("PM Checklist Template", n, u)
            updated += 1
    print(f"  ✅ PM Checklist Template — điền {updated} record")


def _fill_calibration_schedule():
    recs = frappe.get_all("IMM Calibration Schedule", pluck="name")
    updated = 0
    for n in recs:
        d = frappe.db.get_value("IMM Calibration Schedule", n,
            ["interval_days","next_due_date","is_active","calibration_type"], as_dict=True)
        if not d: continue
        u = {}
        if not d.interval_days: u["interval_days"] = 365
        if not d.next_due_date: u["next_due_date"] = add_days(nowdate(), 60)
        if d.is_active is None: u["is_active"] = 1
        if not d.calibration_type: u["calibration_type"] = "External"
        if u:
            frappe.db.set_value("IMM Calibration Schedule", n, u)
            updated += 1
    print(f"  ✅ IMM Calibration Schedule — điền {updated} record")


# ─── Main ────────────────────────────────────────────────────────────────────

def hard_reset_modules():
    """Xóa junk/orphan + điền field còn thiếu cho IMM-00/04/05/08/09."""
    frappe.set_user("Administrator")
    print("═" * 72)
    print("HARD RESET MODULES — IMM-00/04/05/08/09")
    print("═" * 72)

    valid_assets = _get_valid_assets()
    print(f"\n[Bước 1] Quét junk/orphan (valid AC Asset = {len(valid_assets)})…")
    deleted = _scan_and_delete_junk(valid_assets)
    if deleted:
        total_deleted = sum(deleted.values())
        print(f"\n  Đã xóa tổng {total_deleted} record rác/orphan:")
        for dt, n in deleted.items():
            print(f"    • {dt}: {n}")
    else:
        print("  (Không phát hiện record rác nào)")

    print("\n[Bước 2] Điền field còn thiếu…")
    try: _fill_asset_transfer()
    except Exception as e: print(f"  ❌ Asset Transfer: {e}")
    try: _fill_service_contract()
    except Exception as e: print(f"  ❌ Service Contract: {e}")
    try: _fill_incident_report()
    except Exception as e: print(f"  ❌ Incident Report: {e}")
    try: _fill_asset_commissioning()
    except Exception as e: print(f"  ❌ Asset Commissioning: {e}")
    try: _fill_asset_document()
    except Exception as e: print(f"  ❌ Asset Document: {e}")
    try: _fill_pm_schedule()
    except Exception as e: print(f"  ❌ PM Schedule: {e}")
    try: _fill_pm_work_order()
    except Exception as e: print(f"  ❌ PM Work Order: {e}")
    try: _fill_pm_checklist_template()
    except Exception as e: print(f"  ❌ PM Checklist Template: {e}")
    try: _fill_asset_repair()
    except Exception as e: print(f"  ❌ Asset Repair: {e}")
    try: _fill_calibration_schedule()
    except Exception as e: print(f"  ❌ IMM Calibration Schedule: {e}")

    frappe.db.commit()
    print("\n" + "═" * 72)
    print("HOÀN TẤT HARD RESET MODULES")
    print("═" * 72)
