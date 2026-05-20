# Copyright (c) 2026, AssetCore Team
"""Tests for Role Profile cleanup — model mới KHÔNG dùng Role Profile.

Verifies:
  - All legacy "IMM - *" Role Profiles removed
  - All AssetCore-branded "AssetCore — *" Role Profiles removed
  - setup_role_profiles.run() vẫn callable (idempotent cleanup) sau khi remap
    mô hình từ Role Profile sang Has Role trực tiếp.
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.setup.setup_role_profiles import run as cleanup_legacy


class TestRoleProfileWipe(unittest.TestCase):
    """Mô hình RBAC mới gán role trực tiếp qua Has Role — không dùng
    Role Profile. Test này khẳng định cleanup đã chạy xong."""

    @classmethod
    def setUpClass(cls) -> None:
        # Idempotent: chạy cleanup để xóa profile sót.
        cleanup_legacy()

    def test_no_legacy_imm_role_profiles_remain(self) -> None:
        """Legacy `IMM - *` Role Profiles must not exist."""
        legacy = frappe.get_all(
            "Role Profile",
            filters=[["name", "like", "IMM - %"]],
            pluck="name",
        )
        self.assertEqual(
            legacy, [],
            f"Legacy IMM Role Profiles still present: {legacy}",
        )

    def test_no_assetcore_branded_role_profiles_remain(self) -> None:
        """`AssetCore — *` Role Profiles must not exist (model mới bỏ)."""
        ac = frappe.get_all(
            "Role Profile",
            filters=[["name", "like", "AssetCore — %"]],
            pluck="name",
        )
        self.assertEqual(
            ac, [],
            f"AssetCore Role Profiles still present: {ac}. "
            "Run setup_role_profiles.run() or patch v3_2/001.",
        )

    def test_cleanup_is_idempotent(self) -> None:
        """Running cleanup twice should not raise."""
        cleanup_legacy()
        cleanup_legacy()
