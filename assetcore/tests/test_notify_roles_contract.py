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
from assetcore.tests._helpers.paths import APP_ROOT

_APP_ROOT = Path(APP_ROOT)

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
    _APP_ROOT / "services" / "imm16.py",
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

    def test_tc_r21_05_incident_sla_escalation_keys_exist_and_resolve(self):
        """TDD-7 (IMM-12): incident-SLA escalation block có trong notify_roles SSoT,
        resolve ra role THẬT tồn tại (anti RBAC-dead-gate).

        Khoá routing escalation incident-SLA (NĐ98 gate Critical/High) PHẢI:
          (a) khai báo trong notify_roles (INCIDENT_ESCALATION_QA / _OPS),
          (b) nằm trong ALL_NOTIFY_ROLES (guard test_tc_r21_01 phủ tồn tại),
          (c) trỏ role THẬT trong Role table (không dead-gate).
        """
        self.assertTrue(
            hasattr(notify_roles, "INCIDENT_ESCALATION_QA"),
            "Thiếu key INCIDENT_ESCALATION_QA cho escalation incident-SLA (IMM-12)",
        )
        self.assertTrue(
            hasattr(notify_roles, "INCIDENT_ESCALATION_OPS"),
            "Thiếu key INCIDENT_ESCALATION_OPS cho escalation incident-SLA (IMM-12)",
        )
        esc_roles = list(notify_roles.INCIDENT_ESCALATION_QA) + list(
            notify_roles.INCIDENT_ESCALATION_OPS
        )
        self.assertTrue(esc_roles, "Escalation block rỗng → không bao giờ resolve recipient")
        for r in esc_roles:
            self.assertIn(
                r, notify_roles.ALL_NOTIFY_ROLES,
                f"Role escalation '{r}' không nằm trong ALL_NOTIFY_ROLES (guard miss)",
            )
            self.assertTrue(
                frappe.db.exists("Role", r),
                f"Escalation role '{r}' không tồn tại trong Role table — RBAC dead-gate",
            )

    def test_tc_r21_04_no_raw_has_role_sql_in_services(self):
        """Toàn bộ truy vấn role->email PHẢI đi qua helpers._get_role_emails.

        Không service nào được tự viết raw SQL ``tabHas Role`` (role-literal
        hardcode -> dead-route âm thầm khi role rename). Điểm tập trung hợp lệ
        DUY NHẤT là ``assetcore/utils/helpers._get_role_emails`` (ngoài services/).
        """
        services_dir = _APP_ROOT / "services"
        offenders: list[str] = []
        for f in services_dir.rglob("*.py"):
            for lineno, line in enumerate(
                f.read_text(encoding="utf-8").splitlines(), 1
            ):
                code = line.split("#", 1)[0]  # bỏ comment
                if "tabHas Role" not in code:
                    continue
                # Real SQL dùng single-backtick table syntax: `tabHas Role`.
                # Docstring/prose RST dùng double-backtick: ``tabHas Role``.
                # Chỉ flag SQL thật, KHÔNG flag prose mô tả anti-pattern (false-positive).
                if "``tabHas Role``" in code:
                    continue
                offenders.append(f"{f.relative_to(_APP_ROOT)}:{lineno}")
        self.assertEqual(
            offenders, [],
            "Raw `tabHas Role` SQL còn trong services/ — phải route qua "
            f"helpers._get_role_emails (SSoT): {offenders}",
        )
