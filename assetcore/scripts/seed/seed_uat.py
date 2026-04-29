"""Seed UAT data — dữ liệu gần giống thật của bệnh viện Việt Nam (HTM).

Phủ: AC Location, AC Department, AC Asset Category, AC Supplier, IMM Device Model,
IMM SLA Policy, AC Asset, Service Contract, Asset Transfer, Incident Report, IMM CAPA Record.

Dữ liệu mô phỏng Bệnh viện Đa khoa Quận 2 (giả lập) — đầy đủ mọi field bắt buộc &
optional quan trọng để demo/UAT sát thực tế: địa chỉ, mã thuế, BYT, UDI, GMDN,
hạn bảo hành, bảo hiểm, khấu hao, lịch PM/Calibration, chứng chỉ ISO lab.

Run: bench --site miyano execute assetcore.scripts.seed.seed_uat.run
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

_CLASS_I = "Class I"
_CLASS_II = "Class II"
_CLASS_III = "Class III"


def _upsert(doctype: str, filters: dict, data: dict) -> str:
    """Tạo mới hoặc trả về doc đã tồn tại theo filter."""
    existing = frappe.db.exists(doctype, filters)
    if existing:
        return existing if isinstance(existing, str) else existing[0]
    doc = frappe.get_doc({"doctype": doctype, **data}).insert(ignore_permissions=True)
    return doc.name


# ─── 1. Locations ────────────────────────────────────────────────────────────
# Phòng/khu vực thực tế trong 1 BV đa khoa hạng II

def _seed_locations() -> list[str]:
    rows = [
        # (name, code, clinical_area, infection_level, has_backup, contact, notes)
        ("Phòng ICU 2.05 — Tầng 2",        "LOC-ICU-205",  "ICU",           "Enhanced",  1, "02862785205",
         "Khu hồi sức tích cực nội khoa, 12 giường, trực 24/7"),
        ("Phòng mổ OR-1 — Khoa Ngoại",     "LOC-OR-1",     "OR",            "Enhanced",  1, "02862785301",
         "Phòng mổ chính phẫu thuật đa khoa, khử khuẩn cấp II"),
        ("Phòng X-quang KCDHA-01",          "LOC-XR-01",    "Imaging",       "Standard",  1, "02862785410",
         "Phòng chụp X-quang tổng quát có chắn chì"),
        ("Phòng CT Scanner KCDHA-02",       "LOC-CT-02",    "Imaging",       "Standard",  1, "02862785411",
         "Phòng CT 64 lát, kiểm soát bức xạ theo Thông tư 19/2012"),
        ("Phòng Xét nghiệm Sinh hóa LAB-3", "LOC-LAB-03",   "Lab",           "Standard",  0, "02862785520",
         "Phòng sinh hóa - huyết học, ISO 15189"),
        ("Phòng Sản Hậu sản 3B.04",         "LOC-OBS-304",  "General Ward",  "Enhanced",  1, "02862785610",
         "Khu hậu sản, 8 giường, có incubator"),
        ("Phòng Siêu âm Sản Khoa",          "LOC-US-01",    "Imaging",       "Standard",  0, "02862785612",
         "Phòng siêu âm khoa Sản"),
        ("Phòng Hồi tỉnh 2.07",             "LOC-REC-207",  "General Ward",  "Enhanced",  1, "02862785206",
         "Khu hồi tỉnh sau mổ, 6 giường monitor"),
        ("Kho Thiết bị HTM tầng hầm",       "LOC-WH-B1",    "Storage",       "Standard",  0, "02862785901",
         "Kho dự phòng thiết bị y tế, điều hòa nhiệt ẩm"),
        ("Phòng Kỹ thuật HTM",              "LOC-WS-101",   "Office",        "Standard",  0, "02862785910",
         "Văn phòng + workshop của Phòng Quản lý Thiết bị Y tế"),
    ]
    names = []
    for (lname, code, ctype, lvl, backup, contact, notes) in rows:
        n = _upsert(_DT_LOCATION, {"location_name": lname}, {
            "location_name": lname,
            "location_code": code,
            "clinical_area_type": ctype,
            "infection_control_level": lvl,
            "power_backup_available": backup,
            "emergency_contact": contact,
            "notes": notes,
            "is_group": 0,
        })
        names.append(n)
    return names


# ─── 2. Departments ──────────────────────────────────────────────────────────

def _seed_departments() -> list[str]:
    rows = [
        # (name, code, phone, email)
        ("Khoa Hồi sức tích cực (ICU)",        "DEPT-ICU",  "02862785200", "icu@bvq2.local"),
        ("Khoa Chẩn đoán hình ảnh (KCDHA)",    "DEPT-DI",   "02862785400", "kcdha@bvq2.local"),
        ("Khoa Gây mê Hồi sức",                "DEPT-ANE",  "02862785300", "gmhs@bvq2.local"),
        ("Khoa Ngoại Tổng quát",               "DEPT-SUR",  "02862785350", "ngoai@bvq2.local"),
        ("Khoa Sản",                           "DEPT-OBS",  "02862785600", "san@bvq2.local"),
        ("Khoa Xét nghiệm",                    "DEPT-LAB",  "02862785500", "lab@bvq2.local"),
        ("Khoa Nội Tim mạch",                  "DEPT-CAR",  "02862785100", "timmach@bvq2.local"),
        ("Phòng Quản lý Thiết bị Y tế (HTM)",  "DEPT-HTM",  "02862785900", "htm@bvq2.local"),
    ]
    names = []
    for (d, code, phone, email) in rows:
        n = _upsert(_DT_DEPT, {"department_name": d}, {
            "department_name": d,
            "department_code": code,
            "phone": phone,
            "email": email,
            "is_active": 1,
            "is_group": 0,
        })
        names.append(n)
    return names


# ─── 3. Asset Categories ─────────────────────────────────────────────────────

def _seed_categories() -> list[str]:
    rows = [
        # (name, pm_days, cal_required, cal_days, has_radiation, description)
        ("Monitor bệnh nhân",               180, 1, 365, 0,
         "Máy theo dõi bệnh nhân (ECG, SpO2, NIBP, Temp)"),
        ("Thiết bị chẩn đoán hình ảnh",     365, 1, 365, 1,
         "X-quang, CT, MRI, siêu âm, C-arm — yêu cầu QC/QA bức xạ"),
        ("Thiết bị hỗ trợ sự sống",         90,  1, 180, 0,
         "Máy thở, ECMO, IABP — thiết bị cứu sinh"),
        ("Thiết bị gây mê",                 180, 1, 180, 0,
         "Máy gây mê, vaporizer — yêu cầu hiệu chuẩn flow/pressure"),
        ("Bơm tiêm / truyền dịch",          365, 1, 365, 0,
         "Syringe pump, infusion pump — hiệu chuẩn flow rate"),
        ("Thiết bị xét nghiệm",             180, 1, 365, 0,
         "Máy sinh hóa, huyết học — ISO 15189"),
        ("Máy siêu âm",                     365, 1, 365, 0,
         "Siêu âm chẩn đoán Doppler 2D/3D/4D"),
    ]
    names = []
    for (cat_name, pm_days, cal_req, cal_days, has_rad, desc) in rows:
        n = _upsert(_DT_CATEGORY, {"category_name": cat_name}, {
            "category_name": cat_name,
            "description": desc,
            "default_pm_required": 1,
            "default_pm_interval_days": pm_days,
            "default_calibration_required": cal_req,
            "default_calibration_interval_days": cal_days,
            "has_radiation": has_rad,
            "is_active": 1,
        })
        names.append(n)
    return names


# ─── 4. Suppliers ────────────────────────────────────────────────────────────

def _seed_suppliers() -> list[str]:
    rows = [
        # (name, group, vtype, country, tax_id, website, address, phone, mobile, email,
        #  local_rep, iso17025, iso17025_exp, iso13485, iso13485_exp, contract_end)
        ("Philips Healthcare Việt Nam", "Manufacturer", "Manufacturer", "Việt Nam",
         "0301234567", "www.philips.com.vn",
         "Tầng 12, Saigon Trade Center, 37 Tôn Đức Thắng, Q.1, TP.HCM", "02838278888", "0908123456",
         "service.vn@philips.com", "Nguyễn Văn Tùng (Country Service Mgr)",
         None, None, "ISO13485-PHI-2024", add_days(nowdate(), 365),
         add_days(nowdate(), 730)),

        ("GE HealthCare Việt Nam", "Manufacturer", "Manufacturer", "Việt Nam",
         "0302345678", "www.gehealthcare.com.vn",
         "Tầng 14, Vincom Center Đồng Khởi, 72 Lê Thánh Tôn, Q.1, TP.HCM", "02839110080", "0903456789",
         "service-vn@gehealthcare.com", "Trần Minh Khôi (Clinical Service Lead)",
         None, None, "ISO13485-GE-2024", add_days(nowdate(), 180),
         add_days(nowdate(), 400)),

        ("Mindray Medical Việt Nam", "Distributor", "Distributor", "Việt Nam",
         "0303456789", "www.mindray.com/vn",
         "Lầu 5, Tòa nhà Bitexco Nam Long, 63A Võ Văn Tần, Q.3, TP.HCM", "02839309888", "0909876543",
         "support.vn@mindray.com", "Lê Thị Bích Ngọc (Service Manager)",
         None, None, "ISO13485-MIN-2023", add_days(nowdate(), 60),
         add_days(nowdate(), 185)),

        ("Công ty TNHH TBYT An Khánh", "Distributor", "Distributor", "Việt Nam",
         "0304567890", "www.ankhanh-medical.vn",
         "168 Nguyễn Đình Chiểu, P.6, Q.3, TP.HCM", "02839301234", "0912345678",
         "info@ankhanh-medical.vn", "Phạm Đức Thành (GĐ Kinh doanh)",
         None, None, "ISO13485-AK-2025", add_days(nowdate(), 540),
         add_days(nowdate(), 365)),

        ("Trung tâm Hiệu chuẩn Quatest 3", "Calibration Lab", "Calibration Lab", "Việt Nam",
         "0305678901", "www.quatest3.com.vn",
         "49 Pasteur, P. Bến Nghé, Q.1, TP.HCM", "02838293273", "0913579246",
         "quatest3@quatest3.com.vn", "TS. Nguyễn Thị Lan (Trưởng PTN)",
         "VILAS-042/QUATEST3", add_days(nowdate(), 400),
         None, None,
         add_days(nowdate(), 300)),

        ("Biobase Calibration Lab VN", "Calibration Lab", "Calibration Lab", "Việt Nam",
         "0306789012", "www.biobase-calibration.vn",
         "Lô B-12, KCN Tân Bình, Q. Tân Phú, TP.HCM", "02838123456", "0914567890",
         "cal@biobase.vn", "KS. Trần Hoàng Nam (Technical Lead)",
         "VILAS-128/BIOBASE", add_days(nowdate(), 90),
         None, None,
         add_days(nowdate(), 200)),

        ("Metrology Services Việt Nam", "Service Provider", "Service", "Việt Nam",
         "0307890123", "www.metrology-vn.com.vn",
         "285/94 Cách Mạng Tháng 8, P.12, Q.10, TP.HCM", "02838621789", "0915678901",
         "support@metrology-vn.com.vn", "Đặng Quốc Việt (Field Service)",
         None, None, None, None,
         add_days(nowdate(), 25)),
    ]
    names = []
    for (sname, grp, vtype, country, tax, site, addr, phone, mobile, email,
         rep, iso17, iso17_exp, iso13, iso13_exp, contract_end) in rows:
        n = _upsert(_DT_SUPPLIER, {"supplier_name": sname}, {
            "supplier_name": sname,
            "supplier_group": grp,
            "vendor_type": vtype,
            "country": country,
            "tax_id": tax,
            "website": site,
            "address": addr,
            "phone": phone,
            "mobile_no": mobile,
            "email_id": email,
            "support_hotline": phone,
            "technical_email": email,
            "local_representative": rep,
            "iso_17025_cert": iso17,
            "iso_17025_expiry": iso17_exp,
            "iso_13485_cert": iso13,
            "iso_13485_expiry": iso13_exp,
            "contract_start": add_days(nowdate(), -180),
            "contract_end": contract_end,
            "contract_value": 100_000_000,
            "is_active": 1,
        })
        names.append(n)
    return names


# ─── 5. Device Models ────────────────────────────────────────────────────────

def _seed_device_models(categories: list[str]) -> list[str]:
    # categories: 0=Monitor, 1=Imaging, 2=LifeSupport, 3=Anesthesia, 4=Pump, 5=Lab, 6=Ultrasound
    rows = [
        # (name, mfg, version, country, power, lifespan, class, risk, gmdn, emdn,
        #  is_rad, pm_days, pm_alert, is_cal, cal_days, cal_alert, cat_idx)
        ("Philips IntelliVue MX550", "Philips Healthcare", "MX550 Rev.B", "Đức", "100-240VAC, 50-60Hz", 8,
         _CLASS_II, "Medium", "37825", "Z12030101", 0, 180, 14, 1, 365, 30, 0),
        ("GE Optima XR220amx",       "GE HealthCare",       "XR220amx v3.2", "Hoa Kỳ", "220VAC, 50Hz", 10,
         _CLASS_III, "High", "40890", "Z11040801", 1, 180, 14, 1, 365, 30, 1),
        ("Mindray SV300 Ventilator", "Mindray",             "SV300 v2.1", "Trung Quốc", "100-240VAC", 7,
         _CLASS_II, "Critical", "36263", "R0301010101", 0, 90, 7, 1, 180, 15, 2),
        ("Dräger Perseus A500",      "Dräger Medical",      "A500 SW 1.5", "Đức", "100-240VAC", 10,
         _CLASS_II, "High", "35048", "R0303010101", 0, 180, 14, 1, 180, 15, 3),
        ("B.Braun Infusomat Space",  "B.Braun",             "Space P 1.3", "Đức", "100-240VAC / Pin Li-Ion", 7,
         _CLASS_II, "Medium", "13287", "Z120601", 0, 365, 30, 1, 365, 30, 4),
        ("Roche Cobas c311",         "Roche Diagnostics",   "c311 sys 2024", "Thụy Sĩ", "220VAC, 50Hz", 8,
         _CLASS_I, "Low", "40568", "W0105", 0, 180, 14, 1, 365, 30, 5),
        ("Mindray DC-70 Ultrasound", "Mindray",             "DC-70 X-Insight", "Trung Quốc", "100-240VAC", 8,
         _CLASS_II, "Low", "40231", "Z110305", 0, 365, 30, 1, 365, 30, 6),
        ("GE LOGIQ P9 Ultrasound",   "GE HealthCare",       "LOGIQ P9 R3", "Hoa Kỳ", "220VAC", 10,
         _CLASS_II, "Low", "41211", "Z110305", 0, 365, 30, 1, 365, 30, 6),
    ]
    names = []
    for (mname, mfg, ver, country, power, lifespan, cls, risk, gmdn, emdn,
         is_rad, pm_d, pm_alt, is_cal, cal_d, cal_alt, cat_i) in rows:
        n = _upsert(_DT_MODEL, {"model_name": mname, "manufacturer": mfg}, {
            "model_name": mname,
            "manufacturer": mfg,
            "model_version": ver,
            "country_of_origin": country,
            "power_supply": power,
            "expected_lifespan_years": lifespan,
            "medical_device_class": cls,
            "risk_classification": risk,
            "gmdn_code": gmdn,
            "emdn_code": emdn,
            "registration_required": 1,
            "is_radiation_device": is_rad,
            "asset_category": categories[cat_i],
            "is_pm_required": 1,
            "pm_interval_days": pm_d,
            "pm_alert_days": pm_alt,
            "is_calibration_required": is_cal,
            "calibration_interval_days": cal_d,
            "calibration_alert_days": cal_alt,
            "default_calibration_type": "External",
            "notes": f"{mname} — dùng trong dịch vụ y tế thường quy",
        })
        names.append(n)
    return names


# ─── 6. SLA Policies ─────────────────────────────────────────────────────────

def _seed_sla_policies() -> list[str]:
    rows = [
        ("SLA P1 Critical — ICU/Life-support", "P1 Critical", "Critical", 30, 4, 1),
        ("SLA P1 High — Emergency diagnostics", "P1 High", "High", 60, 8, 1),
        ("SLA P2 — Routine repair",             "P2", "Medium", 240, 48, 0),
        ("SLA P3 — Non-critical",               "P3", "Low", 480, 120, 0),
        ("SLA Default — Fallback",              "P2", None, 360, 72, 0),
    ]
    names = []
    for (pname, priority, risk, resp_min, res_hr, is_default) in rows:
        if frappe.db.exists(_DT_SLA, {"policy_name": pname}):
            names.append(frappe.db.get_value(_DT_SLA, {"policy_name": pname}, "name"))
            continue
        conflict = {"priority": priority, "is_active": 1}
        if risk: conflict["risk_class"] = risk
        dup = frappe.db.exists(_DT_SLA, conflict)
        if dup:
            names.append(dup)
            continue
        n = _upsert(_DT_SLA, {"policy_name": pname}, {
            "policy_name": pname,
            "priority": priority,
            "risk_class": risk,
            "response_time_minutes": resp_min,
            "resolution_time_hours": res_hr,
            "is_active": 1,
            "is_default": is_default,
        })
        names.append(n)
    return names


# ─── 7. Assets — thiết bị đầy đủ field ──────────────────────────────────────

def _seed_assets(categories, models, locations, departments, suppliers) -> list[str]:
    # Mapping: categories[0]=Monitor, [1]=Imaging, [2]=LifeSupport, [3]=Anesthesia, [4]=Pump, [5]=Lab, [6]=US
    # locations: 0=ICU, 1=OR, 2=XR, 3=CT, 4=LAB, 5=OBS, 6=US, 7=REC, 8=WH, 9=WS
    # depts: 0=ICU, 1=KCDHA, 2=GMHS, 3=SUR, 4=OBS, 5=LAB, 6=CAR, 7=HTM
    # models: 0=Philips MX550, 1=GE Optima XR, 2=Mindray SV300, 3=Dräger A500,
    #         4=B.Braun IS, 5=Roche c311, 6=Mindray DC-70, 7=GE LOGIQ P9
    # suppliers: 0=Philips, 1=GE, 2=Mindray, 3=AnKhanh, 4=Quatest3, 5=Biobase, 6=MetroVN

    rows = [
        # (asset_name, asset_code, cat_i, model_i, loc_i, dept_i, status, lifecycle,
        #  sup_i, sn, udi, byt_no, byt_exp_off, warranty_off, pm_days, cal_days,
        #  last_pm_off, last_cal_off, next_pm_off, next_cal_off, purchase_off,
        #  price, in_service_off, useful_years, residual, tech_user,
        #  calib_status, medical_class, risk)
        ("Monitor BN ICU-01 (Philips MX550)",  "HTM-MON-2024-001", 0, 0, 0, 0, "Active", "Active",
         0, "PHIL-MX550-SN-2024-0011", "(01)07612345000045(17)260131(10)LOT20240311",
         "DK-BYT-2024-MON-001", 400, 720, 180, 365, -90, -60, 90, 305, -365,
         185_000_000, -300, 8, 18_500_000, "Administrator",
         "On Schedule", _CLASS_II, "Medium"),

        ("Monitor BN ICU-02 (Philips MX550)",  "HTM-MON-2024-002", 0, 0, 0, 0, "Active", "Active",
         0, "PHIL-MX550-SN-2024-0012", "(01)07612345000045(17)260131(10)LOT20240311",
         "DK-BYT-2024-MON-001", 400, 720, 180, 365, -85, -60, 95, 305, -365,
         185_000_000, -300, 8, 18_500_000, "Administrator",
         "On Schedule", _CLASS_II, "Medium"),

        ("X-quang DI động Radiology-01 (GE Optima)", "HTM-XRAY-2023-001", 1, 1, 2, 1, "Active", "Active",
         1, "GE-XR220-SN-2023-7788", "(01)08012345000123(17)270715(10)SN77882023",
         "DK-BYT-2023-XR-012", 180, 365, 365, 365, -120, -90, 245, 275, -730,
         2_850_000_000, -700, 10, 285_000_000, "Administrator",
         "On Schedule", _CLASS_III, "High"),

        ("CT Scanner 64-lát KCDHA", "HTM-CT-2022-001", 1, 1, 3, 1, "Active", "Active",
         1, "GE-CT64-SN-2022-0042", "(01)08012345000124(17)280215(10)CT64-2022",
         "DK-BYT-2022-CT-005", 730, 1095, 365, 365, -200, -90, 165, 275, -1200,
         12_500_000_000, -1100, 12, 1_250_000_000, "Administrator",
         "On Schedule", _CLASS_III, "High"),

        ("Máy thở OR-05 (Mindray SV300)",     "HTM-VENT-2023-003", 2, 2, 1, 2, "Under Repair", "Under Repair",
         2, "MIN-SV300-SN-2023-045", "(01)06912345000098(17)270930(10)SV30045",
         "DK-BYT-2023-VENT-078", 280, 90, 90, 180, -45, -30, 45, 150, -700,
         425_000_000, -680, 7, 42_500_000, "Administrator",
         "On Schedule", _CLASS_II, "Critical"),

        ("Máy gây mê OR-03 (Dräger A500)",    "HTM-ANES-2024-002", 3, 3, 1, 2, "Active", "Calibrating",
         0, "DRA-A500-SN-2024-0017", "(01)04012345000201(17)280430(10)A500-17",
         "DK-BYT-2024-ANES-033", 500, 550, 180, 180, -60, -15, 120, 165, -500,
         1_650_000_000, -480, 10, 165_000_000, "Administrator",
         "On Schedule", _CLASS_II, "High"),

        ("Bơm tiêm OBS-Post-04 (B.Braun)",    "HTM-PUMP-2024-007", 4, 4, 5, 4, "Active", "Active",
         3, "BBR-IS-SN-2024-0099", "(01)05712345000555(17)290101(10)IS099-24",
         "DK-BYT-2024-PUMP-007", 600, 730, 365, 365, -30, -120, 335, 245, -400,
         38_000_000, -380, 7, 3_800_000, "Administrator",
         "On Schedule", _CLASS_II, "Medium"),

        ("Bơm tiêm ICU-02 (B.Braun)",         "HTM-PUMP-2024-008", 4, 4, 0, 0, "Active", "Active",
         3, "BBR-IS-SN-2024-0100", "(01)05712345000555(17)290101(10)IS100-24",
         "DK-BYT-2024-PUMP-007", 600, 730, 365, 365, -360, -120, 5, 245, -400,
         38_000_000, -380, 7, 3_800_000, "Administrator",
         "Due Soon", _CLASS_II, "Medium"),

        ("Máy sinh hóa Roche c311 LAB-3",     "HTM-LAB-2022-001",  5, 5, 4, 5, "Active", "Active",
         3, "ROC-C311-SN-2022-015", "(01)07895123400001(17)270801(10)C311-22",
         "DK-BYT-2022-LAB-015", 365, 180, 180, 365, -45, -80, 135, 285, -900,
         3_200_000_000, -850, 8, 320_000_000, "Administrator",
         "On Schedule", _CLASS_I, "Low"),

        ("Siêu âm Sản Mindray DC-70",         "HTM-US-2024-001",   6, 6, 6, 4, "Active", "Active",
         2, "MIN-DC70-SN-2024-0208", "(01)06923456780001(17)291130(10)DC70-208",
         "DK-BYT-2024-US-201", 730, 730, 365, 365, -15, -15, 350, 350, -180,
         580_000_000, -160, 8, 58_000_000, "Administrator",
         "On Schedule", _CLASS_II, "Low"),

        ("Monitor BN Hồi tỉnh (Philips MX550)", "HTM-MON-2023-005", 0, 0, 7, 2, "Out of Service", "Out of Service",
         0, "PHIL-MX550-SN-2023-0005", "(01)07612345000045(17)260131(10)LOT20230305",
         "DK-BYT-2023-MON-005", 300, 500, 180, 365, -220, -200, -40, 165, -800,
         175_000_000, -780, 8, 17_500_000, "Administrator",
         "Overdue", _CLASS_II, "Medium"),

        ("Bơm tiêm kho dự phòng",             "HTM-PUMP-2020-012", 4, 4, 8, 7, "Decommissioned", "Decommissioned",
         3, "BBR-IS-SN-2020-0012", "(01)05712345000555(17)230101(10)IS012-20",
         "DK-BYT-2020-PUMP-012", -30, -400, 365, 365, -500, -500, None, None, -1800,
         32_000_000, -1760, 5, 1_600_000, "Administrator",
         "Not Required", _CLASS_II, "Low"),
    ]

    names = []
    for row in rows:
        (aname, acode, cat_i, model_i, loc_i, dept_i, status, lc,
         sup_i, sn, udi, byt_no, byt_exp, war_off, pm_days, cal_days,
         last_pm, last_cal, next_pm, next_cal, purchase_off,
         price, in_serv, life, residual, tech,
         cal_status, med_class, risk) = row

        if frappe.db.exists(_DT_ASSET, {"asset_code": acode}):
            names.append(frappe.db.get_value(_DT_ASSET, {"asset_code": acode}, "name"))
            continue

        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": aname,
            "asset_code": acode,
            "item_code": acode.replace("HTM-", "ITM-"),
            "asset_category": categories[cat_i],
            "device_model": models[model_i],
            "location": locations[loc_i],
            "department": departments[dept_i],
            "responsible_technician": tech,
            "custodian": tech,
            "status": status,
            "lifecycle_status": lc,
            "supplier": suppliers[sup_i],
            # HTM / Pháp lý
            "manufacturer_sn": sn,
            "udi_code": udi,
            "gmdn_code": frappe.db.get_value(_DT_MODEL, models[model_i], "gmdn_code"),
            "byt_reg_no": byt_no,
            "byt_reg_expiry": add_days(nowdate(), byt_exp),
            "medical_device_class": med_class,
            "risk_classification": risk,
            # Mua sắm / bảo hành
            "purchase_date": add_days(nowdate(), purchase_off),
            "gross_purchase_amount": price,
            "warranty_expiry_date": add_days(nowdate(), war_off),
            "commissioning_date": add_days(nowdate(), in_serv),
            "commissioning_ref": f"ACC-{acode[-3:]}-{abs(purchase_off)}",
            # Khấu hao
            "depreciation_method": "Straight Line",
            "useful_life_years": life,
            "in_service_date": add_days(nowdate(), in_serv),
            "residual_value": residual,
            # PM
            "is_pm_required": 1 if pm_days else 0,
            "pm_interval_days": pm_days or 0,
            "last_pm_date": add_days(nowdate(), last_pm) if last_pm is not None else None,
            "next_pm_date": add_days(nowdate(), next_pm) if next_pm is not None else None,
            # Calibration
            "is_calibration_required": 1 if cal_days else 0,
            "calibration_interval_days": cal_days or 0,
            "last_calibration_date": add_days(nowdate(), last_cal) if last_cal is not None else None,
            "next_calibration_date": add_days(nowdate(), next_cal) if next_cal is not None else None,
            "calibration_status": cal_status,
            # Bảo hiểm
            "insurance_policy_no": f"BVINS-2024-{acode[-3:]}",
            "insurer_name": "Tổng Công ty Bảo hiểm Bảo Việt — CN TP.HCM",
            "insured_value": int(price * 1.1),
            "insurance_start_date": add_days(nowdate(), -180),
            "insurance_end_date": add_days(nowdate(), 185),
            "notes": f"<p>Thiết bị {aname} — bàn giao {add_days(nowdate(), in_serv)}.</p>"
                     f"<p>Số serial {sn}. Model {models[model_i]}.</p>",
        }).insert(ignore_permissions=True)
        names.append(doc.name)
    return names


# ─── 8. Service Contracts ────────────────────────────────────────────────────

def _seed_service_contracts(suppliers, assets) -> list[str]:
    rows = [
        ("HĐ-2026/PM-001 — Bảo trì PM Philips Monitor ICU", suppliers[0], "Preventive Maintenance",
         -90, 275, 180_000_000, 24, [assets[0], assets[1], assets[10]]),
        ("HĐ-2026/CAL-002 — Hiệu chuẩn Quatest3 năm 2026", suppliers[4], "Calibration",
         -30, 335, 85_000_000, 72, [assets[2], assets[3], assets[8]]),
        ("HĐ-2025/FS-003 — Full Service GE XR & CT",       suppliers[1], "Full Service",
         -60, 305, 620_000_000, 8, [assets[2], assets[3]]),
        ("HĐ-2026/REP-004 — Sửa chữa Mindray Ventilator",  suppliers[2], "Repair",
         -180, 185, 95_000_000, 12, [assets[4], assets[9]]),
        ("HĐ-2026/EXT-005 — Gia hạn bảo hành Philips",     suppliers[0], "Warranty Extension",
         0, 730, 120_000_000, 24, [assets[0], assets[1], assets[5]]),
    ]
    names = []
    for (title, sup, ctype, start_off, end_off, value, sla, covered) in rows:
        if frappe.db.exists(_DT_CONTRACT, {"contract_title": title}):
            names.append(frappe.db.get_value(_DT_CONTRACT, {"contract_title": title}, "name"))
            continue
        doc = frappe.get_doc({
            "doctype": _DT_CONTRACT,
            "contract_title": title,
            "supplier": sup,
            "contract_type": ctype,
            "contract_start": add_days(nowdate(), start_off),
            "contract_end": add_days(nowdate(), end_off),
            "contract_value": value,
            "sla_response_hours": sla,
            "coverage_description": f"Phạm vi: {ctype} cho {len(covered)} thiết bị — "
                                    f"bao gồm visit định kỳ, thay thế linh kiện hao mòn, "
                                    f"support kỹ thuật 24/7.",
            "covered_assets": [{"asset": a} for a in covered],
        }).insert(ignore_permissions=True)
        names.append(doc.name)
    return names


# ─── 9. Asset Transfers ──────────────────────────────────────────────────────

def _seed_transfers(assets, locations, departments) -> list[str]:
    rows = [
        (assets[7], "Internal", locations[9], departments[7],
         "Luân chuyển về phòng kỹ thuật HTM để bảo dưỡng định kỳ quý 2/2026"),
        (assets[5], "Loan", locations[1], departments[2],
         "Mượn máy gây mê cho ca mổ khẩn cấp tối 20/04/2026 — trả trong 72h"),
    ]
    names = []
    for (asset, ttype, to_loc, to_dept, reason) in rows:
        data = {
            "doctype": _DT_TRANSFER,
            "asset": asset,
            "transfer_date": nowdate(),
            "transfer_type": ttype,
            "to_location": to_loc,
            "to_department": to_dept,
            "reason": reason,
        }
        if ttype == "Loan":
            data["expected_return_date"] = add_days(nowdate(), 3)
        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        doc.submit()
        names.append(doc.name)
    return names


# ─── 10. Incident Reports (auto-CAPA cho Critical) ───────────────────────────

def _seed_incidents(assets) -> list[str]:
    rows = [
        (assets[0], "Malfunction", "Medium",
         "<p>Monitor BN ICU-01 báo alarm giả (false alarm) liên tục 3 lần/giờ, "
         "không rõ nguyên nhân. Đã thay lead ECG và kiểm tra cable — vẫn còn.</p>"
         "<p>Điều dưỡng trực đã chuyển sang monitor dự phòng.</p>",
         0, None),
        (assets[4], "Failure", "Critical",
         "<p><strong>MÁY THỞ OR-05 NGẮT ĐỘT NGỘT</strong> trong ca mổ cấp cứu lúc 14:35 ngày 19/04/2026.</p>"
         "<p>Bệnh nhân (nam, 58t, mổ ruột thừa) được chuyển sang bóp bóng AMBU trong 4 phút, "
         "sau đó sử dụng máy thở dự phòng SV300 từ OR-06.</p>"
         "<p>Máy báo lỗi 'Air Supply Fault' trước khi ngắt. Đã bảo quản nguyên trạng "
         "để KTV HTM điều tra sáng 20/04.</p>",
         1, "Ảnh hưởng ngắn đến bệnh nhân, SpO2 giảm từ 98% xuống 92% trong 45 giây, "
            "không có di chứng sau mổ. Kip phẫu thuật phản ứng kịp thời."),
        (assets[2], "Safety Event", "High",
         "<p>X-quang DI động Radiology-01 phát hiện liều bức xạ đầu ra cao hơn calibration 12% "
         "trong lần đo QA tuần 16/2026 (kỹ thuật viên KCDHA phát hiện).</p>"
         "<p>Đã ngừng sử dụng chờ hiệu chuẩn khẩn. Có thể đã chụp ~40 ca trong 7 ngày qua "
         "với liều cao hơn dự kiến — cần đánh giá lookback.</p>",
         0, None),
    ]
    names = []
    for (asset, itype, sev, desc, pat_aff, pat_imp) in rows:
        is_critical = sev == "Critical"
        doc = frappe.get_doc({
            "doctype": _DT_INCIDENT,
            "asset": asset,
            "reported_by": frappe.session.user or "Administrator",
            "reported_at": frappe.utils.now(),
            "incident_type": itype,
            "severity": sev,
            "status": "Open",
            "description": desc,
            "patient_affected": pat_aff,
            "patient_impact_description": pat_imp or "",
            # BR-INC-01: Critical phải báo cáo BYT theo NĐ98
            "reported_to_byt": 1 if is_critical else 0,
            "byt_report_date": nowdate() if is_critical else None,
        }).insert(ignore_permissions=True)
        if is_critical:
            doc.submit()
        names.append(doc.name)
    return names


# ─── Summary & Runner ────────────────────────────────────────────────────────

def _print_summary(totals: dict) -> None:
    print("\n" + "=" * 70)
    print("UAT SEED — BỆNH VIỆN ĐA KHOA QUẬN 2 (giả lập)")
    print("=" * 70)
    for dt, names in totals.items():
        print(f"  {dt:32s} {len(names):>2}  {', '.join(names[:3])}{'...' if len(names) > 3 else ''}")
    print("=" * 70)


def run():
    frappe.set_user("Administrator")
    totals = {}

    print("[1/10] AC Location…")
    totals[_DT_LOCATION] = _seed_locations()
    print("[2/10] AC Department…")
    totals[_DT_DEPT] = _seed_departments()
    print("[3/10] AC Asset Category…")
    cats = _seed_categories()
    totals[_DT_CATEGORY] = cats
    print("[4/10] AC Supplier…")
    suppliers = _seed_suppliers()
    totals[_DT_SUPPLIER] = suppliers
    print("[5/10] IMM Device Model…")
    models = _seed_device_models(cats)
    totals[_DT_MODEL] = models
    print("[6/10] IMM SLA Policy…")
    totals[_DT_SLA] = _seed_sla_policies()
    print("[7/10] AC Asset (full fields)…")
    assets = _seed_assets(cats, models, totals[_DT_LOCATION],
                          totals[_DT_DEPT], suppliers)
    totals[_DT_ASSET] = assets
    print("[8/10] Service Contract…")
    totals[_DT_CONTRACT] = _seed_service_contracts(suppliers, assets)
    print("[9/10] Asset Transfer…")
    totals[_DT_TRANSFER] = _seed_transfers(assets, totals[_DT_LOCATION], totals[_DT_DEPT])
    print("[10/10] Incident Report (+ auto-CAPA on Critical)…")
    totals[_DT_INCIDENT] = _seed_incidents(assets)

    capas = frappe.get_all("IMM CAPA Record", filters={"source_type": "Incident"}, pluck="name")
    totals["IMM CAPA Record (auto)"] = capas

    frappe.db.commit()
    _print_summary(totals)
