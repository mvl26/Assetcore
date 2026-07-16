"""Unit tests for IMM-02 — Tech Spec & Market Analysis service layer."""
from __future__ import annotations
import json
import time
import unittest
from types import SimpleNamespace

import frappe

from assetcore.services import imm02 as svc
from assetcore.api import imm02 as api_imm02
from assetcore.api import user as user_api
from assetcore.setup.setup_role_profiles import seed_assetcore_role_profiles
from assetcore.services.imm02 import (
    _rollup_infra_status,
    _rollup_requirement_counts,
    _validate_gate_g01,
    _validate_gate_g04,
    _compute_candidate_score,
    _parse_weighting,
    validate_lock_in_assessment,
    MIN_MANDATORY_REQUIREMENTS,
    LOCK_IN_THRESHOLD_DEFAULT,
    INFRA_DOMAINS_REQUIRED,
)
from assetcore.services.shared import ErrorCode, ServiceError


def _make_req(parameter: str, is_mandatory: bool, test_method: str = "visual") -> SimpleNamespace:
    return SimpleNamespace(parameter=parameter, is_mandatory=is_mandatory,
                           test_method=test_method, idx=1, seq=None)


def _make_infra_item(domain: str, status: str) -> SimpleNamespace:
    return SimpleNamespace(domain=domain, compatibility_status=status)


def _make_lock_in_item(dimension: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(dimension=dimension, score=score, weight_pct=None, weighted=None)


def _make_ts_doc(**kwargs) -> SimpleNamespace:
    defaults = dict(
        name="_Test-TS-001",
        requirements=[],
        infra_compat=[],
        workflow_state="Draft",
        total_mandatory=0,
        total_optional=0,
        lock_in_score=None,
        lock_in_risk_ref=None,
        mitigation_plan=None,
        mitigation_evidence=None,
        benchmark_ref=None,
        candidate_count=None,
        threshold_used=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestRollupInfraStatus(unittest.TestCase):

    def test_empty_returns_blank(self):
        doc = _make_ts_doc()
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "")

    def test_all_compatible(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "N/A"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "All Compatible")

    def test_need_upgrade_gives_partial(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "Need Upgrade"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "Partial")

    def test_need_major_upgrade_wins(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "Need Major Upgrade"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "Need Major Upgrade")

    def test_no_statuses_returns_blank(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", ""),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "")


class TestRollupRequirementCounts(unittest.TestCase):

    def test_counts_mandatory_optional(self):
        doc = _make_ts_doc(requirements=[
            _make_req("R1", True),
            _make_req("R2", True),
            _make_req("R3", False),
        ])
        _rollup_requirement_counts(doc)
        self.assertEqual(doc.total_mandatory, 2)
        self.assertEqual(doc.total_optional, 1)

    def test_sets_seq_on_each_row(self):
        reqs = [_make_req(f"R{i}", True) for i in range(3)]
        doc = _make_ts_doc(requirements=reqs)
        _rollup_requirement_counts(doc)
        for i, r in enumerate(reqs, 1):
            self.assertEqual(r.seq, i)


class TestGateG01(unittest.TestCase):

    def _make_mandatory_reqs(self, count: int, with_method: bool = True) -> list:
        return [_make_req(f"P{i}", True, "visual" if with_method else "") for i in range(count)]

    def test_below_minimum_raises(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS - 1))
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g01(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_exactly_minimum_passes(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS))
        _validate_gate_g01(doc)  # must not raise

    def test_missing_test_method_raises(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS, with_method=False))
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g01(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)


class TestGateG04(unittest.TestCase):

    def test_below_threshold_passes(self):
        doc = _make_ts_doc(lock_in_score=2.0)
        _validate_gate_g04(doc)  # must not raise

    def test_above_threshold_no_plan_raises(self):
        doc = _make_ts_doc(lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1, mitigation_plan=None)
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_above_threshold_with_plan_but_no_evidence_raises(self):
        doc = _make_ts_doc(
            lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1,
            mitigation_plan="Switching to open protocol",
            mitigation_evidence=None,
        )
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_above_threshold_with_plan_and_evidence_passes(self):
        doc = _make_ts_doc(
            lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1,
            mitigation_plan="Switching to open protocol",
            mitigation_evidence="evidence.pdf",
        )
        _validate_gate_g04(doc)  # must not raise


class TestComputeCandidateScore(unittest.TestCase):

    def test_returns_float_in_range(self):
        cand = SimpleNamespace(spec_match_pct=80, support_tier="Tier1")
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        score = _compute_candidate_score(cand, weights)
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 5.0)

    def test_higher_spec_match_gives_higher_score(self):
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        low = _compute_candidate_score(SimpleNamespace(spec_match_pct=40, support_tier="Tier1"), weights)
        high = _compute_candidate_score(SimpleNamespace(spec_match_pct=90, support_tier="Tier1"), weights)
        self.assertGreater(high, low)

    def test_tier1_better_than_tier3(self):
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        t1 = _compute_candidate_score(SimpleNamespace(spec_match_pct=80, support_tier="Tier1"), weights)
        t3 = _compute_candidate_score(SimpleNamespace(spec_match_pct=80, support_tier="Tier3"), weights)
        self.assertGreater(t1, t3)


class TestParseWeighting(unittest.TestCase):

    def test_none_returns_defaults(self):
        result = _parse_weighting(None)
        self.assertIn("spec", result)
        self.assertIn("price", result)

    def test_dict_passthrough(self):
        d = {"spec": 50, "price": 50}
        self.assertEqual(_parse_weighting(d), d)

    def test_json_string_parsed(self):
        result = _parse_weighting('{"spec": 60, "price": 40}')
        self.assertEqual(result["spec"], 60)

    def test_invalid_json_returns_defaults(self):
        result = _parse_weighting("not-json")
        self.assertIn("spec", result)


class TestValidateLockInAssessment(unittest.TestCase):

    def test_computes_weighted_score(self):
        items = [
            _make_lock_in_item("Protocol Standard", 3.0),
            _make_lock_in_item("Consumable Source", 2.0),
        ]
        doc = SimpleNamespace(items=items, lock_in_score=None,
                              threshold_used=None, spec_ref=None,
                              mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        # Protocol Standard: 3.0 * 0.30 = 0.90; Consumable Source: 2.0 * 0.20 = 0.40 → 1.30
        self.assertAlmostEqual(doc.lock_in_score, 1.30, places=3)

    def test_sets_default_threshold(self):
        doc = SimpleNamespace(items=[], lock_in_score=None, threshold_used=None,
                              spec_ref=None, mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        self.assertEqual(doc.threshold_used, LOCK_IN_THRESHOLD_DEFAULT)

    def test_unknown_dimension_ignored(self):
        items = [_make_lock_in_item("Unknown Dim", 5.0)]
        doc = SimpleNamespace(items=items, lock_in_score=None, threshold_used=None,
                              spec_ref=None, mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        self.assertEqual(doc.lock_in_score, 0.0)


# ─── CTA gating + approval RBAC (GATE-8 / LL-FE-51) ────────────────────────────

_ALL_SPEC_STATES = (
    "Draft", "Reviewing", "Benchmarked", "Risk Assessed",
    "Pending Approval", "Locked", "Withdrawn",
)


def _fixture_pending_approval_roles() -> set[str]:
    """Oracle độc lập: parse role `allowed` của transition rời 'Pending Approval'
    (→ Locked / → Withdrawn) TRỰC TIẾP từ fixtures/workflow.json — KHÔNG import
    _SPEC_APPROVAL_ROLES (chống tautology; khoá "SoT mirror transition")."""
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    roles: set[str] = set()
    for wf in data:
        if wf.get("name") != "IMM-02 Spec Workflow":
            continue
        for t in wf.get("transitions", []):
            if (t.get("state") == "Pending Approval"
                    and t.get("next_state") in ("Locked", "Withdrawn")
                    and t.get("allowed")):
                roles.add(t["allowed"])
    return roles


def _ensure_user(email: str, roles: list[str]) -> str:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    doc = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": email.split("@")[0],
        "enabled": 1,
        "user_type": "System User",
        "send_welcome_email": 0,
        "roles": [{"role": r} for r in roles],
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    frappe.db.commit()
    return email


class TestSpecCtaFlags(unittest.TestCase):
    """_spec_cta_flags = SSoT cờ CTA duyệt; test bằng doc mock + user role thật."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        uid = str(int(time.time() * 1000) % 1_000_000)
        cls.approver = _ensure_user(f"_test_imm02_appr_{uid}@example.com", ["Procurement Manager"])
        cls.specuser = _ensure_user(f"_test_imm02_spec_{uid}@example.com", ["Spec User"])
        cls.superadm = _ensure_user(f"_test_imm02_sadm_{uid}@example.com", ["AssetCore Super Admin"])
        cls.plain    = _ensure_user(f"_test_imm02_none_{uid}@example.com", [])
        cls._users = [cls.approver, cls.specuser, cls.superadm, cls.plain]

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for e in cls._users:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()

    @staticmethod
    def _flags(state: str, user: str, owner: str | None = None) -> dict:
        doc = SimpleNamespace(workflow_state=state, owner=owner or user)
        return svc._spec_cta_flags(doc, user)

    def test_get_tech_spec_emits_cta_flags_pending_approval(self):
        f = self._flags("Pending Approval", self.approver)
        self.assertTrue(f["can_lock"])
        self.assertTrue(f["can_withdraw"])
        self.assertFalse(f["can_reissue"])
        self.assertIn("Locked", f["allowed_transitions"])
        self.assertIn("Withdrawn", f["allowed_transitions"])

    def test_get_tech_spec_no_cta_flags_for_non_approver(self):
        f = self._flags("Pending Approval", self.specuser)
        self.assertFalse(f["can_lock"])
        self.assertFalse(f["can_withdraw"])

    def test_withdraw_flag_parity_from_locked(self):
        f = self._flags("Locked", self.approver)
        self.assertTrue(f["can_withdraw"])
        self.assertFalse(f["can_lock"])
        self.assertFalse(f["can_reissue"])

    def test_reissue_flag_only_when_withdrawn(self):
        # Spec User có DocPerm create trên IMM Tech Spec ⇒ reissue-capable.
        for st in _ALL_SPEC_STATES:
            flag = self._flags(st, self.specuser)["can_reissue"]
            if st == "Withdrawn":
                self.assertTrue(flag, st)
            else:
                self.assertFalse(flag, st)

    def test_super_admin_can_lock_flag_at_pending_approval(self):
        f = self._flags("Pending Approval", self.superadm)
        self.assertTrue(f["can_lock"])

    def test_plain_user_gets_no_flags_any_state(self):
        for st in _ALL_SPEC_STATES:
            f = self._flags(st, self.plain)
            self.assertFalse(f["can_lock"], st)
            self.assertFalse(f["can_withdraw"], st)
            self.assertFalse(f["can_reissue"], st)

    def test_spec_cta_flags_subset_of_guard(self):
        """INVARIANT: cờ advertise ⊆ guard-permitted với MỌI state × user.

        Oracle độc lập (fixture roles + get_roles + has_permission) — nếu ai nới
        _spec_cta_flags advertise rộng hơn guard, test này ĐỎ.
        """
        approver_roles = _fixture_pending_approval_roles()
        # Khoá "SoT mirror transition": set service == set parse từ fixture.
        self.assertEqual(set(svc._SPEC_APPROVAL_ROLES), approver_roles)
        states = list(_ALL_SPEC_STATES) + ["", "Bogus State"]
        for user in self._users:
            is_appr = bool(approver_roles & set(frappe.get_roles(user)))
            can_create = bool(frappe.has_permission("IMM Tech Spec", "create", user=user))
            for st in states:
                f = self._flags(st or "Draft", user)
                if f["can_lock"]:
                    self.assertTrue(st == "Pending Approval" and is_appr, (st, user))
                if f["can_withdraw"]:
                    self.assertTrue(st in ("Pending Approval", "Locked") and is_appr, (st, user))
                if f["can_reissue"]:
                    self.assertTrue(st == "Withdrawn" and can_create, (st, user))


class TestSpecApprovalEnforcement(unittest.TestCase):
    """Enforce RBAC ở _lock_spec/_withdraw_spec — chốt lỗ 'ai cũng Chốt được'."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        uid = str(int(time.time() * 1000) % 1_000_000)
        cls.specuser = _ensure_user(f"_test_imm02e_spec_{uid}@example.com", ["Spec User"])
        cls.superadm = _ensure_user(f"_test_imm02e_sadm_{uid}@example.com", ["AssetCore Super Admin"])
        cls._specs: list[str] = []
        # Master refs cho spec hợp lệ: tái dùng device model + NR-không-active-spec
        # thật (read-only), tạo 1 Procurement Plan throwaway (không link phụ thuộc).
        # Device model có asset_category HỢP LỆ (tránh dangling FK khi fetch category).
        _dm = frappe.db.sql(
            """SELECT dm.name FROM `tabIMM Device Model` dm
               JOIN `tabAC Asset Category` c ON c.name = dm.asset_category LIMIT 1""")
        cls.device_model = _dm[0][0] if _dm else None
        # Pool NR chưa có Tech Spec active — mỗi spec test dùng 1 NR khác (vr01 unique).
        cls._free_nrs = [
            r[0] for r in frappe.db.sql(
                """SELECT nr.name FROM `tabIMM Needs Request` nr WHERE nr.name NOT IN (
                     SELECT COALESCE(source_needs_request,'') FROM `tabIMM Tech Spec`
                     WHERE docstatus<1 AND workflow_state<>'Withdrawn'
                       AND source_needs_request IS NOT NULL) LIMIT 5""")
        ]
        plan = frappe.get_doc({
            "doctype": "IMM Procurement Plan", "plan_period": "Annual",
            "plan_year": 2026, "budget_envelope": 1_000_000,
        })
        plan.flags.ignore_permissions = True
        plan.insert()
        frappe.db.commit()
        cls.plan = plan.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._specs:
            try:
                if frappe.db.exists("IMM Tech Spec", name):
                    d = frappe.get_doc("IMM Tech Spec", name)
                    if d.docstatus == 1:
                        d.cancel()
                    frappe.delete_doc("IMM Tech Spec", name, force=True, ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02 spec cleanup")
            try:
                for r in frappe.get_all("IMM Audit Trail", filters={"asset": name}, pluck="name"):
                    frappe.delete_doc("IMM Audit Trail", r, force=True, ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02 audit cleanup")
        try:
            if getattr(cls, "plan", None) and frappe.db.exists("IMM Procurement Plan", cls.plan):
                frappe.delete_doc("IMM Procurement Plan", cls.plan, force=True, ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "test_imm02 plan cleanup")
        for e in (cls.specuser, cls.superadm):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_pa_spec(self) -> str:
        """Spec hợp lệ tối thiểu ở 'Pending Approval' (6/6 infra Compatible)."""
        if not self.device_model or not self._free_nrs:
            self.skipTest("Thiếu master data (device model / needs request) để dựng spec")
        nr = type(self)._free_nrs.pop()  # NR riêng cho mỗi spec (tránh vr01 DUPLICATE)
        frappe.set_user("Administrator")
        doc = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "version": "1.0",
            "device_model_ref": self.device_model,
            "source_plan": self.plan,
            "source_needs_request": nr,
            "quantity": 1,
            "infra_compat": [
                {"domain": d, "compatibility_status": "Compatible"}
                for d in INFRA_DOMAINS_REQUIRED
            ],
        })
        doc.flags.ignore_permissions = True
        doc.insert()  # ở Draft (initial state); insert trực tiếp 'Pending Approval'
        # sẽ bị validate_workflow chặn (ignore_permissions KHÔNG bypass — LL-BE-62).
        frappe.db.set_value("IMM Tech Spec", doc.name, "workflow_state",
                            "Pending Approval", update_modified=False)
        frappe.db.commit()
        type(self)._specs.append(doc.name)
        return doc.name

    def test_lock_spec_forbidden_without_approver_role(self):
        name = self._make_pa_spec()
        frappe.set_user(self.specuser)
        try:
            with self.assertRaises(ServiceError) as cm:
                api_imm02._lock_spec(name, "approver@example.com", "")
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        # KHÔNG được Lock: state + docstatus giữ nguyên.
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Pending Approval")
        self.assertEqual(frappe.db.get_value("IMM Tech Spec", name, "docstatus"), 0)

    def test_withdraw_spec_forbidden_without_approver_role(self):
        name = self._make_pa_spec()
        frappe.set_user(self.specuser)
        try:
            with self.assertRaises(ServiceError) as cm:
                api_imm02._withdraw_spec(name, "Không còn nhu cầu")
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Pending Approval")

    def test_super_admin_can_lock_at_pending_approval(self):
        name = self._make_pa_spec()
        frappe.set_user(self.superadm)
        try:
            res = api_imm02._lock_spec(name, self.superadm, "regression full-rights")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(res["workflow_state"], "Locked")
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Locked")
        self.assertEqual(frappe.db.get_value("IMM Tech Spec", name, "docstatus"), 1)


# ─── CR-WF-02-SPEC: 6 transition trung gian → server-driven CTA ────────────────
#
# SSoT `_SPEC_VALID_TRANSITIONS` ⇄ imm_02_spec_workflow.json. Đóng bug "Spec kẹt ở
# Draft/Reviewing/Benchmarked/Risk Assessed dù đủ quyền" (FE chỉ có 3 nút EXCEPTION
# lock/withdraw/reissue; endpoint transition_workflow LIVE nhưng 0 nút render 6
# cạnh trung gian). Mirror IMM-03 AVL (`_AVL_VALID_TRANSITIONS`).


def _spec_workflow_json() -> dict:
    """Parse WORKFLOW file imm_02_spec_workflow.json (individual — nguồn Core Doc,
    KHÔNG fixture combined) làm Oracle độc lập cho invariant reconcile."""
    from pathlib import Path
    path = (Path(frappe.get_app_path("assetcore")) / "assetcore" / "workflow"
            / "imm_02_spec_workflow.json")
    return json.loads(path.read_text(encoding="utf-8"))


class TestSpecWorkflowInvariant(unittest.TestCase):
    """INVARIANT: SSoT map reconcile EXACT với imm_02_spec_workflow.json + grounding."""

    # ── reconcile map ⇄ workflow json (RED khi map rỗng/thiếu 1 cạnh) ─────────────
    def test_spec_valid_transitions_reconciles_workflow_json(self):
        from assetcore.services.imm02 import (
            _SPEC_VALID_TRANSITIONS, _SPEC_EXCEPTION_ACTIONS)
        wf = _spec_workflow_json()
        # group fixture transitions theo (state, action, next_state) → set(allowed)
        fixture_roles: dict[tuple, set] = {}
        for t in wf["transitions"]:
            fixture_roles.setdefault(
                (t["state"], t["action"], t["next_state"]), set()).add(t["allowed"])
        # (1) mọi cạnh map == group workflow tương ứng (roles khớp đủ)
        for state, rows in _SPEC_VALID_TRANSITIONS.items():
            for action, next_state, roles in rows:
                key = (state, action, next_state)
                self.assertIn(key, fixture_roles,
                              f"Map edge {key} KHÔNG có trong workflow json (bịa cạnh)")
                self.assertEqual(
                    set(roles), fixture_roles[key],
                    f"ROLE DRIFT {state}/{action}: map {sorted(roles)} != "
                    f"wf {sorted(fixture_roles[key])}")
        # (2) (tập action workflow − tập action map) == _SPEC_EXCEPTION_ACTIONS
        wf_actions = {t["action"] for t in wf["transitions"]}
        map_actions = {a for rows in _SPEC_VALID_TRANSITIONS.values()
                       for a, _n, _r in rows}
        self.assertEqual(
            wf_actions - map_actions, set(_SPEC_EXCEPTION_ACTIONS),
            "(wf_actions - map_actions) PHẢI == _SPEC_EXCEPTION_ACTIONS "
            "(2 cạnh Pending Approval do lock/withdraw endpoint xử lý)")
        # (3) completeness — mọi cạnh workflow (action ∉ EXCEPTION) PHẢI ∈ map
        #     (RED khi map THIẾU 1 cạnh trung gian).
        map_edges = {(s, a, n) for s, rows in _SPEC_VALID_TRANSITIONS.items()
                     for a, n, _r in rows}
        for (state, action, next_state) in fixture_roles:
            if action in _SPEC_EXCEPTION_ACTIONS:
                continue
            self.assertIn(
                (state, action, next_state), map_edges,
                f"Workflow edge {(state, action, next_state)} THIẾU trong map")
        # (4) key-set == states[] (kể cả terminal Locked/Withdrawn có key → [])
        self.assertEqual(set(_SPEC_VALID_TRANSITIONS.keys()),
                         {s["state"] for s in wf["states"]})

    # ── grounding — 0 typo / 0 bịa action + next_state ∈ SpecState enum ───────────
    def test_spec_actions_grounded_no_invention(self):
        from assetcore.services.imm02 import (
            _SPEC_VALID_TRANSITIONS, _SPEC_EXCEPTION_ACTIONS, SpecState)
        wf = _spec_workflow_json()
        wf_actions = {t["action"] for t in wf["transitions"]}
        map_actions = {a for rows in _SPEC_VALID_TRANSITIONS.values()
                       for a, _n, _r in rows}
        # mọi action-label ∈ (map ∪ EXCEPTION) ⊆ tập action workflow (0 typo)
        for a in map_actions | set(_SPEC_EXCEPTION_ACTIONS):
            self.assertIn(a, wf_actions,
                          f"Action '{a}' KHÔNG tồn tại trong workflow json (typo/bịa)")
        # mọi next_state ∈ SpecState enum
        for rows in _SPEC_VALID_TRANSITIONS.values():
            for _a, next_state, _r in rows:
                self.assertIn(next_state, SpecState.ALL,
                              f"next_state '{next_state}' ∉ SpecState enum")
        # _SPEC_EXCEPTION_ACTIONS ⊆ tập action workflow (không bịa)
        self.assertTrue(
            set(_SPEC_EXCEPTION_ACTIONS) <= wf_actions,
            "_SPEC_EXCEPTION_ACTIONS chứa action không tồn tại trong workflow")


class TestSpecAllowedActions(unittest.TestCase):
    """spec_allowed_actions — role-filtered SoT (pure-func, không cần DB)."""

    def test_get_tech_spec_emits_allowed_actions_role_filtered(self):
        from assetcore.services.imm02 import spec_allowed_actions
        # Draft + Spec User → ['Gửi rà soát']
        self.assertEqual(spec_allowed_actions("Draft", {"Spec User"}),
                         ["Gửi rà soát"])
        # Reviewing + Needs Manager → chứa CẢ 2 (yêu cầu chỉnh + hoàn tất benchmark)
        rev_nm = spec_allowed_actions("Reviewing", {"Needs Manager"})
        self.assertIn("Hoàn tất benchmark", rev_nm)
        self.assertIn("Yêu cầu chỉnh spec", rev_nm)
        # Reviewing + Spec User → CHỈ ['Yêu cầu chỉnh spec'] (KHÔNG 'Hoàn tất benchmark')
        self.assertEqual(spec_allowed_actions("Reviewing", {"Spec User"}),
                         ["Yêu cầu chỉnh spec"])
        self.assertNotIn("Hoàn tất benchmark",
                         spec_allowed_actions("Reviewing", {"Spec User"}))
        # None (full SoT) → không lọc role
        self.assertEqual(spec_allowed_actions("Draft", None), ["Gửi rà soát"])
        # Admin roles (+2) thấy đủ tại mỗi state
        adm = {"AssetCore Super Admin"}
        self.assertEqual(spec_allowed_actions("Benchmarked", adm),
                         ["Đánh giá rủi ro xong"])
        self.assertEqual(spec_allowed_actions("Risk Assessed", adm),
                         ["Trình duyệt spec"])
        self.assertEqual(spec_allowed_actions("Pending Approval", adm),
                         ["Yêu cầu chỉnh risk"])

    def test_allowed_actions_terminal_states_empty(self):
        from assetcore.services.imm02 import spec_allowed_actions
        # Locked/Withdrawn (terminal workflow-engine) → []
        for st in ("Locked", "Withdrawn"):
            self.assertEqual(spec_allowed_actions(st, {"AssetCore Super Admin"}), [], st)
            self.assertEqual(spec_allowed_actions(st, None), [], st)
        # state unknown → [] (degrade an toàn)
        self.assertEqual(spec_allowed_actions("Bogus", None), [])
        self.assertEqual(spec_allowed_actions("", None), [])
        self.assertEqual(spec_allowed_actions(None, None), [])
        # can_withdraw/can_reissue (EXCEPTION cờ riêng) KHÔNG lẫn vào allowed_actions.
        acts = spec_allowed_actions("Locked", None)
        self.assertNotIn("Rút spec", acts)
        self.assertNotIn("Phê duyệt spec", acts)


class TestSpecTransitionGuard(unittest.TestCase):
    """transition_workflow guard tường minh (advertise ⟺ reachable) + emit
    allowed_actions. Đóng invariant map ⊆ guard-permitted."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        uid = str(int(time.time() * 1000) % 1_000_000)
        # Low-role reader: có READ (AssetCore Auditor) NHƯNG 0 transition role.
        cls.lowuser = _ensure_user(
            f"_test_imm02g_low_{uid}@example.com", ["AssetCore Auditor"])
        cls._specs: list[str] = []
        _dm = frappe.db.sql(
            """SELECT dm.name FROM `tabIMM Device Model` dm
               JOIN `tabAC Asset Category` c ON c.name = dm.asset_category LIMIT 1""")
        cls.device_model = _dm[0][0] if _dm else None
        cls._free_nrs = [
            r[0] for r in frappe.db.sql(
                """SELECT nr.name FROM `tabIMM Needs Request` nr WHERE nr.name NOT IN (
                     SELECT COALESCE(source_needs_request,'') FROM `tabIMM Tech Spec`
                     WHERE docstatus<1 AND workflow_state<>'Withdrawn'
                       AND source_needs_request IS NOT NULL) LIMIT 3""")
        ]
        plan = frappe.get_doc({
            "doctype": "IMM Procurement Plan", "plan_period": "Annual",
            "plan_year": 2026, "budget_envelope": 1_000_000,
        })
        plan.flags.ignore_permissions = True
        plan.insert()
        frappe.db.commit()
        cls.plan = plan.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._specs:
            try:
                for r in frappe.get_all("IMM Audit Trail",
                                        filters={"asset": name}, pluck="name"):
                    frappe.delete_doc("IMM Audit Trail", r, force=True,
                                      ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02g audit cleanup")
            try:
                if frappe.db.exists("IMM Tech Spec", name):
                    d = frappe.get_doc("IMM Tech Spec", name)
                    if d.docstatus == 1:
                        d.cancel()
                    frappe.delete_doc("IMM Tech Spec", name, force=True,
                                      ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02g spec cleanup")
        try:
            if getattr(cls, "plan", None) and frappe.db.exists(
                    "IMM Procurement Plan", cls.plan):
                frappe.delete_doc("IMM Procurement Plan", cls.plan, force=True,
                                  ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "test_imm02g plan cleanup")
        if frappe.db.exists("User", cls.lowuser):
            frappe.delete_doc("User", cls.lowuser, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_gate_complete_spec(self) -> str:
        """Spec ĐỦ gate (8 mandatory req + candidate_count 3 + 6/6 infra) để mọi
        transition trung gian PASS validate khi apply_workflow (Draft→...→Pending)."""
        if not self.device_model or not type(self)._free_nrs:
            self.skipTest("Thiếu master data (device model / needs request)")
        nr = type(self)._free_nrs.pop()
        frappe.set_user("Administrator")
        doc = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "version": "1.0",
            "device_model_ref": self.device_model,
            "source_plan": self.plan,
            "source_needs_request": nr,
            "quantity": 1,
            "candidate_count": 3,   # G02 (Benchmarked)
            "requirements": [
                {"group": "Performance", "parameter": f"Thông số P{i}",
                 "is_mandatory": 1, "test_method": "Kiểm tra trực quan"}
                for i in range(MIN_MANDATORY_REQUIREMENTS)   # G01 (Reviewing)
            ],
            "infra_compat": [
                {"domain": d, "compatibility_status": "Compatible"}
                for d in INFRA_DOMAINS_REQUIRED   # G03 + VR-05 (Risk Assessed/Pending)
            ],
        })
        doc.flags.ignore_permissions = True
        doc.insert()  # ở Draft (initial state)
        frappe.db.commit()
        type(self)._specs.append(doc.name)
        return doc.name

    def test_get_tech_spec_allowed_actions_key_present(self):
        name = self._make_gate_complete_spec()
        frappe.db.set_value("IMM Tech Spec", name, "workflow_state", "Draft",
                            update_modified=False)
        frappe.db.commit()
        frappe.set_user("Administrator")
        res = api_imm02.get_tech_spec(name)
        self.assertTrue(res.get("success"))
        self.assertIn("allowed_actions", res["data"],
                      "get_tech_spec PHẢI luôn emit key allowed_actions")
        # Admin (System Manager) ở Draft → ['Gửi rà soát']
        self.assertEqual(res["data"]["allowed_actions"], ["Gửi rà soát"])
        # 3 cờ EXCEPTION vẫn có mặt (không regress) — tách kênh khỏi allowed_actions.
        for k in ("can_lock", "can_withdraw", "can_reissue"):
            self.assertIn(k, res["data"])

    def test_advertised_action_reachable_via_transition_workflow(self):
        """Mỗi action ∈ allowed_actions (admin) → transition_workflow KHÔNG raise +
        workflow_state đổi đúng next_state (advertise ⟺ reachable)."""
        from assetcore.services.imm02 import _SPEC_VALID_TRANSITIONS, spec_allowed_actions
        name = self._make_gate_complete_spec()
        frappe.set_user("Administrator")
        admin_roles = frappe.get_roles("Administrator")
        for state, rows in _SPEC_VALID_TRANSITIONS.items():
            for action, next_state, _roles in rows:
                # reset về state nguồn (bypass gate — db.set_value)
                frappe.db.set_value("IMM Tech Spec", name, "workflow_state", state,
                                    update_modified=False)
                frappe.db.commit()
                # advertise: action ∈ allowed_actions (admin đủ role)
                self.assertIn(action, spec_allowed_actions(state, admin_roles),
                              (state, action))
                # reachable: transition_workflow KHÔNG raise + state → next_state
                res = api_imm02.transition_workflow(name, action)
                self.assertTrue(res.get("success"), (state, action, res))
                self.assertEqual(res["data"]["workflow_state"], next_state,
                                 (state, action))
                self.assertEqual(
                    frappe.db.get_value("IMM Tech Spec", name, "workflow_state"),
                    next_state, (state, action))

    def test_low_role_action_hidden_and_guard_raises(self):
        """User thiếu role của cạnh → action VẮNG khỏi allowed_actions VÀ guard
        tường minh raise BAD_STATE (chống nhảy-cóc / advertise ⟺ reachable)."""
        from assetcore.services.imm02 import spec_allowed_actions
        name = self._make_gate_complete_spec()
        frappe.db.set_value("IMM Tech Spec", name, "workflow_state", "Draft",
                            update_modified=False)
        frappe.db.commit()
        frappe.set_user(self.lowuser)
        try:
            low_roles = frappe.get_roles(self.lowuser)
            # (a) action VẮNG khỏi allowed_actions (thiếu role transition)
            self.assertNotIn("Gửi rà soát", spec_allowed_actions("Draft", low_roles))
            # (b) guard tường minh raise BAD_STATE (không đến apply_workflow)
            with self.assertRaises(ServiceError) as cm:
                api_imm02._transition_workflow(name, "Gửi rà soát")
            self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
            # (c) action LẠ (nhảy-cóc) từ Draft cũng bị guard chặn
            with self.assertRaises(ServiceError) as cm2:
                api_imm02._transition_workflow(name, "Hoàn tất benchmark")
            self.assertEqual(cm2.exception.code, ErrorCode.BAD_STATE)
        finally:
            frappe.set_user("Administrator")
        # state KHÔNG đổi (guard chặn trước transition)
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Draft")


# ─── CR-WF-RBAC-PROFILE-COVERAGE: dead-gate persona 'Spec User' @ 'Gửi rà soát' ────
#
# Đóng dead-gate: user mang Role Profile chủ-đích SOẠN spec ('Trưởng phòng VT-TTBYT')
# — NON-admin — PHẢI submit rà soát được (Draft→Reviewing). Trước fix catalog: KHÔNG
# profile nào cấp 'Spec User' → profile-user thiếu role → guard chặn / apply_workflow
# raise (RED). Sau fix (ROLE_PROFILE_CATALOG['Trưởng phòng VT-TTBYT'] += 'Spec User'
# + re-seed live): submit được, wf_state=='Reviewing'. Base user thuần (CHỈ base role
# 'AssetCore System User') VẪN bị chặn — không nới lỏng quá tay.


def _ensure_user_with_profile(email: str, profile: str) -> str:
    """Tạo user (xoá nếu tồn tại) rồi gán Role Profile QUA api thật (roles ĐẾN TỪ
    profile ⇒ coupling với fix catalog). Chạy dưới session Administrator."""
    if frappe.db.exists("User", email):
        frappe.db.set_value("User", email, "role_profile_name", None)
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    doc = frappe.get_doc({
        "doctype": "User", "email": email,
        "first_name": email.split("@")[0], "enabled": 1,
        "user_type": "System User", "send_welcome_email": 0,
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    frappe.db.commit()
    res = user_api.assign_role_profile(email, profile)
    assert res.get("success"), f"assign_role_profile fail: {res}"
    frappe.db.commit()
    return email


class TestSpecProfileDeadGate(unittest.TestCase):
    """Persona chủ-đích soạn spec (non-admin) submit rà soát được sau khi Role Profile
    cấp 'Spec User' (fix CR-WF-RBAC-PROFILE-COVERAGE); base user vẫn bị chặn."""

    _PROFILE = "Trưởng phòng VT-TTBYT"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # DB Role Profile phản ánh catalog HIỆN TẠI → RED/GREEN coupling với fix.
        seed_assetcore_role_profiles()
        uid = str(int(time.time() * 1000) % 1_000_000)
        cls.author = _ensure_user_with_profile(
            f"_test_imm02p_author_{uid}@example.com", cls._PROFILE)
        cls.baseuser = _ensure_user(
            f"_test_imm02p_base_{uid}@example.com", ["AssetCore System User"])
        cls.superadm = _ensure_user(
            f"_test_imm02p_sadm_{uid}@example.com", ["AssetCore Super Admin"])
        cls._users = [cls.author, cls.baseuser, cls.superadm]
        cls._specs: list[str] = []
        # Master data (mirror TestSpecTransitionGuard — device model có category HỢP LỆ).
        _dm = frappe.db.sql(
            """SELECT dm.name FROM `tabIMM Device Model` dm
               JOIN `tabAC Asset Category` c ON c.name = dm.asset_category LIMIT 1""")
        cls.device_model = _dm[0][0] if _dm else None
        cls._free_nrs = [
            r[0] for r in frappe.db.sql(
                """SELECT nr.name FROM `tabIMM Needs Request` nr WHERE nr.name NOT IN (
                     SELECT COALESCE(source_needs_request,'') FROM `tabIMM Tech Spec`
                     WHERE docstatus<1 AND workflow_state<>'Withdrawn'
                       AND source_needs_request IS NOT NULL) LIMIT 4""")
        ]
        plan = frappe.get_doc({
            "doctype": "IMM Procurement Plan", "plan_period": "Annual",
            "plan_year": 2026, "budget_envelope": 1_000_000,
        })
        plan.flags.ignore_permissions = True
        plan.insert()
        frappe.db.commit()
        cls.plan = plan.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._specs:
            try:
                for r in frappe.get_all("IMM Audit Trail",
                                        filters={"asset": name}, pluck="name"):
                    frappe.delete_doc("IMM Audit Trail", r, force=True,
                                      ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02p audit cleanup")
            try:
                if frappe.db.exists("IMM Tech Spec", name):
                    d = frappe.get_doc("IMM Tech Spec", name)
                    if d.docstatus == 1:
                        d.cancel()
                    frappe.delete_doc("IMM Tech Spec", name, force=True,
                                      ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "test_imm02p spec cleanup")
        try:
            if getattr(cls, "plan", None) and frappe.db.exists(
                    "IMM Procurement Plan", cls.plan):
                frappe.delete_doc("IMM Procurement Plan", cls.plan, force=True,
                                  ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "test_imm02p plan cleanup")
        for e in cls._users:
            if frappe.db.exists("User", e):
                frappe.db.set_value("User", e, "role_profile_name", None)
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_draft_spec_8_lines(self) -> str:
        """Tech Spec Draft đủ 8 mandatory spec-line (G01 pass khi → Reviewing)."""
        if not self.device_model or not type(self)._free_nrs:
            self.skipTest("Thiếu master data (device model / needs request)")
        nr = type(self)._free_nrs.pop()
        frappe.set_user("Administrator")
        doc = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "version": "1.0",
            "device_model_ref": self.device_model,
            "source_plan": self.plan,
            "source_needs_request": nr,
            "quantity": 1,
            "requirements": [
                {"group": "Performance", "parameter": f"Thông số P{i}",
                 "is_mandatory": 1, "test_method": "Kiểm tra trực quan"}
                for i in range(MIN_MANDATORY_REQUIREMENTS)  # 8 → G01 pass
            ],
        })
        doc.flags.ignore_permissions = True
        doc.insert()  # Draft (initial state)
        frappe.db.commit()
        type(self)._specs.append(doc.name)
        return doc.name

    # ── author persona (VT-TTBYT, non-admin) submit được (RED trước fix) ──────────
    def test_spec_author_persona_can_submit_for_review(self):
        # (0) author là NON-admin NHƯNG có 'Spec User' (đến từ profile SAU fix).
        author_roles = set(frappe.get_roles(self.author))
        self.assertFalse(
            author_roles & {"AssetCore Super Admin", "System Manager"},
            f"author phải NON-admin, roles={sorted(author_roles)}")
        self.assertIn(
            "Spec User", author_roles,
            "Role Profile 'Trưởng phòng VT-TTBYT' phải cấp 'Spec User' (fix "
            "CR-WF-RBAC-PROFILE-COVERAGE) — thiếu ⇒ dead-gate CHƯA đóng (RED)")
        # (1) tạo Draft 8 spec-line → author submit rà soát → Reviewing.
        name = self._make_draft_spec_8_lines()
        frappe.set_user(self.author)
        try:
            res = api_imm02.transition_workflow(name, "Gửi rà soát")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"submit rà soát fail: {res}")
        self.assertEqual(res["data"]["workflow_state"], "Reviewing")
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Reviewing")

    # ── base user thuần VẪN bị chặn (không nới lỏng quá tay) ──────────────────────
    def test_base_user_still_blocked_submit_for_review(self):
        base_roles = set(frappe.get_roles(self.baseuser))
        self.assertNotIn("Spec User", base_roles,
                         "base user KHÔNG được có 'Spec User'")
        name = self._make_draft_spec_8_lines()
        frappe.set_user(self.baseuser)
        try:
            with self.assertRaises(ServiceError) as cm:
                api_imm02._transition_workflow(name, "Gửi rà soát")
        finally:
            frappe.set_user("Administrator")
        # guard tường minh chặn TRƯỚC apply_workflow (allowed_actions rỗng) → BAD_STATE.
        self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Draft")

    # ── super admin override KHÔNG đổi (regression INV-A) ─────────────────────────
    def test_super_admin_override_unchanged(self):
        name = self._make_draft_spec_8_lines()
        frappe.set_user(self.superadm)
        try:
            res = api_imm02.transition_workflow(name, "Gửi rà soát")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"super admin override fail: {res}")
        self.assertEqual(res["data"]["workflow_state"], "Reviewing")
        self.assertEqual(
            frappe.db.get_value("IMM Tech Spec", name, "workflow_state"), "Reviewing")

    # ── frozenset 'Gửi rà soát' ⇄ workflow 'allowed' (FE hint ⊆ enforcement) ──────
    def test_spec_valid_transitions_frozenset_matches_workflow_allowed(self):
        from assetcore.services.imm02 import _SPEC_VALID_TRANSITIONS
        wf = _spec_workflow_json()
        wf_allowed = {
            t["allowed"] for t in wf["transitions"]
            if t["state"] == "Draft" and t["action"] == "Gửi rà soát"
            and t["next_state"] == "Reviewing"
        }
        map_roles = None
        for action, next_state, roles in _SPEC_VALID_TRANSITIONS["Draft"]:
            if action == "Gửi rà soát" and next_state == "Reviewing":
                map_roles = set(roles)
        self.assertIsNotNone(map_roles, "map thiếu cạnh Draft/'Gửi rà soát'")
        self.assertEqual(
            map_roles, wf_allowed,
            f"frozenset 'Gửi rà soát' {sorted(map_roles)} != workflow allowed "
            f"{sorted(wf_allowed)} (FE allowed_actions hint drift khỏi enforcement)")
