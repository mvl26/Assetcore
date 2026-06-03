"""Permission tests cho AC Supplier DocPerm (VÒNG 12 RBAC fix).

Bối cảnh: persona "Trưởng phòng VT-TTBYT" (map Commissioning/Needs/Procurement/
Spec Manager) trước đây bị 403 khi đọc AC Supplier vì DocPerm thiếu các role này.
Quyết định BA: cấp READ cho cả 4 role; chỉ Procurement Manager được WRITE/CREATE
(owns supplier onboarding). Test này khoá quyết định đó + giữ boundary.
"""

from __future__ import annotations

import unittest

import frappe


def _make_user(roles: list[str]) -> str:
    """Tạo test user với danh sách role cho trước. Trả về email."""
    email = f"_test_supperm_{frappe.generate_hash()[:8]}@test.local"
    frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": "TestSupPerm",
            "enabled": 1,
            "roles": [{"role": r} for r in roles],
        }
    ).insert(ignore_permissions=True)
    return email


def _can_read(doctype: str) -> bool:
    return bool(frappe.has_permission(doctype, ptype="read"))


def _can_write(doctype: str) -> bool:
    return bool(frappe.has_permission(doctype, ptype="write"))


def _can_create(doctype: str) -> bool:
    return bool(frappe.has_permission(doctype, ptype="create"))


class TestACSupplierPermissions(unittest.TestCase):
    """DocPerm matrix cho AC Supplier sau RBAC fix vòng 12."""

    DOCTYPE = "AC Supplier"

    @classmethod
    def setUpClass(cls) -> None:
        frappe.set_user("Administrator")
        cls.procurement = _make_user(["Procurement Manager"])
        cls.spec = _make_user(["Spec Manager"])
        cls.needs = _make_user(["Needs Manager"])
        cls.commissioning = _make_user(["Commissioning Manager"])
        # Role hoàn toàn không liên quan supplier — giữ boundary.
        cls.unrelated = _make_user(["PM User"])

    @classmethod
    def tearDownClass(cls) -> None:
        frappe.set_user("Administrator")
        for email in (
            cls.procurement,
            cls.spec,
            cls.needs,
            cls.commissioning,
            cls.unrelated,
        ):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        frappe.db.commit()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    # ── READ: 4 role persona VT-TTBYT đều đọc được (fix 403) ──────────────

    def test_procurement_manager_can_read(self) -> None:
        frappe.set_user(self.procurement)
        try:
            self.assertTrue(_can_read(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_spec_manager_can_read(self) -> None:
        frappe.set_user(self.spec)
        try:
            self.assertTrue(_can_read(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_needs_manager_can_read(self) -> None:
        frappe.set_user(self.needs)
        try:
            self.assertTrue(_can_read(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_commissioning_manager_can_read(self) -> None:
        frappe.set_user(self.commissioning)
        try:
            self.assertTrue(_can_read(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    # ── WRITE/CREATE: chỉ Procurement Manager (least-privilege) ───────────

    def test_procurement_manager_can_write_and_create(self) -> None:
        frappe.set_user(self.procurement)
        try:
            self.assertTrue(_can_write(self.DOCTYPE))
            self.assertTrue(_can_create(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_spec_manager_cannot_write(self) -> None:
        frappe.set_user(self.spec)
        try:
            self.assertFalse(_can_write(self.DOCTYPE))
            self.assertFalse(_can_create(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_needs_manager_cannot_write(self) -> None:
        frappe.set_user(self.needs)
        try:
            self.assertFalse(_can_write(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    def test_commissioning_manager_cannot_write(self) -> None:
        frappe.set_user(self.commissioning)
        try:
            self.assertFalse(_can_write(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")

    # ── BOUNDARY: role không liên quan KHÔNG đọc được ─────────────────────

    def test_unrelated_role_cannot_read(self) -> None:
        """PM User thuần không có quyền trên AC Supplier — giữ boundary."""
        frappe.set_user(self.unrelated)
        try:
            self.assertFalse(_can_read(self.DOCTYPE))
        finally:
            frappe.set_user("Administrator")


if __name__ == "__main__":
    unittest.main()
