# Copyright (c) 2026, AssetCore Team
"""Patch: remove 20 legacy "IMM - *" Role Profiles.

Superseded by the AssetCore-branded persona catalog ("AssetCore — *") which is
seeded by `assetcore.setup.setup_role_profiles.run`. This patch is idempotent:
running it again after legacy profiles are gone is a no-op.

Steps per profile:
  1. Unbind every User.role_profile_name pointing at the legacy profile
     (set to None) — user-level Has Role rows remain intact.
  2. Delete child `Has Role` rows where parenttype='Role Profile'.
  3. Delete the Role Profile doc with `force=True, ignore_permissions=True`.

Run manually:
    bench --site <site> execute \
        assetcore.patches.v3_1.005_remove_legacy_imm_role_profiles.execute
"""
from __future__ import annotations

import frappe

LEGACY_NAMES: list[str] = [
    "IMM - Biomed Technician",
    "IMM - Board Approver",
    "IMM - Clinical User",
    "IMM - Department Head",
    "IMM - Deputy Department Head",
    "IMM - Document Officer",
    "IMM - Field Technician",
    "IMM - Finance Officer",
    "IMM - HTM Engineer",
    "IMM - Internal Auditor",
    "IMM - Operations Manager",
    "IMM - Planning Officer",
    "IMM - Procurement Officer",
    "IMM - QA Officer",
    "IMM - Risk Officer",
    "IMM - Storekeeper",
    "IMM - System Administrator",
    "IMM - Training Officer",
    "IMM - Vendor Engineer",
    "IMM - Workshop Lead",
]


def execute() -> None:
    removed = 0
    unbound_users = 0

    for name in LEGACY_NAMES:
        if not frappe.db.exists("Role Profile", name):
            continue

        # 1. Unbind users still assigned to the legacy profile
        users = frappe.get_all(
            "User",
            filters={"role_profile_name": name},
            pluck="name",
        )
        for u in users:
            frappe.db.set_value("User", u, "role_profile_name", None)
            unbound_users += 1
            print(f"  Unbound user {u} from {name}")

        # 2. Delete child Has Role rows
        frappe.db.delete(
            "Has Role",
            {"parenttype": "Role Profile", "parent": name},
        )

        # 3. Delete the Role Profile
        frappe.delete_doc(
            "Role Profile",
            name,
            force=True,
            ignore_permissions=True,
        )
        removed += 1
        print(f"  Deleted Role Profile: {name}")

    frappe.db.commit()
    print(
        f"[AssetCore] Removed {removed} legacy IMM Role Profiles, "
        f"unbound {unbound_users} users."
    )
