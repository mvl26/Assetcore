# Copyright (c) 2026, AssetCore Team
"""IMM-14 — Decommission Closure Gate test suite (TDD — RED trước).

Cổng "Hồ sơ giải nhiệm": KHÔNG asset nào chuyển sang lifecycle_status=
'Decommissioned' nếu chưa tồn tại 1 'Asset Decommission' record docstatus=1
(Approved) trỏ đúng asset đó.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_imm14
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.tests._asset_cleanup import purge_asset
from assetcore.services.shared import AssetStatus, ServiceError
from assetcore.utils.messages import MSG

_ASSET = "AC Asset"
_DECOM = "Asset Decommission"
_ALE = "Asset Lifecycle Event"
_AUDIT = "IMM Audit Trail"
_SCHED = "AC Asset Depreciation Schedule"


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bỏ qua workflow guard (fixtures), cho phép lifecycle != Draft."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc = frappe.get_doc(data)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        return doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def setUpModule():
    frappe.set_user("Administrator")


class _BaseIMM14(unittest.TestCase):
    """Base — quản lý danh sách asset tự dọn (no leak)."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        for name in self._assets:
            try:
                # Asset Decommission trỏ asset → purge_asset dọn trước qua dependents.
                for d in frappe.get_all(_DECOM, filters={"asset": name}, pluck="name"):
                    doc = frappe.get_doc(_DECOM, d)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(_DECOM, d, force=True, ignore_permissions=True)
                purge_asset(name)
            except Exception:  # noqa: BLE001
                pass
        frappe.db.commit()

    # ── fixtures ─────────────────────────────────────────────────────────────
    def _make_asset(self, suffix: str, *, lifecycle: str = "Active",
                    risk: str = "Medium", gross: float = 0.0) -> str:
        data = {
            "doctype": _ASSET,
            "asset_name": f"_Test IMM14 {suffix}",
            "lifecycle_status": lifecycle,
            "risk_classification": risk,
        }
        if gross > 0:
            data.update({
                "gross_purchase_amount": gross,
                "residual_value": 0,
                "depreciation_method": "Straight Line",
                "total_depreciation_months": 12,
                "depreciation_frequency": "Monthly",
                "depreciation_start_date": "2024-01-01",
                "in_service_date": "2024-01-01",
            })
        doc = _insert_asset_bypass_workflow(data)
        self._assets.append(doc.name)
        # Commit fixture: rollback trong test (sau khi gate/NEG-09 raise) chỉ
        # được undo transition, KHÔNG undo asset fixture (nếu chưa commit, asset
        # bị rollback luôn → get_value trả None).
        frappe.db.commit()
        return doc.name

    def _make_record(self, asset: str, *, disposal="Huỷ",
                     reason="Thiết bị hết khấu hao, sửa chữa không kinh tế, đã có quyết định thanh lý.",
                     sanitized=True, responsible="Administrator",
                     note="") -> str:
        from assetcore.services import imm14
        res = imm14.create_decommission(
            asset=asset, disposal_method=disposal,
            decommission_reason=reason, patient_data_sanitized=sanitized,
            responsible=responsible, sanitization_note=note,
        )
        frappe.db.commit()
        return res["name"]


# ─────────────────────────────────────────────────────────────────────────────
# TC-1 — GATE chặn Decommissioned khi KHÔNG có closure record Approved
# ─────────────────────────────────────────────────────────────────────────────
class TestGateBlocksDecommissionWithoutRecord(_BaseIMM14):

    def test_gate_blocks_decommission_without_record(self):
        from assetcore.services.imm00 import (
            transition_asset_status, InvalidAssetTransition,
        )
        asset = self._make_asset("gate-noclosure", lifecycle="Active")
        before = frappe.db.get_value(_ASSET, asset, "lifecycle_status")
        with self.assertRaises((InvalidAssetTransition, ServiceError)):
            transition_asset_status(
                asset, AssetStatus.DECOMMISSIONED, actor="Administrator",
                reason="Cố thanh lý không qua hồ sơ",
            )
        frappe.db.rollback()
        after = frappe.db.get_value(_ASSET, asset, "lifecycle_status")
        # lifecycle_status BẤT BIẾN
        self.assertEqual(after, before)
        self.assertNotEqual(after, AssetStatus.DECOMMISSIONED)


# ─────────────────────────────────────────────────────────────────────────────
# TC-2 — patient_data_sanitized bắt buộc với risk C/D (High/Critical)
# ─────────────────────────────────────────────────────────────────────────────
class TestPatientDataRequiredForClassCD(_BaseIMM14):

    def test_patient_data_required_for_class_C(self):
        from assetcore.services import imm14
        asset = self._make_asset("pdata-high", lifecycle="Active", risk="High")
        rec = self._make_record(asset, sanitized=False)
        with self.assertRaises(ServiceError) as ctx:
            imm14.approve_decommission(rec)
        self.assertEqual(ctx.exception.message_code, MSG.IMM14_PATIENT_DATA_REQUIRED)
        # asset GIỮ NGUYÊN
        frappe.db.rollback()
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"), "Active")

    def test_patient_data_required_for_class_D(self):
        from assetcore.services import imm14
        asset = self._make_asset("pdata-crit", lifecycle="Active", risk="Critical")
        rec = self._make_record(asset, sanitized=False)
        with self.assertRaises(ServiceError):
            imm14.approve_decommission(rec)
        frappe.db.rollback()
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"), "Active")

    def test_patient_data_not_required_for_class_A_B(self):
        from assetcore.services import imm14
        asset = self._make_asset("pdata-low", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=False)
        # risk Low → không bắt buộc, approve qua
        imm14.approve_decommission(rec)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"),
            AssetStatus.DECOMMISSIONED)


# ─────────────────────────────────────────────────────────────────────────────
# TC-3 — Approve flow: transition + ĐÚNG 1 ALE + ĐÚNG 1 audit + depreciation cancel
# ─────────────────────────────────────────────────────────────────────────────
class TestApproveFlowTransitionsAndAudits(_BaseIMM14):

    def test_approve_flow_transitions_and_audits(self):
        from assetcore.services import imm14, depreciation as depr
        asset = self._make_asset("approve-flow", lifecycle="Active",
                                 risk="Critical", gross=120_000_000)
        # sinh lịch khấu hao Pending
        depr.generate_schedule(asset, force=True)
        frappe.db.commit()
        pending_before = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Pending"})
        self.assertGreater(pending_before, 0, "fixture phải có kỳ Pending")

        ale_before = frappe.db.count(
            _ALE, {"asset": asset, "event_type": "decommissioned"})
        audit_before = frappe.db.count(
            _AUDIT, {"asset": asset, "event_type": "State Change"})

        rec = self._make_record(
            asset, disposal="Bán/Trade-in", sanitized=True,
            reason="Thiết bị hết khấu hao và không còn nhu cầu sử dụng lâm sàng.")
        imm14.approve_decommission(rec)
        frappe.db.commit()

        # (1) asset Decommissioned
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"),
            AssetStatus.DECOMMISSIONED)
        # docstatus=1
        self.assertEqual(frappe.db.get_value(_DECOM, rec, "docstatus"), 1)
        # decommissioned_on được set
        self.assertTrue(frappe.db.get_value(_DECOM, rec, "decommissioned_on"))

        # (a) ĐÚNG 1 ALE event_type='decommissioned' root_record=rec
        ale_after = frappe.db.count(
            _ALE, {"asset": asset, "event_type": "decommissioned"})
        self.assertEqual(ale_after - ale_before, 1)
        ale_root = frappe.db.get_value(
            _ALE, {"asset": asset, "event_type": "decommissioned"},
            "root_record", order_by="creation desc")
        self.assertEqual(ale_root, rec)

        # (b) ĐÚNG 1 IMM Audit Trail 'State Change' chứa disposal_method + patient_data.
        # transition_asset_status ghi 1 audit 'State Change' (transition) +
        # _record_depreciation_stopped ghi thêm 1 audit 'State Change' (dừng khấu
        # hao, summary KHÁC — không chứa disposal_method). Acceptance (c) là audit
        # transition: ĐÚNG 1 audit chứa disposal_method + dữ liệu bệnh nhân.
        decom_audits = [
            a for a in frappe.get_all(
                _AUDIT, filters={"asset": asset, "event_type": "State Change"},
                fields=["name", "change_summary"])
            if a.change_summary and "Bán/Trade-in" in a.change_summary
            and "dữ liệu bệnh nhân" in a.change_summary.lower()
        ]
        self.assertEqual(len(decom_audits), 1)

        # (c) pending depreciation Cancelled
        pending_after = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Pending"})
        cancelled = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Cancelled"})
        self.assertEqual(pending_after, 0)
        self.assertEqual(cancelled, pending_before)


# ─────────────────────────────────────────────────────────────────────────────
# TC-4 — Idempotent + terminal
# ─────────────────────────────────────────────────────────────────────────────
class TestIdempotentAndTerminal(_BaseIMM14):

    def test_terminal_blocks_second_record(self):
        from assetcore.services import imm14
        asset = self._make_asset("terminal", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        imm14.approve_decommission(rec)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"),
            AssetStatus.DECOMMISSIONED)
        # tạo record thứ 2 cho cùng asset đã Decommissioned → chặn
        with self.assertRaises(ServiceError):
            self._make_record(asset, sanitized=True)

    def test_approve_twice_no_double_effect(self):
        from assetcore.services import imm14
        asset = self._make_asset("idemp", lifecycle="Active",
                                 risk="Low", gross=120_000_000)
        from assetcore.services import depreciation as depr
        depr.generate_schedule(asset, force=True)
        frappe.db.commit()
        pending_before = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Pending"})

        rec = self._make_record(asset, sanitized=True)
        imm14.approve_decommission(rec)
        frappe.db.commit()
        ale_1 = frappe.db.count(
            _ALE, {"asset": asset, "event_type": "decommissioned"})
        cancelled_1 = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Cancelled"})

        # approve lần 2 trên CÙNG record → no-op, no double event / no double cancel
        imm14.approve_decommission(rec)
        frappe.db.commit()
        ale_2 = frappe.db.count(
            _ALE, {"asset": asset, "event_type": "decommissioned"})
        cancelled_2 = frappe.db.count(
            _SCHED, {"parent": asset, "parenttype": _ASSET, "status": "Cancelled"})

        self.assertEqual(ale_1, ale_2, "no double lifecycle event")
        self.assertEqual(cancelled_1, cancelled_2, "no double depreciation cancel")
        self.assertEqual(cancelled_1, pending_before)


# ─────────────────────────────────────────────────────────────────────────────
# TC-5 — NEG-09 vẫn chặn (gate mới KHÔNG bypass guard cũ)
# ─────────────────────────────────────────────────────────────────────────────
class TestNeg09StillBlocks(_BaseIMM14):

    def test_neg09_still_blocks_with_approved_closure(self):
        from assetcore.services import imm14
        from assetcore.services.imm00 import InvalidAssetTransition
        asset = self._make_asset("neg09", lifecycle="Under Repair", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        # approve → on_submit gọi transition; NEG-09 chặn (Under Repair)
        with self.assertRaises((InvalidAssetTransition, ServiceError)):
            imm14.approve_decommission(rec)
        frappe.db.rollback()
        # lifecycle_status GIỮ NGUYÊN
        self.assertEqual(
            frappe.db.get_value(_ASSET, asset, "lifecycle_status"),
            "Under Repair")
        # record KHÔNG submit thành công
        self.assertEqual(frappe.db.get_value(_DECOM, rec, "docstatus"), 0)


# ─────────────────────────────────────────────────────────────────────────────
# TC-IMM14-01 — RBAC đường THẬT: stale-safe deny (KHÔNG KeyError→500)
# ─────────────────────────────────────────────────────────────────────────────
class TestDecommissionRbacGate(_BaseIMM14):
    """USER REWORK IMM-14 (2026-06-04): api.imm14 gate qua rbac.require(
    'decommission.create'). User KHÔNG có DocPerm → PermissionError (403-style),
    KHÔNG KeyError→500 (kể cả khi worker cũ thiếu cap trong RAM — rbac.can deny
    thay vì raise). User CÓ DocPerm → tạo/duyệt thành công."""

    def _mk_user(self, email: str, roles: list[str]) -> str:
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
        frappe.db.commit()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        self._extra_users = getattr(self, "_extra_users", [])
        self._extra_users.append(email)
        return email

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in getattr(self, "_extra_users", []):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()
        super().tearDown()

    def test_create_decommission_no_docperm_denies_not_keyerror(self):
        """No-DocPerm user gọi create_decommission → PermissionError (403),
        TUYỆT ĐỐI KHÔNG KeyError (degrade an toàn, không 500)."""
        from assetcore.api import imm14 as api14
        asset = self._make_asset("rbac_deny", lifecycle="Active", risk="Low")
        noperm = self._mk_user("_test_imm14_noperm@assetcore.test", ["PM User"])
        try:
            frappe.set_user(noperm)
            with self.assertRaises(frappe.PermissionError):
                api14.create_decommission(
                    asset=asset, disposal_method="Huỷ",
                    decommission_reason="Khong du quyen test — phai bi chan o BE.",
                    patient_data_sanitized=1, responsible=noperm,
                )
        except KeyError:  # noqa: BLE001 — chính là regression bị cấm
            self.fail("create_decommission raise KeyError → 500 (stale-unsafe). "
                      "Phải là PermissionError 403.")
        finally:
            frappe.set_user("Administrator")

    def test_create_decommission_with_docperm_succeeds(self):
        """User CÓ DocPerm Asset Decommission (Commissioning Manager) → tạo
        hồ sơ giải nhiệm thành công (no-regression đường thật)."""
        from assetcore.api import imm14 as api14
        asset = self._make_asset("rbac_ok", lifecycle="Active", risk="Low")
        mgr = self._mk_user("_test_imm14_mgr@assetcore.test",
                            ["Commissioning Manager"])
        try:
            frappe.set_user(mgr)
            res = api14.create_decommission(
                asset=asset, disposal_method="Huỷ",
                decommission_reason="Thiet bi het khau hao, da co quyet dinh thanh ly.",
                patient_data_sanitized=1, responsible=mgr,
            )
            frappe.db.commit()
            data = res.get("data") if isinstance(res, dict) else res
            name = data.get("name") if isinstance(data, dict) else None
            self.assertTrue(name, f"phải tạo được DECOM record: {res}")
            self.assertTrue(frappe.db.exists(_DECOM, name))
        finally:
            frappe.set_user("Administrator")


# ─────────────────────────────────────────────────────────────────────────────
# TC-IMM14-LIST — list_decommissions (read-only, permission-scoped) — TDD RED trước
# ─────────────────────────────────────────────────────────────────────────────
class TestListDecommissions(_BaseIMM14):
    """Danh sách "Biên bản giải nhiệm" (WHO HTM §3.8 / NĐ98).

    Acceptance:
      - envelope {data:[...], pagination:{page,page_size,total,...}} (mirror imm16).
      - row: name, asset, asset_name_snapshot, risk_classification_snapshot,
        workflow_state, disposal_method, decommissioned_on, responsible +
        responsible_name (full_name, KHÔNG rò email).
      - filter đo được: workflow_state / disposal_method / asset.
      - RBAC: đi qua DocPerm Asset Decommission (KHÔNG ignore_permissions) —
        user thiếu decommission.read → PermissionError hoặc tập rỗng theo scope.
    """

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in getattr(self, "_extra_users", []):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        frappe.db.commit()
        super().tearDown()

    def _mk_user(self, email: str, roles: list[str],
                 *, first_name: str = "", last_name: str = "") -> str:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": first_name or email.split("@")[0],
            "last_name": last_name or "",
            "send_welcome_email": 0, "user_type": "System User",
        }).insert(ignore_permissions=True)
        for r in roles:
            u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save()
        frappe.db.commit()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        self._extra_users = getattr(self, "_extra_users", [])
        self._extra_users.append(email)
        return email

    def _approved_record(self, suffix: str, *, disposal: str = "Huỷ",
                         responsible: str = "Administrator") -> tuple[str, str]:
        """Tạo + duyệt 1 hồ sơ giải nhiệm → (asset, record). risk Low (no sanitize gate)."""
        from assetcore.services import imm14
        asset = self._make_asset(suffix, lifecycle="Active", risk="Low")
        rec = self._make_record(asset, disposal=disposal, sanitized=True,
                                responsible=responsible)
        imm14.approve_decommission(rec)
        frappe.db.commit()
        return asset, rec

    def _names(self, res: dict) -> list[str]:
        return [r["name"] for r in res["data"]]

    # ── envelope + Approved record ───────────────────────────────────────────
    def test_list_decommissions_returns_approved_record(self):
        from assetcore.services import imm14
        asset, rec = self._approved_record("list-approved")
        res = imm14.list_decommissions({})
        # envelope shape
        self.assertIn("data", res)
        self.assertIn("pagination", res)
        for key in ("page", "page_size", "total"):
            self.assertIn(key, res["pagination"])
        # record present + fields
        row = next((r for r in res["data"] if r["name"] == rec), None)
        self.assertIsNotNone(row, f"record {rec} phải có trong danh sách")
        self.assertEqual(row["workflow_state"], "Approved")
        self.assertTrue(row["asset_name_snapshot"])
        self.assertEqual(row["asset"], asset)
        self.assertIn("disposal_method", row)
        self.assertIn("decommissioned_on", row)
        self.assertIn("responsible_name", row)

    # ── filter workflow_state ────────────────────────────────────────────────
    def test_list_decommissions_filter_by_state(self):
        from assetcore.services import imm14
        # Draft (chưa duyệt)
        draft_asset = self._make_asset("list-draft", lifecycle="Active", risk="Low")
        draft_rec = self._make_record(draft_asset, sanitized=True)
        # Approved
        _, appr_rec = self._approved_record("list-appr-state")

        res_appr = imm14.list_decommissions({"workflow_state": "Approved"})
        self.assertIn(appr_rec, self._names(res_appr))
        self.assertNotIn(draft_rec, self._names(res_appr))

        res_draft = imm14.list_decommissions({"workflow_state": "Draft"})
        self.assertIn(draft_rec, self._names(res_draft))
        self.assertNotIn(appr_rec, self._names(res_draft))

    # ── filter disposal_method ───────────────────────────────────────────────
    def test_list_decommissions_filter_by_disposal_method(self):
        from assetcore.services import imm14
        _, rec_huy = self._approved_record("list-huy", disposal="Huỷ")
        _, rec_ban = self._approved_record("list-ban", disposal="Bán/Trade-in")

        res = imm14.list_decommissions({"disposal_method": "Bán/Trade-in"})
        names = self._names(res)
        self.assertIn(rec_ban, names)
        self.assertNotIn(rec_huy, names)
        # mọi row trả về đều đúng phương thức đã lọc
        for r in res["data"]:
            self.assertEqual(r["disposal_method"], "Bán/Trade-in")

    # ── RBAC: user thiếu decommission.read → PermissionError / tập rỗng ───────
    def test_list_decommissions_respects_rbac(self):
        from assetcore.api import imm14 as api14
        from assetcore.services import imm14 as svc14
        _, rec = self._approved_record("list-rbac")
        noperm = self._mk_user("_test_imm14_list_noperm@assetcore.test", ["PM User"])
        try:
            frappe.set_user(noperm)
            # (1) API layer gate rbac.require('decommission.read') → PermissionError.
            with self.assertRaises(frappe.PermissionError):
                api14.list_decommissions(filters="{}")
            # (2) Service layer qua frappe.get_list (DocPerm) → KHÔNG rò hồ sơ ngoài
            #     quyền: hoặc PermissionError, hoặc tập rỗng (record người khác vắng mặt).
            try:
                res = svc14.list_decommissions({})
                self.assertNotIn(rec, self._names(res))
            except frappe.PermissionError:
                pass
        finally:
            frappe.set_user("Administrator")

    # ── responsible_name = full_name (KHÔNG rò email) ────────────────────────
    def test_list_decommissions_responsible_enriched_not_email(self):
        from assetcore.services import imm14
        resp = self._mk_user(
            "_test_imm14_resp@assetcore.test", ["Commissioning Manager"],
            first_name="Nguyễn Văn", last_name="Trách Nhiệm")
        _, rec = self._approved_record("list-resp", responsible=resp)
        res = imm14.list_decommissions({})
        row = next((r for r in res["data"] if r["name"] == rec), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["responsible"], resp)  # raw id = email
        self.assertEqual(row["responsible_name"], "Nguyễn Văn Trách Nhiệm")
        # KHÔNG rò email + khác raw responsible id (LL-FE-53 / user_source policy)
        self.assertNotIn("@", row["responsible_name"] or "")
        self.assertNotEqual(row["responsible_name"], row["responsible"])


# ─────────────────────────────────────────────────────────────────────────────
# TC-IMM14-CTA — get_decommission.can_approve + approve_blocked_reason (GATE-8) —
# server-driven CTA + SoT parity (get ⇆ approve dùng CÙNG helper). TDD RED trước.
# ─────────────────────────────────────────────────────────────────────────────
class TestDecommissionApproveGate(_BaseIMM14):
    """Bề mặt DUYỆT server-driven (GATE-8/LL-FE-51).

    Acceptance:
      - get_decommission emit can_approve (int 0/1) = rbac.can('decommission.approve')
        AND doc-state-approvable (draft + asset chưa Decommissioned + field-gate
        patient_data C/D đạt).
      - approve_blocked_reason = chuỗi VI (từ MSG.*, rỗng khi can_approve=1).
      - can_approve dẫn xuất CÙNG helper SoT mà approve_decommission enforce
        (flip 1 điều kiện → cả 2 đổi đồng bộ, chống desync).
    """

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in getattr(self, "_extra_users", []):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        frappe.db.commit()
        super().tearDown()

    def _mk_user(self, email: str, roles: list[str]) -> str:
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
        frappe.db.commit()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        self._extra_users = getattr(self, "_extra_users", [])
        self._extra_users.append(email)
        return email

    @staticmethod
    def _rendered(code: str, **ctx) -> str:
        from assetcore.utils.messages import format_message
        return format_message(code, ctx)[1]

    # ── can_approve=1 (draft + có cap + patient_data ok) → reason rỗng ─────────
    def test_get_can_approve_true_for_draft_with_cap(self):
        from assetcore.services import imm14
        asset = self._make_asset("cta-ok", lifecycle="Active", risk="Critical")
        rec = self._make_record(asset, sanitized=True)  # High/Critical → sanitized reqd
        mgr = self._mk_user("_test_imm14_cta_mgr@assetcore.test",
                            ["Commissioning Manager"])
        try:
            frappe.set_user(mgr)
            out = imm14.get_decommission(rec)
            self.assertEqual(out["can_approve"], 1)
            self.assertEqual(out["approve_blocked_reason"], "")
        finally:
            frappe.set_user("Administrator")

    # ── can_approve=0 (a) thiếu cap (Commissioning User submit=0) ─────────────
    def test_get_can_approve_false_missing_cap(self):
        from assetcore.services import imm14
        asset = self._make_asset("cta-nocap", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        user = self._mk_user("_test_imm14_cta_user@assetcore.test",
                             ["Commissioning User"])
        try:
            frappe.set_user(user)
            out = imm14.get_decommission(rec)
            self.assertEqual(out["can_approve"], 0)
            self.assertEqual(
                out["approve_blocked_reason"],
                self._rendered(MSG.IMM14_NO_APPROVE_PERMISSION))
        finally:
            frappe.set_user("Administrator")

    # ── can_approve=0 (b) đã docstatus=1 (Approved) ──────────────────────────
    def test_get_can_approve_false_already_approved(self):
        from assetcore.services import imm14
        asset = self._make_asset("cta-appr", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        imm14.approve_decommission(rec)
        frappe.db.commit()
        mgr = self._mk_user("_test_imm14_cta_appr_mgr@assetcore.test",
                            ["Commissioning Manager"])
        try:
            frappe.set_user(mgr)
            out = imm14.get_decommission(rec)
            self.assertEqual(out["can_approve"], 0)
            self.assertEqual(
                out["approve_blocked_reason"],
                self._rendered(MSG.IMM14_ALREADY_APPROVED))
        finally:
            frappe.set_user("Administrator")

    # ── can_approve=0 (c) asset đã Decommissioned bởi record khác ─────────────
    def test_get_can_approve_false_asset_terminal(self):
        from assetcore.services import imm14
        asset = self._make_asset("cta-term", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        # Mô phỏng: asset đã bị record khác giải nhiệm (đặt terminal trực tiếp).
        frappe.db.set_value(_ASSET, asset, "lifecycle_status",
                            AssetStatus.DECOMMISSIONED)
        frappe.db.commit()
        mgr = self._mk_user("_test_imm14_cta_term_mgr@assetcore.test",
                            ["Commissioning Manager"])
        try:
            frappe.set_user(mgr)
            out = imm14.get_decommission(rec)
            self.assertEqual(out["can_approve"], 0)
            self.assertEqual(
                out["approve_blocked_reason"],
                self._rendered(MSG.IMM14_ALREADY_DECOMMISSIONED, asset=asset))
        finally:
            frappe.set_user("Administrator")

    # ── approve: docstatus 0→1 + asset Decommissioned + payload ──────────────
    def test_approve_transitions_and_payload(self):
        from assetcore.services import imm14
        asset = self._make_asset("appr-payload", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        payload = imm14.approve_decommission(rec)
        frappe.db.commit()
        self.assertEqual(payload["docstatus"], 1)
        self.assertEqual(payload["asset"], asset)
        self.assertEqual(payload["lifecycle_status"], AssetStatus.DECOMMISSIONED)
        self.assertTrue(payload["decommissioned_on"])
        # gọi lần 2 idempotent no-op (KHÔNG double effect)
        payload2 = imm14.approve_decommission(rec)
        self.assertEqual(payload2["docstatus"], 1)
        self.assertEqual(payload2["lifecycle_status"], AssetStatus.DECOMMISSIONED)

    # ── approve: asset đã Decommissioned bởi record khác → BAD_STATE/409 ──────
    def test_approve_blocked_when_asset_terminal(self):
        from assetcore.services import imm14
        asset = self._make_asset("appr-term", lifecycle="Active", risk="Low")
        rec = self._make_record(asset, sanitized=True)
        frappe.db.set_value(_ASSET, asset, "lifecycle_status",
                            AssetStatus.DECOMMISSIONED)
        frappe.db.commit()
        with self.assertRaises(ServiceError) as ctx:
            imm14.approve_decommission(rec)
        self.assertEqual(ctx.exception.message_code, MSG.IMM14_ALREADY_DECOMMISSIONED)
        self.assertEqual(ctx.exception.http_status, 409)
        # record KHÔNG submit
        self.assertEqual(frappe.db.get_value(_DECOM, rec, "docstatus"), 0)

    # ── INVARIANT (GATE-8): get.can_approve ⇆ approve dùng CÙNG helper SoT ────
    def test_can_approve_and_approve_derive_same_gate(self):
        """Flip 1 điều kiện gate (patient_data) → CẢ get.can_approve và
        approve_decommission đổi đồng bộ (chống desync server-driven CTA)."""
        from assetcore.services import imm14
        asset = self._make_asset("invariant", lifecycle="Active", risk="Critical")
        rec = self._make_record(asset, sanitized=False)  # High/Critical + chưa sanitize
        mgr = self._mk_user("_test_imm14_inv_mgr@assetcore.test",
                            ["Commissioning Manager"])

        # (1) chưa sanitize → get.can_approve=0 + approve raise PATIENT_DATA_REQUIRED
        try:
            frappe.set_user(mgr)
            out = imm14.get_decommission(rec)
            self.assertEqual(out["can_approve"], 0)
            self.assertEqual(
                out["approve_blocked_reason"],
                self._rendered(MSG.IMM14_PATIENT_DATA_REQUIRED, risk="Critical"))
        finally:
            frappe.set_user("Administrator")
        with self.assertRaises(ServiceError) as ctx:
            imm14.approve_decommission(rec)
        self.assertEqual(ctx.exception.message_code, MSG.IMM14_PATIENT_DATA_REQUIRED)
        frappe.db.rollback()

        # (2) FLIP điều kiện: đánh dấu đã xử lý dữ liệu bệnh nhân
        frappe.db.set_value(_DECOM, rec, "patient_data_sanitized", 1)
        frappe.db.commit()
        # get.can_approve=1 + reason rỗng (đồng bộ)
        try:
            frappe.set_user(mgr)
            out2 = imm14.get_decommission(rec)
            self.assertEqual(out2["can_approve"], 1)
            self.assertEqual(out2["approve_blocked_reason"], "")
        finally:
            frappe.set_user("Administrator")
        # approve giờ THÀNH CÔNG (đồng bộ với can_approve=1)
        payload = imm14.approve_decommission(rec)
        frappe.db.commit()
        self.assertEqual(payload["lifecycle_status"], AssetStatus.DECOMMISSIONED)


if __name__ == "__main__":
    unittest.main()
