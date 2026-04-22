"""Data patch script — biến dữ liệu UAT rác thành dữ liệu bệnh viện VN thực tế.

Quét toàn bộ AC Asset + DocType liên quan đang có trên hệ thống (bất kể trạng thái),
điền thông tin hợp lý theo ngữ cảnh bệnh viện (Khoa, Model, Hãng, Serial, BYT, UDI,
GMDN, bảo hành, khấu hao, PM/Calibration, bảo hiểm…) sao cho KHÔNG còn field quan
trọng nào bị để trống.

Logic chọn Model/Category theo từ khoá trong asset_name — VD "Monitor" → Monitor BN,
"X-quang"/"XR" → X-quang, "CT" → CT Scanner, "Máy thở" → Ventilator, v.v. Nếu không
detect được thì fallback "Monitor BN" (nhóm phổ biến nhất).

Run: bench --site miyano execute assetcore.tests.patch_uat_data.patch_uat_assets_data
"""
from __future__ import annotations

import hashlib
import random

import frappe
from frappe.utils import add_days, nowdate


# ─── Bộ từ điển dữ liệu y tế thực tế Việt Nam ────────────────────────────────

DEPARTMENTS = [
    # (name, code, phone, email)
    ("Khoa Cấp cứu",                            "DEPT-ER",  "02862781010", "capcuu@bvq2.local"),
    ("Khoa Hồi sức tích cực (ICU)",             "DEPT-ICU", "02862785200", "icu@bvq2.local"),
    ("Khoa Chẩn đoán hình ảnh (KCDHA)",         "DEPT-DI",  "02862785400", "kcdha@bvq2.local"),
    ("Khoa Xét nghiệm",                         "DEPT-LAB", "02862785500", "lab@bvq2.local"),
    ("Khoa Phẫu thuật — Gây mê hồi sức",        "DEPT-ANE", "02862785300", "pt-gmhs@bvq2.local"),
    ("Khoa Nội Tim mạch",                       "DEPT-CAR", "02862785100", "timmach@bvq2.local"),
    ("Khoa Sản",                                "DEPT-OBS", "02862785600", "san@bvq2.local"),
    ("Phòng Quản lý Thiết bị Y tế (HTM)",       "DEPT-HTM", "02862785900", "htm@bvq2.local"),
]

LOCATIONS = [
    # (name, code, area_type, infection_level, backup, emergency_contact, notes)
    ("Phòng Cấp cứu ER-01",             "LOC-ER-01",    "General Ward", "Enhanced", 1, "02862781011", "Phòng cấp cứu chính 24/7, 10 giường"),
    ("Phòng ICU 2.05",                  "LOC-ICU-205",  "ICU",          "Enhanced", 1, "02862785205", "Hồi sức tích cực nội, 12 giường monitor"),
    ("Phòng Mổ OR-1",                   "LOC-OR-1",     "OR",           "Enhanced", 1, "02862785301", "Phòng mổ chính, lớp áp suất âm"),
    ("Phòng X-quang KCDHA-01",          "LOC-XR-01",    "Imaging",      "Standard", 1, "02862785410", "Phòng X-quang tổng quát, chắn chì"),
    ("Phòng CT Scanner KCDHA-02",       "LOC-CT-02",    "Imaging",      "Standard", 1, "02862785411", "Phòng CT 64-128 lát, kiểm soát TT19/2012"),
    ("Phòng MRI KCDHA-03",              "LOC-MRI-03",   "Imaging",      "Standard", 1, "02862785412", "Phòng MRI 1.5T, vùng cấm từ"),
    ("Phòng Siêu âm Sản",               "LOC-US-01",    "Imaging",      "Standard", 0, "02862785612", "Siêu âm Doppler 4D"),
    ("Phòng Xét nghiệm Sinh hoá LAB-3", "LOC-LAB-03",   "Lab",          "Standard", 0, "02862785520", "Sinh hoá - huyết học ISO 15189"),
    ("Phòng Hồi tỉnh 2.07",             "LOC-REC-207",  "General Ward", "Enhanced", 1, "02862785206", "Hồi tỉnh sau mổ, 6 giường"),
    ("Kho thiết bị HTM tầng hầm",       "LOC-WH-B1",    "Storage",      "Standard", 0, "02862785901", "Kho dự phòng thiết bị"),
]

CATEGORIES = [
    # (name, pm_days, cal_days, has_radiation, description)
    ("Chẩn đoán hình ảnh",          365, 365, 1, "MRI, CT, X-quang, siêu âm — yêu cầu QC/QA bức xạ"),
    ("Hồi sức - Cấp cứu",           90,  180, 0, "Máy thở, monitor, máy sốc tim, bơm tiêm"),
    ("Xét nghiệm",                  180, 365, 0, "Sinh hoá - huyết học - miễn dịch, ISO 15189"),
    ("Phẫu thuật - Gây mê",         180, 180, 0, "Máy gây mê, vaporizer, dao mổ điện"),
    ("Theo dõi bệnh nhân",          180, 365, 0, "Monitor 5 thông số, cardiac output, BIS"),
    ("Bơm tiêm - Truyền dịch",      365, 365, 0, "Syringe pump, infusion pump"),
]

# Supplier tương ứng với manufacturer phổ biến trên thị trường VN
SUPPLIERS = [
    # (name, manufacturer, country, tax_id, website, address, phone, mobile, email, local_rep)
    ("GE HealthCare Việt Nam",          "GE Healthcare",         "Hoa Kỳ",
     "0302345678", "www.gehealthcare.com.vn",
     "Tầng 14, Vincom Đồng Khởi, 72 Lê Thánh Tôn, Q.1, TP.HCM",
     "02839110080", "0903456789", "service-vn@gehealthcare.com",
     "Trần Minh Khôi — Country Service Lead"),

    ("Siemens Healthineers Việt Nam",   "Siemens Healthineers",  "Đức",
     "0309987654", "www.siemens-healthineers.com.vn",
     "Tầng 18, Metropolitan Tower, 235 Đồng Khởi, Q.1, TP.HCM",
     "02839111234", "0908234567", "service.vn@siemens-healthineers.com",
     "Nguyễn Quang Dũng — Service Mgr"),

    ("Philips Healthcare Việt Nam",     "Philips",               "Hà Lan",
     "0301234567", "www.philips.com.vn",
     "Tầng 12, Saigon Trade Center, 37 Tôn Đức Thắng, Q.1, TP.HCM",
     "02838278888", "0908123456", "service.vn@philips.com",
     "Nguyễn Văn Tùng — Country Service Mgr"),

    ("Medtronic Việt Nam",              "Medtronic",             "Hoa Kỳ",
     "0312345098", "www.medtronic.com/vn",
     "Tầng 10, Saigon Centre, 65 Lê Lợi, Q.1, TP.HCM",
     "02838239999", "0909111222", "vn.service@medtronic.com",
     "Lê Thanh Hà — Clinical Service"),

    ("Mindray Medical Việt Nam",        "Mindray",               "Trung Quốc",
     "0303456789", "www.mindray.com/vn",
     "Lầu 5, Bitexco Nam Long, 63A Võ Văn Tần, Q.3, TP.HCM",
     "02839309888", "0909876543", "support.vn@mindray.com",
     "Lê Thị Bích Ngọc — Service Mgr"),
]

# Device models — gắn với manufacturer thật, có thông số đầy đủ
DEVICE_MODELS = [
    # (keyword_match, model, mfg, cat, class, risk, gmdn, emdn, is_rad, pm_days, cal_days, power, country, lifespan)
    ("mri",        "Siemens MAGNETOM Sola 1.5T",       "Siemens Healthineers", "Chẩn đoán hình ảnh",   "Class III", "High",     "42518", "Z110201", 0, 365, 365, "380VAC 3-phase, 50Hz", "Đức",        12),
    ("ct",         "GE Revolution CT 128 lát",          "GE Healthcare",        "Chẩn đoán hình ảnh",   "Class III", "High",     "40890", "Z110401", 1, 365, 365, "380VAC 3-phase, 50Hz", "Hoa Kỳ",     12),
    ("x-quang",    "Philips DigitalDiagnost C90 DR",    "Philips",              "Chẩn đoán hình ảnh",   "Class III", "High",     "35910", "Z110301", 1, 180, 365, "220VAC, 50Hz, 80kW",  "Hà Lan",    10),
    ("xr",         "Philips DigitalDiagnost C90 DR",    "Philips",              "Chẩn đoán hình ảnh",   "Class III", "High",     "35910", "Z110301", 1, 180, 365, "220VAC, 50Hz, 80kW",  "Hà Lan",    10),
    ("siêu âm",    "Mindray DC-70 X-Insight Doppler 4D","Mindray",              "Chẩn đoán hình ảnh",   "Class II",  "Low",      "40231", "Z110305", 0, 365, 365, "100-240VAC, 50-60Hz", "Trung Quốc", 8),
    ("ultrasound", "Mindray DC-70 X-Insight Doppler 4D","Mindray",              "Chẩn đoán hình ảnh",   "Class II",  "Low",      "40231", "Z110305", 0, 365, 365, "100-240VAC, 50-60Hz", "Trung Quốc", 8),

    ("máy thở",    "Dräger Evita V800 High-end",        "Philips",              "Hồi sức - Cấp cứu",    "Class II",  "Critical", "36263", "R0301010101", 0, 90, 180, "100-240VAC + Pin 4h", "Đức",        8),
    ("ventilator", "Dräger Evita V800 High-end",        "Philips",              "Hồi sức - Cấp cứu",    "Class II",  "Critical", "36263", "R0301010101", 0, 90, 180, "100-240VAC + Pin 4h", "Đức",        8),
    ("vent",       "Dräger Evita V800 High-end",        "Philips",              "Hồi sức - Cấp cứu",    "Class II",  "Critical", "36263", "R0301010101", 0, 90, 180, "100-240VAC + Pin 4h", "Đức",        8),

    ("sốc tim",    "Philips HeartStart MRx Defibrillator","Philips",            "Hồi sức - Cấp cứu",    "Class II",  "Critical", "35022", "Z12060201", 0, 180, 180, "100-240VAC + Pin Li-Ion", "Hà Lan",  7),
    ("defib",      "Philips HeartStart MRx Defibrillator","Philips",            "Hồi sức - Cấp cứu",    "Class II",  "Critical", "35022", "Z12060201", 0, 180, 180, "100-240VAC + Pin Li-Ion", "Hà Lan",  7),

    ("monitor",    "Philips IntelliVue MX550 5-thông số","Philips",             "Theo dõi bệnh nhân",   "Class II",  "Medium",   "37825", "Z12030101", 0, 180, 365, "100-240VAC, 50-60Hz",   "Đức",       8),
    ("patient",    "Philips IntelliVue MX550 5-thông số","Philips",             "Theo dõi bệnh nhân",   "Class II",  "Medium",   "37825", "Z12030101", 0, 180, 365, "100-240VAC, 50-60Hz",   "Đức",       8),

    ("bơm tiêm",   "B.Braun Perfusor Space Syringe Pump","Medtronic",           "Bơm tiêm - Truyền dịch","Class II", "Medium",   "13287", "Z120601",   0, 365, 365, "100-240VAC + Pin Li-Ion","Đức",       7),
    ("bơm truyền", "B.Braun Infusomat Space Volumetric", "Medtronic",           "Bơm tiêm - Truyền dịch","Class II", "Medium",   "13288", "Z120602",   0, 365, 365, "100-240VAC + Pin Li-Ion","Đức",       7),
    ("infusion",   "B.Braun Infusomat Space Volumetric", "Medtronic",           "Bơm tiêm - Truyền dịch","Class II", "Medium",   "13288", "Z120602",   0, 365, 365, "100-240VAC + Pin Li-Ion","Đức",       7),
    ("syringe",    "B.Braun Perfusor Space Syringe Pump","Medtronic",           "Bơm tiêm - Truyền dịch","Class II", "Medium",   "13287", "Z120601",   0, 365, 365, "100-240VAC + Pin Li-Ion","Đức",       7),

    ("gây mê",     "GE Aisys CS2 Anesthesia",          "GE Healthcare",         "Phẫu thuật - Gây mê",  "Class II",  "High",     "35048", "R0303010101", 0, 180, 180, "220VAC, 50Hz",         "Hoa Kỳ",     10),
    ("anesthesia", "GE Aisys CS2 Anesthesia",          "GE Healthcare",         "Phẫu thuật - Gây mê",  "Class II",  "High",     "35048", "R0303010101", 0, 180, 180, "220VAC, 50Hz",         "Hoa Kỳ",     10),

    ("xét nghiệm", "Roche Cobas c311 Biochemistry",    "Siemens Healthineers",  "Xét nghiệm",           "Class I",   "Low",      "40568", "W0105",     0, 180, 365, "220VAC, 50Hz",         "Thuỵ Sĩ",    8),
    ("sinh hóa",   "Roche Cobas c311 Biochemistry",    "Siemens Healthineers",  "Xét nghiệm",           "Class I",   "Low",      "40568", "W0105",     0, 180, 365, "220VAC, 50Hz",         "Thuỵ Sĩ",    8),
    ("huyết học",  "Sysmex XN-1000 Hematology",         "Siemens Healthineers",  "Xét nghiệm",           "Class I",   "Low",      "40570", "W0103",     0, 180, 365, "220VAC, 50Hz",         "Nhật Bản",   8),
]

# Fallback model (khi không match keyword nào)
DEFAULT_MODEL_IDX = DEVICE_MODELS.index(next(m for m in DEVICE_MODELS if m[0] == "monitor"))

# Map tên hãng → tên supplier đầy đủ
MFG_TO_SUPPLIER_NAME = {row[1]: row[0] for row in SUPPLIERS}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _stable_random(seed_key: str) -> random.Random:
    """Random deterministic theo key — re-run → cùng kết quả."""
    h = int(hashlib.md5(seed_key.encode()).hexdigest(), 16)
    return random.Random(h)


def _pick_model_for_asset(asset_name: str, device_model_link: str | None) -> tuple:
    """Chọn model phù hợp theo từ khoá trong tên thiết bị."""
    # Nếu đã có device_model link, ưu tiên lấy model từ DB nếu match
    if device_model_link and frappe.db.exists("IMM Device Model", device_model_link):
        existing_mfg = frappe.db.get_value("IMM Device Model", device_model_link, "manufacturer")
        if existing_mfg:
            for row in DEVICE_MODELS:
                if row[2] == existing_mfg:
                    return row
    lowered = (asset_name or "").lower()
    for row in DEVICE_MODELS:
        if row[0] in lowered:
            return row
    return DEVICE_MODELS[DEFAULT_MODEL_IDX]


def _gen_serial(prefix: str, mfg: str, key: str) -> str:
    rng = _stable_random(key)
    year = rng.choice([2020, 2021, 2022, 2023, 2024])
    num = rng.randint(1, 9999)
    mfg_code = "".join(c for c in mfg.split()[0].upper() if c.isalpha())[:4]
    return f"{mfg_code}-{prefix}-{year}-{num:04d}"


def _gen_udi(gmdn: str, key: str) -> str:
    rng = _stable_random(key + "-udi")
    lot = f"LOT{rng.randint(1, 99999):05d}"
    exp = rng.choice(["260131", "270630", "280831", "290430"])
    return f"(01){gmdn.ljust(14, '0')}(17){exp}(10){lot}"


def _gen_byt(cat_code: str, key: str) -> str:
    rng = _stable_random(key + "-byt")
    year = rng.choice([2022, 2023, 2024])
    num = rng.randint(1, 999)
    return f"DK-BYT-{year}-{cat_code}-{num:03d}"


def _purchase_price(mfg: str, kw: str) -> int:
    prices = {
        "mri": 45_000_000_000, "ct": 12_500_000_000, "x-quang": 2_850_000_000, "xr": 2_850_000_000,
        "siêu âm": 580_000_000, "ultrasound": 580_000_000,
        "máy thở": 425_000_000, "ventilator": 425_000_000, "vent": 425_000_000,
        "sốc tim": 320_000_000, "defib": 320_000_000,
        "monitor": 185_000_000, "patient": 185_000_000,
        "bơm tiêm": 38_000_000, "bơm truyền": 42_000_000, "infusion": 42_000_000, "syringe": 38_000_000,
        "gây mê": 1_650_000_000, "anesthesia": 1_650_000_000,
        "xét nghiệm": 3_200_000_000, "sinh hóa": 3_200_000_000, "huyết học": 2_800_000_000,
    }
    return prices.get(kw, 185_000_000)


# ─── Upsert linked DocTypes ──────────────────────────────────────────────────

def _find_existing(doctype: str, *filter_dicts) -> str | None:
    """Try multiple filter sets (unique fields first) → return first hit or None."""
    for filters in filter_dicts:
        if not any(filters.values()):
            continue
        existing = frappe.db.exists(doctype, filters)
        if existing:
            return existing if isinstance(existing, str) else existing[0]
    return None


def _ensure_departments() -> dict:
    """Đảm bảo các khoa tồn tại → return {name: frappe_name}."""
    result = {}
    for (dname, code, phone, email) in DEPARTMENTS:
        existing = _find_existing("AC Department",
                                  {"department_code": code},
                                  {"department_name": dname})
        if existing:
            result[dname] = existing
            continue
        doc = frappe.get_doc({
            "doctype": "AC Department", "department_name": dname, "department_code": code,
            "phone": phone, "email": email, "is_active": 1, "is_group": 0,
        }).insert(ignore_permissions=True)
        result[dname] = doc.name
        print(f"  [+] Tạo Khoa: {dname} → {doc.name}")
    return result


def _ensure_locations() -> dict:
    result = {}
    for (lname, code, area, lvl, backup, contact, notes) in LOCATIONS:
        existing = _find_existing("AC Location",
                                  {"location_code": code},
                                  {"location_name": lname})
        if existing:
            result[lname] = existing
            continue
        doc = frappe.get_doc({
            "doctype": "AC Location", "location_name": lname, "location_code": code,
            "clinical_area_type": area, "infection_control_level": lvl,
            "power_backup_available": backup, "emergency_contact": contact,
            "notes": notes, "is_group": 0,
        }).insert(ignore_permissions=True)
        result[lname] = doc.name
        print(f"  [+] Tạo Vị trí: {lname} → {doc.name}")
    return result


def _ensure_categories() -> dict:
    result = {}
    for (cname, pm_d, cal_d, has_rad, desc) in CATEGORIES:
        existing = frappe.db.exists("AC Asset Category", {"category_name": cname})
        if existing:
            result[cname] = existing if isinstance(existing, str) else existing[0]
            continue
        doc = frappe.get_doc({
            "doctype": "AC Asset Category", "category_name": cname, "description": desc,
            "default_pm_required": 1, "default_pm_interval_days": pm_d,
            "default_calibration_required": 1, "default_calibration_interval_days": cal_d,
            "has_radiation": has_rad, "is_active": 1,
        }).insert(ignore_permissions=True)
        result[cname] = doc.name
        print(f"  [+] Tạo Danh mục: {cname} → {doc.name}")
    return result


def _ensure_suppliers() -> dict:
    """Return {manufacturer_short_name: supplier_frappe_name}."""
    result = {}
    for (sname, mfg, country, tax, site, addr, phone, mobile, email, rep) in SUPPLIERS:
        existing = _find_existing("AC Supplier",
                                  {"tax_id": tax},
                                  {"supplier_name": sname})
        if existing:
            result[mfg] = existing
            continue
        doc = frappe.get_doc({
            "doctype": "AC Supplier", "supplier_name": sname,
            "supplier_group": "Manufacturer", "vendor_type": "Manufacturer",
            "country": country, "tax_id": tax, "website": site,
            "address": addr, "phone": phone, "mobile_no": mobile, "email_id": email,
            "support_hotline": phone, "technical_email": email,
            "local_representative": rep, "is_active": 1,
            "contract_start": add_days(nowdate(), -180),
            "contract_end": add_days(nowdate(), 365),
            "contract_value": 500_000_000,
        }).insert(ignore_permissions=True)
        result[mfg] = doc.name
        print(f"  [+] Tạo NCC: {sname} → {doc.name}")
    return result


def _ensure_device_models(categories: dict) -> dict:
    """Return {model_name: frappe_name}."""
    result = {}
    seen = set()
    for row in DEVICE_MODELS:
        (_kw, model, mfg, cat, cls, risk, gmdn, emdn, is_rad, pm_d, cal_d, power, country, lifespan) = row
        if model in seen:
            continue
        seen.add(model)
        existing = frappe.db.exists("IMM Device Model", {"model_name": model, "manufacturer": mfg})
        if existing:
            result[model] = existing if isinstance(existing, str) else existing[0]
            continue
        doc = frappe.get_doc({
            "doctype": "IMM Device Model", "model_name": model, "manufacturer": mfg,
            "model_version": "v1.0", "country_of_origin": country, "power_supply": power,
            "expected_lifespan_years": lifespan, "medical_device_class": cls,
            "risk_classification": risk, "gmdn_code": gmdn, "emdn_code": emdn,
            "registration_required": 1, "is_radiation_device": is_rad,
            "asset_category": categories.get(cat),
            "is_pm_required": 1, "pm_interval_days": pm_d, "pm_alert_days": 14,
            "is_calibration_required": 1, "calibration_interval_days": cal_d,
            "calibration_alert_days": 30, "default_calibration_type": "External",
            "notes": f"{model} — sử dụng thường quy trong dịch vụ y tế",
        }).insert(ignore_permissions=True)
        result[model] = doc.name
        print(f"  [+] Tạo Device Model: {model} → {doc.name}")
    return result


# ─── Main patch ──────────────────────────────────────────────────────────────

def patch_uat_assets_data():
    """Quét toàn bộ AC Asset → fill thiếu + thay dữ liệu rác bằng dữ liệu thật."""
    frappe.set_user("Administrator")
    print("═" * 70)
    print("PATCH UAT ASSETS DATA — BỆNH VIỆN ĐA KHOA VIỆT NAM")
    print("═" * 70)

    # Step 1: Đảm bảo các linked DocType tồn tại
    print("\n[Bước 1] Đảm bảo Khoa / Vị trí / Danh mục / NCC / Model…")
    depts = _ensure_departments()
    locations = _ensure_locations()
    categories = _ensure_categories()
    suppliers = _ensure_suppliers()
    models = _ensure_device_models(categories)
    dept_list = list(depts.values())
    loc_list = list(locations.values())

    # Step 2: Patch các IMM Device Model cũ bị thiếu GMDN/metadata
    # (gmdn_code của AC Asset có fetch_from=device_model.gmdn_code → phải
    #  điền ở Model thì Asset mới nhận được giá trị)
    print("\n[Bước 2] Vá Device Model cũ thiếu metadata…")
    orphan_models = frappe.get_all("IMM Device Model",
        filters={"gmdn_code": ["in", [None, ""]]}, fields=["name","model_name","manufacturer"])
    for m in orphan_models:
        # Match tên model / hãng với từ điển DEVICE_MODELS
        lowered = (m.model_name or "").lower()
        match = next((r for r in DEVICE_MODELS if r[0] in lowered), None)
        if not match and m.manufacturer:
            match = next((r for r in DEVICE_MODELS if r[2] == m.manufacturer), None)
        if not match:
            match = DEVICE_MODELS[DEFAULT_MODEL_IDX]
        (_kw, _mdl, _mfg, _cat, cls, risk, gmdn, emdn, is_rad, pm_d, cal_d, power, country, lifespan) = match
        mdoc = frappe.get_doc("IMM Device Model", m.name)
        if not mdoc.gmdn_code: mdoc.gmdn_code = gmdn
        if not mdoc.emdn_code: mdoc.emdn_code = emdn
        if not mdoc.medical_device_class: mdoc.medical_device_class = cls
        if not mdoc.risk_classification: mdoc.risk_classification = risk
        if not mdoc.country_of_origin: mdoc.country_of_origin = country
        if not mdoc.power_supply: mdoc.power_supply = power
        if not mdoc.expected_lifespan_years: mdoc.expected_lifespan_years = lifespan
        if not mdoc.pm_interval_days: mdoc.pm_interval_days = pm_d
        if not mdoc.calibration_interval_days: mdoc.calibration_interval_days = cal_d
        if not mdoc.is_pm_required: mdoc.is_pm_required = 1
        if not mdoc.is_calibration_required: mdoc.is_calibration_required = 1
        if not mdoc.is_radiation_device: mdoc.is_radiation_device = is_rad
        if not mdoc.asset_category and _cat in categories:
            mdoc.asset_category = categories[_cat]
        try:
            mdoc.save(ignore_permissions=True)
            print(f"  ✅ Vá Model: {mdoc.name} (GMDN={gmdn}, class={cls})")
        except Exception as e:
            print(f"  ❌ {mdoc.name}: {type(e).__name__}: {str(e)[:120]}")

    # Step 3: Patch từng AC Asset
    print("\n[Bước 3] Quét & cập nhật AC Asset…")
    all_assets = frappe.get_all("AC Asset", pluck="name")
    print(f"  Tổng số Asset cần xử lý: {len(all_assets)}")

    patched, skipped = 0, 0
    for asset_name in all_assets:
        try:
            doc = frappe.get_doc("AC Asset", asset_name)
        except Exception as e:
            print(f"  [!] Không load được {asset_name}: {e}")
            skipped += 1
            continue

        # Không đụng đến asset đã Decommissioned (để giữ lịch sử)
        if doc.lifecycle_status == "Decommissioned":
            print(f"  [-] Bỏ qua (Decommissioned): {doc.name}")
            skipped += 1
            continue
        # Submitted doc (docstatus=1): nhiều field bị lock, bỏ qua
        if doc.docstatus == 1:
            print(f"  [-] Bỏ qua (Submitted): {doc.name}")
            skipped += 1
            continue

        rng = _stable_random(doc.name)

        # Pre-cleanup: reset các Link field bị orphan (giá trị không tồn tại trong DB)
        for link_field, link_dt in [
            ("location", "AC Location"), ("department", "AC Department"),
            ("asset_category", "AC Asset Category"), ("device_model", "IMM Device Model"),
            ("supplier", "AC Supplier"),
        ]:
            val = doc.get(link_field)
            if val and not frappe.db.exists(link_dt, val):
                doc.set(link_field, None)

        # Detect model theo tên
        model_row = _pick_model_for_asset(doc.asset_name or "", doc.device_model)
        (kw, mdl, mfg, cat_name, cls, risk, gmdn, emdn, is_rad,
         pm_d, cal_d, power, country, lifespan) = model_row

        # ── Fill các field bắt buộc / core ──
        if not (doc.asset_name or "").strip():
            doc.asset_name = f"{mdl} - {rng.choice(['Khoa Cấp cứu','ICU','KCDHA','LAB','OR'])}"

        if not doc.asset_code:
            doc.asset_code = f"HTM-{kw.upper().replace(' ','')[:6]}-{rng.randint(100,9999):04d}"
        if not doc.item_code:
            doc.item_code = doc.asset_code.replace("HTM-", "ITM-")

        # Category + Model + Supplier
        if not doc.asset_category and cat_name in categories:
            doc.asset_category = categories[cat_name]
        if not doc.device_model and mdl in models:
            doc.device_model = models[mdl]
        if not doc.supplier and mfg in suppliers:
            doc.supplier = suppliers[mfg]

        # Department + Location + Custodian + Technician
        if not doc.department:
            doc.department = rng.choice(dept_list)
        if not doc.location:
            doc.location = rng.choice(loc_list)
        if not doc.custodian:
            doc.custodian = "Administrator"
        if not doc.responsible_technician:
            doc.responsible_technician = "Administrator"

        # HTM / Pháp lý
        if not doc.manufacturer_sn:
            doc.manufacturer_sn = _gen_serial(kw.upper().replace(" ","")[:4] or "DEV", mfg, doc.name)
        if not doc.udi_code:
            doc.udi_code = _gen_udi(gmdn, doc.name)
        if not doc.gmdn_code:
            doc.gmdn_code = gmdn
        if not doc.medical_device_class:
            doc.medical_device_class = cls
        if not doc.risk_classification:
            doc.risk_classification = risk
        if not doc.byt_reg_no:
            doc.byt_reg_no = _gen_byt(kw.upper().replace(" ","")[:4] or "DEV", doc.name)
        if not doc.byt_reg_expiry:
            doc.byt_reg_expiry = add_days(nowdate(), rng.randint(180, 800))

        # Mua sắm / Bảo hành
        if not doc.purchase_date:
            doc.purchase_date = add_days(nowdate(), -rng.randint(180, 1500))
        if not doc.gross_purchase_amount or doc.gross_purchase_amount == 0:
            doc.gross_purchase_amount = _purchase_price(mfg, kw)
        if not doc.warranty_expiry_date:
            doc.warranty_expiry_date = add_days(doc.purchase_date, 730)
        if not doc.commissioning_date:
            doc.commissioning_date = add_days(doc.purchase_date, rng.randint(15, 60))
        if not doc.commissioning_ref:
            doc.commissioning_ref = f"ACC-{doc.name[-4:]}-{rng.randint(1000, 9999)}"

        # Khấu hao (bắt buộc phải set khi đưa vào sử dụng)
        if not doc.depreciation_method:
            doc.depreciation_method = "Straight Line"
        if not doc.useful_life_years:
            doc.useful_life_years = lifespan
        if not doc.in_service_date:
            doc.in_service_date = doc.commissioning_date
        if not doc.residual_value:
            doc.residual_value = int(doc.gross_purchase_amount * 0.1)

        # PM
        if not doc.is_pm_required:
            doc.is_pm_required = 1
        if not doc.pm_interval_days:
            doc.pm_interval_days = pm_d
        if not doc.next_pm_date:
            doc.next_pm_date = add_days(nowdate(), rng.randint(15, pm_d))
        if not doc.last_pm_date:
            doc.last_pm_date = add_days(doc.next_pm_date, -pm_d)

        # Calibration
        if not doc.is_calibration_required:
            doc.is_calibration_required = 1
        if not doc.calibration_interval_days:
            doc.calibration_interval_days = cal_d
        if not doc.next_calibration_date:
            doc.next_calibration_date = add_days(nowdate(), rng.randint(30, cal_d))
        if not doc.last_calibration_date:
            doc.last_calibration_date = add_days(doc.next_calibration_date, -cal_d)
        if not doc.calibration_status:
            diff = (frappe.utils.getdate(doc.next_calibration_date) - frappe.utils.getdate(nowdate())).days
            if diff < 0:
                doc.calibration_status = "Overdue"
            elif diff < 30:
                doc.calibration_status = "Due Soon"
            else:
                doc.calibration_status = "On Schedule"

        # Bảo hiểm
        if not doc.insurance_policy_no:
            doc.insurance_policy_no = f"BVINS-2024-{doc.name[-6:]}"
        if not doc.insurer_name:
            doc.insurer_name = "Tổng Công ty Bảo hiểm Bảo Việt — CN TP.HCM"
        if not doc.insured_value:
            doc.insured_value = int(doc.gross_purchase_amount * 1.1)
        if not doc.insurance_start_date:
            doc.insurance_start_date = add_days(nowdate(), -180)
        if not doc.insurance_end_date:
            doc.insurance_end_date = add_days(nowdate(), 185)

        # Status / Lifecycle
        if not doc.status:
            doc.status = "Active"
        if not doc.lifecycle_status:
            doc.lifecycle_status = "Active"

        # Notes (giàu thông tin để UI hiển thị đẹp)
        if not (doc.notes or "").strip():
            doc.notes = (
                f"<p><strong>{doc.asset_name}</strong> — {mdl}</p>"
                f"<p>Hãng: {mfg} ({country}) · Serial: <code>{doc.manufacturer_sn}</code></p>"
                f"<p>Ngày mua: {doc.purchase_date} · Giá: {doc.gross_purchase_amount:,} VND · "
                f"Bảo hành đến: {doc.warranty_expiry_date}</p>"
            )

        # Save (kích hoạt validation hooks)
        try:
            doc.save(ignore_permissions=True)
            patched += 1
            print(f"  ✅ [{patched:>3}/{len(all_assets)}] {doc.name} → {doc.asset_name}")
        except Exception as e:
            skipped += 1
            print(f"  ❌ {doc.name}: {type(e).__name__}: {str(e)[:120]}")

    frappe.db.commit()

    print("\n" + "═" * 70)
    print(f"HOÀN TẤT: đã cập nhật {patched}/{len(all_assets)} thiết bị · bỏ qua {skipped}")
    print(f"Dependencies: {len(depts)} Khoa · {len(locations)} Vị trí · "
          f"{len(categories)} Danh mục · {len(suppliers)} NCC · {len(models)} Model")
    print("═" * 70)
