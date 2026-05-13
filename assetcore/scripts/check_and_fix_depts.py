"""Check and fix AC Department records."""
import frappe


def run():
    frappe.set_user("Administrator")

    # Check current state
    depts = frappe.db.sql(
        "SELECT name, department_name, department_code FROM `tabAC Department`",
        as_dict=True
    )
    print("Current departments:", depts)

    # Delete and re-create with correct names
    for d in depts:
        frappe.delete_doc("AC Department", d["name"], force=True, ignore_permissions=True)
        print(f"  Deleted: {d['name']}")
    frappe.db.commit()

    departments = [
        {"department_name": "Khoa Hồi sức tích cực", "department_code": "ICU"},
        {"department_name": "Khoa Ngoại Tổng hợp", "department_code": "NGTH"},
        {"department_name": "Khoa Chẩn đoán Hình ảnh", "department_code": "CDHA"},
        {"department_name": "Phòng Mổ số 2", "department_code": "PMO2"},
        {"department_name": "Khoa Tim mạch can thiệp", "department_code": "TMCT"},
    ]

    for data in departments:
        doc = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": data["department_name"],
            "department_code": data["department_code"],
            "is_group": 0,
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created: {doc.name}")

    # Locations
    locs = frappe.db.sql("SELECT name FROM `tabAC Location`", as_dict=True)
    for l in locs:
        frappe.delete_doc("AC Location", l["name"], force=True, ignore_permissions=True)
    frappe.db.commit()

    locations = [
        {"location_name": "Phòng ICU — Tầng 3, Nhà A", "location_code": "LOC-ICU-3A", "clinical_area_type": "ICU", "infection_control_level": "High", "power_backup_available": 1},
        {"location_name": "Phòng Mổ số 2 — Tầng 5, Nhà B", "location_code": "LOC-PMO2-5B", "clinical_area_type": "Operating Room", "infection_control_level": "High", "power_backup_available": 1},
        {"location_name": "Phòng X-quang & Siêu âm — Tầng 1, Nhà C", "location_code": "LOC-CDHA-1C", "clinical_area_type": "Radiology", "infection_control_level": "Standard", "power_backup_available": 1},
        {"location_name": "Phòng Tim mạch can thiệp — Tầng 6, Nhà A", "location_code": "LOC-TMCT-6A", "clinical_area_type": "Catheterization Lab", "infection_control_level": "High", "power_backup_available": 1},
        {"location_name": "Kho Vật tư Trang thiết bị Y tế — Tầng B1", "location_code": "LOC-KHO-B1", "clinical_area_type": "Utility", "infection_control_level": "Standard", "power_backup_available": 0},
    ]

    for data in locations:
        doc = frappe.get_doc({"doctype": "AC Location", "is_group": 0, **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Location created: {doc.name}")

    # Asset categories
    cats = frappe.db.sql("SELECT name FROM `tabAC Asset Category`", as_dict=True)
    for c in cats:
        frappe.delete_doc("AC Asset Category", c["name"], force=True, ignore_permissions=True)
    frappe.db.commit()

    categories = [
        {
            "category_name": "Thiết bị Hỗ trợ Sự sống",
            "description": "Máy thở, máy bơm tim phổi nhân tạo, máy tạo nhịp tim — thiết bị Class III, ảnh hưởng trực tiếp đến tính mạng bệnh nhân",
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
            "description": "Monitor bệnh nhân, máy đo SpO2, ECG — thiết bị Class II theo dõi sinh hiệu liên tục",
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

    for data in categories:
        doc = frappe.get_doc({"doctype": "AC Asset Category", **data})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Category created: {doc.name}")

    print("\n✅ All reference data created!")
