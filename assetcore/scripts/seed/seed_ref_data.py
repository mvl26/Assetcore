"""
Seed reference data cho AssetCore test:
- 3 AC Department
- 3 AC Location
- 3 AC Asset Category
Run: bench --site miyano execute assetcore.scripts.seed.seed_ref_data.run
"""
import frappe


def run():
    frappe.set_user("Administrator")

    # --- AC Department (tree DocType) ---
    departments = [
        {
            "doctype": "AC Department",
            "department_name": "Khoa Hồi sức tích cực",
            "department_code": "ICU",
            "is_group": 0,
            "is_active": 1,
        },
        {
            "doctype": "AC Department",
            "department_name": "Khoa Ngoại Tổng hợp",
            "department_code": "NGTH",
            "is_group": 0,
            "is_active": 1,
        },
        {
            "doctype": "AC Department",
            "department_name": "Khoa Chẩn đoán Hình ảnh",
            "department_code": "CDHA",
            "is_group": 0,
            "is_active": 1,
        },
        {
            "doctype": "AC Department",
            "department_name": "Phòng Mổ số 2",
            "department_code": "PMO2",
            "is_group": 0,
            "is_active": 1,
        },
        {
            "doctype": "AC Department",
            "department_name": "Khoa Tim mạch can thiệp",
            "department_code": "TMCT",
            "is_group": 0,
            "is_active": 1,
        },
    ]

    created_depts = []
    for data in departments:
        existing = frappe.db.get_value("AC Department", {"department_name": data["department_name"]})
        if existing:
            print(f"  [skip] AC Department '{data['department_name']}' đã tồn tại: {existing}")
            created_depts.append(existing)
            continue
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  [ok] AC Department '{doc.name}' — {data['department_name']}")
        created_depts.append(doc.name)

    # --- AC Location (tree DocType) ---
    locations = [
        {
            "doctype": "AC Location",
            "location_name": "Phòng ICU — Tầng 3, Nhà A",
            "location_code": "LOC-ICU-3A",
            "is_group": 0,
            "clinical_area_type": "ICU",
            "infection_control_level": "High",
            "power_backup_available": 1,
            "contact_phone": "0909 123 456",
            "dept_head": "administrator",
        },
        {
            "doctype": "AC Location",
            "location_name": "Phòng Mổ số 2 — Tầng 5, Nhà B",
            "location_code": "LOC-PMO2-5B",
            "is_group": 0,
            "clinical_area_type": "Operating Room",
            "infection_control_level": "High",
            "power_backup_available": 1,
            "contact_phone": "0909 234 567",
        },
        {
            "doctype": "AC Location",
            "location_name": "Phòng X-quang & Siêu âm — Tầng 1, Nhà C",
            "location_code": "LOC-CDHA-1C",
            "is_group": 0,
            "clinical_area_type": "Radiology",
            "infection_control_level": "Standard",
            "power_backup_available": 1,
            "contact_phone": "0909 345 678",
        },
        {
            "doctype": "AC Location",
            "location_name": "Phòng Tim mạch can thiệp — Tầng 6, Nhà A",
            "location_code": "LOC-TMCT-6A",
            "is_group": 0,
            "clinical_area_type": "Catheterization Lab",
            "infection_control_level": "High",
            "power_backup_available": 1,
            "contact_phone": "0909 456 789",
        },
        {
            "doctype": "AC Location",
            "location_name": "Kho Vật tư Trang thiết bị Y tế — Tầng B1",
            "location_code": "LOC-KHO-B1",
            "is_group": 0,
            "clinical_area_type": "Utility",
            "infection_control_level": "Standard",
            "power_backup_available": 0,
            "contact_phone": "0909 567 890",
        },
    ]

    created_locs = []
    for data in locations:
        existing = frappe.db.get_value("AC Location", {"location_name": data["location_name"]})
        if existing:
            print(f"  [skip] AC Location '{data['location_name']}' đã tồn tại: {existing}")
            created_locs.append(existing)
            continue
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  [ok] AC Location '{doc.name}' — {data['location_name']}")
        created_locs.append(doc.name)

    # --- AC Asset Category ---
    categories = [
        {
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Hỗ trợ Sự sống (Life Support)",
            "description": "Máy thở, máy bơm tim phổi nhân tạo, máy tạo nhịp tim — thiết bị Class III, ảnh hưởng trực tiếp đến tính mạng bệnh nhân",
            "default_pm_required": 1,
            "default_pm_interval_days": 90,
            "default_calibration_required": 1,
            "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": 5.0,
            "is_active": 1,
        },
        {
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Chẩn đoán Hình ảnh",
            "description": "Máy siêu âm, X-quang, CT, MRI — thiết bị Class II/III phục vụ chẩn đoán",
            "default_pm_required": 1,
            "default_pm_interval_days": 180,
            "default_calibration_required": 1,
            "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": 5.0,
            "is_active": 1,
        },
        {
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Theo dõi Bệnh nhân",
            "description": "Monitor bệnh nhân, máy đo SpO2, ECG — thiết bị Class II theo dõi sinh hiệu liên tục",
            "default_pm_required": 1,
            "default_pm_interval_days": 180,
            "default_calibration_required": 1,
            "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": 84,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": 5.0,
            "is_active": 1,
        },
        {
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Phẫu thuật & Can thiệp",
            "description": "Máy điện phẫu, đèn mổ, bàn phẫu thuật, dụng cụ can thiệp tim mạch",
            "default_pm_required": 1,
            "default_pm_interval_days": 90,
            "default_calibration_required": 0,
            "default_calibration_interval_days": 0,
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": 5.0,
            "is_active": 1,
        },
    ]

    created_cats = []
    for data in categories:
        existing = frappe.db.get_value("AC Asset Category", {"category_name": data["category_name"]})
        if existing:
            print(f"  [skip] AC Asset Category '{data['category_name']}' đã tồn tại: {existing}")
            created_cats.append(existing)
            continue
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  [ok] AC Asset Category '{doc.name}' — {data['category_name']}")
        created_cats.append(doc.name)

    print("\n✅ Seed reference data hoàn tất!")
    print(f"  Departments: {created_depts[:3]}")
    print(f"  Locations: {created_locs[:3]}")
    print(f"  Categories: {created_cats[:3]}")
    return {"departments": created_depts, "locations": created_locs, "categories": created_cats}
