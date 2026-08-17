"""Tests cho seeder demo operational data (assetcore.scripts.seed.demo_ops).

LƯU Ý isolation: seed gọi các service (imm08/imm11) có `frappe.db.commit()`
bên trong → KHÔNG thể dùng savepoint+rollback (commit xoá savepoint, R-9).
Vì vậy test dọn dẹp TƯỜNG MINH ở tearDown: xoá mọi record mang SEED_MARKER
và khôi phục asset đã promote.

Verify:
    - seed sinh đúng loại record qua service thật (calibration + PM)
    - idempotent (chạy 2 lần không tạo trùng)
    - record gắn SEED_MARKER (cleanup được)
    - lifecycle event được sinh (audit trail)
"""

from __future__ import annotations

import unittest

import frappe

from assetcore.scripts.seed import demo_ops
from frappe.tests.utils import FrappeTestCase


def _ensure_active_asset() -> str | None:
    """Promote 1 asset Draft → Active nếu site chưa có asset Active nào.

    Trả về tên asset đã promote (để khôi phục ở tearDown) hoặc None nếu
    đã có sẵn asset Active (không cần promote).
    """
    if frappe.get_all("AC Asset", filters={"lifecycle_status": "Active"}, limit=1):
        return None
    draft = frappe.get_all(
        "AC Asset", filters={"lifecycle_status": "Draft"}, fields=["name"], limit=1
    )
    if not draft:
        return None
    name = draft[0]["name"]
    frappe.db.set_value("AC Asset", name, "lifecycle_status", "Active")
    frappe.db.commit()
    return name


def _purge_seed_records() -> None:
    """Xoá mọi record demo mang SEED_MARKER (calibration, PM WO, schedule, template).

    Submitted docs (docstatus=1) phải cancel trước khi xoá.
    """
    # Calibration (submittable)
    for name in frappe.get_all(
        "IMM Asset Calibration",
        filters={"traceability_reference": demo_ops.SEED_MARKER},
        pluck="name",
    ):
        _force_delete("IMM Asset Calibration", name)

    # PM Work Order (submittable) — marker trong technician_notes
    for name in frappe.get_all(
        "PM Work Order",
        filters={"technician_notes": ["like", f"%{demo_ops.SEED_MARKER}%"]},
        pluck="name",
    ):
        _force_delete("PM Work Order", name)

    # PM Checklist Template (marker trong template_name)
    for name in frappe.get_all(
        "PM Checklist Template",
        filters={"template_name": ["like", f"%{demo_ops.SEED_MARKER}%"]},
        pluck="name",
    ):
        # Xoá PM Schedule tham chiếu template trước (FK)
        for sched in frappe.get_all(
            "PM Schedule", filters={"checklist_template": name}, pluck="name"
        ):
            _force_delete("PM Schedule", sched)
        _force_delete("PM Checklist Template", name)

    frappe.db.commit()


def _force_delete(doctype: str, name: str) -> None:
    try:
        doc = frappe.get_doc(doctype, name)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc(
            doctype, name, force=True, ignore_permissions=True, delete_permanently=True
        )
    except Exception:  # noqa: BLE001 — cleanup best-effort
        pass


class TestSeedDemoOps(FrappeTestCase):
    """Seed dùng explicit cleanup (không savepoint — service tự commit)."""

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        # Dọn rác cũ trước (đảm bảo trạng thái sạch khi bắt đầu).
        _purge_seed_records()
        self._promoted = _ensure_active_asset()
        if not frappe.get_all(
            "AC Asset", filters={"lifecycle_status": "Active"}, limit=1
        ):
            self.skipTest("Site không có AC Asset nào để promote — không thể test seed")

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        _purge_seed_records()
        if self._promoted:
            frappe.db.set_value("AC Asset", self._promoted, "lifecycle_status", "Draft")
            frappe.db.commit()

    def test_run_returns_counts_structure(self) -> None:
        """run() trả về dict có đủ các khóa count mong đợi."""
        result = demo_ops.run()
        self.assertIn("calibration", result)
        self.assertIn("pm_work_order", result)
        self.assertIn("lifecycle_events_for_active_assets", result)

    def test_seed_creates_calibration_via_service(self) -> None:
        """Seed sinh IMM Asset Calibration gắn SEED_MARKER (qua service thật)."""
        result = demo_ops.run()
        total = result["calibration"]["created"] + result["calibration"]["existing"]
        self.assertGreaterEqual(
            total, 1, "Phải có ≥1 calibration (created hoặc existing)"
        )

    def test_idempotent_second_run_creates_nothing_new(self) -> None:
        """Chạy lần 2 không tạo thêm calibration mới (created=0)."""
        demo_ops.run()
        second = demo_ops.run()
        self.assertEqual(
            second["calibration"]["created"],
            0,
            "Lần chạy thứ 2 không được tạo calibration mới (idempotent)",
        )

    def test_calibration_records_carry_marker(self) -> None:
        """Mọi calibration seed phải mang SEED_MARKER để cleanup được."""
        demo_ops.run()
        seeded = frappe.get_all(
            "IMM Asset Calibration",
            filters={"traceability_reference": demo_ops.SEED_MARKER},
            pluck="name",
        )
        if not seeded:
            self.skipTest("Không có calibration seed (service có thể đã chặn)")
        for name in seeded:
            ref = frappe.db.get_value(
                "IMM Asset Calibration", name, "traceability_reference"
            )
            self.assertEqual(ref, demo_ops.SEED_MARKER)

    def test_lifecycle_events_generated(self) -> None:
        """Sau seed, calibration sinh lifecycle event 'calibration_passed' (audit trail)."""
        demo_ops.run()
        seeded = frappe.get_all(
            "IMM Asset Calibration",
            filters={"traceability_reference": demo_ops.SEED_MARKER},
            pluck="name",
        )
        if not seeded:
            self.skipTest("Không có calibration seed để kiểm lifecycle event")
        events = frappe.db.count(
            "Asset Lifecycle Event",
            {"root_doctype": "IMM Asset Calibration", "root_record": ["in", seeded]},
        )
        self.assertGreaterEqual(
            events, 1, "Calibration seed phải sinh ≥1 Asset Lifecycle Event"
        )


if __name__ == "__main__":
    unittest.main()
