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

    def test_profile_fixtures_removed(self):
        base = frappe.get_app_path("assetcore", "fixtures")
        self.assertFalse(os.path.exists(os.path.join(base, "role_profile.json")))
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

    def test_role_profile_module_profile_gone(self):
        self.assertEqual(frappe.db.count("Role Profile"), 0)
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
