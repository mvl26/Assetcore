"""Seed UAT v2 cho IMM-04 — 5 dataset thực tế + master data.

Tạo:
  - 6 AC Department, 5 AC Location
  - 5 AC Supplier (map 1-1 với 5 ERPNext Supplier cùng supplier_name)
  - 5 IMM Device Model (đúng chuẩn UAT v2)
  - 5 ERPNext Item + 5 Purchase Order (cần cho po_reference)
  - 5 Asset Commissioning record: DS-01 → DS-05

Idempotent: chạy lại không tạo duplicate.
Run:
    bench --site miyano execute assetcore.scripts.seed.seed_imm04_uat_v2.run
"""
from __future__ import annotations
import frappe
from frappe.utils import add_days, nowdate

_DT_DEPT = "AC Department"
_DT_LOC = "AC Location"
_DT_SUPPLIER = "AC Supplier"
_DT_MODEL = "IMM Device Model"
_DT_COMM = "Asset Commissioning"
_DT_ITEM = "Item"
_DT_PO = "Purchase Order"
_DT_ERPNEXT_SUPPLIER = "Supplier"

_CLASS_II = "Class II"
_CLASS_III = "Class III"
_CATEGORY = "Medical Equipment"


def _upsert(doctype: str, filters: dict, data: dict, ignore_mandatory: bool = False) -> str:
    """Create or return existing doc by filters."""
    existing = frappe.db.exists(doctype, filters)
    if existing:
        return existing if isinstance(existing, str) else existing[0]
    doc = frappe.get_doc({"doctype": doctype, **data})
    if ignore_mandatory:
        doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


# ─────────────────────────────────────────────────────────────────────
# Master data
# ─────────────────────────────────────────────────────────────────────

DEPARTMENTS = [
    {"department_name": "Khoa Chẩn đoán Hình ảnh",        "department_code": "CDHA"},
    {"department_name": "Khoa Hồi sức Tích cực (ICU)",     "department_code": "ICU"},
    {"department_name": "Khoa Ung bướu",                   "department_code": "UB"},
    {"department_name": "Khoa Nội tổng hợp",               "department_code": "NOI"},
    {"department_name": "Phòng Mổ (OR)",                   "department_code": "OR"},
    {"department_name": "Khoa Kỹ thuật Y sinh",            "department_code": "KTYS"},
]

LOCATIONS = [
    ("CDHA - Phòng X-Quang 1",      "CDHA-XR1", "Imaging"),
    ("ICU - Giường 1",              "ICU-B01",  "ICU"),
    ("UB - Phòng Xạ trị A",         "UB-RT-A",  "Imaging"),
    ("NOI - Phòng 204",             "NOI-204",  "General Ward"),
    ("OR - Phòng Mổ 3",             "OR-03",    "OR"),
]

# AC Supplier name MUST match ERPNext Supplier.supplier_name for get_po_details mapping
SUPPLIERS = [
    {
        "supplier_name": "Công ty Philips Việt Nam",
        "supplier_code": "PHILIPS-VN",
        "vendor_type": "Distributor",
        "supplier_group": "Distributor",
        "country": "Vietnam",
    },
    {
        "supplier_name": "Dräger Medical VN",
        "supplier_code": "DRAGER-VN",
        "vendor_type": "Distributor",
        "supplier_group": "Distributor",
        "country": "Vietnam",
    },
    {
        "supplier_name": "Varian Medical Systems Asia",
        "supplier_code": "VARIAN-APAC",
        "vendor_type": "Manufacturer",
        "supplier_group": "Manufacturer",
        "country": "Singapore",
    },
    {
        "supplier_name": "B.Braun Medical VN",
        "supplier_code": "BBRAUN-VN",
        "vendor_type": "Distributor",
        "supplier_group": "Distributor",
        "country": "Vietnam",
    },
    {
        "supplier_name": "GE Healthcare VN",
        "supplier_code": "GE-VN",
        "vendor_type": "Distributor",
        "supplier_group": "Distributor",
        "country": "Vietnam",
    },
]

DEVICE_MODELS = [
    {
        "model_name": "Philips Affiniti 70 Ultrasound",
        "manufacturer": "Philips",
        "model_number": "Affiniti-70",
        "medical_device_class": _CLASS_II,
        "risk_classification": "Medium",
        "is_radiation_device": 0,
        "is_pm_required": 1, "pm_interval_days": 180,
        "is_calibration_required": 1, "calibration_interval_days": 365,
        "gmdn_code": "34576",
    },
    {
        "model_name": "Dräger Evita V300 Ventilator",
        "manufacturer": "Dräger",
        "model_number": "Evita-V300",
        "medical_device_class": _CLASS_III,
        "risk_classification": "Critical",
        "is_radiation_device": 0,
        "is_pm_required": 1, "pm_interval_days": 90,
        "is_calibration_required": 1, "calibration_interval_days": 365,
        "gmdn_code": "36263",
    },
    {
        "model_name": "Varian TrueBeam STx Linear Accelerator",
        "manufacturer": "Varian",
        "model_number": "TrueBeam-STx",
        "medical_device_class": _CLASS_III,
        "risk_classification": "Critical",
        "is_radiation_device": 1,
        "is_pm_required": 1, "pm_interval_days": 30,
        "is_calibration_required": 1, "calibration_interval_days": 180,
        "gmdn_code": "35749",
    },
    {
        "model_name": "B.Braun Perfusor Space Infusion Pump",
        "manufacturer": "B.Braun",
        "model_number": "Perfusor-Space",
        "medical_device_class": _CLASS_II,
        "risk_classification": "Medium",
        "is_radiation_device": 0,
        "is_pm_required": 1, "pm_interval_days": 365,
        "is_calibration_required": 1, "calibration_interval_days": 365,
        "gmdn_code": "13287",
    },
    {
        "model_name": "GE Vivid E95 Cardiac Ultrasound",
        "manufacturer": "GE",
        "model_number": "Vivid-E95",
        "medical_device_class": _CLASS_II,
        "risk_classification": "Medium",
        "is_radiation_device": 0,
        "is_pm_required": 1, "pm_interval_days": 180,
        "is_calibration_required": 1, "calibration_interval_days": 365,
        "gmdn_code": "34576",
    },
]


def _seed_departments() -> list[str]:
    return [_upsert(_DT_DEPT, {"department_name": d["department_name"]}, {**d, "is_active": 1}) for d in DEPARTMENTS]


def _seed_locations() -> list[str]:
    out = []
    for loc_name, loc_code, area_type in LOCATIONS:
        n = _upsert(_DT_LOC, {"location_name": loc_name}, {
            "location_name": loc_name,
            "location_code": loc_code,
            "clinical_area_type": area_type,
        })
        out.append(n)
    return out


def _seed_ac_suppliers() -> list[str]:
    out = []
    for s in SUPPLIERS:
        n = _upsert(_DT_SUPPLIER, {"supplier_name": s["supplier_name"]}, {**s, "is_active": 1})
        out.append(n)
    return out


def _seed_erpnext_suppliers() -> list[str]:
    """ERPNext Supplier — PO needs this. supplier_name must match AC Supplier."""
    out = []
    for s in SUPPLIERS:
        # ERPNext Supplier uses supplier_name as primary display; naming is autoname
        filters = {"supplier_name": s["supplier_name"]}
        existing = frappe.db.exists(_DT_ERPNEXT_SUPPLIER, filters)
        if existing:
            out.append(existing if isinstance(existing, str) else existing[0])
            continue
        # ERPNext Supplier Group must exist; fall back to safe defaults
        sg = s["supplier_group"] if frappe.db.exists("Supplier Group", s["supplier_group"]) else "All Supplier Groups"
        doc = frappe.get_doc({
            "doctype": _DT_ERPNEXT_SUPPLIER,
            "supplier_name": s["supplier_name"],
            "supplier_group": sg,
            "country": s["country"],
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        out.append(doc.name)
    return out


def _seed_device_models() -> list[str]:
    # Ensure category exists
    _upsert("AC Asset Category", {"category_name": _CATEGORY}, {
        "category_name": _CATEGORY,
        "default_pm_required": 1,
        "default_pm_interval_days": 180,
    })
    out = []
    for m in DEVICE_MODELS:
        data = {**m, "asset_category": _CATEGORY}
        n = _upsert(_DT_MODEL, {"model_name": m["model_name"], "manufacturer": m["manufacturer"]}, data)
        out.append(n)
    return out


def _seed_items_and_pos(erpnext_suppliers: list[str]) -> list[str]:
    """Tạo 5 ERPNext Item + 5 PO để phục vụ po_reference trong IMM-04."""
    items_po = [
        ("PHILIPS-AFF70",  "Philips Affiniti 70 Ultrasound",           0, erpnext_suppliers[0], 1_850_000_000),
        ("DRAGER-EV300",   "Dräger Evita V300 Ventilator",              1, erpnext_suppliers[1],   780_000_000),
        ("VARIAN-TB-STX",  "Varian TrueBeam STx Linear Accelerator",    2, erpnext_suppliers[2],65_000_000_000),
        ("BBRAUN-PS",      "B.Braun Perfusor Space Infusion Pump",      3, erpnext_suppliers[3],    42_500_000),
        ("GE-VIVID-E95",   "GE Vivid E95 Cardiac Ultrasound",           4, erpnext_suppliers[4], 2_150_000_000),
    ]
    po_names = []
    company = frappe.db.get_value("Company", {"abbr": "M"}, "name") or frappe.db.get_value("Company", {}, "name")
    for item_code, item_name, idx, supplier, price in items_po:
        _upsert(_DT_ITEM, {"item_code": item_code}, {
            "item_code": item_code, "item_name": item_name,
            "item_group": _CATEGORY, "stock_uom": "Nos",
            "is_fixed_asset": 1, "is_stock_item": 0,
            "asset_category": _CATEGORY,
        }, ignore_mandatory=True)

        po_expected = f"PO-UAT-2026-{idx+101:05d}"
        existing_po = frappe.db.exists(_DT_PO, {"custom_uat_ref": po_expected})
        if existing_po:
            po_names.append(existing_po if isinstance(existing_po, str) else existing_po[0])
            continue
        po = frappe.get_doc({
            "doctype": _DT_PO,
            "supplier": supplier,
            "company": company,
            "transaction_date": add_days(nowdate(), -30),
            "schedule_date": add_days(nowdate(), 7),
            "currency": "VND", "conversion_rate": 1,
            "items": [{
                "item_code": item_code, "qty": 1, "rate": price,
                "schedule_date": add_days(nowdate(), 7),
                "warehouse": frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name"),
            }],
        })
        po.flags.ignore_mandatory = True
        po.flags.ignore_permissions = True
        po.insert(ignore_permissions=True)
        try:
            po.submit()
        except Exception:
            pass  # keep draft if submit blocked by missing setup
        po_names.append(po.name)
    return po_names


# ─────────────────────────────────────────────────────────────────────
# 5 Commissioning Datasets
# ─────────────────────────────────────────────────────────────────────

BASELINE_PASS_ALL = [
    {"parameter": "Earth Continuity",    "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "0.3", "expected_min": 0, "expected_max": 0.5, "unit": "Ω",
     "test_result": "Pass", "fail_note": ""},
    {"parameter": "Insulation Resistance", "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "15", "expected_min": 2, "expected_max": None, "unit": "MΩ",
     "test_result": "Pass", "fail_note": ""},
    {"parameter": "Leakage Current",     "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "250", "expected_min": 0, "expected_max": 500, "unit": "µA",
     "test_result": "Pass", "fail_note": ""},
    {"parameter": "Visual Inspection",    "is_critical": 1, "measurement_type": "Pass/Fail",
     "measured_val": "", "expected_min": None, "expected_max": None, "unit": "",
     "test_result": "Pass", "fail_note": ""},
]

BASELINE_WITH_FAIL = [
    {"parameter": "Earth Continuity",    "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "0.3", "expected_min": 0, "expected_max": 0.5, "unit": "Ω",
     "test_result": "Pass", "fail_note": ""},
    {"parameter": "Insulation Resistance", "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "15", "expected_min": 2, "expected_max": None, "unit": "MΩ",
     "test_result": "Pass", "fail_note": ""},
    {"parameter": "Leakage Current",     "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": "650", "expected_min": 0, "expected_max": 500, "unit": "µA",
     "test_result": "Fail", "fail_note": "Rò dòng vượt giới hạn — cần replace PCB chính"},
    {"parameter": "Visual Inspection",    "is_critical": 1, "measurement_type": "Pass/Fail",
     "measured_val": "", "expected_min": None, "expected_max": None, "unit": "",
     "test_result": "Pass", "fail_note": ""},
]


def _build_commissioning_datasets(depts, locs, sups, models, pos):
    """DS-01 → DS-05 theo IMM-04_UAT_Script_v2.md §1.2–1.6."""
    return [
        {  # DS-01 — Class II Happy Path
            "po_reference": pos[0], "master_item": models[0], "vendor": sups[0],
            "clinical_dept": depts[0], "installation_location": locs[0],
            "asset_description": "Máy siêu âm Philips Affiniti 70 — CDHA-US-01",
            "delivery_note_no": "DN-2026-0101",
            "purchase_price": 1_850_000_000,
            "warranty_expiry_date": "2028-04-30",
            "expected_installation_date": add_days(nowdate(), 2),
            "reception_date": nowdate(),
            "vendor_engineer_name": "Kim Jae-hoon (Philips Korea)",
            "vendor_serial_no": "PH-AFF70-SN00123456",
            "baseline_tests": BASELINE_PASS_ALL,
        },
        {  # DS-02 — Class III Clinical Hold
            "po_reference": pos[1], "master_item": models[1], "vendor": sups[1],
            "clinical_dept": depts[1], "installation_location": locs[1],
            "asset_description": "Máy thở Dräger Evita V300 — ICU-VENT-01",
            "delivery_note_no": "DN-2026-0102",
            "purchase_price": 780_000_000,
            "warranty_expiry_date": "2027-05-15",
            "expected_installation_date": add_days(nowdate(), 4),
            "reception_date": nowdate(),
            "vendor_engineer_name": "Müller (Dräger DE)",
            "vendor_serial_no": "DR-EV300-SN77881122",
            "baseline_tests": BASELINE_PASS_ALL,
        },
        {  # DS-03 — Radiation Device (Linear Accelerator)
            "po_reference": pos[2], "master_item": models[2], "vendor": sups[2],
            "clinical_dept": depts[2], "installation_location": locs[2],
            "asset_description": "Máy xạ trị Varian TrueBeam STx — UB-LINAC-01",
            "delivery_note_no": "DN-2026-0103",
            "purchase_price": 65_000_000_000,
            "warranty_expiry_date": "2029-01-20",
            "expected_installation_date": add_days(nowdate(), 27),
            "reception_date": nowdate(),
            "vendor_engineer_name": "Johnson (Varian USA)",
            "vendor_serial_no": "VAR-TB-SN-H7A2K9",
            "radiation_license_no": "CATBXHN-2026-0087",
            "baseline_tests": BASELINE_PASS_ALL,
        },
        {  # DS-04 — Baseline Fail → Re-Inspection
            "po_reference": pos[3], "master_item": models[3], "vendor": sups[3],
            "clinical_dept": depts[3], "installation_location": locs[3],
            "asset_description": "Bơm tiêm B.Braun Perfusor Space — NOI-PUMP-05",
            "delivery_note_no": "DN-2026-0104",
            "purchase_price": 42_500_000,
            "warranty_expiry_date": "2028-03-10",
            "expected_installation_date": add_days(nowdate(), 3),
            "reception_date": nowdate(),
            "vendor_engineer_name": "Schmidt (B.Braun DE)",
            "vendor_serial_no": "BB-PS-SN-55443322",
            "baseline_tests": BASELINE_WITH_FAIL,  # ← Leakage Fail
        },
        {  # DS-05 — DOA Incident → Return to Vendor
            "po_reference": pos[4], "master_item": models[4], "vendor": sups[4],
            "clinical_dept": depts[0], "installation_location": locs[0],
            "asset_description": "Máy siêu âm tim GE Vivid E95 — CDHA-US-02",
            "delivery_note_no": "DN-2026-0105",
            "purchase_price": 2_150_000_000,
            "warranty_expiry_date": "2028-04-30",
            "expected_installation_date": add_days(nowdate(), 5),
            "reception_date": nowdate(),
            "vendor_engineer_name": "Park (GE Korea)",
            "vendor_serial_no": "GE-VE95-SN99887766",
            "doa_incident": 1,
            "baseline_tests": [],  # DOA xảy ra trước baseline
        },
    ]


_MANDATORY_DOC_TYPES = [
    ("CO - Chứng nhận Xuất xứ",    1),
    ("CQ - Chứng nhận Chất lượng", 1),
    ("Manual / HDSD",              1),
    ("Warranty Card",              0),
]


def _build_one_commissioning(ds: dict):
    """Build single Asset Commissioning doc with pre-populated child tables."""
    doc_data = {k: v for k, v in ds.items() if k != "baseline_tests"}
    doc = frappe.get_doc({"doctype": _DT_COMM, **doc_data})

    # Pre-populate commissioning_documents BEFORE insert → initialize_commissioning will skip
    for doc_type, mandatory in _MANDATORY_DOC_TYPES:
        doc.append("commissioning_documents", {
            "doc_type": doc_type,
            "is_mandatory": mandatory,
            "status": "Received" if mandatory else "Pending",
            "received_date": nowdate() if mandatory else None,
        })

    for row in ds.get("baseline_tests", []):
        doc.append("baseline_tests", row)

    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _seed_commissioning_records(datasets) -> list[str]:
    """Tạo 5 Asset Commissioning. Pre-populate mandatory docs as Received để pass G01."""
    created = []
    for i, ds in enumerate(datasets, start=1):
        existing = frappe.db.exists(_DT_COMM, {"vendor_serial_no": ds["vendor_serial_no"]})
        if existing:
            name = existing if isinstance(existing, str) else existing[0]
            created.append(f"DS-{i:02d}: {name} (existing)")
            continue
        new_name = _build_one_commissioning(ds)
        created.append(f"DS-{i:02d}: {new_name}")
    return created


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

def run():
    print("▶ Seeding IMM-04 UAT v2 master data...")
    depts = _seed_departments()
    print(f"  ✓ {len(depts)} AC Department")
    locs = _seed_locations()
    print(f"  ✓ {len(locs)} AC Location")
    ac_sups = _seed_ac_suppliers()
    print(f"  ✓ {len(ac_sups)} AC Supplier")
    erp_sups = _seed_erpnext_suppliers()
    print(f"  ✓ {len(erp_sups)} ERPNext Supplier")
    models = _seed_device_models()
    print(f"  ✓ {len(models)} IMM Device Model")
    pos = _seed_items_and_pos(erp_sups)
    print(f"  ✓ {len(pos)} ERPNext Item + Purchase Order")

    frappe.db.commit()

    print("\n▶ Seeding 5 Asset Commissioning datasets...")
    datasets = _build_commissioning_datasets(depts, locs, ac_sups, models, pos)
    created = _seed_commissioning_records(datasets)
    for c in created:
        print(f"  ✓ {c}")

    frappe.db.commit()
    print("\n✓ IMM-04 UAT v2 seed DONE — 5 datasets ready for test execution")
    print("  Review in UI: /app/asset-commissioning")
    return {"depts": depts, "locs": locs, "ac_sups": ac_sups, "models": models, "pos": pos, "commissioning": created}
