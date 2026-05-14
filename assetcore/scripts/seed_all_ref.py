"""
Seed toàn bộ reference data cho AssetCore test.
Run: bench --site miyano execute assetcore.scripts.seed_all_ref.run
"""
import frappe


def run():
    frappe.set_user("Administrator")

    # Xóa data cũ
    for name in frappe.db.sql("SELECT name FROM `tabAC Department`", as_list=True):
        frappe.delete_doc("AC Department", name[0], force=True, ignore_permissions=True)
    for name in frappe.db.sql("SELECT name FROM `tabAC Location`", as_list=True):
        frappe.delete_doc("AC Location", name[0], force=True, ignore_permissions=True)
    for name in frappe.db.sql("SELECT name FROM `tabAC Asset Category`", as_list=True):
        frappe.delete_doc("AC Asset Category", name[0], force=True, ignore_permissions=True)
    frappe.db.commit()
    print("Cleaned old ref data.")

    # --- DEPARTMENTS (no department_code → naming series, department_name stays) ---
    dept_data = [
        {"department_name": "Khoa Hồi sức tích cực", "is_group": 0, "is_active": 1},
        {"department_name": "Khoa Ngoại Tổng hợp", "is_group": 0, "is_active": 1},
        {"department_name": "Khoa Chẩn đoán Hình ảnh", "is_group": 0, "is_active": 1},
        {"department_name": "Phòng Mổ số 2", "is_group": 0, "is_active": 1},
        {"department_name": "Khoa Tim mạch can thiệp", "is_group": 0, "is_active": 1},
    ]
    dept_names = []
    for data in dept_data:
        doc = frappe.get_doc({"doctype": "AC Department", **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        dept_names.append(doc.name)
        print(f"  Dept: name={doc.name!r}, department_name={doc.department_name!r}")

    # --- LOCATIONS ---
    loc_data = [
        {"location_name": "Phòng ICU — Tầng 3, Nhà A", "is_group": 0,
         "clinical_area_type": "ICU", "infection_control_level": "Isolation",
         "power_backup_available": 1, "emergency_contact": "0909 123 456"},
        {"location_name": "Phòng Mổ số 2 — Tầng 5, Nhà B", "is_group": 0,
         "clinical_area_type": "Operating Room", "infection_control_level": "Isolation",
         "power_backup_available": 1, "emergency_contact": "0909 234 567"},
        {"location_name": "Phòng X-quang & Siêu âm — Tầng 1, Nhà C", "is_group": 0,
         "clinical_area_type": "Radiology", "infection_control_level": "Standard",
         "power_backup_available": 1, "emergency_contact": "0909 345 678"},
        {"location_name": "Phòng Tim mạch can thiệp — Tầng 6, Nhà A", "is_group": 0,
         "clinical_area_type": "Catheterization Lab", "infection_control_level": "Enhanced",
         "power_backup_available": 1, "emergency_contact": "0909 456 789"},
        {"location_name": "Kho Vật tư Thiết bị Y tế — Tầng B1", "is_group": 0,
         "clinical_area_type": "Utility", "infection_control_level": "Standard",
         "power_backup_available": 0, "emergency_contact": "0909 567 890"},
    ]
    loc_names = []
    for data in loc_data:
        doc = frappe.get_doc({"doctype": "AC Location", **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        loc_names.append(doc.name)
        print(f"  Location: {doc.name!r}")

    # --- ASSET CATEGORIES ---
    cat_data = [
        {
            "category_name": "Thiết bị Hỗ trợ Sự sống",
            "description": "Máy thở, máy bơm tim phổi nhân tạo, máy tạo nhịp tim — thiết bị Class III",
            "default_pm_required": 1, "default_pm_interval_days": 90,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiết bị Chẩn đoán Hình ảnh",
            "description": "Máy siêu âm, X-quang, CT, MRI — thiết bị Class II/III phục vụ chẩn đoán",
            "default_pm_required": 1, "default_pm_interval_days": 180,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 120,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiết bị Theo dõi Bệnh nhân",
            "description": "Monitor bệnh nhân, máy đo SpO2, ECG — thiết bị Class II",
            "default_pm_required": 1, "default_pm_interval_days": 180,
            "default_calibration_required": 1, "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line", "total_depreciation_months": 84,
            "depreciation_frequency": "Monthly", "default_residual_value_pct": 5.0, "is_active": 1,
        },
        {
            "category_name": "Thiết bị Phẫu thuật và Can thiệp",
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
        print(f"  Category: {doc.name!r}")

    print("\n=== RESULT ===")
    print(f"Departments: {dept_names}")
    print(f"Locations: {loc_names}")
    print(f"Categories: {cat_names}")
    print("✅ Reference data seeded!")
