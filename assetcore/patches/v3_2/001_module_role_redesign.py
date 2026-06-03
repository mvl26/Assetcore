# Copyright (c) 2026, AssetCore Team
"""Wipe 19 persona + 11 legacy Role + Role/Module Profile. Idempotent.

KHÔNG xóa role do app khác (`normcore_dmktkt`/`norm_himedic`) hoặc Frappe core
sở hữu (`Internal Auditor`, `Norm*`, `Laboratory User`,
`Healthcare Administrator`, `System Manager`...). `Vendor Engineer` GIỮ
(re-scope qua DocPerm/fixture). Role mới do fixtures/JSON tạo khi
sync_fixtures sau patches.

Run:  bench --site <site> migrate  (patch tự chạy)
"""
from __future__ import annotations

import frappe

_PERSONA = [
    "IMM System Admin", "IMM Operations Manager", "IMM Department Head",
    "IMM Deputy Department Head", "IMM Workshop Lead", "IMM QA Officer",
    "IMM Biomed Technician", "IMM Technician", "IMM Document Officer",
    "IMM Storekeeper", "IMM Clinical User", "IMM Auditor",
    "IMM Planning Officer", "IMM Finance Officer", "IMM HTM Engineer",
    "IMM Procurement Officer", "IMM Risk Officer", "IMM Board Approver",
    "IMM Training Officer",
]
_LEGACY = [
    "IMM Manager", "Kho vật tư", "Workshop Manager", "Clinical Head",
    "CMMS Admin", "Tổ HC-QLCL", "QA Risk Team", "HTM Technician",
    "VP Block2", "Workshop Head", "Biomed Engineer",
]
_KILL_ROLES = _PERSONA + _LEGACY


def execute() -> None:
    # 1. Detach khỏi User
    frappe.db.delete("Has Role", {"role": ("in", _KILL_ROLES)})

    # 2. Xóa DocPerm/Custom DocPerm tham chiếu persona/legacy
    frappe.db.delete("DocPerm", {"role": ("in", _KILL_ROLES)})
    frappe.db.delete("Custom DocPerm", {"role": ("in", _KILL_ROLES)})

    # 3. Xóa Role Profile + Module Profile (mô hình mới bỏ)
    for dt in ("Role Profile", "Module Profile"):
        for n in frappe.get_all(dt, pluck="name"):
            try:
                frappe.delete_doc(
                    dt, n,
                    force=True, ignore_permissions=True,
                )
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"patch v3_2/001: delete {dt}:{n}",
                )

    # 4. Xóa role persona + legacy. KHÔNG xóa role do app khác / Frappe core.
    for r in _KILL_ROLES:
        if not frappe.db.exists("Role", r):
            continue
        try:
            frappe.delete_doc(
                "Role", r,
                force=True, ignore_permissions=True,
            )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"patch v3_2/001: delete Role:{r}",
            )

    # 5. Backfill umbrella: mọi user đang có Super Admin -> đảm bảo
    #    System Manager (idempotent).
    super_users = frappe.db.get_all(
        "Has Role",
        filters={"role": "AssetCore Super Admin", "parenttype": "User"},
        pluck="parent",
    )
    for u in super_users:
        if not frappe.db.exists("User", u):
            continue
        existing = frappe.db.get_all(
            "Has Role",
            filters={"parent": u, "parenttype": "User", "role": "System Manager"},
            pluck="name",
        )
        if existing:
            continue
        try:
            user = frappe.get_doc("User", u)
            user.append("roles", {"role": "System Manager"})
            user.flags.ignore_permissions = True
            user.save()
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"patch v3_2/001: backfill System Manager for {u}",
            )

    frappe.db.commit()
    print(
        f"[patch v3_2/001] Detached {len(_KILL_ROLES)} legacy roles; "
        f"backfilled System Manager for {len(super_users)} Super Admin user(s)."
    )
