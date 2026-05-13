# Copyright (c) 2026, AssetCore Team
"""Tests for AssetCore-branded Role Profile catalog.

Verifies:
  - All AssetCore-branded Role Profiles exist after migrate/seed
  - Each profile contains exactly the canonical role set (idempotent upsert)
  - Assigning a profile to a User grants its roles
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.setup.setup_role_profiles import (
    get_assetcore_profiles,
    run as seed_role_profiles,
)


class TestAssetCoreRoleProfiles(unittest.TestCase):
    """Ensure AssetCore Role Profile catalog is seeded and consistent."""

    @classmethod
    def setUpClass(cls) -> None:
        # Idempotent re-seed: safe on existing site
        seed_role_profiles()
        cls.catalog = get_assetcore_profiles()

    def test_all_role_profiles_exist_after_migrate(self) -> None:
        """Every profile in canonical catalog must exist as Role Profile doc."""
        missing = [
            name for name, _ in self.catalog
            if not frappe.db.exists("Role Profile", name)
        ]
        self.assertEqual(
            missing, [],
            f"Missing AssetCore Role Profiles: {missing}",
        )

    def test_role_profile_roles_match_catalog(self) -> None:
        """Each Role Profile must have the exact role set declared in catalog
        (filtered to roles that actually exist in the Role master)."""
        for name, expected_roles in self.catalog:
            with self.subTest(profile=name):
                if not frappe.db.exists("Role Profile", name):
                    self.fail(f"Role Profile not found: {name}")
                expected_valid = {
                    r for r in expected_roles if frappe.db.exists("Role", r)
                }
                actual = set(
                    frappe.get_all(
                        "Has Role",
                        filters={"parenttype": "Role Profile", "parent": name},
                        pluck="role",
                    )
                )
                self.assertEqual(
                    actual, expected_valid,
                    f"Role mismatch on '{name}': "
                    f"expected={expected_valid}, actual={actual}",
                )

    def test_assigning_profile_to_user_grants_roles(self) -> None:
        """Setting User.role_profile_name applies bundle roles to user."""
        test_user_email = "_test_role_profile@assetcore.local"
        # Cleanup if leftover from previous run
        if frappe.db.exists("User", test_user_email):
            frappe.delete_doc(
                "User", test_user_email,
                ignore_permissions=True, force=True, delete_permanently=True,
            )

        user = frappe.new_doc("User")
        user.email = test_user_email
        user.first_name = "Test"
        user.send_welcome_email = 0
        user.flags.ignore_permissions = True
        user.insert()

        profile_name = "AssetCore — Department Head"
        self.assertTrue(
            frappe.db.exists("Role Profile", profile_name),
            f"Test prerequisite missing: {profile_name}",
        )

        user.role_profile_name = profile_name
        user.flags.ignore_permissions = True
        user.save()
        user.reload()

        granted = {r.role for r in user.roles}
        expected = {
            r for r in dict(self.catalog)[profile_name]
            if frappe.db.exists("Role", r)
        }
        self.assertTrue(
            expected.issubset(granted),
            f"Profile assignment did not grant expected roles. "
            f"expected_subset={expected}, granted={granted}",
        )

        # Cleanup
        frappe.delete_doc(
            "User", test_user_email,
            ignore_permissions=True, force=True, delete_permanently=True,
        )

    def test_seed_is_idempotent(self) -> None:
        """Running seed twice should not duplicate roles or profiles."""
        before = {
            name: frappe.get_all(
                "Has Role",
                filters={"parenttype": "Role Profile", "parent": name},
                pluck="role",
            )
            for name, _ in self.catalog
        }
        seed_role_profiles()
        after = {
            name: frappe.get_all(
                "Has Role",
                filters={"parenttype": "Role Profile", "parent": name},
                pluck="role",
            )
            for name, _ in self.catalog
        }
        for name in before:
            self.assertEqual(
                sorted(before[name]), sorted(after[name]),
                f"Roles changed after re-seed on '{name}'",
            )
