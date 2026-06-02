# Copyright (c) 2026, AssetCore Team
"""R21 dead-role-name guard — contract test cho notification recipient roles.

Run: bench --site miyano run-tests --module assetcore.tests.test_notify_roles_contract

ROOT CAUSE (xem assetcore/services/shared/notify_roles.py): code cũ gửi email
tới persona-role không tồn tại ("IMM Workshop Lead", "IMM QA Officer", ...) ->
_get_role_emails trả [] -> email im lặng không tới ai.

Test này:
  TC-R21-01  Mọi role trong notify_roles.ALL_NOTIFY_ROLES PHẢI tồn tại trong
             Role table (chống tái phát dead-role âm thầm).
  TC-R21-02  Các literal dead-role KHÔNG còn xuất hiện trong code LIVE
             (tasks.py, services/inventory.py, services/imm00.py).
  TC-R21-03  _get_role_emails với role THẬT (đã có user) trả về email; với role
             KHÔNG tồn tại trả [] — chứng minh cơ chế silent-failure cũ.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import frappe

from assetcore.services.shared import notify_roles
from assetcore.utils.helpers import _get_role_emails

_APP_ROOT = Path(__file__).resolve().parents[1]  # apps/assetcore/assetcore

# Literal dead-role không được phép xuất hiện trong các file LIVE dưới đây.
_DEAD_LITERALS = [
    "IMM Workshop Lead",
    "IMM Operations Manager",
    "IMM QA Officer",
    "IMM Biomed Technician",
    "IMM Storekeeper",
    "IMM Auditor",
]
_LIVE_FILES = [
    _APP_ROOT / "tasks.py",
    _APP_ROOT / "services" / "inventory.py",
    _APP_ROOT / "services" / "imm00.py",
    _APP_ROOT / "services" / "imm04.py",
]


class TestNotifyRolesContract(unittest.TestCase):
    def test_tc_r21_01_all_notify_roles_exist(self):
        """Mọi role nhận notification phải là Role THẬT trong hệ thống."""
        missing = [
            r for r in sorted(notify_roles.ALL_NOTIFY_ROLES)
            if not frappe.db.exists("Role", r)
        ]
        self.assertEqual(
            missing, [],
            f"Dead notification role(s) — không tồn tại trong Role table: {missing}",
        )

    def test_tc_r21_02_no_dead_literals_in_live_code(self):
        """Literal dead-role không còn nằm trong code LIVE (chỉ comment được tha)."""
        offenders: list[str] = []
        for f in _LIVE_FILES:
            if not f.exists():
                continue
            for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]  # bỏ comment
                for lit in _DEAD_LITERALS:
                    if f'"{lit}"' in code or f"'{lit}'" in code:
                        offenders.append(f"{f.name}:{lineno} -> {lit}")
        self.assertEqual(
            offenders, [],
            "Dead-role literal còn trong code LIVE (phải dùng notify_roles.* "
            f"hoặc role thật): {offenders}",
        )

    def test_tc_r21_03_get_role_emails_silent_for_dead_role(self):
        """Chứng minh cơ chế cũ: role không tồn tại -> [] (im lặng)."""
        self.assertEqual(
            _get_role_emails(["IMM Workshop Lead"]), [],
            "Role không tồn tại phải trả [] — đây là lý do email im lặng",
        )
