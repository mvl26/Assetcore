# assetcore/tests/test_rowscope_invariant.py
# Copyright (c) 2026, AssetCore Team
"""INV-ROWSCOPE — `BaseRepository.list` row-scope invariant (ADR-IMM00-LIST-SCOPE §8).

Finding CRITICAL (factory vòng trước, persona KTV nội bộ trên `/cm/work-orders`):
  1. Bảng HIỆN phiếu ``assigned_to == KTV_B`` — KTV_A đọc được phiếu KHÔNG được giao.
  2. Bấm "Đính ảnh" trên chính phiếu đó → 403 (``_assert_can_attach_repair_photo``).
  3. Header "Tổng N" ≠ số dòng hiển thị.

Root cause (ADR §8.1): sau fix §4b, ``count_with_or`` đếm bằng ``frappe.get_list``
(permission-aware) NHƯNG ``BaseRepository.list`` vẫn lấy rows bằng ``frappe.get_all``
⇒ rows KHÔNG áp ``permission_query_conditions``. Lệch NGƯỢC CHIỀU so với §1: count
scoped < rows thô — và chiều này RÒ DỮ LIỆU.

Quyết định BA (ADR §8.2):
  D4 — row-scope của PHIẾU CÔNG VIỆC (Asset Repair / PM Work Order) = ``assigned_to``
       (KHÁC D1 read-all của AC Asset: registry đọc-tham-chiếu ≠ phiếu-có-ghi).
       ⟹ ``asset_repair_query`` / ``pm_work_order_query`` /
       ``_assert_can_attach_repair_photo`` GIỮ NGUYÊN; cái phải sửa là ROWS.
  D5 — MỘT predicate cho list + count + detail + mutate của CÙNG DocType.
  D6 — assignment-centric → ``scope="user"``; device/plan-centric → ``scope="system"``.
  D7 — card-đếm cùng chế độ scope với drill-list của nó.

Bất biến chứng minh ở đây: INV-ROWSCOPE-1..10 (ADR §8.9). INV-ROWSCOPE-4/6 PHẢI chạy
dưới **session user THẬT** (``frappe.set_user(ktv_a)``) — Administrator bypass
``permission_query_conditions`` nên test sẽ XANH GIẢ.

Run: bench --site miyano run-tests --app assetcore \
     --module assetcore.tests.test_rowscope_invariant
"""
from __future__ import annotations

import json
import time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from assetcore.api.imm08 import list_pm_work_orders
from assetcore.api.imm09 import list_repair_work_orders
from assetcore.repositories.pm_repo import PMWorkOrderRepo
from assetcore.repositories.repair_repo import RepairRepo
from assetcore.services.imm09 import (
    RepairStatus,
    _assert_can_attach_repair_photo,
    validate_asset_not_under_repair,
)
from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name

_KTV_A = "ktv_a_rowscope@example.com"
_KTV_B = "ktv_b_rowscope@example.com"
_SENIOR = "senior_rowscope@example.com"
_VENDOR = "vendor_rowscope@example.com"
_ALL_USERS = (_KTV_A, _KTV_B, _SENIOR, _VENDOR)

_CAT_NAME = "_RowScope Test Category"


def _ensure_user(email: str, first_name: str, *roles: str) -> str:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "send_welcome_email": 0,
        "enabled": 1,
    }).insert(ignore_permissions=True)
    if roles:
        u.add_roles(*roles)
    return u.name


def _drop_user(email: str) -> None:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)


def _ensure_cat() -> str:
    existing = frappe.db.get_value("AC Asset Category", {"category_name": _CAT_NAME}, "name")
    if existing:
        return existing
    return frappe.get_doc({
        "doctype": "AC Asset Category",
        "category_name": _CAT_NAME,
        "default_pm_interval_days": 90,
    }).insert(ignore_permissions=True).name


def _make_asset(tag: str, cat: str) -> str:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_RowScope Asset {tag}",
            "asset_category": cat,
            "manufacturer_sn": f"RS-SN-{tag}-{int(time.time()) % 100000}",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True).name
    finally:
        frappe.flags.in_install = prev


class TestRowScopeInvariant(FrappeTestCase):
    """ADR-IMM00-LIST-SCOPE §8 — rows permission-aware KHỚP count, cho 5 DocType row-scoped."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = _ensure_cat()

        # KTV nội bộ: cần CẢ `Repair User` (DocPerm read Asset Repair) LẪN `PM User`
        # (DocPerm read PM Work Order) để 2 assert đối xứng A3/A5 chạy được. Không
        # senior ⇒ rơi vào nhánh `assigned_to = <user>` của asset_repair_query /
        # pm_work_order_query (permissions.py:113-131).
        cls.ktv_a = _ensure_user(_KTV_A, "KTV A", "Repair User", "PM User")
        cls.ktv_b = _ensure_user(_KTV_B, "KTV B", "Repair User", "PM User")
        # Senior: read-all trên CẢ 2 doctype (chống over-block, A6).
        cls.senior = _ensure_user(_SENIOR, "Senior RS", "Repair Manager", "PM Manager")
        # Vendor Engineer THUẦN: KHÔNG có DocPerm read trên Asset Repair /
        # PM Work Order (ADR §8.5 bảng persona) ⇒ dùng cho INV-ROWSCOPE-8/9.
        cls.vendor = _ensure_user(_VENDOR, "Vendor RS", "Vendor Engineer", "AssetCore System User")

        cls.asset_a = _make_asset("A", cls.cat)
        cls.asset_b = _make_asset("B", cls.cat)
        cls.assets = [cls.asset_a, cls.asset_b]

        cls.repair_a = cls._make_repair(cls.asset_a, cls.ktv_a)
        cls.repair_b = cls._make_repair(cls.asset_b, cls.ktv_b)
        # Cờ SLA để card `cm_sla_breach_count` (D7) có giá trị non-vacuous:
        # KTV_A phải đếm 1 (của mình), KHÔNG 2 (gồm phiếu KTV_B).
        for name in (cls.repair_a, cls.repair_b):
            frappe.db.set_value("Asset Repair", name, "sla_breached", 1, update_modified=False)

        cls.template = cls._make_template(cls.cat)
        cls.sched_a = cls._make_schedule(cls.asset_a, cls.template)
        cls.sched_b = cls._make_schedule(cls.asset_b, cls.template)
        cls.pm_a = cls._make_pm_wo(cls.asset_a, cls.sched_a, cls.ktv_a)
        cls.pm_b = cls._make_pm_wo(cls.asset_b, cls.sched_b, cls.ktv_b)

        frappe.db.commit()

    # ── fixture builders ─────────────────────────────────────────────────────
    @classmethod
    def _make_repair(cls, asset_ref: str, assignee: str) -> str:
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset_ref,
            "repair_type": "Corrective",
            "priority": "Normal",
            "failure_description": "_RowScope fixture failure",
            "status": RepairStatus.ASSIGNED,
            "assigned_to": assignee,
        }).insert(ignore_permissions=True)
        return doc.name

    @classmethod
    def _make_template(cls, cat: str) -> str:
        det = f"PMCT-{cat}-Quarterly"
        if frappe.db.exists("PM Checklist Template", det):
            return det
        return frappe.get_doc({
            "doctype": "PM Checklist Template",
            "template_name": "_RowScope Template",
            "asset_category": cat,
            "pm_type": "Quarterly",
            "checklist_items": [
                {"description": "_RowScope check", "measurement_type": "Pass/Fail"},
            ],
        }).insert(ignore_permissions=True).name

    @classmethod
    def _make_schedule(cls, asset_ref: str, template: str) -> str:
        det = f"PMS-{asset_ref}-Quarterly"
        if frappe.db.exists("PM Schedule", det):
            return det
        return frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": asset_ref,
            "pm_type": "Quarterly",
            "pm_interval_days": 90,
            "checklist_template": template,
            "status": "Active",
        }).insert(ignore_permissions=True).name

    @classmethod
    def _make_pm_wo(cls, asset_ref: str, sched: str, assignee: str) -> str:
        due = add_days(nowdate(), -3)
        doc = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": asset_ref,
            "pm_schedule": sched,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": due,
            "scheduled_date": due,
            "assigned_to": assignee,
        }).insert(ignore_permissions=True)
        # status Overdue set qua db (không đi qua validate) — mirror cron
        # `check_pm_overdue`, cần cho INV-ROWSCOPE-10 (count_overdue_pm).
        frappe.db.set_value("PM Work Order", doc.name, "status", "Overdue", update_modified=False)
        return doc.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in (getattr(cls, "pm_a", None), getattr(cls, "pm_b", None)):
            if name and frappe.db.exists("PM Work Order", name):
                frappe.delete_doc("PM Work Order", name, force=True, ignore_permissions=True)
        for name in (getattr(cls, "sched_a", None), getattr(cls, "sched_b", None)):
            if name and frappe.db.exists("PM Schedule", name):
                frappe.delete_doc("PM Schedule", name, force=True, ignore_permissions=True)
        if getattr(cls, "template", None) and frappe.db.exists("PM Checklist Template", cls.template):
            frappe.delete_doc("PM Checklist Template", cls.template, force=True, ignore_permissions=True)
        for name in (getattr(cls, "repair_a", None), getattr(cls, "repair_b", None)):
            if name and frappe.db.exists("Asset Repair", name):
                frappe.delete_doc("Asset Repair", name, force=True, ignore_permissions=True)
        for name in getattr(cls, "assets", []):
            purge_asset(name)
        if frappe.db.exists("AC Asset Category", getattr(cls, "cat", "")):
            frappe.delete_doc("AC Asset Category", cls.cat, force=True, ignore_permissions=True)
        for email in _ALL_USERS:
            _drop_user(email)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _walk(api_fn, **kw) -> tuple[int, list[str], dict]:
        """Trả (pagination.total, names TẤT CẢ trang, envelope trang 1).

        Bất biến count==rows định nghĩa trên TOÀN tập (cộng dồn mọi trang) —
        ``paginate`` cap page_size ở 100 nên persona read-all có thể >1 trang.
        """
        first = api_fn(page=1, page_size=100, **kw)
        if not first.get("success"):
            return -1, [], first
        data = first["data"]
        total = data["pagination"]["total"]
        names = [r["name"] for r in data["data"]]
        for p in range(2, (data["pagination"].get("total_pages") or 0) + 1):
            nxt = api_fn(page=p, page_size=100, **kw)
            names.extend(r["name"] for r in nxt["data"]["data"])
        return total, names, first

    def _asset_filter(self) -> str:
        return json.dumps({"asset_ref": ["in", self.assets]})

    # ── T1 / INV-ROWSCOPE-4 — repair list KHÔNG lộ phiếu người khác ───────────
    def test_rowscope_repair_list_excludes_other_assignee(self):
        frappe.set_user(self.ktv_a)
        total, names, env = self._walk(list_repair_work_orders)
        self.assertTrue(env.get("success"), f"KTV_A list CM phải 200-success: {env}")
        self.assertIn(self.repair_a, names,
                      "KTV_A PHẢI thấy phiếu CM được giao cho mình")
        self.assertNotIn(
            self.repair_b, names,
            "RÒ DỮ LIỆU: KTV_A KHÔNG được thấy phiếu CM assigned_to == KTV_B "
            "(D4 row-scope = assigned_to; rows phải qua frappe.get_list)",
        )
        self.assertGreater(total, 0)

    # ── T2 / INV-ROWSCOPE-4 — total == rows ──────────────────────────────────
    def test_rowscope_repair_total_equals_rows(self):
        frappe.set_user(self.ktv_a)
        total, names, env = self._walk(list_repair_work_orders)
        self.assertTrue(env.get("success"), f"envelope: {env}")
        self.assertEqual(
            total, len(names),
            "INV-ROWSCOPE-1: pagination.total == len(rows) — count và rows PHẢI "
            "cùng một engine (count_with_or ↔ frappe.get_list)",
        )
        # KTV_A là user MỚI ⇒ tập của họ đúng bằng 1 phiếu fixture.
        self.assertEqual(total, 1, "KTV_A chỉ có đúng 1 phiếu CM được giao")

    # ── T3 / INV-ROWSCOPE-5 — đọc được ⇒ ghi được (đóng finding CRITICAL) ─────
    def test_rowscope_read_implies_attach(self):
        frappe.set_user(self.ktv_a)
        _total, names, env = self._walk(list_repair_work_orders)
        self.assertTrue(env.get("success"), f"envelope: {env}")
        self.assertTrue(names, "fixture phải cho KTV_A ít nhất 1 phiếu")
        for name in names:
            wo = RepairRepo.get(name)
            try:
                _assert_can_attach_repair_photo(wo)
            except Exception as exc:  # ServiceError(FORBIDDEN) hoặc bất kỳ
                self.fail(
                    f"INV-ROWSCOPE-5 VỠ: phiếu {name} ĐỌC được trong list nhưng "
                    f"KHÔNG đính được ảnh ({exc}) — read-gate lệch write-gate",
                )

    # ── T4 / INV-ROWSCOPE-6 — đối xứng PM ────────────────────────────────────
    def test_rowscope_pm_list_excludes_other_assignee_and_total_matches(self):
        frappe.set_user(self.ktv_a)
        total, names, env = self._walk(list_pm_work_orders)
        self.assertTrue(env.get("success"), f"KTV_A list PM phải 200-success: {env}")
        self.assertIn(self.pm_a, names, "KTV_A PHẢI thấy phiếu PM được giao cho mình")
        self.assertNotIn(
            self.pm_b, names,
            "RÒ DỮ LIỆU: KTV_A KHÔNG được thấy phiếu PM assigned_to == KTV_B",
        )
        self.assertEqual(total, len(names),
                         "INV-ROWSCOPE-6: PM total == len(rows)")
        self.assertEqual(total, 1, "KTV_A chỉ có đúng 1 phiếu PM được giao")

    # ── T5 — scope="system" giữ bất biến nghiệp vụ (duplicate guard) ─────────
    def test_rowscope_system_scope_preserves_duplicate_guard(self):
        """KTV_A KHÔNG đọc được phiếu của KTV_B, nhưng guard trùng-phiếu VẪN chặn.

        ``validate_asset_not_under_repair`` đi qua ``RepairRepo.exists`` /
        ``find_one`` (không permission-aware, ADR §8.10 B1) ⇒ permission-scope
        KHÔNG được làm mù bất biến nghiệp vụ (2 phiếu active trên cùng asset).
        """
        frappe.set_user(self.ktv_a)
        with self.assertRaises(Exception) as cm:
            validate_asset_not_under_repair(self.asset_b)
        self.assertNotIsInstance(
            cm.exception, AssertionError,
            "guard PHẢI raise lỗi nghiệp vụ, không phải assertion nội bộ",
        )

    # ── T6 / INV-ROWSCOPE-7 — senior thấy đủ (chống over-block) ─────────────
    def test_rowscope_senior_sees_all_rows(self):
        frappe.set_user(self.senior)
        total, names, env = self._walk(list_repair_work_orders, filters=self._asset_filter())
        self.assertTrue(env.get("success"), f"envelope: {env}")
        self.assertIn(self.repair_a, names)
        self.assertIn(self.repair_b, names)
        self.assertEqual(total, 2, "senior/quản lý phải thấy ĐỦ 2 phiếu CM (không over-block)")
        self.assertEqual(total, len(names), "INV-ROWSCOPE-1 cho persona senior")

        total_pm, names_pm, env_pm = self._walk(list_pm_work_orders, filters=self._asset_filter())
        self.assertTrue(env_pm.get("success"), f"envelope PM: {env_pm}")
        self.assertIn(self.pm_a, names_pm)
        self.assertIn(self.pm_b, names_pm)
        self.assertEqual(total_pm, 2, "senior phải thấy ĐỦ 2 phiếu PM")
        self.assertEqual(total_pm, len(names_pm))

    # ── T7 / INV-ROWSCOPE-1/2/3 — contract tham số `scope` ──────────────────
    def test_rowscope_scope_param_consistency(self):
        filters = {"asset_ref": ("in", self.assets)}
        frappe.set_user(self.ktv_a)

        rows_sys, pg_sys = RepairRepo.list(filters=filters, fields=["name"], scope="system")
        self.assertEqual(pg_sys["total"], 2,
                         'scope="system" bỏ qua permission ⇒ đếm cả 2 phiếu')
        self.assertEqual(len(rows_sys), 2, 'scope="system" trả cả 2 rows')
        self.assertEqual(pg_sys["total"], len(rows_sys), "INV-ROWSCOPE-2")

        rows_usr, pg_usr = RepairRepo.list(filters=filters, fields=["name"], scope="user")
        self.assertEqual(pg_usr["total"], 1, 'scope="user" áp permission_query_conditions')
        self.assertEqual([r["name"] for r in rows_usr], [self.repair_a])
        self.assertEqual(pg_usr["total"], len(rows_usr), "INV-ROWSCOPE-1")

        # default = "user" (fail-safe: call site quên khai báo bị SIẾT, không NỚI)
        rows_def, pg_def = RepairRepo.list(filters=filters, fields=["name"])
        self.assertEqual(pg_def["total"], 1, 'default scope PHẢI là "user" (fail-safe)')
        self.assertEqual(len(rows_def), 1)

        # INV-ROWSCOPE-3: giá trị lạ → ValueError (chống typo "System" thành silent-permissive)
        for bad in ("bogus", "System", "", None):
            with self.assertRaises(ValueError, msg=f"scope={bad!r} phải raise ValueError"):
                RepairRepo.list(filters=filters, fields=["name"], scope=bad)

    # ── INV-ROWSCOPE-8 — vendor KHÔNG bị nới quyền ──────────────────────────
    def test_rowscope_vendor_not_widened(self):
        frappe.set_user(self.vendor)
        _total, names, env = self._walk(list_repair_work_orders)
        if env.get("success"):
            for n in names:
                self.assertNotIn(
                    n, (self.repair_a, self.repair_b),
                    "VENDOR KHÔNG được thấy phiếu CM của KTV nội bộ (D2 isolation)",
                )
        else:
            # Không có DocPerm read ⇒ in-handler 403 (INV-ROWSCOPE-9) — cũng là
            # 'không bị nới quyền'.
            self.assertEqual(env.get("code"), "FORBIDDEN")

    # ── INV-ROWSCOPE-9 — thiếu DocPerm read ⇒ HTTP-200 + Error envelope ──────
    def test_rowscope_missing_docperm_returns_error_envelope(self):
        """BR-00-ROWSCOPE-403: KHÔNG 500 câm, KHÔNG list rỗng giả."""
        frappe.set_user(self.vendor)
        env = list_repair_work_orders(page=1, page_size=20)
        self.assertIsInstance(env, dict)
        if env.get("success"):
            self.skipTest("Vendor Engineer có DocPerm read trên Asset Repair — "
                          "backlog B2 đã được ratify, nhánh 403 không áp dụng")
        self.assertFalse(env["success"])
        self.assertEqual(env.get("code"), "FORBIDDEN",
                         "lỗi quyền trên list = FORBIDDEN, KHÔNG SYS-500")
        self.assertEqual(env.get("http_status"), 403)
        self.assertTrue((env.get("error") or "").strip(),
                        "message KHÔNG được rỗng (vacuous error envelope)")

    # ── INV-ROWSCOPE-10 (D7) — card đếm == drill list, CÙNG persona ─────────
    def test_rowscope_card_equals_drill_per_persona(self):
        from assetcore.services.imm08 import count_overdue_pm
        from assetcore.services.imm09 import cm_sla_breach_count

        frappe.set_user(self.ktv_a)
        card_cm = cm_sla_breach_count()
        _t, drill_cm, env_cm = self._walk(
            list_repair_work_orders, filters=json.dumps({"sla_breached_live": 1}))
        self.assertTrue(env_cm.get("success"), f"drill CM envelope: {env_cm}")
        self.assertEqual(
            card_cm, len(drill_cm),
            "D7: card `cm_sla_breach_count` PHẢI cùng scope với drill "
            "?sla_breached_live=1 (card global + drill scoped = card≠drill)",
        )
        self.assertEqual(card_cm, 1, "KTV_A chỉ có 1 phiếu SLA breach của mình")

        card_pm = count_overdue_pm()
        _t2, drill_pm, env_pm = self._walk(
            list_pm_work_orders, filters=json.dumps({"overdue": 1}))
        self.assertTrue(env_pm.get("success"), f"drill PM envelope: {env_pm}")
        self.assertEqual(
            card_pm, len(drill_pm),
            "D7: card `count_overdue_pm` PHẢI cùng scope với drill ?overdue=1",
        )
        self.assertEqual(card_pm, 1, "KTV_A chỉ có 1 phiếu PM quá hạn của mình")


class TestRowScopeSystemModeParity(FrappeTestCase):
    """INV-ROWSCOPE-2 — ``count_ignore_permissions`` là cặp song sinh raw của
    ``count_with_or``: cùng filters/or_filters, khác duy nhất entrypoint."""

    def test_count_ignore_permissions_matches_get_all(self):
        from assetcore.services.shared.filters import count_ignore_permissions

        filters = {"docstatus": ("<", 2)}
        expected = len(frappe.get_all("Asset Repair", filters=filters,
                                      fields=["name"], limit_page_length=0))
        self.assertEqual(count_ignore_permissions("Asset Repair", filters, None), expected)

    def test_count_ignore_permissions_honours_or_filters(self):
        from assetcore.services.shared.filters import count_ignore_permissions

        or_filters = [["name", "like", "WO-CM-%"], ["asset_ref", "like", "AC-ASSET-%"]]
        expected = len(frappe.get_all("Asset Repair", filters=None,
                                      or_filters=or_filters, fields=["name"],
                                      limit_page_length=0))
        self.assertEqual(count_ignore_permissions("Asset Repair", None, or_filters), expected)

    def test_system_scope_total_equals_rows_administrator(self):
        rows, pg = PMWorkOrderRepo.list(fields=["name"], page_size=100, scope="system")
        if pg["total"] <= pg["page_size"]:
            self.assertEqual(pg["total"], len(rows), "INV-ROWSCOPE-2")
        else:
            self.assertEqual(len(rows), pg["page_size"])


# ═══════════════════════════════════════════════════════════════════════════════
# CR-74 — INV-DETAIL-2/3/4 (ADR-IMM00-LIST-SCOPE §9)
#   §8 đã siết `list`; khoảng cách read-vs-write còn lại nằm TRỌN ở đường `detail`.
#   Ở đây chứng minh 3 đường của CÙNG một phiếu kết luận GIỐNG NHAU:
#       thấy-trong-list  ⇔  đọc-được-detail  ⇔  đính-được-ảnh
#   và persona ĐÚNG quyền KHÔNG bị siết oan (payload key-set không đổi).
# ═══════════════════════════════════════════════════════════════════════════════
_D_KTV_A = "cr74_inv_ktv_a@example.invalid"
_D_KTV_B = "cr74_inv_ktv_b@example.invalid"
_D_SENIOR = "cr74_inv_senior@example.invalid"
_D_AUDITOR = "cr74_inv_auditor@example.invalid"
_D_USERS = (_D_KTV_A, _D_KTV_B, _D_SENIOR, _D_AUDITOR)
_D_CAT = "_CR74Inv Test Category"

# Khoá hợp đồng TỐI THIỂU của từng payload success (chống payload teo lại sau khi
# thêm gate). Nguồn: docs/mobile/openapi §3.2 `<X>Detail` + service dict literal.
_D_MUST_HAVE_KEYS = {
    "getPmWorkOrder": {"name", "asset_ref", "status", "assigned_to", "allowed_transitions"},
    "getRepairWorkOrder": {"name", "asset_ref", "status", "assigned_to", "asset_info",
                           "risk_classification", "allowed_transitions"},
    "getCalibration": {"name", "asset", "status", "technician", "allowed_transitions"},
    "getIncident": {"name", "asset", "status", "allowed_transitions"},
}


class TestDetailReadGateCR74Invariant(FrappeTestCase):
    """INV-DETAIL-2/3/4 — detail dùng CÙNG predicate với list + write-gate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.cat = frappe.db.get_value("AC Asset Category", {"category_name": _D_CAT}, "name")
        if not cls.cat:
            cls.cat = frappe.get_doc({
                "doctype": "AC Asset Category", "category_name": _D_CAT,
                "default_pm_interval_days": 90,
            }).insert(ignore_permissions=True).name

        # KTV nội bộ ĐỦ 4 domain-role ⇒ CÓ DocPerm read cả 4 DocType, nhưng KHÔNG
        # senior ⇒ rơi vào nhánh `assigned_to`/`reported_by` của hook (permissions.py).
        tech_roles = ("Repair User", "PM User", "Corrective User", "Calibration User",
                      "AssetCore System User")
        cls.ktv_a = _ensure_user(_D_KTV_A, "CR74 KTV A", *tech_roles)
        cls.ktv_b = _ensure_user(_D_KTV_B, "CR74 KTV B", *tech_roles)
        cls.senior = _ensure_user(_D_SENIOR, "CR74 Senior", "Repair Manager", "PM Manager",
                                  "Corrective Manager", "Calibration Manager")
        cls.auditor = _ensure_user(_D_AUDITOR, "CR74 Auditor", "AssetCore Auditor")

        cls.asset_a = _make_asset("CR74A", cls.cat)
        cls.asset_b = _make_asset("CR74B", cls.cat)
        cls.assets = [cls.asset_a, cls.asset_b]

        cls.repair_a = cls._mk_repair(cls.asset_a, cls.ktv_a)
        cls.repair_b = cls._mk_repair(cls.asset_b, cls.ktv_b)

        cls.template = frappe.get_doc({
            "doctype": "PM Checklist Template", "template_name": "_CR74Inv Template",
            "asset_category": cls.cat, "pm_type": "Quarterly",
            "checklist_items": [{"description": "_CR74Inv check",
                                 "measurement_type": "Pass/Fail"}],
        }).insert(ignore_permissions=True).name
        cls.sched_a = cls._mk_sched(cls.asset_a, cls.template)
        cls.sched_b = cls._mk_sched(cls.asset_b, cls.template)
        cls.pm_a = cls._mk_pm(cls.asset_a, cls.sched_a, cls.ktv_a)
        cls.pm_b = cls._mk_pm(cls.asset_b, cls.sched_b, cls.ktv_b)

        cls.incident_a = cls._mk_incident(cls.asset_a, cls.ktv_a)
        cls.incident_b = cls._mk_incident(cls.asset_b, cls.ktv_b)
        cls.cal_a = cls._mk_cal(cls.asset_a, cls.ktv_a)
        frappe.db.commit()

    # ── fixture builders ─────────────────────────────────────────────────────
    @classmethod
    def _mk_repair(cls, asset_ref: str, assignee: str) -> str:
        return frappe.get_doc({
            "doctype": "Asset Repair", "asset_ref": asset_ref,
            "repair_type": "Corrective", "priority": "Normal",
            "failure_description": "_CR74Inv fixture failure",
            "status": RepairStatus.ASSIGNED, "assigned_to": assignee,
        }).insert(ignore_permissions=True).name

    @classmethod
    def _mk_sched(cls, asset_ref: str, template: str) -> str:
        det = f"PMS-{asset_ref}-Quarterly"
        if frappe.db.exists("PM Schedule", det):
            return det
        return frappe.get_doc({
            "doctype": "PM Schedule", "asset_ref": asset_ref, "pm_type": "Quarterly",
            "pm_interval_days": 90, "checklist_template": template, "status": "Active",
        }).insert(ignore_permissions=True).name

    @classmethod
    def _mk_pm(cls, asset_ref: str, sched: str, assignee: str) -> str:
        due = nowdate()
        return frappe.get_doc({
            "doctype": "PM Work Order", "asset_ref": asset_ref, "pm_schedule": sched,
            "pm_type": "Quarterly", "wo_type": "Preventive", "status": "Open",
            "due_date": due, "scheduled_date": due, "assigned_to": assignee,
        }).insert(ignore_permissions=True).name

    @classmethod
    def _mk_incident(cls, asset: str, reporter: str) -> str:
        return frappe.get_doc({
            "doctype": "Incident Report", "asset": asset, "incident_type": "Malfunction",
            "severity": "Low", "description": "_CR74Inv fixture incident",
            "reported_by": reporter, "status": "Open",
        }).insert(ignore_permissions=True).name

    @classmethod
    def _mk_cal(cls, asset: str, technician: str) -> str:
        return frappe.get_doc({
            "doctype": "IMM Asset Calibration", "asset": asset,
            "calibration_type": "In-House", "status": "Scheduled",
            "reference_standard_serial": "_CR74-REF-STD-001",
            "scheduled_date": add_days(nowdate(), 7), "technician": technician,
        }).insert(ignore_permissions=True).name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for dt, names in (
            ("IMM Asset Calibration", (getattr(cls, "cal_a", None),)),
            ("Incident Report", (getattr(cls, "incident_a", None),
                                 getattr(cls, "incident_b", None))),
            ("PM Work Order", (getattr(cls, "pm_a", None), getattr(cls, "pm_b", None))),
            ("PM Schedule", (getattr(cls, "sched_a", None), getattr(cls, "sched_b", None))),
            ("PM Checklist Template", (getattr(cls, "template", None),)),
            ("Asset Repair", (getattr(cls, "repair_a", None), getattr(cls, "repair_b", None))),
        ):
            for name in names:
                if name and frappe.db.exists(dt, name):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        for name in getattr(cls, "assets", []):
            purge_asset(name)
        if frappe.db.exists("AC Asset Category", getattr(cls, "cat", "")):
            frappe.delete_doc("AC Asset Category", cls.cat, force=True, ignore_permissions=True)
        for email in _D_USERS:
            _drop_user(email)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _api(label: str):
        from assetcore.api.imm08 import get_pm_work_order
        from assetcore.api.imm09 import get_repair_work_order
        from assetcore.api.imm11 import get_calibration
        from assetcore.api.imm12 import get_incident

        return {
            "getPmWorkOrder": get_pm_work_order,
            "getRepairWorkOrder": get_repair_work_order,
            "getCalibration": get_calibration,
            "getIncident": get_incident,
        }[label]

    def _detail_keys(self, label: str, name: str, user: str) -> set[str]:
        frappe.set_user(user)
        try:
            env = self._api(label)(name=name)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(env.get("success"),
                        f"{label} dưới {user} PHẢI 200-success (0 regress): {env}")
        return set((env.get("data") or {}).keys())

    def _assert_row_denied(self, label: str, name: str, user: str) -> None:
        frappe.set_user(user)
        env = self._api(label)(name=name)
        self.assertFalse(
            env.get("success"),
            f"INV-DETAIL-2 VỠ ({label}): KTV mở được phiếu KHÔNG giao cho mình "
            f"bằng URL trực tiếp — hook has_permission (hooks.py:448-455) chưa được "
            f"kích hoạt trên đường detail. env={env}",
        )
        self.assertEqual(env.get("code"), "FORBIDDEN", f"{label}: row-deny = FORBIDDEN")
        self.assertEqual(env.get("http_status"), 403,
                         f"{label}: 403 in-envelope trên HTTP-200 (KHÔNG logout)")

    # ── TC-CR74-02a..02c / INV-DETAIL-2 — row-gate cho 3 DocType CÓ hook ─────
    def test_cr74_02a_repair_detail_denied_for_non_assignee(self):
        self._assert_row_denied("getRepairWorkOrder", self.repair_b, self.ktv_a)

    def test_cr74_02b_pm_detail_denied_for_non_assignee(self):
        self._assert_row_denied("getPmWorkOrder", self.pm_b, self.ktv_a)

    def test_cr74_02c_incident_detail_denied_for_non_reporter(self):
        self._assert_row_denied("getIncident", self.incident_b, self.ktv_a)

    # ── TC-CR74-03a..03d / INV-DETAIL-4 — persona ĐÚNG quyền: 0 regress ─────
    def _assert_no_shape_regress(self, label: str, name: str, user: str) -> None:
        """Key-set dưới persona == key-set dưới Administrator (bypass toàn bộ gate,
        `frappe/permissions.py:107-109`) ⇒ gate KHÔNG cắt/đổi payload; và tập khoá
        hợp đồng tối thiểu vẫn còn đủ (chống payload teo)."""
        keys_user = self._detail_keys(label, name, user)
        keys_admin = self._detail_keys(label, name, "Administrator")
        self.assertEqual(
            keys_user, keys_admin,
            f"{label}: key-set dưới {user} LỆCH baseline (Administrator) — gate mới "
            f"KHÔNG được đổi shape payload success (A7 byte-identical). "
            f"thiếu={sorted(keys_admin - keys_user)} thừa={sorted(keys_user - keys_admin)}",
        )
        missing = sorted(_D_MUST_HAVE_KEYS[label] - keys_user)
        self.assertEqual(missing, [],
                         f"{label}: payload THIẾU khoá hợp đồng {missing}")

    def test_cr74_03a_pm_detail_assignee_unchanged(self):
        self._assert_no_shape_regress("getPmWorkOrder", self.pm_a, self.ktv_a)

    def test_cr74_03b_repair_detail_assignee_unchanged(self):
        self._assert_no_shape_regress("getRepairWorkOrder", self.repair_a, self.ktv_a)

    def test_cr74_03c_calibration_detail_unchanged_for_technician_and_senior(self):
        """D10 — `IMM Asset Calibration` KHÔNG có hook ⇒ trục ROW **giữ nguyên**:
        KTV hiệu chuẩn CÓ DocPerm read vẫn đọc được phiếu KHÔNG phải của mình.
        Ghim hành vi này để vòng sau không "sửa" nhầm thành 403 khi chưa có [BA] ratify."""
        self._assert_no_shape_regress("getCalibration", self.cal_a, self.ktv_a)
        self._assert_no_shape_regress("getCalibration", self.cal_a, self.senior)
        frappe.set_user(self.ktv_b)
        env = self._api("getCalibration")(name=self.cal_a)
        self.assertTrue(
            env.get("success"),
            "D10: IMM-11 CHỈ siết trục ROLE trong CR-74 — KTV hiệu chuẩn khác "
            f"KHÔNG được siết oan khi chưa có hook + [BA] ratify. env={env}",
        )

    def test_cr74_03d_senior_and_auditor_unchanged_on_all_four(self):
        """Hook `has_controller_permissions` CHỈ DENY, KHÔNG GRANT (frappe/permissions.py:
        443-446) ⇒ senior/auditor giữ 200 là nhờ **DocPerm**, không nhờ hook."""
        for label, name in (("getPmWorkOrder", self.pm_b),
                            ("getRepairWorkOrder", self.repair_b),
                            ("getIncident", self.incident_b),
                            ("getCalibration", self.cal_a)):
            self._assert_no_shape_regress(label, name, self.senior)
            self._assert_no_shape_regress(label, name, self.auditor)

    # ── TC-CR74-04 / INV-DETAIL-3 — bảng chân trị 2 persona × 2 phiếu ────────
    def test_cr74_04_detail_read_write_truth_table(self):
        """ĐÓNG P0: `list` ⇔ `detail` ⇔ `attach-photo` PHẢI trùng nhau 4/4 tổ hợp.

        Trước CR-74 ô (ktv_a, repair_b) = (KHÔNG thấy trong list, ĐỌC được detail,
        KHÔNG đính được ảnh) — người dùng nhìn thấy hai sự thật mâu thuẫn về CÙNG
        một phiếu.
        """
        from assetcore.api.imm09 import get_repair_work_order

        rows = []
        for user in (self.ktv_a, self.ktv_b):
            for repair in (self.repair_a, self.repair_b):
                frappe.set_user(user)
                _total, names, env_list = self._walk_list()
                self.assertTrue(env_list.get("success"), f"list envelope: {env_list}")
                in_list = repair in names

                env_detail = get_repair_work_order(name=repair)
                detail_ok = bool(env_detail.get("success"))
                if not detail_ok:
                    self.assertEqual(env_detail.get("http_status"), 403,
                                     f"detail-deny PHẢI là 403 in-envelope: {env_detail}")

                wo = RepairRepo.get(repair)
                try:
                    _assert_can_attach_repair_photo(wo)
                    attach_ok = True
                except Exception:                       # noqa: BLE001 — ServiceError(403)
                    attach_ok = False
                frappe.set_user("Administrator")

                rows.append((user, repair, in_list, detail_ok, attach_ok))

        mismatched = [r for r in rows if not (r[2] == r[3] == r[4])]
        self.assertEqual(
            mismatched, [],
            "INV-DETAIL-3 VỠ — bảng chân trị (user, phiếu, thấy-trong-list, đọc-được, "
            f"đính-được-ảnh) có ô LỆCH: {mismatched}. MỘT predicate row-scope PHẢI phủ "
            f"cả list + detail + mutate của CÙNG DocType (ADR §9.2 D8). Toàn bảng: {rows}",
        )
        # non-vacuous: bảng phải có CẢ ô True LẪN ô False (nếu toàn True/False thì
        # test "trùng khớp" là rỗng nghĩa).
        self.assertTrue(any(r[3] for r in rows), "bảng chân trị vacuous: 0 ô đọc-được")
        self.assertTrue(any(not r[3] for r in rows), "bảng chân trị vacuous: 0 ô bị chặn")

    def _walk_list(self):
        first = list_repair_work_orders(page=1, page_size=100)
        if not first.get("success"):
            return -1, [], first
        data = first["data"]
        names = [r["name"] for r in data["data"]]
        for p in range(2, (data["pagination"].get("total_pages") or 0) + 1):
            nxt = list_repair_work_orders(page=p, page_size=100)
            names.extend(r["name"] for r in nxt["data"]["data"])
        return data["pagination"]["total"], names, first


# ═════════════════════════════════════════════════════════════════════════════
# AC-CR-98 + AC-CR-106 (ADR-IMM00-LIST-SCOPE **§10**, chốt 2026-07-30) —
# INV-COMM-SCOPE-2/3 · INV-CONN-27 (enforce) · INV-CONN-21 (enforce).
# Vị trí file do §10.9 CHỈ ĐỊNH (không tự chọn): đây là nhà của họ INV-ROWSCOPE,
# đã có `_ensure_user` + kỷ luật `frappe.set_user` (Administrator bypass
# `permission_query_conditions` ⇒ chấm dưới Administrator là XANH GIẢ, §8.9).
# ═════════════════════════════════════════════════════════════════════════════

_COMM_DT = "Asset Commissioning"


class TestCommissioningOneEngineScope(FrappeTestCase):
    """INV-COMM-SCOPE-2/3 + INV-CONN-27 — `list_commissioning` đếm & đọc MỘT ENGINE.

    RED-before (đo trên đĩa 2026-07-30): `total = frappe.db.count(...)` +
    `records = frappe.get_all(...)` — **cả hai** bỏ `permission_query_conditions`
    (`asset_commissioning_query`, `hooks.py:444`) ⇒ persona bị row-scope đọc được phiếu
    NGOÀI phạm vi (RÒ DỮ LIỆU) và ô «Phiếu nghiệm thu lắp đặt» của `get_connections`
    (đi `frappe.get_list`) không bao giờ khớp drill.

    ⚠️ Fixture CỐ Ý **không** dựa vào `vendor_engineer_name == email`: field đó là
    `Data` («Tên Kỹ sư Hãng»), KHÔNG `Link → User` ⇒ so với `frappe.session.user` gần
    như không bao giờ khớp trên dữ liệu thật (nợ CÓ TÊN `AC-CR-108`, §10.2). Phiếu
    "trong phạm vi" của vendor ở đây là phiếu **do chính họ tạo** (`owner`) — đúng
    mệnh đề CÒN SỐNG của predicate.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        sfx = frappe.generate_hash(length=6)
        cls.sfx = sfx
        cls.cat_name = f"_CommScope Category {sfx}"
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls.cat_name,
            "default_pm_interval_days": 90,
        }).insert(ignore_permissions=True).name

        # 3 persona §10.2. QTV = Commissioning Manager (senior read-all); Nội bộ =
        # Commissioning User (rơi `return ""` cuối `asset_commissioning_query`);
        # KTV NCC = Vendor Engineer + Commissioning User (dual-role — vendor THUẦN
        # KHÔNG có DocPerm read nên sẽ dừng ở lớp ROLE và không kiểm được row-scope).
        cls.qtv = _ensure_user(f"commscope_qtv_{sfx}@example.invalid", "QTV Comm",
                               "AssetCore System User", "Commissioning Manager")
        cls.internal = _ensure_user(f"commscope_ktv_{sfx}@example.invalid", "KTV Comm",
                                    "AssetCore System User", "Commissioning User")
        cls.vendor = _ensure_user(f"commscope_vendor_{sfx}@example.invalid", "NCC Comm",
                                  "AssetCore System User", "Commissioning User",
                                  "Vendor Engineer")
        cls.users = [cls.qtv, cls.internal, cls.vendor]

        # `ac_asset_has_permission` (nhánh vendor) chỉ cho đọc asset mình là
        # responsible_technician ⇒ thiếu field này thì `get_connections` trả 403 và
        # INV-CONN-27 không kiểm được gì.
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"_CommScope Asset {sfx}",
                "asset_category": cls.cat,
                "manufacturer_sn": f"CS-SN-{sfx}",
                "lifecycle_status": "Active",
                "responsible_technician": cls.vendor,
            }).insert(ignore_permissions=True).name
            # Thiết bị THỨ HAI — "ngoài phạm vi" của KTV NCC (không phải
            # responsible_technician, không sở hữu phiếu nào trên nó). Dùng cho
            # TC-IMM04-SCOPE-12: giao rỗng phải ra 0 dòng, KHÔNG fallback về tập
            # phiếu của mình. Có thiết bị + phiếu THẬT ở đây mới chống được assert
            # vacuous ("0 dòng vì không có bản ghi nào" ≠ "0 dòng vì giao rỗng").
            cls.other_asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"_CommScope Asset Other {sfx}",
                "asset_category": cls.cat,
                "manufacturer_sn": f"CS-SN-OTH-{sfx}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True).name
        finally:
            frappe.flags.in_install = prev

        # Mốc `reception_date` cho nhánh `overdue=1` (BR-04-10): lấy TỪ SoT
        # `OVERDUE_DAYS` chứ không hằng số rời — nếu SLA đổi, fixture vẫn quá hạn
        # (không rot thành assert vacuous "0 dòng quá hạn").
        from assetcore.services.imm04 import OVERDUE_DAYS  # noqa: PLC0415

        cls.overdue_date = add_days(nowdate(), -(OVERDUE_DAYS + 5))

        # 4 phiếu trên CÙNG thiết bị — phủ docstatus 0/1/2 (chống assert vacuous §10.8):
        cls.own_draft = cls._make_comm(owner=cls.vendor, docstatus=0)
        cls.own_submitted = cls._make_comm(owner=cls.vendor, docstatus=1)
        cls.own_cancelled = cls._make_comm(owner=cls.vendor, docstatus=2)
        cls.foreign = cls._make_comm(owner="Administrator", docstatus=0,
                                     engineer=f"KTV NCC khac {sfx}")
        # Phiếu QUÁ HẠN trên thiết bị NGOÀI phạm vi vendor (owner = Administrator).
        cls.foreign_other = cls._make_comm(owner="Administrator", docstatus=0,
                                          asset=cls.other_asset,
                                          engineer=f"KTV NCC khac {sfx}")
        cls.comms = [cls.own_draft, cls.own_submitted, cls.own_cancelled, cls.foreign,
                     cls.foreign_other]
        frappe.db.commit()

    @classmethod
    def _make_comm(cls, *, owner: str, docstatus: int = 0, engineer: str = "",
                   asset: str = "") -> str:
        """Phiếu nghiệm thu gắn ``final_asset``; ``owner`` = người tạo THẬT (set_user).

        ``reception_date`` LUÔN đặt về mốc quá hạn (``cls.overdue_date``) để 4 phiếu
        đồng thời phục vụ nhánh ``overdue=1`` (list-form filters) — nhánh mà bản
        trước KHÔNG có TC nào (nợ TDD AC-CR-112).
        """
        frappe.set_user(owner)
        try:
            doc = frappe.get_doc({
                "doctype": _COMM_DT, "workflow_state": "Draft",
            }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        finally:
            frappe.set_user("Administrator")
        doc.db_set("workflow_state", "To Be Installed", update_modified=False)
        doc.db_set("final_asset", asset or cls.asset, update_modified=False)
        doc.db_set("reception_date", cls.overdue_date, update_modified=False)
        if engineer:
            doc.db_set("vendor_engineer_name", engineer, update_modified=False)
        if docstatus:
            frappe.db.set_value(_COMM_DT, doc.name, "docstatus", docstatus,
                                update_modified=False)
        return doc.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in getattr(cls, "comms", []):
            if frappe.db.exists(_COMM_DT, name):
                # docstatus 1/2 được set bằng cột (fixture) nên `doc.cancel()` không
                # áp dụng; hạ về 0 trước khi xoá, nếu không `delete_doc` chặn
                # "Submitted Record cannot be deleted" ⇒ fixture RÒ sang phiên sau.
                frappe.db.set_value(_COMM_DT, name, "docstatus", 0, update_modified=False)
                frappe.delete_doc(_COMM_DT, name, force=True, ignore_permissions=True)
        purge_asset(getattr(cls, "asset", None))
        purge_asset(getattr(cls, "other_asset", None))
        purge_category_by_name(getattr(cls, "cat_name", ""))
        for email in getattr(cls, "users", []):
            _drop_user(email)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _drill(self, user: str, *, page_size: int = 100) -> dict:
        """`list_commissioning({"final_asset": X})` dưới session user THẬT."""
        from assetcore.services import imm04 as svc  # noqa: PLC0415 - khuôn cục bộ

        frappe.set_user(user)
        try:
            return svc.list_commissioning({"final_asset": self.asset},
                                          page=1, page_size=page_size)
        finally:
            frappe.set_user("Administrator")

    def _list(self, user: str, filters: dict, *, page: int = 1,
              page_size: int = 100) -> dict:
        """``list_commissioning(filters)`` dưới session user THẬT — filters TỰ DO.

        Tách khỏi :meth:`_drill` (chỉ dict ``final_asset``) để chạm được nhánh
        **list-form** (``overdue=1`` → ``_dict_to_list_filters``, ``imm04.py:1100-1105``)
        mà không đổi hành vi 3 TC cũ (Hyrum).
        """
        from assetcore.services import imm04 as svc  # noqa: PLC0415 - khuôn cục bộ

        frappe.set_user(user)
        try:
            return svc.list_commissioning(dict(filters), page=page, page_size=page_size)
        finally:
            frappe.set_user("Administrator")

    def _visible(self, user: str, docstatus: int) -> list[str]:
        """Phiếu của thiết bị này mà persona NHÌN THẤY ở một docstatus — CÙNG engine."""
        frappe.set_user(user)
        try:
            return [r["name"] for r in frappe.get_list(
                _COMM_DT,
                filters={"final_asset": self.asset, "docstatus": docstatus},
                fields=["name"], limit_page_length=0,
            )]
        finally:
            frappe.set_user("Administrator")

    def _cell(self, user: str) -> dict:
        from assetcore.api.connections import get_connections  # noqa: PLC0415

        frappe.set_user(user)
        try:
            res = get_connections("AC Asset", self.asset)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"get_connections phải 200-success: {res}")
        cells = {it["doctype"]: it
                 for g in res["data"]["groups"] for it in g["items"]}
        self.assertIn(
            _COMM_DT, cells,
            f"Ô «Phiếu nghiệm thu lắp đặt» VẮNG cho persona {user} ⇒ so số thành "
            f"vacuous (ô bị ẩn vì thiếu DocPerm read ⇒ fixture persona sai)",
        )
        return cells[_COMM_DT]

    # ── INV-COMM-SCOPE-2 — HẾT RÒ DỮ LIỆU (ĐỎ trước fix) ─────────────────────
    def test_inv_comm_scope_2_vendor_never_sees_foreign_commissioning(self):
        res = self._drill(self.vendor)
        names = {r["name"] for r in res["items"]}
        self.assertEqual(
            names, {self.own_draft, self.own_submitted},
            "RÒ DỮ LIỆU / SIẾT QUÁ TAY: persona `Vendor Engineer + Commissioning User` "
            "phải thấy ĐÚNG phiếu của mình (docstatus 0 và 1), không thêm không bớt. "
            "`frappe.get_all` bỏ `asset_commissioning_query` ⇒ phiếu của người khác lọt.",
        )
        self.assertNotIn(self.foreign, names)
        self.assertEqual(
            res["pagination"]["total"], 2,
            "TỔNG vẫn đếm phiếu ngoài phạm vi: `frappe.db.count` KHÔNG áp "
            "`permission_query_conditions` ⇒ header nói 3 mà drill được 2.",
        )

    # ── INV-COMM-SCOPE-3 — count == rows cho CẢ 3 persona, 2 nhánh phân trang ─
    def test_inv_comm_scope_3_total_equals_rows_all_personas(self):
        expected = {
            self.qtv: {self.own_draft, self.own_submitted, self.foreign},
            self.internal: {self.own_draft, self.own_submitted, self.foreign},
            self.vendor: {self.own_draft, self.own_submitted},
        }
        for user, want in expected.items():
            with self.subTest(user=user):
                res = self._drill(user)
                names = {r["name"] for r in res["items"]}
                self.assertEqual(names, want, f"tập dòng LỆCH cho {user}")
                self.assertEqual(
                    res["pagination"]["total"], len(res["items"]),
                    f"[{user}] count != rows ⇒ hai engine khác nhau cho total và items",
                )
                self.assertNotIn(
                    self.own_cancelled, names,
                    "`docstatus != 2` (bước 3 §10.5) phải GIỮ NGUYÊN — phiếu huỷ không "
                    "thuộc danh sách làm việc",
                )
                # Nhánh total > page_size: total vẫn là số dòng ROW-SCOPED, KHÔNG
                # phải tổng toàn bảng (đây là chỗ `db.count` từng nói dối).
                paged = self._drill(user, page_size=1)
                self.assertEqual(len(paged["items"]), 1)
                self.assertEqual(
                    paged["pagination"]["total"], len(want),
                    f"[{user}] total khi phân trang phải bằng số dòng đếm qua CÙNG "
                    f"predicate ({len(want)}), không phải tổng toàn bảng",
                )

    # ── INV-CONN-27 (enforce) — ô đếm == drill + #{docstatus==2}, 3 persona ──
    def test_inv_conn_27_cell_total_equals_drill_plus_cancelled(self):
        """Dung sai DUY NHẤT được phép: ô chưa loại phiếu huỷ = nợ CÓ TÊN `AC-CR-99`.

        Khi AC-CR-99 land, số hạng thứ hai về 0 và chính assert này ĐỎ ⇒ nợ hữu hình.
        """
        for user in (self.vendor, self.internal, self.qtv):
            with self.subTest(user=user):
                cell = self._cell(user)
                drill = self._drill(user)
                cancelled = self._visible(user, 2)
                rows = drill["items"]
                self.assertEqual(
                    [r["name"] for r in rows
                     if r.get("final_asset") != self.asset], [],
                    f"[{user}] drill trả dòng của thiết bị KHÁC ⇒ bộ lọc final_asset bị "
                    f"nuốt/ghi đè (hai con số có thể bằng nhau mà CÙNG SAI)",
                )
                self.assertEqual(cell["total_capped"], 0, "fixture nhỏ ⇒ total chính xác")
                self.assertEqual(
                    cell["total"], len(rows) + len(cancelled),
                    f"[{user}] ô báo {cell['total']}, drill {len(rows)}, phiếu huỷ "
                    f"{len(cancelled)} — dung sai được phép DUY NHẤT là "
                    f"`ô.total == drill + #{{docstatus==2}}` (nợ AC-CR-99, CHƯA land)",
                )
                self.assertEqual(
                    len(cancelled), 1,
                    f"[{user}] không nhìn thấy phiếu HUỶ nào ⇒ công thức dung sai thành "
                    f"vacuous (§10.8 cấm assert vacuous)",
                )

    # ── TC-IMM04-SCOPE-11 — nhánh LIST-FORM (overdue=1) cũng MỘT ENGINE ──────
    def test_tc_imm04_scope_11_overdue_list_form_total_equals_rows(self):
        """``overdue=1`` đi ``_dict_to_list_filters`` ⇒ ``count_with_or`` nhận filters
        dạng **LIST**, không phải dict (``imm04.py:1100-1105``).

        Nợ TDD đóng ở đây (AC-CR-112): 3 TC cũ của class này CHỈ chạm nhánh dict
        (``{"final_asset": …}``). Nhánh list-form là nhánh mà FE gọi thật khi người dùng
        bấm thẻ «Quá hạn SLA», và nó đi qua CÙNG ``count_with_or`` — nhưng nếu một vòng
        sau ai đó "tối ưu" nhánh này về ``frappe.db.count`` (dạng list vẫn chạy, chỉ mất
        row-scope) thì KHÔNG có test nào đỏ. Giờ có.
        """
        expected = {
            self.internal: {self.own_draft, self.own_submitted, self.foreign},
            self.vendor: {self.own_draft, self.own_submitted},
        }
        for user, want in expected.items():
            with self.subTest(user=user):
                res = self._list(user, {"final_asset": self.asset, "overdue": 1})
                names = {r["name"] for r in res["items"]}
                self.assertEqual(
                    names, want,
                    f"[{user}] tập dòng nhánh overdue LỆCH — hoặc bộ lọc "
                    f"`final_asset` bị nuốt khi chuyển sang list-form, hoặc row-scope "
                    f"`asset_commissioning_query` không áp trên nhánh này",
                )
                self.assertTrue(
                    names,
                    f"[{user}] 0 dòng quá hạn ⇒ assert total==len(items) thành VACUOUS "
                    f"(fixture `reception_date`={self.overdue_date} phải < cutoff)",
                )
                self.assertEqual(
                    res["pagination"]["total"], len(res["items"]),
                    f"[{user}] pagination.total ({res['pagination']['total']}) != "
                    f"len(items) ({len(res['items'])}) trên nhánh LIST-FORM ⇒ total và "
                    f"items đi HAI engine khác nhau (đường đếm mất row-scope)",
                )
                self.assertNotIn(
                    self.own_cancelled, names,
                    "phiếu docstatus==2 phải bị loại cả trên nhánh overdue",
                )
                self.assertNotIn(
                    self.foreign_other, names,
                    "phiếu của thiết bị KHÁC lọt vào ⇒ bộ lọc final_asset bị ghi đè",
                )
                # Nhánh phân trang: total vẫn là số dòng ROW-SCOPED của CÙNG predicate.
                paged = self._list(user, {"final_asset": self.asset, "overdue": 1},
                                   page_size=1)
                self.assertEqual(len(paged["items"]), 1)
                self.assertEqual(
                    paged["pagination"]["total"], len(want),
                    f"[{user}] total khi phân trang nhánh overdue phải bằng {len(want)}, "
                    f"không phải tổng toàn bảng",
                )

    # ── TC-IMM04-SCOPE-12 — giao RỖNG ⇒ 0 dòng, KHÔNG fallback ───────────────
    def test_tc_imm04_scope_12_overdue_out_of_scope_asset_yields_zero_not_fallback(self):
        """Deep-link thiết bị NGOÀI phạm vi + ``overdue=1`` ⇒ ``total==0`` và ``items==[]``.

        Hai chế độ hỏng bị khoá cùng lúc:
          * **fallback** về "mọi phiếu của tôi" (bug GÁN của AC-CR-106) — sẽ ra 2 dòng;
          * ``total`` đếm bằng engine khác (thô) — sẽ ra 1 (phiếu của Administrator).
        Không 403: hết phạm vi là **danh sách rỗng có ngữ cảnh**, không phải lỗi quyền.
        """
        res = self._list(self.vendor,
                         {"final_asset": self.other_asset, "overdue": 1})
        self.assertEqual(
            res["items"], [],
            "KTV NCC nhận dòng cho thiết bị ngoài phạm vi ⇒ hoặc row-scope không áp, "
            "hoặc bộ lọc caller bị ghi đè bằng tập được-giao (fallback = bug AC-CR-106)",
        )
        self.assertEqual(
            res["pagination"]["total"], 0,
            f"total={res['pagination']['total']} trong khi 0 dòng ⇒ đường đếm bỏ "
            f"row-scope (`frappe.db.count` sẽ trả 1: phiếu của Administrator)",
        )
        # NON-VACUOUS: phiếu đó TỒN TẠI và ĐANG quá hạn — persona read-all thấy nó.
        seen_by_qtv = self._list(self.qtv,
                                 {"final_asset": self.other_asset, "overdue": 1})
        self.assertEqual(
            [r["name"] for r in seen_by_qtv["items"]], [self.foreign_other],
            "fixture rot: phiếu quá hạn trên thiết bị thứ hai phải TỒN TẠI (nếu không, "
            "assert 0-dòng ở trên là vacuous — 0 vì không có bản ghi, không vì giao rỗng)",
        )
        self.assertEqual(seen_by_qtv["pagination"]["total"], 1)

    # ── TC-IMM04-SCOPE-13 — mutation guard: db.count phải làm TC-11 ĐỎ ───────
    def test_tc_imm04_scope_13_mutation_db_count_breaks_overdue_invariant(self):
        """Proof-by-mutation SỐNG: thay ``count_with_or`` → ``frappe.db.count`` trong
        nhánh overdue thì bất biến ``total == len(items)`` PHẢI vỡ.

        Vì sao cần: TC-11 xanh chưa chứng minh nó *phát hiện* được hồi quy — nó có thể
        xanh vì fixture nhỏ/đối xứng (xanh giả). TC này bơm chính hồi quy đó và đòi
        thấy lệch. Nếu một ngày TC này ĐỎ (không còn lệch) ⇒ hoặc row-scope đã bị tháo
        khỏi hook, hoặc fixture mất phiếu "ngoài phạm vi" ⇒ TC-11 mất giá trị.
        """
        from unittest.mock import patch  # noqa: PLC0415 - khuôn cục bộ

        def _raw_count(doctype, filters, or_filters):  # mirror chữ ký, mất row-scope
            return frappe.db.count(doctype, filters)

        with patch("assetcore.services.imm04.count_with_or", side_effect=_raw_count):
            mutated = self._list(self.vendor,
                                 {"final_asset": self.asset, "overdue": 1})
        self.assertEqual(
            len(mutated["items"]), 2,
            "mutation chỉ được đụng ĐƯỜNG ĐẾM; số dòng phải giữ nguyên 2",
        )
        self.assertNotEqual(
            mutated["pagination"]["total"], len(mutated["items"]),
            f"MUTATION KHÔNG BỊ PHÁT HIỆN: `frappe.db.count` vẫn cho total == "
            f"len(items) == {len(mutated['items'])} ⇒ TC-IMM04-SCOPE-11 là XANH GIẢ "
            f"(fixture thiếu phiếu ngoài phạm vi để hai engine lệch nhau)",
        )
        self.assertEqual(
            mutated["pagination"]["total"], 3,
            "engine thô phải đếm cả phiếu của Administrator trên CÙNG thiết bị "
            "(2 của mình + 1 ngoài phạm vi) — con số này là 'lời nói dối' mà "
            "AC-CR-98 đã bịt",
        )
        # Sau khi thoát `with`, đường đếm THẬT phải xanh lại (revert tự động).
        restored = self._list(self.vendor, {"final_asset": self.asset, "overdue": 1})
        self.assertEqual(restored["pagination"]["total"], len(restored["items"]))


class TestVendorDeepLinkIntersection(FrappeTestCase):
    """INV-CONN-21 (enforce) — vendor deep-link 1 thiết bị ⇒ CHỈ dòng của thiết bị đó.

    RED-before: `apply_vendor_scope` **GÁN** `filters[field] = ["in", assigned]` ⇒ bộ lọc
    `?asset=X` của caller bị xoá và endpoint trả MỌI thiết bị được giao (S-10.2).
    D1 (§10.6): endpoint LIST trả **200 + 0 dòng** cho thiết bị ngoài phạm vi — 403 chỉ
    dành cho đường DETAIL (`assert_vendor_can_access`).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        sfx = frappe.generate_hash(length=6)
        cls.cat_name = f"_DeepLink Category {sfx}"
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category", "category_name": cls.cat_name,
            "default_pm_interval_days": 90,
        }).insert(ignore_permissions=True).name
        # Vendor kiêm 3 domain-role để CÓ DocPerm read trên PM WO / Asset Repair /
        # phiếu-lịch hiệu chuẩn; row-scope của 2 doctype đầu là `assigned_to == user`.
        cls.vendor = _ensure_user(
            f"deeplink_vendor_{sfx}@example.invalid", "NCC DeepLink",
            "AssetCore System User", "Vendor Engineer",
            "PM User", "Repair User", "Calibration User",
        )
        cls.assets = []
        for tag in ("X", "Y"):
            prev = frappe.flags.in_install
            frappe.flags.in_install = "frappe"
            try:
                cls.assets.append(frappe.get_doc({
                    "doctype": "AC Asset",
                    "asset_name": f"_DeepLink Asset {tag} {sfx}",
                    "asset_category": cls.cat,
                    "manufacturer_sn": f"DL-SN-{tag}-{sfx}",
                    "lifecycle_status": "Active",
                    "responsible_technician": cls.vendor,
                }).insert(ignore_permissions=True).name)
            finally:
                frappe.flags.in_install = prev
        cls.asset_x, cls.asset_y = cls.assets

        cls.template = frappe.get_doc({
            "doctype": "PM Checklist Template",
            "template_name": f"_DeepLink Template {sfx}",
            "asset_category": cls.cat, "pm_type": "Quarterly",
        }).insert(ignore_permissions=True).name
        cls.pm, cls.repair, cls.cal = {}, {}, {}
        for asset in cls.assets:
            sched = frappe.get_doc({
                "doctype": "PM Schedule", "asset_ref": asset, "pm_type": "Quarterly",
                "pm_interval_days": 3650, "checklist_template": cls.template,
                "status": "Active",
            }).insert(ignore_permissions=True).name
            # `assigned_to = vendor` ⇒ CẢ HAI phiếu qua được row-scope; thứ DUY NHẤT
            # phân biệt chúng là bộ lọc `asset_ref` của caller (chính thứ bị GÁN xoá).
            cls.pm[asset] = frappe.get_doc({
                "doctype": "PM Work Order", "asset_ref": asset, "pm_schedule": sched,
                "pm_type": "Quarterly", "wo_type": "Preventive", "status": "Open",
                "due_date": add_days(nowdate(), 7), "assigned_to": cls.vendor,
            }).insert(ignore_permissions=True).name
            cls.repair[asset] = frappe.get_doc({
                "doctype": "Asset Repair", "asset_ref": asset,
                "repair_type": "Corrective", "priority": "Normal",
                "failure_description": "_DeepLink fixture failure",
                "status": RepairStatus.ASSIGNED, "assigned_to": cls.vendor,
            }).insert(ignore_permissions=True).name
            cls.cal[asset] = frappe.get_doc({
                "doctype": "IMM Calibration Schedule", "asset": asset,
                "calibration_type": "External", "interval_days": 365,
                "next_due_date": add_days(nowdate(), 3650), "is_active": 1,
            }).insert(ignore_permissions=True).name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for asset in getattr(cls, "assets", []):
            purge_asset(asset)
        if getattr(cls, "template", None) and frappe.db.exists("PM Checklist Template", cls.template):
            frappe.delete_doc("PM Checklist Template", cls.template, force=True,
                              ignore_permissions=True)
        purge_category_by_name(getattr(cls, "cat_name", ""))
        _drop_user(getattr(cls, "vendor", ""))
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def _as_vendor(self, api_fn, **kw) -> dict:
        frappe.set_user(self.vendor)
        try:
            res = api_fn(**kw)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"{api_fn.__name__} phải 200-success: {res}")
        return res["data"]

    def test_inv_conn_21_pm_deep_link_returns_only_that_asset(self):
        data = self._as_vendor(list_pm_work_orders,
                               filters=json.dumps({"asset_ref": self.asset_x}),
                               page_size=100)
        names = {r["name"] for r in data["data"]}
        self.assertEqual(
            names, {self.pm[self.asset_x]},
            "Deep-link 1 thiết bị mà trả phiếu PM của thiết bị KHÁC ⇒ vendor-scope GÁN "
            "đè bộ lọc caller (S-10.2)",
        )
        self.assertEqual(data["pagination"]["total"], len(data["data"]))

    def test_inv_conn_21_repair_deep_link_returns_only_that_asset(self):
        data = self._as_vendor(list_repair_work_orders,
                               filters=json.dumps({"asset_ref": self.asset_y}),
                               page_size=100)
        names = {r["name"] for r in data["data"]}
        self.assertEqual(names, {self.repair[self.asset_y]})
        self.assertEqual(data["pagination"]["total"], len(data["data"]))

    def test_inv_conn_21_calibration_schedule_deep_link_returns_only_that_asset(self):
        from assetcore.api.imm11 import list_calibration_schedules  # noqa: PLC0415

        data = self._as_vendor(list_calibration_schedules,
                               filters=json.dumps({"asset": self.asset_x}),
                               page_size=100)
        rows = data["data"]
        self.assertEqual({r["name"] for r in rows}, {self.cal[self.asset_x]})
        self.assertEqual(
            [r["name"] for r in rows if r.get("asset") != self.asset_x], [],
            "lịch hiệu chuẩn của thiết bị khác lọt vào ⇒ GIAO bị thay bằng GÁN",
        )

    def test_inv_conn_21_out_of_scope_asset_yields_zero_rows_not_403(self):
        """D1 (§10.6): thiết bị NGOÀI phạm vi ⇒ 200 + 0 dòng cho CẢ 3 endpoint LIST."""
        outsider = f"_DL-NOT-ASSIGNED-{frappe.generate_hash(length=6)}"
        from assetcore.api.imm11 import list_calibration_schedules  # noqa: PLC0415

        pm = self._as_vendor(list_pm_work_orders,
                             filters=json.dumps({"asset_ref": outsider}), page_size=100)
        cm = self._as_vendor(list_repair_work_orders,
                             filters=json.dumps({"asset_ref": outsider}), page_size=100)
        cal = self._as_vendor(list_calibration_schedules,
                              filters=json.dumps({"asset": outsider}), page_size=100)
        for label, data in (("PM", pm), ("CM", cm), ("hiệu chuẩn", cal)):
            with self.subTest(endpoint=label):
                self.assertEqual(
                    data["data"], [],
                    f"[{label}] thiết bị KHÔNG được giao vẫn ra dòng ⇒ vendor-scope GÁN "
                    f"đè bộ lọc caller (leo phạm vi so với ý định caller)",
                )
