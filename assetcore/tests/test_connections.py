# Copyright (c) 2026, AssetCore Team
"""TC-CONN-API — endpoint chung ``assetcore.api.connections.get_connections``.

Kiểm 4 nhóm bất biến:
  1. **Đầu vào xấu** không làm vỡ màn chi tiết (doctype lạ / mã lạ / doctype chưa khai
     đồ thị đều trả có kiểm soát, KHÔNG 500).
  2. **Đếm đúng** theo đồ thị đã khai, kể cả khi Link field không cùng tên (
     ``non_standard_fieldnames`` — vd ``PM Work Order.asset_ref``).
  3. **Phân quyền THẬT**: chạy dưới session user, KHÔNG ``ignore_permissions``. Doctype
     ngoài quyền bị ẩn hẳn; row ngoài scope không được đếm. Đây là phần dễ hỏng nhất —
     một endpoint "chỉ đếm" vẫn rò rỉ được quy mô dữ liệu toàn viện nếu đếm sai đường.
  4. **Hợp đồng với FE**: mỗi ô trả ``deep_link_filters`` đủ để FE tự dựng link drill,
     không phải đoán tên field.

AC-CR-92 (ADR §17 · bảng migration §17.2.2) **DỜI** assert legacy sang khoá cùng tính
chất (``count`` → ``total`` · ``assertFalse(capped)`` → ``total_capped == 0`` ·
``filters`` → ``deep_link_filters``) — 0 TC bị xoá, và
``test_counts_run_under_session_user_not_administrator`` giữ **0 dòng sửa** vì nó là
bằng chứng RATIFY cổng I/O (D-CR92-6).

Run:
  bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections
"""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.connections import get_connections
from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name

_CAT_NAME = "ConnAPI Test Category"
_LIMITED_EMAIL = "conn_limited@example.com"


def _insert_bypassing_workflow(data: dict):
    """Insert fixture bỏ qua workflow lifecycle (giống các test IMM-00 khác)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestGetConnections(FrappeTestCase):
    """Bản ghi liên quan của AC Asset — đếm, phân quyền, hợp đồng FE."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": _CAT_NAME,
            "category_code": "TEST-CAT-CONNAPI",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        cls.asset = _insert_bypassing_workflow({
            "doctype": "AC Asset",
            "asset_name": "ConnAPI Asset",
            "asset_category": cls.cat.name,
            "lifecycle_status": "Commissioned",
            "manufacturer_sn": "CONNAPI-SN-1",
        }).name

        # Tài sản thứ 2 KHÔNG có bản ghi liên quan — chứng minh đếm không lẫn sang nhau.
        cls.other_asset = _insert_bypassing_workflow({
            "doctype": "AC Asset",
            "asset_name": "ConnAPI Asset Rỗng",
            "asset_category": cls.cat.name,
            "lifecycle_status": "Commissioned",
            "manufacturer_sn": "CONNAPI-SN-2",
        }).name

        # 2 sự cố trên asset chính (Link cùng tên field mặc định: 'asset').
        cls.incidents = []
        for i in range(2):
            doc = _insert_bypassing_workflow({
                "doctype": "Incident Report",
                "asset": cls.asset,
                "reported_by": "Administrator",
                "reported_at": frappe.utils.now_datetime(),
                "incident_type": "Failure",
                "severity": "Medium",
                "status": "Open",
                "description": "Fixture kiểm thử connections",
            })
            cls.incidents.append(doc.name)

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in getattr(cls, "incidents", []):
            frappe.db.delete("Incident Report", {"name": name})
        purge_asset(getattr(cls, "asset", None))
        purge_asset(getattr(cls, "other_asset", None))
        purge_category_by_name(_CAT_NAME)
        if frappe.db.exists("User", _LIMITED_EMAIL):
            frappe.delete_doc("User", _LIMITED_EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── 1. Đầu vào xấu ────────────────────────────────────────────────────────
    def test_unknown_doctype_returns_not_found(self) -> None:
        res = get_connections("Doctype Không Tồn Tại", "X")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "NOT_FOUND")

    def test_unknown_record_returns_not_found(self) -> None:
        res = get_connections("AC Asset", "AC-ASSET-KHONG-CO-THAT")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "NOT_FOUND")

    def test_blank_input_returns_validation_error(self) -> None:
        res = get_connections("", "")
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "VALIDATION_ERROR")

    def test_doctype_without_dashboard_returns_empty_groups(self) -> None:
        # AC Asset Category CHƯA khai đồ thị ⇒ phải trả rỗng có kiểm soát, KHÔNG lỗi:
        # màn chi tiết vẫn render được, chỉ là chưa có gì để nối.
        res = get_connections("AC Asset Category", self.cat.name)
        self.assertTrue(res["success"], res)
        self.assertEqual(res["data"]["groups"], [])
        self.assertEqual(res["data"]["total"], 0)

    # ── 2. Đếm đúng theo đồ thị ───────────────────────────────────────────────
    def _items_by_doctype(self, payload: dict) -> dict[str, dict]:
        return {
            item["doctype"]: item
            for group in payload["groups"]
            for item in group["items"]
        }

    def test_counts_reflect_declared_graph(self) -> None:
        res = get_connections("AC Asset", self.asset)
        self.assertTrue(res["success"], res)
        items = self._items_by_doctype(res["data"])

        self.assertIn("Incident Report", items)
        self.assertEqual(items["Incident Report"]["total"], 2)
        # AC-CR-92: `capped` (bool) → `total_capped` (int 0|1) — 2 < trần ⇒ `total` là con
        # số CHÍNH XÁC, không phải cận dưới (badge "2", KHÔNG "2+").
        self.assertEqual(items["Incident Report"]["total_capped"], 0)

        # ``AC Asset.after_insert`` phát 1 sự kiện vòng đời (qr_generated) cho MỖI tài
        # sản ⇒ 1 là con số ĐÚNG, không phải nhiễu. Khẳng định tường minh để lần sau
        # ai đó đổi hành vi đó thì test này chỉ thẳng vào nguyên nhân.
        self.assertEqual(items["Asset Lifecycle Event"]["total"], 1)
        self.assertEqual(res["data"]["total"], 3)

    def test_counts_do_not_bleed_across_records(self) -> None:
        res = get_connections("AC Asset", self.other_asset)
        self.assertTrue(res["success"], res)
        items = self._items_by_doctype(res["data"])
        # Tài sản này KHÔNG có sự cố nào — sự cố của tài sản kia không được lọt sang.
        #
        # INV-CONN-22: `assertIn` TRƯỚC rồi mới kiểm giá trị. `items.get(dt, {}).get(...)`
        # xanh CẢ KHI ô biến mất hoàn toàn khỏi payload ⇒ mutation "thôi liệt kê ô rỗng"
        # sống sót, trong khi hợp đồng là ô rỗng VẪN có mặt (người dùng phải thấy
        # "0 sự cố", không phải một khoảng trắng không giải thích).
        self.assertIn("Incident Report", items,
                      "Ô rỗng PHẢI vẫn có mặt trong payload (ADR §D1)")
        self.assertEqual(items["Incident Report"]["total"], 0)
        self.assertEqual(items["Asset Lifecycle Event"]["total"], 1)
        self.assertEqual(res["data"]["total"], 1)

    def test_groups_carry_vietnamese_labels(self) -> None:
        res = get_connections("AC Asset", self.asset)
        labels = [g["label"] for g in res["data"]["groups"]]
        self.assertTrue(labels, "Không nhóm nào được trả về")
        self.assertTrue(all(lbl.strip() for lbl in labels), f"Có nhóm thiếu nhãn: {labels}")
        self.assertIn("Sự cố & Chất lượng", labels)

    def test_non_standard_fieldname_is_used_for_filters(self) -> None:
        # PM Work Order trỏ AC Asset qua 'asset_ref' (KHÔNG phải 'asset'). Nếu endpoint
        # dùng nhầm fieldname mặc định thì filter sai ⇒ đếm luôn 0 mà không báo lỗi.
        res = get_connections("AC Asset", self.asset)
        items = self._items_by_doctype(res["data"])
        self.assertIn("PM Work Order", items)
        self.assertEqual(items["PM Work Order"]["deep_link_filters"],
                         {"asset_ref": self.asset})

    def test_filters_let_frontend_drill(self) -> None:
        res = get_connections("AC Asset", self.asset)
        items = self._items_by_doctype(res["data"])
        drill = items["Incident Report"]["deep_link_filters"]
        self.assertEqual(drill, {"asset": self.asset})
        # Bất biến count == drill (ADR-IMM00-LIST-SCOPE §4b): bộ lọc trả về phải dùng
        # được THẬT — query lại ra ĐÚNG số bản ghi ô đã báo. AC-CR-92 chỉ đổi TÊN khoá
        # (`filters` → `deep_link_filters`); bỏ vế query lại là mất chính oracle này.
        rows = frappe.get_all("Incident Report", filters=drill)
        self.assertEqual(len(rows), items["Incident Report"]["total"])

    # ── 3. Phân quyền ─────────────────────────────────────────────────────────
    def test_hides_doctypes_the_user_cannot_read(self) -> None:
        """Người dùng chỉ có role nền không được thấy ô của doctype ngoài quyền."""
        user = frappe.get_doc({
            "doctype": "User", "email": _LIMITED_EMAIL, "first_name": "Han Che",
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
        user.add_roles("AssetCore System User")
        frappe.db.commit()

        frappe.set_user(_LIMITED_EMAIL)
        res = get_connections("AC Asset", self.asset)
        frappe.set_user("Administrator")

        if not res["success"]:
            # Không đọc được chính tài sản ⇒ 403 là kết quả ĐÚNG (không rò gì cả).
            self.assertEqual(res["code"], "FORBIDDEN")
            return

        shown = set(self._items_by_doctype(res["data"]))
        readable = {
            dt for dt in shown
            if frappe.has_permission(dt, ptype="read", user=_LIMITED_EMAIL)
        }
        self.assertEqual(
            shown, readable,
            f"Endpoint trả về doctype người dùng KHÔNG có quyền đọc: {shown - readable}",
        )

    def test_counts_run_under_session_user_not_administrator(self) -> None:
        """Đếm phải qua frappe.get_list (áp row-scope), KHÔNG phải frappe.db.count.

        Oracle bằng AST chứ không phải tìm chuỗi: chỉ tính LỜI GỌI thật và THAM SỐ
        thật, nên docstring giải thích "vì sao không dùng frappe.db.count" không làm
        test đỏ oan — và ngược lại, không thể lách guard bằng cách viết tách chuỗi.
        """
        import ast
        import inspect

        from assetcore.api import connections as mod

        tree = ast.parse(inspect.getsource(mod))
        called: list[str] = []
        kwargs_used: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                called.append(ast.unparse(node.func))
                kwargs_used.extend(kw.arg for kw in node.keywords if kw.arg)

        self.assertNotIn(
            "frappe.db.count", called,
            "api/connections.py GỌI frappe.db.count ⇒ BỎ QUA permission_query_conditions "
            "⇒ rò rỉ tổng số bản ghi toàn viện cho persona bị giới hạn.",
        )
        self.assertNotIn(
            "frappe.get_all", called,
            "frappe.get_all = get_list(ignore_permissions=True) ⇒ bỏ qua phân quyền.",
        )
        self.assertNotIn(
            "ignore_permissions", kwargs_used,
            "api/connections.py không được truyền ignore_permissions ở bất kỳ lời gọi nào.",
        )
        self.assertIn("frappe.get_list", called, "Phải đếm qua frappe.get_list (scoped).")
