# Copyright (c) 2026, AssetCore Team
"""Seed UAT test data cho IMM-00 UOM.

Usage:
    bench --site <site> execute assetcore.scripts.uat_seed_uom.seed
    bench --site <site> execute assetcore.scripts.uat_seed_uom.cleanup
"""

from __future__ import annotations

import frappe

_UAT_UOM_TEST = ["Test-Viên", "Tạm-UOM-99"]

_UAT_PARTS = [
    # (part_code, part_name, stock_uom, purchase_uom)
    ("SP-UAT-01", "Găng tay y tế latex size M (UAT)",   "Cái", ""),
    ("SP-UAT-02", "Dung dịch NaCl 0.9% 500mL (UAT)",    "mL",  "Chai"),
    ("SP-UAT-03", "Kim tiêm 5mL (UAT)",                  "",    ""),   # missing stock_uom
    ("SP-BULK-1", "Bulk test 1 (UAT)",                    "",    ""),
    ("SP-BULK-2", "Bulk test 2 (UAT)",                    "",    ""),
    ("SP-BULK-3", "Bulk test 3 (UAT)",                    "",    ""),
]

_UAT_CONVERSIONS = [
    # (part_code, uom, factor, is_purchase_uom, is_issue_uom)
    ("SP-UAT-01", "Hộp",   100,  1, 0),
    ("SP-UAT-01", "Thùng", 1000, 0, 0),
    ("SP-UAT-02", "Chai",  500,  1, 1),
    ("SP-UAT-02", "L",     1000, 0, 0),
]


def seed():
    """Tạo UOM chuẩn + parts UAT + conversions."""
    from assetcore.services.uom import seed_ac_uoms
    created_uoms = seed_ac_uoms()
    print(f"[seed] UOM master: tạo thêm {len(created_uoms)} — {created_uoms}")

    # Ensure "Test-Viên" UOM for TC-UOM-02 cleanup later (if needed)
    for uom_name in []:  # empty — Test-Viên created in UI
        pass

    created_parts = 0
    for part_code, part_name, stock_uom, purchase_uom in _UAT_PARTS:
        if frappe.db.exists("AC Spare Part", {"part_code": part_code}):
            continue
        doc = frappe.get_doc({
            "doctype":       "AC Spare Part",
            "part_code":     part_code,
            "part_name":     part_name,
            "stock_uom":     stock_uom or None,
            "purchase_uom":  purchase_uom or None,
            "is_active":     1,
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        created_parts += 1
    print(f"[seed] AC Spare Part: tạo thêm {created_parts} dòng UAT")

    # Conversions
    added_conv = 0
    for part_code, uom, factor, is_purchase, is_issue in _UAT_CONVERSIONS:
        part = frappe.db.get_value("AC Spare Part", {"part_code": part_code}, "name")
        if not part:
            continue
        doc = frappe.get_doc("AC Spare Part", part)
        has = any(r.uom == uom for r in (doc.uom_conversions or []))
        if has:
            continue
        doc.append("uom_conversions", {
            "uom": uom, "conversion_factor": factor,
            "is_purchase_uom": is_purchase, "is_issue_uom": is_issue,
        })
        doc.save(ignore_permissions=True)
        added_conv += 1
    print(f"[seed] AC UOM Conversion: thêm {added_conv} dòng")

    frappe.db.commit()
    print("[seed] DONE — kiểm tra UI /inventory/uom")


def cleanup():
    """Xóa toàn bộ data UAT đã tạo."""
    deleted = 0

    # Remove UAT parts (cascade remove conversions)
    for part_code, *_ in _UAT_PARTS:
        name = frappe.db.get_value("AC Spare Part", {"part_code": part_code}, "name")
        if name:
            try:
                frappe.delete_doc("AC Spare Part", name, ignore_permissions=True, force=True)
                deleted += 1
            except Exception as e:
                print(f"[cleanup] Cannot delete {part_code}: {e}")
    print(f"[cleanup] AC Spare Part: xóa {deleted} dòng")

    # Remove test UOMs
    deleted_uom = 0
    for uom_name in _UAT_UOM_TEST:
        if frappe.db.exists("AC UOM", uom_name):
            try:
                frappe.delete_doc("AC UOM", uom_name, ignore_permissions=True)
                deleted_uom += 1
            except Exception as e:
                print(f"[cleanup] Cannot delete UOM {uom_name}: {e}")
    print(f"[cleanup] AC UOM: xóa {deleted_uom} UOM test")

    frappe.db.commit()
    print("[cleanup] DONE")


def assert_rules():
    """Tự kiểm tra một số business rules sau khi seed."""
    errors = []

    # SP-UAT-03 phải thiếu stock_uom
    sp03 = frappe.db.get_value("AC Spare Part", {"part_code": "SP-UAT-03"},
                                ["name", "stock_uom"], as_dict=True)
    if sp03 and sp03.stock_uom:
        errors.append(f"SP-UAT-03 không được có stock_uom, nhưng đang là '{sp03.stock_uom}'")

    # SP-UAT-01 phải có conversion Hộp=100
    sp01 = frappe.db.get_value("AC Spare Part", {"part_code": "SP-UAT-01"}, "name")
    if sp01:
        conv = frappe.db.get_value("AC UOM Conversion",
            {"parent": sp01, "uom": "Hộp"}, "conversion_factor")
        if not conv or float(conv) != 100:
            errors.append(f"SP-UAT-01 phải có quy đổi Hộp=100, got {conv}")

    # Đủ seed 20 UOM Việt Nam?
    vi_uoms = ["Cái", "Hộp", "Thùng", "mL", "L", "mg", "g"]
    for u in vi_uoms:
        if not frappe.db.exists("AC UOM", u):
            errors.append(f"UOM chuẩn '{u}' chưa được seed")

    if errors:
        print("[assert] FAIL:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("[assert] PASS — tất cả rules OK")

    return errors
