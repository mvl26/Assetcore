# Copyright (c) 2026, AssetCore Team
"""TC-PATCH-011 — patch đồng bộ ``workflow_state ← status`` (ADR-CORE-01).

Patch sửa DỮ LIỆU LỊCH SỬ trên site khách nên phải chứng minh 3 điều TRƯỚC khi ai đó
chạy ``bench migrate``:

  1. **Chạy đôi cho cùng kết quả** — lần 2 sửa 0 bản ghi. Patch không idempotent sẽ gây
     hại mỗi lần migrate lại.
  2. **Không chép giá trị rác** — ``status`` nằm ngoài danh sách state của workflow thì
     BỎ QUA và báo cáo, thay vì đẩy rác sang trục trạng thái mới.
  3. **Không đụng bản ghi đã khớp** — kể cả trường `modified`, để không làm nhiễu các
     job đồng bộ theo mốc thời gian.

Test tự dựng dữ liệu lệch rồi dọn sạch; KHÔNG chạy ``bench migrate``.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_patch_backfill_workflow_state
"""
from __future__ import annotations

import importlib

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name

# Tên module patch bắt đầu bằng chữ số nên không import bằng cú pháp thường được.
backfill = importlib.import_module(
    "assetcore.patches.v3_2.011_backfill_workflow_state"
).backfill

_CAT_NAME = "PatchWFState Test Category"
_SCOPE = [("Incident Report", "status")]


class TestBackfillWorkflowState(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": _CAT_NAME,
            "category_code": "TEST-CAT-PWFS",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "PatchWFState Asset",
                "asset_category": cls.cat.name,
                "lifecycle_status": "Commissioned",
                "manufacturer_sn": "PWFS-SN-1",
            }).insert(ignore_permissions=True).name

            def _incident(status: str) -> str:
                return frappe.get_doc({
                    "doctype": "Incident Report",
                    "asset": cls.asset,
                    "reported_by": "Administrator",
                    "reported_at": frappe.utils.now_datetime(),
                    "incident_type": "Failure",
                    "severity": "Medium",
                    "status": status,
                    "description": "Fixture patch 011",
                }).insert(ignore_permissions=True).name

            cls.stale = _incident("Acknowledged")   # sẽ bị lệch workflow_state
            cls.aligned = _incident("Open")         # đã khớp sẵn
            cls.garbage = _incident("Open")         # sẽ bị nhét status rác
        finally:
            frappe.flags.in_install = prev

        # Dựng đúng tình trạng của site cũ: workflow_state đọng ở 'Open'.
        frappe.db.set_value("Incident Report", cls.stale, "workflow_state", "Open",
                            update_modified=False)
        frappe.db.set_value("Incident Report", cls.aligned, "workflow_state", "Open",
                            update_modified=False)
        # Giá trị rác: không phải state nào của workflow.
        frappe.db.sql(
            "update `tabIncident Report` set status=%s, workflow_state=%s where name=%s",
            ("Trạng Thái Rác", "Open", cls.garbage),
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for attr in ("stale", "aligned", "garbage"):
            name = getattr(cls, attr, None)
            if name:
                frappe.db.delete("Incident Report", {"name": name})
        purge_asset(getattr(cls, "asset", None))
        purge_category_by_name(_CAT_NAME)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        # Mỗi test phải bắt đầu từ CÙNG tình trạng lệch. Không có bước này thì test nào
        # chạy trước sẽ đồng bộ sẵn dữ liệu, và test idempotent (chạy sau theo thứ tự
        # bảng chữ cái) đo được 0 bản ghi rồi đỏ vì lý do sai.
        frappe.db.set_value("Incident Report", self.stale, "workflow_state", "Open",
                            update_modified=False)
        frappe.db.set_value("Incident Report", self.garbage, "workflow_state", "Open",
                            update_modified=False)

    def _ws(self, name: str) -> str:
        return frappe.db.get_value("Incident Report", name, "workflow_state")

    def test_backfill_aligns_stale_rows_then_is_idempotent(self) -> None:
        first = backfill(_SCOPE)
        self.assertEqual(self._ws(self.stale), "Acknowledged")
        self.assertGreaterEqual(first.get("Incident Report", 0), 1)

        # Chạy lần 2 trên cùng dữ liệu ⇒ 0 bản ghi bị sửa.
        second = backfill(_SCOPE)
        self.assertEqual(
            second.get("Incident Report", 0), 0,
            "Patch KHÔNG idempotent — chạy lại vẫn ghi, mỗi lần migrate lại là một lần rủi ro.",
        )

    def test_garbage_status_is_not_copied_to_workflow_state(self) -> None:
        backfill(_SCOPE)
        self.assertEqual(
            self._ws(self.garbage), "Open",
            "Giá trị `status` ngoài danh sách state của workflow đã bị chép sang trục mới.",
        )

    def test_already_aligned_row_is_left_untouched(self) -> None:
        before = frappe.db.get_value("Incident Report", self.aligned, "modified")
        backfill(_SCOPE)
        self.assertEqual(self._ws(self.aligned), "Open")
        self.assertEqual(
            frappe.db.get_value("Incident Report", self.aligned, "modified"), before,
            "Bản ghi đã khớp vẫn bị chạm vào `modified`.",
        )
