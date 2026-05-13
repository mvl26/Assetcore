"""
Seed final reference data.
Run: bench --site miyano execute assetcore.scripts.seed_final_ref.run
"""
import frappe


def run():
    frappe.set_user("Administrator")

    # --- Xóa sạch ---
    for name in frappe.db.sql("SELECT name FROM `tabAC Department`", as_list=True):
        frappe.delete_doc("AC Department", name[0], force=True, ignore_permissions=True)
    for name in frappe.db.sql("SELECT name FROM `tabAC Location`", as_list=True):
        frappe.delete_doc("AC Location", name[0], force=True, ignore_permissions=True)
    for name in frappe.db.sql("SELECT name FROM `tabAC Asset Category`", as_list=True):
        frappe.delete_doc("AC Asset Category", name[0], force=True, ignore_permissions=True)
    frappe.db.commit()
    print("Cleaned.")

    # --- DEPARTMENTS (code = meaningful short name, also serves as display) ---
    # Note: department_name = department_code = name due to Frappe field:autoname sync
    dept_codes = [
        "Khoa-HSTC",   # Hồi sức tích cực
        "Khoa-NGTH",   # Ngoại Tổng hợp
        "Khoa-CDHA",   # Chẩn đoán Hình ảnh
        "Phong-Mo-2",  # Phòng Mổ số 2
        "Khoa-TMCT",   # Tim mạch can thiệp
    ]
    dept_names = []
    for code in dept_codes:
        doc = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": code,
            "department_code": code,
            "is_group": 0,
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        dept_names.append(doc.name)
        print(f"  Dept: {doc.name}")

    # --- LOCATIONS ---
    loc_data = [
        {"location_name": "Phong-ICU-T3-NhaA", "is_group": 0,
         "clinical_area_type": "ICU", "infection_control_level": "Isolation",
         "power_backup_available": 1, "emergency_contact": "0909 123 456"},
        {"location_name": "Phong-Mo-2-T5-NhaB", "is_group": 0,
         "clinical_area_type": "OR", "infection_control_level": "Isolation",
         "power_backup_available": 1, "emergency_contact": "0909 234 567"},
        {"location_name": "Phong-Xquang-Sieuu-am-T1-NhaC", "is_group": 0,
         "clinical_area_type": "Imaging", "infection_control_level": "Standard",
         "power_backup_available": 1, "emergency_contact": "0909 345 678"},
        {"location_name": "Phong-Tim-mach-T6-NhaA", "is_group": 0,
         "clinical_area_type": "OR", "infection_control_level": "Enhanced",
         "power_backup_available": 1, "emergency_contact": "0909 456 789"},
        {"location_name": "Kho-Vat-tu-TTYT-Tang-B1", "is_group": 0,
         "clinical_area_type": "Storage", "infection_control_level": "Standard",
         "power_backup_available": 0, "emergency_contact": "0909 567 890"},
    ]
    loc_names = []
    for data in loc_data:
        doc = frappe.get_doc({"doctype": "AC Location", **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        loc_names.append(doc.name)
        print(f"  Location: {doc.name}")

    # --- ASSET CATEGORIES ---
    cat_data = [
        {
            "category_name": "Thiet-bi-Ho-tro-Su-song",
            "description": "Máy thở, máy bơm tim phổi nhân tạo, máy tạo nhịp tim — thiết bị Class III, ảnh hưởng trực tiếp đến tính mạng bệnh nhân",
            "default_pm_required": 1, "default_pm_interval_days": 90,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiet-bi-Chan-doan-Hinh-anh",
            "description": "Máy siêu âm, X-quang, CT, MRI — thiết bị Class II/III phục vụ chẩn đoán hình ảnh",
            "default_pm_required": 1, "default_pm_interval_days": 180,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiet-bi-Theo-doi-Benh-nhan",
            "description": "Monitor bệnh nhân, máy đo SpO2, ECG — thiết bị Class II theo dõi sinh hiệu liên tục",
            "default_pm_required": 1, "default_pm_interval_days": 180,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 84,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiet-bi-Phau-thuat-Can-thiep",
            "description": "Máy điện phẫu, đèn mổ, bàn phẫu thuật, dụng cụ can thiệp tim mạch",
            "default_pm_required": 1, "default_pm_interval_days": 90,
            "default_calibration_required": 0, "default_calibration_interval_days": 0,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
    ]
    cat_names = []
    for data in cat_data:
        doc = frappe.get_doc({"doctype": "AC Asset Category", **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        cat_names.append(doc.name)
        print(f"  Category: {doc.name}")

    print("\n=== SUMMARY ===")
    print(f"Departments ({len(dept_names)}): {dept_names}")
    print(f"Locations ({len(loc_names)}): {loc_names}")
    print(f"Categories ({len(cat_names)}): {cat_names}")
    print("✅ Done!")
