"""HARD RESET — xóa sổ dữ liệu rác UAT/Test/Demo + ghi đè 100% bằng catalog thật.

STRICT RULES (tuân thủ tuyệt đối):
  1. Cấm ghép chữ "UAT"/"Test"/"Demo" vào bất kỳ field nào.
  2. Cấm bịa tên thiết bị chung chung.
  3. Chỉ bốc từ REAL_MEDICAL_ASSETS catalog bên dưới. Chọn item nào phải đi kèm
     đúng model, manufacturer, department của item đó.
  4. Record không sửa được (Submitted lock / locked validation) → CANCEL + DELETE.

Hành động:
  • Bước 1: Xóa sổ các AC Asset chứa "UAT"/"Test"/"Demo" trong tên/mã/model.
  • Bước 2: Xóa sổ các IMM Device Model rác (tên chứa UAT/Test/Demo).
  • Bước 3: Ghi đè toàn bộ AC Asset còn lại bằng catalog thật — dùng db_set()
    để bypass validation nếu save() fail.

Run: bench --site miyano execute assetcore.tests.hard_reset_assets.hard_reset
"""
from __future__ import annotations

import random
import re

import frappe
from frappe.utils import add_days, add_years, nowdate


# ─── CATALOG: Dữ liệu thiết bị y tế 100% thật (BV hạng 1 VN) ────────────────

REAL_MEDICAL_ASSETS = [
    {"asset_name": "Máy X-Quang kỹ thuật số (DR)",          "model": "Definium 5000",       "manufacturer": "GE Healthcare",         "department": "Khoa Chẩn đoán hình ảnh"},
    {"asset_name": "Máy CT Scanner 128 lát cắt",             "model": "Somatom go.Top",      "manufacturer": "Siemens Healthineers",  "department": "Khoa Chẩn đoán hình ảnh"},
    {"asset_name": "Máy siêu âm Doppler màu 4D",             "model": "Voluson E10",         "manufacturer": "GE Healthcare",         "department": "Khoa Sản"},
    {"asset_name": "Máy thở chức năng cao",                  "model": "Puritan Bennett 980", "manufacturer": "Medtronic",             "department": "Khoa Hồi sức tích cực (ICU)"},
    {"asset_name": "Monitor theo dõi bệnh nhân 5 thông số", "model": "BeneVision N12",      "manufacturer": "Mindray",               "department": "Khoa Cấp cứu"},
    {"asset_name": "Hệ thống phẫu thuật nội soi",            "model": "Visera 4K UHD",       "manufacturer": "Olympus",               "department": "Khoa Phẫu thuật - GMHS"},
    {"asset_name": "Máy xét nghiệm sinh hóa tự động",        "model": "Cobas c 501",         "manufacturer": "Roche Diagnostics",     "department": "Khoa Xét nghiệm"},
    {"asset_name": "Máy điện tim 12 chuyển đạo",             "model": "MAC 2000",            "manufacturer": "GE Healthcare",         "department": "Khoa Khám bệnh"},
    {"asset_name": "Bơm tiêm điện",                          "model": "Perfusor Space",      "manufacturer": "B. Braun",              "department": "Khoa Hồi sức tích cực (ICU)"},
    {"asset_name": "Máy lọc máu liên tục (CRRT)",            "model": "Prismaflex",          "manufacturer": "Baxter",                "department": "Khoa Hồi sức tích cực (ICU)"},
]

# Metadata bổ sung cho từng mục catalog — map theo asset_name
REAL_ASSET_META = {
    "Máy X-Quang kỹ thuật số (DR)":          {"category": "Chẩn đoán hình ảnh",   "class": "Class III", "risk": "High",     "gmdn": "35910", "emdn": "Z110301", "is_rad": 1, "pm_days": 180, "cal_days": 365, "power": "220VAC, 50Hz, 80kW",   "country": "Hoa Kỳ",   "lifespan": 10, "price":  2_850_000_000, "code_prefix": "XR"},
    "Máy CT Scanner 128 lát cắt":             {"category": "Chẩn đoán hình ảnh",   "class": "Class III", "risk": "High",     "gmdn": "40890", "emdn": "Z110401", "is_rad": 1, "pm_days": 365, "cal_days": 365, "power": "380VAC 3-phase, 50Hz", "country": "Đức",      "lifespan": 12, "price": 12_500_000_000, "code_prefix": "CT"},
    "Máy siêu âm Doppler màu 4D":             {"category": "Chẩn đoán hình ảnh",   "class": "Class II",  "risk": "Low",      "gmdn": "40231", "emdn": "Z110305", "is_rad": 0, "pm_days": 365, "cal_days": 365, "power": "100-240VAC, 50-60Hz",  "country": "Hoa Kỳ",   "lifespan": 10, "price":    580_000_000, "code_prefix": "US"},
    "Máy thở chức năng cao":                  {"category": "Hồi sức - Cấp cứu",    "class": "Class II",  "risk": "Critical", "gmdn": "36263", "emdn": "R0301010101", "is_rad": 0, "pm_days": 90, "cal_days": 180, "power": "100-240VAC + Pin 4h", "country": "Hoa Kỳ", "lifespan":  8, "price":    425_000_000, "code_prefix": "VNT"},
    "Monitor theo dõi bệnh nhân 5 thông số":  {"category": "Theo dõi bệnh nhân",   "class": "Class II",  "risk": "Medium",   "gmdn": "37825", "emdn": "Z12030101", "is_rad": 0, "pm_days": 180, "cal_days": 365, "power": "100-240VAC, 50-60Hz", "country": "Trung Quốc","lifespan":  8, "price":    185_000_000, "code_prefix": "MON"},
    "Hệ thống phẫu thuật nội soi":            {"category": "Phẫu thuật - Gây mê", "class": "Class II",  "risk": "High",     "gmdn": "38120", "emdn": "R0302010101", "is_rad": 0, "pm_days": 180, "cal_days": 365, "power": "220VAC, 50Hz",        "country": "Nhật Bản",  "lifespan": 10, "price":  1_850_000_000, "code_prefix": "ENDO"},
    "Máy xét nghiệm sinh hóa tự động":        {"category": "Xét nghiệm",           "class": "Class I",   "risk": "Low",      "gmdn": "40568", "emdn": "W0105",    "is_rad": 0, "pm_days": 180, "cal_days": 365, "power": "220VAC, 50Hz",         "country": "Thụy Sĩ",  "lifespan":  8, "price":  3_200_000_000, "code_prefix": "LAB"},
    "Máy điện tim 12 chuyển đạo":             {"category": "Theo dõi bệnh nhân",   "class": "Class II",  "risk": "Medium",   "gmdn": "17882", "emdn": "Z12030201", "is_rad": 0, "pm_days": 365, "cal_days": 365, "power": "100-240VAC + Pin",    "country": "Hoa Kỳ",   "lifespan":  8, "price":     95_000_000, "code_prefix": "ECG"},
    "Bơm tiêm điện":                          {"category": "Bơm tiêm - Truyền dịch","class": "Class II","risk": "Medium",   "gmdn": "13287", "emdn": "Z120601",  "is_rad": 0, "pm_days": 365, "cal_days": 365, "power": "100-240VAC + Pin Li-Ion","country": "Đức",   "lifespan":  7, "price":     38_000_000, "code_prefix": "PUMP"},
    "Máy lọc máu liên tục (CRRT)":            {"category": "Hồi sức - Cấp cứu",    "class": "Class III", "risk": "Critical", "gmdn": "35260", "emdn": "R0303020101","is_rad": 0, "pm_days": 180, "cal_days": 180, "power": "220VAC + Pin dự phòng","country": "Hoa Kỳ",  "lifespan":  8, "price":  1_450_000_000, "code_prefix": "CRRT"},
}

# Manufacturer → full supplier info (đã tạo ở seed_uat.py/patch_uat_data.py)
MFG_TO_SUPPLIER = {
    "GE Healthcare":         "GE HealthCare Việt Nam",
    "Siemens Healthineers":  "Siemens Healthineers Việt Nam",
    "Medtronic":             "Medtronic Việt Nam",
    "Mindray":               "Mindray Medical Việt Nam",
    "Olympus":               "Olympus Việt Nam",
    "Roche Diagnostics":     "Siemens Healthineers Việt Nam",  # Roche phân phối qua nhiều NCC — dùng Siemens làm fallback
    "B. Braun":              "Medtronic Việt Nam",             # B.Braun phân phối qua Medtronic VN
    "Baxter":                "Medtronic Việt Nam",             # Baxter qua Medtronic VN
}

# Department → full Frappe name (đã tạo sẵn)
DEPT_NAME_MAP = {
    "Khoa Cấp cứu": None,
    "Khoa Hồi sức tích cực (ICU)": None,
    "Khoa Chẩn đoán hình ảnh": None,
    "Khoa Xét nghiệm": None,
    "Khoa Phẫu thuật - GMHS": None,
    "Khoa Sản": None,
    "Khoa Khám bệnh": None,
}

RE_JUNK = re.compile(r"\b(uat|test|demo|dummy|fake|placeholder)\b", re.IGNORECASE)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_junk(*values) -> bool:
    """True nếu bất kỳ value nào chứa từ rác."""
    for v in values:
        if v and RE_JUNK.search(str(v)):
            return True
    return False


def _resolve_department(dept_name: str) -> str | None:
    """Tìm hoặc tạo AC Department."""
    cached = DEPT_NAME_MAP.get(dept_name)
    if cached:
        return cached
    existing = frappe.db.exists("AC Department", {"department_name": dept_name})
    if existing:
        name = existing if isinstance(existing, str) else existing[0]
        DEPT_NAME_MAP[dept_name] = name
        return name
    # Tự tạo nếu chưa có
    code = "DEPT-" + re.sub(r"[^A-Z0-9]", "", dept_name.upper())[:8]
    try:
        doc = frappe.get_doc({
            "doctype": "AC Department", "department_name": dept_name,
            "department_code": code, "is_active": 1, "is_group": 0,
        }).insert(ignore_permissions=True)
        DEPT_NAME_MAP[dept_name] = doc.name
        print(f"  [+] Tạo Khoa: {dept_name} → {doc.name}")
        return doc.name
    except Exception as e:
        print(f"  [!] Không tạo được Khoa {dept_name}: {e}")
        return None


_SUPPLIER_FALLBACK_DATA = {
    "Olympus Việt Nam": {
        "country": "Nhật Bản", "tax_id": "0308765432", "website": "www.olympus-vietnam.com",
        "address": "Tầng 7, AB Tower, 76 Lê Lai, Q.1, TP.HCM",
        "phone": "02838222666", "mobile_no": "0908333444", "email_id": "service.vn@olympus.com",
        "local_representative": "Hoàng Minh Tuấn — Service Mgr",
    },
}


def _resolve_supplier(manufacturer: str) -> str | None:
    supplier_name = MFG_TO_SUPPLIER.get(manufacturer)
    if not supplier_name:
        return None
    existing = frappe.db.exists("AC Supplier", {"supplier_name": supplier_name})
    if existing:
        return existing if isinstance(existing, str) else existing[0]
    # Auto-create fallback supplier nếu có metadata
    data = _SUPPLIER_FALLBACK_DATA.get(supplier_name)
    if not data:
        return None
    try:
        doc = frappe.get_doc({
            "doctype": "AC Supplier", "supplier_name": supplier_name,
            "supplier_group": "Manufacturer", "vendor_type": "Manufacturer",
            "support_hotline": data["phone"], "technical_email": data["email_id"],
            "contract_start": add_days(nowdate(), -180),
            "contract_end": add_days(nowdate(), 365),
            "contract_value": 500_000_000, "is_active": 1,
            **data,
        }).insert(ignore_permissions=True)
        print(f"  [+] Tạo NCC: {supplier_name} → {doc.name}")
        return doc.name
    except Exception as e:
        print(f"  [!] Không tạo được NCC {supplier_name}: {e}")
        return None


def _resolve_category(cat_name: str) -> str | None:
    existing = frappe.db.exists("AC Asset Category", {"category_name": cat_name})
    return existing if isinstance(existing, str) else (existing[0] if existing else None)


def _ensure_device_model(catalog_entry: dict, meta: dict, category: str | None) -> str:
    """Đảm bảo IMM Device Model có đầy đủ thông tin thật."""
    model_name = catalog_entry["model"]
    mfg = catalog_entry["manufacturer"]
    existing = frappe.db.exists("IMM Device Model", {"model_name": model_name, "manufacturer": mfg})
    if existing:
        name = existing if isinstance(existing, str) else existing[0]
        # Đảm bảo metadata đầy đủ
        updates = {
            "gmdn_code": meta["gmdn"], "emdn_code": meta["emdn"],
            "medical_device_class": meta["class"], "risk_classification": meta["risk"],
            "country_of_origin": meta["country"], "power_supply": meta["power"],
            "expected_lifespan_years": meta["lifespan"], "pm_interval_days": meta["pm_days"],
            "calibration_interval_days": meta["cal_days"], "is_pm_required": 1,
            "is_calibration_required": 1, "is_radiation_device": meta["is_rad"],
            "registration_required": 1,
        }
        if category: updates["asset_category"] = category
        frappe.db.set_value("IMM Device Model", name, updates)
        return name
    # Tạo mới
    doc_data = {
        "doctype": "IMM Device Model", "model_name": model_name, "manufacturer": mfg,
        "model_version": "v1.0", "country_of_origin": meta["country"], "power_supply": meta["power"],
        "expected_lifespan_years": meta["lifespan"], "medical_device_class": meta["class"],
        "risk_classification": meta["risk"], "gmdn_code": meta["gmdn"], "emdn_code": meta["emdn"],
        "registration_required": 1, "is_radiation_device": meta["is_rad"],
        "is_pm_required": 1, "pm_interval_days": meta["pm_days"], "pm_alert_days": 14,
        "is_calibration_required": 1, "calibration_interval_days": meta["cal_days"],
        "calibration_alert_days": 30, "default_calibration_type": "External",
        "notes": f"{model_name} — {mfg} ({meta['country']})",
    }
    if category: doc_data["asset_category"] = category
    doc = frappe.get_doc(doc_data).insert(ignore_permissions=True)
    print(f"  [+] Tạo Device Model: {model_name} ({mfg})")
    return doc.name


def _force_delete_asset(name: str) -> bool:
    """Cancel (nếu submitted) → delete. Trả True nếu xóa được."""
    try:
        doc = frappe.get_doc("AC Asset", name)
        if doc.docstatus == 1:
            doc.flags.ignore_permissions = True
            doc.cancel()
            print(f"  [cancel] {name}")
        frappe.delete_doc("AC Asset", name, force=1, ignore_permissions=True, ignore_missing=True)
        return True
    except Exception as e:
        # Có thể có linked records (Transfer, Incident, WO) chặn delete — thử db_set docstatus=2
        try:
            frappe.db.set_value("AC Asset", name, "docstatus", 2)
            frappe.db.delete("AC Asset", {"name": name})
            return True
        except Exception as e2:
            print(f"  ❌ Không thể xóa {name}: {type(e).__name__}/{type(e2).__name__}: {str(e)[:100]}")
            return False


def _force_delete_device_model(name: str) -> bool:
    try:
        frappe.delete_doc("IMM Device Model", name, force=1, ignore_permissions=True, ignore_missing=True)
        return True
    except Exception as e:
        print(f"  ❌ Không thể xóa Model {name}: {str(e)[:100]}")
        return False


def _gen_serial(code_prefix: str) -> str:
    return f"SN-{code_prefix}-{random.randint(100000, 999999)}"


def _gen_udi(gmdn: str) -> str:
    lot = f"LOT{random.randint(10000, 99999)}"
    exp_date = random.choice(["260131", "270630", "280831", "290430"])
    return f"(01){gmdn.ljust(14, '0')}(17){exp_date}(10){lot}"


def _gen_byt(code_prefix: str) -> str:
    year = random.choice([2022, 2023, 2024])
    num = random.randint(1, 999)
    return f"DK-BYT-{year}-{code_prefix}-{num:03d}"


def _gen_asset_code(code_prefix: str, exclude_name: str | None = None) -> str:
    """Sinh asset_code chưa bị trùng với asset khác."""
    for _ in range(100):
        code = f"HTM-{code_prefix}-{random.randint(1000, 99999)}"
        existing = frappe.db.exists("AC Asset", {"asset_code": code})
        if not existing or existing == exclude_name:
            return code
    # Fallback với UUID-suffix
    import uuid
    return f"HTM-{code_prefix}-{uuid.uuid4().hex[:8].upper()}"


def _gen_unique_serial(code_prefix: str, exclude_name: str | None = None) -> str:
    for _ in range(100):
        sn = _gen_serial(code_prefix)
        existing = frappe.db.exists("AC Asset", {"manufacturer_sn": sn})
        if not existing or existing == exclude_name:
            return sn
    import uuid
    return f"SN-{code_prefix}-{uuid.uuid4().hex[:10].upper()}"


# ─── Main ────────────────────────────────────────────────────────────────────

def hard_reset():
    """Xóa dữ liệu rác + ghi đè 100% bằng catalog thật."""
    frappe.set_user("Administrator")
    # Không seed — mỗi lần chạy sinh unique code khác nhau (tránh duplicate)

    print("═" * 72)
    print("HARD RESET — XÓA DỮ LIỆU UAT/TEST/DEMO + BƠM DỮ LIỆU Y TẾ THẬT")
    print("═" * 72)

    # ─── Bước 1: Xóa AC Asset rác ────────────────────────────────────────────
    print("\n[1/4] Quét & xóa AC Asset rác…")
    all_assets = frappe.get_all("AC Asset",
        fields=["name", "asset_name", "asset_code", "item_code"])
    junk_assets = [a for a in all_assets if _is_junk(
        a.asset_name, a.asset_code, a.item_code, a.name
    )]
    print(f"  Phát hiện {len(junk_assets)} AC Asset rác / tổng {len(all_assets)}")

    deleted_assets = 0
    for a in junk_assets:
        if _force_delete_asset(a.name):
            deleted_assets += 1
            print(f"  🗑  Xóa: {a.name} — {a.asset_name}")

    # Xóa nốt các Asset Submitted không edit được (locked) — user yêu cầu
    locked_assets = frappe.get_all("AC Asset", filters={"docstatus": 1}, pluck="name")
    for name in locked_assets:
        if _force_delete_asset(name):
            deleted_assets += 1
            print(f"  🗑  Xóa (locked): {name}")

    # ─── Bước 2: Xóa IMM Device Model rác ────────────────────────────────────
    print("\n[2/4] Quét & xóa IMM Device Model rác…")
    all_models = frappe.get_all("IMM Device Model",
        fields=["name", "model_name", "manufacturer"])
    junk_models = [m for m in all_models if _is_junk(m.model_name, m.manufacturer, m.name)]
    print(f"  Phát hiện {len(junk_models)} Device Model rác / tổng {len(all_models)}")

    deleted_models = 0
    for m in junk_models:
        if _force_delete_device_model(m.name):
            deleted_models += 1
            print(f"  🗑  Xóa Model: {m.name} — {m.model_name}")

    # ─── Bước 3: Đảm bảo dependencies (Department / Supplier / Category / Model) ─
    print("\n[3/4] Đảm bảo dependencies…")
    for entry in REAL_MEDICAL_ASSETS:
        _resolve_department(entry["department"])
    # Resolve all device models trong catalog
    model_cache: dict = {}
    for entry in REAL_MEDICAL_ASSETS:
        meta = REAL_ASSET_META[entry["asset_name"]]
        cat = _resolve_category(meta["category"])
        model_cache[entry["asset_name"]] = _ensure_device_model(entry, meta, cat)

    # ─── Bước 4: Ghi đè toàn bộ AC Asset còn lại bằng catalog thật ───────────
    print("\n[4/4] Ghi đè AC Asset còn lại bằng catalog thật…")
    remaining = frappe.get_all("AC Asset", pluck="name")
    print(f"  Tổng Asset cần overwrite: {len(remaining)}")

    updated = 0
    for name in remaining:
        catalog = random.choice(REAL_MEDICAL_ASSETS)
        meta = REAL_ASSET_META[catalog["asset_name"]]
        dept = _resolve_department(catalog["department"])
        supplier = _resolve_supplier(catalog["manufacturer"])
        category = _resolve_category(meta["category"])
        model_ref = model_cache.get(catalog["asset_name"])

        # Compute realistic dates
        purchase_date = add_years(nowdate(), -random.randint(1, 5))
        warranty_date = add_years(purchase_date, random.randint(2, 3))
        commissioning_date = add_days(purchase_date, random.randint(15, 60))

        code_prefix = meta["code_prefix"]
        asset_code = _gen_asset_code(code_prefix, exclude_name=name)
        serial_no = _gen_unique_serial(code_prefix, exclude_name=name)
        udi = _gen_udi(meta["gmdn"])
        byt = _gen_byt(code_prefix)
        gross_amount = meta["price"]

        # Build payload
        payload = {
            # Core identifiers
            "asset_name": catalog["asset_name"],
            "asset_code": asset_code,
            "item_code": asset_code.replace("HTM-", "ITM-"),
            # Links
            "asset_category": category,
            "device_model": model_ref,
            "department": dept,
            "supplier": supplier,
            "custodian": "Administrator",
            "responsible_technician": "Administrator",
            # HTM / Pháp lý
            "manufacturer_sn": serial_no,
            "udi_code": udi,
            "gmdn_code": meta["gmdn"],
            "medical_device_class": meta["class"],
            "risk_classification": meta["risk"],
            "byt_reg_no": byt,
            "byt_reg_expiry": add_days(nowdate(), random.randint(180, 800)),
            # Mua sắm
            "purchase_date": purchase_date,
            "gross_purchase_amount": gross_amount,
            "warranty_expiry_date": warranty_date,
            "commissioning_date": commissioning_date,
            "commissioning_ref": f"ACC-{asset_code[-4:]}-{random.randint(1000, 9999)}",
            # Khấu hao
            "depreciation_method": "Straight Line",
            "useful_life_years": meta["lifespan"],
            "in_service_date": commissioning_date,
            "residual_value": int(gross_amount * 0.1),
            # PM
            "is_pm_required": 1,
            "pm_interval_days": meta["pm_days"],
            "last_pm_date": add_days(nowdate(), -random.randint(10, meta["pm_days"] // 2)),
            "next_pm_date": add_days(nowdate(), random.randint(15, meta["pm_days"])),
            # Calibration
            "is_calibration_required": 1,
            "calibration_interval_days": meta["cal_days"],
            "last_calibration_date": add_days(nowdate(), -random.randint(30, meta["cal_days"] // 2)),
            "next_calibration_date": add_days(nowdate(), random.randint(30, meta["cal_days"])),
            "calibration_status": "On Schedule",
            # Bảo hiểm
            "insurance_policy_no": f"BVINS-2024-{asset_code[-6:]}",
            "insurer_name": "Tổng Công ty Bảo hiểm Bảo Việt — CN TP.HCM",
            "insured_value": int(gross_amount * 1.1),
            "insurance_start_date": add_days(nowdate(), -180),
            "insurance_end_date": add_days(nowdate(), 185),
            # Status
            "status": "Active",
            "lifecycle_status": "Active",
            # Notes
            "notes": (
                f"<p><strong>{catalog['asset_name']}</strong></p>"
                f"<p>Model: {catalog['model']} · Hãng: {catalog['manufacturer']} "
                f"({meta['country']})</p>"
                f"<p>Serial: <code>{serial_no}</code> · Ngày mua: {purchase_date} · "
                f"Giá: {gross_amount:,} VND · Bảo hành đến: {warranty_date}</p>"
            ),
        }

        # Thử save() trước (trigger validation hooks)
        try:
            doc = frappe.get_doc("AC Asset", name)
            for field, value in payload.items():
                doc.set(field, value)
            doc.save(ignore_permissions=True)
            updated += 1
            print(f"  ✅ [{updated:>3}/{len(remaining)}] {name} → {catalog['asset_name']} ({catalog['manufacturer']})")
        except Exception as e:
            # Fallback: db_set từng field (bypass validation)
            try:
                frappe.db.set_value("AC Asset", name, payload)
                updated += 1
                print(f"  ⚠  [{updated:>3}/{len(remaining)}] {name} (db_set bypass) → {catalog['asset_name']}")
            except Exception as e2:
                print(f"  ❌ {name}: {type(e).__name__}: {str(e)[:80]} // {type(e2).__name__}: {str(e2)[:80]}")

    frappe.db.commit()

    print("\n" + "═" * 72)
    print(f"HOÀN TẤT HARD RESET")
    print(f"  • Xóa {deleted_assets} AC Asset rác/locked")
    print(f"  • Xóa {deleted_models} IMM Device Model rác")
    print(f"  • Ghi đè {updated}/{len(remaining)} Asset bằng catalog thật ({len(REAL_MEDICAL_ASSETS)} items)")
    print("═" * 72)
