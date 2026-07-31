# assetcore/tests/test_rowscope_docperm_gate.py
# Copyright (c) 2026, AssetCore Team
"""INV-ROWSCOPE gap guard — `scope="system"` KHÔNG được biến thành DocPerm bypass.

Bối cảnh (vòng INV-ROWSCOPE, ADR-IMM00-LIST-SCOPE §8): `BaseRepository.list` được
tham-số-hoá `scope`. Trước vòng này MỌI call site đều chạy `count_with_or` →
`frappe.get_list` ⇒ DocPerm `read` bị enforce (dù chỉ là tác dụng phụ). Sau vòng:

  * `scope="system"` ⇒ CẢ count LẪN rows đi `frappe.get_all` ⇒ **mất luôn kiểm tra
    DocPerm read cấp-vai-trò**, không chỉ mất row-scope. ADR D6 chỉ chốt nới
    ROW-scope (ai-được-giao), KHÔNG chốt nới ROLE-scope (vai-trò-nào-được-đọc).
  * `count_overdue_pm` chuyển `PMWorkOrderRepo.count` (frappe.db.count, KHÔNG
    permission) → `count_with_or` (frappe.get_list, RAISE PermissionError) ⇒ tạo
    bề mặt raise MỚI ở `imm08.get_dashboard_stats` (KHÔNG có `run_rowscoped` /
    `_scoped_helper` bọc) ⇒ HTTP 500 câm thay vì envelope.

3 test dưới đây là hợp đồng: endpoint whitelist KHÔNG được phục vụ dữ liệu của
DocType mà session-user không có DocPerm `read`, và KHÔNG được ném PermissionError
trần ra khỏi `handle()`.

Run: bench --site miyano run-tests --app assetcore \
     --module assetcore.tests.test_rowscope_docperm_gate
"""
from __future__ import annotations

import time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from assetcore.api.imm08 import (get_due_pm_schedules, get_pm_calendar,
                                 get_pm_dashboard_stats)
from assetcore.api.imm09 import get_asset_repair_history
from assetcore.api.imm12 import get_asset_incident_history
from assetcore.services.imm09 import RepairStatus
from assetcore.tests._asset_cleanup import purge_asset

_PM_ONLY = "docperm_gate_pm@example.invalid"      # read PM WO, KHÔNG read Asset Repair
_REPAIR_ONLY = "docperm_gate_repair@example.invalid"  # read Asset Repair, KHÔNG read PM WO
_OWNER = "docperm_gate_owner@example.invalid"     # người được giao phiếu (senior)
# Vendor Engineer = nhân sự NGOÀI viện. `incident_report_query` (permissions.py:96)
# giới hạn họ ở incident của asset họ phụ trách — clause đó KHÔNG chạy trên
# `frappe.get_all`, nên isolation của vendor ở endpoint device-centric phụ thuộc
# HOÀN TOÀN vào DocPerm read (Vendor Engineer: 0 read trên Incident Report).
_VENDOR = "docperm_gate_vendor@example.invalid"
_ALL_USERS = (_PM_ONLY, _REPAIR_ONLY, _OWNER, _VENDOR)
_CAT_NAME = "_DocPermGate Test Category"


def _ensure_user(email: str, first_name: str, *roles: str) -> str:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User", "email": email, "first_name": first_name,
        "send_welcome_email": 0, "enabled": 1,
    }).insert(ignore_permissions=True)
    if roles:
        u.add_roles(*roles)
    return u.name


class TestRowScopeDocPermGate(FrappeTestCase):
    """scope="system" phải giữ DocPerm read cấp-vai-trò (OWASP A01 broken access control)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = frappe.db.get_value("AC Asset Category", {"category_name": _CAT_NAME}, "name")
        if not cls.cat:
            cls.cat = frappe.get_doc({
                "doctype": "AC Asset Category", "category_name": _CAT_NAME,
                "default_pm_interval_days": 90,
            }).insert(ignore_permissions=True).name

        # Senior: read-all cả 2 doctype ⇒ dùng làm assignee (phiếu KHÔNG thuộc
        # 2 persona bị test) — chứng minh leak là leak THẬT, không phải "phiếu của tôi".
        cls.owner = _ensure_user(_OWNER, "Gate Owner", "Repair Manager", "PM Manager")
        cls.pm_only = _ensure_user(_PM_ONLY, "Gate PM", "PM User", "AssetCore System User")
        cls.repair_only = _ensure_user(_REPAIR_ONLY, "Gate Repair",
                                       "Repair User", "AssetCore System User")
        cls.vendor = _ensure_user(_VENDOR, "Gate Vendor",
                                  "Vendor Engineer", "AssetCore System User")

        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_DocPermGate Asset",
                "asset_category": cls.cat,
                "manufacturer_sn": f"DPG-SN-{int(time.time()) % 100000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True).name
        finally:
            frappe.flags.in_install = prev

        # Asset Repair ĐÃ SUBMIT (get_asset_history lọc docstatus=1) của OWNER.
        rep = frappe.get_doc({
            "doctype": "Asset Repair", "asset_ref": cls.asset,
            "repair_type": "Corrective", "priority": "Normal",
            "failure_description": "_DocPermGate fixture failure",
            "status": RepairStatus.ASSIGNED, "assigned_to": cls.owner,
        }).insert(ignore_permissions=True)
        cls.repair = rep.name
        frappe.db.set_value("Asset Repair", cls.repair, "docstatus", 1, update_modified=False)

        cls.template = frappe.get_doc({
            "doctype": "PM Checklist Template", "template_name": "_DocPermGate Template",
            "asset_category": cls.cat, "pm_type": "Quarterly",
            "checklist_items": [{"description": "_DPG check", "measurement_type": "Pass/Fail"}],
        }).insert(ignore_permissions=True).name
        cls.sched = frappe.get_doc({
            "doctype": "PM Schedule", "asset_ref": cls.asset, "pm_type": "Quarterly",
            "pm_interval_days": 90, "checklist_template": cls.template, "status": "Active",
        }).insert(ignore_permissions=True).name
        due = nowdate()
        cls.pm_wo = frappe.get_doc({
            "doctype": "PM Work Order", "asset_ref": cls.asset, "pm_schedule": cls.sched,
            "pm_type": "Quarterly", "wo_type": "Preventive", "status": "Open",
            "due_date": due, "scheduled_date": due, "assigned_to": cls.owner,
        }).insert(ignore_permissions=True).name
        frappe.db.set_value("PM Work Order", cls.pm_wo, "status", "Overdue",
                            update_modified=False)
        frappe.db.set_value("PM Schedule", cls.sched, "next_due_date",
                            add_days(nowdate(), 3), update_modified=False)

        # Thành viên thứ 3 của bộ-ba lịch-sử-thiết-bị (CR-69): Incident Report.
        # `reported_by` = OWNER (KHÔNG phải persona bị test) và asset KHÔNG có
        # `responsible_technician` ⇒ CẢ HAI clause của `incident_report_query`
        # (vendor: asset-phụ-trách; technician: reported_by) đều loại bản ghi này
        # ra khỏi tầm nhìn của pm_only/vendor ⇒ thấy nó = leak THẬT.
        cls.incident = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": cls.asset,
            "incident_type": "Malfunction",
            "severity": "Low",
            "description": "_DocPermGate fixture incident",
            "reported_by": cls.owner,
            "status": "Open",
        }).insert(ignore_permissions=True).name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for dt, name in (("PM Work Order", getattr(cls, "pm_wo", None)),
                         ("PM Schedule", getattr(cls, "sched", None)),
                         ("PM Checklist Template", getattr(cls, "template", None))):
            if name and frappe.db.exists(dt, name):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        if getattr(cls, "repair", None) and frappe.db.exists("Asset Repair", cls.repair):
            frappe.db.set_value("Asset Repair", cls.repair, "docstatus", 0,
                                update_modified=False)
            frappe.delete_doc("Asset Repair", cls.repair, force=True, ignore_permissions=True)
        if getattr(cls, "asset", None):
            purge_asset(cls.asset)
        if frappe.db.exists("AC Asset Category", getattr(cls, "cat", "")):
            frappe.delete_doc("AC Asset Category", cls.cat, force=True, ignore_permissions=True)
        for email in _ALL_USERS:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── G1 — get_asset_repair_history KHÔNG phục vụ DocType user không được đọc ──
    def test_repair_history_denied_without_asset_repair_docperm(self):
        frappe.set_user(self.pm_only)
        self.assertFalse(
            frappe.has_permission("Asset Repair", "read"),
            "tiền đề fixture: PM User KHÔNG có DocPerm read trên Asset Repair",
        )
        env = get_asset_repair_history(asset_ref=self.asset, limit="10")
        names = [h["name"] for h in ((env.get("data") or {}).get("history") or [])]
        self.assertNotIn(
            self.repair, names,
            "RÒ DỮ LIỆU (OWASP A01): persona KHÔNG có DocPerm read trên `Asset Repair` "
            "vẫn nhận được bản ghi sửa chữa qua `get_asset_repair_history` — "
            'scope="system" (ADR §8.4 R5) bỏ qua CẢ row-scope LẪN DocPerm cấp vai trò. '
            "Fix: gate `frappe.has_permission('Asset Repair', 'read')` (hoặc rbac cap) "
            "ở API/service TRƯỚC khi phục vụ rows scope=system.",
        )

    # ── G2 — get_pm_calendar đối xứng ────────────────────────────────────────
    def test_pm_calendar_denied_without_pm_wo_docperm(self):
        frappe.set_user(self.repair_only)
        self.assertFalse(
            frappe.has_permission("PM Work Order", "read"),
            "tiền đề fixture: Repair User KHÔNG có DocPerm read trên PM Work Order",
        )
        d = frappe.utils.getdate(nowdate())
        env = get_pm_calendar(year=d.year, month=d.month)
        events = (env.get("data") or {}).get("events") or []
        self.assertNotIn(
            self.pm_wo, [e.get("name") for e in events],
            "RÒ DỮ LIỆU (OWASP A01): persona KHÔNG có DocPerm read trên `PM Work Order` "
            'vẫn nhận lịch PM toàn viện (scope="system", ADR §8.4 P3) — kèm `assigned_to`. '
            "api/imm08.py:220 tự mô tả nhóm endpoint này là 'DocPerm-governed' ⇒ bất biến "
            "đó đã vỡ.",
        )

    # ── G3 — count_overdue_pm KHÔNG được ném PermissionError trần ────────────
    def test_pm_dashboard_stats_no_bare_permission_error(self):
        """BR-00-ROWSCOPE-403: lỗi quyền = envelope, KHÔNG 500 câm."""
        frappe.set_user(self.repair_only)
        try:
            env = get_pm_dashboard_stats(year=frappe.utils.getdate(nowdate()).year,
                                         month=frappe.utils.getdate(nowdate()).month)
        except frappe.PermissionError:
            self.fail(
                "REGRESSION: `count_overdue_pm` đổi `PMWorkOrderRepo.count` "
                "(frappe.db.count, KHÔNG permission) → `count_with_or` "
                "(frappe.get_list, RAISE) ⇒ `imm08.get_dashboard_stats:1457` ném "
                "`frappe.PermissionError` TRẦN qua `handle()` (handle KHÔNG bắt "
                "Exception chung) ⇒ HTTP 500 / trang lỗi Frappe cho persona thiếu "
                "DocPerm read PM Work Order. Fix: bọc `run_rowscoped` quanh "
                "`get_dashboard_stats` (BR-00-ROWSCOPE-403) hoặc `_scoped_helper` "
                "quanh `count_overdue_pm()` tại imm08.py:1457."
            )
        self.assertIsInstance(env, dict)
        self.assertIn("success", env)

    # ── G4 — get_due_pm_schedules đối xứng (bề mặt CÙNG lớp) ────────────────
    def test_due_pm_schedules_no_bare_permission_error(self):
        frappe.set_user(self.repair_only)
        try:
            env = get_due_pm_schedules(days=30, limit=5)
        except frappe.PermissionError:
            self.fail(
                "`get_due_pm_schedules` (api/imm08.py:218, bare @whitelist) ném "
                "`frappe.PermissionError` TRẦN cho persona thiếu DocPerm read `PM "
                "Schedule` — `PMScheduleRepo.list` mặc định scope='user' ⇒ "
                "frappe.get_list RAISE. Cần `run_rowscoped` như 2 `list_work_orders`."
            )
        self.assertIsInstance(env, dict)

    # ── G5 — get_asset_incident_history (thành viên thứ 3 của bộ-ba CR-69) ───
    def test_incident_history_denied_without_incident_docperm(self):
        """`Incident Report` chỉ có 5 role DocPerm read ⇒ persona khác KHÔNG được
        phục vụ dòng nào, KỂ CẢ chỉ số đếm (`total`)."""
        frappe.set_user(self.pm_only)
        self.assertFalse(
            frappe.has_permission("Incident Report", "read"),
            "tiền đề fixture: PM User KHÔNG có DocPerm read trên Incident Report "
            "(5 role có read: Auditor / Super Admin / Commissioning Manager / "
            "Corrective User / Corrective Manager)",
        )
        env = get_asset_incident_history(asset=self.asset, limit=10)
        data = env.get("data") or {}
        items = data.get("items") or []
        self.assertNotIn(
            self.incident, [i.get("name") for i in items],
            "RÒ DỮ LIỆU (OWASP A01): `get_asset_incident_history` gọi thẳng "
            "`frappe.get_all('Incident Report')` ⇒ bỏ CẢ DocPerm read cấp vai-trò "
            "LẪN `permission_query_conditions` (permissions.py:96 — clause vendor "
            "asset-phụ-trách + clause technician reported_by). 2 anh em cùng bộ-ba "
            "ĐÃ gate (imm08 ServiceError FORBIDDEN / imm09 "
            "assert_doctype_read_permission). Fix: gate role + @rowscoped.",
        )
        self.assertFalse(
            env.get("success"),
            "persona thiếu DocPerm read PHẢI nhận Error envelope (403 trên "
            "HTTP-200, BR-00-ROWSCOPE-403) — KHÔNG success:true, KHÔNG list rỗng "
            "giả (silent-empty che RBAC misconfig = dead-gate).",
        )
        self.assertNotIn(
            "total", data,
            "CR-69 thêm `total` = COUNT DB thật KHÔNG qua permission ⇒ nếu vẫn trả "
            "về, endpoint lộ TỔNG SỐ sự cố của thiết bị (disclosure MỚI, vượt cả "
            "`limit`) cho persona không được đọc bảng.",
        )

    # ── G6 — vendor isolation ở endpoint device-centric ─────────────────────
    def test_incident_history_vendor_isolated(self):
        """Vendor Engineer (nhân sự NGOÀI viện) KHÔNG được đọc sự cố của thiết bị
        họ không phụ trách.

        ⚠️ Isolation này hiện dựa HOÀN TOÀN vào DocPerm read (Vendor Engineer có 0
        read trên `Incident Report`) — clause row-scope `incident_report_query`
        KHÔNG chạy vì endpoint là device-centric (`scope="system"`, ADR §8.2 D6).
        Nếu [BA] cấp DocPerm read cho Vendor Engineer thì PHẢI đồng thời chuyển
        endpoint sang row-scope, nếu không test này đỏ ⇒ đúng ý đồ (fail-loud).
        """
        frappe.set_user(self.vendor)
        env = get_asset_incident_history(asset=self.asset, limit=10)
        items = (env.get("data") or {}).get("items") or []
        self.assertNotIn(
            self.incident, [i.get("name") for i in items],
            "VỠ VENDOR ISOLATION (AUTH-01): vendor đọc được sự cố của thiết bị "
            "KHÔNG do họ phụ trách (asset.responsible_technician != vendor).",
        )

    # ── G7 — không 500 câm cho persona thiếu quyền ──────────────────────────
    def test_incident_history_no_bare_permission_error(self):
        """BR-00-ROWSCOPE-403: 403 envelope trên HTTP-200, KHÔNG PermissionError trần."""
        frappe.set_user(self.pm_only)
        try:
            env = get_asset_incident_history(asset=self.asset, limit=10)
        except frappe.PermissionError:
            self.fail(
                "`get_asset_incident_history` ném `frappe.PermissionError` TRẦN "
                "(handle() KHÔNG bắt Exception chung) ⇒ HTTP-500 / dispatcher-403 "
                "— FE hiểu nhầm hết phiên và ĐĂNG XUẤT người dùng. Cần "
                "`@rowscoped` (services/shared/permissions.py:117)."
            )
        self.assertIsInstance(env, dict)
        self.assertIn("success", env)


# ═══════════════════════════════════════════════════════════════════════════════
# CR-73(a) §3.13-bis(6) — role-gate cho `search_spare_parts`
#   Endpoint đọc bằng `frappe.db.sql` THÔ ⇒ 0 permission tự động. Child table
#   `IMM Device Spare Part` KHÔNG có DocPerm riêng ⇒ gate ở parent `IMM Device Model`.
#   Test CẶP (bắt buộc, A6): thiếu quyền ⇒ 403 envelope; persona KTV THẬT ⇒ VẪN có
#   kết quả. Test âm một mình sẽ "xanh" cả khi ta khoá nhầm chính người dùng chính.
# ═══════════════════════════════════════════════════════════════════════════════
_NO_BASE = "docperm_gate_nobase@example.invalid"   # CHỈ `Repair User` ⇒ 0 read IMM Device Model
_SPARE_TOKEN = "GATEZQ73"


class TestSearchSparePartsRoleGate(FrappeTestCase):
    """A6 — `search_spare_parts` phải gate DocPerm read `IMM Device Model` (OWASP A01).

    Không gate ⇒ MỌI user đã đăng nhập (kể cả `Vendor Engineer` của hãng khác) đọc
    được toàn bộ danh mục phụ tùng + **giá ước tính** của mọi model thiết bị.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.no_base = _ensure_user(_NO_BASE, "Gate NoBase", "Repair User")
        # persona "Kỹ thuật viên" THẬT = base role + Repair User (setup/role_profile_catalog.py)
        cls.technician = _ensure_user(_REPAIR_ONLY, "Gate Repair",
                                      "Repair User", "AssetCore System User")

        cls.cat = frappe.db.get_value("AC Asset Category", {"category_name": _CAT_NAME}, "name")
        if not cls.cat:
            cls.cat = frappe.get_doc({
                "doctype": "AC Asset Category", "category_name": _CAT_NAME,
                "default_pm_interval_days": 90,
            }).insert(ignore_permissions=True).name
        cls.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"_Test Model GATE {_SPARE_TOKEN}",
            "manufacturer": "_TestMfr GATE",
            "asset_category": cls.cat,
            "medical_device_class": "Class II",
            "spare_parts_list": [{
                "part_name": f"_Test Part {_SPARE_TOKEN}",
                "manufacturer_part_no": f"MPN-{_SPARE_TOKEN}",
                "estimated_cost": 42000,
            }],
        }).insert(ignore_permissions=True).name
        cls.spare = frappe.get_doc({
            "doctype": "AC Spare Part", "part_name": f"_Test Part {_SPARE_TOKEN}",
            "manufacturer_part_no": f"MPN-{_SPARE_TOKEN}", "part_category": "Other",
            "stock_uom": "Cái", "is_active": 1,
        }).insert(ignore_permissions=True).name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for dt, name in (("IMM Device Model", cls.model), ("AC Spare Part", cls.spare)):
            try:
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                                  delete_permanently=True)
            except Exception:
                pass
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── TC-CM-SPARE-08a — thiếu quyền ⇒ 403 envelope, 0 dòng rò ─────────────
    def test_search_spare_parts_requires_read_on_device_model(self):
        """User 0 DocPerm read `IMM Device Model` ⇒ Error envelope FORBIDDEN/403.

        Decision-B: lỗi quyền đến TRÊN HTTP-200 (in-handler cap-403) ⇒ FE hiển thị
        message, KHÔNG hiểu nhầm "hết phiên" rồi ĐĂNG XUẤT người dùng. TUYỆT ĐỐI
        KHÔNG trả `[]` câm (dead-gate: RBAC misconfig chết âm thầm).
        """
        from assetcore.api.imm09 import search_spare_parts
        frappe.set_user(self.no_base)
        try:
            env = search_spare_parts(query=_SPARE_TOKEN, limit="10")
        except frappe.PermissionError:
            self.fail("PermissionError TRẦN ⇒ HTTP-500/dispatcher-403; cần `@rowscoped`.")
        self.assertFalse(env.get("success"),
                         "Thiếu quyền mà `success:true` = gate không tồn tại.")
        self.assertEqual(env.get("code"), "FORBIDDEN")
        self.assertEqual(env.get("http_status"), 403)
        self.assertFalse(env.get("data"),
                         "KHÔNG được rò dòng nào kèm lỗi (danh mục phụ tùng + giá).")

    # ── TC-CM-SPARE-08b — persona KTV THẬT KHÔNG bị khoá nhầm ──────────────
    def test_search_spare_parts_technician_persona_still_gets_results(self):
        """Persona KTV (`AssetCore System User` + `Repair User`) VẪN nhận kết quả.

        Chống "sửa quyền làm chết chính người dùng": KTV KHÔNG có DocPerm trên
        `AC Spare Part` ⇒ nếu resolve `spare_part` chạy permission-aware thì họ luôn
        nhận `""` (dead-gate) trong khi test chạy Administrator vẫn xanh giả
        (ADR-IMM09-SPARE-02).
        """
        from assetcore.api.imm09 import search_spare_parts
        frappe.set_user(self.technician)
        env = search_spare_parts(query=_SPARE_TOKEN, limit="10")
        self.assertTrue(env.get("success"), f"KTV bị khoá nhầm: {env}")
        rows = [r for r in (env.get("data") or []) if r.get("device_model") == self.model]
        self.assertTrue(rows, "Persona KTV PHẢI thấy gợi ý phụ tùng (đây là người dùng chính).")
        self.assertEqual(rows[0]["spare_part"], self.spare,
                         "`spare_part` PHẢI non-empty với persona THẬT (system-scope resolve).")
        self.assertEqual(rows[0]["device_model_name"], f"_Test Model GATE {_SPARE_TOKEN}")


# ═══════════════════════════════════════════════════════════════════════════════
# CR-74 — C6-DETAIL read-gate (ADR-IMM00-LIST-SCOPE §9 · D8/D9/D10)
#   4 GET-detail (`getPmWorkOrder` / `getRepairWorkOrder` / `getCalibration` /
#   `getIncident`) đọc bằng `<X>Repo.get` → `frappe.get_doc`, mà `frappe.get_doc`
#   KHÔNG gọi `check_permission` (frappe/model/document.py:36) ⇒ hook `has_permission`
#   đã đăng ký ở hooks.py:448-455 CHƯA BAO GIỜ chạy trên đường detail, và DocPerm
#   read cấp vai-trò cũng không được kiểm ⇒ persona 0-DocPerm đọc trọn hồ sơ bằng URL.
#
#   INV-DETAIL-1 (01a..01d) · INV-DETAIL-5 (05a) · INV-DETAIL-6 (05b) ·
#   INV-DETAIL-7 (06) · no-500 (07).
#
#   ⚠️ MỌI TC chạy dưới `frappe.set_user(<persona thật>)` — `frappe/permissions.py:107-109`
#   short-circuit `user == "Administrator"` ⇒ chạy bằng Administrator = XANH GIẢ.
# ═══════════════════════════════════════════════════════════════════════════════
_CR74_NOPERM = "cr74_noperm@example.invalid"    # CHỈ base role ⇒ 0 DocPerm read cả 4 DocType
_CR74_SENIOR = "cr74_senior@example.invalid"    # manager 4 domain ⇒ read-all (hook trả True)
_CR74_VENDOR = "cr74_vendor@example.invalid"    # Vendor Engineer ngoài scope (A5)
_CR74_USERS = (_CR74_NOPERM, _CR74_SENIOR, _CR74_VENDOR)
_CR74_CAT = "_CR74 DetailGate Category"

# Khoá nghiệp vụ TUYỆT ĐỐI không được xuất hiện trong body 403 (ADR §9.5).
_CR74_FORBIDDEN_LEAK_KEYS = (
    "asset_ref", "repair_summary", "mttr_hours", "root_cause_category",
    "clinical_impact", "failure_description", "checklist_results",
    "repair_checklist", "allowed_transitions", "technician_notes",
)
_BOGUS_NAME = "WO-CR74-DOES-NOT-EXIST-000"


def _all_keys(obj) -> set[str]:
    """Tập MỌI khoá dict (đệ quy) — dùng chứng minh body 403 KHÔNG chở field nghiệp vụ."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            out |= _all_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out |= _all_keys(v)
    return out


class TestDetailReadGateCR74(FrappeTestCase):
    """CR-74 — 4 GET-detail phải kết luận bằng CÙNG predicate quyền-đọc."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = frappe.db.get_value("AC Asset Category", {"category_name": _CR74_CAT}, "name")
        if not cls.cat:
            cls.cat = frappe.get_doc({
                "doctype": "AC Asset Category", "category_name": _CR74_CAT,
                "default_pm_interval_days": 90,
            }).insert(ignore_permissions=True).name

        cls.noperm = _ensure_user(_CR74_NOPERM, "CR74 NoPerm", "AssetCore System User")
        cls.senior = _ensure_user(_CR74_SENIOR, "CR74 Senior", "PM Manager", "Repair Manager",
                                  "Corrective Manager", "Calibration Manager")
        cls.vendor = _ensure_user(_CR74_VENDOR, "CR74 Vendor",
                                  "Vendor Engineer", "AssetCore System User")

        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_CR74 DetailGate Asset",
                "asset_category": cls.cat,
                "manufacturer_sn": f"CR74-SN-{int(time.time()) % 100000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True).name
        finally:
            frappe.flags.in_install = prev

        cls.repair = frappe.get_doc({
            "doctype": "Asset Repair", "asset_ref": cls.asset,
            "repair_type": "Corrective", "priority": "Normal",
            "failure_description": "_CR74 fixture failure",
            "status": RepairStatus.ASSIGNED, "assigned_to": cls.senior,
        }).insert(ignore_permissions=True).name

        cls.template = frappe.get_doc({
            "doctype": "PM Checklist Template", "template_name": "_CR74 Template",
            "asset_category": cls.cat, "pm_type": "Quarterly",
            "checklist_items": [{"description": "_CR74 check", "measurement_type": "Pass/Fail"}],
        }).insert(ignore_permissions=True).name
        cls.sched = frappe.get_doc({
            "doctype": "PM Schedule", "asset_ref": cls.asset, "pm_type": "Quarterly",
            "pm_interval_days": 90, "checklist_template": cls.template, "status": "Active",
        }).insert(ignore_permissions=True).name
        due = nowdate()
        cls.pm_wo = frappe.get_doc({
            "doctype": "PM Work Order", "asset_ref": cls.asset, "pm_schedule": cls.sched,
            "pm_type": "Quarterly", "wo_type": "Preventive", "status": "Open",
            "due_date": due, "scheduled_date": due, "assigned_to": cls.senior,
        }).insert(ignore_permissions=True).name

        cls.incident = frappe.get_doc({
            "doctype": "Incident Report", "asset": cls.asset,
            "incident_type": "Malfunction", "severity": "Low",
            "description": "_CR74 fixture incident",
            "reported_by": cls.senior, "status": "Open",
        }).insert(ignore_permissions=True).name

        cls.calibration = frappe.get_doc({
            "doctype": "IMM Asset Calibration", "asset": cls.asset,
            "calibration_type": "In-House", "status": "Scheduled",
            "reference_standard_serial": "_CR74-REF-STD-001",
            "scheduled_date": add_days(nowdate(), 7), "technician": cls.senior,
        }).insert(ignore_permissions=True).name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for dt, name in (
            ("IMM Asset Calibration", getattr(cls, "calibration", None)),
            ("Incident Report", getattr(cls, "incident", None)),
            ("PM Work Order", getattr(cls, "pm_wo", None)),
            ("PM Schedule", getattr(cls, "sched", None)),
            ("PM Checklist Template", getattr(cls, "template", None)),
            ("Asset Repair", getattr(cls, "repair", None)),
        ):
            if name and frappe.db.exists(dt, name):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        if getattr(cls, "asset", None):
            purge_asset(cls.asset)
        if frappe.db.exists("AC Asset Category", getattr(cls, "cat", "")):
            frappe.delete_doc("AC Asset Category", cls.cat, force=True, ignore_permissions=True)
        for email in _CR74_USERS:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _ops(self) -> dict:
        """{label: (api_callable, doctype, fixture_name)} — 4 op C6-DETAIL."""
        from assetcore.api.imm08 import get_pm_work_order
        from assetcore.api.imm09 import get_repair_work_order
        from assetcore.api.imm11 import get_calibration
        from assetcore.api.imm12 import get_incident

        return {
            "getPmWorkOrder": (get_pm_work_order, "PM Work Order", self.pm_wo),
            "getRepairWorkOrder": (get_repair_work_order, "Asset Repair", self.repair),
            "getCalibration": (get_calibration, "IMM Asset Calibration", self.calibration),
            "getIncident": (get_incident, "Incident Report", self.incident),
        }

    def _assert_forbidden_envelope(self, label: str, env) -> None:
        self.assertIsInstance(env, dict, f"{label}: PHẢI trả envelope dict")
        self.assertFalse(
            env.get("success"),
            f"{label}: persona 0 DocPerm read vẫn nhận success:true ⇒ RÒ HỒ SƠ "
            f"(OWASP A01). `frappe.get_doc` KHÔNG check quyền — cần khuôn 3 lớp "
            f"ROLE→EXISTS→ROW (ADR-IMM00-LIST-SCOPE §9.4). env={env}",
        )
        self.assertEqual(
            env.get("code"), "FORBIDDEN",
            f"{label}: thiếu quyền đọc = FORBIDDEN, KHÔNG NOT_FOUND/INTERNAL "
            f"(404 thay 403 che lỗi cấu hình quyền thành 'mất dữ liệu'). env={env}",
        )
        self.assertEqual(
            env.get("http_status"), 403,
            f"{label}: BR-00-DETAIL-403 — 403 nằm TRONG body trên HTTP-200. env={env}",
        )
        self.assertTrue(
            (env.get("error") or "").strip(),
            f"{label}: message KHÔNG được rỗng (vacuous envelope → FE hiện 'Lỗi không xác định')",
        )
        self.assertFalse(
            env.get("data"),
            f"{label}: body 403 KHÔNG được chở `data` (silent-partial còn tệ hơn silent-empty)",
        )
        leaked = sorted(set(_CR74_FORBIDDEN_LEAK_KEYS) & _all_keys(env))
        self.assertEqual(
            leaked, [],
            f"{label}: body 403 chở khoá NGHIỆP VỤ {leaked} — ADR §9.5 cấm tuyệt đối "
            f"(chỉ được có khoá của Error envelope).",
        )

    # ── TC-CR74-01a..01d / INV-DETAIL-1 ──────────────────────────────────────
    def test_cr74_01a_pm_detail_denied_without_docperm(self):
        frappe.set_user(self.noperm)
        self.assertFalse(frappe.has_permission("PM Work Order", "read"),
                         "tiền đề: base role KHÔNG có DocPerm read PM Work Order")
        self._assert_forbidden_envelope(
            "getPmWorkOrder", self._ops()["getPmWorkOrder"][0](name=self.pm_wo))

    def test_cr74_01b_repair_detail_denied_without_docperm(self):
        frappe.set_user(self.noperm)
        self.assertFalse(frappe.has_permission("Asset Repair", "read"),
                         "tiền đề: base role KHÔNG có DocPerm read Asset Repair")
        self._assert_forbidden_envelope(
            "getRepairWorkOrder", self._ops()["getRepairWorkOrder"][0](name=self.repair))

    def test_cr74_01c_calibration_detail_denied_without_docperm(self):
        """D10 — `IMM Asset Calibration` chưa có hook row-scope ⇒ CHỈ siết trục ROLE,
        nhưng vẫn PHẢI siết: không gate = mọi user đọc trọn hồ sơ hiệu chuẩn."""
        frappe.set_user(self.noperm)
        self.assertFalse(frappe.has_permission("IMM Asset Calibration", "read"),
                         "tiền đề: base role KHÔNG có DocPerm read IMM Asset Calibration")
        self._assert_forbidden_envelope(
            "getCalibration", self._ops()["getCalibration"][0](name=self.calibration))

    def test_cr74_01d_incident_detail_denied_without_docperm(self):
        frappe.set_user(self.noperm)
        self.assertFalse(frappe.has_permission("Incident Report", "read"),
                         "tiền đề: base role KHÔNG có DocPerm read Incident Report")
        self._assert_forbidden_envelope(
            "getIncident", self._ops()["getIncident"][0](name=self.incident))

    # ── TC-CR74-05a / INV-DETAIL-5 — KHÔNG existence-oracle ──────────────────
    def test_cr74_05a_no_existence_oracle(self):
        """Thiếu DocPerm read ⇒ `name` có thật và `name` bịa trả **ĐÚNG CÙNG mã**.

        Nếu gate ROLE chạy SAU `exists`, user không quyền vẫn phân biệt được phiếu
        nào tồn tại (403 vs 404) ⇒ liệt kê được naming-series (D9).
        """
        frappe.set_user(self.noperm)
        for label, (fn, _dt, real) in self._ops().items():
            env_real = fn(name=real)
            env_fake = fn(name=_BOGUS_NAME)
            self.assertEqual(
                (env_fake.get("success"), env_fake.get("code"), env_fake.get("http_status")),
                (env_real.get("success"), env_real.get("code"), env_real.get("http_status")),
                f"{label}: EXISTENCE-ORACLE — `name` bịa trả {env_fake.get('code')}/"
                f"{env_fake.get('http_status')} khác `name` thật ({env_real.get('code')}/"
                f"{env_real.get('http_status')}). Gate ROLE PHẢI chạy TRƯỚC `exists` "
                f"(ADR §9.2 D9, tiền lệ api/imm00.py::get_asset).",
            )
            self.assertEqual(env_fake.get("http_status"), 403,
                             f"{label}: cả hai nhánh PHẢI là 403 (không phải 404)")

    # ── TC-CR74-05b / INV-DETAIL-6 — 404 GIỮ NGUYÊN cho người CÓ quyền ───────
    def test_cr74_05b_404_preserved_for_permitted_user(self):
        frappe.set_user(self.senior)
        for label, (fn, dt, _real) in self._ops().items():
            self.assertTrue(frappe.has_permission(dt, "read"),
                            f"tiền đề: senior PHẢI có DocPerm read {dt}")
            env = fn(name=_BOGUS_NAME)
            self.assertFalse(env.get("success"), f"{label}: name bịa ⇒ Error envelope")
            self.assertEqual(
                env.get("http_status"), 404,
                f"{label}: người CÓ quyền + `name` không tồn tại PHẢI GIỮ 404 "
                f"(CR-74 không được siết oan). env={env}",
            )
            self.assertEqual(env.get("code"), "NOT_FOUND", f"{label}: mã 404 GIỮ NGUYÊN")

    # ── TC-CR74-06 / INV-DETAIL-7 — vendor-isolation KHÔNG bị gate mới nuốt ──
    def test_cr74_06_vendor_layer_still_present(self):
        """A5: `assert_vendor_can_access` (API tier) GIỮ NGUYÊN — 2 lớp cùng tồn tại.

        Chứng minh bằng 2 vế: (1) lớp cũ vẫn raise ServiceError(FORBIDDEN) khi gọi
        trực tiếp dưới persona vendor ngoài scope; (2) endpoint trả 403 envelope
        (KHÔNG 500, KHÔNG PermissionError trần) — bất kể lớp nào bắn trước.
        """
        from assetcore.services.shared.errors import ServiceError
        from assetcore.services.shared.scope import assert_vendor_can_access

        frappe.set_user(self.vendor)
        with self.assertRaises(ServiceError) as cm:
            assert_vendor_can_access("Asset Repair", self.repair)
        self.assertEqual(
            cm.exception.code, "FORBIDDEN",
            "LỚP CŨ BIẾN MẤT: gate mới KHÔNG được gỡ/thay vendor-IDOR guard (A5).",
        )

        fn = self._ops()["getRepairWorkOrder"][0]
        try:
            env = fn(name=self.repair)
        except frappe.PermissionError:
            self.fail("vendor ngoài scope nhận PermissionError TRẦN ⇒ 500 câm, không phải envelope")
        self.assertFalse(env.get("success"), f"vendor ngoài scope PHẢI bị chặn: {env}")
        self.assertEqual(
            env.get("code"), "FORBIDDEN",
            f"vendor ⇒ bucket FORBIDDEN (client route theo `code`), KHÔNG 500: {env}",
        )
        # ⚠️ KNOWN DEFECT (pre-existing, NGOÀI scope CR-74 — A5 cấm sửa lớp vendor):
        # `assert_vendor_can_access` (services/shared/scope.py:214-217) raise
        # `ServiceError(FORBIDDEN, ...)` KHÔNG truyền `http_status` ⇒ nhận default 400,
        # trong khi OAS khai vendor-IDOR-**403** in-envelope. Test chấp nhận CẢ HAI để
        # KHÔNG ossify bug, nhưng ghim `code` (thứ client thật sự route theo) và cấm
        # tuyệt đối 500. Sửa = 1 dòng `http_status=403` ở scope.py — cần [BA] ratify vì
        # đổi giá trị observable của hợp đồng (Hyrum's Law).
        self.assertIn(
            env.get("http_status"), (400, 403),
            f"vendor ⇒ envelope 4xx (KHÔNG 500 / KHÔNG status-line): {env}",
        )

    # ── TC-CR74-07 — KHÔNG bao giờ 500 / PermissionError trần ───────────────
    def test_cr74_07_no_bare_permission_error(self):
        """Parity `test_incident_history_no_bare_permission_error:302` — `handle()` cố ý
        KHÔNG bắt Exception chung ⇒ thiếu `@rowscoped` = HTTP-500/dispatcher-403 và FE
        hiểu nhầm "hết phiên" rồi ĐĂNG XUẤT người dùng giữa ca trực."""
        frappe.set_user(self.noperm)
        for label, (fn, _dt, real) in self._ops().items():
            try:
                env = fn(name=real)
            except frappe.PermissionError:
                self.fail(
                    f"{label}: `frappe.PermissionError` TRẦN thoát khỏi handle() — "
                    f"cần `@rowscoped` (services/shared/permissions.py::rowscoped)."
                )
            except Exception as exc:                    # noqa: BLE001 — fail-loud
                self.fail(f"{label}: exception TRẦN {type(exc).__name__}: {exc}")
            self.assertIsInstance(env, dict, f"{label}: envelope dict")
            self.assertIn("success", env, f"{label}: envelope PHẢI có khoá `success`")


# ═══════════════════════════════════════════════════════════════════════════════
# CR-76 — `get_gate_status` gác quyền như một GET-detail (BR-04-16 · ADR-IMM-04-07)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Thẻ «Điều kiện bàn giao» bộc lộ tình trạng hồ sơ pháp lý, kết quả đo kiểm an toàn,
# tồn tại NC và việc đã/chưa có người ký của MỘT phiếu ⇒ đủ để suy ra tình trạng tuân
# thủ của thiết bị. Trước CR-76 endpoint có **0 gate** và trả `_err(msg, 404)` cho
# `name` lạ TRƯỚC mọi kiểm tra quyền ⇒ vừa IDOR-đọc vừa **existence-oracle** cho
# naming-series. Khuôn đích = ROLE → EXISTS → ROW (mirror CR-74 §9.4).
#
#   ⚠️ MỌI TC chạy dưới `frappe.set_user(<persona thật>)` — `frappe/permissions.py:107-109`
#   short-circuit `user == "Administrator"` ⇒ chạy bằng Administrator = XANH GIẢ.
_CR76_NOPERM = "cr76_noperm@example.invalid"      # base role ⇒ 0 DocPerm read Asset Commissioning
_CR76_MANAGER = "cr76_manager@example.invalid"    # Commissioning Manager ⇒ read-all
_CR76_USERS = (_CR76_NOPERM, _CR76_MANAGER)
_CR76_COMM = "_TEST-COMM-CR76-READGATE"
_CR76_BOGUS = "COMM-CR76-DOES-NOT-EXIST-000"
_CR76_DT = "Asset Commissioning"
# 8 khoá (AC-CR-85: `g04_applicable` additive — cổng G04 tự mô tả «không áp dụng»).
_CR76_GATE_KEYS = ("g01_docs", "g01_waived", "g02_facility", "g03_baseline",
                   "g04_radiation", "g04_applicable", "g05_nc", "g06_approver")


class TestGateStatusReadGateCR76(FrappeTestCase):
    """TC-04-GATE-15..18 (`07 §III.4e`) — read-gate của thẻ cổng == read-gate của phiếu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.noperm = _ensure_user(_CR76_NOPERM, "CR76 NoPerm", "AssetCore System User")
        cls.manager = _ensure_user(_CR76_MANAGER, "CR76 Manager",
                                   "AssetCore System User", "Commissioning Manager")
        # Phiếu dựng bằng RAW SQL: `insert()` kéo theo mandatory link (po_reference/
        # master_item/vendor) hoàn toàn không liên quan tới lớp QUYỀN đang đo.
        frappe.db.delete(_CR76_DT, {"name": _CR76_COMM})
        frappe.db.sql(
            """
            INSERT INTO `tabAsset Commissioning`
                (name, creation, modified, owner, modified_by, docstatus, idx, workflow_state)
            VALUES (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, 0,
                    'To Be Installed')
            """,
            {"name": _CR76_COMM},
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.db.delete(_CR76_DT, {"name": _CR76_COMM})
        for email in _CR76_USERS:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    @staticmethod
    def _call(name: str):
        from assetcore.api.imm04 import get_gate_status

        return get_gate_status(name=name)

    def _assert_no_gate_leak(self, label: str, env: dict) -> None:
        leaked = sorted(k for k in _all_keys(env) if k.startswith("g0"))
        self.assertEqual(
            leaked, [],
            f"{label}: body lỗi chở khoá cổng {leaked} — người KHÔNG được đọc phiếu vẫn "
            f"suy ra được tình trạng tuân thủ của thiết bị (ADR-IMM-04-07).",
        )

    # ── TC-04-GATE-15 — persona 0 DocPerm read, `name` CÓ THẬT ───────────────
    def test_cr76_15_gate_status_denied_without_docperm(self):
        frappe.set_user(self.noperm)
        self.assertFalse(
            frappe.has_permission(_CR76_DT, "read"),
            "tiền đề: base role KHÔNG có DocPerm read Asset Commissioning",
        )
        env = self._call(_CR76_COMM)
        self.assertFalse(env.get("success"),
                         f"persona 0 DocPerm vẫn đọc được thẻ cổng ⇒ IDOR-đọc. env={env}")
        self.assertEqual(env.get("code"), "FORBIDDEN",
                         f"thiếu quyền đọc = FORBIDDEN, KHÔNG NOT_FOUND/INTERNAL. env={env}")
        self.assertEqual(env.get("http_status"), 403,
                         f"403 nằm TRONG body trên HTTP-200 (in-handler cap-403). env={env}")
        self.assertTrue((env.get("error") or "").strip(),
                        "message KHÔNG được rỗng (vacuous envelope → 'Lỗi không xác định')")
        self._assert_no_gate_leak("TC-15", env)

    # ── TC-04-GATE-16 — 0 existence-oracle (L0 ROLE chạy TRƯỚC EXISTS) ───────
    def test_cr76_16_no_existence_oracle(self):
        frappe.set_user(self.noperm)
        real = self._call(_CR76_COMM)
        bogus = self._call(_CR76_BOGUS)
        self.assertEqual(
            (real.get("code"), real.get("http_status")),
            (bogus.get("code"), bogus.get("http_status")),
            "Envelope cho `name` CÓ THẬT và `name` BỊA phải TRÙNG (code+http_status): "
            "khác nhau = endpoint trở thành existence-oracle cho naming-series "
            f"(ROLE phải chạy TRƯỚC EXISTS). real={real} bogus={bogus}",
        )
        self.assertEqual(bogus.get("code"), "FORBIDDEN")
        self._assert_no_gate_leak("TC-16", bogus)

    # ── TC-04-GATE-17 — 404 GIỮ NGUYÊN cho người CÓ quyền ───────────────────
    def test_cr76_17_not_found_preserved_for_permitted_user(self):
        frappe.set_user(self.manager)
        self.assertTrue(frappe.has_permission(_CR76_DT, "read"),
                        "tiền đề: Commissioning Manager CÓ DocPerm read")
        env = self._call(_CR76_BOGUS)
        self.assertFalse(env.get("success"), env)
        self.assertEqual(
            env.get("code"), "NOT_FOUND",
            f"Người CÓ quyền tra `name` không tồn tại PHẢI nhận NOT_FOUND (nếu trả 403 "
            f"thì lỗi cấu hình quyền bị che thành 'mất dữ liệu'). env={env}",
        )
        self.assertEqual(env.get("message_code"), "IMM04-NOT-FOUND",
                         f"envelope nay đi qua handle() ⇒ có message_code. env={env}")
        self._assert_no_gate_leak("TC-17", env)

    # ── TC-04-GATE-18 — persona đủ quyền: 8 khoá, 0 regress khoá cũ ─────────
    def test_cr76_18_permitted_persona_gets_eight_boolean_keys(self):
        frappe.set_user(self.manager)
        env = self._call(_CR76_COMM)
        self.assertTrue(env.get("success"), f"persona đủ quyền phải nhận 200. env={env}")
        data = env.get("data") or {}
        self.assertEqual(
            sorted(data), sorted(_CR76_GATE_KEYS),
            f"Hợp đồng 8 khoá (6 gốc + `g01_waived` CR-76 + `g04_applicable` AC-CR-85, "
            f"đều additive). Thực tế: {sorted(data)}",
        )
        for key, value in data.items():
            self.assertIsInstance(value, bool, f"`{key}` PHẢI bool THẬT: {value!r}")
        # 0 regress khoá: key-set persona == key-set Administrator (baseline trước-gate,
        # `frappe/permissions.py:107-109` short-circuit) ⇒ gate KHÔNG lặng lẽ cắt field.
        frappe.set_user("Administrator")
        admin_env = self._call(_CR76_COMM)
        self.assertEqual(
            sorted(data), sorted(admin_env.get("data") or {}),
            "Persona đủ quyền phải nhận ĐÚNG tập khoá của Administrator — lệch = gate "
            "đang cắt bớt field theo persona (không phải hợp đồng CR-76).",
        )

    # ── không bao giờ PermissionError trần (500 câm / FE tưởng hết phiên) ───
    def test_cr76_19_no_bare_permission_error(self):
        frappe.set_user(self.noperm)
        try:
            env = self._call(_CR76_COMM)
        except frappe.PermissionError:
            self.fail("`frappe.PermissionError` TRẦN thoát khỏi handle() — thiếu @rowscoped")
        except Exception as exc:                        # noqa: BLE001 — fail-loud
            self.fail(f"exception TRẦN {type(exc).__name__}: {exc}")
        self.assertIsInstance(env, dict)
        self.assertIn("success", env)
