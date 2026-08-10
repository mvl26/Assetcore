# Copyright (c) 2026, AssetCore Team
"""APPROVAL-INBOX-CR32 — endpoint gộp "Phiếu chờ tôi duyệt" xuyên module.

``services.imm00.get_pending_approvals_inbox`` gộp 3 nguồn TÁI DÙNG SSoT sẵn có:
  (a) Asset Commissioning  — imm04.list_my_pending_approvals (pending_approver == session user);
  (b) Asset Transfer       — status='Pending Approval', CHỈ khi caller đạt _TRANSFER_APPROVE_CAP
                             (services/imm00.py — commissioning.submit);
  (c) IMM Spare Allocation — allocation_status='Requested' (SSoT predicate của approve_allocation
                             @services/imm15.py), CHỈ khi caller đạt _CAP_APPROVE (inventory.submit).

Permission-aware: user thiếu cap nguồn nào → nguồn đó EXCLUDE im lặng (KHÔNG lỗi);
0 cap → success:true + items=[] (chống anti-pattern RBAC dead-gate — KHÔNG hardcode
role-name mới). Session-scoped: KHÔNG nhận param ``user`` (**_ignore nuốt kwargs spoof).

Spec: Core Doc IMM-00 §III.22 + ADR-IMM00-APPROVAL-INBOX (test plan 10 TC tối thiểu).

Run: bench --site miyano run-tests --module assetcore.tests.test_imm00_approvals_inbox
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import nowdate

from assetcore.tests._asset_cleanup import purge_asset

# Item shape thống nhất (hợp đồng BE↔FE↔mobile — Hyrum's Law: đủ 11 key, không thừa).
# CR-44: +summary (chuỗi VI ≤120 server-built, LUÔN emit coalesce '').
_ITEM_KEYS = {
    "doctype", "name", "module", "title", "asset", "asset_name",
    "requested_by", "requested_by_name", "pending_since", "route", "summary",
}
_SUMMARY_MAX = 120

# CR-44 — 2 dòng phụ tùng cho _ALLOC_PM → summary '<part1> ×<qty> <uom> …+1'.
_ALLOC_PM_PART1 = "Van PEEP máy thở Dräger Evita V500"
_ALLOC_PM_PART2 = "Cảm biến SpO2 Masimo SET"
_ALLOC_PM_UOM   = "Cái"

# Timestamp CỐ ĐỊNH trong quá khứ xa (2020) → 3 phiếu fixture LUÔN đứng đầu list
# sort pending_since asc, bất kể data pending thật trên site dev (miyano).
_T_COMMISSIONING = "2020-01-01 08:00:00"
_T_TRANSFER      = "2020-01-02 08:00:00"
_T_ALLOCATION    = "2020-01-03 08:00:00"

_COMM_NAME  = "_TEST-INBOX-COMM-CR32"
_COMM_DESC  = "Máy X-quang GE (inbox CR32)"
_ALLOC_NAME = "_TEST-INBOX-ALLOC-CR32"          # KHÔNG work_order_ref → route /inventory
_ALLOC_PM   = "_TEST-INBOX-ALLOC-PM-CR32"       # PM Work Order → /pm/work-orders/{ref}
_ALLOC_CM   = "_TEST-INBOX-ALLOC-CM-CR32"       # Asset Repair (CM) → /cm/work-orders/{ref}
_WO_PM_REF  = "_TEST-INBOX-WO-PM-CR32"
_WO_CM_REF  = "_TEST-INBOX-WO-CM-CR32"

# ── CR-42: NGUỒN THỨ 4 — Asset Repair 'Pending Inspection' (Nghiệm thu CM) ──
# SoD (đối xứng CR-41): người ĐÓNG phiếu (close_work_order → event
# repair_pending_inspection, actor=closer) KHÔNG được tự nghiệm thu → ẩn khỏi
# inbox của họ. Closer unknown (không event) → FAIL-OPEN (vẫn hiện).
_WO_CM_INSPECT = "_TEST-INBOX-CM-INSPECT-CR42"   # có event closer=B → hiện cho A, ẩn cho B
_WO_CM_NOEVT   = "_TEST-INBOX-CM-NOEVT-CR42"      # KHÔNG event → closer None → fail-open
_CM_SUMMARY    = "Thay bộ nguồn máy thở Dräger Evita V500 (inbox CR42)"
_T_INSPECT_EVT = "2020-01-06 08:00:00"            # ts event → pending_since (WO có event)
_T_NOEVT_MOD   = "2020-01-07 08:00:00"            # modified WO no-event → pending_since fallback


def _mk_user(email: str, roles: list[str], registry: list[str]) -> str:
    """Tạo user test với đúng role-set (mirror pattern test_imm00 TestTransferReceiveAuthz)."""
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User", "email": email,
        "first_name": email.split("@")[0], "send_welcome_email": 0,
        "user_type": "System User",
    }).insert(ignore_permissions=True)
    for r in roles:
        u.append("roles", {"role": r})
    u.flags.ignore_permissions = True
    u.save()
    from assetcore.services.shared import rbac as _rbac
    _rbac.invalidate_capabilities(email)
    registry.append(email)
    frappe.db.commit()
    return email


class TestPendingApprovalsInbox(unittest.TestCase):
    """TC-BE-1..5 — service + API tier (TDD viết TRƯỚC implement, CLAUDE.md §17)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._users: list[str] = []
        cls._transfers: list[str] = []

        # User "QTV" đủ CẢ 3 nguồn: AssetCore Super Admin có DocPerm submit trên
        # Asset Commissioning (commissioning.submit) + AC Stock Movement
        # (inventory.submit); pending_approver commissioning gán đích danh bên dưới.
        cls.qtv = _mk_user("_test_inbox_qtv_cr32@assetcore.test",
                           ["AssetCore System User", "AssetCore Super Admin"],
                           cls._users)
        # User CHỈ có cap duyệt transfer (Commissioning Manager → commissioning.submit;
        # KHÔNG có submit AC Stock Movement, KHÔNG là pending_approver).
        cls.transfer_only = _mk_user("_test_inbox_trf_only_cr32@assetcore.test",
                                     ["AssetCore System User", "Commissioning Manager"],
                                     cls._users)
        # User base 0 cap duyệt.
        cls.base = _mk_user("_test_inbox_base_cr32@assetcore.test",
                            ["AssetCore System User"], cls._users)

        # Fixture asset thật cho transfer (enrich asset_name phải hoạt động).
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCat Inbox CR32",
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestDept Inbox CR32",
        }).insert(ignore_permissions=True)
        # CR-44: khoa NGUỒN cho summary transfer '<nguồn> → <đích> · <asset>'.
        cls.dept_from = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestDeptFrom Inbox CR32",
        }).insert(ignore_permissions=True)
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_Test Asset Inbox CR32",
                "asset_category": cls.cat.name,
                "manufacturer_sn": f"SN-INBOX-{int(time.time() * 1000) % 10_000_000}",
                "lifecycle_status": "Commissioned",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

        # (a) Asset Commissioning pending_approver=qtv — raw-SQL insert tối thiểu
        #     (precedent test_imm04 _TEST-COMM-G05: bypass reqd-link validation).
        frappe.db.sql(
            "INSERT INTO `tabAsset Commissioning` "
            "(name, docstatus, workflow_state, pending_approver, approval_stage, "
            " approval_submitted_at, asset_description, owner, creation, modified) "
            "VALUES (%s, 0, 'Doc Verify', %s, 'Doc Verify', %s, %s, %s, %s, %s)",
            (_COMM_NAME, cls.qtv, _T_COMMISSIONING, _COMM_DESC, cls.base,
             _T_COMMISSIONING, _T_COMMISSIONING),
        )
        # (b) Asset Transfer Pending Approval (doc-insert thật + ép creation về 2020).
        tdoc = frappe.get_doc({
            "doctype": "Asset Transfer",
            "asset": cls.asset.name,
            "transfer_type": "Internal",
            "transfer_date": nowdate(),
            "to_department": cls.dept.name,
            "reason": "Điều chuyển phục vụ kiểm thử inbox CR32",
        })
        tdoc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Transfer", tdoc.name, {
            "status": "Pending Approval",
            "creation": _T_TRANSFER,
            # CR-44: set from_department qua db (bypass validate current-dept) →
            # summary có ĐỦ nguồn→đích.
            "from_department": cls.dept_from.name,
        }, update_modified=False)
        cls.transfer_name = tdoc.name
        cls._transfers.append(tdoc.name)
        # (c) IMM Spare Allocation Requested — raw-SQL insert tối thiểu (không đụng
        #     reserved_qty ledger; inbox chỉ ĐỌC header). 3 biến thể route-drill
        #     (Core Doc §III.22): no-ref → /inventory; PM WO → /pm/work-orders;
        #     Asset Repair → /cm/work-orders.
        for name, wo_dt, wo_ref, created in (
            (_ALLOC_NAME, None, None, _T_ALLOCATION),
            (_ALLOC_PM, "PM Work Order", _WO_PM_REF, "2020-01-04 08:00:00"),
            (_ALLOC_CM, "Asset Repair", _WO_CM_REF, "2020-01-05 08:00:00"),
        ):
            frappe.db.sql(
                "INSERT INTO `tabIMM Spare Allocation` "
                "(name, docstatus, workflow_state, allocation_status, requested_by, "
                " requested_date, urgency, work_order_doctype, work_order_ref, "
                " owner, creation, modified) "
                "VALUES (%s, 0, 'Requested', 'Requested', %s, %s, 'Routine', "
                "        %s, %s, %s, %s, %s)",
                (name, cls.qtv, "2020-01-03", wo_dt, wo_ref, cls.qtv,
                 created, created),
            )
        # CR-44: 2 dòng phụ tùng cho _ALLOC_PM → summary đa dòng '<part1> ×2 Cái …+1'.
        #   _ALLOC_NAME giữ 0 dòng → summary '' (case coalesce blank).
        for cidx, (part, qty) in enumerate(
                ((_ALLOC_PM_PART1, 2), (_ALLOC_PM_PART2, 1)), start=1):
            frappe.db.sql(
                "INSERT INTO `tabIMM Spare Allocation Item` "
                "(name, parent, parenttype, parentfield, idx, part_name, "
                " qty_requested, uom, owner, creation, modified) "
                "VALUES (%s, %s, 'IMM Spare Allocation', 'items', %s, %s, %s, %s, "
                "        %s, %s, %s)",
                (f"{_ALLOC_PM}-ITEM{cidx}", _ALLOC_PM, cidx, part, qty,
                 _ALLOC_PM_UOM, cls.qtv, "2020-01-04 08:00:00", "2020-01-04 08:00:00"),
            )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.db.sql("DELETE FROM `tabAsset Commissioning` WHERE name=%s", (_COMM_NAME,))
        frappe.db.sql(
            "DELETE FROM `tabIMM Spare Allocation` WHERE name IN (%s, %s, %s)",
            (_ALLOC_NAME, _ALLOC_PM, _ALLOC_CM),
        )
        # CR-44: child rows KHÔNG cascade (no FK MariaDB) → xoá tường minh.
        frappe.db.sql(
            "DELETE FROM `tabIMM Spare Allocation Item` WHERE parent=%s", (_ALLOC_PM,))
        for name in cls._transfers:
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True,
                                  ignore_permissions=True)
        purge_asset(cls.asset.name)
        for dt, nm in [("AC Department", cls.dept.name),
                       ("AC Department", cls.dept_from.name),
                       ("AC Asset Category", cls.cat.name)]:
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _call_service(self) -> dict:
        from assetcore.services.imm00 import get_pending_approvals_inbox
        return get_pending_approvals_inbox()

    def _call_api(self, **kwargs) -> dict:
        from assetcore.api.imm00 import get_pending_approvals_inbox
        return get_pending_approvals_inbox(**kwargs)

    # ── TC-BE-1: QTV đủ cap cả 3 nguồn → 3 doctype, sort asc, total/by_module đúng
    def test_tc_be_1_qtv_sees_all_three_sources_sorted(self):
        """User Super Admin (cap duyệt transfer + allocation, pending_approver
        commissioning) → items chứa đủ 3 doctype fixture; sort pending_since asc
        (3 phiếu 2020 đứng đầu, đúng thứ tự comm→transfer→alloc); total==len(items);
        by_module đếm đúng theo module của từng item (robust với data pending thật
        trên site dev)."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")

        items = data["items"]
        by_name = {(i["doctype"], i["name"]): idx for idx, i in enumerate(items)}
        self.assertIn(("Asset Commissioning", _COMM_NAME), by_name,
                      "Thiếu phiếu nghiệm thu pending_approver=user")
        self.assertIn(("Asset Transfer", self.transfer_name), by_name,
                      "Thiếu phiếu điều chuyển Pending Approval")
        self.assertIn(("IMM Spare Allocation", _ALLOC_NAME), by_name,
                      "Thiếu phiếu cấp phát Requested")
        # Sort asc: 3 fixture 2020 phải đứng ĐẦU list, đúng thứ tự thời gian.
        self.assertEqual(by_name[("Asset Commissioning", _COMM_NAME)], 0)
        self.assertEqual(by_name[("Asset Transfer", self.transfer_name)], 1)
        self.assertEqual(by_name[("IMM Spare Allocation", _ALLOC_NAME)], 2)
        stamps = [i["pending_since"] for i in items]
        self.assertEqual(stamps, sorted(stamps), "items PHẢI sort pending_since asc")
        # total + by_module nhất quán với items (không đếm 2 predicate khác nhau).
        self.assertEqual(data["total"], len(items))
        for mod in ("imm00", "imm04", "imm15"):
            self.assertEqual(
                data["by_module"][mod],
                sum(1 for i in items if i["module"] == mod),
                f"by_module[{mod}] phải khớp số item module đó",
            )
        # Item shape thống nhất 10 key + enrich display.
        for i in items[:3]:
            self.assertEqual(set(i.keys()), _ITEM_KEYS,
                             f"Item shape phải đúng 10 key hợp đồng: {sorted(i.keys())}")
        trf = items[by_name[("Asset Transfer", self.transfer_name)]]
        self.assertEqual(trf["module"], "imm00")
        self.assertEqual(trf["asset"], self.asset.name)
        self.assertEqual(trf["asset_name"], "_Test Asset Inbox CR32")
        self.assertEqual(trf["route"], f"/asset-transfers/{self.transfer_name}")
        comm = items[by_name[("Asset Commissioning", _COMM_NAME)]]
        self.assertEqual(comm["module"], "imm04")
        self.assertEqual(comm["route"], f"/commissioning/{_COMM_NAME}")
        self.assertEqual(comm["requested_by"], self.base)
        # Derivation §III.22: title/asset_name = asset_description (phiếu chưa có
        # AC Asset → asset '' + display từ mô tả).
        self.assertEqual(comm["title"], _COMM_DESC)
        self.assertEqual(comm["asset_name"], _COMM_DESC)
        self.assertEqual(comm["asset"], "")

    # ── TC-BE-1b (BR-00-INBOX-02): total == len(items) == sum(by_module.values())
    def test_tc_be_1b_count_equals_rows_invariant(self):
        """Bất biến count==rows (LL-BE-42/49): KHÔNG phát count DB riêng lệch drill."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(data["total"], len(data["items"]))
        self.assertEqual(data["total"], sum(data["by_module"].values()))
        self.assertEqual(set(data["by_module"].keys()),
                         {"imm00", "imm04", "imm15", "imm09"},
                         "by_module LUÔN đủ 4 khoá (0 khi nguồn rỗng — CR-42 thêm imm09)")

    # ── TC-BE-1c: route WO-drill cấp phát theo work_order_doctype (§III.22 / ADR B)
    def test_tc_be_1c_allocation_route_wo_drill(self):
        """Cấp phát KHÔNG có detail view riêng → route drill: PM WO → /pm/work-orders,
        Asset Repair (CM) → /cm/work-orders, thiếu ref → /inventory; LUÔN non-empty."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        routes = {i["name"]: i["route"] for i in data["items"]
                  if i["doctype"] == "IMM Spare Allocation"}
        self.assertEqual(routes.get(_ALLOC_NAME), "/inventory",
                         "Thiếu work_order_ref → fallback /inventory")
        self.assertEqual(routes.get(_ALLOC_PM), f"/pm/work-orders/{_WO_PM_REF}",
                         "PM Work Order → drill /pm/work-orders/{ref}")
        self.assertEqual(routes.get(_ALLOC_CM), f"/cm/work-orders/{_WO_CM_REF}",
                         "Asset Repair (CM) → drill /cm/work-orders/{ref}")
        for i in data["items"]:
            self.assertTrue(i["route"], f"route PHẢI non-empty: {i['name']}")

    # ── TC-BE-2: user CHỈ có cap transfer → 2 nguồn kia exclude im lặng
    def test_tc_be_2_transfer_only_cap_excludes_other_sources(self):
        """Commissioning Manager (commissioning.submit, KHÔNG inventory.submit,
        KHÔNG pending_approver) → items CHỈ chứa Asset Transfer; commissioning +
        allocation exclude im lặng, KHÔNG lỗi."""
        frappe.set_user(self.transfer_only)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        doctypes = {i["doctype"] for i in data["items"]}
        self.assertEqual(doctypes, {"Asset Transfer"},
                         f"Chỉ được thấy Asset Transfer, got: {doctypes}")
        names = {i["name"] for i in data["items"]}
        self.assertIn(self.transfer_name, names)
        self.assertEqual(data["by_module"]["imm04"], 0)
        self.assertEqual(data["by_module"]["imm15"], 0)

    # ── TC-BE-3: user 0 cap duyệt → success:true + items=[] (KHÔNG throw/403)
    def test_tc_be_3_zero_cap_returns_empty_success(self):
        """Base user 0 cap duyệt → API envelope success:true, items=[], total=0
        (KHÔNG throw, KHÔNG 403 in-handler — fail-soft theo spec)."""
        frappe.set_user(self.base)
        try:
            out = self._call_api()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(out.get("success"), f"Envelope phải success:true: {out}")
        self.assertEqual(out["data"]["items"], [])
        self.assertEqual(out["data"]["total"], 0)
        self.assertEqual(out["data"]["by_module"],
                         {"imm00": 0, "imm04": 0, "imm15": 0, "imm09": 0})

    # ── TC-BE-4: guest → dispatcher-403 (PermissionError tại gate is_whitelisted)
    def test_tc_be_4_guest_dispatcher_403(self):
        """Guest/no-session → dispatcher PermissionError 403 (bare @whitelist KHÔNG
        allow_guest; gate frappe.is_whitelisted — y hệt đường đi HTTP thật)."""
        from assetcore.api import imm00 as api_imm00
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.is_whitelisted(api_imm00.get_pending_approvals_inbox)
        finally:
            frappe.set_user("Administrator")

    # ── TC-BE-5: kwarg lạ user=... bị **_ignore nuốt — vẫn scope session user
    def test_tc_be_5_spoof_user_kwarg_ignored(self):
        """Gọi kèm user='<user khác có phiếu>' → **_ignore nuốt; kết quả VẪN scope
        theo frappe.session.user (chống spoof đọc inbox người khác)."""
        frappe.set_user(self.base)
        try:
            out = self._call_api(user=self.qtv)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(out.get("success"))
        self.assertEqual(out["data"]["items"], [],
                         "Spoof kwarg user PHẢI bị nuốt — base user vẫn 0 phiếu")
        self.assertEqual(out["data"]["total"], 0)

    # ── CR-44: field `summary` VI server-built (≤120, coalesce '') ────────────
    def test_inbox_item_has_summary_key(self):
        """MỌI item có key ``summary`` là str, độ dài ≤120 (kể cả data thật trên
        site — coalesce '' non-crash). Fail TRƯỚC khi thêm field (TDD)."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(data["items"], "cần ≥1 item để kiểm summary")
        for it in data["items"]:
            self.assertIn("summary", it, "MỌI item PHẢI có key summary")
            self.assertIsInstance(it["summary"], str, "summary PHẢI là str (coalesce '')")
            self.assertLessEqual(len(it["summary"]), _SUMMARY_MAX,
                                 f"summary ≤120 ký tự: {it['summary']!r}")

    def test_inbox_summary_transfer_format(self):
        """Asset Transfer: summary = '<khoa nguồn> → <khoa đích> · <asset_name>'."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        trf = next((i for i in data["items"]
                    if i["doctype"] == "Asset Transfer" and i["name"] == self.transfer_name),
                   None)
        self.assertIsNotNone(trf, "thiếu phiếu transfer fixture")
        self.assertIn("→", trf["summary"], "transfer summary PHẢI chứa '→'")
        self.assertIn("_Test Asset Inbox CR32", trf["summary"], "PHẢI chứa asset_name")
        self.assertEqual(
            trf["summary"],
            "_TestDeptFrom Inbox CR32 → _TestDept Inbox CR32 · _Test Asset Inbox CR32")
        self.assertLessEqual(len(trf["summary"]), _SUMMARY_MAX)

    def test_inbox_summary_allocation_format(self):
        """IMM Spare Allocation: summary = '<item_name> ×<qty> <uom>' + đa dòng '…+N'."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        alloc = next((i for i in data["items"] if i["name"] == _ALLOC_PM), None)
        self.assertIsNotNone(alloc, "thiếu phiếu cấp phát _ALLOC_PM (2 dòng phụ tùng)")
        s = alloc["summary"]
        self.assertIn(_ALLOC_PM_PART1, s, "PHẢI chứa item_name dòng đầu")
        self.assertIn("×2", s, "PHẢI chứa ×<qty> (dạng ×N)")
        self.assertIn(_ALLOC_PM_UOM, s, "PHẢI chứa uom")
        self.assertIn("…+1", s, "đa dòng → dòng đầu + '…+N' (N=1 dòng còn lại)")
        self.assertEqual(s, f"{_ALLOC_PM_PART1} ×2 {_ALLOC_PM_UOM} …+1")

    def test_inbox_summary_commissioning_stage(self):
        """Asset Commissioning: summary khớp 'Nghiệm thu ban đầu · bậc X/Y'."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        comm = next((i for i in data["items"] if i["name"] == _COMM_NAME), None)
        self.assertIsNotNone(comm, "thiếu phiếu nghiệm thu fixture")
        self.assertRegex(comm["summary"], r"^Nghiệm thu ban đầu · bậc \d+/\d+$")
        # approval_stage='Doc Verify' = bậc 1 trong 4 (SSoT Select opts).
        self.assertEqual(comm["summary"], "Nghiệm thu ban đầu · bậc 1/4")

    def test_inbox_summary_coalesce_blank(self):
        """Thiếu dữ liệu (cấp phát 0 dòng phụ tùng) → summary là str '' non-crash
        (KHÔNG None, KHÔNG raise); mọi item khác cũng str (real-data dangling-safe)."""
        frappe.set_user(self.qtv)
        try:
            data = self._call_service()
        finally:
            frappe.set_user("Administrator")
        alloc0 = next((i for i in data["items"] if i["name"] == _ALLOC_NAME), None)
        self.assertIsNotNone(alloc0, "thiếu _ALLOC_NAME (0 dòng phụ tùng)")
        self.assertIsInstance(alloc0["summary"], str)
        self.assertEqual(alloc0["summary"], "",
                         "cấp phát 0 dòng phụ tùng → summary coalesce '' (non-crash)")
        for it in data["items"]:
            self.assertIsInstance(it["summary"], str,
                                  f"summary phải str non-crash: {it['name']}")

    def test_inbox_summary_no_n_plus_1(self):
        """Denorm summary batch: query-count KHÔNG tăng tuyến tính theo N item nhiều
        nguồn (dept/location + child phụ tùng gom 1 query/loại — chống N+1)."""
        from assetcore.services import imm00 as svc
        frappe.set_user("Administrator")

        def _mk_specs(n):
            items, specs = [], []
            for _ in range(n):
                items.append(svc._inbox_item(
                    doctype="Asset Transfer", name="x", module="imm00", title="",
                    asset="", requested_by="", pending_since="", route="/x"))
                specs.append({"idx": len(items) - 1, "kind": "transfer",
                              "from_department": self.dept_from.name,
                              "to_department": self.dept.name,
                              "from_location": None, "to_location": None})
                items.append(svc._inbox_item(
                    doctype="IMM Spare Allocation", name="y", module="imm15", title="",
                    asset="", requested_by="", pending_since="", route="/y"))
                specs.append({"idx": len(items) - 1, "kind": "allocation",
                              "alloc": _ALLOC_PM})
            return items, specs

        def _count(items, specs):
            calls = {"n": 0}
            orig = frappe.db.sql

            def _wrap(*a, **k):
                calls["n"] += 1
                return orig(*a, **k)

            frappe.db.sql = _wrap
            try:
                svc._build_inbox_summaries(items, specs)
            finally:
                frappe.db.sql = orig
            return calls["n"]

        # Warm meta/schema cache → query-count phản ánh DATA query, không cache-warm.
        _count(*_mk_specs(1))
        items_s, specs_s = _mk_specs(2)
        q_small = _count(items_s, specs_s)
        q_large = _count(*_mk_specs(10))
        self.assertEqual(q_small, q_large,
                         f"denorm PHẢI batch — query KHÔNG tăng theo N "
                         f"(N=2→{q_small}, N=10→{q_large}); N+1 sẽ khiến large≫small")
        self.assertLessEqual(q_large, 4,
                             f"≤ vài batch query (dept+location+alloc-items): {q_large}")
        # Sanity: batch resolve ĐÚNG (summary thực sự dựng, không rỗng do bug).
        self.assertIn("→", items_s[0]["summary"])
        self.assertIn("×", items_s[1]["summary"])

    def test_inbox_still_session_scoped(self):
        """BẤT BIẾN: endpoint KHÔNG nhận param ``user`` (session-scoped chống spoof);
        service không nhận tham số. Regression signature."""
        import inspect
        from assetcore.api.imm00 import get_pending_approvals_inbox as api_fn
        from assetcore.services.imm00 import get_pending_approvals_inbox as svc_fn
        api_params = inspect.signature(api_fn).parameters
        self.assertNotIn("user", api_params,
                         "endpoint KHÔNG nhận param user (spoof-surface) — session-scoped")
        self.assertTrue(
            all(p.kind == inspect.Parameter.VAR_KEYWORD for p in api_params.values()),
            f"api chỉ được có **kwargs (nuốt kwargs lạ): {list(api_params)}")
        self.assertEqual(list(inspect.signature(svc_fn).parameters), [],
                         "service get_pending_approvals_inbox KHÔNG nhận tham số")


class TestInboxPendingInspectionCR42(unittest.TestCase):
    """CR-42 — NGUỒN THỨ 4: Asset Repair 'Pending Inspection' (Nghiệm thu CM).

    Đối xứng CR-41 (SoD close_work_order↔confirm_inspection): phiếu CM đã đóng
    (event repair_pending_inspection, actor=closer) chờ nghiệm thu. Inbox hiển thị
    ⇔ user có cap ``repair.submit`` (cùng cap confirm_inspection enforce) VÀ KHÁC
    người đóng phiếu (closer≠session.user). Unknown-closer → FAIL-OPEN (vẫn hiện,
    đối xứng confirm_inspection). TDD viết TRƯỚC implement (CLAUDE.md §17).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._users: list[str] = []

        # A: có cap repair.submit (Repair Manager), KHÁC người đóng phiếu → duyệt được.
        cls.approver = _mk_user("_test_inbox_cm_approver_cr42@assetcore.test",
                                ["AssetCore System User", "Repair Manager"],
                                cls._users)
        # B: người ĐÓNG phiếu (closer) — CŨNG có repair.submit nhưng SoD chặn tự-nghiệm-thu.
        cls.closer = _mk_user("_test_inbox_cm_closer_cr42@assetcore.test",
                              ["AssetCore System User", "Repair Manager"],
                              cls._users)
        # C: 0 cap repair.submit → 0 item imm09 (exclude im lặng).
        cls.base = _mk_user("_test_inbox_cm_base_cr42@assetcore.test",
                            ["AssetCore System User"], cls._users)

        # Asset thật (enrich asset_name imm09 item phải hoạt động).
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCat InboxCM CR42",
        }).insert(ignore_permissions=True)
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_Test Asset InboxCM CR42",
                "asset_category": cls.cat.name,
                "manufacturer_sn": f"SN-INBOXCM-{int(time.time() * 1000) % 10_000_000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

        # WO #1 — Pending Inspection + event repair_pending_inspection (actor=B).
        #   Raw-SQL insert (precedent _COMM_NAME/_ALLOC_*): bỏ qua reqd-link validation
        #   + workflow-state guard; inbox chỉ ĐỌC header.
        for wo, mod in ((_WO_CM_INSPECT, "2020-01-06 08:00:00"),
                        (_WO_CM_NOEVT, _T_NOEVT_MOD)):
            frappe.db.sql(
                "INSERT INTO `tabAsset Repair` "
                "(name, docstatus, status, workflow_state, asset_ref, repair_summary, "
                " assigned_to, requested_by, owner, creation, modified) "
                "VALUES (%s, 0, 'Pending Inspection', 'Pending Inspection', %s, %s, "
                "        %s, %s, %s, %s, %s)",
                (wo, cls.asset.name, _CM_SUMMARY, cls.closer, cls.closer,
                 cls.closer, mod, mod),
            )
        # Event repair_pending_inspection cho WO #1 (actor=closer=B) → closer resolve = B.
        #   WO #2 KHÔNG có event → _resolve_wo_closer = None → fail-open.
        frappe.db.sql(
            "INSERT INTO `tabAsset Lifecycle Event` "
            "(name, event_type, asset, actor, root_doctype, root_record, timestamp, "
            " owner, creation, modified) "
            "VALUES (%s, 'repair_pending_inspection', %s, %s, 'Asset Repair', %s, %s, "
            "        %s, %s, %s)",
            ("_TEST-INBOX-ALE-CR42", cls.asset.name, cls.closer, _WO_CM_INSPECT,
             _T_INSPECT_EVT, cls.closer, _T_INSPECT_EVT, _T_INSPECT_EVT),
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.db.sql(
            "DELETE FROM `tabAsset Repair` WHERE name IN (%s, %s)",
            (_WO_CM_INSPECT, _WO_CM_NOEVT),
        )
        frappe.db.sql(
            "DELETE FROM `tabAsset Lifecycle Event` WHERE root_record IN (%s, %s)",
            (_WO_CM_INSPECT, _WO_CM_NOEVT),
        )
        purge_asset(cls.asset.name)
        if frappe.db.exists("AC Asset Category", cls.cat.name):
            frappe.delete_doc("AC Asset Category", cls.cat.name, force=True,
                              ignore_permissions=True)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def _inbox_as(self, user: str) -> dict:
        from assetcore.services.imm00 import get_pending_approvals_inbox
        frappe.set_user(user)
        try:
            return get_pending_approvals_inbox()
        finally:
            frappe.set_user("Administrator")

    # ── TC-1: A (cap repair.submit, A≠closer) → item xuất hiện, shape 10-key đúng.
    def test_inbox_includes_pending_inspection_for_authorized_non_closer(self):
        data = self._inbox_as(self.approver)
        by_name = {i["name"]: i for i in data["items"]}
        self.assertIn(_WO_CM_INSPECT, by_name,
                      "Phiếu CM Pending Inspection PHẢI hiện cho user có cap ≠ closer")
        it = by_name[_WO_CM_INSPECT]
        self.assertEqual(it["doctype"], "Asset Repair")
        self.assertEqual(it["module"], "imm09")
        self.assertEqual(it["route"], f"/cm/work-orders/{_WO_CM_INSPECT}")
        self.assertEqual(set(it.keys()), _ITEM_KEYS,
                         f"Item shape PHẢI đúng 10 key hợp đồng: {sorted(it.keys())}")
        # title = repair_summary; asset = asset_ref (enrich asset_name).
        self.assertEqual(it["title"], _CM_SUMMARY)
        self.assertEqual(it["asset"], self.asset.name)
        self.assertEqual(it["asset_name"], "_Test Asset InboxCM CR42")
        # requested_by = closer (người đóng phiếu = người đề nghị nghiệm thu).
        self.assertEqual(it["requested_by"], self.closer)
        # pending_since = ts event repair_pending_inspection.
        self.assertEqual(it["pending_since"], _T_INSPECT_EVT)

    # ── TC-2: B (chính người đóng, closer==session.user) → item KHÔNG hiện (SoD).
    def test_inbox_excludes_self_closed_wo_segregation_of_duties(self):
        data = self._inbox_as(self.closer)
        names = {i["name"] for i in data["items"]}
        self.assertNotIn(_WO_CM_INSPECT, names,
                         "SoD: người tự đóng phiếu KHÔNG được thấy dòng tự-nghiệm-thu "
                         "(chống dead-end click→422)")

    # ── TC-3: C (0 cap repair.submit) → 0 item imm09; success; nguồn khác im lặng.
    def test_inbox_no_imm09_items_without_repair_submit_cap(self):
        from assetcore.api.imm00 import get_pending_approvals_inbox as _api
        frappe.set_user(self.base)
        try:
            out = _api()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(out.get("success"), f"Envelope PHẢI success:true: {out}")
        imm09 = [i for i in out["data"]["items"] if i["module"] == "imm09"]
        self.assertEqual(imm09, [], "0 cap repair.submit → 0 item imm09 (exclude im lặng)")
        self.assertEqual(out["data"]["by_module"]["imm09"], 0)

    # ── TC-4: by_module có khoá imm09 + bất biến BR-00-INBOX-02 total==len==sum.
    def test_inbox_by_module_has_imm09_key_and_total_invariant(self):
        data = self._inbox_as(self.approver)
        self.assertIn("imm09", data["by_module"], "by_module PHẢI có khoá imm09 (CR-42)")
        self.assertEqual(data["total"], len(data["items"]))
        self.assertEqual(data["total"], sum(data["by_module"].values()),
                         "BR-00-INBOX-02: total==len(items)==sum(by_module.values())")
        self.assertEqual(
            data["by_module"]["imm09"],
            sum(1 for i in data["items"] if i["module"] == "imm09"),
            "by_module[imm09] PHẢI khớp số item module imm09",
        )
        # ≥ 2 fixture Pending Inspection (WO có-event + WO no-event fail-open) đều hiện.
        names = {i["name"] for i in data["items"]}
        self.assertIn(_WO_CM_INSPECT, names)
        self.assertIn(_WO_CM_NOEVT, names)

    # ── TC-5: closer unknown (KHÔNG event) → fail-open, VẪN hiện cho user có cap.
    def test_inbox_pending_inspection_closer_unknown_fail_open(self):
        data = self._inbox_as(self.approver)
        by_name = {i["name"]: i for i in data["items"]}
        self.assertIn(_WO_CM_NOEVT, by_name,
                      "Unknown-closer (0 event repair_pending_inspection) → FAIL-OPEN "
                      "(đối xứng CR-41 confirm_inspection)")
        it = by_name[_WO_CM_NOEVT]
        self.assertEqual(it["module"], "imm09")
        self.assertEqual(it["route"], f"/cm/work-orders/{_WO_CM_NOEVT}")
        # closer None → pending_since fallback = modified WO.
        self.assertEqual(it["pending_since"], _T_NOEVT_MOD)
        # requested_by fallback (closer None) = assigned_to → owner (KHÔNG rỗng).
        self.assertEqual(it["requested_by"], self.closer)

    # ── CR-44: repair CM summary = '<failure_description|repair_summary> · <asset_name>'
    def test_inbox_summary_repair_cm_format(self):
        """Asset Repair CM: summary chứa failure_description/repair_summary + asset_name."""
        data = self._inbox_as(self.approver)
        by_name = {i["name"]: i for i in data["items"]}
        self.assertIn(_WO_CM_INSPECT, by_name, "thiếu phiếu CM Pending Inspection")
        it = by_name[_WO_CM_INSPECT]
        s = it["summary"]
        # Fixture KHÔNG set failure_description → fallback repair_summary (_CM_SUMMARY).
        self.assertIn(_CM_SUMMARY, s, "PHẢI chứa repair_summary/failure_description")
        self.assertIn("_Test Asset InboxCM CR42", s, "PHẢI chứa asset_name")
        self.assertEqual(s, f"{_CM_SUMMARY} · _Test Asset InboxCM CR42")
        self.assertLessEqual(len(s), _SUMMARY_MAX)


class TestInboxTruncationContract(unittest.TestCase):
    """CR-43 — hợp đồng TRUNG THỰC khi cắt inbox: get_pending_approvals_inbox trả
    THÊM ``truncated`` (int 0/1) + ``totals_uncapped`` (4 khoá int) + ``excluded_modules``
    (list[str] ⊆ {imm00, imm15, imm09}); 3 khoá cũ items/total/by_module GIỮ shape.

    TDD viết TRƯỚC implement (CLAUDE.md §17). Nguồn cap-based (imm00/imm15/imm09)
    thiếu cap → excluded IM LẶNG + báo qua excluded_modules; imm04 identity-based
    KHÔNG bao giờ excluded. Zero-cost (AC2): KHÔNG COUNT nào chạy ca không-cắt.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._users: list[str] = []
        cls._transfers: list[str] = []
        cls._assets: list[str] = []

        # QTV đủ CẢ 3 cap duyệt (transfer=commissioning.submit / allocation=
        # inventory.submit / inspect=repair.submit) → excluded_modules==[].
        cls.qtv = _mk_user("_test_inbox_trunc_qtv@assetcore.test",
                           ["AssetCore System User", "AssetCore Super Admin",
                            "Repair Manager"], cls._users)
        # Base user 0 cap duyệt → 3 nguồn cap-based excluded.
        cls.base = _mk_user("_test_inbox_trunc_base@assetcore.test",
                            ["AssetCore System User"], cls._users)

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCat InboxTrunc CR43",
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestDept InboxTrunc CR43",
        }).insert(ignore_permissions=True)

        # 2 Asset Transfer 'Pending Approval' (creation 2020 → oldest, fetched-first
        # với order creation asc bất kể data dev). 2 asset RIÊNG (né guard 1-pending/asset).
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            for i in range(2):
                a = frappe.get_doc({
                    "doctype": "AC Asset",
                    "asset_name": f"_Test Asset InboxTrunc {i}",
                    "asset_category": cls.cat.name,
                    "manufacturer_sn": f"SN-TRUNC-{int(time.time() * 1000) % 10_000_000}-{i}",
                    "lifecycle_status": "Commissioned",
                }).insert(ignore_permissions=True)
                cls._assets.append(a.name)
                td = frappe.get_doc({
                    "doctype": "Asset Transfer",
                    "asset": a.name,
                    "transfer_type": "Internal",
                    "transfer_date": nowdate(),
                    "to_department": cls.dept.name,
                    "reason": f"Kiểm thử truncation inbox #{i}",
                })
                td.insert(ignore_permissions=True)
                frappe.db.set_value("Asset Transfer", td.name, {
                    "status": "Pending Approval",
                    "creation": f"2020-01-0{i + 1} 08:00:00",
                }, update_modified=False)
                cls._transfers.append(td.name)
        finally:
            frappe.flags.in_install = prev
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._transfers:
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True,
                                  ignore_permissions=True)
        for a in cls._assets:
            purge_asset(a)
        for dt, nm in [("AC Department", cls.dept.name),
                       ("AC Asset Category", cls.cat.name)]:
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def _inbox_as(self, user: str) -> dict:
        from assetcore.services.imm00 import get_pending_approvals_inbox
        frappe.set_user(user)
        try:
            return get_pending_approvals_inbox()
        finally:
            frappe.set_user("Administrator")

    # ── T1: dưới trần, đủ cap → truncated=0, totals_uncapped==by_module, excluded==[]
    def test_inbox_untruncated_totals_equal_by_module(self):
        from unittest.mock import patch
        from assetcore.services import imm00 as svc
        # Trần khổng lồ ⇒ KHÔNG nguồn nào chạm trần (deterministic bất kể data dev).
        with patch.object(svc, "_INBOX_LIMIT_PER_SOURCE", 10 ** 6):
            data = self._inbox_as(self.qtv)
        self.assertEqual(data["truncated"], 0, "không nguồn nào chạm trần ⇒ truncated=0")
        self.assertEqual(data["totals_uncapped"], data["by_module"],
                         "không cắt ⇒ totals_uncapped[m]==by_module[m] cho MỌI m")
        self.assertEqual(data["excluded_modules"], [],
                         "QTV đủ 3 cap ⇒ excluded_modules rỗng")

    # ── T2: zero-cost — KHÔNG COUNT nào chạy ca không-cắt (AC2)
    def test_inbox_no_extra_count_query_when_untruncated(self):
        from unittest.mock import patch
        from assetcore.services import imm00 as svc
        calls = {"n": 0}
        real = svc._inbox_source_count

        def _spy(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        with patch.object(svc, "_INBOX_LIMIT_PER_SOURCE", 10 ** 6), \
                patch.object(svc, "_inbox_source_count", _spy):
            self._inbox_as(self.qtv)
        self.assertEqual(calls["n"], 0,
                         "ca không-cắt PHẢI 0 COUNT (zero-cost — count_fn lazy)")

    # ── T3: nguồn chạm trần → truncated=1, by_module cắt, totals_uncapped=COUNT thật
    def test_inbox_truncated_flag_and_uncapped_count(self):
        from unittest.mock import patch
        from assetcore.services import imm00 as svc
        calls = {"n": 0}
        real = svc._inbox_source_count

        def _spy(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        pending_total = frappe.db.count("Asset Transfer",
                                        {"status": "Pending Approval"})
        self.assertGreaterEqual(pending_total, 2, "≥2 transfer Pending (2 seed)")
        with patch.object(svc, "_INBOX_LIMIT_PER_SOURCE", 1), \
                patch.object(svc, "_inbox_source_count", _spy):
            data = self._inbox_as(self.qtv)
        self.assertEqual(data["truncated"], 1, "∃ nguồn chạm trần ⇒ truncated=1")
        self.assertEqual(data["by_module"]["imm00"], 1,
                         "limit=1 ⇒ CHỈ 1 item transfer (count==rows GIỮ)")
        self.assertEqual(data["totals_uncapped"]["imm00"], pending_total,
                         "totals_uncapped[imm00] = COUNT DB cùng predicate (≥2)")
        self.assertGreater(data["totals_uncapped"]["imm00"], data["by_module"]["imm00"],
                           "uncapped > hiển thị ⇒ chính là nguồn khiến truncated=1")
        self.assertGreaterEqual(calls["n"], 1,
                                "nguồn chạm trần PHẢI gọi COUNT (đúng nguồn đó)")

    # ── T4: thiếu cap → excluded_modules; imm04 identity KHÔNG bao giờ excluded
    def test_inbox_excluded_modules_when_missing_cap(self):
        out = None
        from assetcore.api.imm00 import get_pending_approvals_inbox as _api
        frappe.set_user(self.base)
        try:
            out = _api()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(out.get("success"), f"envelope PHẢI success (fail-soft): {out}")
        data = out["data"]
        ex = set(data["excluded_modules"])
        self.assertEqual(ex, {"imm00", "imm15", "imm09"},
                         "base user 0 cap ⇒ 3 nguồn cap-based excluded")
        self.assertNotIn("imm04", data["excluded_modules"],
                         "imm04 identity-based KHÔNG bao giờ excluded")
        mods = {i["module"] for i in data["items"]}
        self.assertFalse(mods & {"imm00", "imm15", "imm09"},
                         "items KHÔNG chứa module đã excluded")

    # ── T5: kiểu cờ int (KHÔNG bool/None) — parity CR-01
    def test_inbox_flag_types_int_not_bool(self):
        data = self._inbox_as(self.qtv)
        t = data["truncated"]
        self.assertIsInstance(t, int)
        self.assertNotIsInstance(t, bool, "truncated int (KHÔNG bool)")
        self.assertIn(t, (0, 1), "truncated ∈ {0,1}")
        self.assertEqual(set(data["totals_uncapped"].keys()),
                         {"imm00", "imm04", "imm15", "imm09"},
                         "totals_uncapped đủ 4 khoá")
        for m, v in data["totals_uncapped"].items():
            self.assertIsInstance(v, int, f"totals_uncapped[{m}] int")
            self.assertNotIsInstance(v, bool, f"totals_uncapped[{m}] KHÔNG bool")
            self.assertGreaterEqual(v, 0, f"totals_uncapped[{m}] ≥ 0")
        self.assertIsInstance(data["excluded_modules"], list)
        for m in data["excluded_modules"]:
            self.assertIsInstance(m, str, "excluded_modules là list[str]")

    # ── T6: legacy shape non-regression (BR-00-INBOX-02)
    def test_inbox_legacy_shape_non_regression(self):
        data = self._inbox_as(self.qtv)
        self.assertEqual(data["total"], len(data["items"]),
                         "total == len(items)")
        self.assertEqual(data["total"], sum(data["by_module"].values()),
                         "total == sum(by_module.values())")
        for it in data["items"]:
            self.assertEqual(set(it.keys()), _ITEM_KEYS,
                             f"item GIỮ đủ 11 khoá cũ: {sorted(it.keys())}")


if __name__ == "__main__":
    unittest.main()
