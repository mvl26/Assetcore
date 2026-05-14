# Copyright (c) 2026, AssetCore Team
"""
cleanup_imm00.py — Xóa các Custom DocType IMM-00 User/Profile đã lỗi thời.

Chạy bằng bench:
    bench --site miyano execute assetcore.scripts.maintenance.cleanup_imm00.run

Lưu ý:
  - Chạy dry_run=True trước để xem trước các bước.
  - Sau khi chạy script, xóa thủ công các thư mục vật lý (xem PHYSICAL_DIRS bên dưới).
  - Chạy `bench migrate` để áp dụng thay đổi.
"""
from __future__ import annotations

import frappe

# ─── DocTypes cần xóa khỏi DB ─────────────────────────────────────────────────

_DOCTYPES_TO_DROP: list[str] = [
    "AC User Certification",   # child table của AC User Profile
    "AC User Role",            # child table của AC User Profile
    "AC User Profile",         # custom profile — thay bởi Frappe User + custom fields
]

# ─── Thư mục vật lý cần xóa THỦ CÔNG sau khi chạy script ─────────────────────
# (bench execute không xóa file — phải rm -rf tay)

PHYSICAL_DIRS: list[str] = [
    "apps/assetcore/assetcore/assetcore/doctype/ac_user_certification",
    "apps/assetcore/assetcore/assetcore/doctype/ac_user_role",
    "apps/assetcore/assetcore/assetcore/doctype/ac_user_profile",
]

# ─── Files code legacy cần xóa THỦ CÔNG ──────────────────────────────────────

LEGACY_FILES: list[str] = [
    "apps/assetcore/assetcore/api/user_profile.py",
    "apps/assetcore/frontend/src/api/userProfile.ts",
]


# ─── Logic ────────────────────────────────────────────────────────────────────

def _drop_doctype(name: str, dry_run: bool) -> dict:
    exists = frappe.db.exists("DocType", name)
    if not exists:
        return {"doctype": name, "action": "skip", "reason": "not found in DB"}

    if dry_run:
        return {"doctype": name, "action": "would_delete"}

    try:
        frappe.delete_doc("DocType", name, ignore_missing=True, force=True)
        return {"doctype": name, "action": "deleted"}
    except Exception as exc:
        return {"doctype": name, "action": "error", "error": str(exc)}


def run(dry_run: bool = False) -> dict:
    """Điểm vào chính — gọi từ bench execute."""
    mode = "DRY RUN" if dry_run else "LIVE"
    frappe.logger().info(f"[cleanup_imm00] Starting {mode}")

    results = []
    for dt in _DOCTYPES_TO_DROP:
        result = _drop_doctype(dt, dry_run)
        results.append(result)
        frappe.logger().info(f"[cleanup_imm00] {result}")

    if not dry_run:
        frappe.db.commit()

    print("\n" + "=" * 60)
    print(f"[cleanup_imm00] {mode} kết quả:")
    for r in results:
        status = r["action"].upper()
        print(f"  [{status}] {r['doctype']}")
        if "error" in r:
            print(f"    ERROR: {r['error']}")

    print("\n[cleanup_imm00] Sau khi chạy script, xóa thủ công các thư mục:")
    for d in PHYSICAL_DIRS:
        print(f"  rm -rf ~/frappe-bench/{d}")

    print("\n[cleanup_imm00] Sau khi xóa thư mục, xóa các file legacy:")
    for f in LEGACY_FILES:
        print(f"  rm ~/frappe-bench/{f}")

    print("\n[cleanup_imm00] Cuối cùng chạy:")
    print("  bench --site miyano migrate")
    print("=" * 60 + "\n")

    return {"mode": mode, "results": results}


def dry_run() -> dict:
    """Alias tiện lợi — preview không thay đổi DB."""
    return run(dry_run=True)
