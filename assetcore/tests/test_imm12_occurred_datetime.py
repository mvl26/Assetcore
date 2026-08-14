# Copyright (c) 2026, AssetCore Team
"""L-19 (audit BaoCao_RaSoat_AssetCore_17062026) — occurred_datetime guard.

`report_incident(occurred_datetime=...)` = thời điểm sự cố THỰC SỰ xảy ra
(phục vụ MTTR/MTBF & truy vết chronic):
  - tương lai  → ServiceError MSG.IMM12_OCCURRED_DATETIME_FUTURE (chặn).
  - quá khứ    → lưu verbatim.
  - rỗng       → fallback = reported_at (now).

Tách FILE RIÊNG (không sửa test_imm12.py — đang chỉnh ở phiên song song) để
tránh va chạm shared-file. BE guard đã có (services/imm12.py:385-391); đây là
test bao phủ (pin behavior) cho phần audit báo "no functional test".

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12_occurred_datetime
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import get_datetime

from assetcore.services.imm12 import report_incident
from assetcore.services.shared import ServiceError
from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name
from assetcore.utils.messages import MSG

_RUN_TAG = str(int(time.time() * 1000))[-7:]
_PAST = "2026-01-01 08:00:00"     # < hôm nay (2026-06-29)
_FUTURE = "2027-01-01 00:00:00"   # > hôm nay


def _ensure_cat() -> str:
    name = "_TestCatIMM12Occ"
    existing = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if existing:
        return existing
    return frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": name}
    ).insert(ignore_permissions=True).name


def _make_asset() -> str:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset OccDT-{_RUN_TAG}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": f"SN-OCC-{_RUN_TAG}",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True).name
    finally:
        frappe.flags.in_install = prev


class TestOccurredDatetimeGuard(unittest.TestCase):
    """L-19: future rejected · past verbatim · empty → reported_at."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        # R-9: fixture của setUpClass đã commit ⇒ KHÔNG được rollback tự động; thiếu
        # tearDownClass thì mỗi lượt chạy để lại 1 asset trên site (đo 2026-08-14).
        # Phải đi qua purge_asset: WR-03 (on_trash) chặn delete_doc khi còn Sự kiện
        # vòng đời, kể cả force=True.
        purge_asset(cls.asset)
        purge_category_by_name("_TestCatIMM12Occ")

    def setUp(self):
        frappe.set_user("Administrator")
        self._incidents: list[str] = []

    def tearDown(self):
        for name in self._incidents:
            frappe.delete_doc("Incident Report", name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()

    def _report(self, **kw) -> dict:
        res = report_incident(
            asset=self.asset,
            incident_type="Malfunction",
            severity="Medium",
            description="_Test occurred_datetime guard",
            **kw,
        )
        self._incidents.append(res["name"])
        return res

    def test_future_occurred_datetime_rejected(self):
        with self.assertRaises(ServiceError) as ctx:
            report_incident(
                asset=self.asset,
                incident_type="Malfunction",
                severity="Medium",
                description="_Test future occurred",
                occurred_datetime=_FUTURE,
            )
        self.assertEqual(
            getattr(ctx.exception, "message_code", ""),
            MSG.IMM12_OCCURRED_DATETIME_FUTURE,
            "occurred_datetime tương lai phải raise IMM12_OCCURRED_DATETIME_FUTURE",
        )

    def test_past_occurred_datetime_accepted_verbatim(self):
        res = self._report(occurred_datetime=_PAST)
        doc = frappe.get_doc("Incident Report", res["name"])
        self.assertEqual(get_datetime(doc.occurred_datetime), get_datetime(_PAST))

    def test_empty_occurred_datetime_falls_back_to_reported_at(self):
        res = self._report()
        doc = frappe.get_doc("Incident Report", res["name"])
        self.assertEqual(
            get_datetime(doc.occurred_datetime), get_datetime(doc.reported_at),
            "occurred_datetime rỗng phải = reported_at (now)",
        )


if __name__ == "__main__":
    unittest.main()
