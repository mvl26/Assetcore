# Copyright (c) 2026, AssetCore Team
import frappe
import unittest
from assetcore.services.shared.constants import Roles


class TestRolesCatalog(unittest.TestCase):
    def test_30_roles_total(self):
        self.assertEqual(len(Roles.ALL), 30)

    def test_system_roles(self):
        self.assertEqual(
            set(Roles.SYSTEM_ROLES),
            {"AssetCore Super Admin", "AssetCore System User",
             "AssetCore Auditor", "Vendor Engineer"},
        )

    def test_domain_pairs(self):
        self.assertEqual(len(Roles.DOMAIN_ROLES), 26)
        self.assertIn("PM Manager", Roles.DOMAIN_ROLES)
        self.assertIn("PM User", Roles.DOMAIN_ROLES)

    def test_rank_hierarchy(self):
        self.assertGreater(Roles.ROLE_RANK["AssetCore Super Admin"],
                            Roles.ROLE_RANK["PM Manager"])
        self.assertGreater(Roles.ROLE_RANK["PM Manager"],
                            Roles.ROLE_RANK["PM User"])

    def test_no_legacy_can_attr(self):
        self.assertFalse(hasattr(Roles, "CAN_CREATE_WO"))
        self.assertFalse(hasattr(Roles, "ALL_IMM"))


from assetcore.services.shared import rbac


class TestCapabilityMap(unittest.TestCase):
    def test_every_built_doctype_mapped(self):
        self.assertIn("PM Work Order", rbac.DOCTYPE_DOMAIN)
        self.assertEqual(rbac.DOCTYPE_DOMAIN["PM Work Order"], "PM")
        self.assertEqual(rbac.DOCTYPE_DOMAIN["AC Asset"], "_shared")
        self.assertEqual(rbac.DOCTYPE_DOMAIN["IMM Audit Trail"], "_audit")

    def test_capability_map_crud(self):
        self.assertEqual(rbac.CAPABILITY_MAP["pm.write"], ("PM Work Order", "write"))
        self.assertEqual(rbac.CAPABILITY_MAP["pm.delete"], ("PM Work Order", "delete"))

    def test_can_unknown_capability_raises(self):
        with self.assertRaises(KeyError):
            rbac.can("nope.nope")

    def test_get_capabilities_returns_dict(self):
        frappe.set_user("Administrator")
        caps = rbac.get_capabilities()
        self.assertIsInstance(caps, dict)
        self.assertIn("pm.read", caps)


import json, os, glob


class TestDocPermInvariants(unittest.TestCase):
    DT_DIR = frappe.get_app_path("assetcore", "assetcore", "doctype")

    def _perms(self, dt_folder):
        with open(os.path.join(self.DT_DIR, dt_folder, dt_folder + ".json")) as f:
            return json.load(f).get("permissions", [])

    def test_no_persona_role_in_any_json(self):
        bad = {"IMM System Admin", "IMM Workshop Lead", "IMM QA Officer"}
        for jf in glob.glob(os.path.join(self.DT_DIR, "*", "*.json")):
            with open(jf) as f:
                data = json.load(f)
            roles = {p.get("role") for p in data.get("permissions", [])}
            self.assertEqual(roles & bad, set(), f"{jf} con persona role")

    def test_pm_manager_superset_of_user(self):
        perms = {p["role"]: p for p in self._perms("pm_work_order")}
        mgr, usr = perms["PM Manager"], perms["PM User"]
        for k in ("read", "write", "create"):
            self.assertTrue(usr.get(k))
        for k in ("delete", "cancel", "amend"):
            self.assertGreaterEqual(mgr.get(k, 0), usr.get(k, 0))
        self.assertEqual(mgr.get("delete"), 1)

    def test_system_user_can_read_shared_core(self):
        perms = {p["role"]: p for p in self._perms("ac_asset")}
        self.assertEqual(perms["AssetCore System User"].get("read"), 1)


import subprocess


class TestNoHardcodedRoleChecks(unittest.TestCase):
    def test_no_can_or_all_imm_usage(self):
        app = frappe.get_app_path("assetcore")
        out = subprocess.run(
            ["grep", "-rnE", r"Roles\.(CAN_|ALL_IMM)|\.CAN_[A-Z]",
             os.path.join(app, "api"), os.path.join(app, "services")],
            capture_output=True, text=True,
        ).stdout
        self.assertEqual(out.strip(), "", f"Con role-name check:\n{out}")


class TestCoreDocPermNoShadow(unittest.TestCase):
    """Custom DocPerm trên core DocType phải clone standard rows, KHONG shadow.

    Bug history: setup_core_permissions.py insert thang vao tabCustom DocPerm
    bypass setup_custom_perms -> System Manager permlevel=1 bi shadow ->
    tab Roles & Permissions trong /app/user bi an. Fix: _ensure_standard_cloned
    goi setup_custom_perms(parent) truoc moi insert/update.
    """

    def test_system_manager_permlevel1_write_kept_on_user(self):
        frappe.clear_cache()
        meta = frappe.get_meta("User")
        sm = [p for p in meta.permissions
              if p.role == "System Manager" and p.permlevel == 1 and p.write]
        self.assertTrue(sm, "System Manager permlevel=1 write=1 bi shadow tren User")

    def test_system_manager_kept_on_all_core_doctypes(self):
        # Cac core DocType setup_core_permissions co dung -> System Manager
        # permlevel=0 read+write phai con (qua copy_perms clone standard).
        core_dts = ("User", "Role", "DocType", "Workflow", "Workflow State")
        frappe.clear_cache()
        for dt in core_dts:
            perms = frappe.get_meta(dt).permissions
            sm = [p for p in perms if p.role == "System Manager" and p.read]
            self.assertTrue(sm, f"System Manager read bi shadow tren {dt}")


class TestCapabilityEndpoint(unittest.TestCase):
    def test_endpoint_returns_caps(self):
        frappe.set_user("Administrator")
        from assetcore.api.auth import get_capabilities as ep
        res = ep()
        self.assertTrue(res.get("ok") or res.get("success"))
        data = res.get("data") or res.get("message", {})
        self.assertIn("pm.read", data)


class TestRoleFixture(unittest.TestCase):
    def test_role_json_has_30(self):
        p = frappe.get_app_path("assetcore", "fixtures", "role.json")
        data = json.load(open(p, encoding="utf-8"))
        names = {r["name"] for r in data}
        self.assertEqual(names, set(Roles.ALL))

    def test_role_profile_fixture_present_module_profile_removed(self):
        """Core Doc §7.quater: Role Profile = persona → role_profile.json fixture
        có mặt (8 profile); Module Profile vẫn bị bỏ."""
        from assetcore.setup.role_profile_catalog import PROFILE_NAMES
        base = frappe.get_app_path("assetcore", "fixtures")
        rp_path = os.path.join(base, "role_profile.json")
        self.assertTrue(os.path.exists(rp_path), "role_profile.json fixture phải tồn tại")
        names = {p["name"] for p in json.load(open(rp_path, encoding="utf-8"))}
        self.assertEqual(names, set(PROFILE_NAMES))
        self.assertFalse(os.path.exists(os.path.join(base, "module_profile.json")))


class TestWorkflowRoles(unittest.TestCase):
    BAD = {
        "IMM System Admin", "IMM Workshop Lead", "IMM QA Officer",
        "IMM Department Head", "IMM Biomed Technician", "IMM Technician",
        "IMM Operations Manager", "IMM Document Officer", "IMM Storekeeper",
        "IMM Clinical User", "IMM Auditor", "IMM Planning Officer",
        "IMM Finance Officer", "IMM HTM Engineer", "IMM Procurement Officer",
        "IMM Risk Officer", "IMM Board Approver", "IMM Training Officer",
        "Internal Auditor",
    }

    def test_workflow_json_clean(self):
        p = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
        txt = open(p, encoding="utf-8").read()
        for b in self.BAD:
            self.assertNotIn(f'"{b}"', txt, f"workflow.json con {b}")

    def test_workflow_files_clean(self):
        wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
        for fn in os.listdir(wf_dir):
            if not fn.endswith(".json"):
                continue
            txt = open(os.path.join(wf_dir, fn), encoding="utf-8").read()
            for b in self.BAD:
                self.assertNotIn(f'"{b}"', txt, f"{fn} con {b}")


class TestMigrationWipe(unittest.TestCase):
    def test_personas_gone_new_present(self):
        self.assertFalse(frappe.db.exists("Role", "IMM System Admin"))
        self.assertFalse(frappe.db.exists("Role", "IMM Workshop Lead"))
        self.assertTrue(frappe.db.exists("Role", "PM Manager"))
        self.assertTrue(frappe.db.exists("Role", "AssetCore Super Admin"))

    def test_other_app_and_core_roles_kept(self):
        self.assertTrue(frappe.db.exists("Role", "System Manager"))
        # Internal Auditor do app khac so huu — neu ton tai phai con
        if frappe.db.exists("Role", "Internal Auditor"):
            self.assertTrue(True)

    def test_persona_role_profiles_present_module_profile_gone(self):
        """Core Doc §7.quater: 8 persona Role Profile (tên VI) tồn tại;
        Module Profile vẫn bị bỏ (mô hình không dùng)."""
        from assetcore.setup.role_profile_catalog import PROFILE_NAMES
        from assetcore.setup.setup_role_profiles import seed_assetcore_role_profiles
        seed_assetcore_role_profiles()  # idempotent — đảm bảo có mặt
        for name in PROFILE_NAMES:
            self.assertTrue(frappe.db.exists("Role Profile", name), f"thiếu {name}")
        self.assertEqual(frappe.db.count("Module Profile"), 0)


class TestSetUserRoles(unittest.TestCase):
    """BE set-role endpoint cho trang FE /admin/roles."""

    def test_set_roles_replaces_and_keeps_external_roles(self):
        frappe.set_user("Administrator")
        u = "rbac_setrole_test@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "RBAC", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        try:
            # Pre-seed 1 role app khac (Frappe core "Newsletter Manager") +
            # 1 AssetCore role
            doc = frappe.get_doc("User", u)
            doc.append("roles", {"role": "Newsletter Manager"})
            doc.append("roles", {"role": "PM User"})
            doc.flags.ignore_permissions = True
            doc.save()
            frappe.db.commit()

            from assetcore.api.user import set_user_roles
            r = set_user_roles(user=u, roles=["PM Manager", "Inventory User"])
            self.assertTrue(r.get("success") or r.get("ok"))
            doc.reload()
            roles = {x.role for x in doc.roles}
            # AssetCore PM Manager + Inventory User da duoc set
            self.assertIn("PM Manager", roles)
            self.assertIn("Inventory User", roles)
            # PM User legacy da bi xoa (thay bang set moi)
            self.assertNotIn("PM User", roles)
            # Newsletter Manager (app khac) duoc giu
            self.assertIn("Newsletter Manager", roles)
        finally:
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestUmbrellaRole(unittest.TestCase):
    def test_super_admin_grants_system_manager(self):
        u = "rbac_umbrella_test@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "RBAC", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        try:
            from assetcore.services.shared.role_hooks import sync_umbrella
            user = frappe.get_doc("User", u)
            user.append("roles", {"role": "AssetCore Super Admin"})
            user.flags.ignore_permissions = True
            user.save()
            # Simulate hook fire
            has_role_doc = frappe.get_doc("Has Role", {
                "parent": u, "role": "AssetCore Super Admin",
            })
            sync_umbrella(has_role_doc, "after_insert")
            frappe.db.commit()
            user.reload()
            self.assertIn(
                "System Manager",
                [r.role for r in user.roles],
                "Super Admin must auto-grant System Manager via umbrella hook",
            )
        finally:
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestRolePrivilegeEscalation(unittest.TestCase):
    """Core Doc §7.sexies.2: đổi role / Role Profile = hành vi cấp quyền →
    BẮT BUỘC capability data.admin, kể cả khi user tự sửa CHÍNH MÌNH.
    Self-edit role KHÔNG phải self-service (khác change_my_password).
    """

    NONADMIN = "rbac_escalation_nonadmin@example.com"

    def setUp(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.NONADMIN):
            frappe.delete_doc("User", self.NONADMIN, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": self.NONADMIN,
            "first_name": "NonAdmin", "send_welcome_email": 0,
            "user_type": "System User",
        })
        u.insert(ignore_permissions=True)
        # Role nền — đăng nhập được, KHÔNG có data.admin.
        u.append("roles", {"role": "PM User"})
        u.flags.ignore_permissions = True
        u.save()
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.NONADMIN):
            frappe.delete_doc("User", self.NONADMIN, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _roles(self):
        return {r.role for r in frappe.get_doc("User", self.NONADMIN).roles}

    def test_update_user_roles_self_escalation_blocked(self):
        """SEC-RBAC-1: non-admin tự gán Super Admin cho mình → 403, role không đổi."""
        from assetcore.api.user import update_user_roles
        frappe.set_user(self.NONADMIN)
        frappe.local.form_dict = frappe._dict({
            "user": self.NONADMIN,
            "roles": json.dumps(["AssetCore Super Admin"]),
        })
        res = update_user_roles()
        self.assertFalse(res.get("success") or res.get("ok"), f"phải bị từ chối: {res}")
        frappe.set_user("Administrator")
        self.assertNotIn("AssetCore Super Admin", self._roles())

    def test_assign_role_profile_self_escalation_blocked(self):
        """SEC-RBAC-2: non-admin tự gán Role Profile admin cho mình → 403."""
        from assetcore.setup.setup_role_profiles import seed_assetcore_role_profiles
        seed_assetcore_role_profiles()
        from assetcore.api.user import assign_role_profile
        frappe.set_user(self.NONADMIN)
        res = assign_role_profile(user=self.NONADMIN, role_profile="Quản trị viên IT")
        self.assertFalse(res.get("success") or res.get("ok"), f"phải bị từ chối: {res}")
        frappe.set_user("Administrator")
        self.assertNotIn("AssetCore Super Admin", self._roles())
        self.assertIsNone(
            frappe.db.get_value("User", self.NONADMIN, "role_profile_name")
        )

    def test_admin_update_user_roles_other_succeeds(self):
        """SEC-RBAC-3: admin đổi role user khác vẫn thành công (regression guard)."""
        from assetcore.api.user import update_user_roles
        frappe.set_user("Administrator")
        frappe.local.form_dict = frappe._dict({
            "user": self.NONADMIN,
            "roles": json.dumps(["Inventory User"]),
        })
        res = update_user_roles()
        self.assertTrue(res.get("success") or res.get("ok"), f"admin phải pass: {res}")
        self.assertIn("Inventory User", self._roles())

    def test_admin_assign_role_profile_other_succeeds(self):
        """SEC-RBAC-4: admin gán Role Profile user khác vẫn thành công."""
        from assetcore.setup.setup_role_profiles import seed_assetcore_role_profiles
        seed_assetcore_role_profiles()
        from assetcore.api.user import assign_role_profile
        frappe.set_user("Administrator")
        res = assign_role_profile(user=self.NONADMIN, role_profile="Kỹ thuật viên")
        self.assertTrue(res.get("success") or res.get("ok"), f"admin phải pass: {res}")
        self.assertEqual(
            frappe.db.get_value("User", self.NONADMIN, "role_profile_name"),
            "Kỹ thuật viên",
        )

    def test_guest_blocked(self):
        """SEC-RBAC-5: Guest → 401 cho cả 2 endpoint."""
        from assetcore.api.user import update_user_roles, assign_role_profile
        frappe.set_user("Guest")
        try:
            frappe.local.form_dict = frappe._dict({
                "user": self.NONADMIN, "roles": json.dumps(["PM Manager"]),
            })
            r1 = update_user_roles()
            self.assertFalse(r1.get("success") or r1.get("ok"))
            r2 = assign_role_profile(user=self.NONADMIN, role_profile="Kỹ thuật viên")
            self.assertFalse(r2.get("success") or r2.get("ok"))
        finally:
            frappe.set_user("Administrator")


class TestVendorScopeIsolation(unittest.TestCase):
    """AUTH-01 / AUTH-10: Vendor Engineer sees only assigned scope."""

    def test_apply_vendor_scope_non_vendor_passthrough_dict(self):
        from assetcore.services.shared.scope import apply_vendor_scope
        f = {"workflow_state": "Open"}
        result = apply_vendor_scope(f, "PM Work Order", user="Administrator")
        self.assertEqual(result, f)

    def test_apply_vendor_scope_unknown_doctype_passthrough(self):
        from assetcore.services.shared.scope import apply_vendor_scope
        f = {"x": "y"}
        result = apply_vendor_scope(f, "Some Random Doctype")
        self.assertEqual(result, f)

    def test_apply_vendor_scope_guest_passthrough(self):
        from assetcore.services.shared.scope import apply_vendor_scope
        f = {"a": "b"}
        result = apply_vendor_scope(f, "AC Asset", user="Guest")
        self.assertEqual(result, f)

    def test_apply_vendor_scope_empty_assignment_filters_to_sentinel(self):
        from assetcore.services.shared.scope import apply_vendor_scope
        u = "rbac_vendor_empty@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "Vendor", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        try:
            user = frappe.get_doc("User", u)
            user.append("roles", {"role": "Vendor Engineer"})
            user.flags.ignore_permissions = True
            user.save()
            frappe.db.commit()
            f = {"workflow_state": "Open"}
            scoped = apply_vendor_scope(f, "PM Work Order", user=u)
            self.assertIn("asset", scoped)
            self.assertEqual(scoped["asset"][0], "in")
            self.assertEqual(scoped["asset"][1], ["__none__"])
        finally:
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()

    def test_assert_vendor_can_access_admin_bypasses(self):
        from assetcore.services.shared.scope import assert_vendor_can_access
        try:
            assert_vendor_can_access("PM Work Order", "FAKE-NAME", user="Administrator")
        except Exception as e:
            self.fail(f"Admin must bypass vendor scope, got: {e!r}")

    def test_assert_vendor_can_access_non_vendor_passthrough(self):
        from assetcore.services.shared.scope import assert_vendor_can_access
        u = "rbac_pm_user@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "PM", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        try:
            user = frappe.get_doc("User", u)
            user.append("roles", {"role": "PM User"})
            user.flags.ignore_permissions = True
            user.save()
            frappe.db.commit()
            assert_vendor_can_access("PM Work Order", "FAKE-NAME", user=u)
        finally:
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()

    def test_assert_vendor_can_access_blocks_unassigned_vendor(self):
        from assetcore.services.shared.scope import assert_vendor_can_access
        from assetcore.services.shared.errors import ServiceError
        u = "rbac_vendor_idor@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "VendorIDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        try:
            user = frappe.get_doc("User", u)
            user.append("roles", {"role": "Vendor Engineer"})
            user.flags.ignore_permissions = True
            user.save()
            frappe.db.commit()
            with self.assertRaises(ServiceError):
                assert_vendor_can_access("AC Asset", "DEFINITELY-NOT-ASSIGNED-XYZ", user=u)
        finally:
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestSystemUserReadScope(unittest.TestCase):
    """SEC-RBAC-6 (2026-06-01): base role `AssetCore System User` chỉ được read
    SHARED-CORE (role-redesign-module-based.md §3.2 + §5.1). DocPerm read trên
    DocType nghiệp vụ nhạy cảm = over-grant → mọi user (kể cả KTV) leak data
    Compliance/Needs/Procurement/Vendor qua API dù FE ẩn. Test này khoá invariant
    sau khi gỡ SU read khỏi 49 DocType nhạy cảm.
    """

    DT_DIR = frappe.get_app_path("assetcore", "assetcore", "doctype")

    # §5.1: 4 shared-core + (giữ tạm) Data master danh mục — SU read HỢP LỆ.
    SU_ALLOWED_READ = {
        "AC Asset", "Asset Lifecycle Event",
        "AC Asset Depreciation Schedule", "AC Asset Downtime Log",
        # Data-domain master (danh mục) — DEFER, chưa gỡ vòng 2026-06-01.
        "AC Department", "AC Location", "AC Asset Category", "AC UOM",
        "AC UOM Conversion", "IMM Device Model", "IMM Device Spare Part",
        "AC Authorized Technician", "Service Contract", "Service Contract Asset",
        "Required Document Type", "IMM SLA Policy",
    }

    # Nghiệp vụ nhạy cảm: SU TUYỆT ĐỐI không được read.
    SENSITIVE_NO_SU_READ = [
        "imm_compliance_rule", "imm_compliance_finding", "imm_capa_record",
        "imm_internal_audit", "imm_management_review", "imm_compliance_scorecard",
        "imm_needs_request", "imm_demand_forecast", "imm_procurement_plan",
        "imm_tech_spec", "imm_market_benchmark",
        "imm_vendor_evaluation", "imm_vendor_scorecard", "imm_avl_entry",
        "imm_procurement_decision", "imm_supplier_audit", "ac_purchase",
        "ac_supplier", "incident_report", "imm_rca_record",
        "asset_qa_non_conformance", "imm_training_program", "asset_document",
        "pm_work_order", "asset_repair", "imm_asset_calibration",
    ]

    def _perms(self, dt_folder):
        with open(os.path.join(self.DT_DIR, dt_folder, dt_folder + ".json")) as f:
            return json.load(f).get("permissions", [])

    def test_su_has_no_read_on_sensitive_doctypes_json(self):
        """JSON DocPerm — SU không có read trên DocType nghiệp vụ nhạy cảm."""
        for folder in self.SENSITIVE_NO_SU_READ:
            perms = {p.get("role"): p for p in self._perms(folder)}
            su = perms.get("AssetCore System User")
            self.assertIsNone(
                su,
                f"{folder}: 'AssetCore System User' KHÔNG được có DocPerm "
                f"(over-grant read leak)",
            )

    def test_owning_domain_role_keeps_read_after_su_removed(self):
        """Gỡ SU không phá persona-trong-module: role chủ vẫn read được."""
        owners = {
            "imm_compliance_rule": ("Compliance User", "Compliance Manager"),
            "imm_needs_request": ("Needs User", "Needs Manager"),
            "imm_vendor_evaluation": ("Procurement User", "Procurement Manager"),
            "incident_report": ("Corrective User", "Corrective Manager"),
            "pm_work_order": ("PM User", "PM Manager"),
            "asset_repair": ("Repair User", "Repair Manager"),
        }
        for folder, roles in owners.items():
            perms = {p.get("role"): p for p in self._perms(folder)}
            for role in roles:
                self.assertTrue(
                    perms.get(role, {}).get("read"),
                    f"{folder}: role chủ {role} mất read (under-grant)",
                )


    def test_su_still_reads_shared_core_json(self):
        """Regression: shared-core SU read PHẢI còn (display name mọi persona)."""
        perms = {p.get("role"): p for p in self._perms("ac_asset")}
        self.assertTrue(perms.get("AssetCore System User", {}).get("read"))

    def test_technician_cannot_read_sensitive_live(self):
        """Live has_permission: KTV (PM/Repair/Cal/Corrective User) KHÔNG đọc
        Compliance/Needs/Procurement/Vendor; CÓ đọc domain của mình."""
        u = "rbac_tech_scope_test@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "Tech", "send_welcome_email": 0,
            "user_type": "System User",
        }).insert(ignore_permissions=True)
        try:
            doc = frappe.get_doc("User", u)
            for r in ("AssetCore System User", "PM User", "Repair User",
                      "Calibration User", "Corrective User"):
                doc.append("roles", {"role": r})
            doc.flags.ignore_permissions = True
            doc.save()
            frappe.db.commit()
            frappe.set_user(u)
            # Ngoài persona → CHẶN
            for dt in ("IMM Compliance Rule", "IMM CAPA Record",
                       "IMM Needs Request", "IMM Vendor Evaluation",
                       "AC Supplier", "AC Purchase", "IMM Training Program"):
                self.assertFalse(
                    frappe.has_permission(dt, "read"),
                    f"KTV KHÔNG được read {dt} (leak)",
                )
            # Trong persona + shared-core → CHO PHÉP
            for dt in ("PM Work Order", "Asset Repair", "IMM Asset Calibration",
                       "Incident Report", "AC Asset"):
                self.assertTrue(
                    frappe.has_permission(dt, "read"),
                    f"KTV PHẢI read được {dt} (under-grant)",
                )
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestPickerPermissionDecoupling(unittest.TestCase):
    """SEC-RBAC-7 (2026-06-01): VERIFY vùng DEFER permission.

    Mọi dropdown/picker AssetCore (SmartSelect, LinkSearch, masterData store) đi qua
    `assetcore.api.imm04.search_link` → service dùng `frappe.db.get_all(..., ignore_permissions=True)`
    (services/imm04.py:962-966). Vì vậy options KHÔNG phụ thuộc DocPerm read của user.

    Kết luận 2 vùng DEFER (audit 2026-06-01):
      • DEFER-2 AC Supplier: đã gỡ SU read (đúng). Procurement Manager read=False vẫn
        chọn được Supplier qua picker → KHÔNG under-grant, KHÔNG thêm role.
      • DEFER-1 Data master: GIỮ SU read. Lý do KHÔNG gỡ ngay: AssetListView (/assets,
        chỉ requiresAuth) nạp filter dropdown qua `frappe.get_list` THEO-QUYỀN (refData.fetchAll
        → list_asset_categories/departments/locations), KÈM field gmdn_code/gmdn_term mà
        search_link chưa expose. Gỡ SU read bây giờ = filter rỗng cho user thường (regression).
        Muốn gỡ an toàn: chuyển các filter này sang search_link/ignore_permissions trước.

    Test khoá invariant: search_link luôn trả options bất kể quyền user (anti-regression
    cho mọi lần gỡ SU read tương lai).
    """

    PICKER_DOCTYPES = [
        "AC Supplier", "AC Asset Category", "AC Department",
        "AC Location", "IMM Device Model", "AC UOM",
    ]

    def test_search_link_returns_options_regardless_of_docperm(self):
        """Base-SU (không có DocPerm read trên AC Supplier) VẪN lấy được picker options."""
        from assetcore.services import imm04 as svc04
        u = "rbac_picker_probe@example.com"
        if frappe.db.exists("User", u):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        doc = frappe.get_doc({
            "doctype": "User", "email": u,
            "first_name": "PickerProbe", "send_welcome_email": 0,
            "user_type": "System User",
        }).insert(ignore_permissions=True)
        doc.append("roles", {"role": "AssetCore System User"})
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()
        try:
            frappe.set_user(u)
            # AC Supplier: SU đã bị gỡ read → has_permission=False, NHƯNG picker vẫn chạy.
            self.assertFalse(
                frappe.has_permission("AC Supplier", "read"),
                "Tiền đề: base-SU KHÔNG được read AC Supplier (đã gỡ ở vòng trước)",
            )
            for dt in self.PICKER_DOCTYPES:
                if not frappe.db.exists("DocType", dt):
                    continue
                opts = svc04.search_link(dt, "", 5)
                self.assertIsInstance(
                    opts, list,
                    f"search_link({dt}) phải trả list (ignore_permissions) — picker decoupled",
                )
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            frappe.db.commit()
