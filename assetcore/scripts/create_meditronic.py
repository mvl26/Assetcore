"""Create Meditronic supplier directly."""
import frappe


def run():
    frappe.set_user("Administrator")
    doc = frappe.new_doc("AC Supplier")
    doc.update({
        "supplier_name": "Meditronic Vietnam Co. Ltd",
        "vendor_type": "Service",
        "country": "Vietnam",
        "email_id": "contact@meditronic.vn",
        "phone": "028 3547 8800",
        "mobile_no": "0912 345 678",
        "website": "www.meditronic.vn",
        "address": "34 Le Duan, Quan 1, TP.HCM",
        "tax_id": "0315678901",
        "contract_start": "2024-06-15",
        "contract_end": "2027-06-14",
        "iso_13485_cert": "ISO13485-MDT-2023-VN-015",
        "iso_13485_expiry": "2026-06-30",
        "iso_17025_cert": "VILAS-MDT-2024-0312",
        "iso_17025_expiry": "2027-06-30",
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Created: {doc.name} — {doc.supplier_name}")
