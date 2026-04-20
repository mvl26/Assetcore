"""Seed UAT data — creates 5+ realistic medical equipment records per DocType.

Covers: AC Location, AC Department, AC Asset Category, AC Supplier, IMM Device Model,
IMM SLA Policy, AC Asset, Service Contract, Asset Transfer, Incident Report, IMM CAPA Record.

Realistic Vietnamese HTM domain per docs/imm-00 and docs/res.
Run: bench --site miyano execute assetcore.tests.seed_uat.run
"""
import frappe
from frappe.utils import add_days, nowdate

_DT_LOCATION = "AC Location"
_DT_DEPT = "AC Department"
_DT_CATEGORY = "AC Asset Category"
_DT_SUPPLIER = "AC Supplier"
_DT_MODEL = "IMM Device Model"
_DT_SLA = "IMM SLA Policy"
_DT_ASSET = "AC Asset"
_DT_CONTRACT = "Service Contract"
_DT_TRANSFER = "Asset Transfer"
_DT_INCIDENT = "Incident Report"
_CLASS_II = "Class II"
_CLASS_III = "Class III"


def _upsert(doctype: str, filters: dict, data: dict) -> str:
    """Create or return existing doc by filters."""
    existing = frappe.db.exists(doctype, filters)
    if existing:
        return existing if isinstance(existing, str) else existing[0]
    doc = frappe.get_doc({"doctype": doctype, **data}).insert(ignore_permissions=True)
    return doc.name


def _seed_locations() -> list[str]:
    rows = [
        ("Phòng ICU", "Room"),
        ("Phòng X-quang 1", "Room"),
        ("Phòng mổ 3", "Room"),
        ("Kho thiết bị HTM", "Storage"),
        ("Phòng kỹ thuật", "Room"),
    ]
    names = []
    for loc_name, loc_type in rows:
        n = _upsert(_DT_LOCATION, {"location_name": loc_name},
                    {"location_name": loc_name, "location_type": loc_type, "is_active": 1})
        names.append(n)
    return names


def _seed_departments() -> list[str]:
    rows = [
        "Khoa Hồi sức tích cực (ICU)",
        "Khoa Chẩn đoán hình ảnh",
        "Khoa Gây mê hồi sức",
        "Phòng Quản lý thiết bị y tế (HTM)",
        "Khoa Sản",
    ]
    names = []
    for d in rows:
        n = _upsert(_DT_DEPT, {"department_name": d}, {"department_name": d})
        names.append(n)
    return names


def _seed_categories() -> list[str]:
    rows = [
        ("Monitor bệnh nhân", "Medium", False),
        ("Thiết bị chẩn đoán hình ảnh", "High", True),
        ("Thiết bị hỗ trợ sự sống", "High", False),
        ("Thiết bị gây mê", "High", False),
        ("Bơm tiêm / truyền dịch", "Low", False),
    ]
    names = []
    for cat_name, _risk, has_rad in rows:
        n = _upsert("AC Asset Category", {"category_name": cat_name}, {
            "category_name": cat_name,
            "default_pm_required": 1,
            "default_pm_interval_days": 180,
            "has_radiation": 1 if has_rad else 0,
            "is_active": 1,
        })
        names.append(n)
    return names


def _seed_suppliers() -> list[str]:
    rows = [
        ("Philips Healthcare Việt Nam", "Manufacturer", "Manufacturer", "VN", add_days(nowdate(), 365)),
        ("GE Medical Systems", "Manufacturer", "Manufacturer", "US", add_days(nowdate(), 180)),
        ("Mindray Vietnam", "Distributor", "Distributor", "VN", add_days(nowdate(), 60)),
        ("Biobase Calibration Lab", "Calibration Lab", "Calibration Lab", "VN", add_days(nowdate(), 90)),
        ("Metrology Services VN", "Service Provider", "Service", "VN", add_days(nowdate(), 25)),
    ]
    names = []
    for sup_name, group, vtype, country, contract_end in rows:
        n = _upsert("AC Supplier", {"supplier_name": sup_name}, {
            "supplier_name": sup_name,
            "supplier_group": group,
            "vendor_type": vtype,
            "country": country,
            "contact_email": f"sales@{sup_name.split()[0].lower()}.example",
            "contract_expiry_date": contract_end,
            "contract_end": contract_end,
            "is_active": 1,
        })
        names.append(n)
    return names


def _seed_device_models(categories: list[str]) -> list[str]:
    rows = [
        ("Philips IntelliVue MX550", "Philips Healthcare", "MX550", _CLASS_II, "37825", categories[0]),
        ("GE Optima XR220amx", "GE Healthcare", "XR220amx", _CLASS_III, "40890", categories[1]),
        ("Mindray SV300 Ventilator", "Mindray", "SV300", _CLASS_II, "36263", categories[2]),
        ("Dräger Perseus A500", "Dräger Medical", "A500", _CLASS_II, "35048", categories[3]),
        ("B.Braun Infusomat Space", "B.Braun", "Infusomat", _CLASS_II, "13287", categories[4]),
    ]
    names = []
    for model_name, mfg, mnum, dev_class, gmdn, cat in rows:
        filters = {"model_name": model_name, "manufacturer": mfg}
        data = {
            "model_name": model_name,
            "manufacturer": mfg,
            "model_number": mnum,
            "medical_device_class": dev_class,
            "gmdn_code": gmdn,
            "asset_category": cat,
            "is_pm_required": 1,
            "is_calibration_required": 1,
        }
        n = _upsert("IMM Device Model", filters, data)
        names.append(n)
    return names


def _seed_sla_policies() -> list[str]:
    rows = [
        ("SLA P1 Critical — ICU/Life-support", "P1 Critical", "Critical", 30, 4, 1),
        ("SLA P1 High — Emergency diagnostics", "P1 High", "High", 60, 8, 1),
        ("SLA P2 — Routine repair", "P2", "Medium", 240, 48, 0),
        ("SLA P3 — Non-critical", "P3", "Low", 480, 120, 0),
        ("SLA Default — Fallback", "P2", None, 360, 72, 0),
    ]
    names = []
    for pname, priority, risk, resp_min, res_hr, is_default in rows:
        # If policy with this name exists, reuse
        if frappe.db.exists(_DT_SLA, {"policy_name": pname}):
            names.append(frappe.db.get_value(_DT_SLA, {"policy_name": pname}, "name"))
            continue
        # BR-00-05: skip creation if any active policy for this priority already exists
        # (validator logic: if risk_class empty, matches any risk_class for same priority)
        conflict_filters = {"priority": priority, "is_active": 1}
        if risk:
            conflict_filters["risk_class"] = risk
        dup = frappe.db.exists(_DT_SLA, conflict_filters)
        if dup:
            names.append(dup)
            continue
        n = _upsert(_DT_SLA, {"policy_name": pname}, {
            "policy_name": pname,
            "priority": priority,
            "risk_class": risk,
            "response_time_minutes": resp_min,
            "resolution_time_hours": res_hr,
            "working_hours_only": 0,
            "is_active": 1,
            "is_default": is_default,
        })
        names.append(n)
    return names


def _seed_assets(categories: list[str], models: list[str], locations: list[str],
                 departments: list[str], suppliers: list[str]) -> list[str]:
    rows = [
        ("Monitor bệnh nhân ICU-01", "HTM-MON-001", categories[0], models[0],
         locations[0], departments[0], "Active", "Active", suppliers[0],
         "PHIL-SN-001", "UDI-(01)07612345000045", "DK-BYT-2024-001", add_days(nowdate(), 400),
         add_days(nowdate(), 720), 180, add_days(nowdate(), 25)),
        ("X-quang di động Radiology-01", "HTM-XRAY-001", categories[1], models[1],
         locations[1], departments[1], "Active", "Active", suppliers[1],
         "GE-SN-2023-7788", "UDI-(01)08012345000123", "DK-BYT-2024-012", add_days(nowdate(), 180),
         add_days(nowdate(), 365), 365, add_days(nowdate(), 120)),
        ("Máy thở OR-05", "HTM-VENT-003", categories[2], models[2],
         locations[2], departments[2], "Under Repair", "Under Repair", suppliers[2],
         "MIN-SN-SV300-045", "UDI-(01)06912345000098", "DK-BYT-2023-078", add_days(nowdate(), 280),
         add_days(nowdate(), 90), 90, add_days(nowdate(), 15)),
        ("Máy gây mê OR-03", "HTM-ANES-002", categories[3], models[3],
         locations[2], departments[2], "Active", "Calibrating", suppliers[0],
         "DRA-SN-A500-017", "UDI-(01)04012345000201", "DK-BYT-2024-033", add_days(nowdate(), 500),
         add_days(nowdate(), 550), 180, add_days(nowdate(), 60)),
        ("Bơm tiêm kho dự phòng", "HTM-PUMP-007", categories[4], models[4],
         locations[3], departments[3], "Decommissioned", "Decommissioned", suppliers[2],
         "BBR-SN-IS-0099", "UDI-(01)05712345000555", None, None, None, None, None),
    ]
    names = []
    for (aname, acode, cat, model, loc, dept, status, lc_status, supplier,
         sn, udi, byt_no, byt_exp, warranty_exp, pm_int, next_pm) in rows:
        if frappe.db.exists(_DT_ASSET, {"asset_code": acode}):
            names.append(frappe.db.get_value(_DT_ASSET, {"asset_code": acode}, "name"))
            continue
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": aname,
            "asset_code": acode,
            "asset_category": cat,
            "device_model": model,
            "location": loc,
            "department": dept,
            "status": status,
            "lifecycle_status": lc_status,
            "supplier": supplier,
            "manufacturer_sn": sn,
            "udi_code": udi,
            "byt_reg_no": byt_no,
            "byt_reg_expiry": byt_exp,
            "warranty_expiry_date": warranty_exp,
            "purchase_date": add_days(nowdate(), -365),
            "gross_purchase_amount": 150_000_000,
            "commissioning_date": add_days(nowdate(), -300),
            "is_pm_required": 1 if pm_int else 0,
            "pm_interval_days": pm_int or 0,
            "next_pm_date": next_pm,
            "insurance_policy_no": f"INS-{acode}",
            "insurer_name": "Bảo Việt Insurance",
            "insured_value": 200_000_000,
            "insurance_start_date": add_days(nowdate(), -180),
            "insurance_end_date": add_days(nowdate(), 185),
        }).insert(ignore_permissions=True)
        names.append(doc.name)
    return names


def _seed_service_contracts(suppliers: list[str], assets: list[str]) -> list[str]:
    rows = [
        ("HĐ Bảo trì PM Philips 2026", suppliers[0], "Preventive Maintenance",
         add_days(nowdate(), -90), add_days(nowdate(), 275), 120_000_000, 24, [assets[0]]),
        ("HĐ Hiệu chuẩn Biobase 2026", suppliers[3], "Calibration",
         add_days(nowdate(), -30), add_days(nowdate(), 90), 45_000_000, 48, [assets[1], assets[3]]),
        ("HĐ Sửa chữa Mindray 2026", suppliers[2], "Repair",
         add_days(nowdate(), -180), add_days(nowdate(), 185), 60_000_000, 12, [assets[2]]),
        ("HĐ Full Service GE 2026", suppliers[1], "Full Service",
         add_days(nowdate(), -60), add_days(nowdate(), 305), 250_000_000, 8, [assets[1]]),
        ("HĐ Gia hạn bảo hành Philips", suppliers[0], "Warranty Extension",
         nowdate(), add_days(nowdate(), 730), 80_000_000, 24, [assets[0], assets[3]]),
    ]
    names = []
    for (title, sup, ctype, start, end, value, sla, covered) in rows:
        if frappe.db.exists(_DT_CONTRACT, {"contract_title": title}):
            names.append(frappe.db.get_value(_DT_CONTRACT, {"contract_title": title}, "name"))
            continue
        doc = frappe.get_doc({
            "doctype": _DT_CONTRACT,
            "contract_title": title,
            "supplier": sup,
            "contract_type": ctype,
            "contract_start": start,
            "contract_end": end,
            "contract_value": value,
            "sla_response_hours": sla,
            "coverage_description": f"Phạm vi: {ctype} cho {len(covered)} thiết bị",
            "covered_assets": [{"asset": a} for a in covered],
        }).insert(ignore_permissions=True)
        names.append(doc.name)
    return names


def _seed_transfers(assets: list[str], locations: list[str], departments: list[str]) -> list[str]:
    """Create transfers that move assets between locations. Auto-submits."""
    rows = [
        (assets[0], "Internal", locations[4], departments[3], "Luân chuyển định kỳ sang phòng kỹ thuật"),
        (assets[3], "Loan", locations[2], departments[2], "Mượn cho ca mổ khẩn cấp"),
    ]
    names = []
    for (asset, ttype, to_loc, to_dept, reason) in rows:
        data = {
            "doctype": "Asset Transfer",
            "asset": asset,
            "transfer_date": nowdate(),
            "transfer_type": ttype,
            "to_location": to_loc,
            "to_department": to_dept,
            "reason": reason,
        }
        if ttype == "Loan":
            data["expected_return_date"] = add_days(nowdate(), 7)
        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        doc.submit()
        names.append(doc.name)
    return names


def _seed_incidents(assets: list[str]) -> list[str]:
    rows = [
        (assets[0], "Malfunction", "Medium", "Monitor ICU-01 báo alarm liên tục không rõ nguyên nhân",
         0, None),
        (assets[2], "Failure", "Critical",
         "Máy thở OR-05 ngắt đột ngột trong ca mổ — bệnh nhân cần hỗ trợ thủ công",
         1, "Ảnh hưởng ngắn tới bệnh nhân, chuyển sang bóp bóng AMBU, không di chứng"),
        (assets[1], "Safety Event", "High",
         "X-quang phát tia không ổn định — nghi ngờ vượt ngưỡng an toàn",
         0, None),
    ]
    names = []
    for (asset, itype, sev, desc, pat_affected, pat_impact) in rows:
        data = {
            "doctype": "Incident Report",
            "asset": asset,
            "reported_by": frappe.session.user or "Administrator",
            "reported_at": frappe.utils.now(),
            "incident_type": itype,
            "severity": sev,
            "status": "Open",
            "description": desc,
            "patient_affected": pat_affected,
            "patient_impact_description": pat_impact or "",
        }
        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        # Submit Critical incident to trigger BR-00-08 (auto-CAPA)
        if sev == "Critical":
            doc.submit()
        names.append(doc.name)
    return names


def _print_summary(totals: dict) -> None:
    print("\n" + "=" * 60)
    print("SEED SUMMARY")
    print("=" * 60)
    for dt, names in totals.items():
        print(f"  {dt:25s} {len(names):>2}  {', '.join(names[:3])}{'...' if len(names) > 3 else ''}")
    print("=" * 60)


def run():
    frappe.set_user("Administrator")
    totals = {}

    print("[1/10] AC Location…")
    totals[_DT_LOCATION] = _seed_locations()
    print("[2/10] AC Department…")
    totals[_DT_DEPT] = _seed_departments()
    print("[3/10] AC Asset Category…")
    cats = _seed_categories()
    totals["AC Asset Category"] = cats
    print("[4/10] AC Supplier…")
    suppliers = _seed_suppliers()
    totals["AC Supplier"] = suppliers
    print("[5/10] IMM Device Model…")
    models = _seed_device_models(cats)
    totals["IMM Device Model"] = models
    print("[6/10] IMM SLA Policy…")
    totals["IMM SLA Policy"] = _seed_sla_policies()
    print("[7/10] AC Asset…")
    assets = _seed_assets(cats, models, totals[_DT_LOCATION],
                          totals[_DT_DEPT], suppliers)
    totals[_DT_ASSET] = assets
    print("[8/10] Service Contract…")
    totals[_DT_CONTRACT] = _seed_service_contracts(suppliers, assets)
    print("[9/10] Asset Transfer…")
    totals["Asset Transfer"] = _seed_transfers(assets, totals[_DT_LOCATION], totals[_DT_DEPT])
    print("[10/10] Incident Report (+ auto-CAPA on Critical)…")
    totals["Incident Report"] = _seed_incidents(assets)

    # Count CAPAs auto-created
    capas = frappe.get_all("IMM CAPA Record", filters={"source_type": "Incident"}, pluck="name")
    totals["IMM CAPA Record (auto)"] = capas

    frappe.db.commit()
    _print_summary(totals)
