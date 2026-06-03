# Copyright (c) 2026, AssetCore Team
"""Tests Role Profile (Core Doc FE_Persona_Navigation.md §7.quinquies).

BE = Role Profile + Role Permission chuẩn Frappe; "persona" là khái niệm FE-only.
Verify:
  TRP1..TRP8 — seed 8 Role Profile (tên VI) idempotent; mỗi profile đúng bộ role;
               assign_role_profile clear+replace; lock role khi có profile.
  TRP11..TRP14 — ranh giới Phase 1.4: catalog key = tên Role Profile (KHÔNG
               persona_code); bộ role bất biến; BE role-path không còn chữ
               "persona"; thông báo lock theo "Role Profile".
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import frappe

from assetcore.api import user as user_api
from assetcore.setup.role_profile_catalog import (
    ROLE_PROFILE_CATALOG,
    PROFILE_NAMES,
    roles_for_profile,
    profile_name_to_roles,
)
from assetcore.setup.setup_role_profiles import seed_assetcore_role_profiles

_TECH = "Kỹ thuật viên"
_STORE = "Thủ kho phụ tùng"


class TestRoleProfile(unittest.TestCase):
    _TEST_EMAIL = "_test_rp_profile@assetcore.test"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        seed_assetcore_role_profiles()
        # User test thật để verify gán profile / khoá role.
        if not frappe.db.exists("User", cls._TEST_EMAIL):
            u = frappe.new_doc("User")
            u.email = cls._TEST_EMAIL
            u.first_name = "_Test"
            u.last_name = "RP Profile"
            u.send_welcome_email = 0
            u.user_type = "System User"
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            if frappe.db.exists("User", cls._TEST_EMAIL):
                frappe.db.set_value("User", cls._TEST_EMAIL, "role_profile_name", None)
                frappe.delete_doc("User", cls._TEST_EMAIL, force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass
        super().tearDownClass()

    # ── TRP1: 8 profile tồn tại, tên VI đúng ────────────────────────────────
    def test_trp1_eight_profiles_exist(self) -> None:
        for name in PROFILE_NAMES:
            self.assertTrue(
                frappe.db.exists("Role Profile", name),
                f"Role Profile thiếu: {name}",
            )
        self.assertEqual(len(PROFILE_NAMES), 8)

    # ── TRP2: profile "Kỹ thuật viên" chứa đúng bộ role ─────────────────────
    def test_trp2_tech_profile_roles(self) -> None:
        rows = frappe.get_all(
            "Has Role",
            filters={"parent": _TECH, "parenttype": "Role Profile"},
            pluck="role",
        )
        self.assertEqual(set(rows), set(roles_for_profile(_TECH)))

    # ── TRP3: seed idempotent — chạy 2 lần không nhân đôi ───────────────────
    def test_trp3_seed_idempotent(self) -> None:
        seed_assetcore_role_profiles()
        seed_assetcore_role_profiles()
        self.assertEqual(
            frappe.db.count("Role Profile", {"name": ("in", PROFILE_NAMES)}), 8
        )
        rows = frappe.get_all(
            "Has Role", filters={"parent": _STORE, "parenttype": "Role Profile"}, pluck="role"
        )
        # không nhân đôi rows
        self.assertEqual(len(rows), len(set(rows)))
        self.assertEqual(set(rows), set(roles_for_profile(_STORE)))

    # ── TRP4: assign_role_profile gán đúng bộ role ──────────────────────────
    def test_trp4_assign_sets_roles(self) -> None:
        user_api.assign_role_profile(self._TEST_EMAIL, _STORE)
        actual = {r.role for r in frappe.get_doc("User", self._TEST_EMAIL).roles}
        self.assertEqual(actual, set(roles_for_profile(_STORE)))

    # ── TRP5: đổi profile tech→store → role clear+replace ───────────────────
    def test_trp5_switch_profile_replaces_roles(self) -> None:
        user_api.assign_role_profile(self._TEST_EMAIL, _TECH)
        self.assertIn("PM User", {r.role for r in frappe.get_doc("User", self._TEST_EMAIL).roles})
        user_api.assign_role_profile(self._TEST_EMAIL, _STORE)
        roles = {r.role for r in frappe.get_doc("User", self._TEST_EMAIL).roles}
        self.assertNotIn("PM User", roles)  # bộ tech bị clear
        self.assertEqual(roles, set(roles_for_profile(_STORE)))

    # ── TRP6: user có profile → set_user_roles thủ công bị từ chối ──────────
    def test_trp6_manual_edit_rejected_when_profile_locked(self) -> None:
        user_api.assign_role_profile(self._TEST_EMAIL, _STORE)
        frappe.set_user("Administrator")
        res = user_api.set_user_roles(self._TEST_EMAIL, ["Compliance Manager"])
        # Bị từ chối (success=False, http 409) — role không đổi.
        self.assertFalse(res.get("success", True), f"Phải bị chặn, nhận: {res}")
        roles = {r.role for r in frappe.get_doc("User", self._TEST_EMAIL).roles}
        self.assertNotIn("Compliance Manager", roles)
        self.assertEqual(roles, set(roles_for_profile(_STORE)))

    # ── TRP7: bỏ profile → sửa thủ công thành công ──────────────────────────
    def test_trp7_manual_edit_ok_after_clearing_profile(self) -> None:
        user_api.assign_role_profile(self._TEST_EMAIL, "")  # bỏ profile
        self.assertIsNone(
            frappe.db.get_value("User", self._TEST_EMAIL, "role_profile_name") or None
        )
        frappe.set_user("Administrator")
        res = user_api.set_user_roles(self._TEST_EMAIL, ["Compliance Manager"])
        self.assertTrue(res.get("success"), f"Phải thành công, nhận: {res}")
        roles = {r.role for r in frappe.get_doc("User", self._TEST_EMAIL).roles}
        self.assertIn("Compliance Manager", roles)

    # ── TRP11: catalog key = tên Role Profile (KHÔNG persona_code) ──────────
    def test_trp11_catalog_keyed_by_profile_name(self) -> None:
        expected = {
            "Quản trị viên IT", "Trưởng phòng VT-TTBYT", "Trưởng xưởng kỹ thuật",
            "Kỹ thuật viên", "Cán bộ QA / Kiểm toán", "Cán bộ hồ sơ",
            "Thủ kho phụ tùng", "Trưởng khoa lâm sàng",
        }
        self.assertEqual(set(ROLE_PROFILE_CATALOG.keys()), expected)
        # Không còn persona_code làm khoá.
        for legacy_code in ("admin", "opsmgr", "workshop", "tech", "store", "qa", "doc", "clinical"):
            self.assertNotIn(legacy_code, ROLE_PROFILE_CATALOG)

    # ── TRP12: bộ role profile bất biến (vs §7.quater.2) ───────────────────
    def test_trp12_tech_roles_invariant(self) -> None:
        self.assertEqual(
            set(profile_name_to_roles()[_TECH]),
            {"PM User", "Repair User", "Calibration User", "Corrective User",
             "AssetCore System User"},
        )

    # ── TRP13: BE role-path không dùng "persona" như KHÁI NIỆM CODE ─────────
    # Acceptance #25: cấm persona làm identifier/key/biến/logic ở BE. Prose
    # giải thích "persona là FE-only" hoặc tham chiếu tên file Core Doc
    # (FE_Persona_Navigation.md) được phép — đó chính là cách ghi rõ ranh giới.
    def test_trp13_no_persona_as_code_concept_in_be_role_path(self) -> None:
        app_root = Path(frappe.get_app_path("assetcore"))
        targets = [
            app_root / "setup" / "role_profile_catalog.py",
            app_root / "setup" / "setup_role_profiles.py",
            app_root / "api" / "user.py",
        ]
        # persona như code: identifier/key (persona_code, PERSONA_..., .persona,
        # persona=, persona[...]). KHÔNG bắt prose tiếng Việt/Anh chứa từ "persona".
        code_pat = re.compile(
            r"persona_code|PERSONA_[A-Z]|\bpersona\s*[:=\[]|\.persona\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []
        for path in targets:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                # Bỏ phần comment (sau #) để chỉ soi CODE thật, không soi prose.
                code_part = line.split("#", 1)[0]
                # Bỏ tham chiếu tên file Core Doc (FE_Persona_Navigation.md).
                code_part = code_part.replace("FE_Persona_Navigation", "")
                if code_pat.search(code_part):
                    offenders.append(f"{path.name}:{i}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "BE role-path dùng 'persona' như khái niệm code:\n" + "\n".join(offenders),
        )

    # ── TRP14: thông báo lock theo "Role Profile", không "persona" ─────────
    def test_trp14_lock_message_says_role_profile(self) -> None:
        user_api.assign_role_profile(self._TEST_EMAIL, _STORE)
        err = user_api._profile_lock_error(self._TEST_EMAIL)
        self.assertIsNotNone(err)
        msg = err.get("error", "")
        self.assertIn("Role Profile", msg)
        self.assertNotIn("persona", msg.lower())
