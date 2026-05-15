# Copyright (c) 2026, AssetCore Team
# One-off cleanup: gỡ dữ liệu test/seed rò rỉ sang site thật (BUG-16-01/06).
#
# An toàn & idempotent. KHÔNG dùng SQL trực tiếp — chỉ Frappe ORM API.
# Chạy: bench --site <site> execute
#         assetcore.scripts.cleanup_imm16_test_data.run
from __future__ import annotations

from contextlib import suppress

import frappe


def _del(doctype: str, name: str) -> None:
    if frappe.db.exists(doctype, name):
        frappe.delete_doc(doctype, name, force=True,
                          ignore_permissions=True, ignore_on_trash=True)
        print(f"  deleted {doctype} {name}")


def run() -> None:
    """Xoá test fixtures: CAPA test, Finding gắn rule test, rule test,
    và các AC Asset có tên _Test Asset IMM08* cùng phụ thuộc."""
    frappe.set_user("Administrator")

    # 1. CAPA test-prefixed
    for nm in frappe.get_all("IMM CAPA Record",
                             filters={"name": ("like", "TEST-CAPA-%")},
                             pluck="name"):
        with suppress(Exception):
            _del("IMM CAPA Record", nm)

    # 2. Findings tham chiếu rule test (gỡ liên kết CAPA trước)
    for f in frappe.get_all("IMM Compliance Finding",
                            filters={"rule": "TEST-R-IMM08-PM-90"},
                            fields=["name", "capa_ref"]):
        if f.capa_ref and frappe.db.exists("IMM CAPA Record", f.capa_ref):
            with suppress(Exception):
                _del("IMM CAPA Record", f.capa_ref)
        with suppress(Exception):
            _del("IMM Compliance Finding", f.name)

    # 3. Rule test
    with suppress(Exception):
        _del("IMM Compliance Rule", "TEST-R-IMM08-PM-90")

    # 4. Test scorecards / MR / audits test-prefixed
    for dt, pref in (
        ("IMM Compliance Scorecard", "TEST-SCR-%"),
        ("IMM Management Review", "TEST-MR-%"),
        ("IMM Internal Audit", "TEST-AUD-%"),
    ):
        for nm in frappe.get_all(dt, filters={"name": ("like", pref)},
                                 pluck="name"):
            with suppress(Exception):
                _del(dt, nm)

    # 5. AC Asset _Test Asset IMM08* + CAPA/Finding tham chiếu
    test_assets = frappe.get_all(
        "AC Asset",
        filters={"asset_name": ("like", "_Test Asset IMM08%")},
        pluck="name",
    )
    for asset in test_assets:
        for dt in ("IMM CAPA Record", "IMM Compliance Finding"):
            for nm in frappe.get_all(dt, filters={"asset": asset},
                                     pluck="name"):
                with suppress(Exception):
                    _del(dt, nm)
        with suppress(Exception):
            _del("AC Asset", asset)

    frappe.db.commit()
    print("IMM-16 test data cleanup complete.")
