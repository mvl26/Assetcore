"""Fix slugged display names → proper Vietnamese names for IMM-00 master data.

Per assetcore-test R-1: must use real hospital context. Names like 'Khoa-CDHA'
or 'Thiet-bi-Chan-doan-Hinh-anh' violate the rule when shown on UI.

Strategy: keep record name (id) as-is to preserve FK integrity. Update only the
human-readable display fields (department_name, location_name, category_name).
"""
import frappe


DEPT_NAMES = {
    "Khoa-HSTC": "Khoa Hồi sức tích cực (ICU)",
    "Khoa-NGTH": "Khoa Ngoại Tổng hợp",
    "Khoa-CDHA": "Khoa Chẩn đoán Hình ảnh",
    "Phong-Mo-2": "Phòng Mổ số 2",
    "Khoa-TMCT": "Khoa Tim mạch can thiệp",
}

CATEGORY_NAMES = {
    "Thiet-bi-Ho-tro-Su-song": "Thiết bị hỗ trợ sự sống",
    "Thiet-bi-Theo-doi-Benh-nhan": "Thiết bị theo dõi bệnh nhân",
    "Thiet-bi-Chan-doan-Hinh-anh": "Thiết bị chẩn đoán hình ảnh",
    "Thiet-bi-Phau-thuat-Can-thiep": "Thiết bị phẫu thuật & can thiệp",
}

LOCATION_NAMES = {
    "Phong-ICU-T3-NhaA": "Phòng ICU — Tầng 3, Nhà A",
    "Phong-Mo-2-T5-NhaB": "Phòng Mổ số 2 — Tầng 5, Nhà B",
    "Phong-Xquang-Sieuu-am-T1-NhaC": "Phòng Chẩn đoán Hình ảnh — Tầng 1, Nhà C",
    "Phong-Tim-mach-T6-NhaA": "Phòng Tim mạch can thiệp — Tầng 6, Nhà A",
    "Kho-Vat-tu-TTYT-Tang-B1": "Kho Vật tư Thiết bị Y tế — Tầng B1",
}

SUPPLIER_NAMES = {
    "AC-SUP-2026-0017": "Công ty TNHH Dräger Medical Vietnam",
    "AC-SUP-2026-0018": "Công ty CP Thiết bị Y tế Bình Minh",
    "AC-SUP-2026-0021": "Meditronic Vietnam Co., Ltd",
}


def run():
    # AC Department
    for name, label in DEPT_NAMES.items():
        if frappe.db.exists("AC Department", name):
            frappe.db.set_value("AC Department", name, "department_name", label)
            print(f"Department {name} -> {label}")

    # AC Asset Category
    for name, label in CATEGORY_NAMES.items():
        if frappe.db.exists("AC Asset Category", name):
            frappe.db.set_value("AC Asset Category", name, "category_name", label)
            print(f"Category {name} -> {label}")

    # AC Location
    for loc in frappe.get_all("AC Location", fields=["name", "location_name"]):
        new = LOCATION_NAMES.get(loc.location_name)
        if new:
            frappe.db.set_value("AC Location", loc.name, "location_name", new)
            print(f"Location {loc.name} -> {new}")

    # AC Supplier (already mostly fine, but normalize)
    for name, label in SUPPLIER_NAMES.items():
        if frappe.db.exists("AC Supplier", name):
            frappe.db.set_value("AC Supplier", name, "supplier_name", label)
            print(f"Supplier {name} -> {label}")

    # AC Asset: ensure depreciation_method defaulted
    for asset in frappe.get_all("AC Asset", fields=["name", "depreciation_method"]):
        updates = {}
        if not asset.depreciation_method:
            updates["depreciation_method"] = "Straight Line"
        if updates:
            for k, v in updates.items():
                frappe.db.set_value("AC Asset", asset.name, k, v)
            print(f"Asset {asset.name} -> {updates}")

    frappe.db.commit()
    print("DONE")
